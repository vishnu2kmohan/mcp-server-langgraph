"""
Tests for agent call metrics in health/checks.py.

Validates that agent_calls_successful_total and agent_calls_failed_total
metrics are properly defined and recorded.

TDD: Tests written FIRST before wiring to agent code.
"""

import gc

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.metrics]


@pytest.mark.xdist_group(name="test_agent_metrics")
class TestAgentCallMetrics:
    """Test agent call success/failure metrics."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_agent_calls_successful_total_defined(self) -> None:
        """Test agent_calls_successful_total counter is defined."""
        from mcp_server_langgraph.health import checks

        assert checks.PROMETHEUS_CLIENT_AVAILABLE
        assert checks.agent_calls_successful_total is not None

    def test_agent_calls_failed_total_defined(self) -> None:
        """Test agent_calls_failed_total counter is defined."""
        from mcp_server_langgraph.health import checks

        assert checks.PROMETHEUS_CLIENT_AVAILABLE
        assert checks.agent_calls_failed_total is not None

    def test_record_agent_call_success_function_exists(self) -> None:
        """Test record_agent_call_success helper function exists."""
        from mcp_server_langgraph.health import checks

        assert hasattr(checks, "record_agent_call_success")
        assert callable(checks.record_agent_call_success)

    def test_record_agent_call_failure_function_exists(self) -> None:
        """Test record_agent_call_failure helper function exists."""
        from mcp_server_langgraph.health import checks

        assert hasattr(checks, "record_agent_call_failure")
        assert callable(checks.record_agent_call_failure)

    def test_record_agent_call_success(self) -> None:
        """Test recording a successful agent call."""
        from mcp_server_langgraph.health.checks import record_agent_call_success

        # Should not raise
        record_agent_call_success(agent_type="default", model="gpt-4o")

    def test_record_agent_call_success_default_args(self) -> None:
        """Test recording with default arguments."""
        from mcp_server_langgraph.health.checks import record_agent_call_success

        # Should not raise
        record_agent_call_success()

    def test_record_agent_call_failure(self) -> None:
        """Test recording a failed agent call."""
        from mcp_server_langgraph.health.checks import record_agent_call_failure

        # Should not raise
        record_agent_call_failure(agent_type="default", model="gpt-4o", error_type="timeout")

    def test_record_agent_call_failure_default_args(self) -> None:
        """Test recording failure with default arguments."""
        from mcp_server_langgraph.health.checks import record_agent_call_failure

        # Should not raise
        record_agent_call_failure()

    def test_record_agent_call_failure_various_error_types(self) -> None:
        """Test recording failures with various error types."""
        from mcp_server_langgraph.health.checks import record_agent_call_failure

        error_types = ["timeout", "rate_limit", "api_error", "invalid_response", "connection_error"]
        for error_type in error_types:
            # Should not raise
            record_agent_call_failure(error_type=error_type)
