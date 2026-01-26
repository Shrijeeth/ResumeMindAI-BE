from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from configs import get_settings


def _rate_limit_key(request: Request):
    """Resolve client identifier respecting trusted proxies."""

    settings = get_settings()
    client_host = request.client.host if request.client else None

    if client_host in settings.TRUSTED_PROXIES:
        x_forwarded_for = request.headers.get("x-forwarded-for")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()

        x_real_ip = request.headers.get("x-real-ip")
        if x_real_ip:
            return x_real_ip.strip()

    return client_host or get_remote_address(request)


# Shared limiter instance for app and endpoint decorators
limiter = Limiter(
    key_func=_rate_limit_key,
    default_limits=get_settings().RATE_LIMITER_DEFAULT_LIMITS,
)


def get_limiter() -> Limiter:
    return limiter
