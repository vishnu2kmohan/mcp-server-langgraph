"""
Tests for MCP Prometheus Metrics.

Provides Prometheus metrics for MCP features including tasks,
sampling, elicitation, and tool execution.

TDD: RED phase - Define expected behavior for MCP metrics.
"""

import gc

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="mcp_metrics")
class TestMCPMetricsDefinition:
    """Test that MCP metrics are properly defined."""

    def teardown_method(self) -> None:
        """Clean up after each test."""
        gc.collect()

    def test_task_created_counter_exists(self) -> None:
        """Should have counter for task creation."""
        from mcp_server_langgraph.mcp.metrics import mcp_task_created_total

        assert mcp_task_created_total is not None
        assert hasattr(mcp_task_created_total, "inc")

    def test_task_duration_histogram_exists(self) -> None:
        """Should have histogram for task duration."""
        from mcp_server_langgraph.mcp.metrics import mcp_task_duration_seconds

        assert mcp_task_duration_seconds is not None
        assert hasattr(mcp_task_duration_seconds, "observe")

    def test_sampling_requests_counter_exists(self) -> None:
        """Should have counter for sampling requests."""
        from mcp_server_langgraph.mcp.metrics import mcp_sampling_requests_total

        assert mcp_sampling_requests_total is not None
        assert hasattr(mcp_sampling_requests_total, "inc")

    def test_elicitation_requests_counter_exists(self) -> None:
        """Should have counter for elicitation requests."""
        from mcp_server_langgraph.mcp.metrics import mcp_elicitation_requests_total

        assert mcp_elicitation_requests_total is not None
        assert hasattr(mcp_elicitation_requests_total, "inc")

    def test_tool_validation_errors_counter_exists(self) -> None:
        """Should have counter for tool validation errors."""
        from mcp_server_langgraph.mcp.metrics import mcp_tool_validation_errors_total

        assert mcp_tool_validation_errors_total is not None
        assert hasattr(mcp_tool_validation_errors_total, "inc")


@pytest.mark.xdist_group(name="mcp_metrics")
class TestMCPMetricsLabels:
    """Test that metrics have appropriate labels."""

    def teardown_method(self) -> None:
        """Clean up after each test."""
        gc.collect()

    def test_task_created_has_operation_label(self) -> None:
        """Task created counter should have operation label."""
        from mcp_server_langgraph.mcp.metrics import mcp_task_created_total

        # Check that labels can be used
        labeled = mcp_task_created_total.labels(operation="test_op")
        assert labeled is not None

    def test_sampling_has_status_label(self) -> None:
        """Sampling counter should have status label."""
        from mcp_server_langgraph.mcp.metrics import mcp_sampling_requests_total

        labeled = mcp_sampling_requests_total.labels(status="success")
        assert labeled is not None

    def test_elicitation_has_action_label(self) -> None:
        """Elicitation counter should have action label."""
        from mcp_server_langgraph.mcp.metrics import mcp_elicitation_requests_total

        labeled = mcp_elicitation_requests_total.labels(action="accept")
        assert labeled is not None


@pytest.mark.xdist_group(name="mcp_metrics")
class TestMCPMetricsHelpers:
    """Test helper functions for recording metrics."""

    def teardown_method(self) -> None:
        """Clean up after each test."""
        gc.collect()

    def test_record_task_created_increments_counter(self) -> None:
        """Should increment task created counter."""
        from mcp_server_langgraph.mcp.metrics import record_task_created

        # Should not raise
        record_task_created("code_execution")

    def test_record_sampling_request_increments_counter(self) -> None:
        """Should increment sampling request counter."""
        from mcp_server_langgraph.mcp.metrics import record_sampling_request

        # Should not raise
        record_sampling_request(status="success")

    def test_record_elicitation_increments_counter(self) -> None:
        """Should increment elicitation counter."""
        from mcp_server_langgraph.mcp.metrics import record_elicitation

        # Should not raise
        record_elicitation(action="accept")

    def test_record_tool_validation_error_increments_counter(self) -> None:
        """Should increment tool validation error counter."""
        from mcp_server_langgraph.mcp.metrics import record_tool_validation_error

        # Should not raise
        record_tool_validation_error(tool_name="agent_chat")
