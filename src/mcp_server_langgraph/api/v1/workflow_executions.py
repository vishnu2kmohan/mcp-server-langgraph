"""
Workflow Executions Router

Provides REST API for workflow execution history.

Endpoints:
- GET /workflows/{id}/executions - List executions for a workflow
- GET /workflows/{id}/executions/{execution_id} - Get a specific execution

This complements the WebSocket endpoint at /api/v1/ws/workflows/{workflow_id}
(handler: mcp_server_langgraph.websocket.handlers.workflow) for real-time execution updates.
"""

from datetime import datetime, UTC
from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from mcp_server_langgraph.auth.dependencies import require_workflow_viewer
from mcp_server_langgraph.observability.telemetry import logger

workflow_executions_router = APIRouter(tags=["workflow-executions"])


# ==============================================================================
# Response Models
# ==============================================================================


class ExecutionResponse(BaseModel):
    """Response model for a single execution."""

    id: str = Field(..., description="Execution ID")
    workflow_id: str = Field(..., description="Workflow ID")
    status: str = Field(..., description="Execution status (pending, running, completed, failed)")
    started_at: str = Field(..., description="Start time (ISO 8601)")
    completed_at: str | None = Field(default=None, description="Completion time (ISO 8601)")
    input_data: dict[str, Any] | None = Field(default=None, description="Input data")
    output_data: dict[str, Any] | None = Field(default=None, description="Output data")
    error: str | None = Field(default=None, description="Error message if failed")


class PaginatedExecutionResponse(BaseModel):
    """Paginated response for execution listings."""

    items: list[ExecutionResponse] = Field(..., description="List of executions")
    total: int = Field(..., ge=0, description="Total number of executions")
    next_cursor: str | None = Field(default=None, description="Cursor for next page")


# ==============================================================================
# Execution History Manager Interface
# ==============================================================================


class ExecutionHistoryManagerInterface:
    """Interface for execution history management."""

    async def get_workflow(self, workflow_id: str) -> dict[str, Any] | None:
        """Get a workflow by ID."""
        raise NotImplementedError

    async def list_executions(
        self,
        workflow_id: str,
        status: str | None = None,
        limit: int = 50,
        cursor: str | None = None,
    ) -> list[dict[str, Any]]:
        """List executions for a workflow."""
        raise NotImplementedError

    async def get_execution(
        self,
        workflow_id: str,
        execution_id: str,
    ) -> dict[str, Any] | None:
        """Get a specific execution."""
        raise NotImplementedError


class DefaultExecutionHistoryManager(ExecutionHistoryManagerInterface):
    """Default in-memory execution history manager.

    In production, this would integrate with a database or LangGraph's
    execution history.
    """

    def __init__(self) -> None:
        """Initialize with empty state."""
        self._workflows: dict[str, dict[str, Any]] = {}
        self._executions: dict[str, list[dict[str, Any]]] = {}

    async def get_workflow(self, workflow_id: str) -> dict[str, Any] | None:
        """Get a workflow by ID."""
        return self._workflows.get(workflow_id)

    async def list_executions(
        self,
        workflow_id: str,
        status: str | None = None,
        limit: int = 50,
        cursor: str | None = None,
    ) -> list[dict[str, Any]]:
        """List executions for a workflow."""
        executions = self._executions.get(workflow_id, [])

        # Apply status filter
        if status:
            executions = [e for e in executions if e.get("status") == status]

        # Apply pagination (simple offset-based for now)
        offset = int(cursor) if cursor else 0
        return executions[offset : offset + limit]

    async def get_execution(
        self,
        workflow_id: str,
        execution_id: str,
    ) -> dict[str, Any] | None:
        """Get a specific execution."""
        executions = self._executions.get(workflow_id, [])
        for execution in executions:
            if execution.get("id") == execution_id:
                return execution
        return None

    # Methods for adding data (for testing/development)

    def add_workflow(self, workflow_id: str, name: str) -> None:
        """Add a workflow."""
        self._workflows[workflow_id] = {"id": workflow_id, "name": name}

    def add_execution(
        self,
        workflow_id: str,
        execution_id: str | None = None,
        status: str = "running",
        input_data: dict[str, Any] | None = None,
    ) -> str:
        """Add an execution."""
        exec_id = execution_id or str(uuid4())

        if workflow_id not in self._executions:
            self._executions[workflow_id] = []

        self._executions[workflow_id].append(
            {
                "id": exec_id,
                "workflow_id": workflow_id,
                "status": status,
                "started_at": datetime.now(UTC).isoformat(),
                "completed_at": None,
                "input_data": input_data,
                "output_data": None,
            }
        )

        return exec_id


# ==============================================================================
# Singleton Manager
# ==============================================================================

_execution_history_manager: ExecutionHistoryManagerInterface | None = None


def get_execution_history_manager() -> ExecutionHistoryManagerInterface:
    """Get the execution history manager instance."""
    global _execution_history_manager

    if _execution_history_manager is None:
        _execution_history_manager = DefaultExecutionHistoryManager()
        logger.info("Initialized DefaultExecutionHistoryManager")

    return _execution_history_manager


def set_execution_history_manager(manager: ExecutionHistoryManagerInterface) -> None:
    """Set a custom execution history manager (for testing/DI)."""
    global _execution_history_manager
    _execution_history_manager = manager


# ==============================================================================
# Endpoints
# ==============================================================================


@workflow_executions_router.get("/workflows/{workflow_id}/executions")
async def list_executions(
    workflow_id: str,
    _: Annotated[dict[str, Any], Depends(require_workflow_viewer)],
    manager: ExecutionHistoryManagerInterface = Depends(get_execution_history_manager),
    status: str | None = Query(default=None, description="Filter by status"),
    limit: int = Query(default=50, ge=1, le=100, description="Maximum entries per page"),
    cursor: str | None = Query(default=None, description="Pagination cursor"),
) -> PaginatedExecutionResponse:
    """
    List executions for a workflow.

    Args:
        workflow_id: Workflow ID
        manager: Execution history manager (injected)
        status: Optional status filter (pending, running, completed, failed)
        limit: Maximum number of executions to return
        cursor: Pagination cursor

    Returns:
        PaginatedExecutionResponse with list of executions.

    Raises:
        404: If workflow not found.
    """
    # Check workflow exists
    workflow = await manager.get_workflow(workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail=f"Workflow not found: {workflow_id}")

    executions = await manager.list_executions(
        workflow_id=workflow_id,
        status=status,
        limit=limit,
        cursor=cursor,
    )

    items = [
        ExecutionResponse(
            id=e.get("id", ""),
            workflow_id=e.get("workflow_id", workflow_id),
            status=e.get("status", "unknown"),
            started_at=e.get("started_at", ""),
            completed_at=e.get("completed_at"),
            input_data=e.get("input_data"),
            output_data=e.get("output_data"),
            error=e.get("error"),
        )
        for e in executions
    ]

    return PaginatedExecutionResponse(
        items=items,
        total=len(items),
        next_cursor=None,  # Would be computed based on total count
    )


@workflow_executions_router.get("/workflows/{workflow_id}/executions/{execution_id}")
async def get_execution(
    workflow_id: str,
    execution_id: str,
    _: Annotated[dict[str, Any], Depends(require_workflow_viewer)],
    manager: ExecutionHistoryManagerInterface = Depends(get_execution_history_manager),
) -> ExecutionResponse:
    """
    Get a specific execution.

    Args:
        workflow_id: Workflow ID
        execution_id: Execution ID
        manager: Execution history manager (injected)

    Returns:
        ExecutionResponse with execution details.

    Raises:
        404: If workflow or execution not found.
    """
    # Check workflow exists
    workflow = await manager.get_workflow(workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail=f"Workflow not found: {workflow_id}")

    execution = await manager.get_execution(workflow_id, execution_id)
    if execution is None:
        raise HTTPException(status_code=404, detail=f"Execution not found: {execution_id}")

    return ExecutionResponse(
        id=execution.get("id", ""),
        workflow_id=execution.get("workflow_id", workflow_id),
        status=execution.get("status", "unknown"),
        started_at=execution.get("started_at", ""),
        completed_at=execution.get("completed_at"),
        input_data=execution.get("input_data"),
        output_data=execution.get("output_data"),
        error=execution.get("error"),
    )


# ==============================================================================
# Exports
# ==============================================================================

__all__ = [
    "workflow_executions_router",
    "get_execution_history_manager",
    "set_execution_history_manager",
    "ExecutionHistoryManagerInterface",
    "DefaultExecutionHistoryManager",
    "ExecutionResponse",
    "PaginatedExecutionResponse",
]
