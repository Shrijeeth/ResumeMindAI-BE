from supabase import AsyncClient, create_async_client

from configs.settings import get_settings

supabase_client: AsyncClient | None = None


async def init_supabase_client() -> None:
    global supabase_client
    settings = get_settings()
    supabase_client = await create_async_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_ANON_KEY,
    )


async def shutdown_supabase_client() -> None:
    global supabase_client
    supabase_client = None


async def get_supabase_client() -> AsyncClient:
    if supabase_client is None:
        raise RuntimeError("Supabase client is not initialized")
    return supabase_client
