"""
MCP WebSocket Package.

This package contains MCP-specific WebSocket infrastructure classes that have been
moved from the legacy `api.v1.mcp_websocket` module to enable better separation
of concerns and reduce code duplication.

Classes:
- ConnectionManager: Manages MCP WebSocket connections with user context
- StreamingToolCallHandler: Handles streaming tool execution with notifications
- StreamingMetricsCollector: Collects streaming metrics
- StreamStats: Statistics for streaming operations
- MCPWebSocketLifecycleManager: Lifecycle management for MCP WebSocket
- OTelMCPMetrics: OpenTelemetry metrics for MCP WebSocket

Usage:
    from mcp_server_langgraph.mcp.websocket import (
        ConnectionManager,
        StreamingToolCallHandler,
        get_connection_manager,
        set_connection_manager,
    )

Migration Notice:
    This module replaces `mcp_server_langgraph.api.v1.mcp_websocket` for these classes.
    The old module now provides deprecation warnings for imports.
"""

from mcp_server_langgraph.mcp.websocket.connection_manager import (
    ConnectionInfo,
    ConnectionManager,
    create_connection_manager,
    get_connection_manager,
    is_connection_idle,
    set_connection_manager,
    update_connection_activity,
)
from mcp_server_langgraph.mcp.websocket.lifecycle import (
    MCPWebSocketLifecycleManager,
    create_mcp_lifecycle_manager,
    get_mcp_lifecycle_manager,
    set_mcp_lifecycle_manager,
)
from mcp_server_langgraph.mcp.websocket.metrics import (
    OTelMCPMetrics,
)
from mcp_server_langgraph.mcp.websocket.streaming import (
    StreamingMetricsCollector,
    StreamingToolCallHandler,
    StreamStats,
    streaming_metrics_collector,
)
from mcp_server_langgraph.mcp.websocket.config import (
    get_streaming_max_chunk_size,
    is_streaming_enabled,
    set_streaming_enabled,
    set_streaming_max_chunk_size,
)
from mcp_server_langgraph.mcp.websocket.rate_limiter import (
    OutboundRateLimiter,
    UserRateLimiterManager,
    create_outbound_rate_limiter,
    create_user_rate_limiter,
    get_outbound_rate_limiter,
    get_user_rate_limiter,
    set_outbound_rate_limiter,
    set_user_rate_limiter,
)

__all__ = [
    # Connection management
    "ConnectionInfo",
    "ConnectionManager",
    "get_connection_manager",
    "set_connection_manager",
    "create_connection_manager",
    "update_connection_activity",
    "is_connection_idle",
    # Streaming
    "StreamingToolCallHandler",
    "StreamingMetricsCollector",
    "StreamStats",
    "streaming_metrics_collector",
    # Lifecycle
    "MCPWebSocketLifecycleManager",
    "get_mcp_lifecycle_manager",
    "set_mcp_lifecycle_manager",
    "create_mcp_lifecycle_manager",
    # Metrics
    "OTelMCPMetrics",
    # Config
    "is_streaming_enabled",
    "set_streaming_enabled",
    "get_streaming_max_chunk_size",
    "set_streaming_max_chunk_size",
    # Rate limiting
    "UserRateLimiterManager",
    "OutboundRateLimiter",
    "get_user_rate_limiter",
    "set_user_rate_limiter",
    "create_user_rate_limiter",
    "get_outbound_rate_limiter",
    "set_outbound_rate_limiter",
    "create_outbound_rate_limiter",
]
