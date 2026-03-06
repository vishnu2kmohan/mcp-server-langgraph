"""
Tests for Semantic Tool Selection Analytics Metrics.

TDD tests for Prometheus metrics tracking:
1. Tool search counter increments on each search
2. Tool search duration histogram records latency
3. Tools selected histogram records result count
4. Cache hit/miss counters for query/embedding caches
5. Metrics functions are safe when Prometheus unavailable

RED Phase: These tests define the expected behavior.
GREEN Phase: Implementation will add metrics to SemanticIndexManager.
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit]


@pytest.mark.xdist_group(name="semantic_tool_selection_metrics")
class TestToolSelectionMetrics:
    """Tests for tool selection Prometheus metrics."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_emit_tool_search_metric_function_exists(self) -> None:
        """emit_tool_search_metric function should exist."""
        from mcp_server_langgraph.core.semantic_index_manager import (
            emit_tool_search_metric,
        )

        assert callable(emit_tool_search_metric)

    def test_emit_tool_search_metric_safe_when_prometheus_unavailable(self) -> None:
        """emit_tool_search_metric should not raise when Prometheus is unavailable."""
        from mcp_server_langgraph.core.semantic_index_manager import (
            emit_tool_search_metric,
        )

        # Should not raise even if Prometheus is not available
        emit_tool_search_metric(
            duration_seconds=0.1,
            results_count=5,
            cache_hit=False,
            user_id="user:test",
        )

    def test_emit_cache_hit_metric_function_exists(self) -> None:
        """emit_cache_hit_metric function should exist for query/embedding caches."""
        from mcp_server_langgraph.core.semantic_index_manager import (
            emit_cache_hit_metric,
        )

        assert callable(emit_cache_hit_metric)

    def test_emit_cache_hit_metric_safe_when_prometheus_unavailable(self) -> None:
        """emit_cache_hit_metric should not raise when Prometheus is unavailable."""
        from mcp_server_langgraph.core.semantic_index_manager import (
            emit_cache_hit_metric,
        )

        # Should not raise even if Prometheus is not available
        emit_cache_hit_metric(cache_type="query", result="hit")
        emit_cache_hit_metric(cache_type="embedding", result="miss")


@pytest.mark.xdist_group(name="semantic_tool_selection_metrics")
class TestSearchToolsMetricsIntegration:
    """Tests for metrics integration in search_tools."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_search_tools_emits_duration_metric(self) -> None:
        """search_tools should emit duration metric."""
        from mcp_server_langgraph.core.semantic_index_manager import (
            SemanticIndexManager,
        )

        mock_embedder = MagicMock()
        mock_embedder.embed_query = MagicMock(return_value=[0.1] * 384)

        mock_point = MagicMock()
        mock_point.id = "builtin:test"
        mock_point.payload = {
            "tool_id": "builtin:test",
            "name": "test_tool",
            "description": "A test tool",
            "category": "other",
        }
        mock_point.score = 0.95

        mock_qdrant = AsyncMock(return_value=None)
        mock_qdrant.query_points = AsyncMock(return_value=MagicMock(points=[mock_point]))

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant,
            collection_name="test",
            vector_size=384,
        )

        with (
            patch.object(manager, "_check_authorization", return_value=True),
            patch("mcp_server_langgraph.core.semantic_index_manager.emit_tool_search_metric") as mock_emit,
        ):
            await manager.search_tools(
                query="test query",
                user_id="user:test",
                limit=10,
            )

            # Verify metric was emitted
            mock_emit.assert_called_once()
            call_kwargs = mock_emit.call_args.kwargs
            assert "duration_seconds" in call_kwargs
            assert call_kwargs["duration_seconds"] >= 0
            assert call_kwargs["results_count"] == 1

    @pytest.mark.asyncio
    async def test_search_tools_emits_cache_hit_metric_on_query_cache_hit(self) -> None:
        """search_tools should emit cache hit metric when query cache hits."""
        from mcp_server_langgraph.core.semantic_index_manager import (
            SemanticIndexManager,
        )
        from mcp_server_langgraph.tools.semantic_index import ToolIndexEntry

        mock_embedder = MagicMock()
        mock_qdrant = AsyncMock(return_value=None)

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant,
            collection_name="test",
            vector_size=384,
        )

        # Pre-populate query cache
        cached_entry = ToolIndexEntry(
            tool_id="builtin:cached",
            name="cached_tool",
            description="A cached tool",
            category="other",
        )
        cache_key = manager._make_query_cache_key(
            query="test query",
            search_type="tools",
            user_id="user:test",
            limit=10,
        )
        manager._query_cache[cache_key] = [cached_entry]

        with (
            patch.object(manager, "_check_authorization", return_value=True),
            patch("mcp_server_langgraph.core.semantic_index_manager.emit_cache_hit_metric") as mock_emit,
        ):
            await manager.search_tools(
                query="test query",
                user_id="user:test",
                limit=10,
            )

            # Verify cache hit metric was emitted
            mock_emit.assert_called()
            # Find call with cache_type="query"
            query_cache_calls = [call for call in mock_emit.call_args_list if call.kwargs.get("cache_type") == "query"]
            assert len(query_cache_calls) >= 1
            assert query_cache_calls[0].kwargs["result"] == "hit"


@pytest.mark.xdist_group(name="semantic_tool_selection_metrics")
class TestMetricsConstants:
    """Tests for metrics constants and exports."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_metrics_functions_exported(self) -> None:
        """Metrics functions should be exported from module."""
        from mcp_server_langgraph.core.semantic_index_manager import (
            emit_auth_cache_metric,
            emit_cache_hit_metric,
            emit_tool_search_metric,
        )

        assert callable(emit_auth_cache_metric)
        assert callable(emit_cache_hit_metric)
        assert callable(emit_tool_search_metric)
