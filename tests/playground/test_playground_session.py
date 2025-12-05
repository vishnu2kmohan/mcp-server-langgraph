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
from datetime import datetime, UTC
from unittest.mock import AsyncMock

import pytest

# Mark all tests in this module for xdist memory safety
pytestmark = [
    pytest.mark.unit,
    pytest.mark.playground,
    pytest.mark.xdist_group(name="playground_session"),
]


class TestSessionCreation:
    """Tests for session creation functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_create_session_returns_session_object(self) -> None:
        """Creating a session should return a Session object with ID."""
        from mcp_server_langgraph.playground.session.manager import SessionManager

        manager = SessionManager(redis_url="redis://localhost:6379/2")

        session = await manager.create_session(
            user_id="user-123",
            name="Test Session",
        )

        assert session.id is not None
        assert session.user_id == "user-123"
        assert session.name == "Test Session"
        assert session.created_at is not None

    @pytest.mark.asyncio
    async def test_create_session_generates_unique_ids(self) -> None:
        """Each session should have a unique ID."""
        from mcp_server_langgraph.playground.session.manager import SessionManager

        manager = SessionManager(redis_url="redis://localhost:6379/2")

        session1 = await manager.create_session(user_id="user-123", name="Session 1")
        session2 = await manager.create_session(user_id="user-123", name="Session 2")

        assert session1.id != session2.id

    @pytest.mark.asyncio
    async def test_create_session_stores_in_redis(self) -> None:
        """Created session should be stored in Redis."""
        from mcp_server_langgraph.playground.session.manager import SessionManager

        mock_redis = AsyncMock()
        manager = SessionManager(redis_client=mock_redis)

        await manager.create_session(user_id="user-123", name="Test")

        # Verify Redis set was called
        mock_redis.set.assert_called()


class TestSessionRetrieval:
    """Tests for session retrieval functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_session_by_id(self) -> None:
        """Should retrieve session by ID."""
        from mcp_server_langgraph.playground.session.manager import SessionManager

        manager = SessionManager(redis_url="redis://localhost:6379/2")

        # Create a session
        created = await manager.create_session(user_id="user-123", name="Test")

        # Retrieve it
        retrieved = await manager.get_session(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == created.name

    @pytest.mark.asyncio
    async def test_get_nonexistent_session_returns_none(self) -> None:
        """Getting non-existent session should return None."""
        from mcp_server_langgraph.playground.session.manager import SessionManager

        manager = SessionManager(redis_url="redis://localhost:6379/2")

        result = await manager.get_session("nonexistent-id-999")

        assert result is None

    @pytest.mark.asyncio
    async def test_list_sessions_for_user(self) -> None:
        """Should list all sessions for a specific user."""
        from mcp_server_langgraph.playground.session.manager import SessionManager

        manager = SessionManager(redis_url="redis://localhost:6379/2")

        # Create sessions for different users
        await manager.create_session(user_id="user-123", name="Session 1")
        await manager.create_session(user_id="user-123", name="Session 2")
        await manager.create_session(user_id="user-456", name="Other User Session")

        # List sessions for user-123
        sessions = await manager.list_sessions(user_id="user-123")

        assert len(sessions) >= 2
        assert all(s.user_id == "user-123" for s in sessions)


class TestSessionDeletion:
    """Tests for session deletion functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_delete_session(self) -> None:
        """Should delete session by ID."""
        from mcp_server_langgraph.playground.session.manager import SessionManager

        manager = SessionManager(redis_url="redis://localhost:6379/2")

        # Create and then delete
        session = await manager.create_session(user_id="user-123", name="Test")
        await manager.delete_session(session.id)

        # Verify it's gone
        result = await manager.get_session(session.id)
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_session_is_noop(self) -> None:
        """Deleting non-existent session should not raise."""
        from mcp_server_langgraph.playground.session.manager import SessionManager

        manager = SessionManager(redis_url="redis://localhost:6379/2")

        # Should not raise
        await manager.delete_session("nonexistent-id-999")


class TestSessionExpiration:
    """Tests for session expiration functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_session_has_expiration(self) -> None:
        """Sessions should have an expiration time."""
        from mcp_server_langgraph.playground.session.manager import SessionManager

        manager = SessionManager(
            redis_url="redis://localhost:6379/2",
            session_ttl_seconds=3600,  # 1 hour
        )

        session = await manager.create_session(user_id="user-123", name="Test")

        assert session.expires_at is not None
        assert session.expires_at > datetime.now(UTC)

    @pytest.mark.asyncio
    async def test_session_refresh_extends_expiration(self) -> None:
        """Refreshing session should extend expiration time."""
        from mcp_server_langgraph.playground.session.manager import SessionManager

        manager = SessionManager(
            redis_url="redis://localhost:6379/2",
            session_ttl_seconds=3600,
        )

        session = await manager.create_session(user_id="user-123", name="Test")
        original_expiry = session.expires_at

        # Refresh the session
        await manager.refresh_session(session.id)
        refreshed = await manager.get_session(session.id)

        assert refreshed.expires_at >= original_expiry


class TestSessionMessages:
    """Tests for message history within sessions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_add_message_to_session(self) -> None:
        """Should add messages to session history."""
        from mcp_server_langgraph.playground.session.manager import SessionManager

        manager = SessionManager(redis_url="redis://localhost:6379/2")

        session = await manager.create_session(user_id="user-123", name="Test")

        await manager.add_message(
            session_id=session.id,
            role="user",
            content="Hello!",
        )

        messages = await manager.get_messages(session.id)
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hello!"

    @pytest.mark.asyncio
    async def test_get_messages_returns_ordered_history(self) -> None:
        """Messages should be returned in chronological order."""
        from mcp_server_langgraph.playground.session.manager import SessionManager

        manager = SessionManager(redis_url="redis://localhost:6379/2")

        session = await manager.create_session(user_id="user-123", name="Test")

        await manager.add_message(session.id, "user", "First")
        await manager.add_message(session.id, "assistant", "Second")
        await manager.add_message(session.id, "user", "Third")

        messages = await manager.get_messages(session.id)

        assert len(messages) == 3
        assert messages[0]["content"] == "First"
        assert messages[1]["content"] == "Second"
        assert messages[2]["content"] == "Third"

    @pytest.mark.asyncio
    async def test_message_limit_per_session(self) -> None:
        """Sessions should enforce maximum message limit."""
        from mcp_server_langgraph.playground.session.manager import SessionManager

        manager = SessionManager(
            redis_url="redis://localhost:6379/2",
            max_messages_per_session=5,
        )

        session = await manager.create_session(user_id="user-123", name="Test")

        # Add more than limit
        for i in range(10):
            await manager.add_message(session.id, "user", f"Message {i}")

        messages = await manager.get_messages(session.id)

        # Should only keep last N messages
        assert len(messages) <= 5
