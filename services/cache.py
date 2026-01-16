"""Cache service for Redis-backed caching operations."""

import json
import logging
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from configs.redis import get_redis_client

logger = logging.getLogger(__name__)

# Constants
PROVIDER_TEST_CACHE_TTL_SECONDS = 300
CACHE_KEY_PREFIX_PROVIDER_TEST = "cache:provider_test"


def _cache_key_provider_test(provider_id: UUID) -> str:
    """Generate cache key for provider test connection response."""
    return f"{CACHE_KEY_PREFIX_PROVIDER_TEST}:{provider_id}"


class CacheEncoder(json.JSONEncoder):
    """Custom JSON encoder for cache serialization."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, UUID):
            return str(obj)
        if hasattr(obj, "value"):  # Enum
            return obj.value
        return super().default(obj)


async def get_provider_test_cache(provider_id: UUID) -> Optional[dict]:
    """
    Get cached test response.

    Args:
        provider_id: UUID of the provider

    Returns:
        Cached response dict if found, None on miss or error
    """
    try:
        redis_client = await get_redis_client()
        cached = await redis_client.get(_cache_key_provider_test(provider_id))
        if cached:
            logger.debug(f"Cache hit for provider test: {provider_id}")
            return json.loads(cached)
        logger.debug(f"Cache miss for provider test: {provider_id}")
        return None
    except RuntimeError as e:
        logger.warning(f"Redis not available for cache lookup: {e}")
        return None
    except Exception as e:
        logger.warning(f"Cache lookup failed for {provider_id}: {e}")
        return None


async def set_provider_test_cache(
    provider_id: UUID,
    data: dict,
    ttl: int = PROVIDER_TEST_CACHE_TTL_SECONDS,
) -> bool:
    """
    Cache test response.

    Args:
        provider_id: UUID of the provider
        data: Response dict to cache (status, latency_ms, error_message, provider)
        ttl: Time-to-live in seconds (default: 300)

    Returns:
        True if cached successfully, False on error
    """
    try:
        redis_client = await get_redis_client()
        payload = {**data, "cached_at": datetime.utcnow().isoformat()}
        await redis_client.set(
            _cache_key_provider_test(provider_id),
            json.dumps(payload, cls=CacheEncoder),
            ex=ttl,
        )
        logger.debug(f"Cached provider test response for {provider_id} (TTL: {ttl}s)")
        return True
    except RuntimeError as e:
        logger.warning(f"Redis not available for caching: {e}")
        return False
    except Exception as e:
        logger.warning(f"Cache set failed for {provider_id}: {e}")
        return False


async def delete_provider_test_cache(provider_id: UUID) -> bool:
    """
    Delete cached test response.

    Best-effort deletion - errors are logged but not raised.

    Args:
        provider_id: UUID of the provider

    Returns:
        True if deleted (or key didn't exist), False on error
    """
    try:
        redis_client = await get_redis_client()
        await redis_client.delete(_cache_key_provider_test(provider_id))
        logger.debug(f"Deleted cache for provider test: {provider_id}")
        return True
    except RuntimeError as e:
        logger.warning(f"Redis not available for cache deletion: {e}")
        return False
    except Exception as e:
        logger.warning(f"Cache delete failed for {provider_id}: {e}")
        return False
