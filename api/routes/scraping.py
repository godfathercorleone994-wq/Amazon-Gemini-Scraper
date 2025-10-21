"""
Scraping API routes
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Path
from typing import List, Optional
from pydantic import BaseModel, HttpUrl, Field
from datetime import datetime

from core.scraper_agent import ScraperAgent, ScraperPool
from core.gemini_extractor import GeminiExtractor
from core.correction_flow import CorrectionFlow
from core.fallback_extractors import FallbackManager
from storage.mongodb_client import get_mongodb
from storage.redis_cache import get_redis
from utils.logger import logger
from utils.validators import validate_amazon_url, validate_asin
from models.product import Product
from models.extraction_result import ExtractionResult, ExtractionStatus

router = APIRouter()

# ==================== Request/Response Models ====================

class ScrapeRequest(BaseModel):
    """Request model for scraping"""
    url: HttpUrl = Field(..., description="Amazon product URL")
    force_refresh: bool = Field(default=False, description="Force refresh cached data")
    use_ai: bool = Field(default=True, description="Use AI for extraction")
    ai_provider: Optional[str] = Field(default="gemini", description="AI provider (gemini/openai)")
    
    class Config:
        schema_extra = {
            "example": {
                "url": "https://www.amazon.com/dp/B08N5WRWNW",
                "force_refresh": False,
                "use_ai": True,
                "ai_provider": "gemini"
            }
        }

class BulkScrapeRequest(BaseModel):
    """Request model for bulk scraping"""
    urls: List[HttpUrl] = Field(..., max_items=100, description="List of Amazon URLs (max 100)")
    parallel: bool = Field(default=True, description="Scrape in parallel")
    
    class Config:
        schema_extra = {
            "example": {
                "urls": [
                    "https://www.amazon.com/dp/B08N5WRWNW",
                    "https://www.amazon.com/dp/B09G9FPHY6"
                ],
                "parallel": True
            }
        }

class SearchRequest(BaseModel):
    """Request model for search scraping"""
    query: str = Field(..., min_length=1, max_length=200, description="Search query")
    max_pages: int = Field(default=1, ge=1, le=10, description="Maximum pages to scrape")
    
    class Config:
        schema_extra = {
            "example": {
                "query": "wireless headphones",
                "max_pages": 2
            }
        }

class ScrapeResponse(BaseModel):
    """Response model for scraping"""
    success: bool
    message: str
    task_id: str
    product: Optional[Product] = None
    extraction_result: Optional[ExtractionResult] = None

class BulkScrapeResponse(BaseModel):
    """Response model for bulk scraping"""
    success: bool
    message: str
    total: int
    successful: int
    failed: int
    results: List[ScrapeResponse]

# ==================== Background Tasks ====================

async def scrape_and_save(url: str, task_id: str, use_ai: bool, ai_provider: str):
    """Background task for scraping and saving"""
    try:
        mongodb = await get_mongodb()
        redis = await get_redis()
        
        # Scrape product
        async with ScraperAgent() as scraper:
            extraction_result = await scraper.scrape_product(url)
        
        # Extract with AI if enabled
        if use_ai and extraction_result.status == ExtractionStatus.SUCCESS:
            if ai_provider == "gemini":
                extractor = GeminiExtractor()
            else:
                # Use fallback manager for other providers
                fallback = FallbackManager()
                product = await fallback.extract_with_fallback(
                    extraction_result.raw_html,
                    extraction_result
                )
            
            if ai_provider == "gemini":
                product = await extractor.extract_product_data(
                    extraction_result.raw_html,
                    extraction_result
                )
            
            # Validate and correct
            correction = CorrectionFlow()
            product, errors = await correction.validate_and_correct(product, extraction_result)
            
            # Save product
            await mongodb.save_product(product)
            
            # Cache product
            await redis.cache_product(product.asin, product.dict())
        
        # Save extraction result
        await mongodb.save_extraction_result(extraction_result)
        
        # Cache extraction result
        await redis.cache_extraction_result(task_id, extraction_result.dict())
        
        logger.info(f"Scraping task completed: {task_id}")
        
    except Exception as e:
        logger.error(f"Scraping task failed: {str(e)}")

# ==================== Endpoints ====================

@router.post("/scrape", response_model=ScrapeResponse)
async def scrape_product(
    request: ScrapeRequest,
    background_tasks: BackgroundTasks
):
    """
    Scrape a single Amazon product
    
    - **url**: Amazon product URL
    - **force_refresh**: Force refresh cached data
    - **use_ai**: Use AI for extraction
    - **ai_provider**: AI provider (gemini/openai)
    """
    try:
        # Validate URL
        is_valid, asin = validate_amazon_url(str(request.url))
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail="Invalid Amazon URL"
            )
        
        # Check cache if not forcing refresh
        if not request.force_refresh:
            redis = await get_redis()
            cached_product = await redis.get_cached_product(asin)
            
            if cached_product:
                logger.info(f"Returning cached product: {asin}")
                return ScrapeResponse(
                    success=True,
                    message="Product retrieved from cache",
                    task_id=f"cached_{asin}",
                    product=Product(**cached_product)
                )
        
        # Check if AI provider is available
        from config.settings import settings
        if request.use_ai and not settings.has_ai_provider(request.ai_provider):
            raise HTTPException(
                status_code=400,
                detail=f"AI provider '{request.ai_provider}' not configured"
            )
        
        # Create scraping task
        mongodb = await get_mongodb()
        
        async with ScraperAgent() as scraper:
            extraction_result = await scraper.scrape_product(str(request.url))
        
        if extraction_result.status == ExtractionStatus.FAILED:
            raise HTTPException(
                status_code=500,
                detail="Scraping failed: " + str(extraction_result.errors)
            )
        
        product = None
        
        # Extract with AI if enabled
        if request.use_ai:
            if request.ai_provider == "gemini":
                extractor = GeminiExtractor()
                product = await extractor.extract_product_data(
                    extraction_result.raw_html,
                    extraction_result
                )
            else:
                fallback = FallbackManager()
                product = await fallback.extract_with_fallback(
                    extraction_result.raw_html,
                    extraction_result
                )
            
            # Validate and correct
            correction = CorrectionFlow()
            product, errors = await correction.validate_and_correct(product, extraction_result)
            
            if errors:
                logger.warning(f"Product has validation errors: {errors}")
            
            # Save product
            await mongodb.save_product(product)
            
            # Cache product
            redis = await get_redis()
            await redis.cache_product(product.asin, product.dict())
        
        # Save extraction result
        await mongodb.save_extraction_result(extraction_result)
        
        return ScrapeResponse(
            success=True,
            message="Product scraped successfully",
            task_id=extraction_result.task_id,
            product=product,
            extraction_result=extraction_result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Scraping error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Scraping failed: {str(e)}"
        )

@router.post("/scrape/bulk", response_model=BulkScrapeResponse)
async def scrape_bulk(request: BulkScrapeRequest):
    """
    Scrape multiple Amazon products
    
    - **urls**: List of Amazon product URLs (max 100)
    - **parallel**: Scrape in parallel for better performance
    """
    try:
        results = []
        successful = 0
        failed = 0
        
        if request.parallel:
            # Use scraper pool for parallel scraping
            pool = ScraperPool()
            extraction_results = await pool.scrape_products([str(url) for url in request.urls])
            
            mongodb = await get_mongodb()
            redis = await get_redis()
            
            for extraction_result in extraction_results:
                try:
                    # Extract with AI
                    extractor = GeminiExtractor()
                    product = await extractor.extract_product_data(
                        extraction_result.raw_html,
                        extraction_result
                    )
                    
                    # Validate and correct
                    correction = CorrectionFlow()
                    product, errors = await correction.validate_and_correct(product, extraction_result)
                    
                    # Save
                    await mongodb.save_product(product)
                    await mongodb.save_extraction_result(extraction_result)
                    await redis.cache_product(product.asin, product.dict())
                    
                    results.append(ScrapeResponse(
                        success=True,
                        message="Success",
                        task_id=extraction_result.task_id,
                        product=product,
                        extraction_result=extraction_result
                    ))
                    successful += 1
                    
                except Exception as e:
                    logger.error(f"Failed to process result: {str(e)}")
                    results.append(ScrapeResponse(
                        success=False,
                        message=str(e),
                        task_id=extraction_result.task_id
                    ))
                    failed += 1
            
            await pool.close()
        else:
            # Sequential scraping
            for url in request.urls:
                try:
                    async with ScraperAgent() as scraper:
                        extraction_result = await scraper.scrape_product(str(url))
                    
                    # Process similar to single scrape
                    # ... (similar logic as above)
                    successful += 1
                except Exception as e:
                    logger.error(f"Failed to scrape {url}: {str(e)}")
                    failed += 1
        
        return BulkScrapeResponse(
            success=True,
            message=f"Scraped {successful}/{len(request.urls)} products",
            total=len(request.urls),
            successful=successful,
            failed=failed,
            results=results
        )
        
    except Exception as e:
        logger.error(f"Bulk scraping error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Bulk scraping failed: {str(e)}"
        )

@router.post("/search", response_model=dict)
async def scrape_search(request: SearchRequest):
    """
    Scrape Amazon search results
    
    - **query**: Search query
    - **max_pages**: Maximum pages to scrape (1-10)
    """
    try:
        # Check cache first
        redis = await get_redis()
        cached_results = await redis.get_cached_search(request.query)
        
        if cached_results:
            logger.info(f"Returning cached search results for: {request.query}")
            return {
                "success": True,
                "query": request.query,
                "total": len(cached_results),
                "results": cached_results,
                "cached": True
            }
        
        # Scrape search results
        async with ScraperAgent() as scraper:
            results = await scraper.scrape_search_results(request.query, request.max_pages)
        
        # Cache results
        await redis.cache_search_results(request.query, results)
        
        return {
            "success": True,
            "query": request.query,
            "total": len(results),
            "results": results,
            "cached": False
        }
        
    except Exception as e:
        logger.error(f"Search scraping error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Search scraping failed: {str(e)}"
        )

@router.get("/product/{asin}", response_model=Product)
async def get_product(
    asin: str = Path(..., description="Amazon ASIN", pattern="^[A-Z0-9]{10}$")
):
    """
    Get product by ASIN
    
    - **asin**: Amazon Standard Identification Number (10 characters)
    """
    try:
        # Check cache first
        redis = await get_redis()
        cached_product = await redis.get_cached_product(asin)
        
        if cached_product:
            return Product(**cached_product)
        
        # Get from database
        mongodb = await get_mongodb()
        product = await mongodb.get_product_by_asin(asin)
        
        if not product:
            raise HTTPException(
                status_code=404,
                detail=f"Product not found: {asin}"
            )
        
        # Cache for next time
        await redis.cache_product(asin, product.dict())
        
        return product
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting product: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get product: {str(e)}"
        )

@router.get("/products", response_model=dict)
async def list_products(
    skip: int = Query(0, ge=0, description="Number of products to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of products to return"),
    status: Optional[str] = Query(None, description="Filter by status"),
    brand: Optional[str] = Query(None, description="Filter by brand"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price"),
    sort_by: str = Query("scraped_at", description="Field to sort by"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order")
):
    """
    List products with filters and pagination
    
    - **skip**: Number of products to skip (pagination)
    - **limit**: Number of products to return (max 100)
    - **status**: Filter by availability status
    - **brand**: Filter by brand name
    - **min_price**: Minimum price filter
    - **max_price**: Maximum price filter
    - **sort_by**: Field to sort by
    - **sort_order**: Sort order (asc/desc)
    """
    try:
        from pymongo import ASCENDING, DESCENDING
        
        # Build filters
        filters = {}
        
        if status:
            filters["status"] = status
        
        if brand:
            filters["brand"] = brand
        
        if min_price is not None or max_price is not None:
            filters["current_price"] = {}
            if min_price is not None:
                filters["current_price"]["$gte"] = min_price
            if max_price is not None:
                filters["current_price"]["$lte"] = max_price
        
        # Get products
        mongodb = await get_mongodb()
        products = await mongodb.get_products(
            skip=skip,
            limit=limit,
            filters=filters,
            sort_by=sort_by,
            sort_order=DESCENDING if sort_order == "desc" else ASCENDING
        )
        
        # Get total count
        total = await mongodb.products.count_documents(filters)
        
        return {
            "success": True,
            "total": total,
            "skip": skip,
            "limit": limit,
            "count": len(products),
            "products": [p.dict() for p in products]
        }
        
    except Exception as e:
        logger.error(f"Error listing products: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list products: {str(e)}"
        )

@router.delete("/product/{asin}")
async def delete_product(
    asin: str = Path(..., description="Amazon ASIN", pattern="^[A-Z0-9]{10}$")
):
    """
    Delete product by ASIN
    
    - **asin**: Amazon Standard Identification Number
    """
    try:
        mongodb = await get_mongodb()
        redis = await get_redis()
        
        # Delete from database
        deleted = await mongodb.delete_product(asin)
        
        if not deleted:
            raise HTTPException(
                status_code=404,
                detail=f"Product not found: {asin}"
            )
        
        # Clear cache
        await redis.delete(f"product:{asin}")
        
        return {
            "success": True,
            "message": f"Product deleted: {asin}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting product: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete product: {str(e)}"
        )

@router.get("/extraction/{task_id}", response_model=ExtractionResult)
async def get_extraction_result(
    task_id: str = Path(..., description="Extraction task ID")
):
    """
    Get extraction result by task ID
    
    - **task_id**: Unique task identifier
    """
    try:
        # Check cache first
        redis = await get_redis()
        cached_result = await redis.get_cached_extraction(task_id)
        
        if cached_result:
            return ExtractionResult(**cached_result)
        
        # Get from database
        mongodb = await get_mongodb()
        result = await mongodb.get_extraction_result(task_id)
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Extraction result not found: {task_id}"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting extraction result: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get extraction result: {str(e)}"
  )
