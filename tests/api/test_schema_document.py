from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

from api.schemas.document import DocumentListItem, DocumentOut, DocumentStatusResponse
from models.document import DocumentStatus, DocumentType, FileType


def test_document_status_response_from_orm_model_maps_fields_and_progress():
    now = datetime.utcnow()
    doc = SimpleNamespace(
        id=uuid4(),
        status=DocumentStatus.VALIDATING.value,
        document_type=DocumentType.UNKNOWN.value,
        classification_confidence=0.9,
        error_message=None,
        created_at=now,
        updated_at=now,
        processed_at=None,
    )

    resp = DocumentStatusResponse.from_orm_model(doc)

    assert resp.document_id == doc.id
    assert resp.status == DocumentStatus.VALIDATING
    assert resp.document_type is None  # UNKNOWN should map to None
    assert resp.classification_confidence == 0.9
    assert resp.progress_message == "Validating document type with AI"


def test_document_out_validators_accept_enums():
    dto = DocumentOut(
        id=uuid4(),
        original_filename="resume.pdf",
        file_type=FileType.PDF,
        file_size_bytes=123,
        document_type=DocumentType.RESUME,
        classification_confidence=0.8,
        markdown_content="# md",
        status=DocumentStatus.PARSING,
        error_message=None,
        s3_key="key",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        processed_at=None,
    )

    assert dto.file_type == FileType.PDF.value
    assert dto.document_type == DocumentType.RESUME.value
    assert dto.status == DocumentStatus.PARSING.value


def test_document_out_from_orm_model_maps_fields():
    now = datetime.utcnow()
    doc = SimpleNamespace(
        id=uuid4(),
        original_filename="cv.docx",
        file_type="docx",
        file_size_bytes=2048,
        document_type=DocumentType.RESUME.value,
        classification_confidence=0.7,
        markdown_content="md content",
        status=DocumentStatus.COMPLETED.value,
        error_message=None,
        s3_key="s3/key",
        created_at=now,
        updated_at=now,
        processed_at=now,
    )

    dto = DocumentOut.from_orm_model(doc)

    assert dto.original_filename == "cv.docx"
    assert dto.file_size_bytes == 2048
    assert dto.document_type == DocumentType.RESUME.value
    assert dto.status == DocumentStatus.COMPLETED.value
    assert dto.processed_at == now


def test_document_list_item_from_orm_model():
    now = datetime.utcnow()
    doc = SimpleNamespace(
        id=uuid4(),
        original_filename="cover_letter.md",
        file_type="md",
        document_type=DocumentType.COVER_LETTER.value,
        status=DocumentStatus.PENDING.value,
        created_at=now,
    )

    item = DocumentListItem.from_orm_model(doc)

    assert item.id == doc.id
    assert item.document_type == DocumentType.COVER_LETTER.value
    assert item.status == DocumentStatus.PENDING.value
    assert item.created_at == now
