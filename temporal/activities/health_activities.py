"""Health check activities for Temporal workflows."""

import httpx
from temporalio import activity

from configs import get_settings


@activity.defn
async def check_api_health() -> dict:
    """Activity to check API health endpoint.

    This replaces the Prefect health_check flow logic.
    """
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
        activity.logger.info(f"Health check passed: {data}")
        return data
