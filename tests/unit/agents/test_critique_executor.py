"""Tests for CritiqueExecutor - Multi-pass executor+critic pattern.

TDD: These tests define the contract for the critique execution loop.
The executor generates a response, the critic reviews it, and the
executor refines based on feedback for N rounds.

PYTEST-XDIST FIX: Uses gc.collect() in teardown for memory safety.
"""

from __future__ import annotations

import gc
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="critique_executor")
class TestCritiqueResult:
    """Tests for CritiqueResult dataclass."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_critique_result_approved_no_feedback(self) -> None:
        """GIVEN an approved critique
        WHEN CritiqueResult is created
        THEN approved is True and feedback is None
        """
        from mcp_server_langgraph.agents.critique_executor import CritiqueResult

        result = CritiqueResult(
            approved=True,
            feedback=None,
            refinement_suggestions=[],
            confidence=0.95,
        )

        assert result.approved is True
        assert result.feedback is None
        assert result.refinement_suggestions == []
        assert result.confidence == 0.95

    def test_critique_result_rejected_with_feedback(self) -> None:
        """GIVEN a rejected critique with feedback
        WHEN CritiqueResult is created
        THEN approved is False and feedback contains suggestions
        """
        from mcp_server_langgraph.agents.critique_executor import CritiqueResult

        result = CritiqueResult(
            approved=False,
            feedback="The response lacks specificity",
            refinement_suggestions=["Add concrete examples", "Include metrics"],
            confidence=0.7,
        )

        assert result.approved is False
        assert result.feedback == "The response lacks specificity"
        assert len(result.refinement_suggestions) == 2
        assert result.confidence == 0.7


@pytest.mark.unit
@pytest.mark.xdist_group(name="critique_executor")
class TestCritiqueExecutor:
    """Tests for CritiqueExecutor multi-pass loop."""

    @pytest.fixture(autouse=True)
    def _isolate_otel(self):
        """Isolate OTEL instruments from global state contamination in xdist workers.

        Module-level OTEL instruments (tracer, counters, histograms) can become stale
        when another test in the same worker shuts down the meter/tracer provider.
        Patching them ensures tests don't depend on global OTEL lifecycle.
        """
        with (
            patch("mcp_server_langgraph.agents.critique_executor.tracer", MagicMock()),
            patch("mcp_server_langgraph.agents.critique_executor.critique_rounds_counter", MagicMock()),
            patch("mcp_server_langgraph.agents.critique_executor.critique_latency_histogram", MagicMock()),
            patch("mcp_server_langgraph.agents.critique_executor.critique_approval_counter", MagicMock()),
        ):
            yield

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_execute_without_critic_returns_single_response(self) -> None:
        """GIVEN no critic model configured
        WHEN execute_with_critique is called
        THEN only the executor response is yielded (no critique rounds)
        """
        from mcp_server_langgraph.agents.critique_executor import CritiqueExecutor

        # Create a mock LLM instance that will be returned when LLMFactory is instantiated
        mock_llm_instance = MagicMock()
        mock_llm_instance.ainvoke = AsyncMock(return_value=MagicMock(content="Executor response"))

        # Mock the LLMFactory class to return our mock instance when instantiated
        mock_llm_factory_class = MagicMock(return_value=mock_llm_instance)

        with patch(
            "mcp_server_langgraph.agents.critique_executor.LLMFactory",
            mock_llm_factory_class,
        ):
            executor = CritiqueExecutor(
                executor_model="gemini-3-flash",
                critic_model=None,  # No critic
                max_rounds=3,
            )

            events = []
            async for event in executor.execute_with_critique(
                messages=[{"role": "user", "content": "Hello"}],
                critique_rounds=0,
            ):
                events.append(event)

        # Should have exactly one response event
        assert len(events) == 1
        assert events[0]["type"] == "executor_response"
        assert events[0]["round"] == 0

    @pytest.mark.asyncio
    async def test_execute_with_critique_approved_first_round(self) -> None:
        """GIVEN critic approves on first round
        WHEN execute_with_critique is called with critique_rounds=2
        THEN executor + critique events are yielded, no refinement
        """
        from mcp_server_langgraph.agents.critique_executor import (
            CritiqueExecutor,
        )

        # Create mock LLM instances
        mock_executor_instance = MagicMock()
        mock_executor_instance.ainvoke = AsyncMock(return_value=MagicMock(content="Good response"))

        mock_critic_instance = MagicMock()
        mock_critic_instance.ainvoke = AsyncMock(
            return_value=MagicMock(content='{"approved": true, "feedback": null, "suggestions": [], "confidence": 0.95}')
        )

        # LLMFactory class mock returns different instances based on model_name
        def create_llm_instance(model_name: str = None, **kwargs: Any):
            if model_name and ("critic" in model_name.lower() or "claude" in model_name.lower()):
                return mock_critic_instance
            return mock_executor_instance

        mock_llm_factory_class = MagicMock(side_effect=create_llm_instance)

        with patch(
            "mcp_server_langgraph.agents.critique_executor.LLMFactory",
            mock_llm_factory_class,
        ):
            executor = CritiqueExecutor(
                executor_model="gemini-3-flash",
                critic_model="claude-haiku",
                max_rounds=3,
            )

            events = []
            async for event in executor.execute_with_critique(
                messages=[{"role": "user", "content": "Hello"}],
                critique_rounds=2,
            ):
                events.append(event)

        # Should have: executor_response (round 0) + critique (round 1)
        assert len(events) == 2
        assert events[0]["type"] == "executor_response"
        assert events[0]["round"] == 0
        assert events[1]["type"] == "critique"
        assert events[1]["round"] == 1
        assert events[1]["result"].approved is True

    @pytest.mark.asyncio
    async def test_execute_with_critique_refines_on_rejection(self) -> None:
        """GIVEN critic rejects first response
        WHEN execute_with_critique is called
        THEN executor refines based on feedback
        """
        from mcp_server_langgraph.agents.critique_executor import CritiqueExecutor

        # Track call count for executor
        executor_call_count = [0]

        async def mock_executor_invoke(*args: Any, **kwargs: Any):
            executor_call_count[0] += 1
            if executor_call_count[0] == 1:
                return MagicMock(content="Initial response")
            return MagicMock(content="Refined response with examples")

        mock_executor_instance = MagicMock()
        mock_executor_instance.ainvoke = AsyncMock(side_effect=mock_executor_invoke)

        # Track call count for critic
        critic_call_count = [0]

        async def mock_critic_invoke(*args: Any, **kwargs: Any):
            critic_call_count[0] += 1
            if critic_call_count[0] == 1:
                # First critique: reject
                return MagicMock(
                    content='{"approved": false, "feedback": "Add examples", "suggestions": ["Include code samples"], "confidence": 0.6}'
                )
            # Second critique: approve
            return MagicMock(content='{"approved": true, "feedback": null, "suggestions": [], "confidence": 0.9}')

        mock_critic_instance = MagicMock()
        mock_critic_instance.ainvoke = AsyncMock(side_effect=mock_critic_invoke)

        def create_llm_instance(model_name: str = None, **kwargs: Any):
            if model_name and "claude" in model_name.lower():
                return mock_critic_instance
            return mock_executor_instance

        mock_llm_factory_class = MagicMock(side_effect=create_llm_instance)

        with patch(
            "mcp_server_langgraph.agents.critique_executor.LLMFactory",
            mock_llm_factory_class,
        ):
            executor = CritiqueExecutor(
                executor_model="gemini-3-flash",
                critic_model="claude-haiku",
                max_rounds=3,
            )

            events = []
            async for event in executor.execute_with_critique(
                messages=[{"role": "user", "content": "Hello"}],
                critique_rounds=2,
            ):
                events.append(event)

        # Should have: executor(0) -> critique(1,reject) -> refined(1) -> critique(2,approve)
        assert len(events) == 4
        assert events[0]["type"] == "executor_response"
        assert events[1]["type"] == "critique"
        assert events[1]["result"].approved is False
        assert events[2]["type"] == "refined_response"
        assert events[3]["type"] == "critique"
        assert events[3]["result"].approved is True

    @pytest.mark.asyncio
    async def test_execute_respects_max_rounds(self) -> None:
        """GIVEN critic never approves
        WHEN execute_with_critique is called
        THEN loop stops after max_rounds
        """
        from mcp_server_langgraph.agents.critique_executor import CritiqueExecutor

        mock_executor_instance = MagicMock()
        mock_executor_instance.ainvoke = AsyncMock(return_value=MagicMock(content="Response"))

        mock_critic_instance = MagicMock()
        # Critic always rejects
        mock_critic_instance.ainvoke = AsyncMock(
            return_value=MagicMock(
                content='{"approved": false, "feedback": "Still not good", "suggestions": [], "confidence": 0.5}'
            )
        )

        def create_llm_instance(model_name: str = None, **kwargs: Any):
            if model_name and "claude" in model_name.lower():
                return mock_critic_instance
            return mock_executor_instance

        mock_llm_factory_class = MagicMock(side_effect=create_llm_instance)

        with patch(
            "mcp_server_langgraph.agents.critique_executor.LLMFactory",
            mock_llm_factory_class,
        ):
            executor = CritiqueExecutor(
                executor_model="gemini-3-flash",
                critic_model="claude-haiku",
                max_rounds=2,  # Limit to 2 rounds
            )

            events = []
            async for event in executor.execute_with_critique(
                messages=[{"role": "user", "content": "Hello"}],
                critique_rounds=5,  # Request 5, but max is 2
            ):
                events.append(event)

        # Count critique events - should be limited to max_rounds
        critique_events = [e for e in events if e["type"] == "critique"]
        assert len(critique_events) <= 2

    @pytest.mark.asyncio
    async def test_execute_emits_otel_spans(self) -> None:
        """GIVEN OTEL tracing is enabled
        WHEN execute_with_critique is called
        THEN spans are created for each phase
        """
        from mcp_server_langgraph.agents.critique_executor import CritiqueExecutor

        mock_llm_instance = MagicMock()
        mock_llm_instance.ainvoke = AsyncMock(return_value=MagicMock(content="Response"))
        mock_llm_factory_class = MagicMock(return_value=mock_llm_instance)

        mock_tracer = MagicMock()
        mock_span = MagicMock()
        mock_span.__enter__ = MagicMock(return_value=mock_span)
        mock_span.__exit__ = MagicMock(return_value=None)
        mock_tracer.start_as_current_span.return_value = mock_span

        with (
            patch(
                "mcp_server_langgraph.agents.critique_executor.LLMFactory",
                mock_llm_factory_class,
            ),
            patch(
                "mcp_server_langgraph.agents.critique_executor.tracer",
                mock_tracer,
            ),
        ):
            executor = CritiqueExecutor(
                executor_model="gemini-3-flash",
                critic_model=None,
                max_rounds=3,
            )

            events = []
            async for event in executor.execute_with_critique(
                messages=[{"role": "user", "content": "Hello"}],
                critique_rounds=0,
            ):
                events.append(event)

        # Verify OTEL span was created
        mock_tracer.start_as_current_span.assert_called()


@pytest.mark.unit
@pytest.mark.xdist_group(name="critique_executor")
class TestCritiqueExecutorMetrics:
    """Tests for OTEL metrics emission."""

    @pytest.fixture(autouse=True)
    def _isolate_otel(self):
        """Isolate OTEL instruments from global state contamination in xdist workers."""
        with (
            patch("mcp_server_langgraph.agents.critique_executor.tracer", MagicMock()),
            patch("mcp_server_langgraph.agents.critique_executor.critique_rounds_counter", MagicMock()),
            patch("mcp_server_langgraph.agents.critique_executor.critique_latency_histogram", MagicMock()),
            patch("mcp_server_langgraph.agents.critique_executor.critique_approval_counter", MagicMock()),
        ):
            yield

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_records_critique_round_count_metric(self) -> None:
        """GIVEN critique loop completes
        WHEN metrics are recorded
        THEN critique_rounds_total counter is incremented
        """
        from mcp_server_langgraph.agents.critique_executor import CritiqueExecutor

        mock_executor_instance = MagicMock()
        mock_executor_instance.ainvoke = AsyncMock(return_value=MagicMock(content="Response"))

        mock_critic_instance = MagicMock()
        mock_critic_instance.ainvoke = AsyncMock(
            return_value=MagicMock(content='{"approved": true, "feedback": null, "suggestions": [], "confidence": 0.9}')
        )

        def create_llm_instance(model_name: str = None, **kwargs: Any):
            if model_name and "claude" in model_name.lower():
                return mock_critic_instance
            return mock_executor_instance

        mock_llm_factory_class = MagicMock(side_effect=create_llm_instance)

        mock_counter = MagicMock()

        with (
            patch(
                "mcp_server_langgraph.agents.critique_executor.LLMFactory",
                mock_llm_factory_class,
            ),
            patch(
                "mcp_server_langgraph.agents.critique_executor.critique_rounds_counter",
                mock_counter,
            ),
        ):
            executor = CritiqueExecutor(
                executor_model="gemini-3-flash",
                critic_model="claude-haiku",
                max_rounds=3,
            )

            async for _ in executor.execute_with_critique(
                messages=[{"role": "user", "content": "Hello"}],
                critique_rounds=1,
            ):
                pass

        # Verify metric was recorded
        mock_counter.add.assert_called()

    @pytest.mark.asyncio
    async def test_records_critique_latency_histogram(self) -> None:
        """GIVEN critique loop completes
        WHEN metrics are recorded
        THEN critique_latency_seconds histogram is recorded
        """
        from mcp_server_langgraph.agents.critique_executor import CritiqueExecutor

        # Create a mock LLM instance that will be returned when LLMFactory is instantiated
        mock_llm_instance = MagicMock()
        mock_llm_instance.ainvoke = AsyncMock(return_value=MagicMock(content="Response"))

        # Mock the LLMFactory class to return our mock instance when instantiated
        mock_llm_factory_class = MagicMock(return_value=mock_llm_instance)

        mock_histogram = MagicMock()

        with (
            patch(
                "mcp_server_langgraph.agents.critique_executor.LLMFactory",
                mock_llm_factory_class,
            ),
            patch(
                "mcp_server_langgraph.agents.critique_executor.critique_latency_histogram",
                mock_histogram,
            ),
        ):
            executor = CritiqueExecutor(
                executor_model="gemini-3-flash",
                critic_model=None,
                max_rounds=3,
            )

            async for _ in executor.execute_with_critique(
                messages=[{"role": "user", "content": "Hello"}],
                critique_rounds=0,
            ):
                pass

        # Verify histogram was recorded
        mock_histogram.record.assert_called()
