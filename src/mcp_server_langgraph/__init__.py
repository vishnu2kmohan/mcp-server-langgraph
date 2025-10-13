"""
MCP Server with LangGraph.

A production-ready MCP (Model Context Protocol) server built with LangGraph,
featuring multi-LLM support, fine-grained authorization, and comprehensive observability.
"""

__version__ = "2.1.0"

# Auth exports
from mcp_server_langgraph.auth.middleware import AuthMiddleware
from mcp_server_langgraph.auth.openfga import OpenFGAClient
from mcp_server_langgraph.core.agent import AgentState, agent_graph

# Core exports
from mcp_server_langgraph.core.config import settings

# LLM exports
from mcp_server_langgraph.llm.factory import create_llm_from_config

# Observability exports
from mcp_server_langgraph.observability.telemetry import logger, metrics, tracer

__all__ = [
    "__version__",
    "settings",
    "agent_graph",
    "AgentState",
    "AuthMiddleware",
    "OpenFGAClient",
    "create_llm_from_config",
    "logger",
    "tracer",
    "metrics",
]
