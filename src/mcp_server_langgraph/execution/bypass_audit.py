"""
Bypass audit event helper functions.

Reduces duplication when logging BYPASS_* audit events across the codebase.
All bypass-related audit events use consistent actor, category, and regulation tags.

Usage:
    from mcp_server_langgraph.execution.bypass_audit import log_bypass_audit_event

    await log_bypass_audit_event(
        audit_service=audit_service,
        event_type=AuditEventType.BYPASS_ACTIVATED,
        current_user=current_user,
        resource_type="session",
        resource_id=session_id,
        action="Activated risk-aware bypass execution mode",
        details={"execution_mode": "bypass"},
    )

See: .claude/memory/execution-mode-patterns.md gotcha #6
"""

from typing import TYPE_CHECKING, Any
from uuid import uuid4

from mcp_server_langgraph.audit.models import (
    AuditActor,
    AuditContext,
    AuditEventCategory,
    AuditEventType,
    UnifiedAuditEvent,
)
from mcp_server_langgraph.execution.bypass_prometheus_metrics import (
    record_bypass_activation,
    record_bypass_approval,
    record_bypass_rejection,
)

if TYPE_CHECKING:
    from mcp_server_langgraph.audit.service import UnifiedAuditService


def create_bypass_audit_event(
    *,
    event_type: AuditEventType,
    current_user: dict[str, Any],
    resource_type: str,
    resource_id: str,
    action: str,
    details: dict[str, Any] | None = None,
    context: AuditContext | None = None,
) -> UnifiedAuditEvent:
    """
    Create a bypass-related audit event with consistent structure.

    All bypass events use:
    - Category: SYSTEM
    - Outcome: "success"
    - Regulation tags: SOC2, FedRAMP

    Args:
        event_type: One of BYPASS_ACTIVATED, BYPASS_AUTO_APPROVED,
                   BYPASS_USER_APPROVED, or BYPASS_REJECTED.
        current_user: User dict from JWT/auth context. CRITICAL: user_id is
                     already prefixed as "user:alice" - use as-is!
        resource_type: Resource being affected (e.g., "session", "execution_plan").
        resource_id: ID of the resource.
        action: Human-readable description of the action.
        details: Optional additional context (risk_level, complexity, etc.).

        context: Optional AuditContext. If None, creates a minimal context
                 with a generated request_id.

    Returns:
        UnifiedAuditEvent ready to be logged.
    """
    # CRITICAL: current_user["user_id"] is ALREADY "user:alice" (from jwt_utils.py:170)
    # Use it AS-IS - DO NOT prefix again!
    actor_id = current_user.get("user_id", "user:anonymous")

    # Use username, fallback to preferred_username
    username = current_user.get("username") or current_user.get("preferred_username")

    # Create a minimal context if not provided
    if context is None:
        context = AuditContext(request_id=str(uuid4()))

    # Use empty dict if details is None (UnifiedAuditEvent.details has default_factory=dict)
    event_details = details if details is not None else {}

    return UnifiedAuditEvent(
        category=AuditEventCategory.SYSTEM,
        event_type=event_type,
        actor=AuditActor(
            actor_id=actor_id,
            actor_type="user",
            username=username,
            organization_id=current_user.get("org_id"),
            roles=current_user.get("roles", []),
        ),
        resource_type=resource_type,
        resource_id=resource_id,
        action=action,
        outcome="success",
        context=context,
        details=event_details,
        regulation_tags=["SOC2", "FedRAMP"],
    )


def _record_prometheus_metrics(
    event_type: AuditEventType,
    current_user: dict[str, Any],
    details: dict[str, Any] | None,
) -> None:
    """
    Record Prometheus metrics for bypass audit events.

    Called BEFORE audit logging so metrics are recorded even if
    audit_service is None or fails.

    Args:
        event_type: The audit event type.
        current_user: User dict from JWT/auth context.
        details: Event details containing risk_level and complexity.
    """
    actor_id = current_user.get("user_id", "user:anonymous")
    event_details = details or {}

    if event_type == AuditEventType.BYPASS_ACTIVATED:
        record_bypass_activation(user=actor_id)
    elif event_type == AuditEventType.BYPASS_AUTO_APPROVED:
        record_bypass_approval(
            approval_type="auto",
            risk_level=event_details.get("risk_level", "low"),
            complexity=event_details.get("complexity", "simple"),
        )
    elif event_type == AuditEventType.BYPASS_USER_APPROVED:
        record_bypass_approval(
            approval_type="user",
            risk_level=event_details.get("risk_level", "low"),
            complexity=event_details.get("complexity", "simple"),
        )
    elif event_type == AuditEventType.BYPASS_REJECTED:
        record_bypass_rejection(
            risk_level=event_details.get("risk_level", "low"),
            complexity=event_details.get("complexity", "simple"),
        )
    # Other event types (like SANDBOXED_EXECUTION_AUTO_ALLOWED) don't record metrics


async def log_bypass_audit_event(
    *,
    audit_service: "UnifiedAuditService | None",
    event_type: AuditEventType,
    current_user: dict[str, Any],
    resource_type: str,
    resource_id: str,
    action: str,
    details: dict[str, Any] | None = None,
    context: AuditContext | None = None,
) -> None:
    """
    Log a bypass-related audit event with error handling.

    Guards against:
    - audit_service being None (optional dependency)
    - Exceptions from audit service (don't fail the request)

    Also records Prometheus metrics for bypass events (activation, approval,
    rejection) regardless of whether audit_service is available.

    Args:
        audit_service: Optional audit service instance.
        event_type: One of BYPASS_ACTIVATED, BYPASS_AUTO_APPROVED,
                   BYPASS_USER_APPROVED, or BYPASS_REJECTED.
        current_user: User dict from JWT/auth context.
        resource_type: Resource being affected.
        resource_id: ID of the resource.
        action: Human-readable description.
        details: Optional additional context.
        context: Optional AuditContext (e.g., from create_context_from_request).
    """
    # Record Prometheus metrics FIRST (even if audit_service is None)
    _record_prometheus_metrics(event_type, current_user, details)

    if audit_service is None:
        return

    try:
        event = create_bypass_audit_event(
            event_type=event_type,
            current_user=current_user,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            details=details,
            context=context,
        )
        await audit_service.log_event(event)
    except Exception:
        # Don't fail the request if audit logging fails
        pass
