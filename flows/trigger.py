"""Utilities for triggering Prefect flows from FastAPI endpoints.

Two approaches are available:

1. Via Prefect Cloud (requires PREFECT_API_URL and PREFECT_API_KEY):
   - Use `trigger_background_task_via_deployment()`
   - Task is submitted to Prefect Cloud, picked up by worker
   - Best for production with separate worker Space

2. Direct execution (no Prefect Cloud needed):
   - Use `trigger_background_task_direct()`
   - Runs in background thread, doesn't block API response
   - Simpler setup, good for development or single-instance deployments
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from prefect.client.orchestration import get_client

from flows.tasks import run_background_task

# Thread pool for running flows without blocking the API
_executor = ThreadPoolExecutor(max_workers=4)


# =============================================================================
# Option 1: Via Prefect Cloud Deployments (recommended for production)
# Requires: PREFECT_API_URL, PREFECT_API_KEY env vars
# Requires: Deployments registered via `prefect deploy`
# =============================================================================


async def trigger_background_task_via_deployment(payload: dict) -> str:
    """Trigger background task via Prefect Cloud deployment.

    The task is submitted to Prefect Cloud and picked up by a worker.
    Returns the flow run ID immediately without waiting for completion.

    Requires:
        - PREFECT_API_URL and PREFECT_API_KEY environment variables
        - Deployment registered: `prefect deploy`

    Args:
        payload: Data to pass to the background task

    Returns:
        Flow run ID for tracking
    """
    async with get_client() as client:
        deployment = await client.read_deployment_by_name(
            "run-background-task/background-task"
        )
        flow_run = await client.create_flow_run_from_deployment(
            deployment_id=deployment.id,
            parameters={"payload": payload},
        )
        return str(flow_run.id)


async def trigger_health_check_via_deployment() -> str:
    """Trigger health check flow via Prefect Cloud deployment."""
    async with get_client() as client:
        deployment = await client.read_deployment_by_name("health-check/health-6h")
        flow_run = await client.create_flow_run_from_deployment(
            deployment_id=deployment.id,
        )
        return str(flow_run.id)


# =============================================================================
# Option 2: Direct execution (no Prefect Cloud needed)
# Runs in background thread, good for development or simple setups
# =============================================================================


def _run_flow_sync(payload: dict) -> Any:
    """Run flow synchronously in a thread."""
    return asyncio.run(run_background_task(payload))


async def trigger_background_task_direct(payload: dict) -> str:
    """Trigger background task directly without Prefect Cloud.

    Runs the flow in a background thread so it doesn't block the API response.
    No Prefect Cloud connection required.

    Args:
        payload: Data to pass to the background task

    Returns:
        Status message (no flow run ID available in this mode)
    """
    loop = asyncio.get_event_loop()
    loop.run_in_executor(_executor, _run_flow_sync, payload)
    return "submitted-direct"


# =============================================================================
# Default aliases (use Prefect Cloud by default)
# =============================================================================

trigger_background_task = trigger_background_task_via_deployment
trigger_health_check = trigger_health_check_via_deployment
