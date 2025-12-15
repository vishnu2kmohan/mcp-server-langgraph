"""
Factory functions for audit components.

Provides factory functions for creating audit-related components
with proper configuration and dependencies.
"""

from typing import Any, Callable, Coroutine

from mcp_server_langgraph.audit.alerts import AuditAlert, AuditAlertDetector
from mcp_server_langgraph.audit.metrics import AuditMetrics
from mcp_server_langgraph.audit.scheduler import AuditIntegrityScheduler


def create_audit_scheduler(
    audit_service: Any,
    schedule_hours: int = 24,
    alert_callback: Callable[[AuditAlert], Coroutine[Any, Any, None]] | None = None,
    metrics: AuditMetrics | None = None,
    alert_detector: AuditAlertDetector | None = None,
) -> AuditIntegrityScheduler:
    """
    Create an audit integrity scheduler with the given configuration.

    This factory function simplifies creation of the scheduler
    with proper dependency injection.

    Args:
        audit_service: The audit service for verification.
        schedule_hours: Hours between verification runs (default 24).
        alert_callback: Optional async callback for integrity alerts.
        metrics: Optional metrics instance for recording verification results.
        alert_detector: Optional alert detector for triggering alerts.

    Returns:
        Configured AuditIntegrityScheduler instance.

    Example:
        scheduler = create_audit_scheduler(
            audit_service=audit_service,
            schedule_hours=settings.audit_scheduler_hours,
            alert_callback=notification_router.send,
        )
        await scheduler.start()
    """
    return AuditIntegrityScheduler(
        audit_service=audit_service,
        schedule_hours=schedule_hours,
        alert_callback=alert_callback,
        metrics=metrics,
        alert_detector=alert_detector,
    )
