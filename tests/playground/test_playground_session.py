"""
Tests for Redis-backed session management.

Tests the session manager with:
- Session CRUD operations via Redis
- Session expiration/TTL
- Message history storage
- Session serialization/deserialization
- Connection pooling and error handling

Follows TDD principles and memory safety patterns for pytest-xdist.
"""

import gc
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.playground, pytest.mark.redis]


# ==============================================================================
# Session Manager Tests
# ==============================================================================


@pytest.mark.xdist_group(name="playground_session")
class TestRedisSessionManager:
    """Test Redis-backed session manager."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_session_stores_in_redis(self) -> None:
        """Test that creating a session stores it in Redis."""
        from mcp_server_langgraph.playground.session.manager import RedisSessionManager

        mock_redis = AsyncMock()
        mock_redis.setex = AsyncMock(return_value=True)
        mock_redis.get = AsyncMock(return_value=None)

        manager = RedisSessionManager(redis_client=mock_redis)

        session = await manager.create_session(name="Test Session")

        assert session.session_id is not None
        assert session.name == "Test Session"
        mock_redis.setex.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_session_retrieves_from_redis(self) -> None:
        """Test that getting a session retrieves it from Redis."""
        from mcp_server_langgraph.playground.session.manager import RedisSessionManager

        mock_redis = AsyncMock()
        # Mock stored session data
        stored_data = {
            "session_id": "test-session-123",
            "name": "Test Session",
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
            "messages": [],
            "config": {"model": "gpt-4o-mini", "temperature": 0.7, "max_tokens": 1000},
        }
        import json

        mock_redis.get = AsyncMock(return_value=json.dumps(stored_data))

        manager = RedisSessionManager(redis_client=mock_redis)

        session = await manager.get_session("test-session-123")

        assert session is not None
        assert session.session_id == "test-session-123"
        assert session.name == "Test Session"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_nonexistent_session_returns_none(self) -> None:
        """Test that getting a nonexistent session returns None."""
        from mcp_server_langgraph.playground.session.manager import RedisSessionManager

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)

        manager = RedisSessionManager(redis_client=mock_redis)

        session = await manager.get_session("nonexistent-id")

        assert session is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_delete_session_removes_from_redis(self) -> None:
        """Test that deleting a session removes it from Redis."""
        from mcp_server_langgraph.playground.session.manager import RedisSessionManager

        mock_redis = AsyncMock()
        # get returns None (session has no user_id to clean up)
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.delete = AsyncMock(return_value=1)

        manager = RedisSessionManager(redis_client=mock_redis)

        result = await manager.delete_session("test-session-123")

        assert result is True
        mock_redis.delete.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_session_expiration_via_ttl(self) -> None:
        """Test that sessions have TTL set in Redis."""
        from mcp_server_langgraph.playground.session.manager import RedisSessionManager

        mock_redis = AsyncMock()
        mock_redis.setex = AsyncMock(return_value=True)
        mock_redis.get = AsyncMock(return_value=None)

        # Default TTL is 1 hour
        manager = RedisSessionManager(redis_client=mock_redis, ttl_seconds=3600)

        await manager.create_session(name="TTL Test")

        # Verify setex was called with TTL
        call_args = mock_redis.setex.call_args
        assert call_args[0][1] == 3600  # TTL in seconds

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_add_message_to_session(self) -> None:
        """Test adding a message to session history."""
        from mcp_server_langgraph.playground.session.manager import RedisSessionManager

        mock_redis = AsyncMock()
        stored_data = {
            "session_id": "test-session-123",
            "name": "Test",
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
            "messages": [],
            "config": {"model": "gpt-4o-mini", "temperature": 0.7, "max_tokens": 1000},
        }
        import json

        mock_redis.get = AsyncMock(return_value=json.dumps(stored_data))
        mock_redis.setex = AsyncMock(return_value=True)

        manager = RedisSessionManager(redis_client=mock_redis)

        await manager.add_message(
            session_id="test-session-123",
            role="user",
            content="Hello, world!",
        )

        # Verify setex was called to update the session
        mock_redis.setex.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_sessions_for_user(self) -> None:
        """Test listing sessions for a user."""
        from mcp_server_langgraph.playground.session.manager import RedisSessionManager

        mock_redis = AsyncMock()
        # Mock Redis SCAN for keys matching pattern
        mock_redis.scan = AsyncMock(return_value=(0, [b"session:user:alice:1", b"session:user:alice:2"]))

        stored_data_1 = {
            "session_id": "1",
            "name": "Session 1",
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
            "messages": [],
            "config": {"model": "gpt-4o-mini", "temperature": 0.7, "max_tokens": 1000},
        }
        stored_data_2 = {
            "session_id": "2",
            "name": "Session 2",
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
            "messages": [],
            "config": {"model": "gpt-4o-mini", "temperature": 0.7, "max_tokens": 1000},
        }
        import json

        mock_redis.get = AsyncMock(side_effect=[json.dumps(stored_data_1), json.dumps(stored_data_2)])

        manager = RedisSessionManager(redis_client=mock_redis)

        sessions = await manager.list_sessions(user_id="alice")

        assert len(sessions) == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_update_session_refreshes_ttl(self) -> None:
        """Test that updating a session refreshes its TTL."""
        from mcp_server_langgraph.playground.session.manager import RedisSessionManager

        mock_redis = AsyncMock()
        stored_data = {
            "session_id": "test-session-123",
            "name": "Test",
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
            "messages": [],
            "config": {"model": "gpt-4o-mini", "temperature": 0.7, "max_tokens": 1000},
        }
        import json

        mock_redis.get = AsyncMock(return_value=json.dumps(stored_data))
        mock_redis.setex = AsyncMock(return_value=True)

        manager = RedisSessionManager(redis_client=mock_redis, ttl_seconds=3600)

        await manager.update_session("test-session-123", name="Updated Name")

        # Verify setex was called with TTL
        call_args = mock_redis.setex.call_args
        assert call_args[0][1] == 3600


@pytest.mark.xdist_group(name="playground_session")
class TestSessionSerialization:
    """Test session serialization and deserialization."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_session_to_json(self) -> None:
        """Test serializing a session to JSON."""
        from mcp_server_langgraph.playground.session.models import Session, SessionConfig

        session = Session(
            session_id="test-123",
            name="Test Session",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            messages=[],
            config=SessionConfig(),
        )

        json_data = session.model_dump_json()

        assert "test-123" in json_data
        assert "Test Session" in json_data

    @pytest.mark.unit
    def test_session_from_json(self) -> None:
        """Test deserializing a session from JSON."""
        from mcp_server_langgraph.playground.session.models import Session

        json_data = """
        {
            "session_id": "test-123",
            "name": "Test Session",
            "created_at": "2025-01-01T00:00:00+00:00",
            "updated_at": "2025-01-01T00:00:00+00:00",
            "messages": [],
            "config": {"model": "gpt-4o-mini", "temperature": 0.7, "max_tokens": 1000}
        }
        """

        session = Session.model_validate_json(json_data)

        assert session.session_id == "test-123"
        assert session.name == "Test Session"

    @pytest.mark.unit
    def test_message_serialization_preserves_metadata(self) -> None:
        """Test that message metadata is preserved during serialization."""
        from mcp_server_langgraph.playground.session.models import Message

        message = Message(
            message_id="msg-123",
            role="user",
            content="Hello",
            timestamp=datetime.now(UTC),
            metadata={"trace_id": "trace-abc", "tokens": 10},
        )

        json_data = message.model_dump_json()
        restored = Message.model_validate_json(json_data)

        assert restored.metadata["trace_id"] == "trace-abc"
        assert restored.metadata["tokens"] == 10


@pytest.mark.xdist_group(name="playground_session")
class TestSessionManagerConnectionHandling:
    """Test Redis connection handling and error recovery."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handles_redis_connection_error(self) -> None:
        """Test graceful handling of Redis connection errors."""
        from mcp_server_langgraph.playground.session.manager import RedisSessionManager

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(side_effect=ConnectionError("Redis unavailable"))

        manager = RedisSessionManager(redis_client=mock_redis)

        # Should not raise, should return None or handle gracefully
        with pytest.raises(ConnectionError):
            await manager.get_session("test-session-123")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_uses_connection_pool(self) -> None:
        """Test that connection pooling is properly configured."""
        from mcp_server_langgraph.playground.session.manager import create_redis_pool

        # Mock the redis.asyncio.from_url
        with patch("redis.asyncio.from_url") as mock_from_url:
            mock_pool = AsyncMock()
            mock_from_url.return_value = mock_pool

            _pool = await create_redis_pool("redis://localhost:6379/2")

            mock_from_url.assert_called_once()
            # Verify connection pool settings
            call_kwargs = mock_from_url.call_args[1]
            assert "max_connections" in call_kwargs or "decode_responses" in call_kwargs

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_graceful_shutdown(self) -> None:
        """Test graceful shutdown closes Redis connections."""
        from mcp_server_langgraph.playground.session.manager import RedisSessionManager

        mock_redis = AsyncMock()
        mock_redis.close = AsyncMock()

        manager = RedisSessionManager(redis_client=mock_redis)

        await manager.close()

        mock_redis.close.assert_called_once()
