"""Scheduler setup for recurring tasks.

Replaces: temporal/schedules.py

Uses TaskIQ scheduler for cron-based scheduling.
"""

import logging

from taskiq import TaskiqScheduler
from taskiq.schedule_sources import LabelScheduleSource

from tasks import broker
from tasks.health_task import check_api_health_task

logger = logging.getLogger(__name__)

# Create scheduler with label-based schedule source
scheduler = TaskiqScheduler(
    broker=broker,
    sources=[LabelScheduleSource(broker)],
)


@broker.task(
    task_name="scheduled_health_check",
    schedule=[
        # Run every 6 hours: at 00:00, 06:00, 12:00, 18:00
        {"cron": "0 */6 * * *"},
    ],
)
async def scheduled_health_check() -> dict:
    """Scheduled wrapper for health check.

    Runs every 6 hours via cron schedule.
    Delegates to the main health check task.
    """
    logger.info("Running scheduled health check (every 6 hours)")
    return await check_api_health_task()
