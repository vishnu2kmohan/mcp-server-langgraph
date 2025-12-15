"""
Audit alert notification integrations.

Provides notification channels for audit alerts:
- Slack webhook integration
- PagerDuty Events API v2 integration
- Notification routing for severity-based delivery

This module supports FedRAMP AU-5 requirements for
alerting personnel to audit processing failures.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

import httpx

from mcp_server_langgraph.audit.alerts import AuditAlert

logger = logging.getLogger(__name__)

# Severity levels in order of priority
SEVERITY_LEVELS = ["info", "warning", "error", "critical"]


def severity_meets_threshold(severity: str, min_severity: str) -> bool:
    """Check if severity meets minimum threshold."""
    try:
        severity_idx = SEVERITY_LEVELS.index(severity)
        min_idx = SEVERITY_LEVELS.index(min_severity)
        return severity_idx >= min_idx
    except ValueError:
        return True  # Unknown severity, allow through


class AlertNotifier(ABC):
    """Abstract base class for alert notifiers."""

    min_severity: str = "info"

    @abstractmethod
    async def send(self, alert: AuditAlert) -> bool:
        """
        Send an alert notification.

        Args:
            alert: The audit alert to send.

        Returns:
            True if sent successfully, False otherwise.
        """
        ...


class SlackNotifier(AlertNotifier):
    """
    Slack webhook notifier for audit alerts.

    Sends alerts to a Slack channel via incoming webhook.

    Example:
        notifier = SlackNotifier(
            webhook_url="https://hooks.slack.com/services/xxx",
        )
        await notifier.send(alert)
    """

    def __init__(
        self,
        webhook_url: str,
        channel: str | None = None,
        username: str = "Audit Alerts",
        icon_emoji: str = ":warning:",
        min_severity: str = "info",
    ) -> None:
        """
        Initialize Slack notifier.

        Args:
            webhook_url: Slack incoming webhook URL.
            channel: Optional channel override.
            username: Bot username.
            icon_emoji: Bot icon emoji.
            min_severity: Minimum severity to send.
        """
        self.webhook_url = webhook_url
        self.channel = channel
        self.username = username
        self.icon_emoji = icon_emoji
        self.min_severity = min_severity

    def format_message(self, alert: AuditAlert) -> dict[str, Any]:
        """
        Format alert as Slack message.

        Args:
            alert: The audit alert to format.

        Returns:
            Slack message payload.
        """
        # Severity color mapping
        color_map = {
            "info": "#36a64f",
            "warning": "#ffc107",
            "error": "#ff5722",
            "critical": "#dc3545",
        }

        color = color_map.get(alert.severity, "#808080")

        # Build attachment
        attachment = {
            "color": color,
            "title": f":rotating_light: {alert.alert_type}",
            "text": alert.message,
            "fields": [
                {
                    "title": "Severity",
                    "value": alert.severity.upper(),
                    "short": True,
                },
                {
                    "title": "Time",
                    "value": alert.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "short": True,
                },
            ],
            "footer": "Audit Alert System",
            "ts": int(alert.timestamp.timestamp()),
        }

        # Add details if present
        if alert.details:
            fields_list: list[dict[str, Any]] = attachment["fields"]  # type: ignore[assignment]
            for key, value in list(alert.details.items())[:3]:  # Limit to 3 fields
                fields_list.append(
                    {
                        "title": key.replace("_", " ").title(),
                        "value": str(value)[:100],  # Truncate long values
                        "short": True,
                    }
                )

        message: dict[str, Any] = {
            "text": f"Audit Alert: {alert.alert_type} ({alert.severity})",
            "username": self.username,
            "icon_emoji": self.icon_emoji,
            "attachments": [attachment],
        }

        if self.channel:
            message["channel"] = self.channel

        return message

    async def send(self, alert: AuditAlert) -> bool:
        """
        Send alert to Slack.

        Args:
            alert: The audit alert to send.

        Returns:
            True if sent successfully, False otherwise.
        """
        if not severity_meets_threshold(alert.severity, self.min_severity):
            logger.debug(
                "Alert severity below threshold, skipping Slack notification",
                extra={"alert_type": alert.alert_type, "severity": alert.severity},
            )
            return True

        try:
            message = self.format_message(alert)

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.webhook_url,
                    json=message,
                    timeout=10.0,
                )

                if response.status_code == 200:
                    logger.info(
                        "Alert sent to Slack",
                        extra={"alert_type": alert.alert_type},
                    )
                    return True
                else:
                    logger.error(
                        "Slack webhook failed",
                        extra={
                            "status_code": response.status_code,
                            "alert_type": alert.alert_type,
                        },
                    )
                    return False

        except Exception as e:
            logger.exception(
                "Failed to send alert to Slack",
                extra={"error": str(e), "alert_type": alert.alert_type},
            )
            return False


class PagerDutyNotifier(AlertNotifier):
    """
    PagerDuty Events API v2 notifier for critical alerts.

    Sends alerts to PagerDuty for incident management.

    Example:
        notifier = PagerDutyNotifier(
            routing_key="your-integration-key",
            service_name="audit-service",
        )
        await notifier.send(alert)
    """

    EVENTS_API_URL = "https://events.pagerduty.com/v2/enqueue"

    def __init__(
        self,
        routing_key: str,
        service_name: str = "Audit Service",
        min_severity: str = "critical",
    ) -> None:
        """
        Initialize PagerDuty notifier.

        Args:
            routing_key: PagerDuty integration/routing key.
            service_name: Service name for the alert source.
            min_severity: Minimum severity to send (default: critical).
        """
        self.routing_key = routing_key
        self.service_name = service_name
        self.min_severity = min_severity

    def format_event(self, alert: AuditAlert) -> dict[str, Any]:
        """
        Format alert as PagerDuty Events API v2 payload.

        Args:
            alert: The audit alert to format.

        Returns:
            PagerDuty event payload.
        """
        # Map our severity to PagerDuty severity
        pd_severity_map = {
            "info": "info",
            "warning": "warning",
            "error": "error",
            "critical": "critical",
        }

        return {
            "routing_key": self.routing_key,
            "event_action": "trigger",
            "dedup_key": alert.alert_id,
            "payload": {
                "summary": f"[{alert.alert_type}] {alert.message}",
                "severity": pd_severity_map.get(alert.severity, "error"),
                "source": self.service_name,
                "timestamp": alert.timestamp.isoformat(),
                "custom_details": {
                    "alert_id": alert.alert_id,
                    "alert_type": alert.alert_type,
                    **(alert.details or {}),
                },
            },
            "client": "Unified Audit System",
            "client_url": "",
        }

    async def send(self, alert: AuditAlert) -> bool:
        """
        Send alert to PagerDuty.

        Args:
            alert: The audit alert to send.

        Returns:
            True if sent successfully, False otherwise.
        """
        if not severity_meets_threshold(alert.severity, self.min_severity):
            logger.debug(
                "Alert severity below threshold, skipping PagerDuty notification",
                extra={"alert_type": alert.alert_type, "severity": alert.severity},
            )
            return True

        try:
            payload = self.format_event(alert)

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.EVENTS_API_URL,
                    json=payload,
                    timeout=10.0,
                )

                if response.status_code == 202:
                    logger.info(
                        "Alert sent to PagerDuty",
                        extra={"alert_type": alert.alert_type},
                    )
                    return True
                else:
                    logger.error(
                        "PagerDuty API failed",
                        extra={
                            "status_code": response.status_code,
                            "alert_type": alert.alert_type,
                        },
                    )
                    return False

        except Exception as e:
            logger.exception(
                "Failed to send alert to PagerDuty",
                extra={"error": str(e), "alert_type": alert.alert_type},
            )
            return False


class NotificationRouter:
    """
    Routes alerts to multiple notification channels.

    Sends alerts to all configured notifiers, filtering by severity.

    Example:
        router = NotificationRouter(notifiers=[
            SlackNotifier(webhook_url="..."),
            PagerDutyNotifier(routing_key="..."),
        ])

        await router.send_all(alert)
    """

    def __init__(self, notifiers: list[AlertNotifier] | None = None) -> None:
        """
        Initialize notification router.

        Args:
            notifiers: List of alert notifiers.
        """
        self.notifiers = notifiers or []

    def add_notifier(self, notifier: AlertNotifier) -> None:
        """Add a notifier to the router."""
        self.notifiers.append(notifier)

    async def send_all(self, alert: AuditAlert) -> list[bool]:
        """
        Send alert to all notifiers.

        Args:
            alert: The audit alert to send.

        Returns:
            List of success/failure results for each notifier.
        """
        results = []

        for notifier in self.notifiers:
            try:
                result = await notifier.send(alert)
                results.append(result)
            except Exception as e:
                logger.exception(
                    "Notifier failed",
                    extra={
                        "notifier": type(notifier).__name__,
                        "error": str(e),
                    },
                )
                results.append(False)

        return results


def create_notification_callback(
    router: NotificationRouter,
) -> Any:
    """
    Create an async callback for the alert detector.

    Args:
        router: The notification router to use.

    Returns:
        Async callback function for AuditAlertDetector.
    """

    async def callback(alert: AuditAlert) -> None:
        await router.send_all(alert)

    return callback
