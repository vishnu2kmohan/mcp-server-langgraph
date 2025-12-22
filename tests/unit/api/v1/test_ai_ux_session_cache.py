"""
AI UX Session Cache Tests

TDD tests for session-based caching with ArtifactStorage integration.

The enhanced caching system provides:
1. Request-level caching (TTLCache) - for cost reduction
2. Session-level context storage (ArtifactStorage) - for cross-service intelligence

Tests verify:
- AIUXService accepts optional ArtifactStorage for session context
- Significant results are stored to session context
- Cross-service context retrieval works
- Session context enables personalized responses

Reference: UX Audit Plan - ArtifactStorage for Rich Context
"""

import gc
import pytest
from unittest.mock import AsyncMock, MagicMock

from langchain_core.messages import AIMessage

pytestmark = pytest.mark.unit

# =============================================================================
# Test Constants
# =============================================================================

SAMPLE_ERROR_LLM_RESPONSE = """{
  "category": "timeout",
  "subcategory": "request_timeout",
  "confidence": 0.95,
  "root_cause": "Server timeout due to high load",
  "suggestions": [{"action": "retry", "label": "Try again", "estimated_success": 0.8}]
}"""

SAMPLE_PERSONA_LLM_RESPONSE = """{
  "detected_persona": "alice-builder",
  "confidence": 0.85,
  "behavior_signals": ["Frequent workflow creation", "Advanced feature usage"],
  "recommendation": "Enable advanced features",
  "ui_adaptations": [{"feature": "workflow_builder", "action": "unlock"}]
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
    factory.ainvoke = AsyncMock(return_value=AIMessage(content=SAMPLE_ERROR_LLM_RESPONSE))
    return factory


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = MagicMock()
    settings.ff_enable_ai_suggestions = True
    return settings


# =============================================================================
# AIUXService ArtifactStorage Integration Tests
# =============================================================================


@pytest.mark.xdist_group(name="ai_ux_session_cache")
class TestAIUXServiceArtifactStorageParam:
    """Test AIUXService accepts ArtifactStorage parameter."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_service_accepts_artifact_storage(
        self, mock_llm_factory, mock_settings, artifact_storage
    ):
        """AIUXService can be initialized with optional ArtifactStorage."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        service = AIUXService(
            llm_factory=mock_llm_factory,
            settings=mock_settings,
            artifact_storage=artifact_storage,
        )
        assert service.artifact_storage is artifact_storage

    def test_service_works_without_artifact_storage(
        self, mock_llm_factory, mock_settings
    ):
        """AIUXService works without ArtifactStorage (backward compatible)."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        service = AIUXService(
            llm_factory=mock_llm_factory,
            settings=mock_settings,
        )
        assert service.artifact_storage is None


@pytest.mark.xdist_group(name="ai_ux_session_cache")
class TestSessionContextStorage:
    """Test session context is stored to ArtifactStorage."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_persona_analysis_stores_to_session(
        self, mock_llm_factory, mock_settings, artifact_storage
    ):
        """Persona analysis stores results to session context."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService
        from mcp_server_langgraph.api.v1.ai_ux import PersonaAnalyzeRequest

        mock_llm_factory.ainvoke = AsyncMock(
            return_value=AIMessage(content=SAMPLE_PERSONA_LLM_RESPONSE)
        )

        service = AIUXService(
            llm_factory=mock_llm_factory,
            settings=mock_settings,
            artifact_storage=artifact_storage,
        )

        request = PersonaAnalyzeRequest(
            user_id="user-123",
            assigned_persona="bob",
            recent_actions=["view_workflows", "create_workflow"],
            feature_usage={"workflow_builder": 5},
        )

        result = await service.analyze_persona(request, session_id="session-456")

        # Result should be stored to artifact storage
        stored = artifact_storage.retrieve("session-456", "persona_analysis")
        assert stored is not None
        assert stored["detected_persona"] == "alice-builder"

    @pytest.mark.asyncio
    async def test_error_analysis_stores_to_session(
        self, mock_llm_factory, mock_settings, artifact_storage
    ):
        """Error analysis stores results to session context."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService
        from mcp_server_langgraph.api.v1.ai_ux import ErrorInfo, UserContext

        mock_llm_factory.ainvoke = AsyncMock(
            return_value=AIMessage(content=SAMPLE_ERROR_LLM_RESPONSE)
        )

        service = AIUXService(
            llm_factory=mock_llm_factory,
            settings=mock_settings,
            artifact_storage=artifact_storage,
        )

        error = ErrorInfo(name="TimeoutError", message="Request timed out")
        user_context = UserContext(persona="bob", session_id="session-456")

        result = await service.analyze_error(error, user_context, session_id="session-456")

        # Result should be stored to artifact storage
        stored = artifact_storage.retrieve("session-456", "error_analysis")
        assert stored is not None


@pytest.mark.xdist_group(name="ai_ux_session_cache")
class TestCrossServiceContextRetrieval:
    """Test cross-service context retrieval from ArtifactStorage."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_nudge_uses_persona_context(
        self, mock_llm_factory, mock_settings, artifact_storage
    ):
        """Nudge recommendation uses stored persona context."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService
        from mcp_server_langgraph.api.v1.ai_ux import NudgeRecommendRequest

        # Pre-populate persona context in artifact storage
        artifact_storage.store(
            task_id="session-456",
            name="persona_analysis",
            data={
                "detected_persona": "alice-builder",
                "confidence": 0.85,
                "behavior_signals": ["Advanced feature usage"],
            },
        )

        mock_llm_factory.ainvoke = AsyncMock(
            return_value=AIMessage(content="""{
                "should_show": true,
                "nudge": {
                    "id": "advanced-features",
                    "type": "tooltip",
                    "target_element": "[data-testid='workflow-panel']",
                    "message": "Try the advanced workflow features!",
                    "priority": "medium",
                    "show_after_ms": 2000
                },
                "confidence": 0.82
            }""")
        )

        service = AIUXService(
            llm_factory=mock_llm_factory,
            settings=mock_settings,
            artifact_storage=artifact_storage,
        )

        request = NudgeRecommendRequest(
            user_id="user-123",
            current_context={"page": "/workflows", "action": "view"},
        )

        result = await service.recommend_nudge(request, session_id="session-456")

        # Service should have access to persona context
        persona_context = service.get_session_context("session-456", "persona_analysis")
        assert persona_context is not None
        assert persona_context["detected_persona"] == "alice-builder"

    def test_get_session_context_returns_none_when_not_found(
        self, mock_llm_factory, mock_settings, artifact_storage
    ):
        """get_session_context returns None when context not found."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        service = AIUXService(
            llm_factory=mock_llm_factory,
            settings=mock_settings,
            artifact_storage=artifact_storage,
        )

        result = service.get_session_context("unknown-session", "persona_analysis")
        assert result is None

    def test_get_session_context_works_without_artifact_storage(
        self, mock_llm_factory, mock_settings
    ):
        """get_session_context returns None when ArtifactStorage not configured."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        service = AIUXService(
            llm_factory=mock_llm_factory,
            settings=mock_settings,
            # No artifact_storage
        )

        result = service.get_session_context("session-456", "persona_analysis")
        assert result is None


@pytest.mark.xdist_group(name="ai_ux_session_cache")
class TestSessionContextAccumulation:
    """Test session context accumulates across multiple service calls."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_multiple_analyses_accumulate_in_session(
        self, mock_llm_factory, mock_settings, artifact_storage
    ):
        """Multiple analyses accumulate in session context."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService
        from mcp_server_langgraph.api.v1.ai_ux import (
            ErrorInfo,
            PersonaAnalyzeRequest,
            UserContext,
        )

        service = AIUXService(
            llm_factory=mock_llm_factory,
            settings=mock_settings,
            artifact_storage=artifact_storage,
        )

        # First: persona analysis
        mock_llm_factory.ainvoke = AsyncMock(
            return_value=AIMessage(content=SAMPLE_PERSONA_LLM_RESPONSE)
        )
        persona_request = PersonaAnalyzeRequest(
            user_id="user-123",
            assigned_persona="bob",
        )
        await service.analyze_persona(persona_request, session_id="session-456")

        # Second: error analysis
        mock_llm_factory.ainvoke = AsyncMock(
            return_value=AIMessage(content=SAMPLE_ERROR_LLM_RESPONSE)
        )
        error = ErrorInfo(name="TimeoutError", message="Request timed out")
        await service.analyze_error(error, None, session_id="session-456")

        # Both should be in session context
        all_artifacts = artifact_storage.list_for_task("session-456")
        artifact_names = [a.name for a in all_artifacts]

        assert "persona_analysis" in artifact_names
        assert "error_analysis" in artifact_names

    def test_get_all_session_context(
        self, mock_llm_factory, mock_settings, artifact_storage
    ):
        """Can retrieve all context for a session."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        # Pre-populate session context
        artifact_storage.store("session-456", "persona_analysis", {"persona": "alice"})
        artifact_storage.store("session-456", "error_analysis", {"count": 2})
        artifact_storage.store("session-456", "disclosure_level", {"level": "advanced"})

        service = AIUXService(
            llm_factory=mock_llm_factory,
            settings=mock_settings,
            artifact_storage=artifact_storage,
        )

        all_context = service.get_all_session_context("session-456")

        assert len(all_context) == 3
        assert "persona_analysis" in all_context
        assert "error_analysis" in all_context
        assert "disclosure_level" in all_context
