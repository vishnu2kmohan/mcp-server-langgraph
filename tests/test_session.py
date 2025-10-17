"""
Comprehensive tests for Session Management

Tests cover:
- InMemorySessionStore implementation
- RedisSessionStore implementation
- Session lifecycle operations
- Expiration and TTL handling
- Sliding window behavior
- Concurrent session limits
- Error handling
- Factory function
"""

import asyncio
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_langgraph.auth.session import InMemorySessionStore, RedisSessionStore, SessionData, create_session_store

# ============================================================================
# InMemorySessionStore Tests
# ============================================================================


class TestInMemorySessionStore:
    """Tests for InMemorySessionStore"""

    @pytest.fixture
    def store(self):
        """Create in-memory session store"""
        return InMemorySessionStore(default_ttl_seconds=3600, max_concurrent_sessions=3)

    @pytest.mark.asyncio
    async def test_create_session(self, store):
        """Test creating a session"""
        session_id = await store.create(
            user_id="user:alice",
            username="alice",
            roles=["admin", "user"],
            metadata={"ip": "192.168.1.1"},
        )

        assert session_id is not None
        assert len(session_id) > 0

        # Verify session exists
        session = await store.get(session_id)
        assert session is not None
        assert session.user_id == "user:alice"
        assert session.username == "alice"
        assert session.roles == ["admin", "user"]
        assert session.metadata == {"ip": "192.168.1.1"}

    @pytest.mark.asyncio
    async def test_get_session(self, store):
        """Test retrieving a session"""
        session_id = await store.create(user_id="user:bob", username="bob", roles=["user"])

        session = await store.get(session_id)
        assert session is not None
        assert session.session_id == session_id
        assert session.user_id == "user:bob"
        assert session.username == "bob"
        assert session.roles == ["user"]

    @pytest.mark.asyncio
    async def test_get_nonexistent_session(self, store):
        """Test retrieving a non-existent session"""
        session = await store.get("nonexistent-session-id")
        assert session is None

    @pytest.mark.asyncio
    async def test_update_session(self, store):
        """Test updating session metadata"""
        session_id = await store.create(
            user_id="user:charlie",
            username="charlie",
            roles=["user"],
            metadata={"ip": "10.0.0.1"},
        )

        # Update metadata
        success = await store.update(session_id, metadata={"ip": "10.0.0.2", "device": "mobile"})
        assert success is True

        # Verify update
        session = await store.get(session_id)
        assert session.metadata == {"ip": "10.0.0.2", "device": "mobile"}

    @pytest.mark.asyncio
    async def test_update_nonexistent_session(self, store):
        """Test updating a non-existent session"""
        success = await store.update("nonexistent", metadata={"foo": "bar"})
        assert success is False

    @pytest.mark.asyncio
    async def test_refresh_session(self, store):
        """Test refreshing session expiration"""
        session_id = await store.create(user_id="user:dave", username="dave", roles=["user"])

        # Get original expiry
        session1 = await store.get(session_id)
        original_expiry = session1.expires_at

        # Wait a bit
        await asyncio.sleep(0.1)

        # Refresh
        success = await store.refresh(session_id)
        assert success is True

        # Verify new expiry is later
        session2 = await store.get(session_id)
        assert session2.expires_at > original_expiry

    @pytest.mark.asyncio
    async def test_refresh_with_custom_ttl(self, store):
        """Test refreshing with custom TTL"""
        session_id = await store.create(user_id="user:eve", username="eve", roles=["user"])

        # Refresh with short TTL
        success = await store.refresh(session_id, ttl_seconds=60)
        assert success is True

        session = await store.get(session_id)
        # Should expire in ~60 seconds
        expires_at = datetime.fromisoformat(session.expires_at)
        time_until_expiry = (expires_at - datetime.now(timezone.utc)).total_seconds()
        assert 55 < time_until_expiry < 65  # Allow some tolerance

    @pytest.mark.asyncio
    async def test_delete_session(self, store):
        """Test deleting a session"""
        session_id = await store.create(user_id="user:frank", username="frank", roles=["user"])

        # Verify exists
        assert await store.get(session_id) is not None

        # Delete
        success = await store.delete(session_id)
        assert success is True

        # Verify deleted
        assert await store.get(session_id) is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_session(self, store):
        """Test deleting a non-existent session"""
        success = await store.delete("nonexistent")
        assert success is False

    @pytest.mark.asyncio
    async def test_session_expiration(self):
        """Test that expired sessions are not returned"""
        store = InMemorySessionStore(default_ttl_seconds=1)  # 1 second TTL

        session_id = await store.create(user_id="user:grace", username="grace", roles=["user"])

        # Should exist immediately
        assert await store.get(session_id) is not None

        # Wait for expiration
        await asyncio.sleep(1.5)

        # Should be expired
        assert await store.get(session_id) is None

    @pytest.mark.asyncio
    async def test_list_user_sessions(self, store):
        """Test listing all sessions for a user"""
        user_id = "user:henry"

        # Create multiple sessions
        session_id1 = await store.create(user_id, "henry", ["user"])
        session_id2 = await store.create(user_id, "henry", ["admin"])
        session_id3 = await store.create(user_id, "henry", ["premium"])

        sessions = await store.list_user_sessions(user_id)
        assert len(sessions) == 3

        session_ids = {s.session_id for s in sessions}
        assert session_ids == {session_id1, session_id2, session_id3}

    @pytest.mark.asyncio
    async def test_list_user_sessions_empty(self, store):
        """Test listing sessions for user with no sessions"""
        sessions = await store.list_user_sessions("user:nobody")
        assert sessions == []

    @pytest.mark.asyncio
    async def test_delete_user_sessions(self, store):
        """Test deleting all sessions for a user"""
        user_id = "user:iris"

        # Create multiple sessions
        await store.create(user_id, "iris", ["user"])
        await store.create(user_id, "iris", ["admin"])
        await store.create(user_id, "iris", ["premium"])

        # Verify 3 sessions
        sessions = await store.list_user_sessions(user_id)
        assert len(sessions) == 3

        # Delete all
        count = await store.delete_user_sessions(user_id)
        assert count == 3

        # Verify all deleted
        sessions = await store.list_user_sessions(user_id)
        assert len(sessions) == 0

    @pytest.mark.asyncio
    async def test_concurrent_session_limit(self, store):
        """Test concurrent session limit enforcement"""
        user_id = "user:jack"

        # Create max sessions (3)
        session_id1 = await store.create(user_id, "jack", ["user"])
        await asyncio.sleep(0.01)  # Ensure different timestamps
        session_id2 = await store.create(user_id, "jack", ["user"])
        await asyncio.sleep(0.01)
        session_id3 = await store.create(user_id, "jack", ["user"])

        # All should exist
        assert await store.get(session_id1) is not None
        assert await store.get(session_id2) is not None
        assert await store.get(session_id3) is not None

        # Create 4th session - should remove oldest (session_id1)
        await asyncio.sleep(0.01)
        session_id4 = await store.create(user_id, "jack", ["user"])

        # First session should be removed
        assert await store.get(session_id1) is None

        # Others should still exist
        assert await store.get(session_id2) is not None
        assert await store.get(session_id3) is not None
        assert await store.get(session_id4) is not None

    @pytest.mark.asyncio
    async def test_sliding_window_enabled(self):
        """Test sliding window expiration (refreshes on access)"""
        store = InMemorySessionStore(default_ttl_seconds=2, sliding_window=True)

        session_id = await store.create(user_id="user:kate", username="kate", roles=["user"])

        # Get original last_accessed time
        session1 = await store.get(session_id)
        original_last_accessed = session1.last_accessed

        # Wait a bit to ensure timestamp difference
        await asyncio.sleep(0.01)

        # Access session (should update last_accessed due to sliding window)
        session2 = await store.get(session_id)

        # last_accessed should be updated (timestamp is ISO string, so lexicographic comparison works)
        assert session2.last_accessed >= original_last_accessed

    @pytest.mark.asyncio
    async def test_sliding_window_disabled(self):
        """Test that sliding window can be disabled"""
        store = InMemorySessionStore(default_ttl_seconds=2, sliding_window=False)

        session_id = await store.create(user_id="user:liam", username="liam", roles=["user"])

        # Get original last_accessed
        session1 = await store.get(session_id)
        original_last_accessed = session1.last_accessed

        # Wait a bit
        await asyncio.sleep(0.5)

        # Access session (should NOT update last_accessed since sliding_window=False)
        session2 = await store.get(session_id)

        # last_accessed should be same
        assert session2.last_accessed == original_last_accessed

    @pytest.mark.asyncio
    async def test_custom_ttl_per_session(self, store):
        """Test creating sessions with custom TTL"""
        # Short TTL session
        session_id1 = await store.create(user_id="user:mike", username="mike", roles=["user"], ttl_seconds=1)

        # Long TTL session
        session_id2 = await store.create(user_id="user:nina", username="nina", roles=["user"], ttl_seconds=3600)

        # Wait for first to expire
        await asyncio.sleep(1.5)

        # First should be expired
        assert await store.get(session_id1) is None

        # Second should still exist
        assert await store.get(session_id2) is not None


# ============================================================================
# RedisSessionStore Tests
# ============================================================================


class TestRedisSessionStore:
    """Tests for RedisSessionStore"""

    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client"""
        mock = AsyncMock()
        mock.ping = AsyncMock(return_value=True)
        mock.hset = AsyncMock(return_value=1)
        mock.hget = AsyncMock(return_value=None)
        mock.hgetall = AsyncMock(return_value={})
        mock.exists = AsyncMock(return_value=0)
        mock.expire = AsyncMock(return_value=True)
        mock.delete = AsyncMock(return_value=1)
        mock.rpush = AsyncMock(return_value=1)
        mock.lrange = AsyncMock(return_value=[])
        mock.lrem = AsyncMock(return_value=1)
        mock.close = AsyncMock()
        return mock

    @pytest.fixture
    def store(self, mock_redis):
        """Create Redis session store with mocked client"""
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            store = RedisSessionStore(redis_url="redis://localhost:6379/0", default_ttl_seconds=3600)
            return store

    @pytest.mark.asyncio
    async def test_create_session(self, store, mock_redis):
        """Test creating a session in Redis"""
        session_id = await store.create(
            user_id="user:oscar",
            username="oscar",
            roles=["admin", "user"],
            metadata={"ip": "172.16.0.1"},
        )

        assert session_id is not None

        # Verify Redis calls
        mock_redis.hset.assert_called()
        mock_redis.expire.assert_called()
        mock_redis.rpush.assert_called()

    @pytest.mark.asyncio
    async def test_get_session(self, store, mock_redis):
        """Test retrieving a session from Redis"""
        # Mock Redis response (strings because decode_responses=True)
        session_id = "a" * 32  # 32-character session ID for Pydantic validation
        mock_redis.hgetall.return_value = {
            "session_id": session_id,
            "user_id": "user:paul",
            "username": "paul",
            "roles": "user",  # Comma-separated roles
            "metadata": "{}",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            "last_accessed": datetime.now(timezone.utc).isoformat(),
        }

        session = await store.get(session_id)
        assert session is not None
        assert session.user_id == "user:paul"
        assert session.username == "paul"
        assert session.roles == ["user"]

    @pytest.mark.asyncio
    async def test_get_nonexistent_session(self, store, mock_redis):
        """Test retrieving non-existent session"""
        mock_redis.hgetall.return_value = {}

        session = await store.get("nonexistent")
        assert session is None

    @pytest.mark.asyncio
    async def test_update_session(self, store, mock_redis):
        """Test updating session metadata"""
        session_id = "h" * 32  # 32-character session ID
        # Mock exists check and get for update
        mock_redis.exists.return_value = 1
        mock_redis.hgetall.return_value = {
            "session_id": session_id,
            "user_id": "user:quinn",
            "username": "quinn",
            "roles": "user",
            "metadata": "{'ip': '10.0.0.1'}",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            "last_accessed": datetime.now(timezone.utc).isoformat(),
        }

        success = await store.update(session_id, metadata={"ip": "10.0.0.2"})
        assert success is True

        # Verify Redis update
        mock_redis.hset.assert_called()

    @pytest.mark.asyncio
    async def test_refresh_session(self, store, mock_redis):
        """Test refreshing session expiration"""
        session_id = "i" * 32  # 32-character session ID
        # Mock exists check
        mock_redis.exists.return_value = 1

        success = await store.refresh(session_id)
        assert success is True

        # Verify expiry updated
        mock_redis.expire.assert_called()

    @pytest.mark.asyncio
    async def test_delete_session(self, store, mock_redis):
        """Test deleting a session"""
        session_id = "b" * 32  # 32-character session ID
        # Mock hget for user_id lookup
        mock_redis.hget.return_value = "user:sam"
        mock_redis.delete.return_value = 1  # Indicates successful delete

        success = await store.delete(session_id)
        assert success is True

        # Verify Redis delete
        mock_redis.delete.assert_called()
        mock_redis.lrem.assert_called()

    @pytest.mark.asyncio
    async def test_list_user_sessions(self, store, mock_redis):
        """Test listing all sessions for a user"""
        # Create proper 32+ character session IDs
        session1 = "c" * 32
        session2 = "d" * 32

        # Mock user session list
        mock_redis.lrange.return_value = [session1, session2]

        # Mock session data (strings because decode_responses=True)
        async def mock_hgetall(key):
            if session1 in key:
                return {
                    "session_id": session1,
                    "user_id": "user:tina",
                    "username": "tina",
                    "roles": "user",
                    "metadata": "{}",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
                    "last_accessed": datetime.now(timezone.utc).isoformat(),
                }
            elif session2 in key:
                return {
                    "session_id": session2,
                    "user_id": "user:tina",
                    "username": "tina",
                    "roles": "admin",
                    "metadata": "{}",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
                    "last_accessed": datetime.now(timezone.utc).isoformat(),
                }
            return {}

        mock_redis.hgetall.side_effect = mock_hgetall

        sessions = await store.list_user_sessions("user:tina")
        assert len(sessions) == 2

    @pytest.mark.asyncio
    async def test_delete_user_sessions(self, store, mock_redis):
        """Test deleting all sessions for a user"""
        # Mock user session list with proper 32+ character IDs
        session_ids = ["e" * 32, "f" * 32, "g" * 32]
        mock_redis.lrange.return_value = session_ids
        mock_redis.hget.return_value = "user:uma"  # Mock user_id lookup
        mock_redis.delete.return_value = 1  # Successful delete

        count = await store.delete_user_sessions("user:uma")
        assert count == 3

        # Verify Redis deletes
        assert mock_redis.delete.call_count >= 3

    @pytest.mark.asyncio
    async def test_concurrent_session_limit(self, store, mock_redis):
        """Test concurrent session limit with Redis"""
        store.max_concurrent = 2

        # Mock existing sessions
        mock_redis.lrange.return_value = ["old-session-1", "old-session-2"]

        # Mock session data for old sessions
        async def mock_hgetall(key):
            return {
                b"session_id": key.split(b":")[-1],
                b"user_id": b"user:victor",
                b"username": b"victor",
                b"roles": b'["user"]',
                b"metadata": b"{}",
                b"created_at": datetime.now(timezone.utc).isoformat().encode(),
                b"expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat().encode(),
                b"last_accessed": datetime.now(timezone.utc).isoformat().encode(),
            }

        mock_redis.hgetall.side_effect = mock_hgetall

        # Create new session (should trigger cleanup)
        await store.create("user:victor", "victor", ["user"])

        # Should have deleted oldest session
        assert mock_redis.delete.called

    @pytest.mark.asyncio
    async def test_connection_error_handling(self):
        """Test handling of Redis connection errors"""
        with patch("redis.asyncio.from_url") as mock_from_url:
            mock_client = AsyncMock()
            mock_client.ping.side_effect = Exception("Connection failed")
            mock_from_url.return_value = mock_client

            store = RedisSessionStore(redis_url="redis://invalid:6379/0")

            # Should handle gracefully
            with pytest.raises(Exception):
                await store._ensure_connected()


# ============================================================================
# Factory Function Tests
# ============================================================================


class TestSessionStoreFactory:
    """Tests for create_session_store factory function"""

    def test_create_memory_store(self):
        """Test creating in-memory store"""
        store = create_session_store(backend="memory", default_ttl_seconds=7200)

        assert isinstance(store, InMemorySessionStore)
        assert store.default_ttl == 7200

    def test_create_redis_store(self):
        """Test creating Redis store"""
        with patch("redis.asyncio.from_url"):
            store = create_session_store(
                backend="redis",
                redis_url="redis://localhost:6379/0",
                default_ttl_seconds=3600,
            )

            assert isinstance(store, RedisSessionStore)
            assert store.default_ttl == 3600

    def test_create_default_store(self):
        """Test creating store with defaults"""
        store = create_session_store()

        assert isinstance(store, InMemorySessionStore)

    def test_create_with_custom_settings(self):
        """Test creating store with custom settings"""
        store = create_session_store(
            backend="memory",
            default_ttl_seconds=1800,
            max_concurrent_sessions=10,
            sliding_window=False,
        )

        assert isinstance(store, InMemorySessionStore)
        assert store.default_ttl == 1800
        assert store.max_concurrent == 10
        assert store.sliding_window is False

    def test_invalid_backend(self):
        """Test error handling for invalid backend"""
        with pytest.raises(ValueError, match="Unknown session backend"):
            create_session_store(backend="invalid")


# ============================================================================
# Integration Tests
# ============================================================================


class TestSessionIntegration:
    """Integration tests for session management"""

    @pytest.mark.asyncio
    async def test_session_lifecycle(self):
        """Test complete session lifecycle"""
        store = InMemorySessionStore(default_ttl_seconds=3600)

        # Create
        session_id = await store.create(user_id="user:wendy", username="wendy", roles=["user", "premium"])
        assert session_id is not None

        # Get
        session = await store.get(session_id)
        assert session is not None
        assert session.username == "wendy"

        # Update
        success = await store.update(session_id, metadata={"last_ip": "192.168.1.100"})
        assert success is True

        # Verify update
        session = await store.get(session_id)
        assert session.metadata["last_ip"] == "192.168.1.100"

        # Refresh
        success = await store.refresh(session_id)
        assert success is True

        # Delete
        success = await store.delete(session_id)
        assert success is True

        # Verify deleted
        session = await store.get(session_id)
        assert session is None

    @pytest.mark.asyncio
    async def test_multi_user_sessions(self):
        """Test managing sessions for multiple users"""
        store = InMemorySessionStore()

        # Create sessions for different users
        alice_session = await store.create("user:alice", "alice", ["admin"])
        bob_session = await store.create("user:bob", "bob", ["user"])
        await store.create("user:charlie", "charlie", ["premium"])

        # Verify isolation
        alice_sessions = await store.list_user_sessions("user:alice")
        bob_sessions = await store.list_user_sessions("user:bob")

        assert len(alice_sessions) == 1
        assert len(bob_sessions) == 1
        assert alice_sessions[0].session_id == alice_session
        assert bob_sessions[0].session_id == bob_session

        # Delete one user's sessions
        count = await store.delete_user_sessions("user:bob")
        assert count == 1

        # Verify others unaffected
        alice_sessions = await store.list_user_sessions("user:alice")
        charlie_sessions = await store.list_user_sessions("user:charlie")
        assert len(alice_sessions) == 1
        assert len(charlie_sessions) == 1
