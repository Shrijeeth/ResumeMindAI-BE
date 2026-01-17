import pytest
from fastapi.testclient import TestClient

from api import health
from app import app
from configs import get_settings
from middlewares.api_key import require_internal_api_key


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def bypass_internal_api_key(monkeypatch):
    monkeypatch.setenv("INTERNAL_API_KEY", "")

    async def _noop():
        return None

    app.dependency_overrides[require_internal_api_key] = _noop
    for dep in getattr(health.router, "dependencies", []):
        if getattr(dep, "dependency", None):
            app.dependency_overrides[dep.dependency] = _noop
    yield
    app.dependency_overrides.clear()


def test_health_endpoint_returns_status_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_NAME", "TestApp")
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("VERSION", "9.9.9")
    monkeypatch.setenv("INTERNAL_API_KEY", "")

    class DummyResult:
        @staticmethod
        def scalar():
            return 1

    class DummySession:
        async def execute(self, _):
            return DummyResult()

    class DummyCtx:
        async def __aenter__(self):
            return DummySession()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(health, "use_db_session", lambda: DummyCtx())

    async def supabase_ok():
        return object()

    async def redis_ok():
        class DummyRedis:
            async def ping(self):
                return True

        return DummyRedis()

    monkeypatch.setattr(health, "get_supabase_client", supabase_ok)
    monkeypatch.setattr(health, "get_redis_client", redis_ok)

    async def s3_ok():
        class DummyS3:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def get_object(self, Bucket, Key):
                return {"Bucket": Bucket, "Key": Key}

        return DummyS3()

    monkeypatch.setattr(health, "get_s3_client", s3_ok)

    async def falkordb_ok():
        class DummyGraph:
            async def ro_query(self, _query):
                class Resp:
                    result_set = [[1]]

                return Resp()

        class DummyFalkor:
            def select_graph(self, _name):
                return DummyGraph()

        return DummyFalkor()

    monkeypatch.setattr(health, "get_falkordb_client", falkordb_ok)

    client = TestClient(app)
    response = client.get("/api/health/")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "app": "TestApp",
        "environment": "test",
        "version": "9.9.9",
        "database": "ok",
        "supabase": "ok",
        "redis": "ok",
        "s3": "ok",
        "falkordb": "ok",
    }


def test_health_endpoint_handles_db_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_NAME", "TestApp")
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("VERSION", "9.9.9")
    monkeypatch.setenv("INTERNAL_API_KEY", "")

    class FailingCtx:
        async def __aenter__(self):
            raise RuntimeError("boom")

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(health, "use_db_session", lambda: FailingCtx())

    async def supabase_ok():
        return object()

    monkeypatch.setattr(health, "get_supabase_client", supabase_ok)

    async def redis_ok():
        class DummyRedis:
            async def ping(self):
                return True

        return DummyRedis()

    monkeypatch.setattr(health, "get_redis_client", redis_ok)

    client = TestClient(app)
    response = client.get("/api/health/")

    assert response.status_code == 503
    assert response.json()["database"] == "error"


def test_health_endpoint_handles_supabase_not_initialized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_NAME", "TestApp")
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("VERSION", "9.9.9")
    monkeypatch.setenv("INTERNAL_API_KEY", "")

    class DummyResult:
        @staticmethod
        def scalar():
            return 1

    class DummySession:
        async def execute(self, _):
            return DummyResult()

    class DummyCtx:
        async def __aenter__(self):
            return DummySession()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(health, "use_db_session", lambda: DummyCtx())

    async def supabase_none():
        return None

    async def redis_ok():
        class DummyRedis:
            async def ping(self):
                return True

        return DummyRedis()

    monkeypatch.setattr(health, "get_supabase_client", supabase_none)
    monkeypatch.setattr(health, "get_redis_client", redis_ok)

    client = TestClient(app)
    response = client.get("/api/health/")

    assert response.status_code == 503
    assert response.json()["supabase"] == "error"


def test_health_endpoint_handles_falkordb_empty_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_NAME", "TestApp")
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("VERSION", "9.9.9")
    monkeypatch.setenv("INTERNAL_API_KEY", "")

    class DummyResult:
        @staticmethod
        def scalar():
            return 1

    class DummySession:
        async def execute(self, _):
            return DummyResult()

    class DummyCtx:
        async def __aenter__(self):
            return DummySession()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(health, "use_db_session", lambda: DummyCtx())

    async def supabase_ok():
        return object()

    async def redis_ok():
        class DummyRedis:
            async def ping(self):
                return True

        return DummyRedis()

    async def s3_ok():
        class DummyS3:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def get_object(self, Bucket, Key):
                return {"Bucket": Bucket, "Key": Key}

        return DummyS3()

    async def falkordb_empty():
        class DummyGraph:
            async def ro_query(self, _query):
                class Resp:
                    result_set = []

                return Resp()

        class DummyFalkor:
            def select_graph(self, _name):
                return DummyGraph()

        return DummyFalkor()

    monkeypatch.setattr(health, "get_supabase_client", supabase_ok)
    monkeypatch.setattr(health, "get_redis_client", redis_ok)
    monkeypatch.setattr(health, "get_s3_client", s3_ok)
    monkeypatch.setattr(health, "get_falkordb_client", falkordb_empty)

    client = TestClient(app)
    response = client.get("/api/health/")

    assert response.status_code == 503
    body = response.json()
    assert body["falkordb"] == "error"
    assert body["status"] == "ok"


def test_health_endpoint_handles_db_scalar_none(monkeypatch) -> None:
    monkeypatch.setenv("APP_NAME", "TestApp")
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("VERSION", "9.9.9")
    monkeypatch.setenv("INTERNAL_API_KEY", "")

    class DummyResult:
        @staticmethod
        def scalar():
            return None

    class DummySession:
        async def execute(self, _):
            return DummyResult()

    class DummyCtx:
        async def __aenter__(self):
            return DummySession()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    async def supabase_ok():
        return object()

    async def redis_ok():
        class DummyRedis:
            async def ping(self):
                return True

        return DummyRedis()

    monkeypatch.setattr(health, "use_db_session", lambda: DummyCtx())
    monkeypatch.setattr(health, "get_supabase_client", supabase_ok)
    monkeypatch.setattr(health, "get_redis_client", redis_ok)

    client = TestClient(app)
    response = client.get("/api/health/")

    assert response.status_code == 503
    assert response.json()["database"] == "error"


def test_health_endpoint_handles_redis_ping_failure(monkeypatch) -> None:
    monkeypatch.setenv("APP_NAME", "TestApp")
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("VERSION", "9.9.9")
    monkeypatch.setenv("INTERNAL_API_KEY", "")

    class DummyResult:
        @staticmethod
        def scalar():
            return 1

    class DummySession:
        async def execute(self, _):
            return DummyResult()

    class DummyCtx:
        async def __aenter__(self):
            return DummySession()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class BadRedis:
        async def ping(self):
            return False

    async def supabase_ok():
        return object()

    async def redis_bad():
        return BadRedis()

    monkeypatch.setattr(health, "use_db_session", lambda: DummyCtx())
    monkeypatch.setattr(health, "get_supabase_client", supabase_ok)
    monkeypatch.setattr(health, "get_redis_client", redis_bad)

    client = TestClient(app)
    response = client.get("/api/health/")

    assert response.status_code == 503
    assert response.json()["redis"] == "error"


def test_health_endpoint_handles_redis_not_initialized(monkeypatch) -> None:
    monkeypatch.setenv("APP_NAME", "TestApp")
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("VERSION", "9.9.9")
    monkeypatch.setenv("INTERNAL_API_KEY", "")

    class DummyResult:
        @staticmethod
        def scalar():
            return 1

    class DummySession:
        async def execute(self, _):
            return DummyResult()

    class DummyCtx:
        async def __aenter__(self):
            return DummySession()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    async def supabase_ok():
        return object()

    async def redis_none():
        return None

    monkeypatch.setattr(health, "use_db_session", lambda: DummyCtx())
    monkeypatch.setattr(health, "get_supabase_client", supabase_ok)
    monkeypatch.setattr(health, "get_redis_client", redis_none)

    client = TestClient(app)
    response = client.get("/api/health/")

    assert response.status_code == 503
    assert response.json()["redis"] == "error"


def test_health_endpoint_handles_redis_exception(monkeypatch) -> None:
    monkeypatch.setenv("APP_NAME", "TestApp")
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("VERSION", "9.9.9")
    monkeypatch.setenv("INTERNAL_API_KEY", "")

    class DummyResult:
        @staticmethod
        def scalar():
            return 1

    class DummySession:
        async def execute(self, _):
            return DummyResult()

    class DummyCtx:
        async def __aenter__(self):
            return DummySession()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    async def supabase_ok():
        return object()

    async def redis_boom():
        raise RuntimeError("redis down")

    monkeypatch.setattr(health, "use_db_session", lambda: DummyCtx())
    monkeypatch.setattr(health, "get_supabase_client", supabase_ok)
    monkeypatch.setattr(health, "get_redis_client", redis_boom)

    client = TestClient(app)
    response = client.get("/api/health/")

    assert response.status_code == 503
    assert response.json()["redis"] == "error"


def test_health_endpoint_handles_supabase_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_NAME", "TestApp")
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("VERSION", "9.9.9")

    class DummySession:
        async def execute(self, _):
            return None

    class DummyCtx:
        async def __aenter__(self):
            return DummySession()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    async def boom():
        raise RuntimeError("supabase down")

    async def redis_ok():
        class DummyRedis:
            async def ping(self):
                return True

        return DummyRedis()

    monkeypatch.setattr(health, "use_db_session", lambda: DummyCtx())
    monkeypatch.setattr(health, "get_supabase_client", boom)
    monkeypatch.setattr(health, "get_redis_client", redis_ok)

    client = TestClient(app)
    response = client.get("/api/health/")

    assert response.status_code == 503
    assert response.json()["supabase"] == "error"
