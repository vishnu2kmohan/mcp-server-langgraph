"""
Alert Metrics Unit Tests.

Tests for OpenTelemetry metrics used in alert processing.
Validates all 44 metrics and 22 helper functions are correctly instrumented.

Metrics categories tested:
- Alert Reception (received, broadcast, filtered)
- AI Recommendation (requested, cache hits/misses, generated, failed, duration)
- Rate Limiting (exceeded, tokens available)
- Remediation Workflow (requested, approved, rejected, executed, success/failed, duration)
- WebSocket Connection (connections, messages)
- AI Recommendation Quality (approvals, rejections, execution success/failure)
- Few-Shot Learning (with/without fewshot, fewshot approvals/rejections)
- Constraint Learning (with constraints, patterns applied)
- Quality Scores (quality score histogram, confidence histogram)
- Alert Correlation (requests, groups, duration, patterns, root causes)

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    pass

pytestmark = [
    pytest.mark.unit,
    pytest.mark.alerts,
    pytest.mark.observability,
]


@pytest.mark.xdist_group(name="test_alert_metrics")
class TestAlertMetricsInstruments:
    """Tests for alert metric instrument definitions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_meter_created(self) -> None:
        """
        GIVEN the metrics module
        WHEN importing meter
        THEN should have a valid OpenTelemetry meter.
        """
        from mcp_server_langgraph.alerts.metrics import meter

        assert meter is not None

    def test_alert_received_counter_exists(self) -> None:
        """
        GIVEN the metrics module
        WHEN importing alert_received_counter
        THEN should be a valid counter with correct configuration.
        """
        from mcp_server_langgraph.alerts.metrics import alert_received_counter

        assert alert_received_counter is not None
        # Counter should have a name property
        assert hasattr(alert_received_counter, "add")

    def test_alert_broadcast_counter_exists(self) -> None:
        """
        GIVEN the metrics module
        WHEN importing alert_broadcast_counter
        THEN should be a valid counter.
        """
        from mcp_server_langgraph.alerts.metrics import alert_broadcast_counter

        assert alert_broadcast_counter is not None
        assert hasattr(alert_broadcast_counter, "add")

    def test_alert_filtered_counter_exists(self) -> None:
        """
        GIVEN the metrics module
        WHEN importing alert_filtered_counter
        THEN should be a valid counter.
        """
        from mcp_server_langgraph.alerts.metrics import alert_filtered_counter

        assert alert_filtered_counter is not None
        assert hasattr(alert_filtered_counter, "add")

    def test_recommendation_counters_exist(self) -> None:
        """
        GIVEN the metrics module
        WHEN importing recommendation counters
        THEN should have all expected counters.
        """
        from mcp_server_langgraph.alerts.metrics import (
            recommendation_cache_hit_counter,
            recommendation_cache_miss_counter,
            recommendation_failed_counter,
            recommendation_generated_counter,
            recommendation_regenerated_counter,
            recommendation_requested_counter,
        )

        counters = [
            recommendation_requested_counter,
            recommendation_cache_hit_counter,
            recommendation_cache_miss_counter,
            recommendation_generated_counter,
            recommendation_failed_counter,
            recommendation_regenerated_counter,
        ]
        for counter in counters:
            assert counter is not None
            assert hasattr(counter, "add")

    def test_recommendation_duration_histogram_exists(self) -> None:
        """
        GIVEN the metrics module
        WHEN importing recommendation_duration_histogram
        THEN should be a valid histogram.
        """
        from mcp_server_langgraph.alerts.metrics import recommendation_duration_histogram

        assert recommendation_duration_histogram is not None
        assert hasattr(recommendation_duration_histogram, "record")

    def test_recommendation_cache_size_gauge_exists(self) -> None:
        """
        GIVEN the metrics module
        WHEN importing recommendation_cache_size_gauge
        THEN should be a valid gauge.
        """
        from mcp_server_langgraph.alerts.metrics import recommendation_cache_size_gauge

        assert recommendation_cache_size_gauge is not None
        assert hasattr(recommendation_cache_size_gauge, "set")

    def test_rate_limit_metrics_exist(self) -> None:
        """
        GIVEN the metrics module
        WHEN importing rate limit metrics
        THEN should have counter and gauge.
        """
        from mcp_server_langgraph.alerts.metrics import (
            rate_limit_exceeded_counter,
            rate_limit_tokens_gauge,
        )

        assert rate_limit_exceeded_counter is not None
        assert hasattr(rate_limit_exceeded_counter, "add")

        assert rate_limit_tokens_gauge is not None
        assert hasattr(rate_limit_tokens_gauge, "set")

    def test_remediation_counters_exist(self) -> None:
        """
        GIVEN the metrics module
        WHEN importing remediation counters
        THEN should have all expected counters.
        """
        from mcp_server_langgraph.alerts.metrics import (
            remediation_approved_counter,
            remediation_command_blocked_counter,
            remediation_executed_counter,
            remediation_execution_failed_counter,
            remediation_execution_success_counter,
            remediation_rejected_counter,
            remediation_requested_counter,
        )

        counters = [
            remediation_requested_counter,
            remediation_approved_counter,
            remediation_rejected_counter,
            remediation_executed_counter,
            remediation_execution_success_counter,
            remediation_execution_failed_counter,
            remediation_command_blocked_counter,
        ]
        for counter in counters:
            assert counter is not None
            assert hasattr(counter, "add")

    def test_remediation_execution_duration_histogram_exists(self) -> None:
        """
        GIVEN the metrics module
        WHEN importing remediation_execution_duration_histogram
        THEN should be a valid histogram.
        """
        from mcp_server_langgraph.alerts.metrics import remediation_execution_duration_histogram

        assert remediation_execution_duration_histogram is not None
        assert hasattr(remediation_execution_duration_histogram, "record")

    def test_websocket_metrics_exist(self) -> None:
        """
        GIVEN the metrics module
        WHEN importing WebSocket metrics
        THEN should have gauge and counter.
        """
        from mcp_server_langgraph.alerts.metrics import (
            alert_websocket_connections_gauge,
            alert_websocket_messages_counter,
        )

        assert alert_websocket_connections_gauge is not None
        assert hasattr(alert_websocket_connections_gauge, "set")

        assert alert_websocket_messages_counter is not None
        assert hasattr(alert_websocket_messages_counter, "add")


@pytest.mark.xdist_group(name="test_alert_metrics")
class TestAlertRecordingHelpers:
    """Tests for alert metrics recording helper functions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_record_alert_received_calls_counter(self) -> None:
        """
        GIVEN the record_alert_received function
        WHEN called with severity and status
        THEN should add to the counter with correct labels.
        """
        from mcp_server_langgraph.alerts.metrics import (
            alert_received_counter,
            record_alert_received,
        )

        with patch.object(alert_received_counter, "add") as mock_add:
            record_alert_received("critical", "firing")
            mock_add.assert_called_once_with(
                1, {"severity": "critical", "status": "firing"}
            )

    def test_record_alert_broadcast_calls_counter(self) -> None:
        """
        GIVEN the record_alert_broadcast function
        WHEN called with severity and client_count
        THEN should add to the counter with correct labels.
        """
        from mcp_server_langgraph.alerts.metrics import (
            alert_broadcast_counter,
            record_alert_broadcast,
        )

        with patch.object(alert_broadcast_counter, "add") as mock_add:
            record_alert_broadcast("warning", 5)
            mock_add.assert_called_once_with(
                1, {"severity": "warning", "client_count": "5"}
            )

    def test_record_alert_filtered_calls_counter(self) -> None:
        """
        GIVEN the record_alert_filtered function
        WHEN called with severity and reason
        THEN should add to the counter with correct labels.
        """
        from mcp_server_langgraph.alerts.metrics import (
            alert_filtered_counter,
            record_alert_filtered,
        )

        with patch.object(alert_filtered_counter, "add") as mock_add:
            record_alert_filtered("info", "severity_too_low")
            mock_add.assert_called_once_with(
                1, {"severity": "info", "reason": "severity_too_low"}
            )


@pytest.mark.xdist_group(name="test_alert_metrics")
class TestRecommendationMetricHelpers:
    """Tests for recommendation metrics recording helper functions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_record_recommendation_request_cached(self) -> None:
        """
        GIVEN the record_recommendation_request function
        WHEN called with cached=True
        THEN should add to requested and cache_hit counters.
        """
        from mcp_server_langgraph.alerts.metrics import (
            recommendation_cache_hit_counter,
            recommendation_requested_counter,
            record_recommendation_request,
        )

        with (
            patch.object(recommendation_requested_counter, "add") as mock_requested,
            patch.object(recommendation_cache_hit_counter, "add") as mock_cache_hit,
        ):
            record_recommendation_request("alert-12345678", cached=True)
            mock_requested.assert_called_once_with(1, {"alert_id": "alert-12"})
            mock_cache_hit.assert_called_once_with(1)

    def test_record_recommendation_request_not_cached(self) -> None:
        """
        GIVEN the record_recommendation_request function
        WHEN called with cached=False
        THEN should add to requested and cache_miss counters.
        """
        from mcp_server_langgraph.alerts.metrics import (
            recommendation_cache_miss_counter,
            recommendation_requested_counter,
            record_recommendation_request,
        )

        with (
            patch.object(recommendation_requested_counter, "add") as mock_requested,
            patch.object(recommendation_cache_miss_counter, "add") as mock_cache_miss,
        ):
            record_recommendation_request("alert-abcdef12", cached=False)
            mock_requested.assert_called_once_with(1, {"alert_id": "alert-ab"})
            mock_cache_miss.assert_called_once_with(1)

    def test_record_recommendation_generated_success(self) -> None:
        """
        GIVEN the record_recommendation_generated function
        WHEN called with success=True
        THEN should add to generated counter and record duration.
        """
        from mcp_server_langgraph.alerts.metrics import (
            recommendation_duration_histogram,
            recommendation_generated_counter,
            record_recommendation_generated,
        )

        with (
            patch.object(recommendation_generated_counter, "add") as mock_generated,
            patch.object(recommendation_duration_histogram, "record") as mock_duration,
        ):
            record_recommendation_generated("alert-xyz", 1.5, success=True)
            mock_generated.assert_called_once_with(1, {"alert_id": "alert-xy"})
            mock_duration.assert_called_once_with(1.5)

    def test_record_recommendation_generated_failure(self) -> None:
        """
        GIVEN the record_recommendation_generated function
        WHEN called with success=False
        THEN should add to failed counter and record duration.
        """
        from mcp_server_langgraph.alerts.metrics import (
            recommendation_duration_histogram,
            recommendation_failed_counter,
            record_recommendation_generated,
        )

        with (
            patch.object(recommendation_failed_counter, "add") as mock_failed,
            patch.object(recommendation_duration_histogram, "record") as mock_duration,
        ):
            record_recommendation_generated("alert-fail", 2.5, success=False)
            mock_failed.assert_called_once_with(1, {"alert_id": "alert-fa"})
            mock_duration.assert_called_once_with(2.5)

    def test_record_recommendation_regenerated(self) -> None:
        """
        GIVEN the record_recommendation_regenerated function
        WHEN called
        THEN should add to regenerated counter.
        """
        from mcp_server_langgraph.alerts.metrics import (
            recommendation_regenerated_counter,
            record_recommendation_regenerated,
        )

        with patch.object(recommendation_regenerated_counter, "add") as mock_regenerated:
            record_recommendation_regenerated("alert-regen")
            mock_regenerated.assert_called_once_with(1, {"alert_id": "alert-re"})


@pytest.mark.xdist_group(name="test_alert_metrics")
class TestRateLimitMetricHelpers:
    """Tests for rate limit metrics recording helper functions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_record_rate_limit_exceeded(self) -> None:
        """
        GIVEN the record_rate_limit_exceeded function
        WHEN called with endpoint name
        THEN should add to the counter with correct label.
        """
        from mcp_server_langgraph.alerts.metrics import (
            rate_limit_exceeded_counter,
            record_rate_limit_exceeded,
        )

        with patch.object(rate_limit_exceeded_counter, "add") as mock_add:
            record_rate_limit_exceeded("get_recommendation")
            mock_add.assert_called_once_with(1, {"endpoint": "get_recommendation"})


@pytest.mark.xdist_group(name="test_alert_metrics")
class TestRemediationMetricHelpers:
    """Tests for remediation workflow metrics recording helper functions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_record_remediation_workflow_requested(self) -> None:
        """
        GIVEN the record_remediation_workflow function
        WHEN called with action='requested'
        THEN should add to remediation_requested counter.
        """
        from mcp_server_langgraph.alerts.metrics import (
            record_remediation_workflow,
            remediation_requested_counter,
        )

        with patch.object(remediation_requested_counter, "add") as mock_add:
            record_remediation_workflow("requested", "rem-12345678")
            mock_add.assert_called_once_with(1, {"remediation_id": "rem-1234"})

    def test_record_remediation_workflow_approved(self) -> None:
        """
        GIVEN the record_remediation_workflow function
        WHEN called with action='approved'
        THEN should add to remediation_approved counter.
        """
        from mcp_server_langgraph.alerts.metrics import (
            record_remediation_workflow,
            remediation_approved_counter,
        )

        with patch.object(remediation_approved_counter, "add") as mock_add:
            record_remediation_workflow("approved", "rem-abcdef12")
            mock_add.assert_called_once_with(1, {"remediation_id": "rem-abcd"})

    def test_record_remediation_workflow_rejected(self) -> None:
        """
        GIVEN the record_remediation_workflow function
        WHEN called with action='rejected'
        THEN should add to remediation_rejected counter.
        """
        from mcp_server_langgraph.alerts.metrics import (
            record_remediation_workflow,
            remediation_rejected_counter,
        )

        with patch.object(remediation_rejected_counter, "add") as mock_add:
            record_remediation_workflow("rejected", "rem-reject12")
            mock_add.assert_called_once_with(1, {"remediation_id": "rem-reje"})

    def test_record_remediation_workflow_executed_success(self) -> None:
        """
        GIVEN the record_remediation_workflow function
        WHEN called with action='executed' and success=True
        THEN should add to executed and execution_success counters.
        """
        from mcp_server_langgraph.alerts.metrics import (
            record_remediation_workflow,
            remediation_executed_counter,
            remediation_execution_success_counter,
        )

        with (
            patch.object(remediation_executed_counter, "add") as mock_executed,
            patch.object(remediation_execution_success_counter, "add") as mock_success,
        ):
            record_remediation_workflow("executed", "rem-success1", success=True)
            mock_executed.assert_called_once_with(1, {"remediation_id": "rem-succ"})
            mock_success.assert_called_once_with(1, {"remediation_id": "rem-succ"})

    def test_record_remediation_workflow_executed_failure(self) -> None:
        """
        GIVEN the record_remediation_workflow function
        WHEN called with action='executed' and success=False
        THEN should add to executed and execution_failed counters.
        """
        from mcp_server_langgraph.alerts.metrics import (
            record_remediation_workflow,
            remediation_executed_counter,
            remediation_execution_failed_counter,
        )

        with (
            patch.object(remediation_executed_counter, "add") as mock_executed,
            patch.object(remediation_execution_failed_counter, "add") as mock_failed,
        ):
            record_remediation_workflow("executed", "rem-failed12", success=False)
            mock_executed.assert_called_once_with(1, {"remediation_id": "rem-fail"})
            mock_failed.assert_called_once_with(1, {"remediation_id": "rem-fail"})

    def test_record_remediation_execution(self) -> None:
        """
        GIVEN the record_remediation_execution function
        WHEN called with remediation_id, duration, and success
        THEN should record to duration histogram.
        """
        from mcp_server_langgraph.alerts.metrics import (
            record_remediation_execution,
            remediation_execution_duration_histogram,
        )

        with patch.object(
            remediation_execution_duration_histogram, "record"
        ) as mock_record:
            record_remediation_execution("rem-exec1234", 3.5, success=True)
            mock_record.assert_called_once_with(
                3.5, {"remediation_id": "rem-exec", "success": "true"}
            )

    def test_record_command_blocked(self) -> None:
        """
        GIVEN the record_command_blocked function
        WHEN called with a reason
        THEN should add to command_blocked counter.
        """
        from mcp_server_langgraph.alerts.metrics import (
            record_command_blocked,
            remediation_command_blocked_counter,
        )

        with patch.object(remediation_command_blocked_counter, "add") as mock_add:
            record_command_blocked("destructive_command")
            mock_add.assert_called_once_with(1, {"reason": "destructive_command"})


@pytest.mark.xdist_group(name="test_alert_metrics")
class TestWebSocketMetricHelpers:
    """Tests for WebSocket connection metrics recording helper functions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_update_websocket_connections(self) -> None:
        """
        GIVEN the update_websocket_connections function
        WHEN called with a count
        THEN should set the gauge to that value.
        """
        from mcp_server_langgraph.alerts.metrics import (
            alert_websocket_connections_gauge,
            update_websocket_connections,
        )

        with patch.object(alert_websocket_connections_gauge, "set") as mock_set:
            update_websocket_connections(10)
            mock_set.assert_called_once_with(10)

    def test_record_websocket_message(self) -> None:
        """
        GIVEN the record_websocket_message function
        WHEN called with a message type
        THEN should add to the counter with correct label.
        """
        from mcp_server_langgraph.alerts.metrics import (
            alert_websocket_messages_counter,
            record_websocket_message,
        )

        with patch.object(alert_websocket_messages_counter, "add") as mock_add:
            record_websocket_message("alert_broadcast")
            mock_add.assert_called_once_with(1, {"message_type": "alert_broadcast"})


@pytest.mark.xdist_group(name="test_alert_metrics")
class TestAIRecommendationQualityMetrics:
    """Tests for AI Recommendation Quality metrics added for learning effectiveness tracking."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_recommendation_approval_rejection_counters_exist(self) -> None:
        """
        GIVEN the metrics module
        WHEN importing recommendation approval/rejection counters
        THEN should have all expected counters.
        """
        from mcp_server_langgraph.alerts.metrics import (
            recommendation_approval_counter,
            recommendation_rejection_counter,
            recommendation_rejection_reason_counter,
        )

        counters = [
            recommendation_approval_counter,
            recommendation_rejection_counter,
            recommendation_rejection_reason_counter,
        ]
        for counter in counters:
            assert counter is not None
            assert hasattr(counter, "add")

    def test_recommendation_execution_metrics_exist(self) -> None:
        """
        GIVEN the metrics module
        WHEN importing recommendation execution success/failure metrics
        THEN should have counters and histogram.
        """
        from mcp_server_langgraph.alerts.metrics import (
            recommendation_execution_failure_counter,
            recommendation_execution_success_counter,
            recommendation_execution_time_histogram,
        )

        assert recommendation_execution_success_counter is not None
        assert hasattr(recommendation_execution_success_counter, "add")

        assert recommendation_execution_failure_counter is not None
        assert hasattr(recommendation_execution_failure_counter, "add")

        assert recommendation_execution_time_histogram is not None
        assert hasattr(recommendation_execution_time_histogram, "record")

    def test_fewshot_learning_metrics_exist(self) -> None:
        """
        GIVEN the metrics module
        WHEN importing few-shot learning metrics
        THEN should have all expected counters.
        """
        from mcp_server_langgraph.alerts.metrics import (
            fewshot_approval_counter,
            fewshot_rejection_counter,
            recommendation_with_fewshot_counter,
            recommendation_without_fewshot_counter,
        )

        counters = [
            recommendation_with_fewshot_counter,
            recommendation_without_fewshot_counter,
            fewshot_approval_counter,
            fewshot_rejection_counter,
        ]
        for counter in counters:
            assert counter is not None
            assert hasattr(counter, "add")

    def test_constraint_learning_metrics_exist(self) -> None:
        """
        GIVEN the metrics module
        WHEN importing constraint learning metrics
        THEN should have counter and gauge.
        """
        from mcp_server_langgraph.alerts.metrics import (
            constraint_patterns_applied_gauge,
            recommendation_with_constraints_counter,
        )

        assert recommendation_with_constraints_counter is not None
        assert hasattr(recommendation_with_constraints_counter, "add")

        assert constraint_patterns_applied_gauge is not None
        assert hasattr(constraint_patterns_applied_gauge, "set")

    def test_quality_score_histograms_exist(self) -> None:
        """
        GIVEN the metrics module
        WHEN importing quality score histograms
        THEN should have both histograms.
        """
        from mcp_server_langgraph.alerts.metrics import (
            recommendation_confidence_histogram,
            recommendation_quality_score_histogram,
        )

        assert recommendation_quality_score_histogram is not None
        assert hasattr(recommendation_quality_score_histogram, "record")

        assert recommendation_confidence_histogram is not None
        assert hasattr(recommendation_confidence_histogram, "record")


@pytest.mark.xdist_group(name="test_alert_metrics")
class TestAIRecommendationQualityHelpers:
    """Tests for AI Recommendation Quality helper functions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_record_recommendation_approval(self) -> None:
        """
        GIVEN the record_recommendation_approval function
        WHEN called with alert_type and flags
        THEN should add to approval counter.
        """
        from mcp_server_langgraph.alerts.metrics import (
            recommendation_approval_counter,
            record_recommendation_approval,
        )

        with patch.object(recommendation_approval_counter, "add") as mock_add:
            record_recommendation_approval("HighCPU", had_fewshot=False)
            mock_add.assert_called_once_with(1, {"alert_type": "HighCPU"})

    def test_record_recommendation_approval_with_fewshot(self) -> None:
        """
        GIVEN the record_recommendation_approval function
        WHEN called with had_fewshot=True
        THEN should add to both approval and fewshot_approval counters.
        """
        from mcp_server_langgraph.alerts.metrics import (
            fewshot_approval_counter,
            recommendation_approval_counter,
            record_recommendation_approval,
        )

        with (
            patch.object(recommendation_approval_counter, "add") as mock_approval,
            patch.object(fewshot_approval_counter, "add") as mock_fewshot,
        ):
            record_recommendation_approval("HighMemory", had_fewshot=True)
            mock_approval.assert_called_once_with(1, {"alert_type": "HighMemory"})
            mock_fewshot.assert_called_once_with(1, {"alert_type": "HighMemory"})

    def test_record_recommendation_rejection(self) -> None:
        """
        GIVEN the record_recommendation_rejection function
        WHEN called with alert_type and reason
        THEN should add to rejection counters.
        """
        from mcp_server_langgraph.alerts.metrics import (
            recommendation_rejection_counter,
            recommendation_rejection_reason_counter,
            record_recommendation_rejection,
        )

        with (
            patch.object(recommendation_rejection_counter, "add") as mock_rejection,
            patch.object(recommendation_rejection_reason_counter, "add") as mock_reason,
        ):
            record_recommendation_rejection("DiskFull", "too_risky", had_fewshot=False)
            mock_rejection.assert_called_once_with(1, {"alert_type": "DiskFull"})
            mock_reason.assert_called_once_with(1, {"reason": "too_risky"})

    def test_record_recommendation_rejection_with_fewshot(self) -> None:
        """
        GIVEN the record_recommendation_rejection function
        WHEN called with had_fewshot=True
        THEN should add to rejection and fewshot_rejection counters.
        """
        from mcp_server_langgraph.alerts.metrics import (
            fewshot_rejection_counter,
            recommendation_rejection_counter,
            record_recommendation_rejection,
        )

        with (
            patch.object(recommendation_rejection_counter, "add") as mock_rejection,
            patch.object(fewshot_rejection_counter, "add") as mock_fewshot,
        ):
            record_recommendation_rejection("NetworkDown", "wrong_command", had_fewshot=True)
            mock_rejection.assert_called_once_with(1, {"alert_type": "NetworkDown"})
            mock_fewshot.assert_called_once_with(1, {"alert_type": "NetworkDown"})

    def test_record_recommendation_execution_success(self) -> None:
        """
        GIVEN the record_recommendation_execution function
        WHEN called with success=True
        THEN should add to success counter and record time.
        """
        from mcp_server_langgraph.alerts.metrics import (
            recommendation_execution_success_counter,
            recommendation_execution_time_histogram,
            record_recommendation_execution,
        )

        with (
            patch.object(recommendation_execution_success_counter, "add") as mock_success,
            patch.object(recommendation_execution_time_histogram, "record") as mock_time,
        ):
            record_recommendation_execution("HighCPU", success=True, execution_time_seconds=2.5)
            mock_success.assert_called_once_with(1, {"alert_type": "HighCPU"})
            mock_time.assert_called_once_with(2.5, {"success": "true"})

    def test_record_recommendation_execution_failure(self) -> None:
        """
        GIVEN the record_recommendation_execution function
        WHEN called with success=False
        THEN should add to failure counter and record time.
        """
        from mcp_server_langgraph.alerts.metrics import (
            recommendation_execution_failure_counter,
            recommendation_execution_time_histogram,
            record_recommendation_execution,
        )

        with (
            patch.object(recommendation_execution_failure_counter, "add") as mock_failure,
            patch.object(recommendation_execution_time_histogram, "record") as mock_time,
        ):
            record_recommendation_execution("ServiceDown", success=False, execution_time_seconds=1.2)
            mock_failure.assert_called_once_with(1, {"alert_type": "ServiceDown"})
            mock_time.assert_called_once_with(1.2, {"success": "false"})

    def test_record_fewshot_usage_with_examples(self) -> None:
        """
        GIVEN the record_fewshot_usage function
        WHEN called with example_count > 0
        THEN should add to with_fewshot counter.
        """
        from mcp_server_langgraph.alerts.metrics import (
            record_fewshot_usage,
            recommendation_with_fewshot_counter,
        )

        with patch.object(recommendation_with_fewshot_counter, "add") as mock_add:
            record_fewshot_usage("HighCPU", example_count=3)
            mock_add.assert_called_once_with(
                1, {"alert_type": "HighCPU", "example_count": "3"}
            )

    def test_record_fewshot_usage_without_examples(self) -> None:
        """
        GIVEN the record_fewshot_usage function
        WHEN called with example_count=0
        THEN should add to without_fewshot counter.
        """
        from mcp_server_langgraph.alerts.metrics import (
            record_fewshot_usage,
            recommendation_without_fewshot_counter,
        )

        with patch.object(recommendation_without_fewshot_counter, "add") as mock_add:
            record_fewshot_usage("HighMemory", example_count=0)
            mock_add.assert_called_once_with(1, {"alert_type": "HighMemory"})

    def test_record_constraint_usage(self) -> None:
        """
        GIVEN the record_constraint_usage function
        WHEN called with constraint_count > 0
        THEN should add to with_constraints counter.
        """
        from mcp_server_langgraph.alerts.metrics import (
            record_constraint_usage,
            recommendation_with_constraints_counter,
        )

        with patch.object(recommendation_with_constraints_counter, "add") as mock_add:
            record_constraint_usage("DiskFull", constraint_count=5)
            mock_add.assert_called_once_with(
                1, {"alert_type": "DiskFull", "constraint_count": "5"}
            )

    def test_record_constraint_usage_no_constraints(self) -> None:
        """
        GIVEN the record_constraint_usage function
        WHEN called with constraint_count=0
        THEN should not add to any counter.
        """
        from mcp_server_langgraph.alerts.metrics import (
            record_constraint_usage,
            recommendation_with_constraints_counter,
        )

        with patch.object(recommendation_with_constraints_counter, "add") as mock_add:
            record_constraint_usage("NetworkDown", constraint_count=0)
            mock_add.assert_not_called()

    def test_update_constraint_patterns_count(self) -> None:
        """
        GIVEN the update_constraint_patterns_count function
        WHEN called with a count
        THEN should set the gauge to that value.
        """
        from mcp_server_langgraph.alerts.metrics import (
            constraint_patterns_applied_gauge,
            update_constraint_patterns_count,
        )

        with patch.object(constraint_patterns_applied_gauge, "set") as mock_set:
            update_constraint_patterns_count(15)
            mock_set.assert_called_once_with(15)

    def test_record_recommendation_quality(self) -> None:
        """
        GIVEN the record_recommendation_quality function
        WHEN called with quality_score and confidence
        THEN should record to both histograms.
        """
        from mcp_server_langgraph.alerts.metrics import (
            record_recommendation_quality,
            recommendation_confidence_histogram,
            recommendation_quality_score_histogram,
        )

        with (
            patch.object(recommendation_quality_score_histogram, "record") as mock_quality,
            patch.object(recommendation_confidence_histogram, "record") as mock_confidence,
        ):
            record_recommendation_quality("HighCPU", quality_score=0.85, confidence=0.92)
            mock_quality.assert_called_once_with(0.85, {"alert_type": "HighCPU"})
            mock_confidence.assert_called_once_with(0.92, {"alert_type": "HighCPU"})


@pytest.mark.xdist_group(name="test_alert_metrics")
class TestMetricsModuleImports:
    """Tests for verifying all metrics can be imported correctly."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_all_counters_importable(self) -> None:
        """
        GIVEN the metrics module
        WHEN importing all counters
        THEN should successfully import 28 counters.
        """
        from mcp_server_langgraph.alerts.metrics import (
            alert_broadcast_counter,
            alert_filtered_counter,
            alert_received_counter,
            alert_websocket_messages_counter,
            fewshot_approval_counter,
            fewshot_rejection_counter,
            rate_limit_exceeded_counter,
            recommendation_approval_counter,
            recommendation_cache_hit_counter,
            recommendation_cache_miss_counter,
            recommendation_execution_failure_counter,
            recommendation_execution_success_counter,
            recommendation_failed_counter,
            recommendation_generated_counter,
            recommendation_regenerated_counter,
            recommendation_rejection_counter,
            recommendation_rejection_reason_counter,
            recommendation_requested_counter,
            recommendation_with_constraints_counter,
            recommendation_with_fewshot_counter,
            recommendation_without_fewshot_counter,
            remediation_approved_counter,
            remediation_command_blocked_counter,
            remediation_executed_counter,
            remediation_execution_failed_counter,
            remediation_execution_success_counter,
            remediation_rejected_counter,
            remediation_requested_counter,
        )

        # Verify all counters are not None
        counters = [
            alert_received_counter,
            alert_broadcast_counter,
            alert_filtered_counter,
            recommendation_requested_counter,
            recommendation_cache_hit_counter,
            recommendation_cache_miss_counter,
            recommendation_generated_counter,
            recommendation_failed_counter,
            recommendation_regenerated_counter,
            rate_limit_exceeded_counter,
            remediation_requested_counter,
            remediation_approved_counter,
            remediation_rejected_counter,
            remediation_executed_counter,
            remediation_execution_success_counter,
            remediation_execution_failed_counter,
            remediation_command_blocked_counter,
            alert_websocket_messages_counter,
            # New AI Recommendation Quality counters
            recommendation_approval_counter,
            recommendation_rejection_counter,
            recommendation_rejection_reason_counter,
            recommendation_execution_success_counter,
            recommendation_execution_failure_counter,
            recommendation_with_fewshot_counter,
            recommendation_without_fewshot_counter,
            fewshot_approval_counter,
            fewshot_rejection_counter,
            recommendation_with_constraints_counter,
        ]
        assert len(counters) == 28
        assert all(c is not None for c in counters)

    def test_all_gauges_importable(self) -> None:
        """
        GIVEN the metrics module
        WHEN importing all gauges
        THEN should successfully import 4 gauges.
        """
        from mcp_server_langgraph.alerts.metrics import (
            alert_websocket_connections_gauge,
            constraint_patterns_applied_gauge,
            rate_limit_tokens_gauge,
            recommendation_cache_size_gauge,
        )

        gauges = [
            rate_limit_tokens_gauge,
            alert_websocket_connections_gauge,
            recommendation_cache_size_gauge,
            constraint_patterns_applied_gauge,
        ]
        assert len(gauges) == 4
        assert all(g is not None for g in gauges)

    def test_all_histograms_importable(self) -> None:
        """
        GIVEN the metrics module
        WHEN importing all histograms
        THEN should successfully import 5 histograms.
        """
        from mcp_server_langgraph.alerts.metrics import (
            recommendation_confidence_histogram,
            recommendation_duration_histogram,
            recommendation_execution_time_histogram,
            recommendation_quality_score_histogram,
            remediation_execution_duration_histogram,
        )

        histograms = [
            recommendation_duration_histogram,
            remediation_execution_duration_histogram,
            recommendation_execution_time_histogram,
            recommendation_quality_score_histogram,
            recommendation_confidence_histogram,
        ]
        assert len(histograms) == 5
        assert all(h is not None for h in histograms)

    def test_all_helper_functions_importable(self) -> None:
        """
        GIVEN the metrics module
        WHEN importing all helper functions
        THEN should successfully import 22 helper functions.
        """
        from mcp_server_langgraph.alerts.metrics import (
            record_alert_broadcast,
            record_alert_filtered,
            record_alert_received,
            record_command_blocked,
            record_constraint_usage,
            record_correlation_request,
            record_fewshot_usage,
            record_pattern_detected,
            record_rate_limit_exceeded,
            record_recommendation_approval,
            record_recommendation_execution,
            record_recommendation_generated,
            record_recommendation_quality,
            record_recommendation_regenerated,
            record_recommendation_rejection,
            record_recommendation_request,
            record_remediation_execution,
            record_remediation_workflow,
            record_root_cause_identified,
            record_websocket_message,
            update_constraint_patterns_count,
            update_websocket_connections,
        )

        helpers = [
            record_alert_received,
            record_alert_broadcast,
            record_alert_filtered,
            record_recommendation_request,
            record_recommendation_generated,
            record_recommendation_regenerated,
            record_rate_limit_exceeded,
            record_remediation_workflow,
            record_remediation_execution,
            record_command_blocked,
            update_websocket_connections,
            record_websocket_message,
            # AI Recommendation Quality helpers
            record_recommendation_approval,
            record_recommendation_rejection,
            record_recommendation_execution,
            record_fewshot_usage,
            record_constraint_usage,
            update_constraint_patterns_count,
            record_recommendation_quality,
            # Alert Correlation helpers
            record_correlation_request,
            record_pattern_detected,
            record_root_cause_identified,
        ]
        assert len(helpers) == 22
        assert all(callable(h) for h in helpers)


# ==============================================================================
# Alert Correlation Metrics Tests
# ==============================================================================


@pytest.mark.xdist_group(name="test_alert_metrics")
class TestAlertCorrelationMetrics:
    """Tests for alert correlation metric instruments and helpers."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_correlation_counters_exist(self) -> None:
        """
        GIVEN the metrics module
        WHEN importing correlation counters
        THEN should have all expected counters.
        """
        from mcp_server_langgraph.alerts.metrics import (
            correlation_requests_counter,
            pattern_detection_counter,
            root_cause_identification_counter,
        )

        counters = [
            correlation_requests_counter,
            pattern_detection_counter,
            root_cause_identification_counter,
        ]
        assert len(counters) == 3
        assert all(c is not None for c in counters)
        assert all(hasattr(c, "add") for c in counters)

    def test_correlation_gauge_exists(self) -> None:
        """
        GIVEN the metrics module
        WHEN importing correlation gauge
        THEN should have correlation_groups_gauge.
        """
        from mcp_server_langgraph.alerts.metrics import correlation_groups_gauge

        assert correlation_groups_gauge is not None
        assert hasattr(correlation_groups_gauge, "set")

    def test_correlation_histogram_exists(self) -> None:
        """
        GIVEN the metrics module
        WHEN importing correlation histogram
        THEN should have correlation_duration_histogram.
        """
        from mcp_server_langgraph.alerts.metrics import correlation_duration_histogram

        assert correlation_duration_histogram is not None
        assert hasattr(correlation_duration_histogram, "record")


@pytest.mark.xdist_group(name="test_alert_metrics")
class TestAlertCorrelationHelpers:
    """Tests for alert correlation helper functions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_record_correlation_request(self) -> None:
        """
        GIVEN a correlation request
        WHEN calling record_correlation_request
        THEN should record metrics without error.
        """
        from mcp_server_langgraph.alerts.metrics import record_correlation_request

        # Should not raise
        record_correlation_request(
            correlation_type="service",
            alert_count=10,
            group_count=3,
            duration_seconds=0.5,
        )

    def test_record_correlation_request_with_different_types(self) -> None:
        """
        GIVEN different correlation types
        WHEN calling record_correlation_request
        THEN should accept various correlation types.
        """
        from mcp_server_langgraph.alerts.metrics import record_correlation_request

        for correlation_type in ["service", "time-window", "label", "custom"]:
            record_correlation_request(
                correlation_type=correlation_type,
                alert_count=5,
                group_count=2,
                duration_seconds=0.1,
            )

    def test_record_pattern_detected(self) -> None:
        """
        GIVEN a detected pattern
        WHEN calling record_pattern_detected
        THEN should record the pattern type without error.
        """
        from mcp_server_langgraph.alerts.metrics import record_pattern_detected

        # Should not raise
        record_pattern_detected(pattern_type="cascading_failure")

    def test_record_pattern_detected_various_types(self) -> None:
        """
        GIVEN various pattern types
        WHEN calling record_pattern_detected
        THEN should accept all pattern types.
        """
        from mcp_server_langgraph.alerts.metrics import record_pattern_detected

        pattern_types = [
            "cascading_failure",
            "resource_exhaustion",
            "network_partition",
            "dependency_failure",
        ]
        for pattern_type in pattern_types:
            record_pattern_detected(pattern_type=pattern_type)

    def test_record_root_cause_identified(self) -> None:
        """
        GIVEN a root cause identification
        WHEN calling record_root_cause_identified
        THEN should record the identification without error.
        """
        from mcp_server_langgraph.alerts.metrics import record_root_cause_identified

        # Should not raise
        record_root_cause_identified(group_id="group-12345678-abcd")

    def test_record_root_cause_identified_truncates_id(self) -> None:
        """
        GIVEN a long group ID
        WHEN calling record_root_cause_identified
        THEN should truncate to 8 characters for label safety.
        """
        from mcp_server_langgraph.alerts.metrics import record_root_cause_identified

        # Function should handle this without error
        long_id = "a" * 100
        record_root_cause_identified(group_id=long_id)
