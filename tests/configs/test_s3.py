import types

import pytest

from configs import s3


@pytest.fixture(autouse=True)
def reset_s3_globals():
    s3.s3_boto_session = None
    yield
    s3.s3_boto_session = None


@pytest.fixture
def settings_stub():
    stub = types.SimpleNamespace(
        S3_ACCESS_KEY_ID="key",
        S3_SECRET_ACCESS_KEY="secret",
        S3_ENDPOINT_URL="https://example.com",
    )
    return stub


@pytest.mark.asyncio
async def test_init_s3_session_sets_client(monkeypatch, settings_stub):
    created_sessions = []

    class DummySession:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            created_sessions.append(kwargs)

    monkeypatch.setattr(s3, "get_settings", lambda: settings_stub)
    monkeypatch.setattr(s3.aioboto3, "Session", DummySession)

    await s3.init_s3_session()

    assert isinstance(s3.s3_boto_session, DummySession)
    assert len(created_sessions) == 1
    kwargs = created_sessions[0]
    # Session creation no longer passes endpoint_url; it's applied per client
    assert kwargs.get("endpoint_url") is None
    assert kwargs.get("aws_access_key_id") == settings_stub.S3_ACCESS_KEY_ID
    assert kwargs.get("aws_secret_access_key") == settings_stub.S3_SECRET_ACCESS_KEY


@pytest.mark.asyncio
async def test_get_s3_client_raises_when_uninitialized(reset_s3_globals):
    with pytest.raises(RuntimeError, match="Session is not initialized"):
        await s3.get_s3_client()


@pytest.mark.asyncio
async def test_get_s3_client_returns_existing_client(reset_s3_globals):
    class DummySession:
        def client(self, service_name, endpoint_url=None):
            return {"service": service_name, "endpoint": endpoint_url}

    s3.s3_boto_session = DummySession()

    result = await s3.get_s3_client()

    assert result == {"service": "s3", "endpoint": s3.get_settings().S3_ENDPOINT_URL}


@pytest.mark.asyncio
async def test_shutdown_s3_session_resets_globals(monkeypatch):
    s3.s3_boto_session = object()

    await s3.shutdown_s3_session()

    assert s3.s3_boto_session is None
