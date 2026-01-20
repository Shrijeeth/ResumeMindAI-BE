"""Idempotency decorator for FastAPI endpoints.

Implements payload-based duplicate detection without requiring client-side
idempotency keys. The server automatically computes a fingerprint from
user_id + endpoint + method + body to detect duplicates.

Usage:
    @router.post("/resource", status_code=201)
    @idempotent(ttl=300)
    async def create_resource(
        request: Request,
        current_user=Depends(get_current_user),
        ...
    ):
        # Your endpoint logic
        return {"id": "123", "status": "created"}

Response Headers:
    X-Idempotency-Key: <server-generated-fingerprint>
    X-Idempotency-Status: hit | miss
"""

import functools
import logging
from typing import Any, Callable

from fastapi import HTTPException, Request, Response, status
from fastapi.responses import JSONResponse

from configs.settings import get_settings
from services.idempotency import (
    acquire_lock,
    cache_response,
    compute_fingerprint,
    delete_cached_response,
    get_cached_response,
    release_lock,
)

logger = logging.getLogger(__name__)
settings = get_settings()

# Response header names
IDEMPOTENCY_KEY_HEADER = "X-Idempotency-Key"
IDEMPOTENCY_STATUS_HEADER = "X-Idempotency-Status"


def idempotent(ttl: int = None, methods: tuple = ("POST", "PUT", "PATCH")):
    """Decorator to enable idempotency for an endpoint.

    Automatically detects duplicate requests based on payload fingerprint.
    No client-side idempotency key required.

    Args:
        ttl: Custom TTL for cached responses in seconds (default: 300 from settings)
        methods: HTTP methods to apply idempotency to (default: POST, PUT, PATCH)

    Example:
        @router.post("/orders", status_code=201)
        @idempotent(ttl=600)  # Cache for 10 minutes
        async def create_order(request: Request, ...):
            ...
    """
    _ttl = ttl or settings.IDEMPOTENCY_TTL_SECONDS

    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from kwargs
            request: Request = kwargs.get("request")
            if not request:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            if not request:
                logger.warning("Request not found in endpoint arguments")
                return await func(*args, **kwargs)

            # Check if method should have idempotency
            if request.method not in methods:
                return await func(*args, **kwargs)

            # Get user_id for fingerprint scoping
            current_user = kwargs.get("current_user")
            if not current_user:
                logger.warning("current_user not found - skipping idempotency")
                return await func(*args, **kwargs)

            user_id = str(current_user.id)

            # Compute request fingerprint
            body = await request.body()
            fingerprint = compute_fingerprint(
                user_id=user_id,
                path=request.url.path,
                method=request.method,
                body=body,
            )

            # Check for cached response
            cached = await get_cached_response(user_id, fingerprint)

            if cached:
                logger.info(f"Idempotency hit for user {user_id}: {fingerprint[:8]}...")
                return _create_cached_response(cached, fingerprint, "hit")

            # Try to acquire lock for this fingerprint
            lock_acquired = await acquire_lock(user_id, fingerprint)

            if not lock_acquired:
                logger.warning(
                    "Concurrent duplicate request for user %s: %s...",
                    user_id,
                    fingerprint[:8],
                )
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "error": "duplicate_request_in_progress",
                        "message": (
                            "A request with the same payload is currently being "
                            "processed. Please retry after a short delay."
                        ),
                        "retry_after": settings.IDEMPOTENCY_LOCK_TTL_SECONDS,
                    },
                    headers={"Retry-After": str(settings.IDEMPOTENCY_LOCK_TTL_SECONDS)},
                )

            try:
                # Execute the actual endpoint
                response = await func(*args, **kwargs)

                # Extract response data for caching
                response_data = await _extract_response_data(response)

                # Only cache successful responses (2xx status codes)
                if 200 <= response_data["status_code"] < 300:
                    await cache_response(
                        user_id=user_id,
                        fingerprint=fingerprint,
                        status_code=response_data["status_code"],
                        headers=response_data["headers"],
                        body=response_data["body"],
                        ttl=_ttl,
                    )

                # Add idempotency headers to response
                return _add_idempotency_headers(response, fingerprint, "miss")

            except HTTPException:
                # Don't cache HTTP exceptions, just release lock and re-raise
                raise
            except Exception as e:
                # Clean up on unexpected errors
                logger.error(
                    "Endpoint error with fingerprint %s: %s",
                    fingerprint[:8],
                    e,
                )
                await delete_cached_response(user_id, fingerprint)
                raise
            finally:
                # Always release the lock
                await release_lock(user_id, fingerprint)

        return wrapper

    return decorator


def _create_cached_response(
    cached: dict[str, Any],
    fingerprint: str,
    idempotency_status: str,
) -> Response:
    """Create a Response object from cached data."""
    headers = dict(cached.get("headers", {}))
    headers[IDEMPOTENCY_KEY_HEADER] = fingerprint
    headers[IDEMPOTENCY_STATUS_HEADER] = idempotency_status

    body = cached["body"]
    if isinstance(body, str):
        try:
            body = __import__("json").loads(body)
        except (ValueError, TypeError):
            pass

    return JSONResponse(
        content=body,
        status_code=cached["status_code"],
        headers=headers,
    )


def _add_idempotency_headers(
    response: Any,
    fingerprint: str,
    idempotency_status: str,
) -> Any:
    """Add idempotency headers to response."""
    if isinstance(response, Response):
        response.headers[IDEMPOTENCY_KEY_HEADER] = fingerprint
        response.headers[IDEMPOTENCY_STATUS_HEADER] = idempotency_status
        return response

    # For Pydantic models or dicts, wrap in JSONResponse
    if hasattr(response, "model_dump"):
        body = response.model_dump(mode="json")
    elif isinstance(response, dict):
        body = response
    else:
        body = response

    return JSONResponse(
        content=body,
        status_code=200,
        headers={
            IDEMPOTENCY_KEY_HEADER: fingerprint,
            IDEMPOTENCY_STATUS_HEADER: idempotency_status,
        },
    )


async def _extract_response_data(response: Any) -> dict[str, Any]:
    """Extract data from response for caching.

    Handles various response types:
    - JSONResponse
    - Response with body
    - Pydantic models
    - Plain dicts
    """
    if isinstance(response, JSONResponse):
        body = response.body
        if isinstance(body, bytes):
            body = body.decode("utf-8")
        try:
            body = __import__("json").loads(body)
        except (ValueError, TypeError):
            pass
        return {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": body,
        }
    elif isinstance(response, Response):
        body = response.body
        if isinstance(body, bytes):
            body = body.decode("utf-8")
        try:
            body = __import__("json").loads(body)
        except (ValueError, TypeError):
            pass
        return {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": body,
        }
    elif hasattr(response, "model_dump"):
        # Pydantic model
        return {
            "status_code": 200,
            "headers": {},
            "body": response.model_dump(mode="json"),
        }
    elif isinstance(response, dict):
        return {
            "status_code": 200,
            "headers": {},
            "body": response,
        }
    else:
        # Fallback for other types
        return {
            "status_code": 200,
            "headers": {},
            "body": response,
        }
