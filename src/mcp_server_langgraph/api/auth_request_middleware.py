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

from mcp_server_langgraph.auth.jwt_utils import extract_user_from_jwt_payload
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
                    # Uses shared function for consistent extraction across all services
                    user_data = extract_user_from_jwt_payload(verification.payload)
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
