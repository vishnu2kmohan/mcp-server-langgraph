"""
Alert WebSocket Handler.

Provides real-time alert streaming using the standardized WebSocketBase class.

Features:
    - Subscribe to alert stream
    - Get recent alerts
    - Real-time alert push notifications
    - Admin-only access (enforced via OpenFGA)

Message Types (Client -> Server):
    - subscribe: Subscribe to alert stream
    - unsubscribe: Unsubscribe from alert stream
    - get_recent: Get recent alerts

Response Types (Server -> Client):
    - subscribed: Subscription confirmed
    - unsubscribed: Unsubscription confirmed
    - recent_alerts: List of recent alerts
    - alert: Real-time alert notification
    - error: Error message
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from mcp_server_langgraph.websocket.base import WebSocketBase
from mcp_server_langgraph.websocket.mixins import BroadcasterMixin
from mcp_server_langgraph.websocket.types import (
    AuthUser,
    MessageEnvelope,
    WebSocketConfig,
)

if TYPE_CHECKING:
    from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

logger = logging.getLogger(__name__)


@runtime_checkable
class AlertBroadcasterProtocol(Protocol):
    """Protocol defining the alert broadcaster interface.

    This protocol is intentionally flexible to support both the actual
    AlertBroadcaster implementation and test mocks.
    """

    async def subscribe(self, connection: Any, user_id: str) -> None:
        """Subscribe to alerts.

        Args:
            connection: WebSocket connection (FastAPI WebSocket or WebSocketConnection)
            user_id: User ID (required by broadcaster)
        """
        ...

    async def unsubscribe(self, connection: Any) -> None:
        """Unsubscribe from alerts."""
        ...

    async def get_recent_alerts(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent alerts from internal buffer.

        Args:
            limit: Maximum number of alerts to return.

        Returns:
            List of recent alerts as dictionaries.
        """
        ...


class AlertHandler(WebSocketBase, BroadcasterMixin):
    """
    WebSocket handler for real-time alert streaming.

    Extends WebSocketBase to provide alert streaming with the
    standardized infrastructure (auth, rate limiting, metrics, etc.).

    Usage:
        handler = AlertHandler(
            config=WebSocketConfig(
                endpoint_name="alerts",
                require_auth=True,
                authz_resource_type="dashboard",
                authz_resource_id="alerts",
                authz_required_relation="admin",
            ),
            broadcaster=get_alert_broadcaster(),
        )
        await handler.run(websocket)
    """

    def __init__(
        self,
        config: WebSocketConfig,
        broadcaster: AlertBroadcasterProtocol,
        metrics: WebSocketMetrics | None = None,
    ) -> None:
        """
        Initialize the alert handler.

        Args:
            config: WebSocket configuration.
            broadcaster: Alert broadcaster for managing subscriptions.
            metrics: Optional metrics collector.
        """
        super().__init__(config=config, metrics=metrics)
        self._broadcaster = broadcaster
        # Note: _subscribed is managed by BroadcasterMixin

    async def on_connect(self, user: AuthUser) -> None:
        """
        Handle connection establishment.

        Args:
            user: The authenticated user.
        """
        logger.info(
            f"Alert stream connected: user={user.id}",
            extra={"user_id": user.id},
        )

    async def on_disconnect(self) -> None:
        """Clean up on disconnect."""
        # Use BroadcasterMixin's unsubscribe() for cleanup
        await self.unsubscribe()
        logger.info(
            f"Alert stream disconnected: user={self.user_id}",
            extra={"user_id": self.user_id},
        )

    async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
        """
        Handle incoming messages.

        Supports:
        - subscribe: Subscribe to alert stream
        - unsubscribe: Unsubscribe from alert stream
        - get_recent: Get recent alerts

        Args:
            message: The incoming message envelope.

        Returns:
            Response message or None.
        """
        if message.type == "subscribe":
            return await self._handle_subscribe(message)
        elif message.type == "unsubscribe":
            return await self._handle_unsubscribe(message)
        elif message.type == "get_recent":
            return await self._handle_get_recent(message)
        else:
            return MessageEnvelope(
                type="error",
                payload={
                    "code": "unknown_message_type",
                    "message": f"Unknown message type: {message.type}",
                },
                id=message.id,
            )

    async def _handle_subscribe(self, message: MessageEnvelope) -> MessageEnvelope:
        """Handle subscribe message."""
        if self._websocket and not self._subscribed:
            # Use BroadcasterMixin's subscribe() with user_id kwarg
            await self.subscribe(user_id=self.user_id or "")

        return self.create_subscribed_response(correlation_id=message.id)

    async def _handle_unsubscribe(self, message: MessageEnvelope) -> MessageEnvelope:
        """Handle unsubscribe message."""
        # Use BroadcasterMixin's unsubscribe()
        await self.unsubscribe()

        return self.create_unsubscribed_response(correlation_id=message.id)

    async def _handle_get_recent(self, message: MessageEnvelope) -> MessageEnvelope:
        """Handle get_recent message."""
        payload = message.payload or {}
        limit = payload.get("limit", 10)

        try:
            alerts = await self._broadcaster.get_recent_alerts(limit=limit)

            return MessageEnvelope(
                type="recent_alerts",
                payload={"alerts": alerts, "count": len(alerts)},
                id=message.id,
            )

        except Exception as e:
            logger.warning(f"Error getting recent alerts: {e}")
            return MessageEnvelope(
                type="error",
                payload={
                    "code": "get_recent_failed",
                    "message": str(e),
                },
                id=message.id,
            )

    async def push_alert(self, alert: dict[str, Any]) -> None:
        """
        Push an alert to the client.

        Only sends if the client is subscribed.

        Args:
            alert: The alert data to send.
        """
        await self.send_if_subscribed(
            {
                "type": "alert",
                "payload": alert,
            }
        )
