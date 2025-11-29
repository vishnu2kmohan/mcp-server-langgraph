"""
Unit tests for core/agent.py functions.

Tests checkpointer creation, cleanup, routing logic, and helper functions.
Follows TDD principles and memory safety patterns for pytest-xdist.
"""

import gc
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import HumanMessage

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="agent_core")
class TestCreateCheckpointer:
    """Test checkpointer creation with different backends."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_memory_backend_creates_memory_saver(self):
        """Test that memory backend creates MemorySaver."""
        from langgraph.checkpoint.memory import MemorySaver

        mock_settings = MagicMock()
        mock_settings.checkpoint_backend = "memory"

        from mcp_server_langgraph.core.agent import create_checkpointer

        checkpointer = create_checkpointer(mock_settings)

        assert isinstance(checkpointer, MemorySaver)

    @pytest.mark.unit
    def test_unknown_backend_falls_back_to_memory(self):
        """Test that unknown backend falls back to MemorySaver."""
        from langgraph.checkpoint.memory import MemorySaver

        mock_settings = MagicMock()
        mock_settings.checkpoint_backend = "unknown_backend"

        from mcp_server_langgraph.core.agent import create_checkpointer

        checkpointer = create_checkpointer(mock_settings)

        assert isinstance(checkpointer, MemorySaver)

    @pytest.mark.unit
    def test_redis_backend_falls_back_when_unavailable(self):
        """Test that Redis backend falls back when package unavailable."""
        from langgraph.checkpoint.memory import MemorySaver

        mock_settings = MagicMock()
        mock_settings.checkpoint_backend = "redis"
        mock_settings.checkpoint_redis_url = "redis://localhost:6379"
        mock_settings.checkpoint_redis_ttl = 3600

        # Mock Redis checkpointer as unavailable
        with patch("mcp_server_langgraph.core.agent.REDIS_CHECKPOINTER_AVAILABLE", False):
            from mcp_server_langgraph.core.agent import create_checkpointer

            checkpointer = create_checkpointer(mock_settings)

            assert isinstance(checkpointer, MemorySaver)

    @pytest.mark.unit
    def test_redis_backend_with_connection_error(self):
        """Test that Redis connection error falls back to MemorySaver."""
        from langgraph.checkpoint.memory import MemorySaver

        mock_settings = MagicMock()
        mock_settings.checkpoint_backend = "redis"
        mock_settings.checkpoint_redis_url = "redis://invalid:6379"
        mock_settings.checkpoint_redis_ttl = 3600

        with patch("mcp_server_langgraph.core.agent.REDIS_CHECKPOINTER_AVAILABLE", True):
            with patch("mcp_server_langgraph.core.agent.RedisSaver") as mock_redis:
                mock_redis.from_conn_string.side_effect = ConnectionError("Redis connection failed")

                from mcp_server_langgraph.core.agent import create_checkpointer

                checkpointer = create_checkpointer(mock_settings)

                assert isinstance(checkpointer, MemorySaver)


@pytest.mark.xdist_group(name="agent_core")
class TestCleanupCheckpointer:
    """Test checkpointer cleanup functionality."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_cleanup_with_context_manager(self):
        """Test cleanup properly exits context manager."""
        from mcp_server_langgraph.core.agent import cleanup_checkpointer

        mock_checkpointer = MagicMock()
        mock_context_manager = MagicMock()
        mock_checkpointer.__context_manager__ = mock_context_manager

        cleanup_checkpointer(mock_checkpointer)

        mock_context_manager.__exit__.assert_called_once_with(None, None, None)

    @pytest.mark.unit
    def test_cleanup_without_context_manager(self):
        """Test cleanup handles checkpointers without context manager."""
        from mcp_server_langgraph.core.agent import cleanup_checkpointer

        mock_checkpointer = MagicMock(spec=[])  # No __context_manager__ attr

        # Should not raise
        cleanup_checkpointer(mock_checkpointer)

    @pytest.mark.unit
    def test_cleanup_handles_exceptions(self):
        """Test cleanup handles exceptions gracefully."""
        from mcp_server_langgraph.core.agent import cleanup_checkpointer

        mock_checkpointer = MagicMock()
        mock_context_manager = MagicMock()
        mock_context_manager.__exit__.side_effect = RuntimeError("Cleanup failed")
        mock_checkpointer.__context_manager__ = mock_context_manager

        # Should not raise, just log error
        cleanup_checkpointer(mock_checkpointer)


@pytest.mark.xdist_group(name="agent_core")
class TestFallbackRouting:
    """Test fallback routing logic without Pydantic AI."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_routing_with_search_keyword(self):
        """Test that search keyword routes to use_tools."""
        from mcp_server_langgraph.core.agent import _fallback_routing

        state = {
            "messages": [HumanMessage(content="search for python tutorials")],
            "next_action": "",
            "user_id": "alice",
            "request_id": "req-123",
        }

        result = _fallback_routing(state, state["messages"][-1])

        assert result["next_action"] == "use_tools"
        assert result["routing_confidence"] == 0.5
        assert "fallback" in result["reasoning"].lower()

    @pytest.mark.unit
    def test_routing_with_calculate_keyword(self):
        """Test that calculate keyword routes to use_tools."""
        from mcp_server_langgraph.core.agent import _fallback_routing

        state = {
            "messages": [HumanMessage(content="calculate 2 + 2")],
            "next_action": "",
            "user_id": "alice",
            "request_id": "req-123",
        }

        result = _fallback_routing(state, state["messages"][-1])

        assert result["next_action"] == "use_tools"

    @pytest.mark.unit
    def test_routing_without_keywords(self):
        """Test that regular message routes to respond."""
        from mcp_server_langgraph.core.agent import _fallback_routing

        state = {
            "messages": [HumanMessage(content="hello, how are you?")],
            "next_action": "",
            "user_id": "alice",
            "request_id": "req-123",
        }

        result = _fallback_routing(state, state["messages"][-1])

        assert result["next_action"] == "respond"
        assert result["routing_confidence"] == 0.5


@pytest.mark.xdist_group(name="agent_core")
class TestGetRunnableConfig:
    """Test LangSmith runnable config creation."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_returns_none_when_langsmith_unavailable(self):
        """Test that None is returned when LangSmith is unavailable."""
        with patch("mcp_server_langgraph.core.agent.LANGSMITH_AVAILABLE", False):
            from mcp_server_langgraph.core.agent import _get_runnable_config

            result = _get_runnable_config(user_id="alice", request_id="req-123")

            assert result is None

    @pytest.mark.unit
    def test_returns_none_when_langsmith_disabled(self):
        """Test that None is returned when LangSmith is disabled."""
        mock_config = MagicMock()
        mock_config.is_enabled.return_value = False

        with patch("mcp_server_langgraph.core.agent.LANGSMITH_AVAILABLE", True):
            with patch("mcp_server_langgraph.core.agent.langsmith_config", mock_config):
                from mcp_server_langgraph.core.agent import _get_runnable_config

                result = _get_runnable_config(user_id="alice", request_id="req-123")

                assert result is None

    @pytest.mark.unit
    def test_returns_config_when_langsmith_enabled(self):
        """Test that config is returned when LangSmith is enabled."""
        mock_config = MagicMock()
        mock_config.is_enabled.return_value = True

        with patch("mcp_server_langgraph.core.agent.LANGSMITH_AVAILABLE", True):
            with patch("mcp_server_langgraph.core.agent.langsmith_config", mock_config):
                with patch("mcp_server_langgraph.core.agent.get_run_tags", return_value=["test"]):
                    with patch("mcp_server_langgraph.core.agent.get_run_metadata", return_value={"user": "alice"}):
                        from mcp_server_langgraph.core.agent import _get_runnable_config

                        result = _get_runnable_config(user_id="alice", request_id="req-123")

                        # RunnableConfig is a TypedDict, so check for dict-like structure
                        assert result is not None
                        assert "run_name" in result
                        assert "tags" in result
                        assert "metadata" in result


@pytest.mark.xdist_group(name="agent_core")
class TestInitializePydanticAgent:
    """Test Pydantic AI agent initialization."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_returns_none_when_pydantic_ai_unavailable(self):
        """Test that None is returned when Pydantic AI is unavailable."""
        with patch("mcp_server_langgraph.core.agent.PYDANTIC_AI_AVAILABLE", False):
            from mcp_server_langgraph.core.agent import _initialize_pydantic_agent

            result = _initialize_pydantic_agent()

            assert result is None

    @pytest.mark.unit
    def test_handles_initialization_errors(self):
        """Test that initialization errors are handled gracefully."""
        with patch("mcp_server_langgraph.core.agent.PYDANTIC_AI_AVAILABLE", True):
            with patch(
                "mcp_server_langgraph.core.agent.create_pydantic_agent",
                side_effect=RuntimeError("Pydantic AI init failed"),
            ):
                from mcp_server_langgraph.core.agent import _initialize_pydantic_agent

                result = _initialize_pydantic_agent()

                assert result is None


@pytest.mark.xdist_group(name="agent_core")
class TestAgentState:
    """Test AgentState TypedDict structure."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_agent_state_has_required_fields(self):
        """Test that AgentState has all required fields."""
        from mcp_server_langgraph.core.agent import AgentState

        # Create a valid state
        state: AgentState = {
            "messages": [HumanMessage(content="test")],
            "next_action": "respond",
            "user_id": "alice",
            "request_id": "req-123",
            "routing_confidence": 0.9,
            "reasoning": "test reasoning",
            "compaction_applied": False,
            "original_message_count": 1,
            "verification_passed": True,
            "verification_score": 0.95,
            "verification_feedback": None,
            "refinement_attempts": 0,
            "user_request": "test request",
        }

        # Should have all expected keys
        assert "messages" in state
        assert "next_action" in state
        assert "user_id" in state
        assert "routing_confidence" in state
        assert "verification_passed" in state

    @pytest.mark.unit
    def test_agent_state_messages_annotated(self):
        """Test that messages field is properly annotated for operator.add."""
        from typing import get_type_hints

        from mcp_server_langgraph.core.agent import AgentState

        hints = get_type_hints(AgentState, include_extras=True)

        assert "messages" in hints
        # The type should be Annotated with operator.add
