import asyncio
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.testclient import TestClient
from starlette.responses import Response

import middlewares.idempotency as middleware
from middlewares.idempotency import (
    IDEMPOTENCY_KEY_HEADER,
    IDEMPOTENCY_STATUS_HEADER,
    idempotent,
)
from services import idempotency as svc


def run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def mock_settings(monkeypatch):
    monkeypatch.setattr(svc, "IDEMPOTENCY_TTL_SECONDS", 10)
    monkeypatch.setattr(svc, "IDEMPOTENCY_LOCK_TTL_SECONDS", 5)
    monkeypatch.setattr(svc, "IDEMPOTENCY_KEY_PREFIX", "idem")


@pytest.fixture
def app(monkeypatch):
    app = FastAPI()
    user_stub = SimpleNamespace(id="user1")
    middleware.settings = SimpleNamespace(
        IDEMPOTENCY_TTL_SECONDS=10,
        IDEMPOTENCY_LOCK_TTL_SECONDS=5,
        IDEMPOTENCY_KEY_PREFIX="idem",
    )

    def fake_compute_fingerprint(user_id: str, path: str, method: str, body: bytes):
        return "fingerprint"

    async def fake_get_cached_response(user_id: str, fingerprint: str):
        return None

    async def fake_acquire_lock(user_id: str, fingerprint: str):
        return True

    async def fake_release_lock(user_id: str, fingerprint: str):
        return True

    async def fake_cache_response(*args, **kwargs):
        return True

    monkeypatch.setattr(middleware, "compute_fingerprint", fake_compute_fingerprint)
    monkeypatch.setattr(middleware, "get_cached_response", fake_get_cached_response)
    monkeypatch.setattr(middleware, "acquire_lock", fake_acquire_lock)
    monkeypatch.setattr(middleware, "release_lock", fake_release_lock)
    monkeypatch.setattr(middleware, "cache_response", fake_cache_response)

    @app.post("/echo")
    @idempotent()
    async def echo(request: Request, current_user=user_stub):
        return {"echo": await request.json()}

    @app.post("/error")
    @idempotent()
    async def error_endpoint(request: Request, current_user=user_stub):
        raise HTTPException(status_code=400, detail="bad")

    @app.post("/unexpected")
    @idempotent()
    async def unexpected(request: Request, current_user=user_stub):
        raise RuntimeError("boom")

    return app


@pytest.fixture
def client(app):
    client = TestClient(app, raise_server_exceptions=False)
    client.headers.update({"Authorization": "Bearer token"})
    return client


@pytest.fixture
def user():
    return SimpleNamespace(id="user1")


@pytest.mark.asyncio
async def test_skips_when_no_request_arg(user):
    called = {}

    @idempotent()
    async def no_request(current_user):
        called["done"] = True
        return "ok"

    result = await no_request(current_user=user)
    assert called["done"] is True
    assert result == "ok"


def test_idempotency_hit(monkeypatch, app, client, user):
    async def fake_get_cached_response(user_id, fingerprint):
        return {
            "status_code": 200,
            "headers": {"X": "1"},
            "body": {"hello": "world"},
        }

    monkeypatch.setattr(middleware, "get_cached_response", fake_get_cached_response)

    response = client.post("/echo", json={"a": 1}, headers={"X-User": "1"})

    assert response.status_code == 200
    assert response.json() == {"hello": "world"}
    assert response.headers[IDEMPOTENCY_STATUS_HEADER] == "hit"
    assert IDEMPOTENCY_KEY_HEADER in response.headers


def test_concurrent_duplicate(monkeypatch, app, client, user):
    async def fake_acquire_lock(user_id, fingerprint):
        return False

    monkeypatch.setattr(middleware, "acquire_lock", fake_acquire_lock)

    response = client.post("/echo", json={"a": 1})

    assert response.status_code == status.HTTP_409_CONFLICT
    body = response.json()
    assert body["detail"]["error"] == "duplicate_request_in_progress"
    assert body["detail"]["retry_after"] == 5


def test_successful_cache_and_headers(monkeypatch, app, client, user):
    cached_calls = {}

    async def fake_cache_response(
        user_id, fingerprint, status_code, headers, body, ttl
    ):
        cached_calls["user_id"] = user_id
        cached_calls["fingerprint"] = fingerprint
        cached_calls["status_code"] = status_code
        cached_calls["headers"] = headers
        cached_calls["body"] = body
        cached_calls["ttl"] = ttl
        return True

    monkeypatch.setattr(middleware, "cache_response", fake_cache_response)

    response = client.post("/echo", json={"a": 1})

    assert response.status_code == 200
    assert response.headers[IDEMPOTENCY_STATUS_HEADER] == "miss"
    assert cached_calls["status_code"] == 200
    assert cached_calls["body"] == {"echo": {"a": 1}}
    assert cached_calls["ttl"] == middleware.settings.IDEMPOTENCY_TTL_SECONDS


def test_http_exception_bubbles_and_releases_lock(monkeypatch, app, client, user):
    released = {}

    async def fake_release_lock(user_id, fingerprint):
        released["fingerprint"] = fingerprint
        return True

    monkeypatch.setattr(middleware, "release_lock", fake_release_lock)

    response = client.post("/error", json={"a": 1})

    assert response.status_code == 400
    assert "fingerprint" in released["fingerprint"]


def test_unexpected_exception_cleans_cache_and_releases(monkeypatch, app, client, user):
    deleted = {}
    released = {}

    async def fake_delete_cached_response(user_id, fingerprint):
        deleted["fingerprint"] = fingerprint
        return True

    async def fake_release_lock(user_id, fingerprint):
        released["fingerprint"] = fingerprint
        return True

    monkeypatch.setattr(
        middleware, "delete_cached_response", fake_delete_cached_response
    )
    monkeypatch.setattr(middleware, "release_lock", fake_release_lock)

    response = client.post("/unexpected", json={"a": 1})

    assert response.status_code == 500
    assert "fingerprint" in deleted["fingerprint"]
    assert "fingerprint" in released["fingerprint"]


def test_skips_for_other_methods(app, user):
    called = {}

    @middleware.idempotent(methods=("POST",))
    async def handler(request: Request, current_user=None):
        called["ran"] = True
        return "ok"

    request = Request(scope={"type": "http", "method": "GET", "path": "/"})
    result = run(handler(request=request, current_user=user))
    assert called["ran"] is True
    assert result == "ok"


def test_skips_when_no_current_user(app):
    called = {}

    @middleware.idempotent()
    async def handler(request: Request, current_user=None):
        called["ran"] = True
        return "ok"

    request = Request(scope={"type": "http", "method": "POST", "path": "/"})
    result = run(handler(request=request))
    assert called["ran"] is True
    assert result == "ok"


def test_create_cached_response_parses_str_body():
    cached = {
        "status_code": 201,
        "headers": {"X": "y"},
        "body": '{"msg": "ok"}',
    }
    resp = middleware._create_cached_response(cached, "fp", "hit")
    assert resp.status_code == 201
    assert resp.headers[IDEMPOTENCY_KEY_HEADER] == "fp"
    assert resp.headers["X"] == "y"
    assert resp.body
    assert __import__("json").loads(resp.body)["msg"] == "ok"


def test_create_cached_response_invalid_json_str():
    cached = {
        "status_code": 200,
        "headers": {},
        "body": "not-json",
    }
    resp = middleware._create_cached_response(cached, "fp", "hit")
    assert resp.status_code == 200
    # JSONResponse wraps string content with quotes
    assert resp.body == b'"not-json"'


def test_add_idempotency_headers_with_response_object():
    resp = Response(content=b"hi", status_code=202)
    out = middleware._add_idempotency_headers(resp, "fp", "miss")
    assert out.headers[IDEMPOTENCY_KEY_HEADER] == "fp"
    assert out.headers[IDEMPOTENCY_STATUS_HEADER] == "miss"


def test_add_idempotency_headers_model_dump():
    class Dummy:
        def model_dump(self, mode="json"):
            return {"v": 1}

    out = middleware._add_idempotency_headers(Dummy(), "fp", "miss")
    assert out.status_code == 200
    assert __import__("json").loads(out.body) == {"v": 1}
    assert out.headers[IDEMPOTENCY_KEY_HEADER] == "fp"


def test_add_idempotency_headers_fallback():
    out = middleware._add_idempotency_headers("hello", "fp", "miss")
    assert out.status_code == 200
    assert __import__("json").loads(out.body) == "hello"


def test_extract_response_data_variants():
    # JSONResponse
    jr = middleware.JSONResponse(content={"a": 1}, status_code=203)
    jr_data = run(middleware._extract_response_data(jr))
    assert jr_data["status_code"] == 203
    assert jr_data["body"] == {"a": 1}

    # Plain Response
    r = Response(content=b"{}", status_code=204)
    r_data = run(middleware._extract_response_data(r))
    assert r_data["status_code"] == 204
    assert r_data["body"] == {}

    # model_dump object
    class Dummy:
        def model_dump(self, mode="json"):
            return {"m": 1}

    md_data = run(middleware._extract_response_data(Dummy()))
    assert md_data["body"] == {"m": 1}

    # dict fallback
    dict_data = run(middleware._extract_response_data({"k": 2}))
    assert dict_data["body"] == {"k": 2}

    # JSONResponse with invalid body to hit except
    jr_bad = middleware.JSONResponse(content={"a": 1}, status_code=206)
    jr_bad.body = b"notjson"
    jr_bad_data = run(middleware._extract_response_data(jr_bad))
    assert jr_bad_data["body"] == "notjson"

    # Response with invalid JSON body to hit except
    r_bad = Response(content=b"notjson", status_code=207)
    r_bad_data = run(middleware._extract_response_data(r_bad))
    assert r_bad_data["body"] == "notjson"

    # fallback else branch
    fallback = run(middleware._extract_response_data(123))
    assert fallback["body"] == 123


def test_wrapper_finds_request_in_args(monkeypatch):
    user = SimpleNamespace(id="u1")

    def fake_compute_fingerprint(user_id: str, path: str, method: str, body: bytes):
        return "fp"

    async def fake_get_cached_response(*_):
        return None

    async def fake_acquire_lock(*_):
        return True

    async def fake_cache_response(*_args, **_kwargs):
        return True

    async def fake_release_lock(*_):
        return True

    monkeypatch.setattr(middleware, "compute_fingerprint", fake_compute_fingerprint)
    monkeypatch.setattr(middleware, "get_cached_response", fake_get_cached_response)
    monkeypatch.setattr(middleware, "acquire_lock", fake_acquire_lock)
    monkeypatch.setattr(middleware, "cache_response", fake_cache_response)
    monkeypatch.setattr(middleware, "release_lock", fake_release_lock)

    async def handler(request: Request, current_user):
        return {"ok": True}

    decorated = middleware.idempotent()(handler)

    async def receive():
        return {"type": "http.request", "body": b"{}", "more_body": False}

    scope = {"type": "http", "method": "POST", "path": "/pos", "headers": []}
    request = Request(scope=scope, receive=receive)

    result = run(decorated(request, user))
    assert result == {"ok": True}
