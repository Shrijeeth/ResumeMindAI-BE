import pytest
from fastapi.testclient import TestClient

from app import app
from configs import get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    get_settings.cache_clear()


def test_health_endpoint_returns_status_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_NAME", "TestApp")
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("VERSION", "9.9.9")

    client = TestClient(app)
    response = client.get("/api/health/")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "app": "TestApp",
        "environment": "test",
        "version": "9.9.9",
    }
