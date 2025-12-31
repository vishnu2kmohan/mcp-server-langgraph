"""Unit tests for WebSocket HeartMetricsServiceAdapter.

Tests the HeartMetricsServiceAdapter that provides HEART framework metrics
for WebSocket handlers.

HEART Framework:
- Happiness: User satisfaction
- Engagement: User activity levels
- Adoption: Feature uptake
- Retention: User return rate
- Task success: Completion rates
"""

from __future__ import annotations

import gc
from unittest.mock import MagicMock, patch

import pytest

# Module-level marker for test discovery
pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="websocket_services_heart_metrics")
class TestHeartMetricsServiceAdapter:
    """Test suite for HeartMetricsServiceAdapter."""

    def teardown_method(self) -> None:
        """Force GC and reset singleton to prevent mock accumulation."""
        from mcp_server_langgraph.websocket.services.heart_metrics import (
            reset_websocket_heart_metrics_service,
        )

        reset_websocket_heart_metrics_service()
        gc.collect()

    def test_init_creates_empty_caches(self) -> None:
        """Test adapter initialization creates empty caches."""
        from mcp_server_langgraph.websocket.services.heart_metrics import (
            HeartMetricsServiceAdapter,
        )

        adapter = HeartMetricsServiceAdapter()

        assert adapter._cached_snapshot is None
        assert adapter._cached_dimensions == {}

    @pytest.mark.asyncio
    async def test_get_current_snapshot_with_metrics_enabled(self) -> None:
        """Test get_current_snapshot returns full data when metrics enabled."""
        from mcp_server_langgraph.websocket.services.heart_metrics import (
            HeartMetricsServiceAdapter,
        )

        adapter = HeartMetricsServiceAdapter()

        with patch("mcp_server_langgraph.websocket.services.heart_metrics.get_feature_flags") as mock_flags:
            mock_ff = MagicMock()
            mock_ff.enable_websocket_enhanced_metrics = True
            mock_flags.return_value = mock_ff

            result = await adapter.get_current_snapshot()

            # Check all HEART dimensions are present
            assert "happiness" in result
            assert "engagement" in result
            assert "adoption" in result
            assert "retention" in result
            assert "task_success" in result
            assert "time_range" in result
            assert "last_updated" in result

            # Check structure of dimension data
            assert "score" in result["happiness"]
            assert "trend" in result["happiness"]
            assert "change" in result["happiness"]

    @pytest.mark.asyncio
    async def test_get_current_snapshot_with_custom_time_range(self) -> None:
        """Test get_current_snapshot with custom time range."""
        from mcp_server_langgraph.websocket.services.heart_metrics import (
            HeartMetricsServiceAdapter,
        )

        adapter = HeartMetricsServiceAdapter()

        with patch("mcp_server_langgraph.websocket.services.heart_metrics.get_feature_flags") as mock_flags:
            mock_ff = MagicMock()
            mock_ff.enable_websocket_enhanced_metrics = True
            mock_flags.return_value = mock_ff

            result = await adapter.get_current_snapshot(time_range="7d")

            assert result["time_range"] == "7d"

    @pytest.mark.asyncio
    async def test_get_current_snapshot_with_metrics_disabled(self) -> None:
        """Test get_current_snapshot returns minimal data when metrics disabled."""
        from mcp_server_langgraph.websocket.services.heart_metrics import (
            HeartMetricsServiceAdapter,
        )

        adapter = HeartMetricsServiceAdapter()

        with patch("mcp_server_langgraph.websocket.services.heart_metrics.get_feature_flags") as mock_flags:
            mock_ff = MagicMock()
            mock_ff.enable_websocket_enhanced_metrics = False
            mock_flags.return_value = mock_ff

            result = await adapter.get_current_snapshot()

            # Check minimal data
            assert result["metrics_enabled"] is False
            assert result["happiness"]["score"] == 0
            assert result["engagement"]["score"] == 0
            assert result["adoption"]["score"] == 0
            assert result["retention"]["score"] == 0
            assert result["task_success"]["score"] == 0

    @pytest.mark.asyncio
    async def test_get_dimension_metrics_happiness(self) -> None:
        """Test get_dimension_metrics for happiness dimension."""
        from mcp_server_langgraph.websocket.services.heart_metrics import (
            HeartMetricsServiceAdapter,
        )

        adapter = HeartMetricsServiceAdapter()

        result = await adapter.get_dimension_metrics("happiness")

        assert result["score"] == 85
        assert result["trend"] == "up"
        assert "breakdown" in result
        assert "response_quality" in result["breakdown"]
        assert "response_speed" in result["breakdown"]
        assert "error_rate" in result["breakdown"]

    @pytest.mark.asyncio
    async def test_get_dimension_metrics_engagement(self) -> None:
        """Test get_dimension_metrics for engagement dimension."""
        from mcp_server_langgraph.websocket.services.heart_metrics import (
            HeartMetricsServiceAdapter,
        )

        adapter = HeartMetricsServiceAdapter()

        result = await adapter.get_dimension_metrics("engagement")

        assert result["score"] == 72
        assert result["trend"] == "stable"
        assert "breakdown" in result
        assert "sessions_per_user" in result["breakdown"]
        assert "messages_per_session" in result["breakdown"]

    @pytest.mark.asyncio
    async def test_get_dimension_metrics_adoption(self) -> None:
        """Test get_dimension_metrics for adoption dimension."""
        from mcp_server_langgraph.websocket.services.heart_metrics import (
            HeartMetricsServiceAdapter,
        )

        adapter = HeartMetricsServiceAdapter()

        result = await adapter.get_dimension_metrics("adoption")

        assert result["score"] == 90
        assert result["trend"] == "up"
        assert "breakdown" in result
        assert "new_users" in result["breakdown"]
        assert "onboarding_completion" in result["breakdown"]

    @pytest.mark.asyncio
    async def test_get_dimension_metrics_retention(self) -> None:
        """Test get_dimension_metrics for retention dimension."""
        from mcp_server_langgraph.websocket.services.heart_metrics import (
            HeartMetricsServiceAdapter,
        )

        adapter = HeartMetricsServiceAdapter()

        result = await adapter.get_dimension_metrics("retention")

        assert result["score"] == 88
        assert result["trend"] == "stable"
        assert "breakdown" in result
        assert "day_1" in result["breakdown"]
        assert "day_7" in result["breakdown"]
        assert "day_30" in result["breakdown"]

    @pytest.mark.asyncio
    async def test_get_dimension_metrics_task_success(self) -> None:
        """Test get_dimension_metrics for task_success dimension."""
        from mcp_server_langgraph.websocket.services.heart_metrics import (
            HeartMetricsServiceAdapter,
        )

        adapter = HeartMetricsServiceAdapter()

        result = await adapter.get_dimension_metrics("task_success")

        assert result["score"] == 95
        assert result["trend"] == "up"
        assert "breakdown" in result
        assert "completion_rate" in result["breakdown"]
        assert "error_recovery" in result["breakdown"]
        assert "avg_attempts" in result["breakdown"]

    @pytest.mark.asyncio
    async def test_get_dimension_metrics_unknown_dimension(self) -> None:
        """Test get_dimension_metrics with unknown dimension returns error."""
        from mcp_server_langgraph.websocket.services.heart_metrics import (
            HeartMetricsServiceAdapter,
        )

        adapter = HeartMetricsServiceAdapter()

        result = await adapter.get_dimension_metrics("unknown_dimension")

        assert "error" in result
        assert "Unknown dimension" in result["error"]

    @pytest.mark.asyncio
    async def test_get_dimension_metrics_with_time_range(self) -> None:
        """Test get_dimension_metrics accepts time_range parameter."""
        from mcp_server_langgraph.websocket.services.heart_metrics import (
            HeartMetricsServiceAdapter,
        )

        adapter = HeartMetricsServiceAdapter()

        # Should not raise, time_range is accepted but not used in stub
        result = await adapter.get_dimension_metrics("happiness", time_range="30d")

        assert "score" in result

    def test_get_minimal_snapshot(self) -> None:
        """Test _get_minimal_snapshot returns minimal data structure."""
        from mcp_server_langgraph.websocket.services.heart_metrics import (
            HeartMetricsServiceAdapter,
        )

        adapter = HeartMetricsServiceAdapter()

        result = adapter._get_minimal_snapshot()

        assert result["metrics_enabled"] is False
        for dimension in ["happiness", "engagement", "adoption", "retention", "task_success"]:
            assert result[dimension]["score"] == 0
            assert result[dimension]["trend"] == "stable"


@pytest.mark.unit
@pytest.mark.xdist_group(name="websocket_services_heart_metrics")
class TestHeartMetricsSingleton:
    """Test suite for HEART metrics service singleton functions."""

    def teardown_method(self) -> None:
        """Force GC and reset singleton to prevent mock accumulation."""
        from mcp_server_langgraph.websocket.services.heart_metrics import (
            reset_websocket_heart_metrics_service,
        )

        reset_websocket_heart_metrics_service()
        gc.collect()

    def test_get_websocket_heart_metrics_service_creates_singleton(self) -> None:
        """Test get_websocket_heart_metrics_service creates singleton instance."""
        from mcp_server_langgraph.websocket.services.heart_metrics import (
            get_websocket_heart_metrics_service,
            HeartMetricsServiceAdapter,
        )

        result = get_websocket_heart_metrics_service()

        assert isinstance(result, HeartMetricsServiceAdapter)

    def test_get_websocket_heart_metrics_service_returns_same_instance(self) -> None:
        """Test get_websocket_heart_metrics_service returns same instance."""
        from mcp_server_langgraph.websocket.services.heart_metrics import (
            get_websocket_heart_metrics_service,
        )

        result1 = get_websocket_heart_metrics_service()
        result2 = get_websocket_heart_metrics_service()

        assert result1 is result2

    def test_reset_websocket_heart_metrics_service_clears_singleton(self) -> None:
        """Test reset_websocket_heart_metrics_service clears singleton."""
        from mcp_server_langgraph.websocket.services.heart_metrics import (
            get_websocket_heart_metrics_service,
            reset_websocket_heart_metrics_service,
        )

        first = get_websocket_heart_metrics_service()
        reset_websocket_heart_metrics_service()
        second = get_websocket_heart_metrics_service()

        assert first is not second


@pytest.mark.unit
@pytest.mark.xdist_group(name="websocket_services_heart_metrics")
class TestHeartDimensionValidation:
    """Test suite for HEART dimension validation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation."""
        gc.collect()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "dimension",
        [
            "happiness",
            "engagement",
            "adoption",
            "retention",
            "task_success",
        ],
    )
    async def test_all_valid_dimensions(self, dimension: str) -> None:
        """Test all valid HEART dimensions return data without error."""
        from mcp_server_langgraph.websocket.services.heart_metrics import (
            HeartMetricsServiceAdapter,
        )

        adapter = HeartMetricsServiceAdapter()

        result = await adapter.get_dimension_metrics(dimension)

        assert "error" not in result
        assert "score" in result

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "invalid_dimension",
        [
            "invalid",
            "performance",
            "latency",
            "happy",  # Close but not exact
            "HAPPINESS",  # Case sensitive
            "",
        ],
    )
    async def test_invalid_dimensions_return_error(self, invalid_dimension: str) -> None:
        """Test invalid HEART dimensions return error."""
        from mcp_server_langgraph.websocket.services.heart_metrics import (
            HeartMetricsServiceAdapter,
        )

        adapter = HeartMetricsServiceAdapter()

        result = await adapter.get_dimension_metrics(invalid_dimension)

        assert "error" in result


@pytest.mark.unit
@pytest.mark.xdist_group(name="websocket_services_heart_metrics")
class TestHeartMetricsPrometheusIntegration:
    """Tests for HEART metrics Prometheus/Mimir integration."""

    def setup_method(self) -> None:
        """Reset singleton before each test."""
        from mcp_server_langgraph.websocket.services.heart_metrics import (
            reset_websocket_heart_metrics_service,
        )

        reset_websocket_heart_metrics_service()

    def teardown_method(self) -> None:
        """Force GC and reset singleton to prevent mock accumulation."""
        from mcp_server_langgraph.websocket.services.heart_metrics import (
            reset_websocket_heart_metrics_service,
        )

        reset_websocket_heart_metrics_service()
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_current_snapshot_queries_prometheus(self) -> None:
        """get_current_snapshot queries Prometheus when metrics client is provided."""
        from unittest.mock import AsyncMock

        from mcp_server_langgraph.websocket.services.heart_metrics import (
            HeartMetricsServiceAdapter,
        )

        mock_metrics_client = AsyncMock()
        mock_metrics_client.query_instant.return_value = MagicMock(series=[MagicMock(values=[MagicMock(value=85.0)])])

        adapter = HeartMetricsServiceAdapter()
        adapter._metrics_client = mock_metrics_client

        with patch("mcp_server_langgraph.websocket.services.heart_metrics.get_feature_flags") as mock_flags:
            mock_ff = MagicMock()
            mock_ff.enable_websocket_enhanced_metrics = True
            mock_flags.return_value = mock_ff

            result = await adapter.get_current_snapshot()

        # Should return data with HEART dimensions
        assert "happiness" in result
        # Prometheus should have been queried
        assert mock_metrics_client.query_instant.called

    @pytest.mark.asyncio
    async def test_get_current_snapshot_falls_back_on_prometheus_error(self) -> None:
        """get_current_snapshot falls back to stub data on Prometheus error."""
        from unittest.mock import AsyncMock

        from mcp_server_langgraph.websocket.services.heart_metrics import (
            HeartMetricsServiceAdapter,
        )

        mock_metrics_client = AsyncMock()
        mock_metrics_client.query_instant.side_effect = Exception("Prometheus unavailable")

        adapter = HeartMetricsServiceAdapter()
        adapter._metrics_client = mock_metrics_client

        with patch("mcp_server_langgraph.websocket.services.heart_metrics.get_feature_flags") as mock_flags:
            mock_ff = MagicMock()
            mock_ff.enable_websocket_enhanced_metrics = True
            mock_flags.return_value = mock_ff

            result = await adapter.get_current_snapshot()

        # Should still return valid data (fallback to stubs)
        assert "happiness" in result
        assert result["happiness"]["score"] is not None

    @pytest.mark.asyncio
    async def test_get_dimension_metrics_queries_prometheus(self) -> None:
        """get_dimension_metrics queries Prometheus when metrics client is provided."""
        from unittest.mock import AsyncMock

        from mcp_server_langgraph.websocket.services.heart_metrics import (
            HeartMetricsServiceAdapter,
        )

        mock_metrics_client = AsyncMock()
        mock_metrics_client.query_instant.return_value = MagicMock(series=[MagicMock(values=[MagicMock(value=92.0)])])

        adapter = HeartMetricsServiceAdapter()
        adapter._metrics_client = mock_metrics_client

        result = await adapter.get_dimension_metrics("happiness")

        # Should return data with score
        assert "score" in result
        # Prometheus should have been queried
        assert mock_metrics_client.query_instant.called

    @pytest.mark.asyncio
    async def test_minimal_snapshot_when_metrics_disabled(self) -> None:
        """get_current_snapshot returns minimal data when metrics disabled."""
        from mcp_server_langgraph.websocket.services.heart_metrics import (
            HeartMetricsServiceAdapter,
        )

        adapter = HeartMetricsServiceAdapter()

        with patch("mcp_server_langgraph.websocket.services.heart_metrics.get_feature_flags") as mock_flags:
            mock_ff = MagicMock()
            mock_ff.enable_websocket_enhanced_metrics = False
            mock_flags.return_value = mock_ff

            result = await adapter.get_current_snapshot()

        assert result["metrics_enabled"] is False
        # Should have zero scores
        assert result["happiness"]["score"] == 0
