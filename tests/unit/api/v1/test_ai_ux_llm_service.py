"""
AI UX LLM Service Tests

TDD tests for LLM-enhanced AI UX features.

Tests verify:
- LLM is called when available and enabled
- Fallback to heuristics when LLM unavailable
- Proper prompt construction
- Response parsing
- Error handling
- Feature flag control

Reference: UX Audit Plan - Phase 6 AI-Native Integration
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.messages import AIMessage

pytestmark = pytest.mark.unit

# =============================================================================
# Test Data
# =============================================================================

SAMPLE_ERROR_MESSAGE = "Connection timeout: Request to /api/v1/chat timed out after 30s"

SAMPLE_ERROR_LLM_RESPONSE = """
{
  "error_type": "timeout",
  "recovery_steps": [
    {
      "title": "Try again",
      "description": "Wait a moment and try your request again",
      "action_type": "automatic"
    },
    {
      "title": "Simplify your request",
      "description": "Try breaking your request into smaller parts",
      "action_type": "manual"
    }
  ],
  "auto_recoverable": true,
  "suggested_action": "Retry the request",
  "confidence": 0.95
}
"""

SAMPLE_EMPTY_STATE_LLM_RESPONSE = """
{
  "suggestions": [
    {
      "text": "Start building your first AI workflow",
      "action": "navigate",
      "target": "/studio/workflows/new",
      "confidence": 0.92,
      "category": "onboarding"
    },
    {
      "text": "Explore workflow templates",
      "action": "navigate",
      "target": "/studio/templates",
      "confidence": 0.88,
      "category": "discovery"
    }
  ]
}
"""

SAMPLE_PERSONA_LLM_RESPONSE = """
{
  "detected_persona": "alice-builder",
  "confidence": 0.85,
  "behavior_signals": [
    "Frequent workflow creation",
    "Advanced feature exploration",
    "Technical terminology in searches"
  ],
  "recommendation": "This user shows developer patterns. Consider enabling advanced features.",
  "ui_adaptations": [
    {"feature": "workflow_builder", "action": "unlock"},
    {"feature": "traces", "action": "promote"}
  ]
}
"""

SAMPLE_DISCLOSURE_LLM_RESPONSE = """
{
  "current_level": "intermediate",
  "recommended_level": "advanced",
  "confidence": 0.88,
  "unlock_features": ["workflow_builder", "traces", "mcp"],
  "personalized_message": "Your expertise with workflows suggests you're ready for advanced mode!"
}
"""

SAMPLE_NUDGE_LLM_RESPONSE = """
{
  "should_show": true,
  "nudge": {
    "id": "ai-generated-nudge",
    "type": "tooltip",
    "target_element": "[data-testid='workflow-panel']",
    "message": "You've been working on this page for a while. Try the workflow shortcuts!",
    "priority": "medium",
    "show_after_ms": 2000
  },
  "confidence": 0.82
}
"""

SAMPLE_ONBOARDING_LLM_RESPONSE = """
{
  "detected_intent": "build_automation",
  "confidence": 0.91,
  "recommended_path": [
    {"step": "template_gallery", "template": "automation-starter", "guided": true},
    {"step": "first_workflow", "guided": true},
    {"step": "test_run"}
  ],
  "skip_steps": ["project_setup", "welcome_tour"],
  "persona_prediction": "alice-builder"
}
"""

SAMPLE_METRICS_INSIGHTS_LLM_RESPONSE = """
{
  "insights": [
    {
      "type": "anomaly",
      "dimension": "retention",
      "message": "Unusual drop in D7 retention for new users",
      "severity": "warning",
      "sentiment": "negative",
      "suggested_actions": ["Review onboarding flow", "Check for UX issues"],
      "detected_at": "2025-12-20T10:00:00Z"
    },
    {
      "type": "trend",
      "dimension": "engagement",
      "message": "Session duration up 18% after AI features rollout",
      "severity": "info",
      "sentiment": "positive"
    }
  ],
  "predictions": [
    {
      "metric": "monthly_active_users",
      "current": 1250,
      "predicted": 1450,
      "confidence": 0.72,
      "drivers": ["improved_onboarding", "ai_features"]
    }
  ]
}
"""


# =============================================================================
# Service Import - Tests verify contract before implementation
# =============================================================================


# Note: reset_ai_circuit_breakers fixture is defined in conftest.py


@pytest.fixture
def mock_llm_factory():
    """Create mock LLM factory."""
    factory = MagicMock()
    factory.ainvoke = AsyncMock(return_value=AIMessage(content=SAMPLE_ERROR_LLM_RESPONSE))
    return factory


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = MagicMock()
    settings.ff_enable_ai_suggestions = True
    settings.llm_provider = "google"
    settings.model_name = "gemini-2.5-flash"
    return settings


# =============================================================================
# AIUXService Tests
# =============================================================================


class TestAIUXServiceInitialization:
    """Test AIUXService initialization."""

    @pytest.mark.asyncio
    async def test_service_creates_with_llm_factory(self, mock_llm_factory, mock_settings):
        """Service initializes with LLM factory when enabled."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        service = AIUXService(llm_factory=mock_llm_factory, settings=mock_settings)
        assert service.llm_factory is not None
        assert service.llm_enabled is True

    @pytest.mark.asyncio
    async def test_service_creates_without_llm_factory(self, mock_settings):
        """Service initializes without LLM factory (heuristics only)."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        service = AIUXService(llm_factory=None, settings=mock_settings)
        assert service.llm_factory is None
        assert service.llm_enabled is False

    @pytest.mark.asyncio
    async def test_service_respects_feature_flag(self, mock_llm_factory, mock_settings):
        """Service disables LLM when feature flag is off."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        mock_settings.ff_enable_ai_suggestions = False
        service = AIUXService(llm_factory=mock_llm_factory, settings=mock_settings)
        assert service.llm_enabled is False


class TestErrorAnalysisWithLLM:
    """Test LLM-enhanced error analysis."""

    @pytest.mark.asyncio
    async def test_error_analysis_calls_llm(self, mock_llm_factory, mock_settings):
        """Error analysis uses LLM when available."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService
        from mcp_server_langgraph.api.v1.ai_ux import ErrorAnalyzeRequest

        service = AIUXService(llm_factory=mock_llm_factory, settings=mock_settings)

        # ADR-0091 Phase 9: Use new ErrorAnalyzeRequest schema
        request = ErrorAnalyzeRequest(
            error_code="TimeoutError",
            error_message=SAMPLE_ERROR_MESSAGE,
            context={"persona": "bob", "session_id": "test-session"},
        )

        result = await service.analyze_error(request)

        # LLM should be called
        mock_llm_factory.ainvoke.assert_called_once()

        # Result should be parsed from LLM response (ADR-0091 aligned fields)
        assert result.error_type == "timeout"
        assert result.confidence >= 0.9

    @pytest.mark.asyncio
    async def test_error_analysis_includes_context_in_prompt(self, mock_llm_factory, mock_settings):
        """Error analysis prompt includes user context."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService
        from mcp_server_langgraph.api.v1.ai_ux import ErrorAnalyzeRequest

        service = AIUXService(llm_factory=mock_llm_factory, settings=mock_settings)

        # ADR-0091 Phase 9: Use new ErrorAnalyzeRequest schema
        request = ErrorAnalyzeRequest(
            error_code="AuthorizationError",
            error_message="Permission denied",
            stack_trace="at checkPermission(...)",
            context={"persona": "alice-builder", "recent_actions": ["created_workflow", "edited_node"]},
        )

        await service.analyze_error(request)

        # Check prompt includes context (across all messages)
        call_args = mock_llm_factory.ainvoke.call_args
        messages = call_args[0][0]  # First positional arg is messages
        # Combine all message contents for checking
        all_content = " ".join(m.content if hasattr(m, "content") else str(m) for m in messages)

        assert "Permission denied" in all_content
        assert "persona" in all_content or "alice-builder" in all_content

    @pytest.mark.asyncio
    async def test_error_analysis_falls_back_on_llm_error(self, mock_llm_factory, mock_settings):
        """Error analysis falls back to heuristics when LLM fails."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService
        from mcp_server_langgraph.api.v1.ai_ux import ErrorAnalyzeRequest

        mock_llm_factory.ainvoke.side_effect = Exception("LLM service unavailable")

        service = AIUXService(llm_factory=mock_llm_factory, settings=mock_settings)

        # ADR-0091 Phase 9: Use new ErrorAnalyzeRequest schema
        request = ErrorAnalyzeRequest(
            error_code="TimeoutError",
            error_message="Connection timeout",
        )

        # Should not raise, should fallback to heuristics
        result = await service.analyze_error(request)

        assert result is not None
        assert result.error_type == "timeout"

    @pytest.mark.asyncio
    async def test_error_analysis_uses_heuristics_when_llm_disabled(self, mock_llm_factory, mock_settings):
        """Error analysis uses heuristics when LLM is disabled."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService
        from mcp_server_langgraph.api.v1.ai_ux import ErrorAnalyzeRequest

        mock_settings.ff_enable_ai_suggestions = False
        service = AIUXService(llm_factory=mock_llm_factory, settings=mock_settings)

        # ADR-0091 Phase 9: Use new ErrorAnalyzeRequest schema
        request = ErrorAnalyzeRequest(
            error_code="AuthError",
            error_message="401 Unauthorized",
        )

        result = await service.analyze_error(request)

        # LLM should NOT be called
        mock_llm_factory.ainvoke.assert_not_called()

        # Result should come from heuristics (ADR-0091 aligned fields)
        assert result.error_type == "authentication"


class TestEmptyStateSuggestionsWithLLM:
    """Test LLM-enhanced empty state suggestions."""

    @pytest.mark.asyncio
    async def test_empty_state_calls_llm(self, mock_llm_factory, mock_settings):
        """Empty state uses LLM for personalized suggestions."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService
        from mcp_server_langgraph.api.v1.ai_ux import EmptyStateSuggestionsRequest

        mock_llm_factory.ainvoke.return_value = AIMessage(content=SAMPLE_EMPTY_STATE_LLM_RESPONSE)

        service = AIUXService(llm_factory=mock_llm_factory, settings=mock_settings)

        request = EmptyStateSuggestionsRequest(
            context="workflows",
            persona="alice-builder",
            session_id="test-session",
        )

        result = await service.get_empty_state_suggestions(request)

        # LLM should be called
        mock_llm_factory.ainvoke.assert_called_once()

        # Result should have suggestions
        assert len(result.suggestions) >= 1

    @pytest.mark.asyncio
    async def test_empty_state_falls_back_on_llm_error(self, mock_llm_factory, mock_settings):
        """Empty state falls back to heuristics when LLM fails."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService
        from mcp_server_langgraph.api.v1.ai_ux import EmptyStateSuggestionsRequest

        mock_llm_factory.ainvoke.side_effect = Exception("LLM error")

        service = AIUXService(llm_factory=mock_llm_factory, settings=mock_settings)

        request = EmptyStateSuggestionsRequest(
            context="workflows",
            persona="bob",
        )

        result = await service.get_empty_state_suggestions(request)

        # Should still return valid suggestions from heuristics
        assert result is not None
        assert len(result.suggestions) >= 1


class TestPersonaAnalysisWithLLM:
    """Test LLM-enhanced persona analysis."""

    @pytest.mark.asyncio
    async def test_persona_analysis_calls_llm(self, mock_llm_factory, mock_settings):
        """Persona analysis uses LLM for nuanced behavior detection."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService
        from mcp_server_langgraph.api.v1.ai_ux import PersonaAnalyzeRequest

        mock_llm_factory.ainvoke.return_value = AIMessage(content=SAMPLE_PERSONA_LLM_RESPONSE)

        service = AIUXService(llm_factory=mock_llm_factory, settings=mock_settings)

        request = PersonaAnalyzeRequest(
            user_id="user-123",
            assigned_persona="bob",
            recent_actions=["created_workflow", "viewed_traces", "edited_node"],
            feature_usage={"workflow_builder": 15, "traces": 8, "chat": 5},
        )

        result = await service.analyze_persona(request)

        # LLM should be called
        mock_llm_factory.ainvoke.assert_called_once()

        # Result should detect persona mismatch
        assert result.detected_persona != result.assigned_persona

    @pytest.mark.asyncio
    async def test_persona_analysis_returns_behavior_signals(self, mock_llm_factory, mock_settings):
        """Persona analysis includes behavior signals from LLM."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService
        from mcp_server_langgraph.api.v1.ai_ux import PersonaAnalyzeRequest

        mock_llm_factory.ainvoke.return_value = AIMessage(content=SAMPLE_PERSONA_LLM_RESPONSE)

        service = AIUXService(llm_factory=mock_llm_factory, settings=mock_settings)

        request = PersonaAnalyzeRequest(
            user_id="user-123",
            assigned_persona="bob",
            recent_actions=[],
            feature_usage={},
        )

        result = await service.analyze_persona(request)

        # Should have behavior signals
        assert len(result.behavior_signals) > 0


class TestLLMPromptConstruction:
    """Test prompt construction for LLM calls."""

    @pytest.mark.asyncio
    async def test_error_prompt_includes_system_message(self, mock_llm_factory, mock_settings):
        """Error analysis prompt includes system instructions."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService
        from mcp_server_langgraph.api.v1.ai_ux import ErrorAnalyzeRequest

        service = AIUXService(llm_factory=mock_llm_factory, settings=mock_settings)

        # ADR-0091 Phase 9: Use new ErrorAnalyzeRequest schema
        request = ErrorAnalyzeRequest(
            error_code="TestError",
            error_message="Test error",
        )
        await service.analyze_error(request)

        call_args = mock_llm_factory.ainvoke.call_args
        messages = call_args[0][0]

        # First message should be system message
        assert len(messages) >= 1
        first_msg = messages[0]
        assert hasattr(first_msg, "content") or isinstance(first_msg, dict)

    @pytest.mark.asyncio
    async def test_prompts_request_json_output(self, mock_llm_factory, mock_settings):
        """Prompts instruct LLM to return JSON format."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService
        from mcp_server_langgraph.api.v1.ai_ux import ErrorAnalyzeRequest

        service = AIUXService(llm_factory=mock_llm_factory, settings=mock_settings)

        # ADR-0091 Phase 9: Use new ErrorAnalyzeRequest schema
        request = ErrorAnalyzeRequest(
            error_code="Test",
            error_message="Test",
        )
        await service.analyze_error(request)

        call_args = mock_llm_factory.ainvoke.call_args
        messages = call_args[0][0]
        prompt_content = str(messages[0].content if hasattr(messages[0], "content") else messages[0])

        assert "json" in prompt_content.lower()


class TestResponseParsing:
    """Test LLM response parsing."""

    @pytest.mark.asyncio
    async def test_handles_malformed_json_response(self, mock_llm_factory, mock_settings):
        """Falls back to heuristics when LLM returns invalid JSON."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService
        from mcp_server_langgraph.api.v1.ai_ux import ErrorAnalyzeRequest

        mock_llm_factory.ainvoke.return_value = AIMessage(content="This is not valid JSON")

        service = AIUXService(llm_factory=mock_llm_factory, settings=mock_settings)

        # ADR-0091 Phase 9: Use new ErrorAnalyzeRequest schema
        request = ErrorAnalyzeRequest(
            error_code="TimeoutError",
            error_message="timeout error",
        )
        result = await service.analyze_error(request)

        # Should fallback to heuristics instead of crashing (ADR-0091 aligned fields)
        assert result is not None
        assert result.error_type is not None

    @pytest.mark.asyncio
    async def test_handles_json_with_markdown_wrapping(self, mock_llm_factory, mock_settings):
        """Parses JSON even when wrapped in markdown code blocks."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService
        from mcp_server_langgraph.api.v1.ai_ux import ErrorAnalyzeRequest

        wrapped_response = f"```json\n{SAMPLE_ERROR_LLM_RESPONSE}\n```"
        mock_llm_factory.ainvoke.return_value = AIMessage(content=wrapped_response)

        service = AIUXService(llm_factory=mock_llm_factory, settings=mock_settings)

        # ADR-0091 Phase 9: Use new ErrorAnalyzeRequest schema
        request = ErrorAnalyzeRequest(
            error_code="TimeoutError",
            error_message="timeout",
        )
        result = await service.analyze_error(request)

        # Should parse successfully (ADR-0091 aligned fields)
        assert result.error_type == "timeout"


class TestTelemetryIntegration:
    """Test telemetry and logging."""

    @pytest.mark.asyncio
    async def test_logs_llm_call_success(self, mock_llm_factory, mock_settings):
        """Logs successful LLM calls."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService
        from mcp_server_langgraph.api.v1.ai_ux import ErrorAnalyzeRequest

        with patch("mcp_server_langgraph.api.v1.ai_ux_service.logger") as mock_logger:
            service = AIUXService(llm_factory=mock_llm_factory, settings=mock_settings)

            # ADR-0091 Phase 9: Use new ErrorAnalyzeRequest schema
            request = ErrorAnalyzeRequest(
                error_code="Test",
                error_message="test",
            )
            await service.analyze_error(request)

            # Should log LLM usage
            assert mock_logger.debug.called or mock_logger.info.called

    @pytest.mark.asyncio
    async def test_logs_llm_fallback(self, mock_llm_factory, mock_settings):
        """Logs when falling back to heuristics."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService
        from mcp_server_langgraph.api.v1.ai_ux import ErrorAnalyzeRequest

        mock_llm_factory.ainvoke.side_effect = Exception("LLM error")

        with patch("mcp_server_langgraph.api.v1.ai_ux_service.logger") as mock_logger:
            service = AIUXService(llm_factory=mock_llm_factory, settings=mock_settings)

            # ADR-0091 Phase 9: Use new ErrorAnalyzeRequest schema
            request = ErrorAnalyzeRequest(
                error_code="TimeoutError",
                error_message="timeout",
            )
            await service.analyze_error(request)

            # Should log fallback warning
            assert mock_logger.warning.called or mock_logger.error.called


# =============================================================================
# Disclosure Analysis with LLM Tests
# =============================================================================


class TestDisclosureAnalysisWithLLM:
    """Test LLM-enhanced disclosure analysis."""

    @pytest.mark.asyncio
    async def test_disclosure_calls_llm(self, mock_llm_factory, mock_settings):
        """Disclosure analysis uses LLM when available."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService
        from mcp_server_langgraph.api.v1.ai_ux import DisclosureAnalyzeRequest

        mock_llm_factory.ainvoke.return_value = AIMessage(content=SAMPLE_DISCLOSURE_LLM_RESPONSE)

        service = AIUXService(llm_factory=mock_llm_factory, settings=mock_settings)

        # ADR-0091 Phase 9: Use aligned DisclosureAnalyzeRequest schema
        request = DisclosureAnalyzeRequest(
            current_level="beginner",
            persona="bob",
        )

        result = await service.analyze_disclosure(request)

        # LLM should be called
        mock_llm_factory.ainvoke.assert_called_once()

        # Result should be parsed from LLM response (recommended_level is a string, not enum)
        assert result.recommended_level == "advanced"
        assert result.confidence >= 0.8

    @pytest.mark.asyncio
    async def test_disclosure_includes_feature_usage_in_prompt(self, mock_llm_factory, mock_settings):
        """Disclosure prompt includes feature usage data."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService
        from mcp_server_langgraph.api.v1.ai_ux import (
            DisclosureAnalyzeRequest,
            UserBehavior,
        )

        mock_llm_factory.ainvoke.return_value = AIMessage(content=SAMPLE_DISCLOSURE_LLM_RESPONSE)

        service = AIUXService(llm_factory=mock_llm_factory, settings=mock_settings)

        # ADR-0091 Phase 9: Use aligned DisclosureAnalyzeRequest schema
        request = DisclosureAnalyzeRequest(
            current_level="intermediate",
            persona="alice-builder",
            user_behavior=UserBehavior(
                feature_usage={"workflow_builder": 100, "mcp": 50},
                session_count=15,
            ),
        )

        await service.analyze_disclosure(request)

        call_args = mock_llm_factory.ainvoke.call_args
        messages = call_args[0][0]
        all_content = " ".join(m.content if hasattr(m, "content") else str(m) for m in messages)

        assert "workflow_builder" in all_content or "mcp" in all_content

    @pytest.mark.asyncio
    async def test_disclosure_falls_back_on_llm_error(self, mock_llm_factory, mock_settings):
        """Disclosure falls back to heuristics when LLM fails."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService
        from mcp_server_langgraph.api.v1.ai_ux import DisclosureAnalyzeRequest

        mock_llm_factory.ainvoke.side_effect = Exception("LLM unavailable")

        service = AIUXService(llm_factory=mock_llm_factory, settings=mock_settings)

        # ADR-0091 Phase 9: Use aligned DisclosureAnalyzeRequest schema
        request = DisclosureAnalyzeRequest(
            current_level="beginner",
        )

        result = await service.analyze_disclosure(request)

        # Should still return valid response from heuristics
        assert result is not None
        assert result.current_level is not None
        assert result.recommended_level is not None


# =============================================================================
# Nudge Recommendations with LLM Tests
# =============================================================================


class TestNudgeRecommendationsWithLLM:
    """Test LLM-enhanced nudge recommendations."""

    @pytest.mark.asyncio
    async def test_nudge_calls_llm(self, mock_llm_factory, mock_settings):
        """Nudge recommendation uses LLM when available."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService
        from mcp_server_langgraph.api.v1.ai_ux import (
            NudgeRecommendRequest,
            NudgeContext,
        )

        mock_llm_factory.ainvoke.return_value = AIMessage(content=SAMPLE_NUDGE_LLM_RESPONSE)

        service = AIUXService(llm_factory=mock_llm_factory, settings=mock_settings)

        request = NudgeRecommendRequest(
            user_id="user-123",
            current_context=NudgeContext(
                page="/workflows",
                action="editing",
                time_on_page=45000,
            ),
            nudge_history=[],
        )

        result = await service.recommend_nudge(request)

        # LLM should be called
        mock_llm_factory.ainvoke.assert_called_once()

        # Result should include nudge from LLM
        assert result.should_show is True
        assert result.nudge is not None

    @pytest.mark.asyncio
    async def test_nudge_considers_history_in_prompt(self, mock_llm_factory, mock_settings):
        """Nudge prompt includes dismissal history."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService
        from mcp_server_langgraph.api.v1.ai_ux import (
            NudgeRecommendRequest,
            NudgeContext,
            NudgeHistoryItem,
        )

        mock_llm_factory.ainvoke.return_value = AIMessage(content=SAMPLE_NUDGE_LLM_RESPONSE)

        service = AIUXService(llm_factory=mock_llm_factory, settings=mock_settings)

        request = NudgeRecommendRequest(
            user_id="user-456",
            current_context=NudgeContext(page="/chat", time_on_page=60000),
            nudge_history=[
                # ADR-0091 Phase 9: Use nudge_id (not id) per aligned schema
                NudgeHistoryItem(
                    nudge_id="keyboard-shortcuts",
                    shown_at="2025-12-20T09:00:00Z",
                    action="dismissed",
                ),
            ],
        )

        await service.recommend_nudge(request)

        call_args = mock_llm_factory.ainvoke.call_args
        messages = call_args[0][0]
        all_content = " ".join(m.content if hasattr(m, "content") else str(m) for m in messages)

        # Should mention nudge history
        assert "keyboard-shortcuts" in all_content or "dismissed" in all_content

    @pytest.mark.asyncio
    async def test_nudge_falls_back_on_llm_error(self, mock_llm_factory, mock_settings):
        """Nudge falls back to heuristics when LLM fails."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService
        from mcp_server_langgraph.api.v1.ai_ux import (
            NudgeRecommendRequest,
            NudgeContext,
        )

        mock_llm_factory.ainvoke.side_effect = Exception("LLM timeout")

        service = AIUXService(llm_factory=mock_llm_factory, settings=mock_settings)

        request = NudgeRecommendRequest(
            user_id="user-789",
            current_context=NudgeContext(page="/chat", time_on_page=30000),
            nudge_history=[],
        )

        result = await service.recommend_nudge(request)

        # Should still return valid response
        assert result is not None
        assert isinstance(result.should_show, bool)


# =============================================================================
# Onboarding Personalization with LLM Tests
# =============================================================================


class TestOnboardingPersonalizationWithLLM:
    """Test LLM-enhanced onboarding personalization."""

    @pytest.mark.asyncio
    async def test_onboarding_calls_llm(self, mock_llm_factory, mock_settings):
        """Onboarding personalization uses LLM when available."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService
        from mcp_server_langgraph.api.v1.ai_ux import (
            OnboardingPersonalizeRequest,
            SignupContext,
        )

        mock_llm_factory.ainvoke.return_value = AIMessage(content=SAMPLE_ONBOARDING_LLM_RESPONSE)

        service = AIUXService(llm_factory=mock_llm_factory, settings=mock_settings)

        request = OnboardingPersonalizeRequest(
            user_id="new-user",
            initial_actions=["viewed_templates", "clicked_automation"],
            signup_context=SignupContext(referrer="github.com", utm_source="docs"),
        )

        result = await service.personalize_onboarding(request)

        # LLM should be called
        mock_llm_factory.ainvoke.assert_called_once()

        # Result should be parsed from LLM
        assert result.detected_intent == "build_automation"
        assert result.confidence >= 0.9

    @pytest.mark.asyncio
    async def test_onboarding_includes_actions_in_prompt(self, mock_llm_factory, mock_settings):
        """Onboarding prompt includes user's initial actions."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService
        from mcp_server_langgraph.api.v1.ai_ux import OnboardingPersonalizeRequest

        mock_llm_factory.ainvoke.return_value = AIMessage(content=SAMPLE_ONBOARDING_LLM_RESPONSE)

        service = AIUXService(llm_factory=mock_llm_factory, settings=mock_settings)

        request = OnboardingPersonalizeRequest(
            user_id="new-user-2",
            initial_actions=["explored_workflows", "viewed_traces"],
        )

        await service.personalize_onboarding(request)

        call_args = mock_llm_factory.ainvoke.call_args
        messages = call_args[0][0]
        all_content = " ".join(m.content if hasattr(m, "content") else str(m) for m in messages)

        assert "explored_workflows" in all_content or "viewed_traces" in all_content

    @pytest.mark.asyncio
    async def test_onboarding_falls_back_on_llm_error(self, mock_llm_factory, mock_settings):
        """Onboarding falls back to heuristics when LLM fails."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService
        from mcp_server_langgraph.api.v1.ai_ux import OnboardingPersonalizeRequest

        mock_llm_factory.ainvoke.side_effect = Exception("LLM quota exceeded")

        service = AIUXService(llm_factory=mock_llm_factory, settings=mock_settings)

        request = OnboardingPersonalizeRequest(
            user_id="new-user-3",
            initial_actions=["clicked_chat"],
        )

        result = await service.personalize_onboarding(request)

        # Should still return valid response
        assert result is not None
        assert result.detected_intent is not None
        assert len(result.recommended_path) > 0


# =============================================================================
# Metrics Insights with LLM Tests
# =============================================================================


class TestMetricsInsightsWithLLM:
    """Test LLM-enhanced HEART metrics insights."""

    @pytest.mark.asyncio
    async def test_metrics_insights_calls_llm(self, mock_llm_factory, mock_settings):
        """Metrics insights uses LLM when available."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        mock_llm_factory.ainvoke.return_value = AIMessage(content=SAMPLE_METRICS_INSIGHTS_LLM_RESPONSE)

        service = AIUXService(llm_factory=mock_llm_factory, settings=mock_settings)

        result = await service.get_metrics_insights()

        # LLM should be called
        mock_llm_factory.ainvoke.assert_called_once()

        # Result should have insights from LLM (ADR-0091 Phase 9: uses category enum)
        assert len(result.insights) >= 1
        # MetricInsight uses category (MetricsInsightCategory enum), not type
        assert any(
            i.category.value in ("happiness", "engagement", "adoption", "retention", "task_success") for i in result.insights
        )

    @pytest.mark.asyncio
    async def test_metrics_insights_includes_health_and_recommendations(self, mock_llm_factory, mock_settings):
        """Metrics insights includes overall health and recommendations (ADR-0091 Phase 9 aligned)."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        mock_llm_factory.ainvoke.return_value = AIMessage(content=SAMPLE_METRICS_INSIGHTS_LLM_RESPONSE)

        service = AIUXService(llm_factory=mock_llm_factory, settings=mock_settings)

        result = await service.get_metrics_insights()

        # ADR-0091 Phase 9: New schema has happiness_score, overall_health, recommendations
        # (predictions field removed in aligned schema)
        assert result.happiness_score >= 0
        assert result.overall_health is not None
        assert result.overall_health.value in ("excellent", "good", "needs_attention", "critical")

    @pytest.mark.asyncio
    async def test_metrics_insights_falls_back_on_llm_error(self, mock_llm_factory, mock_settings):
        """Metrics insights falls back to heuristics when LLM fails."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        mock_llm_factory.ainvoke.side_effect = Exception("LLM service down")

        service = AIUXService(llm_factory=mock_llm_factory, settings=mock_settings)

        result = await service.get_metrics_insights()

        # Should still return valid response
        assert result is not None
        assert len(result.insights) >= 1


# =============================================================================
# Observability Metrics Tests
# =============================================================================


@pytest.fixture
def reset_metrics():
    """Reset Prometheus metrics before each test."""
    from mcp_server_langgraph.api.v1.ai_ux_service import (
        ai_ux_llm_calls_total,
        ai_ux_llm_fallbacks_total,
        ai_ux_llm_latency_seconds,
    )

    # Reset counters - Prometheus counters can't be reset in tests easily
    # so we just get the current values and verify increments
    return {
        "calls": ai_ux_llm_calls_total,
        "fallbacks": ai_ux_llm_fallbacks_total,
        "latency": ai_ux_llm_latency_seconds,
    }


class TestAIUXServiceObservabilityMetrics:
    """Test observability metrics for AI UX service."""

    @pytest.mark.asyncio
    async def test_llm_call_increments_counter(self, mock_llm_factory, mock_settings):
        """LLM calls increment the calls counter."""
        from mcp_server_langgraph.api.v1.ai_ux_service import (
            AIUXService,
            ai_ux_llm_calls_total,
        )
        from mcp_server_langgraph.api.v1.ai_ux import ErrorAnalyzeRequest

        mock_llm_factory.ainvoke.return_value = AIMessage(content=SAMPLE_ERROR_LLM_RESPONSE)

        # Get initial value
        initial = ai_ux_llm_calls_total.labels(method="error_analysis")._value.get()

        service = AIUXService(llm_factory=mock_llm_factory, settings=mock_settings)

        # ADR-0091 Phase 9: Use new ErrorAnalyzeRequest schema
        request = ErrorAnalyzeRequest(
            error_code="Error",
            error_message="timeout error",
        )
        await service.analyze_error(request)

        # Counter should increment
        after = ai_ux_llm_calls_total.labels(method="error_analysis")._value.get()
        assert after > initial

    @pytest.mark.asyncio
    async def test_fallback_increments_fallback_counter(self, mock_llm_factory, mock_settings):
        """Fallback to heuristics increments the fallback counter."""
        from mcp_server_langgraph.api.v1.ai_ux_service import (
            AIUXService,
            ai_ux_llm_fallbacks_total,
        )
        from mcp_server_langgraph.api.v1.ai_ux import ErrorAnalyzeRequest

        mock_llm_factory.ainvoke.side_effect = Exception("LLM failed")

        # Get initial value
        initial = ai_ux_llm_fallbacks_total.labels(method="error_analysis")._value.get()

        service = AIUXService(llm_factory=mock_llm_factory, settings=mock_settings)

        # ADR-0091 Phase 9: Use new ErrorAnalyzeRequest schema
        request = ErrorAnalyzeRequest(
            error_code="Error",
            error_message="timeout error",
        )
        await service.analyze_error(request)

        # Fallback counter should increment
        after = ai_ux_llm_fallbacks_total.labels(method="error_analysis")._value.get()
        assert after > initial

    @pytest.mark.asyncio
    async def test_llm_call_records_latency(self, mock_llm_factory, mock_settings):
        """LLM calls record latency in histogram."""
        from mcp_server_langgraph.api.v1.ai_ux_service import (
            AIUXService,
            ai_ux_llm_latency_seconds,
        )
        from mcp_server_langgraph.api.v1.ai_ux import ErrorAnalyzeRequest

        mock_llm_factory.ainvoke.return_value = AIMessage(content=SAMPLE_ERROR_LLM_RESPONSE)

        # Get initial sum from histogram
        labeled_histogram = ai_ux_llm_latency_seconds.labels(method="error_analysis")
        # Access the _sum value from the underlying Child object
        initial_sum = labeled_histogram._sum.get()

        service = AIUXService(llm_factory=mock_llm_factory, settings=mock_settings)

        # ADR-0091 Phase 9: Use new ErrorAnalyzeRequest schema
        request = ErrorAnalyzeRequest(
            error_code="Error",
            error_message="timeout error",
        )
        await service.analyze_error(request)

        # Histogram sum should increase (indicating an observation was made)
        after_sum = labeled_histogram._sum.get()
        assert after_sum > initial_sum

    @pytest.mark.asyncio
    async def test_all_endpoints_track_metrics(self, mock_llm_factory, mock_settings):
        """All AI UX endpoints track metrics."""
        from mcp_server_langgraph.api.v1.ai_ux_service import (
            AIUXService,
            ai_ux_llm_calls_total,
        )
        from mcp_server_langgraph.api.v1.ai_ux import (
            DisclosureAnalyzeRequest,
            EmptyStateSuggestionsRequest,
            NudgeRecommendRequest,
            NudgeContext,
            OnboardingPersonalizeRequest,
            PersonaAnalyzeRequest,
            ErrorAnalyzeRequest,
        )

        # Setup mocks for all responses
        mock_llm_factory.ainvoke.side_effect = [
            AIMessage(content=SAMPLE_ERROR_LLM_RESPONSE),
            AIMessage(content=SAMPLE_EMPTY_STATE_LLM_RESPONSE),
            AIMessage(content=SAMPLE_PERSONA_LLM_RESPONSE),
            AIMessage(content=SAMPLE_DISCLOSURE_LLM_RESPONSE),
            AIMessage(content=SAMPLE_NUDGE_LLM_RESPONSE),
            AIMessage(content=SAMPLE_ONBOARDING_LLM_RESPONSE),
            AIMessage(content=SAMPLE_METRICS_INSIGHTS_LLM_RESPONSE),
        ]

        service = AIUXService(llm_factory=mock_llm_factory, settings=mock_settings)

        # Call each endpoint
        methods = [
            "error_analysis",
            "empty_state",
            "persona_analysis",
            "disclosure_analysis",
            "nudge_recommendation",
            "onboarding_personalization",
            "metrics_insights",
        ]

        # ADR-0091 Phase 9: Use new ErrorAnalyzeRequest schema
        await service.analyze_error(ErrorAnalyzeRequest(error_code="E", error_message="test"))
        await service.get_empty_state_suggestions(EmptyStateSuggestionsRequest(context="workflows", persona="bob"))
        await service.analyze_persona(PersonaAnalyzeRequest(user_id="u1", assigned_persona="bob"))
        await service.analyze_disclosure(DisclosureAnalyzeRequest(current_level="beginner"))
        await service.recommend_nudge(
            NudgeRecommendRequest(
                user_id="u1",
                current_context=NudgeContext(page="/chat", action="viewing"),
            )
        )
        await service.personalize_onboarding(OnboardingPersonalizeRequest(user_id="u1", initial_actions=["chat"]))
        await service.get_metrics_insights()

        # All methods should have incremented counters
        for method in methods:
            counter = ai_ux_llm_calls_total.labels(method=method)._value.get()
            assert counter >= 1, f"Counter for {method} should be >= 1"

    @pytest.mark.asyncio
    async def test_heuristic_mode_does_not_increment_llm_counter(self, mock_settings):
        """Heuristic-only mode does not increment LLM counters."""
        from mcp_server_langgraph.api.v1.ai_ux_service import (
            AIUXService,
            ai_ux_llm_calls_total,
        )
        from mcp_server_langgraph.api.v1.ai_ux import ErrorAnalyzeRequest

        # Get initial value
        initial = ai_ux_llm_calls_total.labels(method="error_analysis")._value.get()

        # No LLM factory = heuristics only
        service = AIUXService(llm_factory=None, settings=mock_settings)

        # ADR-0091 Phase 9: Use new ErrorAnalyzeRequest schema
        request = ErrorAnalyzeRequest(
            error_code="Error",
            error_message="timeout error",
        )
        await service.analyze_error(request)

        # Counter should NOT increment
        after = ai_ux_llm_calls_total.labels(method="error_analysis")._value.get()
        assert after == initial


# =============================================================================
# Response Caching Tests
# =============================================================================


class TestAIUXServiceResponseCaching:
    """Test response caching for AI UX service."""

    @pytest.mark.asyncio
    async def test_identical_requests_use_cache(self, mock_llm_factory, mock_settings):
        """Identical requests should return cached response without calling LLM again."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService
        from mcp_server_langgraph.api.v1.ai_ux import EmptyStateSuggestionsRequest

        mock_llm_factory.ainvoke.return_value = AIMessage(content=SAMPLE_EMPTY_STATE_LLM_RESPONSE)

        service = AIUXService(llm_factory=mock_llm_factory, settings=mock_settings)

        # First request - should call LLM
        request = EmptyStateSuggestionsRequest(
            context="workflows",
            persona="alice-builder",
        )
        result1 = await service.get_empty_state_suggestions(request)

        # Second identical request - should use cache
        result2 = await service.get_empty_state_suggestions(request)

        # LLM should only be called once
        assert mock_llm_factory.ainvoke.call_count == 1
        # Both results should be the same
        assert result1 == result2

    @pytest.mark.asyncio
    async def test_different_requests_call_llm(self, mock_llm_factory, mock_settings):
        """Different requests should call LLM separately."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService
        from mcp_server_langgraph.api.v1.ai_ux import EmptyStateSuggestionsRequest

        mock_llm_factory.ainvoke.return_value = AIMessage(content=SAMPLE_EMPTY_STATE_LLM_RESPONSE)

        service = AIUXService(llm_factory=mock_llm_factory, settings=mock_settings)

        # First request
        request1 = EmptyStateSuggestionsRequest(
            context="workflows",
            persona="alice-builder",
        )
        await service.get_empty_state_suggestions(request1)

        # Different request
        request2 = EmptyStateSuggestionsRequest(
            context="sessions",
            persona="bob",
        )
        await service.get_empty_state_suggestions(request2)

        # LLM should be called twice
        assert mock_llm_factory.ainvoke.call_count == 2

    @pytest.mark.asyncio
    async def test_cache_hit_increments_metric(self, mock_llm_factory, mock_settings):
        """Cache hits should increment the cache hit metric."""
        from mcp_server_langgraph.api.v1.ai_ux_service import (
            AIUXService,
            ai_ux_cache_hits_total,
        )
        from mcp_server_langgraph.api.v1.ai_ux import EmptyStateSuggestionsRequest

        mock_llm_factory.ainvoke.return_value = AIMessage(content=SAMPLE_EMPTY_STATE_LLM_RESPONSE)

        # Get initial value
        initial = ai_ux_cache_hits_total.labels(method="empty_state")._value.get()

        service = AIUXService(llm_factory=mock_llm_factory, settings=mock_settings)

        request = EmptyStateSuggestionsRequest(
            context="workflows",
            persona="alice-builder",
        )
        await service.get_empty_state_suggestions(request)
        await service.get_empty_state_suggestions(request)  # Cache hit

        # Cache hit counter should increment
        after = ai_ux_cache_hits_total.labels(method="empty_state")._value.get()
        assert after > initial

    @pytest.mark.asyncio
    async def test_persona_analysis_caching(self, mock_llm_factory, mock_settings):
        """Persona analysis should use caching."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService
        from mcp_server_langgraph.api.v1.ai_ux import PersonaAnalyzeRequest

        mock_llm_factory.ainvoke.return_value = AIMessage(content=SAMPLE_PERSONA_LLM_RESPONSE)

        service = AIUXService(llm_factory=mock_llm_factory, settings=mock_settings)

        request = PersonaAnalyzeRequest(
            user_id="user-123",
            assigned_persona="bob",
            recent_actions=["clicked_workflows"],
            feature_usage={"chat": 10},
        )

        # Call twice with identical request
        await service.analyze_persona(request)
        await service.analyze_persona(request)

        # LLM should only be called once
        assert mock_llm_factory.ainvoke.call_count == 1
