"""Unit tests for agent.py - LangGraph Agent"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from langchain_core.messages import HumanMessage, AIMessage


@pytest.mark.unit
class TestAgentState:
    """Test AgentState TypedDict"""

    def test_agent_state_structure(self):
        """Test AgentState can be created with required fields"""
        from agent import AgentState

        state: AgentState = {
            "messages": [HumanMessage(content="Hello")],
            "next_action": "respond",
            "user_id": "user:alice",
            "request_id": "req-123"
        }

        assert len(state["messages"]) == 1
        assert state["next_action"] == "respond"
        assert state["user_id"] == "user:alice"
        assert state["request_id"] == "req-123"


@pytest.mark.unit
class TestAgentGraph:
    """Test LangGraph agent creation and execution"""

    @patch('llm_factory.create_llm_from_config')
    def test_create_agent_graph(self, mock_create_llm):
        """Test agent graph is created successfully"""
        from agent import create_agent_graph

        # Mock the LLM
        mock_llm = MagicMock()
        mock_create_llm.return_value = mock_llm

        graph = create_agent_graph()

        assert graph is not None
        assert hasattr(graph, 'invoke')
        assert hasattr(graph, 'stream')

    @patch('agent.create_llm_from_config')
    def test_route_input_to_respond(self, mock_create_llm):
        """Test routing to direct response"""
        from agent import create_agent_graph

        mock_model = MagicMock()
        mock_model.invoke.return_value = AIMessage(content="Hello! I can help you.")
        mock_create_llm.return_value = mock_model

        graph = create_agent_graph()

        initial_state = {
            "messages": [HumanMessage(content="Hello, what can you do?")],
            "next_action": "",
            "user_id": "user:alice",
            "request_id": "req-123"
        }

        result = graph.invoke(initial_state, config={"configurable": {"thread_id": "test-1"}})

        assert result is not None
        assert "messages" in result
        assert len(result["messages"]) > 1
        assert result["next_action"] == "end"

    @patch('agent.create_llm_from_config')
    def test_route_input_to_tools(self, mock_create_llm):
        """Test routing to tools when keywords detected"""
        from agent import create_agent_graph

        mock_model = MagicMock()
        mock_model.invoke.return_value = AIMessage(content="Search completed.")
        mock_create_llm.return_value = mock_model

        graph = create_agent_graph()

        initial_state = {
            "messages": [HumanMessage(content="Please search for information about Python")],
            "next_action": "",
            "user_id": "user:bob",
            "request_id": "req-456"
        }

        result = graph.invoke(initial_state, config={"configurable": {"thread_id": "test-2"}})

        assert result is not None
        # Should go through tools node
        assert len(result["messages"]) > 2

    @patch('agent.create_llm_from_config')
    def test_route_with_calculate_keyword(self, mock_create_llm):
        """Test routing detects calculate keyword"""
        from agent import create_agent_graph

        mock_model = MagicMock()
        mock_model.invoke.return_value = AIMessage(content="Calculation result")
        mock_create_llm.return_value = mock_model

        graph = create_agent_graph()

        initial_state = {
            "messages": [HumanMessage(content="Calculate 2 + 2")],
            "next_action": "",
            "user_id": "user:alice",
            "request_id": "req-789"
        }

        result = graph.invoke(initial_state, config={"configurable": {"thread_id": "test-3"}})

        assert result is not None
        assert result["next_action"] == "end"

    @patch('agent.create_llm_from_config')
    def test_agent_with_conversation_history(self, mock_create_llm):
        """Test agent handles conversation history"""
        from agent import create_agent_graph

        mock_model = MagicMock()
        mock_model.invoke.return_value = AIMessage(content="Follow-up response")
        mock_create_llm.return_value = mock_model

        graph = create_agent_graph()

        initial_state = {
            "messages": [
                HumanMessage(content="What is Python?"),
                AIMessage(content="Python is a programming language."),
                HumanMessage(content="Tell me more")
            ],
            "next_action": "",
            "user_id": "user:alice",
            "request_id": "req-999"
        }

        result = graph.invoke(initial_state, config={"configurable": {"thread_id": "test-4"}})

        assert result is not None
        assert len(result["messages"]) > 3

    @patch('agent.create_llm_from_config')
    def test_checkpointing_works(self, mock_create_llm):
        """Test conversation checkpointing"""
        from agent import create_agent_graph

        mock_model = MagicMock()
        mock_model.invoke.return_value = AIMessage(content="Response")
        mock_create_llm.return_value = mock_model

        graph = create_agent_graph()

        thread_id = "checkpoint-test"

        # First message
        state1 = {
            "messages": [HumanMessage(content="First message")],
            "next_action": "",
            "user_id": "user:alice",
            "request_id": "req-1"
        }
        result1 = graph.invoke(state1, config={"configurable": {"thread_id": thread_id}})

        # Second message - should maintain history
        state2 = {
            "messages": [HumanMessage(content="Second message")],
            "next_action": "",
            "user_id": "user:alice",
            "request_id": "req-2"
        }
        result2 = graph.invoke(state2, config={"configurable": {"thread_id": thread_id}})

        # Second result should have more messages due to checkpointing
        assert len(result2["messages"]) > len(result1["messages"])

    def test_state_accumulation(self):
        """Test that messages accumulate in state"""
        from agent import AgentState
        import operator

        # Verify that the Annotated type with operator.add works
        state: AgentState = {
            "messages": [HumanMessage(content="First")],
            "next_action": "respond",
            "user_id": "user:alice",
            "request_id": "req-1"
        }

        # Simulate message accumulation
        new_messages = [AIMessage(content="Second")]
        combined = operator.add(state["messages"], new_messages)

        assert len(combined) == 2
        assert isinstance(combined[0], HumanMessage)
        assert isinstance(combined[1], AIMessage)

    @patch('agent.LANGSMITH_AVAILABLE', False)
    @patch('agent.create_llm_from_config')
    def test_agent_without_langsmith(self, mock_create_llm):
        """Test agent works when LangSmith is not available"""
        from agent import create_agent_graph

        mock_model = MagicMock()
        mock_model.invoke.return_value = AIMessage(content="Response without LangSmith")
        mock_create_llm.return_value = mock_model

        graph = create_agent_graph()

        initial_state = {
            "messages": [HumanMessage(content="Test message")],
            "next_action": "",
            "user_id": "user:test",
            "request_id": "req-test"
        }

        result = graph.invoke(initial_state, config={"configurable": {"thread_id": "test-no-langsmith"}})

        assert result is not None
        assert len(result["messages"]) > 0

    @patch('agent.create_llm_from_config')
    def test_agent_with_langsmith_enabled(self, mock_create_llm):
        """Test agent with LangSmith configuration"""
        from agent import create_agent_graph

        mock_model = MagicMock()
        mock_model.invoke.return_value = AIMessage(content="Response")
        mock_create_llm.return_value = mock_model

        # This test verifies the agent works regardless of LangSmith availability
        graph = create_agent_graph()

        initial_state = {
            "messages": [HumanMessage(content="Test message")],
            "next_action": "",
            "user_id": "user:test",
            "request_id": "req-test"
        }

        result = graph.invoke(initial_state, config={"configurable": {"thread_id": "test-langsmith"}})

        assert result is not None
        assert len(result["messages"]) > 0

    @patch('agent.create_llm_from_config')
    def test_routing_with_tool_keywords(self, mock_create_llm):
        """Test routing detects tool keywords"""
        from agent import create_agent_graph

        mock_model = MagicMock()
        mock_model.invoke.return_value = AIMessage(content="Search result")
        mock_create_llm.return_value = mock_model

        graph = create_agent_graph()

        # Test with "search" keyword
        state_search = {
            "messages": [HumanMessage(content="Please search for information")],
            "next_action": "",
            "user_id": "user:test",
            "request_id": "req-test"
        }

        result = graph.invoke(state_search, config={"configurable": {"thread_id": "test-routing"}})

        assert result is not None


@pytest.mark.integration
class TestAgentIntegration:
    """Integration tests for agent (may require API keys)"""

    @pytest.mark.skip(reason="Requires ANTHROPIC_API_KEY")
    def test_real_llm_invocation(self):
        """Test with real Anthropic API"""
        import os
        from agent import create_agent_graph

        if not os.getenv("ANTHROPIC_API_KEY"):
            pytest.skip("ANTHROPIC_API_KEY not set")

        graph = create_agent_graph()

        state = {
            "messages": [HumanMessage(content="What is 2+2?")],
            "next_action": "",
            "user_id": "user:test",
            "request_id": "integration-test"
        }

        result = graph.invoke(state, config={"configurable": {"thread_id": "integration"}})

        assert result is not None
        assert len(result["messages"]) > 1
        # Should have a response mentioning "4"
        last_message = result["messages"][-1]
        assert isinstance(last_message, AIMessage)
        assert "4" in last_message.content
