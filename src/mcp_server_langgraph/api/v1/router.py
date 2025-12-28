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
from mcp_server_langgraph.api.v1.config import config_router
from mcp_server_langgraph.api.v1.agent_requests import agent_request_router
from mcp_server_langgraph.api.v1.artifacts import artifacts_router
from mcp_server_langgraph.api.v1.auth import auth_router
from mcp_server_langgraph.api.v1.notifications import notifications_router
from mcp_server_langgraph.api.v1.notification_preferences import notification_preferences_router
from mcp_server_langgraph.api.v1.ai import ai_router
from mcp_server_langgraph.api.v1.ai_ux import ai_ux_router
from mcp_server_langgraph.api.v1.studio_ai import studio_ai_router
from mcp_server_langgraph.api.v1.audit import router as unified_audit_router
from mcp_server_langgraph.api.v1.compliance_reports import router as compliance_reports_router
from mcp_server_langgraph.api.v1.chat import chat_router
from mcp_server_langgraph.api.v1.connection_audit import audit_router as connection_audit_router
from mcp_server_langgraph.api.v1.connection_templates import templates_router
from mcp_server_langgraph.api.v1.connections import connections_router
from mcp_server_langgraph.api.v1.connections_bulk import bulk_router as connections_bulk_router
from mcp_server_langgraph.api.v1.cost import cost_router
from mcp_server_langgraph.api.v1.features import features_router
from mcp_server_langgraph.api.v1.identity_providers import router as identity_providers_router
from mcp_server_langgraph.api.v1.mcp import mcp_router
from mcp_server_langgraph.api.v1.mcp_aggregated import aggregated_router as mcp_aggregated_router
from mcp_server_langgraph.api.v1.mcp_websocket import mcp_websocket_router
from mcp_server_langgraph.api.v1.observability import observability_router
from mcp_server_langgraph.api.v1.projects import projects_router
from mcp_server_langgraph.api.v1.sessions import sessions_router
from mcp_server_langgraph.api.v1.user import user_router
from mcp_server_langgraph.api.v1.user_preferences import user_preferences_router
from mcp_server_langgraph.api.v1.session_export import session_export_router
from mcp_server_langgraph.api.v1.project_context import project_context_router
from mcp_server_langgraph.api.v1.vectors import router as vectors_router
from mcp_server_langgraph.api.v1.workflow_bootstrap import workflow_bootstrap_router
from mcp_server_langgraph.api.v1.workflows import workflows_router
from mcp_server_langgraph.api.v1.workflow_executions import workflow_executions_router
from mcp_server_langgraph.api.v1.sandbox import router as sandbox_router
from mcp_server_langgraph.api.v1.code_execution import router as code_execution_router

# Alert infrastructure imports (ADR-0026 - Comprehensive Client Resilience Patterns)
# Note: Alert WebSocket moved to consolidated ws_router (ADR-0068)
from mcp_server_langgraph.api.v1.alertmanager_webhook import alertmanager_webhook_router
from mcp_server_langgraph.api.v1.remediation_approvals import remediation_approval_router
from mcp_server_langgraph.api.v1.alert_recommendations import alert_recommendation_router

# UX measurement and feedback endpoints
from mcp_server_langgraph.api.v1.analytics import router as analytics_router
from mcp_server_langgraph.api.v1.feedback import router as feedback_router
from mcp_server_langgraph.api.v1.surveys import router as surveys_router

# Frontend infrastructure endpoints
from mcp_server_langgraph.api.v1.frontend_cache import frontend_cache_router

# Session control endpoints
from mcp_server_langgraph.api.v1.interrupt import router as interrupt_router

# Note: marketplace_admin uses factory pattern (create_marketplace_router) requiring DI
# It is registered separately during application bootstrap if marketplace feature is enabled

# Main v1 router that includes all sub-routers
v1_router = APIRouter()

# Include feature flags endpoint
v1_router.include_router(features_router)

# Include server config defaults endpoint (12-Factor App - frontend hydration)
v1_router.include_router(config_router)

# Include user info endpoint (/me for persona detection)
v1_router.include_router(user_router)

# Include OAuth2 Authorization Code + PKCE endpoints
v1_router.include_router(auth_router)

# Include projects CRUD endpoints (Unified Workspace Paradigm)
v1_router.include_router(projects_router)

# Include workflows CRUD endpoints
v1_router.include_router(workflows_router)

# Note: Workflow execution WebSocket moved to consolidated ws_router (ADR-0068)

# Include workflow execution history REST endpoint
v1_router.include_router(workflow_executions_router)

# Include sessions CRUD endpoints
v1_router.include_router(sessions_router)

# Include artifacts CRUD endpoints (Studio Canvas feature)
v1_router.include_router(artifacts_router)

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

# Include MCP aggregated capabilities REST endpoints (MCP Protocol 2025-11-25)
# Provides /mcp/aggregated/tools, /mcp/aggregated/resources, /mcp/aggregated/prompts, /mcp/aggregated/servers
v1_router.include_router(mcp_aggregated_router)

# Note: MCP task status WebSocket moved to consolidated ws_router (ADR-0068)

# Include vectors proxy endpoints (Qdrant with OpenFGA authorization - ADR-0068)
v1_router.include_router(vectors_router, prefix="/vectors", tags=["vectors"])

# Include MCP connections CRUD endpoints
v1_router.include_router(connections_router)

# Note: Connection health WebSocket moved to consolidated ws_router (ADR-0068)

# Include connection templates endpoint
v1_router.include_router(templates_router)

# Include connections bulk operations endpoint
v1_router.include_router(connections_bulk_router)

# Include connection audit logging endpoint
v1_router.include_router(connection_audit_router)

# Include agents config endpoint
v1_router.include_router(agents_router)

# Include agent HITL request endpoints (approval, rejection, clarification)
v1_router.include_router(agent_request_router)

# Include admin endpoints (audit logs, etc.)
v1_router.include_router(admin_router)

# Include unified audit logging endpoints (FedRAMP/HIPAA/GDPR/SOC2/EU AI Act)
v1_router.include_router(unified_audit_router, prefix="/audit", tags=["audit"])

# Note: Audit WebSocket streaming moved to consolidated ws_router (ADR-0068)

# Include compliance report endpoints
v1_router.include_router(compliance_reports_router, prefix="/compliance", tags=["compliance"])

# Include AI-native endpoints (node config assistance, suggestions)
v1_router.include_router(ai_router, prefix="/ai", tags=["ai"])

# Include AI UX endpoints (disclosure, nudges, error recovery, onboarding, metrics)
v1_router.include_router(ai_ux_router, prefix="/ai", tags=["ai-ux"])

# Sandbox runner for high-risk operations (bash, etc.)
v1_router.include_router(sandbox_router, tags=["sandbox"])

# Include sandboxed code execution endpoint for Studio Canvas
v1_router.include_router(code_execution_router, tags=["code-execution"])

# Include Studio AI endpoints (unified StudioShell AI capabilities - Sprint 1)
v1_router.include_router(studio_ai_router, prefix="/studio", tags=["studio-ai"])

# Include push notification endpoints (PWA support)
v1_router.include_router(notifications_router)

# Include notification preferences endpoints
v1_router.include_router(notification_preferences_router)

# Include user preferences endpoints (theme, accessibility, model defaults)
v1_router.include_router(user_preferences_router)

# Include identity provider discovery endpoints (SSO IdP discovery for login page)
v1_router.include_router(identity_providers_router)

# Include session export endpoints
v1_router.include_router(session_export_router)

# Include project context endpoints
v1_router.include_router(project_context_router)

# Include alert infrastructure endpoints (ADR-0026 - Comprehensive Client Resilience Patterns)
# Note: Alert WebSocket moved to consolidated ws_router (ADR-0068)

# Alertmanager webhook receiver for Mimir/Prometheus alerts
v1_router.include_router(alertmanager_webhook_router, tags=["webhooks"])

# Remediation approval queue REST API
v1_router.include_router(remediation_approval_router, tags=["remediations"])

# Alert recommendation REST API (AI-powered analysis)
v1_router.include_router(alert_recommendation_router, tags=["alerts"])

# Skills management REST API (auto-update, marketplace)
from mcp_server_langgraph.api.v1.skills import router as skills_router

v1_router.include_router(skills_router, tags=["skills"])

# =============================================================================
# UX Measurement & Feedback Endpoints
# =============================================================================
# HEART analytics for UX measurement (Happiness, Engagement, Adoption, Retention, Task Success)
v1_router.include_router(analytics_router, prefix="/analytics", tags=["analytics"])

# User feedback collection (hallucination reports, message ratings)
v1_router.include_router(feedback_router, prefix="/feedback", tags=["feedback"])

# SUS (System Usability Scale) surveys
v1_router.include_router(surveys_router, prefix="/surveys", tags=["surveys"])

# =============================================================================
# Frontend Infrastructure Endpoints
# =============================================================================
# Redis L2 cache for frontend useTieredCache hook (cross-tab sharing)
v1_router.include_router(frontend_cache_router, tags=["frontend-cache"])

# =============================================================================
# Session Control Endpoints
# =============================================================================
# Session interrupt control (Claude Agent SDK pattern)
v1_router.include_router(interrupt_router, tags=["interrupt"])

# Note: Admin marketplace management (marketplace_admin) uses factory pattern
# It is registered separately during application bootstrap if marketplace feature is enabled

# =============================================================================
# Consolidated WebSocket Router (ADR-0068 - WebSocket Standardization)
# =============================================================================
# All WebSocket endpoints consolidated under /api/v1/ws/* for consistent access
# This replaces scattered WebSocket routes with a unified structure:
#   /api/v1/ws/mcp          - MCP WebSocket
#   /api/v1/ws/mcp/tasks    - MCP task status streaming
#   /api/v1/ws/workflows    - Workflow execution streaming
#   /api/v1/ws/connections  - Connection health monitoring
#   /api/v1/ws/audit        - Audit log streaming
#   /api/v1/ws/notifications - Push notifications
#   /api/v1/ws/agents       - Agent request (HITL) streaming
#   /api/v1/ws/alerts       - Alert streaming (admin)
#   /api/v1/ws/metrics/heart - HEART metrics streaming
#   /api/v1/ws/usage/cost   - Cost tracking streaming
from mcp_server_langgraph.api.v1.ws_router import ws_router

v1_router.include_router(ws_router, prefix="/ws", tags=["websocket"])
