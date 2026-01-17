"""Schedule setup for recurring workflows.

Schedules are created automatically on worker startup.
Can also be run manually: python -m temporal.schedules
"""

import asyncio
import logging
from datetime import timedelta
from typing import Optional

from dotenv import load_dotenv
from temporalio.client import (
    Client,
    Schedule,
    ScheduleActionStartWorkflow,
    ScheduleIntervalSpec,
    ScheduleSpec,
)

from temporal.config import get_temporal_config
from temporal.workflows.health_workflow import HealthCheckWorkflow

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s]: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def _build_rpc_metadata(api_key: str | None) -> dict[str, str]:
    """Build RPC metadata headers for API key auth."""
    if api_key:
        return {"authorization": f"Bearer {api_key}"}
    return {}


async def create_health_check_schedule(client: Optional[Client] = None):
    """Create the 6-hour health check schedule.

    Idempotent - skips if schedule already exists.

    Args:
        client: Optional Temporal client. If not provided, creates a new connection.
    """
    config = get_temporal_config()

    # Use provided client or create new connection
    if client is None:
        rpc_metadata = _build_rpc_metadata(config.api_key)
        client = await Client.connect(
            config.server_address,
            namespace=config.namespace,
            rpc_metadata=rpc_metadata,
        )

    # Create schedule (idempotent - skips if already exists)
    try:
        await client.create_schedule(
            "health-check-6h",
            Schedule(
                action=ScheduleActionStartWorkflow(
                    HealthCheckWorkflow.run,
                    id="scheduled-health-check",
                    task_queue=config.task_queue,
                ),
                spec=ScheduleSpec(
                    intervals=[ScheduleIntervalSpec(every=timedelta(hours=6))],
                ),
            ),
        )
        logger.info("Health check schedule created successfully")
    except Exception as e:
        if "already exists" in str(e).lower():
            logger.info("Health check schedule already exists, skipping")
        else:
            raise


async def main():
    """Create all schedules (for manual invocation)."""
    logger.info("Setting up Temporal schedules...")
    await create_health_check_schedule()
    logger.info("Schedule setup complete")


if __name__ == "__main__":
    asyncio.run(main())
