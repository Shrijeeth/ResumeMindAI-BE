from types import SimpleNamespace

import pytest

from tasks import health_task


@pytest.fixture(autouse=True)
def clear_settings_cache():
    health_task.get_settings.cache_clear()
    yield
    health_task.get_settings.cache_clear()


@pytest.mark.asyncio
async def test_check_api_health_task_success(monkeypatch):
    settings = SimpleNamespace(
        API_BASE_URL="http://example.com/", INTERNAL_API_KEY="secret"
    )
    monkeypatch.setattr(health_task, "get_settings", lambda: settings)

    # Capture request details and simulate response
    calls = {}

    class DummyResponse:
        def __init__(self):
            self._json = {"status": "ok"}

        def json(self):
            return self._json

        def raise_for_status(self):
            return None

    class DummyClient:
        def __init__(self, **kwargs):
            calls["timeout"] = kwargs.get("timeout")

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            calls["exited"] = True

        async def get(self, url, headers=None):
            calls["url"] = url
            calls["headers"] = headers
            return DummyResponse()

    monkeypatch.setattr(health_task.httpx, "AsyncClient", DummyClient)

    result = await health_task.check_api_health_task()

    assert result == {"status": "ok"}
    assert calls["url"] == "http://example.com/api/health"
    assert calls["headers"] == {"X-Api-Key": "secret"}
    assert calls["timeout"] == 30.0
    assert calls["exited"] is True


@pytest.mark.asyncio
async def test_check_api_health_task_raises_for_http_error(monkeypatch):
    settings = SimpleNamespace(
        API_BASE_URL="http://example.com", INTERNAL_API_KEY="secret"
    )
    monkeypatch.setattr(health_task, "get_settings", lambda: settings)

    class DummyResponse:
        def raise_for_status(self):
            raise RuntimeError("boom")

    class DummyClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url, headers=None):
            return DummyResponse()

    monkeypatch.setattr(health_task.httpx, "AsyncClient", lambda timeout: DummyClient())

    with pytest.raises(RuntimeError, match="boom"):
        await health_task.check_api_health_task()
