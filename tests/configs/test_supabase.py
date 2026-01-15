from types import SimpleNamespace

import pytest

from configs import supabase


@pytest.fixture(autouse=True)
def reset_supabase_client():
    supabase.supabase_client = None
    yield
    supabase.supabase_client = None


@pytest.mark.asyncio
async def test_init_supabase_client_uses_settings_and_create_client(monkeypatch):
    created = {}

    def fake_get_settings():
        return SimpleNamespace(
            SUPABASE_URL="http://example.com",
            SUPABASE_ANON_KEY="anon-key",
        )

    def fake_create_client(url, key):
        created["url"] = url
        created["key"] = key
        return "client"

    monkeypatch.setattr(supabase, "get_settings", fake_get_settings)
    monkeypatch.setattr(supabase, "create_client", fake_create_client)

    await supabase.init_supabase_client()

    assert supabase.supabase_client == "client"
    assert created == {
        "url": "http://example.com",
        "key": "anon-key",
    }


@pytest.mark.asyncio
async def test_shutdown_supabase_client_sets_none():
    supabase.supabase_client = "client"

    await supabase.shutdown_supabase_client()

    assert supabase.supabase_client is None


@pytest.mark.asyncio
async def test_get_supabase_client_returns_instance():
    supabase.supabase_client = "client"

    result = await supabase.get_supabase_client()

    assert result == "client"


@pytest.mark.asyncio
async def test_get_supabase_client_raises_when_none():
    with pytest.raises(RuntimeError, match="not initialized"):
        await supabase.get_supabase_client()
