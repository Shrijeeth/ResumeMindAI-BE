"""Shared lifecycle management for FastAPI app and TaskIQ workers.

This module provides common initialization and shutdown utilities
that can be used by both the FastAPI application and TaskIQ tasks.
"""

import logging
from contextlib import asynccontextmanager

from configs.falkordb import init_falkordb_client, shutdown_falkordb_client
from configs.postgres import init_engine, shutdown_engine
from configs.redis import init_redis_client, shutdown_redis_client
from configs.s3 import init_s3_session, shutdown_s3_session
from configs.supabase import init_supabase_client, shutdown_supabase_client

logger = logging.getLogger(__name__)


def get_broker():
    """Lazy import to avoid circular dependency."""
    from tasks import broker

    return broker


async def startup_all() -> None:
    """Initialize all service clients.

    Used by FastAPI lifespan and can be used by flows that need all services.
    """
    logger.info("Initializing database engine...")
    init_engine()

    logger.info("Initializing supabase client...")
    await init_supabase_client()

    logger.info("Initializing redis client...")
    await init_redis_client()

    logger.info("Initializing s3 session...")
    await init_s3_session()

    logger.info("Initializing falkordb client...")
    await init_falkordb_client()

    logger.info("Initializing TaskIQ broker...")
    broker = get_broker()
    await broker.startup()


async def shutdown_all() -> None:
    """Shutdown all service clients.

    Used by FastAPI lifespan and can be used by flows that need all services.
    """
    logger.info("Shutting down TaskIQ broker...")
    broker = get_broker()
    await broker.shutdown()

    logger.info("Shutting down database engine...")
    await shutdown_engine()

    logger.info("Shutting down supabase client...")
    await shutdown_supabase_client()

    logger.info("Shutting down redis client...")
    await shutdown_redis_client()

    logger.info("Shutting down s3 session...")
    await shutdown_s3_session()

    logger.info("Shutting down falkordb client...")
    await shutdown_falkordb_client()


@asynccontextmanager
async def app_lifespan():
    """Full application context with all services.

    Usage in FastAPI:
        async def lifespan(app: FastAPI):
            async with app_lifespan():
                yield

    Usage in TaskIQ tasks:
        async with app_lifespan():
            # task logic here
    """
    await startup_all()
    try:
        yield
    finally:
        await shutdown_all()


@asynccontextmanager
async def worker_context(
    postgres: bool = True,
    redis: bool = True,
    supabase: bool = False,
    s3: bool = False,
    falkordb: bool = False,
):
    """Configurable context for TaskIQ workers/tasks.

    Initialize only the services needed by a specific task.

    Args:
        postgres: Initialize PostgreSQL connection
        redis: Initialize Redis connection
        supabase: Initialize Supabase client
        s3: Initialize S3 session
        falkordb: Initialize FalkorDB client

    Usage:
        @broker.task
        async def my_task():
            async with worker_context(postgres=True, redis=True):
                # task logic with db and redis access
    """
    try:
        if postgres:
            logger.info("Initializing database engine...")
            init_engine()
        if redis:
            logger.info("Initializing redis client...")
            await init_redis_client()
        if supabase:
            logger.info("Initializing supabase client...")
            await init_supabase_client()
        if s3:
            logger.info("Initializing s3 session...")
            await init_s3_session()
        if falkordb:
            logger.info("Initializing falkordb client...")
            await init_falkordb_client()

        yield

    finally:
        if falkordb:
            logger.info("Shutting down falkordb client...")
            await shutdown_falkordb_client()
        if s3:
            logger.info("Shutting down s3 session...")
            await shutdown_s3_session()
        if supabase:
            logger.info("Shutting down supabase client...")
            await shutdown_supabase_client()
        if redis:
            logger.info("Shutting down redis client...")
            await shutdown_redis_client()
        if postgres:
            logger.info("Shutting down database engine...")
            await shutdown_engine()
