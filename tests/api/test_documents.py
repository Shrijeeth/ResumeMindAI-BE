import io
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from starlette.datastructures import UploadFile

from api import documents
from models.document import DocumentStatus


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
async def test_get_document_status_not_found(monkeypatch):
    async def fake_get_doc(session, doc_id, user_id):
        return None

    monkeypatch.setattr(documents, "get_document_by_id", fake_get_doc)

    with pytest.raises(HTTPException) as exc:
        await documents.get_document_status(uuid.uuid4(), SimpleNamespace(id="u"), None)

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_list_documents_invalid_status_filter(monkeypatch):
    with pytest.raises(HTTPException) as exc:
        await documents.list_documents(
            SimpleNamespace(id="u"), None, status_filter="bad", limit=10, offset=0
        )

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_get_document_not_found(monkeypatch):
    async def fake_get_doc(session, doc_id, user_id):
        return None

    monkeypatch.setattr(documents, "get_document_by_id", fake_get_doc)

    with pytest.raises(HTTPException) as exc:
        await documents.get_document(uuid.uuid4(), SimpleNamespace(id="u"), None)

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_document_not_found(monkeypatch):
    async def fake_get_doc(session, doc_id, user_id):
        return None

    monkeypatch.setattr(documents, "get_document_by_id", fake_get_doc)

    with pytest.raises(HTTPException) as exc:
        await documents.delete_document(uuid.uuid4(), SimpleNamespace(id="u"), None)

    assert exc.value.status_code == 404
