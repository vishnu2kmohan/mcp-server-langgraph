"""
Main v1 Router

Aggregates all v1 API routers into a single router for mounting.

Usage:
    from mcp_server_langgraph.api.v1 import v1_router
    app.include_router(v1_router, prefix="/api/v1")
"""

from fastapi import APIRouter

from mcp_server_langgraph.api.v1.admin import admin_router
from mcp_server_langgraph.api.v1.agents import agents_router
from mcp_server_langgraph.api.v1.auth import auth_router
from mcp_server_langgraph.api.v1.notifications import notifications_router
from mcp_server_langgraph.api.v1.notification_preferences import notification_preferences_router
from mcp_server_langgraph.api.v1.ai import ai_router
from mcp_server_langgraph.api.v1.audit import router as unified_audit_router
from mcp_server_langgraph.api.v1.audit_websocket import router as audit_ws_router
from mcp_server_langgraph.api.v1.compliance_reports import router as compliance_reports_router
from mcp_server_langgraph.api.v1.chat import chat_router
from mcp_server_langgraph.api.v1.connection_audit import audit_router as connection_audit_router
from mcp_server_langgraph.api.v1.connection_health_ws import connection_health_router
from mcp_server_langgraph.api.v1.connection_templates import templates_router
from mcp_server_langgraph.api.v1.connections import connections_router
from mcp_server_langgraph.api.v1.connections_bulk import bulk_router as connections_bulk_router
from mcp_server_langgraph.api.v1.cost import cost_router
from mcp_server_langgraph.api.v1.features import features_router
from mcp_server_langgraph.api.v1.identity_providers import router as identity_providers_router
from mcp_server_langgraph.api.v1.mcp import mcp_router
from mcp_server_langgraph.api.v1.mcp_task_websocket import mcp_task_ws_router
from mcp_server_langgraph.api.v1.mcp_websocket import mcp_websocket_router
from mcp_server_langgraph.api.v1.observability import observability_router
from mcp_server_langgraph.api.v1.projects import projects_router
from mcp_server_langgraph.api.v1.sessions import sessions_router
from mcp_server_langgraph.api.v1.user import user_router
from mcp_server_langgraph.api.v1.user_preferences import user_preferences_router
from mcp_server_langgraph.api.v1.vectors import router as vectors_router
from mcp_server_langgraph.api.v1.workflow_bootstrap import workflow_bootstrap_router
from mcp_server_langgraph.api.v1.workflows import workflows_router
from mcp_server_langgraph.api.v1.workflow_execution_ws import workflow_execution_router
from mcp_server_langgraph.api.v1.workflow_executions import workflow_executions_router

# Main v1 router that includes all sub-routers
v1_router = APIRouter()

# Include feature flags endpoint
v1_router.include_router(features_router)

# Include user info endpoint (/me for persona detection)
v1_router.include_router(user_router)

# Include OAuth2 Authorization Code + PKCE endpoints
v1_router.include_router(auth_router)

# Include projects CRUD endpoints (Unified Workspace Paradigm)
v1_router.include_router(projects_router)

# Include workflows CRUD endpoints
v1_router.include_router(workflows_router)

# Include workflow execution WebSocket endpoint
v1_router.include_router(workflow_execution_router)

# Include workflow execution history REST endpoint
v1_router.include_router(workflow_executions_router)

# Include sessions CRUD endpoints
v1_router.include_router(sessions_router)

# Include workflow bootstrap endpoints
v1_router.include_router(workflow_bootstrap_router)

# Include chat endpoints
v1_router.include_router(chat_router)

# Include cost dashboard endpoints
v1_router.include_router(cost_router)

# Include observability endpoints
v1_router.include_router(observability_router)

# Include MCP WebSocket endpoints
v1_router.include_router(mcp_websocket_router)

# Include MCP REST endpoints (MCP Protocol 2025-11-25 features)
v1_router.include_router(mcp_router, prefix="/mcp")

# Include MCP task status WebSocket endpoint
v1_router.include_router(mcp_task_ws_router)

# Include vectors proxy endpoints (Qdrant with OpenFGA authorization - ADR-0068)
v1_router.include_router(vectors_router, prefix="/vectors", tags=["vectors"])

# Include MCP connections CRUD endpoints
v1_router.include_router(connections_router)

# Include connection health WebSocket endpoint
v1_router.include_router(connection_health_router)

# Include connection templates endpoint
v1_router.include_router(templates_router)

# Include connections bulk operations endpoint
v1_router.include_router(connections_bulk_router)

# Include connection audit logging endpoint
v1_router.include_router(connection_audit_router)

# Include agents config endpoint
v1_router.include_router(agents_router)

# Include admin endpoints (audit logs, etc.)
v1_router.include_router(admin_router)

# Include unified audit logging endpoints (FedRAMP/HIPAA/GDPR/SOC2/EU AI Act)
v1_router.include_router(unified_audit_router, prefix="/audit", tags=["audit"])

# Include audit WebSocket streaming endpoint for real-time monitoring
v1_router.include_router(audit_ws_router, prefix="/audit", tags=["audit"])

# Include compliance report endpoints
v1_router.include_router(compliance_reports_router, prefix="/compliance", tags=["compliance"])

# Include AI-native endpoints (node config assistance, suggestions)
v1_router.include_router(ai_router, prefix="/ai", tags=["ai"])

# Include push notification endpoints (PWA support)
v1_router.include_router(notifications_router)

# Include notification preferences endpoints
v1_router.include_router(notification_preferences_router)

# Include user preferences endpoints (theme, accessibility, model defaults)
v1_router.include_router(user_preferences_router)

# Include identity provider discovery endpoints (SSO IdP discovery for login page)
v1_router.include_router(identity_providers_router)
