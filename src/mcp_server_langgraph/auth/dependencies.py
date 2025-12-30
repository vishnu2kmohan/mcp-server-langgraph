"""
FastAPI Dependency Injection for Authentication and Authorization

Provides FastAPI dependencies for:
- get_current_user: Extract authenticated user from request
- get_current_user_with_auth: Authentication + authorization
- require_auth_dependency: Decorator-style dependency factory

Phase 2.2 SRP decomposition: Extracted from middleware.py
"""

from typing import TYPE_CHECKING, Any

from mcp_server_langgraph.auth.jwt_utils import extract_user_from_jwt_payload
from mcp_server_langgraph.observability.telemetry import logger

# FastAPI imports (optional)
try:
    from fastapi import HTTPException, Request, status
    from fastapi.security import HTTPBearer

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

if TYPE_CHECKING:
    from fastapi import Request

    from mcp_server_langgraph.auth.middleware import AuthMiddleware


# ============================================================================
# Global Auth Middleware Instance Management
# ============================================================================

# Global auth middleware instance (set by application)
_global_auth_middleware: "AuthMiddleware | None" = None


def set_global_auth_middleware(auth: "AuthMiddleware | None") -> None:
    """
    Set global auth middleware instance for FastAPI dependencies.

    This should be called during application startup, or with None during test teardown.

    Args:
        auth: AuthMiddleware instance configured with user provider, OpenFGA, etc.
              Pass None to clear the global middleware (e.g., in test teardown).
    """
    global _global_auth_middleware
    _global_auth_middleware = auth
    if auth is not None:
        logger.info(
            "Global auth middleware set",
            extra={"provider_type": type(auth.user_provider).__name__},
        )
    else:
        logger.debug("Global auth middleware cleared")


def get_auth_middleware() -> "AuthMiddleware":
    """
    Get global auth middleware instance.

    .. deprecated:: 2.9.0
        Use :func:`get_auth_middleware_from_request` instead for proper DI pattern.
        This function will be removed in version 3.0.0.

    Returns:
        AuthMiddleware instance

    Raises:
        RuntimeError: If auth middleware not initialized
    """
    import warnings

    warnings.warn(
        "get_auth_middleware() is deprecated. Use get_auth_middleware_from_request(request) "
        "for proper dependency injection. This will be removed in version 3.0.0.",
        DeprecationWarning,
        stacklevel=2,
    )
    if _global_auth_middleware is None:
        msg = "Auth middleware not initialized. Call set_global_auth_middleware() during app startup."
        raise RuntimeError(msg)
    return _global_auth_middleware


def clear_global_auth_middleware() -> None:
    """
    Clear global auth middleware instance.

    Useful for testing to reset state between tests.
    """
    global _global_auth_middleware
    _global_auth_middleware = None


# ============================================================================
# DI-Based Auth Middleware Access (Recommended Pattern)
# ============================================================================


def get_auth_middleware_from_request(request: "Request") -> "AuthMiddleware | None":
    """
    Get AuthMiddleware from FastAPI request state (DI pattern).

    This is the PREFERRED way to access auth middleware in FastAPI routes.
    The middleware is initialized once during app lifespan startup and stored
    in app.state.auth_middleware.

    Benefits over global state pattern:
    - Proper dependency injection (testable without global state)
    - Request-scoped access (proper FastAPI idiom)
    - No global mutable state (thread-safe)
    - Explicit dependency chain (easier to trace)

    Args:
        request: FastAPI Request object (injected via Depends)

    Returns:
        AuthMiddleware if configured and initialized, None otherwise

    Example:
        @router.get("/protected")
        async def protected_route(
            auth: AuthMiddleware = Depends(get_auth_middleware_from_request),
        ):
            if auth:
                user = await auth.verify_token(token)
    """
    return getattr(request.app.state, "auth_middleware", None)


def require_auth_middleware_from_request(request: "Request") -> "AuthMiddleware":
    """
    Get AuthMiddleware from request state, raising if not initialized.

    Use this when auth middleware is REQUIRED for the endpoint to function.
    This is stricter than get_auth_middleware_from_request which returns None.

    Args:
        request: FastAPI Request object (injected via Depends)

    Returns:
        AuthMiddleware instance

    Raises:
        RuntimeError: If auth middleware not initialized in app.state

    Example:
        @router.get("/admin")
        async def admin_route(
            auth: AuthMiddleware = Depends(require_auth_middleware_from_request),
        ):
            # auth is guaranteed to be available
            user = await auth.verify_token(token)
    """
    auth = get_auth_middleware_from_request(request)
    if auth is None:
        msg = "Auth middleware not initialized. Ensure app lifespan sets app.state.auth_middleware."
        raise RuntimeError(msg)
    return auth


# ============================================================================
# WebSocket Auth Middleware Access
# ============================================================================


if FASTAPI_AVAILABLE:
    from fastapi import WebSocket as FastAPIWebSocket

    def get_auth_middleware_from_websocket(websocket: "FastAPIWebSocket") -> "AuthMiddleware | None":
        """
        Get AuthMiddleware from WebSocket app state (DI pattern).

        This is the WebSocket equivalent of get_auth_middleware_from_request.
        WebSocket connections share the same app.state as regular HTTP requests.

        Args:
            websocket: FastAPI WebSocket object

        Returns:
            AuthMiddleware if configured and initialized, None otherwise

        Example:
            @router.websocket("/ws")
            async def websocket_endpoint(websocket: WebSocket):
                auth = get_auth_middleware_from_websocket(websocket)
                if auth:
                    user = await auth.verify_token(token)
        """
        return getattr(websocket.app.state, "auth_middleware", None)


# ============================================================================
# FastAPI Dependencies (only available if FastAPI is installed)
# ============================================================================

if FASTAPI_AVAILABLE:
    # HTTP Bearer security scheme for JWT tokens
    bearer_scheme = HTTPBearer(auto_error=False)

    async def get_current_user(
        request: Request,
    ) -> dict[str, Any]:
        """
        FastAPI dependency for extracting authenticated user from request.

        Supports multiple authentication methods:
        1. JWT token in Authorization header (Bearer token)
        2. User already set in request.state.user (by middleware)

        Args:
            request: FastAPI request object

        Returns:
            User dict with user_id, username, roles, etc.

        Raises:
            HTTPException: If authentication fails (401)
        """
        # Check if user already set by middleware
        if hasattr(request.state, "user") and request.state.user:
            return request.state.user  # type: ignore[no-any-return]

        # Extract bearer token from Authorization header
        auth_header = request.headers.get("Authorization")
        token = None
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix

        # Try to authenticate with Bearer token
        if token:
            # DI pattern: Try app.state first, fall back to global for backward compatibility
            auth = get_auth_middleware_from_request(request)
            if auth is None:
                auth = get_auth_middleware()
            verification = await auth.verify_token(token)

            if verification.valid and verification.payload:
                # Extract user information from token payload
                # Uses shared function for consistent extraction across all services
                user_data = extract_user_from_jwt_payload(verification.payload)
                # Cache in request state for subsequent calls
                request.state.user = user_data
                return user_data
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Invalid token: {verification.error}",
                    headers={"WWW-Authenticate": "Bearer"},
                )

        # No authentication provided
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    async def get_current_user_with_auth(
        user: dict[str, Any],
        relation: str | None = None,
        resource: str | None = None,
    ) -> dict[str, Any]:
        """
        FastAPI dependency for authenticated + authorized user.

        Use this when you need both authentication and authorization.

        Example:
            @app.get("/protected")
            async def protected_endpoint(
                user: Dict[str, Any] = Depends(
                    lambda: get_current_user_with_auth(relation="viewer", resource="tool:chat")
                )
            ):
                return {"user": user}

        Args:
            user: User dict from get_current_user dependency
            relation: Required relation (e.g., "executor", "viewer")
            resource: Resource to check access to (e.g., "tool:chat")

        Returns:
            User dict if authorized

        Raises:
            HTTPException: If authorization fails (403)
        """
        if relation and resource:
            auth = get_auth_middleware()
            user_id = user.get("user_id", "")

            authorized = await auth.authorize(user_id=user_id, relation=relation, resource=resource)

            if not authorized:
                # Audit log the denial
                from mcp_server_langgraph.auth.metrics import log_authorization_denied

                log_authorization_denied(
                    user_id=user_id,
                    relation=relation,
                    resource=resource,
                    reason="permission_denied",
                )

                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Not authorized: {user_id} cannot {relation} {resource}",
                )

        return user

    def require_auth_dependency(relation: str | None = None, resource: str | None = None) -> None:
        """
        Create a FastAPI dependency for authentication + authorization.

        This replaces the @require_auth decorator for FastAPI routes.

        Example:
            from fastapi import Depends

            @app.get("/tools")
            async def list_tools(user: Dict = Depends(require_auth_dependency(relation="executor", resource="tool:*"))):
                return {"tools": [...]}

        Args:
            relation: Required relation (e.g., "executor")
            resource: Resource to check access to

        Returns:
            FastAPI dependency function
        """

        async def dependency(
            request: Request,
        ) -> dict[str, Any]:
            # Get authenticated user
            user = await get_current_user(request)

            # Check authorization if required
            if relation and resource:
                auth = get_auth_middleware()
                user_id = user["user_id"]
                authorized = await auth.authorize(user_id=user_id, relation=relation, resource=resource)

                if not authorized:
                    # Audit log the denial
                    from mcp_server_langgraph.auth.metrics import log_authorization_denied

                    log_authorization_denied(
                        user_id=user_id,
                        relation=relation,
                        resource=resource,
                        reason="permission_denied",
                    )

                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Not authorized: {user_id} cannot {relation} {resource}",
                    )

            return user

        return dependency  # type: ignore[return-value]


# ============================================================================
# Resource-Specific Authorization Dependencies
# ============================================================================

if FASTAPI_AVAILABLE:
    from fastapi import Path

    def _create_resource_auth_dependency(
        resource_type: str,
        relation: str,
        resource_id_param: str = "project_id",
    ) -> Any:
        """
        Factory for creating resource-specific authorization dependencies.

        Creates a FastAPI dependency that:
        1. Authenticates the user via JWT token
        2. Extracts the resource ID from the path parameter
        3. Checks OpenFGA authorization for user:relation:resource_type:resource_id

        Args:
            resource_type: OpenFGA resource type (e.g., "project", "connection")
            relation: Required relation (e.g., "viewer", "editor", "owner")
            resource_id_param: Name of the path parameter containing resource ID

        Returns:
            FastAPI dependency function that returns user dict if authorized

        Raises:
            HTTPException 401: If authentication fails
            HTTPException 403: If authorization fails
        """

        async def dependency(
            request: Request,
            resource_id: str = Path(..., alias=resource_id_param),
        ) -> dict[str, Any]:
            # Get authenticated user (handles JWT extraction from Authorization header)
            user = await get_current_user(request)

            # Build OpenFGA resource string
            resource = f"{resource_type}:{resource_id}"

            # Check authorization via OpenFGA
            auth = get_auth_middleware_from_request(request)
            if auth is None:
                # Fall back to global for backward compatibility
                auth = _global_auth_middleware
            if auth is None:
                # No auth middleware available, allow (for development)
                logger.warning(
                    "No auth middleware available, skipping authorization check",
                    extra={"resource": resource, "relation": relation},
                )
                return user

            user_id = user.get("sub") or user.get("user_id") or ""
            # Format user ID for OpenFGA if not already prefixed
            if not user_id.startswith("user:"):
                user_id = f"user:{user_id}"

            authorized = await auth.authorize(
                user_id=user_id,
                relation=relation,
                resource=resource,
            )

            if not authorized:
                # Audit log the denial
                from mcp_server_langgraph.auth.metrics import log_authorization_denied

                log_authorization_denied(
                    user_id=user_id,
                    relation=relation,
                    resource=resource,
                    reason="permission_denied",
                )

                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Not authorized: {user_id} cannot {relation} {resource}",
                )

            return user

        return dependency

    # ============================================================================
    # Admin Role Dependency
    # ============================================================================

    async def require_admin(
        request: Request,
    ) -> dict[str, Any]:
        """
        Require admin role for endpoint access.

        Use for: Admin-only operations like user management, system configuration.

        Checks if the authenticated user has 'admin' role in their JWT token.
        This is a role-based check, not a resource-based OpenFGA check.

        Args:
            request: FastAPI Request object

        Returns:
            User dict if user has admin role

        Raises:
            HTTPException 401: If authentication fails
            HTTPException 403: If user does not have admin role
        """
        user = await get_current_user(request)

        # Check for admin role in user's roles
        roles = user.get("roles", [])
        # Also check realm_access for Keycloak tokens
        realm_access = user.get("realm_access", {})
        realm_roles = realm_access.get("roles", [])

        all_roles = set(roles) | set(realm_roles)

        if "admin" not in all_roles:
            user_id = user.get("sub") or user.get("user_id") or "unknown"
            logger.warning(
                "Admin access denied",
                extra={"user_id": user_id, "roles": list(all_roles)},
            )

            # Audit log the denial
            from mcp_server_langgraph.auth.metrics import log_authorization_denied

            log_authorization_denied(
                user_id=user_id,
                relation="admin",
                resource="system:global",
                reason="missing_admin_role",
            )

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin role required",
            )

        return user

    # ============================================================================
    # Project Authorization Dependencies
    # ============================================================================

    async def require_project_viewer(
        request: Request,
        project_id: str = Path(...),
    ) -> Any:
        """
        Require viewer access to a project.

        Use for: GET /projects/{project_id}, GET /projects/{project_id}/*

        The user must have 'viewer' relation to 'project:{project_id}' in OpenFGA.
        Owners and editors inherit viewer access via OpenFGA model relations.
        """
        return await _create_resource_auth_dependency("project", "viewer", "project_id")(request, project_id)

    async def require_project_editor(
        request: Request,
        project_id: str = Path(...),
    ) -> Any:
        """
        Require editor access to a project.

        Use for: PUT /projects/{project_id}, POST /projects/{project_id}/*

        The user must have 'editor' relation to 'project:{project_id}' in OpenFGA.
        Owners inherit editor access via OpenFGA model relations.
        """
        return await _create_resource_auth_dependency("project", "editor", "project_id")(request, project_id)

    async def require_project_owner(
        request: Request,
        project_id: str = Path(...),
    ) -> Any:
        """
        Require owner access to a project.

        Use for: DELETE /projects/{project_id}

        The user must have 'owner' relation to 'project:{project_id}' in OpenFGA.
        """
        return await _create_resource_auth_dependency("project", "owner", "project_id")(request, project_id)

    # ============================================================================
    # Connection Authorization Dependencies
    # ============================================================================

    async def require_connection_viewer(
        request: Request,
        connection_id: str = Path(...),
    ) -> Any:
        """
        Require viewer access to a connection.

        Use for: GET /connections/{connection_id}
        """
        return await _create_resource_auth_dependency("connection", "viewer", "connection_id")(request, connection_id)

    async def require_connection_owner(
        request: Request,
        connection_id: str = Path(...),
    ) -> Any:
        """
        Require owner access to a connection.

        Use for: PUT/DELETE /connections/{connection_id}
        """
        return await _create_resource_auth_dependency("connection", "owner", "connection_id")(request, connection_id)

    # ============================================================================
    # Chat Authorization Dependencies
    # ============================================================================

    async def require_chat_viewer(
        request: Request,
        chat_id: str = Path(...),
    ) -> Any:
        """
        Require viewer access to a chat.

        Use for: GET /chat/{chat_id}
        """
        return await _create_resource_auth_dependency("chat", "viewer", "chat_id")(request, chat_id)

    async def require_chat_owner(
        request: Request,
        chat_id: str = Path(...),
    ) -> Any:
        """
        Require owner access to a chat.

        Use for: PUT/DELETE /chat/{chat_id}
        """
        return await _create_resource_auth_dependency("chat", "owner", "chat_id")(request, chat_id)

    # ============================================================================
    # Observability Authorization Dependencies
    # ============================================================================

    async def require_observability_viewer(
        request: Request,
    ) -> Any:
        """
        Require viewer access to observability resources.

        Use for: GET /observability/*
        Checks against 'observability:default' resource.
        """
        user = await get_current_user(request)
        resource = "observability:default"

        auth = get_auth_middleware_from_request(request)
        if auth is None:
            auth = _global_auth_middleware
        if auth is None:
            logger.warning("No auth middleware, skipping observability auth check")
            return user

        user_id = user.get("sub") or user.get("user_id") or ""
        if not user_id.startswith("user:"):
            user_id = f"user:{user_id}"

        authorized = await auth.authorize(user_id=user_id, relation="viewer", resource=resource)
        if not authorized:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not authorized: {user_id} cannot view {resource}",
            )
        return user

    async def require_observability_admin(
        request: Request,
    ) -> Any:
        """
        Require admin access to observability resources.

        Use for: PUT /observability/config, POST /observability/*
        Checks against 'observability:default' resource.
        """
        user = await get_current_user(request)
        resource = "observability:default"

        auth = get_auth_middleware_from_request(request)
        if auth is None:
            auth = _global_auth_middleware
        if auth is None:
            logger.warning("No auth middleware, skipping observability auth check")
            return user

        user_id = user.get("sub") or user.get("user_id") or ""
        if not user_id.startswith("user:"):
            user_id = f"user:{user_id}"

        authorized = await auth.authorize(user_id=user_id, relation="admin", resource=resource)
        if not authorized:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not authorized: {user_id} cannot admin {resource}",
            )
        return user

    # ============================================================================
    # Workflow Authorization Dependencies
    # ============================================================================

    async def require_workflow_viewer(
        request: Request,
        workflow_id: str = Path(...),
    ) -> Any:
        """
        Require viewer access to a workflow.

        Use for: GET /workflows/{workflow_id}
        """
        return await _create_resource_auth_dependency("workflow", "viewer", "workflow_id")(request, workflow_id)

    async def require_workflow_editor(
        request: Request,
        workflow_id: str = Path(...),
    ) -> Any:
        """
        Require editor access to a workflow.

        Use for: PUT /workflows/{workflow_id}
        """
        return await _create_resource_auth_dependency("workflow", "editor", "workflow_id")(request, workflow_id)

    async def require_workflow_owner(
        request: Request,
        workflow_id: str = Path(...),
    ) -> Any:
        """
        Require owner access to a workflow.

        Use for: DELETE /workflows/{workflow_id}
        """
        return await _create_resource_auth_dependency("workflow", "owner", "workflow_id")(request, workflow_id)

    async def require_workflow_executor(
        request: Request,
        workflow_id: str = Path(...),
    ) -> Any:
        """
        Require executor access to a workflow.

        Use for: POST /workflows/{workflow_id}/execute
        """
        return await _create_resource_auth_dependency("workflow", "executor", "workflow_id")(request, workflow_id)

    # ============================================================================
    # Agent Authorization Dependencies
    # ============================================================================

    async def require_agent_viewer(
        request: Request,
        agent_id: str = Path(...),
    ) -> Any:
        """
        Require viewer access to an agent.

        Use for: GET /agents/{agent_id}
        """
        return await _create_resource_auth_dependency("agent", "viewer", "agent_id")(request, agent_id)

    async def require_agent_admin(
        request: Request,
        agent_id: str = Path(...),
    ) -> Any:
        """
        Require admin access to an agent.

        Use for: PUT /agents/{agent_id}/config
        """
        return await _create_resource_auth_dependency("agent", "admin", "agent_id")(request, agent_id)

    async def require_agent_owner(
        request: Request,
        agent_id: str = Path(...),
    ) -> Any:
        """
        Require owner access to an agent.

        Use for: DELETE /agents/{agent_id}
        """
        return await _create_resource_auth_dependency("agent", "owner", "agent_id")(request, agent_id)

    # ============================================================================
    # Skill Authorization Dependencies
    # ============================================================================

    async def require_skill_viewer(
        request: Request,
        skill_id: str = Path(...),
    ) -> Any:
        """
        Require viewer access to a skill.

        Use for: GET /skills/{skill_id}
        """
        return await _create_resource_auth_dependency("skill", "viewer", "skill_id")(request, skill_id)

    async def require_skill_admin(
        request: Request,
        skill_id: str = Path(...),
    ) -> Any:
        """
        Require admin access to a skill.

        Use for: PUT/DELETE /skills/{skill_id}
        """
        return await _create_resource_auth_dependency("skill", "admin", "skill_id")(request, skill_id)

    # ============================================================================
    # Execution Authorization Dependencies
    # ============================================================================

    async def require_execution_viewer(
        request: Request,
        execution_id: str = Path(...),
    ) -> Any:
        """
        Require viewer access to an execution.

        Use for: GET /executions/{execution_id}
        """
        return await _create_resource_auth_dependency("execution", "viewer", "execution_id")(request, execution_id)

    async def require_execution_owner(
        request: Request,
        execution_id: str = Path(...),
    ) -> Any:
        """
        Require owner access to an execution.

        Use for: DELETE /executions/{execution_id}
        """
        return await _create_resource_auth_dependency("execution", "owner", "execution_id")(request, execution_id)

    # ============================================================================
    # Session Authorization Dependencies
    # ============================================================================

    async def require_session_viewer(
        request: Request,
        session_id: str = Path(...),
    ) -> Any:
        """
        Require viewer access to a session.

        Use for: GET /sessions/{session_id}
        """
        return await _create_resource_auth_dependency("session", "viewer", "session_id")(request, session_id)

    async def require_session_editor(
        request: Request,
        session_id: str = Path(...),
    ) -> Any:
        """
        Require editor access to a session.

        Use for: PUT /sessions/{session_id}
        """
        return await _create_resource_auth_dependency("session", "editor", "session_id")(request, session_id)

    async def require_session_owner(
        request: Request,
        session_id: str = Path(...),
    ) -> Any:
        """
        Require owner access to a session.

        Use for: DELETE /sessions/{session_id}
        """
        return await _create_resource_auth_dependency("session", "owner", "session_id")(request, session_id)

    # ============================================================================
    # Compliance Authorization Dependencies
    # ============================================================================

    async def require_compliance_viewer(
        request: Request,
    ) -> Any:
        """
        Require viewer access to compliance reports.

        Use for: GET /compliance/reports/*
        Checks against 'compliance:default' resource.
        """
        user = await get_current_user(request)
        resource = "compliance:default"

        auth = get_auth_middleware_from_request(request)
        if auth is None:
            auth = _global_auth_middleware
        if auth is None:
            logger.warning("No auth middleware, skipping compliance auth check")
            return user

        user_id = user.get("sub") or user.get("user_id") or ""
        if not user_id.startswith("user:"):
            user_id = f"user:{user_id}"

        authorized = await auth.authorize(user_id=user_id, relation="viewer", resource=resource)
        if not authorized:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not authorized: {user_id} cannot view {resource}",
            )
        return user

    async def require_compliance_admin(
        request: Request,
    ) -> Any:
        """
        Require admin access to compliance reports.

        Use for: POST /compliance/reports/*
        Checks against 'compliance:default' resource.
        """
        user = await get_current_user(request)
        resource = "compliance:default"

        auth = get_auth_middleware_from_request(request)
        if auth is None:
            auth = _global_auth_middleware
        if auth is None:
            logger.warning("No auth middleware, skipping compliance auth check")
            return user

        user_id = user.get("sub") or user.get("user_id") or ""
        if not user_id.startswith("user:"):
            user_id = f"user:{user_id}"

        authorized = await auth.authorize(user_id=user_id, relation="admin", resource=resource)
        if not authorized:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not authorized: {user_id} cannot admin {resource}",
            )
        return user

    # ============================================================================
    # Marketplace Authorization Dependencies
    # ============================================================================

    async def require_marketplace_admin(
        request: Request,
    ) -> Any:
        """
        Require admin access to marketplace.

        Use for: POST/PUT/DELETE /marketplace/*
        Checks against 'marketplace:default' resource.
        """
        user = await get_current_user(request)
        resource = "marketplace:default"

        auth = get_auth_middleware_from_request(request)
        if auth is None:
            auth = _global_auth_middleware
        if auth is None:
            logger.warning("No auth middleware, skipping marketplace auth check")
            return user

        user_id = user.get("sub") or user.get("user_id") or ""
        if not user_id.startswith("user:"):
            user_id = f"user:{user_id}"

        authorized = await auth.authorize(user_id=user_id, relation="admin", resource=resource)
        if not authorized:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not authorized: {user_id} cannot admin {resource}",
            )
        return user

    # ============================================================================
    # Config Authorization Dependencies
    # ============================================================================

    async def require_config_viewer(
        request: Request,
    ) -> Any:
        """
        Require viewer access to system config.

        Use for: GET /config/*
        Checks against 'config:default' resource.
        """
        user = await get_current_user(request)
        resource = "config:default"

        auth = get_auth_middleware_from_request(request)
        if auth is None:
            auth = _global_auth_middleware
        if auth is None:
            logger.warning("No auth middleware, skipping config auth check")
            return user

        user_id = user.get("sub") or user.get("user_id") or ""
        if not user_id.startswith("user:"):
            user_id = f"user:{user_id}"

        authorized = await auth.authorize(user_id=user_id, relation="viewer", resource=resource)
        if not authorized:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not authorized: {user_id} cannot view {resource}",
            )
        return user

    async def require_config_admin(
        request: Request,
    ) -> Any:
        """
        Require admin access to system config.

        Use for: PUT/DELETE /config/*
        Checks against 'config:default' resource.
        """
        user = await get_current_user(request)
        resource = "config:default"

        auth = get_auth_middleware_from_request(request)
        if auth is None:
            auth = _global_auth_middleware
        if auth is None:
            logger.warning("No auth middleware, skipping config auth check")
            return user

        user_id = user.get("sub") or user.get("user_id") or ""
        if not user_id.startswith("user:"):
            user_id = f"user:{user_id}"

        authorized = await auth.authorize(user_id=user_id, relation="admin", resource=resource)
        if not authorized:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not authorized: {user_id} cannot admin {resource}",
            )
        return user

    # ============================================================================
    # Cost Authorization Dependencies
    # ============================================================================

    async def require_cost_viewer(
        request: Request,
    ) -> Any:
        """
        Require viewer access to cost data.

        Use for: GET /cost/*
        Checks against 'cost:default' resource.
        """
        user = await get_current_user(request)
        resource = "cost:default"

        auth = get_auth_middleware_from_request(request)
        if auth is None:
            auth = _global_auth_middleware
        if auth is None:
            logger.warning("No auth middleware, skipping cost auth check")
            return user

        user_id = user.get("sub") or user.get("user_id") or ""
        if not user_id.startswith("user:"):
            user_id = f"user:{user_id}"

        authorized = await auth.authorize(user_id=user_id, relation="viewer", resource=resource)
        if not authorized:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not authorized: {user_id} cannot view {resource}",
            )
        return user

    async def require_cost_admin(
        request: Request,
    ) -> Any:
        """
        Require admin access to cost data.

        Use for: PUT /cost/settings
        Checks against 'cost:default' resource.
        """
        user = await get_current_user(request)
        resource = "cost:default"

        auth = get_auth_middleware_from_request(request)
        if auth is None:
            auth = _global_auth_middleware
        if auth is None:
            logger.warning("No auth middleware, skipping cost auth check")
            return user

        user_id = user.get("sub") or user.get("user_id") or ""
        if not user_id.startswith("user:"):
            user_id = f"user:{user_id}"

        authorized = await auth.authorize(user_id=user_id, relation="admin", resource=resource)
        if not authorized:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not authorized: {user_id} cannot admin {resource}",
            )
        return user


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "FASTAPI_AVAILABLE",
    # Global pattern (legacy, for backward compatibility)
    "set_global_auth_middleware",
    "get_auth_middleware",
    "clear_global_auth_middleware",
    # DI pattern (recommended)
    "get_auth_middleware_from_request",
    "require_auth_middleware_from_request",
]

if FASTAPI_AVAILABLE:
    __all__.extend(
        [
            "bearer_scheme",
            "get_current_user",
            "get_current_user_with_auth",
            "require_auth_dependency",
            "require_admin",
            # WebSocket auth middleware access
            "get_auth_middleware_from_websocket",
            # Project authorization
            "require_project_viewer",
            "require_project_editor",
            "require_project_owner",
            # Connection authorization
            "require_connection_viewer",
            "require_connection_owner",
            # Chat authorization
            "require_chat_viewer",
            "require_chat_owner",
            # Observability authorization
            "require_observability_viewer",
            "require_observability_admin",
            # Workflow authorization
            "require_workflow_viewer",
            "require_workflow_editor",
            "require_workflow_owner",
            "require_workflow_executor",
            # Agent authorization
            "require_agent_viewer",
            "require_agent_admin",
            "require_agent_owner",
            # Skill authorization
            "require_skill_viewer",
            "require_skill_admin",
            # Execution authorization
            "require_execution_viewer",
            "require_execution_owner",
            # Session authorization
            "require_session_viewer",
            "require_session_editor",
            "require_session_owner",
            # Compliance authorization
            "require_compliance_viewer",
            "require_compliance_admin",
            # Marketplace authorization
            "require_marketplace_admin",
            # Config authorization
            "require_config_viewer",
            "require_config_admin",
            # Cost authorization
            "require_cost_viewer",
            "require_cost_admin",
        ]
    )
