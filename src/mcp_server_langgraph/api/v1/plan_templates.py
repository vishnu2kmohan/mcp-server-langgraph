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


@plan_templates_router.get("/templates")
async def list_templates(
    limit: int = Query(default=20, ge=1, le=100),
    template_repo: PlanTemplateRepository = Depends(get_template_repository),
    current_user: CurrentUser = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List all plan templates.

    Args:
        limit: Maximum number of templates to return
        template_repo: Template repository (injected)
        current_user: Current authenticated user (injected)

    Returns:
        List of templates
    """
    templates = await template_repo.list_all(limit=limit)
    return [_template_to_dict(t) for t in templates]


@plan_templates_router.get("/templates/{template_id}")
async def get_template(
    template_id: str,
    template_repo: PlanTemplateRepository = Depends(get_template_repository),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
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
    return _template_to_dict(template)


@plan_templates_router.post("/templates")
async def create_template(
    request: CreateTemplateRequest,
    template_repo: PlanTemplateRepository = Depends(get_template_repository),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
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
    return _template_to_dict(created)


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


@plan_templates_router.get("/templates/search")
async def search_templates(
    tags: str | None = Query(default=None, description="Comma-separated tags"),
    orchestrator: str | None = Query(default=None),
    template_repo: PlanTemplateRepository = Depends(get_template_repository),
    current_user: CurrentUser = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Search templates by tags or orchestrator type.

    Args:
        tags: Comma-separated list of tags to search for
        orchestrator: Orchestrator type to filter by
        template_repo: Template repository (injected)
        current_user: Current authenticated user (injected)

    Returns:
        List of matching templates
    """
    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        templates = await template_repo.find_by_tags(tag_list)
    elif orchestrator:
        templates = await template_repo.find_by_orchestrator(orchestrator)
    else:
        templates = await template_repo.list_all()

    return [_template_to_dict(t) for t in templates]


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


# =============================================================================
# Helpers
# =============================================================================


def _template_to_dict(template: PlanTemplate) -> dict[str, Any]:
    """Convert a PlanTemplate to a dictionary for API response."""
    return {
        "template_id": template.template_id,
        "name": template.name,
        "description": template.description,
        "orchestrator": template.orchestrator,
        "thinking_budget": template.thinking_budget,
        "critique_rounds": template.critique_rounds,
        "auto_approve": template.auto_approve,
        "created_by": template.created_by,
        "created_at": template.created_at.isoformat(),
        "use_count": template.use_count,
        "success_rate": template.success_rate,
        "tags": template.tags,
    }
