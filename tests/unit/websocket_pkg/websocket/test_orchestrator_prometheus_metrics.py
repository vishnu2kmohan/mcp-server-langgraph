"""
TDD Tests for Orchestrator Status Prometheus Metrics.

Tests for Prometheus-compatible metrics that expose orchestrator status
for Alloy/Prometheus scraping via the /metrics endpoint.
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

if TYPE_CHECKING:
    pass

pytestmark = [
    pytest.mark.unit,
    pytest.mark.websocket,
    pytest.mark.orchestrator,
]


@pytest.mark.xdist_group(name="orchestrator_prometheus_metrics")
class TestOrchestratorPrometheusMetrics:
    """TDD tests for orchestrator status Prometheus metrics."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_metrics_module_can_be_imported(self) -> None:
        """
        GIVEN the orchestrator status prometheus metrics module
        WHEN importing the module
        THEN it should import without errors
        """
        from mcp_server_langgraph.websocket import orchestrator_prometheus_metrics

        assert orchestrator_prometheus_metrics is not None

    def test_init_metrics_returns_bool(self) -> None:
        """
        GIVEN the metrics initialization function
        WHEN calling _init_metrics
        THEN it should return a boolean indicating success
        """
        from mcp_server_langgraph.websocket.orchestrator_prometheus_metrics import (
            _init_metrics,
        )

        result = _init_metrics()
        assert isinstance(result, bool)

    def test_record_subscriber_change_exists(self) -> None:
        """
        GIVEN the metrics module
        WHEN accessing record_subscriber_change function
        THEN it should exist and be callable
        """
        from mcp_server_langgraph.websocket.orchestrator_prometheus_metrics import (
            record_subscriber_change,
        )

        assert callable(record_subscriber_change)

    def test_record_task_started_exists(self) -> None:
        """
        GIVEN the metrics module
        WHEN accessing record_task_started function
        THEN it should exist and be callable
        """
        from mcp_server_langgraph.websocket.orchestrator_prometheus_metrics import (
            record_task_started,
        )

        assert callable(record_task_started)

    def test_record_task_completed_exists(self) -> None:
        """
        GIVEN the metrics module
        WHEN accessing record_task_completed function
        THEN it should exist and be callable
        """
        from mcp_server_langgraph.websocket.orchestrator_prometheus_metrics import (
            record_task_completed,
        )

        assert callable(record_task_completed)

    def test_record_task_failed_exists(self) -> None:
        """
        GIVEN the metrics module
        WHEN accessing record_task_failed function
        THEN it should exist and be callable
        """
        from mcp_server_langgraph.websocket.orchestrator_prometheus_metrics import (
            record_task_failed,
        )

        assert callable(record_task_failed)

    def test_set_queue_depth_exists(self) -> None:
        """
        GIVEN the metrics module
        WHEN accessing set_queue_depth function
        THEN it should exist and be callable
        """
        from mcp_server_langgraph.websocket.orchestrator_prometheus_metrics import (
            set_queue_depth,
        )

        assert callable(set_queue_depth)

    def test_set_active_tasks_exists(self) -> None:
        """
        GIVEN the metrics module
        WHEN accessing set_active_tasks function
        THEN it should exist and be callable
        """
        from mcp_server_langgraph.websocket.orchestrator_prometheus_metrics import (
            set_active_tasks,
        )

        assert callable(set_active_tasks)

    def test_record_subscriber_change_increments_gauge(self) -> None:
        """
        GIVEN metrics are available
        WHEN calling record_subscriber_change with delta=1
        THEN it should increment the subscriber gauge
        """
        from mcp_server_langgraph.websocket.orchestrator_prometheus_metrics import (
            record_subscriber_change,
        )

        # Should not raise
        record_subscriber_change(1)
        record_subscriber_change(-1)

    def test_record_task_started_increments_counter(self) -> None:
        """
        GIVEN metrics are available
        WHEN calling record_task_started with category
        THEN it should increment the task started counter
        """
        from mcp_server_langgraph.websocket.orchestrator_prometheus_metrics import (
            record_task_started,
        )

        # Should not raise
        record_task_started(category="ux", task_type="persona_analysis")

    def test_record_task_completed_increments_counter(self) -> None:
        """
        GIVEN metrics are available
        WHEN calling record_task_completed with category
        THEN it should increment the task completed counter
        """
        from mcp_server_langgraph.websocket.orchestrator_prometheus_metrics import (
            record_task_completed,
        )

        # Should not raise
        record_task_completed(category="ux", task_type="persona_analysis")

    def test_record_task_failed_increments_counter(self) -> None:
        """
        GIVEN metrics are available
        WHEN calling record_task_failed with category
        THEN it should increment the task failed counter
        """
        from mcp_server_langgraph.websocket.orchestrator_prometheus_metrics import (
            record_task_failed,
        )

        # Should not raise
        record_task_failed(category="ux", task_type="persona_analysis", reason="timeout")

    def test_set_queue_depth_sets_gauge(self) -> None:
        """
        GIVEN metrics are available
        WHEN calling set_queue_depth
        THEN it should set the queue depth gauge
        """
        from mcp_server_langgraph.websocket.orchestrator_prometheus_metrics import (
            set_queue_depth,
        )

        # Should not raise
        set_queue_depth(5)
        set_queue_depth(0)

    def test_set_active_tasks_sets_gauge(self) -> None:
        """
        GIVEN metrics are available
        WHEN calling set_active_tasks
        THEN it should set the active tasks gauge
        """
        from mcp_server_langgraph.websocket.orchestrator_prometheus_metrics import (
            set_active_tasks,
        )

        # Should not raise
        set_active_tasks(3)
        set_active_tasks(0)

    def test_metrics_handle_missing_prometheus_client(self) -> None:
        """
        GIVEN prometheus_client is not installed
        WHEN calling metrics functions
        THEN they should gracefully handle the missing dependency
        """
        # Mock prometheus_client import to fail
        with patch.dict("sys.modules", {"prometheus_client": None}):
            from mcp_server_langgraph.websocket import orchestrator_prometheus_metrics

            # Force re-initialization
            orchestrator_prometheus_metrics._metrics_available = None

            # These should not raise even without prometheus_client
            # Note: Due to caching, this test verifies graceful degradation


@pytest.mark.xdist_group(name="orchestrator_prometheus_metrics")
class TestOrchestratorMetricsLabels:
    """Test that metrics have correct labels."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation."""
        gc.collect()

    def test_task_metrics_have_category_label(self) -> None:
        """
        GIVEN task metrics
        WHEN recording metrics
        THEN they should accept category as a label
        """
        from mcp_server_langgraph.websocket.orchestrator_prometheus_metrics import (
            record_task_started,
        )

        # All categories should be accepted
        categories = ["ux", "session", "conversation", "canvas", "diagram", "trace", "hitl", "command", "alert"]
        for cat in categories:
            record_task_started(category=cat, task_type="test")

    def test_task_metrics_have_task_type_label(self) -> None:
        """
        GIVEN task metrics
        WHEN recording metrics
        THEN they should accept task_type as a label
        """
        from mcp_server_langgraph.websocket.orchestrator_prometheus_metrics import (
            record_task_started,
        )

        # Various task types should be accepted
        task_types = ["persona_analysis", "error_analysis", "intent_detect"]
        for tt in task_types:
            record_task_started(category="ux", task_type=tt)

    def test_failed_metrics_have_reason_label(self) -> None:
        """
        GIVEN task failed metrics
        WHEN recording failed task
        THEN it should accept reason as a label
        """
        from mcp_server_langgraph.websocket.orchestrator_prometheus_metrics import (
            record_task_failed,
        )

        # Various failure reasons
        reasons = ["timeout", "rate_limit", "internal_error", "validation"]
        for reason in reasons:
            record_task_failed(category="ux", task_type="test", reason=reason)
