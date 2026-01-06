"""
Unit tests for PreferencesRepository close functionality.

Tests that RedisPreferencesRepository properly closes its async Redis client.
"""

import gc
from unittest.mock import AsyncMock, MagicMock

import pytest


pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="preferences_close")
class TestPreferencesRepositoryClose:
    """Tests for PreferencesRepository aclose() method."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_redis_preferences_repository_aclose_closes_redis_client(self) -> None:
        """Test that RedisPreferencesRepository.aclose() closes the async Redis client."""
        from mcp_server_langgraph.notifications.preferences import RedisPreferencesRepository

        # Create mock Redis client
        mock_redis = MagicMock()
        mock_redis.aclose = AsyncMock(return_value=None)

        repo = RedisPreferencesRepository(redis_client=mock_redis)

        # Call aclose
        await repo.aclose()

        # Verify Redis client was closed
        mock_redis.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_redis_preferences_repository_aclose_is_idempotent(self) -> None:
        """Test that aclose() can be called multiple times safely."""
        from mcp_server_langgraph.notifications.preferences import RedisPreferencesRepository

        # Create mock Redis client
        mock_redis = MagicMock()
        mock_redis.aclose = AsyncMock(return_value=None)

        repo = RedisPreferencesRepository(redis_client=mock_redis)

        # Call aclose twice
        await repo.aclose()
        await repo.aclose()

        # Should only close once (idempotent)
        assert mock_redis.aclose.call_count == 1

    @pytest.mark.asyncio
    async def test_redis_preferences_repository_aclose_sets_redis_to_none(self) -> None:
        """Test that aclose() sets redis client to None after close."""
        from mcp_server_langgraph.notifications.preferences import RedisPreferencesRepository

        # Create mock Redis client
        mock_redis = MagicMock()
        mock_redis.aclose = AsyncMock(return_value=None)

        repo = RedisPreferencesRepository(redis_client=mock_redis)
        assert repo._redis is not None

        await repo.aclose()

        assert repo._redis is None

    @pytest.mark.asyncio
    async def test_inmemory_preferences_repository_aclose_is_noop(self) -> None:
        """Test that InMemoryPreferencesRepository.aclose() is a no-op."""
        from mcp_server_langgraph.notifications.preferences import InMemoryPreferencesRepository

        repo = InMemoryPreferencesRepository()

        # Should not raise
        await repo.aclose()
        # Should be callable multiple times
        await repo.aclose()

    @pytest.mark.asyncio
    async def test_preferences_repository_abc_has_aclose_method(self) -> None:
        """Test that PreferencesRepository ABC defines aclose() method."""
        from mcp_server_langgraph.notifications.preferences import PreferencesRepository

        # Verify aclose is defined in PreferencesRepository
        assert hasattr(PreferencesRepository, "aclose")
        assert callable(getattr(PreferencesRepository, "aclose", None))


@pytest.mark.xdist_group(name="preferences_close")
class TestStorageStatePreferencesCleanup:
    """Tests for StorageState cleanup of preferences repository."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_storage_state_cleanup_closes_preferences_repository(self) -> None:
        """Test that StorageState.cleanup() closes the preferences repository."""
        from mcp_server_langgraph.bootstrap.storage import StorageState

        # Create mock preferences repository
        mock_repo = MagicMock()
        mock_repo.aclose = AsyncMock(return_value=None)

        state = StorageState(preferences_repository=mock_repo)

        # Call cleanup
        await state.cleanup()

        # Verify preferences repository was closed
        mock_repo.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_storage_state_cleanup_handles_none_preferences_repository(self) -> None:
        """Test that StorageState.cleanup() handles None preferences repository."""
        from mcp_server_langgraph.bootstrap.storage import StorageState

        state = StorageState(preferences_repository=None)

        # Should not raise
        await state.cleanup()

    @pytest.mark.asyncio
    async def test_storage_state_cleanup_handles_preferences_close_error(self) -> None:
        """Test that StorageState.cleanup() handles errors from preferences close."""
        from mcp_server_langgraph.bootstrap.storage import StorageState

        # Create mock that raises on close
        mock_repo = MagicMock()
        mock_repo.aclose = AsyncMock(side_effect=Exception("Close error"))

        state = StorageState(preferences_repository=mock_repo)

        # Should not raise even if close fails
        await state.cleanup()
