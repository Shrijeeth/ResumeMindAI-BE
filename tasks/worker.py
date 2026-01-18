"""TaskIQ worker entry point.

Replaces: temporal/worker.py

Run with: python -m tasks.worker
"""

import asyncio
import logging
import signal

from aiohttp import web
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


async def health_handler(request: web.Request) -> web.Response:
    """Health check endpoint for HF Spaces."""
    return web.json_response({"status": "healthy", "service": "taskiq-worker"})


async def run_health_server() -> web.AppRunner:
    """Start a minimal HTTP server for health checks."""
    app = web.Application()
    app.router.add_get("/", health_handler)
    app.router.add_get("/health", health_handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8000)
    await site.start()
    logger.info("Health check server running on port 8000")
    return runner


async def run_worker():
    """Start and run the TaskIQ worker with scheduler."""
    await startup_all()

    logger.info("Starting TaskIQ worker...")

    # Start health check server for HF Spaces
    health_runner = await run_health_server()

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
        await health_runner.cleanup()
        await scheduler.shutdown()
        await broker.shutdown()
        await shutdown_all()
        logger.info("Worker shutdown complete")


if __name__ == "__main__":
    asyncio.run(run_worker())
