"""
HEART Metrics WebSocket Handler.

Provides real-time HEART metrics streaming using the standardized WebSocketBase class.

HEART Framework Dimensions:
- Happiness: User satisfaction (NPS, CSAT)
- Engagement: User activity levels
- Adoption: Feature adoption rates
- Retention: User retention metrics
- Task Success: Task completion rates

Features:
    - Real-time HEART metrics updates
    - Configurable time ranges
    - Subscribe to specific dimensions
    - Threshold alerts

Message Types (Client -> Server):
    - set_time_range: Set the time range for metrics (e.g., "24h", "7d", "30d")
    - subscribe_dimension: Subscribe to updates for a specific dimension
    - unsubscribe_dimension: Unsubscribe from a dimension

Response Types (Server -> Client):
    - metrics_snapshot: Full HEART metrics snapshot
    - dimension_update: Update for a specific dimension
    - threshold_alert: Alert when a metric crosses a threshold
    - unsubscribed: Confirmation of unsubscription
    - error: Error message
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from mcp_server_langgraph.websocket.base import WebSocketBase
from mcp_server_langgraph.websocket.types import (
    AuthUser,
    MessageEnvelope,
    WebSocketConfig,
)

if TYPE_CHECKING:
    from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

logger = logging.getLogger(__name__)

# Valid HEART dimensions
HEART_DIMENSIONS = {"happiness", "engagement", "adoption", "retention", "task_success"}

# Valid time ranges
VALID_TIME_RANGES = {"1h", "6h", "24h", "7d", "30d", "90d"}


@runtime_checkable
class HeartMetricsServiceProtocol(Protocol):
    """Protocol defining the HEART metrics service interface."""

    async def get_current_snapshot(self, time_range: str = "24h") -> dict[str, Any]:
        """Get current HEART metrics snapshot."""
        ...

    async def get_dimension_metrics(self, dimension: str, time_range: str = "24h") -> dict[str, Any]:
        """Get metrics for a specific dimension."""
        ...


class HeartMetricsHandler(WebSocketBase):
    """
    WebSocket handler for real-time HEART metrics streaming.

    Extends WebSocketBase to provide HEART metrics monitoring with the
    standardized infrastructure (auth, rate limiting, metrics, etc.).

    This handler replaces the polling-based approach in useHeartDashboard.ts
    with efficient push-based updates.

    Usage:
        handler = HeartMetricsHandler(
            config=WebSocketConfig(
                endpoint_name="heart-metrics",
                require_auth=True,
                authz_resource_type="observability",
                authz_resource_id="heart",
                authz_required_relation="viewer",
            ),
            metrics_service=get_heart_metrics_service(),
        )
        await handler.run(websocket)
    """

    def __init__(
        self,
        config: WebSocketConfig,
        metrics_service: HeartMetricsServiceProtocol,
        metrics: WebSocketMetrics | None = None,
    ) -> None:
        """
        Initialize the HEART metrics handler.

        Args:
            config: WebSocket configuration.
            metrics_service: HEART metrics service for data retrieval.
            metrics: Optional metrics collector.
        """
        super().__init__(config=config, metrics=metrics)
        self._metrics_service = metrics_service
        self.time_range: str = "24h"
        self.subscribed_dimensions: set[str] = set()

    async def on_connect(self, user: AuthUser) -> None:
        """
        Handle connection establishment.

        Sends the initial HEART metrics snapshot to the client.

        Args:
            user: The authenticated user.
        """
        # Send initial metrics snapshot
        snapshot = await self._metrics_service.get_current_snapshot(self.time_range)

        if self._websocket:
            await self._websocket.send_json(
                {
                    "type": "metrics_snapshot",
                    "metrics": snapshot,
                    "time_range": self.time_range,
                }
            )

    async def on_disconnect(self) -> None:
        """Clean up subscriptions on disconnect."""
        self.subscribed_dimensions.clear()

    async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
        """
        Handle incoming messages.

        Supports:
        - set_time_range: Update the time range for metrics
        - subscribe_dimension: Subscribe to a specific dimension
        - unsubscribe_dimension: Unsubscribe from a dimension

        Args:
            message: The incoming message envelope.

        Returns:
            Response message or None.
        """
        if message.type == "set_time_range":
            return await self._handle_set_time_range(message)
        elif message.type == "subscribe_dimension":
            return await self._handle_subscribe_dimension(message)
        elif message.type == "unsubscribe_dimension":
            return await self._handle_unsubscribe_dimension(message)
        else:
            return MessageEnvelope(
                type="error",
                payload={
                    "code": "unknown_message_type",
                    "message": f"Unknown message type: {message.type}",
                },
                id=message.id,
            )

    async def _handle_set_time_range(self, message: MessageEnvelope) -> MessageEnvelope:
        """Handle set_time_range message."""
        payload = message.payload or {}
        time_range = payload.get("time_range", "24h")

        if time_range not in VALID_TIME_RANGES:
            return MessageEnvelope(
                type="error",
                payload={
                    "code": "invalid_time_range",
                    "message": f"Invalid time range: {time_range}. Valid: {VALID_TIME_RANGES}",
                },
                id=message.id,
            )

        self.time_range = time_range

        # Get fresh snapshot with new time range
        snapshot = await self._metrics_service.get_current_snapshot(self.time_range)

        return MessageEnvelope(
            type="metrics_snapshot",
            payload={
                "metrics": snapshot,
                "time_range": self.time_range,
            },
            id=message.id,
        )

    async def _handle_subscribe_dimension(self, message: MessageEnvelope) -> MessageEnvelope:
        """Handle subscribe_dimension message."""
        payload = message.payload or {}
        dimension = payload.get("dimension")

        if not dimension:
            return MessageEnvelope(
                type="error",
                payload={
                    "code": "missing_dimension",
                    "message": "dimension is required for subscribe_dimension",
                },
                id=message.id,
            )

        if dimension not in HEART_DIMENSIONS:
            return MessageEnvelope(
                type="error",
                payload={
                    "code": "invalid_dimension",
                    "message": f"Invalid dimension: {dimension}. Valid: {HEART_DIMENSIONS}",
                },
                id=message.id,
            )

        self.subscribed_dimensions.add(dimension)

        # Get current metrics for the dimension
        dimension_metrics = await self._metrics_service.get_dimension_metrics(dimension, self.time_range)

        return MessageEnvelope(
            type="dimension_update",
            payload={
                "dimension": dimension,
                "metrics": dimension_metrics,
            },
            id=message.id,
        )

    async def _handle_unsubscribe_dimension(self, message: MessageEnvelope) -> MessageEnvelope:
        """Handle unsubscribe_dimension message."""
        payload = message.payload or {}
        dimension = payload.get("dimension")

        if dimension:
            self.subscribed_dimensions.discard(dimension)

        return MessageEnvelope(
            type="unsubscribed",
            payload={"dimension": dimension},
            id=message.id,
        )

    async def push_dimension_update(self, dimension: str, metrics: dict[str, Any]) -> None:
        """
        Push a dimension update to the client if subscribed.

        Args:
            dimension: The dimension being updated.
            metrics: The updated metrics data.
        """
        if dimension not in self.subscribed_dimensions:
            return

        if self._websocket:
            await self.send(
                MessageEnvelope(
                    type="dimension_update",
                    payload={
                        "dimension": dimension,
                        "metrics": metrics,
                    },
                )
            )

    async def push_threshold_alert(self, dimension: str, threshold: str, current_value: float) -> None:
        """
        Push a threshold alert to the client.

        Args:
            dimension: The dimension that crossed the threshold.
            threshold: The threshold type (e.g., "low", "critical").
            current_value: The current value of the metric.
        """
        if self._websocket:
            await self.send(
                MessageEnvelope(
                    type="threshold_alert",
                    payload={
                        "dimension": dimension,
                        "threshold": threshold,
                        "current_value": current_value,
                    },
                )
            )
