"""
Analysis API routes with comprehensive error handling and validation
"""
from fastapi import APIRouter, HTTPException, Query, Path, Depends, status
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime, timedelta
from enum import Enum

from storage.mongodb_client import get_mongodb
from core.gemini_extractor import GeminiExtractor
from core.auth import get_current_user, User, require_scopes
from utils.logger import logger
from utils.cache import cache_decorator

router = APIRouter(prefix="/api/v1/analysis", tags=["analysis"])


# ==================== Enums ====================

class SortOrder(str, Enum):
    """Sort order options"""
    ASC = "asc"
    DESC = "desc"


class AnalyticsPeriod(int, Enum):
    """Analytics period options"""
    ONE_DAY = 1
    SEVEN_DAYS = 7
    THIRTY_DAYS = 30
    NINETY_DAYS = 90


# ==================== Request Models ====================

class SentimentAnalysisRequest(BaseModel):
    """Sentiment analysis request"""
    asin: str = Field(
        ...,
        min_length=10,
        max_length=10,
        description="Product ASIN (10 characters)"
    )
    max_reviews: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Max reviews to analyze"
    )
    language: str = Field(
        default="en",
        pattern="^[a-z]{2}$",
        description="Language code (e.g., 'en', 'es')"
    )

    @validator("asin")
    def validate_asin(cls, v):
        """Validate ASIN format"""
        if not v.isalnum():
            raise ValueError("ASIN must be alphanumeric")
        return v.upper()


class ComparisonRequest(BaseModel):
    """Product comparison request"""
    asins: List[str] = Field(
        ...,
        min_items=2,
        max_items=5,
        description="ASINs to compare"
    )
    include_price_history: bool = Field(
        default=False,
        description="Include price history in comparison"
    )
    price_history_days: int = Field(
        default=30,
        ge=1,
        le=365,
        description="Days of price history to include"
    )

    @validator("asins")
    def validate_asins(cls, v):
        """Validate and normalize ASINs"""
        return [asin.upper() for asin in v]


# ==================== Response Models ====================

class PricePoint(BaseModel):
    """Price history point"""
    timestamp: datetime
    price: float
    currency: str = "USD"


class PriceHistoryResponse(BaseModel):
    """Price history response"""
    asin: str
    title: str
    current_price: float
    lowest_price: float
    highest_price: float
    average_price: float
    price_change_percentage: float
    price_change_amount: float
    history_points: int
    history: List[PricePoint]
    currency: str = "USD"

    class Config:
        from_attributes = True


class SentimentAnalysisResponse(BaseModel):
    """Sentiment analysis response"""
    success: bool
    asin: str
    sentiment_score: float = Field(..., ge=-1, le=1)
    sentiment_label: str
    reviews_analyzed: int
    confidence: float = Field(..., ge=0, le=1)
    aspects: Optional[Dict[str, float]] = None
    timestamp: datetime


class ProductComparisonItem(BaseModel):
    """Product comparison item"""
    asin: str
    title: str
    brand: Optional[str]
    current_price: float
    currency: str = "USD"
    rating: float = Field(default=0, ge=0, le=5)
    reviews_count: int = Field(default=0, ge=0)
    availability_status: str
    price_history: Optional[List[PricePoint]] = None


class ComparisonResult(BaseModel):
    """Comparison result"""
    success: bool
    products: List[ProductComparisonItem]
    best_price: Optional[Dict[str, Any]]
    best_rating: Optional[Dict[str, Any]]
    most_reviews: Optional[Dict[str, Any]]
    price_difference: Optional[float]
    rating_difference: Optional[float]
    comparison_timestamp: datetime


class AnalyticsSummary(BaseModel):
    """Analytics summary"""
    period_days: int
    total_products_tracked: int
    average_price_change: float
    price_volatility: float
    trending_brands: List[Dict[str, Any]]
    market_insights: Optional[Dict[str, Any]]


class TrendingProduct(BaseModel):
    """Trending product"""
    asin: str
    title: str
    brand: Optional[str]
    current_price: float
    rating: float = Field(default=0, ge=0, le=5)
    reviews_count: int = Field(default=0, ge=0)
    scrape_count: int
    trend_score: float
    last_scraped: datetime


# ==================== Dependencies ====================

async def validate_product_exists(
    asin: str,
    mongodb = Depends(get_mongodb)
) -> Dict[str, Any]:
    """
    Validate that product exists in database
    
    Args:
        asin: Product ASIN
        mongodb: MongoDB client
        
    Returns:
        Product document
        
    Raises:
        HTTPException: If product not found
    """
    try:
        product = await mongodb.db.products.find_one({"asin": asin})
        
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with ASIN '{asin}' not found"
            )
        
        return product
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating product: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error"
        )


# ==================== Endpoints ====================

@router.get(
    "/price-history/{asin}",
    response_model=PriceHistoryResponse,
    summary="Get price history"
)
async def get_price_history(
    asin: str = Path(..., min_length=10, max_length=10, description="Product ASIN"),
    days: int = Query(30, ge=1, le=365, description="Number of days"),
    product: Dict = Depends(validate_product_exists),
    current_user: User = Depends(get_current_user),
    mongodb = Depends(get_mongodb)
):
    """
    Get price history for product
    
    Returns price statistics and historical price points for the specified period.
    
    Args:
        asin: Product ASIN (10 characters)
        days: Number of days to look back (1-365)
        
    Returns:
        Price history with statistics
        
    Raises:
        HTTPException: 404 if product not found, 400 if invalid parameters
    """
    try:
        asin = asin.upper()
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Get price history from database
        history_cursor = mongodb.db.price_history.find({
            "asin": asin,
            "timestamp": {"$gte": cutoff_date}
        }).sort("timestamp", 1)
        
        history = await history_cursor.to_list(length=None)
        
        if not history:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No price history found for ASIN '{asin}' in the last {days} days"
            )
        
        # Convert to PricePoint objects
        price_points = [
            PricePoint(
                timestamp=entry.get("timestamp"),
                price=float(entry.get("price", 0)),
                currency=entry.get("currency", "USD")
            )
            for entry in history
        ]
        
        # Calculate statistics
        prices = [p.price for p in price_points]
        current_price = prices[-1] if prices else 0
        lowest_price = min(prices) if prices else current_price
        highest_price = max(prices) if prices else current_price
        average_price = sum(prices) / len(prices) if prices else current_price
        
        # Calculate price change
        first_price = prices[0]
        price_change_amount = current_price - first_price
        price_change_percentage = (
            (price_change_amount / first_price * 100) if first_price > 0 else 0
        )
        
        logger.info(
            f"Price history retrieved",
            asin=asin,
            days=days,
            data_points=len(price_points),
            user_id=current_user.id
        )
        
        return PriceHistoryResponse(
            asin=asin,
            title=product.get("title", ""),
            current_price=round(current_price, 2),
            lowest_price=round(lowest_price, 2),
            highest_price=round(highest_price, 2),
            average_price=round(average_price, 2),
            price_change_percentage=round(price_change_percentage, 2),
            price_change_amount=round(price_change_amount, 2),
            history_points=len(price_points),
            history=price_points,
            currency=price_points[0].currency if price_points else "USD"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting price history: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve price history"
        )


@router.post(
    "/sentiment",
    response_model=SentimentAnalysisResponse,
    summary="Analyze product sentiment"
)
async def analyze_sentiment(
    request: SentimentAnalysisRequest,
    current_user: User = Depends(require_scopes(["analysis"])),
    mongodb = Depends(get_mongodb)
):
    """
    Analyze product review sentiment using AI
    
    Analyzes reviews to determine sentiment score and sentiment breakdown
    by aspect (quality, value, delivery, etc.).
    
    Args:
        request: Sentiment analysis request with ASIN and parameters
        
    Returns:
        Sentiment analysis results with score and confidence
        
    Raises:
        HTTPException: 404 if product not found, 400 for invalid request
    """
    try:
        # Validate product exists
        product = await mongodb.db.products.find_one({"asin": request.asin})
        
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product '{request.asin}' not found"
            )
        
        # Get reviews from database
        reviews_cursor = mongodb.db.reviews.find({
            "asin": request.asin
        }).limit(request.max_reviews).sort("timestamp", -1)
        
        reviews = await reviews_cursor.to_list(length=request.max_reviews)
        
        if not reviews:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No reviews found for product '{request.asin}'"
            )
        
        # Extract review texts
        review_texts = [review.get("text", "") for review in reviews if review.get("text")]
        
        if not review_texts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No review text available for analysis"
            )
        
        # Analyze with Gemini
        try:
            extractor = GeminiExtractor()
            sentiment_result = await extractor.analyze_reviews_sentiment(
                reviews=review_texts,
                language=request.language
            )
        except Exception as e:
            logger.error(f"Gemini analysis error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI analysis service unavailable"
            )
        
        # Determine sentiment label
        score = sentiment_result.get("score", 0)
        if score >= 0.2:
            label = "positive"
        elif score <= -0.2:
            label = "negative"
        else:
            label = "neutral"
        
        # Update product with sentiment
        await mongodb.db.products.update_one(
            {"asin": request.asin},
            {
                "$set": {
                    "sentiment_score": score,
                    "sentiment_label": label,
                    "sentiment_updated_at": datetime.utcnow(),
                    "reviews_analyzed": len(review_texts)
                }
            }
        )
        
        logger.info(
            f"Sentiment analysis completed",
            asin=request.asin,
            score=score,
            reviews_count=len(review_texts),
            user_id=current_user.id
        )
        
        return SentimentAnalysisResponse(
            success=True,
            asin=request.asin,
            sentiment_score=round(score, 3),
            sentiment_label=label,
            reviews_analyzed=len(review_texts),
            confidence=sentiment_result.get("confidence", 0),
            aspects=sentiment_result.get("aspects"),
            timestamp=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing sentiment: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze sentiment"
        )


@router.post(
    "/compare",
    response_model=ComparisonResult,
    summary="Compare products"
)
async def compare_products(
    request: ComparisonRequest,
    current_user: User = Depends(get_current_user),
    mongodb = Depends(get_mongodb)
):
    """
    Compare multiple products
    
    Compares products by price, rating, reviews, and other metrics.
    Optionally includes price history for each product.
    
    Args:
        request: Comparison request with list of ASINs
        
    Returns:
        Detailed comparison with best products identified
        
    Raises:
        HTTPException: 400 if less than 2 valid products
    """
    try:
        # Fetch all products
        products_data = []
        
        for asin in request.asins:
            product = await mongodb.db.products.find_one({"asin": asin})
            
            if product:
                products_data.append(product)
        
        # Validate minimum products
        if len(products_data) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"At least 2 valid products required. Found {len(products_data)}"
            )
        
        # Build comparison items
        comparison_items = []
        prices = []
        ratings = []
        
        for product in products_data:
            # Get price history if requested
            price_history = None
            if request.include_price_history:
                cutoff_date = datetime.utcnow() - timedelta(days=request.price_history_days)
                history_cursor = mongodb.db.price_history.find({
                    "asin": product["asin"],
                    "timestamp": {"$gte": cutoff_date}
                }).sort("timestamp", -1).limit(10)
                
                history_data = await history_cursor.to_list(length=10)
                price_history = [
                    PricePoint(
                        timestamp=h.get("timestamp"),
                        price=float(h.get("price", 0)),
                        currency=h.get("currency", "USD")
                    )
                    for h in history_data
                ]
            
            current_price = product.get("current_price", 0)
            rating = product.get("rating", 0)
            
            item = ProductComparisonItem(
                asin=product["asin"],
                title=product.get("title", ""),
                brand=product.get("brand"),
                current_price=current_price,
                rating=rating,
                reviews_count=product.get("reviews_count", 0),
                availability_status=product.get("availability", "unknown"),
                price_history=price_history
            )
            
            comparison_items.append(item)
            prices.append(current_price)
            ratings.append(rating)
        
        # Identify best products
        best_price = min(comparison_items, key=lambda x: x.current_price)
        best_rating = max(comparison_items, key=lambda x: x.rating)
        most_reviews = max(comparison_items, key=lambda x: x.reviews_count)
        
        # Calculate differences
        price_difference = max(prices) - min(prices)
        rating_difference = max(ratings) - min(ratings)
        
        logger.info(
            f"Product comparison completed",
            asins=request.asins,
            product_count=len(comparison_items),
            user_id=current_user.id
        )
        
        return ComparisonResult(
            success=True,
            products=comparison_items,
            best_price={
                "asin": best_price.asin,
                "price": best_price.current_price
            },
            best_rating={
                "asin": best_rating.asin,
                "rating": best_rating.rating
            },
            most_reviews={
                "asin": most_reviews.asin,
                "reviews": most_reviews.reviews_count
            },
            price_difference=round(price_difference, 2),
            rating_difference=round(rating_difference, 2),
            comparison_timestamp=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing products: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compare products"
        )


@router.get(
    "/analytics",
    response_model=AnalyticsSummary,
    summary="Get analytics summary"
)
async def get_analytics(
    days: int = Query(7, ge=1, le=90, description="Days to analyze"),
    current_user: User = Depends(get_current_user),
    mongodb = Depends(get_mongodb)
):
    """
    Get analytics summary
    
    Returns market insights, price trends, and top-performing brands
    for the specified period.
    
    Args:
        days: Number of days to analyze (1-90)
        
    Returns:
        Analytics summary with trends and insights
    """
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Get total products tracked
        total_products = await mongodb.db.products.count_documents({})
        
        # Get price change average
        pipeline = [
            {
                "$match": {
                    "timestamp": {"$gte": cutoff_date}
                }
            },
            {
                "$group": {
                    "_id": "$asin",
                    "first_price": {"$first": "$price"},
                    "last_price": {"$last": "$price"}
                }
            },
            {
                "$project": {
                    "change_percentage": {
                        "$cond": [
                            {"$gt": ["$first_price", 0]},
                            {
                                "$multiply": [
                                    {"$divide": [
                                        {"$subtract": ["$last_price", "$first_price"]},
                                        "$first_price"
                                    ]},
                                    100
                                ]
                            },
                            0
                        ]
                    }
                }
            }
        ]
        
        results = await mongodb.db.price_history.aggregate(pipeline).to_list(None)
        
        avg_price_change = (
            sum(r.get("change_percentage", 0) for r in results) / len(results)
            if results else 0
        )
        
        # Get price volatility
        price_volatility = (
            max(
                (r.get("change_percentage", 0) for r in results),
                default=0
            ) if results else 0
        )
        # Get top brands
        top_brands_pipeline = [
            {"$match": {"timestamp": {"$gte": cutoff_date}}},
            {"$group": {
                "_id": "$brand",
                "count": {"$sum": 1},
                "avg_rating": {"$avg": "$rating"}
            }},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        
        top_brands = await mongodb.db.products.aggregate(
            top_brands_pipeline
        ).to_list(10)
        
        logger.info(
            f"Analytics retrieved",
            days=days,
            total_products=total_products,
            user_id=current_user.id
        )
        return AnalyticsSummary(
            period_days=days,
            total_products_tracked=total_products,
            average_price_change=round(avg_price_change, 2),
            price_volatility=round(price_volatility, 2),
            trending_brands=[
                {
                    "brand": b.get("_id"),
                    "products": b.get("count", 0),
                    "avg_rating": round(b.get("avg_rating", 0), 2)
                }
                for b in top_brands
            ]
        )
        
    except Exception as e:
        logger.error(f"Error getting analytics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve analytics"
        )
        @router.get(
    "/trending",
    response_model=List[TrendingProduct],
    summary="Get trending products"
)
@cache_decorator(ttl=300)  # Cache for 5 minutes
async def get_trending_products(
    limit: int = Query(10, ge=1, le=50, description="Number of products"),
    current_user: User = Depends(get_current_user),
    mongodb = Depends(get_mongodb)
):
    """
    Get trending products
    
    Returns most recently scraped and viewed products with trend scores.
    Results are cached for 5 minutes.
    
    Args:
        limit: Number of products to return (1-50)
        
    Returns:
        List of trending products with trend scores
    """
    try:
        # Get trending products using aggregation
        pipeline = [
            {
                "$addFields": {
                    "trend_score": {
                        "$add": [
                            {"$multiply": [
                                {"$divide": ["$scrape_count", 100]},
                                0.5
                            ]},
                            {"$multiply": [
                                "$rating",
                                0.3
                            ]},
                            {"$multiply": [
                                {"$divide": [
                                    "$reviews_count",
                                    1000
                                ]},
                                0.2
                            ]}
                        ]
                    }
                }
            },
            {
                "$sort": {"trend_score": -1}
                },
            {
                "$limit": limit
            }
        ]
        
        products = await mongodb.db.products.aggregate(pipeline).to_list(limit)
        
        if not products:
            return []
        
        trending = [
            TrendingProduct(
                asin=p["asin"],
                title=p.get("title", ""),
                brand=p.get("brand"),
                current_price=p.get("current_price", 0),
                rating=p.get("rating", 0),
                reviews_count=p.get("reviews_count", 0),
                scrape_count=p.get("scrape_count", 0),
                trend_score=round(p.get("trend_score", 0), 3),
                last_scraped=p.get("last_scraped", datetime.utcnow())
            )
            for p in products
        ]
        
        logger.info(
            f"Trending products retrieved",
            limit=limit,
            count=len(trending),
            user_id=current_user.id
        )
        
        return trending
        
    except Exception as e:
        logger.error(f"Error getting trending products: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve trending products"
        )
