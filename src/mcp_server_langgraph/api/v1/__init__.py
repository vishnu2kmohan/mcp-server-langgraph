"""
Unified API v1 Routers

Consolidates all API endpoints under /api/v1/* for the unified BFF architecture.

Routes:
    /api/v1/features - UI feature flags for frontend
    /api/v1/workflows - Workflow builder operations
    /api/v1/sessions - Chat session management
    /api/v1/chat - Real-time chat endpoints
    /api/v1/cost - Cost tracking and analysis
    /api/v1/observability - Trace and metrics access
    /api/v1/mcp/ws - MCP WebSocket endpoint (MCP 2025-11-25 compliant)
    /api/v1/vectors - Qdrant vector database proxy (ADR-0068)
"""

from mcp_server_langgraph.api.v1.chat import chat_router
from mcp_server_langgraph.api.v1.cost import cost_router
from mcp_server_langgraph.api.v1.features import features_router
from mcp_server_langgraph.api.v1.mcp_websocket import mcp_websocket_router
from mcp_server_langgraph.api.v1.observability import observability_router
from mcp_server_langgraph.api.v1.router import v1_router
from mcp_server_langgraph.api.v1.sessions import sessions_router
from mcp_server_langgraph.api.v1.vectors import router as vectors_router
from mcp_server_langgraph.api.v1.workflows import workflows_router

__all__ = [
    "v1_router",
    "chat_router",
    "cost_router",
    "features_router",
    "mcp_websocket_router",
    "observability_router",
    "sessions_router",
    "vectors_router",
    "workflows_router",
]
