"""
MCP Aggregated Capabilities WebSocket Handler.

Provides real-time capability change notifications using WebSocketBase.

Features:
    - Subscribe to capability change events
    - Real-time updates when tools/resources/prompts change
    - Server registration/unregistration events
    - Current capability counts on demand

Message Types (Client -> Server):
    - subscribe: Subscribe to capability events
    - unsubscribe: Unsubscribe from capability events
    - get_counts: Get current capability counts

Response Types (Server -> Client):
    - subscribed: Successfully subscribed to events
    - unsubscribed: Successfully unsubscribed from events
    - capability_counts: Current capability counts
    - tools_changed: Tools list has changed
    - resources_changed: Resources list has changed
    - prompts_changed: Prompts list has changed
    - server_registered: New server registered
    - server_unregistered: Server unregistered

Reference: MCP Protocol 2025-11-25 capability aggregation
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
class MCPAggregatedBroadcasterProtocol(Protocol):
    """Protocol defining the MCP aggregated broadcaster interface."""

    async def subscribe(
        self,
        websocket: FastAPIWebSocket,
        user_id: str | None = None,
    ) -> None:
        """Subscribe to capability events."""
        ...

    async def unsubscribe(self, websocket: FastAPIWebSocket) -> None:
        """Unsubscribe from capability events."""
        ...

    async def get_current_counts(self) -> dict[str, int]:
        """Get current capability counts."""
        ...


# =============================================================================
# Broadcaster Implementation
# =============================================================================


class MCPAggregatedBroadcaster:
    """
    Broadcaster for MCP aggregated capability changes.

    Manages WebSocket subscriptions and broadcasts capability change events
    to all connected clients.

    Usage:
        broadcaster = MCPAggregatedBroadcaster()

        # Subscribe a client
        await broadcaster.subscribe(websocket, user_id="user-123")

        # Broadcast an event
        await broadcaster.broadcast_tools_changed(server_name="test", count=5)

        # Unsubscribe
        await broadcaster.unsubscribe(websocket)
    """

    def __init__(self) -> None:
        """Initialize the broadcaster."""
        self._subscribers: dict[Any, str | None] = {}

    async def subscribe(
        self,
        websocket: Any,
        user_id: str | None = None,
    ) -> None:
        """Subscribe a WebSocket to capability events.

        Args:
            websocket: The WebSocket connection
            user_id: Optional user ID for tracking
        """
        self._subscribers[websocket] = user_id
        logger.info(
            "Client subscribed to MCP aggregated events",
            extra={"user_id": user_id, "subscriber_count": len(self._subscribers)},
        )

    async def unsubscribe(self, websocket: Any) -> None:
        """Unsubscribe a WebSocket from capability events.

        Args:
            websocket: The WebSocket connection
        """
        if websocket in self._subscribers:
            user_id = self._subscribers.pop(websocket)
            logger.info(
                "Client unsubscribed from MCP aggregated events",
                extra={"user_id": user_id, "subscriber_count": len(self._subscribers)},
            )

    async def get_current_counts(self) -> dict[str, int]:
        """Get current capability counts from the cached registry.

        Returns:
            Dict with total_servers, total_tools, total_resources, total_prompts
        """
        try:
            from mcp_server_langgraph.mcp.client.cached_unified_registry import (
                get_cached_unified_registry,
            )

            registry = get_cached_unified_registry()
            server_names = await registry.get_server_names()

            total_tools = 0
            total_resources = 0
            total_prompts = 0

            for name in server_names:
                caps = await registry.get_server_capabilities(name)
                total_tools += caps.get("tool_count", 0)
                total_resources += caps.get("resource_count", 0)
                total_prompts += caps.get("prompt_count", 0)

            return {
                "total_servers": len(server_names),
                "total_tools": total_tools,
                "total_resources": total_resources,
                "total_prompts": total_prompts,
            }
        except Exception as e:
            logger.exception(
                "Failed to get current counts",
                extra={"error": str(e)},
            )
            return {
                "total_servers": 0,
                "total_tools": 0,
                "total_resources": 0,
                "total_prompts": 0,
            }

    async def _broadcast(self, message: dict[str, Any]) -> None:
        """Broadcast a message to all subscribers.

        Args:
            message: The message to broadcast
        """
        failed_subscribers: list[Any] = []

        for websocket in list(self._subscribers.keys()):
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(
                    "Failed to send to subscriber, removing",
                    extra={"error": str(e)},
                )
                failed_subscribers.append(websocket)

        # Remove failed subscribers
        for ws in failed_subscribers:
            self._subscribers.pop(ws, None)

    async def broadcast_tools_changed(
        self,
        server_name: str,
        count: int,
    ) -> None:
        """Broadcast tools changed event using MCP JSON-RPC 2.0 format.

        Args:
            server_name: Name of the server whose tools changed
            count: New tool count for this server

        Reference: MCP Protocol 2025-11-25 notifications/tools/list_changed
        """
        await self._broadcast(
            {
                "jsonrpc": "2.0",
                "method": "notifications/tools/list_changed",
                "params": {
                    "serverName": server_name,
                    "count": count,
                },
            }
        )

    async def broadcast_resources_changed(
        self,
        server_name: str,
        count: int,
    ) -> None:
        """Broadcast resources changed event using MCP JSON-RPC 2.0 format.

        Args:
            server_name: Name of the server whose resources changed
            count: New resource count for this server

        Reference: MCP Protocol 2025-11-25 notifications/resources/list_changed
        """
        await self._broadcast(
            {
                "jsonrpc": "2.0",
                "method": "notifications/resources/list_changed",
                "params": {
                    "serverName": server_name,
                    "count": count,
                },
            }
        )

    async def broadcast_prompts_changed(
        self,
        server_name: str,
        count: int,
    ) -> None:
        """Broadcast prompts changed event using MCP JSON-RPC 2.0 format.

        Args:
            server_name: Name of the server whose prompts changed
            count: New prompt count for this server

        Reference: MCP Protocol 2025-11-25 notifications/prompts/list_changed
        """
        await self._broadcast(
            {
                "jsonrpc": "2.0",
                "method": "notifications/prompts/list_changed",
                "params": {
                    "serverName": server_name,
                    "count": count,
                },
            }
        )

    async def broadcast_server_registered(
        self,
        server_name: str,
        tool_count: int,
        resource_count: int,
        prompt_count: int,
    ) -> None:
        """Broadcast server registered event using MCP JSON-RPC 2.0 format.

        Args:
            server_name: Name of the newly registered server
            tool_count: Number of tools the server provides
            resource_count: Number of resources the server provides
            prompt_count: Number of prompts the server provides

        Note: Server registration is an extension to standard MCP notifications.
        """
        await self._broadcast(
            {
                "jsonrpc": "2.0",
                "method": "notifications/server/registered",
                "params": {
                    "serverName": server_name,
                    "toolCount": tool_count,
                    "resourceCount": resource_count,
                    "promptCount": prompt_count,
                },
            }
        )

    async def broadcast_server_unregistered(
        self,
        server_name: str,
    ) -> None:
        """Broadcast server unregistered event using MCP JSON-RPC 2.0 format.

        Args:
            server_name: Name of the unregistered server

        Note: Server unregistration is an extension to standard MCP notifications.
        """
        await self._broadcast(
            {
                "jsonrpc": "2.0",
                "method": "notifications/server/unregistered",
                "params": {
                    "serverName": server_name,
                },
            }
        )


# =============================================================================
# WebSocket Handler
# =============================================================================


class MCPAggregatedHandler(WebSocketBase, BroadcasterMixin):
    """
    WebSocket handler for real-time MCP capability change events.

    Extends WebSocketBase to provide capability streaming with the
    standardized infrastructure (auth, rate limiting, metrics, etc.).

    Usage:
        handler = MCPAggregatedHandler(
            config=WebSocketConfig(
                endpoint_name="mcp-aggregated",
                require_auth=True,
                authz_resource_type="mcp",
                authz_resource_id="aggregated-capabilities",
                authz_required_relation="viewer",
            ),
            broadcaster=get_mcp_aggregated_broadcaster(),
        )
        await handler.run(websocket)
    """

    def __init__(
        self,
        config: WebSocketConfig,
        broadcaster: MCPAggregatedBroadcasterProtocol,
        metrics: WebSocketMetrics | None = None,
    ) -> None:
        """
        Initialize the MCP aggregated handler.

        Args:
            config: WebSocket configuration.
            broadcaster: Broadcaster for managing subscriptions.
            metrics: Optional metrics collector.
        """
        super().__init__(config=config, metrics=metrics)
        self._broadcaster = broadcaster
        # Note: _subscribed is managed by BroadcasterMixin
    async def on_connect(self, user: AuthUser) -> None:
        """
        Handle connection establishment.

        Subscribes the client to the capability broadcaster.

        Args:
            user: The authenticated user.
        """
        if self._websocket:
            # Use BroadcasterMixin's subscribe() with user_id kwarg
            await self.subscribe(user_id=self.user_id)
            logger.info(
                f"MCP aggregated stream connected: user={self.user_id}",
                extra={"user_id": self.user_id},
            )

    async def on_disconnect(self) -> None:
        """
        Handle connection teardown.

        Unsubscribes the client from the capability broadcaster.
        """
        # Use BroadcasterMixin's unsubscribe() for cleanup
        await self.unsubscribe()
        logger.info(
            f"MCP aggregated stream disconnected: user={self.user_id}",
            extra={"user_id": self.user_id},
        )

    async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
        """
        Handle incoming messages.

        Supports subscribe, unsubscribe, and get_counts messages.

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
            if self._websocket and not self._subscribed:
                # Use BroadcasterMixin's subscribe()
                await self.subscribe(user_id=self.user_id)

            return self.create_subscribed_response(
                correlation_id=message.id,
                extra_payload={"status": "subscribed"},
            )

        elif message.type == "unsubscribe":
            # Use BroadcasterMixin's unsubscribe()
            await self.unsubscribe()

            return self.create_unsubscribed_response(
                correlation_id=message.id,
                extra_payload={"status": "unsubscribed"},
            )

        elif message.type == "get_counts":
            counts = await self._broadcaster.get_current_counts()
            return MessageEnvelope(
                type="capability_counts",
                id=message.id,
                payload=counts,
            )

        # Ping/pong is handled by the base class
        return None


# =============================================================================
# Singleton Instance
# =============================================================================

_broadcaster: MCPAggregatedBroadcaster | None = None


def get_mcp_aggregated_broadcaster() -> MCPAggregatedBroadcaster:
    """Get the application-wide MCP aggregated broadcaster instance.

    Returns:
        Singleton MCPAggregatedBroadcaster instance
    """
    global _broadcaster
    if _broadcaster is None:
        _broadcaster = MCPAggregatedBroadcaster()
    return _broadcaster


def reset_mcp_aggregated_broadcaster() -> None:
    """Reset the MCP aggregated broadcaster (for testing)."""
    global _broadcaster
    _broadcaster = None
