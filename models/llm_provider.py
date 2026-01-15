import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import BYTEA, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from configs.postgres import Base


class ProviderType(str, enum.Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE_GEMINI = "google-gemini"
    AZURE_OPENAI = "azure-openai"
    OLLAMA = "ollama"
    HUGGINGFACE = "huggingface"
    GROQ = "groq"
    CUSTOM = "custom"


class ProviderStatus(str, enum.Enum):
    CONNECTED = "connected"
    INACTIVE = "inactive"
    ERROR = "error"


class EventType(str, enum.Enum):
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    TESTED = "tested"


class EventStatus(str, enum.Enum):
    SUCCESS = "success"
    FAILURE = "failure"


class LLMProvider(Base):
    __tablename__ = "llm_providers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    provider_type: Mapped[str] = mapped_column(String(100), nullable=False)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    base_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    api_key_encrypted: Mapped[bytes] = mapped_column(BYTEA, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default=ProviderStatus.INACTIVE.value, nullable=False
    )
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "provider_type",
            "model_name",
            name="uq_user_provider_model",
        ),
        Index("ix_llm_providers_user_provider", "user_id", "provider_type"),
        CheckConstraint("latency_ms >= 0", name="ck_latency_non_negative"),
    )


class LLMProviderEvent(Base):
    __tablename__ = "llm_provider_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    provider_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    event: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow, nullable=False
    )

    __table_args__ = (Index("ix_llm_provider_events_user", "user_id"),)
