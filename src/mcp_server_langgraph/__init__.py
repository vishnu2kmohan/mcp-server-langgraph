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
        __version__ = "2.8.0"
else:
    __version__ = "2.8.0"

# Core exports (lightweight - eagerly imported)
from mcp_server_langgraph.core.config import settings

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


def __getattr__(name: str):  # type: ignore[no-untyped-def]
    """
    Lazy import heavy dependencies on demand.

    This prevents ModuleNotFoundError for users who don't have optional dependencies
    installed. Heavy modules are only loaded when actually accessed.

    Pattern:
        import mcp_server_langgraph           # ✓ Fast, no heavy deps loaded
        from mcp_server_langgraph import settings  # ✓ Fast, lightweight
        from mcp_server_langgraph import AuthMiddleware  # Loads FastAPI, OpenFGA only when needed

    Raises:
        AttributeError: If module attribute doesn't exist
    """
    # Heavy auth modules (require FastAPI, OpenFGA SDK)
    if name == "AuthMiddleware":
        from mcp_server_langgraph.auth.middleware import AuthMiddleware

        return AuthMiddleware
    elif name == "OpenFGAClient":
        from mcp_server_langgraph.auth.openfga import OpenFGAClient

        return OpenFGAClient

    # Heavy agent modules (require LangGraph, LangChain)
    elif name == "AgentState":
        from mcp_server_langgraph.core.agent import AgentState

        return AgentState
    elif name == "agent_graph":
        from mcp_server_langgraph.core.agent import agent_graph

        return agent_graph

    # Heavy LLM modules (require langchain_core, sentence_transformers, etc.)
    elif name == "create_llm_from_config":
        from mcp_server_langgraph.llm.factory import create_llm_from_config

        return create_llm_from_config

    # Observability modules (potentially heavy with OpenTelemetry)
    elif name == "logger":
        from mcp_server_langgraph.observability.telemetry import logger

        return logger
    elif name == "tracer":
        from mcp_server_langgraph.observability.telemetry import tracer

        return tracer
    elif name == "metrics":
        from mcp_server_langgraph.observability.telemetry import metrics

        return metrics
    elif name == "auth":
        # Allow access to auth submodule for importlib.reload() scenarios
        # Used in tests/regression/test_bearer_scheme_isolation.py
        # Prevent recursion: if auth module is already being imported, return it from sys.modules
        module_name = f"{__name__}.auth"
        if module_name in sys.modules:
            return sys.modules[module_name]

        import mcp_server_langgraph.auth as auth_module

        return auth_module
    elif name == "api":
        # Allow access to api submodule for importlib.reload() scenarios
        # Used in tests/regression/test_bearer_scheme_isolation.py
        # Prevent recursion: if api module is already being imported, return it from sys.modules
        module_name = f"{__name__}.api"
        if module_name in sys.modules:
            return sys.modules[module_name]

        import mcp_server_langgraph.api as api_module

        return api_module

    # Not found
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
