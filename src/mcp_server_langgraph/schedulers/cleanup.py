"""
Data Cleanup Scheduler

Scheduled background jobs for data retention policy enforcement.
Runs daily at configured time (default: 3 AM UTC).
"""

from datetime import datetime, timezone
from typing import Any, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from mcp_server_langgraph.auth.session import SessionStore
from mcp_server_langgraph.compliance.retention import DataRetentionService
from mcp_server_langgraph.integrations.alerting import Alert, AlertCategory, AlertingService, AlertSeverity
from mcp_server_langgraph.observability.telemetry import logger


class CleanupScheduler:
    """
    Scheduler for automated data retention cleanup

    Features:
    - Daily execution at configured time
    - Graceful error handling
    - Metrics tracking
    - Dry-run support for testing
    """

    def __init__(
        self,
        session_store: Optional[SessionStore] = None,
        config_path: str = "config/retention_policies.yaml",
        dry_run: bool = False,
    ):
        """
        Initialize cleanup scheduler

        Args:
            session_store: Session storage backend
            config_path: Path to retention policies configuration
            dry_run: If True, simulate cleanups without actually deleting
        """
        self.session_store = session_store
        self.config_path = config_path
        self.dry_run = dry_run
        self.scheduler = AsyncIOScheduler()
        self.retention_service: Optional[DataRetentionService] = None

    async def start(self) -> None:
        """
        Start the cleanup scheduler

        Loads configuration and schedules daily cleanup job.
        """
        logger.info(
            "Starting data retention cleanup scheduler",
            extra={"config_path": self.config_path, "dry_run": self.dry_run},
        )

        # Initialize retention service
        self.retention_service = DataRetentionService(
            config_path=self.config_path,
            session_store=self.session_store,
            dry_run=self.dry_run,
        )

        # Get cleanup schedule from configuration
        config = self.retention_service.config
        schedule = config.get("global", {}).get("cleanup_schedule", "0 3 * * *")

        # Parse cron expression (default: 0 3 * * * = daily at 3 AM)
        parts = schedule.split()
        if len(parts) == 5:
            minute, hour, day, month, day_of_week = parts

            # Create cron trigger
            trigger = CronTrigger(
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=day_of_week,
                timezone="UTC",
            )

            # Add scheduled job
            self.scheduler.add_job(
                self._run_cleanup,
                trigger=trigger,
                id="data_retention_cleanup",
                name="Data Retention Cleanup",
                replace_existing=True,
                max_instances=1,  # Prevent overlapping runs
            )

            logger.info(
                "Scheduled data retention cleanup",
                extra={"schedule": schedule, "next_run": self._get_next_run_time()},
            )

        else:
            logger.error(f"Invalid cron schedule: {schedule}", extra={"schedule": schedule})

        # Start scheduler
        self.scheduler.start()
        logger.info("Cleanup scheduler started")

    async def stop(self) -> None:
        """Stop the cleanup scheduler"""
        logger.info("Stopping data retention cleanup scheduler")
        self.scheduler.shutdown(wait=True)
        logger.info("Cleanup scheduler stopped")

    async def _run_cleanup(self) -> None:
        """
        Execute data retention cleanup

        This is the main scheduled job that runs all retention policies.
        """
        logger.info(
            "Executing scheduled data retention cleanup",
            extra={"timestamp": datetime.now(timezone.utc).isoformat(), "dry_run": self.dry_run},
        )

        try:
            if not self.retention_service:
                logger.error("Retention service not initialized")
                return

            # Run all cleanup policies
            results = await self.retention_service.run_all_cleanups()

            # Log summary
            total_deleted = sum(r.deleted_count for r in results)
            total_archived = sum(r.archived_count for r in results)
            total_errors = sum(len(r.errors) for r in results)

            log_level = "error" if total_errors > 0 else "info"
            log_method = getattr(logger, log_level)

            log_method(
                "Data retention cleanup completed",
                extra={
                    "total_deleted": total_deleted,
                    "total_archived": total_archived,
                    "total_errors": total_errors,
                    "policies_executed": len(results),
                    "dry_run": self.dry_run,
                },
            )

            # Send notification if configured
            if self.retention_service.config.get("notifications", {}).get("enabled", True):
                await self._send_cleanup_notification(results)  # type: ignore[attr-defined]

        except Exception as e:
            logger.error(f"Data retention cleanup failed: {e}", exc_info=True)

    async def _send_cleanup_notification(self, results: list) -> None:
        """
        Send notification about cleanup execution

        Args:
            results: List of RetentionResults
        """
        total_deleted = sum(r.deleted_count for r in results)

        logger.info(
            "Cleanup notification",
            extra={
                "results_count": len(results),
                "total_deleted": total_deleted,
            },
        )

        # Send notification to operations team
        try:
            alerting_service = AlertingService()
            await alerting_service.initialize()

            # Determine severity based on deleted count
            if total_deleted > 1000:
                severity = AlertSeverity.WARNING  # type: ignore[attr-defined]
                title = "Large Data Cleanup Executed"
            else:
                severity = AlertSeverity.INFO
                title = "Data Cleanup Completed"

            alert = Alert(
                title=title,
                description=f"Data retention cleanup processed {len(results)} data types, deleted {total_deleted} records",
                severity=severity,
                category=AlertCategory.INFRASTRUCTURE,
                source="cleanup_scheduler",
                metadata={
                    "results_count": len(results),
                    "total_deleted": total_deleted,
                    "data_types": [r.data_type for r in results],  # type: ignore[attr-defined]
                },
            )

            await alerting_service.send_alert(alert)
            logger.info("Cleanup notification sent", extra={"alert_id": alert.alert_id})

        except Exception as e:
            logger.error(f"Failed to send cleanup notification: {e}", exc_info=True)

    def _get_next_run_time(self) -> str:
        """Get next scheduled run time"""
        try:
            job = self.scheduler.get_job("data_retention_cleanup")
            if job and hasattr(job, "next_run_time") and job.next_run_time:
                return job.next_run_time.isoformat()  # type: ignore[no-any-return]
        except Exception:
            pass
        return "Not scheduled"

    async def run_now(self) -> None:
        """
        Manually trigger cleanup immediately (for testing/admin)

        Returns:
            List of RetentionResults
        """
        logger.info("Manual cleanup triggered")
        await self._run_cleanup()


# Global scheduler instance
_cleanup_scheduler: Optional[CleanupScheduler] = None


async def start_cleanup_scheduler(  # type: ignore[no-untyped-def]
    session_store: Optional[SessionStore] = None,
    config_path: str = "config/retention_policies.yaml",
    dry_run: bool = False,
):
    """
    Start the global cleanup scheduler

    Args:
        session_store: Session storage backend
        config_path: Path to retention policies
        dry_run: Test mode without actual deletions

    Example:
        # At application startup
        await start_cleanup_scheduler(
            session_store=session_store,
            dry_run=False
        )
    """
    global _cleanup_scheduler

    if _cleanup_scheduler is not None:
        logger.warning("Cleanup scheduler already running")
        return

    _cleanup_scheduler = CleanupScheduler(
        session_store=session_store,
        config_path=config_path,
        dry_run=dry_run,
    )

    await _cleanup_scheduler.start()


async def stop_cleanup_scheduler() -> None:
    """Stop the global cleanup scheduler"""
    global _cleanup_scheduler

    if _cleanup_scheduler is None:
        logger.warning("Cleanup scheduler not running")
        return

    await _cleanup_scheduler.stop()
    _cleanup_scheduler = None


def get_cleanup_scheduler() -> Optional[CleanupScheduler]:
    """Get the global cleanup scheduler instance"""
    return _cleanup_scheduler
