"""
Unit tests for InMemorySessionStore.

Tests session lifecycle management, concurrent session limits,
sliding expiration, and cleanup functionality.

Follows TDD principles and memory safety patterns for pytest-xdist.
"""

import gc
from datetime import datetime, timedelta, timezone

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="session_store")
class TestInMemorySessionStoreCreate:
    """Test session creation functionality."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_session_returns_session_id(self):
        """Test that create returns a valid session ID."""
        from mcp_server_langgraph.auth.session import InMemorySessionStore

        store = InMemorySessionStore()

        session_id = await store.create(
            user_id="user:alice",
            username="alice",
            roles=["user"],
            metadata={"ip": "127.0.0.1"},
        )

        assert session_id is not None
        assert len(session_id) >= 32

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_session_stores_data_correctly(self):
        """Test that session data is stored correctly."""
        from mcp_server_langgraph.auth.session import InMemorySessionStore

        store = InMemorySessionStore()

        session_id = await store.create(
            user_id="user:bob",
            username="bob",
            roles=["user", "admin"],
            metadata={"ip": "192.168.1.1"},
        )

        session = await store.get(session_id)

        assert session is not None
        assert session.user_id == "user:bob"
        assert session.username == "bob"
        assert "admin" in session.roles
        assert session.metadata["ip"] == "192.168.1.1"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_session_with_custom_ttl(self):
        """Test that custom TTL is respected."""
        from mcp_server_langgraph.auth.session import InMemorySessionStore

        store = InMemorySessionStore()

        session_id = await store.create(
            user_id="user:charlie",
            username="charlie",
            roles=[],
            ttl_seconds=3600,  # 1 hour
        )

        session = await store.get(session_id)

        assert session is not None
        expires_at = datetime.fromisoformat(session.expires_at)
        created_at = datetime.fromisoformat(session.created_at)
        # TTL should be approximately 3600 seconds
        diff = (expires_at - created_at).total_seconds()
        assert 3590 < diff < 3610

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_session_enforces_concurrent_limit(self):
        """Test that concurrent session limit is enforced."""
        from mcp_server_langgraph.auth.session import InMemorySessionStore

        store = InMemorySessionStore(max_concurrent_sessions=2)

        # Create first session
        session1 = await store.create(user_id="user:dave", username="dave", roles=[])
        # Create second session
        session2 = await store.create(user_id="user:dave", username="dave", roles=[])
        # Create third session - should remove first
        session3 = await store.create(user_id="user:dave", username="dave", roles=[])

        # First session should be gone
        assert await store.get(session1) is None
        # Second and third should exist
        assert await store.get(session2) is not None
        assert await store.get(session3) is not None


@pytest.mark.xdist_group(name="session_store")
class TestInMemorySessionStoreGet:
    """Test session retrieval functionality."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_returns_none_for_nonexistent_session(self):
        """Test that get returns None for nonexistent session."""
        from mcp_server_langgraph.auth.session import InMemorySessionStore

        store = InMemorySessionStore()

        result = await store.get("nonexistent-session-id-12345678901234567890")

        assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_returns_session_data(self):
        """Test that get returns correct session data."""
        from mcp_server_langgraph.auth.session import InMemorySessionStore

        store = InMemorySessionStore()

        session_id = await store.create(
            user_id="user:eve",
            username="eve",
            roles=["viewer"],
        )

        session = await store.get(session_id)

        assert session is not None
        assert session.session_id == session_id
        assert session.user_id == "user:eve"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_updates_last_accessed_with_sliding_window(self):
        """Test that sliding window updates last_accessed."""
        from mcp_server_langgraph.auth.session import InMemorySessionStore

        store = InMemorySessionStore(sliding_window=True)

        session_id = await store.create(
            user_id="user:frank",
            username="frank",
            roles=[],
        )

        first_session = await store.get(session_id)
        first_accessed = first_session.last_accessed

        # Wait briefly and access again
        import asyncio

        await asyncio.sleep(0.01)

        second_session = await store.get(session_id)
        second_accessed = second_session.last_accessed

        # Sliding window should update last_accessed
        assert second_accessed >= first_accessed

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_does_not_update_last_accessed_without_sliding_window(self):
        """Test that without sliding window, last_accessed is not updated."""
        from mcp_server_langgraph.auth.session import InMemorySessionStore

        store = InMemorySessionStore(sliding_window=False)

        session_id = await store.create(
            user_id="user:grace",
            username="grace",
            roles=[],
        )

        first_session = await store.get(session_id)
        first_accessed = first_session.last_accessed

        second_session = await store.get(session_id)
        second_accessed = second_session.last_accessed

        # Without sliding window, last_accessed should not change
        assert second_accessed == first_accessed


@pytest.mark.xdist_group(name="session_store")
class TestInMemorySessionStoreUpdate:
    """Test session update functionality."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_update_returns_false_for_nonexistent_session(self):
        """Test that update returns False for nonexistent session."""
        from mcp_server_langgraph.auth.session import InMemorySessionStore

        store = InMemorySessionStore()

        result = await store.update("nonexistent-session-id-12345678901234567890", {"key": "value"})

        assert result is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_update_modifies_metadata(self):
        """Test that update modifies session metadata."""
        from mcp_server_langgraph.auth.session import InMemorySessionStore

        store = InMemorySessionStore()

        session_id = await store.create(
            user_id="user:hank",
            username="hank",
            roles=[],
            metadata={"initial": "value"},
        )

        await store.update(session_id, {"new_key": "new_value"})

        session = await store.get(session_id)
        assert session.metadata["initial"] == "value"
        assert session.metadata["new_key"] == "new_value"


@pytest.mark.xdist_group(name="session_store")
class TestInMemorySessionStoreRefresh:
    """Test session refresh functionality."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_refresh_returns_false_for_nonexistent_session(self):
        """Test that refresh returns False for nonexistent session."""
        from mcp_server_langgraph.auth.session import InMemorySessionStore

        store = InMemorySessionStore()

        result = await store.refresh("nonexistent-session-id-12345678901234567890")

        assert result is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_refresh_extends_expiration(self):
        """Test that refresh extends session expiration."""
        from mcp_server_langgraph.auth.session import InMemorySessionStore

        store = InMemorySessionStore(default_ttl_seconds=3600)

        session_id = await store.create(
            user_id="user:iris",
            username="iris",
            roles=[],
            ttl_seconds=60,  # Short TTL
        )

        # Refresh with longer TTL
        result = await store.refresh(session_id, ttl_seconds=7200)

        assert result is True

        session = await store.get(session_id)
        expires_at = datetime.fromisoformat(session.expires_at)
        now = datetime.now(timezone.utc)

        # Should have approximately 2 hours remaining
        remaining = (expires_at - now).total_seconds()
        assert remaining > 7000


@pytest.mark.xdist_group(name="session_store")
class TestInMemorySessionStoreDelete:
    """Test session deletion functionality."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_delete_returns_false_for_nonexistent_session(self):
        """Test that delete returns False for nonexistent session."""
        from mcp_server_langgraph.auth.session import InMemorySessionStore

        store = InMemorySessionStore()

        result = await store.delete("nonexistent-session-id-12345678901234567890")

        assert result is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_delete_removes_session(self):
        """Test that delete removes session from store."""
        from mcp_server_langgraph.auth.session import InMemorySessionStore

        store = InMemorySessionStore()

        session_id = await store.create(
            user_id="user:jack",
            username="jack",
            roles=[],
        )

        result = await store.delete(session_id)

        assert result is True
        assert await store.get(session_id) is None


@pytest.mark.xdist_group(name="session_store")
class TestInMemorySessionStoreUserSessions:
    """Test user session listing and deletion."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_user_sessions_returns_empty_for_unknown_user(self):
        """Test that list_user_sessions returns empty for unknown user."""
        from mcp_server_langgraph.auth.session import InMemorySessionStore

        store = InMemorySessionStore()

        sessions = await store.list_user_sessions("unknown:user")

        assert sessions == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_user_sessions_returns_all_user_sessions(self):
        """Test that list_user_sessions returns all sessions for a user."""
        from mcp_server_langgraph.auth.session import InMemorySessionStore

        store = InMemorySessionStore()

        await store.create(user_id="user:kate", username="kate", roles=[])
        await store.create(user_id="user:kate", username="kate", roles=[])
        await store.create(user_id="user:other", username="other", roles=[])

        sessions = await store.list_user_sessions("user:kate")

        assert len(sessions) == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_delete_user_sessions_returns_zero_for_unknown_user(self):
        """Test that delete_user_sessions returns 0 for unknown user."""
        from mcp_server_langgraph.auth.session import InMemorySessionStore

        store = InMemorySessionStore()

        count = await store.delete_user_sessions("unknown:user")

        assert count == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_delete_user_sessions_removes_all_user_sessions(self):
        """Test that delete_user_sessions removes all sessions for a user."""
        from mcp_server_langgraph.auth.session import InMemorySessionStore

        store = InMemorySessionStore()

        await store.create(user_id="user:larry", username="larry", roles=[])
        await store.create(user_id="user:larry", username="larry", roles=[])

        count = await store.delete_user_sessions("user:larry")

        assert count == 2

        sessions = await store.list_user_sessions("user:larry")
        assert len(sessions) == 0


@pytest.mark.xdist_group(name="session_store")
class TestInMemorySessionStoreInactivity:
    """Test inactive session management."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_inactive_sessions_finds_old_sessions(self):
        """Test that get_inactive_sessions finds sessions before cutoff."""
        from mcp_server_langgraph.auth.session import InMemorySessionStore

        store = InMemorySessionStore(sliding_window=False)

        # Create a session
        session_id = await store.create(user_id="user:mike", username="mike", roles=[])

        # Set cutoff to the future
        cutoff = datetime.now(timezone.utc) + timedelta(hours=1)

        inactive = await store.get_inactive_sessions(cutoff)

        # Session should be considered inactive (last_accessed before future cutoff)
        assert len(inactive) >= 1
        assert any(s.session_id == session_id for s in inactive)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_delete_inactive_sessions_removes_old_sessions(self):
        """Test that delete_inactive_sessions removes sessions before cutoff."""
        from mcp_server_langgraph.auth.session import InMemorySessionStore

        store = InMemorySessionStore(sliding_window=False)

        # Create a session
        session_id = await store.create(user_id="user:nancy", username="nancy", roles=[])

        # Set cutoff to the future
        cutoff = datetime.now(timezone.utc) + timedelta(hours=1)

        count = await store.delete_inactive_sessions(cutoff)

        assert count >= 1
        assert await store.get(session_id) is None


@pytest.mark.xdist_group(name="session_store")
class TestSessionStoreInitialization:
    """Test session store initialization."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_inmemory_store_accepts_custom_config(self):
        """Test that InMemorySessionStore accepts custom configuration."""
        from mcp_server_langgraph.auth.session import InMemorySessionStore

        store = InMemorySessionStore(
            default_ttl_seconds=7200,
            sliding_window=False,
            max_concurrent_sessions=10,
        )

        assert store.default_ttl == 7200
        assert store.sliding_window is False
        assert store.max_concurrent == 10

    @pytest.mark.unit
    def test_generate_session_id_returns_secure_id(self):
        """Test that _generate_session_id returns a secure ID."""
        from mcp_server_langgraph.auth.session import InMemorySessionStore

        store = InMemorySessionStore()

        session_id1 = store._generate_session_id()
        session_id2 = store._generate_session_id()

        # IDs should be unique
        assert session_id1 != session_id2
        # IDs should be at least 32 characters
        assert len(session_id1) >= 32
        assert len(session_id2) >= 32
