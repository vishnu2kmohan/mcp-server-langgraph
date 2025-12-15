"""
Unified Audit API endpoints.

Provides RESTful endpoints for:
- Querying audit events with filters
- Getting specific event details
- Verifying hash chain integrity
- Exporting audit logs for compliance
- Managing retention policies

These endpoints support compliance requirements for:
- GDPR, HIPAA, SOC 2, FedRAMP, EU AI Act

SECURITY:
All audit endpoints require authentication.
Sensitive operations (export, retention, integrity) require admin role.
"""

import logging
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field

from mcp_server_langgraph.audit.constants import Regulation
from mcp_server_langgraph.audit.service import UnifiedAuditService
from mcp_server_langgraph.auth.middleware import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["audit"])

# Type alias for authenticated user dependency
CurrentUser = Annotated[dict[str, Any], Depends(get_current_user)]


def require_admin_role(current_user: dict[str, Any]) -> None:
    """
    Require admin role for sensitive audit operations.

    SECURITY: Protects sensitive compliance data from unauthorized access.
    Audit log access should be restricted to compliance officers and admins.

    Args:
        current_user: Authenticated user from get_current_user dependency

    Raises:
        HTTPException: 403 if user lacks admin role
    """
    roles = current_user.get("roles", [])
    if "admin" not in roles and "compliance_officer" not in roles:
        logger.warning(
            "Unauthorized audit access attempt",
            extra={
                "user_id": current_user.get("user_id"),
                "username": current_user.get("username"),
                "roles": roles,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or compliance officer role required for audit access",
        )


# Response models
class AuditEventResponse(BaseModel):
    """Response model for audit event."""

    event_id: str
    timestamp: str
    category: str
    event_type: str
    actor: dict[str, Any]
    resource_type: str
    resource_id: str
    action: str
    outcome: str
    context: dict[str, Any] | None = None
    details: dict[str, Any] | None = None
    ai_operation: dict[str, Any] | None = None
    regulation_tags: list[str] | None = None
    sequence_number: int | None = None
    event_hash: str | None = None


class AuditEventsListResponse(BaseModel):
    """Response model for paginated audit events list."""

    events: list[dict[str, Any]]
    total: int
    page: int = 1
    page_size: int = 50


class IntegrityVerificationResponse(BaseModel):
    """Response model for integrity verification."""

    start_time: str
    end_time: str
    events_verified: int
    chain_valid: bool
    errors: list[str]
    verification_time: float
    verified_at: str | None = None


class RetentionStatusResponse(BaseModel):
    """Response model for retention status."""

    regulations: dict[str, dict[str, int]] = Field(default_factory=dict)


class RetentionApplyResponse(BaseModel):
    """Response model for retention policy application."""

    regulation: str
    deleted_count: int


# Dependency for audit service
_audit_service: UnifiedAuditService | None = None


def get_audit_service() -> UnifiedAuditService:
    """Get the audit service instance."""
    global _audit_service
    if _audit_service is None:
        raise HTTPException(
            status_code=503,
            detail="Audit service not initialized",
        )
    return _audit_service


def set_audit_service(service: UnifiedAuditService) -> None:
    """Set the audit service instance (for app initialization)."""
    global _audit_service
    _audit_service = service


@router.get("/events")
async def list_audit_events(
    current_user: CurrentUser,
    service: Annotated[UnifiedAuditService, Depends(get_audit_service)],
    category: str | None = Query(None, description="Filter by event category"),
    event_type: str | None = Query(None, description="Filter by event type"),
    regulation: str | None = Query(None, description="Filter by regulation tag"),
    actor_id: str | None = Query(None, description="Filter by actor ID"),
    resource_type: str | None = Query(None, description="Filter by resource type"),
    resource_id: str | None = Query(None, description="Filter by resource ID"),
    start_time: datetime | None = Query(None, description="Start of time range"),
    end_time: datetime | None = Query(None, description="End of time range"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Page size"),
) -> AuditEventsListResponse:
    """
    List audit events with optional filters.

    Requires authentication and admin/compliance_officer role.

    Supports filtering by:
    - category: Event category (authentication, data_access, etc.)
    - event_type: Specific event type
    - regulation: Regulation tag (GDPR, HIPAA, etc.)
    - actor_id: Actor identifier
    - resource_type/resource_id: Resource filters
    - start_time/end_time: Time range

    Results are paginated with configurable page size.
    """
    require_admin_role(current_user)
    events, total = await service.query_events(
        category=category,
        event_type=event_type,
        regulation=regulation,
        actor_id=actor_id,
        resource_type=resource_type,
        resource_id=resource_id,
        start_time=start_time,
        end_time=end_time,
        page=page,
        page_size=page_size,
    )

    return AuditEventsListResponse(
        events=events,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/events/{event_id}")
async def get_audit_event(
    event_id: str,
    current_user: CurrentUser,
    service: Annotated[UnifiedAuditService, Depends(get_audit_service)],
) -> dict[str, Any]:
    """
    Get a specific audit event by ID.

    Requires authentication and admin/compliance_officer role.

    Returns the full event details including:
    - Actor information
    - Context (trace ID, span ID, etc.)
    - AI operation details (if applicable)
    - Integrity information (hash, sequence)
    """
    require_admin_role(current_user)
    event = await service.get_event(event_id)

    if event is None:
        raise HTTPException(
            status_code=404,
            detail=f"Audit event not found: {event_id}",
        )

    return event


@router.get("/integrity/verify")
async def verify_integrity(
    current_user: CurrentUser,
    service: Annotated[UnifiedAuditService, Depends(get_audit_service)],
    start_time: datetime = Query(..., description="Start of time range"),
    end_time: datetime = Query(..., description="End of time range"),
) -> IntegrityVerificationResponse:
    """
    Verify audit log integrity for a time range.

    Requires authentication and admin/compliance_officer role.

    Performs cryptographic verification of the hash chain including:
    - Hash computation verification
    - Chain linkage validation
    - Sequence number continuity check

    This endpoint supports FedRAMP AU-9 compliance for
    protecting audit information from unauthorized modification.
    """
    require_admin_role(current_user)
    report = await service.get_integrity_report(start_time, end_time)

    return IntegrityVerificationResponse(
        start_time=report["start_time"],
        end_time=report["end_time"],
        events_verified=report["events_verified"],
        chain_valid=report["chain_valid"],
        errors=report.get("errors", []),
        verification_time=report["verification_time"],
        verified_at=report.get("verified_at"),
    )


@router.get("/export")
async def export_audit_logs(
    current_user: CurrentUser,
    service: Annotated[UnifiedAuditService, Depends(get_audit_service)],
    format: str = Query("json", description="Export format: json or csv"),
    start_time: datetime = Query(..., description="Start of time range"),
    end_time: datetime = Query(..., description="End of time range"),
    category: str | None = Query(None, description="Filter by category"),
    regulation: str | None = Query(None, description="Filter by regulation"),
) -> Response:
    """
    Export audit logs for compliance reporting.

    Requires authentication and admin/compliance_officer role.

    Supports JSON and CSV formats. Time range is required to
    prevent accidental export of entire audit log.

    Use this endpoint to generate evidence for:
    - GDPR Article 30 Records of Processing
    - HIPAA 164.312(b) Audit Controls
    - SOC 2 Type II Evidence
    - FedRAMP AU Controls
    """
    require_admin_role(current_user)
    if format.lower() == "csv":
        csv_content = await service.export_events_csv(
            start_time=start_time,
            end_time=end_time,
            category=category,
            regulation=regulation,
        )

        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=audit_export_{start_time.date()}_{end_time.date()}.csv"},
        )
    else:
        # JSON format
        events = await service.export_events(
            start_time=start_time,
            end_time=end_time,
            category=category,
            regulation=regulation,
        )

        import json

        json_content = json.dumps(events, indent=2, default=str)

        return Response(
            content=json_content,
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=audit_export_{start_time.date()}_{end_time.date()}.json"},
        )


@router.get("/retention/status")
async def get_retention_status(
    current_user: CurrentUser,
    service: Annotated[UnifiedAuditService, Depends(get_audit_service)],
) -> dict[str, dict[str, int]]:
    """
    Get retention status per regulation.

    Requires authentication and admin/compliance_officer role.

    Returns counts for each regulation showing:
    - total: Total events tagged with regulation
    - expiring_soon: Events expiring within 30 days

    Use this to monitor compliance with retention requirements.
    """
    require_admin_role(current_user)
    return await service.get_retention_status()


@router.post("/retention/apply")
async def apply_retention_policy(
    current_user: CurrentUser,
    service: Annotated[UnifiedAuditService, Depends(get_audit_service)],
    regulation: str = Query(..., description="Regulation to apply retention for"),
) -> RetentionApplyResponse:
    """
    Apply retention policy for a specific regulation.

    Requires authentication and admin/compliance_officer role.

    Deletes audit events that have exceeded their retention period
    based on the regulation's requirements:
    - GDPR: 7 years
    - HIPAA: 6 years
    - FedRAMP: 7 years
    - EU AI Act: 6 months
    - SOC 2: 3 years

    Returns the count of deleted events.
    """
    require_admin_role(current_user)
    try:
        reg = Regulation(regulation)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid regulation: {regulation}. Valid values: {[r.value for r in Regulation]}",
        )

    deleted = await service.apply_retention_policy(reg)

    return RetentionApplyResponse(
        regulation=regulation,
        deleted_count=deleted,
    )
