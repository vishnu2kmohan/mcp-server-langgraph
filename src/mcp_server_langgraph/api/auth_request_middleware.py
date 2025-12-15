"""
FastAPI Request Middleware for Authentication

This middleware intercepts incoming HTTP requests, extracts Bearer tokens,
verifies them, and sets request.state.user for downstream handlers.

Benefits of middleware approach over dependency injection:
- Runs before route handlers (earlier in request lifecycle)
- Simpler testing (no dependency override complexity)
- More explicit request flow
- Easier to understand and maintain
"""

from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from mcp_server_langgraph.auth.middleware import AuthMiddleware
from mcp_server_langgraph.observability.telemetry import logger


class AuthRequestMiddleware(BaseHTTPMiddleware):
    """
    FastAPI request middleware for JWT-based authentication.

    Supports multiple authentication methods:
    1. Bearer token in Authorization header (JWT direct auth)
    2. X-Forwarded-* headers from Traefik forward-auth (Keycloak SSO)

    Extracts authentication info and sets request.state.user for authenticated requests.

    Usage:
        app = FastAPI()
        auth_middleware = AuthMiddleware(secret_key=settings.secret_key)
        app.add_middleware(AuthRequestMiddleware, auth_middleware=auth_middleware)
    """

    def __init__(self, app, auth_middleware: AuthMiddleware):  # type: ignore[no-untyped-def]
        """
        Initialize the auth request middleware.

        Args:
            app: FastAPI application
            auth_middleware: AuthMiddleware instance for token verification
        """
        super().__init__(app)
        self.auth_middleware = auth_middleware

    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        """
        Process incoming request, extract and verify auth token.

        Checks authentication sources in order:
        1. Bearer token in Authorization header
        2. X-Forwarded-* headers from Traefik forward-auth

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            HTTP response from downstream handlers
        """
        # Try Method 1: Extract Bearer token from Authorization header
        auth_header = request.headers.get("Authorization", "")
        token = None

        if auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix

        # If token present, verify it and set request.state.user
        if token:
            try:
                verification = await self.auth_middleware.verify_token(token)

                if verification.valid and verification.payload:
                    # Extract user information from token payload
                    user_data = self._extract_user_from_payload(verification.payload)
                    request.state.user = user_data

                    logger.debug(
                        "Request authenticated via middleware",
                        extra={
                            "user_id": user_data.get("user_id"),
                            "username": user_data.get("username"),
                            "path": request.url.path,
                        },
                    )
                else:
                    # Invalid token - don't set request.state.user
                    # Let endpoints decide how to handle unauthenticated requests
                    logger.debug(
                        "Token verification failed",
                        extra={
                            "error": verification.error,
                            "path": request.url.path,
                        },
                    )

            except Exception as e:
                # Token verification error - don't set request.state.user
                logger.warning(
                    f"Token verification exception: {e}",
                    extra={"path": request.url.path},
                    exc_info=True,
                )

        # Try Method 2: Forward-auth headers from Traefik (Keycloak SSO)
        # Only if request.state.user not already set by Bearer token
        if not hasattr(request.state, "user") or not request.state.user:
            forward_auth_data = self._extract_user_from_forward_auth_headers(request)
            if forward_auth_data:
                request.state.user = forward_auth_data
                logger.debug(
                    "Request authenticated via forward-auth headers",
                    extra={
                        "user_id": forward_auth_data.get("user_id"),
                        "username": forward_auth_data.get("username"),
                        "path": request.url.path,
                    },
                )

        # Continue to next middleware/handler
        # If authentication failed, request.state.user won't be set,
        # and endpoints can return 401 as needed
        response = await call_next(request)
        return response

    def _extract_user_from_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Extract user information from JWT payload.

        Handles both InMemory tokens and Keycloak tokens with proper field mapping.

        Args:
            payload: JWT token payload

        Returns:
            User data dict with user_id, username, roles, etc.
        """
        # Extract Keycloak UUID from sub claim (if present)
        keycloak_id = payload.get("sub")

        # Priority: preferred_username (Keycloak) > username (InMemory) > extract from sub (fallback)
        username = payload.get("preferred_username") or payload.get("username")

        if not username:
            # Fallback to extracting username from sub
            sub = keycloak_id or "unknown"

            # If sub is in "user:username" format, extract username
            if sub.startswith("user:"):
                id_part = sub.replace("user:", "")

                # Handle worker-safe IDs (e.g., "user:test_gw0_charlie" → "charlie")
                import re

                match = re.match(r"test_gw\d+_(.*)", id_part)
                username = match.group(1) if match else id_part
            else:
                username = sub

        # For user_id, use sub directly if it's already in "user:*" format, otherwise normalize from username
        # This preserves worker-safe IDs like "user:test_gw0_alice" from InMemoryUserProvider tokens
        if keycloak_id and keycloak_id.startswith("user:"):
            user_id = keycloak_id  # Use sub directly (preserves worker-safe IDs)
        else:
            # Normalize to "user:username" format for OpenFGA compatibility
            user_id = f"user:{username}" if not username.startswith("user:") else username

        # Extract roles from Keycloak JWT structure
        # Keycloak can put roles in multiple places:
        # 1. realm_access.roles - realm-level roles
        # 2. resource_access.<client>.roles - client-level roles
        # 3. roles - sometimes mapped directly (InMemoryUserProvider)
        roles: list[str] = []

        # Check direct roles first (InMemoryUserProvider)
        if payload.get("roles"):
            roles = payload.get("roles", [])
        else:
            # Extract from Keycloak realm_access structure
            realm_access = payload.get("realm_access", {})
            if realm_access and isinstance(realm_access, dict):
                roles.extend(realm_access.get("roles", []))

            # Also check resource_access for client-specific roles
            resource_access = payload.get("resource_access", {})
            if resource_access and isinstance(resource_access, dict):
                for client_roles in resource_access.values():
                    if isinstance(client_roles, dict):
                        roles.extend(client_roles.get("roles", []))

        return {
            "user_id": user_id,
            "keycloak_id": keycloak_id,  # Raw UUID for Keycloak Admin API
            "username": username,
            "roles": roles,
            "email": payload.get("email"),
        }

    def _extract_user_from_forward_auth_headers(self, request: Request) -> dict[str, Any] | None:
        """
        Extract user information from Traefik forward-auth headers.

        Traefik forward-auth middleware sets headers like:
        - X-Forwarded-User: Username (from preferred_username claim)
        - X-Forwarded-Email: Email address
        - X-Forwarded-Groups: Comma-separated list of roles/groups

        This enables Keycloak SSO without requiring a Bearer token in the request.

        Args:
            request: Incoming HTTP request

        Returns:
            User data dict if forward-auth headers present, None otherwise
        """
        # Check for X-Forwarded-User header (set by Traefik forward-auth)
        username = request.headers.get("X-Forwarded-User")
        if not username:
            return None

        # Extract additional info from forward-auth headers
        email = request.headers.get("X-Forwarded-Email")
        groups_header = request.headers.get("X-Forwarded-Groups", "")

        # Parse roles from comma-separated groups header
        roles = [g.strip() for g in groups_header.split(",") if g.strip()] if groups_header else []

        # Build user_id in OpenFGA format
        user_id = f"user:{username}"

        return {
            "user_id": user_id,
            "keycloak_id": None,  # Not available via forward-auth headers
            "username": username,
            "roles": roles,
            "email": email,
        }
