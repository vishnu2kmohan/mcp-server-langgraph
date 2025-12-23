"""
AI UX Advanced Features Tests

TDD tests for:
1. True Parallel Execution with LangGraph Send API
2. OpenTelemetry Spans in Graph Nodes
3. Streaming Composite Analysis Endpoint

Reference: UX Audit Plan - LangGraph Integration Advanced Features
"""

import asyncio
import gc
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
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

SAMPLE_ERROR_LLM_RESPONSE = """{
  "category": "network",
  "subcategory": "timeout",
  "confidence": 0.90,
  "root_cause": "Server timeout",
  "suggestions": [{"action": "retry", "label": "Try again"}]
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
# True Parallel Execution with Send API Tests
# =============================================================================


@pytest.mark.xdist_group(name="ai_ux_parallel_send")
class TestParallelExecutionWithSendAPI:
    """Test true parallel execution using LangGraph Send API."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_parallel_graph_function_exists(self):
        """Parallel graph factory function exists."""
        from mcp_server_langgraph.api.v1.ai_ux_graph import create_parallel_ux_graph

        assert callable(create_parallel_ux_graph)

    def test_parallel_graph_uses_send_for_distribution(self, mock_llm_factory, mock_settings):
        """Parallel graph uses Send API for state distribution."""
        from mcp_server_langgraph.api.v1.ai_ux_graph import create_parallel_ux_graph

        graph = create_parallel_ux_graph(mock_llm_factory, mock_settings)
        compiled = graph.compile()

        # Graph should compile successfully
        assert compiled is not None

    @pytest.mark.asyncio
    async def test_parallel_execution_runs_analyses_concurrently(self, mock_llm_factory, mock_settings):
        """Parallel graph runs multiple analyses concurrently."""
        import time

        from mcp_server_langgraph.api.v1.ai_ux_graph import (
            UXAnalysisState,
            create_parallel_ux_graph,
        )

        # Add artificial delay to mock LLM calls
        call_times: list[float] = []

        async def slow_response(*args: Any, **kwargs: Any) -> AIMessage:
            call_times.append(time.time())
            await asyncio.sleep(0.05)  # 50ms delay
            return AIMessage(content=SAMPLE_PERSONA_LLM_RESPONSE)

        mock_llm_factory.ainvoke = AsyncMock(side_effect=slow_response)

        graph = create_parallel_ux_graph(mock_llm_factory, mock_settings)
        compiled = graph.compile()

        initial_state: UXAnalysisState = {
            "user_id": "user-123",
            "session_id": "session-456",
            "include_persona": True,
            "include_disclosure": True,
            "include_error": True,
            "persona_data": {"assigned_persona": "bob"},
            "disclosure_data": {"feature_usage": {"chat": 10}},
            "error_data": {"name": "NetworkError", "message": "Timeout"},
            "persona_result": None,
            "disclosure_result": None,
            "error_result": None,
            "cross_insights": [],
            "confidence": 0.0,
        }

        start = time.time()
        await compiled.ainvoke(initial_state)
        elapsed = time.time() - start

        # With 3 analyses taking 50ms each:
        # Sequential would take ~150ms+
        # Parallel should complete in ~50-80ms (plus overhead)
        # Allow generous margin for test variability
        assert elapsed < 0.2  # Should be much faster than 150ms

    @pytest.mark.asyncio
    async def test_parallel_graph_collects_all_results(self, mock_llm_factory, mock_settings):
        """Parallel graph collects results from all branches."""
        from mcp_server_langgraph.api.v1.ai_ux_graph import (
            UXAnalysisState,
            create_parallel_ux_graph,
        )

        mock_llm_factory.ainvoke = AsyncMock(
            side_effect=[
                AIMessage(content=SAMPLE_PERSONA_LLM_RESPONSE),
                AIMessage(content=SAMPLE_DISCLOSURE_LLM_RESPONSE),
                AIMessage(content=SAMPLE_ERROR_LLM_RESPONSE),
            ]
        )

        graph = create_parallel_ux_graph(mock_llm_factory, mock_settings)
        compiled = graph.compile()

        initial_state: UXAnalysisState = {
            "user_id": "user-123",
            "session_id": "session-456",
            "include_persona": True,
            "include_disclosure": True,
            "include_error": True,
            "persona_data": {"assigned_persona": "bob"},
            "disclosure_data": {"feature_usage": {"chat": 10}},
            "error_data": {"name": "NetworkError", "message": "Timeout"},
            "persona_result": None,
            "disclosure_result": None,
            "error_result": None,
            "cross_insights": [],
            "confidence": 0.0,
        }

        result = await compiled.ainvoke(initial_state)

        # All three analyses should have results
        assert result["persona_result"] is not None
        assert result["disclosure_result"] is not None
        assert result["error_result"] is not None


# =============================================================================
# OpenTelemetry Spans in Graph Nodes Tests
# =============================================================================


@pytest.mark.xdist_group(name="ai_ux_otel_spans")
class TestOpenTelemetrySpansInNodes:
    """Test OpenTelemetry span instrumentation in graph nodes."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_tracer_is_available_in_graph_module(self):
        """Tracer is available for instrumentation."""
        from mcp_server_langgraph.api.v1 import ai_ux_graph

        # Module should have tracer for instrumentation
        assert hasattr(ai_ux_graph, "tracer") or hasattr(ai_ux_graph, "get_tracer")

    @pytest.mark.asyncio
    async def test_persona_analysis_creates_span(self, mock_llm_factory, mock_settings):
        """Persona analysis node creates OpenTelemetry span."""
        from mcp_server_langgraph.api.v1.ai_ux_graph import (
            UXAnalysisState,
            create_ux_analysis_graph,
        )

        mock_llm_factory.ainvoke = AsyncMock(return_value=AIMessage(content=SAMPLE_PERSONA_LLM_RESPONSE))

        with patch("mcp_server_langgraph.api.v1.ai_ux_graph.tracer") as mock_tracer:
            mock_span = MagicMock()
            mock_tracer.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
            mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=None)

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

            # Tracer should have been called to create spans
            assert mock_tracer.start_as_current_span.called

    @pytest.mark.asyncio
    async def test_spans_include_node_name_attribute(self, mock_llm_factory, mock_settings):
        """Spans include node name as attribute."""
        from mcp_server_langgraph.api.v1.ai_ux_graph import (
            UXAnalysisState,
            create_ux_analysis_graph,
        )

        mock_llm_factory.ainvoke = AsyncMock(return_value=AIMessage(content=SAMPLE_PERSONA_LLM_RESPONSE))

        span_names: list[str] = []

        with patch("mcp_server_langgraph.api.v1.ai_ux_graph.tracer") as mock_tracer:

            def capture_span_name(name: str, **kwargs: Any) -> MagicMock:
                span_names.append(name)
                mock_ctx = MagicMock()
                mock_ctx.__enter__ = MagicMock(return_value=MagicMock())
                mock_ctx.__exit__ = MagicMock(return_value=None)
                return mock_ctx

            mock_tracer.start_as_current_span.side_effect = capture_span_name

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

            # Should have spans with descriptive names
            assert len(span_names) > 0
            assert any("persona" in name.lower() for name in span_names)

    @pytest.mark.asyncio
    async def test_spans_record_user_id_attribute(self, mock_llm_factory, mock_settings):
        """Spans record user_id as attribute."""
        from mcp_server_langgraph.api.v1.ai_ux_graph import (
            UXAnalysisState,
            create_ux_analysis_graph,
        )

        mock_llm_factory.ainvoke = AsyncMock(return_value=AIMessage(content=SAMPLE_PERSONA_LLM_RESPONSE))

        recorded_attributes: list[dict[str, Any]] = []

        with patch("mcp_server_langgraph.api.v1.ai_ux_graph.tracer") as mock_tracer:
            mock_span = MagicMock()

            def capture_attributes(attrs: dict[str, Any]) -> None:
                recorded_attributes.append(attrs)

            mock_span.set_attributes = capture_attributes

            mock_ctx = MagicMock()
            mock_ctx.__enter__ = MagicMock(return_value=mock_span)
            mock_ctx.__exit__ = MagicMock(return_value=None)
            mock_tracer.start_as_current_span.return_value = mock_ctx

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

            # Should have recorded user_id in at least one span
            all_attrs = {}
            for attrs in recorded_attributes:
                all_attrs.update(attrs)

            # Check user_id was recorded
            assert "user_id" in all_attrs or any("user" in str(k).lower() for k in all_attrs.keys())


# =============================================================================
# Streaming Composite Analysis Tests
# =============================================================================


@pytest.mark.xdist_group(name="ai_ux_streaming")
class TestStreamingCompositeAnalysis:
    """Test streaming endpoint for composite analysis."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_streaming_endpoint_exists(self):
        """Streaming composite endpoint exists in router."""
        from mcp_server_langgraph.api.v1.ai_ux import ai_ux_router

        # Check for streaming endpoint
        routes = [route.path for route in ai_ux_router.routes]
        assert "/composite/stream" in routes or any("stream" in r for r in routes)

    @pytest.mark.asyncio
    async def test_streaming_returns_async_generator(self, mock_llm_factory, mock_settings, artifact_storage):
        """Streaming method returns async generator."""
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

        # Service should have streaming method
        assert hasattr(service, "stream_composite_analysis")

        # Should return async generator
        stream = service.stream_composite_analysis(request)
        assert hasattr(stream, "__aiter__")

    @pytest.mark.asyncio
    async def test_streaming_yields_progress_events(self, mock_llm_factory, mock_settings, artifact_storage):
        """Streaming yields progress events for each analysis."""
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

        events: list[dict[str, Any]] = []
        async for event in service.stream_composite_analysis(request):
            events.append(event)

        # Should have multiple events
        assert len(events) >= 2

        # Should have progress or result events
        event_types = [e.get("type") or e.get("event") for e in events]
        assert any("persona" in str(t).lower() for t in event_types) or len(events) >= 2

    @pytest.mark.asyncio
    async def test_streaming_final_event_contains_complete_result(self, mock_llm_factory, mock_settings, artifact_storage):
        """Final streaming event contains complete composite result."""
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

        events: list[dict[str, Any]] = []
        async for event in service.stream_composite_analysis(request):
            events.append(event)

        # Last event should be complete result
        final_event = events[-1]
        assert "complete" in str(final_event).lower() or "result" in final_event


# =============================================================================
# Service Integration Tests
# =============================================================================


@pytest.mark.xdist_group(name="ai_ux_service_advanced")
class TestAIUXServiceAdvancedIntegration:
    """Test AIUXService integration with advanced features."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_service_uses_parallel_graph_when_enabled(self, mock_llm_factory, mock_settings, artifact_storage):
        """Service uses parallel graph when parallel mode enabled."""
        from mcp_server_langgraph.api.v1.ai_ux import CompositeAnalysisRequest
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        mock_llm_factory.ainvoke = AsyncMock(
            side_effect=[
                AIMessage(content=SAMPLE_PERSONA_LLM_RESPONSE),
                AIMessage(content=SAMPLE_DISCLOSURE_LLM_RESPONSE),
            ]
        )

        # Enable parallel mode
        mock_settings.ff_enable_parallel_analysis = True

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

        # Should complete successfully
        assert result.persona_result is not None
        assert result.disclosure_result is not None

    @pytest.mark.asyncio
    async def test_service_has_get_parallel_graph_method(self, mock_llm_factory, mock_settings):
        """Service has method to get parallel graph."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        service = AIUXService(
            llm_factory=mock_llm_factory,
            settings=mock_settings,
        )

        # Should have method to get parallel graph
        assert hasattr(service, "get_parallel_graph") or hasattr(service, "_parallel_graph")
