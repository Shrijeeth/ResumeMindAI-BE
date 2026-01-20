"""Idempotency service for Redis-backed request deduplication.

Provides payload-based duplicate detection without requiring client-side
idempotency keys. Computes a fingerprint from user_id + endpoint + method + body
to identify duplicate requests.
"""

import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Optional

from configs.redis import get_redis_client
from configs.settings import get_settings
from services.cache import CacheEncoder

logger = logging.getLogger(__name__)

settings = get_settings()

IDEMPOTENCY_TTL_SECONDS = settings.IDEMPOTENCY_TTL_SECONDS
IDEMPOTENCY_LOCK_TTL_SECONDS = settings.IDEMPOTENCY_LOCK_TTL_SECONDS
IDEMPOTENCY_KEY_PREFIX = settings.IDEMPOTENCY_KEY_PREFIX


def _cache_key(user_id: str, fingerprint: str) -> str:
    """Generate Redis key for idempotency cache."""
    return f"{IDEMPOTENCY_KEY_PREFIX}:{user_id}:{fingerprint}"


def _lock_key(user_id: str, fingerprint: str) -> str:
    """Generate Redis key for distributed lock."""
    return f"{IDEMPOTENCY_KEY_PREFIX}:lock:{user_id}:{fingerprint}"


def compute_fingerprint(user_id: str, path: str, method: str, body: bytes) -> str:
    """Compute SHA256 fingerprint from request attributes.

    Args:
        user_id: User identifier
        path: Request path (e.g., /api/documents/upload)
        method: HTTP method (e.g., POST)
        body: Request body bytes

    Returns:
        32-character hex fingerprint
    """
    content = f"{user_id}:{method}:{path}:{body.decode('utf-8', errors='replace')}"
    return hashlib.sha256(content.encode()).hexdigest()[:32]


async def acquire_lock(user_id: str, fingerprint: str, ttl: int = None) -> bool:
    """Acquire distributed lock for idempotency fingerprint.

    Uses Redis SET NX (set if not exists) for atomic lock acquisition.

    Args:
        user_id: User identifier
        fingerprint: Computed request fingerprint
        ttl: Lock timeout in seconds (default from settings)

    Returns:
        True if lock acquired, False if already locked
    """
    ttl = ttl or IDEMPOTENCY_LOCK_TTL_SECONDS

    try:
        redis_client = await get_redis_client()
        key = _lock_key(user_id, fingerprint)

        acquired = await redis_client.set(key, "1", nx=True, ex=ttl)

        if acquired:
            logger.debug(f"Lock acquired for fingerprint: {fingerprint[:8]}...")
        else:
            logger.debug(f"Lock already held for fingerprint: {fingerprint[:8]}...")

        return bool(acquired)

    except RuntimeError as e:
        logger.warning(f"Redis not available for lock acquisition: {e}")
        return True  # Graceful degradation: allow request to proceed
    except Exception as e:
        logger.warning(f"Lock acquisition failed: {e}")
        return True  # Graceful degradation


async def release_lock(user_id: str, fingerprint: str) -> bool:
    """Release distributed lock for idempotency fingerprint.

    Args:
        user_id: User identifier
        fingerprint: Computed request fingerprint

    Returns:
        True if released successfully, False on error
    """
    try:
        redis_client = await get_redis_client()
        key = _lock_key(user_id, fingerprint)
        await redis_client.delete(key)
        logger.debug(f"Lock released for fingerprint: {fingerprint[:8]}...")
        return True
    except RuntimeError as e:
        logger.warning(f"Redis not available for lock release: {e}")
        return False
    except Exception as e:
        logger.warning(f"Lock release failed: {e}")
        return False


async def get_cached_response(
    user_id: str,
    fingerprint: str,
) -> Optional[dict[str, Any]]:
    """Retrieve cached response for fingerprint.

    Args:
        user_id: User identifier
        fingerprint: Computed request fingerprint

    Returns:
        Cached response dict if found, None on miss or error
    """
    try:
        redis_client = await get_redis_client()
        key = _cache_key(user_id, fingerprint)

        cached = await redis_client.get(key)
        if cached:
            logger.debug(f"Idempotency cache hit: {fingerprint[:8]}...")
            return json.loads(cached)

        logger.debug(f"Idempotency cache miss: {fingerprint[:8]}...")
        return None

    except RuntimeError as e:
        logger.warning(f"Redis not available for idempotency lookup: {e}")
        return None
    except Exception as e:
        logger.warning(f"Idempotency lookup failed: {e}")
        return None


async def cache_response(
    user_id: str,
    fingerprint: str,
    status_code: int,
    headers: dict[str, str],
    body: Any,
    ttl: int = None,
) -> bool:
    """Cache response for fingerprint.

    Args:
        user_id: User identifier
        fingerprint: Computed request fingerprint
        status_code: HTTP status code
        headers: Response headers (filtered to relevant ones)
        body: Response body (JSON-serializable)
        ttl: Time-to-live in seconds (default from settings)

    Returns:
        True if cached successfully, False on error
    """
    ttl = ttl or IDEMPOTENCY_TTL_SECONDS

    try:
        redis_client = await get_redis_client()
        key = _cache_key(user_id, fingerprint)

        payload = {
            "status_code": status_code,
            "headers": headers,
            "body": body,
            "created_at": datetime.utcnow().isoformat(),
        }

        await redis_client.set(
            key,
            json.dumps(payload, cls=CacheEncoder),
            ex=ttl,
        )

        logger.debug(f"Cached idempotency response: {fingerprint[:8]}... (TTL: {ttl}s)")
        return True

    except RuntimeError as e:
        logger.warning(f"Redis not available for idempotency caching: {e}")
        return False
    except Exception as e:
        logger.warning(f"Idempotency cache failed: {e}")
        return False


async def delete_cached_response(user_id: str, fingerprint: str) -> bool:
    """Delete cached response (for error cleanup).

    Args:
        user_id: User identifier
        fingerprint: Computed request fingerprint

    Returns:
        True if deleted, False on error
    """
    try:
        redis_client = await get_redis_client()
        key = _cache_key(user_id, fingerprint)
        await redis_client.delete(key)
        logger.debug(f"Deleted idempotency cache: {fingerprint[:8]}...")
        return True
    except RuntimeError as e:
        logger.warning(f"Redis not available for idempotency deletion: {e}")
        return False
    except Exception as e:
        logger.warning(f"Idempotency deletion failed: {e}")
        return False
