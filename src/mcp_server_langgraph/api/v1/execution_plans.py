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
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from mcp_server_langgraph.api.deps import get_audit_service
from mcp_server_langgraph.api.v1.serializers import (
    plan_to_admin_dict,
    plan_to_dict,
    template_to_dict,
)
from mcp_server_langgraph.audit.models import AuditEventType
from mcp_server_langgraph.auth.dependencies import get_current_user, require_admin
from mcp_server_langgraph.core.dependencies import (
    get_execution_plan_repository,
    set_execution_plan_repository,
)
from mcp_server_langgraph.core.models.plan_template import PlanTemplate
from mcp_server_langgraph.execution.bypass_audit import log_bypass_audit_event
from mcp_server_langgraph.repositories.execution_plan import (
    ExecutionPlanRepository,
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
AdminUser = Annotated[dict[str, Any], Depends(require_admin)]
AuditService = Annotated[Any, Depends(get_audit_service)]


def _get_user_id(user: dict[str, Any]) -> str:
    """Extract user ID from authenticated user dict."""
    return user.get("sub") or user.get("user_id") or user.get("preferred_username") or "anonymous"


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
    """Response model for an execution plan (27 fields)."""

    # Core identification
    plan_id: str
    session_id: str
    status: str  # awaiting_approval|approved|rejected|executed|expired

    # Classification
    complexity: str  # simple|complicated|complex
    risk_level: str  # low|medium|high
    task_type: str  # chat|code|analysis|data|ops|other

    # Model configuration
    executor_model: str
    critic_model: str | None = None

    # Cost
    estimated_cost: str  # Decimal serialized as string
    actual_cost: str | None = None

    # Content
    message: str
    # v35.0: Preserve NULL semantics (None = "router didn't suggest", [] = "explicitly no tools")
    tools_needed: list[str] | None = None

    # Approval config
    force_approval: bool = False
    confidence: float = 0.0

    # Orchestrator
    suggested_orchestrator: str = "standard"
    orchestrator: str = "standard"  # Alias = suggested_orchestrator

    # Computed property
    requires_approval: bool = True

    # Thinking
    thinking_budget: str = "none"
    critique_rounds: int = 0

    # v35.0: New fields for audit trail and capability tracking
    skills_needed: list[str] | None = None
    selected_tool_ids: list[str] | None = None
    llm_provider: str | None = None
    kb_focus: str | None = None

    # v35.0 Phase 2e: Tool preference fields
    tool_preference: str | None = None
    tool_selection_mode: str | None = None

    # Timestamps
    created_at: str | None = None
    expires_at: str | None = None
    executed_at: str | None = None
    approved_by: str | None = None
    approved_at: str | None = None
    rejected_by: str | None = None
    rejected_at: str | None = None
    rejection_reason: str | None = None


class PlanListResponse(BaseModel):
    """List of execution plans with count."""

    plans: list[PlanResponse]
    total: int


class AdminPlanResponse(PlanResponse):
    """Response model for admin view with additional fields (v35.0 Phase 2f).

    Extends PlanResponse with admin-only fields for debugging and audit:
    - user_id: User who created the plan
    - created_by: User/system that created the plan
    - embedding_status: Status of embedding generation
    - embedding_error: Error message if embedding failed
    """

    # GDPR compliance fields (admin-only visibility)
    user_id: str | None = None
    created_by: str | None = None

    # Embedding status (admin debugging)
    embedding_status: str = "pending"
    embedding_error: str | None = None


class AdminPlanListResponse(BaseModel):
    """List of execution plans with admin fields (v35.0 Phase 2f)."""

    plans: list[AdminPlanResponse]
    total: int


# Literal types for strict validation at API boundary
OrchestratorType = Literal["standard", "swarm", "studio", "ux", "alert"]
ThinkingBudgetType = Literal["none", "light", "medium", "deep"]


class UpdatePlanRequest(BaseModel):
    """Request body for updating a plan before approval."""

    orchestrator: OrchestratorType | None = Field(default=None, description="Orchestrator pattern")
    thinking_budget: ThinkingBudgetType | None = Field(default=None, description="Thinking budget level")
    critique_rounds: int | None = Field(default=None, ge=0, le=3, description="Critique rounds")
    executor_model: str | None = Field(default=None, description="Executor model override")
    critic_model: str | None = Field(default=None, description="Critic model override")


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


# ============================================================================
# Repository Dependency (delegates to core.dependencies)
# ============================================================================


def get_plan_repo() -> ExecutionPlanRepository:
    """Get the plan repository instance.

    Delegates to core.dependencies.get_execution_plan_repository() for
    centralized DI management. Returns InMemory or Postgres based on settings.
    """
    return get_execution_plan_repository()


def set_plan_repo(repo: ExecutionPlanRepository) -> None:
    """Set the plan repository instance (for testing/DI).

    Delegates to core.dependencies.set_execution_plan_repository().
    """
    set_execution_plan_repository(repo)


def reset_plan_repo() -> None:
    """Reset the plan repository singleton (for testing).

    Uses core.dependencies.reset_singleton_dependencies() for full reset.
    """
    from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

    reset_singleton_dependencies()


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


# ============================================================================
# Endpoints
# ============================================================================


@execution_plans_router.get("/all", response_model=AdminPlanListResponse)
async def list_all_plans(
    admin_user: AdminUser,
    limit: int = 100,
    offset: int = 0,
) -> AdminPlanListResponse:
    """
    List all execution plans with pagination (Admin endpoint).

    v35.0: Returns all plans regardless of status, sorted by created_at DESC.
    Applies hard caps: limit ≤ 1000, offset ≤ 100000.
    Clamps negative values to 0 for consistent behavior across backends.
    Requires admin role for access (Phase 2f).

    Args:
        admin_user: Admin user (from require_admin dependency)
        limit: Maximum number of plans to return (default 100, max 1000)
        offset: Number of plans to skip (default 0, max 100000)

    Returns:
        Paginated list of all execution plans with admin fields
    """
    # Clamp negative values to 0 (consistent behavior, prevent SQL LIMIT -1 bypass)
    safe_limit = max(0, limit)
    safe_offset = max(0, offset)
    repo = get_plan_repo()
    plans = await repo.list_all(limit=safe_limit, offset=safe_offset)
    return AdminPlanListResponse(
        plans=[AdminPlanResponse(**plan_to_admin_dict(plan)) for plan in plans],
        total=len(plans),
    )


@execution_plans_router.get("/", response_model=PlanListResponse)
async def list_pending_plans(
    current_user: CurrentUser,
) -> PlanListResponse:
    """
    List all pending execution plans.

    Returns plans with status 'awaiting_approval'.
    Requires authentication.
    """
    repo = get_plan_repo()
    plans = await repo.list_pending()
    return PlanListResponse(
        plans=[PlanResponse(**plan_to_dict(plan)) for plan in plans],
        total=len(plans),
    )


@execution_plans_router.get("/{plan_id}", response_model=PlanResponse)
async def get_plan(
    plan_id: str,
    current_user: CurrentUser,
) -> PlanResponse:
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

    return PlanResponse(**plan_to_dict(plan))


@execution_plans_router.post("/{plan_id}/approve", response_model=PlanResponse)
async def approve_plan(
    plan_id: str,
    current_user: CurrentUser,
    audit_service: AuditService,
) -> PlanResponse:
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

    # Audit logging: BYPASS_USER_APPROVED event (FedRAMP/SOC2 compliance)
    await log_bypass_audit_event(
        audit_service=audit_service,
        event_type=AuditEventType.BYPASS_USER_APPROVED,
        current_user=current_user,
        resource_type="execution_plan",
        resource_id=plan_id,
        action="User approved execution plan",
        details={
            "risk_level": approved_plan.risk_level,
            "complexity": approved_plan.complexity,
            "tools_needed": approved_plan.tools_needed,
        },
    )

    return PlanResponse(**plan_to_dict(approved_plan))


@execution_plans_router.post("/{plan_id}/reject", response_model=PlanResponse)
async def reject_plan(
    plan_id: str,
    request: RejectRequest,
    current_user: CurrentUser,
    audit_service: AuditService,
) -> PlanResponse:
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

    # Audit logging: BYPASS_REJECTED event (FedRAMP/SOC2 compliance)
    await log_bypass_audit_event(
        audit_service=audit_service,
        event_type=AuditEventType.BYPASS_REJECTED,
        current_user=current_user,
        resource_type="execution_plan",
        resource_id=plan_id,
        action="User rejected execution plan",
        details={
            "risk_level": rejected_plan.risk_level,
            "complexity": rejected_plan.complexity,
            "tools_needed": rejected_plan.tools_needed,
            "rejection_reason": request.reason,
        },
    )

    return PlanResponse(**plan_to_dict(rejected_plan))


@execution_plans_router.get("/sessions/{session_id}/plans", response_model=PlanListResponse)
async def list_session_plans(
    session_id: str,
    current_user: CurrentUser,
) -> PlanListResponse:
    """
    List all execution plans for a session.

    Returns all plans (pending, approved, rejected) for the specified session.
    Requires authentication.
    """
    repo = get_plan_repo()
    plans = await repo.list_by_session(session_id)
    return PlanListResponse(
        plans=[PlanResponse(**plan_to_dict(plan)) for plan in plans],
        total=len(plans),
    )


@execution_plans_router.patch("/{plan_id}", response_model=PlanResponse)
async def update_plan(
    plan_id: str,
    request: UpdatePlanRequest,
    current_user: CurrentUser,
) -> PlanResponse:
    """
    Update an execution plan's configuration before approval.

    Only plans with status 'awaiting_approval' can be updated.
    Allows editing orchestrator, thinking_budget, critique_rounds,
    executor_model, and critic_model.

    Null-clearing: If a field is explicitly set to null in the request,
    it will be cleared. If the field is not provided, it remains unchanged.

    Raises:
        HTTPException 404: When plan not found
        HTTPException 409: When plan is not in 'awaiting_approval' status
        HTTPException 422: When executor_model is set to null (required field)
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
            detail=f"Only awaiting_approval plans can be updated (status: {plan.status})",
        )

    # Use model_fields_set to distinguish "not provided" vs "explicitly null"
    # Fields in model_fields_set were explicitly provided (even if None)
    updates: dict[str, Any] = {}
    fields_set = request.model_fields_set

    # Nullable field: critic_model - null clears it
    if "critic_model" in fields_set:
        updates["critic_model"] = request.critic_model  # Can be None to clear

    # Fields with defaults: null resets to default value
    if "orchestrator" in fields_set:
        if request.orchestrator is None:
            updates["suggested_orchestrator"] = "standard"  # Reset to default
        else:
            updates["suggested_orchestrator"] = request.orchestrator
    if "thinking_budget" in fields_set:
        if request.thinking_budget is None:
            updates["thinking_budget"] = "none"  # Reset to default
        else:
            updates["thinking_budget"] = request.thinking_budget
    if "critique_rounds" in fields_set:
        if request.critique_rounds is None:
            updates["critique_rounds"] = 0  # Reset to default
        else:
            updates["critique_rounds"] = request.critique_rounds

    # Required field: executor_model - reject null
    if "executor_model" in fields_set:
        if request.executor_model is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="executor_model cannot be null",
            )
        updates["executor_model"] = request.executor_model

    if updates:
        updated_plan = plan.model_copy(update=updates)
        await repo.update(updated_plan)
        return PlanResponse(**plan_to_dict(updated_plan))

    return PlanResponse(**plan_to_dict(plan))


@execution_plans_router.post("/{plan_id}/save-as-template", response_model=PlanTemplateResponse)
async def save_as_template(
    plan_id: str,
    request: SaveAsTemplateRequest,
    current_user: CurrentUser,
) -> PlanTemplateResponse:
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
    thinking_budget: Literal["none", "light", "medium", "deep"] = thinking_budget_map.get(plan.complexity, "light")

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

    return PlanTemplateResponse(**template_to_dict(created_template))
