import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from api.documents import router as documents_router
from api.health import router as health_router
from api.llm_providers import router as llm_providers_router
from configs import get_settings
from configs.lifecycle import app_lifespan

logger = logging.getLogger(__name__)


async def lifespan(app: FastAPI):
    logger.info("Starting the application...")
    async with app_lifespan():
        yield
    logger.info("Shutting down the application...")


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

    if settings.ENVIRONMENT.lower() != "test":
        limiter = Limiter(
            key_func=get_remote_address,
            default_limits=settings.RATE_LIMITER_DEFAULT_LIMITS,
        )
        application.state.limiter = limiter
        application.add_exception_handler(
            RateLimitExceeded, _rate_limit_exceeded_handler
        )
        application.add_middleware(SlowAPIMiddleware)

    application.include_router(health_router, prefix="/api/health")
    application.include_router(
        llm_providers_router, prefix="/api/settings/llm-providers"
    )
    application.include_router(documents_router, prefix="/api/documents")

    return application


app = create_app()
