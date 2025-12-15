"""
Studio API Endpoints

REST API for Studio workflows, AI suggestions, and template recommendations.
Provides CRUD operations for workflows and AI-powered assistance features.

NOTE: Workflow endpoints delegate to the unified /api/v1/workflows storage layer.
The legacy in-memory WorkflowService has been removed. All workflow operations
now use PostgresWorkflowManager or RedisWorkflowManager via WorkflowServiceAdapter.

See ADR-0042 for Studio API design decisions.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from mcp_server_langgraph.api.v1.workflows import WorkflowService
from mcp_server_langgraph.auth.middleware import get_current_user
from mcp_server_langgraph.studio.ai.suggestions import WorkflowSuggestionAgent
from mcp_server_langgraph.studio.ai.templates import BUILT_IN_TEMPLATES, TemplateRecommender

# Type aliases for FastAPI dependencies
CurrentUser = Annotated[dict[str, Any], Depends(get_current_user)]

router = APIRouter(
    prefix="/api/v1/studio",
    tags=["Studio"],
)


# =============================================================================
# Request/Response Models
# =============================================================================


class WorkflowNode(BaseModel):
    """A node in a workflow graph."""

    id: str
    type: str
    data: dict[str, Any] = Field(default_factory=dict)


class WorkflowEdge(BaseModel):
    """An edge connecting two workflow nodes."""

    source: str
    target: str


class CreateWorkflowRequest(BaseModel):
    """Request to create a new workflow."""

    name: str = Field(..., min_length=1, max_length=255, description="Workflow name")
    description: str = Field(default="", max_length=2000, description="Workflow description")
    nodes: list[WorkflowNode] = Field(default_factory=list)
    edges: list[WorkflowEdge] = Field(default_factory=list)


class UpdateWorkflowRequest(BaseModel):
    """Request to update an existing workflow."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    nodes: list[WorkflowNode] | None = None
    edges: list[WorkflowEdge] | None = None


class WorkflowResponse(BaseModel):
    """Response containing workflow data."""

    id: str
    name: str
    description: str
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    owner_id: str
    created_at: str
    updated_at: str


class SuggestionRequest(BaseModel):
    """Request for AI suggestions on a workflow."""

    workflow: dict[str, Any] = Field(..., description="Workflow to analyze")
    max_suggestions: int = Field(default=5, ge=1, le=20, description="Max suggestions to return")
    confidence_threshold: float = Field(default=0.0, ge=0.0, le=1.0)


class SuggestionResponse(BaseModel):
    """A single suggestion item."""

    type: str
    description: str
    confidence: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class SuggestionsResponse(BaseModel):
    """Response containing AI suggestions."""

    suggestions: list[SuggestionResponse]
    workflow_id: str | None = None


class RecommendTemplatesRequest(BaseModel):
    """Request for template recommendations."""

    description: str = Field(..., min_length=1, max_length=1000, description="Description of desired workflow")
    top_k: int = Field(default=5, ge=1, le=10, description="Maximum number of templates to return")


class TemplateRecommendation(BaseModel):
    """A single template recommendation."""

    id: str
    name: str
    description: str
    category: str
    similarity: float


class RecommendationsResponse(BaseModel):
    """Response containing template recommendations."""

    recommendations: list[TemplateRecommendation]
    query: str


class TemplateResponse(BaseModel):
    """Response containing template data."""

    id: str
    name: str
    description: str
    category: str
    tags: list[str]
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]


# =============================================================================
# Workflow Service (Unified Storage Layer)
# =============================================================================
#
# NOTE: The legacy in-memory WorkflowService has been removed.
# All workflow operations now delegate to the unified /api/v1/workflows storage
# layer via WorkflowServiceAdapter, which uses either:
# - PostgresWorkflowManager (default, with FTS and composite indices)
# - RedisWorkflowManager (for fast access with TTL support)
#
# This ensures consistent workflow storage across all API endpoints.


# =============================================================================
# Workflow Endpoints
# =============================================================================
#
# These endpoints delegate to the unified /api/v1/workflows storage layer.
# User authentication and ownership is enforced via the current_user dependency.


@router.post("/workflows", status_code=status.HTTP_201_CREATED)
async def create_workflow(
    request: CreateWorkflowRequest,
    current_user: CurrentUser,
    service: WorkflowService,
) -> WorkflowResponse:
    """
    Create a new workflow.

    Creates a new workflow for the authenticated user.
    Delegates to the unified workflow storage layer.

    Example:
        ```json
        {
            "name": "My Chatbot",
            "description": "A simple chatbot workflow",
            "nodes": [{"id": "input", "type": "input", "data": {}}],
            "edges": []
        }
        ```
    """
    user_id = current_user.get("keycloak_id") or current_user["user_id"]

    workflow_data = {
        "name": request.name,
        "description": request.description,
        "nodes": [n.model_dump() for n in request.nodes],
        "edges": [e.model_dump() for e in request.edges],
        "user_id": user_id,
    }
    workflow = await service.create_workflow(workflow_data)

    # Map to WorkflowResponse format
    return WorkflowResponse(
        id=workflow["id"],
        name=workflow["name"],
        description=workflow["description"],
        nodes=workflow["nodes"],
        edges=workflow["edges"],
        owner_id=str(workflow.get("user_id") or user_id),
        created_at=workflow["created_at"],
        updated_at=workflow["updated_at"],
    )


@router.get("/workflows/{workflow_id}")
async def get_workflow(
    workflow_id: str,
    current_user: CurrentUser,
    service: WorkflowService,
) -> WorkflowResponse:
    """
    Get a workflow by ID.

    Returns the workflow if the user has access.
    """
    user_id = current_user.get("keycloak_id") or current_user["user_id"]

    workflow = await service.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    # Check ownership (user_id must match)
    if workflow.get("user_id") and workflow["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return WorkflowResponse(
        id=workflow["id"],
        name=workflow["name"],
        description=workflow["description"],
        nodes=workflow["nodes"],
        edges=workflow["edges"],
        owner_id=str(workflow.get("user_id") or user_id),
        created_at=workflow["created_at"],
        updated_at=workflow["updated_at"],
    )


@router.put("/workflows/{workflow_id}")
async def update_workflow(
    workflow_id: str,
    request: UpdateWorkflowRequest,
    current_user: CurrentUser,
    service: WorkflowService,
) -> WorkflowResponse:
    """
    Update an existing workflow.

    Only the workflow owner can update it.
    """
    user_id = current_user.get("keycloak_id") or current_user["user_id"]

    # First, check if workflow exists and user owns it
    existing = await service.get_workflow(workflow_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    if existing.get("user_id") and existing["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Build update data
    updates: dict[str, Any] = {}
    if request.name is not None:
        updates["name"] = request.name
    if request.description is not None:
        updates["description"] = request.description
    if request.nodes is not None:
        updates["nodes"] = [n.model_dump() for n in request.nodes]
    if request.edges is not None:
        updates["edges"] = [e.model_dump() for e in request.edges]

    workflow = await service.update_workflow(workflow_id, updates)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    return WorkflowResponse(
        id=workflow["id"],
        name=workflow["name"],
        description=workflow["description"],
        nodes=workflow["nodes"],
        edges=workflow["edges"],
        owner_id=str(workflow.get("user_id") or user_id),
        created_at=workflow["created_at"],
        updated_at=workflow["updated_at"],
    )


@router.delete("/workflows/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    workflow_id: str,
    current_user: CurrentUser,
    service: WorkflowService,
) -> None:
    """
    Delete a workflow.

    Permanently deletes the workflow. This action cannot be undone.
    """
    user_id = current_user.get("keycloak_id") or current_user["user_id"]

    # First, check if workflow exists and user owns it
    existing = await service.get_workflow(workflow_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    if existing.get("user_id") and existing["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    deleted = await service.delete_workflow(workflow_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )


@router.get("/workflows")
async def list_workflows(
    current_user: CurrentUser,
    service: WorkflowService,
) -> list[WorkflowResponse]:
    """
    List all workflows for the current user.

    Returns all workflows owned by the authenticated user.
    """
    user_id = current_user.get("keycloak_id") or current_user["user_id"]

    workflows, _ = await service.list_workflows(owner_id=user_id)
    return [
        WorkflowResponse(
            id=w["id"],
            name=w["name"],
            description=w["description"],
            nodes=w.get("nodes", []),
            edges=w.get("edges", []),
            owner_id=str(w.get("user_id") or user_id),
            created_at=w["created_at"],
            updated_at=w["updated_at"],
        )
        for w in workflows
    ]


# =============================================================================
# AI Suggestion Endpoints
# =============================================================================


@router.post("/suggestions")
async def get_suggestions(
    request: SuggestionRequest,
    current_user: CurrentUser,
) -> SuggestionsResponse:
    """
    Get AI suggestions for a workflow.

    Analyzes the workflow and returns optimization suggestions.
    """
    agent = WorkflowSuggestionAgent()
    suggestions = await agent.suggest(
        workflow=request.workflow,
        max_suggestions=request.max_suggestions,
        confidence_threshold=request.confidence_threshold,
    )

    return SuggestionsResponse(
        suggestions=[
            SuggestionResponse(
                type=s.type,
                description=s.description,
                confidence=s.confidence,
                metadata=s.metadata,
            )
            for s in suggestions
        ],
        workflow_id=request.workflow.get("id"),
    )


# =============================================================================
# Template Endpoints
# =============================================================================


@router.get("/templates")
async def list_templates() -> list[TemplateResponse]:
    """
    List all available workflow templates.

    Returns all built-in templates that can be used as starting points.
    """
    return [
        TemplateResponse(
            id=t.id,
            name=t.name,
            description=t.description,
            category=t.category,
            tags=t.tags,
            nodes=t.nodes,
            edges=t.edges,
        )
        for t in BUILT_IN_TEMPLATES
    ]


@router.post("/templates/recommend")
async def recommend_templates(
    request: RecommendTemplatesRequest,
) -> RecommendationsResponse:
    """
    Get template recommendations based on description.

    Uses semantic similarity to find templates matching the description.
    """
    recommender = TemplateRecommender()
    recommendations = await recommender.recommend(
        description=request.description,
        top_k=request.top_k,
    )

    return RecommendationsResponse(
        recommendations=[
            TemplateRecommendation(
                id=r["id"],
                name=r["name"],
                description=r["description"],
                category=r["category"],
                similarity=r["similarity"],
            )
            for r in recommendations
        ],
        query=request.description,
    )
