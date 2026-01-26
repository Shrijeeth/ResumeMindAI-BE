import types
import uuid

import pytest

from models.document import DocumentType
from ontology import graph_processor
from ontology.exceptions import (
    GraphConnectionError,
    GraphProcessingError,
    OntologyExtractionError,
    UnsupportedDocumentTypeError,
)


class DummySettings:
    FALKORDB_HOST = "host"
    FALKORDB_PORT = 1234
    FALKORDB_USERNAME = "user"
    FALKORDB_PASSWORD = "pass"
    GRAPHRAG_ENABLED = True


def make_processor(monkeypatch):
    monkeypatch.setattr(graph_processor, "get_settings", lambda: DummySettings())
    provider = types.SimpleNamespace(provider_type="openai", model_name="gpt4")
    return graph_processor.DocumentGraphProcessor(user_id="user-1", provider=provider)


def test_initialize_invalid_provider(monkeypatch):
    processor = make_processor(monkeypatch)
    monkeypatch.setattr(
        graph_processor,
        "validate_provider_for_graphrag",
        lambda provider: (False, "oops"),
    )

    with pytest.raises(GraphProcessingError):
        processor.initialize()


def test_initialize_success_and_idempotent(monkeypatch):
    processor = make_processor(monkeypatch)
    calls = {}

    monkeypatch.setattr(
        graph_processor,
        "validate_provider_for_graphrag",
        lambda provider: (True, None),
    )
    monkeypatch.setattr(
        graph_processor,
        "create_kg_model_config",
        lambda provider: "cfg",
    )
    monkeypatch.setattr(graph_processor, "build_ontology", lambda: "ontology")

    class FakeKG:
        def __init__(self, **kwargs):
            calls["created"] = kwargs

    monkeypatch.setattr(graph_processor, "KnowledgeGraph", FakeKG)

    processor.initialize()
    assert processor._initialized is True
    assert calls["created"]["name"] == processor.graph_name

    # Second call should short-circuit
    calls.clear()
    processor.initialize()
    assert calls == {}


def test_initialize_wraps_connection_error(monkeypatch):
    processor = make_processor(monkeypatch)
    monkeypatch.setattr(
        graph_processor,
        "validate_provider_for_graphrag",
        lambda provider: (
            True,
            None,
        ),
    )
    monkeypatch.setattr(
        graph_processor,
        "create_kg_model_config",
        lambda provider: "cfg",
    )
    monkeypatch.setattr(
        graph_processor,
        "build_ontology",
        lambda: "ontology",
    )

    def boom(**_):
        raise RuntimeError("fail")

    monkeypatch.setattr(graph_processor, "KnowledgeGraph", boom)

    with pytest.raises(GraphConnectionError):
        processor.initialize()


def test_process_document_requires_initialized(monkeypatch):
    processor = make_processor(monkeypatch)
    with pytest.raises(RuntimeError):
        processor.process_document(uuid.uuid4(), "content", DocumentType.RESUME)


def test_process_document_unsupported_type(monkeypatch):
    processor = make_processor(monkeypatch)
    processor._kg = object()
    with pytest.raises(UnsupportedDocumentTypeError):
        processor.process_document(uuid.uuid4(), "content", DocumentType.OTHER)


def test_process_document_success_with_failed_docs(monkeypatch):
    processor = make_processor(monkeypatch)

    class FakeKG:
        def __init__(self):
            self.failed_documents = ["bad"]

        def process_sources(self, **_):
            return None

    added = {}

    processor._kg = FakeKG()
    monkeypatch.setattr(
        processor,
        "_add_document_node",
        lambda doc_id, document_type: added.update({"called": True}),
    )

    graph_id, ontology_version = processor.process_document(
        uuid.UUID("12345678-1234-5678-1234-567812345678"),
        "markdown",
        DocumentType.RESUME,
    )

    assert added.get("called") is True
    assert ontology_version == graph_processor.ONTOLOGY_VERSION
    assert graph_id.startswith(processor.graph_name)


def test_process_document_raises_on_processing_error(monkeypatch):
    processor = make_processor(monkeypatch)

    class FakeKG:
        failed_documents = []

        def process_sources(self, **_):
            raise RuntimeError("boom")

    processor._kg = FakeKG()

    with pytest.raises(OntologyExtractionError):
        processor.process_document(uuid.uuid4(), "content", DocumentType.RESUME)


def test_add_document_node_handles_errors(monkeypatch):
    processor = make_processor(monkeypatch)
    captured = {}

    class FakeKG:
        def add_node(self, **kwargs):
            captured.update(kwargs)

    processor._kg = FakeKG()

    processor._add_document_node(uuid.uuid4(), DocumentType.RESUME)
    assert captured["entity"] == "Document"
    assert captured["attributes"]["document_type"] == DocumentType.RESUME.value

    class FailingKG:
        def add_node(self, **_):
            raise RuntimeError("fail")

    processor._kg = FailingKG()
    processor._add_document_node(uuid.uuid4(), DocumentType.RESUME)


@pytest.mark.asyncio
async def test_convert_to_graph_disabled(monkeypatch):
    monkeypatch.setattr(
        graph_processor,
        "get_settings",
        lambda: types.SimpleNamespace(GRAPHRAG_ENABLED=False),
    )

    result = await graph_processor.convert_to_graph_ontology(
        uuid.uuid4(),
        "md",
        DocumentType.RESUME,
        "user-1",
    )

    assert result == (None, None)


@pytest.mark.asyncio
async def test_convert_to_graph_provider_lookup_not_configured(monkeypatch):
    monkeypatch.setattr(
        graph_processor,
        "get_settings",
        lambda: types.SimpleNamespace(GRAPHRAG_ENABLED=True),
    )

    class DummySession:
        async def __aenter__(self):
            return "session"

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(graph_processor, "use_db_session", lambda: DummySession())

    async def raise_not_configured(session, user_id):
        raise graph_processor.LLMProviderNotConfiguredError(user_id)

    monkeypatch.setattr(graph_processor, "get_user_llm_provider", raise_not_configured)

    result = await graph_processor.convert_to_graph_ontology(
        uuid.uuid4(),
        "md",
        DocumentType.RESUME,
        "user-1",
    )

    assert result == (None, None)


@pytest.mark.asyncio
async def test_convert_to_graph_handles_provider_not_configured(monkeypatch):
    monkeypatch.setattr(
        graph_processor,
        "get_settings",
        lambda: types.SimpleNamespace(GRAPHRAG_ENABLED=True),
    )

    class DummySession:
        async def __aenter__(self):
            return "session"

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(graph_processor, "use_db_session", lambda: DummySession())

    async def get_provider(session, user_id):
        return None

    monkeypatch.setattr(graph_processor, "get_user_llm_provider", get_provider)

    class FailingProcessor:
        def __init__(self, user_id, provider):
            pass

        def initialize(self):
            raise graph_processor.LLMProviderNotConfiguredError("no provider")

    monkeypatch.setattr(graph_processor, "DocumentGraphProcessor", FailingProcessor)

    result = await graph_processor.convert_to_graph_ontology(
        uuid.uuid4(),
        "md",
        DocumentType.RESUME,
        "user-1",
    )

    assert result == (None, None)


@pytest.mark.asyncio
async def test_convert_to_graph_handles_unexpected_error(monkeypatch):
    monkeypatch.setattr(
        graph_processor,
        "get_settings",
        lambda: types.SimpleNamespace(GRAPHRAG_ENABLED=True),
    )

    class DummySession:
        async def __aenter__(self):
            return "session"

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(graph_processor, "use_db_session", lambda: DummySession())

    async def get_provider(session, user_id):
        return None

    monkeypatch.setattr(graph_processor, "get_user_llm_provider", get_provider)

    class FailingProcessor:
        def __init__(self, user_id, provider):
            pass

        def initialize(self):
            raise RuntimeError("unexpected")

    monkeypatch.setattr(graph_processor, "DocumentGraphProcessor", FailingProcessor)

    result = await graph_processor.convert_to_graph_ontology(
        uuid.uuid4(),
        "md",
        DocumentType.RESUME,
        "user-1",
    )

    assert result == (None, None)


@pytest.mark.asyncio
async def test_convert_to_graph_skips_unsupported_type(monkeypatch):
    monkeypatch.setattr(
        graph_processor,
        "get_settings",
        lambda: types.SimpleNamespace(GRAPHRAG_ENABLED=True),
    )

    result = await graph_processor.convert_to_graph_ontology(
        uuid.uuid4(),
        "md",
        DocumentType.OTHER,
        "user-1",
    )

    assert result == (None, None)


@pytest.mark.asyncio
async def test_convert_to_graph_no_provider(monkeypatch):
    monkeypatch.setattr(
        graph_processor,
        "get_settings",
        lambda: types.SimpleNamespace(GRAPHRAG_ENABLED=True),
    )

    class DummySession:
        async def __aenter__(self):
            return "session"

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(graph_processor, "use_db_session", lambda: DummySession())

    async def get_provider(session, user_id):
        return "provider"

    monkeypatch.setattr(graph_processor, "get_user_llm_provider", get_provider)

    result = await graph_processor.convert_to_graph_ontology(
        uuid.uuid4(),
        "md",
        DocumentType.RESUME,
        "user-1",
    )

    assert result == (None, None)


@pytest.mark.asyncio
async def test_convert_to_graph_success(monkeypatch):
    monkeypatch.setattr(
        graph_processor,
        "get_settings",
        lambda: types.SimpleNamespace(GRAPHRAG_ENABLED=True),
    )

    class DummySession:
        async def __aenter__(self):
            return "session"

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(graph_processor, "use_db_session", lambda: DummySession())

    async def get_provider(session, user_id):
        return "provider"

    monkeypatch.setattr(graph_processor, "get_user_llm_provider", get_provider)

    class FakeProcessor:
        def __init__(self, user_id, provider):
            self.user_id = user_id
            self.provider = provider
            self.initialized = False

        def initialize(self):
            self.initialized = True

        def process_document(self, document_id, markdown_content, document_type):
            return "node-id", "v1"

    monkeypatch.setattr(graph_processor, "DocumentGraphProcessor", FakeProcessor)

    result = await graph_processor.convert_to_graph_ontology(
        uuid.uuid4(),
        "md",
        DocumentType.RESUME,
        "user-1",
    )

    assert result == ("node-id", "v1")


@pytest.mark.asyncio
async def test_convert_to_graph_handles_connection_error(monkeypatch):
    monkeypatch.setattr(
        graph_processor,
        "get_settings",
        lambda: types.SimpleNamespace(GRAPHRAG_ENABLED=True),
    )

    class DummySession:
        async def __aenter__(self):
            return "session"

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(graph_processor, "use_db_session", lambda: DummySession())

    async def get_provider(session, user_id):
        return "provider"

    monkeypatch.setattr(graph_processor, "get_user_llm_provider", get_provider)

    class FailingProcessor:
        def __init__(self, user_id, provider):
            pass

        def initialize(self):
            raise GraphConnectionError("connect fail")

    monkeypatch.setattr(graph_processor, "DocumentGraphProcessor", FailingProcessor)

    result = await graph_processor.convert_to_graph_ontology(
        uuid.uuid4(),
        "md",
        DocumentType.RESUME,
        "user-1",
    )

    assert result == (None, None)
