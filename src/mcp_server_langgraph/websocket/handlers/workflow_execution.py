"""
Workflow Execution WebSocket Handler.

Provides real-time workflow execution updates using the standardized WebSocketBase class.

Features:
    - Start/stop workflow execution
    - Real-time node status updates
    - Execution logs streaming
    - Status queries

Message Types (Client -> Server):
    - start: Start workflow execution (with optional input)
    - stop: Stop current execution
    - status: Query current execution status

Response Types (Server -> Client):
    - execution_started: Execution has begun
    - execution_stopped: Execution was stopped
    - execution_status: Current execution status
    - node_started: A node started executing
    - node_completed: A node finished executing
    - node_error: A node failed
    - log: Execution log message
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
class ExecutionServiceProtocol(Protocol):
    """Protocol defining the execution service interface."""

    async def get_workflow(self, workflow_id: str) -> dict[str, Any] | None:
        """Get workflow by ID."""
        ...

    async def start_execution(self, workflow_id: str, input_data: dict[str, Any] | None = None) -> str:
        """Start workflow execution, returns execution ID."""
        ...

    async def stop_execution(self, workflow_id: str) -> bool:
        """Stop workflow execution."""
        ...

    async def get_execution_status(self, workflow_id: str) -> dict[str, Any] | None:
        """Get current execution status."""
        ...


class WorkflowExecutionHandler(WebSocketBase):
    """
    WebSocket handler for real-time workflow execution.

    Extends WebSocketBase to provide workflow execution monitoring with the
    standardized infrastructure (auth, rate limiting, metrics, etc.).

    Usage:
        handler = WorkflowExecutionHandler(
            config=WebSocketConfig(
                endpoint_name="workflow-execution",
                require_auth=True,
                authz_resource_type="workflow",
                authz_resource_id=workflow_id,
                authz_required_relation="executor",
            ),
            execution_service=get_execution_service(),
            workflow_id=workflow_id,
        )
        await handler.run(websocket)
    """

    def __init__(
        self,
        config: WebSocketConfig,
        execution_service: ExecutionServiceProtocol,
        workflow_id: str,
        metrics: WebSocketMetrics | None = None,
    ) -> None:
        """
        Initialize the workflow execution handler.

        Args:
            config: WebSocket configuration.
            execution_service: Execution service for workflow operations.
            workflow_id: ID of the workflow to execute.
            metrics: Optional metrics collector.
        """
        super().__init__(config=config, metrics=metrics)
        self._execution_service = execution_service
        self._workflow_id = workflow_id
        self._current_execution_id: str | None = None

    async def on_connect(self, user: AuthUser) -> None:
        """
        Handle connection establishment.

        Args:
            user: The authenticated user.
        """
        logger.info(
            f"Workflow execution connected: workflow={self._workflow_id}, user={user.id}",
            extra={"workflow_id": self._workflow_id, "user_id": user.id},
        )

    async def on_disconnect(self) -> None:
        """Clean up on disconnect."""
        logger.info(
            f"Workflow execution disconnected: workflow={self._workflow_id}",
            extra={"workflow_id": self._workflow_id},
        )

    async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
        """
        Handle incoming messages.

        Supports:
        - start: Start workflow execution
        - stop: Stop current execution
        - status: Query execution status

        Args:
            message: The incoming message envelope.

        Returns:
            Response message or None.
        """
        if message.type == "start":
            return await self._handle_start(message)
        elif message.type == "stop":
            return await self._handle_stop(message)
        elif message.type == "status":
            return await self._handle_status(message)
        else:
            return MessageEnvelope(
                type="error",
                payload={
                    "code": "unknown_message_type",
                    "message": f"Unknown message type: {message.type}",
                },
                id=message.id,
            )

    async def _handle_start(self, message: MessageEnvelope) -> MessageEnvelope:
        """Handle start execution message."""
        payload = message.payload or {}
        input_data = payload.get("input")

        try:
            execution_id = await self._execution_service.start_execution(self._workflow_id, input_data)
            self._current_execution_id = execution_id

            return MessageEnvelope(
                type="execution_started",
                payload={
                    "workflow_id": self._workflow_id,
                    "execution_id": execution_id,
                },
                id=message.id,
            )

        except Exception as e:
            logger.warning(f"Error starting execution for workflow {self._workflow_id}: {e}")
            return MessageEnvelope(
                type="error",
                payload={
                    "code": "start_failed",
                    "message": str(e),
                },
                id=message.id,
            )

    async def _handle_stop(self, message: MessageEnvelope) -> MessageEnvelope:
        """Handle stop execution message."""
        try:
            success = await self._execution_service.stop_execution(self._workflow_id)

            if success:
                self._current_execution_id = None
                return MessageEnvelope(
                    type="execution_stopped",
                    payload={"workflow_id": self._workflow_id},
                    id=message.id,
                )
            else:
                return MessageEnvelope(
                    type="error",
                    payload={
                        "code": "stop_failed",
                        "message": "No running execution found",
                    },
                    id=message.id,
                )

        except Exception as e:
            logger.warning(f"Error stopping execution for workflow {self._workflow_id}: {e}")
            return MessageEnvelope(
                type="error",
                payload={
                    "code": "stop_failed",
                    "message": str(e),
                },
                id=message.id,
            )

    async def _handle_status(self, message: MessageEnvelope) -> MessageEnvelope:
        """Handle status query message."""
        try:
            status = await self._execution_service.get_execution_status(self._workflow_id)

            return MessageEnvelope(
                type="execution_status",
                payload={
                    "workflow_id": self._workflow_id,
                    "status": status,
                },
                id=message.id,
            )

        except Exception as e:
            logger.warning(f"Error getting execution status for workflow {self._workflow_id}: {e}")
            return MessageEnvelope(
                type="error",
                payload={
                    "code": "status_failed",
                    "message": str(e),
                },
                id=message.id,
            )

    async def push_node_update(self, node_id: str, status: str, details: dict[str, Any] | None = None) -> None:
        """
        Push a node status update to the client.

        Args:
            node_id: The node ID.
            status: The node status (started, completed, error).
            details: Optional additional details.
        """
        if self._websocket:
            payload: dict[str, Any] = {"node_id": node_id}
            if details:
                payload.update(details)

            await self._websocket.send_json(
                {
                    "type": f"node_{status}",
                    "payload": payload,
                }
            )

    async def push_log(self, level: str, message_text: str, node_id: str | None = None) -> None:
        """
        Push a log message to the client.

        Args:
            level: Log level (info, warning, error).
            message_text: Log message.
            node_id: Optional node ID.
        """
        if self._websocket:
            payload: dict[str, Any] = {
                "level": level,
                "message": message_text,
            }
            if node_id:
                payload["node_id"] = node_id

            await self._websocket.send_json(
                {
                    "type": "log",
                    "payload": payload,
                }
            )

    async def push_execution_completed(self, result: Any | None = None) -> None:
        """
        Push execution completed notification.

        Args:
            result: Optional execution result.
        """
        if self._websocket:
            payload: dict[str, Any] = {"workflow_id": self._workflow_id}
            if result is not None:
                payload["result"] = result

            await self._websocket.send_json(
                {
                    "type": "execution_completed",
                    "payload": payload,
                }
            )

    async def push_execution_error(self, error: str) -> None:
        """
        Push execution error notification.

        Args:
            error: Error message.
        """
        if self._websocket:
            await self._websocket.send_json(
                {
                    "type": "execution_error",
                    "payload": {
                        "workflow_id": self._workflow_id,
                        "error": error,
                    },
                }
            )
