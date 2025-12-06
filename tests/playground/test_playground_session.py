"""
Playground Session Management Tests (TDD Red Phase)

Tests for the session manager that handles Redis-backed session storage.
Following TDD: These tests are written BEFORE the implementation.

Test Coverage:
- Session creation and storage
- Session retrieval
- Session deletion
- Session expiration
- Message history within sessions
"""

import gc
import json
from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock

import pytest

# Mark all tests in this module for xdist memory safety
pytestmark = [
    pytest.mark.unit,
    pytest.mark.xdist_group(name="playground_session"),
]


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
    redis.close = AsyncMock()
    return redis


@pytest.mark.xdist_group(name="playground_session")
class TestSessionCreation:
    """Tests for session creation functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_create_session_returns_session_object(self, mock_redis: AsyncMock) -> None:
        """Creating a session should return a Session object with ID."""
        from mcp_server_langgraph.playground.session.manager import SessionManager

        manager = SessionManager(redis_client=mock_redis)

        session = await manager.create_session(
            user_id="user-123",
            name="Test Session",
        )

        assert session.id is not None
        assert session.user_id == "user-123"
        assert session.name == "Test Session"
        assert session.created_at is not None

    @pytest.mark.asyncio
    async def test_create_session_generates_unique_ids(self, mock_redis: AsyncMock) -> None:
        """Each session should have a unique ID."""
        from mcp_server_langgraph.playground.session.manager import SessionManager

        manager = SessionManager(redis_client=mock_redis)

        session1 = await manager.create_session(user_id="user-123", name="Session 1")
        session2 = await manager.create_session(user_id="user-123", name="Session 2")

        assert session1.id != session2.id

    @pytest.mark.asyncio
    async def test_create_session_stores_in_redis(self, mock_redis: AsyncMock) -> None:
        """Created session should be stored in Redis."""
        from mcp_server_langgraph.playground.session.manager import SessionManager

        manager = SessionManager(redis_client=mock_redis)

        await manager.create_session(user_id="user-123", name="Test")

        # Verify Redis set was called
        mock_redis.set.assert_called()


@pytest.mark.xdist_group(name="playground_session")
class TestSessionRetrieval:
    """Tests for session retrieval functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_session_by_id(self, mock_redis: AsyncMock) -> None:
        """Should retrieve session by ID."""
        from mcp_server_langgraph.playground.session.manager import SessionManager

        # Set up mock to return session data
        session_data = {
            "id": "session-123",
            "user_id": "user-123",
            "name": "Test Session",
            "created_at": datetime.now(UTC).isoformat(),
            "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
            "message_count": 0,
            "metadata": {},
        }
        mock_redis.get = AsyncMock(return_value=json.dumps(session_data))

        manager = SessionManager(redis_client=mock_redis)

        retrieved = await manager.get_session("session-123")

        assert retrieved is not None
        assert retrieved.id == "session-123"
        assert retrieved.name == "Test Session"

    @pytest.mark.asyncio
    async def test_get_nonexistent_session_returns_none(self, mock_redis: AsyncMock) -> None:
        """Getting non-existent session should return None."""
        from mcp_server_langgraph.playground.session.manager import SessionManager

        mock_redis.get = AsyncMock(return_value=None)
        manager = SessionManager(redis_client=mock_redis)

        result = await manager.get_session("nonexistent-id-999")

        assert result is None

    @pytest.mark.asyncio
    async def test_list_sessions_for_user(self, mock_redis: AsyncMock) -> None:
        """Should list all sessions for a specific user."""
        from mcp_server_langgraph.playground.session.manager import SessionManager

        # Mock session IDs in user's set
        mock_redis.smembers = AsyncMock(return_value={"session-1", "session-2"})

        # Mock session data for each
        session1 = {
            "id": "session-1",
            "user_id": "user-123",
            "name": "Session 1",
            "created_at": datetime.now(UTC).isoformat(),
            "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
            "message_count": 0,
            "metadata": {},
        }
        session2 = {
            "id": "session-2",
            "user_id": "user-123",
            "name": "Session 2",
            "created_at": (datetime.now(UTC) - timedelta(hours=1)).isoformat(),
            "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
            "message_count": 0,
            "metadata": {},
        }

        async def get_session_data(key: str) -> str | None:
            if "session-1" in key:
                return json.dumps(session1)
            elif "session-2" in key:
                return json.dumps(session2)
            return None

        mock_redis.get = AsyncMock(side_effect=get_session_data)

        manager = SessionManager(redis_client=mock_redis)
        sessions = await manager.list_sessions(user_id="user-123")

        assert len(sessions) == 2
        assert all(s.user_id == "user-123" for s in sessions)


@pytest.mark.xdist_group(name="playground_session")
class TestSessionDeletion:
    """Tests for session deletion functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_delete_session(self, mock_redis: AsyncMock) -> None:
        """Should delete session by ID."""
        from mcp_server_langgraph.playground.session.manager import SessionManager

        # Set up mock to return session data for deletion
        session_data = {
            "id": "session-123",
            "user_id": "user-123",
            "name": "Test Session",
            "created_at": datetime.now(UTC).isoformat(),
            "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
            "message_count": 0,
            "metadata": {},
        }
        mock_redis.get = AsyncMock(return_value=json.dumps(session_data))

        manager = SessionManager(redis_client=mock_redis)
        result = await manager.delete_session("session-123")

        assert result is True
        mock_redis.delete.assert_called()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_session_returns_false(self, mock_redis: AsyncMock) -> None:
        """Deleting non-existent session should return False."""
        from mcp_server_langgraph.playground.session.manager import SessionManager

        mock_redis.get = AsyncMock(return_value=None)
        manager = SessionManager(redis_client=mock_redis)

        result = await manager.delete_session("nonexistent-id-999")

        assert result is False


@pytest.mark.xdist_group(name="playground_session")
class TestSessionExpiration:
    """Tests for session expiration functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_session_has_expiration(self, mock_redis: AsyncMock) -> None:
        """Sessions should have an expiration time."""
        from mcp_server_langgraph.playground.session.manager import SessionManager

        manager = SessionManager(
            redis_client=mock_redis,
            session_ttl_seconds=3600,  # 1 hour
        )

        session = await manager.create_session(user_id="user-123", name="Test")

        assert session.expires_at is not None
        assert session.expires_at > datetime.now(UTC)

    @pytest.mark.asyncio
    async def test_session_refresh_extends_expiration(self, mock_redis: AsyncMock) -> None:
        """Refreshing session should extend expiration time."""
        from mcp_server_langgraph.playground.session.manager import SessionManager

        # Set up mock to return session data
        original_expiry = datetime.now(UTC) + timedelta(hours=1)
        session_data = {
            "id": "session-123",
            "user_id": "user-123",
            "name": "Test Session",
            "created_at": datetime.now(UTC).isoformat(),
            "expires_at": original_expiry.isoformat(),
            "message_count": 0,
            "metadata": {},
        }
        mock_redis.get = AsyncMock(return_value=json.dumps(session_data))

        manager = SessionManager(
            redis_client=mock_redis,
            session_ttl_seconds=3600,
        )

        result = await manager.refresh_session("session-123")

        assert result is True
        mock_redis.set.assert_called()


@pytest.mark.xdist_group(name="playground_session")
class TestSessionMessages:
    """Tests for message history within sessions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_add_message_to_session(self, mock_redis: AsyncMock) -> None:
        """Should add messages to session history."""
        from mcp_server_langgraph.playground.session.manager import SessionManager

        # Mock session exists
        session_data = {
            "id": "session-123",
            "user_id": "user-123",
            "name": "Test Session",
            "created_at": datetime.now(UTC).isoformat(),
            "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
            "message_count": 0,
            "metadata": {},
        }
        mock_redis.get = AsyncMock(return_value=json.dumps(session_data))
        mock_redis.llen = AsyncMock(return_value=1)

        manager = SessionManager(redis_client=mock_redis)

        message = await manager.add_message(
            session_id="session-123",
            role="user",
            content="Hello!",
        )

        assert message["role"] == "user"
        assert message["content"] == "Hello!"
        mock_redis.rpush.assert_called()

    @pytest.mark.asyncio
    async def test_get_messages_returns_ordered_history(self, mock_redis: AsyncMock) -> None:
        """Messages should be returned in chronological order."""
        from mcp_server_langgraph.playground.session.manager import SessionManager

        # Mock messages in Redis
        messages = [
            json.dumps({"id": "1", "role": "user", "content": "First", "timestamp": "2024-01-01T00:00:00Z", "metadata": {}}),
            json.dumps(
                {"id": "2", "role": "assistant", "content": "Second", "timestamp": "2024-01-01T00:00:01Z", "metadata": {}}
            ),
            json.dumps({"id": "3", "role": "user", "content": "Third", "timestamp": "2024-01-01T00:00:02Z", "metadata": {}}),
        ]
        mock_redis.lrange = AsyncMock(return_value=messages)

        manager = SessionManager(redis_client=mock_redis)
        result = await manager.get_messages("session-123")

        assert len(result) == 3
        assert result[0]["content"] == "First"
        assert result[1]["content"] == "Second"
        assert result[2]["content"] == "Third"

    @pytest.mark.asyncio
    async def test_message_limit_per_session(self, mock_redis: AsyncMock) -> None:
        """Sessions should enforce maximum message limit."""
        from mcp_server_langgraph.playground.session.manager import SessionManager

        # Mock session exists
        session_data = {
            "id": "session-123",
            "user_id": "user-123",
            "name": "Test Session",
            "created_at": datetime.now(UTC).isoformat(),
            "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
            "message_count": 0,
            "metadata": {},
        }
        mock_redis.get = AsyncMock(return_value=json.dumps(session_data))
        mock_redis.llen = AsyncMock(return_value=5)

        manager = SessionManager(
            redis_client=mock_redis,
            max_messages_per_session=5,
        )

        # Add a message
        await manager.add_message("session-123", "user", "Test message")

        # Verify ltrim was called to enforce limit
        mock_redis.ltrim.assert_called()
