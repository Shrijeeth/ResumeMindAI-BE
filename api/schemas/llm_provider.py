from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from models.llm_provider import ProviderStatus, ProviderType

PROVIDER_INITIALS = {
    ProviderType.OPENAI: "OA",
    ProviderType.ANTHROPIC: "AN",
    ProviderType.GOOGLE_GEMINI: "GG",
    ProviderType.AZURE_OPENAI: "AZ",
    ProviderType.OLLAMA: "OL",
    ProviderType.HUGGINGFACE: "HF",
    ProviderType.GROQ: "GQ",
    ProviderType.CUSTOM: "CU",
}

PROVIDER_COLOR_CLASSES = {
    ProviderType.OPENAI: "bg-emerald-500/10 text-emerald-500 border-emerald-500/20",
    ProviderType.ANTHROPIC: "bg-orange-500/10 text-orange-500 border-orange-500/20",
    ProviderType.GOOGLE_GEMINI: "bg-blue-500/10 text-blue-500 border-blue-500/20",
    ProviderType.AZURE_OPENAI: "bg-sky-500/10 text-sky-500 border-sky-500/20",
    ProviderType.OLLAMA: "bg-purple-500/10 text-purple-500 border-purple-500/20",
    ProviderType.HUGGINGFACE: "bg-yellow-500/10 text-yellow-500 border-yellow-500/20",
    ProviderType.GROQ: "bg-rose-500/10 text-rose-500 border-rose-500/20",
    ProviderType.CUSTOM: "bg-slate-500/10 text-slate-400 border-slate-500/20",
}

PROVIDER_DISPLAY_NAMES = {
    ProviderType.OPENAI: "OpenAI",
    ProviderType.ANTHROPIC: "Anthropic",
    ProviderType.GOOGLE_GEMINI: "Google Gemini",
    ProviderType.AZURE_OPENAI: "Azure OpenAI",
    ProviderType.OLLAMA: "Ollama",
    ProviderType.HUGGINGFACE: "Hugging Face",
    ProviderType.GROQ: "Groq",
    ProviderType.CUSTOM: "Custom",
}


class ProviderBase(BaseModel):
    provider_type: ProviderType
    model_name: str = Field(..., min_length=1, max_length=255)
    base_url: Optional[str] = None
    api_key: str = Field(..., min_length=1)


class ProviderCreate(ProviderBase):
    pass


class ProviderUpdate(BaseModel):
    model_name: Optional[str] = Field(None, min_length=1, max_length=255)
    base_url: Optional[str] = None
    api_key: Optional[str] = Field(None, min_length=1)
    status: Optional[ProviderStatus] = None
    latency_ms: Optional[int] = Field(None, ge=0)
    error_message: Optional[str] = None


class ProviderOut(BaseModel):
    id: UUID
    provider_type: ProviderType
    model_name: str
    base_url: Optional[str]
    status: ProviderStatus
    is_active: bool
    latency_ms: Optional[int]
    error_message: Optional[str]
    logo_initials: str
    logo_color_class: str
    created_at: datetime
    updated_at: datetime

    @field_validator("provider_type", mode="before")
    @classmethod
    def validate_provider_type(cls, v):
        if isinstance(v, str):
            try:
                return ProviderType(v)
            except ValueError:
                raise ValueError(
                    f"Invalid provider_type: {v}. Must be one of: "
                    f"{', '.join([t.value for t in ProviderType])}"
                )
        raise ValueError(
            f"Invalid provider_type: {v}. Must be one of: "
            f"{', '.join([t.value for t in ProviderType])}"
        )

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v):
        if isinstance(v, str):
            try:
                return ProviderStatus(v)
            except ValueError:
                raise ValueError(
                    f"Invalid status: {v}. Must be one of: "
                    f"{', '.join([s.value for s in ProviderStatus])}"
                )
        raise ValueError(
            f"Invalid status: {v}. Must be one of: "
            f"{', '.join([s.value for s in ProviderStatus])}"
        )

    @classmethod
    def from_orm_model(cls, provider) -> "ProviderOut":
        return cls(
            id=provider.id,
            provider_type=provider.provider_type,
            model_name=provider.model_name,
            base_url=provider.base_url,
            status=provider.status,
            is_active=provider.is_active,
            latency_ms=provider.latency_ms,
            error_message=provider.error_message,
            logo_initials=PROVIDER_INITIALS.get(
                ProviderType(provider.provider_type)
                if isinstance(provider.provider_type, str)
                else provider.provider_type,
                "??",
            ),
            logo_color_class=PROVIDER_COLOR_CLASSES.get(
                ProviderType(provider.provider_type)
                if isinstance(provider.provider_type, str)
                else provider.provider_type,
                "bg-slate-500/10 text-slate-400 border-slate-500/20",
            ),
            created_at=provider.created_at,
            updated_at=provider.updated_at,
        )

    class Config:
        from_attributes = True


class SupportedProvider(BaseModel):
    provider_type: ProviderType
    provider_name: str
    logo_initials: str
    logo_color_class: str
