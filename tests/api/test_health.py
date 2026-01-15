import pytest
from fastapi.testclient import TestClient

from api import health
from app import app
from configs import get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    get_settings.cache_clear()


def test_health_endpoint_returns_status_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_NAME", "TestApp")
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("VERSION", "9.9.9")

    class DummySession:
        async def execute(self, _):
            return None

    class DummyCtx:
        async def __aenter__(self):
            return DummySession()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(health, "use_db_session", lambda: DummyCtx())

    client = TestClient(app)
    response = client.get("/api/health/")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "app": "TestApp",
        "environment": "test",
        "version": "9.9.9",
        "database": "ok",
    }


def test_health_endpoint_handles_db_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_NAME", "TestApp")
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("VERSION", "9.9.9")

    class FailingCtx:
        async def __aenter__(self):
            raise RuntimeError("boom")

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(health, "use_db_session", lambda: FailingCtx())

    client = TestClient(app)
    response = client.get("/api/health/")

    assert response.status_code == 503
    assert response.json()["database"] == "error"
