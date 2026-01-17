"""Temporal worker entry point.

Replaces Prefect worker started via:
    prefect worker start --pool default
"""

import asyncio
import logging
import signal

from dotenv import load_dotenv
from temporalio.client import Client
from temporalio.worker import Worker

from configs.lifecycle import shutdown_all, startup_all
from temporal.activities.health_activities import check_api_health
from temporal.config import get_temporal_config
from temporal.schedules import create_health_check_schedule
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


async def run_worker():
    """Start and run the Temporal worker."""
    await startup_all()

    config = get_temporal_config()

    logger.info(f"Connecting to Temporal server at {config.server_address}")

    # Build connection options with API key if provided
    rpc_metadata = _build_rpc_metadata(config.api_key)

    client = await Client.connect(
        config.server_address,
        namespace=config.namespace,
        rpc_metadata=rpc_metadata,
    )

    # Create schedules on startup (idempotent - skips if already exists)
    logger.info("Setting up schedules...")
    await create_health_check_schedule(client)

    logger.info(f"Starting worker for task queue: {config.task_queue}")
    worker = Worker(
        client,
        task_queue=config.task_queue,
        workflows=[
            HealthCheckWorkflow,
        ],
        activities=[
            check_api_health,
        ],
    )

    # Handle graceful shutdown
    shutdown_event = asyncio.Event()

    def signal_handler():
        logger.info("Shutdown signal received")
        shutdown_event.set()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    logger.info("Worker started, waiting for tasks...")

    # Run worker until shutdown signal
    async with worker:
        await shutdown_event.wait()

    await shutdown_all()
    logger.info("Worker shutdown complete")


if __name__ == "__main__":
    asyncio.run(run_worker())
