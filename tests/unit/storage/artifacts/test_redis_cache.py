"""
Tests for Redis Cached Artifacts Service.

TDD RED Phase: These tests define the expected behavior of RedisCachedArtifactsService.

The cache layer wraps PostgresArtifactsRepository and provides:
- Cache-aside pattern for reads
- Write-through for updates
- Cache invalidation on deletes
- TTL-based expiration
"""

from __future__ import annotations

import gc
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.unit

# Test constants
TEST_USER_ID = "user-cache-123"
TEST_SESSION_ID = "session-cache-456"
TEST_ARTIFACT_ID = "art-cache-789"
CACHE_TTL = 300  # 5 minutes


def create_mock_artifact_dict(
    artifact_id: str = TEST_ARTIFACT_ID,
    user_id: str = TEST_USER_ID,
    session_id: str = TEST_SESSION_ID,
    **overrides: Any,
) -> dict[str, Any]:
    """Create mock artifact dictionary for testing."""
    now = datetime.now(UTC).isoformat()
    base = {
        "id": artifact_id,
        "session_id": session_id,
        "user_id": user_id,
        "type": "code",
        "title": "Cached Artifact",
        "content": "console.log('cached');",
        "content_type": "code",
        "version": 1,
        "storage_type": "inline",
        "storage_key": None,
        "edit_metadata": None,
        "created_at": now,
        "updated_at": now,
    }
    base.update(overrides)
    return base


@pytest.mark.xdist_group(name="test_redis_cached_artifacts")
@pytest.mark.unit
class TestRedisCachedArtifactsServiceGet:
    """Tests for cache-aside read pattern."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_returns_cached_artifact_on_hit(self) -> None:
        """Test that get returns cached artifact without hitting database."""
        from mcp_server_langgraph.storage.artifacts.redis_cache import (
            RedisCachedArtifactsService,
        )

        mock_repo = AsyncMock(return_value=None)
        mock_cache = MagicMock()

        # Cache hit
        cached_artifact = create_mock_artifact_dict()
        mock_cache.aget = AsyncMock(return_value=cached_artifact)

        service = RedisCachedArtifactsService(
            repository=mock_repo,
            cache=mock_cache,
            ttl=CACHE_TTL,
        )

        # Act
        result = await service.get(TEST_ARTIFACT_ID, user_id=TEST_USER_ID)

        # Assert
        assert result is not None
        assert result["id"] == TEST_ARTIFACT_ID
        # Repository should NOT be called on cache hit
        mock_repo.get.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_get_fetches_from_db_on_cache_miss(self) -> None:
        """Test that get fetches from database on cache miss."""
        from mcp_server_langgraph.storage.artifacts.redis_cache import (
            RedisCachedArtifactsService,
        )

        mock_repo = AsyncMock(return_value=None)
        mock_cache = MagicMock()

        # Cache miss
        mock_cache.aget = AsyncMock(return_value=None)
        mock_cache.aset = AsyncMock(return_value=None)

        # DB has the artifact
        db_artifact = create_mock_artifact_dict()
        mock_repo.get = AsyncMock(return_value=db_artifact)

        service = RedisCachedArtifactsService(
            repository=mock_repo,
            cache=mock_cache,
            ttl=CACHE_TTL,
        )

        # Act
        result = await service.get(TEST_ARTIFACT_ID, user_id=TEST_USER_ID)

        # Assert
        assert result is not None
        assert result["id"] == TEST_ARTIFACT_ID
        # Repository should be called
        mock_repo.get.assert_awaited_once_with(TEST_ARTIFACT_ID, user_id=TEST_USER_ID)
        # Cache should be populated
        mock_cache.aset.assert_awaited()

    @pytest.mark.asyncio
    async def test_get_returns_none_when_not_found(self) -> None:
        """Test that get returns None when artifact not in cache or DB."""
        from mcp_server_langgraph.storage.artifacts.redis_cache import (
            RedisCachedArtifactsService,
        )

        mock_repo = AsyncMock(return_value=None)
        mock_cache = MagicMock()

        # Cache miss
        mock_cache.aget = AsyncMock(return_value=None)
        # DB also doesn't have it
        mock_repo.get = AsyncMock(return_value=None)

        service = RedisCachedArtifactsService(
            repository=mock_repo,
            cache=mock_cache,
            ttl=CACHE_TTL,
        )

        # Act
        result = await service.get("non-existent", user_id=TEST_USER_ID)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_get_generates_correct_cache_key(self) -> None:
        """Test that cache key includes artifact_id and user_id for security."""
        from mcp_server_langgraph.storage.artifacts.redis_cache import (
            RedisCachedArtifactsService,
        )

        mock_repo = AsyncMock(return_value=None)
        mock_cache = MagicMock()

        cached_artifact = create_mock_artifact_dict()
        mock_cache.aget = AsyncMock(return_value=cached_artifact)

        service = RedisCachedArtifactsService(
            repository=mock_repo,
            cache=mock_cache,
            ttl=CACHE_TTL,
        )

        # Act
        await service.get(TEST_ARTIFACT_ID, user_id=TEST_USER_ID)

        # Assert - verify cache key format
        mock_cache.aget.assert_awaited_once()
        call_args = mock_cache.aget.call_args
        cache_key = call_args[0][0]  # First positional argument
        assert TEST_ARTIFACT_ID in cache_key
        assert TEST_USER_ID in cache_key


@pytest.mark.xdist_group(name="test_redis_cached_artifacts")
@pytest.mark.unit
class TestRedisCachedArtifactsServiceCreate:
    """Tests for write-through create pattern."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_create_writes_to_db_and_cache(self) -> None:
        """Test that create writes to database then caches the result."""
        from mcp_server_langgraph.storage.artifacts.redis_cache import (
            RedisCachedArtifactsService,
        )

        mock_repo = AsyncMock(return_value=None)
        mock_cache = MagicMock()
        mock_cache.aset = AsyncMock(return_value=None)

        # DB create returns new artifact
        create_result = {"id": "art-new-123", "version": 1, "created_at": "2025-01-01T00:00:00Z"}
        mock_repo.create = AsyncMock(return_value=create_result)

        service = RedisCachedArtifactsService(
            repository=mock_repo,
            cache=mock_cache,
            ttl=CACHE_TTL,
        )

        artifact_data = {
            "type": "code",
            "content": "new content",
            "session_id": TEST_SESSION_ID,
        }

        # Act
        result = await service.create(artifact_data, user_id=TEST_USER_ID)

        # Assert
        assert result is not None
        assert result["id"] == "art-new-123"
        mock_repo.create.assert_awaited_once()


@pytest.mark.xdist_group(name="test_redis_cached_artifacts")
@pytest.mark.unit
class TestRedisCachedArtifactsServiceUpdate:
    """Tests for write-through update pattern with cache invalidation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_update_invalidates_cache_then_writes(self) -> None:
        """Test that update invalidates cache before writing to DB."""
        from mcp_server_langgraph.storage.artifacts.redis_cache import (
            RedisCachedArtifactsService,
        )

        mock_repo = AsyncMock(return_value=None)
        mock_cache = MagicMock()
        mock_cache.adelete = AsyncMock(return_value=None)

        # DB update returns updated artifact
        update_result = {"id": TEST_ARTIFACT_ID, "version": 2, "updated_at": "2025-01-01T00:00:00Z"}
        mock_repo.update = AsyncMock(return_value=update_result)

        service = RedisCachedArtifactsService(
            repository=mock_repo,
            cache=mock_cache,
            ttl=CACHE_TTL,
        )

        update_data = {"content": "updated content"}

        # Act
        result = await service.update(TEST_ARTIFACT_ID, update_data, user_id=TEST_USER_ID)

        # Assert
        assert result is not None
        assert result["version"] == 2
        # Cache should be invalidated
        mock_cache.adelete.assert_awaited()
        mock_repo.update.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_returns_none_when_not_found(self) -> None:
        """Test that update returns None when artifact doesn't exist."""
        from mcp_server_langgraph.storage.artifacts.redis_cache import (
            RedisCachedArtifactsService,
        )

        mock_repo = AsyncMock(return_value=None)
        mock_cache = MagicMock()
        mock_cache.adelete = AsyncMock(return_value=None)

        # DB update returns None (not found or not owned)
        mock_repo.update = AsyncMock(return_value=None)

        service = RedisCachedArtifactsService(
            repository=mock_repo,
            cache=mock_cache,
            ttl=CACHE_TTL,
        )

        # Act
        result = await service.update("non-existent", {"content": "x"}, user_id=TEST_USER_ID)

        # Assert
        assert result is None


@pytest.mark.xdist_group(name="test_redis_cached_artifacts")
@pytest.mark.unit
class TestRedisCachedArtifactsServiceDelete:
    """Tests for delete with cache invalidation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_delete_invalidates_cache(self) -> None:
        """Test that delete invalidates cache entry."""
        from mcp_server_langgraph.storage.artifacts.redis_cache import (
            RedisCachedArtifactsService,
        )

        mock_repo = AsyncMock(return_value=None)
        mock_cache = MagicMock()
        mock_cache.adelete = AsyncMock(return_value=None)

        # DB delete succeeds
        mock_repo.delete = AsyncMock(return_value=True)

        service = RedisCachedArtifactsService(
            repository=mock_repo,
            cache=mock_cache,
            ttl=CACHE_TTL,
        )

        # Act
        result = await service.delete(TEST_ARTIFACT_ID, user_id=TEST_USER_ID)

        # Assert
        assert result is True
        mock_cache.adelete.assert_awaited()
        mock_repo.delete.assert_awaited_once()


@pytest.mark.xdist_group(name="test_redis_cached_artifacts")
@pytest.mark.unit
class TestRedisCachedArtifactsServiceList:
    """Tests for list operations (cache bypass for freshness)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_list_bypasses_cache_for_freshness(self) -> None:
        """Test that list always hits database for fresh results."""
        from mcp_server_langgraph.storage.artifacts.redis_cache import (
            RedisCachedArtifactsService,
        )

        mock_repo = AsyncMock(return_value=None)
        mock_cache = MagicMock()

        # DB returns list
        artifacts = [create_mock_artifact_dict(artifact_id=f"art-{i}") for i in range(3)]
        mock_repo.list = AsyncMock(return_value=(artifacts, None, False))

        service = RedisCachedArtifactsService(
            repository=mock_repo,
            cache=mock_cache,
            ttl=CACHE_TTL,
        )

        # Act
        items, cursor, has_more = await service.list(user_id=TEST_USER_ID)

        # Assert - directly from DB, not cache
        assert len(items) == 3
        mock_repo.list.assert_awaited_once()


@pytest.mark.xdist_group(name="test_redis_cached_artifacts")
@pytest.mark.unit
class TestRedisCachedArtifactsServiceVersions:
    """Tests for version history operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_versions_uses_cache(self) -> None:
        """Test that get_versions uses cache for version history."""
        from mcp_server_langgraph.storage.artifacts.redis_cache import (
            RedisCachedArtifactsService,
        )

        mock_repo = AsyncMock(return_value=None)
        mock_cache = MagicMock()

        # Cache miss for versions
        mock_cache.aget = AsyncMock(return_value=None)
        mock_cache.aset = AsyncMock(return_value=None)

        # DB returns versions
        versions = [{"id": f"ver-{i}", "version": i} for i in range(1, 4)]
        mock_repo.get_versions = AsyncMock(return_value=versions)

        service = RedisCachedArtifactsService(
            repository=mock_repo,
            cache=mock_cache,
            ttl=CACHE_TTL,
        )

        # Act
        result = await service.get_versions(TEST_ARTIFACT_ID, user_id=TEST_USER_ID)

        # Assert
        assert result is not None
        assert len(result) == 3
        mock_repo.get_versions.assert_awaited_once()
        # Versions should be cached
        mock_cache.aset.assert_awaited()


@pytest.mark.xdist_group(name="test_redis_cached_artifacts")
@pytest.mark.unit
class TestRedisCachedArtifactsServiceFork:
    """Tests for fork operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_fork_does_not_cache_immediately(self) -> None:
        """Test that fork creates new artifact without caching source."""
        from mcp_server_langgraph.storage.artifacts.redis_cache import (
            RedisCachedArtifactsService,
        )

        mock_repo = AsyncMock(return_value=None)
        mock_cache = MagicMock()

        # DB fork returns new artifact
        fork_result = {"id": "art-forked-123", "parent_id": TEST_ARTIFACT_ID, "version": 1}
        mock_repo.fork = AsyncMock(return_value=fork_result)

        service = RedisCachedArtifactsService(
            repository=mock_repo,
            cache=mock_cache,
            ttl=CACHE_TTL,
        )

        # Act
        result = await service.fork(TEST_ARTIFACT_ID, new_name="Fork", user_id=TEST_USER_ID)

        # Assert
        assert result is not None
        assert result["id"] == "art-forked-123"
        mock_repo.fork.assert_awaited_once()


@pytest.mark.xdist_group(name="test_redis_cached_artifacts")
@pytest.mark.unit
class TestRedisCachedArtifactsServiceCacheFailure:
    """Tests for graceful degradation when cache is unavailable."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_falls_back_to_db_on_cache_error(self) -> None:
        """Test that get falls back to database when cache raises error."""
        from mcp_server_langgraph.storage.artifacts.redis_cache import (
            RedisCachedArtifactsService,
        )

        mock_repo = AsyncMock(return_value=None)
        mock_cache = MagicMock()

        # Cache raises error
        mock_cache.aget = AsyncMock(side_effect=Exception("Redis unavailable"))

        # DB has the artifact
        db_artifact = create_mock_artifact_dict()
        mock_repo.get = AsyncMock(return_value=db_artifact)

        service = RedisCachedArtifactsService(
            repository=mock_repo,
            cache=mock_cache,
            ttl=CACHE_TTL,
        )

        # Act - should not raise
        result = await service.get(TEST_ARTIFACT_ID, user_id=TEST_USER_ID)

        # Assert - graceful degradation
        assert result is not None
        assert result["id"] == TEST_ARTIFACT_ID
        mock_repo.get.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_cache_set_failure_does_not_block_operation(self) -> None:
        """Test that cache set failure doesn't block the operation."""
        from mcp_server_langgraph.storage.artifacts.redis_cache import (
            RedisCachedArtifactsService,
        )

        mock_repo = AsyncMock(return_value=None)
        mock_cache = MagicMock()

        # Cache miss
        mock_cache.aget = AsyncMock(return_value=None)
        # Cache set fails
        mock_cache.aset = AsyncMock(side_effect=Exception("Redis write failed"))

        # DB returns artifact
        db_artifact = create_mock_artifact_dict()
        mock_repo.get = AsyncMock(return_value=db_artifact)

        service = RedisCachedArtifactsService(
            repository=mock_repo,
            cache=mock_cache,
            ttl=CACHE_TTL,
        )

        # Act - should not raise despite cache failure
        result = await service.get(TEST_ARTIFACT_ID, user_id=TEST_USER_ID)

        # Assert
        assert result is not None
        assert result["id"] == TEST_ARTIFACT_ID
