from fastapi import FastAPI

from api.health import router as health_router
from configs import get_settings


def create_app() -> FastAPI:
    settings = get_settings()

    if settings.ENVIRONMENT == "production":
        application = FastAPI(
            title=settings.APP_NAME,
            version=settings.VERSION,
            openapi_url=None,
            docs_url=None,
            redoc_url=None,
        )
    else:
        application = FastAPI(title=settings.APP_NAME, version=settings.VERSION)

    application.include_router(health_router, prefix="/api/health")

    return application


app = create_app()
