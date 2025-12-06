"""
Playground Test Fixtures

Shared fixtures for playground tests to avoid Redis connections in unit tests.
"""

from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock

import pytest


@pytest.fixture
def mock_redis() -> AsyncMock:
    """Create a mock Redis client for unit testing."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock()
    redis.delete = AsyncMock()
    redis.expire = AsyncMock()
    redis.sadd = AsyncMock()
    redis.srem = AsyncMock()
    redis.smembers = AsyncMock(return_value=set())
    redis.rpush = AsyncMock()
    redis.ltrim = AsyncMock()
    redis.lrange = AsyncMock(return_value=[])
    redis.llen = AsyncMock(return_value=0)
    redis.ping = AsyncMock()
    redis.close = AsyncMock()
    return redis


@pytest.fixture
def mock_session_manager(mock_redis: AsyncMock) -> AsyncMock:
    """Create a mock session manager to avoid Redis connections."""
    from mcp_server_langgraph.playground.session.manager import Session

    manager = AsyncMock()

    # Mock session for tests
    test_session = Session(
        id="test-session-123",
        user_id="test-user-123",
        name="Test Session",
        created_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        message_count=0,
    )

    manager.list_sessions = AsyncMock(return_value=[test_session])
    manager.get_session = AsyncMock(return_value=test_session)
    manager.create_session = AsyncMock(return_value=test_session)
    manager.delete_session = AsyncMock(return_value=True)
    manager.add_message = AsyncMock(
        return_value={"id": "msg-1", "role": "user", "content": "test", "timestamp": datetime.now(UTC).isoformat()}
    )
    manager.get_messages = AsyncMock(return_value=[])
    manager.refresh_session = AsyncMock(return_value=True)
    manager._get_redis = AsyncMock(return_value=mock_redis)
    manager.close = AsyncMock()

    return manager


@pytest.fixture
def app_with_mock_manager(mock_session_manager: AsyncMock):
    """Create app with mocked session manager."""
    from mcp_server_langgraph.playground.api import server

    # Save original function and manager
    original_get_manager = server.get_session_manager
    original_manager = server._session_manager

    # Replace with mock
    server._session_manager = mock_session_manager
    server.get_session_manager = lambda: mock_session_manager

    yield server.app

    # Restore
    server._session_manager = original_manager
    server.get_session_manager = original_get_manager
