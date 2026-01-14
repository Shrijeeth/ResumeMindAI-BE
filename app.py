from fastapi import FastAPI

from api.health import router as health_router
from configs import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(title=settings.APP_NAME, version=settings.VERSION)

    application.include_router(health_router, prefix="/api/health")

    return application


app = create_app()
