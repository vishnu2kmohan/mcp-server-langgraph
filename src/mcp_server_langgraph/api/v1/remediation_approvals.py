"""
Remediation Approval REST API.

Provides endpoints for managing remediation approvals from alert recommendations.

Endpoints:
- GET /remediations/pending - List pending remediations
- POST /remediations/{id}/approve - Approve a remediation
- POST /remediations/{id}/reject - Reject a remediation
- GET /remediations/history - Get approval history

SECURITY:
All remediation endpoints require authentication.
Approve/reject/history operations require admin or compliance_officer role.

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from mcp_server_langgraph.alerts.approval_queue import (
    RemediationApprovalQueue,
    RemediationRequest,
    get_approval_queue,
)
from mcp_server_langgraph.alerts.feedback import (
    FeedbackStore,
    InMemoryFeedbackStore,
    RejectionReason,
)
from mcp_server_langgraph.alerts.metrics import (
    record_recommendation_approval,
    record_recommendation_rejection,
)
from mcp_server_langgraph.api.deps import get_audit_service
from mcp_server_langgraph.audit.models import (
    AuditActor,
    AuditContext,
    AuditEventCategory,
    AuditEventType,
    UnifiedAuditEvent,
)
from mcp_server_langgraph.audit.service import UnifiedAuditService
from mcp_server_langgraph.auth.middleware import get_current_user
from mcp_server_langgraph.core.interrupts.approval import ApprovalStatus

logger = logging.getLogger(__name__)

# Type alias for authenticated user dependency
CurrentUser = Annotated[dict[str, Any], Depends(get_current_user)]

# Type alias for optional audit service dependency
AuditService = Annotated[UnifiedAuditService | None, Depends(get_audit_service)]

# Global feedback store instance (configurable for production)
_feedback_store: FeedbackStore | None = None


def get_feedback_store() -> FeedbackStore:
    """
    Get the global feedback store instance.

    In development, uses InMemoryFeedbackStore.
    In production, can be configured to use PostgresFeedbackStore.

    To use PostgreSQL in production, call set_feedback_store()
    during application startup with a properly configured store.

    Example:
        from mcp_server_langgraph.alerts.feedback import PostgresFeedbackStore
        from mcp_server_langgraph.database.session import get_session_maker

        session_maker = get_session_maker(settings.database_url)
        store = PostgresFeedbackStore(session_maker)
        set_feedback_store(store)
    """
    global _feedback_store
    if _feedback_store is None:
        _feedback_store = InMemoryFeedbackStore()
    return _feedback_store


def set_feedback_store(store: FeedbackStore | None) -> None:
    """
    Set the global feedback store (for production configuration or testing).

    Args:
        store: FeedbackStore implementation to use, or None to reset.
    """
    global _feedback_store
    _feedback_store = store


# Type alias for feedback store dependency
FeedbackStoreDepends = Annotated[FeedbackStore, Depends(get_feedback_store)]


def require_admin_role(current_user: dict[str, Any]) -> None:
    """
    Require admin or compliance_officer role for remediation operations.

    SECURITY: Protects critical remediation actions from unauthorized access.
    Only admins and compliance officers can approve/reject remediations.

    Args:
        current_user: Authenticated user from get_current_user dependency

    Raises:
        HTTPException: 403 if user lacks required role
    """
    roles = current_user.get("roles", [])
    if "admin" not in roles and "compliance_officer" not in roles:
        logger.warning(
            "Unauthorized remediation access attempt",
            extra={
                "user_id": current_user.get("user_id"),
                "username": current_user.get("username"),
                "roles": roles,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or compliance officer role required for remediation operations",
        )


async def log_remediation_audit_event(
    audit_service: UnifiedAuditService | None,
    event_type: AuditEventType,
    remediation_id: str,
    alert_id: str,
    user_id: str,
    username: str,
    action: str,
    details: dict[str, Any] | None = None,
) -> None:
    """
    Log a remediation audit event for compliance tracking.

    Args:
        audit_service: The audit service (may be None if not configured).
        event_type: The type of audit event (REMEDIATION_APPROVED/REJECTED).
        remediation_id: The remediation ID being acted upon.
        alert_id: The associated alert ID.
        user_id: ID of the user performing the action.
        username: Username of the user performing the action.
        action: Description of the action (approve/reject).
        details: Additional details about the action.
    """
    if audit_service is None:
        logger.debug("Audit service not configured, skipping audit log")
        return

    try:
        event = UnifiedAuditEvent(
            category=AuditEventCategory.SYSTEM,
            event_type=event_type,
            actor=AuditActor(
                actor_id=user_id,
                actor_type="user",
                username=username,
            ),
            resource_type="remediation",
            resource_id=remediation_id,
            action=action,
            outcome="success",
            context=AuditContext(
                request_id=f"remediation-{remediation_id}",
            ),
            details={
                "alert_id": alert_id,
                **(details or {}),
            },
        )
        await audit_service.log_event(event)
        logger.debug(f"Logged remediation audit event: {event_type} for {remediation_id}")
    except Exception as e:
        # Audit logging should not fail the main operation
        logger.warning(f"Failed to log remediation audit event: {e}")


remediation_approval_router = APIRouter(prefix="/remediations", tags=["remediations"])


# Re-export RemediationRequest for API consumers
RemediationRequest = RemediationRequest


class ApproveRequest(BaseModel):
    """Request body for approving a remediation."""

    approved_by: str = Field(..., description="Email/ID of the approver")


class RejectRequest(BaseModel):
    """Request body for rejecting a remediation."""

    rejected_by: str = Field(..., description="Email/ID of the rejector")
    reason: RejectionReason = Field(RejectionReason.OTHER, description="Structured rejection reason")
    reason_detail: str | None = Field(None, description="Additional details for rejection reason")


class ApprovalResponse(BaseModel):
    """Response for approval/rejection actions."""

    remediation_id: str
    status: ApprovalStatus
    message: str


class PendingRemediationsResponse(BaseModel):
    """Response for list pending remediations."""

    remediations: list[RemediationRequest]
    count: int


class HistoryResponse(BaseModel):
    """Response for remediation history."""

    remediations: list[RemediationRequest]
    count: int


@remediation_approval_router.get(
    "/pending",
    summary="List pending remediations",
    description="Get all remediations waiting for approval. Requires admin role.",
)
async def list_pending_remediations(
    current_user: CurrentUser,
    queue: RemediationApprovalQueue = Depends(get_approval_queue),
) -> PendingRemediationsResponse:
    """
    List all pending remediations.

    Returns remediations that are awaiting human approval before execution.
    Requires admin or compliance_officer role.
    """
    require_admin_role(current_user)
    pending = await queue.list_pending()
    return PendingRemediationsResponse(
        remediations=pending,
        count=len(pending),
    )


@remediation_approval_router.post(
    "/{remediation_id}/approve",
    summary="Approve a remediation",
    description="Approve a pending remediation for execution. Requires admin role.",
)
async def approve_remediation(
    remediation_id: str,
    request: ApproveRequest,
    current_user: CurrentUser,
    audit_service: AuditService,
    feedback_store: FeedbackStoreDepends,
    queue: RemediationApprovalQueue = Depends(get_approval_queue),
) -> ApprovalResponse:
    """
    Approve a pending remediation.

    Once approved, the remediation action can be executed.
    Also saves feedback for AI learning (few-shot examples).
    Requires admin or compliance_officer role.
    """
    require_admin_role(current_user)
    try:
        result = await queue.approve_with_feedback(
            remediation_id=remediation_id,
            approved_by=request.approved_by,
            feedback_store=feedback_store,
        )

        # Record approval metric for AI recommendation quality tracking
        record_recommendation_approval(
            alert_type=result.alert_name,
            had_fewshot=False,  # TODO: Track few-shot usage in recommendation
            had_constraints=False,  # TODO: Track constraint usage in recommendation
        )

        # Log audit event for compliance
        await log_remediation_audit_event(
            audit_service=audit_service,
            event_type=AuditEventType.REMEDIATION_APPROVED,
            remediation_id=remediation_id,
            alert_id=result.alert_id,
            user_id=current_user.get("user_id", "unknown"),
            username=current_user.get("username", request.approved_by),
            action=f"Approved remediation for alert {result.alert_name}",
            details={"approved_by": request.approved_by},
        )

        return ApprovalResponse(
            remediation_id=remediation_id,
            status=result.status,
            message=f"Remediation approved by {request.approved_by}",
        )
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Remediation {remediation_id} not found",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


@remediation_approval_router.post(
    "/{remediation_id}/reject",
    summary="Reject a remediation",
    description="Reject a pending remediation. Requires admin role.",
)
async def reject_remediation(
    remediation_id: str,
    request: RejectRequest,
    current_user: CurrentUser,
    audit_service: AuditService,
    feedback_store: FeedbackStoreDepends,
    queue: RemediationApprovalQueue = Depends(get_approval_queue),
) -> ApprovalResponse:
    """
    Reject a pending remediation.

    The remediation will not be executed.
    Also saves feedback for AI constraint learning.
    Requires admin or compliance_officer role.
    """
    require_admin_role(current_user)
    try:
        result = await queue.reject_with_feedback(
            remediation_id=remediation_id,
            rejected_by=request.rejected_by,
            reason=request.reason,
            feedback_store=feedback_store,
            reason_detail=request.reason_detail,
        )

        # Record rejection metric for AI recommendation quality tracking
        record_recommendation_rejection(
            alert_type=result.alert_name,
            reason=request.reason.value,
            had_fewshot=False,  # TODO: Track few-shot usage in recommendation
            had_constraints=False,  # TODO: Track constraint usage in recommendation
        )

        # Log audit event for compliance
        await log_remediation_audit_event(
            audit_service=audit_service,
            event_type=AuditEventType.REMEDIATION_REJECTED,
            remediation_id=remediation_id,
            alert_id=result.alert_id,
            user_id=current_user.get("user_id", "unknown"),
            username=current_user.get("username", request.rejected_by),
            action=f"Rejected remediation for alert {result.alert_name}",
            details={
                "rejected_by": request.rejected_by,
                "reason": request.reason.value,
                "reason_detail": request.reason_detail,
            },
        )

        return ApprovalResponse(
            remediation_id=remediation_id,
            status=result.status,
            message=f"Remediation rejected by {request.rejected_by}",
        )
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Remediation {remediation_id} not found",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


@remediation_approval_router.get(
    "/history",
    summary="Get remediation history",
    description="Get completed (approved/rejected) remediations. Requires admin role.",
)
async def get_remediation_history(
    current_user: CurrentUser,
    limit: int = Query(default=100, ge=1, le=500, description="Maximum results"),
    offset: int = Query(default=0, ge=0, description="Results to skip"),
    queue: RemediationApprovalQueue = Depends(get_approval_queue),
) -> HistoryResponse:
    """
    Get remediation approval history.

    Returns approved and rejected remediations, sorted by most recent first.
    Requires admin or compliance_officer role.
    """
    require_admin_role(current_user)
    history = await queue.get_history(limit=limit, offset=offset)
    return HistoryResponse(
        remediations=history,
        count=len(history),
    )


@remediation_approval_router.get(
    "/{remediation_id}",
    summary="Get remediation details",
    description="Get details of a specific remediation.",
)
async def get_remediation(
    remediation_id: str,
    queue: RemediationApprovalQueue = Depends(get_approval_queue),
) -> RemediationRequest:
    """
    Get details of a specific remediation by ID.
    """
    result = await queue.get_remediation(remediation_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Remediation {remediation_id} not found",
        )
    return result
