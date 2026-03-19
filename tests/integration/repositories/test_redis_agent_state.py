"""
Integration Tests for RedisAgentStateRepository.

Tests the Redis implementation of the agent state repository
with real Redis connections.

Phase 5: Redis Implementation for AgentState
"""

import gc
import socket
import uuid

import pytest

from tests.constants import TEST_REDIS_PORT

pytestmark = [pytest.mark.integration, pytest.mark.repository]

TEST_REDIS_HOST = "localhost"


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.xdist_group(name="testredisagentstaterepo")
@pytest.mark.skip_isolation_check
class TestRedisAgentStateRepository:
    """Test RedisAgentStateRepository with real Redis."""

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.fixture
    async def repo(self):
        try:
            with socket.create_connection((TEST_REDIS_HOST, TEST_REDIS_PORT), timeout=2):
                pass
        except (ConnectionRefusedError, TimeoutError, OSError):
            pytest.skip(f"Redis not available at {TEST_REDIS_HOST}:{TEST_REDIS_PORT}")

        import redis.asyncio as aioredis

        from mcp_server_langgraph.repositories.redis_agent_state import RedisAgentStateRepository

        client = aioredis.from_url(
            f"redis://{TEST_REDIS_HOST}:{TEST_REDIS_PORT}/4",
            decode_responses=True,
        )
        repo = RedisAgentStateRepository(client, session_ttl_seconds=60)

        # Clean test keys
        keys = await client.keys("agent_state:*")
        if keys:
            await client.delete(*keys)

        yield repo
        await client.aclose()

    async def test_save_and_get(self, repo):
        session_id = f"session-{uuid.uuid4().hex[:8]}"
        state = {"last_query": "Hello", "progress": "50%"}

        await repo.save(session_id, state)
        result = await repo.get(session_id)

        assert result is not None
        assert result["last_query"] == "Hello"
        assert result["progress"] == "50%"

    async def test_get_nonexistent_returns_none(self, repo):
        result = await repo.get("nonexistent-session")
        assert result is None

    async def test_checkpoint(self, repo):
        session_id = f"session-{uuid.uuid4().hex[:8]}"

        await repo.checkpoint(session_id, "research", "Completed research")

        state = await repo.get(session_id)
        assert state is not None
        assert "checkpoints" in state
        assert len(state["checkpoints"]) == 1
        assert state["checkpoints"][0]["phase"] == "research"

    async def test_list_sessions(self, repo):
        s1 = f"session-{uuid.uuid4().hex[:8]}"
        s2 = f"session-{uuid.uuid4().hex[:8]}"

        await repo.save(s1, {"progress": "50%"})
        await repo.save(s2, {"progress": "100%"})

        sessions = await repo.list_sessions()
        assert s1 in sessions
        assert s2 in sessions

    async def test_delete_session(self, repo):
        session_id = f"session-{uuid.uuid4().hex[:8]}"
        await repo.save(session_id, {"progress": "50%"})

        await repo.delete(session_id)

        result = await repo.get(session_id)
        assert result is None

    async def test_ttl_is_set(self, repo):
        session_id = f"session-{uuid.uuid4().hex[:8]}"
        await repo.save(session_id, {"progress": "50%"})

        ttl = await repo._redis.ttl(f"agent_state:{session_id}")
        assert ttl > 0
        assert ttl <= 60  # matches session_ttl_seconds=60
