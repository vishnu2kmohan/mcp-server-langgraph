"""
Plan Templates API Endpoints

FastAPI endpoints for managing reusable plan templates.
Supports CRUD operations and search functionality.

Usage:
    from mcp_server_langgraph.api.v1.plan_templates import plan_templates_router

    app.include_router(plan_templates_router, prefix="/api/v1")
"""

from __future__ import annotations

import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from mcp_server_langgraph.api.v1.serializers import template_to_dict
from mcp_server_langgraph.core.models.plan_template import PlanTemplate
from mcp_server_langgraph.repositories.plan_template import (
    InMemoryPlanTemplateRepository,
    PlanTemplateRepository,
)

# =============================================================================
# Request/Response Models
# =============================================================================


class CreateTemplateRequest(BaseModel):
    """Request body for creating a new template."""

    name: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=2000)
    orchestrator: Literal["standard", "swarm", "studio", "ux", "alert"]
    thinking_budget: Literal["none", "light", "medium", "deep"]
    critique_rounds: int = Field(ge=0, le=3)
    auto_approve: bool = False
    tags: list[str] = Field(default_factory=list)


class RecordUsageRequest(BaseModel):
    """Request body for recording template usage."""

    success: bool


class PlanTemplateResponse(BaseModel):
    """Response model for a plan template (12 fields)."""

    template_id: str
    name: str
    description: str | None  # Nullable for DB compatibility with legacy rows
    orchestrator: Literal["standard", "swarm", "studio", "ux", "alert"]
    thinking_budget: Literal["none", "light", "medium", "deep"]
    critique_rounds: int = Field(ge=0, le=3)
    auto_approve: bool
    created_by: str
    created_at: str  # ISO timestamp string
    use_count: int = Field(ge=0)
    success_rate: float = Field(ge=0.0, le=1.0)
    tags: list[str] = Field(default_factory=list)


class TemplateSearchResponse(BaseModel):
    """Paginated template search response."""

    templates: list[PlanTemplateResponse]
    total: int
    limit: int
    offset: int


# =============================================================================
# Dependencies
# =============================================================================

# Singleton repository instance for development
_template_repo: PlanTemplateRepository | None = None


def get_template_repository() -> PlanTemplateRepository:
    """Get the plan template repository (dependency injection)."""
    global _template_repo
    if _template_repo is None:
        _template_repo = InMemoryPlanTemplateRepository()
    return _template_repo


# Mock current user dependency for testing
class MockUser:
    """Mock user for testing."""

    def __init__(self, email: str = "test@example.com"):
        self.email = email


def get_current_user() -> MockUser:
    """Get current user (mock for development)."""
    return MockUser()


# Type alias for current user
CurrentUser = MockUser

# =============================================================================
# Router
# =============================================================================

plan_templates_router = APIRouter(tags=["plan-templates"])


# =============================================================================
# Endpoints
# =============================================================================


@plan_templates_router.get("/templates", response_model=list[PlanTemplateResponse])
async def list_templates(
    limit: int = Query(default=20, ge=1, le=100),
    template_repo: PlanTemplateRepository = Depends(get_template_repository),
    current_user: CurrentUser = Depends(get_current_user),
) -> list[PlanTemplateResponse]:
    """List all plan templates.

    Args:
        limit: Maximum number of templates to return
        template_repo: Template repository (injected)
        current_user: Current authenticated user (injected)

    Returns:
        List of templates
    """
    templates = await template_repo.list_all(limit=limit)
    return [PlanTemplateResponse(**template_to_dict(t)) for t in templates]


@plan_templates_router.get("/templates/{template_id}", response_model=PlanTemplateResponse)
async def get_template(
    template_id: str,
    template_repo: PlanTemplateRepository = Depends(get_template_repository),
    current_user: CurrentUser = Depends(get_current_user),
) -> PlanTemplateResponse:
    """Get a specific template by ID.

    Args:
        template_id: The template ID
        template_repo: Template repository (injected)
        current_user: Current authenticated user (injected)

    Returns:
        Template data

    Raises:
        HTTPException: 404 if template not found
    """
    template = await template_repo.get(template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return PlanTemplateResponse(**template_to_dict(template))


@plan_templates_router.post("/templates", response_model=PlanTemplateResponse)
async def create_template(
    request: CreateTemplateRequest,
    template_repo: PlanTemplateRepository = Depends(get_template_repository),
    current_user: CurrentUser = Depends(get_current_user),
) -> PlanTemplateResponse:
    """Create a new plan template.

    Args:
        request: Template creation request
        template_repo: Template repository (injected)
        current_user: Current authenticated user (injected)

    Returns:
        Created template data
    """
    template = PlanTemplate(
        template_id=f"tmpl-{uuid.uuid4().hex[:12]}",
        name=request.name,
        description=request.description,
        orchestrator=request.orchestrator,
        thinking_budget=request.thinking_budget,
        critique_rounds=request.critique_rounds,
        auto_approve=request.auto_approve,
        created_by=current_user.email,
        tags=request.tags,
    )
    created = await template_repo.create(template)
    return PlanTemplateResponse(**template_to_dict(created))


@plan_templates_router.delete("/templates/{template_id}")
async def delete_template(
    template_id: str,
    template_repo: PlanTemplateRepository = Depends(get_template_repository),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Delete a plan template.

    Args:
        template_id: The template ID to delete
        template_repo: Template repository (injected)
        current_user: Current authenticated user (injected)

    Returns:
        Deletion confirmation

    Raises:
        HTTPException: 404 if template not found
    """
    deleted = await template_repo.delete(template_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"deleted": True, "template_id": template_id}


@plan_templates_router.get("/templates/search", response_model=TemplateSearchResponse)
async def search_templates(
    query: str | None = Query(default=None, description="Text search in name/description (ILIKE)"),
    tags: str | None = Query(default=None, description="Comma-separated tags"),
    orchestrator: str | None = Query(default=None),
    sort_by: Literal["popularity", "success_rate", "recent"] | None = Query(default=None),
    sort_order: Literal["asc", "desc"] = Query(default="desc"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    template_repo: PlanTemplateRepository = Depends(get_template_repository),
    current_user: CurrentUser = Depends(get_current_user),
) -> TemplateSearchResponse:
    """Search templates with pagination and sorting.

    IMPORTANT: Use snake_case params (sort_by, sort_order) because frontend
    transformCamelToSnake converts sortBy->sort_by before sending.

    Args:
        query: Text search in name/description (uses ILIKE substring match)
        tags: Comma-separated list of tags to filter by
        orchestrator: Orchestrator type to filter by
        sort_by: Sort field (popularity=use_count, success_rate, recent=created_at)
        sort_order: Sort direction (asc/desc)
        limit: Max results per page
        offset: Skip first N results
        template_repo: Template repository (injected)
        current_user: Current authenticated user (injected)

    Returns:
        Paginated search results with templates and total count
    """
    # Build filters
    filters: dict[str, Any] = {}
    if tags:
        filters["tags"] = [t.strip() for t in tags.split(",") if t.strip()]
    if orchestrator:
        filters["orchestrator"] = orchestrator
    if query:
        filters["query"] = query

    # Sort mapping - semantic names to database fields
    sort_field_map = {
        "popularity": "use_count",
        "success_rate": "success_rate",
        "recent": "created_at",
    }
    sort_field = sort_field_map.get(sort_by, "created_at") if sort_by else "created_at"

    # Get paginated results
    templates, total = await template_repo.search(
        filters=filters,
        sort_field=sort_field,
        sort_order=sort_order,
        limit=limit,
        offset=offset,
    )

    return TemplateSearchResponse(
        templates=[PlanTemplateResponse(**template_to_dict(t)) for t in templates],
        total=total,
        limit=limit,
        offset=offset,
    )


@plan_templates_router.post("/templates/{template_id}/usage")
async def record_usage(
    template_id: str,
    request: RecordUsageRequest,
    template_repo: PlanTemplateRepository = Depends(get_template_repository),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Record template usage for metrics.

    Args:
        template_id: The template that was used
        request: Usage record request
        template_repo: Template repository (injected)
        current_user: Current authenticated user (injected)

    Returns:
        Recording confirmation
    """
    await template_repo.record_usage(template_id, success=request.success)
    return {"recorded": True, "template_id": template_id}
