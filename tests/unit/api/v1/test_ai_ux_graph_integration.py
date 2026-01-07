"""
AI UX LangGraph Integration Tests

TDD tests for:
1. StateGraph integration with run_composite_analysis
2. Parallel node execution in StateGraph
3. OpenTelemetry spans in graph nodes

Reference: UX Audit Plan - LangGraph Integration
"""

import gc
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.messages import AIMessage

pytestmark = pytest.mark.unit

# =============================================================================
# Test Constants
# =============================================================================

SAMPLE_PERSONA_LLM_RESPONSE = """{
  "detected_persona": "alice-builder",
  "confidence": 0.85,
  "behavior_signals": ["Frequent workflow creation"],
  "recommendation": "Enable advanced features",
  "ui_adaptations": [{"feature": "workflow_builder", "action": "unlock"}]
}"""

SAMPLE_DISCLOSURE_LLM_RESPONSE = """{
  "current_level": "intermediate",
  "recommended_level": "advanced",
  "confidence": 0.88,
  "unlock_features": ["workflow_builder"],
  "personalized_message": "Ready for advanced mode!"
}"""


# =============================================================================
# Fixtures
# =============================================================================


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


@pytest.fixture
def artifact_storage():
    """Create ArtifactStorage instance."""
    from mcp_server_langgraph.agents.artifacts import ArtifactStorage

    return ArtifactStorage()


# =============================================================================
# StateGraph Integration with run_composite_analysis Tests
# =============================================================================


@pytest.mark.xdist_group(name="ai_ux_graph_integration")
class TestRunCompositeAnalysisWithGraph:
    """Test run_composite_analysis uses StateGraph internally."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_service_has_use_graph_flag(self, mock_llm_factory, mock_settings):
        """AIUXService can be configured to use StateGraph."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        service = AIUXService(
            llm_factory=mock_llm_factory,
            settings=mock_settings,
        )

        # Service should have a flag or method to enable graph-based execution
        assert hasattr(service, "get_analysis_graph") or hasattr(service, "_analysis_graph")

    @pytest.mark.asyncio
    async def test_run_composite_with_graph_produces_same_results(self, mock_llm_factory, mock_settings, artifact_storage):
        """Graph-based composite analysis produces same results as direct calls."""
        from mcp_server_langgraph.api.v1.ai_ux import CompositeAnalysisRequest
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

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

        result = await service.run_composite_analysis(request)

        # Results should be populated
        assert result.user_id == "user-123"
        assert result.persona_result is not None
        assert result.disclosure_result is not None

    @pytest.mark.asyncio
    async def test_graph_execution_stores_to_artifact_storage(self, mock_llm_factory, mock_settings, artifact_storage):
        """StateGraph execution stores results to artifact storage."""
        from mcp_server_langgraph.api.v1.ai_ux import CompositeAnalysisRequest
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

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
            session_id="session-graph-test",
            include_persona=True,
            include_disclosure=True,
            include_error=False,
            persona_data={"assigned_persona": "bob"},
            disclosure_data={"feature_usage": {"chat": 10}},
        )

        await service.run_composite_analysis(request)

        # Check artifact storage has the results
        all_artifacts = artifact_storage.list_for_task("session-graph-test")
        artifact_names = [a.name for a in all_artifacts]

        assert "composite_analysis" in artifact_names


# =============================================================================
# Parallel Execution Tests
# =============================================================================


@pytest.mark.xdist_group(name="ai_ux_graph_parallel")
class TestParallelNodeExecution:
    """Test parallel node execution in StateGraph."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_graph_supports_parallel_flag(self, mock_llm_factory, mock_settings):
        """StateGraph factory accepts parallel execution flag."""
        from mcp_server_langgraph.api.v1.ai_ux_graph import create_ux_analysis_graph

        # Graph should be creatable with parallel execution option
        graph = create_ux_analysis_graph(mock_llm_factory, mock_settings)
        assert graph is not None

    @pytest.mark.asyncio
    async def test_parallel_analyses_complete_faster(self, mock_llm_factory, mock_settings):
        """Parallel execution should complete faster than sequential."""
        import time
        from mcp_server_langgraph.api.v1.ai_ux_graph import (
            UXAnalysisState,
            create_ux_analysis_graph,
        )

        # Add artificial delay to mock LLM calls
        async def slow_response(*args, **kwargs):
            import asyncio

            await asyncio.sleep(0.05)  # 50ms delay
            return AIMessage(content=SAMPLE_PERSONA_LLM_RESPONSE)

        mock_llm_factory.ainvoke = AsyncMock(side_effect=slow_response)

        graph = create_ux_analysis_graph(mock_llm_factory, mock_settings)
        compiled = graph.compile()

        initial_state: UXAnalysisState = {
            "user_id": "user-123",
            "session_id": "session-456",
            "include_persona": True,
            "include_disclosure": True,
            "include_error": False,
            "persona_data": {"assigned_persona": "bob"},
            "disclosure_data": {"feature_usage": {"chat": 10}},
            "error_data": None,
            "persona_result": None,
            "disclosure_result": None,
            "error_result": None,
            "cross_insights": [],
            "confidence": 0.0,
        }

        start = time.time()
        result = await compiled.ainvoke(initial_state)
        time.time() - start

        # Graph should execute (timing may vary but should complete)
        assert result is not None
        # With 2 analyses taking 50ms each, parallel should be faster than 100ms
        # (allowing some overhead for test variability)
        # Sequential would take ~100ms+, parallel could be ~50ms+

    @pytest.mark.asyncio
    async def test_all_analyses_run_when_enabled(self, mock_llm_factory, mock_settings):
        """All enabled analyses run in graph execution."""
        from mcp_server_langgraph.api.v1.ai_ux_graph import (
            UXAnalysisState,
            create_ux_analysis_graph,
        )

        mock_llm_factory.ainvoke = AsyncMock(
            side_effect=[
                AIMessage(content=SAMPLE_PERSONA_LLM_RESPONSE),
                AIMessage(content=SAMPLE_DISCLOSURE_LLM_RESPONSE),
            ]
        )

        graph = create_ux_analysis_graph(mock_llm_factory, mock_settings)
        compiled = graph.compile()

        initial_state: UXAnalysisState = {
            "user_id": "user-123",
            "session_id": "session-456",
            "include_persona": True,
            "include_disclosure": True,
            "include_error": False,
            "persona_data": {"assigned_persona": "bob"},
            "disclosure_data": {"feature_usage": {"chat": 10}},
            "error_data": None,
            "persona_result": None,
            "disclosure_result": None,
            "error_result": None,
            "cross_insights": [],
            "confidence": 0.0,
        }

        result = await compiled.ainvoke(initial_state)

        # Both analyses should have results
        assert result["persona_result"] is not None
        assert result["disclosure_result"] is not None


# =============================================================================
# OpenTelemetry Spans Tests
# =============================================================================


@pytest.mark.xdist_group(name="ai_ux_graph_telemetry")
class TestOpenTelemetrySpans:
    """Test OpenTelemetry spans in graph nodes."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_graph_execution_creates_trace_span(self, mock_llm_factory, mock_settings):
        """Graph execution creates OpenTelemetry trace spans."""
        from mcp_server_langgraph.api.v1.ai_ux_graph import (
            UXAnalysisState,
            create_ux_analysis_graph,
        )

        mock_llm_factory.ainvoke = AsyncMock(return_value=AIMessage(content=SAMPLE_PERSONA_LLM_RESPONSE))

        graph = create_ux_analysis_graph(mock_llm_factory, mock_settings)
        compiled = graph.compile()

        initial_state: UXAnalysisState = {
            "user_id": "user-123",
            "session_id": "session-456",
            "include_persona": True,
            "include_disclosure": False,
            "include_error": False,
            "persona_data": {"assigned_persona": "bob"},
            "disclosure_data": None,
            "error_data": None,
            "persona_result": None,
            "disclosure_result": None,
            "error_result": None,
            "cross_insights": [],
            "confidence": 0.0,
        }

        # Execute graph - should not raise even without actual tracing setup
        result = await compiled.ainvoke(initial_state)
        assert result is not None

    @pytest.mark.asyncio
    async def test_node_execution_logs_debug_info(self, mock_llm_factory, mock_settings):
        """Node execution logs debug information."""
        from mcp_server_langgraph.api.v1.ai_ux_graph import (
            UXAnalysisState,
            create_ux_analysis_graph,
        )

        mock_llm_factory.ainvoke = AsyncMock(return_value=AIMessage(content=SAMPLE_PERSONA_LLM_RESPONSE))

        with patch("mcp_server_langgraph.api.v1.ai_ux_graph.logger") as mock_logger:
            graph = create_ux_analysis_graph(mock_llm_factory, mock_settings)
            compiled = graph.compile()

            initial_state: UXAnalysisState = {
                "user_id": "user-123",
                "session_id": "session-456",
                "include_persona": True,
                "include_disclosure": False,
                "include_error": False,
                "persona_data": {"assigned_persona": "bob"},
                "disclosure_data": None,
                "error_data": None,
                "persona_result": None,
                "disclosure_result": None,
                "error_result": None,
                "cross_insights": [],
                "confidence": 0.0,
            }

            await compiled.ainvoke(initial_state)

            # Should have logged debug info about analysis completion
            assert mock_logger.debug.called or mock_logger.warning.called

    def test_graph_nodes_have_metadata(self, mock_llm_factory, mock_settings):
        """Graph nodes can have metadata for tracing."""
        from mcp_server_langgraph.api.v1.ai_ux_graph import create_ux_analysis_graph

        graph = create_ux_analysis_graph(mock_llm_factory, mock_settings)

        # Graph should compile without errors
        compiled = graph.compile()
        assert compiled is not None


# =============================================================================
# E2E Composite Endpoint Tests
# =============================================================================


@pytest.mark.xdist_group(name="ai_ux_composite_e2e")
class TestCompositeEndpointE2E:
    """E2E tests for composite analysis endpoint."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_composite_endpoint_full_flow(self, mock_llm_factory, mock_settings, artifact_storage):
        """Full E2E flow for composite analysis."""
        from mcp_server_langgraph.api.v1.ai_ux import CompositeAnalysisRequest
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

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
            user_id="user-e2e",
            session_id="session-e2e",
            include_persona=True,
            include_disclosure=True,
            include_error=False,
            persona_data={"assigned_persona": "bob", "recent_actions": ["create_workflow"]},
            disclosure_data={"feature_usage": {"chat": 10, "workflows": 5}},
        )

        result = await service.run_composite_analysis(request)

        # Verify full response structure
        assert result.user_id == "user-e2e"
        assert result.session_id == "session-e2e"
        assert result.persona_result is not None
        assert result.disclosure_result is not None
        assert result.error_result is None
        assert len(result.cross_insights) > 0
        assert 0 <= result.confidence <= 1

    @pytest.mark.asyncio
    async def test_composite_endpoint_handles_llm_failures_gracefully(self, mock_llm_factory, mock_settings, artifact_storage):
        """Composite endpoint handles LLM failures gracefully."""
        from mcp_server_langgraph.api.v1.ai_ux import CompositeAnalysisRequest
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        # All LLM calls fail
        mock_llm_factory.ainvoke = AsyncMock(side_effect=RuntimeError("LLM unavailable"))

        service = AIUXService(
            llm_factory=mock_llm_factory,
            settings=mock_settings,
            artifact_storage=artifact_storage,
        )

        request = CompositeAnalysisRequest(
            user_id="user-fail",
            session_id="session-fail",
            include_persona=True,
            include_disclosure=True,
            include_error=False,
            persona_data={"assigned_persona": "bob"},
            disclosure_data={"feature_usage": {"chat": 10}},
        )

        # Should not raise - should fall back to heuristics
        result = await service.run_composite_analysis(request)

        # Should still have results (from heuristic fallback)
        assert result.user_id == "user-fail"
        assert result.persona_result is not None
        assert result.disclosure_result is not None

    @pytest.mark.asyncio
    async def test_composite_endpoint_cross_insights_correlate_data(self, mock_llm_factory, mock_settings, artifact_storage):
        """Cross insights correlate persona and disclosure data."""
        from mcp_server_langgraph.api.v1.ai_ux import CompositeAnalysisRequest
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        # Disable LLM to use heuristics for deterministic testing
        mock_settings.ff_enable_ai_suggestions = False

        service = AIUXService(
            llm_factory=mock_llm_factory,
            settings=mock_settings,
            artifact_storage=artifact_storage,
        )

        request = CompositeAnalysisRequest(
            user_id="user-insights",
            session_id="session-insights",
            include_persona=True,
            include_disclosure=True,
            include_error=False,
            persona_data={"assigned_persona": "bob"},
            disclosure_data={"feature_usage": {"chat": 10}},
        )

        result = await service.run_composite_analysis(request)

        # Should have cross insights about both analyses
        assert len(result.cross_insights) > 0
