"""
Tests for SemanticIndexManager Authorization Cache Metrics and Size Limits.

TDD tests for:
1. Prometheus metrics for cache hit/miss rates
2. Cache size limits with LRU eviction
3. Cache statistics reporting

RED Phase: These tests define the expected behavior.
GREEN Phase: Implementation will add metrics and size limits.
"""

import gc
import time
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


@pytest.mark.xdist_group(name="semantic_index_cache_metrics")
class TestAuthorizationCacheMetrics:
    """Tests for authorization cache Prometheus metrics."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_semantic_index_manager_has_cache_stats_method(
        self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock
    ) -> None:
        """SemanticIndexManager should have get_cache_stats method."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
        )

        assert hasattr(manager, "get_cache_stats")
        assert callable(manager.get_cache_stats)

    def test_cache_stats_returns_hit_miss_counts(
        self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock
    ) -> None:
        """get_cache_stats should return hit and miss counts."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
        )

        stats = manager.get_cache_stats()

        assert "hits" in stats
        assert "misses" in stats
        assert "size" in stats
        assert isinstance(stats["hits"], int)
        assert isinstance(stats["misses"], int)

    @pytest.mark.asyncio
    async def test_cache_hit_increments_hit_counter(
        self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock, mock_openfga_client: AsyncMock
    ) -> None:
        """Cache hit should increment hit counter."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
            auth_cache_ttl_seconds=60,
        )

        with patch(
            "mcp_server_langgraph.core.semantic_index_manager.get_openfga_client",
            return_value=mock_openfga_client,
        ):
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

        stats = manager.get_cache_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1

    @pytest.mark.asyncio
    async def test_cache_miss_increments_miss_counter(
        self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock, mock_openfga_client: AsyncMock
    ) -> None:
        """Cache miss should increment miss counter."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
            auth_cache_ttl_seconds=60,
        )

        with patch(
            "mcp_server_langgraph.core.semantic_index_manager.get_openfga_client",
            return_value=mock_openfga_client,
        ):
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

        stats = manager.get_cache_stats()
        assert stats["misses"] == 2
        assert stats["hits"] == 0


@pytest.mark.xdist_group(name="semantic_index_cache_size_limits")
class TestAuthorizationCacheSizeLimits:
    """Tests for authorization cache size limits."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_semantic_index_manager_accepts_cache_maxsize(
        self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock
    ) -> None:
        """SemanticIndexManager should accept auth_cache_maxsize parameter."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
            auth_cache_maxsize=100,
        )

        assert manager.auth_cache_maxsize == 100

    def test_semantic_index_manager_default_cache_maxsize(
        self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock
    ) -> None:
        """SemanticIndexManager should have default cache maxsize of 1000."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
        )

        assert manager.auth_cache_maxsize == 1000

    @pytest.mark.asyncio
    async def test_cache_evicts_oldest_when_maxsize_reached(
        self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock, mock_openfga_client: AsyncMock
    ) -> None:
        """Cache should evict oldest entries when maxsize is reached."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
            auth_cache_ttl_seconds=60,
            auth_cache_maxsize=3,  # Very small cache for testing
        )

        with patch(
            "mcp_server_langgraph.core.semantic_index_manager.get_openfga_client",
            return_value=mock_openfga_client,
        ):
            # Fill cache with 3 entries
            await manager._check_authorization(
                user_id="user:alice", relation="viewer", object_type="tool_index"
            )
            await manager._check_authorization(
                user_id="user:bob", relation="viewer", object_type="tool_index"
            )
            await manager._check_authorization(
                user_id="user:charlie", relation="viewer", object_type="tool_index"
            )

            # Add 4th entry - should evict oldest (alice)
            await manager._check_authorization(
                user_id="user:dave", relation="viewer", object_type="tool_index"
            )

        stats = manager.get_cache_stats()
        assert stats["size"] <= 3  # Should not exceed maxsize

    @pytest.mark.asyncio
    async def test_cache_size_reported_correctly(
        self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock, mock_openfga_client: AsyncMock
    ) -> None:
        """Cache size should be reported correctly in stats."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
            auth_cache_ttl_seconds=60,
        )

        with patch(
            "mcp_server_langgraph.core.semantic_index_manager.get_openfga_client",
            return_value=mock_openfga_client,
        ):
            await manager._check_authorization(
                user_id="user:alice", relation="viewer", object_type="tool_index"
            )
            await manager._check_authorization(
                user_id="user:bob", relation="viewer", object_type="tool_index"
            )

        stats = manager.get_cache_stats()
        assert stats["size"] == 2


@pytest.mark.xdist_group(name="semantic_index_cache_stats_extended")
class TestAuthorizationCacheStatsExtended:
    """Extended tests for cache statistics."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_cache_stats_includes_maxsize(
        self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock
    ) -> None:
        """Cache stats should include maxsize."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
            auth_cache_maxsize=500,
        )

        stats = manager.get_cache_stats()
        assert "maxsize" in stats
        assert stats["maxsize"] == 500

    def test_cache_stats_includes_ttl(
        self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock
    ) -> None:
        """Cache stats should include TTL."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
            auth_cache_ttl_seconds=120,
        )

        stats = manager.get_cache_stats()
        assert "ttl_seconds" in stats
        assert stats["ttl_seconds"] == 120

    def test_cache_stats_includes_hit_rate(
        self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock
    ) -> None:
        """Cache stats should include hit rate percentage."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
        )

        stats = manager.get_cache_stats()
        assert "hit_rate" in stats
        # Initially 0.0 when no operations have occurred
        assert stats["hit_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_cache_hit_rate_calculated_correctly(
        self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock, mock_openfga_client: AsyncMock
    ) -> None:
        """Cache hit rate should be calculated correctly."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
            auth_cache_ttl_seconds=60,
        )

        with patch(
            "mcp_server_langgraph.core.semantic_index_manager.get_openfga_client",
            return_value=mock_openfga_client,
        ):
            # 1 miss (first call)
            await manager._check_authorization(
                user_id="user:alice", relation="viewer", object_type="tool_index"
            )
            # 3 hits (subsequent calls)
            for _ in range(3):
                await manager._check_authorization(
                    user_id="user:alice", relation="viewer", object_type="tool_index"
                )

        stats = manager.get_cache_stats()
        # 3 hits / 4 total = 75%
        assert stats["hit_rate"] == 0.75

    def test_clear_cache_resets_stats(
        self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock
    ) -> None:
        """Clearing cache should reset stats counters."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
        )

        # Simulate some activity by directly manipulating internal state for test
        manager._cache_hits = 10
        manager._cache_misses = 5

        manager.clear_auth_cache()

        stats = manager.get_cache_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["size"] == 0
