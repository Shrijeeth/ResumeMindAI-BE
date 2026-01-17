from unittest.mock import AsyncMock, MagicMock

import pytest

from configs import lifecycle


@pytest.mark.asyncio
async def test_startup_all_calls_all_services(monkeypatch):
    init_engine = MagicMock()
    init_supabase = AsyncMock()
    init_redis = AsyncMock()
    init_s3 = AsyncMock()
    init_falkor = AsyncMock()

    monkeypatch.setattr(lifecycle, "init_engine", init_engine)
    monkeypatch.setattr(lifecycle, "init_supabase_client", init_supabase)
    monkeypatch.setattr(lifecycle, "init_redis_client", init_redis)
    monkeypatch.setattr(lifecycle, "init_s3_session", init_s3)
    monkeypatch.setattr(lifecycle, "init_falkordb_client", init_falkor)

    await lifecycle.startup_all()

    init_engine.assert_called_once()
    init_supabase.assert_awaited_once()
    init_redis.assert_awaited_once()
    init_s3.assert_awaited_once()
    init_falkor.assert_awaited_once()


@pytest.mark.asyncio
async def test_shutdown_all_calls_all_services(monkeypatch):
    shutdown_engine = AsyncMock()
    shutdown_supabase = AsyncMock()
    shutdown_redis = AsyncMock()
    shutdown_s3 = AsyncMock()
    shutdown_falkor = AsyncMock()

    monkeypatch.setattr(lifecycle, "shutdown_engine", shutdown_engine)
    monkeypatch.setattr(lifecycle, "shutdown_supabase_client", shutdown_supabase)
    monkeypatch.setattr(lifecycle, "shutdown_redis_client", shutdown_redis)
    monkeypatch.setattr(lifecycle, "shutdown_s3_session", shutdown_s3)
    monkeypatch.setattr(lifecycle, "shutdown_falkordb_client", shutdown_falkor)

    await lifecycle.shutdown_all()

    shutdown_engine.assert_awaited_once()
    shutdown_supabase.assert_awaited_once()
    shutdown_redis.assert_awaited_once()
    shutdown_s3.assert_awaited_once()
    shutdown_falkor.assert_awaited_once()


@pytest.mark.asyncio
async def test_app_lifespan_runs_startup_and_shutdown(monkeypatch):
    startup = AsyncMock()
    shutdown = AsyncMock()
    monkeypatch.setattr(lifecycle, "startup_all", startup)
    monkeypatch.setattr(lifecycle, "shutdown_all", shutdown)

    async with lifecycle.app_lifespan():
        startup.assert_awaited_once()
        shutdown.assert_not_called()

    shutdown.assert_awaited_once()


@pytest.mark.asyncio
async def test_worker_context_initializes_and_tears_down_all(monkeypatch):
    events = []

    def init_engine():
        events.append("init_engine")

    async def init_redis_client():
        events.append("init_redis")

    async def init_supabase_client():
        events.append("init_supabase")

    async def init_s3_session():
        events.append("init_s3")

    async def init_falkordb_client():
        events.append("init_falkor")

    async def shutdown_falkordb_client():
        events.append("shutdown_falkor")

    async def shutdown_s3_session():
        events.append("shutdown_s3")

    async def shutdown_supabase_client():
        events.append("shutdown_supabase")

    async def shutdown_redis_client():
        events.append("shutdown_redis")

    async def shutdown_engine():
        events.append("shutdown_engine")

    monkeypatch.setattr(lifecycle, "init_engine", init_engine)
    monkeypatch.setattr(lifecycle, "init_redis_client", init_redis_client)
    monkeypatch.setattr(lifecycle, "init_supabase_client", init_supabase_client)
    monkeypatch.setattr(lifecycle, "init_s3_session", init_s3_session)
    monkeypatch.setattr(lifecycle, "init_falkordb_client", init_falkordb_client)
    monkeypatch.setattr(lifecycle, "shutdown_falkordb_client", shutdown_falkordb_client)
    monkeypatch.setattr(lifecycle, "shutdown_s3_session", shutdown_s3_session)
    monkeypatch.setattr(lifecycle, "shutdown_supabase_client", shutdown_supabase_client)
    monkeypatch.setattr(lifecycle, "shutdown_redis_client", shutdown_redis_client)
    monkeypatch.setattr(lifecycle, "shutdown_engine", shutdown_engine)

    async with lifecycle.worker_context(
        postgres=True, redis=True, supabase=True, s3=True, falkordb=True
    ):
        events.append("inside")

    assert events == [
        "init_engine",
        "init_redis",
        "init_supabase",
        "init_s3",
        "init_falkor",
        "inside",
        "shutdown_falkor",
        "shutdown_s3",
        "shutdown_supabase",
        "shutdown_redis",
        "shutdown_engine",
    ]
