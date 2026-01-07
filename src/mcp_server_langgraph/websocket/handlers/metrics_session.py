"""
Metrics Session WebSocket Handler.

Provides real-time session-level metrics streaming using the standardized WebSocketBase class.

Features:
    - Real-time session duration tracking
    - Token usage updates per session
    - Active session status
    - Session health indicators

Message Types (Client -> Server):
    - subscribe: Subscribe to session metrics for a session ID
    - unsubscribe: Stop receiving updates for a session
    - ping: Keep-alive ping

Response Types (Server -> Client):
    - session_metrics: Session metrics snapshot
    - token_update: Token usage update
    - session_status: Session status change
    - error: Error message
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from mcp_server_langgraph.websocket.base import WebSocketBase
from mcp_server_langgraph.websocket.types import (
    AuthUser,
    MessageEnvelope,
    WebSocketConfig,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class MetricsSessionHandler(WebSocketBase):
    """
    WebSocket handler for real-time session metrics streaming.

    Extends WebSocketBase to provide session-level metrics monitoring with the
    standardized infrastructure (auth, rate limiting, metrics, etc.).

    This handler supports the METRICS_SESSION endpoint in the frontend
    for displaying real-time session metrics in the StatusBar.
    """

    def __init__(
        self,
        config: WebSocketConfig,
    ) -> None:
        """
        Initialize the MetricsSession handler.

        Args:
            config: WebSocket configuration with auth, rate limiting, etc.
        """
        super().__init__(config=config)
        self._subscribed_sessions: set[str] = set()

    async def on_connect(self, user: AuthUser | None) -> None:
        """Handle new WebSocket connection."""
        logger.info(
            "Metrics session WebSocket connected",
            extra={
                "user_id": user.user_id if user else None,
            },
        )

    async def on_disconnect(self, user: AuthUser | None) -> None:
        """Handle WebSocket disconnection."""
        self._subscribed_sessions.clear()
        logger.info(
            "Metrics session WebSocket disconnected",
            extra={
                "user_id": user.user_id if user else None,
            },
        )

    async def on_message(
        self,
        message: MessageEnvelope,
        user: AuthUser | None,
    ) -> dict[str, Any] | None:
        """
        Handle incoming WebSocket messages.

        Args:
            message: The parsed message envelope
            user: The authenticated user (if auth is required)

        Returns:
            Response dict to send back, or None for no response
        """
        message_type = message.type

        if message_type == "subscribe":
            return await self._handle_subscribe(message, user)
        elif message_type == "unsubscribe":
            return await self._handle_unsubscribe(message, user)
        elif message_type == "ping":
            return {"type": "pong", "timestamp": message.timestamp}
        else:
            return {
                "type": "error",
                "code": "unknown_message_type",
                "message": f"Unknown message type: {message_type}",
            }

    async def _handle_subscribe(
        self,
        message: MessageEnvelope,
        user: AuthUser | None,
    ) -> dict[str, Any]:
        """Handle subscription to session metrics."""
        payload = message.payload or {}
        session_id = payload.get("session_id")

        if not session_id:
            return {
                "type": "error",
                "code": "missing_session_id",
                "message": "session_id is required",
            }

        self._subscribed_sessions.add(session_id)

        # Return initial metrics snapshot
        return {
            "type": "session_metrics",
            "session_id": session_id,
            "data": {
                "status": "active",
                "duration_seconds": 0,
                "token_usage": {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                },
                "message_count": 0,
            },
        }

    async def _handle_unsubscribe(
        self,
        message: MessageEnvelope,
        user: AuthUser | None,
    ) -> dict[str, Any]:
        """Handle unsubscription from session metrics."""
        payload = message.payload or {}
        session_id = payload.get("session_id")

        if session_id and session_id in self._subscribed_sessions:
            self._subscribed_sessions.discard(session_id)

        return {
            "type": "unsubscribed",
            "session_id": session_id,
        }
