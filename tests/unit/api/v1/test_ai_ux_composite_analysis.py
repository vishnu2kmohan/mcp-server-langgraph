"""
AI UX Composite Analysis Tests

TDD tests for the composite analysis endpoint that orchestrates
multiple AI UX analyses in parallel and provides unified insights.

Tests verify:
- Composite analysis runs persona, disclosure, and error analyses
- Results are aggregated into a unified response
- Cross-service context enables intelligent recommendations
- Partial failures don't block overall response
- Session context is stored for future use

Reference: UX Audit Plan - Orchestrator Pattern Integration
"""

import gc
import pytest
from unittest.mock import AsyncMock, MagicMock

from langchain_core.messages import AIMessage

pytestmark = pytest.mark.unit

# =============================================================================
# Test Constants
# =============================================================================

SAMPLE_PERSONA_LLM_RESPONSE = """{
  "detected_persona": "alice-builder",
  "confidence": 0.85,
  "behavior_signals": ["Frequent workflow creation", "Advanced feature usage"],
  "recommendation": "Enable advanced features",
  "ui_adaptations": [{"feature": "workflow_builder", "action": "unlock"}]
}"""

SAMPLE_DISCLOSURE_LLM_RESPONSE = """{
  "current_level": "intermediate",
  "recommended_level": "advanced",
  "confidence": 0.88,
  "unlock_features": ["workflow_builder", "mcp"],
  "personalized_message": "Ready for advanced mode!"
}"""

SAMPLE_ERROR_LLM_RESPONSE = """{
  "category": "timeout",
  "subcategory": "request_timeout",
  "confidence": 0.95,
  "root_cause": "Server timeout due to high load",
  "suggestions": [{"action": "retry", "label": "Try again", "estimated_success": 0.8}]
}"""


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def artifact_storage():
    """Create ArtifactStorage instance."""
    from mcp_server_langgraph.agents.artifacts import ArtifactStorage

    return ArtifactStorage()


@pytest.fixture
def mock_llm_factory():
    """Create mock LLM factory."""
    factory = MagicMock()
    factory.ainvoke = AsyncMock(return_value=AIMessage(content=SAMPLE_PERSONA_LLM_RESPONSE))
    return factory


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = MagicMock()
    settings.ff_enable_ai_suggestions = True
    return settings


# =============================================================================
# Composite Analysis Request/Response Models Tests
# =============================================================================


@pytest.mark.xdist_group(name="ai_ux_composite")
class TestCompositeAnalysisModels:
    """Test composite analysis request/response models exist."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_composite_analysis_request_model_exists(self):
        """CompositeAnalysisRequest model is defined."""
        from mcp_server_langgraph.api.v1.ai_ux import CompositeAnalysisRequest

        request = CompositeAnalysisRequest(
            user_id="user-123",
            session_id="session-456",
            include_persona=True,
            include_disclosure=True,
            include_error=False,
        )
        assert request.user_id == "user-123"
        assert request.session_id == "session-456"
        assert request.include_persona is True
        assert request.include_disclosure is True
        assert request.include_error is False

    def test_composite_analysis_response_model_exists(self):
        """CompositeAnalysisResponse model is defined."""
        from mcp_server_langgraph.api.v1.ai_ux import CompositeAnalysisResponse

        response = CompositeAnalysisResponse(
            user_id="user-123",
            session_id="session-456",
            persona_result=None,
            disclosure_result=None,
            error_result=None,
            cross_insights=[],
            confidence=0.8,
        )
        assert response.user_id == "user-123"
        assert response.confidence == 0.8


# =============================================================================
# AIUXService Composite Analysis Method Tests
# =============================================================================


@pytest.mark.xdist_group(name="ai_ux_composite")
class TestAIUXServiceCompositeMethod:
    """Test AIUXService.run_composite_analysis method."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_composite_analysis_runs_all_requested_analyses(self, mock_llm_factory, mock_settings, artifact_storage):
        """Composite analysis runs all requested analyses."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService
        from mcp_server_langgraph.api.v1.ai_ux import CompositeAnalysisRequest

        # Configure mock to return appropriate responses
        mock_llm_factory.ainvoke = AsyncMock(
            side_effect=[
                AIMessage(content=SAMPLE_PERSONA_LLM_RESPONSE),
                AIMessage(content=SAMPLE_DISCLOSURE_LLM_RESPONSE),
            ]
        )

        service = AIUXService(
            llm_factory=mock_llm_factory,
            settings=mock_settings,
            artifact_storage=artifact_storage,
        )

        request = CompositeAnalysisRequest(
            user_id="user-123",
            session_id="session-456",
            include_persona=True,
            include_disclosure=True,
            include_error=False,
            persona_data={"assigned_persona": "bob", "recent_actions": []},
            disclosure_data={"feature_usage": {"chat": 10}},
        )

        result = await service.run_composite_analysis(request)

        # Both requested analyses should have results
        assert result.persona_result is not None
        assert result.disclosure_result is not None
        assert result.error_result is None  # Not requested

    @pytest.mark.asyncio
    async def test_composite_analysis_stores_all_to_session(self, mock_llm_factory, mock_settings, artifact_storage):
        """Composite analysis stores all results to session context."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService
        from mcp_server_langgraph.api.v1.ai_ux import CompositeAnalysisRequest

        mock_llm_factory.ainvoke = AsyncMock(
            side_effect=[
                AIMessage(content=SAMPLE_PERSONA_LLM_RESPONSE),
                AIMessage(content=SAMPLE_DISCLOSURE_LLM_RESPONSE),
            ]
        )

        service = AIUXService(
            llm_factory=mock_llm_factory,
            settings=mock_settings,
            artifact_storage=artifact_storage,
        )

        request = CompositeAnalysisRequest(
            user_id="user-123",
            session_id="session-456",
            include_persona=True,
            include_disclosure=True,
            include_error=False,
            persona_data={"assigned_persona": "bob"},
            disclosure_data={"feature_usage": {"chat": 10}},
        )

        await service.run_composite_analysis(request)

        # All results should be stored
        all_context = artifact_storage.list_for_task("session-456")
        artifact_names = [a.name for a in all_context]

        assert "persona_analysis" in artifact_names
        assert "disclosure_analysis" in artifact_names
        assert "composite_analysis" in artifact_names

    @pytest.mark.asyncio
    async def test_composite_analysis_generates_cross_insights(self, mock_llm_factory, mock_settings, artifact_storage):
        """Composite analysis generates cross-service insights."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService
        from mcp_server_langgraph.api.v1.ai_ux import CompositeAnalysisRequest

        mock_llm_factory.ainvoke = AsyncMock(
            side_effect=[
                AIMessage(content=SAMPLE_PERSONA_LLM_RESPONSE),
                AIMessage(content=SAMPLE_DISCLOSURE_LLM_RESPONSE),
            ]
        )

        service = AIUXService(
            llm_factory=mock_llm_factory,
            settings=mock_settings,
            artifact_storage=artifact_storage,
        )

        request = CompositeAnalysisRequest(
            user_id="user-123",
            session_id="session-456",
            include_persona=True,
            include_disclosure=True,
            include_error=False,
            persona_data={"assigned_persona": "bob"},
            disclosure_data={"feature_usage": {"chat": 10, "workflows": 5}},
        )

        result = await service.run_composite_analysis(request)

        # Should have cross-service insights
        assert result.cross_insights is not None
        assert len(result.cross_insights) > 0

    @pytest.mark.asyncio
    async def test_composite_analysis_handles_partial_failures(self, mock_llm_factory, mock_settings, artifact_storage):
        """Composite analysis handles partial failures gracefully."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService
        from mcp_server_langgraph.api.v1.ai_ux import CompositeAnalysisRequest

        # First call succeeds, second fails
        mock_llm_factory.ainvoke = AsyncMock(
            side_effect=[
                AIMessage(content=SAMPLE_PERSONA_LLM_RESPONSE),
                RuntimeError("LLM call failed"),
            ]
        )

        service = AIUXService(
            llm_factory=mock_llm_factory,
            settings=mock_settings,
            artifact_storage=artifact_storage,
        )

        request = CompositeAnalysisRequest(
            user_id="user-123",
            session_id="session-456",
            include_persona=True,
            include_disclosure=True,
            include_error=False,
            persona_data={"assigned_persona": "bob"},
            disclosure_data={"feature_usage": {"chat": 10}},
        )

        # Should not raise, should fall back to heuristics
        result = await service.run_composite_analysis(request)

        # Both should have results (one from LLM, one from heuristics)
        assert result.persona_result is not None
        assert result.disclosure_result is not None


# =============================================================================
# Cross-Insights Generation Tests
# =============================================================================


@pytest.mark.xdist_group(name="ai_ux_composite")
class TestCrossInsightsGeneration:
    """Test cross-service insight generation."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_persona_disclosure_mismatch_generates_insight(self, mock_llm_factory, mock_settings):
        """Persona-disclosure mismatch generates insight."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        # Disable LLM to use heuristics
        mock_settings.ff_enable_ai_suggestions = False

        service = AIUXService(
            llm_factory=mock_llm_factory,
            settings=mock_settings,
        )

        # Simulate persona suggesting advanced, disclosure at beginner
        # ADR-0091 Phase 9: current_level and recommended_level are strings
        from mcp_server_langgraph.api.v1.ai_ux import (
            DisclosureAnalyzeResponse,
            PersonaAnalyzeResponse,
        )

        persona_result = PersonaAnalyzeResponse(
            assigned_persona="bob",
            detected_persona="alice-builder",
            confidence=0.85,
            behavior_signals=["Advanced feature usage"],
            recommendation="Upgrade to developer role",
            ui_adaptations=[],
        )

        disclosure_result = DisclosureAnalyzeResponse(
            current_level="beginner",
            recommended_level="beginner",
            confidence=0.9,
            unlock_features=[],
            personalized_message="Keep learning!",
        )

        insights = service._generate_cross_insights(
            persona_result=persona_result,
            disclosure_result=disclosure_result,
            error_result=None,
        )

        # Should detect mismatch
        assert len(insights) > 0
        assert any("mismatch" in i.lower() or "upgrade" in i.lower() for i in insights)

    def test_high_confidence_results_boost_overall_confidence(self, mock_llm_factory, mock_settings):
        """High confidence results boost overall composite confidence."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService
        from mcp_server_langgraph.api.v1.ai_ux import (
            DisclosureAnalyzeResponse,
            PersonaAnalyzeResponse,
        )

        mock_settings.ff_enable_ai_suggestions = False

        service = AIUXService(
            llm_factory=mock_llm_factory,
            settings=mock_settings,
        )

        persona_result = PersonaAnalyzeResponse(
            assigned_persona="bob",
            detected_persona="bob",
            confidence=0.95,
            behavior_signals=[],
            ui_adaptations=[],
        )

        # ADR-0091 Phase 9: current_level and recommended_level are strings
        disclosure_result = DisclosureAnalyzeResponse(
            current_level="intermediate",
            recommended_level="intermediate",
            confidence=0.92,
            unlock_features=[],
        )

        confidence = service._calculate_composite_confidence(
            persona_result=persona_result,
            disclosure_result=disclosure_result,
            error_result=None,
        )

        # High individual confidences should yield high composite
        assert confidence >= 0.85


# =============================================================================
# API Endpoint Tests
# =============================================================================


@pytest.mark.xdist_group(name="ai_ux_composite")
class TestCompositeAnalysisEndpoint:
    """Test composite analysis API endpoint."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_endpoint_exists(self, mock_llm_factory, mock_settings):
        """POST /ai/composite/analyze endpoint exists."""
        from mcp_server_langgraph.api.v1.ai_ux import (
            composite_analyze,
        )

        # Verify endpoint function exists and is callable
        assert callable(composite_analyze)

    @pytest.mark.asyncio
    async def test_endpoint_returns_composite_response(self, mock_llm_factory, mock_settings):
        """Endpoint returns CompositeAnalysisResponse."""
        from mcp_server_langgraph.api.v1.ai_ux import (
            CompositeAnalysisRequest,
            CompositeAnalysisResponse,
        )
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        # Disable LLM for simpler testing
        mock_settings.ff_enable_ai_suggestions = False

        service = AIUXService(
            llm_factory=mock_llm_factory,
            settings=mock_settings,
        )

        request = CompositeAnalysisRequest(
            user_id="user-123",
            session_id="session-456",
            include_persona=True,
            include_disclosure=True,
            include_error=False,
            persona_data={"assigned_persona": "bob"},
            disclosure_data={"feature_usage": {"chat": 10}},
        )

        result = await service.run_composite_analysis(request)

        assert isinstance(result, CompositeAnalysisResponse)
        assert result.user_id == "user-123"
        assert result.session_id == "session-456"
