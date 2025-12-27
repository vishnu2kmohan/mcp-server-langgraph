"""
WebSocket Handlers Module.

Provides standardized WebSocket handlers for various endpoints,
all built on the WebSocketBase class for consistent behavior.

Available Handlers:
    - MCPWebSocketHandler: MCP protocol WebSocket (JSON-RPC 2.0)
    - MCPTaskWebSocketHandler: Real-time task status updates
    - MCPAggregatedHandler: Real-time MCP capability change notifications
    - NotificationWebSocketHandler: Real-time notification streaming
    - ConnectionsRealtimeHandler: Real-time connection status updates
    - ConnectionHealthHandler: Real-time connection health monitoring
    - AlertHandler: Real-time alert streaming (admin-only)
    - AuditHandler: Real-time audit event streaming
    - AgentRequestHandler: Real-time HITL agent request notifications
    - HeartMetricsHandler: Real-time HEART metrics streaming
    - CostTrackingHandler: Real-time cost tracking during LLM operations
    - WorkflowExecutionHandler: Real-time workflow execution updates
    - AISuggestionsHandler: Real-time AI suggestion streaming
    - TraceHandler: Real-time trace/span streaming
"""

from mcp_server_langgraph.websocket.handlers.agent_request import AgentRequestHandler
from mcp_server_langgraph.websocket.handlers.ai_suggestions import AISuggestionsHandler
from mcp_server_langgraph.websocket.handlers.alert import AlertHandler
from mcp_server_langgraph.websocket.handlers.audit import AuditHandler
from mcp_server_langgraph.websocket.handlers.connection_health import (
    ConnectionHealthHandler,
)
from mcp_server_langgraph.websocket.handlers.connections_realtime import (
    ConnectionsRealtimeHandler,
)
from mcp_server_langgraph.websocket.handlers.cost_tracking import CostTrackingHandler
from mcp_server_langgraph.websocket.handlers.heart_metrics import HeartMetricsHandler
from mcp_server_langgraph.websocket.handlers.mcp import MCPWebSocketHandler
from mcp_server_langgraph.websocket.handlers.mcp_aggregated import (
    MCPAggregatedHandler,
)
from mcp_server_langgraph.websocket.handlers.mcp_task import MCPTaskWebSocketHandler
from mcp_server_langgraph.websocket.handlers.notifications import (
    NotificationWebSocketHandler,
)
from mcp_server_langgraph.websocket.handlers.trace import TraceHandler
from mcp_server_langgraph.websocket.handlers.workflow_execution import (
    WorkflowExecutionHandler,
)

__all__ = [
    "AgentRequestHandler",
    "AISuggestionsHandler",
    "AlertHandler",
    "AuditHandler",
    "ConnectionHealthHandler",
    "ConnectionsRealtimeHandler",
    "CostTrackingHandler",
    "HeartMetricsHandler",
    "MCPAggregatedHandler",
    "MCPTaskWebSocketHandler",
    "MCPWebSocketHandler",
    "NotificationWebSocketHandler",
    "TraceHandler",
    "WorkflowExecutionHandler",
]
