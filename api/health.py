import logging

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy import text

from configs import get_settings
from configs.falkordb import get_falkordb_client
from configs.postgres import use_db_session
from configs.rate_limiter import limiter
from configs.redis import get_redis_client
from configs.s3 import get_s3_client
from configs.supabase import get_supabase_client
from middlewares.api_key import require_internal_api_key

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"], dependencies=[Depends(require_internal_api_key)])


@router.get("/", status_code=status.HTTP_200_OK)
@limiter.limit("60/minute")
async def health_check(request: Request, response: Response) -> dict[str, str]:
    settings = get_settings()
    db_status = "ok"
    supabase_status = "ok"
    redis_status = "ok"
    s3_status = "ok"
    falkordb_status = "ok"
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
        redis_result = await redis_client.ping()
        if not redis_result:
            logger.error("Redis connection error")
            redis_status = "error"
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    except Exception as e:
        redis_status = "error"
        logger.error(f"Redis connection error: {e}")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    try:
        s3_client = await get_s3_client()
        async with s3_client as s3:
            await s3.get_object(
                Bucket=settings.S3_BUCKET_NAME,
                Key=settings.S3_TEST_FILE_PATH,
            )
    except Exception as e:
        s3_status = "error"
        logger.error(f"S3 connection error: {e}")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    try:
        falkordb_client = await get_falkordb_client()
        graph = falkordb_client.select_graph(settings.FALKORDB_TEST_GRAPH_NAME)
        test_response = await graph.ro_query(
            "MATCH (n) OPTIONAL MATCH (n)-[e]-(m) RETURN * LIMIT 1"
        )
        test_result = test_response.result_set
        if len(test_result) == 0:
            logger.error("Falkordb connection error")
            falkordb_status = "error"
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    except Exception as e:
        falkordb_status = "error"
        logger.error(f"Falkordb connection error: {e}")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
        "version": settings.VERSION,
        "database": db_status,
        "supabase": supabase_status,
        "redis": redis_status,
        "s3": s3_status,
        "falkordb": falkordb_status,
    }
