"""
FastAPI main application
"""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import time

from config.settings import settings
from utils.logger import logger
from storage.mongodb_client import mongodb_client
from storage.redis_cache import redis_cache
from api.routes import scraping, analysis, health, notifications
from api.middleware.rate_limit import RateLimitMiddleware

# Prometheus metrics
if settings.prometheus_enabled:
    from prometheus_fastapi_instrumentator import Instrumentator

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for startup and shutdown"""
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    
    # Connect to databases
    try:
        await mongodb_client.connect()
        await redis_cache.connect()
        logger.info("Database connections established")
    except Exception as e:
        logger.error(f"Failed to connect to databases: {str(e)}")
        raise
    
    # Initialize Prometheus metrics
    if settings.prometheus_enabled:
        instrumentator = Instrumentator()
        instrumentator.instrument(app).expose(app)
        logger.info("Prometheus metrics enabled")
    
    logger.info(f"{settings.app_name} started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    
    # Close database connections
    await mongodb_client.disconnect()
    await redis_cache.disconnect()
    
    logger.info("Application shutdown complete")

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Advanced Amazon Product Scraper with AI-powered extraction",
    docs_url=f"{settings.api_prefix}/docs",
    redoc_url=f"{settings.api_prefix}/redoc",
    openapi_url=f"{settings.api_prefix}/openapi.json",
    lifespan=lifespan
)

# ==================== Middleware ====================

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_credentials,
    allow_methods=settings.cors_methods,
    allow_headers=settings.cors_headers,
)

# Gzip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Rate limiting
app.add_middleware(RateLimitMiddleware)

# Request timing
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time to response headers"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests"""
    logger.info(
        f"Request: {request.method} {request.url.path}",
        client_ip=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    
    response = await call_next(request)
    
    logger.info(
        f"Response: {response.status_code}",
        path=request.url.path,
        status_code=response.status_code
    )
    
    return response

# ==================== Exception Handlers ====================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(x) for x in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    logger.warning(f"Validation error: {errors}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": "Validation Error",
            "details": errors
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=exc)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "Internal Server Error",
            "message": str(exc) if settings.debug else "An error occurred"
        }
    )

# ==================== Routes ====================

# Include routers
app.include_router(
    health.router,
    prefix=f"{settings.api_prefix}/health",
    tags=["Health"]
)

app.include_router(
    scraping.router,
    prefix=f"{settings.api_prefix}/scraping",
    tags=["Scraping"]
)

app.include_router(
    analysis.router,
    prefix=f"{settings.api_prefix}/analysis",
    tags=["Analysis"]
)

app.include_router(
    notifications.router,
    prefix=f"{settings.api_prefix}/notifications",
    tags=["Notifications"]
)

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": f"{settings.api_prefix}/docs"
    }

# API info endpoint
@app.get(f"{settings.api_prefix}/info")
async def api_info():
    """Get API information"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "features": {
            "ml_enabled": settings.enable_ml_features,
            "notifications_enabled": settings.enable_notifications,
            "dashboard_enabled": settings.enable_dashboard,
            "webhooks_enabled": settings.enable_webhooks
        },
        "ai_providers": {
            "gemini": settings.has_ai_provider("gemini"),
            "openai": settings.has_ai_provider("openai"),
            "huggingface": settings.has_ai_provider("huggingface")
        }
    }

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        workers=settings.workers if not settings.reload else 1,
        log_level=settings.log_level.lower()
)
