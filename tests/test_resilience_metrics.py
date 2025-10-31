"""
Unit tests for resilience metrics module.

Tests OpenTelemetry metrics recording for all resilience patterns:
- Circuit breaker metrics
- Retry metrics
- Timeout metrics
- Bulkhead metrics
- Fallback metrics
"""

from unittest.mock import Mock, patch

import pytest

from mcp_server_langgraph.resilience import metrics


class TestCircuitBreakerMetrics:
    """Tests for circuit breaker metric recording"""

    def test_record_success_event(self):
        """Test recording circuit breaker success event"""
        with patch.object(metrics.circuit_breaker_success_counter, "add") as mock_add:
            metrics.record_circuit_breaker_event(
                service="llm",
                event_type="success",
            )

            mock_add.assert_called_once()
            call_args = mock_add.call_args
            assert call_args[0][0] == 1  # Count
            assert call_args[0][1]["service"] == "llm"

    def test_record_failure_event(self):
        """Test recording circuit breaker failure event"""
        with patch.object(metrics.circuit_breaker_failure_counter, "add") as mock_add:
            metrics.record_circuit_breaker_event(
                service="openfga",
                event_type="failure",
                exception_type="ConnectionError",
            )

            mock_add.assert_called_once()
            call_args = mock_add.call_args
            assert call_args[0][0] == 1
            assert call_args[0][1]["service"] == "openfga"
            assert call_args[0][1]["exception_type"] == "ConnectionError"

    def test_record_failure_without_exception_type(self):
        """Test recording failure without exception type"""
        with patch.object(metrics.circuit_breaker_failure_counter, "add") as mock_add:
            metrics.record_circuit_breaker_event(
                service="redis",
                event_type="failure",
            )

            mock_add.assert_called_once()
            call_args = mock_add.call_args
            assert call_args[0][1]["service"] == "redis"
            assert "exception_type" not in call_args[0][1]

    def test_record_state_change_event(self):
        """Test recording circuit breaker state change"""
        with patch.object(metrics.circuit_breaker_state_change_counter, "add") as mock_add:
            metrics.record_circuit_breaker_event(
                service="llm",
                event_type="state_change",
            )

            mock_add.assert_called_once()
            call_args = mock_add.call_args
            assert call_args[0][0] == 1
            assert call_args[0][1]["service"] == "llm"


class TestRetryMetrics:
    """Tests for retry metric recording"""

    def test_record_retry_attempt(self):
        """Test recording retry attempt"""
        with patch.object(metrics.retry_attempt_counter, "add") as mock_add:
            metrics.record_retry_event(
                function="call_llm",
                event_type="attempt",
                attempt_number=2,
                exception_type="TimeoutError",
            )

            mock_add.assert_called_once()
            call_args = mock_add.call_args
            assert call_args[0][0] == 1
            assert call_args[0][1]["function"] == "call_llm"
            assert call_args[0][1]["attempt_number"] == "2"
            assert call_args[0][1]["exception_type"] == "TimeoutError"

    def test_record_retry_exhausted(self):
        """Test recording retry exhaustion"""
        with patch.object(metrics.retry_exhausted_counter, "add") as mock_add:
            metrics.record_retry_event(
                function="check_permission",
                event_type="exhausted",
                exception_type="OpenFGAError",
            )

            mock_add.assert_called_once()
            call_args = mock_add.call_args
            assert call_args[0][0] == 1
            assert call_args[0][1]["function"] == "check_permission"
            assert call_args[0][1]["exception_type"] == "OpenFGAError"

    def test_record_success_after_retry(self):
        """Test recording successful retry"""
        with patch.object(metrics.retry_success_after_retry_counter, "add") as mock_add:
            metrics.record_retry_event(
                function="call_llm",
                event_type="success_after_retry",
                attempt_number=3,
            )

            mock_add.assert_called_once()
            call_args = mock_add.call_args
            assert call_args[0][0] == 1
            assert call_args[0][1]["function"] == "call_llm"
            assert call_args[0][1]["attempt_number"] == "3"

    def test_record_retry_without_optional_fields(self):
        """Test recording retry event without optional fields"""
        with patch.object(metrics.retry_attempt_counter, "add") as mock_add:
            metrics.record_retry_event(
                function="some_func",
                event_type="attempt",
            )

            mock_add.assert_called_once()
            call_args = mock_add.call_args
            assert call_args[0][1]["function"] == "some_func"
            assert "attempt_number" not in call_args[0][1]
            assert "exception_type" not in call_args[0][1]


class TestTimeoutMetrics:
    """Tests for timeout metric recording"""

    def test_record_timeout_violation(self):
        """Test recording timeout exceeded event"""
        with (
            patch.object(metrics.timeout_exceeded_counter, "add") as mock_add_counter,
            patch.object(metrics.timeout_duration_histogram, "record") as mock_record_histogram,
        ):
            metrics.record_timeout_event(
                function="call_llm",
                operation_type="llm",
                timeout_seconds=30,
            )

            # Verify counter was incremented
            mock_add_counter.assert_called_once()
            counter_args = mock_add_counter.call_args
            assert counter_args[0][0] == 1
            assert counter_args[0][1]["function"] == "call_llm"
            assert counter_args[0][1]["operation_type"] == "llm"
            assert counter_args[0][1]["timeout_seconds"] == "30"

            # Verify histogram was recorded
            mock_record_histogram.assert_called_once()
            histogram_args = mock_record_histogram.call_args
            assert histogram_args[0][0] == 30
            assert histogram_args[0][1]["function"] == "call_llm"

    def test_record_timeout_for_different_operations(self):
        """Test recording timeouts for different operation types"""
        operation_types = ["llm", "auth", "db", "http", "default"]

        for op_type in operation_types:
            with patch.object(metrics.timeout_exceeded_counter, "add") as mock_add:
                metrics.record_timeout_event(
                    function=f"test_{op_type}",
                    operation_type=op_type,
                    timeout_seconds=10,
                )

                call_args = mock_add.call_args
                assert call_args[0][1]["operation_type"] == op_type


class TestBulkheadMetrics:
    """Tests for bulkhead metric recording"""

    def test_record_bulkhead_rejection(self):
        """Test recording bulkhead rejection"""
        with patch.object(metrics.bulkhead_rejected_counter, "add") as mock_add:
            metrics.record_bulkhead_event(
                resource_type="llm",
                event_type="rejection",
            )

            mock_add.assert_called_once()
            call_args = mock_add.call_args
            assert call_args[0][0] == 1
            assert call_args[0][1]["resource_type"] == "llm"

    def test_record_active_operations(self):
        """Test recording active operations count"""
        with patch.object(metrics.bulkhead_active_operations_gauge, "set") as mock_set:
            metrics.record_bulkhead_event(
                resource_type="openfga",
                event_type="active",
                active_count=25,
            )

            mock_set.assert_called_once()
            call_args = mock_set.call_args
            assert call_args[0][0] == 25
            assert call_args[0][1]["resource_type"] == "openfga"

    def test_record_queue_depth(self):
        """Test recording queue depth"""
        with patch.object(metrics.bulkhead_queue_depth_gauge, "set") as mock_set:
            metrics.record_bulkhead_event(
                resource_type="redis",
                event_type="queued",
                queue_depth=10,
            )

            mock_set.assert_called_once()
            call_args = mock_set.call_args
            assert call_args[0][0] == 10
            assert call_args[0][1]["resource_type"] == "redis"

    def test_record_active_without_count(self):
        """Test recording active event without count (should not call set)"""
        with patch.object(metrics.bulkhead_active_operations_gauge, "set") as mock_set:
            metrics.record_bulkhead_event(
                resource_type="db",
                event_type="active",
            )

            mock_set.assert_not_called()

    def test_record_queued_without_depth(self):
        """Test recording queued event without depth (should not call set)"""
        with patch.object(metrics.bulkhead_queue_depth_gauge, "set") as mock_set:
            metrics.record_bulkhead_event(
                resource_type="db",
                event_type="queued",
            )

            mock_set.assert_not_called()


class TestFallbackMetrics:
    """Tests for fallback metric recording"""

    def test_record_default_fallback(self):
        """Test recording default fallback usage"""
        with patch.object(metrics.fallback_used_counter, "add") as mock_add:
            metrics.record_fallback_event(
                function="check_permission",
                exception_type="OpenFGAError",
                fallback_type="default",
            )

            mock_add.assert_called_once()
            call_args = mock_add.call_args
            assert call_args[0][0] == 1
            assert call_args[0][1]["function"] == "check_permission"
            assert call_args[0][1]["exception_type"] == "OpenFGAError"
            assert call_args[0][1]["fallback_type"] == "default"

    def test_record_function_fallback(self):
        """Test recording function fallback usage"""
        with patch.object(metrics.fallback_used_counter, "add") as mock_add:
            metrics.record_fallback_event(
                function="call_llm",
                exception_type="RateLimitError",
                fallback_type="function",
            )

            call_args = mock_add.call_args
            assert call_args[0][1]["fallback_type"] == "function"

    def test_record_cache_fallback(self):
        """Test recording cache fallback with cache hit counter"""
        with (
            patch.object(metrics.fallback_used_counter, "add") as mock_add_used,
            patch.object(metrics.fallback_cache_hits_counter, "add") as mock_add_cache,
        ):
            metrics.record_fallback_event(
                function="get_user_data",
                exception_type="DatabaseError",
                fallback_type="cache",
            )

            # Verify fallback used counter
            mock_add_used.assert_called_once()
            used_args = mock_add_used.call_args
            assert used_args[0][1]["fallback_type"] == "cache"

            # Verify cache hits counter
            mock_add_cache.assert_called_once()
            cache_args = mock_add_cache.call_args
            assert cache_args[0][0] == 1
            assert cache_args[0][1]["function"] == "get_user_data"

    def test_record_non_cache_fallback_no_cache_hit(self):
        """Test non-cache fallback doesn't increment cache hits"""
        with patch.object(metrics.fallback_cache_hits_counter, "add") as mock_add_cache:
            metrics.record_fallback_event(
                function="some_func",
                exception_type="SomeError",
                fallback_type="default",
            )

            # Cache hits should not be incremented
            mock_add_cache.assert_not_called()


class TestMetricsSummary:
    """Tests for metrics summary and export functions"""

    def test_get_resilience_metrics_summary(self):
        """Test getting metrics summary"""
        summary = metrics.get_resilience_metrics_summary()

        # Verify structure
        assert "circuit_breakers" in summary
        assert "retries" in summary
        assert "timeouts" in summary
        assert "bulkheads" in summary
        assert "fallbacks" in summary

        # Verify circuit breaker metrics
        assert "total_failures" in summary["circuit_breakers"]
        assert "total_successes" in summary["circuit_breakers"]
        assert "state_changes" in summary["circuit_breakers"]
        assert "current_state" in summary["circuit_breakers"]

        # Verify retry metrics
        assert "total_attempts" in summary["retries"]
        assert "exhausted" in summary["retries"]
        assert "successes" in summary["retries"]

        # Verify timeout metrics
        assert "total_exceeded" in summary["timeouts"]
        assert "duration_histogram" in summary["timeouts"]

        # Verify bulkhead metrics
        assert "total_rejections" in summary["bulkheads"]
        assert "active_operations" in summary["bulkheads"]
        assert "queue_depth" in summary["bulkheads"]

        # Verify fallback metrics
        assert "total_used" in summary["fallbacks"]
        assert "cache_hits" in summary["fallbacks"]

    def test_export_prometheus_format(self):
        """Test Prometheus format export"""
        prometheus_output = metrics.export_resilience_metrics_for_prometheus()

        # Verify output is a string
        assert isinstance(prometheus_output, str)

        # Verify it contains expected metric names
        assert "circuit_breaker_failures" in prometheus_output
        assert "circuit_breaker_state" in prometheus_output
        assert "retry_attempts" in prometheus_output
        assert "timeout_exceeded" in prometheus_output
        assert "bulkhead_rejections" in prometheus_output
        assert "fallback_used" in prometheus_output

        # Verify it contains HELP and TYPE comments
        assert "# HELP" in prometheus_output
        assert "# TYPE" in prometheus_output

        # Verify it contains metric types
        assert "counter" in prometheus_output
        assert "gauge" in prometheus_output


class TestMetricsIntegration:
    """Integration tests for metrics recording"""

    def test_multiple_circuit_breaker_events(self):
        """Test recording multiple circuit breaker events"""
        with (
            patch.object(metrics.circuit_breaker_success_counter, "add") as mock_success,
            patch.object(metrics.circuit_breaker_failure_counter, "add") as mock_failure,
        ):
            # Record successes
            for i in range(5):
                metrics.record_circuit_breaker_event("llm", "success")

            # Record failures
            for i in range(2):
                metrics.record_circuit_breaker_event("llm", "failure", "TimeoutError")

            # Verify call counts
            assert mock_success.call_count == 5
            assert mock_failure.call_count == 2

    def test_retry_workflow(self):
        """Test complete retry workflow metrics"""
        with (
            patch.object(metrics.retry_attempt_counter, "add") as mock_attempt,
            patch.object(metrics.retry_success_after_retry_counter, "add") as mock_success,
        ):
            # Record 3 retry attempts
            for attempt in range(1, 4):
                metrics.record_retry_event(
                    function="call_llm",
                    event_type="attempt",
                    attempt_number=attempt,
                )

            # Record final success
            metrics.record_retry_event(
                function="call_llm",
                event_type="success_after_retry",
                attempt_number=3,
            )

            # Verify metrics
            assert mock_attempt.call_count == 3
            mock_success.assert_called_once()

    def test_bulkhead_lifecycle(self):
        """Test bulkhead full lifecycle metrics"""
        with (
            patch.object(metrics.bulkhead_active_operations_gauge, "set") as mock_active,
            patch.object(metrics.bulkhead_queue_depth_gauge, "set") as mock_queue,
            patch.object(metrics.bulkhead_rejected_counter, "add") as mock_reject,
        ):
            # Operations start
            metrics.record_bulkhead_event("llm", "active", active_count=10)

            # Queue builds up
            metrics.record_bulkhead_event("llm", "queued", queue_depth=5)

            # Rejection happens
            metrics.record_bulkhead_event("llm", "rejection")

            # Verify all metrics recorded
            mock_active.assert_called_once()
            mock_queue.assert_called_once()
            mock_reject.assert_called_once()


class TestMetricsOpenTelemetryIntegration:
    """Tests for OpenTelemetry metrics integration"""

    def test_metrics_have_correct_names(self):
        """Verify all metrics have correct OpenTelemetry names"""
        # Circuit breaker metrics
        assert metrics.circuit_breaker_state_gauge is not None
        assert metrics.circuit_breaker_failure_counter is not None
        assert metrics.circuit_breaker_success_counter is not None
        assert metrics.circuit_breaker_state_change_counter is not None

        # Retry metrics
        assert metrics.retry_attempt_counter is not None
        assert metrics.retry_exhausted_counter is not None
        assert metrics.retry_success_after_retry_counter is not None

        # Timeout metrics
        assert metrics.timeout_exceeded_counter is not None
        assert metrics.timeout_duration_histogram is not None

        # Bulkhead metrics
        assert metrics.bulkhead_rejected_counter is not None
        assert metrics.bulkhead_active_operations_gauge is not None
        assert metrics.bulkhead_queue_depth_gauge is not None

        # Fallback metrics
        assert metrics.fallback_used_counter is not None
        assert metrics.fallback_cache_hits_counter is not None

    def test_meter_is_initialized(self):
        """Test that OpenTelemetry meter is initialized"""
        assert metrics.meter is not None


class TestEdgeCases:
    """Tests for edge cases and error handling"""

    def test_record_event_with_empty_strings(self):
        """Test recording events with empty string values"""
        with patch.object(metrics.circuit_breaker_success_counter, "add") as mock_add:
            metrics.record_circuit_breaker_event(
                service="",
                event_type="success",
            )

            call_args = mock_add.call_args
            assert call_args[0][1]["service"] == ""

    def test_record_timeout_with_zero_timeout(self):
        """Test recording timeout with zero timeout value"""
        with patch.object(metrics.timeout_exceeded_counter, "add") as mock_add:
            metrics.record_timeout_event(
                function="test",
                operation_type="default",
                timeout_seconds=0,
            )

            call_args = mock_add.call_args
            assert call_args[0][1]["timeout_seconds"] == "0"

    def test_record_bulkhead_with_negative_counts(self):
        """Test recording bulkhead with negative values (edge case)"""
        with patch.object(metrics.bulkhead_active_operations_gauge, "set") as mock_set:
            metrics.record_bulkhead_event(
                resource_type="llm",
                event_type="active",
                active_count=-1,
            )

            # Should still record (validation happens at metrics backend)
            call_args = mock_set.call_args
            assert call_args[0][0] == -1
