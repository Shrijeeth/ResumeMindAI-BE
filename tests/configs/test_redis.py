import pytest

from configs import redis


@pytest.fixture(autouse=True)
def reset_client():
    redis.redis_client = None
    yield
    redis.redis_client = None


@pytest.mark.asyncio
async def test_get_redis_client_raises_when_not_initialized():
    with pytest.raises(RuntimeError, match="not initialized"):
        await redis.get_redis_client()


@pytest.mark.asyncio
async def test_shutdown_closes_client(monkeypatch):
    closed = {}

    class DummyRedis:
        async def close(self):
            closed["called"] = True

    redis.redis_client = DummyRedis()

    await redis.shutdown_redis_client()

    assert closed == {"called": True}
    assert redis.redis_client is None


@pytest.mark.asyncio
async def test_init_redis_client_sets_instance(monkeypatch):
    created = {}

    def fake_get_settings():
        return type("S", (), {"REDIS_URL": "redis://localhost:6379/0"})

    class DummyRedis:
        def __init__(self, url, max_connections, decode_responses):
            created["url"] = url
            created["max_connections"] = max_connections
            created["decode_responses"] = decode_responses

        async def close(self):
            created["closed"] = True

    def fake_from_url(url, max_connections, decode_responses):
        return DummyRedis(url, max_connections, decode_responses)

    monkeypatch.setattr(redis, "get_settings", fake_get_settings)
    monkeypatch.setattr(redis.redis.Redis, "from_url", staticmethod(fake_from_url))
    redis.redis_client = None

    await redis.init_redis_client()

    assert isinstance(redis.redis_client, DummyRedis)
    assert created == {
        "url": "redis://localhost:6379/0",
        "max_connections": 20,
        "decode_responses": True,
    }
    # clean up
    redis.redis_client = None


@pytest.mark.asyncio
async def test_get_redis_client_returns_existing(monkeypatch):
    class DummyRedis:
        pass

    dummy = DummyRedis()
    redis.redis_client = dummy

    result = await redis.get_redis_client()

    assert result is dummy
