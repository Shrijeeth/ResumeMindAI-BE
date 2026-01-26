from starlette.requests import Request

from configs import get_settings
from configs.rate_limiter import _rate_limit_key, get_limiter, limiter


def make_request(
    client_host: str | None,
    headers: dict[str, str] | None = None,
) -> Request:
    scope = {
        "type": "http",
        "path": "/",
        "headers": [],
    }

    if client_host:
        scope["client"] = (client_host, 1234)

    if headers:
        scope["headers"] = [
            (name.lower().encode(), value.encode()) for name, value in headers.items()
        ]

    return Request(scope)


def test_rate_limit_key_prefers_x_forwarded_for_for_trusted_proxy():
    settings = get_settings()
    original_trusted = settings.TRUSTED_PROXIES.copy()
    settings.TRUSTED_PROXIES = ["10.0.0.1"]

    request = make_request(
        client_host="10.0.0.1",
        headers={"x-forwarded-for": "2.2.2.2, 3.3.3.3"},
    )

    try:
        assert _rate_limit_key(request) == "2.2.2.2"
    finally:
        settings.TRUSTED_PROXIES = original_trusted


def test_rate_limit_key_uses_x_real_ip_when_forwarded_missing():
    settings = get_settings()
    original_trusted = settings.TRUSTED_PROXIES.copy()
    settings.TRUSTED_PROXIES = ["10.0.0.1"]

    request = make_request(
        client_host="10.0.0.1",
        headers={"x-real-ip": "4.4.4.4"},
    )

    try:
        assert _rate_limit_key(request) == "4.4.4.4"
    finally:
        settings.TRUSTED_PROXIES = original_trusted


def test_rate_limit_key_falls_back_to_client_host():
    request = make_request(client_host="5.5.5.5")
    assert _rate_limit_key(request) == "5.5.5.5"


def test_rate_limit_key_handles_missing_client():
    request = make_request(client_host=None)
    assert _rate_limit_key(request) == "127.0.0.1"


def test_get_limiter_returns_shared_instance():
    assert get_limiter() is limiter
