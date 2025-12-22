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
    from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

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


def set_global_auth_middleware(auth: "AuthMiddleware") -> None:
    """
    Set global auth middleware instance for FastAPI dependencies.

    This should be called during application startup.

    Args:
        auth: AuthMiddleware instance configured with user provider, OpenFGA, etc.
    """
    global _global_auth_middleware
    _global_auth_middleware = auth
    logger.info(
        "Global auth middleware set",
        extra={"provider_type": type(auth.user_provider).__name__},
    )


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
            credentials: HTTPAuthorizationCredentials | None = bearer_scheme,  # type: ignore[assignment]
        ) -> dict[str, Any]:
            # Get authenticated user
            user = await get_current_user(request)

            # Check authorization if required
            if relation and resource:
                auth = get_auth_middleware()
                authorized = await auth.authorize(user_id=user["user_id"], relation=relation, resource=resource)

                if not authorized:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Not authorized: {user['user_id']} cannot {relation} {resource}",
                    )

            return user

        return dependency  # type: ignore[return-value]


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
            # WebSocket auth middleware access
            "get_auth_middleware_from_websocket",
        ]
    )
