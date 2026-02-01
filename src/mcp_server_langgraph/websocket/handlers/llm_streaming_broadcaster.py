"""
LLM Streaming Broadcaster.

Provides real-time WebSocket broadcasting of LLM streaming metrics:
- Streaming start/completion events
- First chunk with TTFC (Time To First Chunk)
- Per-chunk metrics with inter-chunk latency
- Session-scoped filtering

This bridges the gap where streaming metrics are recorded to Prometheus
but not pushed to WebSocket for real-time DevTools visibility.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from starlette.websockets import WebSocket

    from mcp_server_langgraph.websocket.handlers.metrics_broadcaster import (
        MetricsBroadcaster,
    )

logger = logging.getLogger(__name__)


class LLMStreamingBroadcaster:
    """
    Broadcasts LLM streaming events to WebSocket subscribers.

    Provides real-time visibility into:
    - Stream lifecycle (started, completed)
    - TTFC (Time To First Chunk)
    - Per-chunk metrics
    - Inter-chunk latency

    Integrates with MetricsBroadcaster for metric recording.
    """

    def __init__(
        self,
        metrics_broadcaster: MetricsBroadcaster | None = None,
    ) -> None:
        """
        Initialize the LLM streaming broadcaster.

        Args:
            metrics_broadcaster: Optional MetricsBroadcaster for emitting metrics.
        """
        self._subscribers: dict[WebSocket, str] = {}  # ws -> session_id
        self._metrics_broadcaster = metrics_broadcaster

    @property
    def subscriber_count(self) -> int:
        """Return the number of active subscribers."""
        return len(self._subscribers)

    async def subscribe(
        self,
        websocket: WebSocket,
        session_id: str,
    ) -> None:
        """
        Subscribe a WebSocket to streaming events.

        Args:
            websocket: The WebSocket connection.
            session_id: Session ID for filtering events.
        """
        self._subscribers[websocket] = session_id
        logger.debug(
            "LLM streaming subscriber added",
            extra={"session_id": session_id, "subscriber_count": self.subscriber_count},
        )

    async def unsubscribe(self, websocket: WebSocket) -> None:
        """
        Unsubscribe a WebSocket from streaming events.

        Args:
            websocket: The WebSocket connection to remove.
        """
        if websocket in self._subscribers:
            session_id = self._subscribers.pop(websocket)
            logger.debug(
                "LLM streaming subscriber removed",
                extra={
                    "session_id": session_id,
                    "subscriber_count": self.subscriber_count,
                },
            )

    async def _broadcast(
        self,
        message: dict[str, Any],
        session_id: str,
    ) -> None:
        """
        Broadcast a message to subscribers matching the session_id.

        Args:
            message: The message to broadcast.
            session_id: Session ID to filter subscribers.
        """
        failed_sockets: list[WebSocket] = []

        for ws, sub_session_id in self._subscribers.items():
            if sub_session_id != session_id:
                continue

            try:
                await ws.send_json(message)
            except Exception as e:
                logger.warning(
                    "Failed to send LLM streaming message",
                    extra={"error": str(e), "session_id": session_id},
                )
                failed_sockets.append(ws)

        # Clean up failed sockets
        for ws in failed_sockets:
            await self.unsubscribe(ws)

    async def broadcast_streaming_started(
        self,
        stream_id: str,
        session_id: str,
        model: str,
        provider: str,
    ) -> None:
        """
        Broadcast streaming started event.

        Args:
            stream_id: Unique identifier for this stream.
            session_id: Session ID for filtering.
            model: LLM model being used.
            provider: LLM provider (openai, anthropic, etc.).
        """
        message = {
            "type": "streaming_started",
            "payload": {
                "stream_id": stream_id,
                "session_id": session_id,
                "model": model,
                "provider": provider,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        }
        await self._broadcast(message, session_id)

    async def broadcast_first_chunk(
        self,
        stream_id: str,
        session_id: str,
        ttfc_ms: float,
        chunk_size: int,
        model: str | None = None,
        provider: str | None = None,
    ) -> None:
        """
        Broadcast first chunk received event with TTFC.

        Args:
            stream_id: Unique identifier for this stream.
            session_id: Session ID for filtering.
            ttfc_ms: Time To First Chunk in milliseconds.
            chunk_size: Size of the first chunk in characters/tokens.
            model: Optional LLM model for metric labeling.
            provider: Optional LLM provider for metric labeling.
        """
        message = {
            "type": "first_chunk",
            "payload": {
                "stream_id": stream_id,
                "session_id": session_id,
                "ttfc_ms": ttfc_ms,
                "chunk_size": chunk_size,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        }
        await self._broadcast(message, session_id)

        # Also emit TTFC metric to MetricsBroadcaster if available
        if self._metrics_broadcaster and model and provider:
            await self._metrics_broadcaster.broadcast_metric(
                name="llm_streaming_ttfc_ms",
                value=ttfc_ms,
                labels={"model": model, "provider": provider},
                session_id=session_id,
            )

    async def broadcast_chunk_received(
        self,
        stream_id: str,
        session_id: str,
        chunk_index: int,
        chunk_size: int,
        inter_chunk_latency_ms: float,
    ) -> None:
        """
        Broadcast chunk received event.

        Args:
            stream_id: Unique identifier for this stream.
            session_id: Session ID for filtering.
            chunk_index: Index of this chunk (0-based).
            chunk_size: Size of the chunk in characters/tokens.
            inter_chunk_latency_ms: Time since previous chunk in milliseconds.
        """
        message = {
            "type": "chunk_received",
            "payload": {
                "stream_id": stream_id,
                "session_id": session_id,
                "chunk_index": chunk_index,
                "chunk_size": chunk_size,
                "inter_chunk_latency_ms": inter_chunk_latency_ms,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        }
        await self._broadcast(message, session_id)

    async def broadcast_streaming_completed(
        self,
        stream_id: str,
        session_id: str,
        status: str,
        total_duration_ms: float,
        total_chunks: int,
        total_tokens: int,
        estimated_cost_usd: float,
    ) -> None:
        """
        Broadcast streaming completed event with final metrics.

        Args:
            stream_id: Unique identifier for this stream.
            session_id: Session ID for filtering.
            status: Completion status (success, error, cancelled).
            total_duration_ms: Total streaming duration in milliseconds.
            total_chunks: Total number of chunks received.
            total_tokens: Total tokens in the response.
            estimated_cost_usd: Estimated cost in USD.
        """
        message = {
            "type": "streaming_completed",
            "payload": {
                "stream_id": stream_id,
                "session_id": session_id,
                "status": status,
                "total_duration_ms": total_duration_ms,
                "total_chunks": total_chunks,
                "total_tokens": total_tokens,
                "estimated_cost_usd": estimated_cost_usd,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        }
        await self._broadcast(message, session_id)


# Singleton instance
_llm_streaming_broadcaster: LLMStreamingBroadcaster | None = None


def get_llm_streaming_broadcaster() -> LLMStreamingBroadcaster:
    """
    Get the singleton LLMStreamingBroadcaster instance.

    Returns:
        The global LLMStreamingBroadcaster instance.
    """
    global _llm_streaming_broadcaster
    if _llm_streaming_broadcaster is None:
        _llm_streaming_broadcaster = LLMStreamingBroadcaster()
    return _llm_streaming_broadcaster


def reset_llm_streaming_broadcaster() -> None:
    """
    Reset the singleton instance (for testing).
    """
    global _llm_streaming_broadcaster
    _llm_streaming_broadcaster = None


# =============================================================================
# WebSocket Handler
# =============================================================================


class LLMStreamingHandler:
    """
    WebSocket handler for real-time LLM streaming events.

    Extends WebSocketBase infrastructure to provide streaming visibility with the
    standardized infrastructure (auth, rate limiting, metrics, etc.).

    Usage:
        handler = LLMStreamingHandler(
            config=WebSocketConfig(
                endpoint_name="llm-streaming",
                require_auth=True,
                authz_resource_type="dashboard",
                authz_resource_id="devtools",
                authz_required_relation="viewer",
            ),
            broadcaster=get_llm_streaming_broadcaster(),
        )
        await handler.run(websocket)
    """

    def __init__(
        self,
        config: Any,  # WebSocketConfig
        broadcaster: LLMStreamingBroadcaster,
    ) -> None:
        """Initialize the LLM streaming handler."""
        self._config = config
        self._broadcaster = broadcaster
        self._websocket: Any = None
        self._session_id: str | None = None

    async def run(self, websocket: Any) -> None:
        """Run the WebSocket handler."""
        handler = _LLMStreamingInnerHandler(
            config=self._config,
            broadcaster=self._broadcaster,
        )
        await handler.run(websocket)


class _LLMStreamingInnerHandler:
    """Inner handler implementing WebSocketBase pattern."""

    def __init__(
        self,
        config: Any,
        broadcaster: LLMStreamingBroadcaster,
    ) -> None:
        self._config = config
        self._broadcaster = broadcaster
        self._websocket: Any = None
        self._session_id: str | None = None
        self._subscribed: bool = False

    async def run(self, websocket: Any) -> None:
        """Run the WebSocket handler loop."""
        import json

        from mcp_server_langgraph.auth.jwt_utils import decode_jwt_token

        self._websocket = websocket
        await websocket.accept()

        # Extract user from token
        token = websocket.query_params.get("token")
        if not token:
            token = websocket.headers.get("Authorization", "").replace("Bearer ", "")

        if token:
            try:
                payload = decode_jwt_token(token)
                if payload:
                    # User auth successful
                    pass
            except Exception:
                pass

        try:
            async for message in websocket.iter_text():
                try:
                    data = json.loads(message)
                    msg_type = data.get("type")

                    if msg_type == "subscribe":
                        self._session_id = data.get("payload", {}).get("session_id")
                        if self._session_id:
                            await self._broadcaster.subscribe(
                                websocket,
                                session_id=self._session_id,
                            )
                            self._subscribed = True
                            await websocket.send_json(
                                {
                                    "type": "subscribed",
                                    "payload": {"session_id": self._session_id},
                                }
                            )

                    elif msg_type == "unsubscribe":
                        if self._subscribed:
                            await self._broadcaster.unsubscribe(websocket)
                            self._subscribed = False
                        await websocket.send_json(
                            {
                                "type": "unsubscribed",
                                "payload": {},
                            }
                        )

                except json.JSONDecodeError as e:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": f"Invalid JSON: {e}",
                        }
                    )
                except Exception as e:
                    logger.exception("Error handling LLM streaming message")
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": str(e),
                        }
                    )

        finally:
            # Clean up subscription
            if self._subscribed:
                await self._broadcaster.unsubscribe(websocket)
