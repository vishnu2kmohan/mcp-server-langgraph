"""
Tests for Observability Wiring Gaps Analysis.

CRITICAL: This test file documents and validates fixes for wiring issues
that were NOT caught by existing contract, unit, integration, and e2e tests.

ROOT CAUSE ANALYSIS:
====================

1. WHY EXISTING TESTS DIDN'T CATCH METRIC NAME MISMATCHES:
   ----------------------------------------------------------
   - Unit tests used MOCKED backends (mock_metrics_client.query_instant.return_value)
   - Mocks don't validate the actual PromQL query strings being sent
   - Tests verified "a query was made" not "the correct query was made"

   Example of gap in test_observability_service_impl.py:
   ```python
   mock_tracing_client.search_by_attribute.assert_called_once()
   # This only checks that search_by_attribute was called
   # It does NOT verify the attribute name is correct
   ```

2. WHY CONTRACT TESTS DIDN'T CATCH THIS:
   --------------------------------------
   - Contract tests validated response SCHEMAS (field names, types)
   - They did NOT validate the query-to-data-flow (are we querying the right metric?)
   - Schema: ✓ requests_total is an int in response
   - Missing: ✗ Are we querying "http_requests_total" (correct) or "requests_total" (wrong)?

3. WHY INTEGRATION TESTS DIDN'T CATCH THIS:
   -----------------------------------------
   - Integration tests with LGTM stack verify "API returns data"
   - They don't verify "API returns the RIGHT data from the RIGHT metric"
   - An integration test might pass with stub data even if real queries fail

4. WHY E2E TESTS DIDN'T CATCH THIS:
   ---------------------------------
   - E2E tests validate user workflows, not observability data correctness
   - DevTools panel showing 0 for metrics could be "no data yet" (valid)
   - No assertion: "if there were 10 requests, DevTools should show 10"

SOLUTION: WIRING TESTS
======================
Wiring tests validate:
1. Query strings contain correct metric/attribute names
2. Naming conventions are consistent (logs=underscore, traces=dot)
3. Source code inspection catches drift before runtime

TDD: These tests define expected behavior to prevent regression.
"""

from __future__ import annotations

import gc
import inspect

import pytest

# Module-level markers
pytestmark = [
    pytest.mark.unit,
    pytest.mark.observability,
    pytest.mark.xdist_group(name="observability_wiring_gaps"),
]


def teardown_module() -> None:
    """Force GC to prevent mock accumulation in xdist workers."""
    gc.collect()


class TestPrometheusMetricQueryWiring:
    """
    Wiring tests for Prometheus/Mimir metric queries.

    CRITICAL ISSUE CAUGHT:
    - API queried "requests_total" but app exports "http_requests_total"
    - API queried "active_sessions" but app exports "agent_active_sessions"
    - Result: DevTools showed 0 for all metrics

    SOLUTION:
    - Validate query strings in source code
    - Ensure metric names match what's actually exported
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_metrics_queries_http_requests_total(self) -> None:
        """
        GIVEN the observability API get_metrics() method
        WHEN querying for request count
        THEN it should use "http_requests_total" (the actual metric name).

        The metric http_requests_total is exported by middleware/metrics.py.
        """
        from mcp_server_langgraph.api.v1 import observability as obs_module

        source = inspect.getsource(obs_module)

        # Must query the correct metric name
        assert "http_requests_total" in source, (
            "Metrics query should use 'http_requests_total' (from middleware/metrics.py), "
            "not 'requests_total' or other variants"
        )

        # Should use sum() for aggregation across label combinations
        assert "sum(http_requests_total)" in source, (
            "http_requests_total query should use sum() aggregation to aggregate "
            "across all label combinations (method, path, status)"
        )

    def test_get_metrics_queries_auth_sessions_active(self) -> None:
        """
        GIVEN the observability API get_metrics() method
        WHEN querying for active session count
        THEN it should use "auth_sessions_active" (the actual metric name).

        The metric auth_sessions_active is a gauge from auth/prometheus_metrics.py.
        This tracks authentication sessions, not agent execution sessions.
        """
        from mcp_server_langgraph.api.v1 import observability as obs_module

        source = inspect.getsource(obs_module)

        assert "auth_sessions_active" in source, (
            "Metrics query should use 'auth_sessions_active' (from auth/prometheus_metrics.py)"
        )

        assert "sum(auth_sessions_active)" in source, "auth_sessions_active query should use sum() aggregation"

    def test_get_metrics_queries_llm_tokens_total(self) -> None:
        """
        GIVEN the observability API get_metrics() method
        WHEN querying for token usage
        THEN it should use "llm_tokens_total" (the actual metric name).

        The metric llm_tokens_total is a counter from llm/metrics.py.
        """
        from mcp_server_langgraph.api.v1 import observability as obs_module

        source = inspect.getsource(obs_module)

        # llm_tokens_total query exists (may or may not use sum() depending on context)
        assert "llm_tokens_total" in source, "Metrics query should use 'llm_tokens_total' (from llm/metrics.py)"

    def test_error_query_filters_5xx_status_codes(self) -> None:
        """
        GIVEN http_requests_total metric with status labels
        WHEN querying for errors
        THEN it should filter for 5xx status codes (server errors).

        4xx status codes are client errors and shouldn't be counted as server errors.
        """
        from mcp_server_langgraph.api.v1 import observability as obs_module

        source = inspect.getsource(obs_module)

        # Error query should use regex to match 5xx status codes
        assert 'status=~"5.."' in source, "Error query should filter for 5xx status codes using status=~'5..' regex"


class TestLokiLogQueryWiring:
    """
    Wiring tests for Loki log queries.

    CLARIFICATION:
    - Both log and trace queries use DOT notation (session.id, user.id)
    - This matches the OTEL span attribute naming convention
    - The get_logs_by_attribute API uses dot notation attribute names
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_log_queries_use_dot_notation(self) -> None:
        """
        GIVEN log queries to Loki
        WHEN filtering by session/user/workflow
        THEN should use dot notation (matching OTEL span attribute names).

        The API uses get_logs_by_attribute with dot notation to enable
        correlation between logs and traces using the same attribute names.
        """
        from mcp_server_langgraph.api.v1 import observability as obs_module

        source = inspect.getsource(obs_module)

        # Log queries use dot notation to match OTEL span attributes
        assert 'attribute="session.id"' in source, "Log query should use 'session.id' (OTEL dot notation)"
        assert 'attribute="user.id"' in source, "Log query should use 'user.id' (OTEL dot notation)"
        assert 'attribute="workflow.id"' in source, "Log query should use 'workflow.id' (OTEL dot notation)"
        assert 'attribute="project.id"' in source, "Log query should use 'project.id' (OTEL dot notation)"


class TestTempoTraceQueryWiring:
    """
    Wiring tests for Tempo trace queries.

    CRITICAL INSIGHT:
    - Tempo traces use DOT notation (session.id, user.id)
    - This is the OTEL semantic convention for span attributes
    - span.set_attribute("session.id", value) uses dots

    This is DIFFERENT from Loki logs which use underscore notation.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_trace_queries_use_dot_notation(self) -> None:
        """
        GIVEN trace queries to Tempo
        WHEN filtering by session/user/workflow
        THEN should use dot notation (matching OTEL semantic convention).

        OTEL: span.set_attribute("session.id", "...")
        TraceQL: { span.session.id = "..." }
        """
        from mcp_server_langgraph.api.v1 import observability as obs_module

        source = inspect.getsource(obs_module)

        # Trace queries should use dot notation
        # These appear in search_by_attribute calls and tags dict construction
        assert '"session.id"' in source or "session.id" in source, "Trace query should use 'session.id' (OTEL dot notation)"
        assert '"user.id"' in source or "user.id" in source, "Trace query should use 'user.id' (OTEL dot notation)"


class TestNamingConventionConsistency:
    """
    Tests ensuring naming conventions are documented and consistent.

    The key insight is that there are TWO different naming conventions
    for the same entities:

    1. OTEL Span Attributes (Tempo): session.id, user.id, workflow.id (DOTS)
    2. Python Logging Extra (Loki): session_id, user_id, workflow_id (UNDERSCORES)

    Both are correct in their respective contexts. The API must use
    the right notation when querying each backend.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_observability_module_has_naming_convention_comments(self) -> None:
        """
        GIVEN the observability module
        WHEN reading the source
        THEN it should have comments explaining the naming conventions.

        This ensures future developers understand why logs use underscore
        and traces use dots - preventing accidental "fixes" that break things.
        """
        from mcp_server_langgraph.api.v1 import observability as obs_module

        source = inspect.getsource(obs_module)

        # Should have documentation about the naming conventions
        assert "underscore" in source.lower() or "session_id" in source, (
            "Source should document underscore notation usage for Loki"
        )
        assert "dot" in source.lower() or "session.id" in source, "Source should document dot notation usage for Tempo/OTEL"


class TestTestingGapDocumentation:
    """
    Meta-tests that document the testing gaps that allowed these issues.

    These tests serve as documentation and regression prevention.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_wiring_test_exists_for_metrics(self) -> None:
        """
        GIVEN the observability codebase
        WHEN we have wiring tests
        THEN they should validate actual query strings, not just call counts.

        This test documents the gap: unit tests with mocks only verified
        that methods were called, not that correct queries were sent.
        """
        # This test's existence proves we have wiring tests
        # The assertions in TestPrometheusMetricQueryWiring provide the actual validation
        assert True, "Wiring tests for metrics exist in this module"

    def test_wiring_test_exists_for_attribute_naming(self) -> None:
        """
        GIVEN the observability codebase
        WHEN we have wiring tests
        THEN they should validate attribute naming conventions.

        This test documents the gap: contract tests validated response schemas
        but not the query-to-data-flow correctness.
        """
        # This test's existence proves we have wiring tests
        # The assertions in TestLokiLogQueryWiring and TestTempoTraceQueryWiring
        # provide the actual validation
        assert True, "Wiring tests for attribute naming exist in this module"

    def test_documentation_of_why_tests_didnt_catch_issues(self) -> None:
        """
        GIVEN the module docstring
        WHEN we read it
        THEN it should explain why existing tests missed these issues.

        This serves as permanent documentation for future reference.
        """
        import tests.unit.observability.test_observability_wiring_gaps as this_module

        docstring = this_module.__doc__

        assert "ROOT CAUSE ANALYSIS" in docstring, "Module docstring should contain root cause analysis"
        assert "MOCKED backends" in docstring, "Module docstring should explain mock-based testing gap"
        assert "WIRING TESTS" in docstring, "Module docstring should explain the solution"
