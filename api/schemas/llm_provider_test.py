from typing import Optional

from pydantic import BaseModel

from api.schemas.llm_provider import ProviderOut
from models.llm_provider import ProviderStatus


class TestConnectionRequest(BaseModel):
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    model_name: Optional[str] = None


class TestConnectionResponse(BaseModel):
    status: ProviderStatus
    latency_ms: Optional[int]
    error_message: Optional[str]
    provider: ProviderOut
