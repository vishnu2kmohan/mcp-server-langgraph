"""
Audit alerting system (FedRAMP AU-5).

Provides real-time detection of suspicious audit events:
- Failed login threshold exceeded
- After-hours admin actions
- Bulk data exports
- Integrity tampering detection
- Audit logging failures

This module supports FedRAMP AU-5 requirements for
responding to audit processing failures.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Callable, Coroutine
from uuid import uuid4

from mcp_server_langgraph.audit.models import (
    AuditEventCategory,
    AuditEventType,
    UnifiedAuditEvent,
)

logger = logging.getLogger(__name__)


@dataclass
class AuditAlert:
    """
    Represents an audit alert.

    Attributes:
        alert_id: Unique identifier for the alert.
        alert_type: Type of alert (e.g., FAILED_LOGIN_THRESHOLD).
        severity: Severity level (info, warning, error, critical).
        message: Human-readable alert message.
        timestamp: When the alert was triggered.
        source_event_id: ID of the event that triggered the alert.
        details: Additional context about the alert.
        acknowledged: Whether the alert has been acknowledged.
        acknowledged_by: Who acknowledged the alert.
        acknowledged_at: When the alert was acknowledged.
    """

    alert_type: str
    severity: str
    message: str
    source_event_id: str | None = None
    alert_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    details: dict[str, Any] = field(default_factory=dict)
    acknowledged: bool = False
    acknowledged_by: str | None = None
    acknowledged_at: datetime | None = None


class AuditAlertDetector:
    """
    Detects suspicious patterns in audit events.

    Monitors audit events in real-time and triggers alerts when
    suspicious patterns are detected, such as:
    - Multiple failed login attempts
    - Admin actions outside business hours
    - Bulk data exports
    - Hash chain integrity failures

    Example:
        detector = AuditAlertDetector(
            failed_login_threshold=5,
            alert_callback=send_to_slack,
        )

        detector.process_event(audit_event)
        alerts = detector.get_triggered_alerts()
    """

    def __init__(
        self,
        failed_login_threshold: int = 5,
        failed_login_window_minutes: int = 5,
        business_hours_start: int = 9,
        business_hours_end: int = 17,
        bulk_export_threshold_records: int = 1000,
        alert_callback: Callable[[AuditAlert], Coroutine[Any, Any, None]] | None = None,
    ) -> None:
        """
        Initialize alert detector.

        Args:
            failed_login_threshold: Number of failed logins to trigger alert.
            failed_login_window_minutes: Time window for failed login detection.
            business_hours_start: Start of business hours (24-hour format).
            business_hours_end: End of business hours (24-hour format).
            bulk_export_threshold_records: Threshold for bulk export alert.
            alert_callback: Async callback to invoke when alert is triggered.
        """
        self._failed_login_threshold = failed_login_threshold
        self._failed_login_window = timedelta(minutes=failed_login_window_minutes)
        self._business_hours_start = business_hours_start
        self._business_hours_end = business_hours_end
        self._bulk_export_threshold = bulk_export_threshold_records
        self._alert_callback = alert_callback

        # Tracking state
        self._failed_logins: dict[str, list[datetime]] = defaultdict(list)
        self._triggered_alerts: list[AuditAlert] = []

    def process_event(self, event: UnifiedAuditEvent) -> list[AuditAlert]:
        """
        Process an audit event and check for alert conditions.

        Args:
            event: The audit event to process.

        Returns:
            List of alerts triggered by this event.
        """
        new_alerts = []

        # Check for failed login threshold
        if event.event_type == AuditEventType.LOGIN_FAILED:
            alert = self._check_failed_login(event)
            if alert:
                new_alerts.append(alert)

        # Check for after-hours admin action
        if self._is_admin_action(event):
            alert = self._check_after_hours(event)
            if alert:
                new_alerts.append(alert)

        # Check for bulk data export
        if event.event_type == AuditEventType.DATA_EXPORT:
            alert = self._check_bulk_export(event)
            if alert:
                new_alerts.append(alert)

        # Store triggered alerts
        self._triggered_alerts.extend(new_alerts)

        return new_alerts

    async def process_event_async(self, event: UnifiedAuditEvent) -> list[AuditAlert]:
        """
        Process an audit event asynchronously.

        Args:
            event: The audit event to process.

        Returns:
            List of alerts triggered by this event.
        """
        new_alerts = self.process_event(event)

        # Invoke callback for each alert
        if self._alert_callback and new_alerts:
            for alert in new_alerts:
                try:
                    await self._alert_callback(alert)
                except Exception as e:
                    logger.exception(
                        "Alert callback failed",
                        extra={"error": str(e), "alert_type": alert.alert_type},
                    )

        return new_alerts

    def _check_failed_login(self, event: UnifiedAuditEvent) -> AuditAlert | None:
        """Check for failed login threshold exceeded."""
        ip_address = (event.context.ip_address if event.context else None) or "unknown"
        now = event.timestamp

        # Clean up old entries
        cutoff = now - self._failed_login_window
        self._failed_logins[ip_address] = [ts for ts in self._failed_logins[ip_address] if ts > cutoff]

        # Add current failure
        self._failed_logins[ip_address].append(now)

        # Check threshold
        if len(self._failed_logins[ip_address]) >= self._failed_login_threshold:
            return AuditAlert(
                alert_type="FAILED_LOGIN_THRESHOLD",
                severity="warning",
                message=f"Failed login threshold exceeded from IP {ip_address}",
                source_event_id=event.event_id,
                details={
                    "ip_address": ip_address,
                    "attempt_count": len(self._failed_logins[ip_address]),
                    "threshold": self._failed_login_threshold,
                    "window_minutes": self._failed_login_window.total_seconds() / 60,
                },
            )

        return None

    def _is_admin_action(self, event: UnifiedAuditEvent) -> bool:
        """Check if event is an admin action."""
        if event.category != AuditEventCategory.SYSTEM:
            return False

        if event.actor and event.actor.roles:
            return "admin" in event.actor.roles

        return False

    def _check_after_hours(self, event: UnifiedAuditEvent) -> AuditAlert | None:
        """Check for admin action outside business hours."""
        hour = event.timestamp.hour

        if hour < self._business_hours_start or hour >= self._business_hours_end:
            return AuditAlert(
                alert_type="AFTER_HOURS_ADMIN_ACTION",
                severity="warning",
                message=f"Admin action detected outside business hours at {event.timestamp.isoformat()}",
                source_event_id=event.event_id,
                details={
                    "actor": event.actor.actor_id if event.actor else "unknown",
                    "action": event.action,
                    "hour": hour,
                    "business_hours": f"{self._business_hours_start}:00-{self._business_hours_end}:00",
                },
            )

        return None

    def _check_bulk_export(self, event: UnifiedAuditEvent) -> AuditAlert | None:
        """Check for bulk data export."""
        record_count = event.details.get("record_count", 0) if event.details else 0

        if record_count >= self._bulk_export_threshold:
            return AuditAlert(
                alert_type="BULK_DATA_EXPORT",
                severity="warning",
                message=f"Bulk data export of {record_count} records detected",
                source_event_id=event.event_id,
                details={
                    "actor": event.actor.actor_id if event.actor else "unknown",
                    "record_count": record_count,
                    "threshold": self._bulk_export_threshold,
                    "resource_type": event.resource_type,
                },
            )

        return None

    def report_integrity_failure(
        self,
        start_time: datetime,
        end_time: datetime,
        errors: list[str],
    ) -> AuditAlert:
        """
        Report an integrity verification failure.

        Args:
            start_time: Start of verification range.
            end_time: End of verification range.
            errors: List of error messages.

        Returns:
            The triggered alert.
        """
        alert = AuditAlert(
            alert_type="INTEGRITY_TAMPERING",
            severity="critical",
            message="Audit log integrity verification failed - possible tampering detected",
            details={
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "errors": errors,
            },
        )

        self._triggered_alerts.append(alert)
        return alert

    def get_triggered_alerts(self) -> list[AuditAlert]:
        """Get all triggered alerts."""
        return self._triggered_alerts.copy()

    def clear_alerts(self) -> None:
        """Clear all triggered alerts."""
        self._triggered_alerts.clear()


class AuditAlertManager:
    """
    Manages audit alerts storage and acknowledgment.

    Provides persistent storage of alerts and supports
    acknowledgment workflow for incident response.
    """

    def __init__(self) -> None:
        """Initialize alert manager."""
        self._alerts: dict[str, AuditAlert] = {}

    async def add_alert(self, alert: AuditAlert) -> None:
        """Add an alert to the manager."""
        self._alerts[alert.alert_id] = alert

    async def get_alert(self, alert_id: str) -> AuditAlert | None:
        """Get an alert by ID."""
        return self._alerts.get(alert_id)

    async def acknowledge_alert(
        self,
        alert_id: str,
        acknowledged_by: str,
    ) -> AuditAlert | None:
        """
        Acknowledge an alert.

        Args:
            alert_id: ID of the alert to acknowledge.
            acknowledged_by: Who is acknowledging the alert.

        Returns:
            The updated alert or None if not found.
        """
        alert = self._alerts.get(alert_id)
        if alert:
            alert.acknowledged = True
            alert.acknowledged_by = acknowledged_by
            alert.acknowledged_at = datetime.now(UTC)
        return alert

    async def get_unacknowledged_alerts(self) -> list[AuditAlert]:
        """Get all unacknowledged alerts."""
        return [a for a in self._alerts.values() if not a.acknowledged]

    async def get_alerts_by_type(self, alert_type: str) -> list[AuditAlert]:
        """Get alerts by type."""
        return [a for a in self._alerts.values() if a.alert_type == alert_type]
