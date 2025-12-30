"""
MCP Connection Audit Logging API

Implements audit logging for connection operations:
- Log CRUD operations on connections
- Log authentication events
- Query audit logs with filtering
- Retention policy management

Usage:
    from mcp_server_langgraph.api.v1.connection_audit import audit_router
    app.include_router(audit_router)
"""

import csv
import io
import json
from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Header, Query, Request, status
from fastapi.responses import Response
from pydantic import BaseModel, Field

from mcp_server_langgraph.auth.dependencies import require_admin
from mcp_server_langgraph.core.dependencies import get_audit_log_repository
from mcp_server_langgraph.repositories.audit_log import AuditLogRepository

# Type alias for admin user dependency
AdminUser = Annotated[dict[str, Any], Depends(require_admin)]


# ============================================================================
# Request/Response Models
# ============================================================================


class AuditLogEventRequest(BaseModel):
    """Request to log an audit event."""

    event_type: str = Field(
        ...,
        description="Type of event (e.g., connection.created, connection.deleted)",
    )
    resource_type: str = Field(
        ...,
        description="Type of resource (e.g., connection, template)",
    )
    resource_id: str = Field(
        ...,
        description="ID of the resource affected",
    )
    actor_id: str = Field(
        ...,
        description="ID of the user/service performing the action",
    )
    action: str = Field(
        ...,
        description="Action performed (e.g., create, update, delete)",
    )
    details: dict[str, Any] | None = Field(
        default=None,
        description="Additional details about the event",
    )


class AuditLogEntry(BaseModel):
    """An audit log entry."""

    id: str
    event_type: str
    resource_type: str
    resource_id: str
    actor_id: str
    action: str
    details: dict[str, Any] = Field(default_factory=dict)
    ip_address: str | None = None
    user_agent: str | None = None
    timestamp: datetime

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    """Response containing a list of audit logs."""

    logs: list[AuditLogEntry]
    total: int
    limit: int
    offset: int


class RetentionDeleteResponse(BaseModel):
    """Response for retention deletion operation."""

    deleted_count: int
    retention_days: int


# ============================================================================
# Router
# ============================================================================

audit_router = APIRouter(prefix="/connections", tags=["connection-audit"])


@audit_router.post(
    "/audit/log",
    status_code=status.HTTP_201_CREATED,
)
async def log_audit_event(
    request: Request,
    event: AuditLogEventRequest,
    admin_user: AdminUser,
    repo: AuditLogRepository = Depends(get_audit_log_repository),
    x_forwarded_for: str | None = Header(None),
    user_agent: str | None = Header(None),
) -> AuditLogEntry:
    """
    Log an audit event for a connection operation.

    Requires admin authorization.

    Records the event with timestamp, actor information, and optional details.
    Automatically captures IP address and user agent from headers.
    """
    # Extract IP address from headers or request
    ip_address = x_forwarded_for
    if not ip_address and request.client:
        ip_address = request.client.host

    log_entry = await repo.log_event(
        event_type=event.event_type,
        resource_type=event.resource_type,
        resource_id=event.resource_id,
        actor_id=event.actor_id,
        action=event.action,
        details=event.details,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return AuditLogEntry(
        id=log_entry["id"],
        event_type=log_entry["event_type"],
        resource_type=log_entry["resource_type"],
        resource_id=log_entry["resource_id"],
        actor_id=log_entry["actor_id"],
        action=log_entry["action"],
        details=log_entry.get("details", {}),
        ip_address=log_entry.get("ip_address"),
        user_agent=log_entry.get("user_agent"),
        timestamp=log_entry["timestamp"],
    )


@audit_router.get("/audit/logs")
async def query_audit_logs(
    admin_user: AdminUser,
    resource_type: str | None = Query(None, description="Filter by resource type"),
    resource_id: str | None = Query(None, description="Filter by resource ID"),
    actor_id: str | None = Query(None, description="Filter by actor ID"),
    event_type: str | None = Query(None, description="Filter by event type"),
    start_time: datetime | None = Query(None, description="Filter logs after this time"),
    end_time: datetime | None = Query(None, description="Filter logs before this time"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of logs to return"),
    offset: int = Query(0, ge=0, description="Number of logs to skip"),
    repo: AuditLogRepository = Depends(get_audit_log_repository),
) -> AuditLogListResponse:
    """
    Query audit logs with filtering and pagination.

    Requires admin authorization.

    Supports filtering by resource type, resource ID, actor, event type,
    and time range. Results are paginated with limit and offset.
    """
    logs, total = await repo.query(
        resource_type=resource_type,
        resource_id=resource_id,
        actor_id=actor_id,
        event_type=event_type,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset,
    )

    return AuditLogListResponse(
        logs=[
            AuditLogEntry(
                id=log["id"],
                event_type=log["event_type"],
                resource_type=log["resource_type"],
                resource_id=log["resource_id"],
                actor_id=log["actor_id"],
                action=log["action"],
                details=log.get("details", {}),
                ip_address=log.get("ip_address"),
                user_agent=log.get("user_agent"),
                timestamp=log["timestamp"],
            )
            for log in logs
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@audit_router.get("/{connection_id}/audit")
async def get_connection_audit_log(
    connection_id: str,
    admin_user: AdminUser,
    limit: int = Query(20, ge=1, le=100, description="Maximum number of logs to return"),
    repo: AuditLogRepository = Depends(get_audit_log_repository),
) -> AuditLogListResponse:
    """
    Get audit log for a specific connection.

    Requires admin authorization.

    Returns the audit trail for a connection, ordered by timestamp descending.
    """
    logs = await repo.get_by_resource(
        resource_type="connection",
        resource_id=connection_id,
        limit=limit,
    )

    return AuditLogListResponse(
        logs=[
            AuditLogEntry(
                id=log["id"],
                event_type=log["event_type"],
                resource_type=log["resource_type"],
                resource_id=log["resource_id"],
                actor_id=log["actor_id"],
                action=log["action"],
                details=log.get("details", {}),
                ip_address=log.get("ip_address"),
                user_agent=log.get("user_agent"),
                timestamp=log["timestamp"],
            )
            for log in logs
        ],
        total=len(logs),
        limit=limit,
        offset=0,
    )


@audit_router.delete("/audit/retention")
async def delete_old_audit_logs(
    admin_user: AdminUser,
    days: int = Query(90, ge=1, le=365, description="Delete logs older than this many days"),
    repo: AuditLogRepository = Depends(get_audit_log_repository),
) -> RetentionDeleteResponse:
    """
    Delete audit logs older than the specified retention period.

    Requires admin authorization.

    This is used for maintenance and compliance with data retention policies.
    """
    deleted_count = await repo.delete_older_than(days)

    return RetentionDeleteResponse(
        deleted_count=deleted_count,
        retention_days=days,
    )


# ============================================================================
# Export Endpoints
# ============================================================================


class AuditLogExportResponse(BaseModel):
    """Response for JSON export."""

    logs: list[AuditLogEntry]
    total: int
    exported_at: datetime


@audit_router.get("/audit/export")
async def export_audit_logs(
    admin_user: AdminUser,
    format: Literal["json", "csv"] = Query(default="json", description="Export format (json or csv)"),
    resource_type: str | None = Query(None, description="Filter by resource type"),
    resource_id: str | None = Query(None, description="Filter by resource ID"),
    actor_id: str | None = Query(None, description="Filter by actor ID"),
    event_type: str | None = Query(None, description="Filter by event type"),
    start_time: datetime | None = Query(None, description="Filter logs after this time"),
    end_time: datetime | None = Query(None, description="Filter logs before this time"),
    repo: AuditLogRepository = Depends(get_audit_log_repository),
) -> Response:
    """
    Export audit logs in JSON or CSV format.

    Requires admin authorization.

    Supports the same filters as the query endpoint. Results are returned
    as a downloadable file.

    Formats:
    - json: Complete JSON export with metadata
    - csv: Comma-separated values with headers
    """
    # Query logs (using high limit for export)
    logs, total = await repo.query(
        resource_type=resource_type,
        resource_id=resource_id,
        actor_id=actor_id,
        event_type=event_type,
        start_time=start_time,
        end_time=end_time,
        limit=10000,  # High limit for export
        offset=0,
    )

    # Convert to AuditLogEntry format
    entries = [
        AuditLogEntry(
            id=log["id"],
            event_type=log["event_type"],
            resource_type=log["resource_type"],
            resource_id=log["resource_id"],
            actor_id=log["actor_id"],
            action=log["action"],
            details=log.get("details", {}),
            ip_address=log.get("ip_address"),
            user_agent=log.get("user_agent"),
            timestamp=log["timestamp"],
        )
        for log in logs
    ]

    timestamp_str = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")

    if format == "csv":
        return _export_csv(entries, total, timestamp_str)
    else:
        return _export_json(entries, total, timestamp_str)


def _export_json(entries: list[AuditLogEntry], total: int, timestamp_str: str) -> Response:
    """Export logs as JSON."""
    export_data = {
        "logs": [
            {
                "id": entry.id,
                "event_type": entry.event_type,
                "resource_type": entry.resource_type,
                "resource_id": entry.resource_id,
                "actor_id": entry.actor_id,
                "action": entry.action,
                "details": entry.details,
                "ip_address": entry.ip_address,
                "user_agent": entry.user_agent,
                "timestamp": entry.timestamp.isoformat(),
            }
            for entry in entries
        ],
        "total": total,
        "exported_at": datetime.now(UTC).isoformat(),
    }

    content = json.dumps(export_data, indent=2)

    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="audit_logs_{timestamp_str}.json"'},
    )


def _export_csv(entries: list[AuditLogEntry], total: int, timestamp_str: str) -> Response:
    """Export logs as CSV."""
    output = io.StringIO()
    fieldnames = [
        "id",
        "event_type",
        "resource_type",
        "resource_id",
        "actor_id",
        "action",
        "details",
        "ip_address",
        "user_agent",
        "timestamp",
    ]

    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for entry in entries:
        writer.writerow(
            {
                "id": entry.id,
                "event_type": entry.event_type,
                "resource_type": entry.resource_type,
                "resource_id": entry.resource_id,
                "actor_id": entry.actor_id,
                "action": entry.action,
                "details": json.dumps(entry.details) if entry.details else "",
                "ip_address": entry.ip_address or "",
                "user_agent": entry.user_agent or "",
                "timestamp": entry.timestamp.isoformat(),
            }
        )

    content = output.getvalue()

    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="audit_logs_{timestamp_str}.csv"'},
    )
