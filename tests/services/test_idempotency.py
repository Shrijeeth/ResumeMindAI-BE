import json

import pytest

from services import idempotency


class DummyRedis:
    def __init__(self):
        self.last_set = None
        self.last_delete = None
        self.store = {}

    async def set(self, key, value, nx=None, ex=None):
        # Simulate NX behavior if required
        if nx is True and key in self.store:
            return False
        self.store[key] = value
        self.last_set = {"key": key, "value": value, "nx": nx, "ex": ex}
        return True

    async def get(self, key):
        return self.store.get(key)

    async def delete(self, key):
        self.last_delete = key
        self.store.pop(key, None)
        return 1


@pytest.mark.asyncio
async def test_cache_and_lock_key_and_fingerprint():
    user_id = "u1"
    path = "/p"
    method = "POST"
    body = b"data"

    fingerprint = idempotency.compute_fingerprint(user_id, path, method, body)

    assert len(fingerprint) == 32
    assert idempotency._cache_key(user_id, fingerprint).startswith(
        f"{idempotency.IDEMPOTENCY_KEY_PREFIX}:{user_id}:"
    )
    assert idempotency._lock_key(user_id, fingerprint).startswith(
        f"{idempotency.IDEMPOTENCY_KEY_PREFIX}:lock:{user_id}:"
    )
    # deterministic
    assert fingerprint == idempotency.compute_fingerprint(user_id, path, method, body)


@pytest.mark.asyncio
async def test_acquire_lock_true_and_false(monkeypatch):
    redis = DummyRedis()

    async def _get_client():
        return redis

    monkeypatch.setattr(idempotency, "get_redis_client", _get_client)

    # First acquisition succeeds
    ok = await idempotency.acquire_lock("u1", "fp")
    assert ok is True
    # Second with NX should fail
    ok_again = await idempotency.acquire_lock("u1", "fp")
    assert ok_again is False


@pytest.mark.asyncio
async def test_acquire_lock_runtime_error(monkeypatch):
    async def _get_client():
        raise RuntimeError("redis down")

    monkeypatch.setattr(idempotency, "get_redis_client", _get_client)

    ok = await idempotency.acquire_lock("u1", "fp")
    assert ok is True  # graceful degradation


@pytest.mark.asyncio
async def test_acquire_lock_general_exception(monkeypatch):
    async def _get_client():
        raise Exception("boom")

    monkeypatch.setattr(idempotency, "get_redis_client", _get_client)

    ok = await idempotency.acquire_lock("u1", "fp")
    assert ok is True  # general exception branch


@pytest.mark.asyncio
async def test_release_lock_success_and_runtime_error(monkeypatch):
    redis = DummyRedis()

    async def _get_client():
        return redis

    monkeypatch.setattr(idempotency, "get_redis_client", _get_client)

    # Seed lock
    await redis.set(idempotency._lock_key("u1", "fp"), "1")
    ok = await idempotency.release_lock("u1", "fp")
    assert ok is True
    assert redis.last_delete == idempotency._lock_key("u1", "fp")

    async def _get_client_error():
        raise RuntimeError("fail")

    monkeypatch.setattr(idempotency, "get_redis_client", _get_client_error)
    ok_error = await idempotency.release_lock("u1", "fp")
    assert ok_error is False


@pytest.mark.asyncio
async def test_release_lock_general_exception(monkeypatch):
    async def _get_client():
        class Failing:
            async def delete(self, _):
                raise Exception("boom")

        return Failing()

    monkeypatch.setattr(idempotency, "get_redis_client", _get_client)

    ok = await idempotency.release_lock("u1", "fp")
    assert ok is False


@pytest.mark.asyncio
async def test_get_cached_response_hit_miss_and_error(monkeypatch):
    redis = DummyRedis()
    payload = {"hello": "world"}
    key = idempotency._cache_key("u1", "fp")
    redis.store[key] = json.dumps(payload)

    async def _get_client():
        return redis

    monkeypatch.setattr(idempotency, "get_redis_client", _get_client)

    hit = await idempotency.get_cached_response("u1", "fp")
    assert hit == payload

    miss = await idempotency.get_cached_response("u1", "missing")
    assert miss is None

    async def _get_client_error():
        raise RuntimeError("no redis")

    monkeypatch.setattr(idempotency, "get_redis_client", _get_client_error)
    error = await idempotency.get_cached_response("u1", "fp")
    assert error is None


@pytest.mark.asyncio
async def test_get_cached_response_general_exception(monkeypatch):
    async def _get_client():
        class Failing:
            async def get(self, _):
                raise Exception("boom")

        return Failing()

    monkeypatch.setattr(idempotency, "get_redis_client", _get_client)

    result = await idempotency.get_cached_response("u1", "fp")
    assert result is None


@pytest.mark.asyncio
async def test_cache_response_success_and_error(monkeypatch):
    redis = DummyRedis()

    async def _get_client():
        return redis

    monkeypatch.setattr(idempotency, "get_redis_client", _get_client)

    ok = await idempotency.cache_response(
        "u1",
        "fp",
        status_code=200,
        headers={"X": "1"},
        body={"foo": "bar"},
    )

    assert ok is True
    assert redis.last_set["ex"] == idempotency.IDEMPOTENCY_TTL_SECONDS
    stored_payload = json.loads(redis.last_set["value"])
    assert stored_payload["status_code"] == 200
    assert stored_payload["headers"] == {"X": "1"}
    assert stored_payload["body"] == {"foo": "bar"}
    assert "created_at" in stored_payload

    async def _get_client_error():
        raise RuntimeError("redis down")

    monkeypatch.setattr(idempotency, "get_redis_client", _get_client_error)
    ok_error = await idempotency.cache_response(
        "u1", "fp", status_code=500, headers={}, body={}
    )
    assert ok_error is False


@pytest.mark.asyncio
async def test_cache_response_general_exception(monkeypatch):
    async def _get_client():
        class Failing:
            async def set(self, *_, **__):
                raise Exception("boom")

        return Failing()

    monkeypatch.setattr(idempotency, "get_redis_client", _get_client)

    ok = await idempotency.cache_response(
        "u1", "fp", status_code=500, headers={}, body={}
    )
    assert ok is False


@pytest.mark.asyncio
async def test_delete_cached_response_success_and_error(monkeypatch):
    redis = DummyRedis()

    async def _get_client():
        return redis

    monkeypatch.setattr(idempotency, "get_redis_client", _get_client)

    # Seed cache
    await redis.set(idempotency._cache_key("u1", "fp"), "value")

    ok = await idempotency.delete_cached_response("u1", "fp")
    assert ok is True
    assert redis.last_delete == idempotency._cache_key("u1", "fp")

    async def _get_client_error():
        raise RuntimeError("no redis")

    monkeypatch.setattr(idempotency, "get_redis_client", _get_client_error)
    ok_error = await idempotency.delete_cached_response("u1", "fp")
    assert ok_error is False


@pytest.mark.asyncio
async def test_delete_cached_response_general_exception(monkeypatch):
    async def _get_client():
        class Failing:
            async def delete(self, _):
                raise Exception("boom")

        return Failing()

    monkeypatch.setattr(idempotency, "get_redis_client", _get_client)

    ok = await idempotency.delete_cached_response("u1", "fp")
    assert ok is False
