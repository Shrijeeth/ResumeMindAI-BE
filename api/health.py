import logging

from fastapi import APIRouter, Response, status
from sqlalchemy import text

from configs import get_settings
from configs.postgres import use_db_session
from configs.redis import get_redis_client
from configs.supabase import get_supabase_client

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/", status_code=status.HTTP_200_OK)
async def health_check(response: Response) -> dict[str, str]:
    settings = get_settings()
    db_status = "ok"
    supabase_status = "ok"
    redis_status = "ok"
    try:
        async with use_db_session() as session:
            db_result = await session.execute(text("SELECT 1"))
            if db_result.scalar() is None:
                logger.error("Database connection error")
                db_status = "error"
                response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        db_status = "error"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    try:
        supabase_client = await get_supabase_client()
        if supabase_client is None:
            logger.error("Supabase client is not initialized")
            supabase_status = "error"
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    except Exception as e:
        supabase_status = "error"
        logger.error(f"Supabase connection error: {e}")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    try:
        redis_client = await get_redis_client()
        if redis_client is None:
            logger.error("Redis client is not initialized")
            redis_status = "error"
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        else:
            redis_result = await redis_client.ping()
            if not redis_result:
                logger.error("Redis connection error")
                redis_status = "error"
                response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    except Exception as e:
        redis_status = "error"
        logger.error(f"Redis connection error: {e}")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
        "version": settings.VERSION,
        "database": db_status,
        "supabase": supabase_status,
        "redis": redis_status,
    }
