"""
Admin Router

Provides admin-only endpoints under /api/v1/admin/*.

This router includes:
- Audit logs listing with filtering and pagination
- User CRUD operations (list, get, create, update, delete)

Usage:
    GET /api/v1/admin/audit-logs - List audit logs with optional filters
    GET /api/v1/admin/users - List all users
    GET /api/v1/admin/users/{user_id} - Get user by ID
    POST /api/v1/admin/users - Create a new user
    PUT /api/v1/admin/users/{user_id} - Update a user
    DELETE /api/v1/admin/users/{user_id} - Delete a user
"""

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field

from mcp_server_langgraph.auth.dependencies import require_admin
from mcp_server_langgraph.auth.user_provider import UserProvider
from mcp_server_langgraph.core.dependencies import get_audit_log_repository, get_user_provider
from mcp_server_langgraph.observability.telemetry import logger
from mcp_server_langgraph.repositories.audit_log import AuditLogRepository

# Type alias for admin user dependency
AdminUser = Annotated[dict[str, Any], Depends(require_admin)]

admin_router = APIRouter(prefix="/admin", tags=["admin"])


# Response Models


class AuditLogEntry(BaseModel):
    """Audit log entry model."""

    id: str = Field(..., description="Unique log entry ID")
    action: str = Field(..., description="Action performed (create, update, delete, login, etc.)")
    user_id: str = Field(..., description="ID of the user who performed the action")
    user_email: str | None = Field(default=None, description="Email of the user (if available)")
    resource_type: str = Field(..., description="Type of resource affected")
    resource_id: str = Field(..., description="ID of the resource affected")
    timestamp: str = Field(..., description="ISO 8601 timestamp of the action")
    ip_address: str | None = Field(default=None, description="IP address of the client")
    details: dict[str, Any] | None = Field(default=None, description="Additional details about the action")


class PaginatedAuditLogResponse(BaseModel):
    """Paginated response for audit logs."""

    items: list[AuditLogEntry] = Field(..., description="List of audit log entries")
    total: int = Field(..., ge=0, description="Total number of matching entries")
    next_cursor: str | None = Field(default=None, description="Cursor for next page (if more results exist)")


async def get_audit_logs(
    repository: AuditLogRepository,
    cursor: str | None = None,
    limit: int = 50,
    user_id: str | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    sort_by: str | None = None,
    sort_order: str | None = None,
) -> dict[str, Any]:
    """
    Get audit logs with optional filtering.

    Queries the audit_logs database table via the AuditLogRepository.

    Args:
        repository: Audit log repository instance
        cursor: Pagination cursor for next page (offset-based)
        limit: Maximum number of entries to return
        user_id: Filter by user ID (maps to actor_id in repository)
        action: Filter by action type (maps to event_type in repository)
        resource_type: Filter by resource type
        start_time: Filter by start time (ISO 8601)
        end_time: Filter by end time (ISO 8601)
        sort_by: Field to sort by (currently unused - repository sorts by timestamp desc)
        sort_order: Sort order (currently unused - repository sorts by timestamp desc)

    Returns:
        Dict with items, total, and next_cursor
    """
    logger.debug(
        "get_audit_logs called",
        cursor=cursor,
        limit=limit,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        start_time=start_time,
        end_time=end_time,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    # Parse cursor as offset (0 if no cursor)
    offset = int(cursor) if cursor else 0

    # Parse time strings to datetime
    start_dt: datetime | None = None
    end_dt: datetime | None = None
    if start_time:
        try:
            start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        except ValueError:
            logger.warning("Invalid start_time format", start_time=start_time)
    if end_time:
        try:
            end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        except ValueError:
            logger.warning("Invalid end_time format", end_time=end_time)

    # Query the repository
    # Note: API's user_id maps to repository's actor_id
    # Note: API's action maps to repository's event_type
    items, total = await repository.query(
        resource_type=resource_type,
        actor_id=user_id,  # API user_id -> repository actor_id
        event_type=action,  # API action -> repository event_type
        start_time=start_dt,
        end_time=end_dt,
        limit=limit,
        offset=offset,
    )

    # Map repository schema to API schema
    api_items = []
    for item in items:
        # Convert datetime to ISO string
        timestamp = item.get("timestamp")
        timestamp_str = timestamp.isoformat() if isinstance(timestamp, datetime) else str(timestamp) if timestamp else ""

        api_items.append(
            {
                "id": item.get("id", ""),
                "action": item.get("action", ""),  # Repository has both event_type and action
                "user_id": item.get("actor_id", ""),  # Repository actor_id -> API user_id
                "user_email": None,  # Not stored in repository
                "resource_type": item.get("resource_type", ""),
                "resource_id": item.get("resource_id", ""),
                "timestamp": timestamp_str,
                "ip_address": item.get("ip_address"),
                "details": item.get("details"),
            }
        )

    # Calculate next cursor
    next_offset = offset + limit
    next_cursor = str(next_offset) if next_offset < total else None

    return {"items": api_items, "total": total, "next_cursor": next_cursor}


@admin_router.get("/audit-logs")
async def list_audit_logs(
    admin_user: AdminUser,
    repository: AuditLogRepository = Depends(get_audit_log_repository),
    cursor: str | None = Query(default=None, description="Pagination cursor"),
    limit: int = Query(default=50, ge=1, le=100, description="Maximum entries per page"),
    user_id: str | None = Query(default=None, description="Filter by user ID"),
    action: str | None = Query(default=None, description="Filter by action type"),
    resource_type: str | None = Query(default=None, description="Filter by resource type"),
    start_time: str | None = Query(default=None, description="Filter by start time (ISO 8601)"),
    end_time: str | None = Query(default=None, description="Filter by end time (ISO 8601)"),
    sort_by: str | None = Query(default=None, description="Field to sort by"),
    sort_order: str | None = Query(default=None, description="Sort order (asc/desc)"),
) -> PaginatedAuditLogResponse:
    """
    List audit logs with optional filtering and pagination.

    Admin-only endpoint for viewing system audit logs.

    Args:
        repository: Audit log repository (injected via dependency)
        cursor: Pagination cursor for fetching next page
        limit: Maximum number of entries to return (1-100, default 50)
        user_id: Filter logs by user ID
        action: Filter by action type (create, update, delete, login, etc.)
        resource_type: Filter by resource type (workflow, session, etc.)
        start_time: Filter logs after this time (ISO 8601 format)
        end_time: Filter logs before this time (ISO 8601 format)
        sort_by: Field to sort by (timestamp, action, user_id, etc.)
        sort_order: Sort order (asc or desc)

    Returns:
        PaginatedAuditLogResponse with items, total count, and next cursor.
    """
    result = await get_audit_logs(
        repository=repository,
        cursor=cursor,
        limit=limit,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        start_time=start_time,
        end_time=end_time,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    return PaginatedAuditLogResponse(
        items=[AuditLogEntry(**item) for item in result.get("items", [])],
        total=result.get("total", 0),
        next_cursor=result.get("next_cursor"),
    )


# ==============================================================================
# User Management Models
# ==============================================================================


class UserResponse(BaseModel):
    """User response model for API responses."""

    user_id: str = Field(..., description="User identifier")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="Email address")
    roles: list[str] = Field(default_factory=list, description="User roles")
    active: bool = Field(default=True, description="Whether user is active")


class PaginatedUserResponse(BaseModel):
    """Paginated response for user listings."""

    items: list[UserResponse] = Field(..., description="List of users")
    total: int = Field(..., ge=0, description="Total number of users")


class CreateUserRequest(BaseModel):
    """Request model for creating a new user."""

    username: str = Field(..., min_length=1, max_length=100, description="Username")
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., min_length=8, description="Password")
    roles: list[str] = Field(default_factory=lambda: ["user"], description="User roles")


class UpdateUserRequest(BaseModel):
    """Request model for updating a user."""

    email: EmailStr | None = Field(default=None, description="New email address")
    roles: list[str] | None = Field(default=None, description="New roles")
    active: bool | None = Field(default=None, description="New active status")


# ==============================================================================
# User Management Endpoints
# ==============================================================================


@admin_router.get("/users")
async def list_users(
    admin_user: AdminUser,
    provider: UserProvider = Depends(get_user_provider),
    search: str | None = Query(default=None, description="Search filter for username/email"),
) -> PaginatedUserResponse:
    """
    List all users.

    Admin-only endpoint for viewing all users in the system.

    Args:
        provider: User provider (injected via dependency)
        search: Optional search filter

    Returns:
        PaginatedUserResponse with list of users and total count.
    """
    users = await provider.list_users()

    # Apply search filter if provided
    if search:
        search_lower = search.lower()
        users = [u for u in users if search_lower in u.username.lower() or search_lower in u.email.lower()]

    return PaginatedUserResponse(
        items=[
            UserResponse(
                user_id=u.user_id,
                username=u.username,
                email=u.email,
                roles=u.roles,
                active=u.active,
            )
            for u in users
        ],
        total=len(users),
    )


@admin_router.get("/users/{user_id}")
async def get_user(
    user_id: str,
    admin_user: AdminUser,
    provider: UserProvider = Depends(get_user_provider),
) -> UserResponse:
    """
    Get a user by username or user_id.

    Args:
        user_id: Username or user_id to look up
        provider: User provider (injected via dependency)

    Returns:
        UserResponse with user details.

    Raises:
        404: If user not found.
    """
    # Try by username first (most common), then by user_id
    user = await provider.get_user_by_username(user_id)
    if user is None:
        user = await provider.get_user_by_id(user_id)

    if user is None:
        raise HTTPException(status_code=404, detail=f"User not found: {user_id}")

    return UserResponse(
        user_id=user.user_id,
        username=user.username,
        email=user.email,
        roles=user.roles,
        active=user.active,
    )


@admin_router.post("/users", status_code=201)
async def create_user(
    request: CreateUserRequest,
    admin_user: AdminUser,
    provider: UserProvider = Depends(get_user_provider),
) -> UserResponse:
    """
    Create a new user.

    Args:
        request: User creation request
        provider: User provider (injected via dependency)

    Returns:
        UserResponse with created user details.

    Raises:
        409: If user already exists.
    """
    # Check if user already exists
    existing = await provider.get_user_by_username(request.username)
    if existing:
        raise HTTPException(status_code=409, detail=f"User already exists: {request.username}")

    try:
        user = await provider.create_user(
            username=request.username,
            email=request.email,
            password=request.password,
            roles=request.roles,
        )

        logger.info(f"Created user: {request.username}")

        return UserResponse(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            roles=user.roles,
            active=user.active,
        )

    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e


@admin_router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    request: UpdateUserRequest,
    admin_user: AdminUser,
    provider: UserProvider = Depends(get_user_provider),
) -> UserResponse:
    """
    Update a user.

    Args:
        user_id: Username or user_id to update
        request: User update request
        provider: User provider (injected via dependency)

    Returns:
        UserResponse with updated user details.

    Raises:
        404: If user not found.
    """
    # Check if user exists
    existing = await provider.get_user_by_username(user_id)
    if existing is None:
        existing = await provider.get_user_by_id(user_id)

    if existing is None:
        raise HTTPException(status_code=404, detail=f"User not found: {user_id}")

    try:
        # Use the username from the found user
        user = await provider.update_user(
            username=existing.username,
            email=request.email,
            roles=request.roles,
            active=request.active,
        )

        logger.info(f"Updated user: {existing.username}")

        return UserResponse(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            roles=user.roles,
            active=user.active,
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@admin_router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: str,
    admin_user: AdminUser,
    provider: UserProvider = Depends(get_user_provider),
) -> None:
    """
    Delete a user.

    Args:
        user_id: Username or user_id to delete
        provider: User provider (injected via dependency)

    Returns:
        No content on success.

    Raises:
        404: If user not found.
    """
    # Check if user exists
    existing = await provider.get_user_by_username(user_id)
    if existing is None:
        existing = await provider.get_user_by_id(user_id)

    if existing is None:
        raise HTTPException(status_code=404, detail=f"User not found: {user_id}")

    deleted = await provider.delete_user(existing.username)

    if not deleted:
        raise HTTPException(status_code=404, detail=f"User not found: {user_id}")

    logger.info(f"Deleted user: {existing.username}")


# ============================================================================
# User API Key Management
# ============================================================================


class UserApiKeyResponse(BaseModel):
    """Response with user API key information."""

    user_id: str = Field(description="The user ID")
    api_key: str | None = Field(None, description="The API key (full key on generation)")
    masked_key: str | None = Field(None, description="Masked key for display")
    created_at: int | None = Field(None, description="Creation timestamp (epoch ms)")


@admin_router.get("/users/{user_id}/api-key")
async def get_user_api_key(
    user_id: str,
    admin_user: AdminUser,
    provider: UserProvider = Depends(get_user_provider),
) -> UserApiKeyResponse:
    """
    Get the API key for a user (masked for security).

    Returns a masked version of the API key for display purposes.
    The full key is only returned when generating a new key.

    Args:
        user_id: Username or user_id

    Returns:
        UserApiKeyResponse with masked_key
    """
    # Check if user exists
    existing = await provider.get_user_by_username(user_id)
    if existing is None:
        existing = await provider.get_user_by_id(user_id)

    if existing is None:
        raise HTTPException(status_code=404, detail=f"User not found: {user_id}")

    # TODO: Retrieve actual API key from storage
    # For now, return a mock masked key
    masked_key = "sk-****...****" if existing else None

    return UserApiKeyResponse(
        user_id=existing.user_id,
        masked_key=masked_key,
        created_at=None,
    )


@admin_router.post("/users/{user_id}/api-key")
async def generate_user_api_key(
    user_id: str,
    admin_user: AdminUser,
    provider: UserProvider = Depends(get_user_provider),
) -> UserApiKeyResponse:
    """
    Generate a new API key for a user.

    This invalidates any existing API key and generates a new one.
    The full key is returned only once - it cannot be retrieved later.

    Args:
        user_id: Username or user_id

    Returns:
        UserApiKeyResponse with the new api_key (full key)
    """
    import secrets
    import time

    # Check if user exists
    existing = await provider.get_user_by_username(user_id)
    if existing is None:
        existing = await provider.get_user_by_id(user_id)

    if existing is None:
        raise HTTPException(status_code=404, detail=f"User not found: {user_id}")

    # Generate a new API key
    api_key = f"sk-{secrets.token_urlsafe(32)}"
    created_at = int(time.time() * 1000)

    # TODO: Store the hashed API key in the database

    logger.info(
        "API key generated for user",
        extra={
            "user_id": existing.user_id,
            "audit_event_type": "admin.api_key_generated",
        },
    )

    return UserApiKeyResponse(
        user_id=existing.user_id,
        api_key=api_key,
        masked_key=f"sk-{api_key[3:7]}...{api_key[-4:]}",
        created_at=created_at,
    )
