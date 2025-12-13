"""
Workflows Router

Provides CRUD operations for workflow management under /api/v1/workflows/*.

This consolidates workflow functionality from builder and studio into a unified API.

Usage:
    GET /api/v1/workflows - List all workflows (with pagination)
    GET /api/v1/workflows/{id} - Get a specific workflow
    POST /api/v1/workflows - Create a new workflow
    PUT /api/v1/workflows/{id} - Update an existing workflow
    DELETE /api/v1/workflows/{id} - Delete a workflow
"""

from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from mcp_server_langgraph.api.pagination import (
    CursorPaginatedResponse,
    CursorPaginationMetadata,
)


workflows_router = APIRouter(tags=["workflows"])


# Request/Response Models


class NodePosition(BaseModel):
    """Position of a node in the workflow canvas."""

    x: float = Field(description="X coordinate")
    y: float = Field(description="Y coordinate")


class WorkflowNode(BaseModel):
    """A node in the workflow graph."""

    id: str = Field(description="Unique identifier for the node")
    type: str = Field(description="Node type (start, llm, tool, condition, end)")
    position: NodePosition = Field(description="Position on the canvas")
    data: dict[str, Any] = Field(default_factory=dict, description="Node-specific data")


class WorkflowEdge(BaseModel):
    """An edge connecting two nodes in the workflow."""

    source: str = Field(description="Source node ID")
    target: str = Field(description="Target node ID")
    label: str | None = Field(default=None, description="Edge label")


class WorkflowCreateRequest(BaseModel):
    """Request body for creating a workflow."""

    name: str = Field(description="Workflow name", min_length=1, max_length=255)
    description: str | None = Field(default=None, description="Workflow description")
    nodes: list[WorkflowNode] = Field(default_factory=list, description="Workflow nodes")
    edges: list[WorkflowEdge] = Field(default_factory=list, description="Workflow edges")


class WorkflowUpdateRequest(BaseModel):
    """Request body for updating a workflow."""

    name: str | None = Field(default=None, description="Workflow name", max_length=255)
    description: str | None = Field(default=None, description="Workflow description")
    nodes: list[WorkflowNode] | None = Field(default=None, description="Workflow nodes")
    edges: list[WorkflowEdge] | None = Field(default=None, description="Workflow edges")


class WorkflowResponse(BaseModel):
    """Response model for a workflow."""

    id: str = Field(description="Workflow ID")
    name: str = Field(description="Workflow name")
    description: str | None = Field(default=None, description="Workflow description")
    nodes: list[dict[str, Any]] = Field(default_factory=list, description="Workflow nodes")
    edges: list[dict[str, Any]] = Field(default_factory=list, description="Workflow edges")
    created_at: str | None = Field(default=None, description="Creation timestamp")
    updated_at: str | None = Field(default=None, description="Last update timestamp")


# Service Interface (will be implemented in Phase 4: Storage Consolidation)


class WorkflowService:
    """Interface for workflow operations. Implemented by storage layer."""

    async def list_workflows(self, cursor: str | None = None, limit: int = 20) -> tuple[list[dict[str, Any]], str | None]:
        """List workflows with pagination. Returns (workflows, next_cursor)."""
        raise NotImplementedError

    async def get_workflow(self, workflow_id: str) -> dict[str, Any] | None:
        """Get a workflow by ID. Returns None if not found."""
        raise NotImplementedError

    async def create_workflow(self, workflow_data: dict[str, Any]) -> dict[str, Any]:
        """Create a new workflow. Returns the created workflow."""
        raise NotImplementedError

    async def update_workflow(self, workflow_id: str, workflow_data: dict[str, Any]) -> dict[str, Any] | None:
        """Update a workflow. Returns None if not found."""
        raise NotImplementedError

    async def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow. Returns True if deleted, False if not found."""
        raise NotImplementedError


# Service singleton (will be replaced by dependency injection in Phase 4)
_workflow_service: WorkflowService | None = None


def get_workflow_service() -> WorkflowService:
    """Get the workflow service instance."""
    global _workflow_service
    if _workflow_service is None:
        _workflow_service = WorkflowService()
    return _workflow_service


def set_workflow_service(service: WorkflowService) -> None:
    """Set the workflow service instance (for testing/DI)."""
    global _workflow_service
    _workflow_service = service


# Endpoints


@workflows_router.get("/workflows")
async def list_workflows(
    cursor: str | None = Query(default=None, description="Pagination cursor"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
) -> CursorPaginatedResponse[dict[str, Any]]:
    """
    List all workflows with cursor-based pagination.

    Returns a paginated list of workflows with metadata for navigation.
    """
    service = get_workflow_service()
    workflows, next_cursor = await service.list_workflows(cursor=cursor, limit=limit)

    # Build pagination metadata
    has_next = next_cursor is not None
    pagination = CursorPaginationMetadata(
        next_cursor=next_cursor,
        prev_cursor=None,  # Would require reverse pagination support
        has_next=has_next,
        has_prev=cursor is not None,
        count=len(workflows),
    )

    return CursorPaginatedResponse(data=workflows, pagination=pagination)


@workflows_router.get("/workflows/{workflow_id}")
async def get_workflow(workflow_id: str) -> WorkflowResponse:
    """
    Get a specific workflow by ID.

    Returns the complete workflow data including nodes and edges.
    """
    service = get_workflow_service()
    workflow = await service.get_workflow(workflow_id)

    if workflow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found",
        )

    return WorkflowResponse(**workflow)


@workflows_router.post("/workflows", status_code=status.HTTP_201_CREATED)
async def create_workflow(request: WorkflowCreateRequest) -> WorkflowResponse:
    """
    Create a new workflow.

    The workflow is created with the provided name, description, nodes, and edges.
    """
    service = get_workflow_service()
    workflow_data = request.model_dump()
    workflow = await service.create_workflow(workflow_data)

    return WorkflowResponse(**workflow)


@workflows_router.put("/workflows/{workflow_id}")
async def update_workflow(workflow_id: str, request: WorkflowUpdateRequest) -> WorkflowResponse:
    """
    Update an existing workflow.

    Only the provided fields are updated; others remain unchanged.
    """
    service = get_workflow_service()
    update_data = request.model_dump(exclude_unset=True)
    workflow = await service.update_workflow(workflow_id, update_data)

    if workflow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found",
        )

    return WorkflowResponse(**workflow)


@workflows_router.delete("/workflows/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(workflow_id: str) -> None:
    """
    Delete a workflow.

    This permanently removes the workflow and cannot be undone.
    """
    service = get_workflow_service()
    deleted = await service.delete_workflow(workflow_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found",
        )
