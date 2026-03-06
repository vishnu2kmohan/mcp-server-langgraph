"""
Agent Execution Tracing Bootstrap Module.

Provides initialization for LangGraph Agent Execution Trace components:
- PostgresLangGraphExecutionTraceRepository
- Global availability tracking

This is DISTINCT from Context Graph (Decision Traces):
- Context Graph: High-level decision context for learning (ADR-0101)
- Agent Execution Traces: LangGraph node execution events for DevTools

Reference: Triple-AI Diagnosis Plan - Fix 3
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mcp_server_langgraph.core.feature_flags import feature_flags
from mcp_server_langgraph.observability.telemetry import logger

if TYPE_CHECKING:
    from mcp_server_langgraph.core.config import Settings

# Global state to track agent execution tracing initialization status
# NOTE: This is SEPARATE from Decision Trace (context_graph) initialization
_agent_execution_tracing_available: bool = False


def is_agent_execution_tracing_available() -> bool:
    """Check if agent execution tracing is available (repository initialized successfully).

    NOTE: This is SEPARATE from Decision Trace availability (context_graph).

    Returns:
        True if the repository was successfully initialized, False otherwise
    """
    return _agent_execution_tracing_available


def set_agent_execution_tracing_available(available: bool) -> None:
    """Set the agent execution tracing availability status.

    This is called by init_agent_execution_trace_repository after initialization.

    Args:
        available: Whether agent execution tracing is available
    """
    global _agent_execution_tracing_available
    _agent_execution_tracing_available = available


async def init_agent_execution_trace_repository(settings: Settings) -> bool:
    """Initialize LangGraph Agent Execution Trace repository.

    This repository stores node execution events from LangGraph graphs.
    DISTINCT from Decision Trace repository (context_graph.py).

    Implements fail-fast pattern:
    - Returns True on success, False on failure
    - Sets global _agent_execution_tracing_available flag
    - Logs errors but does not raise (graceful degradation)

    Args:
        settings: Application settings

    Returns:
        True if successful, False otherwise
    """
    global _agent_execution_tracing_available

    # Check feature flag first
    if not feature_flags.enable_agent_execution_tracing:
        logger.debug("Agent execution tracing disabled by feature flag")
        _agent_execution_tracing_available = False
        return False

    try:
        from mcp_server_langgraph.core.dependencies import (
            get_async_session,
            set_langgraph_execution_trace_repository,
        )
        from mcp_server_langgraph.repositories.langgraph_execution_trace import (
            PostgresLangGraphExecutionTraceRepository,
        )

        session_factory = get_async_session()
        if session_factory is None:
            logger.error(  # type: ignore[unreachable]
                "Cannot initialize agent execution trace repository: async session not available. "
                "Ensure database is initialized before calling this function."
            )
            _agent_execution_tracing_available = False
            return False

        # Create and register the repository
        repository = PostgresLangGraphExecutionTraceRepository(session_factory=session_factory)  # type: ignore[arg-type]
        set_langgraph_execution_trace_repository(repository)

        logger.info(
            "LangGraph Agent Execution Trace repository initialized",
            extra={
                "feature_flag": "enable_agent_execution_tracing",
                "repository_type": "PostgresLangGraphExecutionTraceRepository",
            },
        )
        _agent_execution_tracing_available = True
        return True

    except Exception as e:
        logger.exception(
            f"Failed to initialize agent execution trace repository: {e}",
            extra={
                "error": str(e),
                "feature_flag": "enable_agent_execution_tracing",
            },
        )
        _agent_execution_tracing_available = False
        return False


def cleanup_agent_execution_tracing() -> None:
    """Cleanup agent execution tracing state.

    Called during application shutdown to reset global state.
    """
    global _agent_execution_tracing_available
    _agent_execution_tracing_available = False
    logger.debug("Agent execution tracing cleanup complete")
