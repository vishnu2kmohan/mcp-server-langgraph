"""
Tests for SemanticIndexManager Authorization Caching.

TDD tests for caching authorization checks to reduce OpenFGA calls
and improve performance in high-volume scenarios.

RED Phase: These tests define the expected caching behavior.
GREEN Phase: Implementation will add caching to _check_authorization.

Performance Goal: Reduce OpenFGA calls by caching positive authorization
results with a short TTL (default 60 seconds).
"""

import asyncio
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
    client = AsyncMock()
    client.get_collections = AsyncMock(return_value=MagicMock(collections=[]))
    mock_response = MagicMock()
    mock_response.points = []
    client.query_points = AsyncMock(return_value=mock_response)
    return client


@pytest.fixture
def mock_openfga_client() -> AsyncMock:
    """Create a mock OpenFGA client."""
    client = AsyncMock()
    client.check_permission = AsyncMock(return_value=True)
    return client


@pytest.mark.xdist_group(name="semantic_index_auth_caching")
class TestAuthorizationCachingConfig:
    """Tests for authorization caching configuration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_semantic_index_manager_has_cache_ttl_config(
        self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock
    ) -> None:
        """SemanticIndexManager should accept cache_ttl_seconds parameter."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
            auth_cache_ttl_seconds=30,
        )

        assert manager.auth_cache_ttl_seconds == 30

    def test_semantic_index_manager_default_cache_ttl(
        self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock
    ) -> None:
        """SemanticIndexManager should have default cache TTL of 60 seconds."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
        )

        assert manager.auth_cache_ttl_seconds == 60

    def test_semantic_index_manager_can_disable_cache(
        self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock
    ) -> None:
        """SemanticIndexManager should allow disabling cache with TTL=0."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
            auth_cache_ttl_seconds=0,
        )

        assert manager.auth_cache_ttl_seconds == 0


@pytest.mark.xdist_group(name="semantic_index_auth_caching")
class TestAuthorizationCachingBehavior:
    """Tests for authorization caching behavior."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_authorization_result_is_cached(
        self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock, mock_openfga_client: AsyncMock
    ) -> None:
        """Positive authorization results should be cached."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        mock_openfga_client.check_permission = AsyncMock(return_value=True)

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
            auth_cache_ttl_seconds=60,
        )

        with patch(
            "mcp_server_langgraph.core.semantic_index_manager.get_openfga_client",
            return_value=mock_openfga_client,
        ):
            # First call should hit OpenFGA
            result1 = await manager._check_authorization(
                user_id="user:alice",
                relation="viewer",
                object_type="tool_index",
                object_id="default",
            )

            # Second call should use cache
            result2 = await manager._check_authorization(
                user_id="user:alice",
                relation="viewer",
                object_type="tool_index",
                object_id="default",
            )

        assert result1 is True
        assert result2 is True
        # OpenFGA should only be called once due to caching
        assert mock_openfga_client.check_permission.call_count == 1

    @pytest.mark.asyncio
    async def test_different_users_have_separate_cache_entries(
        self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock, mock_openfga_client: AsyncMock
    ) -> None:
        """Different users should have separate cache entries."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        mock_openfga_client.check_permission = AsyncMock(return_value=True)

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
            auth_cache_ttl_seconds=60,
        )

        with patch(
            "mcp_server_langgraph.core.semantic_index_manager.get_openfga_client",
            return_value=mock_openfga_client,
        ):
            # Alice's authorization
            await manager._check_authorization(
                user_id="user:alice",
                relation="viewer",
                object_type="tool_index",
            )

            # Bob's authorization (should be a new call)
            await manager._check_authorization(
                user_id="user:bob",
                relation="viewer",
                object_type="tool_index",
            )

        # Both users should trigger OpenFGA calls
        assert mock_openfga_client.check_permission.call_count == 2

    @pytest.mark.asyncio
    async def test_different_resources_have_separate_cache_entries(
        self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock, mock_openfga_client: AsyncMock
    ) -> None:
        """Different resources should have separate cache entries."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        mock_openfga_client.check_permission = AsyncMock(return_value=True)

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
            auth_cache_ttl_seconds=60,
        )

        with patch(
            "mcp_server_langgraph.core.semantic_index_manager.get_openfga_client",
            return_value=mock_openfga_client,
        ):
            # tool_index authorization
            await manager._check_authorization(
                user_id="user:alice",
                relation="viewer",
                object_type="tool_index",
            )

            # skill_index authorization (should be a new call)
            await manager._check_authorization(
                user_id="user:alice",
                relation="viewer",
                object_type="skill_index",
            )

        # Both resources should trigger OpenFGA calls
        assert mock_openfga_client.check_permission.call_count == 2

    @pytest.mark.asyncio
    async def test_denied_results_are_not_cached(
        self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock, mock_openfga_client: AsyncMock
    ) -> None:
        """Denied authorization results should NOT be cached (security best practice)."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        mock_openfga_client.check_permission = AsyncMock(return_value=False)

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
            auth_cache_ttl_seconds=60,
        )

        with patch(
            "mcp_server_langgraph.core.semantic_index_manager.get_openfga_client",
            return_value=mock_openfga_client,
        ):
            # First call - denied
            result1 = await manager._check_authorization(
                user_id="user:bob",
                relation="admin",
                object_type="tool_index",
            )

            # Second call - should NOT use cache for denied results
            result2 = await manager._check_authorization(
                user_id="user:bob",
                relation="admin",
                object_type="tool_index",
            )

        assert result1 is False
        assert result2 is False
        # Both calls should hit OpenFGA (no caching for denials)
        assert mock_openfga_client.check_permission.call_count == 2

    @pytest.mark.asyncio
    async def test_cache_disabled_when_ttl_is_zero(
        self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock, mock_openfga_client: AsyncMock
    ) -> None:
        """Caching should be disabled when TTL is 0."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        mock_openfga_client.check_permission = AsyncMock(return_value=True)

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
            auth_cache_ttl_seconds=0,  # Disable caching
        )

        with patch(
            "mcp_server_langgraph.core.semantic_index_manager.get_openfga_client",
            return_value=mock_openfga_client,
        ):
            # Multiple calls
            await manager._check_authorization(
                user_id="user:alice",
                relation="viewer",
                object_type="tool_index",
            )
            await manager._check_authorization(
                user_id="user:alice",
                relation="viewer",
                object_type="tool_index",
            )

        # Both should hit OpenFGA (no caching)
        assert mock_openfga_client.check_permission.call_count == 2


@pytest.mark.xdist_group(name="semantic_index_auth_caching")
class TestAuthorizationCacheExpiry:
    """Tests for authorization cache expiry."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_cache_expires_after_ttl(
        self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock, mock_openfga_client: AsyncMock
    ) -> None:
        """Cached entries should expire after TTL."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        mock_openfga_client.check_permission = AsyncMock(return_value=True)

        # Use very short TTL for testing
        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
            auth_cache_ttl_seconds=0.1,  # 100ms TTL
        )

        with patch(
            "mcp_server_langgraph.core.semantic_index_manager.get_openfga_client",
            return_value=mock_openfga_client,
        ):
            # First call
            await manager._check_authorization(
                user_id="user:alice",
                relation="viewer",
                object_type="tool_index",
            )

            # Wait for cache to expire
            await asyncio.sleep(0.15)

            # Second call - should hit OpenFGA again
            await manager._check_authorization(
                user_id="user:alice",
                relation="viewer",
                object_type="tool_index",
            )

        # Both should hit OpenFGA due to expiry
        assert mock_openfga_client.check_permission.call_count == 2

    @pytest.mark.asyncio
    async def test_cache_clear_method_exists(
        self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock
    ) -> None:
        """SemanticIndexManager should have a method to clear the auth cache."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
        )

        # Should have clear_auth_cache method
        assert hasattr(manager, "clear_auth_cache")
        assert callable(manager.clear_auth_cache)

    @pytest.mark.asyncio
    async def test_cache_clear_forces_new_auth_check(
        self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock, mock_openfga_client: AsyncMock
    ) -> None:
        """Clearing cache should force new authorization check."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        mock_openfga_client.check_permission = AsyncMock(return_value=True)

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
            auth_cache_ttl_seconds=60,
        )

        with patch(
            "mcp_server_langgraph.core.semantic_index_manager.get_openfga_client",
            return_value=mock_openfga_client,
        ):
            # First call
            await manager._check_authorization(
                user_id="user:alice",
                relation="viewer",
                object_type="tool_index",
            )

            # Clear cache
            manager.clear_auth_cache()

            # Second call - should hit OpenFGA again
            await manager._check_authorization(
                user_id="user:alice",
                relation="viewer",
                object_type="tool_index",
            )

        # Both should hit OpenFGA due to cache clear
        assert mock_openfga_client.check_permission.call_count == 2
