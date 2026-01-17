import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from configs import get_settings
from middlewares.api_key import require_internal_api_key


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    get_settings.cache_clear()


def _make_app() -> FastAPI:
    app = FastAPI()

    @app.get("/protected", dependencies=[Depends(require_internal_api_key)])
    async def protected():
        return {"ok": True}

    return app


def test_passes_when_key_not_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTERNAL_API_KEY", "")
    app = _make_app()

    client = TestClient(app)
    resp = client.get("/protected")

    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_rejects_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTERNAL_API_KEY", "secret")
    app = _make_app()

    client = TestClient(app)
    resp = client.get("/protected")

    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid or missing API key"


def test_rejects_when_blank_header(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTERNAL_API_KEY", "secret")
    app = _make_app()

    client = TestClient(app)
    resp = client.get("/protected", headers={"X-API-Key": ""})

    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid or missing API key"


def test_rejects_when_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTERNAL_API_KEY", "secret")
    app = _make_app()

    client = TestClient(app)
    resp = client.get("/protected", headers={"X-API-Key": "wrong"})

    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid or missing API key"


def test_allows_when_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTERNAL_API_KEY", "secret")
    app = _make_app()

    client = TestClient(app)
    resp = client.get("/protected", headers={"X-API-Key": "secret"})

    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
