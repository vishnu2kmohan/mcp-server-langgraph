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

import gc
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from tests.helpers.async_mock_helpers import configured_async_mock

try:
    from freezegun import freeze_time
except ImportError:
    pytest.skip("freezegun not installed (optional test dependency)", allow_module_level=True)
from mcp_server_langgraph.auth.session import InMemorySessionStore, RedisSessionStore, create_session_store
from tests.conftest import get_user_id


@pytest.mark.xdist_group(name="session_tests")
class TestInMemorySessionStore:
    """Tests for InMemorySessionStore"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def store(self):
        """Create in-memory session store"""
        return InMemorySessionStore(default_ttl_seconds=3600, max_concurrent_sessions=3)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_session(self, store):
        """Test creating a session"""
        session_id = await store.create(
            user_id=get_user_id("alice"), username="alice", roles=["admin", "user"], metadata={"ip": "192.168.1.1"}
        )
        assert session_id is not None
        assert len(session_id) > 0
        session = await store.get(session_id)
        assert session is not None
        assert session.user_id == get_user_id("alice")
        assert session.username == "alice"
        assert session.roles == ["admin", "user"]
        assert session.metadata == {"ip": "192.168.1.1"}

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_session(self, store):
        """Test retrieving a session"""
        session_id = await store.create(user_id=get_user_id("bob"), username="bob", roles=["user"])
        session = await store.get(session_id)
        assert session is not None
        assert session.session_id == session_id
        assert session.user_id == get_user_id("bob")
        assert session.username == "bob"
        assert session.roles == ["user"]

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_nonexistent_session(self, store):
        """Test retrieving a non-existent session"""
        session = await store.get("nonexistent-session-id")
        assert session is None

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_update_session(self, store):
        """Test updating session metadata"""
        session_id = await store.create(
            user_id=get_user_id("charlie"), username="charlie", roles=["user"], metadata={"ip": "10.0.0.1"}
        )
        success = await store.update(session_id, metadata={"ip": "10.0.0.2", "device": "mobile"})
        assert success is True
        session = await store.get(session_id)
        assert session.metadata == {"ip": "10.0.0.2", "device": "mobile"}

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_update_nonexistent_session(self, store):
        """Test updating a non-existent session"""
        success = await store.update("nonexistent", metadata={"foo": "bar"})
        assert success is False

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_refresh_session(self, store):
        """Test refreshing session expiration"""
        with freeze_time("2024-01-01 12:00:00") as frozen_time:
            session_id = await store.create(user_id=get_user_id("dave"), username="dave", roles=["user"])
            session1 = await store.get(session_id)
            original_expiry = session1.expires_at
            frozen_time.tick(delta=timedelta(seconds=1))
            success = await store.refresh(session_id)
            assert success is True
            session2 = await store.get(session_id)
            assert session2.expires_at > original_expiry

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_refresh_with_custom_ttl(self, store):
        """Test refreshing with custom TTL"""
        session_id = await store.create(user_id=get_user_id("eve"), username="eve", roles=["user"])
        success = await store.refresh(session_id, ttl_seconds=60)
        assert success is True
        session = await store.get(session_id)
        expires_at = datetime.fromisoformat(session.expires_at)
        time_until_expiry = (expires_at - datetime.now(timezone.utc)).total_seconds()
        assert 55 < time_until_expiry < 65

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_delete_session(self, store):
        """Test deleting a session"""
        session_id = await store.create(user_id=get_user_id("frank"), username="frank", roles=["user"])
        assert await store.get(session_id) is not None
        success = await store.delete(session_id)
        assert success is True
        assert await store.get(session_id) is None

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_delete_nonexistent_session(self, store):
        """Test deleting a non-existent session"""
        success = await store.delete("nonexistent")
        assert success is False

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_session_expiration(self):
        """Test that expired sessions are not returned"""
        with freeze_time("2024-01-01 12:00:00") as frozen_time:
            store = InMemorySessionStore(default_ttl_seconds=1)
            session_id = await store.create(user_id=get_user_id("grace"), username="grace", roles=["user"])
            assert await store.get(session_id) is not None
            frozen_time.tick(delta=timedelta(seconds=1.05))
            assert await store.get(session_id) is None

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_list_user_sessions(self, store):
        """Test listing all sessions for a user"""
        user_id = get_user_id("henry")
        session_id1 = await store.create(user_id, "henry", ["user"])
        session_id2 = await store.create(user_id, "henry", ["admin"])
        session_id3 = await store.create(user_id, "henry", ["premium"])
        sessions = await store.list_user_sessions(user_id)
        assert len(sessions) == 3
        session_ids = {s.session_id for s in sessions}
        assert session_ids == {session_id1, session_id2, session_id3}

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_list_user_sessions_empty(self, store):
        """Test listing sessions for user with no sessions"""
        sessions = await store.list_user_sessions(get_user_id("nobody"))
        assert sessions == []

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_delete_user_sessions(self, store):
        """Test deleting all sessions for a user"""
        user_id = get_user_id("iris")
        await store.create(user_id, "iris", ["user"])
        await store.create(user_id, "iris", ["admin"])
        await store.create(user_id, "iris", ["premium"])
        sessions = await store.list_user_sessions(user_id)
        assert len(sessions) == 3
        count = await store.delete_user_sessions(user_id)
        assert count == 3
        sessions = await store.list_user_sessions(user_id)
        assert len(sessions) == 0

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_concurrent_session_limit(self, store):
        """Test concurrent session limit enforcement"""
        with freeze_time("2024-01-01 12:00:00") as frozen_time:
            user_id = get_user_id("jack")
            session_id1 = await store.create(user_id, "jack", ["user"])
            frozen_time.tick(delta=timedelta(milliseconds=10))
            session_id2 = await store.create(user_id, "jack", ["user"])
            frozen_time.tick(delta=timedelta(milliseconds=10))
            session_id3 = await store.create(user_id, "jack", ["user"])
            assert await store.get(session_id1) is not None
            assert await store.get(session_id2) is not None
            assert await store.get(session_id3) is not None
            frozen_time.tick(delta=timedelta(milliseconds=10))
            session_id4 = await store.create(user_id, "jack", ["user"])
            assert await store.get(session_id1) is None
            assert await store.get(session_id2) is not None
            assert await store.get(session_id3) is not None
            assert await store.get(session_id4) is not None

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_sliding_window_enabled(self):
        """Test sliding window expiration (refreshes on access)"""
        with freeze_time("2024-01-01 12:00:00") as frozen_time:
            store = InMemorySessionStore(default_ttl_seconds=2, sliding_window=True)
            session_id = await store.create(user_id=get_user_id("kate"), username="kate", roles=["user"])
            session1 = await store.get(session_id)
            original_last_accessed = session1.last_accessed
            frozen_time.tick(delta=timedelta(milliseconds=10))
            session2 = await store.get(session_id)
            assert session2.last_accessed >= original_last_accessed

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_sliding_window_disabled(self):
        """Test that sliding window can be disabled"""
        with freeze_time("2024-01-01 12:00:00") as frozen_time:
            store = InMemorySessionStore(default_ttl_seconds=2, sliding_window=False)
            session_id = await store.create(user_id=get_user_id("liam"), username="liam", roles=["user"])
            session1 = await store.get(session_id)
            original_last_accessed = session1.last_accessed
            frozen_time.tick(delta=timedelta(milliseconds=500))
            session2 = await store.get(session_id)
            assert session2.last_accessed == original_last_accessed

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_custom_ttl_per_session(self, store):
        """Test creating sessions with custom TTL"""
        with freeze_time("2024-01-01 12:00:00") as frozen_time:
            session_id1 = await store.create(user_id=get_user_id("mike"), username="mike", roles=["user"], ttl_seconds=1)
            session_id2 = await store.create(user_id=get_user_id("nina"), username="nina", roles=["user"], ttl_seconds=3600)
            frozen_time.tick(delta=timedelta(seconds=1.05))
            assert await store.get(session_id1) is None
            assert await store.get(session_id2) is not None


@pytest.mark.xdist_group(name="session_tests")
class TestRedisSessionStore:
    """Tests for RedisSessionStore"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client"""
        mock = configured_async_mock(return_value=None)
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
        mock.close = configured_async_mock(return_value=None)
        return mock

    @pytest.fixture
    def store(self, mock_redis):
        """Create Redis session store with mocked client"""
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            store = RedisSessionStore(redis_url="redis://localhost:6379/0", default_ttl_seconds=3600)
            return store

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_session(self, store, mock_redis):
        """Test creating a session in Redis"""
        session_id = await store.create(
            user_id=get_user_id("oscar"), username="oscar", roles=["admin", "user"], metadata={"ip": "172.16.0.1"}
        )
        assert session_id is not None
        mock_redis.hset.assert_called()
        mock_redis.expire.assert_called()
        mock_redis.rpush.assert_called()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_session(self, store, mock_redis):
        """Test retrieving a session from Redis"""
        session_id = "a" * 32
        mock_redis.hgetall.return_value = {
            "session_id": session_id,
            "user_id": get_user_id("paul"),
            "username": "paul",
            "roles": "user",
            "metadata": "{}",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            "last_accessed": datetime.now(timezone.utc).isoformat(),
        }
        session = await store.get(session_id)
        assert session is not None
        assert session.user_id == get_user_id("paul")
        assert session.username == "paul"
        assert session.roles == ["user"]

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_nonexistent_session(self, store, mock_redis):
        """Test retrieving non-existent session"""
        mock_redis.hgetall.return_value = {}
        session = await store.get("nonexistent")
        assert session is None

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_update_session(self, store, mock_redis):
        """Test updating session metadata"""
        session_id = "h" * 32
        mock_redis.exists.return_value = 1
        mock_redis.hgetall.return_value = {
            "session_id": session_id,
            "user_id": get_user_id("quinn"),
            "username": "quinn",
            "roles": "user",
            "metadata": "{'ip': '10.0.0.1'}",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            "last_accessed": datetime.now(timezone.utc).isoformat(),
        }
        success = await store.update(session_id, metadata={"ip": "10.0.0.2"})
        assert success is True
        mock_redis.hset.assert_called()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_refresh_session(self, store, mock_redis):
        """Test refreshing session expiration"""
        session_id = "i" * 32
        mock_redis.exists.return_value = 1
        success = await store.refresh(session_id)
        assert success is True
        mock_redis.expire.assert_called()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_delete_session(self, store, mock_redis):
        """Test deleting a session"""
        session_id = "b" * 32
        mock_redis.hget.return_value = get_user_id("sam")
        mock_redis.delete.return_value = 1
        success = await store.delete(session_id)
        assert success is True
        mock_redis.delete.assert_called()
        mock_redis.lrem.assert_called()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_list_user_sessions(self, store, mock_redis):
        """Test listing all sessions for a user"""
        session1 = "c" * 32
        session2 = "d" * 32
        mock_redis.lrange.return_value = [session1, session2]

        async def mock_hgetall(key):
            if session1 in key:
                return {
                    "session_id": session1,
                    "user_id": get_user_id("tina"),
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
                    "user_id": get_user_id("tina"),
                    "username": "tina",
                    "roles": "admin",
                    "metadata": "{}",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
                    "last_accessed": datetime.now(timezone.utc).isoformat(),
                }
            return {}

        mock_redis.hgetall.side_effect = mock_hgetall
        sessions = await store.list_user_sessions(get_user_id("tina"))
        assert len(sessions) == 2

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_delete_user_sessions(self, store, mock_redis):
        """Test deleting all sessions for a user"""
        session_ids = ["e" * 32, "f" * 32, "g" * 32]
        mock_redis.lrange.return_value = session_ids
        mock_redis.hget.return_value = get_user_id("uma")
        mock_redis.delete.return_value = 1
        count = await store.delete_user_sessions(get_user_id("uma"))
        assert count == 3
        assert mock_redis.delete.call_count >= 3

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_concurrent_session_limit(self, store, mock_redis):
        """Test concurrent session limit with Redis"""
        store.max_concurrent = 2
        mock_redis.lrange.return_value = ["old-session-1", "old-session-2"]

        async def mock_hgetall(key):
            return {
                b"session_id": key.split(b":")[-1],
                b"user_id": get_user_id("victor").encode(),
                b"username": b"victor",
                b"roles": b'["user"]',
                b"metadata": b"{}",
                b"created_at": datetime.now(timezone.utc).isoformat().encode(),
                b"expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat().encode(),
                b"last_accessed": datetime.now(timezone.utc).isoformat().encode(),
            }

        mock_redis.hgetall.side_effect = mock_hgetall
        await store.create(get_user_id("victor"), "victor", ["user"])
        assert mock_redis.delete.called

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_connection_error_handling(self):
        """Test handling of Redis connection errors"""
        with patch("redis.asyncio.from_url") as mock_from_url:
            mock_client = configured_async_mock(return_value=None)
            mock_client.ping.side_effect = Exception("Connection failed")
            mock_from_url.return_value = mock_client
            store = RedisSessionStore(redis_url="redis://invalid:6379/0")
            with pytest.raises(Exception):
                await store._ensure_connected()


@pytest.mark.xdist_group(name="session_tests")
class TestSessionStoreFactory:
    """Tests for create_session_store factory function"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.unit
    def test_create_memory_store(self):
        """Test creating in-memory store"""
        store = create_session_store(backend="memory", default_ttl_seconds=7200)
        assert isinstance(store, InMemorySessionStore)
        assert store.default_ttl == 7200

    @pytest.mark.unit
    def test_create_redis_store(self):
        """Test creating Redis store"""
        with patch("redis.asyncio.from_url"):
            store = create_session_store(backend="redis", redis_url="redis://localhost:6379/0", default_ttl_seconds=3600)
            assert isinstance(store, RedisSessionStore)
            assert store.default_ttl == 3600

    @pytest.mark.unit
    def test_create_default_store(self):
        """Test creating store with defaults"""
        store = create_session_store()
        assert isinstance(store, InMemorySessionStore)

    @pytest.mark.unit
    def test_create_with_custom_settings(self):
        """Test creating store with custom settings"""
        store = create_session_store(
            backend="memory", default_ttl_seconds=1800, max_concurrent_sessions=10, sliding_window=False
        )
        assert isinstance(store, InMemorySessionStore)
        assert store.default_ttl == 1800
        assert store.max_concurrent == 10
        assert store.sliding_window is False

    @pytest.mark.unit
    def test_invalid_backend(self):
        """Test error handling for invalid backend"""
        with pytest.raises(ValueError, match="Unknown session backend"):
            create_session_store(backend="invalid")


@pytest.mark.xdist_group(name="session_tests")
class TestSessionIntegration:
    """Integration tests for session management"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_session_lifecycle(self):
        """Test complete session lifecycle"""
        store = InMemorySessionStore(default_ttl_seconds=3600)
        session_id = await store.create(user_id=get_user_id("wendy"), username="wendy", roles=["user", "premium"])
        assert session_id is not None
        session = await store.get(session_id)
        assert session is not None
        assert session.username == "wendy"
        success = await store.update(session_id, metadata={"last_ip": "192.168.1.100"})
        assert success is True
        session = await store.get(session_id)
        assert session.metadata["last_ip"] == "192.168.1.100"
        success = await store.refresh(session_id)
        assert success is True
        success = await store.delete(session_id)
        assert success is True
        session = await store.get(session_id)
        assert session is None

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_multi_user_sessions(self):
        """Test managing sessions for multiple users"""
        store = InMemorySessionStore()
        alice_session = await store.create(get_user_id("alice"), "alice", ["admin"])
        bob_session = await store.create(get_user_id("bob"), "bob", ["user"])
        await store.create(get_user_id("charlie"), "charlie", ["premium"])
        alice_sessions = await store.list_user_sessions(get_user_id("alice"))
        bob_sessions = await store.list_user_sessions(get_user_id("bob"))
        assert len(alice_sessions) == 1
        assert len(bob_sessions) == 1
        assert alice_sessions[0].session_id == alice_session
        assert bob_sessions[0].session_id == bob_session
        count = await store.delete_user_sessions(get_user_id("bob"))
        assert count == 1
        alice_sessions = await store.list_user_sessions(get_user_id("alice"))
        charlie_sessions = await store.list_user_sessions(get_user_id("charlie"))
        assert len(alice_sessions) == 1
        assert len(charlie_sessions) == 1


@pytest.mark.xdist_group(name="session_edge_cases")
class TestSessionEdgeCases:
    """
    P2: Test session management edge cases and validation
    """

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_session_data_with_zulu_time_normalization(self):
        """
        Test that SessionData handles Zulu time (Z suffix) correctly
        """
        from datetime import datetime, timezone

        from mcp_server_langgraph.auth.session import SessionData

        now = datetime.now(timezone.utc)
        timestamp_str = now.isoformat().replace("+00:00", "Z")
        session = SessionData(
            session_id="test-session-12345678901234567890",
            user_id=get_user_id("alice"),
            username="alice",
            roles=["user"],
            created_at=timestamp_str,
            last_accessed=timestamp_str,
            expires_at=timestamp_str,
        )
        assert session.session_id == "test-session-12345678901234567890"
        assert session.user_id == get_user_id("alice")

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_inactive_sessions_with_large_session_store(self):
        """
        Test get_inactive_sessions with many sessions (performance check)
        """
        from datetime import datetime, timedelta, timezone

        from mcp_server_langgraph.auth.session import InMemorySessionStore

        store = InMemorySessionStore()
        for i in range(100):
            await store.create(f"user:user{i}", f"user{i}", ["user"])
        inactive_threshold = datetime.now(timezone.utc) - timedelta(hours=1)
        inactive = await store.get_inactive_sessions(inactive_threshold)
        assert isinstance(inactive, list)
        assert len(inactive) == 0

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_session_data_with_invalid_iso_format_raises_error(self):
        """
        Test that SessionData validation rejects invalid ISO format timestamps
        """
        from pydantic import ValidationError

        from mcp_server_langgraph.auth.session import SessionData

        with pytest.raises(ValidationError, match="timestamp|datetime|iso|valid"):
            SessionData(
                session_id="test-session-invalid-12345678901",
                user_id=get_user_id("alice"),
                username="alice",
                roles=["user"],
                created_at="not-a-valid-timestamp",
                last_accessed="2025-01-01T00:00:00Z",
                expires_at="2025-01-01T00:00:00Z",
            )
