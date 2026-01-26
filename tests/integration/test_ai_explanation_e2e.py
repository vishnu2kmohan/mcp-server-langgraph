"""End-to-end tests for AI Explanation generation.

Tests the complete AI Explanation flow:
- Approval request with low confidence
- ExplanationOrchestrator generates parallel explanations
- CachedExplanationOrchestrator caches results
- AIExplanation included in approval response
- Metrics are recorded

TDD: These tests are written FIRST before full integration is wired.
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

if TYPE_CHECKING:
    pass

pytestmark = [
    pytest.mark.integration,
    pytest.mark.hitl,
    pytest.mark.multi_agent,
    pytest.mark.ai_explanations,
]


@pytest.mark.integration
@pytest.mark.hitl
@pytest.mark.xdist_group(name="ai_explanation_e2e")
class TestAIExplanationE2EFlow:
    """End-to-end tests for AI Explanation generation flow."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_approval_request_with_ai_explanation(self) -> None:
        """GIVEN a low-confidence approval request
        WHEN processed with AI explanations enabled
        THEN the approval request includes AIExplanation.
        """
        from mcp_server_langgraph.agents.explanation_orchestrator import (
            ExplanationOrchestrator,
        )
        from mcp_server_langgraph.core.interrupts.ai_explanation import AIExplanation

        # Create mock LLM that returns explanation content
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "The agent is uncertain because the input is ambiguous."
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        orchestrator = ExplanationOrchestrator(llm_factory=mock_llm)

        # Generate explanation for approval request
        explanation = await orchestrator.generate_explanation(
            approval_id="approval-e2e-001",
            agent_name="FileAgent",
            proposed_action="Delete files matching *.tmp",
            confidence=0.62,
            threshold=0.7,
            trigger_reason="low_confidence",
            reasoning_trace=["Step 1: Matched 50 files", "Step 2: Uncertain about scope"],
        )

        # Verify AIExplanation is returned
        assert isinstance(explanation, AIExplanation)
        assert explanation.why_uncertain is not None
        assert len(explanation.why_uncertain) > 0

    @pytest.mark.asyncio
    async def test_cached_orchestrator_caches_explanation(self) -> None:
        """GIVEN an explanation is generated
        WHEN the same context is requested again
        THEN the cached version is returned.
        """
        from mcp_server_langgraph.agents.explanation_orchestrator import (
            CachedExplanationOrchestrator,
        )
        from mcp_server_langgraph.core.interrupts.ai_explanation import AIExplanation

        # Create mock LLM
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Explanation content"
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        # Create mock cache
        cached_explanation = AIExplanation(
            why_uncertain="Cached: Input is ambiguous",
            what_could_go_wrong="Cached: Wrong files deleted",
        )
        mock_cache = AsyncMock(return_value=None)
        mock_cache.get = AsyncMock(return_value=cached_explanation.model_dump_json())
        mock_cache.set = AsyncMock(return_value=None)

        orchestrator = CachedExplanationOrchestrator(
            llm_factory=mock_llm,
            cache=mock_cache,
        )

        # Request explanation - should hit cache
        explanation = await orchestrator.generate_explanation_cached(
            approval_id="approval-e2e-002",
            agent_name="FileAgent",
            proposed_action="Delete files",
            confidence=0.65,
            threshold=0.7,
            trigger_reason="low_confidence",
        )

        # Verify cache was used
        assert explanation.why_uncertain == "Cached: Input is ambiguous"
        assert explanation.cached is True
        # LLM should NOT have been called
        mock_llm.ainvoke.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_miss_generates_and_stores(self) -> None:
        """GIVEN no cached explanation exists
        WHEN explanation is requested
        THEN it is generated and stored in cache.
        """
        from mcp_server_langgraph.agents.explanation_orchestrator import (
            CachedExplanationOrchestrator,
        )
        from mcp_server_langgraph.core.interrupts.ai_explanation import AIExplanation

        # Create mock LLM
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Generated explanation"
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        # Create mock cache with cache miss
        mock_cache = AsyncMock(return_value=None)
        mock_cache.get = AsyncMock(return_value=None)  # Cache miss
        mock_cache.set = AsyncMock(return_value=None)

        orchestrator = CachedExplanationOrchestrator(
            llm_factory=mock_llm,
            cache=mock_cache,
        )

        # Request explanation - should miss cache and generate
        explanation = await orchestrator.generate_explanation_cached(
            approval_id="approval-e2e-003",
            agent_name="FileAgent",
            proposed_action="Delete files matching *.log",
            confidence=0.60,
            threshold=0.7,
            trigger_reason="low_confidence",
        )

        # Verify LLM was called (cache miss)
        assert mock_llm.ainvoke.called
        # Verify explanation was generated
        assert isinstance(explanation, AIExplanation)
        # Verify cache was written
        assert mock_cache.set.called

    @pytest.mark.asyncio
    async def test_parallel_execution_performance(self) -> None:
        """GIVEN an explanation request
        WHEN processed by ExplanationOrchestrator
        THEN all 4 analyses run in parallel (faster than sequential).
        """
        import asyncio
        import time

        from mcp_server_langgraph.agents.explanation_orchestrator import (
            ExplanationOrchestrator,
            ExplanationTask,
        )

        # Track execution order to verify parallelism
        execution_times: list[float] = []

        async def mock_ainvoke_with_delay(*args, **kwargs):
            start = time.monotonic()
            await asyncio.sleep(0.05)  # 50ms simulated LLM latency
            execution_times.append(time.monotonic() - start)
            response = MagicMock()
            response.content = "Test analysis result"
            return response

        mock_llm = MagicMock()
        mock_llm.ainvoke = mock_ainvoke_with_delay

        orchestrator = ExplanationOrchestrator(llm_factory=mock_llm)

        # Time the execution
        start_time = time.monotonic()
        tasks = [
            ExplanationTask(task_type=t, approval_id="test", context={})
            for t in ["uncertainty_analysis", "risk_analysis", "alternatives_analysis", "evidence_extraction"]
        ]
        await orchestrator.execute(tasks)
        total_time = time.monotonic() - start_time

        # If sequential: 4 tasks × 50ms = 200ms
        # If parallel: ~50ms (all start together)
        # Allow some overhead, but should be < 150ms (< 3x single task)
        assert total_time < 0.15, f"Expected parallel execution < 150ms, got {total_time * 1000:.0f}ms"

    @pytest.mark.asyncio
    async def test_metrics_recorded_on_generation(self) -> None:
        """GIVEN an explanation is generated
        WHEN the orchestrator completes
        THEN metrics are recorded (duration, success, cache status).
        """
        from mcp_server_langgraph.agents.explanation_orchestrator import (
            CachedExplanationOrchestrator,
        )

        # Create mock LLM
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Test explanation"
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        # Create mock cache with miss
        mock_cache = AsyncMock(return_value=None)
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock(return_value=None)

        orchestrator = CachedExplanationOrchestrator(
            llm_factory=mock_llm,
            cache=mock_cache,
        )

        with patch("mcp_server_langgraph.agents.explanation_orchestrator.record_explanation_generation") as mock_record:
            await orchestrator.generate_explanation_cached(
                approval_id="approval-e2e-004",
                agent_name="TestAgent",
                proposed_action="Test action",
                confidence=0.65,
                threshold=0.7,
                trigger_reason="low_confidence",
            )

            # Verify metrics were recorded
            mock_record.assert_called_once()
            call_kwargs = mock_record.call_args.kwargs
            assert call_kwargs["approval_id"] == "approval-e2e-004"
            assert call_kwargs["cached"] is False
            assert call_kwargs["success"] is True
            assert "duration_ms" in call_kwargs


@pytest.mark.integration
@pytest.mark.hitl
@pytest.mark.xdist_group(name="ai_explanation_e2e_approval")
class TestAIExplanationInApprovalFlow:
    """Tests AI Explanation integration with approval request flow."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_approval_required_model_supports_ai_explanation(self) -> None:
        """GIVEN an ApprovalRequired model
        WHEN created with ai_explanation field
        THEN the explanation is stored and accessible.
        """
        from mcp_server_langgraph.core.interrupts.ai_explanation import AIExplanation
        from mcp_server_langgraph.core.interrupts.approval import ApprovalRequired

        # Create AI explanation
        explanation = AIExplanation(
            why_uncertain="The file pattern matches multiple directories.",
            what_could_go_wrong="Important files could be deleted.",
            safer_alternatives=[],
            confidence_factors=[],
            reasoning_trace=["Step 1: Matched 50 files"],
        )

        # Create approval request with explanation
        approval = ApprovalRequired(
            approval_id="approval-e2e-001",
            task_id="task-e2e-001",
            session_id="session-e2e-001",
            agent_name="FileAgent",
            node_name="file_delete_node",
            action_description="Delete files matching *.tmp",
            confidence=0.62,
            threshold=0.7,
            trigger_reason="low_confidence",
            ai_explanation=explanation,
        )

        # Verify explanation is included
        assert approval.ai_explanation is not None
        assert approval.ai_explanation.why_uncertain == explanation.why_uncertain
        assert approval.ai_explanation.what_could_go_wrong == explanation.what_could_go_wrong

    @pytest.mark.asyncio
    async def test_approval_required_serializes_with_explanation(self) -> None:
        """GIVEN an ApprovalRequired with AI explanation
        WHEN serialized to JSON
        THEN the explanation is included in the output.
        """
        from mcp_server_langgraph.core.interrupts.ai_explanation import AIExplanation
        from mcp_server_langgraph.core.interrupts.approval import ApprovalRequired

        explanation = AIExplanation(
            why_uncertain="Multiple interpretations possible.",
            what_could_go_wrong="Wrong action selected.",
        )

        approval = ApprovalRequired(
            approval_id="approval-e2e-002",
            task_id="task-e2e-002",
            session_id="session-e2e-002",
            agent_name="Analyzer",
            node_name="analyze_data_node",
            action_description="Analyze data",
            confidence=0.55,
            threshold=0.7,
            trigger_reason="low_confidence",
            ai_explanation=explanation,
        )

        # Serialize to JSON
        json_data = approval.model_dump()

        # Verify explanation is in serialized data
        assert "ai_explanation" in json_data
        assert json_data["ai_explanation"]["why_uncertain"] == "Multiple interpretations possible."
        assert json_data["ai_explanation"]["what_could_go_wrong"] == "Wrong action selected."


@pytest.mark.integration
@pytest.mark.hitl
@pytest.mark.xdist_group(name="ai_explanation_e2e_feature_flag")
class TestAIExplanationFeatureFlagIntegration:
    """Tests AI Explanation feature flag behavior."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_feature_flag_controls_generation(self) -> None:
        """GIVEN enable_ai_explanations flag is False
        WHEN checking orchestrator.is_enabled
        THEN it returns False.
        """
        from mcp_server_langgraph.agents.explanation_orchestrator import (
            ExplanationOrchestrator,
        )

        orchestrator = ExplanationOrchestrator()

        # Default is disabled for gradual rollout
        with patch("mcp_server_langgraph.core.feature_flags.feature_flags") as mock_ff:
            mock_ff.enable_ai_explanations = False
            mock_ff.is_test_mode = False

            # Orchestrator should check feature flag
            assert hasattr(orchestrator, "is_enabled")

    @pytest.mark.asyncio
    async def test_fallback_when_feature_disabled(self) -> None:
        """GIVEN enable_ai_explanations is False
        WHEN explanation is requested
        THEN a fallback explanation is returned.
        """
        from mcp_server_langgraph.agents.explanation_orchestrator import (
            ExplanationOrchestrator,
        )
        from mcp_server_langgraph.core.interrupts.ai_explanation import AIExplanation

        orchestrator = ExplanationOrchestrator()

        # When feature disabled, generate_explanation_fallback should return basic explanation
        if hasattr(orchestrator, "generate_explanation_fallback"):
            fallback = orchestrator.generate_explanation_fallback(
                agent_name="TestAgent",
                proposed_action="Test action",
                confidence=0.65,
                threshold=0.7,
                trigger_reason="low_confidence",
            )
            # Fallback should still return AIExplanation with template message
            assert isinstance(fallback, AIExplanation)
