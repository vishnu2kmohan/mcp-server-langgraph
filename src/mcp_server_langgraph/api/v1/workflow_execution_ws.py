"""
Workflow Execution WebSocket Endpoint

.. deprecated:: 3.0
    This module is deprecated. Use the new standardized WebSocket infrastructure:

    - Handler: :mod:`mcp_server_langgraph.websocket.handlers.workflow`
    - Base class: :mod:`mcp_server_langgraph.websocket.base.WebSocketBase`
    - New URL: ``/api/v1/ws/workflows``

    This module will be removed in v4.0.

Real-time workflow execution via WebSocket.
Provides:
- Start/stop execution commands
- Node-by-node status updates
- Execution logs streaming
- Connection lifecycle management

Contract: docs-internal/frontend/WORKFLOW_WEBSOCKET_CONTRACT.md
"""

import json
import warnings

warnings.warn(
    "mcp_server_langgraph.api.v1.workflow_execution_ws is deprecated. "
    "Use mcp_server_langgraph.websocket.handlers.workflow instead. "
    "This module will be removed in v4.0.",
    DeprecationWarning,
    stacklevel=2,
)
import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

workflow_execution_router = APIRouter(tags=["workflow-execution"])


# ============================================================================
# Execution Manager Interface
# ============================================================================


class ExecutionManagerInterface:
    """Interface for workflow execution management."""

    async def get_workflow(self, workflow_id: str) -> dict[str, Any] | None:
        """Get a workflow by ID."""
        raise NotImplementedError

    async def start_execution(self, workflow_id: str, input_data: dict[str, Any] | None = None) -> str:
        """Start workflow execution, returns execution ID."""
        raise NotImplementedError

    async def stop_execution(self, workflow_id: str) -> bool:
        """Stop workflow execution."""
        raise NotImplementedError


class DefaultExecutionManager(ExecutionManagerInterface):
    """Default execution manager implementation.

    In production, this would integrate with LangGraph execution engine.
    """

    def __init__(self) -> None:
        """Initialize with empty state."""
        self._workflows: dict[str, dict[str, Any]] = {}
        self._executions: dict[str, dict[str, Any]] = {}

    async def get_workflow(self, workflow_id: str) -> dict[str, Any] | None:
        """Get a workflow by ID.

        In production, this would fetch from the workflow storage.
        """
        return self._workflows.get(workflow_id)

    async def start_execution(self, workflow_id: str, input_data: dict[str, Any] | None = None) -> str:
        """Start workflow execution.

        In production, this would trigger LangGraph execution.
        """
        from uuid import uuid4

        execution_id = str(uuid4())
        self._executions[execution_id] = {
            "id": execution_id,
            "workflow_id": workflow_id,
            "status": "running",
            "input": input_data,
            "started_at": datetime.now(UTC).isoformat(),
        }
        logger.info(f"Started execution {execution_id} for workflow {workflow_id}")
        return execution_id

    async def stop_execution(self, workflow_id: str) -> bool:
        """Stop workflow execution."""
        for exec_id, execution in self._executions.items():
            if execution["workflow_id"] == workflow_id and execution["status"] == "running":
                execution["status"] = "stopped"
                execution["stopped_at"] = datetime.now(UTC).isoformat()
                logger.info(f"Stopped execution {exec_id} for workflow {workflow_id}")
                return True
        return False


# Global execution manager instance
_execution_manager: ExecutionManagerInterface | None = None
_langgraph_manager: Any = None  # LangGraphExecutionManager when initialized


def get_execution_manager() -> ExecutionManagerInterface:
    """Get the execution manager instance.

    Uses LangGraphExecutionManager if workflow storage is available,
    otherwise falls back to DefaultExecutionManager.
    """
    global _execution_manager, _langgraph_manager

    if _execution_manager is None:
        # Try to use LangGraphExecutionManager with workflow storage
        try:
            from mcp_server_langgraph.execution.langgraph_manager import (
                LangGraphExecutionManager,
            )
            from mcp_server_langgraph.storage.workflow.manager import (
                RedisWorkflowManager,
                create_redis_pool,
            )
            from mcp_server_langgraph.core.config import settings
            import asyncio

            # Check if Redis is configured for workflows
            if settings.redis_url:
                # Create Redis pool and workflow manager
                # Note: This is a sync context, so we use run_in_executor for async init
                async def init_storage() -> "RedisWorkflowManager":
                    pool = await create_redis_pool(settings.redis_url)
                    return RedisWorkflowManager(redis_client=pool)

                # Try to get existing event loop or create new one
                try:
                    loop = asyncio.get_running_loop()
                    # Can't use run_until_complete in running loop - use default
                    _execution_manager = DefaultExecutionManager()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    try:
                        storage = loop.run_until_complete(init_storage())
                        _langgraph_manager = LangGraphExecutionManager(workflow_storage=storage)
                        _execution_manager = _langgraph_manager
                        logger.info("Initialized LangGraphExecutionManager with Redis storage")
                    except Exception as e:
                        logger.warning(f"Failed to initialize LangGraphExecutionManager: {e}. Using DefaultExecutionManager.")
                        _execution_manager = DefaultExecutionManager()
                    finally:
                        loop.close()
            else:
                _execution_manager = DefaultExecutionManager()

        except ImportError as e:
            logger.warning(f"LangGraphExecutionManager not available: {e}. Using DefaultExecutionManager.")
            _execution_manager = DefaultExecutionManager()

    return _execution_manager


def set_execution_manager(manager: ExecutionManagerInterface) -> None:
    """Set a custom execution manager (for testing/DI)."""
    global _execution_manager
    _execution_manager = manager


# ============================================================================
# WebSocket Connection Manager
# ============================================================================


class ExecutionWebSocketManager:
    """Manages WebSocket connections for workflow execution."""

    def __init__(self) -> None:
        """Initialize connection manager."""
        self.active_connections: dict[str, dict[str, Any]] = {}
        # workflow_id -> list of client_ids
        self.workflow_clients: dict[str, set[str]] = {}

    async def connect(self, websocket: WebSocket, client_id: str, workflow_id: str) -> None:
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections[client_id] = {
            "websocket": websocket,
            "workflow_id": workflow_id,
            "connected_at": datetime.now(UTC).isoformat(),
        }
        if workflow_id not in self.workflow_clients:
            self.workflow_clients[workflow_id] = set()
        self.workflow_clients[workflow_id].add(client_id)
        logger.info(f"Execution WebSocket connected: {client_id} for workflow {workflow_id}")

    def disconnect(self, client_id: str) -> None:
        """Remove a disconnected client."""
        if client_id in self.active_connections:
            workflow_id = self.active_connections[client_id]["workflow_id"]
            del self.active_connections[client_id]
            if workflow_id in self.workflow_clients:
                self.workflow_clients[workflow_id].discard(client_id)
                if not self.workflow_clients[workflow_id]:
                    del self.workflow_clients[workflow_id]
            logger.info(f"Execution WebSocket disconnected: {client_id}")

    async def send_to_client(self, client_id: str, message: dict[str, Any]) -> None:
        """Send a message to a specific client."""
        if client_id in self.active_connections:
            try:
                websocket = self.active_connections[client_id]["websocket"]
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to client {client_id}: {e}")
                self.disconnect(client_id)

    async def broadcast_to_workflow(self, workflow_id: str, message: dict[str, Any]) -> None:
        """Broadcast a message to all clients watching a workflow."""
        if workflow_id in self.workflow_clients:
            disconnected = []
            for client_id in self.workflow_clients[workflow_id]:
                if client_id in self.active_connections:
                    try:
                        websocket = self.active_connections[client_id]["websocket"]
                        await websocket.send_json(message)
                    except Exception:
                        disconnected.append(client_id)

            for client_id in disconnected:
                self.disconnect(client_id)


# Global manager instance
execution_ws_manager = ExecutionWebSocketManager()


# ============================================================================
# Message Handlers
# ============================================================================


async def handle_message(
    message: dict[str, Any],
    client_id: str,
    workflow_id: str,
    manager: ExecutionManagerInterface,
) -> dict[str, Any]:
    """Handle incoming WebSocket message."""
    msg_type = message.get("type", "")

    if msg_type == "ping":
        return {"type": "pong", "timestamp": datetime.now(UTC).isoformat()}

    elif msg_type == "start":
        input_data = message.get("input")
        execution_id = await manager.start_execution(workflow_id, input_data)
        return {
            "type": "execution_started",
            "workflowId": workflow_id,
            "executionId": execution_id,
        }

    elif msg_type == "stop":
        success = await manager.stop_execution(workflow_id)
        if success:
            return {"type": "execution_stopped", "workflowId": workflow_id}
        return {
            "type": "error",
            "message": "No running execution found for this workflow",
        }

    else:
        return {"type": "error", "message": f"Unknown message type: {msg_type}"}


# ============================================================================
# WebSocket Endpoint
# ============================================================================


@workflow_execution_router.websocket("/workflows/{workflow_id}/execution")
async def workflow_execution_websocket(
    websocket: WebSocket,
    workflow_id: str,
    manager: ExecutionManagerInterface = Depends(get_execution_manager),
) -> None:
    """
    WebSocket endpoint for real-time workflow execution.

    Path Parameters:
        workflow_id: ID of the workflow to execute

    Client -> Server Messages:
        - start: Start workflow execution (optional input data)
        - stop: Stop current execution
        - ping: Heartbeat check

    Server -> Client Messages:
        - execution_started: Execution has begun
        - execution_completed: Execution finished successfully
        - execution_error: Execution failed
        - execution_stopped: Execution was stopped by user
        - node_started: A node started executing
        - node_completed: A node finished executing
        - node_error: A node failed
        - log: Execution log message
        - pong: Response to ping
        - error: Error message
    """
    # Validate workflow exists
    workflow = await manager.get_workflow(workflow_id)
    if workflow is None:
        await websocket.close(code=4004, reason="Workflow not found")
        return

    client_id = str(id(websocket))

    await execution_ws_manager.connect(websocket, client_id, workflow_id)

    try:
        # Message loop
        while True:
            try:
                raw_message = await websocket.receive_text()

                try:
                    message = json.loads(raw_message)
                except json.JSONDecodeError:
                    await websocket.send_json({"type": "error", "message": "Invalid JSON"})
                    continue

                response = await handle_message(message, client_id, workflow_id, manager)
                await websocket.send_json(response)

            except WebSocketDisconnect:
                break

    finally:
        execution_ws_manager.disconnect(client_id)


# ============================================================================
# Helper functions for sending execution updates (for LangGraph integration)
# ============================================================================


async def send_node_started(workflow_id: str, node_id: str) -> None:
    """Send node started notification to all clients watching the workflow."""
    await execution_ws_manager.broadcast_to_workflow(
        workflow_id,
        {"type": "node_started", "nodeId": node_id},
    )


async def send_node_completed(workflow_id: str, node_id: str) -> None:
    """Send node completed notification to all clients watching the workflow."""
    await execution_ws_manager.broadcast_to_workflow(
        workflow_id,
        {"type": "node_completed", "nodeId": node_id},
    )


async def send_node_error(workflow_id: str, node_id: str, error: str) -> None:
    """Send node error notification to all clients watching the workflow."""
    await execution_ws_manager.broadcast_to_workflow(
        workflow_id,
        {"type": "node_error", "nodeId": node_id, "error": error},
    )


async def send_log(
    workflow_id: str,
    level: str,
    message: str,
    node_id: str | None = None,
) -> None:
    """Send log message to all clients watching the workflow."""
    log_message: dict[str, Any] = {
        "type": "log",
        "level": level,
        "message": message,
    }
    if node_id:
        log_message["nodeId"] = node_id
    await execution_ws_manager.broadcast_to_workflow(workflow_id, log_message)


async def send_execution_completed(workflow_id: str, result: Any | None = None) -> None:
    """Send execution completed notification."""
    message: dict[str, Any] = {
        "type": "execution_completed",
        "workflowId": workflow_id,
    }
    if result is not None:
        message["result"] = result
    await execution_ws_manager.broadcast_to_workflow(workflow_id, message)


async def send_execution_error(workflow_id: str, error: str) -> None:
    """Send execution error notification."""
    await execution_ws_manager.broadcast_to_workflow(
        workflow_id,
        {"type": "execution_error", "workflowId": workflow_id, "error": error},
    )


# Re-export for dependency override in tests
__all__ = [
    "workflow_execution_router",
    "get_execution_manager",
    "set_execution_manager",
    "execution_ws_manager",
    "ExecutionWebSocketManager",
    "ExecutionManagerInterface",
    "DefaultExecutionManager",
    "send_node_started",
    "send_node_completed",
    "send_node_error",
    "send_log",
    "send_execution_completed",
    "send_execution_error",
]
