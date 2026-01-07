"""
HEART Metrics WebSocket Endpoint.

Provides real-time HEART metrics streaming replacing polling-based
useHeartDashboard.ts with efficient push-based updates.

URL: /api/v1/ws/metrics/heart

Message Types (Client → Server):
- get_snapshot: Request current metrics snapshot
- set_time_range: Set the time range for metrics
- subscribe_dimension: Subscribe to updates for a dimension
- unsubscribe_dimension: Unsubscribe from dimension updates

Message Types (Server → Client):
- metrics_snapshot: Full HEART metrics snapshot
- dimension_update: Single dimension update
- threshold_alert: Alert when threshold is crossed
- subscribed: Confirmation of dimension subscription
- unsubscribed: Confirmation of dimension unsubscription
- time_range_updated: Confirmation of time range change
- error: Error message
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, WebSocket

from mcp_server_langgraph.websocket.base import WebSocketBase
from mcp_server_langgraph.websocket.services.heart_metrics import (
    HeartMetricsServiceAdapter,
    get_websocket_heart_metrics_service,
)
from mcp_server_langgraph.websocket.types import AuthUser, MessageEnvelope, WebSocketConfig

logger = logging.getLogger(__name__)

# =============================================================================
# Router
# =============================================================================

router = APIRouter(tags=["websocket", "metrics"])


# =============================================================================
# HEART Dimensions
# =============================================================================

HEART_DIMENSIONS = ["happiness", "engagement", "adoption", "retention", "task_success"]


# =============================================================================
# Handler
# =============================================================================


class HeartMetricsWebSocketHandler(WebSocketBase):
    """
    WebSocket handler for real-time HEART metrics streaming.

    Replaces polling-based useHeartDashboard.ts with efficient
    push-based updates using the WebSocketBase infrastructure.
    """

    def __init__(self) -> None:
        """Initialize the handler with configuration."""
        config = WebSocketConfig(
            endpoint_name="heart-metrics",
            require_auth=True,
            heartbeat_interval=30,
            idle_timeout=3600,  # 1 hour for dashboard sessions
            rate_limit_per_minute=60,  # 1 msg/sec for dashboard updates
        )
        super().__init__(config)

        # Subscription state
        self._subscribed_dimensions: set[str] = set()
        self._time_range: str = "24h"

        # Initialize metrics service adapter (integrates with Prometheus/Mimir)
        self._metrics_service: HeartMetricsServiceAdapter = get_websocket_heart_metrics_service()

    async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
        """
        Handle incoming WebSocket messages.

        Args:
            message: The incoming message envelope.

        Returns:
            Response message or None.
        """
        message_type = message.type

        if message_type == "get_snapshot":
            return await self._handle_get_snapshot(message)
        elif message_type == "set_time_range":
            return await self._handle_set_time_range(message)
        elif message_type == "subscribe_dimension":
            return await self._handle_subscribe_dimension(message)
        elif message_type == "unsubscribe_dimension":
            return await self._handle_unsubscribe_dimension(message)
        else:
            logger.warning(f"Unknown message type: {message_type}")
            return MessageEnvelope(
                type="error",
                payload={"message": f"Unknown message type: {message_type}"},
                id=message.id,
            )

    async def _handle_get_snapshot(self, message: MessageEnvelope) -> MessageEnvelope:
        """Handle get_snapshot message - returns current metrics."""
        time_range = message.payload.get("time_range", self._time_range) if message.payload else self._time_range
        self._time_range = time_range

        snapshot = await self._get_metrics_snapshot(time_range)

        return MessageEnvelope(
            type="metrics_snapshot",
            payload={
                "snapshot": snapshot,
                "time_range": time_range,
            },
            id=message.id,
        )

    async def _handle_set_time_range(self, message: MessageEnvelope) -> MessageEnvelope:
        """Handle set_time_range message."""
        time_range = message.payload.get("time_range", "24h") if message.payload else "24h"
        self._time_range = time_range

        return MessageEnvelope(
            type="time_range_updated",
            payload={"time_range": time_range},
            id=message.id,
        )

    async def _handle_subscribe_dimension(self, message: MessageEnvelope) -> MessageEnvelope:
        """Handle subscribe_dimension message."""
        dimension = message.payload.get("dimension") if message.payload else None

        if not dimension:
            return MessageEnvelope(
                type="error",
                payload={"message": "dimension is required"},
                id=message.id,
            )

        if dimension not in HEART_DIMENSIONS:
            return MessageEnvelope(
                type="error",
                payload={"message": f"Invalid dimension: {dimension}"},
                id=message.id,
            )

        self._subscribed_dimensions.add(dimension)

        return MessageEnvelope(
            type="subscribed",
            payload={"dimension": dimension},
            id=message.id,
        )

    async def _handle_unsubscribe_dimension(self, message: MessageEnvelope) -> MessageEnvelope:
        """Handle unsubscribe_dimension message."""
        dimension = message.payload.get("dimension") if message.payload else None

        if dimension:
            self._subscribed_dimensions.discard(dimension)

        return MessageEnvelope(
            type="unsubscribed",
            payload={"dimension": dimension},
            id=message.id,
        )

    async def _get_metrics_snapshot(self, time_range: str) -> dict[str, Any]:
        """
        Get current HEART metrics snapshot from the metrics service.

        Delegates to HeartMetricsServiceAdapter which queries Prometheus/Mimir
        for actual metrics when available, falling back to stub data for development.
        """
        return await self._metrics_service.get_current_snapshot(time_range)

    async def on_connect(self, user: AuthUser) -> None:
        """Called when connection is established."""
        logger.info(
            "HEART metrics WebSocket connected",
            extra={"user_id": user.id},
        )

    async def on_disconnect(self) -> None:
        """Called when connection is closed."""
        self._subscribed_dimensions.clear()
        logger.info(
            "HEART metrics WebSocket disconnected",
            extra={"user_id": self._user.id if self._user else "unknown"},
        )


# =============================================================================
# WebSocket Route
# =============================================================================


@router.websocket("")
async def heart_metrics_websocket(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for real-time HEART metrics streaming.

    Replaces polling-based useHeartDashboard.ts with efficient
    push-based updates.
    """
    handler = HeartMetricsWebSocketHandler()
    await handler.run(websocket)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "router",
    "HeartMetricsWebSocketHandler",
    "HEART_DIMENSIONS",
]
