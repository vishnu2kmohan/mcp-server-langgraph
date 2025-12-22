"""
WebSocket Service Adapters.

Provides service adapters for WebSocket handlers that wrap existing services
or provide stub implementations for features under development.

Services:
- ConnectionsServiceAdapter: Wraps ConnectionRepository for WebSocket use
- CostTrackingServiceAdapter: Wraps CostServiceImpl for WebSocket use
- HeartMetricsServiceAdapter: Wraps metrics infrastructure for HEART framework
- WorkflowExecutionServiceAdapter: Wraps workflow execution for real-time updates
"""

from mcp_server_langgraph.websocket.services.connections import (
    ConnectionsServiceAdapter,
    get_websocket_connections_service,
)
from mcp_server_langgraph.websocket.services.cost_tracking import (
    CostTrackingServiceAdapter,
    get_websocket_cost_service,
)
from mcp_server_langgraph.websocket.services.heart_metrics import (
    HeartMetricsServiceAdapter,
    get_websocket_heart_metrics_service,
)
from mcp_server_langgraph.websocket.services.workflow_execution import (
    WorkflowExecutionServiceAdapter,
    get_websocket_execution_service,
)

__all__ = [
    "ConnectionsServiceAdapter",
    "CostTrackingServiceAdapter",
    "HeartMetricsServiceAdapter",
    "WorkflowExecutionServiceAdapter",
    "get_websocket_connections_service",
    "get_websocket_cost_service",
    "get_websocket_heart_metrics_service",
    "get_websocket_execution_service",
]
