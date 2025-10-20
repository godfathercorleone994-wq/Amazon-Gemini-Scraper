"""
Redis cache for performance optimization
"""
from typing import Optional, Any, List
import json
import pickle
from datetime import timedelta
import redis.asyncio as redis
from redis.asyncio import Redis
from redis.exceptions import RedisError

from config.settings import settings
from utils.logger import logger

class RedisCache:
    """Async Redis cache manager"""
    
    def __init__(self):
        self.redis: Optional[Redis] = None
        self._initialized = False
        self.default_ttl = settings.redis_ttl
    
    async def connect(self):
        """Connect to Redis"""
        if self._initialized:
            return
        
        try:
            logger.info("Connecting to Redis...")
            
            self.redis = await redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=False,  # We'll handle encoding
                max_connections=settings.redis_max_connections
            )
            
            # Test connection
            await self.redis.ping()
            
            self._initialized = True
            logger.info("Redis connected successfully")
            
        except RedisError as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Redis initialization error: {str(e)}")
            raise
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis:
            await self.redis.close()
            self._initialized = False
            logger.info("Redis disconnected")
    
    async def get(self, key: str, deserialize: bool = True) -> Optional[Any]:
        """Get value from cache"""
        try:
            value = await self.redis.get(key)
            
            if value is None:
                return None
            
            if deserialize:
                try:
                    # Try JSON first
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    # Fall back to pickle
                    return pickle.loads(value)
            
            return value
            
        except RedisError as e:
            logger.error(f"Redis get error: {str(e)}")
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        serialize: bool = True
    ) -> bool:
        """Set value in cache"""
        try:
            if serialize:
                try:
                    # Try JSON first for readability
                    encoded_value = json.dumps(value)
                except (TypeError, ValueError):
                    # Fall back to pickle for complex objects
                    encoded_value = pickle.dumps(value)
            else:
                encoded_value = value
            
            expiry = ttl or self.default_ttl
            
            await self.redis.set(key, encoded_value, ex=expiry)
            return True
            
        except RedisError as e:
            logger.error(f"Redis set error: {str(e)}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            result = await self.redis.delete(key)
            return result > 0
        except RedisError as e:
            logger.error(f"Redis delete error: {str(e)}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        try:
            return await self.redis.exists(key) > 0
        except RedisError as e:
            logger.error(f"Redis exists error: {str(e)}")
            return False
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on key"""
        try:
            return await self.redis.expire(key, seconds)
        except RedisError as e:
            logger.error(f"Redis expire error: {str(e)}")
            return False
    
    async def ttl(self, key: str) -> int:
        """Get TTL for key"""
        try:
            return await self.redis.ttl(key)
        except RedisError as e:
            logger.error(f"Redis TTL error: {str(e)}")
            return -1
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment counter"""
        try:
            return await self.redis.incrby(key, amount)
        except RedisError as e:
            logger.error(f"Redis increment error: {str(e)}")
            return 0
    
    async def decrement(self, key: str, amount: int = 1) -> int:
        """Decrement counter"""
        try:
            return await self.redis.decrby(key, amount)
        except RedisError as e:
            logger.error(f"Redis decrement error: {str(e)}")
            return 0
    
    # ==================== List Operations ====================
    
    async def lpush(self, key: str, *values) -> int:
        """Push values to list (left)"""
        try:
            serialized = [json.dumps(v) for v in values]
            return await self.redis.lpush(key, *serialized)
        except RedisError as e:
            logger.error(f"Redis lpush error: {str(e)}")
            return 0
    
    async def rpush(self, key: str, *values) -> int:
        """Push values to list (right)"""
        try:
            serialized = [json.dumps(v) for v in values]
            return await self.redis.rpush(key, *serialized)
        except RedisError as e:
            logger.error(f"Redis rpush error: {str(e)}")
            return 0
    
    async def lrange(self, key: str, start: int = 0, end: int = -1) -> List[Any]:
        """Get range from list"""
        try:
            values = await self.redis.lrange(key, start, end)
            return [json.loads(v) for v in values]
        except RedisError as e:
            logger.error(f"Redis lrange error: {str(e)}")
            return []
    
    async def llen(self, key: str) -> int:
        """Get list length"""
        try:
            return await self.redis.llen(key)
        except RedisError as e:
            logger.error(f"Redis llen error: {str(e)}")
            return 0
    
    # ==================== Set Operations ====================
    
    async def sadd(self, key: str, *members) -> int:
        """Add members to set"""
        try:
            serialized = [json.dumps(m) for m in members]
            return await self.redis.sadd(key, *serialized)
        except RedisError as e:
            logger.error(f"Redis sadd error: {str(e)}")
            return 0
    
    async def smembers(self, key: str) -> set:
        """Get all set members"""
        try:
            members = await self.redis.smembers(key)
            return {json.loads(m) for m in members}
        except RedisError as e:
            logger.error(f"Redis smembers error: {str(e)}")
            return set()
    
    async def sismember(self, key: str, member: Any) -> bool:
        """Check if member is in set"""
        try:
            serialized = json.dumps(member)
            return await self.redis.sismember(key, serialized)
        except RedisError as e:
            logger.error(f"Redis sismember error: {str(e)}")
            return False
    
    # ==================== Hash Operations ====================
    
    async def hset(self, name: str, key: str, value: Any) -> int:
        """Set hash field"""
        try:
            serialized = json.dumps(value)
            return await self.redis.hset(name, key, serialized)
        except RedisError as e:
            logger.error(f"Redis hset error: {str(e)}")
            return 0
    
    async def hget(self, name: str, key: str) -> Optional[Any]:
        """Get hash field"""
        try:
            value = await self.redis.hget(name, key)
            return json.loads(value) if value else None
        except RedisError as e:
            logger.error(f"Redis hget error: {str(e)}")
            return None
    
    async def hgetall(self, name: str) -> dict:
        """Get all hash fields"""
        try:
            data = await self.redis.hgetall(name)
            return {k.decode(): json.loads(v) for k, v in data.items()}
        except RedisError as e:
            logger.error(f"Redis hgetall error: {str(e)}")
            return {}
    
    async def hdel(self, name: str, *keys) -> int:
        """Delete hash fields"""
        try:
            return await self.redis.hdel(name, *keys)
        except RedisError as e:
            logger.error(f"Redis hdel error: {str(e)}")
            return 0
    
    # ==================== Cache Patterns ====================
    
    async def cache_product(self, asin: str, product_data: dict, ttl: Optional[int] = None):
        """Cache product data"""
        key = f"product:{asin}"
        await self.set(key, product_data, ttl=ttl or 3600)  # 1 hour default
    
    async def get_cached_product(self, asin: str) -> Optional[dict]:
        """Get cached product"""
        key = f"product:{asin}"
        return await self.get(key)
    
    async def cache_search_results(self, query: str, results: List[dict], ttl: Optional[int] = None):
        """Cache search results"""
        key = f"search:{query}"
        await self.set(key, results, ttl=ttl or 1800)  # 30 minutes default
    
    async def get_cached_search(self, query: str) -> Optional[List[dict]]:
        """Get cached search results"""
        key = f"search:{query}"
        return await self.get(key)
    
    async def track_rate_limit(self, identifier: str, limit: int, period: int) -> bool:
        """
        Track rate limiting
        Returns True if under limit, False if exceeded
        """
        key = f"ratelimit:{identifier}"
        
        current = await self.increment(key)
        
        if current == 1:
            # First request, set expiry
            await self.expire(key, period)
        
        return current <= limit
    
    async def get_rate_limit_status(self, identifier: str) -> dict:
        """Get rate limit status"""
        key = f"ratelimit:{identifier}"
        
        current = await self.get(key, deserialize=False)
        ttl = await self.ttl(key)
        
        return {
            "current": int(current) if current else 0,
            "remaining_time": ttl if ttl > 0 else 0
        }
    
    async def cache_extraction_result(self, task_id: str, result: dict, ttl: Optional[int] = None):
        """Cache extraction result"""
        key = f"extraction:{task_id}"
        await self.set(key, result, ttl=ttl or 7200)  # 2 hours default
    
    async def get_cached_extraction(self, task_id: str) -> Optional[dict]:
        """Get cached extraction result"""
        key = f"extraction:{task_id}"
        return await self.get(key)
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear keys matching pattern"""
        try:
            keys = await self.redis.keys(pattern)
            if keys:
                return await self.redis.delete(*keys)
            return 0
        except RedisError as e:
            logger.error(f"Redis clear pattern error: {str(e)}")
            return 0
    
    async def get_stats(self) -> dict:
        """Get Redis stats"""
        try:
            info = await self.redis.info()
            
            return {
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory_human", "0"),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "uptime_in_seconds": info.get("uptime_in_seconds", 0)
            }
        except RedisError as e:
            logger.error(f"Redis stats error: {str(e)}")
            return {}

# Global Redis cache instance
redis_cache = RedisCache()

async def get_redis() -> RedisCache:
    """Get Redis cache instance"""
    if not redis_cache._initialized:
        await redis_cache.connect()
    return redis_cache
