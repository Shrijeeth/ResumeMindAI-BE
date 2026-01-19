"""TaskIQ broker and task registration.

This module provides the TaskIQ broker configured with Redis
for distributed task processing.

Usage from FastAPI endpoints:
    from tasks.health_task import check_api_health_task

    @router.post("/trigger-health-check")
    async def trigger_health_check():
        # Queue task for background execution
        task = await check_api_health_task.kiq()
        return {"task_id": task.task_id}
"""

from taskiq_redis import ListQueueBroker, RedisAsyncResultBackend

from configs.settings import get_settings

_broker = None


def get_broker() -> ListQueueBroker:
    """Get or create the TaskIQ broker instance.

    Uses Redis as the message broker for task distribution.
    """
    global _broker
    if _broker is None:
        settings = get_settings()
        _broker = ListQueueBroker(
            url=settings.REDIS_URL,
            queue_name=settings.TASKIQ_QUEUE_NAME,
        ).with_result_backend(
            RedisAsyncResultBackend(
                settings.REDIS_URL,
                prefix_str="taskiq-results",
                result_ex_time=settings.TASKIQ_RESULT_TTL_SECONDS,
            )
        )
    return _broker


broker = get_broker()
