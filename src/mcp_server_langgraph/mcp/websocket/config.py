"""
MCP WebSocket Configuration.

This module provides streaming configuration globals for MCP WebSocket
connections, including streaming enabled flag and chunk size limits.

Migrated from: api.v1.mcp_websocket
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# =============================================================================
# Streaming Configuration Globals
# =============================================================================

# Global streaming enabled flag
_streaming_enabled: bool = True


def is_streaming_enabled() -> bool:
    """
    Check if streaming is enabled globally.

    Returns:
        True if streaming is enabled, False otherwise.
    """
    return _streaming_enabled


def set_streaming_enabled(enabled: bool) -> None:
    """
    Set the global streaming enabled flag.

    Called by bootstrap to configure streaming based on settings.

    Args:
        enabled: Whether streaming should be enabled.
    """
    global _streaming_enabled
    _streaming_enabled = enabled
    logger.debug(f"Streaming enabled set to: {enabled}")


# Global max chunk size for streaming
_streaming_max_chunk_size: int | None = None


def get_streaming_max_chunk_size() -> int | None:
    """
    Get the maximum chunk size for streaming.

    Returns:
        Maximum chunk size in bytes, or None for unlimited.
    """
    return _streaming_max_chunk_size


def set_streaming_max_chunk_size(max_chunk_size: int | None) -> None:
    """
    Set the maximum chunk size for streaming.

    Called by bootstrap to configure chunk size limits based on settings.

    Args:
        max_chunk_size: Maximum chunk size in bytes, or None for unlimited.
    """
    global _streaming_max_chunk_size
    _streaming_max_chunk_size = max_chunk_size
    logger.debug(f"Streaming max chunk size set to: {max_chunk_size}")


# =============================================================================
# Token Validation Configuration
# =============================================================================

# Global token validation interval (seconds)
# Used for periodic JWT token validation during active WebSocket connections
# Set to 0 to disable periodic validation
_token_validation_interval: int = 300  # Default: 5 minutes


def get_token_validation_interval() -> int:
    """
    Get the token validation interval for WebSocket connections.

    This interval determines how often the backend validates JWT tokens
    during active WebSocket connections. When a token is found expired,
    the connection is closed with code 4010 (TokenExpired).

    Returns:
        Interval in seconds between token validation checks.
        0 means validation is disabled.
    """
    return _token_validation_interval


def set_token_validation_interval(interval: int) -> None:
    """
    Set the token validation interval for WebSocket connections.

    Called by bootstrap to configure token validation based on settings.

    Args:
        interval: Interval in seconds between validation checks.
            Set to 0 to disable periodic validation.
    """
    global _token_validation_interval
    _token_validation_interval = interval
    logger.debug(f"Token validation interval set to: {interval}s")


def create_websocket_config(
    endpoint_name: str,
    *,
    require_auth: bool = True,
    rate_limit_per_minute: int = 600,
    message_timeout: int = 30,
    heartbeat_interval: int = 30,
    idle_timeout: int = 1800,
    max_message_size: int = 1_000_000,
    token_validation_interval: int | None = None,
    **kwargs,
):
    """
    Create a WebSocketConfig with global settings applied.

    This factory function creates a WebSocketConfig that uses the globally
    configured token_validation_interval from bootstrap/settings, unless
    an explicit override is provided.

    Args:
        endpoint_name: Name of the WebSocket endpoint for metrics.
        require_auth: Whether authentication is required.
        rate_limit_per_minute: Messages per minute limit.
        message_timeout: Timeout for message processing.
        heartbeat_interval: Interval between heartbeats.
        idle_timeout: Idle connection timeout.
        max_message_size: Maximum message size in bytes.
        token_validation_interval: Override for token validation interval.
            If None, uses the globally configured value.
        **kwargs: Additional WebSocketConfig parameters.

    Returns:
        WebSocketConfig instance with global settings applied.
    """
    from mcp_server_langgraph.websocket.types import WebSocketConfig

    # Use global token validation interval if not explicitly provided
    if token_validation_interval is None:
        token_validation_interval = get_token_validation_interval()

    return WebSocketConfig(
        endpoint_name=endpoint_name,
        require_auth=require_auth,
        rate_limit_per_minute=rate_limit_per_minute,
        message_timeout=message_timeout,
        heartbeat_interval=heartbeat_interval,
        idle_timeout=idle_timeout,
        max_message_size=max_message_size,
        token_validation_interval=token_validation_interval,
        **kwargs,
    )
