"""
TDD tests for session metrics integration.

Verifies that session operations record metrics via record_session_operation().
"""

import gc
from unittest.mock import AsyncMock, patch

import pytest

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.auth
@pytest.mark.metrics
@pytest.mark.xdist_group(name="session_metrics_inmemory")
class TestInMemorySessionMetrics:
    """Test session metrics are recorded during operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_inmemory_session_create_records_metrics(self) -> None:
        """Verify InMemorySessionStore.create records session creation metrics."""
        from mcp_server_langgraph.auth.session import InMemorySessionStore

        store = InMemorySessionStore()

        with patch("mcp_server_langgraph.auth.session.record_session_operation") as mock_record:
            session_id = await store.create(
                user_id="user:test",
                username="testuser",
                roles=["user"],
                metadata={"ip": "192.168.1.1"},
            )

            # Verify session was created
            assert session_id is not None
            assert len(session_id) >= 32

            # Verify metrics were recorded
            mock_record.assert_called_once()
            call_args = mock_record.call_args

            # Check operation is "create"
            assert call_args[0][0] == "create" or call_args.kwargs.get("operation") == "create"
            # Check backend is "memory"
            assert call_args[0][1] == "memory" or call_args.kwargs.get("backend") == "memory"
            # Check result is "success"
            assert call_args[0][2] == "success" or call_args.kwargs.get("result") == "success"

    @pytest.mark.asyncio
    async def test_inmemory_session_get_records_metrics(self) -> None:
        """Verify InMemorySessionStore.get records session retrieval metrics."""
        from mcp_server_langgraph.auth.session import InMemorySessionStore

        store = InMemorySessionStore()

        # Create a session first (without metrics to isolate test)
        with patch("mcp_server_langgraph.auth.session.record_session_operation"):
            session_id = await store.create(
                user_id="user:test",
                username="testuser",
                roles=["user"],
            )

        # Now test get with metrics
        with patch("mcp_server_langgraph.auth.session.record_session_operation") as mock_record:
            session = await store.get(session_id)

            # Verify session was retrieved
            assert session is not None
            assert session.username == "testuser"

            # Verify metrics were recorded
            mock_record.assert_called_once()
            call_args = mock_record.call_args

            # Check operation is "retrieve"
            assert call_args[0][0] == "retrieve" or call_args.kwargs.get("operation") == "retrieve"

    @pytest.mark.asyncio
    async def test_inmemory_session_delete_records_metrics(self) -> None:
        """Verify InMemorySessionStore.delete records session deletion metrics."""
        from mcp_server_langgraph.auth.session import InMemorySessionStore

        store = InMemorySessionStore()

        # Create a session first
        with patch("mcp_server_langgraph.auth.session.record_session_operation"):
            session_id = await store.create(
                user_id="user:test",
                username="testuser",
                roles=["user"],
            )

        # Now test delete with metrics
        with patch("mcp_server_langgraph.auth.session.record_session_operation") as mock_record:
            deleted = await store.delete(session_id)

            # Verify session was deleted
            assert deleted is True

            # Verify metrics were recorded
            mock_record.assert_called_once()
            call_args = mock_record.call_args

            # Check operation is "revoke"
            assert call_args[0][0] == "revoke" or call_args.kwargs.get("operation") == "revoke"


@pytest.mark.unit
@pytest.mark.auth
@pytest.mark.metrics
@pytest.mark.xdist_group(name="session_metrics_redis")
class TestRedisSessionMetrics:
    """Test session metrics are recorded during Redis session operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_redis_session_create_records_metrics(self) -> None:
        """Verify RedisSessionStore.create records session creation metrics."""
        from mcp_server_langgraph.auth.session import RedisSessionStore

        # Create a mock Redis client
        mock_redis = AsyncMock()
        mock_redis.lrange.return_value = []  # No existing sessions
        mock_redis.hset.return_value = True
        mock_redis.expire.return_value = True
        mock_redis.rpush.return_value = 1

        # Create store and inject mock Redis
        store = RedisSessionStore(redis_url="redis://localhost:6379/0")
        store.redis = mock_redis

        with patch("mcp_server_langgraph.auth.session.record_session_operation") as mock_record:
            session_id = await store.create(
                user_id="user:test",
                username="testuser",
                roles=["user"],
                metadata={"ip": "192.168.1.1"},
            )

            # Verify session was created
            assert session_id is not None
            assert len(session_id) >= 32

            # Verify metrics were recorded
            mock_record.assert_called_once()
            call_args = mock_record.call_args

            # Check operation is "create"
            assert call_args[0][0] == "create" or call_args.kwargs.get("operation") == "create"
            # Check backend is "redis"
            assert call_args[0][1] == "redis" or call_args.kwargs.get("backend") == "redis"
            # Check result is "success"
            assert call_args[0][2] == "success" or call_args.kwargs.get("result") == "success"

    @pytest.mark.asyncio
    async def test_redis_session_get_records_metrics(self) -> None:
        """Verify RedisSessionStore.get records session retrieval metrics."""
        import json
        from datetime import UTC, datetime, timedelta

        from mcp_server_langgraph.auth.session import RedisSessionStore

        # Create a mock Redis client with session data
        now = datetime.now(UTC)
        mock_redis = AsyncMock()
        mock_redis.hgetall.return_value = {
            "session_id": "test-session-id-32chars-minimum-x",
            "user_id": "user:test",
            "username": "testuser",
            "roles": "user,admin",
            "metadata": json.dumps({"ip": "192.168.1.1"}),
            "created_at": now.isoformat(),
            "last_accessed": now.isoformat(),
            "expires_at": (now + timedelta(hours=24)).isoformat(),
        }
        mock_redis.hset.return_value = True

        # Create store and inject mock Redis
        store = RedisSessionStore(redis_url="redis://localhost:6379/0")
        store.redis = mock_redis

        with patch("mcp_server_langgraph.auth.session.record_session_operation") as mock_record:
            session = await store.get("test-session-id-32chars-minimum-x")

            # Verify session was retrieved
            assert session is not None
            assert session.username == "testuser"

            # Verify metrics were recorded
            mock_record.assert_called_once()
            call_args = mock_record.call_args

            # Check operation is "retrieve"
            assert call_args[0][0] == "retrieve" or call_args.kwargs.get("operation") == "retrieve"
            # Check backend is "redis"
            assert call_args[0][1] == "redis" or call_args.kwargs.get("backend") == "redis"

    @pytest.mark.asyncio
    async def test_redis_session_delete_records_metrics(self) -> None:
        """Verify RedisSessionStore.delete records session deletion metrics."""
        from mcp_server_langgraph.auth.session import RedisSessionStore

        # Create a mock Redis client
        mock_redis = AsyncMock()
        mock_redis.hget.return_value = "user:test"  # Return user_id
        mock_redis.delete.return_value = 1  # Session deleted
        mock_redis.lrem.return_value = 1

        # Create store and inject mock Redis
        store = RedisSessionStore(redis_url="redis://localhost:6379/0")
        store.redis = mock_redis

        with patch("mcp_server_langgraph.auth.session.record_session_operation") as mock_record:
            deleted = await store.delete("test-session-id-32chars-minimum-x")

            # Verify session was deleted
            assert deleted is True

            # Verify metrics were recorded
            mock_record.assert_called_once()
            call_args = mock_record.call_args

            # Check operation is "revoke"
            assert call_args[0][0] == "revoke" or call_args.kwargs.get("operation") == "revoke"
            # Check backend is "redis"
            assert call_args[0][1] == "redis" or call_args.kwargs.get("backend") == "redis"

    @pytest.mark.asyncio
    async def test_redis_session_get_not_found_records_metrics(self) -> None:
        """Verify RedisSessionStore.get records not_found when session doesn't exist."""
        from mcp_server_langgraph.auth.session import RedisSessionStore

        # Create a mock Redis client that returns empty (no session)
        mock_redis = AsyncMock()
        mock_redis.hgetall.return_value = {}  # No session found

        # Create store and inject mock Redis
        store = RedisSessionStore(redis_url="redis://localhost:6379/0")
        store.redis = mock_redis

        with patch("mcp_server_langgraph.auth.session.record_session_operation") as mock_record:
            session = await store.get("nonexistent-session-id-32chars-x")

            # Verify session was not found
            assert session is None

            # Verify metrics were recorded with not_found result
            mock_record.assert_called_once()
            call_args = mock_record.call_args

            # Check operation is "retrieve"
            assert call_args[0][0] == "retrieve" or call_args.kwargs.get("operation") == "retrieve"
            # Check result is "not_found"
            assert call_args[0][2] == "not_found" or call_args.kwargs.get("result") == "not_found"
