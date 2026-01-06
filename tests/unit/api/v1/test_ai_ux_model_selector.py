"""
AI UX ModelSelector Integration Tests

TDD tests for ModelSelector integration with AIUXService.

Tests verify:
- ModelSelector is properly integrated into AIUXService
- Service uses appropriate model tier based on complexity
- Fallback to default model when ModelSelector unavailable
- SERVICE_COMPLEXITY mapping is used correctly

Reference: UX Audit Plan - Integration Opportunities
"""

import gc
import pytest
from unittest.mock import AsyncMock, MagicMock

from langchain_core.messages import AIMessage

pytestmark = pytest.mark.unit

# =============================================================================
# Test Constants
# =============================================================================

# Service complexity mapping - should match implementation
EXPECTED_SERVICE_COMPLEXITY = {
    "error_analysis": "simple",
    "empty_state": "simple",
    "nudge_recommendation": "simple",
    "disclosure_analysis": "complicated",
    "persona_analysis": "complicated",
    "onboarding_personalization": "complicated",
    "metrics_insights": "complex",
}

SAMPLE_ERROR_LLM_RESPONSE = """
{
  "category": "timeout",
  "subcategory": "request_timeout",
  "confidence": 0.95,
  "root_cause": "Server timeout",
  "suggestions": [{"action": "retry", "label": "Try again", "estimated_success": 0.8}]
}
"""

SAMPLE_DISCLOSURE_LLM_RESPONSE = """
{
  "current_level": "intermediate",
  "recommended_level": "advanced",
  "confidence": 0.88,
  "unlock_features": ["workflow_builder"],
  "personalized_message": "Ready for advanced mode!"
}
"""

SAMPLE_METRICS_LLM_RESPONSE = """
{
  "insights": [{"type": "trend", "dimension": "engagement", "message": "Up 10%", "severity": "info", "sentiment": "positive"}],
  "predictions": []
}
"""


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_model_selector():
    """Create mock ModelSelector."""
    selector = MagicMock()
    selector.select_model = MagicMock(
        side_effect=lambda complexity: {
            "simple": "gemini-flash",
            "complicated": "gemini-2.5-flash",
            "complex": "gemini-pro",
        }.get(complexity, "gemini-flash")
    )
    return selector


@pytest.fixture
def mock_llm_factory():
    """Create mock LLM factory that tracks model selection."""
    factory = MagicMock()
    factory.ainvoke = AsyncMock(return_value=AIMessage(content=SAMPLE_ERROR_LLM_RESPONSE))
    factory.get_model = MagicMock(return_value=MagicMock())
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
# ModelSelector Integration Tests
# =============================================================================


@pytest.mark.xdist_group(name="ai_ux_model_selector")
class TestAIUXServiceModelSelectorIntegration:
    """Test ModelSelector integration with AIUXService."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_service_accepts_model_selector(self, mock_llm_factory, mock_settings, mock_model_selector):
        """Service can be initialized with optional ModelSelector."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        service = AIUXService(
            llm_factory=mock_llm_factory,
            settings=mock_settings,
            model_selector=mock_model_selector,
        )
        assert service.model_selector is mock_model_selector

    @pytest.mark.asyncio
    async def test_service_works_without_model_selector(self, mock_llm_factory, mock_settings):
        """Service works without ModelSelector (backward compatible)."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        service = AIUXService(
            llm_factory=mock_llm_factory,
            settings=mock_settings,
        )
        assert service.model_selector is None

    @pytest.mark.asyncio
    async def test_service_has_complexity_mapping(self, mock_llm_factory, mock_settings):
        """Service defines SERVICE_COMPLEXITY mapping."""
        from mcp_server_langgraph.api.v1.ai_ux_service import SERVICE_COMPLEXITY

        # Verify expected services are mapped
        assert "error_analysis" in SERVICE_COMPLEXITY
        assert "metrics_insights" in SERVICE_COMPLEXITY

        # Verify expected complexity tiers
        assert SERVICE_COMPLEXITY["error_analysis"] == "simple"
        assert SERVICE_COMPLEXITY["metrics_insights"] == "complex"


@pytest.mark.xdist_group(name="ai_ux_model_selector")
class TestModelSelectionByService:
    """Test that each service uses appropriate model tier."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_error_analysis_uses_simple_tier(self, mock_llm_factory, mock_settings, mock_model_selector):
        """Error analysis uses simple tier (fast pattern matching).

        ADR-0091 Phase 9: Uses aligned ErrorAnalyzeRequest schema.
        """
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService
        from mcp_server_langgraph.api.v1.ai_ux import ErrorAnalyzeRequest

        mock_llm_factory.ainvoke = AsyncMock(return_value=AIMessage(content=SAMPLE_ERROR_LLM_RESPONSE))

        service = AIUXService(
            llm_factory=mock_llm_factory,
            settings=mock_settings,
            model_selector=mock_model_selector,
        )

        request = ErrorAnalyzeRequest(
            error_code="TimeoutError",
            error_message="Request timed out",
            context={"persona": "bob"},
        )

        await service.analyze_error(request)

        # Verify ModelSelector was called with simple complexity
        mock_model_selector.select_model.assert_called_with("simple")

    @pytest.mark.asyncio
    async def test_disclosure_analysis_uses_complicated_tier(self, mock_llm_factory, mock_settings, mock_model_selector):
        """Disclosure analysis uses complicated tier (behavior analysis).

        ADR-0091 Phase 9: Uses aligned DisclosureAnalyzeRequest schema.
        """
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService
        from mcp_server_langgraph.api.v1.ai_ux import DisclosureAnalyzeRequest, UserBehavior

        mock_llm_factory.ainvoke = AsyncMock(return_value=AIMessage(content=SAMPLE_DISCLOSURE_LLM_RESPONSE))

        service = AIUXService(
            llm_factory=mock_llm_factory,
            settings=mock_settings,
            model_selector=mock_model_selector,
        )

        request = DisclosureAnalyzeRequest(
            current_level="intermediate",
            persona="alice-builder",
            user_behavior=UserBehavior(
                feature_usage={"workflow_builder": 5},
                session_count=10,
            ),
        )

        await service.analyze_disclosure(request)

        # Verify ModelSelector was called with complicated complexity
        mock_model_selector.select_model.assert_called_with("complicated")

    @pytest.mark.asyncio
    async def test_metrics_insights_uses_complex_tier(self, mock_llm_factory, mock_settings, mock_model_selector):
        """Metrics insights uses complex tier (anomaly detection)."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        mock_llm_factory.ainvoke = AsyncMock(return_value=AIMessage(content=SAMPLE_METRICS_LLM_RESPONSE))

        service = AIUXService(
            llm_factory=mock_llm_factory,
            settings=mock_settings,
            model_selector=mock_model_selector,
        )

        # get_metrics_insights takes no parameters
        await service.get_metrics_insights()

        # Verify ModelSelector was called with complex complexity
        mock_model_selector.select_model.assert_called_with("complex")


@pytest.mark.xdist_group(name="ai_ux_model_selector")
class TestModelSelectionFallback:
    """Test fallback behavior when ModelSelector unavailable."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_uses_default_model_without_selector(self, mock_llm_factory, mock_settings):
        """Service uses default model when ModelSelector not provided.

        ADR-0091 Phase 9: Uses aligned ErrorAnalyzeRequest schema.
        """
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService
        from mcp_server_langgraph.api.v1.ai_ux import ErrorAnalyzeRequest

        mock_llm_factory.ainvoke = AsyncMock(return_value=AIMessage(content=SAMPLE_ERROR_LLM_RESPONSE))

        service = AIUXService(
            llm_factory=mock_llm_factory,
            settings=mock_settings,
            # No model_selector provided
        )

        request = ErrorAnalyzeRequest(
            error_code="Error",
            error_message="Test error",
        )
        await service.analyze_error(request)

        # LLM should still be called (using default factory)
        mock_llm_factory.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_model_selector_exception(self, mock_llm_factory, mock_settings, mock_model_selector):
        """Service gracefully handles ModelSelector exceptions.

        ADR-0091 Phase 9: Uses aligned ErrorAnalyzeRequest schema.
        """
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService
        from mcp_server_langgraph.api.v1.ai_ux import ErrorAnalyzeRequest

        # Make selector raise exception
        mock_model_selector.select_model.side_effect = Exception("Model selection failed")
        mock_llm_factory.ainvoke = AsyncMock(return_value=AIMessage(content=SAMPLE_ERROR_LLM_RESPONSE))

        service = AIUXService(
            llm_factory=mock_llm_factory,
            settings=mock_settings,
            model_selector=mock_model_selector,
        )

        request = ErrorAnalyzeRequest(
            error_code="Error",
            error_message="Test error",
        )
        # Should not raise, falls back to default model
        result = await service.analyze_error(request)

        # Result should be returned (either from LLM or heuristics)
        assert result is not None


@pytest.mark.xdist_group(name="ai_ux_model_selector")
class TestServiceComplexityMapping:
    """Test SERVICE_COMPLEXITY constant is defined correctly."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_all_services_have_complexity_mapping(self):
        """All AI UX services have complexity mappings."""
        from mcp_server_langgraph.api.v1.ai_ux_service import SERVICE_COMPLEXITY

        expected_services = [
            "error_analysis",
            "empty_state",
            "nudge_recommendation",
            "disclosure_analysis",
            "persona_analysis",
            "onboarding_personalization",
            "metrics_insights",
        ]

        for service in expected_services:
            assert service in SERVICE_COMPLEXITY, f"Missing complexity for {service}"

    def test_complexity_values_are_valid_tiers(self):
        """All complexity values are valid model tiers."""
        from mcp_server_langgraph.api.v1.ai_ux_service import SERVICE_COMPLEXITY

        valid_tiers = {"simple", "complicated", "complex"}

        for service, tier in SERVICE_COMPLEXITY.items():
            assert tier in valid_tiers, f"Invalid tier '{tier}' for {service}"

    def test_simple_services_are_fast_operations(self):
        """Simple tier services are fast pattern-matching operations."""
        from mcp_server_langgraph.api.v1.ai_ux_service import SERVICE_COMPLEXITY

        simple_services = ["error_analysis", "empty_state", "nudge_recommendation"]

        for service in simple_services:
            assert SERVICE_COMPLEXITY[service] == "simple", f"Expected {service} to use simple tier"

    def test_complicated_services_require_reasoning(self):
        """Complicated tier services require multi-step reasoning."""
        from mcp_server_langgraph.api.v1.ai_ux_service import SERVICE_COMPLEXITY

        complicated_services = ["disclosure_analysis", "persona_analysis", "onboarding_personalization"]

        for service in complicated_services:
            assert SERVICE_COMPLEXITY[service] == "complicated", f"Expected {service} to use complicated tier"

    def test_complex_services_require_deep_analysis(self):
        """Complex tier services require deep analysis."""
        from mcp_server_langgraph.api.v1.ai_ux_service import SERVICE_COMPLEXITY

        complex_services = ["metrics_insights"]

        for service in complex_services:
            assert SERVICE_COMPLEXITY[service] == "complex", f"Expected {service} to use complex tier"
