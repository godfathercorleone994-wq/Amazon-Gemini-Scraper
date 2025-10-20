"""
Analysis API routes
"""
from fastapi import APIRouter, HTTPException, Query, Path
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timedelta

from storage.mongodb_client import get_mongodb
from core.gemini_extractor import GeminiExtractor
from utils.logger import logger

router = APIRouter()

# ==================== Request/Response Models ====================

class PriceHistoryResponse(BaseModel):
    """Price history response"""
    asin: str
    current_price: float
    lowest_price: float
    highest_price: float
    average_price: float
    price_change_percentage: float
    history: List[dict]

class SentimentAnalysisRequest(BaseModel):
    """Sentiment analysis request"""
    asin: str = Field(..., description="Product ASIN")
    max_reviews: int = Field(default=20, ge=1, le=100, description="Max reviews to analyze")

class ComparisonRequest(BaseModel):
    """Product comparison request"""
    asins: List[str] = Field(..., min_items=2, max_items=5, description="ASINs to compare")

# ==================== Endpoints ====================

@router.get("/price-history/{asin}", response_model=PriceHistoryResponse)
async def get_price_history(
    asin: str = Path(..., description="Product ASIN"),
    days: int = Query(30, ge=1, le=365, description="Number of days")
):
    """
    Get price history for product
    
    - **asin**: Product ASIN
    - **days**: Number of days to look back (1-365)
    """
    try:
        mongodb = await get_mongodb()
        
        # Get product
        product = await mongodb.get_product_by_asin(asin)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # Get price history
        history = await mongodb.get_price_history(asin, days)
        
        if not history:
            raise HTTPException(status_code=404, detail="No price history available")
        
        # Calculate statistics
        prices = [entry["price"] for entry in history]
        lowest_price = min(prices)
        highest_price = max(prices)
        average_price = sum(prices) / len(prices)
        
        # Calculate price change
        first_price = prices[0]
        current_price = prices[-1]
        price_change = ((current_price - first_price) / first_price * 100) if first_price > 0 else 0
        
        return PriceHistoryResponse(
            asin=asin,
            current_price=current_price,
            lowest_price=lowest_price,
            highest_price=highest_price,
            average_price=round(average_price, 2),
            price_change_percentage=round(price_change, 2),
            history=history
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting price history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sentiment")
async def analyze_sentiment(request: SentimentAnalysisRequest):
    """
    Analyze product review sentiment using AI
    
    - **asin**: Product ASIN
    - **max_reviews**: Maximum number of reviews to analyze
    """
    try:
        mongodb = await get_mongodb()
        
        # Get product
        product = await mongodb.get_product_by_asin(request.asin)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # For demo, we'll use mock reviews
        # In production, you'd scrape actual reviews
        reviews = [
            "Great product, works perfectly!",
            "Not worth the price, disappointed",
            "Amazing quality, highly recommend",
            # ... more reviews
        ]
        
        # Analyze with Gemini
        extractor = GeminiExtractor()
        sentiment_result = await extractor.analyze_reviews_sentiment(reviews[:request.max_reviews])
        
        # Update product with sentiment
        product.sentiment_score = sentiment_result.get("score", 0)
        await mongodb.save_product(product)
        
        return {
            "success": True,
            "asin": request.asin,
            "sentiment": sentiment_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing sentiment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/compare")
async def compare_products(request: ComparisonRequest):
    """
    Compare multiple products
    
    - **asins**: List of ASINs to compare (2-5 products)
    """
    try:
        mongodb = await get_mongodb()
        
        # Get all products
        products = []
        for asin in request.asins:
            product = await mongodb.get_product_by_asin(asin)
            if product:
                products.append(product)
        
        if len(products) < 2:
            raise HTTPException(
                status_code=400,
                detail="At least 2 valid products required for comparison"
            )
        
        # Build comparison
        comparison = {
            "products": [],
            "best_price": None,
            "best_rating": None,
            "most_reviews": None
        }
        
        best_price_product = None
        best_rating_product = None
        most_reviews_product = None
        
        for product in products:
            product_data = {
                "asin": product.asin,
                "title": product.title,
                "brand": product.brand,
                "price": product.current_price,
                "rating": product.reviews.average_rating if product.reviews else 0,
                "reviews_count": product.reviews.total_reviews if product.reviews else 0,
                "status": product.status
            }
            comparison["products"].append(product_data)
            
            # Track best
            if not best_price_product or product.current_price < best_price_product.current_price:
                best_price_product = product
            
            if product.reviews:
                if not best_rating_product or (
                    product.reviews.average_rating > (best_rating_product.reviews.average_rating if best_rating_product.reviews else 0)
                ):
                    best_rating_product = product
                
                if not most_reviews_product or (
                    product.reviews.total_reviews > (most_reviews_product.reviews.total_reviews if most_reviews_product.reviews else 0)
                ):
                    most_reviews_product = product
        
        # Set best products
        if best_price_product:
            comparison["best_price"] = {
                "asin": best_price_product.asin,
                "price": best_price_product.current_price
            }
        
        if best_rating_product:
            comparison["best_rating"] = {
                "asin": best_rating_product.asin,
                "rating": best_rating_product.reviews.average_rating
            }
        
        if most_reviews_product:
            comparison["most_reviews"] = {
                "asin": most_reviews_product.asin,
                "reviews": most_reviews_product.reviews.total_reviews
            }
        
        return {
            "success": True,
            "comparison": comparison
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing products: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics")
async def get_analytics(
    days: int = Query(7, ge=1, le=90, description="Days to analyze")
):
    """
    Get analytics summary
    
    - **days**: Number of days to analyze (1-90)
    """
    try:
        mongodb = await get_mongodb()
        
        # Get analytics summary
        summary = await mongodb.get_analytics_summary(days)
        
        # Get top brands
        top_brands = await mongodb.get_top_brands(limit=10)
        
        return {
            "success": True,
            "period_days": days,
            "summary": summary,
            "top_brands": top_brands
        }
        
    except Exception as e:
        logger.error(f"Error getting analytics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trending")
async def get_trending_products(
    limit: int = Query(10, ge=1, le=50, description="Number of products")
):
    """
    Get trending products (most scraped recently)
    
    - **limit**: Number of products to return
    """
    try:
        from pymongo import DESCENDING
        
        mongodb = await get_mongodb()
        
        # Get recently scraped products with high view counts
        products = await mongodb.get_products(
            limit=limit,
            sort_by="scrape_count",
            sort_order=DESCENDING
        )
        
        return {
            "success": True,
            "count": len(products),
            "products": [
                {
                    "asin": p.asin,
                    "title": p.title,
                    "brand": p.brand,
                    "price": p.current_price,
                    "rating": p.reviews.average_rating if p.reviews else 0,
                    "scrape_count": p.scrape_count
                }
                for p in products
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting trending products: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
