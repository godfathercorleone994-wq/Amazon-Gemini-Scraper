"""
Rate limiting middleware
"""
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict, Tuple
import time
import hashlib

from storage.redis_cache import redis_cache
from config.settings import settings
from utils.logger import logger

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using Redis
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.rate_limit = settings.api_rate_limit
        self.rate_limit_period = settings.api_rate_limit_period
        
        # Endpoints with custom limits
        self.custom_limits = {
            "/api/v1/scraping/scrape": (10, 60),  # 10 requests per minute
            "/api/v1/scraping/bulk": (5, 60),      # 5 bulk requests per minute
            "/api/v1/scraping/search": (20, 60),   # 20 searches per minute
            "/api/v1/analysis/sentiment": (10, 60), # 10 sentiment analyses per minute
        }
        
        # Exempted endpoints
        self.exempted = [
            "/",
            "/api/v1/health",
            "/api/v1/health/live",
            "/api/v1/health/ready",
            "/api/v1/docs",
            "/api/v1/redoc",
            "/api/v1/openapi.json"
        ]
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request with rate limiting
        """
        # Skip rate limiting for exempted endpoints
        if request.url.path in self.exempted:
            return await call_next(request)
        
        # Skip if Redis is not available
        if not redis_cache._initialized:
            logger.warning("Redis not initialized, skipping rate limiting")
            return await call_next(request)
        
        try:
            # Get client identifier
            client_id = self.get_client_id(request)
            
            # Get rate limit for endpoint
            limit, period = self.get_endpoint_limit(request.url.path)
            
            # Check rate limit
            is_allowed = await redis_cache.track_rate_limit(
                identifier=client_id,
                limit=limit,
                period=period
            )
            
            if not is_allowed:
                # Get current status
                status_info = await redis_cache.get_rate_limit_status(client_id)
                
                logger.warning(
                    f"Rate limit exceeded for {client_id}",
                    path=request.url.path,
                    current=status_info["current"],
                    limit=limit
                )
                
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": "Rate limit exceeded",
                        "message": f"Too many requests. Please try again in {status_info['remaining_time']} seconds",
                        "limit": limit,
                        "period": period,
                        "retry_after": status_info["remaining_time"]
                    },
                    headers={
                        "X-RateLimit-Limit": str(limit),
                        "X-RateLimit-Remaining": str(max(0, limit - status_info["current"])),
                        "X-RateLimit-Reset": str(int(time.time()) + status_info["remaining_time"]),
                        "Retry-After": str(status_info["remaining_time"])
                    }
                )
            
            # Process request
            response = await call_next(request)
            
            # Add rate limit headers
            status_info = await redis_cache.get_rate_limit_status(client_id)
            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Remaining"] = str(max(0, limit - status_info["current"]))
            response.headers["X-RateLimit-Reset"] = str(int(time.time()) + status_info["remaining_time"])
            
            return response
            
        except Exception as e:
            logger.error(f"Rate limiting error: {str(e)}")
            # Continue without rate limiting on error
            return await call_next(request)
    
    def get_client_id(self, request: Request) -> str:
        """
        Get unique client identifier
        
        Uses API key if present, otherwise IP address
        """
        # Check for API key in headers
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"api_key:{hashlib.md5(api_key.encode()).hexdigest()}"
        
        # Use IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"
        
        # Include path to have per-endpoint limits
        path_hash = hashlib.md5(request.url.path.encode()).hexdigest()[:8]
        
        return f"ip:{ip}:{path_hash}"
    
    def get_endpoint_limit(self, path: str) -> Tuple[int, int]:
        """
        Get rate limit for specific endpoint
        
        Returns (limit, period_seconds)
        """
        # Check for custom limit
        for endpoint, limits in self.custom_limits.items():
            if path.startswith(endpoint):
                return limits
        
        # Return default limit
        return (self.rate_limit, self.rate_limit_period)

class IPRateLimiter:
    """
    Simple in-memory rate limiter (backup when Redis is unavailable)
    """
    
    def __init__(self):
        self.requests = {}
        self.cleanup_interval = 60  # Clean old entries every minute
        self.last_cleanup = time.time()
    
    def is_allowed(self, client_id: str, limit: int, period: int) -> bool:
        """
        Check if request is allowed
        """
        now = time.time()
        
        # Cleanup old entries periodically
        if now - self.last_cleanup > self.cleanup_interval:
            self.cleanup(now)
        
        # Get client's request history
        if client_id not in self.requests:
            self.requests[client_id] = []
        
        # Remove old requests outside the period
        self.requests[client_id] = [
            timestamp for timestamp in self.requests[client_id]
            if now - timestamp < period
        ]
        
        # Check if under limit
        if len(self.requests[client_id]) < limit:
            self.requests[client_id].append(now)
            return True
        
        return False
    
    def cleanup(self, now: float):
        """
        Clean up old entries
        """
        max_period = 3600  # Keep entries for max 1 hour
        
        for client_id in list(self.requests.keys()):
            self.requests[client_id] = [
                timestamp for timestamp in self.requests[client_id]
                if now - timestamp < max_period
            ]
            
            # Remove client if no recent requests
            if not self.requests[client_id]:
                del self.requests[client_id]
        
        self.last_cleanup = now

# Global in-memory rate limiter (backup)
memory_rate_limiter = IPRateLimiter()
