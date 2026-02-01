"""
LLM Streaming WebSocket Handler.

Provides real-time LLM response streaming using the standardized WebSocketBase class.

Features:
    - Real-time token streaming from LLM responses
    - Active stream tracking
    - Stream cancellation support
    - Token counting and metrics

Message Types (Client -> Server):
    - subscribe_stream: Subscribe to a streaming request by ID
    - unsubscribe_stream: Stop receiving stream updates
    - cancel_stream: Cancel an active stream
    - ping: Keep-alive ping

Response Types (Server -> Client):
    - stream_token: Token chunk from LLM response
    - stream_complete: Stream completion with metrics
    - stream_error: Stream error
    - stream_cancelled: Stream cancellation confirmation
    - error: Error message
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from mcp_server_langgraph.websocket.base import WebSocketBase
from mcp_server_langgraph.websocket.types import (
    AuthUser,
    MessageEnvelope,
    WebSocketConfig,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class LLMStreamingHandler(WebSocketBase):
    """
    WebSocket handler for real-time LLM streaming.

    Extends WebSocketBase to provide LLM response streaming with the
    standardized infrastructure (auth, rate limiting, metrics, etc.).

    This handler supports the LLM_STREAMING endpoint in the frontend
    for displaying real-time streaming tokens in the DevTools LLMStreamingTab.
    """

    def __init__(
        self,
        config: WebSocketConfig,
    ) -> None:
        """
        Initialize the LLMStreaming handler.

        Args:
            config: WebSocket configuration with auth, rate limiting, etc.
        """
        super().__init__(config=config)
        self._subscribed_streams: set[str] = set()

    async def on_connect(self, user: AuthUser) -> None:
        """Handle new WebSocket connection.

        Args:
            user: The authenticated user.
        """
        logger.info(
            "LLM streaming WebSocket connected",
            extra={
                "user_id": user.id,
            },
        )

    async def on_disconnect(self) -> None:
        """Handle WebSocket disconnection."""
        self._subscribed_streams.clear()
        user_id = self._user.id if self._user else None
        logger.info(
            "LLM streaming WebSocket disconnected",
            extra={
                "user_id": user_id,
            },
        )

    async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
        """
        Handle incoming WebSocket messages.

        Args:
            message: The parsed message envelope.

        Returns:
            Response MessageEnvelope, or None for no response.
        """
        message_type = message.type

        if message_type == "subscribe_stream":
            return await self._handle_subscribe(message)
        elif message_type == "unsubscribe_stream":
            return await self._handle_unsubscribe(message)
        elif message_type == "cancel_stream":
            return await self._handle_cancel(message)
        elif message_type == "ping":
            return MessageEnvelope(
                type="pong",
                payload={"timestamp": message.timestamp},
            )
        else:
            return MessageEnvelope(
                type="error",
                payload={
                    "code": "unknown_message_type",
                    "message": f"Unknown message type: {message_type}",
                },
            )

    async def _handle_subscribe(self, message: MessageEnvelope) -> MessageEnvelope:
        """Handle subscription to an LLM stream."""
        payload = message.payload or {}
        stream_id = payload.get("stream_id")

        if not stream_id:
            return MessageEnvelope(
                type="error",
                payload={
                    "code": "missing_stream_id",
                    "message": "stream_id is required",
                },
            )

        self._subscribed_streams.add(stream_id)

        return self.create_subscribed_response(
            extra_payload={"stream_id": stream_id},
        )

    async def _handle_unsubscribe(self, message: MessageEnvelope) -> MessageEnvelope:
        """Handle unsubscription from an LLM stream."""
        payload = message.payload or {}
        stream_id = payload.get("stream_id")

        if stream_id and stream_id in self._subscribed_streams:
            self._subscribed_streams.discard(stream_id)

        return self.create_unsubscribed_response(
            extra_payload={"stream_id": stream_id},
        )

    async def _handle_cancel(self, message: MessageEnvelope) -> MessageEnvelope:
        """Handle cancellation of an LLM stream."""
        payload = message.payload or {}
        stream_id = payload.get("stream_id")

        if not stream_id:
            return MessageEnvelope(
                type="error",
                payload={
                    "code": "missing_stream_id",
                    "message": "stream_id is required for cancellation",
                },
            )

        # Remove from subscriptions
        self._subscribed_streams.discard(stream_id)

        return MessageEnvelope(
            type="stream_cancelled",
            payload={"stream_id": stream_id},
        )
