"""
MCP WebSocket Handler - Deprecated Compatibility Shim

DEPRECATION NOTICE:
    This module is deprecated and will be removed in v4.0 (scheduled: 2025-06-01).
    All classes and functions have been migrated to:

    - mcp_server_langgraph.mcp.websocket (ConnectionManager, streaming, lifecycle, metrics)
    - mcp_server_langgraph.mcp.message_handler (MCPMessageHandler, AuthenticatedMCPHandler)

    Please update your imports:

    # NEW (preferred):
    from mcp_server_langgraph.mcp.websocket import (
        ConnectionManager, ConnectionInfo,
        StreamingToolCallHandler, StreamingMetricsCollector, StreamStats,
        MCPWebSocketLifecycleManager,
        OTelMCPMetrics,
        UserRateLimiterManager, OutboundRateLimiter,
        is_streaming_enabled, set_streaming_enabled,
        get_streaming_max_chunk_size, set_streaming_max_chunk_size,
        get_connection_manager, set_connection_manager, create_connection_manager,
        get_mcp_lifecycle_manager, set_mcp_lifecycle_manager, create_mcp_lifecycle_manager,
        get_user_rate_limiter, set_user_rate_limiter, create_user_rate_limiter,
        get_outbound_rate_limiter, set_outbound_rate_limiter, create_outbound_rate_limiter,
        update_connection_activity, is_connection_idle,
        streaming_metrics_collector,
    )

    from mcp_server_langgraph.mcp.message_handler import (
        MCPMessageHandler,
        AuthenticatedMCPHandler,
    )

    # OLD (deprecated, will be removed in v4.0):
    from mcp_server_langgraph.api.v1.mcp_websocket import ConnectionManager  # Deprecated!
"""

from __future__ import annotations

import logging
import re
import warnings
from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Any, TYPE_CHECKING

from fastapi import APIRouter, WebSocket

if TYPE_CHECKING:
    from mcp_server_langgraph.mcp.websocket.connection_manager import ConnectionManager as _CM

# =============================================================================
# JSON-RPC 2.0 Error Codes
# =============================================================================

PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603

# =============================================================================
# Security Limits (Constants for backward compatibility)
# =============================================================================

MAX_CONNECTIONS_PER_USER = 5
MAX_MESSAGE_SIZE = 1_000_000  # 1MB
MAX_MESSAGES_PER_MINUTE = 600
IDLE_TIMEOUT_SECONDS = 1800  # 30 minutes
MAX_SESSION_ID_LENGTH = 128
IDLE_CLEANUP_INTERVAL = 60

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    """Return current UTC time with timezone awareness."""
    return datetime.now(UTC)


# =============================================================================
# Security Utilities (Unique to this module - not yet migrated)
# =============================================================================

_SESSION_ID_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$")


def validate_message_size(message: str, max_size: int | None = None) -> bool:
    """
    Validate that a message does not exceed the size limit.

    Args:
        message: The message string to validate.
        max_size: Optional custom max size. Defaults to MAX_MESSAGE_SIZE if not provided.

    Returns:
        True if message is within size limit, False if oversized.
    """
    limit = max_size if max_size is not None else MAX_MESSAGE_SIZE
    return len(message) <= limit


def validate_session_id(session_id: str) -> bool:
    """
    Validate a session ID for safety and correctness.

    Args:
        session_id: The session ID to validate.

    Returns:
        True if valid, False if invalid.
    """
    if not session_id or not session_id.strip():
        return False

    if len(session_id) > MAX_SESSION_ID_LENGTH:
        return False

    if "\x00" in session_id:
        return False

    return bool(_SESSION_ID_PATTERN.match(session_id))


def sanitize_session_id(session_id: str) -> str:
    """
    Sanitize a session ID by removing unsafe characters.

    Args:
        session_id: The session ID to sanitize.

    Returns:
        Sanitized session ID with only safe characters.
    """
    session_id = session_id.replace("\x00", "")
    sanitized = re.sub(r"[^a-zA-Z0-9_-]", "", session_id)

    if sanitized and not sanitized[0].isalnum():
        sanitized = "s" + sanitized

    return sanitized[:MAX_SESSION_ID_LENGTH]


def extract_websocket_token(websocket: WebSocket) -> str | None:
    """
    Extract authentication token from WebSocket connection.

    Checks query params first (for browsers), then Authorization header.

    Args:
        websocket: The WebSocket connection.

    Returns:
        The extracted token, or None if not found.
    """
    token = websocket.query_params.get("token")
    if token:
        return token

    auth_header = websocket.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]

    return None


# =============================================================================
# Message Rate Limiter (Legacy - kept for backward compatibility)
# =============================================================================


class MessageRateLimiter:
    """
    Rate limiter for WebSocket messages using sliding window.

    DEPRECATED: Use mcp_server_langgraph.websocket.rate_limiter.UserRateLimiter instead.
    """

    def __init__(self, max_messages: int, window_seconds: int) -> None:
        """Initialize the rate limiter."""
        self.max_messages = max_messages
        self.window_seconds = window_seconds
        self._message_count = 0
        self._window_start = _utc_now()

    def check_and_increment(self) -> bool:
        """Check if a message is allowed and increment the counter."""
        now = _utc_now()
        elapsed = (now - self._window_start).total_seconds()

        if elapsed >= self.window_seconds:
            self._window_start = now
            self._message_count = 0

        if self._message_count >= self.max_messages:
            return False

        self._message_count += 1
        return True

    def reset(self) -> None:
        """Reset the rate limiter."""
        self._message_count = 0
        self._window_start = _utc_now()


# =============================================================================
# Validation Result (Used by SecureMessageProcessor)
# =============================================================================


@dataclass
class ValidationResult:
    """Result of message validation."""

    is_valid: bool
    error_message: str = ""
    error_code: int = 0


# =============================================================================
# Secure Message Processor
# =============================================================================


class SecureMessageProcessor:
    """
    Secure message processor that enforces all security checks.

    Combines rate limiting, size validation, activity tracking, and metrics.
    """

    def __init__(
        self,
        session_id: str,
        user_id: str | None = None,
        rate_limiter: Any = None,
        connection_manager: Any = None,
        metrics: Any = None,
        max_message_size: int | None = None,
    ) -> None:
        """Initialize the secure message processor."""
        self.session_id = session_id
        self.user_id = user_id
        self.rate_limiter = rate_limiter
        self.connection_manager = connection_manager
        self.metrics = metrics
        self.max_message_size = max_message_size if max_message_size is not None else MAX_MESSAGE_SIZE

    def validate_incoming(self, message: str) -> ValidationResult:
        """Validate an incoming message against all security checks."""
        if not validate_message_size(message, max_size=self.max_message_size):
            if self.metrics:
                identifier = self.user_id or f"session:{self.session_id}"
                self.metrics.record_message_size_exceeded(user_id=identifier)
            return ValidationResult(
                is_valid=False,
                error_message=f"Message size exceeds limit of {self.max_message_size} bytes",
                error_code=-32600,
            )

        if self.rate_limiter:
            identifier = self.user_id or f"session:{self.session_id}"
            if not self.rate_limiter.check_and_increment(identifier):
                if self.metrics:
                    self.metrics.record_rate_limit_exceeded(identifier)
                return ValidationResult(
                    is_valid=False,
                    error_message="Rate limit exceeded",
                    error_code=-32000,
                )

        return ValidationResult(is_valid=True)

    def on_message_processed(self) -> None:
        """Called after a message has been successfully processed."""
        if self.connection_manager:
            self.connection_manager.update_activity(self.session_id)

    def record_message_received(self, method: str) -> None:
        """Record that a message was received."""
        if self.metrics:
            self.metrics.record_message_received(method)

    def record_message_sent(self, method: str) -> None:
        """Record that a message was sent."""
        if self.metrics:
            self.metrics.record_message_sent(method)


# =============================================================================
# Mock Metrics Classes (For testing without OpenTelemetry)
# =============================================================================


class Counter:
    """Simple thread-safe counter for metrics."""

    def __init__(self, name: str, description: str = "") -> None:
        self.name = name
        self.description = description
        self._value = 0

    def add(self, amount: int = 1, attributes: dict[str, Any] | None = None) -> None:
        self._value += amount

    def get(self) -> int:
        """Get the current counter value."""
        return self._value


class Gauge:
    """Simple gauge for metrics."""

    def __init__(self, name: str, description: str = "") -> None:
        self.name = name
        self.description = description
        self._value = 0

    def set(self, value: int | float, attributes: dict[str, Any] | None = None) -> None:
        self._value = value


class MCPWebSocketMetrics:
    """Legacy MCP WebSocket metrics without OpenTelemetry dependency."""

    def __init__(self) -> None:
        self.messages_received = Counter("mcp_ws_messages_received")
        self.messages_sent = Counter("mcp_ws_messages_sent")
        self.errors = Counter("mcp_ws_errors")
        self.rate_limits_exceeded = Counter("mcp_ws_rate_limits_exceeded")
        self.message_size_exceeded = Counter("mcp_ws_message_size_exceeded")
        self.connections_rejected = Counter("mcp_ws_connections_rejected")
        self.connections = Gauge("mcp_ws_connections")
        self._method_counts: dict[str, int] = {}
        self._active_connections = 0
        self._total_connections = 0
        self._rate_limit_count = 0

    @property
    def active_connections(self) -> int:
        """Get current active connection count."""
        return self._active_connections

    @property
    def total_connections(self) -> int:
        """Get total connection count."""
        return self._total_connections

    @property
    def rate_limit_exceeded(self) -> int:
        """Get rate limit exceeded count."""
        return self._rate_limit_count

    def record_connection(self) -> None:
        """Record a new connection."""
        self._active_connections += 1
        self._total_connections += 1
        self.connections.set(self._active_connections)

    def record_disconnect(self) -> None:
        """Record a disconnection."""
        self._active_connections = max(0, self._active_connections - 1)
        self.connections.set(self._active_connections)

    def record_message_received(self, method: str) -> None:
        self.messages_received.add()
        self._method_counts[method] = self._method_counts.get(method, 0) + 1

    def record_message_sent(self, method: str) -> None:
        self.messages_sent.add()

    def record_error(self, error_type: str) -> None:
        self.errors.add()

    def record_rate_limit_exceeded(self, user_id: str) -> None:
        self.rate_limits_exceeded.add()
        self._rate_limit_count += 1

    def record_message_size_exceeded(self, user_id: str) -> None:
        self.message_size_exceeded.add()

    def record_connection_rejected(self, user_id: str, reason: str) -> None:
        """Record a rejected connection with reason."""
        self.connections_rejected.add()

    def set_connections(self, count: int) -> None:
        self._active_connections = count
        self.connections.set(count)

    def get_method_counts(self) -> dict[str, int]:
        return self._method_counts.copy()

    def reset(self) -> None:
        self._method_counts.clear()
        self._active_connections = 0
        self._total_connections = 0
        self._rate_limit_count = 0


# =============================================================================
# Idle Cleanup Functions (Used by lifecycle manager)
# =============================================================================


async def cleanup_idle_connections(manager: _CM) -> int:
    """
    Close idle connections that have exceeded the timeout.

    Args:
        manager: The connection manager to clean up.

    Returns:
        Number of connections closed.
    """
    idle_sessions = manager.get_idle_connections()
    closed_count = 0

    for session_id in idle_sessions:
        if session_id in manager._connections:
            conn_info = manager._connections[session_id]
            try:
                await conn_info.websocket.close(
                    code=4000,
                    reason="Connection idle timeout",
                )
                logger.info(
                    f"Closed idle connection: {session_id}",
                    extra={"session_id": session_id, "user_id": conn_info.user_id},
                )
            except Exception as e:
                logger.warning(
                    f"Error closing idle connection {session_id}: {e}",
                    extra={"session_id": session_id, "error": str(e)},
                )
            finally:
                manager.disconnect(session_id)
                closed_count += 1

    return closed_count


async def graceful_shutdown(manager: _CM, timeout: float = 5.0) -> None:
    """
    Gracefully shutdown all WebSocket connections.

    Args:
        manager: The connection manager.
        timeout: Timeout in seconds for shutdown.
    """
    import asyncio

    for session_id in list(manager._connections.keys()):
        conn_info = manager._connections.get(session_id)
        if conn_info:
            try:
                await asyncio.wait_for(
                    conn_info.websocket.close(code=1001, reason="Server shutdown"),
                    timeout=timeout,
                )
            except Exception:
                pass
            finally:
                manager.disconnect(session_id)


async def idle_cleanup_task(manager: _CM, interval: int = IDLE_CLEANUP_INTERVAL) -> None:
    """
    Background task to periodically cleanup idle connections.

    Args:
        manager: The connection manager.
        interval: Cleanup interval in seconds.
    """
    import asyncio

    while True:
        await asyncio.sleep(interval)
        try:
            closed = await cleanup_idle_connections(manager)
            if closed > 0:
                logger.info(f"Cleaned up {closed} idle connections")
        except Exception:
            logger.exception("Error in idle cleanup task")


# =============================================================================
# Authentication Utilities
# =============================================================================


async def validate_websocket_token(token: str) -> dict[str, Any] | None:
    """
    Validate a WebSocket authentication token.

    Args:
        token: The JWT token to validate.

    Returns:
        Token claims if valid, None if invalid.
    """
    validator = get_token_validator()
    if not validator:
        return None

    try:
        return await validator.validate_token(token)
    except Exception:
        return None


async def check_mcp_permission(
    user_id: str,
    action: str,
    resource: str = "mcp",
) -> bool:
    """
    Check if a user has permission for an MCP action.

    Args:
        user_id: The user identifier.
        action: The action to check (e.g., "execute", "read").
        resource: The resource type (default: "mcp").

    Returns:
        True if permitted, False otherwise.
    """
    client = get_openfga_client()
    if not client:
        return True  # Allow if no authorization configured

    try:
        result = await client.check(
            user=f"user:{user_id}",
            relation=action,
            object=f"{resource}:*",
        )
        return result.allowed
    except Exception:
        return False


def get_token_validator() -> Any | None:
    """
    Get the token validator from application state.

    Returns:
        TokenValidator instance or None if not configured.
    """
    try:
        from mcp_server_langgraph.auth.jwt_utils import get_token_validator as _get_validator

        return _get_validator()
    except ImportError:
        return None


def get_openfga_client() -> Any | None:
    """
    Get the OpenFGA client from application state.

    Returns:
        OpenFGA client instance or None if not configured.
    """
    try:
        from mcp_server_langgraph.security.openfga_client import get_openfga_client as _get_client

        return _get_client()
    except ImportError:
        return None


# =============================================================================
# Handler Factory Functions
# =============================================================================


async def create_handler_from_token(
    websocket: WebSocket | None = None,
    session_id: str | None = None,
    token: str | None = None,
    token_payload: dict[str, Any] | None = None,
    notification_callback: Any = None,
) -> Any:
    """
    Create an MCPMessageHandler from a WebSocket and optional token.

    Supports both new API (websocket, session_id, token) and legacy API (token_payload, session_id).

    Args:
        websocket: The WebSocket connection (optional for backward compat).
        session_id: The session identifier.
        token: Optional authentication token string.
        token_payload: Optional pre-validated token payload (legacy API).
        notification_callback: Optional callback for notifications (stored on handler).

    Returns:
        MCPMessageHandler or AuthenticatedMCPHandler instance.
    """
    from mcp_server_langgraph.mcp.message_handler import (
        AuthenticatedMCPHandler,
        MCPMessageHandler,
    )

    # Handle legacy API (token_payload passed as first positional arg)
    if isinstance(websocket, dict):
        token_payload = websocket
        websocket = None

    # If we have a token_payload (legacy API) or token string
    claims = token_payload
    if token and not claims:
        claims = await validate_websocket_token(token)

    if claims:
        user_id = claims.get("sub", claims.get("user_id", claims.get("preferred_username")))
        # Extract roles from Keycloak format (realm_access.roles) or direct roles claim
        realm_access = claims.get("realm_access", {})
        roles = realm_access.get("roles") or claims.get("roles") or ["user"]  # Default to "user" role
        handler = AuthenticatedMCPHandler(
            user_id=user_id,
            roles=roles,
            session_id=session_id,
        )
        if notification_callback:
            handler.notification_callback = notification_callback
        return handler

    # Return base handler for anonymous access
    handler = MCPMessageHandler()
    if session_id:
        handler.session_id = session_id
    if notification_callback:
        handler.notification_callback = notification_callback
    return handler


async def create_anonymous_streaming_handler(
    websocket: WebSocket | None = None,
    session_id: str | None = None,
    notification_callback: Any = None,
) -> Any:
    """
    Create an anonymous streaming handler.

    Creates an AuthenticatedMCPHandler with session-based user_id for
    anonymous connections that need streaming support.

    Args:
        websocket: The WebSocket connection (optional for backward compat).
        session_id: The session identifier.
        notification_callback: Optional callback for notifications (stored on handler).

    Returns:
        AuthenticatedMCPHandler instance with session-based identity.
    """
    from mcp_server_langgraph.mcp.message_handler import AuthenticatedMCPHandler

    # Create authenticated handler with session-based identity
    user_id = f"session:{session_id}" if session_id else "session:anonymous"
    handler = AuthenticatedMCPHandler(
        user_id=user_id,
        roles=["anonymous"],
        session_id=session_id,
    )
    if notification_callback:
        handler.notification_callback = notification_callback
    return handler


# =============================================================================
# Lifespan Context Manager
# =============================================================================


from contextlib import asynccontextmanager
from collections.abc import AsyncIterator


@asynccontextmanager
async def mcp_websocket_lifespan(app: Any) -> AsyncIterator[None]:
    """
    Lifespan context manager for MCP WebSocket.

    Starts and stops the lifecycle manager.

    Args:
        app: The FastAPI application.

    Yields:
        None
    """
    from mcp_server_langgraph.mcp.websocket import (
        get_mcp_lifecycle_manager,
    )

    manager = get_mcp_lifecycle_manager()
    if manager:
        await manager.startup()

    yield

    if manager:
        await manager.shutdown()


# =============================================================================
# Router with Metrics Endpoint
# =============================================================================

mcp_websocket_router = APIRouter(tags=["MCP WebSocket"])


@mcp_websocket_router.get("/mcp/metrics/streams")
async def get_streaming_metrics(
    active_only: bool = False,
    limit: int = 100,
) -> dict[str, Any]:
    """
    Get streaming metrics for monitoring and debugging.

    Returns aggregate statistics and per-stream details from the
    streaming_metrics_collector.

    Args:
        active_only: If true, only return active (in-progress) streams.
        limit: Maximum number of stream entries to return.

    Returns:
        JSON object with aggregate stats, active count, stream list, and streaming status.
    """
    from mcp_server_langgraph.mcp.websocket import (
        is_streaming_enabled,
        streaming_metrics_collector,
    )

    aggregate = streaming_metrics_collector.get_aggregate_stats()

    streams: list[dict[str, Any]] = []
    active_count = 0

    for stream_id, stats in streaming_metrics_collector._streams.items():
        is_active = stats.start_time is not None and stats.end_time is None
        if is_active:
            active_count += 1

        if active_only and not is_active:
            continue

        if len(streams) >= limit:
            break

        streams.append(
            {
                "stream_id": stream_id,
                "chunk_count": stats.chunk_count,
                "total_bytes": stats.total_bytes,
                "avg_chunk_size": stats.avg_chunk_size,
                "duration_ms": stats.duration_ms,
                "is_active": is_active,
            }
        )

    return {
        "aggregate": aggregate,
        "active_streams": active_count,
        "streams": streams,
        "streaming_enabled": is_streaming_enabled(),
        "timestamp": _utc_now().isoformat(),
    }


# =============================================================================
# Deprecated Re-exports with Deprecation Warnings
# =============================================================================
# These are re-exported from new locations for backward compatibility.
# All imports will trigger deprecation warnings.

_DEPRECATION_MAP = {
    # Connection management
    "ConnectionManager": ("mcp_server_langgraph.mcp.websocket.connection_manager", "ConnectionManager"),
    "ConnectionInfo": ("mcp_server_langgraph.mcp.websocket.connection_manager", "ConnectionInfo"),
    "connection_manager": ("mcp_server_langgraph.mcp.websocket.connection_manager", "_connection_manager"),
    "get_connection_manager": ("mcp_server_langgraph.mcp.websocket.connection_manager", "get_connection_manager"),
    "set_connection_manager": ("mcp_server_langgraph.mcp.websocket.connection_manager", "set_connection_manager"),
    "create_connection_manager": ("mcp_server_langgraph.mcp.websocket.connection_manager", "create_connection_manager"),
    "update_connection_activity": ("mcp_server_langgraph.mcp.websocket.connection_manager", "update_connection_activity"),
    "is_connection_idle": ("mcp_server_langgraph.mcp.websocket.connection_manager", "is_connection_idle"),
    # Streaming
    "StreamingToolCallHandler": ("mcp_server_langgraph.mcp.websocket.streaming", "StreamingToolCallHandler"),
    "StreamingMetricsCollector": ("mcp_server_langgraph.mcp.websocket.streaming", "StreamingMetricsCollector"),
    "StreamStats": ("mcp_server_langgraph.mcp.websocket.streaming", "StreamStats"),
    "streaming_metrics_collector": ("mcp_server_langgraph.mcp.websocket.streaming", "streaming_metrics_collector"),
    # Lifecycle
    "MCPWebSocketLifecycleManager": ("mcp_server_langgraph.mcp.websocket.lifecycle", "MCPWebSocketLifecycleManager"),
    "_lifecycle_manager": ("mcp_server_langgraph.mcp.websocket.lifecycle", "_lifecycle_manager"),
    "get_mcp_lifecycle_manager": ("mcp_server_langgraph.mcp.websocket.lifecycle", "get_mcp_lifecycle_manager"),
    "set_mcp_lifecycle_manager": ("mcp_server_langgraph.mcp.websocket.lifecycle", "set_mcp_lifecycle_manager"),
    "create_mcp_lifecycle_manager": ("mcp_server_langgraph.mcp.websocket.lifecycle", "create_mcp_lifecycle_manager"),
    # Metrics
    "OTelMCPMetrics": ("mcp_server_langgraph.mcp.websocket.metrics", "OTelMCPMetrics"),
    "otel_metrics": ("mcp_server_langgraph.mcp.websocket.metrics", "otel_metrics"),
    "get_otel_metrics": ("mcp_server_langgraph.mcp.websocket.metrics", "get_otel_metrics"),
    # Config
    "is_streaming_enabled": ("mcp_server_langgraph.mcp.websocket.config", "is_streaming_enabled"),
    "set_streaming_enabled": ("mcp_server_langgraph.mcp.websocket.config", "set_streaming_enabled"),
    "get_streaming_max_chunk_size": ("mcp_server_langgraph.mcp.websocket.config", "get_streaming_max_chunk_size"),
    "set_streaming_max_chunk_size": ("mcp_server_langgraph.mcp.websocket.config", "set_streaming_max_chunk_size"),
    # Rate limiting
    "UserRateLimiterManager": ("mcp_server_langgraph.mcp.websocket.rate_limiter", "UserRateLimiterManager"),
    "OutboundRateLimiter": ("mcp_server_langgraph.mcp.websocket.rate_limiter", "OutboundRateLimiter"),
    "get_user_rate_limiter": ("mcp_server_langgraph.mcp.websocket.rate_limiter", "get_user_rate_limiter"),
    "set_user_rate_limiter": ("mcp_server_langgraph.mcp.websocket.rate_limiter", "set_user_rate_limiter"),
    "create_user_rate_limiter": ("mcp_server_langgraph.mcp.websocket.rate_limiter", "create_user_rate_limiter"),
    "get_outbound_rate_limiter": ("mcp_server_langgraph.mcp.websocket.rate_limiter", "get_outbound_rate_limiter"),
    "set_outbound_rate_limiter": ("mcp_server_langgraph.mcp.websocket.rate_limiter", "set_outbound_rate_limiter"),
    "create_outbound_rate_limiter": ("mcp_server_langgraph.mcp.websocket.rate_limiter", "create_outbound_rate_limiter"),
    # Message handler classes
    "MCPMessageHandler": ("mcp_server_langgraph.mcp.message_handler", "MCPMessageHandler"),
    "AuthenticatedMCPHandler": ("mcp_server_langgraph.mcp.message_handler", "AuthenticatedMCPHandler"),
}


def __getattr__(name: str) -> Any:
    """
    Lazy import with deprecation warning for migrated classes.

    This allows backward-compatible imports while warning users to update.
    """
    if name in _DEPRECATION_MAP:
        module_path, attr_name = _DEPRECATION_MAP[name]
        warnings.warn(
            f"'{name}' is deprecated. Import from '{module_path}' instead. This module will be removed in v4.0 (2025-06-01).",
            DeprecationWarning,
            stacklevel=2,
        )
        import importlib

        module = importlib.import_module(module_path)
        return getattr(module, attr_name)

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


# =============================================================================
# Explicit __all__ for IDE support
# =============================================================================

__all__ = [
    # Router
    "mcp_websocket_router",
    # Constants
    "PARSE_ERROR",
    "INVALID_REQUEST",
    "METHOD_NOT_FOUND",
    "INVALID_PARAMS",
    "INTERNAL_ERROR",
    "MAX_CONNECTIONS_PER_USER",
    "MAX_MESSAGE_SIZE",
    "MAX_MESSAGES_PER_MINUTE",
    "IDLE_TIMEOUT_SECONDS",
    "MAX_SESSION_ID_LENGTH",
    "IDLE_CLEANUP_INTERVAL",
    # Security utilities
    "validate_message_size",
    "validate_session_id",
    "sanitize_session_id",
    "extract_websocket_token",
    "validate_websocket_token",
    "check_mcp_permission",
    "get_token_validator",
    "get_openfga_client",
    # Rate limiting (legacy)
    "MessageRateLimiter",
    # Validation
    "ValidationResult",
    "SecureMessageProcessor",
    # Mock metrics
    "Counter",
    "Gauge",
    "MCPWebSocketMetrics",
    # Cleanup functions
    "cleanup_idle_connections",
    "graceful_shutdown",
    "idle_cleanup_task",
    # Handler factories
    "create_handler_from_token",
    "create_anonymous_streaming_handler",
    # Lifespan
    "mcp_websocket_lifespan",
    # Private
    "_utc_now",
]
