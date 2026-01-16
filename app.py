import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.health import router as health_router
from api.llm_providers import router as llm_providers_router
from configs import get_settings
from configs.postgres import init_engine, shutdown_engine
from configs.redis import init_redis_client, shutdown_redis_client
from configs.supabase import init_supabase_client, shutdown_supabase_client

logger = logging.getLogger(__name__)


async def startup(app: FastAPI) -> None:
    logger.info("Starting the application...")

    logger.info("Initializing database engine...")
    init_engine()

    logger.info("Initializing supabase client...")
    await init_supabase_client()

    logger.info("Initializing redis client...")
    await init_redis_client()


async def shutdown(app: FastAPI) -> None:
    logger.info("Shutting down database engine...")
    await shutdown_engine()

    logger.info("Shutting down supabase client...")
    await shutdown_supabase_client()

    logger.info("Shutting down redis client...")
    await shutdown_redis_client()

    logger.info("Shutting down the application...")


async def lifespan(app: FastAPI) -> None:
    await startup(app)
    yield
    await shutdown(app)


def create_app() -> FastAPI:
    settings = get_settings()

    if settings.ENVIRONMENT == "production":
        application = FastAPI(
            title=settings.APP_NAME,
            version=settings.VERSION,
            lifespan=lifespan,
            openapi_url=None,
            docs_url=None,
            redoc_url=None,
        )
    else:
        application = FastAPI(
            title=settings.APP_NAME,
            version=settings.VERSION,
            lifespan=lifespan,
        )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ALLOW_ORIGINS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    )

    application.include_router(health_router, prefix="/api/health")
    application.include_router(
        llm_providers_router, prefix="/api/settings/llm-providers"
    )

    return application


app = create_app()
