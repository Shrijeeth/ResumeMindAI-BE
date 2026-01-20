import logging
import time
from typing import Optional
from uuid import UUID

from litellm import acompletion
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import (
    EventStatus,
    EventType,
    LLMProvider,
    LLMProviderEvent,
    ProviderStatus,
    ProviderType,
)
from services.encryption import decrypt_api_key

logger = logging.getLogger(__name__)

PROVIDER_PREFIX = {
    ProviderType.OPENAI: "openai",
    ProviderType.ANTHROPIC: "anthropic",
    ProviderType.GOOGLE_GEMINI: "gemini",
    ProviderType.AZURE_OPENAI: "azure",
    ProviderType.OLLAMA: "ollama",
    ProviderType.HUGGINGFACE: "huggingface",
    ProviderType.GROQ: "groq",
}


def get_provider_prefix(provider_type: ProviderType | str) -> str | None:
    if isinstance(provider_type, str):
        try:
            provider_type = ProviderType(provider_type)
        except ValueError:
            return None
    return PROVIDER_PREFIX.get(provider_type)


def format_model_name(provider_type: ProviderType | str, model_name: str) -> str:
    prefix = get_provider_prefix(provider_type)
    if provider_type == ProviderType.CUSTOM:
        return model_name
    if prefix:
        return f"{prefix}/{model_name}"
    return model_name


async def get_user_llm_provider(
    session: AsyncSession,
    user_id: str,
    allow_fallback_connected: bool = True,
) -> Optional[LLMProvider]:
    """Fetch user's LLM provider.

    Prefers active connected provider; optionally falls back to any connected provider.
    """

    result = await session.execute(
        select(LLMProvider)
        .where(LLMProvider.user_id == user_id)
        .where(LLMProvider.status == ProviderStatus.CONNECTED.value)
        .where(LLMProvider.is_active)
        .limit(1)
    )
    provider = result.scalar_one_or_none()

    if not provider and allow_fallback_connected:
        result = await session.execute(
            select(LLMProvider)
            .where(LLMProvider.user_id == user_id)
            .where(LLMProvider.status == ProviderStatus.CONNECTED.value)
            .limit(1)
        )
        provider = result.scalar_one_or_none()

    return provider


async def log_provider_event(
    session: AsyncSession,
    user_id: str,
    provider_id: UUID,
    event: EventType,
    event_status: EventStatus,
    message: Optional[str] = None,
) -> None:
    event_log = LLMProviderEvent(
        user_id=user_id,
        provider_id=provider_id,
        event=event,
        status=event_status,
        message=message,
    )
    session.add(event_log)


async def test_provider_connection(
    provider: LLMProvider,
    override_api_key: Optional[str] = None,
    override_base_url: Optional[str] = None,
    override_model_name: Optional[str] = None,
) -> tuple[ProviderStatus, Optional[int], Optional[str]]:
    start_time = time.time()
    try:
        api_key = override_api_key or decrypt_api_key(provider.api_key_encrypted)
        base_url = override_base_url or provider.base_url
        model_name = override_model_name or provider.model_name

        if not api_key:
            return ProviderStatus.ERROR, None, "API key is required"
        if not model_name:
            return ProviderStatus.ERROR, None, "Model name is required"

        formatted_model = format_model_name(provider.provider_type, model_name)

        logger.info(
            f"Testing connection for provider {provider.provider_type} "
            f"with model {formatted_model} at {base_url or 'default endpoint'}"
        )

        await acompletion(
            model=formatted_model,
            messages=[{"role": "system", "content": "ping"}],
            api_key=api_key,
            base_url=base_url or None,
            timeout=10,
        )

        latency_ms = int((time.time() - start_time) * 1000)
        return ProviderStatus.CONNECTED, latency_ms, None
    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        error_message = (
            f"{provider.provider_type} "
            f"({model_name or 'unknown model'}) connection failed"
        )
        logger.error(
            f"Connection test failed for provider {provider.id} "
            f"[{provider.provider_type} - {model_name}]: {e}"
        )
        return ProviderStatus.ERROR, latency_ms, error_message
