"""
Rate limiting middleware with Redis and fallback support
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict, Tuple, Optional
import time
import hashlib
from collections import defaultdict
from enum import Enum

from storage.redis_cache import redis_cache
from config.settings import settings
from utils.logger import logger


class RateLimitStrategy(str, Enum):
    """Rate limiting strategies"""
    PER_IP = "per_ip"
    PER_API_KEY = "per_api_key"
    PER_USER = "per_user"
    COMBINED = "combined"


class EndpointRateLimit:
    """Endpoint rate limit configuration"""
    
    def __init__(
        self,
        limit: int,
        period: int,
        strategy: RateLimitStrategy = RateLimitStrategy.COMBINED
    ):
        self.limit = limit
        self.period = period
        self.strategy = strategy


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Advanced rate limiting middleware with Redis and fallback support
    """
    
    # Endpoint-specific rate limits
    ENDPOINT_LIMITS = {
        "/api/v1/scraping/scrape": EndpointRateLimit(10, 60),
        "/api/v1/scraping/bulk": EndpointRateLimit(5, 60),
        "/api/v1/scraping/search": EndpointRateLimit(20, 60),
        "/api/v1/analysis/sentiment": EndpointRateLimit(10, 60),
    }
    
    # Exempted endpoints (no rate limiting)
    EXEMPTED_ENDPOINTS = {
        "/",
        "/api/v1/health",
        "/api/v1/health/live",
        "/api/v1/health/ready",
        "/api/v1/docs",
        "/api/v1/redoc",
        "/api/v1/openapi.json",
        "/api/v1/auth/login",
        "/api/v1/auth/register",
    }
    
    # Authentication endpoints with relaxed limits
    AUTH_ENDPOINTS = {
        "/api/v1/auth/login": EndpointRateLimit(5, 300),  # 5 attempts per 5 min
        "/api/v1/auth/register": EndpointRateLimit(3, 3600),  # 3 per hour
        "/api/v1/auth/forgot-password": EndpointRateLimit(3, 3600),  # 3 per hour
    }
    
    def __init__(self, app, default_limit: int = None, default_period: int = None):
        """
        Initialize rate limiting middleware
        
        Args:
            app: FastAPI application
            default_limit: Default request limit
            default_period: Default period in seconds
        """
        super().__init__(app)
        self.default_limit = default_limit or settings.api_rate_limit
        self.default_period = default_period or settings.api_rate_limit_period
        
        # In-memory fallback
        self.memory_limiter = InMemoryRateLimiter()
        self.use_fallback = False
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request with rate limiting
        
        Args:
            request: HTTP request
            call_next: Next middleware/handler
            
        Returns:
            Response with rate limit headers
        """
        # Skip rate limiting for exempted endpoints
        if self._is_exempted(request.url.path):
            return await call_next(request)
        
        try:
            # Get client identifier and rate limit config
            client_id = self._get_client_id(request)
            limit, period = self._get_endpoint_limit(request.url.path)
            
            # Check rate limit
            is_allowed = await self._check_rate_limit(
                client_id=client_id,
                limit=limit,
                period=period
            )
            
            if not is_allowed:
                return await self._handle_rate_limit_exceeded(
                    client_id=client_id,
                    limit=limit,
                    period=period,
                    path=request.url.path
                )
            
            # Process request
            response = await call_next(request)
            
            # Add rate limit headers to response
            await self._add_rate_limit_headers(response, client_id, limit, period)
            
            return response
            
        except Exception as e:
            logger.error(f"Rate limiting error: {str(e)}", exc_info=True)
            # Continue without rate limiting on error
            return await call_next(request)
    
    def _is_exempted(self, path: str) -> bool:
        """
        Check if endpoint is exempted from rate limiting
        
        Args:
            path: Request path
            
        Returns:
            True if exempted, False otherwise
        """
        # Exact match
        if path in self.EXEMPTED_ENDPOINTS:
            return True
        
        # Check auth endpoints separately
        if path in self.AUTH_ENDPOINTS:
            return False
        
        return False
    
    def _get_client_id(self, request: Request) -> str:
        """
        Get unique client identifier
        
        Prioritizes: API Key > User ID > IP Address
        
        Args:
            request: HTTP request
            
        Returns:
            Unique client identifier
        """
        # 1. Check for API key (highest priority)
        api_key = request.headers.get("X-API-Key")
        if api_key:
            api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
            return f"key:{api_key_hash}"
        
        # 2. Check for user ID in request state (set by auth middleware)
        if hasattr(request.state, "user_id") and request.state.user_id:
            return f"user:{request.state.user_id}"
        
        # 3. Use IP address (fallback)
        client_ip = self._get_client_ip(request)
        return f"ip:{client_ip}"
    
    def _get_client_ip(self, request: Request) -> str:
        """
        Extract client IP address from request
        
        Args:
            request: HTTP request
            
        Returns:
            Client IP address
        """
        # Check X-Forwarded-For header (proxy)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        
        # Use client connection info
        if request.client:
            return request.client.host
        
        return "unknown"
    
    def _get_endpoint_limit(self, path: str) -> Tuple[int, int]:
        """
        Get rate limit configuration for endpoint
        
        Args:
            path: Request path
            
        Returns:
            Tuple of (limit, period_seconds)
        """
        # Check exact endpoint match first
        if path in self.AUTH_ENDPOINTS:
            config = self.AUTH_ENDPOINTS[path]
            return (config.limit, config.period)
        
        # Check custom limits with prefix matching
        for endpoint_pattern, config in self.ENDPOINT_LIMITS.items():
            if path.startswith(endpoint_pattern):
                return (config.limit, config.period)
        
        # Return default limit
        return (self.default_limit, self.default_period)
    
    async def _check_rate_limit(
        self,
        client_id: str,
        limit: int,
        period: int
    ) -> bool:
        """
        Check if request is within rate limit
        
        Args:
            client_id: Client identifier
            limit: Request limit
            period: Time period in seconds
            
        Returns:
            True if request allowed, False otherwise
        """
        # Try Redis first
        if redis_cache._initialized:
            try:
                return await redis_cache.track_rate_limit(
                    identifier=client_id,
                    limit=limit,
                    period=period
                )
            except Exception as e:
                logger.warning(f"Redis rate limit check failed: {str(e)}, using fallback")
                self.use_fallback = True
        
        # Fall back to in-memory limiter
        return self.memory_limiter.is_allowed(client_id, limit, period)
    
    async def _handle_rate_limit_exceeded(
        self,
        client_id: str,
        limit: int,
        period: int,
        path: str
    ) -> JSONResponse:
        """
        Handle rate limit exceeded response
        
        Args:
            client_id: Client identifier
            limit: Request limit
            period: Time period
            path: Request path
            
        Returns:
            JSON error response
        """
        logger.warning(
            f"Rate limit exceeded",
            client_id=client_id,
            path=path,
            limit=limit
        )
        
        # Get remaining time
        remaining_time = await self._get_remaining_time(client_id, period)
        
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "rate_limit_exceeded",
                "message": f"Too many requests. Please try again in {remaining_time} seconds",
                "limit": limit,
                "period": period,
                "retry_after": remaining_time
            },
            headers={
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(time.time()) + remaining_time),
                "Retry-After": str(remaining_time)
            }
        )
    
    async def _get_remaining_time(self, client_id: str, period: int) -> int:
        """
        Get remaining time until rate limit reset
        
        Args:
            client_id: Client identifier
            period: Time period in seconds
            
        Returns:
            Remaining time in seconds
        """
        if redis_cache._initialized:
            try:
                status_info = await redis_cache.get_rate_limit_status(client_id)
                return status_info.get("remaining_time", period)
            except Exception:
                pass
        
        return period
    
    async def _add_rate_limit_headers(
        self,
        response,
        client_id: str,
        limit: int,
        period: int
    ) -> None:
        """
        Add rate limit headers to response
        
        Args:
            response: HTTP response
            client_id: Client identifier
            limit: Request limit
            period: Time period
        """
        try:
            if redis_cache._initialized:
                status_info = await redis_cache.get_rate_limit_status(client_id)
                current = status_info.get("current", 0)
                remaining_time = status_info.get("remaining_time", period)
            else:
                current = self.memory_limiter.get_request_count(client_id, period)
                remaining_time = period
            
            remaining = max(0, limit - current)
            reset_time = int(time.time()) + remaining_time
            
            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(reset_time)
            
        except Exception as e:
            logger.error(f"Error adding rate limit headers: {str(e)}")


class InMemoryRateLimiter:
    """
    In-memory rate limiter (fallback when Redis unavailable)
    
    Uses a sliding window approach with automatic cleanup
    """
    
    def __init__(self, cleanup_interval: int = 300):
        """
        Initialize in-memory rate limiter
        
        Args:
            cleanup_interval: Cleanup interval in seconds
        """
        self.requests: Dict[str, list] = defaultdict(list)
        self.cleanup_interval = cleanup_interval
        self.last_cleanup = time.time()
    
    def is_allowed(self, client_id: str, limit: int, period: int) -> bool:
        """
        Check if request is allowed using sliding window
        
        Args:
            client_id: Client identifier
            limit: Request limit
            period: Time period in seconds
            
        Returns:
            True if request allowed, False otherwise
        """
        now = time.time()
        
        # Periodic cleanup
        if now - self.last_cleanup > self.cleanup_interval:
            self._cleanup(now)
        
        # Remove requests outside the period
        cutoff_time = now - period
        self.requests[client_id] = [
            timestamp for timestamp in self.requests[client_id]
            if timestamp > cutoff_time
        ]
        
        # Check if under limit
        if len(self.requests[client_id]) < limit:
            self.requests[client_id].append(now)
            return True
        
        return False
    
    def get_request_count(self, client_id: str, period: int) -> int:
        """
        Get current request count for client
        
        Args:
            client_id: Client identifier
            period: Time period in seconds
            
        Returns:
            Number of requests in current period
        """
        now = time.time()
        cutoff_time = now - period
        
        return len([
            t for t in self.requests.get(client_id, [])
            if t > cutoff_time
        ])
    
    def _cleanup(self, now: float) -> None:
        """
        Clean up old entries to free memory
        
        Args:
            now: Current time
        """
        max_age = 3600  # Keep data for max 1 hour
        cutoff_time = now - max_age
        
        clients_to_remove = []
        
        for client_id, timestamps in self.requests.items():
            # Filter old requests
            self.requests[client_id] = [
                t for t in timestamps if t > cutoff_time
            ]
            
            # Mark for removal if empty
            if not self.requests[client_id]:
                clients_to_remove.append(client_id)
        
        # Remove empty entries
        for client_id in clients_to_remove:
            del self.requests[client_id]
        
        self.last_cleanup = now
        
        logger.debug(
            f"Rate limiter cleanup completed",
            clients_tracked=len(self.requests),
            clients_removed=len(clients_to_remove)
        )
    
    def reset(self, client_id: Optional[str] = None) -> None:
        """
        Reset rate limit for client(s)
        
        Args:
            client_id: Client ID to reset (None to reset all)
        """
        if client_id:
            if client_id in self.requests:
                del self.requests[client_id]
        else:
            self.requests.clear()


class DynamicRateLimiter:
    """
    Dynamic rate limiter that adjusts limits based on system load
    """
    
    def __init__(self, base_limit: int, min_limit: int = 5, max_limit: int = None):
        """
        Initialize dynamic rate limiter
        
        Args:
            base_limit: Base request limit
            min_limit: Minimum allowed limit
            max_limit: Maximum allowed limit
        """
        self.base_limit = base_limit
        self.min_limit = min_limit
        self.max_limit = max_limit or base_limit * 2
        self.load_factor = 1.0
    
    def set_load_factor(self, factor: float) -> None:
        """
        Set system load factor (0.0 - 2.0)
        
        Args:
            factor: Load factor (1.0 = normal, 0.5 = half capacity, 2.0 = double capacity)
        """
        self.load_factor = max(0.0, min(2.0, factor))
    
    def get_current_limit(self) -> int:
        """
        Get current rate limit based on load
        
        Returns:
            Adjusted request limit
        """
        adjusted = int(self.base_limit * self.load_factor)
        return max(self.min_limit, min(self.max_limit, adjusted))
