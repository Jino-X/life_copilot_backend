"""Redis client configuration."""
from typing import Optional

import redis.asyncio as redis
from redis.asyncio import Redis

from app.core.config import settings

_redis_client: Optional[Redis] = None


async def get_redis() -> Redis:
    """Get Redis client instance."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


async def close_redis() -> None:
    """Close Redis connection."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None


class CacheService:
    """Service for caching operations."""
    
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        return await self.redis.get(key)
    
    async def set(
        self,
        key: str,
        value: str,
        expire_seconds: int = 3600
    ) -> None:
        """Set value in cache with expiration."""
        await self.redis.setex(key, expire_seconds, value)
    
    async def delete(self, key: str) -> None:
        """Delete key from cache."""
        await self.redis.delete(key)
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        return await self.redis.exists(key) > 0
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment a counter."""
        return await self.redis.incrby(key, amount)
    
    async def expire(self, key: str, seconds: int) -> None:
        """Set expiration on a key."""
        await self.redis.expire(key, seconds)


async def get_cache_service() -> CacheService:
    """Get cache service instance."""
    redis_client = await get_redis()
    return CacheService(redis_client)
