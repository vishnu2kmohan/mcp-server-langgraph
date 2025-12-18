"""
WebSocket Bootstrap Module

Initializes WebSocket lifecycle management for MCP and notification WebSockets.
Handles background cleanup tasks and graceful shutdown.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from mcp_server_langgraph.observability.telemetry import logger

if TYPE_CHECKING:
    from mcp_server_langgraph.api.v1.mcp_websocket import (
        MCPWebSocketLifecycleManager,
        ConnectionManager,
        UserRateLimiterManager,
    )


@dataclass
class WebSocketState:
    """
    State for WebSocket lifecycle management.

    Holds references to lifecycle managers, connection manager,
    rate limiter, and provides cleanup.
    """

    mcp_lifecycle_manager: MCPWebSocketLifecycleManager | None = None
    connection_manager: ConnectionManager | None = None
    user_rate_limiter: UserRateLimiterManager | None = None

    async def cleanup(self) -> None:
        """
        Cleanup WebSocket resources.

        Shuts down MCP WebSocket lifecycle (cancels tasks, graceful shutdown).
        """
        if self.mcp_lifecycle_manager:
            await self.mcp_lifecycle_manager.shutdown()
            logger.info("WebSocket lifecycle cleanup complete")


# Lazy import cache to avoid circular imports
_lifecycle_manager_class: type | None = None


def _get_lifecycle_manager_class() -> type:
    """Lazy import of MCPWebSocketLifecycleManager."""
    global _lifecycle_manager_class
    if _lifecycle_manager_class is None:
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            MCPWebSocketLifecycleManager as _Manager,
        )

        _lifecycle_manager_class = _Manager
    return _lifecycle_manager_class


async def init_websocket_lifecycle(
    streaming_settings: Any | None = None,
) -> WebSocketState:
    """
    Initialize WebSocket lifecycle management.

    Starts the MCP WebSocket lifecycle manager which runs background
    cleanup tasks for idle connections. Also configures global singletons
    for connection management and rate limiting.

    Args:
        streaming_settings: Optional StreamingSettings instance with cleanup intervals.
            If provided, creates a configured lifecycle manager.
            If None, uses default intervals.

    Returns:
        WebSocketState with initialized lifecycle manager and security configs.
    """
    from mcp_server_langgraph.api.v1.mcp_websocket import (
        create_mcp_lifecycle_manager,
        set_mcp_lifecycle_manager,
        set_streaming_enabled,
        create_connection_manager,
        set_connection_manager,
        create_user_rate_limiter,
        set_user_rate_limiter,
        set_streaming_max_chunk_size,
        create_outbound_rate_limiter,
        set_outbound_rate_limiter,
    )

    # Set global streaming enabled flag if settings provided
    if streaming_settings is not None:
        set_streaming_enabled(streaming_settings.streaming_enabled)

    # Create and set configured lifecycle manager
    mcp_manager = create_mcp_lifecycle_manager(streaming_settings=streaming_settings)
    set_mcp_lifecycle_manager(mcp_manager)

    # Create and set configured connection manager
    conn_manager = create_connection_manager(streaming_settings=streaming_settings)
    set_connection_manager(conn_manager)

    # Create and set configured user rate limiter
    rate_limiter = create_user_rate_limiter(streaming_settings=streaming_settings)
    set_user_rate_limiter(rate_limiter)

    # Set max chunk size from settings
    if streaming_settings is not None:
        set_streaming_max_chunk_size(streaming_settings.streaming_max_chunk_size)

    # Create and set configured outbound rate limiter
    outbound_limiter = create_outbound_rate_limiter(streaming_settings=streaming_settings)
    set_outbound_rate_limiter(outbound_limiter)

    # Start the lifecycle (starts cleanup task)
    await mcp_manager.startup()

    if streaming_settings:
        logger.info(
            "WebSocket lifecycle initialized with custom settings",
            extra={
                "cleanup_interval": streaming_settings.streaming_idle_cleanup_interval,
                "metrics_cleanup_interval": streaming_settings.streaming_metrics_cleanup_interval,
                "streaming_enabled": streaming_settings.streaming_enabled,
                "max_connections_per_user": streaming_settings.streaming_max_connections_per_user,
                "max_messages_per_minute": streaming_settings.streaming_max_messages_per_minute,
            },
        )
    else:
        logger.info("WebSocket lifecycle initialized with default settings")

    return WebSocketState(
        mcp_lifecycle_manager=mcp_manager,
        connection_manager=conn_manager,
        user_rate_limiter=rate_limiter,
    )
