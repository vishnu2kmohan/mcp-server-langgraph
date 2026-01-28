"""
Tests for Semantic Index Embedding Caching.

TDD tests for caching embedding generation:
1. Cache hit returns cached embedding without calling embedder
2. Cache miss calls embedder and caches result
3. Cache key is based on query text hash
4. Cache respects TTL expiration
5. Cache statistics are tracked

RED Phase: These tests define the expected behavior.
GREEN Phase: Implementation will add embedding caching to SemanticIndexManager.
"""

import gc
import hashlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit]


@pytest.mark.xdist_group(name="semantic_embedding_caching")
class TestEmbeddingCaching:
    """Tests for embedding result caching in SemanticIndexManager."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_search_tools_uses_embedding_cache_on_hit(self) -> None:
        """search_tools should use cached embedding without calling embedder."""
        from mcp_server_langgraph.core.semantic_index_manager import (
            SemanticIndexManager,
        )

        mock_embedder = MagicMock()
        mock_embedder.embed_query = MagicMock(return_value=[0.1] * 384)

        mock_point = MagicMock()
        mock_point.id = "tool:test"
        mock_point.payload = {
            "tool_id": "tool:test",
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
            embedding_cache_ttl_seconds=300,  # Enable embedding cache
        )

        # Pre-populate embedding cache
        query = "test query"
        embedding_cache_key = manager._make_embedding_cache_key(query)
        cached_embedding = [0.5] * 384
        manager._embedding_cache[embedding_cache_key] = cached_embedding

        with patch.object(manager, "_check_authorization", return_value=True):
            # First search - should use cached embedding
            await manager.search_tools(
                query=query,
                user_id="user:test",
                limit=10,
            )

        # embedder.embed_query should NOT have been called
        mock_embedder.embed_query.assert_not_called()

        # Qdrant should have been called with the cached embedding
        mock_qdrant.query_points.assert_called_once()
        call_args = mock_qdrant.query_points.call_args
        assert call_args.kwargs["query"] == cached_embedding

    @pytest.mark.asyncio
    async def test_search_tools_caches_embedding_on_miss(self) -> None:
        """search_tools should cache embedding result on cache miss."""
        from mcp_server_langgraph.core.semantic_index_manager import (
            SemanticIndexManager,
        )

        expected_embedding = [0.2] * 384
        mock_embedder = MagicMock()
        mock_embedder.embed_query = MagicMock(return_value=expected_embedding)

        mock_point = MagicMock()
        mock_point.id = "tool:test"
        mock_point.payload = {
            "tool_id": "tool:test",
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
            embedding_cache_ttl_seconds=300,
        )

        query = "test query for caching"

        with patch.object(manager, "_check_authorization", return_value=True):
            await manager.search_tools(
                query=query,
                user_id="user:test",
                limit=10,
            )

        # Verify embedding was called
        mock_embedder.embed_query.assert_called_once_with(query)

        # Verify result was cached
        embedding_cache_key = manager._make_embedding_cache_key(query)
        assert embedding_cache_key in manager._embedding_cache
        assert manager._embedding_cache[embedding_cache_key] == expected_embedding

    def test_embedding_cache_key_uses_text_hash(self) -> None:
        """Embedding cache key should be based on query text hash."""
        from mcp_server_langgraph.core.semantic_index_manager import (
            SemanticIndexManager,
        )

        mock_embedder = MagicMock()
        mock_qdrant = AsyncMock(return_value=None)

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant,
            collection_name="test",
            vector_size=384,
        )

        query1 = "test query one"
        query2 = "test query two"

        key1 = manager._make_embedding_cache_key(query1)
        key2 = manager._make_embedding_cache_key(query2)
        key1_again = manager._make_embedding_cache_key(query1)

        # Same query should produce same key
        assert key1 == key1_again

        # Different queries should produce different keys
        assert key1 != key2

        # Key should contain hash
        expected_hash = hashlib.sha256(query1.encode()).hexdigest()[:16]
        assert expected_hash in key1

    def test_clear_embedding_cache(self) -> None:
        """clear_embedding_cache should remove all cached embeddings."""
        from mcp_server_langgraph.core.semantic_index_manager import (
            SemanticIndexManager,
        )

        mock_embedder = MagicMock()
        mock_qdrant = AsyncMock(return_value=None)

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant,
            collection_name="test",
            vector_size=384,
            embedding_cache_ttl_seconds=300,
        )

        # Add some cached entries
        manager._embedding_cache["key1"] = [0.1] * 384
        manager._embedding_cache["key2"] = [0.2] * 384

        assert len(manager._embedding_cache) == 2

        manager.clear_embedding_cache()

        assert len(manager._embedding_cache) == 0

    def test_embedding_cache_disabled_when_ttl_zero(self) -> None:
        """Embedding cache should be disabled when TTL is 0."""
        from mcp_server_langgraph.core.semantic_index_manager import (
            SemanticIndexManager,
        )

        mock_embedder = MagicMock()
        mock_qdrant = AsyncMock(return_value=None)

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant,
            collection_name="test",
            vector_size=384,
            embedding_cache_ttl_seconds=0,  # Disabled
        )

        # Cache should have minimal size when disabled
        assert manager._embedding_cache.maxsize == 1


@pytest.mark.xdist_group(name="semantic_embedding_caching")
class TestEmbeddingCacheMetrics:
    """Tests for embedding cache metrics."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_embedding_cache_stats(self) -> None:
        """get_embedding_cache_stats should return cache statistics."""
        from mcp_server_langgraph.core.semantic_index_manager import (
            SemanticIndexManager,
        )

        mock_embedder = MagicMock()
        mock_qdrant = AsyncMock(return_value=None)

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant,
            collection_name="test",
            vector_size=384,
            embedding_cache_ttl_seconds=300,
            embedding_cache_maxsize=1000,
        )

        stats = manager.get_embedding_cache_stats()

        assert "hits" in stats
        assert "misses" in stats
        assert "size" in stats
        assert "hit_rate" in stats
        assert stats["maxsize"] == 1000
        assert stats["ttl_seconds"] == 300

    @pytest.mark.asyncio
    async def test_embedding_cache_hit_increments_metric(self) -> None:
        """Cache hit should increment hit counter."""
        from mcp_server_langgraph.core.semantic_index_manager import (
            SemanticIndexManager,
        )

        mock_embedder = MagicMock()
        mock_embedder.embed_query = MagicMock(return_value=[0.1] * 384)

        mock_point = MagicMock()
        mock_point.id = "tool:test"
        mock_point.payload = {
            "tool_id": "tool:test",
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
            embedding_cache_ttl_seconds=300,
        )

        # Pre-populate embedding cache
        query = "test"
        embedding_cache_key = manager._make_embedding_cache_key(query)
        manager._embedding_cache[embedding_cache_key] = [0.5] * 384

        initial_stats = manager.get_embedding_cache_stats()

        with patch.object(manager, "_check_authorization", return_value=True):
            await manager.search_tools(query=query, user_id="user:test", limit=10)

        final_stats = manager.get_embedding_cache_stats()
        assert final_stats["hits"] == initial_stats["hits"] + 1
