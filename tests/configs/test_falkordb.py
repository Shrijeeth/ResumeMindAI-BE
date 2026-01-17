import types

import pytest

from configs import falkordb


@pytest.fixture(autouse=True)
def reset_client():
    falkordb.falkordb_client = None
    yield
    falkordb.falkordb_client = None


@pytest.fixture
def settings_stub():
    return types.SimpleNamespace(
        FALKORDB_HOST="host",
        FALKORDB_PORT=1234,
        FALKORDB_USERNAME="user",
        FALKORDB_PASSWORD="pass",
    )


@pytest.mark.asyncio
async def test_init_falkordb_client(monkeypatch, settings_stub):
    created_args = {}

    class DummyFalkor:
        def __init__(self, host, port, username, password):
            created_args.update(
                {"host": host, "port": port, "username": username, "password": password}
            )

        class Connection:
            async def close(self, _force):
                return None

        @property
        def connection(self):
            return self.Connection()

        def select_graph(self, _name):
            return None

    monkeypatch.setattr(falkordb, "get_settings", lambda: settings_stub)
    monkeypatch.setattr(falkordb, "FalkorDB", DummyFalkor)

    await falkordb.init_falkordb_client()

    assert created_args == {
        "host": "host",
        "port": 1234,
        "username": "user",
        "password": "pass",
    }
    assert isinstance(falkordb.falkordb_client, DummyFalkor)


@pytest.mark.asyncio
async def test_get_falkordb_client_returns_instance():
    sentinel = object()
    falkordb.falkordb_client = sentinel

    result = await falkordb.get_falkordb_client()

    assert result is sentinel


@pytest.mark.asyncio
async def test_get_falkordb_client_raises_when_uninitialized(reset_client):
    with pytest.raises(RuntimeError, match="not initialized"):
        await falkordb.get_falkordb_client()


@pytest.mark.asyncio
async def test_shutdown_falkordb_client_closes_and_resets(monkeypatch):
    closed = {}

    class DummyConn:
        async def close(self, force):
            closed["force"] = force

    class DummyClient:
        connection = DummyConn()

    falkordb.falkordb_client = DummyClient()

    await falkordb.shutdown_falkordb_client()

    assert closed == {"force": True}
    assert falkordb.falkordb_client is None
