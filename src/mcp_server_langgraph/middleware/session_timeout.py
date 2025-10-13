"""
Session Timeout Middleware - HIPAA 164.312(a)(2)(iii)

Implements automatic logoff after period of inactivity.
Required for HIPAA compliance when processing PHI.
"""

from datetime import datetime
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from mcp_server_langgraph.auth.session import SessionStore, get_session_store
from mcp_server_langgraph.observability.telemetry import logger, metrics


class SessionTimeoutMiddleware(BaseHTTPMiddleware):
    """
    Automatic session timeout middleware (HIPAA 164.312(a)(2)(iii))

    Terminates inactive sessions after configured timeout period.
    Default timeout: 15 minutes (HIPAA recommendation).

    Features:
    - Configurable timeout period
    - Sliding window (activity extends session)
    - Audit logging of timeout events
    - Metrics tracking
    """

    def __init__(
        self,
        app,
        timeout_seconds: int = 900,  # 15 minutes default
        session_store: SessionStore = None,
    ):
        """
        Initialize session timeout middleware

        Args:
            app: FastAPI application
            timeout_seconds: Inactivity timeout in seconds (default: 900 = 15 minutes)
            session_store: Session storage backend
        """
        super().__init__(app)
        self.timeout_seconds = timeout_seconds
        self.session_store = session_store or get_session_store()

        logger.info(
            f"Session timeout middleware initialized",
            extra={"timeout_seconds": timeout_seconds, "timeout_minutes": timeout_seconds / 60},
        )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Check session activity and enforce timeout

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/endpoint

        Returns:
            Response (401 if session timed out, otherwise normal response)
        """
        # Skip timeout check for public endpoints
        if self._is_public_endpoint(request.url.path):
            return await call_next(request)

        # Get session from request (if authenticated)
        session_id = self._get_session_id(request)

        if not session_id:
            # No session, continue normally
            return await call_next(request)

        # Check session inactivity
        try:
            session = await self.session_store.get(session_id)

            if not session:
                # Session not found (already expired or deleted)
                return await call_next(request)

            # Parse last accessed time
            last_accessed = datetime.fromisoformat(session.last_accessed.replace("Z", ""))
            now = datetime.utcnow()
            inactive_seconds = (now - last_accessed).total_seconds()

            if inactive_seconds > self.timeout_seconds:
                # Session has timed out
                await self._handle_timeout(request, session_id, inactive_seconds)

                return JSONResponse(
                    status_code=401,
                    content={
                        "detail": "Session expired due to inactivity",
                        "inactive_seconds": int(inactive_seconds),
                        "timeout_seconds": self.timeout_seconds,
                        "code": "SESSION_TIMEOUT",
                    },
                )

            # Update last activity time (sliding window)
            session.last_accessed = now.isoformat() + "Z"
            await self.session_store.update(session)

        except Exception as e:
            logger.error(f"Session timeout check failed: {e}", exc_info=True)
            # Continue on error (fail open for availability)

        # Session is active, continue
        response = await call_next(request)
        return response

    async def _handle_timeout(self, request: Request, session_id: str, inactive_seconds: float):
        """
        Handle session timeout

        Args:
            request: HTTP request
            session_id: Session ID that timed out
            inactive_seconds: Seconds of inactivity
        """
        # Delete the session
        await self.session_store.delete(session_id)

        # Log timeout event (HIPAA audit requirement)
        logger.warning(
            "HIPAA: Session timeout",
            extra={
                "session_id": session_id,
                "inactive_seconds": inactive_seconds,
                "timeout_seconds": self.timeout_seconds,
                "ip_address": request.client.host if request.client else "unknown",
                "path": request.url.path,
            },
        )

        # Track metrics
        metrics.successful_calls.add(
            1,
            {
                "operation": "session_timeout",
                "inactive_seconds": int(inactive_seconds),
            },
        )

    def _get_session_id(self, request: Request) -> str | None:
        """
        Extract session ID from request

        Tries multiple sources:
        1. Authorization header (Bearer token)
        2. Cookie
        3. Request state (if already authenticated)

        Args:
            request: HTTP request

        Returns:
            Session ID or None
        """
        # Try Authorization header
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            # In production, decode JWT to get session_id
            # For now, return None (requires JWT decoding)
            pass

        # Try cookie
        session_id = request.cookies.get("session_id")
        if session_id:
            return session_id

        # Try request state (if already authenticated by previous middleware)
        if hasattr(request.state, "session_id"):
            return request.state.session_id

        return None

    def _is_public_endpoint(self, path: str) -> bool:
        """
        Check if endpoint is public (no timeout enforcement)

        Args:
            path: Request path

        Returns:
            True if public endpoint
        """
        public_paths = [
            "/health",
            "/metrics",
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/docs",
            "/openapi.json",
        ]

        return any(path.startswith(public_path) for public_path in public_paths)


def create_session_timeout_middleware(
    app,
    timeout_minutes: int = 15,
    session_store: SessionStore = None,
) -> SessionTimeoutMiddleware:
    """
    Create session timeout middleware

    Args:
        app: FastAPI application
        timeout_minutes: Inactivity timeout in minutes (default: 15)
        session_store: Session storage backend

    Returns:
        SessionTimeoutMiddleware instance

    Example:
        from fastapi import FastAPI
        from mcp_server_langgraph.middleware.session_timeout import create_session_timeout_middleware

        app = FastAPI()

        # Add session timeout middleware (HIPAA compliant)
        app.add_middleware(
            SessionTimeoutMiddleware,
            timeout_seconds=900,  # 15 minutes
            session_store=session_store
        )
    """
    return SessionTimeoutMiddleware(
        app=app,
        timeout_seconds=timeout_minutes * 60,
        session_store=session_store,
    )
