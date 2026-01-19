"""Document model for resume and job-related file storage."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Float, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from configs.postgres import Base


class DocumentStatus(str, enum.Enum):
    """Document processing status states."""

    PENDING = "pending"
    UPLOADING = "uploading"
    VALIDATING = "validating"
    INVALID = "invalid"
    PARSING = "parsing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentType(str, enum.Enum):
    """Classification of document content type."""

    RESUME = "resume"
    JOB_DESCRIPTION = "job_description"
    COVER_LETTER = "cover_letter"
    OTHER = "other"
    UNKNOWN = "unknown"


class FileType(str, enum.Enum):
    """Supported file types for upload."""

    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    MD = "md"


class Document(Base):
    """Model for storing uploaded documents and their parsed content."""

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # File metadata
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # S3 storage
    s3_key: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    s3_bucket: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Classification & content
    document_type: Mapped[str] = mapped_column(
        String(50), default=DocumentType.UNKNOWN.value, nullable=False
    )
    classification_confidence: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    markdown_content: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Processing state
    status: Mapped[str] = mapped_column(
        String(50), default=DocumentStatus.PENDING.value, nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    task_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    # Graph processing placeholder
    graph_node_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ontology_version: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    __table_args__ = (
        Index("ix_documents_user_status", "user_id", "status"),
        Index("ix_documents_user_created", "user_id", "created_at"),
    )
