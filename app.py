import logging

from fastapi import FastAPI

from api.health import router as health_router
from configs import get_settings, init_engine, shutdown_engine

logger = logging.getLogger(__name__)


async def startup(app: FastAPI) -> None:
    logger.info("Starting the application...")

    logger.info("Initializing database engine...")
    init_engine()


async def shutdown(app: FastAPI) -> None:
    logger.info("Shutting down database engine...")
    await shutdown_engine()

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

    application.include_router(health_router, prefix="/api/health")

    return application


app = create_app()
