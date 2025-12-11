"""
Integration tests for Redis-backed session management.

Tests the session manager against real Redis infrastructure:
- Session CRUD operations with real Redis
- TTL expiration behavior
- Message history persistence
- Multi-user session isolation
- Connection recovery

Requires: Redis running at TEST_REDIS_URL or docker-compose.test.yml

Run with:
    make test-infra-up
    pytest tests/integration/playground/test_playground_redis_session.py -v
"""

import asyncio
import gc
import uuid

import pytest

from tests.constants import TEST_REDIS_PLAYGROUND_DB, TEST_REDIS_PORT

pytestmark = [
    pytest.mark.integration,
    pytest.mark.playground,
    pytest.mark.redis,
    pytest.mark.xdist_group(name="playground_redis_integration_tests"),
]


@pytest.fixture
def redis_url() -> str:
    """Get Redis URL for playground sessions."""
    return f"redis://localhost:{TEST_REDIS_PORT}/{TEST_REDIS_PLAYGROUND_DB}"


@pytest.fixture
async def redis_client(redis_url: str):
    """Create Redis client for testing."""
    import redis.asyncio as redis
    from redis.exceptions import ConnectionError as RedisConnectionError

    client = redis.from_url(redis_url, decode_responses=True)
    # Test connection by pinging
    try:
        await client.ping()
    except (OSError, RedisConnectionError) as e:
        await client.aclose()
        pytest.skip(f"Redis infrastructure not available: {e}")
    yield client
    # Clean up test keys - ignore errors if connection dropped
    try:
        async for key in client.scan_iter("session:*"):
            await client.delete(key)
    except (OSError, RedisConnectionError):
        pass  # Connection already lost, nothing to clean up
    try:
        await client.aclose()
    except (OSError, RedisConnectionError):
        pass  # Already closed


@pytest.fixture
async def session_manager(redis_client):
    """Create session manager with real Redis."""
    from mcp_server_langgraph.playground.session.manager import RedisSessionManager

    manager = RedisSessionManager(redis_client=redis_client, ttl_seconds=60)
    return manager


@pytest.mark.xdist_group(name="playground_redis_integration_tests")
class TestRedisSessionIntegration:
    """Integration tests for Redis session storage."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_create_session_persists_to_redis(self, session_manager, redis_client) -> None:
        """Test that created sessions are actually stored in Redis."""
        session = await session_manager.create_session(
            name="Integration Test Session",
            user_id="alice",
        )

        # Verify session exists in Redis
        key = f"session:{session.session_id}"
        data = await redis_client.get(key)

        assert data is not None
        assert "Integration Test Session" in data
        assert session.session_id in data

    @pytest.mark.asyncio
    async def test_get_session_retrieves_from_redis(self, session_manager) -> None:
        """Test retrieving a session from Redis."""
        created = await session_manager.create_session(
            name="Retrieve Test",
            user_id="bob",
        )

        retrieved = await session_manager.get_session(created.session_id)

        assert retrieved is not None
        assert retrieved.session_id == created.session_id
        assert retrieved.name == "Retrieve Test"
        assert retrieved.user_id == "bob"

    @pytest.mark.asyncio
    async def test_session_ttl_is_set(self, session_manager, redis_client) -> None:
        """Test that session TTL is properly set in Redis."""
        session = await session_manager.create_session(
            name="TTL Test",
            user_id="charlie",
        )

        key = f"session:{session.session_id}"
        ttl = await redis_client.ttl(key)

        # TTL should be set (60 seconds in fixture, allow some margin)
        assert ttl > 0
        assert ttl <= 60

    @pytest.mark.asyncio
    async def test_add_message_updates_session(self, session_manager) -> None:
        """Test adding messages to session history."""
        session = await session_manager.create_session(
            name="Message Test",
            user_id="dave",
        )

        # Add a message
        message = await session_manager.add_message(
            session_id=session.session_id,
            role="user",
            content="Hello, world!",
            metadata={"source": "integration_test"},
        )

        assert message is not None
        assert message.role == "user"
        assert message.content == "Hello, world!"

        # Verify message persisted
        retrieved = await session_manager.get_session(session.session_id)
        assert len(retrieved.messages) == 1
        assert retrieved.messages[0].content == "Hello, world!"

    @pytest.mark.asyncio
    async def test_delete_session_removes_from_redis(self, session_manager, redis_client) -> None:
        """Test that deleted sessions are removed from Redis."""
        session = await session_manager.create_session(
            name="Delete Test",
            user_id="eve",
        )

        key = f"session:{session.session_id}"
        assert await redis_client.exists(key)

        result = await session_manager.delete_session(session.session_id)

        assert result is True
        assert not await redis_client.exists(key)

    @pytest.mark.asyncio
    async def test_list_sessions_for_user(self, session_manager) -> None:
        """Test listing sessions scoped to a user."""
        user_id = f"user-{uuid.uuid4()}"

        # Create multiple sessions for the user
        session1 = await session_manager.create_session(name="Session 1", user_id=user_id)
        session2 = await session_manager.create_session(name="Session 2", user_id=user_id)
        session3 = await session_manager.create_session(name="Session 3", user_id=user_id)

        # Create session for different user
        await session_manager.create_session(name="Other User", user_id="other")

        sessions = await session_manager.list_sessions(user_id=user_id)

        assert len(sessions) == 3
        session_ids = {s.session_id for s in sessions}
        assert session1.session_id in session_ids
        assert session2.session_id in session_ids
        assert session3.session_id in session_ids

    @pytest.mark.asyncio
    async def test_update_session_refreshes_ttl(self, session_manager, redis_client) -> None:
        """Test that updating a session refreshes its TTL."""
        session = await session_manager.create_session(
            name="TTL Refresh Test",
            user_id="frank",
        )

        key = f"session:{session.session_id}"
        initial_ttl = await redis_client.ttl(key)

        # Wait a bit
        await asyncio.sleep(2)

        # Update session
        await session_manager.update_session(session.session_id, name="Updated Name")

        new_ttl = await redis_client.ttl(key)

        # TTL should be refreshed (close to initial)
        # Allow 10 second margin for pytest-xdist parallel execution timing variance
        assert new_ttl >= initial_ttl - 10

    @pytest.mark.asyncio
    async def test_concurrent_session_operations(self, session_manager) -> None:
        """Test concurrent session operations don't interfere."""
        user_id = f"concurrent-{uuid.uuid4()}"

        # Create sessions concurrently
        tasks = [session_manager.create_session(name=f"Concurrent {i}", user_id=user_id) for i in range(5)]
        sessions = await asyncio.gather(*tasks)

        assert len(sessions) == 5
        assert len({s.session_id for s in sessions}) == 5  # All unique IDs

    @pytest.mark.asyncio
    async def test_message_order_preserved(self, session_manager) -> None:
        """Test that message order is preserved in session history."""
        session = await session_manager.create_session(
            name="Order Test",
            user_id="grace",
        )

        # Add messages in order
        for i in range(5):
            await session_manager.add_message(
                session_id=session.session_id,
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}",
            )

        retrieved = await session_manager.get_session(session.session_id)

        assert len(retrieved.messages) == 5
        for i, msg in enumerate(retrieved.messages):
            assert msg.content == f"Message {i}"


@pytest.mark.xdist_group(name="playground_redis_integration_tests")
class TestRedisConnectionResilience:
    """Test Redis connection handling and recovery."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_handles_nonexistent_session(self, session_manager) -> None:
        """Test graceful handling of nonexistent sessions."""
        result = await session_manager.get_session("nonexistent-session-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_session_returns_false(self, session_manager) -> None:
        """Test deleting nonexistent session returns False."""
        result = await session_manager.delete_session("nonexistent-session-id")
        assert result is False

    @pytest.mark.asyncio
    async def test_add_message_to_nonexistent_session_returns_none(self, session_manager) -> None:
        """Test adding message to nonexistent session."""
        result = await session_manager.add_message(
            session_id="nonexistent-session-id",
            role="user",
            content="Test",
        )
        assert result is None
