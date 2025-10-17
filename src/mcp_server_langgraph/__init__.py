"""
MCP Server with LangGraph.

A production-ready MCP (Model Context Protocol) server built with LangGraph,
featuring multi-LLM support, fine-grained authorization, and comprehensive observability.
"""

import sys
from pathlib import Path

# Read version from pyproject.toml (single source of truth)
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        # Fallback if tomli not available (shouldn't happen with uv)
        tomllib = None

if tomllib:
    try:
        pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
        with open(pyproject_path, "rb") as f:
            pyproject_data = tomllib.load(f)
        __version__ = pyproject_data["project"]["version"]
    except Exception:
        # Fallback if reading fails
        __version__ = "2.7.0"
else:
    __version__ = "2.7.0"

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
