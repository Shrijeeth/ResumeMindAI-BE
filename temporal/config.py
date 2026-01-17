"""Temporal configuration and constants."""

from dataclasses import dataclass
from typing import Optional

from configs.settings import get_settings


@dataclass
class TemporalConfig:
    """Configuration for Temporal connection."""

    host: str = "localhost"
    port: int = 8000
    namespace: str = "default"
    task_queue: str = "resumemind-tasks"
    api_key: Optional[str] = None

    @property
    def server_address(self) -> str:
        if self.port is None:
            return self.host
        return f"{self.host}:{self.port}"


def get_temporal_config() -> TemporalConfig:
    """Get Temporal configuration from environment."""
    settings = get_settings()
    api_key = settings.TEMPORAL_API_KEY if settings.TEMPORAL_API_KEY else None
    return TemporalConfig(
        host=settings.TEMPORAL_HOST,
        port=settings.TEMPORAL_PORT,
        namespace=settings.TEMPORAL_NAMESPACE,
        task_queue=settings.TEMPORAL_TASK_QUEUE,
        api_key=api_key,
    )
