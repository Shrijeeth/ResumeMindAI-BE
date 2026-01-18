"""TaskIQ worker entry point.

Replaces: temporal/worker.py

Run with: python -m tasks.worker
"""

import asyncio
import logging
import signal

from dotenv import load_dotenv

from configs.lifecycle import shutdown_all, startup_all
from tasks import broker
from tasks.scheduler import scheduler

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s]: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


async def run_worker():
    """Start and run the TaskIQ worker with scheduler."""
    await startup_all()

    logger.info("Starting TaskIQ worker...")

    # Handle graceful shutdown
    shutdown_event = asyncio.Event()

    def signal_handler():
        logger.info("Shutdown signal received")
        shutdown_event.set()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    # Start the broker and scheduler
    await broker.startup()
    await scheduler.startup()

    logger.info("Worker and scheduler started, listening for tasks...")

    try:
        # Keep running until shutdown signal
        await shutdown_event.wait()
    finally:
        await scheduler.shutdown()
        await broker.shutdown()
        await shutdown_all()
        logger.info("Worker shutdown complete")


if __name__ == "__main__":
    asyncio.run(run_worker())
