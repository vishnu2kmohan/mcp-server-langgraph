"""
LangGraph Functional API Agent with full observability and multi-provider LLM support
Includes OpenTelemetry and LangSmith tracing integration
Enhanced with Pydantic AI for type-safe routing and responses

Implements Anthropic's gather-action-verify-repeat agentic loop:
1. Gather Context: Compaction and just-in-time loading
2. Take Action: Routing and tool execution
3. Verify Work: LLM-as-judge pattern
4. Repeat: Iterative refinement based on feedback
"""

import operator
from typing import Annotated, Any, Sequence, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver

from mcp_server_langgraph.core.config import settings
from mcp_server_langgraph.core.url_utils import ensure_redis_password_encoded
from mcp_server_langgraph.observability.telemetry import logger

# Import Dynamic Context Loader if enabled
try:
    from mcp_server_langgraph.core.dynamic_context_loader import (  # noqa: F401
        DynamicContextLoader,
        search_and_load_context,
    )

    DYNAMIC_CONTEXT_AVAILABLE = True
except ImportError:
    DYNAMIC_CONTEXT_AVAILABLE = False
    # Logger warning deferred to runtime to avoid initialization issues

# Import Redis checkpointer if available
try:
    from langgraph.checkpoint.redis import RedisSaver

    REDIS_CHECKPOINTER_AVAILABLE = True
except ImportError:
    REDIS_CHECKPOINTER_AVAILABLE = False
    # Logger warning deferred to runtime when checkpointer is actually created

# Import Pydantic AI for type-safe responses
try:
    from mcp_server_langgraph.llm.pydantic_agent import create_pydantic_agent

    PYDANTIC_AI_AVAILABLE = True
except ImportError:
    PYDANTIC_AI_AVAILABLE = False
    # Logger warning deferred to runtime to avoid initialization issues

# Import LangSmith config if available
try:
    from mcp_server_langgraph.observability.langsmith import get_run_metadata, get_run_tags, langsmith_config

    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False
    langsmith_config = None  # type: ignore[assignment]


class AgentState(TypedDict):
    """
    State for the agent graph.

    Implements full agentic loop state management:
    - Context: messages, compaction status
    - Routing: next_action, confidence, reasoning
    - Verification: verification results, refinement attempts
    - Metadata: user_id, request_id
    """

    messages: Annotated[Sequence[BaseMessage], operator.add]
    next_action: str
    user_id: str | None
    request_id: str | None
    routing_confidence: float | None  # Confidence from Pydantic AI routing
    reasoning: str | None  # Reasoning from Pydantic AI

    # Context management
    compaction_applied: bool | None  # Whether compaction was applied
    original_message_count: int | None  # Message count before compaction

    # Verification and refinement
    verification_passed: bool | None  # Whether verification passed
    verification_score: float | None  # Overall quality score (0-1)
    verification_feedback: str | None  # Feedback for refinement
    refinement_attempts: int | None  # Number of refinement iterations
    user_request: str | None  # Original user request for verification


def _initialize_pydantic_agent() -> Any:
    """Initialize Pydantic AI agent if available"""
    if not PYDANTIC_AI_AVAILABLE:
        return None

    try:
        pydantic_agent = create_pydantic_agent()
        logger.info("Pydantic AI agent initialized for type-safe routing")
        return pydantic_agent
    except Exception as e:
        logger.warning(f"Failed to initialize Pydantic AI agent: {e}", exc_info=True)
        return None


def _create_checkpointer(settings_to_use: Any | None = None) -> Any:
    """
    Create checkpointer backend based on configuration

    Args:
        settings_to_use: Optional Settings object to use. If None, uses global settings.

    Returns:
        BaseCheckpointSaver: Configured checkpointer (MemorySaver or RedisSaver)
    """
    # Use provided settings or fall back to global settings
    effective_settings = settings_to_use if settings_to_use is not None else settings

    backend = effective_settings.checkpoint_backend.lower()

    if backend == "redis":
        if not REDIS_CHECKPOINTER_AVAILABLE:
            logger.warning(
                "Redis checkpointer not available (langgraph-checkpoint-redis not installed), "
                "falling back to MemorySaver. Add 'langgraph-checkpoint-redis' to "
                "pyproject.toml dependencies, then run: uv sync"
            )
            return MemorySaver()

        try:
            logger.info(
                "Initializing Redis checkpointer for distributed conversation state",
                extra={
                    "redis_url": effective_settings.checkpoint_redis_url,
                    "ttl_seconds": effective_settings.checkpoint_redis_ttl,
                },
            )

            # Create Redis checkpointer with TTL
            # Note: RedisSaver.from_conn_string expects redis_url (not conn_string)
            # and returns a context manager in langgraph-checkpoint-redis 0.1.2+
            # Ensure password is URL-encoded to prevent parsing errors (defense-in-depth)
            encoded_redis_url = ensure_redis_password_encoded(effective_settings.checkpoint_redis_url)
            checkpointer_ctx = RedisSaver.from_conn_string(
                redis_url=encoded_redis_url,
            )

            # Enter the context manager to get the actual RedisSaver instance
            checkpointer = checkpointer_ctx.__enter__()

            # Store context manager reference for proper cleanup on shutdown
            # This prevents resource leaks (Redis connections, file descriptors)
            checkpointer.__context_manager__ = checkpointer_ctx  # type: ignore[attr-defined]

            logger.info("Redis checkpointer initialized successfully")
            return checkpointer

        except Exception as e:
            logger.error(
                f"Failed to initialize Redis checkpointer: {e}. Falling back to MemorySaver",
                exc_info=True,
            )
            return MemorySaver()

    elif backend == "memory":
        logger.info("Using in-memory checkpointer (not suitable for multi-replica deployments)")
        return MemorySaver()

    else:
        logger.warning(f"Unknown checkpoint backend '{backend}', falling back to MemorySaver. Supported: 'memory', 'redis'")
        return MemorySaver()


def create_checkpointer(settings_override: Any | None = None) -> Any:
    """
    Public API to create checkpointer backend based on configuration.

    Args:
        settings_override: Optional Settings object to override global settings.
                          Useful for testing with custom configurations.

    Returns:
        BaseCheckpointSaver: Configured checkpointer (MemorySaver or RedisSaver)

    Example:
        # Use global settings
        checkpointer = create_checkpointer()

        # Use custom settings for testing
        test_settings = Settings(checkpoint_backend="memory")
        checkpointer = create_checkpointer(test_settings)
    """
    # Pass settings directly to avoid global state mutation
    # This eliminates race conditions in concurrent environments
    return _create_checkpointer(settings_to_use=settings_override)


def cleanup_checkpointer(checkpointer: BaseCheckpointSaver[Any]) -> None:
    """
    Clean up checkpointer resources on application shutdown.

    Properly closes Redis connections and context managers to prevent:
    - Connection pool exhaustion
    - File descriptor leaks
    - Memory leaks in long-running processes

    Args:
        checkpointer: Checkpointer instance to clean up

    Usage:
        # In FastAPI lifespan or atexit handler:
        import atexit
        checkpointer = create_checkpointer(settings)
        atexit.register(lambda: cleanup_checkpointer(checkpointer))

    Example:
        # FastAPI lifespan context manager
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            checkpointer = create_checkpointer(settings)
            yield
            cleanup_checkpointer(checkpointer)
    """
    try:
        # Check if checkpointer has context manager reference
        if hasattr(checkpointer, "__context_manager__"):
            context_manager = checkpointer.__context_manager__
            logger.info("Cleaning up Redis checkpointer context manager")

            # Exit context manager to close connections
            context_manager.__exit__(None, None, None)

            logger.info("Redis checkpointer cleanup completed successfully")
        else:
            logger.debug(f"Checkpointer {type(checkpointer).__name__} does not require cleanup")

    except Exception as e:
        logger.error(f"Error during checkpointer cleanup: {e}", exc_info=True)


def _get_runnable_config(user_id: str | None = None, request_id: str | None = None) -> RunnableConfig | None:
    """Get runnable config with LangSmith metadata"""
    if not LANGSMITH_AVAILABLE or not langsmith_config.is_enabled():
        return None

    return RunnableConfig(
        run_name="mcp-server-langgraph", tags=get_run_tags(user_id), metadata=get_run_metadata(user_id, request_id)
    )


def _fallback_routing(state: AgentState, last_message: HumanMessage) -> AgentState:
    """Fallback routing logic without Pydantic AI"""
    # Determine if this needs tools or direct response
    content = last_message.content if isinstance(last_message.content, str) else str(last_message.content)
    if any(keyword in content.lower() for keyword in ["search", "calculate", "lookup"]):
        next_action = "use_tools"
    else:
        next_action = "respond"

    # NOTE: Don't return "messages" key - operator.add would duplicate them!
    # Only return fields we're modifying.
    return {  # type: ignore[typeddict-item]
        "next_action": next_action,
        "routing_confidence": 0.5,  # Low confidence for fallback
        "reasoning": "Fallback keyword-based routing",
        "user_id": state.get("user_id"),
        "request_id": state.get("request_id"),
    }


# ==============================================================================
# DEPRECATED: _create_agent_graph_singleton
# ==============================================================================
# This function has been replaced by the compile-time graph builder pattern.
# See: agent_graph_builder.py and agent_config.py
#
# The new pattern uses build_agent_graph(config, checkpointer, settings) which:
# - Evaluates feature flags at compile time (not runtime) - OCP compliant
# - Supports graph versioning for checkpoint compatibility
# - Enables better testability via AgentConfig
#
# Migration path:
#   OLD: agent = _create_agent_graph_singleton(settings)
#   NEW: config = AgentConfig.from_settings(settings)
#        agent = build_agent_graph(config, checkpointer, settings)
#
# For backwards compatibility, use create_agent() or create_agent_graph() instead.
# ==============================================================================


# ==============================================================================
# Dependency Injection API
# ==============================================================================
# IMPORTANT: Do NOT create agent_graph at module level
# Entry points (mcp/server_stdio.py, mcp/server_streamable.py) must call init_observability()
# before creating agent graphs via create_agent_graph()
#
# The legacy get_agent_graph() singleton has been removed (2025-12).
# All consumers should use create_agent_graph() with DI pattern instead.


def create_agent_graph(
    settings: Any | None = None,
    container: Any | None = None,
) -> Any:
    """
    Create a new agent graph with dependency injection support.

    This function creates a fresh agent graph instance using either:
    - A container (preferred for full DI benefits)
    - Custom settings
    - Default settings (fallback)

    Args:
        settings: Optional Settings instance to use
        container: Optional ApplicationContainer instance to use

    Returns:
        Compiled LangGraph StateGraph

    Example:
        # Using container (preferred)
        from mcp_server_langgraph.core.container import create_test_container
        container = create_test_container()
        agent = create_agent_graph(container=container)

        # Using custom settings
        from mcp_server_langgraph.core.config import Settings
        settings = Settings(environment="test")
        agent = create_agent_graph(settings=settings)

        # Using defaults
        agent = create_agent_graph()
    """
    # Get settings from container or use provided/default
    if container is not None:
        actual_settings = container.settings
    elif settings is not None:
        actual_settings = settings
    else:
        # Use default settings (will use global settings object)
        from mcp_server_langgraph.core.config import settings as default_settings

        actual_settings = default_settings

    # Create a fresh agent graph using the same create_agent_graph function
    # This ensures we use the same logic but with injectable settings
    return create_agent_graph_impl(actual_settings)


def create_agent_graph_impl(settings_to_use: Any) -> Any:
    """
    Implementation of agent graph creation with specific settings.

    This properly threads the settings through to the agent graph creation,
    enabling dependency injection for testing and multi-tenant deployments.

    Uses the new compile-time graph builder (build_agent_graph) which
    implements the Open/Closed Principle - feature flags are evaluated
    at graph construction time, not at runtime.

    Args:
        settings_to_use: Settings instance to use

    Returns:
        Compiled LangGraph StateGraph
    """
    from mcp_server_langgraph.core.agent_config import AgentConfig
    from mcp_server_langgraph.core.agent_graph_builder import build_agent_graph

    # Create AgentConfig from settings
    config = AgentConfig.from_settings(settings_to_use)

    # Create checkpointer (Redis or Memory based on settings)
    checkpointer = _create_checkpointer(settings_to_use)

    # Build the graph using compile-time composition
    return build_agent_graph(
        config=config,
        checkpointer=checkpointer,
        settings=settings_to_use,
    )


def create_agent(
    settings: Any | None = None,
    container: Any | None = None,
) -> Any:
    """
    Create a new agent instance with dependency injection support.

    This is the main factory function for creating agents. It supports:
    - Container-based dependency injection (preferred)
    - Custom settings
    - Default configuration

    Args:
        settings: Optional Settings instance to override defaults
        container: Optional ApplicationContainer for full DI

    Returns:
        Compiled agent graph ready for use

    Example:
        # Preferred: Using container
        from mcp_server_langgraph.core.container import create_test_container
        container = create_test_container()
        agent = create_agent(container=container)
        result = agent.invoke({"messages": [...]})

        # Using custom settings
        from mcp_server_langgraph.core.config import Settings
        settings = Settings(model_name="gpt-4")
        agent = create_agent(settings=settings)

        # Using defaults
        agent = create_agent()
    """
    return create_agent_graph(settings=settings, container=container)
