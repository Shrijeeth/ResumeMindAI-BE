"""Temporal client utilities for connecting to Temporal server."""

import asyncio
from typing import Optional

from temporalio.client import Client

from temporal.config import get_temporal_config

# Cached client instance
_client: Optional[Client] = None
_client_lock = asyncio.Lock()


def _build_rpc_metadata(api_key: str | None) -> dict[str, str]:
    """Build RPC metadata headers for API key auth."""
    if api_key:
        return {"authorization": f"Bearer {api_key}"}
    return {}


async def get_temporal_client() -> Client:
    """Get or create a cached Temporal client."""
    global _client

    async with _client_lock:
        if _client is None:
            config = get_temporal_config()
            rpc_metadata = _build_rpc_metadata(config.api_key)
            _client = await Client.connect(
                config.server_address,
                namespace=config.namespace,
                rpc_metadata=rpc_metadata,
            )
    return _client
