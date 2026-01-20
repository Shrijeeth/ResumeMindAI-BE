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


@pytest.mark.asyncio
async def test_classify_document_no_response(monkeypatch):
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
            return None

    monkeypatch.setattr(agent, "get_user_llm_provider", fake_get_provider)
    monkeypatch.setattr(agent, "decrypt_api_key", lambda _enc: "api-key")
    monkeypatch.setattr(agent, "format_model_name", lambda *_args: "model")
    monkeypatch.setattr(agent, "load_prompt", lambda *_args, **__kwargs: "prompt")
    monkeypatch.setattr(
        agent, "create_classifier_agent", lambda **_kwargs: DummyAgent()
    )

    result = await agent.classify_document("text", "file.txt", "user1")

    assert result["document_type"] == DocumentType.UNKNOWN.value
    assert result["confidence"] == 0.0
    assert "no response" in result["reasoning"].lower()


@pytest.mark.asyncio
async def test_classify_document_exception_returns_unknown(monkeypatch):
    async def fake_get_provider(_user):
        return SimpleNamespace(
            api_key_encrypted="enc", provider_type="p", model_name="m", base_url=None
        )

    class DummyAgent:
        async def arun(self, _prompt):
            raise RuntimeError("boom")

    monkeypatch.setattr(agent, "get_user_llm_provider", fake_get_provider)
    monkeypatch.setattr(agent, "decrypt_api_key", lambda _enc: "api-key")
    monkeypatch.setattr(agent, "format_model_name", lambda *_args: "model")
    monkeypatch.setattr(agent, "load_prompt", lambda *_args, **__kwargs: "prompt")
    monkeypatch.setattr(
        agent, "create_classifier_agent", lambda **_kwargs: DummyAgent()
    )

    result = await agent.classify_document("text", "file.txt", "user1")

    assert result["document_type"] == DocumentType.UNKNOWN.value
    assert result["confidence"] == 0.0
    assert "error" in result["reasoning"].lower()


def test_create_classifier_agent_sets_model_kwargs(monkeypatch):
    captured = {}

    class DummyLLM:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    class DummyAgent:
        def __init__(self, **kwargs):
            captured["agent"] = kwargs

    monkeypatch.setattr(agent, "LiteLLM", DummyLLM)
    monkeypatch.setattr(agent, "Agent", DummyAgent)

    _ = agent.create_classifier_agent("model-id", "secret", base_url="http://base")

    assert captured["id"] == "model-id"
    assert captured["api_key"] == "secret"
    assert captured["api_base"] == "http://base"
    assert captured["agent"]["output_schema"] is agent.DocumentClassification


@pytest.mark.asyncio
async def test_get_user_llm_provider_returns_scalar(monkeypatch):
    provider = SimpleNamespace(id=1)

    class DummyResult:
        def scalar_one_or_none(self):
            return provider

    class DummySession:
        async def execute(self, _q):
            return DummyResult()

    class DummyCM:
        def __init__(self, session):
            self.session = session

        async def __aenter__(self):
            return self.session

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(agent, "use_db_session", lambda: DummyCM(DummySession()))

    result = await agent.get_user_llm_provider("u1")

    assert result is provider


@pytest.mark.asyncio
async def test_get_user_llm_provider_falls_back_when_no_active(monkeypatch):
    active_call = {"count": 0}
    fallback_provider = SimpleNamespace(id=2)

    class DummyResultActiveNone:
        def scalar_one_or_none(self):
            active_call["count"] += 1
            return None

    class DummyResultConnected:
        def scalar_one_or_none(self):
            return fallback_provider

    class DummySession:
        def __init__(self):
            self.calls = 0

        async def execute(self, _q):
            self.calls += 1
            if self.calls == 1:
                return DummyResultActiveNone()
            return DummyResultConnected()

    class DummyCM:
        def __init__(self, session):
            self.session = session

        async def __aenter__(self):
            return self.session

        async def __aexit__(self, exc_type, exc, tb):
            return False

    session = DummySession()
    monkeypatch.setattr(agent, "use_db_session", lambda: DummyCM(session))

    result = await agent.get_user_llm_provider("u1")

    assert session.calls == 2
    assert result is fallback_provider
