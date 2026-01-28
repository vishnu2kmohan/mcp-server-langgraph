"""
Tests for SemanticIndexManager Distributed (Redis) Cache Option.

TDD tests for using the existing CacheService (L1+L2) for authorization
caching in distributed deployments, enabling cache sharing across instances.

RED Phase: These tests define the expected behavior.
GREEN Phase: Implementation will integrate with CacheService.

Architecture:
- Single-node: Uses local TTLCache (default, current implementation)
- Distributed: Uses CacheService with L1+L2 for Redis-backed caching
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.authorization]


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


@pytest.fixture
def mock_cache_service() -> MagicMock:
    """Create a mock CacheService."""
    cache = MagicMock()
    cache.get = MagicMock(return_value=None)
    cache.set = MagicMock()
    cache.aget = AsyncMock(return_value=None)
    cache.aset = AsyncMock(return_value=None)
    cache.delete = MagicMock()
    cache.adelete = AsyncMock(return_value=None)
    return cache


@pytest.mark.xdist_group(name="semantic_index_distributed_cache")
class TestDistributedCacheConfig:
    """Tests for distributed cache configuration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_semantic_index_manager_accepts_cache_service(
        self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock, mock_cache_service: MagicMock
    ) -> None:
        """SemanticIndexManager should accept external CacheService."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
            cache_service=mock_cache_service,
        )

        assert manager.cache_service is mock_cache_service

    def test_semantic_index_manager_uses_local_cache_by_default(
        self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock
    ) -> None:
        """SemanticIndexManager should use local TTLCache when no CacheService provided."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
        )

        # No external cache service
        assert manager.cache_service is None
        # Local cache should still work
        assert manager._auth_cache is not None


@pytest.mark.xdist_group(name="semantic_index_distributed_cache")
class TestDistributedCacheBehavior:
    """Tests for distributed cache behavior."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_authorization_uses_cache_service_when_provided(
        self,
        mock_embedder: MagicMock,
        mock_qdrant_client: AsyncMock,
        mock_openfga_client: AsyncMock,
        mock_cache_service: MagicMock,
    ) -> None:
        """Authorization should use CacheService when provided."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        # Configure cache service to return None (cache miss)
        mock_cache_service.aget = AsyncMock(return_value=None)

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
            cache_service=mock_cache_service,
        )

        with patch(
            "mcp_server_langgraph.core.semantic_index_manager.get_openfga_client",
            return_value=mock_openfga_client,
        ):
            await manager._check_authorization(
                user_id="user:alice",
                relation="viewer",
                object_type="tool_index",
            )

        # CacheService should be called for get
        mock_cache_service.aget.assert_called()

        # CacheService should be called for set (on positive result)
        mock_cache_service.aset.assert_called()

    @pytest.mark.asyncio
    async def test_authorization_cache_hit_from_cache_service(
        self,
        mock_embedder: MagicMock,
        mock_qdrant_client: AsyncMock,
        mock_openfga_client: AsyncMock,
        mock_cache_service: MagicMock,
    ) -> None:
        """Cache hit from CacheService should skip OpenFGA call."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        # Configure cache service to return True (cache hit)
        mock_cache_service.aget = AsyncMock(return_value=True)

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
            cache_service=mock_cache_service,
        )

        with patch(
            "mcp_server_langgraph.core.semantic_index_manager.get_openfga_client",
            return_value=mock_openfga_client,
        ):
            result = await manager._check_authorization(
                user_id="user:alice",
                relation="viewer",
                object_type="tool_index",
            )

        assert result is True
        # OpenFGA should NOT be called due to cache hit
        mock_openfga_client.check_permission.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_key_format_for_distributed_cache(
        self,
        mock_embedder: MagicMock,
        mock_qdrant_client: AsyncMock,
        mock_openfga_client: AsyncMock,
        mock_cache_service: MagicMock,
    ) -> None:
        """Cache key should include appropriate prefix for distributed cache."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        mock_cache_service.aget = AsyncMock(return_value=None)

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
            cache_service=mock_cache_service,
        )

        with patch(
            "mcp_server_langgraph.core.semantic_index_manager.get_openfga_client",
            return_value=mock_openfga_client,
        ):
            await manager._check_authorization(
                user_id="user:alice",
                relation="viewer",
                object_type="tool_index",
                object_id="default",
            )

        # Verify cache key format includes auth_permission prefix for CacheService
        call_args = mock_cache_service.aget.call_args
        cache_key = call_args[0][0]  # First positional argument
        assert cache_key.startswith("auth_permission:")


@pytest.mark.xdist_group(name="semantic_index_distributed_cache")
class TestDistributedCacheStats:
    """Tests for distributed cache statistics."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_cache_stats_indicates_distributed_mode(
        self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock, mock_cache_service: MagicMock
    ) -> None:
        """Cache stats should indicate distributed mode when CacheService is used."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
            cache_service=mock_cache_service,
        )

        stats = manager.get_cache_stats()
        assert "distributed" in stats
        assert stats["distributed"] is True

    def test_cache_stats_indicates_local_mode(self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock) -> None:
        """Cache stats should indicate local mode when no CacheService."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
        )

        stats = manager.get_cache_stats()
        assert "distributed" in stats
        assert stats["distributed"] is False
