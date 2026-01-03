"""
Execution Plans API

Provides endpoints for managing execution plan approvals.

Routes:
    GET  /plans              - List pending plans
    GET  /plans/{plan_id}    - Get a specific plan
    POST /plans/{plan_id}/approve - Approve a plan
    POST /plans/{plan_id}/reject  - Reject a plan
    GET  /sessions/{session_id}/plans - List plans for a session

Authorization:
    All endpoints require authentication. Plans are user-accessible resources
    based on session ownership.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any, Literal, cast

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from mcp_server_langgraph.auth.dependencies import get_current_user
from mcp_server_langgraph.core.models.plan_template import PlanTemplate
from mcp_server_langgraph.repositories.execution_plan import (
    ExecutionPlanRepository,
    InMemoryExecutionPlanRepository,
)
from mcp_server_langgraph.repositories.plan_template import (
    InMemoryPlanTemplateRepository,
    PlanTemplateRepository,
)

execution_plans_router = APIRouter(tags=["execution-plans"])


# ============================================================================
# Authorization Type Aliases
# ============================================================================

CurrentUser = Annotated[dict[str, Any], Depends(get_current_user)]


def _get_user_id(user: dict[str, Any]) -> str:
    """Extract user ID from authenticated user dict."""
    return (
        user.get("sub")
        or user.get("user_id")
        or user.get("preferred_username")
        or "anonymous"
    )


# ============================================================================
# Request/Response Models
# ============================================================================


class RejectRequest(BaseModel):
    """Request body for rejecting a plan."""

    reason: str = Field(description="Reason for rejection", min_length=1, max_length=500)


class SaveAsTemplateRequest(BaseModel):
    """Request body for saving a plan as a template."""

    name: str = Field(description="Template name", min_length=1, max_length=100)
    description: str = Field(description="Template description", min_length=1, max_length=500)
    tags: list[str] = Field(default_factory=list, description="Tags for categorization")


class PlanResponse(BaseModel):
    """Response model for an execution plan."""

    plan_id: str
    session_id: str
    status: str
    complexity: str
    risk_level: str
    task_type: str
    executor_model: str
    estimated_cost: str  # Decimal serialized as string
    message: str
    critic_model: str | None = None
    tools_needed: list[str] = Field(default_factory=list)
    approved_by: str | None = None
    approved_at: str | None = None
    rejected_by: str | None = None
    rejected_at: str | None = None
    rejection_reason: str | None = None


# ============================================================================
# Repository Dependency
# ============================================================================

_plan_repo: ExecutionPlanRepository | None = None


def get_plan_repo() -> ExecutionPlanRepository:
    """Get the plan repository instance."""
    global _plan_repo
    if _plan_repo is None:
        # Default to in-memory for now; production uses Postgres
        _plan_repo = InMemoryExecutionPlanRepository()
    return _plan_repo


def set_plan_repo(repo: ExecutionPlanRepository) -> None:
    """Set the plan repository instance (for testing/DI)."""
    global _plan_repo
    _plan_repo = repo


def reset_plan_repo() -> None:
    """Reset the plan repository singleton (for testing)."""
    global _plan_repo
    _plan_repo = None


# ============================================================================
# Template Repository Dependency
# ============================================================================

_template_repo: PlanTemplateRepository | None = None


def get_template_repo() -> PlanTemplateRepository:
    """Get the template repository instance."""
    global _template_repo
    if _template_repo is None:
        # Default to in-memory for now; production uses Postgres
        _template_repo = InMemoryPlanTemplateRepository()
    return _template_repo


def set_template_repo(repo: PlanTemplateRepository) -> None:
    """Set the template repository instance (for testing/DI)."""
    global _template_repo
    _template_repo = repo


def reset_template_repo() -> None:
    """Reset the template repository singleton (for testing)."""
    global _template_repo
    _template_repo = None


def _plan_to_dict(plan: Any) -> dict[str, Any]:
    """Convert ExecutionPlan to response dict."""
    return {
        "plan_id": plan.plan_id,
        "session_id": plan.session_id,
        "status": plan.status,
        "complexity": plan.complexity,
        "risk_level": plan.risk_level,
        "task_type": plan.task_type,
        "executor_model": plan.executor_model,
        "estimated_cost": str(plan.estimated_cost),
        "message": plan.message,
        "critic_model": plan.critic_model,
        "tools_needed": plan.tools_needed,
        "approved_by": plan.approved_by,
        "approved_at": plan.approved_at.isoformat() if plan.approved_at else None,
        "rejected_by": plan.rejected_by,
        "rejected_at": plan.rejected_at.isoformat() if plan.rejected_at else None,
        "rejection_reason": plan.rejection_reason,
    }


# ============================================================================
# Endpoints
# ============================================================================


@execution_plans_router.get("/plans")
async def list_pending_plans(
    current_user: CurrentUser,
) -> list[dict[str, Any]]:
    """
    List all pending execution plans.

    Returns plans with status 'awaiting_approval'.
    Requires authentication.
    """
    repo = get_plan_repo()
    plans = await repo.list_pending()
    return [_plan_to_dict(plan) for plan in plans]


@execution_plans_router.get("/plans/{plan_id}")
async def get_plan(
    plan_id: str,
    current_user: CurrentUser,
) -> dict[str, Any]:
    """
    Get a specific execution plan by ID.

    Raises:
        HTTPException 404: When plan not found
    """
    repo = get_plan_repo()
    plan = await repo.get(plan_id)

    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan {plan_id} not found",
        )

    return _plan_to_dict(plan)


@execution_plans_router.post("/plans/{plan_id}/approve")
async def approve_plan(
    plan_id: str,
    current_user: CurrentUser,
) -> dict[str, Any]:
    """
    Approve an execution plan.

    Changes the plan status from 'awaiting_approval' to 'approved'.
    Records the approver and timestamp.

    Raises:
        HTTPException 404: When plan not found
        HTTPException 409: When plan is not in 'awaiting_approval' status
    """
    repo = get_plan_repo()
    plan = await repo.get(plan_id)

    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan {plan_id} not found",
        )

    if plan.status != "awaiting_approval":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Plan {plan_id} is not awaiting approval (status: {plan.status})",
        )

    user_id = _get_user_id(current_user)
    approved_plan = plan.approve(approved_by=user_id)
    await repo.update(approved_plan)

    return _plan_to_dict(approved_plan)


@execution_plans_router.post("/plans/{plan_id}/reject")
async def reject_plan(
    plan_id: str,
    request: RejectRequest,
    current_user: CurrentUser,
) -> dict[str, Any]:
    """
    Reject an execution plan.

    Changes the plan status from 'awaiting_approval' to 'rejected'.
    Records the rejector, timestamp, and reason.

    Raises:
        HTTPException 404: When plan not found
        HTTPException 409: When plan is not in 'awaiting_approval' status
    """
    repo = get_plan_repo()
    plan = await repo.get(plan_id)

    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan {plan_id} not found",
        )

    if plan.status != "awaiting_approval":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Plan {plan_id} is not awaiting approval (status: {plan.status})",
        )

    user_id = _get_user_id(current_user)
    rejected_plan = plan.reject(rejected_by=user_id, reason=request.reason)
    await repo.update(rejected_plan)

    return _plan_to_dict(rejected_plan)


@execution_plans_router.get("/sessions/{session_id}/plans")
async def list_session_plans(
    session_id: str,
    current_user: CurrentUser,
) -> list[dict[str, Any]]:
    """
    List all execution plans for a session.

    Returns all plans (pending, approved, rejected) for the specified session.
    Requires authentication.
    """
    repo = get_plan_repo()
    plans = await repo.list_by_session(session_id)
    return [_plan_to_dict(plan) for plan in plans]


@execution_plans_router.post("/plans/{plan_id}/save-as-template")
async def save_as_template(
    plan_id: str,
    request: SaveAsTemplateRequest,
    current_user: CurrentUser,
) -> dict[str, Any]:
    """
    Save an approved execution plan as a reusable template.

    Creates a new template based on the configuration of an approved plan.
    Only approved plans can be saved as templates.

    Args:
        plan_id: The ID of the approved plan
        request: Template name, description, and tags

    Returns:
        The created template

    Raises:
        HTTPException 404: When plan not found
        HTTPException 400: When plan is not approved
    """
    plan_repo = get_plan_repo()
    template_repo = get_template_repo()

    plan = await plan_repo.get(plan_id)

    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan {plan_id} not found",
        )

    if plan.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only approved plans can be saved as templates (status: {plan.status})",
        )

    user_id = _get_user_id(current_user)

    # Map complexity to thinking_budget
    thinking_budget_map: dict[str, Literal["none", "light", "medium", "deep"]] = {
        "simple": "none",
        "complicated": "medium",
        "complex": "deep",
    }
    thinking_budget: Literal["none", "light", "medium", "deep"] = thinking_budget_map.get(
        plan.complexity, "light"
    )

    # Map risk level to critique_rounds
    critique_rounds_map = {
        "low": 0,
        "medium": 1,
        "high": 2,
    }
    critique_rounds = critique_rounds_map.get(plan.risk_level, 1)

    # Determine auto_approve based on risk
    auto_approve = plan.risk_level == "low"

    # Create template from plan configuration
    template = PlanTemplate(
        template_id=f"tmpl-{uuid.uuid4().hex[:12]}",
        name=request.name,
        description=request.description,
        orchestrator="standard",  # Default orchestrator
        thinking_budget=thinking_budget,
        critique_rounds=critique_rounds,
        auto_approve=auto_approve,
        created_by=user_id,
        tags=request.tags,
    )

    created_template = await template_repo.create(template)

    return {
        "template_id": created_template.template_id,
        "name": created_template.name,
        "description": created_template.description,
        "orchestrator": created_template.orchestrator,
        "thinking_budget": created_template.thinking_budget,
        "critique_rounds": created_template.critique_rounds,
        "auto_approve": created_template.auto_approve,
        "created_by": created_template.created_by,
        "tags": created_template.tags,
    }
