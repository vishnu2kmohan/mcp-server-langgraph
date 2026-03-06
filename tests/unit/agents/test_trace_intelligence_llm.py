"""
TDD: Unit tests for Trace Intelligence LLM Integration.

Tests that AIUXService trace intelligence methods use real LLM calls
when llm_factory is configured, with fallback to heuristics.

Sprint 2: Trace Intelligence
- summarize_trace() uses LLM to generate trace summaries
- detect_trace_anomalies() uses LLM to find bottlenecks

RED phase: These tests define expected behavior before implementation.
"""

import gc
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.agents, pytest.mark.trace_intelligence]


# =============================================================================
# LLM Integration Tests for summarize_trace
# =============================================================================


class TestTraceSummarizeLLM:
    """Test summarize_trace LLM integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_summarize_trace_calls_llm_when_enabled(self) -> None:
        """GIVEN LLM factory configured WHEN summarize_trace called THEN uses LLM."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        # Mock LLM factory with a proper response
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = """
        {
            "summary": "Agent executed 5-step workflow for data processing",
            "total_duration_ms": 2500,
            "step_count": 5,
            "tool_call_count": 3,
            "success": true,
            "key_actions": ["Fetched data", "Processed records", "Saved results"],
            "confidence": 0.88
        }
        """
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        # Mock settings
        mock_settings = MagicMock()
        mock_settings.ff_enable_ai_suggestions = True
        mock_settings.ff_enable_trace_intelligence = True

        service = AIUXService(llm_factory=mock_llm, settings=mock_settings)

        result = await service.summarize_trace(trace_id="trace-123", user_id="user-1")

        # Verify LLM was called
        mock_llm.ainvoke.assert_called_once()

        # Verify result structure
        assert "summary" in result
        assert result["summary"] != "Agent completed workflow trace trace-12... with multiple tool calls"
        assert "step_count" in result
        assert "success" in result

    @pytest.mark.asyncio
    async def test_summarize_trace_fallback_when_llm_disabled(self) -> None:
        """GIVEN LLM factory not configured WHEN summarize_trace THEN returns fallback."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        # Mock settings without LLM
        mock_settings = MagicMock()
        mock_settings.ff_enable_ai_suggestions = False

        service = AIUXService(llm_factory=None, settings=mock_settings)

        result = await service.summarize_trace(trace_id="trace-123", user_id="user-1")

        # Verify fallback response (placeholder)
        assert "summary" in result
        assert "step_count" in result

    @pytest.mark.asyncio
    async def test_summarize_trace_fallback_on_llm_error(self) -> None:
        """GIVEN LLM call fails WHEN summarize_trace THEN returns fallback."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        # Mock LLM that raises exception
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(side_effect=Exception("LLM timeout"))

        mock_settings = MagicMock()
        mock_settings.ff_enable_ai_suggestions = True
        mock_settings.ff_enable_trace_intelligence = True

        service = AIUXService(llm_factory=mock_llm, settings=mock_settings)

        result = await service.summarize_trace(trace_id="trace-123", user_id="user-1")

        # Should not raise, should return fallback
        assert "summary" in result

    @pytest.mark.asyncio
    async def test_summarize_trace_parses_llm_response(self) -> None:
        """GIVEN valid LLM JSON response WHEN summarize_trace THEN parses correctly."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = """
        {
            "summary": "Completed API integration workflow",
            "total_duration_ms": 1500,
            "step_count": 3,
            "tool_call_count": 2,
            "success": true,
            "key_actions": ["Called external API", "Parsed response"],
            "confidence": 0.92
        }
        """
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        mock_settings = MagicMock()
        mock_settings.ff_enable_ai_suggestions = True
        mock_settings.ff_enable_trace_intelligence = True

        service = AIUXService(llm_factory=mock_llm, settings=mock_settings)

        result = await service.summarize_trace(trace_id="trace-456", user_id="user-1")

        assert result["summary"] == "Completed API integration workflow"
        assert result["step_count"] == 3
        assert result["success"] is True


# =============================================================================
# LLM Integration Tests for detect_trace_anomalies
# =============================================================================


class TestTraceAnomaliesLLM:
    """Test detect_trace_anomalies LLM integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_detect_anomalies_calls_llm_when_enabled(self) -> None:
        """GIVEN LLM factory configured WHEN detect_trace_anomalies called THEN uses LLM."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = """
        {
            "anomalies": [
                {"type": "timeout", "description": "Step 3 exceeded timeout threshold", "severity": "warning"}
            ],
            "bottlenecks": [
                {"step": "data_fetch", "duration_ms": 1500, "recommendation": "Add caching"}
            ],
            "health_score": 0.75,
            "optimization_suggestions": [
                "Consider parallel execution for independent steps",
                "Add retry logic for flaky API calls"
            ]
        }
        """
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        mock_settings = MagicMock()
        mock_settings.ff_enable_ai_suggestions = True
        mock_settings.ff_enable_trace_intelligence = True

        service = AIUXService(llm_factory=mock_llm, settings=mock_settings)

        result = await service.detect_trace_anomalies(trace_id="trace-789", user_id="user-1")

        # Verify LLM was called
        mock_llm.ainvoke.assert_called_once()

        # Verify result structure
        assert "anomalies" in result
        assert "bottlenecks" in result
        assert "health_score" in result
        assert len(result["anomalies"]) == 1

    @pytest.mark.asyncio
    async def test_detect_anomalies_fallback_when_llm_disabled(self) -> None:
        """GIVEN LLM factory not configured WHEN detect_trace_anomalies THEN returns fallback."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        mock_settings = MagicMock()
        mock_settings.ff_enable_ai_suggestions = False

        service = AIUXService(llm_factory=None, settings=mock_settings)

        result = await service.detect_trace_anomalies(trace_id="trace-789", user_id="user-1")

        # Verify fallback response
        assert "anomalies" in result
        assert "bottlenecks" in result
        assert "health_score" in result

    @pytest.mark.asyncio
    async def test_detect_anomalies_handles_malformed_response(self) -> None:
        """GIVEN LLM returns malformed JSON WHEN detect_trace_anomalies THEN returns fallback."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Not valid JSON"
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        mock_settings = MagicMock()
        mock_settings.ff_enable_ai_suggestions = True
        mock_settings.ff_enable_trace_intelligence = True

        service = AIUXService(llm_factory=mock_llm, settings=mock_settings)

        result = await service.detect_trace_anomalies(trace_id="trace-789", user_id="user-1")

        # Should not raise, should return fallback
        assert "anomalies" in result
        assert "health_score" in result


# =============================================================================
# Feature Flag Tests
# =============================================================================


class TestTraceIntelligenceFeatureFlags:
    """Test feature flag gating for trace intelligence LLM calls."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_trace_intelligence_requires_feature_flag(self) -> None:
        """GIVEN feature flag disabled WHEN trace method called THEN uses fallback."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "{}"
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        mock_settings = MagicMock()
        mock_settings.ff_enable_ai_suggestions = True
        mock_settings.ff_enable_trace_intelligence = False  # Disabled

        service = AIUXService(llm_factory=mock_llm, settings=mock_settings)

        result = await service.summarize_trace(trace_id="t1", user_id="u1")

        # LLM should NOT be called when feature flag is disabled
        mock_llm.ainvoke.assert_not_called()

        # Should still return valid structure (fallback)
        assert "summary" in result
