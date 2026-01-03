"""
Tests for Prometheus/Mimir metrics query wiring.

These tests verify that the observability API queries use the correct metric names
that match what the application actually exports.

TDD: These tests define the expected behavior and catch metric name mismatches.

Similar to the BroadcastingSpanProcessor wiring tests, this ensures:
- Metric queries use correct PromQL metric names
- API responses match what's actually being measured
"""

from __future__ import annotations

import gc
import os

import pytest

# Module-level markers
pytestmark = [
    pytest.mark.unit,
    pytest.mark.observability,
    pytest.mark.xdist_group(name="metrics_query_wiring"),
]


def teardown_module() -> None:
    """Force GC to prevent mock accumulation in xdist workers."""
    gc.collect()


class TestMetricsQueryWiring:
    """
    Tests verifying that observability API queries use correct metric names.

    CRITICAL: These tests catch metric name mismatches between:
    - What metrics the application exports (e.g., http_requests_total)
    - What the observability API queries (must match exported names)

    Root cause of past issues:
    - API queried `requests_total` but app exports `http_requests_total`
    - API queried `active_sessions` but app exports `agent_active_sessions`
    - Result: DevTools showed 0 for all metrics even when app was under load
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_metrics_queries_use_correct_metric_names(self) -> None:
        """
        GIVEN the observability API get_metrics() method
        WHEN it queries for metrics
        THEN it should use the actual metric names from the application.

        This test validates by source code inspection that the correct
        metric names are used.
        """
        import inspect

        from mcp_server_langgraph.api.v1 import observability as obs_module

        source = inspect.getsource(obs_module)

        # Verify correct metric names are used
        # http_requests_total is the actual counter from middleware/metrics.py
        assert "http_requests_total" in source, (
            "Metrics query should use 'http_requests_total' not 'requests_total'"
        )

        # agent_active_sessions is the actual gauge from health/checks.py
        assert "agent_active_sessions" in source, (
            "Metrics query should use 'agent_active_sessions' not 'active_sessions'"
        )

        # llm_tokens_total is the actual counter from llm/metrics.py
        assert "llm_tokens_total" in source, (
            "Metrics query should use 'llm_tokens_total'"
        )

    def test_metrics_queries_use_sum_aggregation(self) -> None:
        """
        GIVEN metrics with labels
        WHEN querying aggregate values
        THEN should use sum() to aggregate across all label combinations.

        Without sum(), queries return multiple series and may get wrong values.
        """
        import inspect

        from mcp_server_langgraph.api.v1 import observability as obs_module

        source = inspect.getsource(obs_module)

        # All aggregate queries should use sum()
        assert "sum(http_requests_total)" in source, (
            "http_requests_total query should use sum() aggregation"
        )
        assert "sum(llm_tokens_total)" in source, (
            "llm_tokens_total query should use sum() aggregation"
        )
        assert "sum(agent_active_sessions)" in source, (
            "agent_active_sessions query should use sum() aggregation"
        )

    def test_error_query_filters_5xx_status(self) -> None:
        """
        GIVEN http_requests_total with status labels
        WHEN querying for errors
        THEN should filter for 5xx status codes.

        This ensures error count reflects actual server errors, not client errors (4xx).
        """
        import inspect

        from mcp_server_langgraph.api.v1 import observability as obs_module

        source = inspect.getsource(obs_module)

        # Error query should filter for 5xx status codes
        assert 'status=~"5.."' in source, (
            "Error query should filter for 5xx status codes using status=~'5..'"
        )


class TestLokiQueryWiring:
    """
    Tests verifying that log queries use correct attribute names for Loki.

    CRITICAL: There's a naming convention difference:
    - OTEL span attributes use dot notation: session.id, user.id
    - Python logging extra fields use underscore: session_id, user_id
    - Loki indexes logs with underscore (from Python logging convention)

    The API must use underscore notation for Loki log queries.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_log_queries_use_underscore_notation(self) -> None:
        """
        GIVEN log queries to Loki
        WHEN filtering by session/user/workflow
        THEN should use underscore notation (matching Loki labels from Python logging).

        Note: This is DIFFERENT from trace queries which use dot notation.
        """
        import inspect

        from mcp_server_langgraph.api.v1 import observability as obs_module

        source = inspect.getsource(obs_module)

        # Log queries should use underscore notation
        assert 'attribute="session_id"' in source, (
            "Log query should use 'session_id' (underscore) for Loki"
        )
        assert 'attribute="user_id"' in source, (
            "Log query should use 'user_id' (underscore) for Loki"
        )

    def test_trace_queries_use_dot_notation(self) -> None:
        """
        GIVEN trace queries to Tempo
        WHEN filtering by session/user/workflow
        THEN should use dot notation (OTEL semantic convention).

        Note: This is DIFFERENT from log queries which use underscore notation.
        """
        import inspect

        from mcp_server_langgraph.api.v1 import observability as obs_module

        source = inspect.getsource(obs_module)

        # Trace queries should use dot notation (OTEL semantic convention)
        # These appear in search_by_attribute calls for Tempo
        assert '"session.id"' in source, (
            "Trace query should use 'session.id' (OTEL dot notation)"
        )
        assert '"user.id"' in source, (
            "Trace query should use 'user.id' (OTEL dot notation)"
        )


class TestAlloyLokiLabelConfiguration:
    """
    Tests verifying Alloy config is consistent with Loki queries.

    The Alloy config in docker/alloy/config.alloy specifies which
    OTEL attributes to extract as Loki labels.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_alloy_config_labels_match_queries(self) -> None:
        """
        GIVEN the Alloy configuration for Loki label extraction
        WHEN Loki queries filter by attributes
        THEN the attribute names should match what Alloy indexes.

        This test reads the Alloy config and verifies consistency.
        """
        import os

        alloy_config_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..", "docker", "alloy", "config.alloy"
        )
        alloy_config_path = os.path.normpath(alloy_config_path)

        if not os.path.exists(alloy_config_path):
            pytest.skip("Alloy config not found (expected in docker/alloy/config.alloy)")

        with open(alloy_config_path) as f:
            alloy_config = f.read()

        # Verify labels extracted by Alloy match what we query
        # Alloy config uses: value = "session_id" (underscore)
        expected_labels = [
            "session_id",
            "user_id",
            "workflow_name",  # Note: workflow_name not workflow_id (bounded cardinality)
            "project_id",
            "organization_id",
            "trace_id",
        ]

        for label in expected_labels:
            assert f'value  = "{label}"' in alloy_config or f'value = "{label}"' in alloy_config, (
                f"Alloy config should extract '{label}' as a Loki label"
            )
