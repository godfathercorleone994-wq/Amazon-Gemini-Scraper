"""
Health check endpoints
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from datetime import datetime
import psutil
import platform

from storage.mongodb_client import mongodb_client
from storage.redis_cache import redis_cache
from config.settings import settings
from utils.logger import logger

router = APIRouter()

@router.get("/")
async def health_check() -> Dict[str, Any]:
    """
    Basic health check
    
    Returns the current status of the API
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment
    }

@router.get("/live")
async def liveness_probe() -> Dict[str, str]:
    """
    Kubernetes liveness probe
    
    Returns 200 if the service is alive
    """
    return {"status": "alive"}

@router.get("/ready")
async def readiness_probe() -> Dict[str, Any]:
    """
    Kubernetes readiness probe
    
    Checks if all dependencies are ready
    """
    try:
        ready = True
        checks = {}
        
        # Check MongoDB
        try:
            if mongodb_client._initialized:
                await mongodb_client.db.command("ping")
                checks["mongodb"] = "ready"
            else:
                checks["mongodb"] = "not_initialized"
                ready = False
        except Exception as e:
            checks["mongodb"] = f"error: {str(e)}"
            ready = False
        
        # Check Redis
        try:
            if redis_cache._initialized:
                await redis_cache.redis.ping()
                checks["redis"] = "ready"
            else:
                checks["redis"] = "not_initialized"
                ready = False
        except Exception as e:
            checks["redis"] = f"error: {str(e)}"
            ready = False
        
        if not ready:
            raise HTTPException(status_code=503, detail=checks)
        
        return {
            "status": "ready",
            "checks": checks
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}")
        raise HTTPException(status_code=503, detail={"error": str(e)})

@router.get("/detailed")
async def detailed_health() -> Dict[str, Any]:
    """
    Detailed health check with system metrics
    
    Returns comprehensive system and service information
    """
    try:
        # System info
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        
        # Process info
        process = psutil.Process()
        process_memory = process.memory_info()
        
        # Database status
        db_status = {}
        try:
            if mongodb_client._initialized:
                await mongodb_client.db.command("ping")
                
                # Get database stats
                stats = await mongodb_client.db.command("serverStatus")
                db_status["mongodb"] = {
                    "status": "connected",
                    "version": stats.get("version", "unknown"),
                    "uptime": stats.get("uptime", 0),
                    "connections": {
                        "current": stats.get("connections", {}).get("current", 0),
                        "available": stats.get("connections", {}).get("available", 0)
                    }
                }
                
                # Get collection counts
                collections = ["products", "extraction_results", "notifications"]
                for collection in collections:
                    count = await mongodb_client.db[collection].count_documents({})
                    db_status["mongodb"][f"{collection}_count"] = count
            else:
                db_status["mongodb"] = {"status": "disconnected"}
        except Exception as e:
            db_status["mongodb"] = {"status": "error", "error": str(e)}
        
        # Cache status
        cache_status = {}
        try:
            if redis_cache._initialized:
                await redis_cache.redis.ping()
                stats = await redis_cache.get_stats()
                cache_status["redis"] = {
                    "status": "connected",
                    **stats
                }
            else:
                cache_status["redis"] = {"status": "disconnected"}
        except Exception as e:
            cache_status["redis"] = {"status": "error", "error": str(e)}
        
        # AI providers status
        ai_status = {
            "gemini": "configured" if settings.gemini_api_key else "not_configured",
            "openai": "configured" if settings.openai_api_key else "not_configured",
            "huggingface": "configured" if settings.huggingface_api_key else "not_configured"
        }
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": {
                "name": settings.app_name,
                "version": settings.app_version,
                "environment": settings.environment,
                "debug": settings.debug,
                "uptime_seconds": (datetime.utcnow() - datetime.fromtimestamp(process.create_time())).total_seconds()
            },
            "system": {
                "platform": platform.platform(),
                "python_version": platform.python_version(),
                "cpu": {
                    "count": psutil.cpu_count(),
                    "percent": cpu_percent
                },
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                    "used": memory.used
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": disk.percent
                }
            },
            "process": {
                "pid": process.pid,
                "memory": {
                    "rss": process_memory.rss,
                    "vms": process_memory.vms
                },
                "threads": process.num_threads(),
                "connections": len(process.connections())
            },
            "databases": db_status,
            "cache": cache_status,
            "ai_providers": ai_status,
            "features": {
                "ml_enabled": settings.enable_ml_features,
                "notifications_enabled": settings.enable_notifications,
                "dashboard_enabled": settings.enable_dashboard,
                "webhooks_enabled": settings.enable_webhooks
            }
        }
        
    except Exception as e:
        logger.error(f"Detailed health check failed: {str(e)}")
        return {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }

@router.get("/metrics")
async def get_metrics() -> Dict[str, Any]:
    """
    Get application metrics
    
    Returns key performance metrics
    """
    try:
        mongodb = mongodb_client
        redis = redis_cache
        
        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "requests": {},
            "scraping": {},
            "database": {},
            "cache": {}
        }
        
        # Get request metrics from Redis if available
        if redis._initialized:
            try:
                # Get rate limit counters
                rate_limit_keys = await redis.redis.keys("ratelimit:*")
                metrics["requests"]["active_rate_limits"] = len(rate_limit_keys)
                
                # Get cached items
                product_keys = await redis.redis.keys("product:*")
                search_keys = await redis.redis.keys("search:*")
                extraction_keys = await redis.redis.keys("extraction:*")
                
                metrics["cache"]["cached_products"] = len(product_keys)
                metrics["cache"]["cached_searches"] = len(search_keys)
                metrics["cache"]["cached_extractions"] = len(extraction_keys)
            except Exception as e:
                logger.error(f"Error getting cache metrics: {str(e)}")
        
        # Get database metrics
        if mongodb._initialized:
            try:
                # Get recent scraping stats
                from datetime import timedelta
                last_hour = datetime.utcnow() - timedelta(hours=1)
                last_day = datetime.utcnow() - timedelta(days=1)
                
                recent_extractions_hour = await mongodb.extraction_results.count_documents({
                    "started_at": {"$gte": last_hour}
                })
                
                recent_extractions_day = await mongodb.extraction_results.count_documents({
                    "started_at": {"$gte": last_day}
                })
                
                successful_extractions_day = await mongodb.extraction_results.count_documents({
                    "started_at": {"$gte": last_day},
                    "status": "success"
                })
                
                metrics["scraping"]["last_hour"] = recent_extractions_hour
                metrics["scraping"]["last_day"] = recent_extractions_day
                metrics["scraping"]["success_rate_day"] = (
                    (successful_extractions_day / recent_extractions_day * 100) 
                    if recent_extractions_day > 0 else 0
                )
                
                # Get database sizes
                db_stats = await mongodb.db.command("dbStats")
                metrics["database"]["size_bytes"] = db_stats.get("dataSize", 0)
                metrics["database"]["collections"] = db_stats.get("collections", 0)
                metrics["database"]["indexes"] = db_stats.get("indexes", 0)
                
            except Exception as e:
                logger.error(f"Error getting database metrics: {str(e)}")
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error getting metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
