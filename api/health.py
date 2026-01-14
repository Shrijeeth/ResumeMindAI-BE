from fastapi import APIRouter, status

from configs import get_settings

router = APIRouter(tags=["health"])


@router.get("/", status_code=status.HTTP_200_OK)
def health_check() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
        "version": settings.VERSION,
    }
