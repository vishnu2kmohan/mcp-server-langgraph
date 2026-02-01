"""
DevTools WebSocket Handler.

Provides real-time console logs and network events for the DevTools panel.

Features:
    - Subscribe to console log events
    - Subscribe to network request events
    - Real-time updates as events occur
    - Context filtering by session/workflow ID

Message Types (Client -> Server):
    - subscribe: Subscribe to console/network events
    - unsubscribe: Unsubscribe from events
    - clear: Clear current entries

Response Types (Server -> Client):
    - subscribed: Successfully subscribed to events
    - unsubscribed: Successfully unsubscribed from events
    - console: Console log entry
    - network: Network request start
    - network_update: Network request completion/update
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
    from fastapi import WebSocket as FastAPIWebSocket

    from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

logger = logging.getLogger(__name__)


# =============================================================================
# Broadcaster Protocol
# =============================================================================


@runtime_checkable
class DevToolsBroadcasterProtocol(Protocol):
    """Protocol defining the DevTools broadcaster interface."""

    async def subscribe(
        self,
        websocket: FastAPIWebSocket,
        user_id: str | None = None,
        context_entity_id: str | None = None,
    ) -> None:
        """Subscribe to DevTools events."""
        ...

    async def unsubscribe(self, websocket: FastAPIWebSocket) -> None:
        """Unsubscribe from DevTools events."""
        ...


# =============================================================================
# Broadcaster Implementation
# =============================================================================


class DevToolsBroadcaster:
    """
    Broadcaster for DevTools console and network events.

    Manages WebSocket subscriptions and broadcasts DevTools events
    to all connected clients.

    Usage:
        broadcaster = DevToolsBroadcaster()

        # Subscribe a client
        await broadcaster.subscribe(websocket, user_id="user-123")

        # Broadcast a console event
        await broadcaster.broadcast_console({
            "level": "info",
            "message": "Test message",
            "timestamp": 1234567890,
            "source": "system",
        })

        # Unsubscribe
        await broadcaster.unsubscribe(websocket)
    """

    def __init__(self) -> None:
        """Initialize the broadcaster."""
        # Map of websocket -> (user_id, context_entity_id)
        self._subscribers: dict[Any, tuple[str | None, str | None]] = {}

    async def subscribe(
        self,
        websocket: Any,
        user_id: str | None = None,
        context_entity_id: str | None = None,
    ) -> None:
        """Subscribe a WebSocket to DevTools events.

        Args:
            websocket: The WebSocket connection
            user_id: Optional user ID for tracking
            context_entity_id: Optional session/workflow ID for filtering
        """
        self._subscribers[websocket] = (user_id, context_entity_id)
        logger.info(
            "Client subscribed to DevTools events",
            extra={
                "user_id": user_id,
                "context_entity_id": context_entity_id,
                "subscriber_count": len(self._subscribers),
            },
        )

    async def unsubscribe(self, websocket: Any) -> None:
        """Unsubscribe a WebSocket from DevTools events.

        Args:
            websocket: The WebSocket connection
        """
        if websocket in self._subscribers:
            user_id, _ = self._subscribers.pop(websocket)
            logger.info(
                "Client unsubscribed from DevTools events",
                extra={"user_id": user_id, "subscriber_count": len(self._subscribers)},
            )

    async def _broadcast(
        self,
        message: dict[str, Any],
        context_entity_id: str | None = None,
    ) -> None:
        """Broadcast a message to subscribers.

        Args:
            message: The message to broadcast
            context_entity_id: Optional context ID for filtering
        """
        failed_subscribers: list[Any] = []
        sent_count = 0
        skipped_count = 0

        msg_type = message.get("type", "unknown")
        total_subscribers = len(self._subscribers)

        for websocket, (user_id, sub_context) in list(self._subscribers.items()):
            # Filter by context if specified
            if sub_context and context_entity_id and sub_context != context_entity_id:
                skipped_count += 1
                continue

            try:
                await websocket.send_json(message)
                sent_count += 1
            except Exception as e:
                logger.warning(
                    "Failed to send to subscriber, removing",
                    extra={"error": str(e)},
                )
                failed_subscribers.append(websocket)

        # Remove failed subscribers
        for ws in failed_subscribers:
            self._subscribers.pop(ws, None)

        logger.debug(
            "DevTools broadcast complete",
            extra={
                "message_type": msg_type,
                "context_entity_id": context_entity_id,
                "total_subscribers": total_subscribers,
                "sent_count": sent_count,
                "skipped_count": skipped_count,
                "failed_count": len(failed_subscribers),
            },
        )

    async def broadcast_console(
        self,
        entry: dict[str, Any],
        context_entity_id: str | None = None,
    ) -> None:
        """Broadcast a console log entry.

        Args:
            entry: Console entry dict with level, message, timestamp, source, etc.
            context_entity_id: Optional session/workflow ID for filtering
        """
        await self._broadcast(
            {
                "type": "console",
                "payload": entry,
            },
            context_entity_id=context_entity_id,
        )

    async def broadcast_network(
        self,
        entry: dict[str, Any],
        context_entity_id: str | None = None,
    ) -> None:
        """Broadcast a network request start event.

        Args:
            entry: Network entry dict with id, method, url, startTime, etc.
            context_entity_id: Optional session/workflow ID for filtering
        """
        await self._broadcast(
            {
                "type": "network",
                "payload": entry,
            },
            context_entity_id=context_entity_id,
        )

    async def broadcast_network_update(
        self,
        update: dict[str, Any],
        context_entity_id: str | None = None,
    ) -> None:
        """Broadcast a network request update/completion.

        Args:
            update: Update dict with id, status, statusCode, duration, etc.
            context_entity_id: Optional session/workflow ID for filtering
        """
        await self._broadcast(
            {
                "type": "network_update",
                "payload": update,
            },
            context_entity_id=context_entity_id,
        )

    async def broadcast_trace_step(
        self,
        step: dict[str, Any],
        context_entity_id: str | None = None,
    ) -> None:
        """Broadcast an agent trace step for DevTools Agent Trace tab.

        Also persists the trace to the database for historical retrieval
        (Phase 4: LangGraph Execution Trace Persistence).

        Args:
            step: Step payload with session_id, name, status, timing, etc.
            context_entity_id: Optional session/workflow ID for filtering
        """
        import asyncio

        logger.info(
            "Broadcasting trace step",
            extra={
                "subscriber_count": len(self._subscribers),
                "node_name": step.get("name"),
                "status": step.get("status"),
                "context_entity_id": context_entity_id,
            },
        )

        # Broadcast to WebSocket subscribers (primary)
        await self._broadcast(
            {
                "type": "trace_step",
                "payload": step,
            },
            context_entity_id=context_entity_id,
        )

        # Persist trace to database (fire-and-forget)
        # This allows historical retrieval via /api/v1/sessions/{id}/agent-execution-trace
        # Store reference to prevent task from being garbage collected (RUF006)
        _task = asyncio.create_task(self._persist_trace_step(step))
        _task.add_done_callback(lambda t: None)  # Suppress "Task exception was never retrieved"

    async def _persist_trace_step(self, step: dict[str, Any]) -> None:
        """Persist a trace step to the database for historical retrieval.

        Phase 4: LangGraph Execution Trace Persistence

        This is called fire-and-forget to avoid blocking the WebSocket broadcast.
        Errors are logged but do not propagate to callers.

        Args:
            step: Trace step payload from broadcast_trace_step
        """
        import uuid
        from datetime import UTC, datetime

        try:
            from mcp_server_langgraph.core.dependencies import (
                get_langgraph_execution_trace_repository,
            )

            repo = get_langgraph_execution_trace_repository()
            if repo is None:
                # Repository not initialized - skip persistence
                return

            # Only persist terminal statuses to avoid duplicate trace_id constraint violations
            # (chat broadcasts reuse the same id for running → completed events)
            status = step.get("status", "running")
            if status not in {"completed", "failed", "skipped"}:
                return

            # Warn if GDPR-required fields are missing
            user_id = step.get("user_id")
            org_id = step.get("organization_id")
            if not user_id or not org_id:
                logger.warning(
                    "Trace step missing user_id or organization_id - GDPR compliance affected",
                    extra={"session_id": step.get("session_id"), "node": step.get("name")},
                )

            # Map WebSocket step payload to database model
            # Support both camelCase (frontend) and snake_case (backend) keys for compatibility
            trace_data = {
                "trace_id": step.get("id") or str(uuid.uuid4()),
                "session_id": step.get("session_id", ""),
                "run_id": step.get("run_id") or str(uuid.uuid4()),
                "workflow_id": step.get("workflow_id"),
                "user_id": user_id or "unknown",
                "organization_id": org_id or "unknown",
                "node_id": step.get("node_id"),
                "node_name": step.get("name", "unknown"),
                "node_type": step.get("node_type"),
                "status": status,
                # Support both snake_case and camelCase keys
                "start_time": step.get("start_time") or step.get("startTime") or int(datetime.now(UTC).timestamp() * 1000),
                "end_time": step.get("end_time") or step.get("endTime"),
                "duration_ms": step.get("duration_ms") or step.get("duration"),
                "sequence_number": step.get("sequence_number", 0),
                "attributes": step.get("attributes") or step.get("metadata"),
                "error_message": step.get("error"),
                "created_at": datetime.now(UTC),
            }

            await repo.create(trace_data)
            logger.debug(
                "Persisted trace step to database",
                extra={
                    "trace_id": trace_data["trace_id"],
                    "node_name": trace_data["node_name"],
                    "session_id": trace_data["session_id"],
                },
            )
        except Exception as e:
            # Log but don't propagate - this is fire-and-forget
            logger.warning(
                "Failed to persist trace step to database",
                extra={"error": str(e), "step": step.get("name")},
            )


# =============================================================================
# WebSocket Handler
# =============================================================================


class DevToolsHandler(WebSocketBase, BroadcasterMixin):
    """
    WebSocket handler for real-time DevTools console and network events.

    Extends WebSocketBase to provide DevTools event streaming with the
    standardized infrastructure (auth, rate limiting, metrics, etc.).

    Usage:
        from mcp_server_langgraph.websocket.registry import get_devtools_broadcaster

        handler = DevToolsHandler(
            config=WebSocketConfig(
                endpoint_name="devtools",
                require_auth=True,
                authz_resource_type="dashboard",
                authz_resource_id="devtools",
                authz_required_relation="viewer",
            ),
            broadcaster=get_devtools_broadcaster(),
        )
        await handler.run(websocket)
    """

    def __init__(
        self,
        config: WebSocketConfig,
        broadcaster: DevToolsBroadcasterProtocol,
        metrics: WebSocketMetrics | None = None,
    ) -> None:
        """
        Initialize the DevTools handler.

        Args:
            config: WebSocket configuration.
            broadcaster: Broadcaster for managing subscriptions.
            metrics: Optional metrics collector.
        """
        super().__init__(config=config, metrics=metrics)
        self._broadcaster = broadcaster
        # Note: _subscribed is managed by BroadcasterMixin
        self._context_entity_id: str | None = None

    async def on_connect(self, user: AuthUser) -> None:
        """
        Handle connection establishment.

        Uses context_id from base class (extracted from query params in run())
        and subscribes the client to the DevTools broadcaster.

        Args:
            user: The authenticated user.
        """
        # Use context_id from base class if available (populated in run()).
        # Fallback to direct query_params extraction for tests that bypass run().
        if self.context_id:
            self._context_entity_id = self.context_id
        elif self._websocket:
            query_params = getattr(self._websocket, "query_params", {}) or {}
            self._context_entity_id = query_params.get("context_id")

        if self._websocket:
            # Use BroadcasterMixin's subscribe() with kwargs
            await self.subscribe(
                user_id=self.user_id,
                context_entity_id=self._context_entity_id,
            )
            logger.info(
                f"DevTools stream connected: user={self.user_id}",
                extra={
                    "user_id": self.user_id,
                    "context_entity_id": self._context_entity_id,
                },
            )

    async def on_disconnect(self) -> None:
        """
        Handle connection teardown.

        Unsubscribes the client from the DevTools broadcaster.
        """
        # Use BroadcasterMixin's unsubscribe() for cleanup
        await self.unsubscribe()
        logger.info(
            f"DevTools stream disconnected: user={self.user_id}",
            extra={"user_id": self.user_id},
        )

    async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
        """
        Handle incoming messages.

        Supports subscribe, unsubscribe, and context messages.

        Args:
            message: The incoming message envelope.

        Returns:
            Response envelope or None.
        """
        logger.debug(
            f"Received message type: {message.type}",
            extra={"message_type": message.type, "user_id": self.user_id},
        )

        if message.type == "subscribe":
            # Extract context entity ID from payload if provided
            if message.payload and isinstance(message.payload, dict):
                self._context_entity_id = message.payload.get("contextEntityId")

            if self._websocket and not self._subscribed:
                # Use BroadcasterMixin's subscribe() with kwargs
                await self.subscribe(
                    user_id=self.user_id,
                    context_entity_id=self._context_entity_id,
                )

            return self.create_subscribed_response(
                correlation_id=message.id,
                extra_payload={"status": "subscribed", "contextEntityId": self._context_entity_id},
            )

        elif message.type == "unsubscribe":
            # Use BroadcasterMixin's unsubscribe()
            await self.unsubscribe()

            return self.create_unsubscribed_response(
                correlation_id=message.id,
                extra_payload={"status": "unsubscribed"},
            )

        elif message.type == "set_context":
            # Update context filter
            if message.payload and isinstance(message.payload, dict):
                self._context_entity_id = message.payload.get("contextEntityId")

                # Re-subscribe with new context using BroadcasterMixin methods
                if self._websocket and self._subscribed:
                    await self.unsubscribe()
                    await self.subscribe(
                        user_id=self.user_id,
                        context_entity_id=self._context_entity_id,
                    )

            return MessageEnvelope(
                type="context_updated",
                id=message.id,
                payload={"contextEntityId": self._context_entity_id},
            )

        # Ping/pong is handled by the base class
        return None


# =============================================================================
# Singleton Instance - CENTRALIZED IN REGISTRY
# =============================================================================
# NOTE: get_devtools_broadcaster() is defined in websocket/registry.py
# to ensure a single application-wide broadcaster instance.
# Import from there: from mcp_server_langgraph.websocket.registry import get_devtools_broadcaster
