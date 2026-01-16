import redis.asyncio as redis

from configs.settings import get_settings

redis_client: redis.Redis | None = None


async def init_redis_client() -> None:
    global redis_client
    settings = get_settings()
    redis_client = redis.Redis.from_url(
        settings.REDIS_URL,
        max_connections=20,
        decode_responses=True,
    )


async def shutdown_redis_client() -> None:
    global redis_client
    if redis_client is not None:
        await redis_client.close()
    redis_client = None


async def get_redis_client() -> redis.Redis | None:
    global redis_client
    if redis_client is None:
        raise RuntimeError("Redis client is not initialized")
    return redis_client
