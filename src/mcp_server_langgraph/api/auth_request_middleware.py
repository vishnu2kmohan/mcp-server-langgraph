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

    Extracts Bearer tokens from Authorization headers, verifies them,
    and sets request.state.user for authenticated requests.

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

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            HTTP response from downstream handlers
        """
        # Extract Bearer token from Authorization header
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

        return {
            "user_id": user_id,
            "keycloak_id": keycloak_id,  # Raw UUID for Keycloak Admin API
            "username": username,
            "roles": payload.get("roles", []),
            "email": payload.get("email"),
        }
