import os
import sys
import types

# Ensure test environment is set before application/settings import
os.environ.setdefault("ENVIRONMENT", "test")

# Provide a lightweight stub for taskiq_redis so imports succeed
# without the real dependency
if "taskiq_redis" not in sys.modules:
    dummy_module = types.ModuleType("taskiq_redis")

    class _DummyListQueueBroker:
        def __init__(self, *args, **kwargs):
            pass

        def with_result_backend(self, backend):
            return self

        def task(self, *args, **kwargs):
            def decorator(func):
                return func

            return decorator

        async def startup(self):  # pragma: no cover - test helper
            return None

        async def shutdown(self):  # pragma: no cover - test helper
            return None

    class _DummyRedisAsyncResultBackend:
        def __init__(self, *args, **kwargs):
            pass

    dummy_module.ListQueueBroker = _DummyListQueueBroker
    dummy_module.RedisAsyncResultBackend = _DummyRedisAsyncResultBackend
    sys.modules["taskiq_redis"] = dummy_module

# Provide a lightweight stub for supabase so lifecycle imports succeed
if "supabase" not in sys.modules:
    supabase_stub = types.ModuleType("supabase")

    class _DummyAsyncClient: ...

    async def _dummy_create_async_client(*args, **kwargs):
        return _DummyAsyncClient()

    supabase_stub.AsyncClient = _DummyAsyncClient
    supabase_stub.create_async_client = _dummy_create_async_client
    sys.modules["supabase"] = supabase_stub

try:
    from configs.settings import get_settings

    # Refresh cached settings after forcing ENVIRONMENT
    get_settings.cache_clear()
except Exception:
    # If settings are not importable yet, allow tests to proceed
    pass
