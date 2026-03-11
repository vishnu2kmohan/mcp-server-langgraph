"""
Tests for SemanticIndexManager Cache Warming on Startup.

TDD tests for pre-warming the authorization cache during application
startup, enabling faster authorization checks for known user/resource
combinations in distributed deployments.

RED Phase: These tests define the expected behavior.
GREEN Phase: Implementation will add cache warming method.
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


@pytest.mark.xdist_group(name="semantic_index_cache_warming")
class TestCacheWarmingMethod:
    """Tests for cache warming method existence and behavior."""

    @pytest.fixture(autouse=True)
    def _isolate_otel(self):
        """Isolate OTEL instruments from global state contamination in xdist workers."""
        with (
            patch("mcp_server_langgraph.core.semantic_index_manager.logger", MagicMock()),
            patch("mcp_server_langgraph.core.semantic_index_manager.tracer", MagicMock()),
        ):
            yield

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_warm_cache_method_exists(self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock) -> None:
        """SemanticIndexManager should have warm_cache method."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
        )

        assert hasattr(manager, "warm_cache")
        assert callable(manager.warm_cache)

    @pytest.mark.asyncio
    async def test_warm_cache_pre_populates_entries(
        self,
        mock_embedder: MagicMock,
        mock_qdrant_client: AsyncMock,
        mock_openfga_client: AsyncMock,
    ) -> None:
        """warm_cache should pre-populate authorization entries."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
            auth_cache_ttl_seconds=60,
        )

        # Define entries to warm
        entries_to_warm = [
            {"user_id": "user:service-account", "relation": "viewer", "object_type": "tool_index"},
            {"user_id": "user:admin", "relation": "admin", "object_type": "skill_index"},
        ]

        with patch(
            "mcp_server_langgraph.core.semantic_index_manager.get_openfga_client",
            side_effect=lambda *a, **kw: mock_openfga_client,
        ):
            warmed_count = await manager.warm_cache(entries_to_warm)

        # Should have warmed 2 entries
        assert warmed_count == 2
        # Cache should have entries
        stats = manager.get_cache_stats()
        assert stats["size"] == 2

    @pytest.mark.asyncio
    async def test_warm_cache_only_caches_authorized(
        self,
        mock_embedder: MagicMock,
        mock_qdrant_client: AsyncMock,
    ) -> None:
        """warm_cache should only cache authorized entries (not denied)."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        # Mock that returns True for first call, False for second
        mock_openfga = AsyncMock(return_value=None)
        mock_openfga.check_permission = AsyncMock(side_effect=[True, False])

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
            auth_cache_ttl_seconds=60,
        )

        entries_to_warm = [
            {"user_id": "user:allowed", "relation": "viewer", "object_type": "tool_index"},
            {"user_id": "user:denied", "relation": "viewer", "object_type": "tool_index"},
        ]

        with patch(
            "mcp_server_langgraph.core.semantic_index_manager.get_openfga_client",
            side_effect=lambda *a, **kw: mock_openfga,
        ):
            warmed_count = await manager.warm_cache(entries_to_warm)

        # Only 1 entry should be cached (the authorized one)
        assert warmed_count == 1
        stats = manager.get_cache_stats()
        assert stats["size"] == 1


@pytest.mark.xdist_group(name="semantic_index_cache_warming")
class TestCacheWarmingWithDistributedCache:
    """Tests for cache warming with distributed (Redis) cache."""

    @pytest.fixture(autouse=True)
    def _isolate_otel(self):
        """Isolate OTEL instruments from global state contamination in xdist workers."""
        with (
            patch("mcp_server_langgraph.core.semantic_index_manager.logger", MagicMock()),
            patch("mcp_server_langgraph.core.semantic_index_manager.tracer", MagicMock()),
        ):
            yield

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_warm_cache_uses_cache_service_when_provided(
        self,
        mock_embedder: MagicMock,
        mock_qdrant_client: AsyncMock,
        mock_openfga_client: AsyncMock,
    ) -> None:
        """warm_cache should use CacheService in distributed mode."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        mock_cache_service = MagicMock()
        mock_cache_service.aget = AsyncMock(return_value=None)
        mock_cache_service.aset = AsyncMock(return_value=None)

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
            cache_service=mock_cache_service,
        )

        entries_to_warm = [
            {"user_id": "user:service", "relation": "viewer", "object_type": "tool_index"},
        ]

        with patch(
            "mcp_server_langgraph.core.semantic_index_manager.get_openfga_client",
            side_effect=lambda *a, **kw: mock_openfga_client,
        ):
            await manager.warm_cache(entries_to_warm)

        # CacheService.aset should have been called
        mock_cache_service.aset.assert_called()


@pytest.mark.xdist_group(name="semantic_index_cache_warming")
class TestCacheWarmingStatistics:
    """Tests for cache warming statistics."""

    @pytest.fixture(autouse=True)
    def _isolate_otel(self):
        """Isolate OTEL instruments from global state contamination in xdist workers."""
        with (
            patch("mcp_server_langgraph.core.semantic_index_manager.logger", MagicMock()),
            patch("mcp_server_langgraph.core.semantic_index_manager.tracer", MagicMock()),
        ):
            yield

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_warm_cache_returns_count_of_warmed_entries(
        self,
        mock_embedder: MagicMock,
        mock_qdrant_client: AsyncMock,
        mock_openfga_client: AsyncMock,
    ) -> None:
        """warm_cache should return the count of successfully warmed entries."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
            auth_cache_ttl_seconds=60,
        )

        entries_to_warm = [
            {"user_id": "user:a", "relation": "viewer", "object_type": "tool_index"},
            {"user_id": "user:b", "relation": "viewer", "object_type": "skill_index"},
            {"user_id": "user:c", "relation": "admin", "object_type": "memory_index"},
        ]

        with patch(
            "mcp_server_langgraph.core.semantic_index_manager.get_openfga_client",
            side_effect=lambda *a, **kw: mock_openfga_client,
        ):
            warmed_count = await manager.warm_cache(entries_to_warm)

        assert warmed_count == 3

    @pytest.mark.asyncio
    async def test_warm_cache_handles_empty_list(
        self,
        mock_embedder: MagicMock,
        mock_qdrant_client: AsyncMock,
    ) -> None:
        """warm_cache should handle empty entries list gracefully."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
        )

        warmed_count = await manager.warm_cache([])

        assert warmed_count == 0

    @pytest.mark.asyncio
    async def test_warm_cache_handles_openfga_errors(
        self,
        mock_embedder: MagicMock,
        mock_qdrant_client: AsyncMock,
    ) -> None:
        """warm_cache should handle OpenFGA errors gracefully."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        mock_openfga = AsyncMock(return_value=None)
        mock_openfga.check_permission = AsyncMock(side_effect=[True, Exception("Connection error"), True])

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
            auth_cache_ttl_seconds=60,
        )

        entries_to_warm = [
            {"user_id": "user:a", "relation": "viewer", "object_type": "tool_index"},
            {"user_id": "user:b", "relation": "viewer", "object_type": "tool_index"},  # This will error
            {"user_id": "user:c", "relation": "viewer", "object_type": "tool_index"},
        ]

        with patch(
            "mcp_server_langgraph.core.semantic_index_manager.get_openfga_client",
            side_effect=lambda *a, **kw: mock_openfga,
        ):
            warmed_count = await manager.warm_cache(entries_to_warm)

        # Only 2 should succeed (1st and 3rd, 2nd errored)
        assert warmed_count == 2
