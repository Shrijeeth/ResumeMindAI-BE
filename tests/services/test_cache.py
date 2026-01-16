import json
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from models import ProviderStatus
from services import cache


@pytest.fixture
def sample_provider_id():
    return uuid.uuid4()


@pytest.fixture
def sample_cache_payload():
    return {
        "status": "connected",
        "latency_ms": 120,
        "error_message": None,
        "provider": {
            "id": str(uuid.uuid4()),
            "provider_type": "openai",
            "model_name": "gpt-4",
            "base_url": "https://api.openai.com",
            "status": "connected",
            "latency_ms": 120,
            "error_message": None,
            "logo_initials": "OA",
            "logo_color_class": "bg-emerald-500/10",
            "created_at": "2024-01-15T10:30:00",
            "updated_at": "2024-01-15T10:35:00",
        },
    }


class TestCacheKeyGeneration:
    def test_cache_key_format(self, sample_provider_id):
        key = cache._cache_key_provider_test(sample_provider_id)
        assert key == f"cache:provider_test:{sample_provider_id}"


class TestCacheEncoder:
    def test_encodes_datetime(self):
        dt = datetime(2024, 1, 15, 10, 30, 0)
        result = json.dumps({"dt": dt}, cls=cache.CacheEncoder)
        assert "2024-01-15T10:30:00" in result

    def test_encodes_uuid(self):
        uid = uuid.uuid4()
        result = json.dumps({"id": uid}, cls=cache.CacheEncoder)
        assert str(uid) in result

    def test_encodes_enum(self):
        result = json.dumps(
            {"status": ProviderStatus.CONNECTED}, cls=cache.CacheEncoder
        )
        assert "connected" in result

    def test_encoder_returns_enum_value_direct(self):
        encoder = cache.CacheEncoder()
        assert encoder.default(ProviderStatus.ERROR) == ProviderStatus.ERROR.value

    def test_encoder_fallback_raises_type_error(self):
        encoder = cache.CacheEncoder()
        with pytest.raises(TypeError):
            encoder.default(object())


class TestGetProviderTestCache:
    @pytest.mark.asyncio
    async def test_returns_none_on_cache_miss(self, sample_provider_id):
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None

        with patch.object(cache, "get_redis_client", return_value=mock_redis):
            result = await cache.get_provider_test_cache(sample_provider_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_payload_on_cache_hit(
        self, sample_provider_id, sample_cache_payload
    ):
        mock_redis = AsyncMock()
        cached_data = json.dumps(
            {**sample_cache_payload, "cached_at": "2024-01-15T10:35:00"}
        )
        mock_redis.get.return_value = cached_data

        with patch.object(cache, "get_redis_client", return_value=mock_redis):
            result = await cache.get_provider_test_cache(sample_provider_id)

        assert result is not None
        assert result["status"] == "connected"
        assert result["cached_at"] == "2024-01-15T10:35:00"

    @pytest.mark.asyncio
    async def test_returns_none_on_redis_not_initialized(self, sample_provider_id):
        with patch.object(
            cache, "get_redis_client", side_effect=RuntimeError("not initialized")
        ):
            result = await cache.get_provider_test_cache(sample_provider_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_redis_error(self, sample_provider_id):
        mock_redis = AsyncMock()
        mock_redis.get.side_effect = Exception("Connection lost")

        with patch.object(cache, "get_redis_client", return_value=mock_redis):
            result = await cache.get_provider_test_cache(sample_provider_id)

        assert result is None


class TestSetProviderTestCache:
    @pytest.mark.asyncio
    async def test_caches_payload_with_default_ttl(
        self, sample_provider_id, sample_cache_payload
    ):
        mock_redis = AsyncMock()

        with patch.object(cache, "get_redis_client", return_value=mock_redis):
            result = await cache.set_provider_test_cache(
                sample_provider_id, sample_cache_payload
            )

        assert result is True
        mock_redis.set.assert_called_once()
        call_kwargs = mock_redis.set.call_args.kwargs
        assert call_kwargs.get("ex") == cache.PROVIDER_TEST_CACHE_TTL_SECONDS

    @pytest.mark.asyncio
    async def test_adds_cached_at_timestamp(
        self, sample_provider_id, sample_cache_payload
    ):
        mock_redis = AsyncMock()

        with patch.object(cache, "get_redis_client", return_value=mock_redis):
            await cache.set_provider_test_cache(
                sample_provider_id, sample_cache_payload
            )

        call_args = mock_redis.set.call_args.args
        cached_json = call_args[1]
        cached_data = json.loads(cached_json)
        assert "cached_at" in cached_data

    @pytest.mark.asyncio
    async def test_returns_false_on_redis_error(
        self, sample_provider_id, sample_cache_payload
    ):
        mock_redis = AsyncMock()
        mock_redis.set.side_effect = Exception("Connection lost")

        with patch.object(cache, "get_redis_client", return_value=mock_redis):
            result = await cache.set_provider_test_cache(
                sample_provider_id, sample_cache_payload
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_custom_ttl(self, sample_provider_id, sample_cache_payload):
        mock_redis = AsyncMock()

        with patch.object(cache, "get_redis_client", return_value=mock_redis):
            await cache.set_provider_test_cache(
                sample_provider_id, sample_cache_payload, ttl=60
            )

        call_kwargs = mock_redis.set.call_args.kwargs
        assert call_kwargs.get("ex") == 60

    @pytest.mark.asyncio
    async def test_returns_false_on_redis_not_initialized(
        self, sample_provider_id, sample_cache_payload
    ):
        with patch.object(
            cache, "get_redis_client", side_effect=RuntimeError("not initialized")
        ):
            result = await cache.set_provider_test_cache(
                sample_provider_id, sample_cache_payload
            )

        assert result is False


class TestDeleteProviderTestCache:
    @pytest.mark.asyncio
    async def test_deletes_cache_key(self, sample_provider_id):
        mock_redis = AsyncMock()

        with patch.object(cache, "get_redis_client", return_value=mock_redis):
            result = await cache.delete_provider_test_cache(sample_provider_id)

        assert result is True
        expected_key = f"cache:provider_test:{sample_provider_id}"
        mock_redis.delete.assert_called_once_with(expected_key)

    @pytest.mark.asyncio
    async def test_returns_false_on_error(self, sample_provider_id):
        mock_redis = AsyncMock()
        mock_redis.delete.side_effect = Exception("Connection lost")

        with patch.object(cache, "get_redis_client", return_value=mock_redis):
            result = await cache.delete_provider_test_cache(sample_provider_id)

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_redis_not_initialized(self, sample_provider_id):
        with patch.object(
            cache, "get_redis_client", side_effect=RuntimeError("not initialized")
        ):
            result = await cache.delete_provider_test_cache(sample_provider_id)

        assert result is False
