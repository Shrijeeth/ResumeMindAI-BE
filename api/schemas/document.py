"""Pydantic schemas for document API endpoints."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from models.document import DocumentStatus, DocumentType, FileType

# Allowed file extensions for validation
ALLOWED_EXTENSIONS = {"pdf", "docx", "txt", "md"}
MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


class DocumentUploadResponse(BaseModel):
    """Response returned immediately after upload request."""

    document_id: UUID
    task_id: str
    status: DocumentStatus
    message: str = Field(default="Document upload initiated")


class DocumentStatusResponse(BaseModel):
    """Response for status polling endpoint."""

    document_id: UUID
    status: DocumentStatus
    document_type: Optional[DocumentType] = None
    classification_confidence: Optional[float] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    processed_at: Optional[datetime] = None
    progress_message: str = Field(default="")

    @classmethod
    def from_orm_model(cls, doc) -> "DocumentStatusResponse":
        status = DocumentStatus(doc.status)
        progress_messages = {
            DocumentStatus.PENDING: "Waiting to start processing",
            DocumentStatus.UPLOADING: "Uploading file to storage",
            DocumentStatus.VALIDATING: "Validating document type with AI",
            DocumentStatus.PARSING: "Converting document to markdown",
            DocumentStatus.COMPLETED: "Processing complete",
            DocumentStatus.INVALID: "Document validation failed",
            DocumentStatus.FAILED: "Processing failed",
        }
        return cls(
            document_id=doc.id,
            status=status,
            document_type=(
                DocumentType(doc.document_type)
                if doc.document_type and doc.document_type != DocumentType.UNKNOWN.value
                else None
            ),
            classification_confidence=doc.classification_confidence,
            error_message=doc.error_message,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
            processed_at=doc.processed_at,
            progress_message=progress_messages.get(status, "Processing"),
        )

    class Config:
        from_attributes = True


class DocumentOut(BaseModel):
    """Full document details for completed documents."""

    id: UUID
    original_filename: str
    file_type: str
    file_size_bytes: Optional[int] = None
    document_type: str
    classification_confidence: Optional[float] = None
    markdown_content: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    s3_key: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    processed_at: Optional[datetime] = None

    @field_validator("file_type", mode="before")
    @classmethod
    def validate_file_type(cls, v):
        if isinstance(v, FileType):
            return v.value
        return v

    @field_validator("document_type", mode="before")
    @classmethod
    def validate_document_type(cls, v):
        if isinstance(v, DocumentType):
            return v.value
        return v

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v):
        if isinstance(v, DocumentStatus):
            return v.value
        return v

    @classmethod
    def from_orm_model(cls, doc) -> "DocumentOut":
        return cls(
            id=doc.id,
            original_filename=doc.original_filename,
            file_type=doc.file_type,
            file_size_bytes=doc.file_size_bytes,
            document_type=doc.document_type,
            classification_confidence=doc.classification_confidence,
            markdown_content=doc.markdown_content,
            status=doc.status,
            error_message=doc.error_message,
            s3_key=doc.s3_key,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
            processed_at=doc.processed_at,
        )

    class Config:
        from_attributes = True


class DocumentListItem(BaseModel):
    """Lightweight document info for list endpoints."""

    id: UUID
    original_filename: str
    file_type: str
    document_type: str
    status: str
    created_at: datetime

    @classmethod
    def from_orm_model(cls, doc) -> "DocumentListItem":
        return cls(
            id=doc.id,
            original_filename=doc.original_filename,
            file_type=doc.file_type,
            document_type=doc.document_type,
            status=doc.status,
            created_at=doc.created_at,
        )

    class Config:
        from_attributes = True
