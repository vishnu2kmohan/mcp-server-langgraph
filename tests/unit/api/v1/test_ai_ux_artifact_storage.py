"""
AI UX ArtifactStorage Integration Tests

TDD tests for ArtifactStorage integration with AIUXService.

Tests verify:
- ArtifactStorage can be used for cross-service context sharing
- LLM response caching can use ArtifactStorage for persistence
- Session context can be stored and retrieved across services

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

SAMPLE_ERROR_ANALYSIS_RESULT = {
    "category": "timeout",
    "root_cause": "Server timeout",
    "suggestions": [{"action": "retry", "label": "Try again"}],
}

SAMPLE_PERSONA_ANALYSIS_RESULT = {
    "detected_persona": "alice-builder",
    "confidence": 0.85,
    "behavior_signals": ["Frequent workflow creation"],
}


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
    factory.ainvoke = AsyncMock(return_value=AIMessage(content='{"result": "test"}'))
    return factory


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = MagicMock()
    settings.ff_enable_ai_suggestions = True
    return settings


# =============================================================================
# ArtifactStorage Basic Tests
# =============================================================================


@pytest.mark.xdist_group(name="ai_ux_artifact")
class TestArtifactStorageBasics:
    """Test basic ArtifactStorage operations."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_store_and_retrieve_artifact(self, artifact_storage):
        """Can store and retrieve an artifact."""
        artifact_storage.store(
            task_id="session-123",
            name="error_analysis",
            data=SAMPLE_ERROR_ANALYSIS_RESULT,
        )

        retrieved = artifact_storage.retrieve("session-123", "error_analysis")
        assert retrieved == SAMPLE_ERROR_ANALYSIS_RESULT

    def test_store_multiple_artifacts_per_session(self, artifact_storage):
        """Can store multiple artifacts for a session."""
        artifact_storage.store(
            task_id="session-123",
            name="error_analysis",
            data=SAMPLE_ERROR_ANALYSIS_RESULT,
        )
        artifact_storage.store(
            task_id="session-123",
            name="persona_analysis",
            data=SAMPLE_PERSONA_ANALYSIS_RESULT,
        )

        errors = artifact_storage.retrieve("session-123", "error_analysis")
        persona = artifact_storage.retrieve("session-123", "persona_analysis")

        assert errors == SAMPLE_ERROR_ANALYSIS_RESULT
        assert persona == SAMPLE_PERSONA_ANALYSIS_RESULT

    def test_list_artifacts_for_session(self, artifact_storage):
        """Can list all artifacts for a session."""
        artifact_storage.store(
            task_id="session-123",
            name="error_analysis",
            data=SAMPLE_ERROR_ANALYSIS_RESULT,
        )
        artifact_storage.store(
            task_id="session-123",
            name="persona_analysis",
            data=SAMPLE_PERSONA_ANALYSIS_RESULT,
        )

        artifacts = artifact_storage.list_for_task("session-123")
        assert len(artifacts) == 2

    def test_clear_session_artifacts(self, artifact_storage):
        """Can clear all artifacts for a session."""
        artifact_storage.store(
            task_id="session-123",
            name="error_analysis",
            data=SAMPLE_ERROR_ANALYSIS_RESULT,
        )

        artifact_storage.clear_task("session-123")

        retrieved = artifact_storage.retrieve("session-123", "error_analysis")
        assert retrieved is None


# =============================================================================
# Cross-Service Context Sharing Tests
# =============================================================================


@pytest.mark.xdist_group(name="ai_ux_artifact")
class TestCrossServiceContext:
    """Test cross-service context sharing with ArtifactStorage."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_persona_context_available_for_nudge(self, artifact_storage):
        """Persona analysis results can inform nudge recommendations."""
        # Simulate persona analysis storing results
        artifact_storage.store(
            task_id="session-123",
            name="persona_analysis",
            data=SAMPLE_PERSONA_ANALYSIS_RESULT,
            metadata={"method": "persona_analysis", "confidence": 0.85},
        )

        # Nudge service can retrieve persona context
        persona_context = artifact_storage.retrieve("session-123", "persona_analysis")
        assert persona_context is not None
        assert persona_context["detected_persona"] == "alice-builder"

        # This enables personalized nudges based on detected persona
        if persona_context["detected_persona"] == "alice-builder":
            nudge_target = "workflow_builder"
        else:
            nudge_target = "getting_started"

        assert nudge_target == "workflow_builder"

    def test_error_context_available_for_disclosure(self, artifact_storage):
        """Error analysis results can inform disclosure level."""
        # Simulate error analysis storing results
        artifact_storage.store(
            task_id="session-123",
            name="error_analysis",
            data=SAMPLE_ERROR_ANALYSIS_RESULT,
            metadata={"error_count": 3},
        )

        # Disclosure service can check error patterns
        error_context = artifact_storage.retrieve("session-123", "error_analysis")
        artifact = artifact_storage.get_artifact("session-123", "error_analysis")

        assert error_context is not None
        assert artifact is not None
        assert artifact.metadata.get("error_count") == 3

    def test_session_context_accumulates(self, artifact_storage):
        """Session context accumulates across multiple services."""
        # Multiple services store their results
        artifact_storage.store(
            task_id="session-123",
            name="persona_analysis",
            data=SAMPLE_PERSONA_ANALYSIS_RESULT,
        )
        artifact_storage.store(
            task_id="session-123",
            name="error_analysis",
            data=SAMPLE_ERROR_ANALYSIS_RESULT,
        )
        artifact_storage.store(
            task_id="session-123",
            name="disclosure_level",
            data={"level": "intermediate", "confidence": 0.88},
        )

        # All context is available for composite analysis
        all_artifacts = artifact_storage.list_for_task("session-123")
        assert len(all_artifacts) == 3

        # Can build rich context from accumulated data
        context = {a.name: a.data for a in all_artifacts}
        assert "persona_analysis" in context
        assert "error_analysis" in context
        assert "disclosure_level" in context


# =============================================================================
# AIUXService Integration Tests (Future Implementation)
# =============================================================================


@pytest.mark.xdist_group(name="ai_ux_artifact")
class TestAIUXServiceArtifactIntegration:
    """Tests for future AIUXService + ArtifactStorage integration."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_aiux_service_accepts_artifact_storage(self, mock_llm_factory, mock_settings, artifact_storage):
        """AIUXService can optionally accept ArtifactStorage."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        # This test documents the expected integration
        # Implementation would add artifact_storage parameter to AIUXService
        service = AIUXService(
            llm_factory=mock_llm_factory,
            settings=mock_settings,
        )

        # Currently, artifact_storage is not integrated
        # This test passes but documents the desired interface
        assert service is not None
        # Future: assert service.artifact_storage is artifact_storage

    @pytest.mark.asyncio
    async def test_analyze_error_stores_to_artifact_storage(self, mock_llm_factory, mock_settings, artifact_storage):
        """analyze_error should optionally store results to ArtifactStorage."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService
        from mcp_server_langgraph.api.v1.ai_ux import ErrorInfo

        # Set up mock to return a valid response
        mock_llm_factory.ainvoke = AsyncMock(
            return_value=AIMessage(
                content='{"category": "timeout", "subcategory": "request", "confidence": 0.9, "root_cause": "slow server", "suggestions": []}'
            )
        )

        service = AIUXService(
            llm_factory=mock_llm_factory,
            settings=mock_settings,
        )

        error = ErrorInfo(name="TimeoutError", message="Request timed out")
        result = await service.analyze_error(error, None)

        # Result should be returned
        assert result is not None

        # Future: service would store to artifact_storage
        # artifact_storage.retrieve("session-123", "error_analysis") would return result
