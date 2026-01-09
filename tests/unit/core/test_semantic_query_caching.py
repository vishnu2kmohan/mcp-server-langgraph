"""
Tests for Semantic Index Query Result Caching.

TDD tests for caching search results:
1. Cache hit returns cached results without Qdrant query
2. Cache miss performs Qdrant query and caches result
3. Cache respects TTL expiration
4. Cache key includes query, user_id, and search parameters
5. Cache can be cleared/invalidated

RED Phase: These tests define the expected behavior.
GREEN Phase: Implementation will add caching to SemanticIndexManager.
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.adr0099]


@pytest.mark.xdist_group(name="semantic_query_caching")
class TestQueryResultCaching:
    """Tests for query result caching in SemanticIndexManager."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_search_tools_uses_cache_on_hit(self) -> None:
        """search_tools should return cached results without querying Qdrant."""
        from mcp_server_langgraph.core.semantic_index_manager import (
            SemanticIndexManager,
        )
        from mcp_server_langgraph.tools.semantic_index import ToolIndexEntry

        mock_embedder = MagicMock()
        mock_embedder.embed_documents = MagicMock(return_value=[[0.1] * 384])
        mock_qdrant = AsyncMock()

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant,
            collection_name="test",
            vector_size=384,
        )

        # Pre-populate cache with a result
        cached_entry = ToolIndexEntry(
            tool_id="tool:cached",
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

        # Search should return cached result without querying Qdrant
        with patch.object(manager, "_check_authorization", return_value=True):
            results = await manager.search_tools(
                query="test query",
                user_id="user:test",
                limit=10,
            )

        assert len(results) == 1
        assert results[0].name == "cached_tool"
        # Qdrant should NOT have been called
        mock_qdrant.query_points.assert_not_called()

    @pytest.mark.asyncio
    async def test_search_tools_caches_result_on_miss(self) -> None:
        """search_tools should cache results on cache miss."""
        from mcp_server_langgraph.core.semantic_index_manager import (
            SemanticIndexManager,
        )

        mock_embedder = MagicMock()
        mock_embedder.embed_documents = MagicMock(return_value=[[0.1] * 384])

        # Mock Qdrant response
        mock_point = MagicMock()
        mock_point.id = "tool:test"
        mock_point.payload = {
            "tool_id": "tool:test",
            "name": "test_tool",
            "description": "A test tool",
            "category": "other",
        }
        mock_point.score = 0.95

        mock_qdrant = AsyncMock()
        mock_qdrant.query_points = AsyncMock(
            return_value=MagicMock(points=[mock_point])
        )

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant,
            collection_name="test",
            vector_size=384,
        )

        with patch.object(manager, "_check_authorization", return_value=True):
            # First search - cache miss
            results = await manager.search_tools(
                query="test query",
                user_id="user:test",
                limit=10,
            )

        assert len(results) == 1
        assert results[0].name == "test_tool"

        # Verify result was cached
        cache_key = manager._make_query_cache_key(
            query="test query",
            search_type="tools",
            user_id="user:test",
            limit=10,
        )
        assert cache_key in manager._query_cache
        assert len(manager._query_cache[cache_key]) == 1

    @pytest.mark.asyncio
    async def test_query_cache_key_includes_parameters(self) -> None:
        """Cache key should include all relevant search parameters."""
        from mcp_server_langgraph.core.semantic_index_manager import (
            SemanticIndexManager,
        )

        mock_embedder = MagicMock()
        mock_qdrant = AsyncMock()

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant,
            collection_name="test",
            vector_size=384,
        )

        key1 = manager._make_query_cache_key(
            query="test", search_type="tools", user_id="user:a", limit=10
        )
        key2 = manager._make_query_cache_key(
            query="test", search_type="tools", user_id="user:b", limit=10
        )
        key3 = manager._make_query_cache_key(
            query="different", search_type="tools", user_id="user:a", limit=10
        )
        key4 = manager._make_query_cache_key(
            query="test", search_type="skills", user_id="user:a", limit=10
        )

        # All keys should be different
        assert key1 != key2  # Different user
        assert key1 != key3  # Different query
        assert key1 != key4  # Different search type

    def test_clear_query_cache(self) -> None:
        """clear_query_cache should remove all cached queries."""
        from mcp_server_langgraph.core.semantic_index_manager import (
            SemanticIndexManager,
        )

        mock_embedder = MagicMock()
        mock_qdrant = AsyncMock()

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant,
            collection_name="test",
            vector_size=384,
        )

        # Add some cached entries
        manager._query_cache["key1"] = ["result1"]
        manager._query_cache["key2"] = ["result2"]

        assert len(manager._query_cache) == 2

        manager.clear_query_cache()

        assert len(manager._query_cache) == 0


@pytest.mark.xdist_group(name="semantic_query_caching")
class TestQueryCacheMetrics:
    """Tests for query cache metrics."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_cache_hit_increments_metric(self) -> None:
        """Cache hit should increment hit counter metric."""
        from mcp_server_langgraph.core.semantic_index_manager import (
            SemanticIndexManager,
        )
        from mcp_server_langgraph.tools.semantic_index import ToolIndexEntry

        mock_embedder = MagicMock()
        mock_qdrant = AsyncMock()

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant,
            collection_name="test",
            vector_size=384,
        )

        # Pre-populate cache
        cached_entry = ToolIndexEntry(
            tool_id="tool:cached",
            name="cached_tool",
            description="A cached tool",
            category="other",
        )
        cache_key = manager._make_query_cache_key(
            query="test", search_type="tools", user_id="user:test", limit=10
        )
        manager._query_cache[cache_key] = [cached_entry]

        # Get initial stats
        initial_stats = manager.get_query_cache_stats()

        with patch.object(manager, "_check_authorization", return_value=True):
            await manager.search_tools(query="test", user_id="user:test", limit=10)

        # Check hit was recorded
        final_stats = manager.get_query_cache_stats()
        assert final_stats["hits"] == initial_stats["hits"] + 1

    def test_get_query_cache_stats(self) -> None:
        """get_query_cache_stats should return cache statistics."""
        from mcp_server_langgraph.core.semantic_index_manager import (
            SemanticIndexManager,
        )

        mock_embedder = MagicMock()
        mock_qdrant = AsyncMock()

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant,
            collection_name="test",
            vector_size=384,
        )

        stats = manager.get_query_cache_stats()

        assert "hits" in stats
        assert "misses" in stats
        assert "size" in stats
        assert "hit_rate" in stats
