"""
Tests for HEART Metrics Service Adapter.

TDD tests for HeartMetricsServiceAdapter - verifies HEART metrics retrieval
from Prometheus/Mimir and fallback to stub data.

Plan Reference: Phase 3.1 - HEART Metrics from Prometheus

PYTEST-XDIST FIX: Uses gc.collect() in teardown for memory safety.
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_langgraph.websocket.services.heart_metrics import (
    HeartMetricsServiceAdapter,
    reset_websocket_heart_metrics_service,
)

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="heart_metrics_service")
class TestHeartMetricsServiceSnapshot:
    """Tests for HeartMetricsServiceAdapter get_current_snapshot."""

    def setup_method(self) -> None:
        """Reset singleton before each test."""
        reset_websocket_heart_metrics_service()

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation."""
        reset_websocket_heart_metrics_service()
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_current_snapshot_queries_prometheus(self) -> None:
        """get_current_snapshot queries Prometheus when client available."""
        mock_client = AsyncMock(return_value=None)
        mock_result = MagicMock()
        mock_series = MagicMock()
        mock_value = MagicMock()
        mock_value.value = 85.5
        mock_series.values = [mock_value]
        mock_result.series = [mock_series]
        mock_client.query_instant.return_value = mock_result

        adapter = HeartMetricsServiceAdapter(metrics_client=mock_client)

        with patch("mcp_server_langgraph.websocket.services.heart_metrics.get_feature_flags") as mock_flags:
            mock_flags.return_value = MagicMock(enable_websocket_enhanced_metrics=True)
            result = await adapter.get_current_snapshot("24h")

        # Should have queried all 5 HEART dimensions
        assert mock_client.query_instant.call_count == 5
        assert result["happiness"]["score"] == 85.5
        assert result["time_range"] == "24h"
        assert "last_updated" in result

    @pytest.mark.asyncio
    async def test_get_current_snapshot_returns_stub_without_client(self) -> None:
        """get_current_snapshot returns stub data when no Prometheus client."""
        adapter = HeartMetricsServiceAdapter(metrics_client=None)

        with patch("mcp_server_langgraph.websocket.services.heart_metrics.get_feature_flags") as mock_flags:
            mock_flags.return_value = MagicMock(enable_websocket_enhanced_metrics=True)
            result = await adapter.get_current_snapshot("24h")

        # Should return stub data with all dimensions
        assert result["happiness"]["score"] == 85
        assert result["engagement"]["score"] == 72
        assert result["adoption"]["score"] == 90
        assert result["retention"]["score"] == 88
        assert result["task_success"]["score"] == 95
        assert result["time_range"] == "24h"

    @pytest.mark.asyncio
    async def test_get_current_snapshot_falls_back_on_prometheus_error(self) -> None:
        """get_current_snapshot returns zeros when all Prometheus queries fail."""
        mock_client = AsyncMock(return_value=None)
        mock_client.query_instant.side_effect = Exception("Prometheus connection failed")

        adapter = HeartMetricsServiceAdapter(metrics_client=mock_client)

        with patch("mcp_server_langgraph.websocket.services.heart_metrics.get_feature_flags") as mock_flags:
            mock_flags.return_value = MagicMock(enable_websocket_enhanced_metrics=True)
            result = await adapter.get_current_snapshot("7d")

        # When individual queries fail, dimensions get zero scores (graceful degradation)
        assert result["happiness"]["score"] == 0
        assert result["happiness"]["trend"] == "stable"
        assert result["time_range"] == "7d"

    @pytest.mark.asyncio
    async def test_minimal_snapshot_when_metrics_disabled(self) -> None:
        """get_current_snapshot returns minimal data when enhanced metrics disabled."""
        adapter = HeartMetricsServiceAdapter(metrics_client=None)

        with patch("mcp_server_langgraph.websocket.services.heart_metrics.get_feature_flags") as mock_flags:
            mock_flags.return_value = MagicMock(enable_websocket_enhanced_metrics=False)
            result = await adapter.get_current_snapshot("24h")

        # Should return minimal snapshot with zero scores
        assert result["happiness"]["score"] == 0
        assert result["engagement"]["score"] == 0
        assert result["adoption"]["score"] == 0
        assert result["retention"]["score"] == 0
        assert result["task_success"]["score"] == 0
        assert result["metrics_enabled"] is False

    @pytest.mark.asyncio
    async def test_get_current_snapshot_handles_empty_prometheus_result(self) -> None:
        """get_current_snapshot handles empty Prometheus results gracefully."""
        mock_client = AsyncMock(return_value=None)
        mock_result = MagicMock()
        mock_result.series = []  # Empty result
        mock_client.query_instant.return_value = mock_result

        adapter = HeartMetricsServiceAdapter(metrics_client=mock_client)

        with patch("mcp_server_langgraph.websocket.services.heart_metrics.get_feature_flags") as mock_flags:
            mock_flags.return_value = MagicMock(enable_websocket_enhanced_metrics=True)
            result = await adapter.get_current_snapshot("24h")

        # Should return zeros for dimensions with no data
        assert result["happiness"]["score"] == 0
        assert result["happiness"]["trend"] == "stable"


@pytest.mark.unit
@pytest.mark.xdist_group(name="heart_metrics_service")
class TestHeartMetricsServiceDimension:
    """Tests for HeartMetricsServiceAdapter get_dimension_metrics."""

    def setup_method(self) -> None:
        """Reset singleton before each test."""
        reset_websocket_heart_metrics_service()

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation."""
        reset_websocket_heart_metrics_service()
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_dimension_metrics_queries_prometheus(self) -> None:
        """get_dimension_metrics queries specific metric from Prometheus."""
        mock_client = AsyncMock(return_value=None)
        mock_result = MagicMock()
        mock_series = MagicMock()
        mock_value = MagicMock()
        mock_value.value = 92.3
        mock_series.values = [mock_value]
        mock_result.series = [mock_series]
        mock_client.query_instant.return_value = mock_result

        adapter = HeartMetricsServiceAdapter(metrics_client=mock_client)
        result = await adapter.get_dimension_metrics("task_success", "7d")

        # Should query the specific metric
        mock_client.query_instant.assert_called_once_with("heart_task_success_rate")
        assert result["score"] == 92.3
        assert result["trend"] == "stable"

    @pytest.mark.asyncio
    async def test_get_dimension_metrics_returns_stub_without_client(self) -> None:
        """get_dimension_metrics returns stub data when no Prometheus client."""
        adapter = HeartMetricsServiceAdapter(metrics_client=None)
        result = await adapter.get_dimension_metrics("engagement", "24h")

        # Should return stub data with breakdown
        assert result["score"] == 72
        assert result["trend"] == "stable"
        assert result["samples"] == 3400
        assert "breakdown" in result
        assert result["breakdown"]["sessions_per_user"] == 3.2

    @pytest.mark.asyncio
    async def test_get_dimension_metrics_invalid_dimension_returns_error(self) -> None:
        """get_dimension_metrics returns error for invalid dimension."""
        adapter = HeartMetricsServiceAdapter(metrics_client=None)
        result = await adapter.get_dimension_metrics("invalid_dimension", "24h")

        assert "error" in result
        assert "Unknown dimension" in result["error"]

    @pytest.mark.asyncio
    async def test_get_dimension_metrics_falls_back_on_error(self) -> None:
        """get_dimension_metrics falls back to stub on Prometheus error."""
        mock_client = AsyncMock(return_value=None)
        mock_client.query_instant.side_effect = Exception("Query failed")

        adapter = HeartMetricsServiceAdapter(metrics_client=mock_client)
        result = await adapter.get_dimension_metrics("happiness", "24h")

        # Should fall back to stub data
        assert result["score"] == 85
        assert result["breakdown"]["response_quality"] == 88

    @pytest.mark.asyncio
    async def test_get_dimension_metrics_all_dimensions_valid(self) -> None:
        """get_dimension_metrics accepts all valid HEART dimensions."""
        adapter = HeartMetricsServiceAdapter(metrics_client=None)

        valid_dimensions = ["happiness", "engagement", "adoption", "retention", "task_success"]

        for dimension in valid_dimensions:
            result = await adapter.get_dimension_metrics(dimension, "24h")
            assert "error" not in result
            assert "score" in result
            assert result["score"] > 0


@pytest.mark.unit
@pytest.mark.xdist_group(name="heart_metrics_service")
class TestHeartMetricsServiceSingleton:
    """Tests for HEART metrics service singleton management."""

    def setup_method(self) -> None:
        """Reset singleton before each test."""
        reset_websocket_heart_metrics_service()

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation."""
        reset_websocket_heart_metrics_service()
        gc.collect()

    def test_reset_clears_singleton(self) -> None:
        """reset_websocket_heart_metrics_service clears the singleton."""

        # After reset, singleton should be None
        reset_websocket_heart_metrics_service()

        # Import the module-level variable again to check
        import mcp_server_langgraph.websocket.services.heart_metrics as module

        assert module._websocket_heart_metrics_service is None

    def test_get_service_creates_singleton(self) -> None:
        """get_websocket_heart_metrics_service creates singleton on first call."""
        from mcp_server_langgraph.websocket.services.heart_metrics import (
            get_websocket_heart_metrics_service,
        )

        # Patch at the import location (inside get_websocket_heart_metrics_service)
        with patch("mcp_server_langgraph.observability.query.factory.get_metrics_client") as mock_get_client:
            mock_get_client.return_value = None

            service1 = get_websocket_heart_metrics_service()
            service2 = get_websocket_heart_metrics_service()

            # Should return same instance
            assert service1 is service2


@pytest.mark.unit
@pytest.mark.xdist_group(name="heart_metrics_service")
class TestHeartMetricsPrometheusIntegration:
    """Tests for Prometheus query behavior."""

    def setup_method(self) -> None:
        """Reset singleton before each test."""
        reset_websocket_heart_metrics_service()

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation."""
        reset_websocket_heart_metrics_service()
        gc.collect()

    @pytest.mark.asyncio
    async def test_queries_correct_metric_names(self) -> None:
        """Prometheus queries use correct metric names for each dimension."""
        mock_client = AsyncMock(return_value=None)
        mock_result = MagicMock()
        mock_result.series = []
        mock_client.query_instant.return_value = mock_result

        adapter = HeartMetricsServiceAdapter(metrics_client=mock_client)

        with patch("mcp_server_langgraph.websocket.services.heart_metrics.get_feature_flags") as mock_flags:
            mock_flags.return_value = MagicMock(enable_websocket_enhanced_metrics=True)
            await adapter.get_current_snapshot("24h")

        # Verify correct metric names were queried
        queried_metrics = [call[0][0] for call in mock_client.query_instant.call_args_list]
        assert "heart_happiness_score" in queried_metrics
        assert "heart_engagement_rate" in queried_metrics
        assert "heart_adoption_rate" in queried_metrics
        assert "heart_retention_rate" in queried_metrics
        assert "heart_task_success_rate" in queried_metrics

    @pytest.mark.asyncio
    async def test_handles_partial_prometheus_failure(self) -> None:
        """Snapshot returns partial data when some metrics fail."""
        mock_client = AsyncMock(return_value=None)

        # First call succeeds, rest fail
        mock_result_success = MagicMock()
        mock_series = MagicMock()
        mock_value = MagicMock()
        mock_value.value = 88.0
        mock_series.values = [mock_value]
        mock_result_success.series = [mock_series]

        mock_client.query_instant.side_effect = [
            mock_result_success,  # happiness succeeds
            Exception("Failed"),  # engagement fails
            Exception("Failed"),  # adoption fails
            Exception("Failed"),  # retention fails
            Exception("Failed"),  # task_success fails
        ]

        adapter = HeartMetricsServiceAdapter(metrics_client=mock_client)

        with patch("mcp_server_langgraph.websocket.services.heart_metrics.get_feature_flags") as mock_flags:
            mock_flags.return_value = MagicMock(enable_websocket_enhanced_metrics=True)
            result = await adapter.get_current_snapshot("24h")

        # Happiness should have real value, others should be zeros
        assert result["happiness"]["score"] == 88.0
        assert result["engagement"]["score"] == 0
        assert result["adoption"]["score"] == 0

    @pytest.mark.asyncio
    async def test_rounds_prometheus_values(self) -> None:
        """Prometheus values are rounded to 1 decimal place."""
        mock_client = AsyncMock(return_value=None)
        mock_result = MagicMock()
        mock_series = MagicMock()
        mock_value = MagicMock()
        mock_value.value = 85.5678  # Should be rounded to 85.6
        mock_series.values = [mock_value]
        mock_result.series = [mock_series]
        mock_client.query_instant.return_value = mock_result

        adapter = HeartMetricsServiceAdapter(metrics_client=mock_client)

        with patch("mcp_server_langgraph.websocket.services.heart_metrics.get_feature_flags") as mock_flags:
            mock_flags.return_value = MagicMock(enable_websocket_enhanced_metrics=True)
            result = await adapter.get_current_snapshot("24h")

        assert result["happiness"]["score"] == 85.6
