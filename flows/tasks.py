from prefect import flow, get_run_logger, task

from configs.lifecycle import worker_context


@task
async def process_payload(payload: dict) -> dict:
    """Placeholder task for processing payloads."""
    logger = get_run_logger()
    logger.info(f"Processing payload: {payload}")
    # Add actual business logic here when needed
    # Example: access database via configs.postgres.use_db_session()
    # Example: access redis via configs.redis.get_redis_client()
    return {"status": "processed", "input": payload}


@flow(name="run-background-task")
async def run_background_task(payload: dict) -> dict:
    """Placeholder flow for background task execution."""
    logger = get_run_logger()
    logger.info(f"Starting background task with payload: {payload}")

    # Initialize only postgres and redis (default). Add supabase=True, s3=True,
    # or falkordb=True if your task needs those services.
    async with worker_context(postgres=True, redis=True):
        result = await process_payload(payload)

    logger.info(f"Background task completed: {result}")
    return result


if __name__ == "__main__":
    import asyncio

    asyncio.run(run_background_task({"test": "data"}))
