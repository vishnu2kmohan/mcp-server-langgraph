"""
Push Notification Metrics Tests.

TDD tests for push notification observability metrics:
- Push notification success/failure counters
- Delivery latency histogram
- Subscription lifecycle metrics
- Cleanup job metrics

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

import gc
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [
    pytest.mark.unit,
    pytest.mark.notifications,
]


@pytest.mark.xdist_group(name="test_push_notification_metrics")
class TestPushNotificationMetrics:
    """Tests for push notification metrics recording."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_record_push_sent_success(self) -> None:
        """
        GIVEN a successful push notification delivery
        WHEN recording the metric
        THEN the success counter should increment with correct labels.
        """
        from mcp_server_langgraph.notifications.push_metrics import (
            record_push_sent,
        )

        # Mock the counter
        with patch(
            "mcp_server_langgraph.notifications.push_metrics.push_sent_counter"
        ) as mock_counter:
            record_push_sent(user_id="user-001", success=True)

            mock_counter.add.assert_called_once()
            call_args = mock_counter.add.call_args
            assert call_args[0][0] == 1  # Increment by 1
            labels = call_args[0][1]  # Labels are second positional arg
            assert labels["status"] == "success"

    def test_record_push_sent_failure(self) -> None:
        """
        GIVEN a failed push notification delivery
        WHEN recording the metric
        THEN the failure counter should increment with reason label.
        """
        from mcp_server_langgraph.notifications.push_metrics import (
            record_push_sent,
        )

        with patch(
            "mcp_server_langgraph.notifications.push_metrics.push_sent_counter"
        ) as mock_counter:
            record_push_sent(user_id="user-001", success=False, reason="expired")

            mock_counter.add.assert_called_once()
            call_args = mock_counter.add.call_args
            labels = call_args[0][1]  # Labels are second positional arg
            assert labels["status"] == "failure"
            assert labels["reason"] == "expired"

    def test_record_push_latency(self) -> None:
        """
        GIVEN a push notification delivery with measured latency
        WHEN recording the latency
        THEN the histogram should record the duration.
        """
        from mcp_server_langgraph.notifications.push_metrics import (
            record_push_latency,
        )

        with patch(
            "mcp_server_langgraph.notifications.push_metrics.push_latency_histogram"
        ) as mock_histogram:
            record_push_latency(duration_seconds=0.125)

            mock_histogram.record.assert_called_once()
            call_args = mock_histogram.record.call_args
            assert call_args[0][0] == 0.125

    def test_record_subscription_created(self) -> None:
        """
        GIVEN a new push subscription creation
        WHEN recording the metric
        THEN the creation counter should increment.
        """
        from mcp_server_langgraph.notifications.push_metrics import (
            record_subscription_created,
        )

        with patch(
            "mcp_server_langgraph.notifications.push_metrics.subscription_created_counter"
        ) as mock_counter:
            record_subscription_created(user_id="user-001")

            mock_counter.add.assert_called_once_with(1, {"user_id": "user-001"[:8]})

    def test_record_subscription_deleted(self) -> None:
        """
        GIVEN a push subscription deletion
        WHEN recording the metric
        THEN the deletion counter should increment with reason.
        """
        from mcp_server_langgraph.notifications.push_metrics import (
            record_subscription_deleted,
        )

        with patch(
            "mcp_server_langgraph.notifications.push_metrics.subscription_deleted_counter"
        ) as mock_counter:
            record_subscription_deleted(reason="expired")

            mock_counter.add.assert_called_once()
            call_args = mock_counter.add.call_args
            labels = call_args[0][1]  # Labels are second positional arg
            assert labels["reason"] == "expired"

    def test_record_subscription_expired(self) -> None:
        """
        GIVEN an expired push subscription detected
        WHEN recording the metric
        THEN the expired counter should increment.
        """
        from mcp_server_langgraph.notifications.push_metrics import (
            record_subscription_expired,
        )

        with patch(
            "mcp_server_langgraph.notifications.push_metrics.subscription_expired_counter"
        ) as mock_counter:
            record_subscription_expired()

            mock_counter.add.assert_called_once_with(1)

    def test_update_active_subscriptions_gauge(self) -> None:
        """
        GIVEN a count of active subscriptions
        WHEN updating the gauge
        THEN the gauge should be set to the new count.
        """
        from mcp_server_langgraph.notifications.push_metrics import (
            update_active_subscriptions,
        )

        with patch(
            "mcp_server_langgraph.notifications.push_metrics.active_subscriptions_gauge"
        ) as mock_gauge:
            update_active_subscriptions(count=42)

            mock_gauge.set.assert_called_once_with(42)


@pytest.mark.xdist_group(name="test_push_notification_metrics")
class TestCleanupJobMetrics:
    """Tests for subscription cleanup job metrics."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_record_cleanup_run(self) -> None:
        """
        GIVEN a cleanup job execution
        WHEN recording the run
        THEN the counter should increment with cleaned count.
        """
        from mcp_server_langgraph.notifications.push_metrics import (
            record_cleanup_run,
        )

        with patch(
            "mcp_server_langgraph.notifications.push_metrics.cleanup_runs_counter"
        ) as mock_counter:
            record_cleanup_run(cleaned_count=15, duration_seconds=2.5)

            mock_counter.add.assert_called_once()
            call_args = mock_counter.add.call_args
            assert call_args[0][0] == 1

    def test_record_cleanup_run_records_duration(self) -> None:
        """
        GIVEN a cleanup job execution with duration
        WHEN recording the run
        THEN the histogram should record the duration.
        """
        from mcp_server_langgraph.notifications.push_metrics import (
            record_cleanup_run,
        )

        with patch(
            "mcp_server_langgraph.notifications.push_metrics.cleanup_runs_counter"
        ):
            with patch(
                "mcp_server_langgraph.notifications.push_metrics.cleanup_duration_histogram"
            ) as mock_histogram:
                record_cleanup_run(cleaned_count=15, duration_seconds=2.5)

                mock_histogram.record.assert_called_once()
                call_args = mock_histogram.record.call_args
                assert call_args[0][0] == 2.5

    def test_record_cleanup_run_records_subscriptions_cleaned(self) -> None:
        """
        GIVEN a cleanup job that cleaned subscriptions
        WHEN recording the run
        THEN the cleaned counter should record the count.
        """
        from mcp_server_langgraph.notifications.push_metrics import (
            record_cleanup_run,
        )

        with patch(
            "mcp_server_langgraph.notifications.push_metrics.cleanup_runs_counter"
        ):
            with patch(
                "mcp_server_langgraph.notifications.push_metrics.cleanup_duration_histogram"
            ):
                with patch(
                    "mcp_server_langgraph.notifications.push_metrics.subscriptions_cleaned_counter"
                ) as mock_counter:
                    record_cleanup_run(cleaned_count=15, duration_seconds=2.5)

                    mock_counter.add.assert_called_once_with(15)
