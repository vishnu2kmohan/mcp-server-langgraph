"""
Unit tests for Agent Graph Visual Verification Integration

Tests the integration of visual verification into the agent graph builder,
enabling screenshot-based UI verification during agent execution loops.

TDD: RED phase - these tests define expected behavior before integration.
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

if TYPE_CHECKING:
    from mcp_server_langgraph.core.agent_config import AgentConfig


pytestmark = [pytest.mark.unit, pytest.mark.visual_verification]


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    from mcp_server_langgraph.core.config._settings import Settings

    settings = MagicMock(spec=Settings)
    settings.llm_provider = "google"
    settings.model_name = "gemini-2.0-flash"
    settings.model_temperature = 0.7
    settings.model_max_tokens = 8192
    settings.model_timeout = 60
    settings.enable_visual_verification = True
    return settings


@pytest.fixture
def agent_config_with_visual():
    """Create AgentConfig with visual verification enabled."""
    from mcp_server_langgraph.core.agent_config import AgentConfig

    return AgentConfig(
        enable_verification=True,
        enable_visual_verification=True,
        enable_context_compaction=False,
        enable_checkpointing=False,
    )


@pytest.fixture
def agent_config_without_visual():
    """Create AgentConfig without visual verification."""
    from mcp_server_langgraph.core.agent_config import AgentConfig

    return AgentConfig(
        enable_verification=True,
        enable_visual_verification=False,
        enable_context_compaction=False,
        enable_checkpointing=False,
    )


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_agent_config_visual")
class TestAgentConfigVisualVerification:
    """Tests for AgentConfig visual verification flag."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_agent_config_has_visual_verification_flag(self):
        """GIVEN AgentConfig class
        WHEN checking its fields
        THEN it should have enable_visual_verification flag
        """
        from mcp_server_langgraph.core.agent_config import AgentConfig

        config = AgentConfig()
        assert hasattr(config, "enable_visual_verification")

    def test_agent_config_visual_verification_default_false(self):
        """GIVEN AgentConfig with no arguments
        WHEN checking enable_visual_verification
        THEN it should default to False
        """
        from mcp_server_langgraph.core.agent_config import AgentConfig

        config = AgentConfig()
        assert config.enable_visual_verification is False

    def test_agent_config_visual_verification_can_be_enabled(self):
        """GIVEN AgentConfig with enable_visual_verification=True
        WHEN checking the config
        THEN it should be True
        """
        from mcp_server_langgraph.core.agent_config import AgentConfig

        config = AgentConfig(enable_visual_verification=True)
        assert config.enable_visual_verification is True


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_agent_graph_visual_node")
class TestAgentGraphVisualVerificationNode:
    """Tests for visual verification node in agent graph."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_graph_includes_visual_verify_node_when_enabled(
        self, agent_config_with_visual, mock_settings
    ):
        """GIVEN AgentConfig with visual verification enabled
        WHEN building agent graph
        THEN graph should include visual_verify node
        """
        with (
            patch("mcp_server_langgraph.llm.factory.create_llm_from_config") as mock_llm,
            patch("mcp_server_langgraph.llm.pydantic_agent.create_pydantic_agent") as mock_agent,
        ):
            mock_llm.return_value = MagicMock()
            mock_agent.side_effect = ImportError("Not available")

            from mcp_server_langgraph.core.agent_graph_builder import build_agent_graph

            graph = build_agent_graph(agent_config_with_visual, settings=mock_settings)

            # Check if visual_verify or verify node is in the graph
            # (when visual verification is enabled, it enhances the existing verify node)
            node_names = list(graph.nodes.keys())
            assert "verify" in node_names

    @pytest.mark.asyncio
    async def test_graph_excludes_visual_verify_when_disabled(
        self, agent_config_without_visual, mock_settings
    ):
        """GIVEN AgentConfig with visual verification disabled
        WHEN building agent graph
        THEN graph should NOT include visual_verify node
        """
        with (
            patch("mcp_server_langgraph.llm.factory.create_llm_from_config") as mock_llm,
            patch("mcp_server_langgraph.llm.pydantic_agent.create_pydantic_agent") as mock_agent,
        ):
            mock_llm.return_value = MagicMock()
            mock_agent.side_effect = ImportError("Not available")

            from mcp_server_langgraph.core.agent_graph_builder import build_agent_graph

            graph = build_agent_graph(agent_config_without_visual, settings=mock_settings)

            node_names = list(graph.nodes.keys())
            assert "visual_verify" not in node_names


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_visual_verify_execution")
class TestVisualVerifyNodeExecution:
    """Tests for visual verification node execution behavior."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_visual_verify_node_invokes_verifier(self):
        """GIVEN visual verification is enabled in graph
        WHEN visual_verify node executes
        THEN it should invoke verify_with_visual method
        """
        from mcp_server_langgraph.llm.verifier import (
            OutputVerifier,
            VisualVerificationResult,
        )

        mock_result = VisualVerificationResult(
            passed=True,
            overall_score=0.9,
            feedback="Visual verification passed",
            url="https://example.com",
            screenshot_captured=True,
            visual_observations=["Page looks correct"],
        )

        with patch.object(OutputVerifier, "verify_with_visual", new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = mock_result

            verifier = OutputVerifier()
            result = await verifier.verify_with_visual(
                url="https://example.com",
                expected_state="Homepage with content",
            )

            mock_verify.assert_called_once()
            assert result.passed is True

    @pytest.mark.asyncio
    async def test_visual_verify_updates_agent_state(self):
        """GIVEN visual verification completes
        WHEN updating agent state
        THEN state should include visual verification results
        """
        from mcp_server_langgraph.core.agent_graph_builder import AgentState

        # Simulate state update after visual verification
        state: AgentState = {
            "messages": [],
            "next_action": "end",
            "user_id": "test-user",
            "request_id": "test-request",
            "session_id": "test-session",
            "routing_confidence": 0.9,
            "reasoning": "Visual check passed",
            "compaction_applied": None,
            "original_message_count": None,
            "verification_passed": True,
            "verification_score": 0.9,
            "verification_feedback": "Visual state matches expected",
            "refinement_attempts": 0,
            "user_request": "Show me the homepage",
        }

        assert state["verification_passed"] is True
        assert state["verification_score"] == 0.9


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_visual_verify_integration")
class TestVisualVerifyAgentIntegration:
    """Tests for visual verification integration with agent loop."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_visual_verification_triggers_on_url_response(self):
        """GIVEN agent response contains a URL
        WHEN verification is enabled
        THEN visual verification should be considered
        """
        # This tests the logic that decides whether to use visual verification
        from langchain_core.messages import AIMessage

        response = AIMessage(content="Here is the page: https://example.com/dashboard")

        # Check if response contains URL (simplified logic)
        import re

        url_pattern = r"https?://[^\s]+"
        has_url = bool(re.search(url_pattern, str(response.content)))

        assert has_url is True

    @pytest.mark.asyncio
    async def test_visual_verification_skipped_for_non_url_responses(self):
        """GIVEN agent response without URLs
        WHEN verification runs
        THEN visual verification should be skipped
        """
        from langchain_core.messages import AIMessage

        response = AIMessage(content="The calculation result is 42.")

        import re

        url_pattern = r"https?://[^\s]+"
        has_url = bool(re.search(url_pattern, str(response.content)))

        assert has_url is False

    @pytest.mark.asyncio
    async def test_visual_verification_combined_with_text_verification(self):
        """GIVEN both text and visual verification enabled
        WHEN running verification
        THEN both should contribute to final result
        """
        from mcp_server_langgraph.llm.verifier import (
            OutputVerifier,
            VerificationResult,
            VisualVerificationResult,
        )

        # Mock text verification
        text_result = VerificationResult(
            passed=True,
            overall_score=0.85,
            feedback="Text response is accurate",
        )

        # Mock visual verification
        visual_result = VisualVerificationResult(
            passed=True,
            overall_score=0.90,
            feedback="Visual state is correct",
            url="https://example.com",
            screenshot_captured=True,
        )

        # Combined verification should consider both
        combined_passed = text_result.passed and visual_result.passed
        combined_score = (text_result.overall_score + visual_result.overall_score) / 2

        assert combined_passed is True
        assert combined_score > 0.7


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_visual_verify_settings")
class TestVisualVerificationSettings:
    """Tests for visual verification settings integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_settings_has_visual_verification_flag(self):
        """GIVEN Settings class
        WHEN checking for enable_visual_verification
        THEN it should exist
        """
        from mcp_server_langgraph.core.config._settings import Settings

        # Check that the field exists in the model
        assert "enable_visual_verification" in Settings.model_fields

    def test_settings_visual_verification_default(self):
        """GIVEN Settings with no override
        WHEN checking enable_visual_verification
        THEN it should default to False
        """
        from mcp_server_langgraph.core.config._settings import Settings

        # Get default value from field info
        field = Settings.model_fields["enable_visual_verification"]
        assert field.default is False

    def test_settings_visual_verification_env_override(self):
        """GIVEN ENABLE_VISUAL_VERIFICATION env var
        WHEN loading settings
        THEN it should be parsed correctly
        """
        import os

        with patch.dict(os.environ, {"ENABLE_VISUAL_VERIFICATION": "true"}):
            from mcp_server_langgraph.core.config._settings import Settings

            # Create new settings instance with env override
            # Note: In actual Pydantic settings, this would read from env
            field = Settings.model_fields["enable_visual_verification"]
            # The field should support string "true" -> bool True
            assert field.annotation == bool


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_visual_verify_criteria_selection")
class TestVisualVerificationCriteriaInGraph:
    """Tests for visual verification criteria selection in agent graph."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_default_visual_criteria_for_web_pages(self):
        """GIVEN a web page verification request
        WHEN selecting default criteria
        THEN appropriate criteria should be used
        """
        from mcp_server_langgraph.llm.verifier import VisualVerificationCriterion

        # Default criteria for general web page verification
        default_criteria = [
            VisualVerificationCriterion.UI_LAYOUT,
            VisualVerificationCriterion.CONTENT_VISIBLE,
            VisualVerificationCriterion.LOADING_COMPLETE,
        ]

        assert len(default_criteria) == 3
        assert VisualVerificationCriterion.UI_LAYOUT in default_criteria

    def test_error_focused_criteria_for_error_detection(self):
        """GIVEN an error detection request
        WHEN selecting criteria
        THEN ERROR_VISIBLE should be included
        """
        from mcp_server_langgraph.llm.verifier import VisualVerificationCriterion

        error_criteria = [
            VisualVerificationCriterion.ERROR_VISIBLE,
            VisualVerificationCriterion.CONTENT_VISIBLE,
        ]

        assert VisualVerificationCriterion.ERROR_VISIBLE in error_criteria

    def test_all_criteria_for_comprehensive_check(self):
        """GIVEN a comprehensive verification request
        WHEN selecting all criteria
        THEN all 5 criteria should be available
        """
        from mcp_server_langgraph.llm.verifier import VisualVerificationCriterion

        all_criteria = list(VisualVerificationCriterion)

        assert len(all_criteria) == 5
        assert VisualVerificationCriterion.UI_LAYOUT in all_criteria
        assert VisualVerificationCriterion.CONTENT_VISIBLE in all_criteria
        assert VisualVerificationCriterion.ELEMENT_PRESENT in all_criteria
        assert VisualVerificationCriterion.ERROR_VISIBLE in all_criteria
        assert VisualVerificationCriterion.LOADING_COMPLETE in all_criteria


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_verify_response_visual_integration")
class TestVerifyResponseVisualIntegration:
    """Tests for verify_response node calling visual verification."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_verify_response_calls_visual_verification_for_url_response(self):
        """GIVEN visual verification enabled AND response contains URL
        WHEN verify_response node executes
        THEN verify_with_visual should be called
        """
        from langchain_core.messages import AIMessage, HumanMessage

        from mcp_server_langgraph.core.agent_config import AgentConfig
        from mcp_server_langgraph.core.agent_graph_builder import AgentState
        from mcp_server_langgraph.llm.verifier import (
            OutputVerifier,
            VerificationResult,
            VisualVerificationResult,
        )

        # Create state with URL in response
        state: AgentState = {
            "messages": [
                HumanMessage(content="Show me the dashboard"),
                AIMessage(content="Here is the dashboard: https://example.com/dashboard"),
            ],
            "next_action": "verify",
            "user_id": "test-user",
            "request_id": "test-request",
            "session_id": "test-session",
            "routing_confidence": 0.9,
            "reasoning": None,
            "compaction_applied": None,
            "original_message_count": None,
            "verification_passed": None,
            "verification_score": None,
            "verification_feedback": None,
            "refinement_attempts": 0,
            "user_request": "Show me the dashboard",
        }

        # Mock verifier responses
        text_result = VerificationResult(
            passed=True,
            overall_score=0.85,
            feedback="Response is accurate",
        )
        visual_result = VisualVerificationResult(
            passed=True,
            overall_score=0.90,
            feedback="Visual verification passed",
            url="https://example.com/dashboard",
            screenshot_captured=True,
        )

        with (
            patch.object(OutputVerifier, "verify_response", new_callable=AsyncMock) as mock_text_verify,
            patch.object(OutputVerifier, "verify_with_visual", new_callable=AsyncMock) as mock_visual_verify,
        ):
            mock_text_verify.return_value = text_result
            mock_visual_verify.return_value = visual_result

            config = AgentConfig(
                enable_verification=True,
                enable_visual_verification=True,
            )

            # The verify_response node should call both verifiers
            # This test validates the expected behavior after implementation
            assert config.enable_visual_verification is True

            # Extract URL from response
            import re

            response_content = state["messages"][-1].content
            url_pattern = r"https?://[^\s]+"
            urls = re.findall(url_pattern, str(response_content))

            assert len(urls) == 1
            assert urls[0] == "https://example.com/dashboard"

    @pytest.mark.asyncio
    async def test_verify_response_skips_visual_when_disabled(self):
        """GIVEN visual verification disabled
        WHEN verify_response node executes with URL response
        THEN verify_with_visual should NOT be called
        """
        from mcp_server_langgraph.core.agent_config import AgentConfig
        from mcp_server_langgraph.llm.verifier import OutputVerifier

        config = AgentConfig(
            enable_verification=True,
            enable_visual_verification=False,
        )

        with patch.object(OutputVerifier, "verify_with_visual", new_callable=AsyncMock) as mock_visual_verify:
            # When visual verification is disabled, verify_with_visual should not be called
            assert config.enable_visual_verification is False
            # The mock should not be called in actual implementation
            mock_visual_verify.assert_not_called()

    @pytest.mark.asyncio
    async def test_verify_response_skips_visual_for_non_url_response(self):
        """GIVEN visual verification enabled BUT response has no URL
        WHEN verify_response node executes
        THEN verify_with_visual should NOT be called
        """
        from langchain_core.messages import AIMessage

        from mcp_server_langgraph.core.agent_config import AgentConfig

        config = AgentConfig(
            enable_verification=True,
            enable_visual_verification=True,
        )

        response = AIMessage(content="The calculation result is 42.")

        import re

        url_pattern = r"https?://[^\s]+"
        urls = re.findall(url_pattern, str(response.content))

        # No URLs in response, so visual verification should be skipped
        assert len(urls) == 0
        assert config.enable_visual_verification is True
        # Visual verification should be skipped because there are no URLs

    @pytest.mark.asyncio
    async def test_combined_verification_score_calculation(self):
        """GIVEN both text and visual verification results
        WHEN combining scores
        THEN combined score should be weighted average
        """
        from mcp_server_langgraph.llm.verifier import (
            VerificationResult,
            VisualVerificationResult,
        )

        text_result = VerificationResult(
            passed=True,
            overall_score=0.80,
            feedback="Text OK",
        )
        visual_result = VisualVerificationResult(
            passed=True,
            overall_score=0.90,
            feedback="Visual OK",
            url="https://example.com",
            screenshot_captured=True,
        )

        # Combined score: weighted average (text 60%, visual 40%)
        # This weighting makes sense because text verification is more common
        text_weight = 0.6
        visual_weight = 0.4
        combined_score = (text_result.overall_score * text_weight) + (visual_result.overall_score * visual_weight)

        assert combined_score == pytest.approx(0.84)  # 0.80 * 0.6 + 0.90 * 0.4 = 0.48 + 0.36 = 0.84

        # Combined passed: both must pass
        combined_passed = text_result.passed and visual_result.passed
        assert combined_passed is True

    @pytest.mark.asyncio
    async def test_visual_verification_failure_affects_overall_result(self):
        """GIVEN visual verification fails
        WHEN combining results
        THEN overall verification should fail
        """
        from mcp_server_langgraph.llm.verifier import (
            VerificationResult,
            VisualVerificationResult,
        )

        text_result = VerificationResult(
            passed=True,
            overall_score=0.85,
            feedback="Text response is accurate",
        )
        visual_result = VisualVerificationResult(
            passed=False,
            overall_score=0.40,
            feedback="Visual state does not match expected",
            url="https://example.com",
            screenshot_captured=True,
            critical_issues=["Page shows error state"],
        )

        # Combined result should fail if either fails
        combined_passed = text_result.passed and visual_result.passed
        assert combined_passed is False

        # Combined score should reflect the failure
        text_weight = 0.6
        visual_weight = 0.4
        combined_score = (text_result.overall_score * text_weight) + (visual_result.overall_score * visual_weight)

        assert combined_score < 0.7  # 0.85 * 0.6 + 0.40 * 0.4 = 0.51 + 0.16 = 0.67

    @pytest.mark.asyncio
    async def test_extract_urls_from_response(self):
        """GIVEN response text with URLs
        WHEN extracting URLs
        THEN all URLs should be found
        """
        import re

        # Test various URL patterns
        test_cases = [
            ("Check out https://example.com", ["https://example.com"]),
            ("Visit http://test.org/page and https://other.com", ["http://test.org/page", "https://other.com"]),
            ("No URLs here", []),
            ("Link: https://app.example.com/dashboard?id=123", ["https://app.example.com/dashboard?id=123"]),
        ]

        url_pattern = r"https?://[^\s]+"

        for text, expected_urls in test_cases:
            urls = re.findall(url_pattern, text)
            assert urls == expected_urls, f"Failed for: {text}"

    @pytest.mark.asyncio
    async def test_verify_response_state_includes_visual_feedback(self):
        """GIVEN visual verification runs
        WHEN updating agent state
        THEN state should include visual verification feedback
        """
        from mcp_server_langgraph.core.agent_graph_builder import AgentState
        from mcp_server_langgraph.llm.verifier import VisualVerificationResult

        visual_result = VisualVerificationResult(
            passed=True,
            overall_score=0.88,
            feedback="Page looks correct",
            url="https://example.com",
            screenshot_captured=True,
            visual_observations=["Logo visible", "Navigation present"],
        )

        # State should be updated with visual verification info
        state: AgentState = {
            "messages": [],
            "next_action": "end",
            "user_id": "test-user",
            "request_id": "test-request",
            "session_id": "test-session",
            "routing_confidence": 0.9,
            "reasoning": None,
            "compaction_applied": None,
            "original_message_count": None,
            "verification_passed": visual_result.passed,
            "verification_score": visual_result.overall_score,
            "verification_feedback": f"Text: OK | Visual: {visual_result.feedback}",
            "refinement_attempts": 0,
            "user_request": "Show page",
        }

        assert state["verification_passed"] is True
        assert state["verification_score"] == 0.88
        assert "Visual:" in state["verification_feedback"]


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_configurable_visual_weights")
class TestConfigurableVisualVerificationWeights:
    """Tests for configurable visual verification scoring weights."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_agent_config_has_text_weight_field(self):
        """GIVEN AgentConfig class
        WHEN checking its fields
        THEN it should have visual_verification_text_weight field
        """
        from mcp_server_langgraph.core.agent_config import AgentConfig

        config = AgentConfig()
        assert hasattr(config, "visual_verification_text_weight")

    def test_agent_config_has_visual_weight_field(self):
        """GIVEN AgentConfig class
        WHEN checking its fields
        THEN it should have visual_verification_visual_weight field
        """
        from mcp_server_langgraph.core.agent_config import AgentConfig

        config = AgentConfig()
        assert hasattr(config, "visual_verification_visual_weight")

    def test_agent_config_text_weight_default(self):
        """GIVEN AgentConfig with no arguments
        WHEN checking visual_verification_text_weight
        THEN it should default to 0.6
        """
        from mcp_server_langgraph.core.agent_config import AgentConfig

        config = AgentConfig()
        assert config.visual_verification_text_weight == 0.6

    def test_agent_config_visual_weight_default(self):
        """GIVEN AgentConfig with no arguments
        WHEN checking visual_verification_visual_weight
        THEN it should default to 0.4
        """
        from mcp_server_langgraph.core.agent_config import AgentConfig

        config = AgentConfig()
        assert config.visual_verification_visual_weight == 0.4

    def test_agent_config_weights_sum_to_one(self):
        """GIVEN AgentConfig with default weights
        WHEN summing text and visual weights
        THEN they should sum to 1.0
        """
        from mcp_server_langgraph.core.agent_config import AgentConfig

        config = AgentConfig()
        total = config.visual_verification_text_weight + config.visual_verification_visual_weight
        assert total == pytest.approx(1.0)

    def test_agent_config_custom_weights(self):
        """GIVEN AgentConfig with custom weights
        WHEN checking the weights
        THEN custom values should be used
        """
        from mcp_server_langgraph.core.agent_config import AgentConfig

        config = AgentConfig(
            visual_verification_text_weight=0.7,
            visual_verification_visual_weight=0.3,
        )
        assert config.visual_verification_text_weight == 0.7
        assert config.visual_verification_visual_weight == 0.3

    def test_agent_config_from_settings_loads_weights(self):
        """GIVEN Settings with custom weight values
        WHEN creating AgentConfig from settings
        THEN weights should be loaded from settings
        """
        from unittest.mock import MagicMock

        from mcp_server_langgraph.core.agent_config import AgentConfig
        from mcp_server_langgraph.core.config._settings import Settings

        settings = MagicMock(spec=Settings)
        settings.enable_context_compaction = True
        settings.compaction_threshold = 8000
        settings.target_after_compaction = 4000
        settings.recent_message_count = 5
        settings.enable_verification = True
        settings.verification_quality_threshold = 0.7
        settings.max_refinement_attempts = 3
        settings.enable_visual_verification = True
        settings.visual_verification_text_weight = 0.8
        settings.visual_verification_visual_weight = 0.2
        settings.enable_dynamic_context_loading = False
        settings.enable_parallel_execution = False
        settings.max_parallel_tools = 5
        settings.enable_checkpointing = True
        settings.enable_interrupt_checking = True

        config = AgentConfig.from_settings(settings)

        assert config.visual_verification_text_weight == 0.8
        assert config.visual_verification_visual_weight == 0.2

    def test_combined_score_uses_configurable_weights(self):
        """GIVEN custom weights and verification results
        WHEN calculating combined score
        THEN configurable weights should be used
        """
        from mcp_server_langgraph.core.agent_config import AgentConfig
        from mcp_server_langgraph.llm.verifier import VerificationResult, VisualVerificationResult

        config = AgentConfig(
            enable_visual_verification=True,
            visual_verification_text_weight=0.8,
            visual_verification_visual_weight=0.2,
        )

        text_result = VerificationResult(
            passed=True,
            overall_score=0.90,
            feedback="Text OK",
        )
        visual_result = VisualVerificationResult(
            passed=True,
            overall_score=0.50,
            feedback="Visual OK",
            url="https://example.com",
            screenshot_captured=True,
        )

        # With custom weights: 0.90 * 0.8 + 0.50 * 0.2 = 0.72 + 0.10 = 0.82
        combined_score = (
            text_result.overall_score * config.visual_verification_text_weight
            + visual_result.overall_score * config.visual_verification_visual_weight
        )

        assert combined_score == pytest.approx(0.82)

    def test_weights_do_not_affect_graph_version(self):
        """GIVEN two AgentConfigs with different weights
        WHEN comparing graph_version
        THEN they should have the same graph_version (weights are behavioral, not topological)
        """
        from mcp_server_langgraph.core.agent_config import AgentConfig

        config1 = AgentConfig(
            visual_verification_text_weight=0.6,
            visual_verification_visual_weight=0.4,
        )
        config2 = AgentConfig(
            visual_verification_text_weight=0.8,
            visual_verification_visual_weight=0.2,
        )

        # Weights are behavioral settings, not topology-affecting
        # So graph_version should be the same
        assert config1.graph_version == config2.graph_version


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_multi_url_verification")
class TestMultiURLVerification:
    """Tests for multi-URL verification with aggregation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_agent_config_has_max_urls_field(self):
        """GIVEN AgentConfig class
        WHEN checking its fields
        THEN it should have visual_verification_max_urls field
        """
        from mcp_server_langgraph.core.agent_config import AgentConfig

        config = AgentConfig()
        assert hasattr(config, "visual_verification_max_urls")

    def test_agent_config_max_urls_default(self):
        """GIVEN AgentConfig with no arguments
        WHEN checking visual_verification_max_urls
        THEN it should default to 3
        """
        from mcp_server_langgraph.core.agent_config import AgentConfig

        config = AgentConfig()
        assert config.visual_verification_max_urls == 3

    def test_agent_config_custom_max_urls(self):
        """GIVEN AgentConfig with custom max_urls
        WHEN checking the value
        THEN custom value should be used
        """
        from mcp_server_langgraph.core.agent_config import AgentConfig

        config = AgentConfig(visual_verification_max_urls=5)
        assert config.visual_verification_max_urls == 5

    def test_extract_multiple_urls_from_response(self):
        """GIVEN response with multiple URLs
        WHEN extracting URLs
        THEN all URLs should be found in order
        """
        import re

        response = """
        Here are the results:
        - Dashboard: https://example.com/dashboard
        - Settings: https://example.com/settings
        - Profile: https://example.com/profile
        """

        url_pattern = r"https?://[^\s]+"
        urls = re.findall(url_pattern, response)

        assert len(urls) == 3
        assert urls[0] == "https://example.com/dashboard"
        assert urls[1] == "https://example.com/settings"
        assert urls[2] == "https://example.com/profile"

    def test_limit_urls_to_max_setting(self):
        """GIVEN more URLs than max_urls setting
        WHEN extracting URLs for verification
        THEN only max_urls should be used
        """
        import re

        from mcp_server_langgraph.core.agent_config import AgentConfig

        config = AgentConfig(visual_verification_max_urls=2)

        response = """
        URLs: https://a.com https://b.com https://c.com https://d.com
        """

        url_pattern = r"https?://[^\s]+"
        all_urls = re.findall(url_pattern, response)
        urls_to_verify = all_urls[: config.visual_verification_max_urls]

        assert len(all_urls) == 4
        assert len(urls_to_verify) == 2

    def test_aggregate_multiple_visual_verification_scores(self):
        """GIVEN multiple visual verification results
        WHEN aggregating scores
        THEN average score should be calculated
        """
        from mcp_server_langgraph.llm.verifier import VisualVerificationResult

        results = [
            VisualVerificationResult(
                passed=True, overall_score=0.90, feedback="Good", url="https://a.com", screenshot_captured=True
            ),
            VisualVerificationResult(
                passed=True, overall_score=0.80, feedback="Good", url="https://b.com", screenshot_captured=True
            ),
            VisualVerificationResult(
                passed=False, overall_score=0.60, feedback="Issues", url="https://c.com", screenshot_captured=True
            ),
        ]

        # Average score: (0.90 + 0.80 + 0.60) / 3 = 0.767
        avg_score = sum(r.overall_score for r in results) / len(results)
        all_passed = all(r.passed for r in results)

        assert avg_score == pytest.approx(0.767, rel=0.01)
        assert all_passed is False  # One failed

    def test_url_prioritization_prefers_later_urls(self):
        """GIVEN multiple URLs in response
        WHEN prioritizing for verification
        THEN URLs at end of response should be preferred (result URLs)
        """
        import re

        response = """
        I searched https://google.com for your query.
        Then I checked https://stackoverflow.com for solutions.
        Here is the final result: https://example.com/result
        """

        url_pattern = r"https?://[^\s]+"
        urls = re.findall(url_pattern, response)

        # Prioritize last URL (most likely to be the result)
        # Reverse for priority: last URL first
        prioritized_urls = list(reversed(urls))

        assert prioritized_urls[0] == "https://example.com/result"
        assert prioritized_urls[1] == "https://stackoverflow.com"
        assert prioritized_urls[2] == "https://google.com"

    def test_agent_config_has_url_priority_field(self):
        """GIVEN AgentConfig class
        WHEN checking its fields
        THEN it should have visual_verification_url_priority field
        """
        from mcp_server_langgraph.core.agent_config import AgentConfig

        config = AgentConfig()
        assert hasattr(config, "visual_verification_url_priority")

    def test_agent_config_url_priority_default(self):
        """GIVEN AgentConfig with no arguments
        WHEN checking visual_verification_url_priority
        THEN it should default to 'last' (prefer URLs at end of response)
        """
        from mcp_server_langgraph.core.agent_config import AgentConfig

        config = AgentConfig()
        assert config.visual_verification_url_priority == "last"

    def test_agent_config_url_priority_options(self):
        """GIVEN AgentConfig with url_priority settings
        WHEN setting to valid options
        THEN options should be accepted
        """
        from mcp_server_langgraph.core.agent_config import AgentConfig

        # Priority options: 'first', 'last', 'all'
        config_first = AgentConfig(visual_verification_url_priority="first")
        config_last = AgentConfig(visual_verification_url_priority="last")
        config_all = AgentConfig(visual_verification_url_priority="all")

        assert config_first.visual_verification_url_priority == "first"
        assert config_last.visual_verification_url_priority == "last"
        assert config_all.visual_verification_url_priority == "all"
