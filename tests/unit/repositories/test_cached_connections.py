"""
Tests for CachedConnectionRepository

Tests the multi-layer caching functionality:
- L1 in-memory cache behavior
- L2 Redis cache behavior
- Cache invalidation on writes
- Cache hit/miss metrics
"""

import gc
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_server_langgraph.core.cache import CacheService
from mcp_server_langgraph.repositories.cached_connections import (
    CachedConnectionRepository,
)
from mcp_server_langgraph.repositories.connections import ConnectionRepository
from mcp_server_langgraph.storage.models import (
    MCPConnection,
    MCPConnectionCreate,
    MCPConnectionSummary,
    MCPConnectionUpdate,
)

pytestmark = [pytest.mark.unit, pytest.mark.repository]


@pytest.fixture
def mock_delegate():
    """Create a mock delegate repository."""
    delegate = MagicMock(spec=ConnectionRepository)

    # Setup async mocks for all methods
    delegate.get = AsyncMock()  # async-mock-configured
    delegate.get_many = AsyncMock()  # async-mock-configured
    delegate.list = AsyncMock()  # async-mock-configured
    delegate.create = AsyncMock()  # async-mock-configured
    delegate.update = AsyncMock()  # async-mock-configured
    delegate.delete = AsyncMock()  # async-mock-configured
    delegate.store_api_key = AsyncMock()  # async-mock-configured
    delegate.get_api_key = AsyncMock()  # async-mock-configured
    delegate.create_oauth2_state = AsyncMock()  # async-mock-configured
    delegate.get_and_delete_oauth2_state = AsyncMock()  # async-mock-configured
    delegate.store_oauth2_tokens = AsyncMock()  # async-mock-configured
    delegate.get_oauth2_access_token = AsyncMock()  # async-mock-configured
    delegate.update_status = AsyncMock()  # async-mock-configured

    return delegate


@pytest.fixture
def mock_cache():
    """Create a mock cache service."""
    cache = MagicMock(spec=CacheService)
    cache.get = MagicMock(return_value=None)  # Default: cache miss
    cache.set = MagicMock()
    cache.delete = MagicMock()
    cache.clear = MagicMock()
    cache.get_statistics = MagicMock(return_value={})
    return cache


@pytest.fixture
def sample_connection():
    """Create a sample connection for tests."""
    return MCPConnection(
        id="conn-123",
        name="Test Connection",
        description="A test MCP connection",
        url="http://localhost:8765",
        auth_type="none",
        status="connected",
        owner_id="user-456",
        tool_count=5,
        resource_count=3,
        prompt_count=2,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def cached_repo(mock_delegate, mock_cache):
    """Create a cached repository with mocks."""
    return CachedConnectionRepository(mock_delegate, mock_cache)


@pytest.mark.xdist_group(name="cached_connections_tests")
class TestCachedConnectionGet:
    """Tests for get() with caching."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_returns_cached_value_on_hit(
        self,
        cached_repo,
        mock_cache,
        mock_delegate,
        sample_connection,
    ):
        """Should return cached connection without hitting database."""
        # Setup: cache returns connection data
        mock_cache.get.return_value = sample_connection.model_dump()

        # Execute
        result = await cached_repo.get("conn-123")

        # Verify
        assert result is not None
        assert result.id == "conn-123"
        mock_cache.get.assert_called_once()
        mock_delegate.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_fetches_from_db_on_cache_miss(
        self,
        cached_repo,
        mock_cache,
        mock_delegate,
        sample_connection,
    ):
        """Should fetch from database and cache on miss."""
        # Setup: cache miss
        mock_cache.get.return_value = None
        mock_delegate.get.return_value = sample_connection

        # Execute
        result = await cached_repo.get("conn-123")

        # Verify
        assert result is not None
        assert result.id == "conn-123"
        mock_delegate.get.assert_called_once_with("conn-123")
        mock_cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_returns_none_for_nonexistent(
        self,
        cached_repo,
        mock_cache,
        mock_delegate,
    ):
        """Should return None for non-existent connection."""
        mock_cache.get.return_value = None
        mock_delegate.get.return_value = None

        result = await cached_repo.get("nonexistent")

        assert result is None
        mock_cache.set.assert_not_called()


@pytest.mark.xdist_group(name="cached_connections_tests")
class TestCachedConnectionGetMany:
    """Tests for get_many() with caching."""

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_many_uses_cache_for_hits(
        self,
        cached_repo,
        mock_cache,
        mock_delegate,
        sample_connection,
    ):
        """Should use cache for available connections."""
        # Setup: first connection cached, second not
        conn2 = MCPConnection(
            id="conn-456",
            name="Second Connection",
            url="http://localhost:8766",
            auth_type="none",
            status="disconnected",
            owner_id="user-456",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        # Mock cache to return first, miss second
        mock_cache.get.side_effect = [
            sample_connection.model_dump(),  # First: hit
            None,  # Second: miss
        ]
        mock_delegate.get_many.return_value = [conn2]

        # Execute
        result = await cached_repo.get_many(["conn-123", "conn-456"])

        # Verify
        assert len(result) == 2
        mock_delegate.get_many.assert_called_once_with(["conn-456"])

    @pytest.mark.asyncio
    async def test_get_many_empty_list(
        self,
        cached_repo,
        mock_delegate,
    ):
        """Should return empty list for empty input."""
        result = await cached_repo.get_many([])

        assert result == []
        mock_delegate.get_many.assert_not_called()


@pytest.mark.xdist_group(name="cached_connections_tests")
class TestCachedConnectionList:
    """Tests for list() with caching."""

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.mark.asyncio
    async def test_list_caches_first_page(
        self,
        cached_repo,
        mock_cache,
        mock_delegate,
    ):
        """Should cache unfiltered first page results."""
        summary = MCPConnectionSummary(
            id="conn-123",
            name="Test",
            url="http://localhost:8765",
            auth_type="none",
            status="connected",
            created_at=datetime.now(UTC),
        )
        mock_cache.get.return_value = None
        mock_delegate.list.return_value = ([summary], "next-cursor")

        # Execute - unfiltered first page
        result, cursor = await cached_repo.list(owner_id="user-456")

        # Verify
        assert len(result) == 1
        mock_cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_does_not_cache_filtered_results(
        self,
        cached_repo,
        mock_cache,
        mock_delegate,
    ):
        """Should not cache filtered results."""
        summary = MCPConnectionSummary(
            id="conn-123",
            name="Test",
            url="http://localhost:8765",
            auth_type="api_key",
            status="connected",
            created_at=datetime.now(UTC),
        )
        mock_cache.get.return_value = None
        mock_delegate.list.return_value = ([summary], None)

        # Execute - with filter
        await cached_repo.list(owner_id="user-456", auth_type="api_key")

        # Verify - no cache set
        mock_cache.set.assert_not_called()

    @pytest.mark.asyncio
    async def test_list_returns_cached_first_page(
        self,
        cached_repo,
        mock_cache,
        mock_delegate,
    ):
        """Should return cached first page without DB query."""
        cached_data = (
            [
                {
                    "id": "conn-123",
                    "name": "Cached",
                    "url": "http://localhost",
                    "auth_type": "none",
                    "status": "connected",
                    "created_at": datetime.now(UTC).isoformat(),
                }
            ],
            "cursor",
        )
        mock_cache.get.return_value = cached_data

        result, cursor = await cached_repo.list(owner_id="user-456")

        assert len(result) == 1
        mock_delegate.list.assert_not_called()


@pytest.mark.xdist_group(name="cached_connections_tests")
class TestCachedConnectionWrites:
    """Tests for write operations with cache invalidation."""

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.mark.asyncio
    async def test_create_invalidates_list_cache(
        self,
        cached_repo,
        mock_cache,
        mock_delegate,
        sample_connection,
    ):
        """Should invalidate owner's list cache on create."""
        mock_delegate.create.return_value = sample_connection

        create_data = MCPConnectionCreate(
            name="New Connection",
            url="http://localhost:8765",
            auth_type="none",
        )

        await cached_repo.create(create_data, "user-456")

        mock_cache.clear.assert_called_once()
        assert "connection_list:user-456" in mock_cache.clear.call_args[0][0]

    @pytest.mark.asyncio
    async def test_update_invalidates_caches(
        self,
        cached_repo,
        mock_cache,
        mock_delegate,
        sample_connection,
    ):
        """Should invalidate connection and list caches on update."""
        mock_delegate.update.return_value = sample_connection

        update_data = MCPConnectionUpdate(name="Updated Name")

        await cached_repo.update("conn-123", update_data)

        # Should delete individual cache and clear list cache
        mock_cache.delete.assert_called()
        mock_cache.clear.assert_called()

    @pytest.mark.asyncio
    async def test_delete_invalidates_all_caches(
        self,
        cached_repo,
        mock_cache,
        mock_delegate,
        sample_connection,
    ):
        """Should invalidate all related caches on delete."""
        mock_delegate.get.return_value = sample_connection
        mock_delegate.delete.return_value = True

        await cached_repo.delete("conn-123")

        # Should delete connection cache, health cache, and clear list cache
        assert mock_cache.delete.call_count >= 2
        mock_cache.clear.assert_called()


@pytest.mark.xdist_group(name="cached_connections_tests")
class TestCachedConnectionHealth:
    """Tests for status updates and health caching."""

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.mark.asyncio
    async def test_update_status_caches_health(
        self,
        cached_repo,
        mock_cache,
        mock_delegate,
    ):
        """Should cache health status separately."""
        await cached_repo.update_status(
            connection_id="conn-123",
            status="connected",
            server_name="Test Server",
            tool_count=5,
        )

        # Should delete connection cache and set health cache
        mock_cache.delete.assert_called()
        mock_cache.set.assert_called_once()

        # Verify health data in cache set
        call_args = mock_cache.set.call_args
        assert "connection_health" in call_args[0][0]
        assert call_args[0][1]["status"] == "connected"

    def test_get_cached_health(
        self,
        cached_repo,
        mock_cache,
    ):
        """Should return cached health without DB query."""
        mock_cache.get.return_value = {
            "status": "connected",
            "tool_count": 5,
        }

        result = cached_repo.get_cached_health("conn-123")

        assert result is not None
        assert result["status"] == "connected"


@pytest.mark.xdist_group(name="cached_connections_tests")
class TestCachedConnectionUtilities:
    """Tests for cache management utilities."""

    def teardown_method(self) -> None:
        gc.collect()

    def test_invalidate_connection_clears_all_related_caches(
        self,
        cached_repo,
        mock_cache,
    ):
        """Should invalidate all caches for a connection."""
        cached_repo.invalidate_connection("conn-123")

        assert mock_cache.delete.call_count == 2

    def test_get_cache_stats(
        self,
        cached_repo,
        mock_cache,
    ):
        """Should return cache statistics."""
        mock_cache.get_statistics.return_value = {
            "l1": {"hits": 100, "misses": 20},
            "l2": {"hits": 50, "misses": 10},
        }

        stats = cached_repo.get_cache_stats()

        assert stats["l1"]["hits"] == 100
        mock_cache.get_statistics.assert_called_once()


@pytest.mark.xdist_group(name="cached_connections_tests")
class TestCachedConnectionDelegation:
    """Tests for methods that delegate without caching."""

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.mark.asyncio
    async def test_store_api_key_delegates(
        self,
        cached_repo,
        mock_delegate,
    ):
        """Should delegate to underlying repository."""
        await cached_repo.store_api_key("conn-123", "secret-key")

        mock_delegate.store_api_key.assert_called_once_with("conn-123", "secret-key")

    @pytest.mark.asyncio
    async def test_get_api_key_does_not_cache(
        self,
        cached_repo,
        mock_cache,
        mock_delegate,
    ):
        """API keys should not be cached for security."""
        mock_delegate.get_api_key.return_value = "secret-key"

        result = await cached_repo.get_api_key("conn-123")

        assert result == "secret-key"
        mock_cache.set.assert_not_called()

    @pytest.mark.asyncio
    async def test_oauth2_state_operations_delegate(
        self,
        cached_repo,
        mock_delegate,
    ):
        """OAuth2 state operations should delegate without caching."""
        await cached_repo.create_oauth2_state("conn-123", "state", "verifier", "redirect")
        mock_delegate.create_oauth2_state.assert_called_once()

        mock_delegate.get_and_delete_oauth2_state.return_value = {"state": "data"}
        result = await cached_repo.get_and_delete_oauth2_state("state")

        assert result is not None
        mock_delegate.get_and_delete_oauth2_state.assert_called_once()
