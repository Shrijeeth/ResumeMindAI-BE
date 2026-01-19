"""API schemas package."""

from api.schemas.document import (
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE_BYTES,
    MAX_FILE_SIZE_MB,
    DocumentListItem,
    DocumentOut,
    DocumentStatusResponse,
    DocumentUploadResponse,
)
from api.schemas.llm_provider import (
    ProviderCreate,
    ProviderOut,
    ProviderUpdate,
    SupportedProvider,
)
from api.schemas.llm_provider_test import (
    TestConnectionRequest,
    TestConnectionResponse,
)

__all__ = [
    "ALLOWED_EXTENSIONS",
    "MAX_FILE_SIZE_BYTES",
    "MAX_FILE_SIZE_MB",
    "DocumentListItem",
    "DocumentOut",
    "DocumentStatusResponse",
    "DocumentUploadResponse",
    "ProviderCreate",
    "ProviderOut",
    "ProviderUpdate",
    "SupportedProvider",
    "TestConnectionRequest",
    "TestConnectionResponse",
]
