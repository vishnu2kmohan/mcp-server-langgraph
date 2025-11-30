"""
MCP Server with LangGraph.

A production-ready MCP (Model Context Protocol) server built with LangGraph,
featuring multi-LLM support, fine-grained authorization, and comprehensive observability.
"""

import sys
import tomllib
from pathlib import Path

# Read version from pyproject.toml (single source of truth)
try:
    pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
    with open(pyproject_path, "rb") as f:
        pyproject_data = tomllib.load(f)
    __version__ = pyproject_data["project"]["version"]
except Exception:
    # Fallback if reading fails
    __version__ = "2.8.0"

# Core exports (lightweight - eagerly imported)
from mcp_server_langgraph.core.config import settings

__all__ = [
    "AgentState",
    "AuthMiddleware",
    "OpenFGAClient",
    "__version__",
    "agent_graph",
    "create_llm_from_config",
    "logger",
    "metrics",
    "settings",
    "tracer",
]


def __getattr__(name: str):  # type: ignore[no-untyped-def]  # noqa: C901
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
    elif name == "health":
        # Allow access to health submodule for health check endpoints
        # Used in tests/integration/test_health_check.py
        # Prevent recursion: if health module is already being imported, return it from sys.modules
        module_name = f"{__name__}.health"
        if module_name in sys.modules:
            return sys.modules[module_name]

        import mcp_server_langgraph.health as health_module

        return health_module
    elif name == "tools":
        # Allow access to tools submodule for patch/mock scenarios in tests
        # Prevent recursion: if tools module is already being imported, return it from sys.modules
        module_name = f"{__name__}.tools"
        if module_name in sys.modules:
            return sys.modules[module_name]

        import mcp_server_langgraph.tools as tools_module

        return tools_module
    elif name == "llm":
        # Allow access to llm submodule for tests (needed for Python 3.10 mock compatibility)
        module_name = f"{__name__}.llm"
        if module_name in sys.modules:
            return sys.modules[module_name]

        import mcp_server_langgraph.llm as llm_module

        return llm_module
    elif name == "core":
        # Allow access to core submodule for tests (needed for Python 3.10 mock compatibility)
        module_name = f"{__name__}.core"
        if module_name in sys.modules:
            return sys.modules[module_name]

        import mcp_server_langgraph.core as core_module

        return core_module
    elif name == "monitoring":
        # Allow access to monitoring submodule for tests (needed for Python 3.10 mock compatibility)
        module_name = f"{__name__}.monitoring"
        if module_name in sys.modules:
            return sys.modules[module_name]

        import mcp_server_langgraph.monitoring as monitoring_module

        return monitoring_module
    elif name == "app":
        # Allow access to app submodule for tests (needed for Python 3.10 mock compatibility)
        module_name = f"{__name__}.app"
        if module_name in sys.modules:
            return sys.modules[module_name]

        import mcp_server_langgraph.app as app_module

        return app_module
    elif name == "middleware":
        # Allow access to middleware submodule for tests (needed for Python 3.10 mock compatibility)
        module_name = f"{__name__}.middleware"
        if module_name in sys.modules:
            return sys.modules[module_name]

        import mcp_server_langgraph.middleware as middleware_module

        return middleware_module
    elif name == "execution":
        # Allow access to execution submodule for tests (needed for Python 3.10 mock compatibility)
        module_name = f"{__name__}.execution"
        if module_name in sys.modules:
            return sys.modules[module_name]

        import mcp_server_langgraph.execution as execution_module

        return execution_module
    elif name == "compliance":
        # Allow access to compliance submodule for tests (needed for Python 3.10 mock compatibility)
        module_name = f"{__name__}.compliance"
        if module_name in sys.modules:
            return sys.modules[module_name]

        import mcp_server_langgraph.compliance as compliance_module

        return compliance_module
    elif name == "schedulers":
        # Allow access to schedulers submodule for tests (needed for Python 3.10 mock compatibility)
        module_name = f"{__name__}.schedulers"
        if module_name in sys.modules:
            return sys.modules[module_name]

        import mcp_server_langgraph.schedulers as schedulers_module

        return schedulers_module
    elif name == "resilience":
        # Allow access to resilience submodule for resilience pattern tests
        module_name = f"{__name__}.resilience"
        if module_name in sys.modules:
            return sys.modules[module_name]

        import mcp_server_langgraph.resilience as resilience_module

        return resilience_module
    elif name == "mcp":
        # Allow access to mcp submodule for MCP server tests
        module_name = f"{__name__}.mcp"
        if module_name in sys.modules:
            return sys.modules[module_name]

        import mcp_server_langgraph.mcp as mcp_module

        return mcp_module
    elif name == "observability":
        # Allow access to observability submodule for telemetry tests
        module_name = f"{__name__}.observability"
        if module_name in sys.modules:
            return sys.modules[module_name]

        import mcp_server_langgraph.observability as observability_module

        return observability_module

    # Not found
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
