from falkordb.asyncio import FalkorDB

from configs.settings import get_settings

falkordb_client: FalkorDB | None = None


async def init_falkordb_client():
    global falkordb_client
    settings = get_settings()
    falkordb_client = FalkorDB(
        host=settings.FALKORDB_HOST,
        port=settings.FALKORDB_PORT,
        username=settings.FALKORDB_USERNAME,
        password=settings.FALKORDB_PASSWORD,
    )


async def shutdown_falkordb_client():
    global falkordb_client
    if falkordb_client is not None:
        await falkordb_client.connection.close(True)
    falkordb_client = None


async def get_falkordb_client():
    global falkordb_client
    if falkordb_client is None:
        raise RuntimeError("Falkordb client is not initialized")
    return falkordb_client
