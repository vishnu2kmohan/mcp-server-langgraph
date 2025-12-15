"""
Audit integrity verification scheduler.

Provides scheduled verification of audit log integrity:
- Daily verification of hash chain
- Alerting on integrity failures
- Metrics recording for monitoring

This module supports FedRAMP AU-9 requirements for
protecting audit information from unauthorized changes.
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any, Callable, Coroutine

from mcp_server_langgraph.audit.alerts import AuditAlert, AuditAlertDetector
from mcp_server_langgraph.audit.metrics import AuditMetrics

logger = logging.getLogger(__name__)


class AuditIntegrityScheduler:
    """
    Scheduled integrity verification for audit logs.

    Runs periodic verification of the audit hash chain to detect
    tampering. Supports configurable schedule and alert callbacks.

    Example:
        scheduler = AuditIntegrityScheduler(
            audit_service=audit_service,
            schedule_hours=24,
            alert_callback=send_to_pagerduty,
        )

        # Start background verification
        await scheduler.start()
    """

    def __init__(
        self,
        audit_service: Any,
        schedule_hours: int = 24,
        alert_callback: Callable[[AuditAlert], Coroutine[Any, Any, None]] | None = None,
        metrics: AuditMetrics | None = None,
        alert_detector: AuditAlertDetector | None = None,
    ) -> None:
        """
        Initialize integrity scheduler.

        Args:
            audit_service: The audit service for verification.
            schedule_hours: Hours between verification runs (default 24).
            alert_callback: Async callback for integrity alerts.
            metrics: Metrics instance for recording verification results.
            alert_detector: Alert detector for triggering alerts.
        """
        self._audit_service = audit_service
        self.schedule_hours = schedule_hours
        self._alert_callback = alert_callback
        self._metrics = metrics
        self._alert_detector = alert_detector
        self._stopped = False
        self._task: asyncio.Task[None] | None = None

    async def run_verification(self) -> dict[str, Any]:
        """
        Run integrity verification for the scheduled period.

        Verifies the hash chain for events in the last schedule_hours
        and triggers alerts if integrity issues are detected.

        Returns:
            Verification result dictionary.
        """
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(hours=self.schedule_hours)

        logger.info(
            "Starting scheduled integrity verification",
            extra={
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
            },
        )

        try:
            result: dict[str, Any] = await self._audit_service.verify_integrity(
                start_time=start_time,
                end_time=end_time,
            )

            # Record metrics
            if self._metrics:
                self._metrics.record_integrity_verification(
                    success=result.get("valid", False),
                    events_verified=result.get("events_verified", 0),
                )

            # Handle failures
            if not result.get("valid", True):
                await self._handle_verification_failure(result, start_time, end_time)

            logger.info(
                "Integrity verification completed",
                extra={
                    "valid": result.get("valid"),
                    "events_verified": result.get("events_verified"),
                    "errors": len(result.get("errors", [])),
                },
            )

            return result

        except Exception as e:
            logger.exception(
                "Integrity verification failed with exception",
                extra={"error": str(e)},
            )
            raise

    async def _handle_verification_failure(
        self,
        result: dict[str, Any],
        start_time: datetime,
        end_time: datetime,
    ) -> None:
        """Handle integrity verification failure."""
        errors = result.get("errors", [])

        # Create alert
        if self._alert_detector:
            self._alert_detector.report_integrity_failure(
                start_time=start_time,
                end_time=end_time,
                errors=errors,
            )

        # Invoke callback
        if self._alert_callback:
            alert = AuditAlert(
                alert_type="INTEGRITY_TAMPERING",
                severity="critical",
                message="Audit log integrity verification failed - possible tampering detected",
                details={
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "events_verified": result.get("events_verified", 0),
                    "errors": errors,
                },
            )
            try:
                await self._alert_callback(alert)
            except Exception as e:
                logger.exception(
                    "Alert callback failed",
                    extra={"error": str(e)},
                )

    async def start(self) -> None:
        """
        Start the background verification scheduler.

        Runs verification at the configured interval until stopped.
        """
        self._stopped = False
        self._task = asyncio.create_task(self._run_loop())
        logger.info(
            "Integrity scheduler started",
            extra={"schedule_hours": self.schedule_hours},
        )

    async def _run_loop(self) -> None:
        """Background loop for scheduled verification."""
        while not self._stopped:
            try:
                await self.run_verification()
            except Exception as e:
                logger.exception(
                    "Scheduled verification failed",
                    extra={"error": str(e)},
                )

            # Wait for next scheduled run
            await asyncio.sleep(self.schedule_hours * 3600)

    def stop(self) -> None:
        """
        Stop the background scheduler.

        Gracefully stops the verification loop.
        """
        self._stopped = True
        if self._task and not self._task.done():
            self._task.cancel()
        logger.info("Integrity scheduler stopped")

    async def wait_until_stopped(self) -> None:
        """Wait for the scheduler to fully stop."""
        if self._task:
            try:
                await self._task
            except asyncio.CancelledError:
                pass
