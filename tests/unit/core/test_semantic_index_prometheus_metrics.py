"""
Tests for SemanticIndexManager Prometheus Metrics Integration.

TDD tests for emitting Prometheus counter metrics for authorization
cache hit/miss rates, enabling observability dashboards.

RED Phase: These tests define the expected behavior.
GREEN Phase: Implementation will add Prometheus metric emission.
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.authorization, pytest.mark.adr0099]


@pytest.fixture
def mock_embedder() -> MagicMock:
    """Create a mock embedder."""
    embedder = MagicMock()
    embedder.embed_query = MagicMock(return_value=[0.1, 0.2, 0.3, 0.4] * 96)
    return embedder


@pytest.fixture
def mock_qdrant_client() -> AsyncMock:
    """Create a mock Qdrant client."""
    client = AsyncMock(return_value=None)
    client.get_collections = AsyncMock(return_value=MagicMock(collections=[]))
    mock_response = MagicMock()
    mock_response.points = []
    client.query_points = AsyncMock(return_value=mock_response)
    return client


@pytest.fixture
def mock_openfga_client() -> AsyncMock:
    """Create a mock OpenFGA client."""
    client = AsyncMock(return_value=None)
    client.check_permission = AsyncMock(return_value=True)
    return client


@pytest.mark.xdist_group(name="semantic_index_prometheus")
class TestPrometheusMetricsEmission:
    """Tests for Prometheus metrics emission."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_cache_hit_emits_prometheus_counter(
        self,
        mock_embedder: MagicMock,
        mock_qdrant_client: AsyncMock,
        mock_openfga_client: AsyncMock,
    ) -> None:
        """Cache hit should emit Prometheus counter metric."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
            auth_cache_ttl_seconds=60,
        )

        with patch(
            "mcp_server_langgraph.core.semantic_index_manager.get_openfga_client",
            return_value=mock_openfga_client,
        ), patch(
            "mcp_server_langgraph.core.semantic_index_manager.emit_auth_cache_metric"
        ) as mock_emit:
            # First call - miss
            await manager._check_authorization(
                user_id="user:alice",
                relation="viewer",
                object_type="tool_index",
            )

            # Second call - hit
            await manager._check_authorization(
                user_id="user:alice",
                relation="viewer",
                object_type="tool_index",
            )

            # Verify metrics emitted
            calls = mock_emit.call_args_list
            assert len(calls) == 2
            # First call should be miss
            assert calls[0][1]["result"] == "miss"
            # Second call should be hit
            assert calls[1][1]["result"] == "hit"

    @pytest.mark.asyncio
    async def test_cache_miss_emits_prometheus_counter(
        self,
        mock_embedder: MagicMock,
        mock_qdrant_client: AsyncMock,
        mock_openfga_client: AsyncMock,
    ) -> None:
        """Cache miss should emit Prometheus counter metric."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
            auth_cache_ttl_seconds=60,
        )

        with patch(
            "mcp_server_langgraph.core.semantic_index_manager.get_openfga_client",
            return_value=mock_openfga_client,
        ), patch(
            "mcp_server_langgraph.core.semantic_index_manager.emit_auth_cache_metric"
        ) as mock_emit:
            # Different users = different cache keys = all misses
            await manager._check_authorization(
                user_id="user:alice",
                relation="viewer",
                object_type="tool_index",
            )
            await manager._check_authorization(
                user_id="user:bob",
                relation="viewer",
                object_type="tool_index",
            )

            # Both should emit miss
            assert mock_emit.call_count == 2
            for call in mock_emit.call_args_list:
                assert call[1]["result"] == "miss"

    @pytest.mark.asyncio
    async def test_prometheus_metric_includes_resource_type(
        self,
        mock_embedder: MagicMock,
        mock_qdrant_client: AsyncMock,
        mock_openfga_client: AsyncMock,
    ) -> None:
        """Prometheus metric should include resource_type label."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
            auth_cache_ttl_seconds=60,
        )

        with patch(
            "mcp_server_langgraph.core.semantic_index_manager.get_openfga_client",
            return_value=mock_openfga_client,
        ), patch(
            "mcp_server_langgraph.core.semantic_index_manager.emit_auth_cache_metric"
        ) as mock_emit:
            await manager._check_authorization(
                user_id="user:alice",
                relation="viewer",
                object_type="tool_index",
            )

            call_kwargs = mock_emit.call_args[1]
            assert "resource_type" in call_kwargs
            assert call_kwargs["resource_type"] == "tool_index"


@pytest.mark.xdist_group(name="semantic_index_prometheus")
class TestPrometheusMetricsModule:
    """Tests for the Prometheus metrics module."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_emit_auth_cache_metric_function_exists(self) -> None:
        """emit_auth_cache_metric function should exist."""
        from mcp_server_langgraph.core.semantic_index_manager import emit_auth_cache_metric

        assert callable(emit_auth_cache_metric)

    def test_emit_auth_cache_metric_accepts_required_params(self) -> None:
        """emit_auth_cache_metric should accept required parameters."""
        from mcp_server_langgraph.core.semantic_index_manager import emit_auth_cache_metric

        # Should not raise
        emit_auth_cache_metric(result="hit", resource_type="tool_index")
        emit_auth_cache_metric(result="miss", resource_type="skill_index")

    def test_emit_auth_cache_metric_handles_missing_prometheus(self) -> None:
        """emit_auth_cache_metric should gracefully handle missing Prometheus."""
        from mcp_server_langgraph.core.semantic_index_manager import emit_auth_cache_metric

        # Should not raise even if prometheus_client is not available
        with patch.dict("sys.modules", {"prometheus_client": None}):
            emit_auth_cache_metric(result="hit", resource_type="tool_index")


@pytest.mark.xdist_group(name="semantic_index_prometheus_gauge")
class TestPrometheusCacheSizeGauge:
    """Tests for Prometheus cache size gauge."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_update_cache_size_gauge_function_exists(self) -> None:
        """update_cache_size_gauge function should exist."""
        from mcp_server_langgraph.core.semantic_index_manager import update_cache_size_gauge

        assert callable(update_cache_size_gauge)

    def test_update_cache_size_gauge_accepts_size_parameter(self) -> None:
        """update_cache_size_gauge should accept size parameter."""
        from mcp_server_langgraph.core.semantic_index_manager import update_cache_size_gauge

        # Should not raise
        update_cache_size_gauge(size=42)
        update_cache_size_gauge(size=0)

    @pytest.mark.asyncio
    async def test_cache_size_gauge_updated_on_cache_change(
        self,
        mock_embedder: MagicMock,
        mock_qdrant_client: AsyncMock,
        mock_openfga_client: AsyncMock,
    ) -> None:
        """Cache size gauge should be updated when cache changes."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
            auth_cache_ttl_seconds=60,
        )

        with patch(
            "mcp_server_langgraph.core.semantic_index_manager.get_openfga_client",
            return_value=mock_openfga_client,
        ), patch(
            "mcp_server_langgraph.core.semantic_index_manager.update_cache_size_gauge"
        ) as mock_gauge:
            await manager._check_authorization(
                user_id="user:alice",
                relation="viewer",
                object_type="tool_index",
            )

            # Gauge should have been called with size=1
            mock_gauge.assert_called()
            # Get the last call's size argument
            last_call = mock_gauge.call_args_list[-1]
            assert last_call[1]["size"] == 1


@pytest.mark.xdist_group(name="semantic_index_prometheus_histogram")
class TestPrometheusCacheWarmingHistogram:
    """Tests for Prometheus cache warming duration histogram."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_record_cache_warming_duration_function_exists(self) -> None:
        """record_cache_warming_duration function should exist."""
        from mcp_server_langgraph.core.semantic_index_manager import (
            record_cache_warming_duration,
        )

        assert callable(record_cache_warming_duration)

    def test_record_cache_warming_duration_accepts_parameters(self) -> None:
        """record_cache_warming_duration should accept duration and count."""
        from mcp_server_langgraph.core.semantic_index_manager import (
            record_cache_warming_duration,
        )

        # Should not raise
        record_cache_warming_duration(duration_seconds=1.5, entries_count=10)

    @pytest.mark.asyncio
    async def test_warm_cache_records_duration_histogram(
        self,
        mock_embedder: MagicMock,
        mock_qdrant_client: AsyncMock,
        mock_openfga_client: AsyncMock,
    ) -> None:
        """warm_cache should record duration in histogram."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
            auth_cache_ttl_seconds=60,
        )

        entries = [
            {"user_id": "user:a", "relation": "viewer", "object_type": "tool_index"},
        ]

        with patch(
            "mcp_server_langgraph.core.semantic_index_manager.get_openfga_client",
            return_value=mock_openfga_client,
        ), patch(
            "mcp_server_langgraph.core.semantic_index_manager.record_cache_warming_duration"
        ) as mock_histogram:
            await manager.warm_cache(entries)

            # Histogram should have been called
            mock_histogram.assert_called_once()
            call_kwargs = mock_histogram.call_args[1]
            assert "duration_seconds" in call_kwargs
            assert "entries_count" in call_kwargs
            assert call_kwargs["entries_count"] == 1
