"""Health check workflow - replaces Prefect health_check flow."""

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from temporal.activities.health_activities import check_api_health


@workflow.defn
class HealthCheckWorkflow:
    """Periodic health check workflow that verifies API availability.

    Equivalent to Prefect flow: flows/health.py:health_check
    """

    @workflow.run
    async def run(self) -> dict:
        """Execute the health check.

        Returns:
            Health check response from the API.
        """
        workflow.logger.info("Starting health check workflow")

        result = await workflow.execute_activity(
            check_api_health,
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=1),
                maximum_interval=timedelta(seconds=30),
                maximum_attempts=3,
                backoff_coefficient=2.0,
            ),
        )

        workflow.logger.info(f"Health check completed: {result}")
        return result
