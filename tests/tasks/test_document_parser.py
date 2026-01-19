import asyncio
import runpy
from types import SimpleNamespace
from uuid import uuid4

import pytest

from models.document import DocumentStatus, DocumentType
from tasks import document_parser


class DummySessionCM:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        return False


class DummyWorkerContext:
    async def __aenter__(self):
        return None

    async def __aexit__(self, exc_type, exc, tb):
        return False


def test_health_server_main_runs_asyncio_run(monkeypatch):
    calls = {}

    def fake_run(coro):
        calls["coro"] = coro

    monkeypatch.setattr(asyncio, "run", fake_run)

    # Execute module as __main__ to hit the guard without actually running the server
    runpy.run_module("tasks.health_server", run_name="__main__")

    assert calls["coro"].__name__ == "run_health_server"


@pytest.mark.asyncio
async def test_update_document_status_sets_fields_and_processed_at(monkeypatch):
    doc = SimpleNamespace(
        id=uuid4(),
        status="pending",
        error_message=None,
        processed_at=None,
        extra=None,
    )

    class FakeResult:
        def scalar_one_or_none(self):
            return doc

    async def execute(_q):
        return FakeResult()

    session = SimpleNamespace(execute=execute)

    monkeypatch.setattr(
        document_parser, "use_db_session", lambda: DummySessionCM(session)
    )

    await document_parser.update_document_status(
        doc.id,
        DocumentStatus.COMPLETED,
        error_message="done",
        extra="value",
    )

    assert doc.status == DocumentStatus.COMPLETED.value
    assert doc.error_message == "done"
    assert doc.extra == "value"
    assert doc.processed_at is not None


@pytest.mark.asyncio
async def test_upload_to_s3_puts_object(monkeypatch):
    calls = {}

    class DummyClient:
        async def put_object(self, **kwargs):
            calls.update(kwargs)

    class DummyCM:
        def __init__(self, client):
            self.client = client

        async def __aenter__(self):
            return self.client

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class DummySettings:
        S3_BUCKET_NAME = "bucket"

    monkeypatch.setattr(document_parser, "get_settings", lambda: DummySettings())

    async def get_client():
        return DummyCM(DummyClient())

    monkeypatch.setattr(document_parser, "get_s3_client", get_client)

    key = await document_parser.upload_to_s3(
        b"content", "user1", "doc1", "file.pdf", "pdf"
    )

    assert key == "users/user1/documents/doc1/file.pdf"
    assert calls["Bucket"] == "bucket"
    assert calls["Key"] == key
    assert calls["Body"] == b"content"
    assert calls["ContentType"] == "application/pdf"


def test_parse_document_to_markdown_uses_markitdown_and_cleans_tmp(monkeypatch):
    captured = {}

    class DummyResult:
        def __init__(self, markdown):
            self.markdown = markdown

    class DummyMD:
        def convert(self, path):
            captured["path"] = path
            return DummyResult("parsed md")

    def fake_unlink(self, missing_ok=False):
        captured["unlinked"] = self
        captured["missing_ok"] = missing_ok

    monkeypatch.setattr(document_parser, "MarkItDown", lambda: DummyMD())
    monkeypatch.setattr(document_parser.Path, "unlink", fake_unlink)

    result = document_parser.parse_document_to_markdown(b"hi", "file.pdf", "pdf")

    assert result == "parsed md"
    assert "path" in captured
    assert "unlinked" in captured
    assert captured["missing_ok"] is True


@pytest.mark.asyncio
async def test_convert_to_graph_ontology_placeholder_logs_and_returns_none():
    result = await document_parser.convert_to_graph_ontology(
        uuid4(), "markdown", DocumentType.RESUME
    )

    assert result == (None, None)


@pytest.mark.asyncio
async def test_parse_document_task_invalid_type(monkeypatch):
    doc = SimpleNamespace(
        id=uuid4(),
        s3_key="key",
        s3_bucket="bucket",
        original_filename="file.pdf",
        file_type="pdf",
    )

    class FakeResult:
        def scalar_one_or_none(self):
            return doc

    class DummyBody:
        async def read(self):
            return b"content"

    class DummyS3Client:
        async def get_object(self, **kwargs):
            return {"Body": DummyBody()}

    class DummyS3CM:
        def __init__(self, client):
            self.client = client

        async def __aenter__(self):
            return self.client

        async def __aexit__(self, exc_type, exc, tb):
            return False

    async def execute(_q):
        return FakeResult()

    session = SimpleNamespace(execute=execute)

    monkeypatch.setattr(
        document_parser, "worker_context", lambda **_: DummyWorkerContext()
    )
    monkeypatch.setattr(
        document_parser, "use_db_session", lambda: DummySessionCM(session)
    )

    async def get_s3_client():
        return DummyS3CM(DummyS3Client())

    monkeypatch.setattr(document_parser, "get_s3_client", get_s3_client)
    monkeypatch.setattr(document_parser, "parse_document_to_markdown", lambda *_: "md")

    update_calls = []

    async def fake_update(doc_id, status, **kwargs):
        update_calls.append((status, kwargs))

    async def fake_classify(**_):
        return {"document_type": "other", "confidence": 0.2}

    monkeypatch.setattr(document_parser, "update_document_status", fake_update)
    monkeypatch.setattr(document_parser, "classify_document", fake_classify)

    result = await document_parser.parse_document_task(str(doc.id), "user1")

    assert result["status"] == "invalid"
    assert update_calls[0][0] == DocumentStatus.VALIDATING
    assert update_calls[-1][0] == DocumentStatus.INVALID


@pytest.mark.asyncio
async def test_parse_document_task_success(monkeypatch):
    doc = SimpleNamespace(
        id=uuid4(),
        s3_key="key",
        s3_bucket="bucket",
        original_filename="file.pdf",
        file_type="pdf",
    )

    class FakeResult:
        def scalar_one_or_none(self):
            return doc

    class DummyBody:
        async def read(self):
            return b"content"

    class DummyS3Client:
        async def get_object(self, **kwargs):
            return {"Body": DummyBody()}

    class DummyS3CM:
        def __init__(self, client):
            self.client = client

        async def __aenter__(self):
            return self.client

        async def __aexit__(self, exc_type, exc, tb):
            return False

    async def execute(_q):
        return FakeResult()

    session = SimpleNamespace(execute=execute)

    monkeypatch.setattr(
        document_parser, "worker_context", lambda **_: DummyWorkerContext()
    )
    monkeypatch.setattr(
        document_parser, "use_db_session", lambda: DummySessionCM(session)
    )

    async def get_s3_client():
        return DummyS3CM(DummyS3Client())

    monkeypatch.setattr(document_parser, "get_s3_client", get_s3_client)
    monkeypatch.setattr(
        document_parser, "parse_document_to_markdown", lambda *_: "md content"
    )

    async def fake_convert_to_graph_ontology(**_):
        return None, None

    monkeypatch.setattr(
        document_parser, "convert_to_graph_ontology", fake_convert_to_graph_ontology
    )

    async def fake_classify(**_):
        return {"document_type": DocumentType.RESUME.value, "confidence": 0.9}

    update_calls = []

    async def fake_update(doc_id, status, **kwargs):
        update_calls.append(status)

    monkeypatch.setattr(document_parser, "classify_document", fake_classify)
    monkeypatch.setattr(document_parser, "update_document_status", fake_update)

    result = await document_parser.parse_document_task(str(doc.id), "user1")

    assert result["status"] == "completed"
    assert result["markdown_length"] == len("md content")
    assert update_calls == [
        DocumentStatus.VALIDATING,
        DocumentStatus.PARSING,
        DocumentStatus.COMPLETED,
    ]


@pytest.mark.asyncio
async def test_parse_document_task_txt_branch(monkeypatch):
    doc = SimpleNamespace(
        id=uuid4(),
        s3_key="key",
        s3_bucket="bucket",
        original_filename="file.txt",
        file_type="txt",
    )

    class FakeResult:
        def scalar_one_or_none(self):
            return doc

    class DummyBody:
        async def read(self):
            return b"text content"

    class DummyS3Client:
        async def get_object(self, **kwargs):
            return {"Body": DummyBody()}

    class DummyS3CM:
        def __init__(self, client):
            self.client = client

        async def __aenter__(self):
            return self.client

        async def __aexit__(self, exc_type, exc, tb):
            return False

    async def execute(_q):
        return FakeResult()

    session = SimpleNamespace(execute=execute)

    monkeypatch.setattr(
        document_parser, "worker_context", lambda **_: DummyWorkerContext()
    )
    monkeypatch.setattr(
        document_parser, "use_db_session", lambda: DummySessionCM(session)
    )

    async def get_s3_client():
        return DummyS3CM(DummyS3Client())

    monkeypatch.setattr(document_parser, "get_s3_client", get_s3_client)

    def fail_parse(*_):
        raise AssertionError("should not parse txt with MarkItDown")

    monkeypatch.setattr(document_parser, "parse_document_to_markdown", fail_parse)

    async def fake_convert(**_):
        return None, None

    monkeypatch.setattr(document_parser, "convert_to_graph_ontology", fake_convert)

    async def fake_classify(**_):
        return {"document_type": DocumentType.RESUME.value, "confidence": 0.8}

    update_calls = []

    async def fake_update(doc_id, status, **kwargs):
        update_calls.append(status)

    monkeypatch.setattr(document_parser, "classify_document", fake_classify)
    monkeypatch.setattr(document_parser, "update_document_status", fake_update)

    result = await document_parser.parse_document_task(str(doc.id), "user1")

    assert result["status"] == "completed"
    assert update_calls == [
        DocumentStatus.VALIDATING,
        DocumentStatus.PARSING,
        DocumentStatus.COMPLETED,
    ]


@pytest.mark.asyncio
async def test_parse_document_task_not_found_sets_failed(monkeypatch):
    class FakeResult:
        def scalar_one_or_none(self):
            return None

    async def execute(_q):
        return FakeResult()

    session = SimpleNamespace(execute=execute)

    monkeypatch.setattr(
        document_parser, "worker_context", lambda **_: DummyWorkerContext()
    )
    monkeypatch.setattr(
        document_parser, "use_db_session", lambda: DummySessionCM(session)
    )

    update_calls = []

    async def fake_update(doc_id, status, **kwargs):
        update_calls.append(status)

    monkeypatch.setattr(document_parser, "update_document_status", fake_update)

    with pytest.raises(ValueError, match="not found"):
        await document_parser.parse_document_task(str(uuid4()), "user1")

    assert update_calls[-1] == DocumentStatus.FAILED
