"""
WebSocket Authentication Middleware.

Provides centralized authentication utilities for WebSocket endpoints,
eliminating duplicated JWT extraction and validation logic across endpoints.

Usage:
    from mcp_server_langgraph.websocket.middleware import (
        extract_websocket_token,
        validate_websocket_auth,
        extract_user_from_jwt_payload,
    )

    # In a WebSocket endpoint:
    token = extract_websocket_token(websocket)
    user_data = await validate_websocket_auth(websocket)
"""

from __future__ import annotations

import logging
import warnings
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fastapi import WebSocket

logger = logging.getLogger(__name__)


def get_auth_middleware() -> Any:
    """
    Get the authentication middleware.

    Returns:
        AuthMiddleware instance.
    """
    from mcp_server_langgraph.auth.middleware import get_auth_middleware as _get

    warnings.warn(
        "get_auth_middleware() is deprecated. Use get_auth_middleware_from_request(request) "
        "for proper dependency injection. This will be removed in version 3.0.0.",
        DeprecationWarning,
        stacklevel=2,
    )
    return _get()


def extract_websocket_token(websocket: WebSocket) -> str | None:
    """
    Extract JWT token from WebSocket connection.

    Token sources (in order of precedence):
    1. Query parameter: ?token=<jwt>
    2. Authorization header: Bearer <jwt>

    Args:
        websocket: The WebSocket connection.

    Returns:
        JWT token string if found, None otherwise.
    """
    # Check for token in query params (takes precedence for WebSocket)
    token = websocket.query_params.get("token")

    # Fallback to Authorization header
    if not token:
        auth_header = websocket.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix

    return token if token else None


async def validate_websocket_auth(websocket: WebSocket) -> dict[str, Any] | None:
    """
    Validate WebSocket authentication using JWT.

    Extracts JWT token from query params or Authorization header,
    validates using AuthMiddleware, and returns user data.

    Token sources (in order of precedence):
    1. Query parameter: ?token=<jwt>
    2. Authorization header: Bearer <jwt>

    Args:
        websocket: The WebSocket connection.

    Returns:
        User dict if authenticated, None otherwise.
        User dict contains: user_id, username, roles, email, etc.
    """
    token = extract_websocket_token(websocket)

    if not token:
        logger.debug("WebSocket auth failed: no token provided")
        return None

    try:
        # Use AuthMiddleware for token validation (DI pattern preferred)
        auth_middleware = getattr(websocket.app.state, "auth_middleware", None)
        if auth_middleware is None:
            # Fallback to global for backward compatibility
            from mcp_server_langgraph.auth.middleware import (
                get_auth_middleware as _get_auth,
            )

            auth_middleware = _get_auth()

        result = await auth_middleware.verify_token(token)

        if not result.valid or not result.payload:
            logger.warning(
                "WebSocket auth failed: token verification failed",
                extra={"error": result.error},
            )
            return None

        # Extract user information from JWT payload
        user_data = extract_user_from_jwt_payload(result.payload)

        logger.debug(
            "WebSocket auth success",
            extra={"user_id": user_data.get("user_id")},
        )

        return user_data

    except Exception as e:
        logger.warning(f"WebSocket auth error: {e}", exc_info=True)
        return None


def extract_user_from_jwt_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Extract user information from a JWT payload.

    Handles various JWT claim formats from different identity providers
    (Keycloak, Auth0, generic OIDC, etc.).

    Args:
        payload: The decoded JWT payload.

    Returns:
        Normalized user data dictionary containing:
        - user_id: Unique user identifier
        - username: Display name or preferred username
        - email: User's email address
        - roles: List of user roles
        - raw_payload: Original payload for advanced use cases
    """
    # Try common claim names for user ID
    user_id = payload.get("sub") or payload.get("user_id") or payload.get("uid") or payload.get("id") or "unknown"

    # Try common claim names for username
    username = (
        payload.get("preferred_username")
        or payload.get("username")
        or payload.get("name")
        or payload.get("email", "").split("@")[0]
        or user_id
    )

    # Try common claim names for email
    email = payload.get("email") or payload.get("mail") or ""

    # Try to extract roles from various locations
    roles: list[str] = []

    # Keycloak realm_access.roles
    realm_access = payload.get("realm_access", {})
    if isinstance(realm_access, dict):
        roles.extend(realm_access.get("roles", []))

    # Keycloak resource_access.{client}.roles
    resource_access = payload.get("resource_access", {})
    if isinstance(resource_access, dict):
        for client_roles in resource_access.values():
            if isinstance(client_roles, dict):
                roles.extend(client_roles.get("roles", []))

    # Direct roles claim (Auth0, generic OIDC)
    direct_roles = payload.get("roles", [])
    if isinstance(direct_roles, list):
        roles.extend(direct_roles)

    # Groups claim (sometimes used for roles)
    groups = payload.get("groups", [])
    if isinstance(groups, list):
        roles.extend(groups)

    # Deduplicate roles while preserving order
    seen: set[str] = set()
    unique_roles: list[str] = []
    for role in roles:
        if role not in seen:
            seen.add(role)
            unique_roles.append(role)

    return {
        "user_id": user_id,
        "username": username,
        "email": email,
        "roles": unique_roles,
        "raw_payload": payload,
    }


async def validate_websocket_token(token: str) -> dict[str, Any] | None:
    """
    Validate a JWT token and return the payload.

    This is a lower-level function for cases where you already have
    the token extracted.

    Args:
        token: The JWT token to validate.

    Returns:
        JWT payload dict if valid, None otherwise.
    """
    try:
        from mcp_server_langgraph.auth.middleware import (
            get_auth_middleware as _get_auth,
        )

        auth_middleware = _get_auth()
        result = await auth_middleware.verify_token(token)

        if not result.valid or not result.payload:
            logger.warning(
                "Token validation failed",
                extra={"error": result.error},
            )
            return None

        return result.payload

    except Exception as e:
        logger.warning(f"Token validation error: {e}", exc_info=True)
        return None
