"""
Main v1 Router

Aggregates all v1 API routers into a single router for mounting.

Usage:
    from mcp_server_langgraph.api.v1 import v1_router
    app.include_router(v1_router, prefix="/api/v1")
"""

from fastapi import APIRouter

from mcp_server_langgraph.api.v1.chat import chat_router
from mcp_server_langgraph.api.v1.cost import cost_router
from mcp_server_langgraph.api.v1.features import features_router
from mcp_server_langgraph.api.v1.mcp_websocket import mcp_websocket_router
from mcp_server_langgraph.api.v1.observability import observability_router
from mcp_server_langgraph.api.v1.sessions import sessions_router
from mcp_server_langgraph.api.v1.vectors import router as vectors_router
from mcp_server_langgraph.api.v1.workflow_bootstrap import workflow_bootstrap_router
from mcp_server_langgraph.api.v1.workflows import workflows_router

# Main v1 router that includes all sub-routers
v1_router = APIRouter()

# Include feature flags endpoint
v1_router.include_router(features_router)

# Include workflows CRUD endpoints
v1_router.include_router(workflows_router)

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

# Include vectors proxy endpoints (Qdrant with OpenFGA authorization - ADR-0068)
v1_router.include_router(vectors_router, prefix="/vectors", tags=["vectors"])
