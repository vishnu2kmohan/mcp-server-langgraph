"""
Alert Broadcasting for Real-Time Admin Notifications.

Provides real-time streaming of infrastructure alerts to connected Admin WebSocket clients.

Features:
- Subscribe/unsubscribe pattern for WebSocket connections
- Admin-only access (caller must verify admin role)
- Severity filtering (critical/warning only - no info/error alerts)
- Broadcast to all admin subscribers
- Graceful handling of disconnected clients
- Thread-safe subscriber management

Message Format:
    {
        "type": "alert",
        "payload": {
            "alert_id": "string",
            "name": "string",
            "severity": "critical" | "warning",
            "state": "pending" | "firing" | "resolved" | "silenced",
            "message": "string",
            "labels": { ... },
            "annotations": { ... },
            "started_at": "ISO8601 timestamp",
            "ended_at": "ISO8601 timestamp" | null,
            "duration_ms": number | null,
            "generator_url": "string" | null
        }
    }

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

from opentelemetry import trace

from mcp_server_langgraph.alerts.executor import ExecutionResult
from mcp_server_langgraph.alerts.metrics import (
    record_websocket_message,
    update_websocket_connections,
)
from mcp_server_langgraph.observability.query.interfaces import (
    Alert,
    AlertSeverity,
)

if TYPE_CHECKING:
    from mcp_server_langgraph.alerts.routing import AlertRouter, RoutingResult
    from mcp_server_langgraph.notifications.push_sender import PushNotificationSender

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

# Allowed severity levels for admin alerts (user-confirmed requirement)
ALLOWED_SEVERITIES = {AlertSeverity.CRITICAL, AlertSeverity.WARNING}


class WebSocketConnection(Protocol):
    """Protocol for WebSocket connections."""

    async def send_json(self, data: dict[str, Any]) -> None:
        """Send JSON data to the WebSocket."""
        ...


@dataclass
class AlertSubscriber:
    """A WebSocket subscriber for alert streaming."""

    connection: WebSocketConnection
    user_id: str


def alert_to_message(alert: Alert) -> dict[str, Any]:
    """
    Convert an Alert dataclass to WebSocket message format.

    Args:
        alert: The Alert to convert.

    Returns:
        Dictionary in the expected WebSocket message format.
    """
    payload: dict[str, Any] = {
        "alert_id": alert.alert_id,
        "name": alert.name,
        "severity": alert.severity.value,
        "state": alert.state.value,
        "message": alert.message,
        "labels": alert.labels,
        "annotations": alert.annotations,
        "started_at": alert.started_at.isoformat() if alert.started_at else None,
        "ended_at": alert.ended_at.isoformat() if alert.ended_at else None,
        "duration_ms": alert.duration_ms,
        "generator_url": alert.generator_url,
    }

    return {
        "type": "alert",
        "payload": payload,
    }


def execution_result_to_message(result: ExecutionResult) -> dict[str, Any]:
    """
    Convert an ExecutionResult to WebSocket message format.

    Args:
        result: The ExecutionResult to convert.

    Returns:
        Dictionary in the expected WebSocket message format.
    """
    payload: dict[str, Any] = {
        "remediation_id": result.remediation_id,
        "success": result.success,
        "exit_code": result.exit_code,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "executed_at": result.executed_at,
        "duration_ms": result.duration_ms,
        "error_message": result.error_message,
    }

    return {
        "type": "execution_result",
        "payload": payload,
    }


class AlertBroadcaster:
    """
    Broadcasts infrastructure alerts to subscribed Admin WebSocket connections.

    Provides real-time alert streaming for:
    - Circuit breaker alerts
    - HTTP pool exhaustion alerts
    - LLM provider throttling alerts
    - Retry exhaustion alerts
    - Other resilience-related alerts

    Only critical and warning severity alerts are broadcast (per user requirements).
    Info-level alerts are filtered out.

    Optionally integrates with PushNotificationSender to send push notifications
    for critical alerts when users are not connected to WebSocket.
    """

    def __init__(
        self,
        push_sender: PushNotificationSender | None = None,
        router: AlertRouter | None = None,
    ) -> None:
        """
        Initialize the broadcaster.

        Args:
            push_sender: Optional push notification sender for critical alerts.
            router: Optional AlertRouter for multi-tenant routing and subscriptions.
        """
        self._subscribers: list[AlertSubscriber] = []
        self._lock = asyncio.Lock()
        self._push_sender = push_sender
        self._router = router
        # Buffer for recent alerts (for get_recent_alerts)
        self._recent_alerts: list[dict[str, Any]] = []
        self._max_recent_alerts: int = 100

    @property
    def subscriber_count(self) -> int:
        """Get the number of active subscribers."""
        return len(self._subscribers)

    def get_subscriber_count_for_user(self, user_id: str) -> int:
        """
        Get the number of active subscriptions for a specific user.

        Args:
            user_id: The user ID to check.

        Returns:
            Number of connections for the user.
        """
        return sum(1 for s in self._subscribers if s.user_id == user_id)

    async def get_recent_alerts(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Get recent alerts from internal buffer.

        Args:
            limit: Maximum number of alerts to return.

        Returns:
            List of recent alerts as dictionaries.
        """
        return self._recent_alerts[-limit:] if limit > 0 else self._recent_alerts.copy()

    def _store_recent_alert(self, alert_dict: dict[str, Any]) -> None:
        """
        Store an alert in the recent alerts buffer.

        Args:
            alert_dict: Alert dictionary to store.
        """
        self._recent_alerts.append(alert_dict)
        # Keep buffer size limited
        if len(self._recent_alerts) > self._max_recent_alerts:
            self._recent_alerts = self._recent_alerts[-self._max_recent_alerts:]

    async def subscribe(
        self,
        connection: WebSocketConnection,
        user_id: str,
    ) -> None:
        """
        Subscribe an admin WebSocket connection to alerts.

        Args:
            connection: The WebSocket connection to subscribe.
            user_id: The admin user ID (caller must verify admin role).
        """
        async with self._lock:
            subscriber = AlertSubscriber(
                connection=connection,
                user_id=user_id,
            )
            self._subscribers.append(subscriber)
            # Update WebSocket connections gauge
            update_websocket_connections(self.subscriber_count)
            logger.info(f"Alert subscriber added. User: {user_id}. Total: {self.subscriber_count}")

    async def unsubscribe(self, connection: WebSocketConnection) -> None:
        """
        Unsubscribe a WebSocket connection.

        Args:
            connection: The WebSocket connection to unsubscribe.
        """
        async with self._lock:
            self._subscribers = [s for s in self._subscribers if s.connection != connection]
            # Update WebSocket connections gauge
            update_websocket_connections(self.subscriber_count)
            logger.info(f"Alert subscriber removed. Total: {self.subscriber_count}")

    async def broadcast_alert(self, alert: Alert) -> None:
        """
        Broadcast an alert to admin subscribers.

        Only critical and warning severity alerts are broadcast.
        Info and error severity alerts are filtered out.

        If a router is configured:
        - Routes the alert to determine target tenants
        - Filters subscribers by routing subscriptions
        - Respects routing rules that may filter out alerts

        For critical alerts, also sends push notifications if push_sender is configured.

        Args:
            alert: The alert to broadcast.
        """
        with tracer.start_as_current_span(
            "alert.broadcast",
            attributes={
                "alert.id": alert.alert_id,
                "alert.name": alert.name,
                "alert.severity": alert.severity.value,
                "alert.state": alert.state.value,
                "alert.subscriber_count": self.subscriber_count,
            },
        ) as span:
            # Filter by severity (only critical and warning)
            if alert.severity not in ALLOWED_SEVERITIES:
                logger.debug(f"Filtering alert {alert.alert_id} with severity {alert.severity.value}")
                span.set_attribute("alert.filtered", True)
                span.set_attribute("alert.filter_reason", "severity")
                return

            # Route the alert if router is configured
            routing_result: RoutingResult | None = None
            subscribed_user_ids: set[str] | None = None

            if self._router is not None:
                try:
                    # Convert Alert to routing format and route
                    routing_result = await self._router.route_async(self._convert_to_routing_alert(alert))

                    # If routing filtered out the alert, don't broadcast
                    if not routing_result.routed:
                        logger.debug(f"Alert {alert.alert_id} filtered by routing rules")
                        span.set_attribute("alert.filtered", True)
                        span.set_attribute("alert.filter_reason", "routing")
                        return

                    # Get subscribed users from routing result
                    if routing_result.subscribed_users:
                        subscribed_user_ids = set(routing_result.subscribed_users)
                        logger.debug(f"Alert {alert.alert_id} routed to {len(subscribed_user_ids)} users")
                        span.set_attribute("alert.routed_users", len(subscribed_user_ids))

                except Exception as e:
                    logger.warning(f"Router error for alert {alert.alert_id}, falling back to all: {e}")
                    span.record_exception(e)
                    # On router error, fall back to broadcasting to all subscribers

            # Send push notification for critical alerts
            if self._push_sender and alert.severity == AlertSeverity.CRITICAL:
                try:
                    push_count = await self._push_sender.send_critical_alert(alert)
                    logger.info(f"Sent push notification for critical alert {alert.alert_id} to {push_count} subscribers")
                    span.set_attribute("alert.push_sent", push_count)
                except Exception as e:
                    logger.warning(f"Failed to send push notification for alert {alert.alert_id}: {e}")
                    span.record_exception(e)

            if not self._subscribers:
                span.set_attribute("alert.broadcast_count", 0)
                return

            message = alert_to_message(alert)

            # Add routing metadata to message if available
            if routing_result and routing_result.tenant_id:
                message["payload"]["tenant_id"] = routing_result.tenant_id
                span.set_attribute("alert.tenant_id", routing_result.tenant_id)

            failed_connections: list[WebSocketConnection] = []

            async with self._lock:
                broadcast_count = 0
                for subscriber in self._subscribers:
                    # Filter by subscription if router provided subscribed users
                    if subscribed_user_ids is not None:
                        if subscriber.user_id not in subscribed_user_ids:
                            continue

                    try:
                        await subscriber.connection.send_json(message)
                        # Record message sent metric
                        record_websocket_message("alert")
                        broadcast_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to send alert to subscriber {subscriber.user_id}: {e}")
                        failed_connections.append(subscriber.connection)

                span.set_attribute("alert.broadcast_count", broadcast_count)
                span.set_attribute("alert.failed_count", len(failed_connections))

                # Remove failed connections
                if failed_connections:
                    self._subscribers = [s for s in self._subscribers if s.connection not in failed_connections]
                    # Update connections gauge after removing failed
                    update_websocket_connections(self.subscriber_count)
                    logger.info(f"Removed {len(failed_connections)} failed subscribers. Remaining: {self.subscriber_count}")

    def _convert_to_routing_alert(self, alert: Alert) -> Any:
        """
        Convert observability Alert to routing Alert format.

        Args:
            alert: Observability Alert instance.

        Returns:
            Routing Alert instance.
        """
        from datetime import UTC, datetime

        from mcp_server_langgraph.alerts.routing import Alert as RoutingAlert

        return RoutingAlert(
            alert_id=alert.alert_id,
            name=alert.name,
            severity=alert.severity.value,
            labels=alert.labels,
            message=alert.message,
            started_at=alert.started_at or datetime.now(UTC),
            acknowledged=False,
        )

    async def broadcast_alert_update(
        self,
        alert: Alert,
        update_type: str = "update",
    ) -> None:
        """
        Broadcast an alert update (state change, resolution, etc.).

        Args:
            alert: The updated alert.
            update_type: Type of update ("update", "resolved", "silenced").
        """
        with tracer.start_as_current_span(
            "alert.broadcast_update",
            attributes={
                "alert.id": alert.alert_id,
                "alert.name": alert.name,
                "alert.severity": alert.severity.value,
                "alert.update_type": update_type,
            },
        ) as span:
            if alert.severity not in ALLOWED_SEVERITIES:
                span.set_attribute("alert.filtered", True)
                return

            if not self._subscribers:
                span.set_attribute("alert.broadcast_count", 0)
                return

            message = alert_to_message(alert)
            message["update_type"] = update_type

            failed_connections: list[WebSocketConnection] = []
            broadcast_count = 0

            async with self._lock:
                for subscriber in self._subscribers:
                    try:
                        await subscriber.connection.send_json(message)
                        # Record message sent metric
                        record_websocket_message("alert_update")
                        broadcast_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to send alert update to {subscriber.user_id}: {e}")
                        failed_connections.append(subscriber.connection)

                span.set_attribute("alert.broadcast_count", broadcast_count)
                span.set_attribute("alert.failed_count", len(failed_connections))

                if failed_connections:
                    self._subscribers = [s for s in self._subscribers if s.connection not in failed_connections]
                    # Update connections gauge after removing failed
                    update_websocket_connections(self.subscriber_count)

    async def broadcast_execution_result(self, result: ExecutionResult) -> None:
        """
        Broadcast a remediation execution result to all admin subscribers.

        Args:
            result: The execution result to broadcast.
        """
        if not self._subscribers:
            return

        message = execution_result_to_message(result)
        failed_connections: list[WebSocketConnection] = []

        async with self._lock:
            for subscriber in self._subscribers:
                try:
                    await subscriber.connection.send_json(message)
                    # Record message sent metric
                    record_websocket_message("execution_result")
                except Exception as e:
                    logger.warning(f"Failed to send execution result to {subscriber.user_id}: {e}")
                    failed_connections.append(subscriber.connection)

            # Remove failed connections
            if failed_connections:
                self._subscribers = [s for s in self._subscribers if s.connection not in failed_connections]
                # Update connections gauge after removing failed
                update_websocket_connections(self.subscriber_count)
                logger.info(f"Removed {len(failed_connections)} failed subscribers. Remaining: {self.subscriber_count}")
