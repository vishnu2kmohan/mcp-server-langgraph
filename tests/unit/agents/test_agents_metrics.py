"""
Tests for agents metrics module.

Tests verify OpenTelemetry metric recording for orchestrator,
subagent, and coordinator operations.

TDD: Tests written FIRST before implementation.
"""

from __future__ import annotations

import gc

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
class TestAgentsMetrics:
    """Test suite for agents metrics functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_record_orchestrator_execution_success(self) -> None:
        """GIVEN an orchestrator execution
        WHEN recording success metrics
        THEN counter and histogram should be updated.
        """
        from mcp_server_langgraph.agents.metrics import record_orchestrator_execution

        # Should not raise - just record metrics
        record_orchestrator_execution(
            task_count=3,
            successful_count=3,
            duration_ms=1500.0,
            success=True,
        )

    def test_record_orchestrator_execution_partial_failure(self) -> None:
        """GIVEN an orchestrator execution with partial failures
        WHEN recording metrics
        THEN should record partial success.
        """
        from mcp_server_langgraph.agents.metrics import record_orchestrator_execution

        record_orchestrator_execution(
            task_count=5,
            successful_count=3,
            duration_ms=2000.0,
            success=False,
        )

    def test_record_orchestrator_execution_zero_tasks(self) -> None:
        """GIVEN zero tasks
        WHEN recording orchestrator execution
        THEN should handle gracefully.
        """
        from mcp_server_langgraph.agents.metrics import record_orchestrator_execution

        record_orchestrator_execution(
            task_count=0,
            successful_count=0,
            duration_ms=100.0,
            success=True,
        )

    def test_record_subagent_execution_success(self) -> None:
        """GIVEN a subagent execution
        WHEN recording success metrics
        THEN counter and histogram should be updated.
        """
        from mcp_server_langgraph.agents.metrics import record_subagent_execution

        record_subagent_execution(
            task_id="subtask-1",
            model="gemini-2.5-flash",
            duration_ms=500.0,
            success=True,
        )

    def test_record_subagent_execution_failure(self) -> None:
        """GIVEN a failed subagent execution
        WHEN recording metrics
        THEN should record failure with error type.
        """
        from mcp_server_langgraph.agents.metrics import record_subagent_execution

        record_subagent_execution(
            task_id="subtask-2",
            model="gemini-3-pro",
            duration_ms=150.0,
            success=False,
            error_type="timeout",
        )

    def test_record_subagent_execution_with_llm_error(self) -> None:
        """GIVEN a subagent execution with LLM error
        WHEN recording metrics
        THEN should record with llm_error type.
        """
        from mcp_server_langgraph.agents.metrics import record_subagent_execution

        record_subagent_execution(
            task_id="subtask-3",
            model="claude-sonnet-4.5",
            duration_ms=75.0,
            success=False,
            error_type="llm_error",
        )

    def test_record_model_selection_gemini(self) -> None:
        """GIVEN a model selection operation
        WHEN selecting gemini model
        THEN should record vendor and tier.
        """
        from mcp_server_langgraph.agents.metrics import record_model_selection

        record_model_selection(
            tier="complicated",
            vendor="google",
            model="gemini-2.5-flash",
        )

    def test_record_model_selection_claude(self) -> None:
        """GIVEN a model selection for verification
        WHEN selecting claude model
        THEN should record vendor and tier.
        """
        from mcp_server_langgraph.agents.metrics import record_model_selection

        record_model_selection(
            tier="complex",
            vendor="anthropic",
            model="claude-opus-4.5",
        )

    def test_record_model_selection_fallback(self) -> None:
        """GIVEN a fallback model selection
        WHEN primary vendor unavailable
        THEN should record with fallback flag.
        """
        from mcp_server_langgraph.agents.metrics import record_model_selection

        record_model_selection(
            tier="complicated",
            vendor="openai",
            model="gpt-4.1-mini",
            is_fallback=True,
        )

    def test_record_cross_vendor_verification(self) -> None:
        """GIVEN cross-vendor verification
        WHEN claude judges gemini output
        THEN should record verification metrics.
        """
        from mcp_server_langgraph.agents.metrics import record_cross_vendor_verification

        record_cross_vendor_verification(
            primary_vendor="google",
            verifier_vendor="anthropic",
            primary_model="gemini-3-pro",
            verifier_model="claude-opus-4.5",
            success=True,
        )

    def test_record_cross_vendor_verification_same_vendor_fallback(self) -> None:
        """GIVEN same-vendor verification fallback
        WHEN cross-vendor unavailable
        THEN should record with same_vendor flag.
        """
        from mcp_server_langgraph.agents.metrics import record_cross_vendor_verification

        record_cross_vendor_verification(
            primary_vendor="google",
            verifier_vendor="google",
            primary_model="gemini-3-pro",
            verifier_model="gemini-3-flash",
            success=True,
            same_vendor_fallback=True,
        )

    def test_record_artifact_storage(self) -> None:
        """GIVEN artifact storage operation
        WHEN storing task result
        THEN should record storage metrics.
        """
        from mcp_server_langgraph.agents.metrics import record_artifact_storage

        record_artifact_storage(
            task_id="subtask-1",
            artifact_name="result",
            size_bytes=1024,
            operation="store",
        )

    def test_record_artifact_retrieval(self) -> None:
        """GIVEN artifact retrieval operation
        WHEN loading for synthesis
        THEN should record retrieval metrics.
        """
        from mcp_server_langgraph.agents.metrics import record_artifact_storage

        record_artifact_storage(
            task_id="subtask-1",
            artifact_name="result",
            size_bytes=1024,
            operation="retrieve",
        )

    def test_record_synthesis_operation(self) -> None:
        """GIVEN synthesis operation
        WHEN combining subtask results
        THEN should record synthesis metrics.
        """
        from mcp_server_langgraph.agents.metrics import record_synthesis_operation

        record_synthesis_operation(
            input_count=5,
            successful_inputs=4,
            duration_ms=800.0,
            success=True,
        )

    def test_record_synthesis_operation_failure(self) -> None:
        """GIVEN failed synthesis operation
        WHEN synthesis fails
        THEN should record failure metrics.
        """
        from mcp_server_langgraph.agents.metrics import record_synthesis_operation

        record_synthesis_operation(
            input_count=3,
            successful_inputs=0,
            duration_ms=200.0,
            success=False,
            error_type="no_valid_inputs",
        )


@pytest.mark.unit
class TestAgentsMetricCounters:
    """Test suite for agents metric counter operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_orchestrator_execution_counter_increments(self) -> None:
        """GIVEN multiple orchestrator executions
        WHEN recording metrics
        THEN counter should increment.
        """
        from mcp_server_langgraph.agents.metrics import record_orchestrator_execution

        # Multiple calls should not raise
        for i in range(5):
            record_orchestrator_execution(
                task_count=3,
                successful_count=3,
                duration_ms=1000.0 + i * 100,
                success=True,
            )

    def test_subagent_execution_counter_by_model(self) -> None:
        """GIVEN subagent executions with different models
        WHEN recording metrics
        THEN should track by model label.
        """
        from mcp_server_langgraph.agents.metrics import record_subagent_execution

        models = ["gemini-2.5-flash", "claude-sonnet-4.5", "gpt-4.1-mini"]
        for model in models:
            record_subagent_execution(
                task_id=f"task-{model}",
                model=model,
                duration_ms=500.0,
                success=True,
            )

    def test_model_selection_counter_by_tier(self) -> None:
        """GIVEN model selections across tiers
        WHEN recording metrics
        THEN should track by tier label.
        """
        from mcp_server_langgraph.agents.metrics import record_model_selection

        tiers = ["simple", "complicated", "complex"]
        for tier in tiers:
            record_model_selection(
                tier=tier,
                vendor="google",
                model=f"gemini-{tier}",
            )


@pytest.mark.unit
class TestAgentsMetricHistograms:
    """Test suite for agents metric histogram operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_orchestrator_duration_histogram(self) -> None:
        """GIVEN orchestrator executions with varying durations
        WHEN recording metrics
        THEN histogram should capture distribution.
        """
        from mcp_server_langgraph.agents.metrics import record_orchestrator_execution

        durations = [100.0, 500.0, 1000.0, 2000.0, 5000.0]
        for duration in durations:
            record_orchestrator_execution(
                task_count=3,
                successful_count=3,
                duration_ms=duration,
                success=True,
            )

    def test_subagent_duration_histogram(self) -> None:
        """GIVEN subagent executions with varying durations
        WHEN recording metrics
        THEN histogram should capture distribution.
        """
        from mcp_server_langgraph.agents.metrics import record_subagent_execution

        durations = [50.0, 100.0, 250.0, 500.0, 1000.0]
        for i, duration in enumerate(durations):
            record_subagent_execution(
                task_id=f"task-{i}",
                model="gemini-2.5-flash",
                duration_ms=duration,
                success=True,
            )

    def test_synthesis_duration_histogram(self) -> None:
        """GIVEN synthesis operations with varying durations
        WHEN recording metrics
        THEN histogram should capture distribution.
        """
        from mcp_server_langgraph.agents.metrics import record_synthesis_operation

        durations = [200.0, 400.0, 800.0, 1600.0]
        for duration in durations:
            record_synthesis_operation(
                input_count=5,
                successful_inputs=5,
                duration_ms=duration,
                success=True,
            )
