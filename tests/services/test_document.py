import uuid
from unittest.mock import AsyncMock, Mock

import pytest

from models.document import Document, DocumentStatus
from services.document import (
    create_document_record,
    delete_document,
    delete_s3_file,
    get_document_by_id,
    get_documents_by_user,
    get_s3_presigned_url,
    update_document,
)


@pytest.mark.asyncio
async def test_create_document_record_sets_defaults(monkeypatch):
    session = AsyncMock()
    session.add = Mock()

    document = await create_document_record(
        session=session,
        user_id="user-1",
        filename="resume.pdf",
        file_type="pdf",
        file_size=123,
    )

    session.add.assert_called_once_with(document)
    session.flush.assert_awaited_once()
    session.refresh.assert_awaited_once_with(document)
    assert document.user_id == "user-1"
    assert document.original_filename == "resume.pdf"
    assert document.file_type == "pdf"
    assert document.file_size_bytes == 123
    assert document.status == DocumentStatus.PENDING.value


@pytest.mark.asyncio
async def test_get_document_by_id_returns_scalar(monkeypatch):
    target_doc = Document(
        id=uuid.uuid4(),
        user_id="user-1",
        original_filename="resume.pdf",
        file_type="pdf",
        file_size_bytes=123,
    )

    class FakeResult:
        def scalar_one_or_none(self):
            return target_doc

    session = AsyncMock()
    session.execute.return_value = FakeResult()

    result = await get_document_by_id(session, target_doc.id, "user-1")

    session.execute.assert_awaited_once()
    assert result is target_doc


@pytest.mark.asyncio
async def test_get_documents_by_user_with_status(monkeypatch):
    docs = [
        Document(
            id=uuid.uuid4(),
            user_id="user-1",
            original_filename="resume.pdf",
            file_type="pdf",
            file_size_bytes=123,
            status=DocumentStatus.COMPLETED.value,
        )
    ]

    class FakeScalars:
        def all(self):
            return docs

    class FakeResult:
        def scalars(self):
            return FakeScalars()

    session = AsyncMock()
    session.execute.return_value = FakeResult()

    result = await get_documents_by_user(
        session, user_id="user-1", status=DocumentStatus.COMPLETED
    )

    session.execute.assert_awaited_once()
    assert result == docs


@pytest.mark.asyncio
async def test_update_document_updates_known_fields_only(monkeypatch):
    doc = Document(
        id=uuid.uuid4(),
        user_id="user-1",
        original_filename="resume.pdf",
        file_type="pdf",
        file_size_bytes=123,
        status=DocumentStatus.PENDING.value,
    )
    session = AsyncMock()

    updated = await update_document(
        session,
        doc,
        status=DocumentStatus.COMPLETED.value,
        non_existing="ignored",
    )

    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(doc)
    assert updated.status == DocumentStatus.COMPLETED.value
    assert not hasattr(updated, "non_existing")


@pytest.mark.asyncio
async def test_delete_document_commits(monkeypatch):
    doc = Document(
        id=uuid.uuid4(),
        user_id="user-1",
        original_filename="resume.pdf",
        file_type="pdf",
        file_size_bytes=123,
    )
    session = AsyncMock()

    await delete_document(session, doc)

    session.delete.assert_awaited_once_with(doc)
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_s3_file_success(monkeypatch):
    calls = {}

    class DummyClient:
        async def delete_object(self, Bucket, Key):
            calls["bucket"] = Bucket
            calls["key"] = Key

    class DummyCM:
        def __init__(self, client):
            self.client = client

        async def __aenter__(self):
            return self.client

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class DummySettings:
        S3_BUCKET_NAME = "bucket-name"

    monkeypatch.setattr("services.document.get_settings", lambda: DummySettings())

    async def get_cm():
        return DummyCM(DummyClient())

    monkeypatch.setattr("services.document.get_s3_client", get_cm)

    success = await delete_s3_file("path/to/file")

    assert success is True
    assert calls["bucket"] == "bucket-name"
    assert calls["key"] == "path/to/file"


@pytest.mark.asyncio
async def test_delete_s3_file_handles_exception(monkeypatch):
    class DummySettings:
        S3_BUCKET_NAME = "bucket-name"

    monkeypatch.setattr("services.document.get_settings", lambda: DummySettings())

    async def boom():
        raise RuntimeError("fail")

    monkeypatch.setattr("services.document.get_s3_client", boom)

    success = await delete_s3_file("bad/key")

    assert success is False


@pytest.mark.asyncio
async def test_get_s3_presigned_url_success(monkeypatch):
    class DummyClient:
        async def generate_presigned_url(self, *_args, **_kwargs):
            return "https://presigned"

    class DummyCM:
        def __init__(self, client):
            self.client = client

        async def __aenter__(self):
            return self.client

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class DummySettings:
        S3_BUCKET_NAME = "bucket-name"

    monkeypatch.setattr("services.document.get_settings", lambda: DummySettings())

    async def get_cm():
        return DummyCM(DummyClient())

    monkeypatch.setattr("services.document.get_s3_client", get_cm)

    url = await get_s3_presigned_url("path", expiration=10)

    assert url == "https://presigned"


@pytest.mark.asyncio
async def test_get_s3_presigned_url_handles_exception(monkeypatch):
    class DummySettings:
        S3_BUCKET_NAME = "bucket-name"

    monkeypatch.setattr("services.document.get_settings", lambda: DummySettings())

    async def boom():
        raise RuntimeError("fail")

    monkeypatch.setattr("services.document.get_s3_client", boom)

    url = await get_s3_presigned_url("bad-path")

    assert url is None
