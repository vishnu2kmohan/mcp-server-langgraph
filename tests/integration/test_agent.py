import gc
import os

"""Unit tests for agent.py - LangGraph Agent"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from tests.conftest import get_user_id
from langchain_core.messages import AIMessage, HumanMessage

pytestmark = pytest.mark.integration


@pytest.mark.unit
@pytest.mark.xdist_group(name="agent_tests")
class TestAgentState:
    """Test AgentState TypedDict"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_agent_state_structure(self):
        """Test AgentState can be created with required fields"""
        from mcp_server_langgraph.core.agent import AgentState

        state: AgentState = {
            "messages": [HumanMessage(content="Hello")],
            "next_action": "respond",
            "user_id": get_user_id("alice"),
            "request_id": "req-123",
        }

        assert len(state["messages"]) == 1
        assert state["next_action"] == "respond"
        assert state["user_id"] == get_user_id("alice")
        assert state["request_id"] == "req-123"


@pytest.mark.unit
@pytest.mark.xdist_group(name="agent_tests")
class TestAgentGraph:
    """Test LangGraph agent creation and execution"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @patch("mcp_server_langgraph.llm.factory.create_llm_from_config")
    def test_create_agent_graph(self, mock_create_llm):
        """Test agent graph is created successfully"""
        from mcp_server_langgraph.core.agent import create_agent_graph

        # Mock the LLM
        mock_llm = MagicMock()
        mock_create_llm.return_value = mock_llm

        graph = create_agent_graph()

        assert graph is not None
        assert hasattr(graph, "invoke")
        assert hasattr(graph, "stream")

    @patch("mcp_server_langgraph.core.agent.create_llm_from_config")
    async def test_route_input_to_respond(self, mock_create_llm):
        """Test routing to direct response"""
        from mcp_server_langgraph.core.agent import create_agent_graph

        mock_model = MagicMock()
        mock_model.ainvoke = AsyncMock(return_value=AIMessage(content="Hello! I can help you."))
        mock_create_llm.return_value = mock_model

        graph = create_agent_graph()

        initial_state = {
            "messages": [HumanMessage(content="Hello, what can you do?")],
            "next_action": "",
            "user_id": get_user_id("alice"),
            "request_id": "req-123",
        }

        result = await graph.ainvoke(initial_state, config={"configurable": {"thread_id": "test-1"}})

        assert result is not None
        assert "messages" in result
        assert len(result["messages"]) > 1
        assert result["next_action"] == "end"

    @patch("mcp_server_langgraph.core.agent.create_llm_from_config")
    async def test_route_input_to_tools(self, mock_create_llm):
        """Test routing to tools when keywords detected"""
        from mcp_server_langgraph.core.agent import create_agent_graph

        mock_model = MagicMock()
        mock_model.ainvoke = AsyncMock(return_value=AIMessage(content="Search completed."))
        mock_create_llm.return_value = mock_model

        graph = create_agent_graph()

        initial_state = {
            "messages": [HumanMessage(content="Please search for information about Python")],
            "next_action": "",
            "user_id": get_user_id("bob"),
            "request_id": "req-456",
        }

        result = await graph.ainvoke(initial_state, config={"configurable": {"thread_id": "test-2"}})

        assert result is not None
        # Should go through tools node
        assert len(result["messages"]) > 2

    @patch("mcp_server_langgraph.core.agent.create_llm_from_config")
    async def test_route_with_calculate_keyword(self, mock_create_llm):
        """Test routing detects calculate keyword"""
        from mcp_server_langgraph.core.agent import create_agent_graph

        mock_model = MagicMock()
        mock_model.ainvoke = AsyncMock(return_value=AIMessage(content="Calculation result"))
        mock_create_llm.return_value = mock_model

        graph = create_agent_graph()

        initial_state = {
            "messages": [HumanMessage(content="Calculate 2 + 2")],
            "next_action": "",
            "user_id": get_user_id("alice"),
            "request_id": "req-789",
        }

        result = await graph.ainvoke(initial_state, config={"configurable": {"thread_id": "test-3"}})

        assert result is not None
        assert result["next_action"] == "end"

    @patch("mcp_server_langgraph.core.agent.create_llm_from_config")
    async def test_agent_with_conversation_history(self, mock_create_llm):
        """Test agent handles conversation history"""
        from mcp_server_langgraph.core.agent import create_agent_graph

        mock_model = MagicMock()
        mock_model.ainvoke = AsyncMock(return_value=AIMessage(content="Follow-up response"))
        mock_create_llm.return_value = mock_model

        graph = create_agent_graph()

        initial_state = {
            "messages": [
                HumanMessage(content="What is Python?"),
                AIMessage(content="Python is a programming language."),
                HumanMessage(content="Tell me more"),
            ],
            "next_action": "",
            "user_id": get_user_id("alice"),
            "request_id": "req-999",
        }

        result = await graph.ainvoke(initial_state, config={"configurable": {"thread_id": "test-4"}})

        assert result is not None
        assert len(result["messages"]) > 3

    @patch("mcp_server_langgraph.core.agent.create_llm_from_config")
    async def test_checkpointing_works(self, mock_create_llm):
        """Test conversation checkpointing"""
        from mcp_server_langgraph.core.agent import create_agent_graph

        mock_model = MagicMock()
        mock_model.ainvoke = AsyncMock(return_value=AIMessage(content="Response"))
        mock_create_llm.return_value = mock_model

        graph = create_agent_graph()

        thread_id = "checkpoint-test"

        # First message
        state1 = {
            "messages": [HumanMessage(content="First message")],
            "next_action": "",
            "user_id": get_user_id("alice"),
            "request_id": "req-1",
        }
        result1 = await graph.ainvoke(state1, config={"configurable": {"thread_id": thread_id}})

        # Second message - should maintain history
        state2 = {
            "messages": [HumanMessage(content="Second message")],
            "next_action": "",
            "user_id": get_user_id("alice"),
            "request_id": "req-2",
        }
        result2 = await graph.ainvoke(state2, config={"configurable": {"thread_id": thread_id}})

        # Second result should have more messages due to checkpointing
        assert len(result2["messages"]) > len(result1["messages"])

    def test_state_accumulation(self):
        """Test that messages accumulate in state"""
        import operator

        from mcp_server_langgraph.core.agent import AgentState

        # Verify that the Annotated type with operator.add works
        state: AgentState = {
            "messages": [HumanMessage(content="First")],
            "next_action": "respond",
            "user_id": get_user_id("alice"),
            "request_id": "req-1",
        }

        # Simulate message accumulation
        new_messages = [AIMessage(content="Second")]
        combined = operator.add(state["messages"], new_messages)

        assert len(combined) == 2
        assert isinstance(combined[0], HumanMessage)
        assert isinstance(combined[1], AIMessage)

    @patch("mcp_server_langgraph.core.agent.LANGSMITH_AVAILABLE", False)
    @patch("mcp_server_langgraph.core.agent.create_llm_from_config")
    async def test_agent_without_langsmith(self, mock_create_llm):
        """Test agent works when LangSmith is not available"""
        from mcp_server_langgraph.core.agent import create_agent_graph

        mock_model = MagicMock()
        mock_model.ainvoke = AsyncMock(return_value=AIMessage(content="Response without LangSmith"))
        mock_create_llm.return_value = mock_model

        graph = create_agent_graph()

        initial_state = {
            "messages": [HumanMessage(content="Test message")],
            "next_action": "",
            "user_id": get_user_id("test"),
            "request_id": "req-test",
        }

        result = await graph.ainvoke(initial_state, config={"configurable": {"thread_id": "test-no-langsmith"}})

        assert result is not None
        assert len(result["messages"]) > 0

    @patch("mcp_server_langgraph.core.agent.create_llm_from_config")
    async def test_agent_with_langsmith_enabled(self, mock_create_llm):
        """Test agent with LangSmith configuration"""
        from mcp_server_langgraph.core.agent import create_agent_graph

        mock_model = MagicMock()
        mock_model.ainvoke = AsyncMock(return_value=AIMessage(content="Response"))
        mock_create_llm.return_value = mock_model

        # This test verifies the agent works regardless of LangSmith availability
        graph = create_agent_graph()

        initial_state = {
            "messages": [HumanMessage(content="Test message")],
            "next_action": "",
            "user_id": get_user_id("test"),
            "request_id": "req-test",
        }

        result = await graph.ainvoke(initial_state, config={"configurable": {"thread_id": "test-langsmith"}})

        assert result is not None
        assert len(result["messages"]) > 0

    @patch("mcp_server_langgraph.core.agent.create_llm_from_config")
    async def test_routing_with_tool_keywords(self, mock_create_llm):
        """Test routing detects tool keywords"""
        from mcp_server_langgraph.core.agent import create_agent_graph

        mock_model = MagicMock()
        mock_model.ainvoke = AsyncMock(return_value=AIMessage(content="Search result"))
        mock_create_llm.return_value = mock_model

        graph = create_agent_graph()

        # Test with "search" keyword
        state_search = {
            "messages": [HumanMessage(content="Please search for information")],
            "next_action": "",
            "user_id": get_user_id("test"),
            "request_id": "req-test",
        }

        result = await graph.ainvoke(state_search, config={"configurable": {"thread_id": "test-routing"}})

        assert result is not None

    @patch("mcp_server_langgraph.core.agent.create_llm_from_config")
    async def test_handles_empty_message_content(self, mock_create_llm):
        """
        Test agent handles empty message content gracefully.

        Edge case: Empty string content should not crash the agent.
        """
        from mcp_server_langgraph.core.agent import create_agent_graph

        mock_model = MagicMock()
        mock_model.ainvoke = AsyncMock(return_value=AIMessage(content="Handled empty input"))
        mock_create_llm.return_value = mock_model

        graph = create_agent_graph()

        # Test with empty content
        state_empty = {
            "messages": [HumanMessage(content="")],
            "next_action": "",
            "user_id": get_user_id("test"),
            "request_id": "req-empty",
        }

        result = await graph.ainvoke(state_empty, config={"configurable": {"thread_id": "test-empty"}})

        # Should handle gracefully without crashing
        assert result is not None
        assert "messages" in result

    @patch("mcp_server_langgraph.core.agent.create_llm_from_config")
    async def test_handles_missing_optional_fields(self, mock_create_llm):
        """
        Test agent handles missing optional fields (user_id, request_id).

        Edge case: None values for optional fields should be acceptable.
        """
        from mcp_server_langgraph.core.agent import create_agent_graph

        mock_model = MagicMock()
        mock_model.ainvoke = AsyncMock(return_value=AIMessage(content="Response"))
        mock_create_llm.return_value = mock_model

        graph = create_agent_graph()

        # Test with None optional fields
        state_minimal = {
            "messages": [HumanMessage(content="Test")],
            "next_action": "",
            "user_id": None,  # Edge case: no user ID
            "request_id": None,  # Edge case: no request ID
        }

        result = await graph.ainvoke(state_minimal, config={"configurable": {"thread_id": "test-minimal"}})

        assert result is not None
        assert len(result["messages"]) > 0

    @patch("mcp_server_langgraph.core.agent.create_llm_from_config")
    async def test_handles_very_long_conversation_history(self, mock_create_llm):
        """
        Test agent handles very long conversation histories.

        Edge case: Many messages should trigger compaction if enabled.
        """
        from mcp_server_langgraph.core.agent import create_agent_graph

        mock_model = MagicMock()
        mock_model.ainvoke = AsyncMock(return_value=AIMessage(content="Response to long history"))
        mock_create_llm.return_value = mock_model

        graph = create_agent_graph()

        # Create very long conversation (50 messages)
        long_history = []
        for i in range(25):
            long_history.append(HumanMessage(content=f"User message {i}"))
            long_history.append(AIMessage(content=f"AI response {i}"))

        long_history.append(HumanMessage(content="Final question"))

        state_long = {
            "messages": long_history,
            "next_action": "",
            "user_id": get_user_id("test"),
            "request_id": "req-long",
        }

        result = await graph.ainvoke(state_long, config={"configurable": {"thread_id": "test-long"}})

        # Should handle long history (potentially with compaction)
        assert result is not None
        assert len(result["messages"]) > 0


@pytest.mark.integration
@pytest.mark.xdist_group(name="agent_tests")
class TestAgentIntegration:
    """Integration tests for agent (may require API keys)"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @patch("mcp_server_langgraph.core.agent.create_llm_from_config")
    @pytest.mark.asyncio
    async def test_get_agent_graph_lazy_initialization(self, mock_create_llm):
        """Test lazy agent graph initialization (regression test for agent_graph = None bug)"""
        from mcp_server_langgraph.core.agent import get_agent_graph

        mock_model = MagicMock()
        mock_model.ainvoke = AsyncMock(return_value=AIMessage(content="Response"))
        mock_create_llm.return_value = mock_model

        # This should create the graph lazily
        graph = get_agent_graph()

        assert graph is not None
        assert hasattr(graph, "ainvoke")
        assert hasattr(graph, "aget_state")

        # Verify the graph can be invoked successfully
        initial_state = {
            "messages": [HumanMessage(content="Test message")],
            "next_action": "",
            "user_id": get_user_id("alice"),
            "request_id": "req-lazy-test",
        }

        result = await graph.ainvoke(initial_state, config={"configurable": {"thread_id": "lazy-test"}})

        assert result is not None
        assert "messages" in result

    @patch("mcp_server_langgraph.core.agent.create_llm_from_config")
    @pytest.mark.asyncio
    async def test_get_agent_graph_singleton_pattern(self, mock_create_llm):
        """Test that get_agent_graph returns the same instance (singleton pattern)"""
        from mcp_server_langgraph.core.agent import get_agent_graph

        mock_model = MagicMock()
        mock_model.ainvoke = AsyncMock(return_value=AIMessage(content="Response"))
        mock_create_llm.return_value = mock_model

        # Call get_agent_graph twice
        graph1 = get_agent_graph()
        graph2 = get_agent_graph()

        # Should return the same instance
        assert graph1 is graph2

    @pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"), reason="Requires ANTHROPIC_API_KEY")
    async def test_real_llm_invocation(self):
        """
        Test with real Anthropic API.

        Runs only when ANTHROPIC_API_KEY environment variable is set.
        This enables testing in CI environments where API key is available.
        """
        from mcp_server_langgraph.core.agent import create_agent_graph

        graph = create_agent_graph()

        state = {
            "messages": [HumanMessage(content="What is 2+2?")],
            "next_action": "",
            "user_id": get_user_id("test"),
            "request_id": "integration-test",
        }

        result = await graph.ainvoke(state, config={"configurable": {"thread_id": "integration"}})

        assert result is not None
        assert len(result["messages"]) > 1
        # Should have a response mentioning "4"
        last_message = result["messages"][-1]
        assert isinstance(last_message, AIMessage)
        assert "4" in last_message.content


@pytest.mark.unit
@pytest.mark.xdist_group(name="agent_tests")
class TestRedisCheckpointerLifecycle:
    """
    Test Redis checkpointer lifecycle management (TDD RED phase).

    Tests written FIRST to ensure proper context manager cleanup.
    Will fail until cleanup hooks are implemented in agent.py
    """

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @patch("mcp_server_langgraph.core.agent.RedisSaver")
    def test_redis_checkpointer_context_manager_cleanup(self, mock_redis_saver):
        """
        Test Redis checkpointer context manager is properly cleaned up.

        GREEN: Verifies full lifecycle - creation AND cleanup.
        """
        from mcp_server_langgraph.core.agent import cleanup_checkpointer, create_checkpointer
        from mcp_server_langgraph.core.config import Settings

        # Mock context manager
        mock_ctx = MagicMock()
        mock_checkpointer = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_checkpointer)
        mock_ctx.__exit__ = MagicMock(return_value=None)
        mock_redis_saver.from_conn_string.return_value = mock_ctx

        settings = Settings(
            checkpoint_backend="redis",
            checkpoint_redis_url="redis://localhost:6379/0",
        )

        # Create checkpointer
        checkpointer = create_checkpointer(settings)

        # Verify context manager entered
        assert mock_ctx.__enter__.called, "Context manager __enter__ should be called during creation"

        # Verify checkpointer returned
        assert checkpointer == mock_checkpointer

        # Verify context manager reference is stored for later cleanup
        assert hasattr(checkpointer, "__context_manager__"), "Checkpointer must store context manager reference"
        assert checkpointer.__context_manager__ == mock_ctx

        # 🟢 GREEN: Call cleanup_checkpointer to trigger __exit__
        cleanup_checkpointer(checkpointer)

        # Verify context manager __exit__ was called to release Redis connections
        assert mock_ctx.__exit__.called, (
            "Redis checkpointer context manager __exit__ must be called to properly "
            "release connections and prevent resource leaks."
        )

        # Verify __exit__ was called with correct arguments (None, None, None for normal shutdown)
        mock_ctx.__exit__.assert_called_once_with(None, None, None)

    @patch("mcp_server_langgraph.core.agent.RedisSaver")
    def test_redis_checkpointer_stores_context_for_cleanup(self, mock_redis_saver):
        """
        Test Redis checkpointer stores context manager reference for cleanup.

        GREEN: Verifies context manager reference storage and cleanup capability.
        """
        from mcp_server_langgraph.core.agent import create_checkpointer
        from mcp_server_langgraph.core.config import Settings

        mock_ctx = MagicMock()
        mock_checkpointer = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_checkpointer)
        mock_ctx.__exit__ = MagicMock(return_value=None)
        mock_redis_saver.from_conn_string.return_value = mock_ctx

        settings = Settings(
            checkpoint_backend="redis",
            checkpoint_redis_url="redis://localhost:6379/0",
        )

        checkpointer = create_checkpointer(settings)

        # Verify checkpointer stores reference to context manager for cleanup
        assert hasattr(checkpointer, "__context_manager__") or hasattr(
            checkpointer, "_context"
        ), "Checkpointer must store context manager reference to enable proper cleanup"

        # Verify the stored context manager can be used for cleanup
        stored_ctx = getattr(checkpointer, "__context_manager__", getattr(checkpointer, "_context", None))
        assert stored_ctx is not None, "Stored context manager should not be None"
        assert stored_ctx == mock_ctx, "Stored context manager should match original"

        # Verify cleanup can be performed using the stored reference
        stored_ctx.__exit__(None, None, None)
        mock_ctx.__exit__.assert_called_once_with(None, None, None)

    @patch("mcp_server_langgraph.core.agent.RedisSaver")
    def test_memory_checkpointer_no_cleanup_needed(self, mock_redis_saver):
        """Test MemorySaver doesn't require context manager cleanup"""
        from mcp_server_langgraph.core.agent import create_checkpointer
        from mcp_server_langgraph.core.config import Settings

        settings = Settings(checkpoint_backend="memory")

        checkpointer = create_checkpointer(settings)

        # MemorySaver doesn't need context manager
        assert checkpointer is not None
        # Should not call Redis
        assert not mock_redis_saver.called
