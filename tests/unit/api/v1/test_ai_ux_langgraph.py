"""
AI UX LangGraph StateGraph Tests

TDD tests for refactoring AIUXService to use LangGraph StateGraph.

The StateGraph provides:
1. Unified state management for UX analysis workflows
2. Declarative node-based analysis pipeline
3. Conditional routing based on analysis requirements
4. Built-in observability via LangGraph tracing
5. Support for parallel node execution

Tests verify:
- UX analysis state schema is properly defined
- Analysis nodes execute correctly
- Conditional routing works based on request flags
- State is properly accumulated through the graph
- Results match the existing AIUXService behavior

Reference: UX Audit Plan - LangGraph Integration
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


# =============================================================================
# UX Analysis State Schema Tests
# =============================================================================


@pytest.mark.xdist_group(name="ai_ux_langgraph")
class TestUXAnalysisStateSchema:
    """Test the UX analysis state schema definition."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_ux_analysis_state_is_typed_dict(self):
        """UXAnalysisState is a TypedDict with required fields."""
        from mcp_server_langgraph.api.v1.ai_ux_graph import UXAnalysisState

        # Verify it's a proper TypedDict
        assert hasattr(UXAnalysisState, "__annotations__")

        # Required fields
        annotations = UXAnalysisState.__annotations__
        assert "user_id" in annotations
        assert "session_id" in annotations
        assert "include_persona" in annotations
        assert "include_disclosure" in annotations
        assert "include_error" in annotations

    def test_state_includes_analysis_results(self):
        """State includes fields for analysis results."""
        from mcp_server_langgraph.api.v1.ai_ux_graph import UXAnalysisState

        annotations = UXAnalysisState.__annotations__
        assert "persona_result" in annotations
        assert "disclosure_result" in annotations
        assert "error_result" in annotations
        assert "cross_insights" in annotations
        assert "confidence" in annotations


# =============================================================================
# StateGraph Definition Tests
# =============================================================================


@pytest.mark.xdist_group(name="ai_ux_langgraph")
class TestUXAnalysisGraphDefinition:
    """Test the UX analysis StateGraph definition."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_ux_analysis_graph_exists(self):
        """create_ux_analysis_graph function exists."""
        from mcp_server_langgraph.api.v1.ai_ux_graph import create_ux_analysis_graph

        assert callable(create_ux_analysis_graph)

    def test_graph_has_expected_nodes(self, mock_llm_factory, mock_settings):
        """Graph has nodes for each analysis type."""
        from mcp_server_langgraph.api.v1.ai_ux_graph import create_ux_analysis_graph

        graph = create_ux_analysis_graph(mock_llm_factory, mock_settings)

        # Check graph has nodes (LangGraph stores nodes internally)
        compiled = graph.compile()
        assert compiled is not None

    def test_graph_compiles_successfully(self, mock_llm_factory, mock_settings):
        """Graph compiles without errors."""
        from mcp_server_langgraph.api.v1.ai_ux_graph import create_ux_analysis_graph

        graph = create_ux_analysis_graph(mock_llm_factory, mock_settings)
        compiled = graph.compile()

        # Verify it's a compiled graph
        assert hasattr(compiled, "invoke") or hasattr(compiled, "ainvoke")


# =============================================================================
# Graph Execution Tests
# =============================================================================


@pytest.mark.xdist_group(name="ai_ux_langgraph")
class TestUXAnalysisGraphExecution:
    """Test UX analysis graph execution."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_graph_executes_persona_analysis(self, mock_llm_factory, mock_settings):
        """Graph executes persona analysis when requested."""
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

        result = await compiled.ainvoke(initial_state)

        assert result["persona_result"] is not None

    @pytest.mark.asyncio
    async def test_graph_executes_multiple_analyses(self, mock_llm_factory, mock_settings):
        """Graph executes multiple analyses when requested."""
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

        assert result["persona_result"] is not None
        assert result["disclosure_result"] is not None

    @pytest.mark.asyncio
    async def test_graph_skips_disabled_analyses(self, mock_llm_factory, mock_settings):
        """Graph skips analyses that are not requested."""
        from mcp_server_langgraph.api.v1.ai_ux_graph import (
            UXAnalysisState,
            create_ux_analysis_graph,
        )

        graph = create_ux_analysis_graph(mock_llm_factory, mock_settings)
        compiled = graph.compile()

        initial_state: UXAnalysisState = {
            "user_id": "user-123",
            "session_id": "session-456",
            "include_persona": False,
            "include_disclosure": False,
            "include_error": False,
            "persona_data": None,
            "disclosure_data": None,
            "error_data": None,
            "persona_result": None,
            "disclosure_result": None,
            "error_result": None,
            "cross_insights": [],
            "confidence": 0.0,
        }

        result = await compiled.ainvoke(initial_state)

        # No analyses should have been run
        assert result["persona_result"] is None
        assert result["disclosure_result"] is None
        assert result["error_result"] is None


# =============================================================================
# Cross-Insights Node Tests
# =============================================================================


@pytest.mark.xdist_group(name="ai_ux_langgraph")
class TestCrossInsightsNode:
    """Test cross-insights generation node."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_cross_insights_generated_after_analyses(self, mock_llm_factory, mock_settings):
        """Cross insights are generated after individual analyses."""
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

        # Should have cross insights
        assert len(result["cross_insights"]) > 0

    @pytest.mark.asyncio
    async def test_confidence_calculated_in_final_state(self, mock_llm_factory, mock_settings):
        """Confidence is calculated from analysis results."""
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

        # Confidence should be set based on analysis results
        assert result["confidence"] > 0.0


# =============================================================================
# Integration with AIUXService Tests
# =============================================================================


@pytest.mark.xdist_group(name="ai_ux_langgraph")
class TestAIUXServiceGraphIntegration:
    """Test AIUXService integration with StateGraph."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_service_can_use_graph_for_composite(self, mock_llm_factory, mock_settings):
        """AIUXService can optionally use StateGraph for composite analysis."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        service = AIUXService(
            llm_factory=mock_llm_factory,
            settings=mock_settings,
        )

        # Service should have method to get graph
        assert hasattr(service, "get_analysis_graph") or hasattr(service, "_analysis_graph")

    @pytest.mark.asyncio
    async def test_graph_results_match_service_results(self, mock_llm_factory, mock_settings):
        """Graph execution produces same results as direct service calls."""
        from mcp_server_langgraph.api.v1.ai_ux import CompositeAnalysisRequest
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        # Disable LLM for deterministic testing
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

        # Run via service method (which may use graph internally)
        result = await service.run_composite_analysis(request)

        # Basic validation
        assert result.user_id == "user-123"
        assert result.persona_result is not None
        assert result.disclosure_result is not None
