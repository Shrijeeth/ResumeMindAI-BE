import httpx
from prefect import flow, get_run_logger

# Import lifecycle to ensure load_dotenv() is called
import configs.lifecycle  # noqa: F401
from configs import get_settings


@flow(name="health-check", retries=1)
async def health_check() -> dict:
    """Periodic health check flow that verifies API availability."""
    logger = get_run_logger()
    settings = get_settings()

    api_base_url = settings.API_BASE_URL.rstrip("/")
    internal_api_key = settings.INTERNAL_API_KEY

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{api_base_url}/api/health",
            headers={"X-Api-Key": internal_api_key},
        )
        response.raise_for_status()
        data = response.json()
        logger.info(f"Health check passed: {data}")
        return data


if __name__ == "__main__":
    import asyncio

    asyncio.run(health_check())
