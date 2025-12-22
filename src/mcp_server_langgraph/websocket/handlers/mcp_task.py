"""
MCP Task WebSocket Handler.

Provides real-time task status updates using the standardized WebSocketBase class.

Features:
    - Task list on connect
    - Subscribe/unsubscribe to specific tasks
    - Real-time task status updates
    - Refresh capability

Message Types (Client -> Server):
    - subscribe: Subscribe to a task (requires task_id in payload)
    - unsubscribe: Unsubscribe from a task (requires task_id in payload)
    - refresh: Request updated task list

Response Types (Server -> Client):
    - task_list: List of all active tasks
    - task_status: Current status of a subscribed task
    - task_update: Real-time task status change (pushed)
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


@runtime_checkable
class MCPServiceProtocol(Protocol):
    """Protocol defining the MCP service interface needed by this handler."""

    async def list_tasks(self) -> list[Any]:
        """List all active tasks."""
        ...

    async def get_task(self, task_id: str) -> Any:
        """Get a specific task by ID."""
        ...


class MCPTaskWebSocketHandler(WebSocketBase):
    """
    WebSocket handler for MCP task status updates.

    Extends WebSocketBase to provide real-time task status monitoring
    with the standardized infrastructure (auth, rate limiting, metrics, etc.).

    Usage:
        handler = MCPTaskWebSocketHandler(
            config=WebSocketConfig(
                endpoint_name="mcp-tasks",
                require_auth=True,
                authz_resource_type="workflow",
                authz_required_relation="viewer",
            ),
            mcp_service=get_mcp_service(),
        )
        await handler.run(websocket)
    """

    def __init__(
        self,
        config: WebSocketConfig,
        mcp_service: MCPServiceProtocol,
        metrics: WebSocketMetrics | None = None,
    ) -> None:
        """
        Initialize the MCP task handler.

        Args:
            config: WebSocket configuration.
            mcp_service: MCP service for task operations.
            metrics: Optional metrics collector.
        """
        super().__init__(config=config, metrics=metrics)
        self._mcp_service = mcp_service
        self.subscriptions: set[str] = set()

    async def on_connect(self, user: AuthUser) -> None:
        """
        Handle connection establishment.

        Sends the initial task list to the client.

        Args:
            user: The authenticated user.
        """
        # Send initial task list
        tasks = await self._mcp_service.list_tasks()
        task_list = [self._convert_task_to_dict(t) for t in tasks]

        if self._websocket:
            await self._websocket.send_json(
                {
                    "type": "task_list",
                    "tasks": task_list,
                }
            )

    async def on_disconnect(self) -> None:
        """Clean up subscriptions on disconnect."""
        self.subscriptions.clear()

    async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
        """
        Handle incoming messages.

        Supports:
        - subscribe: Subscribe to task updates
        - unsubscribe: Unsubscribe from task updates
        - refresh: Get updated task list

        Args:
            message: The incoming message envelope.

        Returns:
            Response message or None.
        """
        if message.type == "subscribe":
            return await self._handle_subscribe(message)
        elif message.type == "unsubscribe":
            return await self._handle_unsubscribe(message)
        elif message.type == "refresh":
            return await self._handle_refresh(message)
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
        payload = message.payload or {}
        task_id = payload.get("task_id")

        if not task_id:
            return MessageEnvelope(
                type="error",
                payload={
                    "code": "missing_task_id",
                    "message": "task_id is required for subscribe",
                },
                id=message.id,
            )

        try:
            task = await self._mcp_service.get_task(task_id)
            if task is None:
                return MessageEnvelope(
                    type="error",
                    payload={
                        "code": "task_not_found",
                        "message": f"Task {task_id} not found",
                    },
                    id=message.id,
                )

            self.subscriptions.add(task_id)
            return MessageEnvelope(
                type="task_status",
                payload={"task": self._convert_task_to_dict(task)},
                id=message.id,
            )

        except Exception as e:
            logger.warning(f"Error subscribing to task {task_id}: {e}")
            return MessageEnvelope(
                type="error",
                payload={
                    "code": "subscribe_error",
                    "message": str(e),
                },
                id=message.id,
            )

    async def _handle_unsubscribe(self, message: MessageEnvelope) -> MessageEnvelope:
        """Handle unsubscribe message."""
        payload = message.payload or {}
        task_id = payload.get("task_id")

        if task_id:
            self.subscriptions.discard(task_id)

        return MessageEnvelope(
            type="unsubscribed",
            payload={"task_id": task_id},
            id=message.id,
        )

    async def _handle_refresh(self, message: MessageEnvelope) -> MessageEnvelope:
        """Handle refresh message."""
        tasks = await self._mcp_service.list_tasks()
        task_list = [self._convert_task_to_dict(t) for t in tasks]

        return MessageEnvelope(
            type="task_list",
            payload={"tasks": task_list},
            id=message.id,
        )

    def _convert_task_to_dict(self, task: Any) -> dict[str, Any]:
        """Convert a task object to a dictionary for JSON serialization."""
        return {
            "task_id": task.task_id,
            "status": task.status.value if hasattr(task.status, "value") else str(task.status),
            "created_at": task.created_at.isoformat() if hasattr(task.created_at, "isoformat") else str(task.created_at),
            "last_updated_at": task.last_updated_at.isoformat()
            if hasattr(task.last_updated_at, "isoformat")
            else str(task.last_updated_at),
            "ttl": getattr(task, "ttl", 3600),
            "poll_interval": getattr(task, "poll_interval", 5),
            "status_message": getattr(task, "status_message", None),
        }

    async def push_task_update(self, task: Any) -> None:
        """
        Push a task update to the client if subscribed.

        Args:
            task: The updated task object.
        """
        if task.task_id not in self.subscriptions:
            return

        if self._websocket:
            await self.send(
                MessageEnvelope(
                    type="task_update",
                    payload={"task": self._convert_task_to_dict(task)},
                )
            )
