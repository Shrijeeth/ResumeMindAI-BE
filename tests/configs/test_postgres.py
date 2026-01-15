from types import SimpleNamespace

import pytest

from configs import postgres


@pytest.fixture(autouse=True)
def reset_globals():
    # ensure clean slate before/after each test
    postgres.engine = None
    postgres.SessionLocal = None
    yield
    postgres.engine = None
    postgres.SessionLocal = None


@pytest.mark.parametrize(
    "is_async, expected",
    [
        (True, "postgresql+psycopg_async://u:p@h:1/d"),
        (False, "postgresql+psycopg://u:p@h:1/d"),
    ],
)
def test_get_postgres_url(monkeypatch, is_async, expected):
    def fake_settings():
        return SimpleNamespace(
            POSTGRES_USER="u",
            POSTGRES_PASSWORD="p",
            POSTGRES_HOST="h",
            POSTGRES_PORT=1,
            POSTGRES_DB="d",
        )

    monkeypatch.setattr(postgres, "get_settings", fake_settings)

    assert postgres.get_postgres_url(is_async=is_async) == expected


def test_get_postgres_url_quotes_password(monkeypatch):
    def fake_settings():
        return SimpleNamespace(
            POSTGRES_USER="u",
            POSTGRES_PASSWORD="p@ss word",
            POSTGRES_HOST="h",
            POSTGRES_PORT=1,
            POSTGRES_DB="d",
        )

    monkeypatch.setattr(postgres, "get_settings", fake_settings)

    assert (
        postgres.get_postgres_url(is_async=True)
        == "postgresql+psycopg_async://u:p%40ss%20word@h:1/d"
    )


@pytest.mark.asyncio
async def test_get_db_raises_when_not_initialized():
    with pytest.raises(RuntimeError, match="not initialized"):
        async for _ in postgres.get_db():
            pass


@pytest.mark.asyncio
async def test_get_db_yields_session():
    class DummySession:
        pass

    class DummySessionMaker:
        def __init__(self, session):
            self.session = session

        def __call__(self):
            return self

        async def __aenter__(self):
            return self.session

        async def __aexit__(self, exc_type, exc, tb):
            return False

    fake_session = DummySession()
    postgres.SessionLocal = DummySessionMaker(fake_session)

    result = []
    async for s in postgres.get_db():
        result.append(s)

    assert result == [fake_session]


@pytest.mark.asyncio
async def test_use_db_session_commits_on_success():
    class FakeSession:
        def __init__(self):
            self.committed = False
            self.rolled_back = False

        async def commit(self):
            self.committed = True

        async def rollback(self):
            self.rolled_back = True

    class FakeSessionMaker:
        def __init__(self, session):
            self.session = session

        def __call__(self):
            return self

        async def __aenter__(self):
            return self.session

        async def __aexit__(self, exc_type, exc, tb):
            return False

    fake_session = FakeSession()
    postgres.SessionLocal = FakeSessionMaker(fake_session)

    async with postgres.use_db_session() as session:
        assert session is fake_session

    assert fake_session.committed is True
    assert fake_session.rolled_back is False


@pytest.mark.asyncio
async def test_use_db_session_rolls_back_on_error():
    class FakeSession:
        def __init__(self):
            self.committed = False
            self.rolled_back = False

        async def commit(self):
            self.committed = True

        async def rollback(self):
            self.rolled_back = True

    class FakeSessionMaker:
        def __init__(self, session):
            self.session = session

        def __call__(self):
            return self

        async def __aenter__(self):
            return self.session

        async def __aexit__(self, exc_type, exc, tb):
            return False

    fake_session = FakeSession()
    postgres.SessionLocal = FakeSessionMaker(fake_session)

    class Boom(Exception):
        pass

    with pytest.raises(Boom):
        async with postgres.use_db_session() as session:
            assert session is fake_session
            raise Boom()

    assert fake_session.committed is False
    assert fake_session.rolled_back is True


@pytest.mark.asyncio
async def test_use_db_session_raises_when_not_initialized():
    postgres.SessionLocal = None
    with pytest.raises(RuntimeError, match="not initialized"):
        async with postgres.use_db_session():
            pass


@pytest.mark.asyncio
async def test_init_and_shutdown_engine(monkeypatch):
    created = {}

    def fake_create_engine(**kwargs):
        created.update(kwargs)

        class FakeEngine:
            async def dispose(self):
                created["disposed"] = True

        return FakeEngine()

    def fake_create_async_engine(url, **kwargs):
        return fake_create_engine(url=url, **kwargs)

    monkeypatch.setattr(postgres, "create_async_engine", fake_create_async_engine)

    postgres.init_engine()

    assert postgres.engine is not None
    assert postgres.SessionLocal is not None
    assert created["url"].startswith("postgresql+psycopg_async://")

    await postgres.shutdown_engine()
    assert created.get("disposed") is True
    assert postgres.engine is None
    assert postgres.SessionLocal is None
