"""Unit tests for agent.py - LangGraph Agent"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage


@pytest.mark.unit
class TestAgentState:
    """Test AgentState TypedDict"""

    def test_agent_state_structure(self):
        """Test AgentState can be created with required fields"""
        from mcp_server_langgraph.core.agent import AgentState

        state: AgentState = {
            "messages": [HumanMessage(content="Hello")],
            "next_action": "respond",
            "user_id": "user:alice",
            "request_id": "req-123",
        }

        assert len(state["messages"]) == 1
        assert state["next_action"] == "respond"
        assert state["user_id"] == "user:alice"
        assert state["request_id"] == "req-123"


@pytest.mark.unit
class TestAgentGraph:
    """Test LangGraph agent creation and execution"""

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
            "user_id": "user:alice",
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
            "user_id": "user:bob",
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
            "user_id": "user:alice",
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
            "user_id": "user:alice",
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
            "user_id": "user:alice",
            "request_id": "req-1",
        }
        result1 = await graph.ainvoke(state1, config={"configurable": {"thread_id": thread_id}})

        # Second message - should maintain history
        state2 = {
            "messages": [HumanMessage(content="Second message")],
            "next_action": "",
            "user_id": "user:alice",
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
            "user_id": "user:alice",
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
            "user_id": "user:test",
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
            "user_id": "user:test",
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
            "user_id": "user:test",
            "request_id": "req-test",
        }

        result = await graph.ainvoke(state_search, config={"configurable": {"thread_id": "test-routing"}})

        assert result is not None


@pytest.mark.integration
class TestAgentIntegration:
    """Integration tests for agent (may require API keys)"""

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
            "user_id": "user:alice",
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

    @pytest.mark.skip(reason="Requires ANTHROPIC_API_KEY")
    async def test_real_llm_invocation(self):
        """Test with real Anthropic API"""
        import os

        from mcp_server_langgraph.core.agent import create_agent_graph

        if not os.getenv("ANTHROPIC_API_KEY"):
            pytest.skip("ANTHROPIC_API_KEY not set")

        graph = create_agent_graph()

        state = {
            "messages": [HumanMessage(content="What is 2+2?")],
            "next_action": "",
            "user_id": "user:test",
            "request_id": "integration-test",
        }

        result = await graph.ainvoke(state, config={"configurable": {"thread_id": "integration"}})

        assert result is not None
        assert len(result["messages"]) > 1
        # Should have a response mentioning "4"
        last_message = result["messages"][-1]
        assert isinstance(last_message, AIMessage)
        assert "4" in last_message.content
