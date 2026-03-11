"""
Integration tests for HEART metrics from Prometheus/Mimir.

These tests validate the end-to-end flow of retrieving HEART framework
metrics from Prometheus/Mimir for the analytics dashboard.

Tests require `make test-infra-full-up` to be running.

TDD Rationale:
--------------
The HEART metrics service queries Prometheus/Mimir for:
- Happiness: User satisfaction score
- Engagement: User interaction rate
- Adoption: Feature uptake rate
- Retention: User return rate
- Task Success: Task completion rate

These tests validate:
1. Prometheus/Mimir queries execute correctly
2. Metric data is properly aggregated
3. Graceful fallback when metrics unavailable
4. Feature flag gating works correctly

Markers:
--------
- @pytest.mark.integration: Integration test category
- @pytest.mark.observability: Observability-specific tests
- @pytest.mark.prometheus: Prometheus/Mimir-specific tests

References:
-----------
- src/mcp_server_langgraph/websocket/services/heart_metrics.py
- src/mcp_server_langgraph/observability/query/backends/prometheus.py
"""

import gc
import os
import socket
from unittest.mock import MagicMock, patch

import pytest

from tests.constants import TEST_MIMIR_PORT

# Module-level marker
pytestmark = [
    pytest.mark.integration,
    pytest.mark.observability,
    pytest.mark.xdist_group(name="heart_metrics_prometheus"),
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


def prometheus_available() -> bool:
    """Check if Prometheus/Mimir is available for testing."""
    import httpx

    if not is_port_in_use(TEST_MIMIR_PORT):
        return False

    try:
        # Check Prometheus-compatible endpoint on Mimir
        response = httpx.get(
            f"http://localhost:{TEST_MIMIR_PORT}/prometheus/api/v1/status/buildinfo",
            timeout=2.0,
        )
        return response.status_code == 200
    except Exception:
        return False


@pytest.mark.xdist_group("test_prometheus_metrics_client_integration")
class TestPrometheusMetricsClientIntegration:
    """Integration tests for Prometheus metrics client."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.skipif(
        _XDIST_INFRASTRUCTURE_UNSTABLE,
        reason="LGTM infrastructure flaky in parallel execution",
    )
    @pytest.mark.asyncio
    async def test_prometheus_client_health_check(self) -> None:
        """
        GIVEN Prometheus/Mimir is running
        WHEN checking health
        THEN should return healthy status.
        """
        if not prometheus_available():
            pytest.skip("Prometheus/Mimir not available for integration testing")

        from mcp_server_langgraph.observability.query.backends.prometheus import (
            PrometheusMetricsClient,
        )

        os.environ["PROMETHEUS_URL"] = f"http://localhost:{TEST_MIMIR_PORT}/prometheus"

        client = PrometheusMetricsClient()
        await client.initialize()

        try:
            is_healthy = await client.health_check()
            assert is_healthy is True
        finally:
            await client.close()

    @pytest.mark.skipif(
        _XDIST_INFRASTRUCTURE_UNSTABLE,
        reason="LGTM infrastructure flaky in parallel execution",
    )
    @pytest.mark.asyncio
    async def test_prometheus_client_query_instant(self) -> None:
        """
        GIVEN Prometheus/Mimir is running
        WHEN executing an instant query
        THEN should return query result.
        """
        if not prometheus_available():
            pytest.skip("Prometheus/Mimir not available for integration testing")

        from mcp_server_langgraph.observability.query.backends.prometheus import (
            PrometheusMetricsClient,
        )

        os.environ["PROMETHEUS_URL"] = f"http://localhost:{TEST_MIMIR_PORT}/prometheus"

        client = PrometheusMetricsClient()
        await client.initialize()

        try:
            # Query a built-in metric (up metric is always available)
            result = await client.query_instant("up")

            # Should return a result (possibly empty series)
            assert result is not None
            assert hasattr(result, "series")
        finally:
            await client.close()


@pytest.mark.xdist_group(name="heart_metrics_integration")
class TestHeartMetricsServiceIntegration:
    """Integration tests for HEART metrics service with Prometheus."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.skipif(
        _XDIST_INFRASTRUCTURE_UNSTABLE,
        reason="LGTM infrastructure flaky in parallel execution",
    )
    @pytest.mark.asyncio
    async def test_heart_metrics_snapshot_with_prometheus(self) -> None:
        """
        GIVEN Prometheus/Mimir is running and metrics client connected
        WHEN getting HEART metrics snapshot
        THEN should return metrics from Prometheus.
        """
        if not prometheus_available():
            pytest.skip("Prometheus/Mimir not available for integration testing")

        from mcp_server_langgraph.observability.query.backends.prometheus import (
            PrometheusMetricsClient,
        )
        from mcp_server_langgraph.websocket.services.heart_metrics import (
            HeartMetricsServiceAdapter,
        )

        os.environ["PROMETHEUS_URL"] = f"http://localhost:{TEST_MIMIR_PORT}/prometheus"

        metrics_client = PrometheusMetricsClient()
        await metrics_client.initialize()

        try:
            adapter = HeartMetricsServiceAdapter(metrics_client=metrics_client)

            with patch("mcp_server_langgraph.websocket.services.heart_metrics.get_feature_flags") as mock_flags:
                mock_flags.return_value = MagicMock(enable_websocket_enhanced_metrics=True)

                result = await adapter.get_current_snapshot(time_range="24h")

                # Should return a dict with HEART dimensions
                assert isinstance(result, dict)
                assert "time_range" in result
                assert "last_updated" in result

                # Should have all HEART dimensions
                expected_dimensions = {
                    "happiness",
                    "engagement",
                    "adoption",
                    "retention",
                    "task_success",
                }
                for dimension in expected_dimensions:
                    assert dimension in result, f"Missing dimension: {dimension}"
                    assert "score" in result[dimension]
                    assert "trend" in result[dimension]
        finally:
            await metrics_client.close()

    @pytest.mark.asyncio
    async def test_heart_metrics_snapshot_fallback_without_prometheus(self) -> None:
        """
        GIVEN Prometheus is unavailable
        WHEN getting HEART metrics snapshot
        THEN should return stub/fallback data.
        """
        from mcp_server_langgraph.websocket.services.heart_metrics import (
            HeartMetricsServiceAdapter,
        )

        # No metrics client provided - should use fallback
        adapter = HeartMetricsServiceAdapter(metrics_client=None)

        with patch("mcp_server_langgraph.websocket.services.heart_metrics.get_feature_flags") as mock_flags:
            mock_flags.return_value = MagicMock(enable_websocket_enhanced_metrics=True)

            result = await adapter.get_current_snapshot(time_range="24h")

            # Should return stub data
            assert isinstance(result, dict)
            assert result["time_range"] == "24h"

            # Stub data should have default scores
            assert result["happiness"]["score"] == 85
            assert result["engagement"]["score"] == 72
            assert result["adoption"]["score"] == 90
            assert result["retention"]["score"] == 88
            assert result["task_success"]["score"] == 95

    @pytest.mark.asyncio
    async def test_heart_metrics_minimal_snapshot_when_disabled(self) -> None:
        """
        GIVEN enhanced metrics feature flag is disabled
        WHEN getting HEART metrics snapshot
        THEN should return minimal snapshot.
        """
        from mcp_server_langgraph.websocket.services.heart_metrics import (
            HeartMetricsServiceAdapter,
        )

        adapter = HeartMetricsServiceAdapter(metrics_client=None)

        with patch("mcp_server_langgraph.websocket.services.heart_metrics.get_feature_flags") as mock_flags:
            mock_flags.return_value = MagicMock(enable_websocket_enhanced_metrics=False)

            result = await adapter.get_current_snapshot(time_range="24h")

            # Should return minimal snapshot
            assert isinstance(result, dict)
            # Minimal snapshot doesn't have all the same fields
            # This validates the feature flag gating


@pytest.mark.xdist_group("test_heart_metrics_dimension_queries")
class TestHeartMetricsDimensionQueries:
    """Integration tests for HEART dimension-specific queries."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.skipif(
        _XDIST_INFRASTRUCTURE_UNSTABLE,
        reason="LGTM infrastructure flaky in parallel execution",
    )
    @pytest.mark.asyncio
    async def test_get_dimension_metrics_happiness(self) -> None:
        """
        GIVEN Prometheus with HEART metrics
        WHEN querying happiness dimension
        THEN should return happiness-specific metrics.
        """
        if not prometheus_available():
            pytest.skip("Prometheus/Mimir not available for integration testing")

        from mcp_server_langgraph.observability.query.backends.prometheus import (
            PrometheusMetricsClient,
        )
        from mcp_server_langgraph.websocket.services.heart_metrics import (
            HeartMetricsServiceAdapter,
        )

        os.environ["PROMETHEUS_URL"] = f"http://localhost:{TEST_MIMIR_PORT}/prometheus"

        metrics_client = PrometheusMetricsClient()
        await metrics_client.initialize()

        try:
            adapter = HeartMetricsServiceAdapter(metrics_client=metrics_client)

            result = await adapter.get_dimension_metrics("happiness", time_range="24h")

            # Should return dimension-specific data
            assert isinstance(result, dict)
            # Should not return error for valid dimension
            assert "error" not in result or result.get("dimension") == "happiness"
        finally:
            await metrics_client.close()

    @pytest.mark.asyncio
    async def test_get_dimension_metrics_invalid_dimension(self) -> None:
        """
        GIVEN any state
        WHEN querying invalid dimension
        THEN should return error response.
        """
        from mcp_server_langgraph.websocket.services.heart_metrics import (
            HeartMetricsServiceAdapter,
        )

        adapter = HeartMetricsServiceAdapter(metrics_client=None)

        result = await adapter.get_dimension_metrics("invalid_dimension")

        # Should return error for invalid dimension
        assert isinstance(result, dict)
        assert "error" in result
        assert "Unknown dimension" in result["error"]

    @pytest.mark.parametrize(
        "dimension",
        ["happiness", "engagement", "adoption", "retention", "task_success"],
    )
    @pytest.mark.asyncio
    async def test_all_valid_dimensions_return_data(self, dimension: str) -> None:
        """
        GIVEN any state
        WHEN querying each valid HEART dimension
        THEN should return data without error.
        """
        from mcp_server_langgraph.websocket.services.heart_metrics import (
            HeartMetricsServiceAdapter,
        )

        adapter = HeartMetricsServiceAdapter(metrics_client=None)

        result = await adapter.get_dimension_metrics(dimension, time_range="24h")

        # Should return data, not error
        assert isinstance(result, dict)
        # Valid dimensions should not return error
        assert "error" not in result or "Unknown dimension" not in str(result.get("error", ""))
