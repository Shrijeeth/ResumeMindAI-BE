"""Standalone health check server for worker process.

This runs alongside the TaskIQ worker to provide a health endpoint
that can be pinged by GitHub Actions or monitoring services.
"""

import asyncio
import logging

from aiohttp import web

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s]: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


async def health_handler(request: web.Request) -> web.Response:
    """Health check endpoint."""
    return web.json_response({"status": "healthy", "service": "taskiq-worker"})


async def run_health_server(port: int = 8001):
    """Start a minimal HTTP server for health checks."""
    app = web.Application()
    app.router.add_get("/", health_handler)
    app.router.add_get("/health", health_handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Health check server running on port {port}")

    # Keep running
    try:
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        logger.info("Health server shutting down...")
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(run_health_server())
