"""
Workflows Router

Provides CRUD operations for workflow management under /api/v1/workflows/*.

This consolidates workflow functionality from builder and studio into a unified API.

Storage Layer:
- PostgreSQL (default): Uses PostgresWorkflowManager with FTS and composite indices
- Redis: Uses RedisWorkflowManager for fast access with TTL support

Usage:
    GET /api/v1/workflows - List all workflows (with pagination)
    GET /api/v1/workflows/{id} - Get a specific workflow
    POST /api/v1/workflows - Create a new workflow
    PUT /api/v1/workflows/{id} - Update an existing workflow
    DELETE /api/v1/workflows/{id} - Delete a workflow
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from mcp_server_langgraph.api.pagination import (
    CursorPaginatedResponse,
    CursorPaginationMetadata,
)

if TYPE_CHECKING:
    from mcp_server_langgraph.storage.workflow import PostgresWorkflowManager, RedisWorkflowManager


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


# ==============================================================================
# Workflow Service Adapter
# ==============================================================================
#
# This adapter wraps PostgresWorkflowManager or RedisWorkflowManager to provide
# a consistent interface for the API layer. It converts between storage models
# (StoredWorkflow, WorkflowSummary) and API response dictionaries.


class WorkflowServiceAdapter:
    """
    Adapter for workflow storage managers.

    Wraps PostgresWorkflowManager or RedisWorkflowManager to provide a unified
    interface for the API layer. Converts between Pydantic models and dicts.
    """

    def __init__(
        self,
        manager: PostgresWorkflowManager | RedisWorkflowManager,
    ) -> None:
        """
        Initialize the adapter.

        Args:
            manager: Workflow storage manager (PostgreSQL or Redis)
        """
        self._manager = manager

    async def list_workflows(
        self,
        cursor: str | None = None,
        limit: int = 20,
        status: str | None = None,
        owner_id: str | None = None,
        search: str | None = None,
        sort_by: str | None = "created_at",
        sort_order: str | None = "desc",
    ) -> tuple[list[dict[str, Any]], str | None]:
        """List workflows with pagination, filtering, search, and sorting."""
        summaries, next_cursor = await self._manager.list_workflows(
            user_id=owner_id,
            limit=limit,
            cursor=cursor,
            search=search,
            status=status,
            sort_by=sort_by or "updated_at",
            sort_order=sort_order or "desc",
        )

        # Convert WorkflowSummary to dict
        workflows = [
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "nodes": [],  # Summaries don't include full nodes/edges
                "edges": [],
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat(),
                "status": s.status,
                "node_count": s.node_count,
                "edge_count": s.edge_count,
            }
            for s in summaries
        ]

        return workflows, next_cursor

    async def get_workflow(self, workflow_id: str) -> dict[str, Any] | None:
        """Get a workflow by ID. Returns None if not found."""
        workflow = await self._manager.get_workflow(workflow_id)
        if workflow is None:
            return None

        return {
            "id": workflow.id,
            "name": workflow.name,
            "description": workflow.description,
            "nodes": workflow.nodes,
            "edges": workflow.edges,
            "created_at": workflow.created_at.isoformat(),
            "updated_at": workflow.updated_at.isoformat(),
            "status": workflow.status,
            "user_id": workflow.user_id,
        }

    async def create_workflow(self, workflow_data: dict[str, Any]) -> dict[str, Any]:
        """Create a new workflow. Returns the created workflow."""
        # Extract nodes and edges, converting from Pydantic models if needed
        nodes = workflow_data.get("nodes", [])
        edges = workflow_data.get("edges", [])

        # Convert node models to dicts if needed
        if nodes and hasattr(nodes[0], "model_dump"):
            nodes = [n.model_dump() for n in nodes]
        if edges and hasattr(edges[0], "model_dump"):
            edges = [e.model_dump() for e in edges]

        workflow = await self._manager.create_workflow(
            name=workflow_data["name"],
            description=workflow_data.get("description", ""),
            nodes=nodes,
            edges=edges,
            user_id=workflow_data.get("user_id"),
        )

        return {
            "id": workflow.id,
            "name": workflow.name,
            "description": workflow.description,
            "nodes": workflow.nodes,
            "edges": workflow.edges,
            "created_at": workflow.created_at.isoformat(),
            "updated_at": workflow.updated_at.isoformat(),
            "status": workflow.status,
            "user_id": workflow.user_id,
        }

    async def update_workflow(self, workflow_id: str, workflow_data: dict[str, Any]) -> dict[str, Any] | None:
        """Update a workflow. Returns None if not found."""
        # Extract update fields
        nodes = workflow_data.get("nodes")
        edges = workflow_data.get("edges")

        # Convert node models to dicts if needed
        if nodes and len(nodes) > 0 and hasattr(nodes[0], "model_dump"):
            nodes = [n.model_dump() for n in nodes]
        if edges and len(edges) > 0 and hasattr(edges[0], "model_dump"):
            edges = [e.model_dump() for e in edges]

        workflow = await self._manager.update_workflow(
            workflow_id=workflow_id,
            name=workflow_data.get("name"),
            description=workflow_data.get("description"),
            nodes=nodes,
            edges=edges,
        )

        if workflow is None:
            return None

        return {
            "id": workflow.id,
            "name": workflow.name,
            "description": workflow.description,
            "nodes": workflow.nodes,
            "edges": workflow.edges,
            "created_at": workflow.created_at.isoformat(),
            "updated_at": workflow.updated_at.isoformat(),
            "status": workflow.status,
            "user_id": workflow.user_id,
        }

    async def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow. Returns True if deleted, False if not found."""
        return await self._manager.delete_workflow(workflow_id)


# ==============================================================================
# Service Dependency Injection
# ==============================================================================

# Service singleton (lazy-initialized on first use)
_workflow_service: WorkflowServiceAdapter | None = None


def get_workflow_service() -> WorkflowServiceAdapter:
    """
    Get the workflow service instance.

    Lazy-initializes the service using the configured storage backend:
    - PostgreSQL (default): Uses PostgresWorkflowManager with FTS support
    - Redis: Uses RedisWorkflowManager for fast access

    The storage backend is determined by WORKFLOW_STORAGE_BACKEND env var.
    """
    global _workflow_service
    if _workflow_service is None:
        from mcp_server_langgraph.core.config import settings
        from mcp_server_langgraph.observability.telemetry import logger

        storage_backend = getattr(settings, "workflow_storage_backend", "memory")

        if storage_backend == "postgres" and settings.database_url:
            # Use PostgreSQL storage with FTS and cursor pagination
            from mcp_server_langgraph.storage.workflow import (
                PostgresWorkflowManager,
                create_postgres_engine,
            )

            import asyncio

            async def init_postgres_manager() -> PostgresWorkflowManager:
                engine = await create_postgres_engine(settings.database_url)
                return PostgresWorkflowManager(engine=engine)

            # Run async initialization
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            # Use Any type to allow different manager types across branches
            manager: Any = loop.run_until_complete(init_postgres_manager())
            _workflow_service = WorkflowServiceAdapter(manager)
            logger.info("Workflow service initialized with PostgreSQL storage")

        elif storage_backend == "redis" and settings.redis_url:
            # Use Redis storage
            from mcp_server_langgraph.storage.workflow import (
                RedisWorkflowManager,
                create_redis_pool,
            )

            import asyncio

            async def init_redis_manager() -> RedisWorkflowManager:
                redis_client = await create_redis_pool(settings.redis_url)
                return RedisWorkflowManager(redis_client=redis_client)

            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            manager = loop.run_until_complete(init_redis_manager())
            _workflow_service = WorkflowServiceAdapter(manager)
            logger.info("Workflow service initialized with Redis storage")

        else:
            # Fallback to in-memory storage for development/testing
            from mcp_server_langgraph.storage.workflow.manager import RedisWorkflowManager

            # Use a mock Redis for in-memory mode (fakeredis)
            try:
                import fakeredis.aioredis

                redis_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
            except ImportError:
                # If fakeredis not available, use warning
                logger.warning("No storage backend configured. Install fakeredis for in-memory mode: pip install fakeredis")
                raise RuntimeError("No workflow storage backend configured")

            manager = RedisWorkflowManager(redis_client=redis_client)
            _workflow_service = WorkflowServiceAdapter(manager)
            logger.info("Workflow service initialized with in-memory storage (fakeredis)")

    return _workflow_service


def set_workflow_service(service: WorkflowServiceAdapter) -> None:
    """Set the workflow service instance (for testing/DI)."""
    global _workflow_service
    _workflow_service = service


def reset_workflow_service() -> None:
    """Reset the workflow service singleton (for testing)."""
    global _workflow_service
    _workflow_service = None


# Type alias for dependency injection
WorkflowService = Annotated[WorkflowServiceAdapter, Depends(get_workflow_service)]


# Endpoints


@workflows_router.get("/workflows")
async def list_workflows(
    service: WorkflowService,
    cursor: str | None = Query(default=None, description="Pagination cursor"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
    status: str | None = Query(default=None, description="Filter by workflow status (draft, published, archived)"),
    owner_id: str | None = Query(default=None, description="Filter by owner user ID"),
    search: str | None = Query(default=None, min_length=1, max_length=500, description="Search in name and description"),
    sort_by: Literal["name", "created_at", "updated_at"] = Query(default="created_at", description="Field to sort by"),
    sort_order: Literal["asc", "desc"] = Query(default="desc", description="Sort order"),
) -> CursorPaginatedResponse[dict[str, Any]]:
    """
    List all workflows with cursor-based pagination.

    Supports:
    - Pagination: cursor, limit
    - Filtering: status, owner_id
    - Search: search (uses PostgreSQL Full-Text Search when available)
    - Sorting: sort_by, sort_order

    Returns a paginated list of workflows with metadata for navigation.
    """
    workflows, next_cursor = await service.list_workflows(
        cursor=cursor,
        limit=limit,
        status=status,
        owner_id=owner_id,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )

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
async def get_workflow(
    workflow_id: str,
    service: WorkflowService,
) -> WorkflowResponse:
    """
    Get a specific workflow by ID.

    Returns the complete workflow data including nodes and edges.
    """
    workflow = await service.get_workflow(workflow_id)

    if workflow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found",
        )

    return WorkflowResponse(**workflow)


@workflows_router.post("/workflows", status_code=status.HTTP_201_CREATED)
async def create_workflow(
    request: WorkflowCreateRequest,
    service: WorkflowService,
) -> WorkflowResponse:
    """
    Create a new workflow.

    The workflow is created with the provided name, description, nodes, and edges.
    """
    workflow_data = request.model_dump()
    workflow = await service.create_workflow(workflow_data)

    return WorkflowResponse(**workflow)


@workflows_router.put("/workflows/{workflow_id}")
async def update_workflow(
    workflow_id: str,
    request: WorkflowUpdateRequest,
    service: WorkflowService,
) -> WorkflowResponse:
    """
    Update an existing workflow.

    Only the provided fields are updated; others remain unchanged.
    """
    update_data = request.model_dump(exclude_unset=True)
    workflow = await service.update_workflow(workflow_id, update_data)

    if workflow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found",
        )

    return WorkflowResponse(**workflow)


@workflows_router.delete("/workflows/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    workflow_id: str,
    service: WorkflowService,
) -> None:
    """
    Delete a workflow.

    This permanently removes the workflow and cannot be undone.
    """
    deleted = await service.delete_workflow(workflow_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found",
        )
