from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from middlewares import auth


@pytest.mark.asyncio
async def test_get_current_user_returns_user(monkeypatch):
    creds = SimpleNamespace(credentials="token")

    class FakeAuth:
        @staticmethod
        async def get_user(token):
            assert token == "token"
            return SimpleNamespace(user="user_obj")

    class FakeSupabase:
        auth = FakeAuth()

    async def fake_get_supabase_client():
        return FakeSupabase()

    monkeypatch.setattr(auth, "get_supabase_client", fake_get_supabase_client)

    result = await auth.get_current_user(credentials=creds)

    assert result == "user_obj"


@pytest.mark.asyncio
async def test_get_current_user_raises_on_error(monkeypatch):
    creds = SimpleNamespace(credentials="bad-token")

    class FakeAuth:
        @staticmethod
        async def get_user(_token):
            raise RuntimeError("boom")

    class FakeSupabase:
        auth = FakeAuth()

    async def fake_get_supabase_client():
        return FakeSupabase()

    monkeypatch.setattr(auth, "get_supabase_client", fake_get_supabase_client)

    with pytest.raises(HTTPException) as excinfo:
        await auth.get_current_user(credentials=creds)

    assert excinfo.value.status_code == 401
    assert excinfo.value.detail == "Invalid authentication credentials"
