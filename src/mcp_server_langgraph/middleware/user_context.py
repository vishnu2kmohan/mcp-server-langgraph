"""
User Context Middleware

Sets user_id in contextvar for per-request user scoping.
Guarantees setup at request start and cleanup in finally block.

v8 Implementation per Q12 decision (Middleware) and Q20 (dict access):
- Centralized contextvar lifecycle management
- Single place for setup/cleanup, DRY
- Uses dict.get() for user extraction (Finding 49)

Addresses:
- Finding 49: UserContextMiddleware uses getattr but User is Dict
- Q12: Contextvar setup pattern (middleware selected)
- Q15: Middleware ordering (must run after AuthRequestMiddleware)
"""

from __future__ import annotations

from contextvars import Token
from typing import TYPE_CHECKING, Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from mcp_server_langgraph.observability.telemetry import logger
from mcp_server_langgraph.storage.session.adapter import _current_user_id

if TYPE_CHECKING:
    from starlette.types import ASGIApp


class UserContextMiddleware(BaseHTTPMiddleware):
    """Middleware for contextvar lifecycle management.

    Guarantees setup at request start and cleanup in finally block.
    DRY - single place for user context management.

    IMPORTANT: Must be registered AFTER AuthRequestMiddleware in app.py.
    AuthRequestMiddleware sets request.state.user, this middleware reads it.

    v8 FIX: request.state.user is a DICT (set by AuthRequestMiddleware line 82),
    not an object. Use dict.get() instead of getattr() (Finding 49, Q20).

    Example ordering in app.py:
        # Starlette middleware is LIFO for requests
        app.add_middleware(UserContextMiddleware)  # Added first = runs second
        app.add_middleware(AuthRequestMiddleware)   # Added second = runs first
    """

    def __init__(self, app: ASGIApp) -> None:
        """Initialize middleware.

        Args:
            app: ASGI application
        """
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        """Process request with contextvar lifecycle management.

        Sets user_id contextvar at request start, resets in finally block.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            HTTP response from downstream handlers
        """
        # Save token for reset
        token: Token[str] | None = None
        try:
            # Extract user_id from auth (auth middleware handles 401)
            user_id = self._extract_user_id(request)
            if user_id:
                token = _current_user_id.set(user_id)

            response = await call_next(request)
            return response
        finally:
            # Guaranteed cleanup - reset contextvar
            if token is not None:
                _current_user_id.reset(token)

    def _extract_user_id(self, request: Request) -> str | None:
        """Extract user_id from request state (set by auth middleware).

        v8 FIX: AuthRequestMiddleware sets user as DICT (line 82),
        not an object. Use dict.get() instead of getattr (Finding 49, Q20).

        Hardened: Returns None (not empty string) when extraction fails,
        preventing downstream history loss from empty contextvar (RC2).

        Args:
            request: HTTP request with state.user potentially set

        Returns:
            User ID string if found, None otherwise (never empty string)
        """
        # Auth middleware sets request.state.user as dict
        user = getattr(request.state, "user", None)
        if user is None:
            return None

        # v8 FIX: user is dict, use .get() not getattr (Finding 49, Q20)
        if isinstance(user, dict):
            user_id = user.get("sub") or user.get("user_id") or user.get("id")
            if not user_id:
                logger.warning(
                    "Failed to extract user_id from authenticated user dict — JWT may be missing sub/user_id/id claims",
                    extra={
                        "available_keys": list(user.keys()),
                        "path": request.url.path,
                    },
                )
                return None
            return user_id

        # Fallback for object (shouldn't happen with current auth middleware)
        user_id = getattr(user, "sub", None) or getattr(user, "id", None)
        if not user_id:
            logger.warning(
                "Failed to extract user_id from user object",
                extra={"user_type": type(user).__name__},
            )
            return None
        return user_id
