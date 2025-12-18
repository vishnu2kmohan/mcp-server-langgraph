"""
MCP WebSocket Handler

MCP 2025-11-25 compliant WebSocket transport for real-time bidirectional communication.

This module provides:
- JSON-RPC 2.0 message handling over WebSocket
- MCP protocol methods: initialize, tools/*, resources/*, prompts/*
- Elicitation and sampling support
- Streaming extensions ($/streaming/*)
- Trace extensions ($/trace/*)

Usage:
    from mcp_server_langgraph.api.v1.mcp_websocket import mcp_websocket_router

    app.include_router(mcp_websocket_router, prefix="/api/v1")
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, UTC
from collections.abc import AsyncGenerator, AsyncIterator
from typing import Any, Callable, cast

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from mcp_server_langgraph.api.v1.mcp_bridge import ChatError, get_mcp_bridge

# JSON-RPC 2.0 error codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603

# Security limits
MAX_CONNECTIONS_PER_USER = 5
MAX_MESSAGE_SIZE = 1_000_000  # 1MB
MAX_MESSAGES_PER_MINUTE = 600
IDLE_TIMEOUT_SECONDS = 1800  # 30 minutes

logger = logging.getLogger(__name__)


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


class MessageRateLimiter:
    """
    Rate limiter for WebSocket messages using sliding window.

    Tracks message count within a time window and blocks messages
    when the limit is exceeded.
    """

    def __init__(self, max_messages: int, window_seconds: int) -> None:
        """
        Initialize the rate limiter.

        Args:
            max_messages: Maximum messages allowed in the window.
            window_seconds: Duration of the rate limit window in seconds.
        """
        self.max_messages = max_messages
        self.window_seconds = window_seconds
        self._message_count = 0
        self._window_start = _utc_now()

    def check_and_increment(self) -> bool:
        """
        Check if a message is allowed and increment the counter.

        Resets the window if it has expired.

        Returns:
            True if message is allowed, False if rate limit exceeded.
        """
        now = _utc_now()
        elapsed = (now - self._window_start).total_seconds()

        # Reset window if expired
        if elapsed >= self.window_seconds:
            self._window_start = now
            self._message_count = 0

        # Check if under limit
        if self._message_count >= self.max_messages:
            return False

        # Allow and increment
        self._message_count += 1
        return True

    def reset(self) -> None:
        """Reset the rate limiter."""
        self._message_count = 0
        self._window_start = _utc_now()


# =============================================================================
# Per-User Rate Limiting
# =============================================================================


class UserRateLimiterManager:
    """
    Manages rate limiting on a per-user basis across all their connections.

    This ensures a user can't bypass rate limits by opening multiple connections.
    """

    def __init__(self, max_messages: int, window_seconds: int) -> None:
        """
        Initialize the per-user rate limiter manager.

        Args:
            max_messages: Maximum messages allowed per user in the window.
            window_seconds: Duration of the rate limit window in seconds.
        """
        self.max_messages = max_messages
        self.window_seconds = window_seconds
        self._user_limiters: dict[str, MessageRateLimiter] = {}

    def check_and_increment(self, user_id: str) -> bool:
        """
        Check if a user's message is allowed and increment their counter.

        Args:
            user_id: User identifier (e.g., "user:alice" or "session:abc123").

        Returns:
            True if message is allowed, False if rate limit exceeded.
        """
        if user_id not in self._user_limiters:
            self._user_limiters[user_id] = MessageRateLimiter(
                max_messages=self.max_messages,
                window_seconds=self.window_seconds,
            )

        return self._user_limiters[user_id].check_and_increment()

    def get_user_count(self) -> int:
        """Get the number of users being tracked."""
        return len(self._user_limiters)

    def cleanup_expired(self) -> None:
        """
        Remove rate limiters for users whose windows have expired.

        This prevents memory growth from inactive users.
        """
        now = _utc_now()
        expired_users = []

        for user_id, limiter in self._user_limiters.items():
            elapsed = (now - limiter._window_start).total_seconds()
            if elapsed >= self.window_seconds:
                expired_users.append(user_id)

        for user_id in expired_users:
            del self._user_limiters[user_id]


# =============================================================================
# Outbound Rate Limiting for Streaming
# =============================================================================


class OutboundRateLimiter:
    """
    Rate limiter for outbound streaming notifications.

    Uses token bucket algorithm to limit notifications per second.
    Prevents overwhelming clients with too many rapid chunk notifications.
    """

    def __init__(self, max_notifications_per_second: int = 100) -> None:
        """
        Initialize the outbound rate limiter.

        Args:
            max_notifications_per_second: Maximum notifications allowed per second.
        """
        self.max_notifications_per_second = max_notifications_per_second
        self._tokens = float(max_notifications_per_second)
        self._last_refill = _utc_now()
        self._interval = 1.0 / max_notifications_per_second if max_notifications_per_second > 0 else 0.0

    async def check_and_wait(self) -> None:
        """
        Check if a notification can be sent, waiting if necessary.

        Uses token bucket algorithm to smooth out notification rate.
        """
        import asyncio

        now = _utc_now()
        elapsed = (now - self._last_refill).total_seconds()

        # Refill tokens based on elapsed time
        self._tokens = min(
            float(self.max_notifications_per_second),
            self._tokens + elapsed * self.max_notifications_per_second,
        )
        self._last_refill = now

        # If no tokens available, wait
        if self._tokens < 1.0:
            wait_time = (1.0 - self._tokens) / self.max_notifications_per_second
            await asyncio.sleep(wait_time)
            self._tokens = 1.0
            self._last_refill = _utc_now()

        # Consume a token
        self._tokens -= 1.0


# =============================================================================
# Session ID Validation
# =============================================================================

# Maximum length for session IDs
MAX_SESSION_ID_LENGTH = 128

# Valid characters for session IDs (alphanumeric, hyphens, underscores)
import re

_SESSION_ID_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$")


def validate_session_id(session_id: str) -> bool:
    """
    Validate a session ID for safety and correctness.

    Args:
        session_id: The session ID to validate.

    Returns:
        True if valid, False if invalid.
    """
    # Check for empty or whitespace
    if not session_id or not session_id.strip():
        return False

    # Check length
    if len(session_id) > MAX_SESSION_ID_LENGTH:
        return False

    # Check for null bytes
    if "\x00" in session_id:
        return False

    # Check pattern (alphanumeric, hyphens, underscores only)
    return bool(_SESSION_ID_PATTERN.match(session_id))


def sanitize_session_id(session_id: str) -> str:
    """
    Sanitize a session ID by removing unsafe characters.

    Args:
        session_id: The session ID to sanitize.

    Returns:
        Sanitized session ID with only safe characters.
    """
    # Remove null bytes
    session_id = session_id.replace("\x00", "")

    # Keep only alphanumeric, hyphens, and underscores
    sanitized = re.sub(r"[^a-zA-Z0-9_-]", "", session_id)

    # Ensure it starts with alphanumeric
    if sanitized and not sanitized[0].isalnum():
        sanitized = "s" + sanitized

    # Truncate to max length
    return sanitized[:MAX_SESSION_ID_LENGTH]


# =============================================================================
# Secure Message Processor
# =============================================================================


@dataclass
class ValidationResult:
    """Result of message validation."""

    is_valid: bool
    error_message: str = ""
    error_code: int = 0


class SecureMessageProcessor:
    """
    Secure message processor that enforces all security checks.

    Combines rate limiting, size validation, activity tracking, and metrics.
    """

    def __init__(
        self,
        session_id: str,
        user_id: str | None = None,
        rate_limiter: UserRateLimiterManager | None = None,
        connection_manager: ConnectionManager | None = None,
        metrics: MCPWebSocketMetrics | None = None,
        max_message_size: int | None = None,
    ) -> None:
        """
        Initialize the secure message processor.

        Args:
            session_id: The session identifier.
            user_id: Optional user identifier for authenticated connections.
            rate_limiter: Optional per-user rate limiter.
            connection_manager: Optional connection manager for activity tracking.
            metrics: Optional metrics recorder.
            max_message_size: Optional max message size limit. Defaults to MAX_MESSAGE_SIZE.
        """
        self.session_id = session_id
        self.user_id = user_id
        self.rate_limiter = rate_limiter
        self.connection_manager = connection_manager
        self.metrics = metrics
        self.max_message_size = max_message_size if max_message_size is not None else MAX_MESSAGE_SIZE

    def validate_incoming(self, message: str) -> ValidationResult:
        """
        Validate an incoming message against all security checks.

        Args:
            message: The raw message string.

        Returns:
            ValidationResult indicating if the message is valid.
        """
        # Check message size
        if not validate_message_size(message, max_size=self.max_message_size):
            # Record metric for message size exceeded
            if self.metrics:
                identifier = self.user_id or f"session:{self.session_id}"
                self.metrics.record_message_size_exceeded(user_id=identifier)
            return ValidationResult(
                is_valid=False,
                error_message=f"Message size exceeds limit of {self.max_message_size} bytes",
                error_code=-32600,  # Invalid Request
            )

        # Check rate limit
        if self.rate_limiter:
            identifier = self.user_id or f"session:{self.session_id}"
            if not self.rate_limiter.check_and_increment(identifier):
                if self.metrics:
                    self.metrics.record_rate_limit_exceeded(identifier)
                return ValidationResult(
                    is_valid=False,
                    error_message="Rate limit exceeded",
                    error_code=-32000,  # Server error
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
# Idle Connection Cleanup
# =============================================================================

# Cleanup interval in seconds
IDLE_CLEANUP_INTERVAL = 60


async def cleanup_idle_connections(manager: ConnectionManager) -> int:
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


async def idle_cleanup_task(manager: ConnectionManager) -> None:
    """
    Background task that periodically cleans up idle connections.

    Args:
        manager: The connection manager to clean up.
    """
    import asyncio

    while True:
        try:
            await asyncio.sleep(IDLE_CLEANUP_INTERVAL)
            closed = await cleanup_idle_connections(manager)
            if closed > 0:
                logger.info(f"Idle cleanup: closed {closed} connections")
        except asyncio.CancelledError:
            logger.info("Idle cleanup task cancelled")
            break
        except Exception:
            logger.exception("Error in idle cleanup task")


# =============================================================================
# Graceful Shutdown
# =============================================================================


async def graceful_shutdown(manager: ConnectionManager) -> None:
    """
    Gracefully close all WebSocket connections.

    Uses WebSocket close code 1001 (Going Away) to indicate server shutdown.

    Args:
        manager: The connection manager to shut down.
    """
    # Get all session IDs (copy to avoid modification during iteration)
    session_ids = list(manager._connections.keys())

    for session_id in session_ids:
        if session_id in manager._connections:
            conn_info = manager._connections[session_id]
            try:
                await conn_info.websocket.close(
                    code=1001,
                    reason="Server shutting down",
                )
                logger.info(
                    f"Gracefully closed connection: {session_id}",
                    extra={"session_id": session_id, "user_id": conn_info.user_id},
                )
            except Exception as e:
                logger.warning(
                    f"Error closing connection {session_id} during shutdown: {e}",
                    extra={"session_id": session_id, "error": str(e)},
                )
            finally:
                manager.disconnect(session_id)


# =============================================================================
# OpenTelemetry Metrics
# =============================================================================


class OTelMCPMetrics:
    """
    OpenTelemetry-compatible metrics for MCP WebSocket.

    Provides counters, gauges, and histograms for observability.
    """

    def __init__(self) -> None:
        """Initialize OpenTelemetry metrics."""
        try:
            from opentelemetry.metrics import get_meter

            meter = get_meter("mcp_websocket")

            # Counters
            self._connections_total = meter.create_counter(
                "mcp_websocket_connections_total",
                description="Total number of MCP WebSocket connections",
            )
            self._messages_received = meter.create_counter(
                "mcp_websocket_messages_received_total",
                description="Total messages received",
            )
            self._messages_sent = meter.create_counter(
                "mcp_websocket_messages_sent_total",
                description="Total messages sent",
            )
            self._rate_limit_exceeded = meter.create_counter(
                "mcp_websocket_rate_limit_exceeded_total",
                description="Rate limit exceeded events",
            )

            # Histogram for latency
            self._message_latency = meter.create_histogram(
                "mcp_websocket_message_latency_ms",
                description="Message processing latency in milliseconds",
            )

            # Streaming metrics
            self._stream_chunks_total = meter.create_counter(
                "mcp_websocket_stream_chunks_total",
                description="Total streaming chunks sent",
            )
            self._stream_chunk_sizes = meter.create_histogram(
                "mcp_websocket_stream_chunk_size_bytes",
                description="Size of streaming chunks in bytes",
            )

            # Track active connections count
            self._active_connections = 0
            self._active_streams = 0
            self._total_chunks = 0
            self.active_connections_gauge = meter.create_observable_gauge(
                "mcp_websocket_active_connections",
                callbacks=[self._get_active_connections],
                description="Current number of active connections",
            )

            self._otel_available = True
        except ImportError:
            # OpenTelemetry not installed, use fallback
            self._otel_available = False
            self._active_connections = 0
            self._active_streams = 0
            self._total_chunks = 0
            self._stream_chunks_total: Any = None  # type: ignore[assignment,no-redef]
            self._stream_chunk_sizes: Any = None  # type: ignore[assignment,no-redef]
            self.active_connections_gauge: Any = None  # type: ignore[assignment,no-redef]
            logger.debug("OpenTelemetry not available, using fallback metrics")

    def _get_active_connections(self, options: Any) -> Any:
        """Callback for observable gauge."""
        if self._otel_available:
            from opentelemetry.metrics import Observation

            yield Observation(self._active_connections)

    def record_connection(self) -> None:
        """Record a new connection."""
        self._active_connections += 1
        if self._otel_available:
            self._connections_total.add(1)

    def record_disconnect(self) -> None:
        """Record a disconnection."""
        self._active_connections = max(0, self._active_connections - 1)

    def record_message_received(self, method: str = "", user_id: str = "") -> None:
        """Record a received message with attributes."""
        if self._otel_available:
            self._messages_received.add(1, {"method": method, "user_id": user_id})

    def record_message_sent(self, method: str = "", user_id: str = "") -> None:
        """Record a sent message with attributes."""
        if self._otel_available:
            self._messages_sent.add(1, {"method": method, "user_id": user_id})

    def record_rate_limit_exceeded(self, user_id: str = "") -> None:
        """Record rate limit exceeded event."""
        if self._otel_available:
            self._rate_limit_exceeded.add(1, {"user_id": user_id})

    def record_connection_rejected(self, user_id: str = "", reason: str = "") -> None:
        """Record connection rejected event."""
        if self._otel_available:
            # Use the existing connections counter with rejection attribute
            self._connections_total.add(1, {"user_id": user_id, "status": "rejected", "reason": reason})

    def record_message_size_exceeded(self, user_id: str = "") -> None:
        """Record message size exceeded event."""
        if self._otel_available:
            self._messages_received.add(1, {"user_id": user_id, "status": "rejected", "reason": "size_exceeded"})

    def record_message_latency(self, method: str = "", latency_ms: float = 0.0) -> None:
        """Record message processing latency."""
        if self._otel_available:
            self._message_latency.record(latency_ms, {"method": method})

    def record_stream_start(self, stream_id: str = "") -> None:
        """
        Record the start of a streaming operation.

        Args:
            stream_id: Unique identifier for the stream.
        """
        self._active_streams += 1

    def record_stream_chunk(self, stream_id: str = "", chunk_size: int = 0) -> None:
        """
        Record a chunk being sent in a stream.

        Args:
            stream_id: Unique identifier for the stream.
            chunk_size: Size of the chunk in bytes.
        """
        self._total_chunks += 1
        if self._otel_available:
            self._stream_chunks_total.add(1, {"stream_id": stream_id})
            self._stream_chunk_sizes.record(chunk_size, {"stream_id": stream_id})

    def record_stream_end(
        self,
        stream_id: str = "",
        chunks: int = 0,
        total_bytes: int = 0,
        duration_ms: float = 0.0,
    ) -> None:
        """
        Record the end of a streaming operation.

        Args:
            stream_id: Unique identifier for the stream.
            chunks: Total number of chunks sent.
            total_bytes: Total bytes sent.
            duration_ms: Total duration in milliseconds.
        """
        self._active_streams = max(0, self._active_streams - 1)


# =============================================================================
# FastAPI Lifespan
# =============================================================================


from contextlib import asynccontextmanager
import asyncio


@asynccontextmanager
async def mcp_websocket_lifespan(app: Any) -> AsyncGenerator[dict[str, Any], None]:
    """
    FastAPI lifespan context manager for MCP WebSocket.

    Starts background cleanup task and handles graceful shutdown.

    Args:
        app: The FastAPI application.

    Yields:
        State dict with cleanup task reference.
    """
    # Start idle cleanup task
    cleanup_task_handle = asyncio.create_task(idle_cleanup_task(connection_manager))

    logger.info("MCP WebSocket lifespan started, cleanup task running")

    state = {"cleanup_task": cleanup_task_handle}

    try:
        yield state
    finally:
        # Cancel cleanup task
        cleanup_task_handle.cancel()
        try:
            await cleanup_task_handle
        except asyncio.CancelledError:
            pass

        # Graceful shutdown
        await graceful_shutdown(connection_manager)

        logger.info("MCP WebSocket lifespan ended, all connections closed")


# =============================================================================
# Lifecycle Manager
# =============================================================================


class MCPWebSocketLifecycleManager:
    """
    Manages MCP WebSocket lifecycle for integration with FastAPI app.

    Provides startup/shutdown methods that can be called from the main
    app lifespan to start background tasks and handle graceful shutdown.

    Usage:
        manager = get_mcp_lifecycle_manager()
        await manager.startup()  # In app lifespan startup
        await manager.shutdown()  # In app lifespan shutdown
    """

    def __init__(
        self,
        cleanup_interval: float = IDLE_CLEANUP_INTERVAL,
        metrics_cleanup_interval: float = 300,  # 5 minutes default
        streaming_enabled: bool = True,
        max_age_seconds: float = 3600,  # 1 hour default
    ) -> None:
        """
        Initialize the lifecycle manager.

        Args:
            cleanup_interval: Interval in seconds between idle connection cleanup runs.
            metrics_cleanup_interval: Interval in seconds between stream metrics cleanup runs.
            streaming_enabled: Whether streaming is enabled. If False, cleanup tasks won't start.
            max_age_seconds: Maximum age in seconds for completed streams before cleanup.
        """
        self.cleanup_interval = cleanup_interval
        self.metrics_cleanup_interval = metrics_cleanup_interval
        self.streaming_enabled = streaming_enabled
        self.max_age_seconds = max_age_seconds
        self.cleanup_task: asyncio.Task[None] | None = None
        self.metrics_cleanup_task: asyncio.Task[None] | None = None
        self._started = False

    async def startup(self) -> None:
        """
        Start MCP WebSocket lifecycle management.

        Starts the idle connection cleanup and stream metrics cleanup background tasks.
        Idempotent - safe to call multiple times.

        If streaming_enabled is False, skips starting cleanup tasks.
        """
        if self._started:
            logger.debug("MCP WebSocket lifecycle already started")
            return

        # Skip starting cleanup tasks if streaming is disabled
        if not self.streaming_enabled:
            logger.info("Streaming disabled, skipping cleanup task startup")
            self._started = True
            return

        # Start idle cleanup task with custom interval
        async def _cleanup_loop() -> None:
            while True:
                try:
                    await asyncio.sleep(self.cleanup_interval)
                    closed = await cleanup_idle_connections(connection_manager)
                    if closed > 0:
                        logger.info(f"Idle cleanup: closed {closed} connections")
                except asyncio.CancelledError:
                    logger.info("Idle cleanup task cancelled")
                    break
                except Exception:
                    logger.exception("Error in idle cleanup task")

        # Start metrics cleanup task
        async def _metrics_cleanup_loop() -> None:
            while True:
                try:
                    await asyncio.sleep(self.metrics_cleanup_interval)
                    removed = await self.cleanup_stream_metrics()
                    if removed > 0:
                        logger.info(f"Metrics cleanup: removed {removed} old streams")
                except asyncio.CancelledError:
                    logger.info("Metrics cleanup task cancelled")
                    break
                except Exception:
                    logger.exception("Error in metrics cleanup task")

        self.cleanup_task = asyncio.create_task(_cleanup_loop())
        self.metrics_cleanup_task = asyncio.create_task(_metrics_cleanup_loop())
        self._started = True
        logger.info("MCP WebSocket lifecycle started, cleanup tasks running")

    async def shutdown(self) -> None:
        """
        Stop MCP WebSocket lifecycle management.

        Cancels cleanup tasks, cleans up all stream metrics, and calls graceful shutdown.
        Idempotent - safe to call multiple times.
        """
        if not self._started:
            logger.debug("MCP WebSocket lifecycle not started, skipping shutdown")
            return

        # Cancel idle cleanup task
        if self.cleanup_task and not self.cleanup_task.done():
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass

        # Cancel metrics cleanup task
        if self.metrics_cleanup_task and not self.metrics_cleanup_task.done():
            self.metrics_cleanup_task.cancel()
            try:
                await self.metrics_cleanup_task
            except asyncio.CancelledError:
                pass

        # Clean up all completed stream metrics on shutdown
        await self.cleanup_stream_metrics(max_age_seconds=0)

        # Graceful shutdown
        await graceful_shutdown(connection_manager)

        self._started = False
        logger.info("MCP WebSocket lifecycle shutdown complete")

    async def cleanup_stream_metrics(self, max_age_seconds: float | None = None) -> int:
        """
        Clean up old stream metrics from the global streaming_metrics_collector.

        Removes completed streams older than max_age_seconds to prevent memory growth.
        Active streams are never removed.

        Args:
            max_age_seconds: Maximum age in seconds for completed streams.
                            Defaults to self.max_age_seconds if not provided.

        Returns:
            Number of streams removed.
        """
        age = max_age_seconds if max_age_seconds is not None else self.max_age_seconds
        removed = streaming_metrics_collector.cleanup_old_streams(age)
        if removed > 0:
            logger.debug(f"Cleaned up {removed} old stream metrics")
        return removed


# Global lifecycle manager singleton
_lifecycle_manager: MCPWebSocketLifecycleManager | None = None


def get_mcp_lifecycle_manager() -> MCPWebSocketLifecycleManager:
    """
    Get the global MCP WebSocket lifecycle manager singleton.

    Returns:
        The global MCPWebSocketLifecycleManager instance.
    """
    global _lifecycle_manager
    if _lifecycle_manager is None:
        _lifecycle_manager = MCPWebSocketLifecycleManager()
    return _lifecycle_manager


def create_mcp_lifecycle_manager(
    streaming_settings: Any | None = None,
) -> MCPWebSocketLifecycleManager:
    """
    Create a new MCPWebSocketLifecycleManager with optional StreamingSettings.

    Factory function that allows configuration injection for lifecycle manager.
    Does NOT modify the global singleton.

    Args:
        streaming_settings: Optional StreamingSettings instance with cleanup intervals.

    Returns:
        A new MCPWebSocketLifecycleManager instance with configured intervals.
    """
    if streaming_settings is None:
        return MCPWebSocketLifecycleManager()

    return MCPWebSocketLifecycleManager(
        cleanup_interval=streaming_settings.streaming_idle_cleanup_interval,
        metrics_cleanup_interval=streaming_settings.streaming_metrics_cleanup_interval,
        streaming_enabled=streaming_settings.streaming_enabled,
        max_age_seconds=streaming_settings.streaming_max_age_seconds,
    )


def set_mcp_lifecycle_manager(manager: MCPWebSocketLifecycleManager) -> None:
    """
    Set the global MCP WebSocket lifecycle manager singleton.

    Used by bootstrap to inject a configured manager.

    Args:
        manager: The lifecycle manager instance to set as global singleton.
    """
    global _lifecycle_manager
    _lifecycle_manager = manager


# Global per-user rate limiter
user_rate_limiter = UserRateLimiterManager(
    max_messages=MAX_MESSAGES_PER_MINUTE,
    window_seconds=60,
)


def get_user_rate_limiter() -> UserRateLimiterManager:
    """
    Get the global user rate limiter instance.

    Returns:
        The global UserRateLimiterManager instance.
    """
    return user_rate_limiter


def set_user_rate_limiter(limiter: UserRateLimiterManager) -> None:
    """
    Set the global user rate limiter instance.

    Used by bootstrap to inject a configured limiter.

    Args:
        limiter: The rate limiter instance to set as global singleton.
    """
    global user_rate_limiter
    user_rate_limiter = limiter


def create_user_rate_limiter(
    streaming_settings: Any | None = None,
) -> UserRateLimiterManager:
    """
    Create a UserRateLimiterManager with optional StreamingSettings.

    Factory function that allows configuration injection for rate limiter.

    Args:
        streaming_settings: Optional StreamingSettings instance with rate limit config.

    Returns:
        A UserRateLimiterManager instance with configured rate limit.
    """
    if streaming_settings is None:
        return UserRateLimiterManager(
            max_messages=MAX_MESSAGES_PER_MINUTE,
            window_seconds=60,
        )

    return UserRateLimiterManager(
        max_messages=streaming_settings.streaming_max_messages_per_minute,
        window_seconds=60,
    )


# Global OpenTelemetry metrics
otel_metrics = OTelMCPMetrics()

# Global streaming enabled flag
_streaming_enabled: bool = True


def is_streaming_enabled() -> bool:
    """
    Check if streaming is globally enabled.

    Returns:
        True if streaming is enabled, False otherwise.
    """
    return _streaming_enabled


def set_streaming_enabled(enabled: bool) -> None:
    """
    Set the global streaming enabled flag.

    Used by bootstrap to configure streaming based on settings.

    Args:
        enabled: Whether streaming should be enabled.
    """
    global _streaming_enabled
    _streaming_enabled = enabled


# Global streaming max chunk size (None = unlimited)
_streaming_max_chunk_size: int | None = None


def get_streaming_max_chunk_size() -> int | None:
    """
    Get the global streaming max chunk size.

    Returns:
        The configured max chunk size, or None if unlimited.
    """
    return _streaming_max_chunk_size


def set_streaming_max_chunk_size(max_chunk_size: int | None) -> None:
    """
    Set the global streaming max chunk size.

    Used by bootstrap to configure chunk size based on settings.

    Args:
        max_chunk_size: The max chunk size in bytes, or None for unlimited.
    """
    global _streaming_max_chunk_size
    _streaming_max_chunk_size = max_chunk_size


# Global outbound rate limiter (None = no rate limiting)
_outbound_rate_limiter: OutboundRateLimiter | None = None


def get_outbound_rate_limiter() -> OutboundRateLimiter | None:
    """
    Get the global outbound rate limiter.

    Returns:
        The configured OutboundRateLimiter, or None if not configured.
    """
    return _outbound_rate_limiter


def set_outbound_rate_limiter(limiter: OutboundRateLimiter | None) -> None:
    """
    Set the global outbound rate limiter.

    Used by bootstrap to configure outbound rate limiting based on settings.

    Args:
        limiter: The OutboundRateLimiter instance, or None to disable.
    """
    global _outbound_rate_limiter
    _outbound_rate_limiter = limiter


def create_outbound_rate_limiter(
    streaming_settings: Any | None = None,
) -> OutboundRateLimiter | None:
    """
    Create an OutboundRateLimiter with optional StreamingSettings.

    Factory function that allows configuration injection for rate limiter.

    Args:
        streaming_settings: Optional StreamingSettings instance with rate limit config.

    Returns:
        An OutboundRateLimiter instance, or None if streaming is disabled.
    """
    if streaming_settings is None:
        return OutboundRateLimiter(max_notifications_per_second=100)

    if not streaming_settings.streaming_enabled:
        return None

    return OutboundRateLimiter(
        max_notifications_per_second=streaming_settings.streaming_max_notifications_per_second,
    )


def extract_websocket_token(websocket: WebSocket) -> str | None:
    """
    Extract authentication token from WebSocket connection.

    Checks query params first (for browsers), then Authorization header.

    Args:
        websocket: The WebSocket connection.

    Returns:
        The extracted token, or None if not found.
    """
    # Check query params first (common for browser WebSocket)
    token = websocket.query_params.get("token")
    if token:
        return token

    # Check Authorization header
    auth_header = websocket.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]  # Remove "Bearer " prefix

    return None


def _utc_now() -> datetime:
    """Return current UTC time with timezone awareness."""
    return datetime.now(UTC)


@dataclass
class ConnectionInfo:
    """Metadata about a WebSocket connection."""

    websocket: WebSocket
    session_id: str
    user_id: str | None = None
    roles: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=_utc_now)
    last_activity: datetime = field(default_factory=_utc_now)
    message_count: int = 0


def update_connection_activity(conn_info: ConnectionInfo) -> None:
    """
    Update the last activity timestamp for a connection.

    Args:
        conn_info: The connection info to update.
    """
    conn_info.last_activity = _utc_now()


def is_connection_idle(conn_info: ConnectionInfo, timeout_seconds: int | None = None) -> bool:
    """
    Check if a connection has exceeded the idle timeout.

    Args:
        conn_info: The connection info to check.
        timeout_seconds: Optional custom timeout. Defaults to IDLE_TIMEOUT_SECONDS if not provided.

    Returns:
        True if the connection is idle (exceeded timeout), False otherwise.
    """
    now = _utc_now()
    elapsed = (now - conn_info.last_activity).total_seconds()
    timeout = timeout_seconds if timeout_seconds is not None else IDLE_TIMEOUT_SECONDS
    return elapsed > timeout


class Counter:
    """Simple thread-safe counter for metrics."""

    def __init__(self, name: str, description: str = "") -> None:
        """Initialize the counter."""
        self.name = name
        self.description = description
        self._value = 0
        self._labels: dict[str, int] = {}

    def inc(self, value: int = 1, labels: dict[str, str] | None = None) -> None:
        """Increment the counter."""
        self._value += value  # Always increment total
        if labels:
            key = str(sorted(labels.items()))
            self._labels[key] = self._labels.get(key, 0) + value

    def get(self) -> int:
        """Get the counter value (total across all labels)."""
        return self._value


class Gauge:
    """Simple thread-safe gauge for metrics."""

    def __init__(self, name: str, description: str = "") -> None:
        """Initialize the gauge."""
        self.name = name
        self.description = description
        self._value = 0

    def inc(self, value: int = 1) -> None:
        """Increment the gauge."""
        self._value += value

    def dec(self, value: int = 1) -> None:
        """Decrement the gauge."""
        self._value -= value

    def set(self, value: int) -> None:
        """Set the gauge value."""
        self._value = value

    def get(self) -> int:
        """Get the gauge value."""
        return self._value


class MCPWebSocketMetrics:
    """
    Observability metrics for MCP WebSocket connections.

    Tracks connection events, message counts, rate limiting, and errors.
    Designed to be compatible with OpenTelemetry/Prometheus metrics.
    """

    def __init__(self) -> None:
        """Initialize the metrics."""
        # Connection metrics
        self.active_connections = Gauge(
            "mcp_websocket_active_connections",
            "Number of active MCP WebSocket connections",
        )
        self.total_connections = Counter(
            "mcp_websocket_total_connections",
            "Total number of MCP WebSocket connections since startup",
        )

        # Message metrics
        self.messages_received = Counter(
            "mcp_websocket_messages_received",
            "Total messages received by MCP WebSocket",
        )
        self.messages_sent = Counter(
            "mcp_websocket_messages_sent",
            "Total messages sent by MCP WebSocket",
        )

        # Rate limiting metrics
        self.rate_limit_exceeded = Counter(
            "mcp_websocket_rate_limit_exceeded",
            "Number of times rate limit was exceeded",
        )

        # Connection rejection metrics
        self.connections_rejected = Counter(
            "mcp_websocket_connections_rejected",
            "Number of connections rejected due to limits",
        )

        # Message size violation metrics
        self.message_size_exceeded = Counter(
            "mcp_websocket_message_size_exceeded",
            "Number of messages rejected due to size limit",
        )

        # Error metrics
        self.errors = Counter(
            "mcp_websocket_errors",
            "Number of errors in MCP WebSocket handling",
        )

    def record_connection(self) -> None:
        """Record a new connection."""
        self.active_connections.inc()
        self.total_connections.inc()

    def record_disconnect(self) -> None:
        """Record a disconnection."""
        self.active_connections.dec()

    def record_message_received(self, method: str) -> None:
        """
        Record a received message.

        Args:
            method: The MCP method name.
        """
        self.messages_received.inc(labels={"method": method})

    def record_message_sent(self, method: str) -> None:
        """
        Record a sent message.

        Args:
            method: The MCP method name.
        """
        self.messages_sent.inc(labels={"method": method})

    def record_rate_limit_exceeded(self, user_id: str) -> None:
        """
        Record a rate limit exceeded event.

        Args:
            user_id: The user who exceeded the rate limit.
        """
        self.rate_limit_exceeded.inc(labels={"user_id": user_id})

    def record_connection_rejected(self, user_id: str, reason: str) -> None:
        """
        Record a connection rejection event.

        Args:
            user_id: The user whose connection was rejected.
            reason: The reason for rejection (e.g., "connection_limit").
        """
        self.connections_rejected.inc(labels={"user_id": user_id, "reason": reason})

    def record_message_size_exceeded(self, user_id: str) -> None:
        """
        Record a message size exceeded event.

        Args:
            user_id: The user who sent the oversized message.
        """
        self.message_size_exceeded.inc(labels={"user_id": user_id})

    def record_error(self, error_type: str) -> None:
        """
        Record an error event.

        Args:
            error_type: The type of error.
        """
        self.errors.inc(labels={"error_type": error_type})


# Global metrics instance
mcp_websocket_metrics = MCPWebSocketMetrics()


@dataclass
class StreamStats:
    """Statistics for a single stream."""

    chunk_count: int = 0
    total_bytes: int = 0
    start_time: datetime | None = None
    end_time: datetime | None = None

    @property
    def avg_chunk_size(self) -> float:
        """Calculate average chunk size."""
        if self.chunk_count == 0:
            return 0.0
        return self.total_bytes / self.chunk_count

    @property
    def duration_ms(self) -> float:
        """Calculate duration in milliseconds."""
        if self.start_time is None or self.end_time is None:
            return 0.0
        return (self.end_time - self.start_time).total_seconds() * 1000


class StreamingMetricsCollector:
    """
    Collects metrics for streaming tool calls.

    Tracks chunks per stream, total bytes, average chunk size,
    and stream duration for observability.
    """

    def __init__(self) -> None:
        """Initialize the streaming metrics collector."""
        self._streams: dict[str, StreamStats] = {}

    def record_stream_start(self, stream_id: str) -> None:
        """
        Record the start of a stream.

        Args:
            stream_id: Unique identifier for the stream.
        """
        self._streams[stream_id] = StreamStats(start_time=_utc_now())

    def record_chunk(self, stream_id: str, chunk_size: int) -> None:
        """
        Record a chunk being sent.

        Args:
            stream_id: Unique identifier for the stream.
            chunk_size: Size of the chunk in bytes.
        """
        if stream_id not in self._streams:
            self._streams[stream_id] = StreamStats()
        stats = self._streams[stream_id]
        stats.chunk_count += 1
        stats.total_bytes += chunk_size

    def record_stream_end(self, stream_id: str) -> None:
        """
        Record the end of a stream.

        Args:
            stream_id: Unique identifier for the stream.
        """
        if stream_id in self._streams:
            self._streams[stream_id].end_time = _utc_now()

    def is_stream_active(self, stream_id: str) -> bool:
        """
        Check if a stream is active (started but not ended).

        Args:
            stream_id: Unique identifier for the stream.

        Returns:
            True if stream is active, False otherwise.
        """
        if stream_id not in self._streams:
            return False
        stats = self._streams[stream_id]
        return stats.start_time is not None and stats.end_time is None

    def get_stream_stats(self, stream_id: str) -> dict[str, Any]:
        """
        Get statistics for a specific stream.

        Args:
            stream_id: Unique identifier for the stream.

        Returns:
            Dictionary with chunk_count, total_bytes, avg_chunk_size, duration_ms.
        """
        if stream_id not in self._streams:
            return {
                "chunk_count": 0,
                "total_bytes": 0,
                "avg_chunk_size": 0.0,
                "duration_ms": 0.0,
            }
        stats = self._streams[stream_id]
        return {
            "chunk_count": stats.chunk_count,
            "total_bytes": stats.total_bytes,
            "avg_chunk_size": stats.avg_chunk_size,
            "duration_ms": stats.duration_ms,
        }

    def get_aggregate_stats(self) -> dict[str, Any]:
        """
        Get aggregate statistics across all streams.

        Returns:
            Dictionary with total_streams, total_chunks, total_bytes.
        """
        total_streams = len(self._streams)
        total_chunks = sum(s.chunk_count for s in self._streams.values())
        total_bytes = sum(s.total_bytes for s in self._streams.values())

        return {
            "total_streams": total_streams,
            "total_chunks": total_chunks,
            "total_bytes": total_bytes,
        }

    def cleanup_old_streams(self, max_age_seconds: float) -> int:
        """
        Remove completed streams older than max_age_seconds.

        Active streams (without end_time) are never removed.

        Args:
            max_age_seconds: Maximum age in seconds for completed streams.
                            Use 0 to remove all completed streams.

        Returns:
            Number of streams removed.
        """
        now = _utc_now()
        to_remove: list[str] = []

        for stream_id, stats in self._streams.items():
            # Skip active streams (no end_time)
            if stats.end_time is None:
                continue

            # Check age
            age_seconds = (now - stats.end_time).total_seconds()
            if age_seconds >= max_age_seconds:
                to_remove.append(stream_id)

        for stream_id in to_remove:
            del self._streams[stream_id]

        return len(to_remove)


# Global streaming metrics collector instance
streaming_metrics_collector = StreamingMetricsCollector()


class MCPMessageHandler:
    """
    Handler for MCP protocol messages over WebSocket.

    Supports all MCP 2025-11-25 methods including:
    - initialize: Protocol handshake
    - tools/list, tools/call: Tool operations
    - resources/list, resources/read: Resource operations
    - prompts/list, prompts/get: Prompt operations
    - elicitation/*, sampling/*: Advanced features
    """

    def __init__(self) -> None:
        """Initialize the message handler."""
        self.protocol_version = "2025-11-25"
        self.server_info = {
            "name": "langgraph-agent",
            "version": "2.8.0",
            "description": "AI Agent with fine-grained authorization, LangGraph workflows, and multi-LLM support",
        }
        self.capabilities = {
            "tools": {"listChanged": False},
            "resources": {"listChanged": False, "subscribe": True},
            "prompts": {"listChanged": False},
            "elicitation": {},
            "sampling": {},
            "logging": {},
            "streaming": {
                "supported": True,
                "textStreaming": True,
                "progressiveRendering": True,
                "chunkedResponses": True,
            },
        }

        # Standard tools available
        self._tools = [
            {
                "name": "langgraph-run",
                "description": "Execute the LangGraph agent with a query",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The query to process",
                        },
                        "session_id": {
                            "type": "string",
                            "description": "Optional session ID for context",
                        },
                    },
                    "required": ["query"],
                },
            }
        ]

        # Standard prompts available
        self._prompts = [
            {
                "name": "code_review",
                "description": "Review code for issues and improvements",
                "arguments": [
                    {"name": "code", "required": True, "description": "Code to review"},
                    {"name": "language", "required": False, "description": "Programming language"},
                ],
            },
            {
                "name": "summarize_conversation",
                "description": "Summarize the current conversation",
                "arguments": [],
            },
            {
                "name": "debug_error",
                "description": "Help debug an error",
                "arguments": [
                    {"name": "error", "required": True, "description": "Error message"},
                    {"name": "context", "required": False, "description": "Additional context"},
                ],
            },
        ]

        # Standard resources available
        self._resources = [
            {
                "uri": "config://playground/default",
                "name": "Default Configuration",
                "mimeType": "application/json",
                "description": "Default playground configuration",
            }
        ]

    def handle_sync(self, message: dict[str, Any]) -> dict[str, Any]:
        """
        Handle an MCP message synchronously.

        Used for simple methods that don't require async operations.
        """
        # Validate JSON-RPC 2.0 structure
        if "method" not in message:
            return self._error_response(message.get("id"), INVALID_REQUEST, "Missing method field")

        method = message.get("method")
        message_id = message.get("id")
        params = message.get("params", {})

        # Handle methods
        if method == "initialize":
            return self._handle_initialize(message_id, params)
        else:
            # Unknown method
            return self._error_response(message_id, METHOD_NOT_FOUND, f"Method not found: {method}")

    async def handle(self, message: dict[str, Any]) -> dict[str, Any]:
        """
        Handle an MCP message asynchronously.

        Supports all MCP methods including async operations.
        """
        # Validate JSON-RPC 2.0 structure
        if "method" not in message:
            return self._error_response(message.get("id"), INVALID_REQUEST, "Missing method field")

        method = cast(str, message.get("method"))  # Already validated above
        message_id = message.get("id")
        params = message.get("params", {})

        # Route to appropriate handler - sync handlers
        sync_handlers: dict[str, Callable[[Any, Any], dict[str, Any]]] = {
            "initialize": self._handle_initialize,
            "tools/list": self._handle_tools_list,
            "resources/list": self._handle_resources_list,
            "resources/read": self._handle_resources_read,
            "prompts/list": self._handle_prompts_list,
            "prompts/get": self._handle_prompts_get,
        }

        # Async handler for tools/call
        if method == "tools/call":
            return await self._handle_tools_call(message_id, params)

        sync_handler = sync_handlers.get(method)
        if sync_handler:
            return sync_handler(message_id, params)
        else:
            return self._error_response(message_id, METHOD_NOT_FOUND, f"Method not found: {method}")

    def handle_parse_error(self) -> dict[str, Any]:
        """Return a parse error response for invalid JSON."""
        return self._error_response(None, PARSE_ERROR, "Parse error")

    def _error_response(self, message_id: Any, code: int, message: str, data: Any | None = None) -> dict[str, Any]:
        """Create a JSON-RPC 2.0 error response."""
        error: dict[str, Any] = {"code": code, "message": message}
        if data is not None:
            error["data"] = data
        return {"jsonrpc": "2.0", "id": message_id, "error": error}

    def _success_response(self, message_id: Any, result: Any) -> dict[str, Any]:
        """Create a JSON-RPC 2.0 success response."""
        return {"jsonrpc": "2.0", "id": message_id, "result": result}

    def _handle_initialize(self, message_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        """Handle initialize request."""
        return self._success_response(
            message_id,
            {
                "protocolVersion": self.protocol_version,
                "serverInfo": self.server_info,
                "capabilities": self.capabilities,
            },
        )

    def _handle_tools_list(self, message_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        """Handle tools/list request."""
        return self._success_response(message_id, {"tools": self._tools})

    async def _handle_tools_call(self, message_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        """Handle tools/call request."""
        tool_name = params.get("name")
        if not isinstance(tool_name, str):
            return self._error_response(message_id, INVALID_PARAMS, "Missing or invalid tool name")
        arguments = params.get("arguments", {})

        try:
            result = await self.execute_tool(tool_name, arguments)
            return self._success_response(message_id, {"content": result, "isError": False})
        except Exception as e:
            return self._success_response(
                message_id,
                {
                    "content": [{"type": "text", "text": str(e)}],
                    "isError": True,
                },
            )

    async def execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Execute a tool and return results.

        This is a placeholder that should be overridden or mocked in tests.
        In production, this integrates with the actual tool execution system.
        """
        # Default implementation returns a placeholder
        return [{"type": "text", "text": f"Executed {tool_name} with {arguments}"}]

    def _handle_resources_list(self, message_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        """Handle resources/list request."""
        return self._success_response(message_id, {"resources": self._resources})

    def _handle_resources_read(self, message_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        """Handle resources/read request."""
        uri = params.get("uri", "")

        # Return placeholder content
        content = {
            "uri": uri,
            "mimeType": "application/json",
            "text": json.dumps({"config": "placeholder", "uri": uri}),
        }
        return self._success_response(message_id, {"contents": [content]})

    def _handle_prompts_list(self, message_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        """Handle prompts/list request."""
        return self._success_response(message_id, {"prompts": self._prompts})

    def _handle_prompts_get(self, message_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        """Handle prompts/get request."""
        prompt_name = params.get("name")
        arguments = params.get("arguments", {})

        # Generate prompt messages based on name
        if prompt_name == "code_review":
            code = arguments.get("code", "")
            language = arguments.get("language", "unknown")
            messages = [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": f"Please review the following {language} code:\n\n```{language}\n{code}\n```",
                    },
                }
            ]
        elif prompt_name == "summarize_conversation":
            messages = [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": "Please summarize the current conversation, highlighting key points and decisions.",
                    },
                }
            ]
        elif prompt_name == "debug_error":
            error = arguments.get("error", "")
            context = arguments.get("context", "")
            messages = [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": f"Please help debug this error:\n\nError: {error}\n\nContext: {context}",
                    },
                }
            ]
        else:
            return self._error_response(message_id, INVALID_PARAMS, f"Unknown prompt: {prompt_name}")

        return self._success_response(message_id, {"messages": messages})

    # =========================================================================
    # Streaming Extensions ($/streaming/*)
    # =========================================================================

    def create_streaming_start_notification(self, stream_id: str, tool_call_id: int) -> dict[str, Any]:
        """Create a $/streaming/start notification."""
        return {
            "jsonrpc": "2.0",
            "method": "$/streaming/start",
            "params": {
                "streamId": stream_id,
                "toolCallId": tool_call_id,
            },
        }

    def create_streaming_chunk_notification(self, stream_id: str, content: dict[str, Any]) -> dict[str, Any]:
        """Create a $/streaming/chunk notification."""
        return {
            "jsonrpc": "2.0",
            "method": "$/streaming/chunk",
            "params": {
                "streamId": stream_id,
                "content": content,
            },
        }

    def create_streaming_end_notification(self, stream_id: str) -> dict[str, Any]:
        """Create a $/streaming/end notification."""
        return {
            "jsonrpc": "2.0",
            "method": "$/streaming/end",
            "params": {
                "streamId": stream_id,
            },
        }

    # =========================================================================
    # Trace Extensions ($/trace/*)
    # =========================================================================

    def create_trace_span_notification(
        self,
        trace_id: str,
        span_id: str,
        name: str,
        start_time: str,
        end_time: str,
        status: str,
        attributes: dict[str, Any] | None = None,
        parent_span_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a $/trace/span notification with OpenTelemetry-compatible data."""
        return {
            "jsonrpc": "2.0",
            "method": "$/trace/span",
            "params": {
                "traceId": trace_id,
                "spanId": span_id,
                "parentSpanId": parent_span_id,
                "name": name,
                "startTime": start_time,
                "endTime": end_time,
                "status": status,
                "attributes": attributes or {},
            },
        }

    def create_trace_event_notification(
        self,
        span_id: str,
        name: str,
        timestamp: str,
        attributes: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a $/trace/event notification."""
        return {
            "jsonrpc": "2.0",
            "method": "$/trace/event",
            "params": {
                "spanId": span_id,
                "name": name,
                "timestamp": timestamp,
                "attributes": attributes or {},
            },
        }


class AuthenticatedMCPHandler(MCPMessageHandler):
    """
    MCP message handler with user authentication context.

    Extends MCPMessageHandler with:
    - User ID and roles tracking
    - Authenticated tool execution
    - User context propagation to agent
    """

    def __init__(
        self,
        user_id: str,
        roles: list[str] | None = None,
        notification_callback: Callable[[dict[str, Any]], Any] | None = None,
        session_id: str | None = None,
    ) -> None:
        """
        Initialize the authenticated handler.

        Args:
            user_id: The authenticated user's ID.
            roles: The user's roles for authorization.
            notification_callback: Optional async callback for sending notifications.
            session_id: Optional session ID for connection tracking and idle timeout prevention.
        """
        super().__init__()
        self.user_id = user_id
        self.roles = roles or []
        self.notification_callback = notification_callback
        self.session_id = session_id

    async def _handle_tools_call(self, message_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        """
        Handle tools/call request with streaming support.

        Overrides base method to check for _meta.streaming parameter
        and use StreamingToolCallHandler when streaming is requested.
        """
        tool_name = params.get("name")
        if not isinstance(tool_name, str):
            return self._error_response(message_id, INVALID_PARAMS, "Missing or invalid tool name")
        arguments = params.get("arguments", {})

        # Check for streaming request
        meta = params.get("_meta", {})
        is_streaming_requested = meta.get("streaming", False)

        # Use streaming handler if:
        # 1. Streaming is globally enabled
        # 2. Client requested streaming
        # 3. We have a notification callback
        if is_streaming_requested and is_streaming_enabled() and self.notification_callback is not None:
            streaming_handler = StreamingToolCallHandler(
                mcp_handler=self,
                send_notification=self.notification_callback,
                metrics_collector=streaming_metrics_collector,
                outbound_rate_limiter=get_outbound_rate_limiter(),
                max_chunk_size=get_streaming_max_chunk_size(),
                connection_manager=get_connection_manager(),
                session_id=self.session_id,
            )
            streaming_result = await streaming_handler.handle_streaming_call(
                message_id=message_id,
                tool_name=tool_name,
                arguments=arguments,
            )
            return self._success_response(message_id, streaming_result)

        # Fall back to non-streaming execution
        try:
            tool_result = await self.execute_tool(tool_name, arguments)
            return self._success_response(message_id, {"content": tool_result, "isError": False})
        except Exception as e:
            return self._success_response(
                message_id,
                {
                    "content": [{"type": "text", "text": str(e)}],
                    "isError": True,
                },
            )

    async def execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Execute a tool with user context.

        Overrides the base method to integrate with the real agent and
        propagate user context for authorization.

        Args:
            tool_name: Name of the tool to execute.
            arguments: Tool arguments.

        Returns:
            List of content items from the tool execution.
        """
        session_id = arguments.get("session_id")

        # Execute with the real agent
        return await self._execute_with_agent(
            tool_name=tool_name,
            arguments=arguments,
            user_id=self.user_id,
            session_id=session_id,
        )

    async def _execute_with_agent(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        user_id: str,
        session_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Execute a tool via the LangGraph agent.

        This method integrates with MCPBridge for real tool execution.

        Args:
            tool_name: Name of the tool to execute.
            arguments: Tool arguments.
            user_id: The user's ID for context.
            session_id: Optional session ID for context preservation.

        Returns:
            List of content items from the agent execution.
        """
        logger.info(
            f"Tool execution requested: {tool_name} by user {user_id}",
            extra={"tool_name": tool_name, "user_id": user_id, "session_id": session_id},
        )

        # Get MCPBridge for real tool execution
        bridge = get_mcp_bridge()

        if tool_name == "langgraph-run":
            query = arguments.get("query", "")

            # Use MCPBridge if available
            if bridge and bridge.is_configured:
                try:
                    response = await bridge.send_chat_message(
                        session_id=session_id or "default",
                        message=query,
                        user_id=user_id,
                    )
                    return [
                        {
                            "type": "text",
                            "text": response.content,
                        }
                    ]
                except ChatError as e:
                    logger.warning(
                        f"MCPBridge execution failed: {e}",
                        extra={"tool_name": tool_name, "user_id": user_id, "error": str(e)},
                    )
                    return [
                        {
                            "type": "text",
                            "text": f"Error executing query: {e}",
                        }
                    ]

            # Fallback when MCPBridge is not available
            logger.debug(
                "MCPBridge not available, using placeholder response",
                extra={"tool_name": tool_name, "user_id": user_id},
            )
            return [
                {
                    "type": "text",
                    "text": f"[Agent] Processing query for user {user_id}: {query}",
                }
            ]

        # For other tools, use MCPBridge.call_tool if available
        if bridge and bridge.is_configured:
            try:
                result = await bridge.call_tool(tool_name, arguments)
                return result.content
            except ChatError as e:
                logger.warning(
                    f"MCPBridge tool call failed: {e}",
                    extra={"tool_name": tool_name, "user_id": user_id, "error": str(e)},
                )
                return [
                    {
                        "type": "text",
                        "text": f"Error executing tool: {e}",
                    }
                ]

        return [{"type": "text", "text": f"Executed {tool_name} with {arguments}"}]

    async def execute_tool_streaming(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Execute a tool with streaming response.

        Yields streaming chunks that can be sent as $/streaming/chunk notifications.

        Args:
            tool_name: Name of the tool to execute.
            arguments: Tool arguments.

        Yields:
            Content chunks from the streaming execution.
        """

        session_id = arguments.get("session_id")
        bridge = get_mcp_bridge()

        if tool_name == "langgraph-run":
            query = arguments.get("query", "")

            # Use MCPBridge streaming if available
            if bridge and bridge.is_configured:
                try:
                    async for chunk in bridge.stream_chat_message(
                        session_id=session_id or "default",
                        message=query,
                        user_id=self.user_id,
                    ):
                        yield {
                            "type": "text",
                            "text": chunk.content,
                            "is_final": chunk.is_final,
                        }
                    return
                except ChatError as e:
                    logger.warning(
                        f"MCPBridge streaming failed: {e}",
                        extra={"tool_name": tool_name, "user_id": self.user_id},
                    )
                    yield {
                        "type": "text",
                        "text": f"Streaming error: {e}",
                        "is_final": True,
                    }
                    return

            # Fallback: yield single chunk
            yield {
                "type": "text",
                "text": f"[Agent] Processing query for user {self.user_id}: {query}",
                "is_final": True,
            }
            return

        # For other tools, yield single result
        yield {
            "type": "text",
            "text": f"Executed {tool_name} with {arguments}",
            "is_final": True,
        }


# =============================================================================
# Streaming Tool Call Handler
# =============================================================================


class StreamingToolCallHandler:
    """
    Handles streaming tool calls by emitting MCP streaming notifications.

    Wraps an AuthenticatedMCPHandler and emits $/streaming/start, $/streaming/chunk,
    and $/streaming/end notifications during streaming tool execution.

    Usage:
        async def send_notification(n):
            await websocket.send_json(n)

        streaming_handler = StreamingToolCallHandler(
            mcp_handler=handler,
            send_notification=send_notification,
        )
        result = await streaming_handler.handle_streaming_call(
            message_id=1,
            tool_name="langgraph-run",
            arguments={"query": "test"},
        )
    """

    def __init__(
        self,
        mcp_handler: AuthenticatedMCPHandler,
        send_notification: Callable[[dict[str, Any]], Any],
        metrics_collector: StreamingMetricsCollector | None = None,
        outbound_rate_limiter: OutboundRateLimiter | None = None,
        connection_manager: ConnectionManager | None = None,
        session_id: str | None = None,
        max_chunk_size: int | None = None,
    ) -> None:
        """
        Initialize the streaming tool call handler.

        Args:
            mcp_handler: The authenticated MCP handler for tool execution.
            send_notification: Async callback to send notifications to client.
            metrics_collector: Optional metrics collector for stream statistics.
            outbound_rate_limiter: Optional rate limiter for outbound notifications.
            connection_manager: Optional connection manager for activity tracking.
            session_id: Optional session ID for activity updates.
            max_chunk_size: Optional max chunk size in bytes. Chunks larger than this are truncated.
        """
        self.mcp_handler = mcp_handler
        self.send_notification = send_notification
        self.metrics_collector = metrics_collector
        self.outbound_rate_limiter = outbound_rate_limiter
        self.connection_manager = connection_manager
        self.session_id = session_id
        self.max_chunk_size = max_chunk_size
        self._stream_counter = 0
        self._client_disconnected = False

    def _generate_stream_id(self) -> str:
        """Generate a unique stream ID."""
        self._stream_counter += 1
        return f"stream-{uuid.uuid4().hex[:12]}-{self._stream_counter}"

    async def handle_streaming_call(
        self,
        message_id: int,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Handle a streaming tool call.

        Emits streaming notifications and returns the final result.
        Handles WebSocket disconnection gracefully without raising.

        Args:
            message_id: The JSON-RPC message ID (toolCallId).
            tool_name: Name of the tool to execute.
            arguments: Tool arguments.

        Returns:
            Result dict with content and isError flag.
        """
        stream_id = self._generate_stream_id()
        collected_content: list[dict[str, Any]] = []
        is_error = False
        error_message = ""
        self._client_disconnected = False

        # Record stream start if metrics collector is provided
        if self.metrics_collector:
            self.metrics_collector.record_stream_start(stream_id)

        # Record OTel stream start
        otel_metrics.record_stream_start(stream_id=stream_id)

        try:
            # Emit streaming start notification
            try:
                await self.send_notification(
                    self.mcp_handler.create_streaming_start_notification(
                        stream_id=stream_id,
                        tool_call_id=message_id,
                    )
                )
            except (ConnectionError, OSError) as e:
                # Client disconnected before streaming could start
                self._client_disconnected = True
                logger.info(
                    f"Client disconnected during streaming start: {e}",
                    extra={"tool_name": tool_name, "stream_id": stream_id},
                )
                return {
                    "content": [{"type": "text", "text": "Client disconnected during streaming"}],
                    "isError": True,
                }

            # Stream chunks
            async for chunk in self.mcp_handler.execute_tool_streaming(tool_name, arguments):
                # Emit streaming chunk notification
                try:
                    # Apply outbound rate limiting if configured
                    if self.outbound_rate_limiter:
                        await self.outbound_rate_limiter.check_and_wait()

                    chunk_text = chunk.get("text", "")
                    # Truncate chunk if it exceeds max_chunk_size
                    if self.max_chunk_size and len(chunk_text) > self.max_chunk_size:
                        chunk_text = chunk_text[: self.max_chunk_size]
                    await self.send_notification(
                        self.mcp_handler.create_streaming_chunk_notification(
                            stream_id=stream_id,
                            content={"type": chunk.get("type", "text"), "text": chunk_text},
                        )
                    )
                    collected_content.append(chunk)
                    # Record chunk metrics
                    chunk_size = len(chunk_text)
                    if self.metrics_collector:
                        self.metrics_collector.record_chunk(stream_id, chunk_size)
                    # Record OTel chunk metrics
                    otel_metrics.record_stream_chunk(
                        stream_id=stream_id,
                        chunk_size=chunk_size,
                    )
                    # Update activity to prevent idle timeout during streaming
                    if self.connection_manager and self.session_id:
                        self.connection_manager.update_activity(self.session_id)
                except (ConnectionError, OSError) as e:
                    # Client disconnected during streaming - stop gracefully
                    self._client_disconnected = True
                    logger.info(
                        f"Client disconnected during streaming chunk: {e}",
                        extra={"tool_name": tool_name, "stream_id": stream_id},
                    )
                    return {
                        "content": [{"type": "text", "text": "Client disconnected during streaming"}],
                        "isError": True,
                    }

        except Exception as e:
            is_error = True
            error_message = str(e)
            logger.warning(
                f"Streaming tool call failed: {e}",
                extra={"tool_name": tool_name, "stream_id": stream_id},
            )

        finally:
            # Always attempt to emit streaming end notification
            # But handle disconnect gracefully (client may already be gone)
            if not self._client_disconnected:
                try:
                    await self.send_notification(self.mcp_handler.create_streaming_end_notification(stream_id=stream_id))
                except (ConnectionError, OSError) as e:
                    # Client disconnected during end notification - log but don't fail
                    # Streaming was already completed, so this is not an error
                    self._client_disconnected = True
                    logger.info(
                        f"Client disconnected during streaming end: {e}",
                        extra={"tool_name": tool_name, "stream_id": stream_id},
                    )

            # Record stream end if metrics collector is provided
            if self.metrics_collector:
                stats = self.metrics_collector.get_stream_stats(stream_id)
                self.metrics_collector.record_stream_end(stream_id)
                # Record OTel stream end with stats
                otel_metrics.record_stream_end(
                    stream_id=stream_id,
                    chunks=stats["chunk_count"],
                    total_bytes=stats["total_bytes"],
                    duration_ms=stats["duration_ms"],
                )
            else:
                # Record OTel stream end without detailed stats
                otel_metrics.record_stream_end(stream_id=stream_id)

        # Build result
        if is_error:
            return {
                "content": [{"type": "text", "text": f"Streaming error: {error_message}"}],
                "isError": True,
            }

        return {
            "content": collected_content,
            "isError": False,
        }


def create_handler_from_token(
    token_payload: dict[str, Any],
    notification_callback: Callable[[dict[str, Any]], Any] | None = None,
    session_id: str | None = None,
) -> AuthenticatedMCPHandler:
    """
    Create an AuthenticatedMCPHandler from a decoded token payload.

    Extracts user_id and roles from the token for authorization context.

    Args:
        token_payload: Decoded JWT token payload.
        notification_callback: Optional async callback for sending streaming notifications.
        session_id: Optional session ID for connection tracking and idle timeout prevention.

    Returns:
        AuthenticatedMCPHandler with user context and optional notification callback.
    """
    # Extract username - prefer preferred_username, fall back to sub
    username = token_payload.get("preferred_username") or token_payload.get("sub", "anonymous")
    user_id = f"user:{username}"

    # Extract roles from realm_access or resource_access
    roles: list[str] = []
    if "realm_access" in token_payload:
        roles.extend(token_payload["realm_access"].get("roles", []))

    # Also check resource_access for client-specific roles
    if "resource_access" in token_payload:
        for resource_roles in token_payload["resource_access"].values():
            if isinstance(resource_roles, dict):
                roles.extend(resource_roles.get("roles", []))

    # Default to "user" role if no roles found
    if not roles:
        roles = ["user"]

    return AuthenticatedMCPHandler(
        user_id=user_id,
        roles=roles,
        notification_callback=notification_callback,
        session_id=session_id,
    )


def create_anonymous_streaming_handler(
    session_id: str,
    notification_callback: Callable[[dict[str, Any]], Any] | None = None,
) -> AuthenticatedMCPHandler:
    """
    Create an AuthenticatedMCPHandler for anonymous (unauthenticated) connections.

    Uses session ID as the user identifier for rate limiting and tracking.
    Provides streaming support for anonymous connections.

    Args:
        session_id: Unique session identifier for this connection.
        notification_callback: Optional async callback for sending streaming notifications.

    Returns:
        AuthenticatedMCPHandler with session-based user context and streaming support.
    """
    # Use session ID as user identifier (prefixed with "session:")
    user_id = f"session:{session_id}"

    # Anonymous users get "anonymous" role
    roles = ["anonymous"]

    return AuthenticatedMCPHandler(
        user_id=user_id,
        roles=roles,
        notification_callback=notification_callback,
        session_id=session_id,
    )


# =============================================================================
# Token Validation and Authorization Functions
# =============================================================================


def get_token_validator() -> Any | None:
    """
    Get the Keycloak token validator instance.

    Returns:
        TokenValidator instance or None if not configured.
    """
    try:
        # Dynamic import - function may not exist in all deployments
        from mcp_server_langgraph.auth.factory import get_token_validator as _get_validator  # type: ignore[attr-defined]

        return _get_validator()
    except ImportError:
        logger.debug("Auth factory not available, token validation disabled")
        return None
    except Exception as e:
        logger.warning(f"Failed to get token validator: {e}")
        return None


def get_openfga_client() -> Any | None:
    """
    Get the OpenFGA client instance.

    Returns:
        OpenFGAClient instance or None if not configured.
    """
    try:
        # Dynamic import - function may not exist in all deployments
        from mcp_server_langgraph.auth.factory import get_openfga_client as _get_openfga  # type: ignore[attr-defined]

        return _get_openfga()
    except ImportError:
        logger.debug("Auth factory not available, OpenFGA disabled")
        return None
    except Exception as e:
        logger.warning(f"Failed to get OpenFGA client: {e}")
        return None


async def validate_websocket_token(token: str) -> dict[str, Any] | None:
    """
    Validate a JWT token for WebSocket connection.

    Uses the Keycloak token validator to verify the token signature
    and expiration.

    Args:
        token: JWT access token to validate.

    Returns:
        Decoded token payload if valid, None if invalid/expired.
    """
    import jwt

    validator = get_token_validator()
    if validator is None:
        logger.warning("Token validator not configured, skipping validation")
        return None

    try:
        payload = await validator.verify_token(token)
        logger.debug(
            "WebSocket token validated",
            extra={"user": payload.get("preferred_username")},
        )
        return cast(dict[str, Any], payload)
    except jwt.ExpiredSignatureError:
        logger.warning("WebSocket token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid WebSocket token: {e}")
        return None
    except Exception:
        logger.exception("Token validation error")
        return None


async def check_mcp_permission(
    user_id: str,
    permission: str,
    resource: str,
) -> bool:
    """
    Check if a user has permission to access an MCP resource.

    Uses OpenFGA for fine-grained authorization checks.

    Args:
        user_id: User identifier (e.g., "user:alice").
        permission: Permission to check (e.g., "use").
        resource: Resource to check access to (e.g., "mcp:websocket").

    Returns:
        True if allowed, False if denied.
    """
    openfga = get_openfga_client()

    if openfga is None:
        # Fail-open when OpenFGA is not configured
        logger.debug("OpenFGA not configured, allowing access")
        return True

    try:
        allowed = await openfga.check(
            user=user_id,
            relation=permission,
            object=resource,
        )
        logger.debug(
            f"MCP permission check: {user_id} {permission} {resource} = {allowed}",
            extra={"user_id": user_id, "permission": permission, "resource": resource, "allowed": allowed},
        )
        return bool(allowed)
    except Exception as e:
        # Fail-open on errors (configurable via feature flag)
        logger.warning(f"OpenFGA check failed, failing open: {e}")
        return True


class ConnectionManager:
    """
    Manages WebSocket connections for MCP sessions.

    Tracks active connections by session ID with user context for:
    - Per-user connection limits
    - User-based message routing
    - Connection lifecycle tracking
    """

    def __init__(
        self,
        max_connections_per_user: int | None = None,
        idle_timeout_seconds: int | None = None,
    ) -> None:
        """
        Initialize the connection manager.

        Args:
            max_connections_per_user: Optional per-user connection limit.
                                      Defaults to MAX_CONNECTIONS_PER_USER if not provided.
            idle_timeout_seconds: Optional idle timeout in seconds.
                                  Defaults to IDLE_TIMEOUT_SECONDS if not provided.
        """
        self._connections: dict[str, ConnectionInfo] = {}
        self._user_connections: dict[str, list[str]] = {}  # user_id -> [session_ids]
        self.max_connections_per_user = (
            max_connections_per_user if max_connections_per_user is not None else MAX_CONNECTIONS_PER_USER
        )
        self.idle_timeout_seconds = idle_timeout_seconds if idle_timeout_seconds is not None else IDLE_TIMEOUT_SECONDS

    async def connect(
        self,
        websocket: WebSocket,
        session_id: str,
        user_id: str | None = None,
        roles: list[str] | None = None,
    ) -> None:
        """
        Accept and track a new WebSocket connection.

        Args:
            websocket: The WebSocket to connect.
            session_id: Unique session identifier.
            user_id: Optional user ID for authenticated connections.
            roles: Optional list of user roles.
        """
        await websocket.accept()

        conn_info = ConnectionInfo(
            websocket=websocket,
            session_id=session_id,
            user_id=user_id,
            roles=roles or [],
        )
        self._connections[session_id] = conn_info

        # Track user connections
        if user_id:
            if user_id not in self._user_connections:
                self._user_connections[user_id] = []
            self._user_connections[user_id].append(session_id)

    def disconnect(self, session_id: str) -> None:
        """Remove a WebSocket connection."""
        if session_id in self._connections:
            conn_info = self._connections[session_id]
            # Remove from user tracking
            if conn_info.user_id and conn_info.user_id in self._user_connections:
                sessions = self._user_connections[conn_info.user_id]
                if session_id in sessions:
                    sessions.remove(session_id)
                if not sessions:
                    del self._user_connections[conn_info.user_id]
            del self._connections[session_id]

    def get_connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self._connections)

    def get_user_connection_count(self, user_id: str) -> int:
        """
        Get the number of active connections for a user.

        Args:
            user_id: The user ID to check.

        Returns:
            Number of active connections for the user.
        """
        return len(self._user_connections.get(user_id, []))

    def can_user_connect(self, user_id: str) -> bool:
        """
        Check if a user can create a new connection.

        Args:
            user_id: The user ID to check.

        Returns:
            True if user is below connection limit.
        """
        return self.get_user_connection_count(user_id) < self.max_connections_per_user

    def has_connection(self, session_id: str) -> bool:
        """Check if a session has an active connection."""
        return session_id in self._connections

    def get_idle_connections(self) -> list[str]:
        """
        Get list of session IDs for connections that have exceeded idle timeout.

        Uses the configured idle_timeout_seconds for the check.

        Returns:
            List of session IDs for idle connections.
        """
        idle_sessions = []
        for session_id, conn_info in self._connections.items():
            if is_connection_idle(conn_info, timeout_seconds=self.idle_timeout_seconds):
                idle_sessions.append(session_id)
        return idle_sessions

    def update_activity(self, session_id: str) -> None:
        """
        Update the last activity timestamp for a connection.

        Args:
            session_id: The session ID to update.
        """
        if session_id in self._connections:
            update_connection_activity(self._connections[session_id])

    async def send_to_session(self, session_id: str, message: dict[str, Any]) -> None:
        """Send a message to a specific session."""
        if session_id in self._connections:
            await self._connections[session_id].websocket.send_json(message)

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Broadcast a message to all connected sessions."""
        for conn_info in self._connections.values():
            try:
                await conn_info.websocket.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to broadcast to session {conn_info.session_id}: {e}")

    async def broadcast_to_user(self, user_id: str, message: dict[str, Any]) -> None:
        """Broadcast a message to all sessions for a specific user."""
        session_ids = self._user_connections.get(user_id, [])
        for session_id in session_ids:
            if session_id in self._connections:
                try:
                    await self._connections[session_id].websocket.send_json(message)
                except Exception as e:
                    logger.warning(f"Failed to send to user {user_id} session {session_id}: {e}")


# Create router
mcp_websocket_router = APIRouter(tags=["MCP WebSocket"])

# Global connection manager
connection_manager = ConnectionManager()


def get_connection_manager() -> ConnectionManager:
    """
    Get the global connection manager instance.

    Returns:
        The global ConnectionManager instance.
    """
    return connection_manager


def set_connection_manager(manager: ConnectionManager) -> None:
    """
    Set the global connection manager instance.

    Used by bootstrap to inject a configured manager.

    Args:
        manager: The connection manager instance to set as global singleton.
    """
    global connection_manager
    connection_manager = manager


def create_connection_manager(
    streaming_settings: Any | None = None,
) -> ConnectionManager:
    """
    Create a ConnectionManager with optional StreamingSettings.

    Factory function that allows configuration injection for connection manager.

    Args:
        streaming_settings: Optional StreamingSettings instance with connection config.

    Returns:
        A ConnectionManager instance with configured connection limit and idle timeout.
    """
    if streaming_settings is None:
        return ConnectionManager()

    return ConnectionManager(
        max_connections_per_user=streaming_settings.streaming_max_connections_per_user,
        idle_timeout_seconds=streaming_settings.streaming_idle_timeout_seconds,
    )


@mcp_websocket_router.websocket("/mcp/ws")
async def mcp_websocket_endpoint(websocket: WebSocket) -> None:
    """
    MCP WebSocket endpoint for real-time bidirectional communication.

    Accepts WebSocket connections and handles MCP protocol messages.
    Each connection is associated with a unique session ID.

    Security Features:
    - Message size validation
    - Per-session rate limiting
    - Activity tracking for idle timeout
    - Metrics recording
    - Streaming support for anonymous connections
    """
    # Generate session ID for this connection
    session_id = str(uuid.uuid4())

    # Define notification callback for streaming support
    async def send_notification(notification: dict[str, Any]) -> None:
        """Send streaming notification to client via WebSocket."""
        await websocket.send_json(notification)

    # Create handler with streaming support for anonymous connection
    handler = create_anonymous_streaming_handler(
        session_id=session_id,
        notification_callback=send_notification,
    )

    # Create secure message processor
    secure_processor = SecureMessageProcessor(
        session_id=session_id,
        user_id=f"session:{session_id}",  # Session-based identity for rate limiting
        rate_limiter=user_rate_limiter,
        connection_manager=connection_manager,
        metrics=mcp_websocket_metrics,
    )

    await connection_manager.connect(websocket, session_id)
    mcp_websocket_metrics.record_connection()
    otel_metrics.record_connection()

    try:
        while True:
            # Receive message
            try:
                data = await websocket.receive_text()

                # Security: Validate message size and rate limit
                validation = secure_processor.validate_incoming(data)
                if not validation.is_valid:
                    response = {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {
                            "code": validation.error_code,
                            "message": validation.error_message,
                        },
                    }
                    await websocket.send_json(response)
                    continue

                message = json.loads(data)
            except json.JSONDecodeError:
                response = handler.handle_parse_error()
                await websocket.send_json(response)
                continue

            # Record metrics and update activity
            method = message.get("method", "unknown")
            secure_processor.record_message_received(method)
            otel_metrics.record_message_received(method=method)

            # Handle message
            response = await handler.handle(message)

            # Update activity and send response
            secure_processor.on_message_processed()
            secure_processor.record_message_sent(method)
            otel_metrics.record_message_sent(method=method)
            await websocket.send_json(response)

    except WebSocketDisconnect:
        connection_manager.disconnect(session_id)
        mcp_websocket_metrics.record_disconnect()
        otel_metrics.record_disconnect()


@mcp_websocket_router.websocket("/mcp/ws/auth")
async def mcp_websocket_authenticated(websocket: WebSocket) -> None:
    """
    Authenticated MCP WebSocket endpoint with full security flow.

    Requires valid JWT token (via query param or Authorization header).
    Validates token via Keycloak and checks permissions via OpenFGA.

    Security Flow:
    1. Extract token from connection
    2. Validate token via Keycloak
    3. Check MCP WebSocket permission via OpenFGA
    4. Check user connection limit
    5. Create AuthenticatedMCPHandler with user context
    """
    # Step 1: Extract token
    token = extract_websocket_token(websocket)
    if not token:
        logger.warning("WebSocket connection rejected: no token provided")
        mcp_websocket_metrics.record_connection_rejected(user_id="unknown", reason="no_token")
        await websocket.close(code=4001, reason="Authentication required")
        return

    # Step 2: Validate token
    token_payload = await validate_websocket_token(token)
    if not token_payload:
        logger.warning("WebSocket connection rejected: invalid token")
        mcp_websocket_metrics.record_connection_rejected(user_id="unknown", reason="invalid_token")
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    # Generate session ID early for handler context
    session_id = str(uuid.uuid4())

    # Define notification callback for streaming support
    async def send_notification(notification: dict[str, Any]) -> None:
        """Send streaming notification to client via WebSocket."""
        await websocket.send_json(notification)

    # Create handler with user context and notification callback
    handler = create_handler_from_token(
        token_payload,
        notification_callback=send_notification,
        session_id=session_id,
    )
    user_id = handler.user_id

    # Step 3: Check MCP WebSocket permission
    has_permission = await check_mcp_permission(
        user_id=user_id,
        permission="use",
        resource="mcp:websocket",
    )
    if not has_permission:
        logger.warning(
            f"WebSocket connection rejected: permission denied for {user_id}",
            extra={"user_id": user_id},
        )
        mcp_websocket_metrics.record_connection_rejected(user_id=user_id, reason="permission_denied")
        await websocket.close(code=4003, reason="Permission denied")
        return

    # Step 4: Check connection limit
    if not connection_manager.can_user_connect(user_id):
        logger.warning(
            f"WebSocket connection rejected: connection limit reached for {user_id}",
            extra={"user_id": user_id, "limit": connection_manager.max_connections_per_user},
        )
        mcp_websocket_metrics.record_connection_rejected(user_id=user_id, reason="connection_limit")
        await websocket.close(code=4029, reason="Too many connections")
        return

    # Step 5: Establish authenticated connection
    # Note: session_id was already generated earlier for handler context

    # Create secure message processor with user context
    secure_processor = SecureMessageProcessor(
        session_id=session_id,
        user_id=user_id,
        rate_limiter=user_rate_limiter,
        connection_manager=connection_manager,
        metrics=mcp_websocket_metrics,
    )

    await connection_manager.connect(
        websocket,
        session_id,
        user_id=user_id,
        roles=handler.roles,
    )
    mcp_websocket_metrics.record_connection()
    otel_metrics.record_connection()

    logger.info(
        f"Authenticated WebSocket connection established for {user_id}",
        extra={"user_id": user_id, "session_id": session_id},
    )

    try:
        while True:
            try:
                data = await websocket.receive_text()

                # Security: Validate message size and rate limit
                validation = secure_processor.validate_incoming(data)
                if not validation.is_valid:
                    response = {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {
                            "code": validation.error_code,
                            "message": validation.error_message,
                        },
                    }
                    await websocket.send_json(response)
                    continue

                message = json.loads(data)
            except json.JSONDecodeError:
                response = handler.handle_parse_error()
                await websocket.send_json(response)
                continue

            # Record metrics and update activity
            method = message.get("method", "unknown")
            secure_processor.record_message_received(method)
            otel_metrics.record_message_received(method=method, user_id=user_id)

            # Handle message with authenticated handler
            response = await handler.handle(message)

            # Update activity and send response
            secure_processor.on_message_processed()
            secure_processor.record_message_sent(method)
            otel_metrics.record_message_sent(method=method, user_id=user_id)
            await websocket.send_json(response)

    except WebSocketDisconnect:
        connection_manager.disconnect(session_id)
        mcp_websocket_metrics.record_disconnect()
        otel_metrics.record_disconnect()
        logger.info(
            f"Authenticated WebSocket disconnected for {user_id}",
            extra={"user_id": user_id, "session_id": session_id},
        )


@mcp_websocket_router.websocket("/mcp/ws/{session_id}")
async def mcp_websocket_with_session(websocket: WebSocket, session_id: str) -> None:
    """
    MCP WebSocket endpoint with explicit session ID.

    Allows clients to specify a session ID for connection resumption
    and context preservation.

    Security Features:
    - Session ID validation and sanitization
    - Message size validation
    - Per-user/session rate limiting
    - Activity tracking for idle timeout
    - Metrics recording

    Note: For authenticated connections, use /mcp/ws/auth instead.
    """
    # Security: Validate and sanitize session ID
    if not validate_session_id(session_id):
        logger.warning(
            "WebSocket connection rejected: invalid session ID",
            extra={"session_id": session_id[:50]},  # Truncate for logging
        )
        await websocket.close(code=4000, reason="Invalid session ID")
        return

    # Sanitize session ID for safety
    session_id = sanitize_session_id(session_id)

    # Define notification callback for streaming support
    async def send_notification(notification: dict[str, Any]) -> None:
        """Send streaming notification to client via WebSocket."""
        await websocket.send_json(notification)

    # Check for optional authentication
    token = extract_websocket_token(websocket)
    handler: MCPMessageHandler
    user_id: str | None = None

    if token:
        token_payload = await validate_websocket_token(token)
        if token_payload:
            handler = create_handler_from_token(
                token_payload,
                notification_callback=send_notification,
                session_id=session_id,
            )
            user_id = handler.user_id
            await connection_manager.connect(
                websocket,
                session_id,
                user_id=user_id,
                roles=handler.roles,
            )
        else:
            handler = MCPMessageHandler()
            await connection_manager.connect(websocket, session_id)
    else:
        handler = MCPMessageHandler()
        await connection_manager.connect(websocket, session_id)

    # Create secure message processor
    secure_processor = SecureMessageProcessor(
        session_id=session_id,
        user_id=user_id,
        rate_limiter=user_rate_limiter,
        connection_manager=connection_manager,
        metrics=mcp_websocket_metrics,
    )

    mcp_websocket_metrics.record_connection()
    otel_metrics.record_connection()

    try:
        while True:
            try:
                data = await websocket.receive_text()

                # Security: Validate message size and rate limit
                validation = secure_processor.validate_incoming(data)
                if not validation.is_valid:
                    response = {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {
                            "code": validation.error_code,
                            "message": validation.error_message,
                        },
                    }
                    await websocket.send_json(response)
                    continue

                message = json.loads(data)
            except json.JSONDecodeError:
                response = handler.handle_parse_error()
                await websocket.send_json(response)
                continue

            # Record metrics and update activity
            method = message.get("method", "unknown")
            secure_processor.record_message_received(method)
            otel_metrics.record_message_received(method=method, user_id=user_id or "")

            response = await handler.handle(message)

            # Update activity and send response
            secure_processor.on_message_processed()
            secure_processor.record_message_sent(method)
            otel_metrics.record_message_sent(method=method, user_id=user_id or "")
            await websocket.send_json(response)

    except WebSocketDisconnect:
        connection_manager.disconnect(session_id)
        mcp_websocket_metrics.record_disconnect()
        otel_metrics.record_disconnect()


# =============================================================================
# Streaming Metrics HTTP Endpoint
# =============================================================================


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
    aggregate = streaming_metrics_collector.get_aggregate_stats()

    # Collect stream details
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
