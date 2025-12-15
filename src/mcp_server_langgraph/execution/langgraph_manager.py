"""
LangGraph Execution Manager

Integrates workflow storage with the WebSocket execution endpoint.
Provides workflow fetching and execution tracking with state management.

Example:
    from mcp_server_langgraph.execution import LangGraphExecutionManager
    from mcp_server_langgraph.storage.workflow import RedisWorkflowManager

    # Create with workflow storage
    manager = LangGraphExecutionManager(workflow_storage=storage)

    # Fetch workflow
    workflow = await manager.get_workflow("wf-123")

    # Start execution
    execution_id = await manager.start_execution("wf-123", {"prompt": "Hello"})

    # Stop execution
    await manager.stop_execution("wf-123")
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import uuid4

logger = logging.getLogger(__name__)


class WorkflowStorageProtocol(Protocol):
    """Protocol for workflow storage backends."""

    async def get_workflow(self, workflow_id: str) -> Any | None:
        """Get a workflow by ID."""
        ...


class ExecutionState:
    """Tracks the state of a workflow execution."""

    def __init__(
        self,
        execution_id: str,
        workflow_id: str,
        input_data: dict[str, Any] | None = None,
    ) -> None:
        """Initialize execution state."""
        self.execution_id = execution_id
        self.workflow_id = workflow_id
        self.input_data = input_data
        self.status = "running"
        self.started_at = datetime.now(UTC)
        self.stopped_at: datetime | None = None

    def stop(self) -> None:
        """Mark execution as stopped."""
        self.status = "stopped"
        self.stopped_at = datetime.now(UTC)


class LangGraphExecutionManager:
    """
    Execution manager that integrates workflow storage with LangGraph execution.

    Implements the ExecutionManagerInterface from workflow_execution_ws.py.
    Uses workflow storage to fetch workflow definitions and tracks
    execution state for running workflows.
    """

    def __init__(self, workflow_storage: WorkflowStorageProtocol) -> None:
        """
        Initialize the execution manager.

        Args:
            workflow_storage: Backend for fetching workflow definitions
        """
        self._storage = workflow_storage
        self._executions: dict[str, ExecutionState] = {}  # workflow_id -> state
        self._execution_id_map: dict[str, str] = {}  # workflow_id -> execution_id

    async def get_workflow(self, workflow_id: str) -> dict[str, Any] | None:
        """
        Get a workflow by ID from storage.

        Args:
            workflow_id: The workflow ID to fetch

        Returns:
            Workflow as dict if found, None otherwise
        """
        workflow = await self._storage.get_workflow(workflow_id)
        if workflow is None:
            return None

        # Convert Pydantic model to dict if needed
        if hasattr(workflow, "model_dump"):
            result = workflow.model_dump()
            return dict(result) if result is not None else None
        workflow_dict: dict[str, Any] = dict(workflow)
        return workflow_dict

    async def start_execution(self, workflow_id: str, input_data: dict[str, Any] | None = None) -> str:
        """
        Start workflow execution.

        Args:
            workflow_id: The workflow to execute
            input_data: Optional input data for the execution

        Returns:
            Unique execution ID
        """
        execution_id = str(uuid4())
        state = ExecutionState(
            execution_id=execution_id,
            workflow_id=workflow_id,
            input_data=input_data,
        )
        self._executions[workflow_id] = state
        self._execution_id_map[workflow_id] = execution_id

        logger.info(
            f"Started execution {execution_id} for workflow {workflow_id}",
            extra={"execution_id": execution_id, "workflow_id": workflow_id},
        )

        return execution_id

    async def stop_execution(self, workflow_id: str) -> bool:
        """
        Stop a running execution.

        Args:
            workflow_id: The workflow to stop

        Returns:
            True if execution was stopped, False if not found
        """
        if workflow_id not in self._executions:
            return False

        state = self._executions[workflow_id]
        if state.status != "running":
            return False

        state.stop()
        logger.info(
            f"Stopped execution {state.execution_id} for workflow {workflow_id}",
            extra={"execution_id": state.execution_id, "workflow_id": workflow_id},
        )

        # Clean up
        del self._executions[workflow_id]
        del self._execution_id_map[workflow_id]

        return True

    def is_execution_running(self, workflow_id: str) -> bool:
        """Check if a workflow has a running execution."""
        return workflow_id in self._executions and self._executions[workflow_id].status == "running"

    def get_execution_id(self, workflow_id: str) -> str | None:
        """Get the execution ID for a workflow."""
        return self._execution_id_map.get(workflow_id)

    def get_execution_input(self, workflow_id: str) -> dict[str, Any] | None:
        """Get the input data for a workflow execution."""
        if workflow_id not in self._executions:
            return None
        return self._executions[workflow_id].input_data
