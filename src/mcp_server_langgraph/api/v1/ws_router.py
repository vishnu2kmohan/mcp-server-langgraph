"""
WebSocket Router Aggregator.

Consolidates all WebSocket endpoints under a unified /api/v1/ws/* URL structure
for consistent client access patterns.

URL Mappings:
    Current URL                      -> New URL (via this router)
    /api/v1/mcp/ws                  -> /api/v1/ws/mcp
    /api/v1/mcp/tasks/ws            -> /api/v1/ws/mcp/tasks
    /api/v1/workflows/ws            -> /api/v1/ws/workflows
    /api/v1/connections/health/ws   -> /api/v1/ws/connections/health
    /api/v1/audit/stream            -> /api/v1/ws/audit
    /ws/notifications               -> /api/v1/ws/notifications
    /ws/agents/requests             -> /api/v1/ws/agents/requests
    /api/v1/ws/alerts               -> /api/v1/ws/alerts (unchanged)

Usage:
    from mcp_server_langgraph.api.v1.ws_router import ws_router
    app.include_router(ws_router, prefix="/api/v1/ws")
"""

from __future__ import annotations

from fastapi import APIRouter, WebSocket

from mcp_server_langgraph.websocket import WebSocketConfig
from mcp_server_langgraph.websocket.handlers.connections_realtime import (
    ConnectionsRealtimeHandler,
)
from mcp_server_langgraph.websocket.handlers.cost_tracking import CostTrackingHandler
from mcp_server_langgraph.websocket.handlers.heart_metrics import HeartMetricsHandler
from mcp_server_langgraph.websocket.handlers.mcp_task import MCPTaskWebSocketHandler
from mcp_server_langgraph.websocket.handlers.notifications import (
    NotificationWebSocketHandler,
)
from mcp_server_langgraph.websocket.handlers.workflow_execution import (
    WorkflowExecutionHandler,
)
from mcp_server_langgraph.websocket.handlers.connection_health import (
    ConnectionHealthHandler,
)
from mcp_server_langgraph.websocket.handlers.alert import AlertHandler
from mcp_server_langgraph.websocket.handlers.audit import AuditHandler
from mcp_server_langgraph.websocket.handlers.agent_request import AgentRequestHandler
from mcp_server_langgraph.websocket.handlers.mcp import MCPWebSocketHandler
from mcp_server_langgraph.websocket.handlers.mcp_aggregated import MCPAggregatedHandler
from mcp_server_langgraph.websocket.handlers.ai_suggestions import AISuggestionsHandler
from mcp_server_langgraph.websocket.handlers.budget_alerts import BudgetAlertsHandler
from mcp_server_langgraph.websocket.handlers.devtools import DevToolsHandler
from mcp_server_langgraph.websocket.handlers.orchestrator_status import (
    OrchestratorStatusHandler,
)
from mcp_server_langgraph.websocket.handlers.trace import TraceHandler

# Create the main WebSocket router
ws_router = APIRouter(tags=["websocket"])


# =============================================================================
# MCP Task WebSocket Endpoint
# =============================================================================


@ws_router.websocket("/mcp/tasks")
async def mcp_tasks_websocket(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for real-time MCP task status updates.

    URL: /api/v1/ws/mcp/tasks

    Uses the standardized WebSocketBase infrastructure with:
    - Message timeout enforcement
    - OpenTelemetry tracing
    - Metrics collection
    - Standard message envelope
    """
    # Lazy import to avoid circular dependencies
    from mcp_server_langgraph.api.v1.mcp import get_mcp_service

    handler = MCPTaskWebSocketHandler(
        config=WebSocketConfig(
            endpoint_name="mcp-tasks",
            require_auth=True,  # SECURITY: Require authentication for task data
            authz_resource_type="mcp",
            authz_resource_id="websocket",
            authz_required_relation="user",
            rate_limit_per_minute=600,
            message_timeout=30,
        ),
        mcp_service=get_mcp_service(),
    )
    await handler.run(websocket)


# =============================================================================
# MCP Aggregated Capabilities WebSocket Endpoint
# =============================================================================


@ws_router.websocket("/mcp/aggregated")
async def mcp_aggregated_websocket(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for real-time MCP capability change notifications.

    URL: /api/v1/ws/mcp/aggregated

    Provides real-time updates when MCP capabilities change:
    - Subscribe/unsubscribe to capability events
    - Get current capability counts
    - Receive tools_changed, resources_changed, prompts_changed events
    - Receive server_registered, server_unregistered events

    Message Types (Client -> Server):
        - subscribe: Subscribe to capability events
        - unsubscribe: Unsubscribe from capability events
        - get_counts: Get current capability counts

    Response Types (Server -> Client):
        - subscribed: Successfully subscribed
        - unsubscribed: Successfully unsubscribed
        - capability_counts: Current capability counts
        - tools_changed: Tools list has changed
        - resources_changed: Resources list has changed
        - prompts_changed: Prompts list has changed
        - server_registered: New server registered
        - server_unregistered: Server unregistered

    Uses the standardized WebSocketBase infrastructure with:
    - JWT authentication required
    - OpenFGA authorization (requires 'viewer' relation on mcp:aggregated-capabilities)
    - OpenTelemetry tracing
    - Metrics collection
    - Standard message envelope

    Reference: MCP Protocol 2025-11-25 capability aggregation
    """
    from mcp_server_langgraph.websocket.registry import get_mcp_aggregated_broadcaster

    handler = MCPAggregatedHandler(
        config=WebSocketConfig(
            endpoint_name="mcp-aggregated",
            require_auth=True,
            authz_resource_type="mcp",
            authz_resource_id="aggregated-capabilities",
            authz_required_relation="viewer",
            rate_limit_per_minute=600,
            message_timeout=30,
        ),
        broadcaster=get_mcp_aggregated_broadcaster(),
    )
    await handler.run(websocket)


# =============================================================================
# Notification WebSocket Endpoint
# =============================================================================


@ws_router.websocket("/notifications")
async def notifications_websocket(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for real-time notification streaming.

    URL: /api/v1/ws/notifications

    Uses the standardized WebSocketBase infrastructure with:
    - JWT authentication
    - OpenFGA authorization
    - OpenTelemetry tracing
    - Metrics collection
    - Standard message envelope
    """
    # Use centralized broadcaster registry
    from mcp_server_langgraph.websocket.registry import get_notification_broadcaster

    handler = NotificationWebSocketHandler(
        config=WebSocketConfig(
            endpoint_name="notifications",
            require_auth=True,
            authz_resource_type="chat",
            authz_resource_id="notifications",
            authz_required_relation="viewer",
            rate_limit_per_minute=100,
            message_timeout=30,
        ),
        broadcaster=get_notification_broadcaster(),
    )
    await handler.run(websocket)


# =============================================================================
# Connections Realtime WebSocket Endpoint
# =============================================================================


@ws_router.websocket("/connections/realtime")
async def connections_realtime_websocket(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for real-time connection status updates.

    URL: /api/v1/ws/connections/realtime

    Replaces polling-based ConnectionsPage updates with efficient push-based
    real-time updates. Uses the standardized WebSocketBase infrastructure with:
    - JWT authentication
    - OpenFGA authorization
    - OpenTelemetry tracing
    - Metrics collection
    - Standard message envelope
    """
    # Lazy import to avoid circular dependencies
    from mcp_server_langgraph.websocket.services import get_websocket_connections_service

    handler = ConnectionsRealtimeHandler(
        config=WebSocketConfig(
            endpoint_name="connections-realtime",
            require_auth=True,
            authz_resource_type="mcp_connection",
            authz_resource_id="realtime",
            authz_required_relation="viewer",
            rate_limit_per_minute=300,
            message_timeout=30,
        ),
        connection_service=get_websocket_connections_service(),
    )
    await handler.run(websocket)


# =============================================================================
# HEART Metrics WebSocket Endpoint
# =============================================================================


@ws_router.websocket("/metrics/heart")
async def heart_metrics_websocket(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for real-time HEART metrics streaming.

    URL: /api/v1/ws/metrics/heart

    Replaces polling-based useHeartDashboard.ts with efficient push-based
    real-time updates. Uses the standardized WebSocketBase infrastructure.
    """
    # Use the service adapter which wraps real services where available
    from mcp_server_langgraph.websocket.services import get_websocket_heart_metrics_service

    handler = HeartMetricsHandler(
        config=WebSocketConfig(
            endpoint_name="heart-metrics",
            require_auth=True,
            authz_resource_type="observability",
            authz_resource_id="heart",
            authz_required_relation="viewer",
            rate_limit_per_minute=100,
            message_timeout=30,
        ),
        metrics_service=get_websocket_heart_metrics_service(),
    )
    await handler.run(websocket)


# =============================================================================
# Cost Tracking WebSocket Endpoint
# =============================================================================


@ws_router.websocket("/usage/cost")
async def cost_tracking_websocket(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for real-time cost tracking during LLM operations.

    URL: /api/v1/ws/usage/cost

    Provides real-time cost updates during LLM operations with budget
    monitoring and alerts.
    """
    # Use the service adapter which wraps real services where available
    from mcp_server_langgraph.websocket.services import get_websocket_cost_service

    handler = CostTrackingHandler(
        config=WebSocketConfig(
            endpoint_name="cost-tracking",
            require_auth=True,
            authz_resource_type="cost",
            authz_resource_id="usage",
            authz_required_relation="viewer",
            rate_limit_per_minute=200,
            message_timeout=30,
        ),
        cost_service=get_websocket_cost_service(),
    )
    await handler.run(websocket)


# =============================================================================
# Workflow Execution WebSocket Endpoint
# =============================================================================


@ws_router.websocket("/workflows/{workflow_id}")
async def workflow_execution_websocket(websocket: WebSocket, workflow_id: str) -> None:
    """
    WebSocket endpoint for real-time workflow execution updates.

    URL: /api/v1/ws/workflows/{workflow_id}

    Provides real-time updates during workflow execution including:
    - Node status updates (started, completed, error)
    - Execution logs
    - Execution completion/error notifications

    Uses the standardized WebSocketBase infrastructure with:
    - JWT authentication
    - OpenFGA authorization (requires 'executor' relation on workflow)
    - OpenTelemetry tracing
    - Metrics collection
    - Standard message envelope
    """
    # Use the service adapter which wraps real services where available
    from mcp_server_langgraph.websocket.services import get_websocket_execution_service

    handler = WorkflowExecutionHandler(
        config=WebSocketConfig(
            endpoint_name="workflow-execution",
            require_auth=True,
            authz_resource_type="workflow",
            authz_resource_id=workflow_id,
            authz_required_relation="executor",
            rate_limit_per_minute=300,
            message_timeout=60,  # Longer timeout for workflow operations
        ),
        execution_service=get_websocket_execution_service(),
        workflow_id=workflow_id,
    )
    await handler.run(websocket)


# =============================================================================
# Connection Health WebSocket Endpoint
# =============================================================================


@ws_router.websocket("/connections/health")
async def connection_health_websocket(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for real-time connection health monitoring.

    URL: /api/v1/ws/connections/health

    Provides real-time connection health status updates including:
    - All connection statuses on connect
    - Subscribe to specific connection updates
    - Health check requests

    Uses the standardized WebSocketBase infrastructure with:
    - JWT authentication
    - OpenFGA authorization
    - OpenTelemetry tracing
    - Metrics collection
    - Standard message envelope
    """
    # Lazy import to avoid circular dependencies
    from mcp_server_langgraph.core.dependencies import get_connection_repository
    from mcp_server_langgraph.auth.jwt_utils import decode_jwt_token

    # Extract user from JWT token
    token = websocket.query_params.get("token")
    if not token:
        token = websocket.headers.get("Authorization", "").replace("Bearer ", "")

    owner_id = "anonymous"
    if token:
        try:
            payload = decode_jwt_token(token)
            if payload:
                owner_id = payload.get("sub") or payload.get("user_id") or "anonymous"
        except Exception:
            pass

    repo = get_connection_repository()

    handler = ConnectionHealthHandler(
        config=WebSocketConfig(
            endpoint_name="connection-health",
            require_auth=True,
            authz_resource_type="mcp_connection",
            authz_resource_id="health",
            authz_required_relation="viewer",
            rate_limit_per_minute=300,
            message_timeout=30,
        ),
        connection_repository=repo,
        owner_id=owner_id,
    )
    await handler.run(websocket)


# =============================================================================
# Alert WebSocket Endpoint
# =============================================================================


@ws_router.websocket("/alerts")
async def alert_websocket(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for real-time alert streaming.

    URL: /api/v1/ws/alerts

    Provides real-time infrastructure alerts to admin users:
    - Subscribe/unsubscribe to alert stream
    - Get recent alerts
    - Real-time alert notifications

    Uses the standardized WebSocketBase infrastructure with:
    - JWT authentication
    - OpenFGA authorization (requires 'admin' relation on dashboard:alerts)
    - OpenTelemetry tracing
    - Metrics collection
    - Standard message envelope
    """
    # Use centralized broadcaster registry
    from mcp_server_langgraph.websocket.registry import get_alert_broadcaster

    handler = AlertHandler(
        config=WebSocketConfig(
            endpoint_name="alerts",
            require_auth=True,
            authz_resource_type="dashboard",
            authz_resource_id="alerts",
            authz_required_relation="admin",
            rate_limit_per_minute=100,
            message_timeout=30,
        ),
        broadcaster=get_alert_broadcaster(),
    )
    await handler.run(websocket)


# =============================================================================
# Audit WebSocket Endpoint
# =============================================================================


@ws_router.websocket("/audit")
async def audit_websocket(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for real-time audit event streaming.

    URL: /api/v1/ws/audit

    Provides real-time audit events for compliance monitoring:
    - Filter by category, regulation, actor
    - Real-time audit event notifications

    Uses the standardized WebSocketBase infrastructure with:
    - JWT authentication
    - OpenFGA authorization (requires 'viewer' relation on logs:audit)
    - OpenTelemetry tracing
    - Metrics collection
    - Standard message envelope
    """
    # Use centralized broadcaster registry
    from mcp_server_langgraph.websocket.registry import get_audit_event_broadcaster

    handler = AuditHandler(
        config=WebSocketConfig(
            endpoint_name="audit",
            require_auth=True,
            authz_resource_type="logs",
            authz_resource_id="audit",
            authz_required_relation="viewer",
            rate_limit_per_minute=100,
            message_timeout=30,
        ),
        broadcaster=get_audit_event_broadcaster(),
    )
    await handler.run(websocket)


# =============================================================================
# Agent Request (HITL) WebSocket Endpoint
# =============================================================================


@ws_router.websocket("/agents/requests")
async def agent_request_websocket(
    websocket: WebSocket,
    session_id: str | None = None,
) -> None:
    """
    WebSocket endpoint for real-time Human-in-the-Loop (HITL) notifications.

    URL: /api/v1/ws/agents/requests

    Provides real-time HITL agent request notifications:
    - Approval requests (low confidence triggers)
    - Clarification requests (agent needs input)
    - Status updates

    Query Parameters:
        session_id: Optional session ID to filter messages

    Uses the standardized WebSocketBase infrastructure with:
    - JWT authentication
    - OpenFGA authorization (requires 'editor' relation on workflow:hitl)
    - OpenTelemetry tracing
    - Metrics collection
    - Standard message envelope
    """
    # Use centralized broadcaster registry
    from mcp_server_langgraph.websocket.registry import get_agent_request_broadcaster

    handler = AgentRequestHandler(
        config=WebSocketConfig(
            endpoint_name="agent-request",
            require_auth=True,
            authz_resource_type="workflow",
            authz_resource_id="hitl",
            authz_required_relation="editor",
            rate_limit_per_minute=200,
            message_timeout=30,
        ),
        broadcaster=get_agent_request_broadcaster(),
        session_id=session_id,
    )
    await handler.run(websocket)


# =============================================================================
# MCP WebSocket Endpoint
# =============================================================================


@ws_router.websocket("/mcp")
async def mcp_websocket(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for MCP protocol (JSON-RPC 2.0 over WebSocket).

    URL: /api/v1/ws/mcp

    Provides MCP 2025-11-25 compliant real-time bidirectional communication:
    - JSON-RPC 2.0 message handling
    - MCP protocol methods: initialize, tools/*, resources/*, prompts/*
    - Elicitation and sampling support
    - Streaming extensions ($/streaming/*)
    - Trace extensions ($/trace/*)

    Uses the standardized WebSocketBase infrastructure with:
    - Optional JWT authentication (anonymous allowed)
    - OpenTelemetry tracing
    - Metrics collection
    - Standard message envelope
    - Per-user rate limiting
    """
    handler = MCPWebSocketHandler(
        config=WebSocketConfig(
            endpoint_name="mcp",
            require_auth=False,  # Anonymous connections allowed
            rate_limit_per_minute=600,  # 10 msg/sec
            message_timeout=30,
            heartbeat_interval=30,
            idle_timeout=1800,  # 30 minutes
        ),
    )
    await handler.run(websocket)


@ws_router.websocket("/mcp/auth")
async def mcp_websocket_authenticated(websocket: WebSocket) -> None:
    """
    Authenticated MCP WebSocket endpoint with full security flow.

    URL: /api/v1/ws/mcp/auth

    Requires valid JWT token (via query param or Authorization header).
    Validates token via Keycloak and checks permissions via OpenFGA.

    Uses the standardized WebSocketBase infrastructure with:
    - JWT authentication required
    - OpenFGA authorization (requires 'user' relation on mcp:websocket)
    - OpenTelemetry tracing
    - Metrics collection
    - Standard message envelope
    - Per-user rate limiting
    """
    handler = MCPWebSocketHandler(
        config=WebSocketConfig(
            endpoint_name="mcp-auth",
            require_auth=True,
            authz_resource_type="mcp",
            authz_resource_id="websocket",
            authz_required_relation="user",
            rate_limit_per_minute=600,  # 10 msg/sec
            message_timeout=30,
            heartbeat_interval=30,
            idle_timeout=1800,  # 30 minutes
        ),
    )
    await handler.run(websocket)


@ws_router.websocket("/mcp/{session_id}")
async def mcp_websocket_with_session(
    websocket: WebSocket,
    session_id: str,
) -> None:
    """
    MCP WebSocket endpoint with explicit session ID.

    URL: /api/v1/ws/mcp/{session_id}

    Allows clients to specify a session ID for connection resumption
    and context preservation.

    Uses the standardized WebSocketBase infrastructure with:
    - Optional JWT authentication
    - OpenTelemetry tracing
    - Metrics collection
    - Standard message envelope
    - Per-user rate limiting
    """
    handler = MCPWebSocketHandler(
        config=WebSocketConfig(
            endpoint_name="mcp-session",
            require_auth=False,  # Anonymous allowed, auth is optional
            rate_limit_per_minute=600,  # 10 msg/sec
            message_timeout=30,
            heartbeat_interval=30,
            idle_timeout=1800,  # 30 minutes
        ),
        session_id=session_id,
    )
    await handler.run(websocket)


# =============================================================================
# AI Suggestions WebSocket Endpoint
# =============================================================================


@ws_router.websocket("/ai/suggestions")
async def ai_suggestions_websocket(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for real-time AI suggestion streaming.

    URL: /api/v1/ws/ai/suggestions

    Provides real-time AI-powered suggestions for the Studio frontend:
    - Typing suggestions based on context
    - Session-aware completions
    - Accept/reject feedback for learning

    Message Types (Client -> Server):
        - suggestion_request: Request an AI suggestion
        - suggestion_accept: User accepted the suggestion
        - suggestion_reject: User rejected the suggestion
        - context_update: Update session context

    Message Types (Server -> Client):
        - suggestion_response: AI suggestion response
        - error: Error response

    Uses the standardized WebSocketBase infrastructure with:
    - JWT authentication required
    - OpenFGA authorization (requires 'user' relation on ai:suggestions)
    - OpenTelemetry tracing
    - Metrics collection
    - Standard message envelope
    - Rate limiting (300 requests/minute)
    """
    handler = AISuggestionsHandler(
        config=WebSocketConfig(
            endpoint_name="ai-suggestions",
            require_auth=True,
            authz_resource_type="ai",
            authz_resource_id="suggestions",
            authz_required_relation="user",
            rate_limit_per_minute=300,
            message_timeout=30,
            max_message_size=65536,  # 64KB max message size
        ),
    )
    await handler.run(websocket)


# =============================================================================
# Trace WebSocket Endpoint
# =============================================================================


@ws_router.websocket("/traces")
async def traces_websocket(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for real-time trace/span streaming.

    URL: /api/v1/ws/traces

    Provides real-time distributed trace streaming:
    - Filter by service_name, operation_name, trace_id
    - Filter by minimum duration and status
    - Real-time span updates as they are collected

    Message Types (Client -> Server):
        - subscribe: Subscribe to trace events
        - unsubscribe: Unsubscribe from trace events
        - set_filter: Set trace filter criteria
        - clear_filter: Clear all filters
        - get_recent: Get recent traces

    Response Types (Server -> Client):
        - subscribed: Successfully subscribed
        - unsubscribed: Successfully unsubscribed
        - filter_updated: Filter has been updated
        - filter_cleared: Filter has been cleared
        - recent_traces: Recent trace data
        - trace_span: Real-time trace span update
        - error: Error message

    Uses the standardized WebSocketBase infrastructure with:
    - JWT authentication required
    - OpenFGA authorization (requires 'viewer' relation on traces:stream)
    - OpenTelemetry tracing
    - Metrics collection
    - Standard message envelope
    """
    from mcp_server_langgraph.websocket.registry import get_trace_broadcaster

    handler = TraceHandler(
        config=WebSocketConfig(
            endpoint_name="traces",
            require_auth=True,
            authz_resource_type="traces",
            authz_resource_id="stream",
            authz_required_relation="viewer",
            rate_limit_per_minute=600,
            message_timeout=30,
        ),
        broadcaster=get_trace_broadcaster(),
    )
    await handler.run(websocket)


# =============================================================================
# Budget Alerts WebSocket Endpoint
# =============================================================================


@ws_router.websocket("/budget/alerts")
async def budget_alerts_websocket(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for real-time budget alert notifications.

    URL: /api/v1/ws/budget/alerts

    Provides real-time budget alerts for cost management:
    - Subscribe to specific entity budget alerts (organization, project, team, user)
    - Subscribe to all budget alerts (admin mode)
    - Receive real-time budget status changes (warning, critical, exceeded)

    Message Types (Client -> Server):
        - subscribe_entities: Subscribe to alerts for specific entity IDs
        - subscribe_all: Subscribe to all budget alerts
        - unsubscribe: Unsubscribe from alerts

    Response Types (Server -> Client):
        - subscription_confirmed: Successfully subscribed
        - budget_alert: Real-time budget status update
        - error: Error message

    Uses the standardized WebSocketBase infrastructure with:
    - JWT authentication required
    - OpenFGA authorization (requires 'viewer' relation on cost:budget)
    - OpenTelemetry tracing
    - Metrics collection
    - Standard message envelope
    """
    from mcp_server_langgraph.websocket.registry import get_budget_alert_broadcaster

    handler = BudgetAlertsHandler(
        config=WebSocketConfig(
            endpoint_name="budget-alerts",
            require_auth=True,
            authz_resource_type="cost",
            authz_resource_id="budget",
            authz_required_relation="viewer",
            rate_limit_per_minute=200,
            message_timeout=30,
        ),
        broadcaster=get_budget_alert_broadcaster(),
    )
    await handler.run(websocket)


# =============================================================================
# DevTools WebSocket Endpoint
# =============================================================================


@ws_router.websocket("/devtools")
async def devtools_websocket(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for DevTools console and network events.

    URL: /api/v1/ws/devtools

    Provides real-time DevTools events for the frontend DevTools panel:
    - Console log entries (info, warning, error, debug)
    - Network request events (start, update, complete)
    - Context-aware filtering by session/workflow ID

    Message Types (Client -> Server):
        - subscribe: Subscribe to DevTools events
        - unsubscribe: Unsubscribe from events
        - set_context: Update context filter (session/workflow ID)

    Response Types (Server -> Client):
        - subscribed: Successfully subscribed
        - unsubscribed: Successfully unsubscribed
        - context_updated: Context filter updated
        - console: Console log entry
        - network: Network request start
        - network_update: Network request update/completion

    Uses the standardized WebSocketBase infrastructure with:
    - JWT authentication required
    - OpenFGA authorization (requires 'viewer' relation on dashboard:devtools)
    - OpenTelemetry tracing
    - Metrics collection
    - Standard message envelope
    """
    from mcp_server_langgraph.websocket.registry import get_devtools_broadcaster

    handler = DevToolsHandler(
        config=WebSocketConfig(
            endpoint_name="devtools",
            require_auth=True,
            authz_resource_type="dashboard",
            authz_resource_id="devtools",
            authz_required_relation="viewer",
            rate_limit_per_minute=300,
            message_timeout=30,
        ),
        broadcaster=get_devtools_broadcaster(),
    )
    await handler.run(websocket)


# =============================================================================
# Migration Status
# =============================================================================
#
# Individual WebSocket routers are included here as they are migrated
# to use the new WebSocketBase class. This provides a clean migration path:
#
# 1. Each endpoint is migrated to WebSocketBase
# 2. The old router continues to work at the old URL
# 3. The new standardized URL is added via this router
# 4. Eventually, old URLs can be deprecated
#
# Current migration status:
# - [x] MCP WebSocket (/mcp) - Migrated!
# - [x] MCP Task WebSocket (/mcp/tasks) - Migrated!
# - [x] Workflow Execution WebSocket (/workflows/{workflow_id}) - Migrated!
# - [x] Connection Health WebSocket (/connections/health) - Migrated!
# - [x] Notification WebSocket (/notifications) - Migrated!
# - [x] Alert WebSocket (/alerts) - Migrated!
# - [x] Audit WebSocket (/audit) - Migrated!
# - [x] Agent Request WebSocket (/agents/requests) - Migrated!
#
# New endpoints added:
# - [x] Connections Realtime WebSocket (/connections/realtime) - New!
# - [x] HEART Metrics WebSocket (/metrics/heart) - New!
# - [x] Cost Tracking WebSocket (/usage/cost) - New!
# - [x] AI Suggestions WebSocket (/ai/suggestions) - New!
# - [x] Trace WebSocket (/traces) - New!
# - [x] MCP Aggregated WebSocket (/mcp/aggregated) - New!
# - [x] Orchestrator Status WebSocket (/orchestrator/status) - New!


# =============================================================================
# Orchestrator Status WebSocket Endpoint
# =============================================================================


@ws_router.websocket("/orchestrator/status")
async def orchestrator_status_websocket(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for real-time AI orchestrator status updates.

    URL: /api/v1/ws/orchestrator/status

    Provides real-time status updates from the AI orchestrators:
    - Orchestrator status changes (idle, processing, error)
    - Task lifecycle events (started, completed, failed)
    - Support for all task categories (UX, SESSION, CONVERSATION, CANVAS, etc.)

    This is a pub/sub endpoint - clients subscribe and receive updates
    as orchestrators process tasks.

    Message Types (Client -> Server):
        - subscribe: Subscribe to status updates
        - unsubscribe: Unsubscribe from status updates
        - get_status: Request current orchestrator status

    Response Types (Server -> Client):
        - subscribed: Successfully subscribed
        - unsubscribed: Successfully unsubscribed
        - status: Current orchestrator status
        - orchestrator_status: Real-time status update (pushed)
        - task_started: Task started (pushed)
        - task_completed: Task completed (pushed)
        - task_failed: Task failed (pushed)

    Example orchestrator_status message:
        {
            "type": "orchestrator_status",
            "payload": {
                "status": "processing",
                "message": "Analyzing persona...",
                "task_type": "persona_analysis",
                "category": "ux"
            }
        }

    Uses the standardized WebSocketBase infrastructure with:
    - JWT authentication required
    - OpenFGA authorization (requires 'viewer' relation on ai:orchestrator)
    - OpenTelemetry tracing
    - Metrics collection
    - Standard message envelope

    Feature Flag: FF_ENABLE_ORCHESTRATOR_STATUS_WEBSOCKET (default: True)
    """
    from mcp_server_langgraph.core.feature_flags import feature_flags
    from mcp_server_langgraph.websocket.registry import get_orchestrator_status_broadcaster

    # Check feature flag before allowing connection
    if not feature_flags.enable_orchestrator_status_websocket:
        await websocket.close(code=4003, reason="Orchestrator status WebSocket disabled")
        return

    handler = OrchestratorStatusHandler(
        config=WebSocketConfig(
            endpoint_name="orchestrator-status",
            require_auth=True,
            authz_resource_type="ai",
            authz_resource_id="orchestrator",
            authz_required_relation="viewer",
            rate_limit_per_minute=200,
            message_timeout=30,
        ),
        broadcaster=get_orchestrator_status_broadcaster(),
    )
    await handler.run(websocket)
