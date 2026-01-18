"""Health check task for TaskIQ.

Replaces:
- temporal/activities/health_activities.py
- temporal/workflows/health_workflow.py
"""

import logging

import httpx

from configs import get_settings
from tasks import broker

logger = logging.getLogger(__name__)


@broker.task(
    task_name="health_check",
    retry_on_error=True,
    max_retries=3,
)
async def check_api_health_task() -> dict:
    """Task to check API health endpoint.

    Retry policy:
    - Maximum 3 attempts
    - TaskIQ handles retries automatically on exceptions

    Timeout: 30 seconds (httpx client timeout)

    Returns:
        Health check response from the API.
    """
    settings = get_settings()
    api_base_url = settings.API_BASE_URL.rstrip("/")
    internal_api_key = settings.INTERNAL_API_KEY

    logger.info("Starting health check task")

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{api_base_url}/api/health",
            headers={"X-Api-Key": internal_api_key},
        )
        response.raise_for_status()
        data = response.json()
        logger.info(f"Health check passed: {data}")
        return data
