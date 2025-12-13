"""
Studio API Endpoints

REST API for Studio workflows, AI suggestions, and template recommendations.
Provides CRUD operations for workflows and AI-powered assistance features.

See ADR-0042 for Studio API design decisions.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from mcp_server_langgraph.auth.middleware import get_current_user
from mcp_server_langgraph.studio.ai.suggestions import WorkflowSuggestionAgent
from mcp_server_langgraph.studio.ai.templates import BUILT_IN_TEMPLATES, TemplateRecommender
from datetime import UTC

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
# Workflow Service (In-Memory for now, can be replaced with DB)
# =============================================================================


class WorkflowService:
    """Service for managing workflows.

    This is a simple in-memory implementation.
    In production, this would use PostgreSQL or another database.
    """

    # Class-level storage (in-memory for now)
    _workflows: dict[str, dict[str, Any]] = {}
    _counter: int = 0

    @classmethod
    async def create_workflow(
        cls,
        owner_id: str,
        name: str,
        description: str,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Create a new workflow."""
        from datetime import datetime

        cls._counter += 1
        workflow_id = f"workflow-{cls._counter}"
        now = datetime.now(UTC).isoformat()

        workflow = {
            "id": workflow_id,
            "name": name,
            "description": description,
            "nodes": nodes,
            "edges": edges,
            "owner_id": owner_id,
            "created_at": now,
            "updated_at": now,
        }
        cls._workflows[workflow_id] = workflow
        return workflow

    @classmethod
    async def get_workflow(cls, workflow_id: str) -> dict[str, Any] | None:
        """Get a workflow by ID."""
        return cls._workflows.get(workflow_id)

    @classmethod
    async def update_workflow(
        cls,
        workflow_id: str,
        owner_id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Update an existing workflow."""
        from datetime import datetime

        workflow = cls._workflows.get(workflow_id)
        if not workflow:
            return None

        # Check ownership
        if workflow["owner_id"] != owner_id:
            return None

        # Apply updates
        for key, value in updates.items():
            if value is not None:
                workflow[key] = value

        workflow["updated_at"] = datetime.now(UTC).isoformat()
        return workflow

    @classmethod
    async def delete_workflow(cls, workflow_id: str, owner_id: str) -> bool:
        """Delete a workflow."""
        workflow = cls._workflows.get(workflow_id)
        if not workflow:
            return False

        if workflow["owner_id"] != owner_id:
            return False

        del cls._workflows[workflow_id]
        return True

    @classmethod
    async def list_workflows(cls, owner_id: str) -> list[dict[str, Any]]:
        """List all workflows for a user."""
        return [w for w in cls._workflows.values() if w["owner_id"] == owner_id]

    @classmethod
    async def check_access(cls, workflow_id: str, user_id: str) -> bool:
        """Check if user has access to workflow."""
        workflow = cls._workflows.get(workflow_id)
        if not workflow:
            return False
        return bool(workflow["owner_id"] == user_id)


# =============================================================================
# Workflow Endpoints
# =============================================================================


@router.post("/workflows", status_code=status.HTTP_201_CREATED)
async def create_workflow(
    request: CreateWorkflowRequest,
    current_user: CurrentUser,
) -> WorkflowResponse:
    """
    Create a new workflow.

    Creates a new workflow for the authenticated user.

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

    workflow = await WorkflowService.create_workflow(
        owner_id=user_id,
        name=request.name,
        description=request.description,
        nodes=[n.model_dump() for n in request.nodes],
        edges=[e.model_dump() for e in request.edges],
    )

    return WorkflowResponse(**workflow)


@router.get("/workflows/{workflow_id}")
async def get_workflow(
    workflow_id: str,
    current_user: CurrentUser,
) -> WorkflowResponse:
    """
    Get a workflow by ID.

    Returns the workflow if the user has access.
    """
    user_id = current_user.get("keycloak_id") or current_user["user_id"]

    workflow = await WorkflowService.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    # Check access
    if not await WorkflowService.check_access(workflow_id, user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return WorkflowResponse(**workflow)


@router.put("/workflows/{workflow_id}")
async def update_workflow(
    workflow_id: str,
    request: UpdateWorkflowRequest,
    current_user: CurrentUser,
) -> WorkflowResponse:
    """
    Update an existing workflow.

    Only the workflow owner can update it.
    """
    user_id = current_user.get("keycloak_id") or current_user["user_id"]

    updates = request.model_dump(exclude_none=True)
    if "nodes" in updates and request.nodes:
        updates["nodes"] = [n.model_dump() for n in request.nodes]
    if "edges" in updates and request.edges:
        updates["edges"] = [e.model_dump() for e in request.edges]

    workflow = await WorkflowService.update_workflow(workflow_id, user_id, updates)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found or access denied",
        )

    return WorkflowResponse(**workflow)


@router.delete("/workflows/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    workflow_id: str,
    current_user: CurrentUser,
) -> None:
    """
    Delete a workflow.

    Permanently deletes the workflow. This action cannot be undone.
    """
    user_id = current_user.get("keycloak_id") or current_user["user_id"]

    deleted = await WorkflowService.delete_workflow(workflow_id, user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found or access denied",
        )


@router.get("/workflows")
async def list_workflows(
    current_user: CurrentUser,
) -> list[WorkflowResponse]:
    """
    List all workflows for the current user.

    Returns all workflows owned by the authenticated user.
    """
    user_id = current_user.get("keycloak_id") or current_user["user_id"]

    workflows = await WorkflowService.list_workflows(user_id)
    return [WorkflowResponse(**w) for w in workflows]


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
