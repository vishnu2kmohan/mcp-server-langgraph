"""
DevTools Event Emitter Middleware.

Emits console log and network request events to the DevTools WebSocket broadcaster.
This middleware integrates with the existing DevToolsBroadcaster to provide
real-time visibility into API requests and application logs.

Features:
    - Emits network events for all HTTP requests
    - Captures request/response details (method, URL, status, duration, size)
    - Session context extraction from request headers/path

Usage:
    Add to FastAPI app middleware stack:

    from mcp_server_langgraph.middleware.devtools_emitter import (
        DevToolsNetworkMiddleware,
    )

    app.add_middleware(DevToolsNetworkMiddleware)
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

if TYPE_CHECKING:
    from starlette.types import ASGIApp

    from mcp_server_langgraph.websocket.handlers.devtools import DevToolsBroadcaster

logger = logging.getLogger(__name__)

# Paths to exclude from network event emission
EXCLUDED_PATHS = frozenset(
    {
        "/health",
        "/healthz",
        "/ready",
        "/api/v1/health",
        "/api/v1/ws/devtools",  # Don't emit events for DevTools WS itself
        "/api/v1/ws/traces",
        "/api/v1/ws/notifications",
        "/metrics",
        "/favicon.ico",
    }
)


def _extract_session_context(request: Request) -> str | None:
    """Extract session ID from request path or headers.

    Args:
        request: The incoming request

    Returns:
        Session ID if found, None otherwise
    """
    # Check path for session ID pattern: /api/v1/sessions/{session_id}/...
    path = request.url.path
    if "/sessions/" in path:
        parts = path.split("/sessions/")
        if len(parts) > 1:
            session_part = parts[1].split("/")[0]
            if session_part and session_part != "":
                return session_part

    # Check header for session context
    session_header = request.headers.get("X-Session-ID")
    if session_header:
        return session_header

    return None


class DevToolsNetworkMiddleware(BaseHTTPMiddleware):
    """Middleware that emits network events to DevTools WebSocket.

    Captures all HTTP requests and emits them as network events to the
    DevToolsBroadcaster for real-time monitoring in the DevTools panel.
    """

    def __init__(self, app: ASGIApp) -> None:
        """Initialize the middleware.

        Args:
            app: The ASGI application
        """
        super().__init__(app)
        self._broadcaster_initialized = False

    def _get_broadcaster(self) -> DevToolsBroadcaster | None:
        """Lazily get the DevTools broadcaster to avoid import issues.

        Returns:
            DevToolsBroadcaster instance or None if websocket module unavailable
            (e.g., in minimal Docker images like authz-proxy).
        """
        try:
            from mcp_server_langgraph.websocket.registry import get_devtools_broadcaster

            return get_devtools_broadcaster()
        except (ImportError, ModuleNotFoundError):
            # Websocket module not available (minimal Docker image)
            return None

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Process the request and emit network events.

        Args:
            request: The incoming request
            call_next: The next middleware/handler in the chain

        Returns:
            The response from the handler
        """
        # Skip excluded paths
        if request.url.path in EXCLUDED_PATHS:
            return await call_next(request)

        # Skip WebSocket upgrade requests
        if request.headers.get("upgrade", "").lower() == "websocket":
            return await call_next(request)

        # Generate request ID
        request_id = str(uuid.uuid4())[:8]
        start_time = time.time()

        # Extract session context for filtering
        session_id = _extract_session_context(request)

        # Emit network request start event
        try:
            broadcaster = self._get_broadcaster()
            if broadcaster is None:
                # Websocket module not available, skip broadcast
                response = await call_next(request)
                return response
            await broadcaster.broadcast_network(
                {
                    "id": request_id,
                    "method": request.method,
                    "url": str(request.url.path),
                    "status": "pending",
                    "startTime": int(start_time * 1000),
                    "requestHeaders": dict(request.headers),
                },
                context_entity_id=session_id,
            )
        except Exception as e:
            # Don't fail the request if broadcasting fails
            logger.debug("Failed to emit network start event: %s", e)

        # Call the actual handler
        response: Response = await call_next(request)

        # Calculate duration
        end_time = time.time()
        duration_ms = int((end_time - start_time) * 1000)

        # Emit network request completion event
        try:
            broadcaster = self._get_broadcaster()
            if broadcaster is None:
                # Websocket module not available, skip broadcast
                return response
            status = "completed" if response.status_code < 400 else "error"

            # Try to get response size from content-length header
            content_length = response.headers.get("content-length")
            response_size = int(content_length) if content_length else None

            await broadcaster.broadcast_network_update(
                {
                    "id": request_id,
                    "status": status,
                    "statusCode": response.status_code,
                    "duration": duration_ms,
                    "responseSize": response_size,
                    "responseHeaders": dict(response.headers),
                },
                context_entity_id=session_id,
            )
        except Exception as e:
            # Don't fail the request if broadcasting fails
            logger.debug("Failed to emit network complete event: %s", e)

        return response


class DevToolsLoggingHandler(logging.Handler):
    """Logging handler that emits console events to DevTools WebSocket.

    Attach to Python loggers to forward log messages to the DevTools panel.

    Usage:
        handler = DevToolsLoggingHandler()
        handler.setLevel(logging.INFO)
        logging.getLogger("mcp_server_langgraph").addHandler(handler)
    """

    def __init__(self, level: int = logging.NOTSET) -> None:
        """Initialize the handler.

        Args:
            level: Minimum log level to emit
        """
        super().__init__(level)
        self._loop: asyncio.AbstractEventLoop | None = None

    def _get_broadcaster(self) -> DevToolsBroadcaster | None:
        """Lazily get the DevTools broadcaster to avoid import issues.

        Returns:
            DevToolsBroadcaster instance or None if websocket module unavailable
            (e.g., in minimal Docker images like authz-proxy).
        """
        try:
            from mcp_server_langgraph.websocket.registry import get_devtools_broadcaster

            return get_devtools_broadcaster()
        except (ImportError, ModuleNotFoundError):
            # Websocket module not available (minimal Docker image)
            return None

    def _map_level(self, levelno: int) -> str:
        """Map Python log level to DevTools console level.

        Args:
            levelno: Python log level number

        Returns:
            DevTools console level string
        """
        if levelno >= logging.ERROR:
            return "error"
        if levelno >= logging.WARNING:
            return "warning"
        if levelno >= logging.INFO:
            return "info"
        return "debug"

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record as a DevTools console event.

        Args:
            record: The log record to emit
        """
        try:
            # Get or create event loop
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # No running loop, skip emission
                return

            # Format the message
            message = self.format(record)

            # Extract session context from record if available
            session_id = getattr(record, "session_id", None)
            if not session_id and hasattr(record, "extra"):
                session_id = record.extra.get("session_id")

            # Create console entry
            entry = {
                "id": str(uuid.uuid4())[:8],
                "level": self._map_level(record.levelno),
                "message": message,
                "timestamp": int(record.created * 1000),
                # Frontend expects a bounded source enum (system/api/mcp/notification/execution/websocket)
                "source": "system",
                # Provide structured context for expanded view without breaking the ConsoleEntry contract
                "data": {
                    "logger": record.name,
                    "filename": record.filename,
                    "lineno": record.lineno,
                    "function": record.funcName,
                },
            }

            # Schedule the broadcast (don't block) - task runs independently
            broadcaster = self._get_broadcaster()
            if broadcaster is None:
                # Websocket module not available, skip broadcast
                return
            task = loop.create_task(broadcaster.broadcast_console(entry, context_entity_id=session_id))
            # Suppress unhandled exception warnings for fire-and-forget task
            task.add_done_callback(lambda t: t.exception() if t.done() and not t.cancelled() else None)

        except Exception:
            # Never fail logging - handle exceptions silently
            self.handleError(record)
