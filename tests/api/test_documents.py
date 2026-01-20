import io
import uuid
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from starlette.datastructures import UploadFile

from api import documents
from models.document import DocumentStatus, DocumentType


def test_validate_file_extension_invalid_filename():
    with pytest.raises(HTTPException) as exc:
        documents.validate_file_extension("nofile")

    assert exc.value.status_code == 400


def test_validate_file_extension_unsupported():
    with pytest.raises(HTTPException) as exc:
        documents.validate_file_extension("file.exe")

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_upload_document_success(monkeypatch):
    doc_id = uuid.uuid4()
    user_id = "user-1"
    file_bytes = b"hello"

    class DummySettings:
        S3_BUCKET_NAME = "bucket"

    class DummyS3Client:
        def __init__(self):
            self.calls = {}

        async def put_object(self, **kwargs):
            self.calls = kwargs

    class DummyCM:
        def __init__(self, client):
            self.client = client

        async def __aenter__(self):
            return self.client

        async def __aexit__(self, exc_type, exc, tb):
            return False

    document = SimpleNamespace(id=doc_id, task_id=None)

    async def fake_create_document_record(**_):
        return document

    async def get_s3_client():
        return DummyCM(DummyS3Client())

    class DummyTask:
        task_id = "task-123"

    class DummyParseTask:
        @staticmethod
        async def kiq(**_):
            return DummyTask()

    session = SimpleNamespace(commit=AsyncMock(), rollback=AsyncMock())

    monkeypatch.setattr(documents, "get_settings", lambda: DummySettings())
    monkeypatch.setattr(documents, "get_s3_client", get_s3_client)
    monkeypatch.setattr(
        documents, "create_document_record", fake_create_document_record
    )
    monkeypatch.setattr(documents, "parse_document_task", DummyParseTask)

    upload = UploadFile(filename="resume.pdf", file=io.BytesIO(file_bytes))

    resp = await documents.upload_document(upload, SimpleNamespace(id=user_id), session)

    assert resp.document_id == doc_id
    assert resp.task_id == "task-123"
    assert resp.status == DocumentStatus.PENDING


@pytest.mark.asyncio
async def test_upload_document_too_large(monkeypatch):
    monkeypatch.setattr(documents, "MAX_FILE_SIZE_BYTES", 1)
    upload = UploadFile(filename="resume.pdf", file=io.BytesIO(b"1234"))

    with pytest.raises(HTTPException) as exc:
        await documents.upload_document(upload, SimpleNamespace(id="u"), None)

    assert exc.value.status_code == 413


@pytest.mark.asyncio
async def test_upload_document_empty(monkeypatch):
    upload = UploadFile(filename="resume.pdf", file=io.BytesIO(b""))

    with pytest.raises(HTTPException) as exc:
        await documents.upload_document(upload, SimpleNamespace(id="u"), None)

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_upload_document_rollback_on_exception(monkeypatch):
    upload = UploadFile(filename="resume.pdf", file=io.BytesIO(b"hi"))

    async def fail_create_document_record(**_):
        raise RuntimeError("boom")

    session = SimpleNamespace(commit=AsyncMock(), rollback=AsyncMock())

    monkeypatch.setattr(
        documents, "create_document_record", fail_create_document_record
    )

    with pytest.raises(HTTPException) as exc:
        await documents.upload_document(upload, SimpleNamespace(id="u"), session)

    session.rollback.assert_awaited()
    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_get_document_status_not_found(monkeypatch):
    async def fake_get_doc(session, doc_id, user_id):
        return None

    monkeypatch.setattr(documents, "get_document_by_id", fake_get_doc)

    with pytest.raises(HTTPException) as exc:
        await documents.get_document_status(uuid.uuid4(), SimpleNamespace(id="u"), None)

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_document_status_success(monkeypatch):
    now = datetime.utcnow()
    doc = SimpleNamespace(
        id=uuid.uuid4(),
        status=DocumentStatus.PARSING.value,
        document_type=DocumentType.RESUME.value,
        classification_confidence=0.8,
        error_message=None,
        created_at=now,
        updated_at=now,
        processed_at=None,
    )

    async def fake_get_doc(session, doc_id, user_id):
        return doc

    monkeypatch.setattr(documents, "get_document_by_id", fake_get_doc)

    resp = await documents.get_document_status(
        uuid.uuid4(), SimpleNamespace(id="u"), None
    )

    assert resp.status == DocumentStatus.PARSING
    assert resp.document_type == DocumentType.RESUME


@pytest.mark.asyncio
async def test_list_documents_invalid_status_filter(monkeypatch):
    with pytest.raises(HTTPException) as exc:
        await documents.list_documents(
            SimpleNamespace(id="u"), None, status_filter="bad", limit=10, offset=0
        )

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_list_documents_success(monkeypatch):
    now = datetime.utcnow()
    doc = SimpleNamespace(
        id=uuid.uuid4(),
        original_filename="f.pdf",
        file_type="pdf",
        document_type=DocumentType.RESUME.value,
        status=DocumentStatus.PENDING.value,
        created_at=now,
    )

    class DummyScalars:
        def all(self):
            return [doc]

    class DummyResult:
        def scalars(self):
            return DummyScalars()

    class DummySession:
        async def execute(self, _q):
            return DummyResult()

    result = await documents.list_documents(
        SimpleNamespace(id="u"),
        DummySession(),
        status_filter=None,
        limit=10,
        offset=0,
    )

    assert len(result) == 1
    assert result[0].document_type == DocumentType.RESUME.value


@pytest.mark.asyncio
async def test_list_documents_with_status_filter(monkeypatch):
    now = datetime.utcnow()
    doc = SimpleNamespace(
        id=uuid.uuid4(),
        original_filename="f.pdf",
        file_type="pdf",
        document_type=DocumentType.RESUME.value,
        status=DocumentStatus.COMPLETED.value,
        created_at=now,
    )

    class DummyScalars:
        def all(self):
            return [doc]

    class DummyResult:
        def scalars(self):
            return DummyScalars()

    class DummySession:
        async def execute(self, query):
            self.query = query
            return DummyResult()

    session = DummySession()

    result = await documents.list_documents(
        SimpleNamespace(id="u"),
        session,
        status_filter=DocumentStatus.COMPLETED.value,
        limit=5,
        offset=0,
    )

    assert len(result) == 1
    assert result[0].status == DocumentStatus.COMPLETED.value
    assert hasattr(session, "query")


@pytest.mark.asyncio
async def test_get_document_not_found(monkeypatch):
    async def fake_get_doc(session, doc_id, user_id):
        return None

    monkeypatch.setattr(documents, "get_document_by_id", fake_get_doc)

    with pytest.raises(HTTPException) as exc:
        await documents.get_document(uuid.uuid4(), SimpleNamespace(id="u"), None)

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_document_success(monkeypatch):
    now = datetime.utcnow()
    doc = SimpleNamespace(
        id=uuid.uuid4(),
        original_filename="f.pdf",
        file_type="pdf",
        file_size_bytes=1,
        document_type=DocumentType.RESUME.value,
        classification_confidence=0.8,
        markdown_content="# md",
        status=DocumentStatus.COMPLETED.value,
        error_message=None,
        s3_key="k",
        created_at=now,
        updated_at=now,
        processed_at=now,
    )

    async def fake_get_doc(session, doc_id, user_id):
        return doc

    monkeypatch.setattr(documents, "get_document_by_id", fake_get_doc)

    resp = await documents.get_document(uuid.uuid4(), SimpleNamespace(id="u"), None)

    assert resp.document_type == DocumentType.RESUME.value
    assert resp.status == DocumentStatus.COMPLETED.value


@pytest.mark.asyncio
async def test_delete_document_not_found(monkeypatch):
    async def fake_get_doc(session, doc_id, user_id):
        return None

    monkeypatch.setattr(documents, "get_document_by_id", fake_get_doc)

    with pytest.raises(HTTPException) as exc:
        await documents.delete_document(uuid.uuid4(), SimpleNamespace(id="u"), None)

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_document_success(monkeypatch):
    doc = SimpleNamespace(id=uuid.uuid4(), s3_key="k")

    async def fake_get_doc(session_param, doc_id, user_id):
        return doc

    delete_calls = {}

    async def fake_delete_s3_file(key):
        delete_calls["key"] = key

    session = SimpleNamespace(
        delete=AsyncMock(), commit=AsyncMock(), rollback=AsyncMock()
    )

    monkeypatch.setattr(documents, "get_document_by_id", fake_get_doc)
    monkeypatch.setattr(documents, "delete_s3_file", fake_delete_s3_file)

    await documents.delete_document(uuid.uuid4(), SimpleNamespace(id="u"), session)

    assert delete_calls["key"] == "k"
    session.delete.assert_awaited_with(doc)
    session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_delete_document_s3_failure(monkeypatch):
    doc = SimpleNamespace(id=uuid.uuid4(), s3_key="k")

    async def fake_get_doc(session_param, doc_id, user_id):
        return doc

    async def failing_delete_s3_file(_key):
        raise RuntimeError("s3 error")

    session = SimpleNamespace(
        delete=AsyncMock(), commit=AsyncMock(), rollback=AsyncMock()
    )

    monkeypatch.setattr(documents, "get_document_by_id", fake_get_doc)
    monkeypatch.setattr(documents, "delete_s3_file", failing_delete_s3_file)

    with pytest.raises(HTTPException) as exc:
        await documents.delete_document(uuid.uuid4(), SimpleNamespace(id="u"), session)

    session.rollback.assert_awaited()
    assert exc.value.status_code == 500
