"""
MCP Connections API Endpoints

Implements CRUD operations for MCP server connections with:
- OAuth2 authentication (per MCP 2025-03-26 / 2025-06-18 spec)
- API Key authentication
- Secure credential storage via secrets provider
- OpenFGA authorization for connection ownership/viewing

Usage:
    from mcp_server_langgraph.api.v1.connections import connections_router
    app.include_router(connections_router)
"""

from secrets import token_urlsafe
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from mcp_server_langgraph.auth.dependencies import (
    get_current_user,
    require_connection_owner,
    require_connection_viewer,
)
from mcp_server_langgraph.core.config import settings
from mcp_server_langgraph.middleware.rate_limiter import (
    rate_limit_for_oauth2_callback,
    rate_limit_for_oauth2_start,
)

from mcp_server_langgraph.core.dependencies import (
    MCPClient,
    OAuth2Service,
    get_audit_log_repository,
    get_connection_repository,
    get_mcp_client,
    get_oauth2_service,
)
from mcp_server_langgraph.repositories.audit_log import AuditLogRepository
from mcp_server_langgraph.repositories.connections import ConnectionRepository
from mcp_server_langgraph.storage.models import (
    MCPConnection,
    MCPConnectionCreate,
    MCPConnectionSummary,
    MCPConnectionTestResult,
    MCPConnectionUpdate,
    OAuth2StartResponse,
)


# ============================================================================
# Response Models
# ============================================================================


class ConnectionListResponse(BaseModel):
    """Response model for listing connections."""

    items: list[MCPConnectionSummary]
    total: int
    cursor: str | None = None


class ConnectionResponse(BaseModel):
    """Full connection response (without secrets).

    SECURITY: This model intentionally excludes sensitive fields:
    - env: Contains environment variables (may include secrets)
    - oauth2_config: Contains OAuth2 configuration
    - command/args: System paths (security exposure risk)
    """

    id: str
    name: str
    description: str | None = None
    url: str
    transport: str  # Required: "streamable_http" or "stdio"
    auth_type: str
    status: str
    scope: str = "user"  # ADR-0102 Phase 6: user, project, or session
    server_name: str | None = None
    server_version: str | None = None
    tool_count: int = 0
    resource_count: int = 0
    prompt_count: int = 0
    created_at: str
    updated_at: str


def to_connection_response(connection: MCPConnection) -> ConnectionResponse:
    """Convert MCPConnection to sanitized ConnectionResponse.

    SECURITY: This function filters out sensitive fields:
    - env: Environment variables (may contain secrets)
    - oauth2_config: OAuth2 configuration with potential secrets
    - command/args: System paths
    """
    return ConnectionResponse(
        id=connection.id,
        name=connection.name,
        description=connection.description,
        url=connection.url,
        transport=connection.transport,
        auth_type=connection.auth_type,
        status=connection.status,
        scope=connection.scope,  # ADR-0102 Phase 6
        server_name=connection.server_name,
        server_version=connection.server_version,
        tool_count=connection.tool_count,
        resource_count=connection.resource_count,
        prompt_count=connection.prompt_count,
        created_at=connection.created_at.isoformat() if connection.created_at else "",
        updated_at=connection.updated_at.isoformat() if connection.updated_at else "",
    )


class OAuth2CallbackRequest(BaseModel):
    """Request body for OAuth2 callback."""

    code: str = Field(..., description="Authorization code from OAuth provider")
    state: str = Field(..., description="State parameter for CSRF protection")


class OAuth2CallbackResponse(BaseModel):
    """Response from OAuth2 callback."""

    status: Literal["success"] = "success"
    message: str = "OAuth2 authorization completed"
    connection_id: str = Field(..., description="ID of the authorized connection")
    popup: bool = Field(
        default=False,
        description="If true, the callback was initiated from a popup flow",
    )


# ============================================================================
# Router
# ============================================================================

connections_router = APIRouter(prefix="/connections", tags=["connections"])


# ============================================================================
# Authorization Type Aliases
# ============================================================================

# Type alias for authenticated user dependency
CurrentUser = Annotated[dict[str, Any], Depends(get_current_user)]

# Type alias for authorized connection access
ConnectionViewer = Annotated[dict[str, Any], Depends(require_connection_viewer)]
ConnectionOwner = Annotated[dict[str, Any], Depends(require_connection_owner)]


def _get_user_id(user: dict[str, Any]) -> str:
    """Extract user ID from authenticated user dict."""
    return user.get("sub") or user.get("user_id") or user.get("preferred_username") or "anonymous"


# ============================================================================
# Endpoints
# ============================================================================


@connections_router.get("")
async def list_connections(
    current_user: CurrentUser,
    status: Literal["disconnected", "connecting", "connected", "error", "auth_required"] | None = Query(
        None, description="Filter by status"
    ),
    auth_type: Literal["none", "api_key", "oauth2"] | None = Query(None, description="Filter by auth type"),
    project_id: str | None = Query(None, description="Filter by project"),
    search: str | None = Query(
        None,
        min_length=1,
        max_length=500,
        description="Search in name and description (uses PostgreSQL Full-Text Search)",
    ),
    cursor: str | None = Query(None, description="Pagination cursor"),
    limit: int = Query(20, ge=1, le=100, description="Page size"),
    sort_by: Literal["name", "created_at", "updated_at", "status"] = Query(
        default="created_at", description="Field to sort by"
    ),
    sort_order: Literal["asc", "desc"] = Query(default="desc", description="Sort order"),
    repo: ConnectionRepository = Depends(get_connection_repository),
) -> ConnectionListResponse:
    """
    List MCP connections for the current user.

    Requires authentication. Returns connections owned by the user.

    Supports:
    - Pagination: cursor, limit (cursor-based for efficient large result sets)
    - Filtering: status, auth_type, project_id
    - Search: search (uses PostgreSQL Full-Text Search on name and description)
    - Sorting: sort_by, sort_order
    """
    user_id = _get_user_id(current_user)
    connections, next_cursor = await repo.list(
        owner_id=user_id,
        cursor=cursor,
        limit=limit,
        status=status,
        auth_type=auth_type,
        project_id=project_id,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    return ConnectionListResponse(
        items=connections,
        total=len(connections),
        cursor=next_cursor,
    )


@connections_router.post("", status_code=status.HTTP_201_CREATED)
async def create_connection(
    request: Request,
    data: MCPConnectionCreate,
    current_user: CurrentUser,
    repo: ConnectionRepository = Depends(get_connection_repository),
    audit_repo: AuditLogRepository = Depends(get_audit_log_repository),
) -> ConnectionResponse:
    """
    Create a new MCP connection.

    Requires authentication. The connection is created with the current user as owner.

    Supports three authentication types:
    - none: No authentication
    - api_key: API key stored in secrets provider
    - oauth2: OAuth2 with PKCE flow
    """
    user_id = _get_user_id(current_user)
    connection = await repo.create(data, owner_id=user_id)

    # Log audit event
    await audit_repo.log_event(
        event_type="connection.created",
        resource_type="connection",
        resource_id=connection.id,
        actor_id=user_id,
        action="create",
        details={"name": connection.name, "auth_type": connection.auth_type, "url": connection.url},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return to_connection_response(connection)


@connections_router.get("/{connection_id}")
async def get_connection(
    connection_id: str,
    user: ConnectionViewer,
    repo: ConnectionRepository = Depends(get_connection_repository),
) -> ConnectionResponse:
    """
    Get a specific MCP connection by ID.

    Requires 'viewer' access to the connection (owner or shared viewer).

    Returns full connection details (without sensitive credentials).
    """
    connection = await repo.get(connection_id)
    if connection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connection {connection_id} not found",
        )
    return to_connection_response(connection)


@connections_router.put("/{connection_id}")
async def update_connection(
    request: Request,
    connection_id: str,
    data: MCPConnectionUpdate,
    user: ConnectionOwner,
    repo: ConnectionRepository = Depends(get_connection_repository),
    audit_repo: AuditLogRepository = Depends(get_audit_log_repository),
) -> ConnectionResponse:
    """
    Update an MCP connection.

    Requires 'owner' access to the connection.

    Note: Authentication changes require separate endpoints for security.
    """
    user_id = _get_user_id(user)
    connection = await repo.update(connection_id, data)
    if connection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connection {connection_id} not found",
        )

    # Log audit event
    await audit_repo.log_event(
        event_type="connection.updated",
        resource_type="connection",
        resource_id=connection.id,
        actor_id=user_id,
        action="update",
        details={"name": connection.name, "changes": data.model_dump(exclude_unset=True)},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return to_connection_response(connection)


@connections_router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connection(
    request: Request,
    connection_id: str,
    user: ConnectionOwner,
    repo: ConnectionRepository = Depends(get_connection_repository),
    audit_repo: AuditLogRepository = Depends(get_audit_log_repository),
) -> None:
    """
    Delete an MCP connection.

    Requires 'owner' access to the connection.

    Also removes associated secrets (API keys, OAuth2 tokens).
    """
    user_id = _get_user_id(user)
    # Get connection info before deletion for audit log
    connection = await repo.get(connection_id)
    if connection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connection {connection_id} not found",
        )

    deleted = await repo.delete(connection_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connection {connection_id} not found",
        )

    # Log audit event
    await audit_repo.log_event(
        event_type="connection.deleted",
        resource_type="connection",
        resource_id=connection_id,
        actor_id=user_id,
        action="delete",
        details={"name": connection.name, "url": connection.url},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@connections_router.post("/{connection_id}/test")
async def test_connection(
    request: Request,
    connection_id: str,
    user: ConnectionOwner,
    repo: ConnectionRepository = Depends(get_connection_repository),  # noqa: PT028
    mcp_client: MCPClient = Depends(get_mcp_client),  # noqa: PT028
    audit_repo: AuditLogRepository = Depends(get_audit_log_repository),  # noqa: PT028
) -> MCPConnectionTestResult:
    """
    Test an MCP connection.

    Requires 'owner' access to the connection.

    Attempts to connect to the MCP server and retrieve server info.
    Updates connection status based on result.
    """
    user_id = _get_user_id(user)
    connection = await repo.get(connection_id)
    if connection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connection {connection_id} not found",
        )

    # Get authentication header if needed
    auth_header = None
    if connection.auth_type == "api_key":
        api_key = await repo.get_api_key(connection_id)
        if api_key:
            auth_header = f"Bearer {api_key}"
    elif connection.auth_type == "oauth2":
        access_token = await repo.get_oauth2_access_token(connection_id)
        if access_token:
            auth_header = f"Bearer {access_token}"

    # Test the connection
    test_result: MCPConnectionTestResult = await mcp_client.test_connection(connection.url, auth_header)

    # Update connection status
    if test_result.success:
        await repo.update_status(
            connection_id=connection_id,
            status="connected",
            server_name=test_result.server_name,
            server_version=test_result.server_version,
            tool_count=test_result.tool_count,
            resource_count=test_result.resource_count,
            prompt_count=test_result.prompt_count,
        )
    else:
        await repo.update_status(
            connection_id=connection_id,
            status="error",
            last_error=test_result.error,
        )

    # Log audit event
    await audit_repo.log_event(
        event_type="connection.tested",
        resource_type="connection",
        resource_id=connection_id,
        actor_id=user_id,
        action="test",
        details={
            "name": connection.name,
            "success": test_result.success,
            "latency_ms": test_result.latency_ms,
            "error": test_result.error,
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return test_result


@connections_router.post("/{connection_id}/oauth/start")
@rate_limit_for_oauth2_start
async def start_oauth2_flow(
    request: Request,
    connection_id: str,
    user: ConnectionOwner,
    popup: bool = Query(
        False,
        description="If true, use popup-friendly flow with postMessage callback instead of redirect",
    ),
    repo: ConnectionRepository = Depends(get_connection_repository),
    oauth2_service: OAuth2Service = Depends(get_oauth2_service),
) -> OAuth2StartResponse:
    """
    Start OAuth2 authorization flow for a connection.

    Requires 'owner' access to the connection.

    Uses PKCE (Proof Key for Code Exchange) for security.
    Returns the authorization URL and state parameter.

    Args:
        popup: If True, the callback will return HTML that posts a message to the
               opener window and closes itself, instead of redirecting. Use this
               for in-chat OAuth flows where you want to maintain the user's
               context in the main window.
    """
    connection = await repo.get(connection_id)
    if connection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connection {connection_id} not found",
        )

    if connection.auth_type != "oauth2":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Connection is not configured for OAuth2 authentication",
        )

    if not connection.oauth2_config or not connection.oauth2_config.client_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth2 client ID is not configured",
        )

    # Discover OAuth2 metadata from MCP server
    metadata = await oauth2_service.discover_metadata(connection.url)

    # Generate PKCE values
    code_verifier = oauth2_service.generate_code_verifier()
    code_challenge = oauth2_service.generate_code_challenge(code_verifier)

    # Generate state for CSRF protection
    state = token_urlsafe(32)

    # Build redirect URI from settings (configurable via OAUTH2_REDIRECT_URI env var)
    redirect_uri = settings.oauth2_redirect_uri

    # Store state for callback validation
    await repo.create_oauth2_state(
        connection_id=connection_id,
        state=state,
        code_verifier=code_verifier,
        redirect_uri=redirect_uri,
        popup=popup,
    )

    # Build authorization URL
    scope = " ".join(connection.oauth2_config.scopes)
    authorization_url = oauth2_service.build_authorization_url(
        authorization_endpoint=metadata["authorization_endpoint"],
        client_id=connection.oauth2_config.client_id,
        redirect_uri=redirect_uri,
        scope=scope,
        state=state,
        code_challenge=code_challenge,
    )

    return OAuth2StartResponse(
        authorization_url=authorization_url,
        state=state,
    )


@connections_router.post("/oauth/callback")
@rate_limit_for_oauth2_callback
async def oauth2_callback_stateless(
    request: Request,
    body: OAuth2CallbackRequest,
    repo: ConnectionRepository = Depends(get_connection_repository),
    oauth2_service: OAuth2Service = Depends(get_oauth2_service),
) -> OAuth2CallbackResponse:
    """
    Handle OAuth2 callback (stateless - looks up connection from state).

    This endpoint is called by the frontend OAuth2CallbackPage after the user
    completes authorization at the OAuth2 provider. The connection_id is
    retrieved from the stored state, allowing for a simpler frontend flow.

    Args:
        request: FastAPI Request object for rate limiting
        body: OAuth2CallbackRequest with code and state from OAuth provider

    Returns:
        OAuth2CallbackResponse with connection_id on success

    Raises:
        HTTPException 400: Invalid or expired state
        HTTPException 404: Connection not found
    """
    # Validate state and get connection_id + PKCE values
    state_data = await repo.get_and_delete_oauth2_state(body.state)
    if state_data is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth2 state",
        )

    connection_id = state_data["connection_id"]
    connection = await repo.get(connection_id)
    if connection is None or not connection.oauth2_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connection {connection_id} not found",
        )

    # Discover token endpoint
    metadata = await oauth2_service.discover_metadata(connection.url)

    # Exchange code for tokens
    client_id = (connection.oauth2_config.client_id or "") if connection.oauth2_config else ""
    tokens = await oauth2_service.exchange_code(
        token_endpoint=metadata["token_endpoint"],
        client_id=client_id,
        client_secret=None,  # PKCE flow doesn't require client secret
        code=body.code,
        redirect_uri=state_data["redirect_uri"],
        code_verifier=state_data["code_verifier"],
    )

    # Calculate expiry
    expires_at = None
    if "expires_in" in tokens:
        from datetime import UTC, datetime, timedelta

        expires_at = datetime.now(UTC) + timedelta(seconds=tokens["expires_in"])

    # Store tokens securely
    await repo.store_oauth2_tokens(
        connection_id=connection_id,
        access_token=tokens["access_token"],
        refresh_token=tokens.get("refresh_token"),
        expires_at=expires_at,
    )

    return OAuth2CallbackResponse(
        connection_id=connection_id,
        popup=state_data.get("popup", False),
    )


@connections_router.post("/{connection_id}/oauth/callback")
@rate_limit_for_oauth2_callback
async def oauth2_callback(
    request: Request,
    connection_id: str,
    code: str = Query(..., description="Authorization code"),
    state: str = Query(..., description="State parameter"),
    repo: ConnectionRepository = Depends(get_connection_repository),
    oauth2_service: OAuth2Service = Depends(get_oauth2_service),
) -> dict[str, str]:
    """
    Handle OAuth2 callback.

    Exchanges the authorization code for tokens and stores them securely.
    """
    # Validate state and get PKCE values
    state_data = await repo.get_and_delete_oauth2_state(state)
    if state_data is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth2 state",
        )

    if state_data["connection_id"] != connection_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Connection ID mismatch",
        )

    connection = await repo.get(connection_id)
    if connection is None or not connection.oauth2_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connection {connection_id} not found",
        )

    # Discover token endpoint
    metadata = await oauth2_service.discover_metadata(connection.url)

    # Exchange code for tokens
    # oauth2_config is guaranteed to exist here since we validated auth_type == "oauth2"
    # Use empty string fallback to satisfy type checker (validation already done above)
    client_id = (connection.oauth2_config.client_id or "") if connection.oauth2_config else ""
    tokens = await oauth2_service.exchange_code(
        token_endpoint=metadata["token_endpoint"],
        client_id=client_id,
        client_secret=None,  # PKCE flow doesn't require client secret
        code=code,
        redirect_uri=state_data["redirect_uri"],
        code_verifier=state_data["code_verifier"],
    )

    # Calculate expiry
    expires_at = None
    if "expires_in" in tokens:
        from datetime import UTC, datetime, timedelta

        expires_at = datetime.now(UTC) + timedelta(seconds=tokens["expires_in"])

    # Store tokens securely
    await repo.store_oauth2_tokens(
        connection_id=connection_id,
        access_token=tokens["access_token"],
        refresh_token=tokens.get("refresh_token"),
        expires_at=expires_at,
    )

    return {"status": "success", "message": "OAuth2 authorization completed"}
