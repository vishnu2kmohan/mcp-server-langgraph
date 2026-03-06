"""
Redis Preferences Repository Tests.

TDD tests for Redis-backed notification preferences storage.
Uses mocked Redis to test without real infrastructure.
"""

from __future__ import annotations

import gc
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = [
    pytest.mark.unit,
    pytest.mark.asyncio,
    pytest.mark.redis,
]


@pytest.fixture
def mock_redis() -> MagicMock:
    """Create a mock Redis client."""
    mock = MagicMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=1)
    return mock


class TestRedisPreferencesRepository:
    """Tests for Redis-backed preferences repository."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_get_returns_none_for_missing_key(self, mock_redis: MagicMock) -> None:
        """
        GIVEN a Redis repository
        WHEN getting preferences for unknown user
        THEN it should return None.
        """
        from mcp_server_langgraph.notifications.preferences import RedisPreferencesRepository

        mock_redis.get = AsyncMock(return_value=None)
        repo = RedisPreferencesRepository(redis_client=mock_redis)

        result = await repo.get("user:unknown")

        assert result is None
        mock_redis.get.assert_called_once_with("notification_preferences:user:unknown")

    async def test_get_returns_preferences_from_redis(self, mock_redis: MagicMock) -> None:
        """
        GIVEN preferences stored in Redis
        WHEN getting preferences
        THEN the stored preferences are returned.
        """
        from mcp_server_langgraph.notifications.preferences import RedisPreferencesRepository

        stored_data = json.dumps(
            {
                "user_id": "user:alice",
                "info_enabled": False,
                "success_enabled": True,
                "warning_enabled": True,
                "error_enabled": True,
            }
        )
        mock_redis.get = AsyncMock(return_value=stored_data)
        repo = RedisPreferencesRepository(redis_client=mock_redis)

        result = await repo.get("user:alice")

        assert result is not None
        assert result.user_id == "user:alice"
        assert result.info_enabled is False
        assert result.success_enabled is True

    async def test_save_stores_preferences_in_redis(self, mock_redis: MagicMock) -> None:
        """
        GIVEN preferences to save
        WHEN calling save
        THEN preferences are stored in Redis with correct key.
        """
        from mcp_server_langgraph.notifications.preferences import (
            NotificationPreferences,
            RedisPreferencesRepository,
        )

        repo = RedisPreferencesRepository(redis_client=mock_redis)
        prefs = NotificationPreferences(
            user_id="user:alice",
            info_enabled=False,
            success_enabled=True,
            warning_enabled=True,
            error_enabled=True,
        )

        await repo.save(prefs)

        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert call_args[0][0] == "notification_preferences:user:alice"
        # Verify stored JSON contains correct values
        stored_json = call_args[0][1]
        stored_data = json.loads(stored_json)
        assert stored_data["user_id"] == "user:alice"
        assert stored_data["info_enabled"] is False

    async def test_delete_removes_preferences_from_redis(self, mock_redis: MagicMock) -> None:
        """
        GIVEN preferences stored in Redis
        WHEN deleting preferences
        THEN the key is removed from Redis.
        """
        from mcp_server_langgraph.notifications.preferences import RedisPreferencesRepository

        repo = RedisPreferencesRepository(redis_client=mock_redis)

        await repo.delete("user:alice")

        mock_redis.delete.assert_called_once_with("notification_preferences:user:alice")

    async def test_key_prefix_is_customizable(self, mock_redis: MagicMock) -> None:
        """
        GIVEN a custom key prefix
        WHEN performing operations
        THEN the custom prefix is used.
        """
        from mcp_server_langgraph.notifications.preferences import RedisPreferencesRepository

        repo = RedisPreferencesRepository(
            redis_client=mock_redis,
            key_prefix="custom_prefix:",
        )

        await repo.get("user:alice")

        mock_redis.get.assert_called_once_with("custom_prefix:user:alice")

    async def test_handles_malformed_json_gracefully(self, mock_redis: MagicMock) -> None:
        """
        GIVEN malformed JSON in Redis
        WHEN getting preferences
        THEN it should return None and log warning.
        """
        from mcp_server_langgraph.notifications.preferences import RedisPreferencesRepository

        mock_redis.get = AsyncMock(return_value="not valid json{")
        repo = RedisPreferencesRepository(redis_client=mock_redis)

        result = await repo.get("user:alice")

        assert result is None

    async def test_handles_redis_connection_error_on_get(self, mock_redis: MagicMock) -> None:
        """
        GIVEN a Redis connection error
        WHEN getting preferences
        THEN it should return None gracefully.
        """
        from mcp_server_langgraph.notifications.preferences import RedisPreferencesRepository

        mock_redis.get = AsyncMock(side_effect=Exception("Connection refused"))
        repo = RedisPreferencesRepository(redis_client=mock_redis)

        result = await repo.get("user:alice")

        assert result is None

    async def test_handles_redis_connection_error_on_save(self, mock_redis: MagicMock) -> None:
        """
        GIVEN a Redis connection error
        WHEN saving preferences
        THEN it should not raise (graceful degradation).
        """
        from mcp_server_langgraph.notifications.preferences import (
            NotificationPreferences,
            RedisPreferencesRepository,
        )

        mock_redis.set = AsyncMock(side_effect=Exception("Connection refused"))
        repo = RedisPreferencesRepository(redis_client=mock_redis)
        prefs = NotificationPreferences.default(user_id="user:alice")

        # Should not raise
        await repo.save(prefs)
