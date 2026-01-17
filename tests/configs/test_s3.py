import types

import pytest

from configs import s3


@pytest.fixture(autouse=True)
def reset_s3_globals():
    s3.s3_client = None
    s3.s3_boto_session = None
    yield
    s3.s3_client = None
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
    created_clients = []

    class DummySession:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def client(self, service_name, endpoint_url=None):
            created_clients.append((service_name, endpoint_url))
            return {"service": service_name, "endpoint": endpoint_url}

    monkeypatch.setattr(s3, "get_settings", lambda: settings_stub)
    monkeypatch.setattr(s3.aioboto3, "Session", DummySession)

    await s3.init_s3_session()

    assert s3.s3_client == {"service": "s3", "endpoint": settings_stub.S3_ENDPOINT_URL}
    assert created_clients == [("s3", settings_stub.S3_ENDPOINT_URL)]


@pytest.mark.asyncio
async def test_get_s3_client_raises_when_uninitialized(reset_s3_globals):
    with pytest.raises(RuntimeError, match="S3 Client is not initialized"):
        await s3.get_s3_client()


@pytest.mark.asyncio
async def test_get_s3_client_returns_existing_client(reset_s3_globals):
    dummy = object()
    s3.s3_client = dummy

    result = await s3.get_s3_client()

    assert result is dummy


@pytest.mark.asyncio
async def test_shutdown_s3_session_resets_globals(monkeypatch):
    s3.s3_client = object()
    s3.s3_boto_session = object()

    await s3.shutdown_s3_session()

    assert s3.s3_client is None
    assert s3.s3_boto_session is None
