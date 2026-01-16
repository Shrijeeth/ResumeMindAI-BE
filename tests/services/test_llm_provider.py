import enum
import uuid
from unittest.mock import AsyncMock

import pytest

from models import LLMProvider, ProviderStatus, ProviderType
from services import llm_provider


@pytest.mark.asyncio
async def test_test_provider_connection_success(monkeypatch):
    provider = LLMProvider(
        id=uuid.uuid4(),
        user_id="user-1",
        provider_type=ProviderType.OPENAI,
        model_name="gpt-4-turbo",
        base_url="https://api.openai.com",
        api_key_encrypted=b"encrypted",
        status=ProviderStatus.INACTIVE,
    )

    def fake_decrypt(_):
        return "sk-test"

    async_acompletion = AsyncMock()

    monkeypatch.setattr(llm_provider, "decrypt_api_key", fake_decrypt)
    monkeypatch.setattr(llm_provider, "acompletion", async_acompletion)

    status, latency_ms, error = await llm_provider.test_provider_connection(provider)

    async_acompletion.assert_awaited_once()
    assert status == ProviderStatus.CONNECTED
    assert latency_ms is not None
    assert error is None


@pytest.mark.asyncio
async def test_test_provider_connection_missing_api_key(monkeypatch):
    provider = LLMProvider(
        id=uuid.uuid4(),
        user_id="user-1",
        provider_type=ProviderType.OPENAI,
        model_name="gpt-4-turbo",
        base_url=None,
        api_key_encrypted=b"",
        status=ProviderStatus.INACTIVE,
    )

    def fake_decrypt(_):
        return ""

    monkeypatch.setattr(llm_provider, "decrypt_api_key", fake_decrypt)

    status, latency_ms, error = await llm_provider.test_provider_connection(provider)

    assert status == ProviderStatus.ERROR
    assert latency_ms is None
    assert error == "API key is required"


@pytest.mark.asyncio
async def test_test_provider_connection_missing_model(monkeypatch):
    provider = LLMProvider(
        id=uuid.uuid4(),
        user_id="user-1",
        provider_type=ProviderType.OPENAI,
        model_name="",
        base_url=None,
        api_key_encrypted=b"encrypted",
        status=ProviderStatus.INACTIVE,
    )

    def fake_decrypt(_):
        return "sk-test"

    monkeypatch.setattr(llm_provider, "decrypt_api_key", fake_decrypt)

    status, latency_ms, error = await llm_provider.test_provider_connection(provider)

    assert status == ProviderStatus.ERROR
    assert latency_ms is None
    assert error == "Model name is required"


@pytest.mark.asyncio
async def test_test_provider_connection_exception(monkeypatch):
    provider = LLMProvider(
        id=uuid.uuid4(),
        user_id="user-1",
        provider_type=ProviderType.OPENAI,
        model_name="gpt-4",
        base_url="https://api.openai.com",
        api_key_encrypted=b"encrypted",
        status=ProviderStatus.INACTIVE,
    )

    def fake_decrypt(_):
        return "sk-test"

    async def boom(**_):
        raise RuntimeError("fail")

    monkeypatch.setattr(llm_provider, "decrypt_api_key", fake_decrypt)
    monkeypatch.setattr(llm_provider, "acompletion", boom)

    status, latency_ms, error = await llm_provider.test_provider_connection(provider)

    assert status == ProviderStatus.ERROR
    assert latency_ms is not None
    assert "connection failed" in error


def test_format_model_name_with_prefix():
    assert (
        llm_provider.format_model_name(ProviderType.OPENAI, "gpt-4") == "openai/gpt-4"
    )
    assert llm_provider.format_model_name("anthropic", "claude") == "anthropic/claude"
    assert llm_provider.format_model_name(ProviderType.CUSTOM, "my-model") == "my-model"


def test_get_provider_prefix_invalid_string_returns_none():
    assert llm_provider.get_provider_prefix("not-a-provider") is None


def test_format_model_name_without_prefix():
    class UnknownProvider(str, enum.Enum):
        UNKNOWN = "unknown-provider"

    assert (
        llm_provider.format_model_name(UnknownProvider.UNKNOWN.value, "foo-model")
        == "foo-model"
    )
