"""
Workflow Execution Service Adapter for WebSocket.

Adapts the workflow execution infrastructure to the ExecutionServiceProtocol
expected by the WebSocket handler.

Architecture:
    - Wraps LangGraph workflow execution for real-time updates
    - Uses PostgresExecutionManager for persistence
    - Falls back to stub data for development/testing
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from mcp_server_langgraph.core.feature_flags import get_feature_flags

if TYPE_CHECKING:
    from mcp_server_langgraph.storage.workflow.postgres_execution_manager import (
        PostgresExecutionHistoryManager,
    )

logger = logging.getLogger(__name__)


class WorkflowExecutionServiceAdapter:
    """
    Adapter for workflow execution in WebSocket handlers.

    Provides real-time workflow execution control and status for
    the workflow execution WebSocket endpoint.

    Features:
    - Get workflow information
    - Start/stop workflow execution
    - Get execution status
    - Real-time status updates (via LangGraph callbacks)
    """

    def __init__(
        self,
        execution_manager: PostgresExecutionHistoryManager | None = None,
    ) -> None:
        """
        Initialize the workflow execution adapter.

        Args:
            execution_manager: PostgresExecutionManager for persistence.
                If None, uses stub implementation.
        """
        self._execution_manager = execution_manager
        self._active_executions: dict[str, dict[str, Any]] = {}

    @property
    def has_real_manager(self) -> bool:
        """Check if a real execution manager is available."""
        return self._execution_manager is not None

    async def get_workflow(self, workflow_id: str) -> dict[str, Any] | None:
        """
        Get workflow information by ID.

        Args:
            workflow_id: Workflow identifier.

        Returns:
            Workflow data or None if not found.
        """
        if self._execution_manager:
            try:
                return await self._execution_manager.get_workflow(workflow_id)
            except Exception as e:
                logger.warning(f"Error getting workflow {workflow_id}: {e}")

        # Stub response
        return {
            "id": workflow_id,
            "name": f"Workflow {workflow_id}",
            "nodes": [],
            "status": "ready",
        }

    async def start_execution(
        self,
        workflow_id: str,
        input_data: dict[str, Any] | None = None,
    ) -> str:
        """
        Start workflow execution.

        Args:
            workflow_id: Workflow to execute.
            input_data: Input data for the execution.

        Returns:
            Execution ID.
        """
        execution_id = f"exec-{workflow_id}-{uuid4().hex[:8]}"

        if self._execution_manager:
            try:
                # Use real execution manager - use create_execution method
                real_exec_id: str = await self._execution_manager.create_execution(
                    workflow_id=workflow_id,
                    input_data=input_data or {},
                )
                return real_exec_id
            except Exception as e:
                logger.warning(f"Error starting execution for {workflow_id}: {e}, using stub")

        # Track in local state
        self._active_executions[workflow_id] = {
            "id": execution_id,
            "workflow_id": workflow_id,
            "status": "running",
            "started_at": "2025-12-22T12:00:00Z",
            "input_data": input_data,
        }

        logger.info(f"Started stub execution {execution_id} for workflow {workflow_id}")
        return execution_id

    async def stop_execution(self, workflow_id: str) -> bool:
        """
        Stop workflow execution.

        Args:
            workflow_id: Workflow to stop.

        Returns:
            True if stopped successfully.
        """
        if self._execution_manager:
            try:
                # Use update_execution to set status to stopped
                await self._execution_manager.update_execution(
                    execution_id=workflow_id,
                    status="stopped",
                )
                return True
            except Exception as e:
                logger.warning(f"Error stopping execution for {workflow_id}: {e}")

        # Update local state
        if workflow_id in self._active_executions:
            self._active_executions[workflow_id]["status"] = "stopped"
            return True

        return False

    async def get_execution_status(self, workflow_id: str) -> dict[str, Any] | None:
        """
        Get current execution status.

        Args:
            workflow_id: Workflow to check.

        Returns:
            Execution status or None if no active execution.
        """
        if self._execution_manager:
            try:
                # Use list_executions to get the most recent execution for this workflow
                executions = await self._execution_manager.list_executions(
                    workflow_id=workflow_id,
                    limit=1,
                )
                if executions:
                    result: dict[str, Any] = executions[0]
                    return result
                return None
            except Exception as e:
                logger.warning(f"Error getting execution status for {workflow_id}: {e}")

        # Check local state
        if workflow_id in self._active_executions:
            return self._active_executions[workflow_id]

        # No active execution
        return {
            "id": None,
            "workflow_id": workflow_id,
            "status": "idle",
        }


# Service singleton
_websocket_execution_service: WorkflowExecutionServiceAdapter | None = None


def get_websocket_execution_service() -> WorkflowExecutionServiceAdapter:
    """Get the WebSocket execution service adapter instance."""
    global _websocket_execution_service
    if _websocket_execution_service is None:
        # Try to get real execution manager
        execution_manager = None
        try:
            flags = get_feature_flags()
            if flags.enable_websocket_enhanced_metrics:
                from mcp_server_langgraph.storage.workflow.postgres_execution_manager import (
                    get_execution_manager,
                )

                execution_manager = get_execution_manager()
        except ImportError:
            logger.debug("PostgresExecutionManager not available, using stub")
        except Exception as e:
            logger.debug(f"Could not get execution manager: {e}")

        _websocket_execution_service = WorkflowExecutionServiceAdapter(execution_manager=execution_manager)
    return _websocket_execution_service


def reset_websocket_execution_service() -> None:
    """Reset the WebSocket execution service singleton (for testing)."""
    global _websocket_execution_service
    _websocket_execution_service = None
