import logging

from fastapi import APIRouter, Response, status
from sqlalchemy import text

from configs import get_settings
from configs.postgres import use_db_session
from configs.supabase import get_supabase_client

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/", status_code=status.HTTP_200_OK)
async def health_check(response: Response) -> dict[str, str]:
    settings = get_settings()
    db_status = "ok"
    supabase_status = "ok"
    try:
        async with use_db_session() as session:
            await session.execute(text("SELECT 1"))
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
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
        "version": settings.VERSION,
        "database": db_status,
        "supabase": supabase_status,
    }
