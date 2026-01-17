import logging

from fastapi import Header, HTTPException, status

from configs import get_settings

logger = logging.getLogger(__name__)


async def require_internal_api_key(
    x_api_key: str | None = Header(default=None),
) -> None:
    """Validate internal API key when configured.

    If INTERNAL_API_KEY is unset/empty, the check is skipped (useful for tests/dev).
    """

    settings = get_settings()
    expected_key = settings.INTERNAL_API_KEY

    if not expected_key:
        return

    if x_api_key != expected_key:
        logger.warning("Invalid or missing internal API key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
