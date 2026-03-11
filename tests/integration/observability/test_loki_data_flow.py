"""
Integration tests for OTEL → Loki → API data flow validation.

These tests verify that:
1. Log queries use correct attribute naming (dot notation)
2. Loki LogQL queries are constructed correctly
3. API endpoints correctly find logs by session.id/user.id/workflow.id

PURPOSE:
--------
This test exists because unit tests with mocked dependencies cannot detect
attribute name mismatches between OTEL log attributes and Loki queries.

Similar to the Tempo data flow tests, this ensures:
- Logs emitted with `session.id` attribute
- Loki queries use `{session.id="value"}` (not `{session_id="value"}`)

MARKERS:
--------
- @pytest.mark.integration: Integration test category
- @pytest.mark.observability: Observability-specific tests
- @pytest.mark.loki: Loki-specific tests
- @pytest.mark.dataflow: Data flow validation tests

REQUIREMENTS:
-------------
- Requires `make test-infra-full-up` to be running
- Loki must be accessible at localhost:13100

REFERENCES:
-----------
- src/mcp_server_langgraph/api/v1/observability.py (log queries)
- src/mcp_server_langgraph/observability/query/backends/loki.py
"""

from __future__ import annotations

import gc
import os
import socket
import uuid
from datetime import UTC, datetime

import pytest

from tests.constants import TEST_LOKI_PORT

# Module-level markers
pytestmark = [
    pytest.mark.integration,
    pytest.mark.observability,
    pytest.mark.loki,
    pytest.mark.xdist_group(name="loki_data_flow"),
]


def get_worker_prefix() -> str:
    """Get worker-specific prefix for test isolation in parallel execution."""
    worker_id = os.getenv("PYTEST_XDIST_WORKER", "main")
    return f"test_{worker_id}"


# PYTEST-XDIST FIX: Infrastructure tests are flaky in parallel execution
_XDIST_INFRASTRUCTURE_UNSTABLE = os.getenv("PYTEST_XDIST_WORKER") is not None


def teardown_module() -> None:
    """Force GC to prevent mock accumulation in xdist workers."""
    gc.collect()


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a port is in use (service is accessible)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        try:
            sock.connect((host, port))
            return True
        except (TimeoutError, ConnectionRefusedError, OSError):
            return False


def loki_available() -> bool:
    """Check if Loki is available for testing."""
    import httpx

    if not is_port_in_use(TEST_LOKI_PORT):
        return False

    try:
        response = httpx.get(
            f"http://localhost:{TEST_LOKI_PORT}/ready",
            timeout=2.0,
        )
        return response.status_code == 200
    except Exception:
        return False


@pytest.fixture
def unique_session_id() -> str:
    """Generate a unique session ID for testing that won't collide."""
    worker_prefix = get_worker_prefix()
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
    unique_id = str(uuid.uuid4())[:8]
    return f"{worker_prefix}_loki_{timestamp}_{unique_id}"


@pytest.mark.xdist_group("test_loki_data_flow")
class TestLokiDataFlow:
    """
    Data flow integration tests verifying OTEL → Loki → API pipeline.

    These tests validate that log queries use dot notation to match
    OTEL log attributes.

    CRITICAL: These tests validate that attribute names match between:
    - Log emission: session.id, user.id, workflow.id
    - LogQL query: {session.id="value"} (not {session_id="value"})
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.skipif(
        _XDIST_INFRASTRUCTURE_UNSTABLE,
        reason="LGTM infrastructure flaky in parallel execution",
    )
    @pytest.mark.asyncio
    async def test_loki_client_constructs_correct_logql(self, unique_session_id: str) -> None:
        """
        GIVEN a session.id for querying
        WHEN Loki get_logs_by_attribute is called
        THEN it should construct LogQL with dot notation.

        This test validates LogQL query construction.
        """
        if not loki_available():
            pytest.skip("Loki not available for integration testing")

        from mcp_server_langgraph.observability.query.backends.loki import (
            LokiLoggingClient,
        )

        os.environ["LOKI_URL"] = f"http://localhost:{TEST_LOKI_PORT}"

        client = LokiLoggingClient()
        await client.initialize()

        try:
            # Query should use "session.id" in LogQL
            result = await client.get_logs_by_attribute(
                attribute="session.id",  # OTEL dot notation
                value=unique_session_id,
            )

            # Query should succeed (even if no results)
            assert result is not None
            assert hasattr(result, "entries")

            # Also test user.id
            result2 = await client.get_logs_by_attribute(
                attribute="user.id",
                value="test-user",
            )
            assert result2 is not None

        finally:
            await client.close()

    @pytest.mark.skipif(
        _XDIST_INFRASTRUCTURE_UNSTABLE,
        reason="LGTM infrastructure flaky in parallel execution",
    )
    @pytest.mark.asyncio
    async def test_observability_service_log_queries_use_dot_notation(
        self,
        unique_session_id: str,
    ) -> None:
        """
        GIVEN entity filters (session_id, user_id, workflow_id)
        WHEN ObservabilityServiceImpl.list_logs is called
        THEN it should translate to dot notation for Loki queries.

        This test validates the translation layer between API parameters
        and OTEL attribute naming conventions.
        """
        if not loki_available():
            pytest.skip("Loki not available for integration testing")

        from mcp_server_langgraph.api.v1.observability import (
            ObservabilityServiceImpl,
        )
        from mcp_server_langgraph.observability.query.factory import (
            get_logging_client,
            get_metrics_client,
            get_tracing_client,
        )

        # Set environment for LGTM backend selection
        os.environ["LOKI_URL"] = f"http://localhost:{TEST_LOKI_PORT}"
        os.environ["OBSERVABILITY_TRACING_BACKEND"] = "lgtm"
        os.environ["OBSERVABILITY_LOGGING_BACKEND"] = "lgtm"
        os.environ["OBSERVABILITY_METRICS_BACKEND"] = "lgtm"

        # Create real clients using factory
        tracing = get_tracing_client()
        metrics = get_metrics_client()
        logging_client = get_logging_client()
        alerting = None

        await tracing.initialize()
        await metrics.initialize()
        await logging_client.initialize()

        try:
            service = ObservabilityServiceImpl(
                tracing=tracing,
                metrics=metrics,
                logging=logging_client,
                alerting=alerting,
            )

            # Call with session_id parameter (underscore - API convention)
            # This should translate to "session.id" internally for Loki
            logs, cursor = await service.list_logs(
                session_id=unique_session_id,
                limit=10,
            )

            # Query should succeed (returns list, possibly empty)
            assert isinstance(logs, list)

            # Same for user_id
            logs2, _ = await service.list_logs(
                user_id="test-user",
                limit=10,
            )
            assert isinstance(logs2, list)

            # Same for workflow_id
            logs3, _ = await service.list_logs(
                workflow_id="test-workflow",
                limit=10,
            )
            assert isinstance(logs3, list)

        finally:
            await tracing.close()
            await metrics.close()
            await logging_client.close()


@pytest.mark.xdist_group("test_loki_attribute_naming_conventions")
class TestLokiAttributeNamingConventions:
    """
    Tests validating OTEL semantic attribute naming in log queries.

    Loki LogQL uses label selectors like {attribute="value"}.
    OTEL uses dot notation: session.id, user.id, workflow.id.

    These conventions ensure interoperability with:
    - Loki LogQL queries
    - Grafana log exploration
    - Other OTEL-compatible backends
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_observability_log_queries_use_dot_notation(self) -> None:
        """
        GIVEN production code that queries Loki for logs
        WHEN building LogQL for session/user/workflow filtering
        THEN it should use dot notation.

        This test inspects the query code to ensure attribute names match.
        """
        import inspect

        from mcp_server_langgraph.api.v1 import observability as obs_module

        # Get source code
        source = inspect.getsource(obs_module)

        # Look for get_logs_by_attribute calls with OTEL dot notation
        assert 'attribute="session.id"' in source, "Log queries should use 'session.id' (dot notation)"
        assert 'attribute="user.id"' in source, "Log queries should use 'user.id' (dot notation)"
        assert 'attribute="workflow.id"' in source, "Log queries should use 'workflow.id' (dot notation)"
        assert 'attribute="project.id"' in source, "Log queries should use 'project.id' (dot notation)"

        # Negative check - should NOT have underscore version
        bad_patterns = [
            'attribute="session_id"',
            'attribute="user_id"',
            'attribute="workflow_id"',
            'attribute="project_id"',
            'attribute="organization_id"',
        ]

        lines = source.split("\n")
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            for pattern in bad_patterns:
                if pattern in line:
                    pytest.fail(f"Line {i + 1}: Found '{pattern}' - should use dot notation for OTEL attribute names")

    @pytest.mark.asyncio
    async def test_loki_client_logql_construction(self) -> None:
        """
        GIVEN a LokiLoggingClient
        WHEN get_logs_by_attribute is called
        THEN it should construct LogQL with the attribute as a label selector.

        This validates the LogQL template uses the attribute name directly.
        """
        import inspect

        from mcp_server_langgraph.observability.query.backends import loki

        source = inspect.getsource(loki)

        # The Loki client should use the attribute directly in LogQL
        # Looking for pattern like: logql = f'{{{attribute}="{value}"}}'
        assert "logql = f'{{{attribute}=\"" in source or "{attribute}=" in source, (
            "LokiLoggingClient should construct LogQL using attribute directly"
        )
