from types import SimpleNamespace

import pytest

from agents.document_classifier import agent
from models.document import DocumentType


@pytest.mark.asyncio
async def test_classify_document_no_provider(monkeypatch):
    async def _no_provider(_user):
        return None

    monkeypatch.setattr(agent, "get_user_llm_provider", _no_provider)

    result = await agent.classify_document("text", "file.txt", "user1")

    assert result["document_type"] == DocumentType.UNKNOWN.value
    assert result["confidence"] == 0.0
    assert "No LLM provider" in result["reasoning"]


@pytest.mark.asyncio
async def test_classify_document_returns_result(monkeypatch):
    provider = SimpleNamespace(
        api_key_encrypted="enc",
        provider_type="openai",
        model_name="gpt-4",
        base_url=None,
    )

    async def fake_get_provider(_user):
        return provider

    class DummyAgent:
        def __init__(self, *_, **__):
            pass

        async def arun(self, _prompt):
            return SimpleNamespace(
                content=SimpleNamespace(
                    document_type="resume",
                    confidence=0.9,
                    reasoning="looks like a resume",
                )
            )

    monkeypatch.setattr(agent, "get_user_llm_provider", fake_get_provider)
    monkeypatch.setattr(agent, "decrypt_api_key", lambda _enc: "api-key")
    monkeypatch.setattr(agent, "format_model_name", lambda *_args: "model")
    monkeypatch.setattr(agent, "load_prompt", lambda *_args, **__kwargs: "prompt")
    monkeypatch.setattr(
        agent, "create_classifier_agent", lambda **_kwargs: DummyAgent()
    )

    result = await agent.classify_document("text", "file.txt", "user1")

    assert result == {
        "document_type": "resume",
        "confidence": 0.9,
        "reasoning": "looks like a resume",
    }


@pytest.mark.asyncio
async def test_classify_document_invalid_type_falls_back(monkeypatch):
    provider = SimpleNamespace(
        api_key_encrypted="enc",
        provider_type="openai",
        model_name="gpt-4",
        base_url=None,
    )

    async def fake_get_provider(_user):
        return provider

    class DummyAgent:
        async def arun(self, _prompt):
            return SimpleNamespace(
                content=SimpleNamespace(
                    document_type="unsupported_type",
                    confidence=0.5,
                    reasoning="unknown",
                )
            )

    monkeypatch.setattr(agent, "get_user_llm_provider", fake_get_provider)
    monkeypatch.setattr(agent, "decrypt_api_key", lambda _enc: "api-key")
    monkeypatch.setattr(agent, "format_model_name", lambda *_args: "model")
    monkeypatch.setattr(agent, "load_prompt", lambda *_args, **__kwargs: "prompt")
    monkeypatch.setattr(
        agent, "create_classifier_agent", lambda **_kwargs: DummyAgent()
    )

    result = await agent.classify_document("text", "file.txt", "user1")

    assert result["document_type"] == DocumentType.OTHER.value
    assert result["confidence"] == 0.5
    assert result["reasoning"] == "unknown"
