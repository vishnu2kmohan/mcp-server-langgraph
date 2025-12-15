"""
MCP Task Status WebSocket.

Provides real-time task status updates via WebSocket connection.

Endpoints:
- WS /mcp/tasks/ws - Subscribe to task status updates

Message Types (Client → Server):
- ping: Heartbeat
- refresh: Request updated task list
- subscribe: Subscribe to task status updates
- unsubscribe: Unsubscribe from task updates

Response Types (Server → Client):
- pong: Heartbeat response
- task_list: List of all active tasks
- task_status: Current status of a subscribed task
- task_update: Real-time task status change (pushed)
- unsubscribed: Confirmation of unsubscription
- error: Error message

Example:
    from mcp_server_langgraph.api.v1.mcp_task_websocket import mcp_task_ws_router
    app.include_router(mcp_task_ws_router, prefix="/api/v1")
"""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from mcp_server_langgraph.api.v1.mcp import get_mcp_service
from mcp_server_langgraph.api.v1.mcp_bridge import (
    MCPTask,
    MCPTaskNotFoundError,
)
from mcp_server_langgraph.observability.telemetry import logger


mcp_task_ws_router = APIRouter(tags=["mcp", "websocket"])


# =============================================================================
# Task WebSocket Manager
# =============================================================================


class TaskWebSocketManager:
    """
    Manages WebSocket connections for task status updates.

    Tracks active connections and their task subscriptions.
    """

    def __init__(self) -> None:
        """Initialize the manager."""
        # client_id -> WebSocket
        self.active_connections: dict[str, WebSocket] = {}
        # client_id -> set of task_ids
        self.subscriptions: dict[str, set[str]] = {}

    def connect(self, client_id: str, websocket: WebSocket) -> None:
        """Add a new connection."""
        self.active_connections[client_id] = websocket
        self.subscriptions[client_id] = set()

    def disconnect(self, client_id: str) -> None:
        """Remove a connection and clean up subscriptions."""
        self.active_connections.pop(client_id, None)
        self.subscriptions.pop(client_id, None)

    def subscribe(self, client_id: str, task_id: str) -> None:
        """Subscribe a client to a task."""
        if client_id in self.subscriptions:
            self.subscriptions[client_id].add(task_id)

    def unsubscribe(self, client_id: str, task_id: str) -> None:
        """Unsubscribe a client from a task."""
        if client_id in self.subscriptions:
            self.subscriptions[client_id].discard(task_id)

    def get_subscribers(self, task_id: str) -> list[str]:
        """Get all clients subscribed to a task."""
        return [client_id for client_id, tasks in self.subscriptions.items() if task_id in tasks]

    async def send_to_client(self, client_id: str, message: dict[str, Any]) -> None:
        """Send a message to a specific client."""
        websocket = self.active_connections.get(client_id)
        if websocket:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to client {client_id}: {e}")

    async def broadcast_task_update(self, task: MCPTask) -> None:
        """Broadcast a task update to all subscribers."""
        subscribers = self.get_subscribers(task.task_id)
        message = {
            "type": "task_update",
            "task": _convert_task_to_dict(task),
        }
        for client_id in subscribers:
            await self.send_to_client(client_id, message)


# Global manager instance
task_ws_manager = TaskWebSocketManager()


# =============================================================================
# Helper Functions
# =============================================================================


def _convert_task_to_dict(task: MCPTask) -> dict[str, Any]:
    """Convert MCPTask to dictionary for JSON serialization."""
    return {
        "task_id": task.task_id,
        "status": task.status.value,
        "created_at": task.created_at.isoformat(),
        "last_updated_at": task.last_updated_at.isoformat(),
        "ttl": task.ttl,
        "poll_interval": task.poll_interval,
        "status_message": task.status_message,
    }


# =============================================================================
# WebSocket Endpoint
# =============================================================================


@mcp_task_ws_router.websocket("/mcp/tasks/ws")
async def task_status_websocket(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for real-time task status updates.

    Protocol:
    1. Client connects
    2. Server sends initial task list
    3. Client can subscribe/unsubscribe to specific tasks
    4. Server pushes updates when task status changes
    """
    await websocket.accept()

    # Generate unique client ID
    client_id = str(uuid4())
    task_ws_manager.connect(client_id, websocket)

    try:
        # Send initial task list
        service = get_mcp_service()
        tasks = await service.list_tasks()
        await websocket.send_json(
            {
                "type": "task_list",
                "tasks": [_convert_task_to_dict(t) for t in tasks],
            }
        )

        # Message loop
        while True:
            try:
                # Receive message from client
                raw_data = await websocket.receive_text()

                try:
                    data = json.loads(raw_data)
                except json.JSONDecodeError:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": "Invalid JSON format",
                        }
                    )
                    continue

                message_type = data.get("type", "")

                if message_type == "ping":
                    await websocket.send_json({"type": "pong"})

                elif message_type == "refresh":
                    tasks = await service.list_tasks()
                    await websocket.send_json(
                        {
                            "type": "task_list",
                            "tasks": [_convert_task_to_dict(t) for t in tasks],
                        }
                    )

                elif message_type == "subscribe":
                    task_id = data.get("task_id")
                    if not task_id:
                        await websocket.send_json(
                            {
                                "type": "error",
                                "message": "task_id is required for subscribe",
                            }
                        )
                        continue

                    try:
                        task = await service.get_task(task_id)
                        task_ws_manager.subscribe(client_id, task_id)
                        await websocket.send_json(
                            {
                                "type": "task_status",
                                "task": _convert_task_to_dict(task),
                            }
                        )
                    except MCPTaskNotFoundError:
                        await websocket.send_json(
                            {
                                "type": "error",
                                "message": f"Task {task_id} not found",
                            }
                        )

                elif message_type == "unsubscribe":
                    task_id = data.get("task_id")
                    if task_id:
                        task_ws_manager.unsubscribe(client_id, task_id)
                    await websocket.send_json(
                        {
                            "type": "unsubscribed",
                            "task_id": task_id,
                        }
                    )

                else:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": f"Unknown message type: {message_type}",
                        }
                    )

            except WebSocketDisconnect:
                break

    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}")
    finally:
        task_ws_manager.disconnect(client_id)


# =============================================================================
# Utility function for pushing updates
# =============================================================================


async def push_task_update(task: MCPTask) -> None:
    """
    Push a task update to all subscribed clients.

    Call this when a task status changes to notify subscribers.
    """
    await task_ws_manager.broadcast_task_update(task)
