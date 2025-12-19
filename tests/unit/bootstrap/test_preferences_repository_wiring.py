"""
Preferences Repository Wiring Tests

Tests for conditional RedisPreferencesRepository wiring.

These tests verify that:
1. create_preferences_repository function exists
2. It returns RedisPreferencesRepository when Redis client is provided
3. It returns InMemoryPreferencesRepository when Redis client is None
"""

import gc
from unittest.mock import AsyncMock

import pytest


pytestmark = [
    pytest.mark.unit,
]


@pytest.mark.xdist_group(name="test_preferences_wiring")
class TestCreatePreferencesRepository:
    """Tests for create_preferences_repository helper function."""

    def teardown_method(self) -> None:
        """Clean up after each test."""
        gc.collect()

    def test_create_preferences_repository_exists(self) -> None:
        """
        GIVEN the bootstrap.storage module
        WHEN importing create_preferences_repository
        THEN it should exist and be callable
        """
        from mcp_server_langgraph.bootstrap.storage import create_preferences_repository

        assert callable(create_preferences_repository)

    def test_returns_redis_repository_when_client_provided(self) -> None:
        """
        GIVEN a Redis client
        WHEN create_preferences_repository is called with the client
        THEN it should return RedisPreferencesRepository
        """
        from mcp_server_langgraph.bootstrap.storage import create_preferences_repository
        from mcp_server_langgraph.notifications.preferences import (
            RedisPreferencesRepository,
        )

        mock_redis = AsyncMock()  # noqa: async-mock-config

        repo = create_preferences_repository(redis_client=mock_redis)

        assert isinstance(repo, RedisPreferencesRepository)

    def test_returns_inmemory_repository_when_no_client(self) -> None:
        """
        GIVEN no Redis client (None)
        WHEN create_preferences_repository is called
        THEN it should return InMemoryPreferencesRepository
        """
        from mcp_server_langgraph.bootstrap.storage import create_preferences_repository
        from mcp_server_langgraph.notifications.preferences import (
            InMemoryPreferencesRepository,
        )

        repo = create_preferences_repository(redis_client=None)

        assert isinstance(repo, InMemoryPreferencesRepository)

    def test_redis_repository_uses_provided_client(self) -> None:
        """
        GIVEN a Redis client
        WHEN create_preferences_repository is called
        THEN the returned repository should use that client
        """
        from mcp_server_langgraph.bootstrap.storage import create_preferences_repository

        mock_redis = AsyncMock()  # noqa: async-mock-config

        repo = create_preferences_repository(redis_client=mock_redis)

        # The repository should have a _redis attribute
        assert hasattr(repo, "_redis")
        assert repo._redis is mock_redis
