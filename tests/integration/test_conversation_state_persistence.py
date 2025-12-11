"""
Regression Tests for Conversation State Persistence

Tests that conversation history is properly maintained across multiple turns
and not wiped by generate_response, verify_response, or refine_response.

Related to Codex Finding #1 (CRITICAL):
- agent.py:676 previously returned fresh ["messages": [response]] instead of appending
"""

import gc
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from mcp_server_langgraph.core.agent import AgentState, create_agent_graph
from mcp_server_langgraph.core.config import Settings

# Mark as integration test (file is in tests/integration/)
pytestmark = pytest.mark.integration

# xdist can cause LLM mock to fail due to agent graph singleton caching across workers
_XDIST_LLM_MOCK_UNSTABLE = os.getenv("PYTEST_XDIST_WORKER") is not None


@pytest.fixture
def test_settings():
    """Create test settings"""
    return Settings(
        service_name="test-service",
        anthropic_api_key="test-key",
        enable_verification=False,
        enable_checkpointing=False,
        enable_context_compaction=False,
    )


@pytest.fixture
def mock_llm():
    """Create a mock LLM for testing."""
    llm = AsyncMock(return_value=None)  # Container for configured methods
    llm.ainvoke = AsyncMock(return_value=AIMessage(content="Test response"))
    llm.invoke = MagicMock(return_value=AIMessage(content="Test response"))
    return llm


@pytest.mark.xdist_group(name="conversation_state_persistence_tests")
class TestConversationStatePersistence:
    """Test that conversation state is preserved across agent operations."""

    def setup_method(self):
        """Reset agent graph singleton before each test."""
        import mcp_server_langgraph.core.agent as agent_module

        # Reset agent graph cache to ensure patches apply
        agent_module._agent_graph_cache = None

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_generate_response_appends_to_messages_not_replaces(self, test_settings, mock_llm):
        """
        CRITICAL: generate_response must APPEND to message history, not replace it.

        Regression test for: agent.py:676
        Bug: return {**state, "messages": [response], ...}  # ❌ Creates fresh list
        Fix: return {**state, "messages": state["messages"] + [response], ...}  # ✅ Appends
        """
        # Arrange: Create a multi-turn conversation state
        initial_messages = [
            HumanMessage(content="What is 2+2?"),
            AIMessage(content="2+2 equals 4"),
            HumanMessage(content="What about 3+3?"),
        ]

        state: AgentState = {
            "messages": initial_messages,
            "next_action": "",
            "user_id": "test-user",
            "request_id": "test-request",
        }

        # Mock the LLM to return a specific response
        mock_llm.ainvoke = AsyncMock(return_value=AIMessage(content="3+3 equals 6"))

        with patch("mcp_server_langgraph.core.agent.create_llm_from_config", return_value=mock_llm):
            # Get the agent graph
            graph = create_agent_graph(test_settings)

            # Act: Run the graph (which will call generate_response)
            result_state = await graph.ainvoke(state, config={"configurable": {"thread_id": "test"}})

            # Assert: Message history should be preserved AND new message added
            result_messages = result_state["messages"]

            # CRITICAL ASSERTION
            assert len(result_messages) >= 4, (
                f"Expected at least 4 messages (3 original + 1 new), got {len(result_messages)}. "
                f"This indicates generate_response is REPLACING the message list instead of APPENDING!\n"
                f"Messages: {[m.content for m in result_messages]}"
            )

            # Verify original messages are still present
            assert result_messages[0].content == "What is 2+2?", "First message lost!"
            assert result_messages[1].content == "2+2 equals 4", "Second message lost!"
            assert result_messages[2].content == "What about 3+3?", "Third message lost!"

            # Verify new message was appended
            assert any("3+3" in msg.content or "6" in msg.content for msg in result_messages[3:]), (
                "New response not appended correctly"
            )

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        _XDIST_LLM_MOCK_UNSTABLE,
        reason="Agent graph singleton caching can cause LLM mock to fail under xdist",
        strict=False,  # Allow to pass if mock is applied correctly
    )
    async def test_multiple_sequential_invocations_accumulate_history(self, test_settings, mock_llm):
        """
        Test that multiple sequential graph invocations continue to accumulate history.

        This ensures the bug doesn't just affect the first turn, but ALL turns.
        """
        # Arrange: Start with a simple conversation
        state: AgentState = {
            "messages": [HumanMessage(content="Hello")],
            "next_action": "",
            "user_id": "test-user",
            "request_id": "test-request",
        }

        # Create a callable mock that returns responses in sequence across multiple graph invocations
        # The graph calls the LLM multiple times per invocation (router + generate_response)
        # We want to return consistent responses for all calls within each invocation
        invocation_responses = ["Response 1", "Response 2", "Response 3"]
        current_invocation = [0]  # Use list to allow mutation in nested function

        async def mock_ainvoke(*args, **kwargs):
            """Mock that returns appropriate response for current invocation"""
            idx = min(current_invocation[0], len(invocation_responses) - 1)
            return AIMessage(content=invocation_responses[idx])

        mock_llm.ainvoke = mock_ainvoke

        with patch("mcp_server_langgraph.core.agent.create_llm_from_config", return_value=mock_llm):
            graph = create_agent_graph(test_settings)

            # Act: Run graph THREE times
            state = await graph.ainvoke(state, config={"configurable": {"thread_id": "test1"}})
            assert len(state["messages"]) == 2, f"After 1st call: expected 2 messages, got {len(state['messages'])}"
            current_invocation[0] = 1  # Move to next response

            # Add a human message for second turn
            state["messages"] = state["messages"] + [HumanMessage(content="Question 2")]
            state = await graph.ainvoke(state, config={"configurable": {"thread_id": "test2"}})
            assert len(state["messages"]) == 4, f"After 2nd call: expected 4 messages, got {len(state['messages'])}"
            current_invocation[0] = 2  # Move to next response

            # Add a human message for third turn
            state["messages"] = state["messages"] + [HumanMessage(content="Question 3")]
            state = await graph.ainvoke(state, config={"configurable": {"thread_id": "test3"}})

            # Assert: Should have 6 messages total (3 human + 3 AI)
            assert len(state["messages"]) == 6, (
                f"Expected 6 messages after 3 turns, got {len(state['messages'])}. "
                f"Conversation history not accumulating properly!"
            )

            # Verify the sequence
            assert state["messages"][0].content == "Hello"
            assert state["messages"][1].content == "Response 1"
            assert state["messages"][2].content == "Question 2"
            assert state["messages"][3].content == "Response 2"
            assert state["messages"][4].content == "Question 3"
            assert state["messages"][5].content == "Response 3"

    @pytest.mark.asyncio
    async def test_verification_enabled_preserves_history(self, mock_llm):
        """
        Test that when verification is enabled, conversation history is still preserved.

        This tests the verify -> refine loop maintains full context.
        """
        # Arrange: Multi-turn conversation that will go through verification
        initial_messages = [
            HumanMessage(content="Explain quantum computing"),
            AIMessage(content="Quantum computing is about qubits."),
            HumanMessage(content="Tell me more"),
        ]

        state: AgentState = {
            "messages": initial_messages,
            "next_action": "",
            "user_id": "test-user",
            "request_id": "test-request",
        }

        # Mock responses
        mock_llm.ainvoke = AsyncMock(
            return_value=AIMessage(
                content="Quantum computing uses quantum mechanical phenomena like superposition and entanglement."
            )
        )

        # Use settings with verification enabled
        settings_with_verification = Settings(
            service_name="test-service",
            anthropic_api_key="test-key",
            enable_verification=True,
            max_refinement_attempts=2,
            enable_checkpointing=False,
            enable_context_compaction=False,
        )

        # Mock the verifier to pass
        from mcp_server_langgraph.llm.verifier import VerificationResult

        mock_verifier = MagicMock()
        mock_verifier.verify_response = AsyncMock(
            return_value=VerificationResult(
                passed=True,
                overall_score=0.9,
                feedback="Good response",
                requires_refinement=False,
            )
        )

        with patch("mcp_server_langgraph.core.agent.create_llm_from_config", return_value=mock_llm):
            with patch("mcp_server_langgraph.core.agent.OutputVerifier", return_value=mock_verifier):
                graph = create_agent_graph(settings_with_verification)

                # Act: Run the graph with verification
                result_state = await graph.ainvoke(state, config={"configurable": {"thread_id": "test"}})

                # Assert: All original messages should STILL be present
                result_messages = result_state["messages"]

                # Should have at least 4 messages (3 original + 1 new response)
                assert len(result_messages) >= 4, (
                    f"Expected at least 4 messages, got {len(result_messages)}. "
                    f"Conversation history lost during verification loop!"
                )

                # Verify original context is preserved
                assert result_messages[0].content == "Explain quantum computing", "First message lost!"
                assert result_messages[1].content == "Quantum computing is about qubits.", "Second message lost!"
                assert result_messages[2].content == "Tell me more", "Third message lost!"

                # Verify new response is present
                assert any("quantum" in msg.content.lower() for msg in result_messages[3:]), "New response not added correctly"

    @pytest.mark.asyncio
    async def test_empty_initial_state_works_correctly(self, test_settings, mock_llm):
        """
        Test that even with a fresh/empty conversation, the agent works correctly.

        This ensures our fix doesn't break the initial message case.
        """
        # Arrange: Fresh conversation with just one message
        state: AgentState = {
            "messages": [HumanMessage(content="Hello, first message!")],
            "next_action": "",
            "user_id": "test-user",
            "request_id": "test-request",
        }

        mock_llm.ainvoke = AsyncMock(return_value=AIMessage(content="Hello! How can I help you?"))

        with patch("mcp_server_langgraph.core.agent.create_llm_from_config", return_value=mock_llm):
            graph = create_agent_graph(test_settings)

            # Act
            result_state = await graph.ainvoke(state, config={"configurable": {"thread_id": "test"}})

            # Assert: Should have 2 messages (original + response)
            result_messages = result_state["messages"]
            assert len(result_messages) == 2, f"Expected 2 messages, got {len(result_messages)}"
            assert result_messages[0].content == "Hello, first message!"
            assert "help" in result_messages[1].content.lower()
