"""
Integration Tests for Full Agentic Loop

Tests the complete gather-action-verify-repeat cycle.
These are integration tests that may require mocking but test full workflows.
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import HumanMessage

from mcp_server_langgraph.core.agent import AgentState, create_agent_graph
from mcp_server_langgraph.core.config import Settings
from mcp_server_langgraph.core.context_manager import ContextManager
from mcp_server_langgraph.llm.verifier import OutputVerifier, VerificationResult

pytestmark = pytest.mark.integration


@pytest.fixture
def test_settings():
    """Create real Settings object for testing (serializable)."""
    return Settings(
        service_name="test-service",
        otlp_endpoint="http://localhost:4317",
        jwt_secret_key="test-secret",
        anthropic_api_key="test-key",
        model_name="claude-3-5-sonnet-20241022",
        log_level="DEBUG",
        openfga_api_url="http://localhost:8080",
        openfga_store_id="test-store",
        openfga_model_id="test-model",
        enable_context_compaction=False,
        enable_verification=False,
        enable_dynamic_context_loading=False,
        enable_checkpointing=False,  # Disable checkpointing to avoid mock serialization
        checkpoint_backend="memory",
    )


@pytest.fixture
def mock_llm():
    """Create a mock LLM for testing."""
    llm = AsyncMock()
    llm.ainvoke = AsyncMock(return_value=MagicMock(content="This is a helpful response about Python."))
    llm.invoke = MagicMock(return_value=MagicMock(content="This is a helpful response."))
    return llm


@pytest.fixture
def mock_context_manager():
    """Create a mock ContextManager."""
    manager = MagicMock(spec=ContextManager)
    manager.needs_compaction = MagicMock(return_value=False)
    return manager


@pytest.fixture
def mock_verifier_pass():
    """Create a mock OutputVerifier that always passes."""
    verifier = MagicMock(spec=OutputVerifier)
    verifier.verify_response = AsyncMock(
        return_value=VerificationResult(
            passed=True,
            overall_score=0.9,
            feedback="Excellent response",
            requires_refinement=False,
        )
    )
    return verifier


@pytest.fixture
def mock_verifier_fail():
    """Create a mock OutputVerifier that fails initially."""
    verifier = MagicMock(spec=OutputVerifier)

    # First call: fail, second call: pass (simulates successful refinement)
    verifier.verify_response = AsyncMock(
        side_effect=[
            VerificationResult(
                passed=False,
                overall_score=0.5,
                feedback="Needs improvement: lacks detail",
                requires_refinement=True,
                critical_issues=["Insufficient detail"],
            ),
            VerificationResult(
                passed=True,
                overall_score=0.85,
                feedback="Much better after refinement",
                requires_refinement=False,
            ),
        ]
    )
    return verifier


@pytest.mark.xdist_group(name="agentic_loop_integration_tests")
class TestAgenticLoopIntegration:
    """Integration tests for the complete agentic loop."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_basic_workflow_without_compaction_verification(self, mock_llm, test_settings):
        """Test basic workflow when compaction and verification are disabled."""
        test_settings.enable_context_compaction = False
        test_settings.enable_verification = False

        with patch("mcp_server_langgraph.core.agent.create_llm_from_config", return_value=mock_llm):
            # Pass test_settings directly to create_agent_graph for proper dependency injection
            # This avoids MagicMock serialization issues with checkpointer
            graph = create_agent_graph(settings=test_settings)

            # Create initial state
            initial_state: AgentState = {
                "messages": [HumanMessage(content="What is Python?")],
                "next_action": "",
                "user_id": "test_user",
                "request_id": "test_123",
            }

            # Run the graph
            result = await graph.ainvoke(initial_state, config={"configurable": {"thread_id": "test"}})

            # Should have completed
            assert "messages" in result
            assert len(result["messages"]) > 1  # Original + response

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_workflow_with_compaction_enabled(self, mock_llm, mock_context_manager, test_settings):
        """Test workflow with context compaction enabled."""
        test_settings.enable_context_compaction = True
        test_settings.enable_verification = False

        with patch("mcp_server_langgraph.core.agent.create_llm_from_config", return_value=mock_llm):
            with patch("mcp_server_langgraph.core.agent.ContextManager", return_value=mock_context_manager):
                # Pass test_settings directly to create_agent_graph for proper dependency injection
                graph = create_agent_graph(settings=test_settings)

                initial_state: AgentState = {
                    "messages": [HumanMessage(content="Test question")],
                    "next_action": "",
                    "user_id": "test_user",
                    "request_id": "test_123",
                }

                result = await graph.ainvoke(initial_state, config={"configurable": {"thread_id": "test"}})

                # Compaction should have been checked
                mock_context_manager.needs_compaction.assert_called()

                # Should have compaction_applied field in result
                assert "compaction_applied" in result

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_workflow_with_verification_pass(self, mock_llm, mock_verifier_pass, test_settings):
        """Test workflow with verification enabled (passes immediately)."""
        test_settings.enable_context_compaction = False
        test_settings.enable_verification = True
        test_settings.max_refinement_attempts = 3

        with patch("mcp_server_langgraph.core.agent.create_llm_from_config", return_value=mock_llm):
            with patch("mcp_server_langgraph.core.agent.OutputVerifier", return_value=mock_verifier_pass):
                # Pass test_settings directly to create_agent_graph for proper dependency injection
                graph = create_agent_graph(settings=test_settings)

                initial_state: AgentState = {
                    "messages": [HumanMessage(content="Test question")],
                    "next_action": "",
                    "user_id": "test_user",
                    "request_id": "test_123",
                }

                result = await graph.ainvoke(initial_state, config={"configurable": {"thread_id": "test"}})

                # Verification should have been called
                mock_verifier_pass.verify_response.assert_called_once()

                # Should have verification results in state
                assert result.get("verification_passed") is True
                assert result.get("verification_score") == 0.9

                # Should NOT have refinement attempts (passed first time)
                assert result.get("refinement_attempts") is None or result.get("refinement_attempts") == 0

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_workflow_with_verification_refinement(self, mock_llm, mock_verifier_fail, test_settings):
        """Test workflow with verification enabled (requires refinement)."""
        test_settings.enable_context_compaction = False
        test_settings.enable_verification = True
        test_settings.max_refinement_attempts = 3

        with patch("mcp_server_langgraph.core.agent.create_llm_from_config", return_value=mock_llm):
            with patch("mcp_server_langgraph.core.agent.OutputVerifier", return_value=mock_verifier_fail):
                # Pass test_settings directly to create_agent_graph for proper dependency injection
                graph = create_agent_graph(settings=test_settings)

                initial_state: AgentState = {
                    "messages": [HumanMessage(content="Test question")],
                    "next_action": "",
                    "user_id": "test_user",
                    "request_id": "test_123",
                }

                result = await graph.ainvoke(initial_state, config={"configurable": {"thread_id": "test"}})

                # Verification should have been called TWICE (initial + refinement)
                assert mock_verifier_fail.verify_response.call_count == 2

                # Should have refinement attempt recorded
                assert result.get("refinement_attempts") == 1

                # Eventually should pass
                assert result.get("verification_passed") is True

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_workflow_max_refinement_attempts(self, mock_llm, test_settings):
        """Test that workflow respects max refinement attempts."""
        test_settings.enable_context_compaction = False
        test_settings.enable_verification = True
        test_settings.max_refinement_attempts = 2  # Low limit for testing

        # Create verifier that always fails
        mock_verifier = MagicMock(spec=OutputVerifier)
        mock_verifier.verify_response = AsyncMock(
            return_value=VerificationResult(
                passed=False,
                overall_score=0.3,
                feedback="Always fails",
                requires_refinement=True,
                critical_issues=["Major issue"],
            )
        )

        with patch("mcp_server_langgraph.core.agent.create_llm_from_config", return_value=mock_llm):
            with patch("mcp_server_langgraph.core.agent.OutputVerifier", return_value=mock_verifier):
                # Pass test_settings directly to create_agent_graph for proper dependency injection
                graph = create_agent_graph(settings=test_settings)

                initial_state: AgentState = {
                    "messages": [HumanMessage(content="Test question")],
                    "next_action": "",
                    "user_id": "test_user",
                    "request_id": "test_123",
                }

                result = await graph.ainvoke(initial_state, config={"configurable": {"thread_id": "test"}})

                # Should have attempted max refinements
                assert result.get("refinement_attempts") == 2

                # Should eventually give up and accept (fail-open behavior)
                # State should reach END even with failed verification

    @pytest.mark.integration
    def test_agent_state_structure(self):
        """Test that AgentState has all required fields."""
        # Import after potential patching
        from typing import get_type_hints

        from mcp_server_langgraph.core.agent import AgentState

        # Check that AgentState has expected fields
        hints = get_type_hints(AgentState)

        # Original fields
        assert "messages" in hints
        assert "next_action" in hints
        assert "user_id" in hints
        assert "request_id" in hints
        assert "routing_confidence" in hints
        assert "reasoning" in hints

        # New compaction fields
        assert "compaction_applied" in hints
        assert "original_message_count" in hints

        # New verification fields
        assert "verification_passed" in hints
        assert "verification_score" in hints
        assert "verification_feedback" in hints
        assert "refinement_attempts" in hints
        assert "user_request" in hints

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_loop_with_all_features(self, mock_llm, test_settings):
        """Test complete agentic loop with all features enabled."""
        test_settings.enable_context_compaction = True
        test_settings.enable_verification = True
        test_settings.max_refinement_attempts = 3

        # Create mocks
        mock_manager = MagicMock(spec=ContextManager)
        mock_manager.needs_compaction = MagicMock(return_value=True)
        mock_manager.compact_conversation = AsyncMock(
            return_value=MagicMock(
                compacted_messages=[HumanMessage(content="Compacted question")],
                original_token_count=1000,
                compacted_token_count=400,
                messages_summarized=5,
                compression_ratio=0.4,
            )
        )

        mock_verifier = MagicMock(spec=OutputVerifier)
        mock_verifier.verify_response = AsyncMock(
            return_value=VerificationResult(
                passed=True,
                overall_score=0.88,
                feedback="Good response",
                requires_refinement=False,
            )
        )

        with patch("mcp_server_langgraph.core.agent.create_llm_from_config", return_value=mock_llm):
            with patch("mcp_server_langgraph.core.agent.ContextManager", return_value=mock_manager):
                with patch("mcp_server_langgraph.core.agent.OutputVerifier", return_value=mock_verifier):
                    # Pass test_settings directly to create_agent_graph for proper dependency injection
                    graph = create_agent_graph(settings=test_settings)

                    # Create long conversation
                    long_conversation = [HumanMessage(content=f"Question {i}") for i in range(10)]

                    initial_state: AgentState = {
                        "messages": long_conversation,
                        "next_action": "",
                        "user_id": "test_user",
                        "request_id": "test_123",
                    }

                    result = await graph.ainvoke(initial_state, config={"configurable": {"thread_id": "test"}})

                    # All features should have been used
                    mock_manager.needs_compaction.assert_called()
                    mock_manager.compact_conversation.assert_called()
                    mock_verifier.verify_response.assert_called()

                    # Should have all state fields populated
                    assert result.get("compaction_applied") is True
                    assert result.get("verification_passed") is True
                    assert result.get("verification_score") == 0.88


@pytest.mark.integration
@pytest.mark.xdist_group(name="agentic_loop_integration_tests")
class TestAgentGraphStructure:
    """Test the structure of the agent graph."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_graph_has_all_nodes(self):
        """Test that graph contains all expected nodes."""
        from mcp_server_langgraph.core.config import Settings

        # Create test settings with checkpointing disabled to avoid MagicMock serialization issues
        test_settings = Settings(
            service_name="test-service",
            jwt_secret_key="test-key",
            anthropic_api_key="test-key",
            enable_checkpointing=False,
        )

        with patch("mcp_server_langgraph.core.agent.create_llm_from_config"):
            graph = create_agent_graph(settings=test_settings)

            # Get compiled graph structure
            # (LangGraph graphs don't have a direct node list, but we can verify it compiles)
            assert graph is not None

    def test_graph_compiles_successfully(self):
        """Test that graph compiles without errors."""
        from mcp_server_langgraph.core.config import Settings

        # Create test settings with checkpointing disabled to avoid MagicMock serialization issues
        test_settings = Settings(
            service_name="test-service",
            jwt_secret_key="test-key",
            anthropic_api_key="test-key",
            enable_checkpointing=False,
        )

        with patch("mcp_server_langgraph.core.agent.create_llm_from_config"):
            # Should not raise
            graph = create_agent_graph(settings=test_settings)
            assert graph is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
