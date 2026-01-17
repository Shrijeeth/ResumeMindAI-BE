from temporalio.client import Client

from configs.settings import get_settings

temporal_client: Client | None = None


async def init_temporal_client() -> None:
    global temporal_client
    settings = get_settings()
    temporal_client = await Client.connect(
        settings.TEMPORAL_HOST,
        namespace=settings.TEMPORAL_NAMESPACE,
    )


async def shutdown_temporal_client() -> None:
    global temporal_client
    temporal_client = None


async def get_temporal_client() -> Client:
    global temporal_client
    if temporal_client is None:
        raise ValueError("Temporal client is not initialized")
    return temporal_client
