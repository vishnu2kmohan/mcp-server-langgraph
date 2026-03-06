"""
Alertmanager Webhook Receiver.

Receives alerts from Prometheus Alertmanager and broadcasts them to Admin WebSocket clients.

Features:
- Parse Alertmanager v4 webhook payload format
- Filter alerts by severity (critical/warning only)
- Broadcast to AlertBroadcaster for real-time WebSocket streaming
- Queue AI recommendation generation for critical alerts
- Handle resolved alerts

Usage:
    Configure Alertmanager to send webhooks to:
    POST /api/v1/webhooks/alertmanager

Alertmanager Configuration Example:
    receivers:
      - name: 'admin-alerts'
        webhook_configs:
          - url: 'http://mcp-server:8000/api/v1/webhooks/alertmanager'
            send_resolved: true

Reference:
- ADR-0026 - Comprehensive Client Resilience Patterns
- https://prometheus.io/docs/alerting/latest/configuration/#webhook_config
"""

import logging
from datetime import UTC, datetime
from typing import Any, Protocol

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from mcp_server_langgraph.alerts.broadcaster import AlertBroadcaster
from mcp_server_langgraph.alerts.metrics import (
    record_alert_broadcast,
    record_alert_filtered,
    record_alert_received,
)
from mcp_server_langgraph.websocket.registry import get_alert_broadcaster
from mcp_server_langgraph.api.v1.alert_recommendations import AlertStore, get_alert_store
from mcp_server_langgraph.observability.query.interfaces import (
    Alert,
    AlertSeverity,
    AlertState,
)

logger = logging.getLogger(__name__)

alertmanager_webhook_router = APIRouter(tags=["webhooks"])

# Allowed severity levels for broadcast (user-confirmed requirement)
ALLOWED_SEVERITIES = {AlertSeverity.CRITICAL, AlertSeverity.WARNING}

# Only pre-compute AI recommendations for critical alerts
AI_RECOMMENDATION_SEVERITIES = {AlertSeverity.CRITICAL}


class AIRecommendationQueue(Protocol):
    """Protocol for AI recommendation queue."""

    async def queue_recommendation(self, alert: Alert) -> None:
        """Queue an alert for AI recommendation generation."""
        ...


def _parse_severity(severity_label: str | None) -> AlertSeverity:
    """
    Parse severity label to AlertSeverity enum.

    Args:
        severity_label: Severity string from Alertmanager labels.

    Returns:
        AlertSeverity enum value.
    """
    if not severity_label:
        return AlertSeverity.WARNING

    severity_map = {
        "critical": AlertSeverity.CRITICAL,
        "warning": AlertSeverity.WARNING,
        "info": AlertSeverity.INFO,
        "error": AlertSeverity.ERROR,
    }

    return severity_map.get(severity_label.lower(), AlertSeverity.WARNING)


def _parse_state(status: str) -> AlertState:
    """
    Parse Alertmanager status to AlertState enum.

    Args:
        status: Status string from Alertmanager ("firing" or "resolved").

    Returns:
        AlertState enum value.
    """
    if status == "resolved":
        return AlertState.RESOLVED
    return AlertState.FIRING


def _parse_timestamp(timestamp_str: str | None) -> datetime | None:
    """
    Parse ISO8601 timestamp from Alertmanager.

    Args:
        timestamp_str: ISO8601 timestamp string.

    Returns:
        datetime object or None if parsing fails.
    """
    if not timestamp_str:
        return None

    # Alertmanager uses "0001-01-01T00:00:00Z" to indicate no end time
    if timestamp_str.startswith("0001-01-01"):
        return None

    try:
        # Handle various ISO8601 formats
        # Remove trailing Z and add UTC timezone
        if timestamp_str.endswith("Z"):
            timestamp_str = timestamp_str[:-1] + "+00:00"

        return datetime.fromisoformat(timestamp_str).replace(tzinfo=UTC)
    except (ValueError, TypeError):
        logger.warning(f"Failed to parse timestamp: {timestamp_str}")
        return None


def parse_alertmanager_payload(payload: dict[str, Any]) -> list[Alert]:
    """
    Parse Alertmanager v4 webhook payload into Alert objects.

    Args:
        payload: Alertmanager webhook payload.

    Returns:
        List of Alert objects.
    """
    alerts: list[Alert] = []

    for alert_data in payload.get("alerts", []):
        labels = alert_data.get("labels", {})
        annotations = alert_data.get("annotations", {})

        alert = Alert(
            alert_id=alert_data.get("fingerprint", "unknown"),
            name=labels.get("alertname", "Unknown"),
            severity=_parse_severity(labels.get("severity")),
            state=_parse_state(alert_data.get("status", "firing")),
            message=annotations.get("description", annotations.get("summary", "")),
            labels=labels,
            annotations=annotations,
            started_at=_parse_timestamp(alert_data.get("startsAt")),
            ended_at=_parse_timestamp(alert_data.get("endsAt")),
            generator_url=alert_data.get("generatorURL"),
        )

        alerts.append(alert)

    return alerts


def filter_alerts_for_broadcast(alerts: list[Alert]) -> list[Alert]:
    """
    Filter alerts to only include critical and warning severity.

    Args:
        alerts: List of all parsed alerts.

    Returns:
        Filtered list containing only critical and warning alerts.
    """
    return [a for a in alerts if a.severity in ALLOWED_SEVERITIES]


async def handle_alertmanager_webhook(
    payload: dict[str, Any],
    broadcaster: AlertBroadcaster,
    alert_store: AlertStore | None = None,
    ai_recommendation_queue: AIRecommendationQueue | None = None,
) -> dict[str, Any]:
    """
    Handle incoming Alertmanager webhook.

    Parses the payload, filters alerts, broadcasts to admin clients,
    stores alerts for recommendation lookup, and queues AI recommendations.

    Args:
        payload: Alertmanager webhook payload.
        broadcaster: AlertBroadcaster instance.
        alert_store: Optional AlertStore for persisting alerts.
        ai_recommendation_queue: Optional queue for AI recommendations.

    Returns:
        Response dict with processing statistics.
    """
    # Parse alerts from payload
    all_alerts = parse_alertmanager_payload(payload)

    # Record metrics for all received alerts
    for alert in all_alerts:
        record_alert_received(alert.severity.value, alert.state.value)

    # Filter for broadcast (critical/warning only)
    filtered_alerts = filter_alerts_for_broadcast(all_alerts)

    # Record metrics for filtered (excluded) alerts
    filtered_out = [a for a in all_alerts if a.severity not in ALLOWED_SEVERITIES]
    for alert in filtered_out:
        record_alert_filtered(alert.severity.value, "severity_not_allowed")

    # Store alerts for recommendation lookup
    if alert_store:
        for alert in filtered_alerts:
            await alert_store.add_alert(alert)

    # Broadcast each filtered alert
    broadcast_count = 0
    client_count = broadcaster.subscriber_count if hasattr(broadcaster, "subscriber_count") else 0
    for alert in filtered_alerts:
        await broadcaster.broadcast_alert(alert)
        broadcast_count += 1
        # Record broadcast metric with client count
        record_alert_broadcast(alert.severity.value, client_count)

    # Queue AI recommendations for critical alerts
    ai_queued = 0
    if ai_recommendation_queue:
        for alert in filtered_alerts:
            if alert.severity in AI_RECOMMENDATION_SEVERITIES:
                await ai_recommendation_queue.queue_recommendation(alert)
                ai_queued += 1

    logger.info(
        f"Processed Alertmanager webhook: received={len(all_alerts)}, broadcast={broadcast_count}, ai_queued={ai_queued}"
    )

    return {
        "status": "ok",
        "alerts_received": len(all_alerts),
        "alerts_broadcast": broadcast_count,
        "ai_recommendations_queued": ai_queued,
    }


class AlertmanagerWebhookResponse(BaseModel):
    """Response model for Alertmanager webhook."""

    status: str
    alerts_received: int
    alerts_broadcast: int
    ai_recommendations_queued: int


@alertmanager_webhook_router.post(
    "/webhooks/alertmanager",
    summary="Receive alerts from Alertmanager",
    description="Webhook endpoint for Prometheus Alertmanager to push alerts.",
)
async def alertmanager_webhook(
    payload: dict[str, Any],
    broadcaster: AlertBroadcaster = Depends(get_alert_broadcaster),
    alert_store: AlertStore = Depends(get_alert_store),
) -> AlertmanagerWebhookResponse:
    """
    Receive and process alerts from Alertmanager.

    This endpoint:
    1. Parses the Alertmanager webhook payload
    2. Filters alerts to critical/warning severity only
    3. Stores alerts for recommendation lookup
    4. Broadcasts filtered alerts to Admin WebSocket clients
    5. Queues AI recommendations for critical alerts

    Configure Alertmanager to send webhooks to this endpoint.
    """
    try:
        result = await handle_alertmanager_webhook(
            payload=payload,
            broadcaster=broadcaster,
            alert_store=alert_store,
            ai_recommendation_queue=None,  # Will be injected when AI service is ready
        )
        return AlertmanagerWebhookResponse(**result)

    except Exception as e:
        logger.error(f"Error processing Alertmanager webhook: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process webhook: {str(e)}",
        )
