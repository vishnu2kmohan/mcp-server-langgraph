"""
Tests for Redis Agent State Repository

Uses mock Redis client for unit testing without a real Redis instance.
"""

from __future__ import annotations

import gc
from unittest.mock import AsyncMock, MagicMock

import pybreaker
import pytest

pytestmark = [pytest.mark.unit, pytest.mark.repository]


class MockPipeline:
    """Minimal mock Redis pipeline supporting set/sadd/delete/srem + execute."""

    def __init__(self, store: dict, sets: dict):
        self._store = store
        self._sets = sets
        self._ops: list = []

    def set(self, key, value, ex=None):
        self._ops.append(("set", key, value, ex))
        return self

    def sadd(self, key, *values):
        self._ops.append(("sadd", key, values))
        return self

    def delete(self, *keys):
        self._ops.append(("delete", keys))
        return self

    def srem(self, key, *values):
        self._ops.append(("srem", key, values))
        return self

    async def execute(self):
        for op in self._ops:
            if op[0] == "set":
                self._store[op[1]] = op[2]
            elif op[0] == "sadd":
                if op[1] not in self._sets:
                    self._sets[op[1]] = set()
                for v in op[2]:
                    self._sets[op[1]].add(v)
            elif op[0] == "delete":
                for k in op[1]:
                    self._store.pop(k, None)
            elif op[0] == "srem":
                if op[1] in self._sets:
                    for v in op[2]:
                        self._sets[op[1]].discard(v)
        self._ops.clear()


def make_mock_redis():
    """Create a mock Redis client that stores data in-memory dicts."""
    store = {}
    sets = {}

    mock = AsyncMock()  # noqa: async-mock-config

    async def mock_get(key):
        return store.get(key)

    async def mock_smembers(key):
        return sets.get(key, set())

    mock.get = mock_get
    mock.smembers = mock_smembers
    mock.pipeline = MagicMock(return_value=MockPipeline(store, sets))

    return mock


@pytest.fixture
def mock_redis():
    return make_mock_redis()


@pytest.fixture
def redis_repo(mock_redis):
    from mcp_server_langgraph.repositories.redis_agent_state import RedisAgentStateRepository

    return RedisAgentStateRepository(mock_redis, session_ttl_seconds=3600)


class TestRedisAgentStateRepository:
    """Tests for RedisAgentStateRepository."""

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.mark.asyncio
    async def test_save_and_get(self, redis_repo) -> None:
        state = {"progress": "50%", "step": 3}
        await redis_repo.save("session-1", state)

        result = await redis_repo.get("session-1")
        assert result is not None
        assert result["progress"] == "50%"

    @pytest.mark.asyncio
    async def test_get_returns_none_for_missing(self, redis_repo) -> None:
        result = await redis_repo.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_save_overwrites_existing(self, redis_repo) -> None:
        await redis_repo.save("session-1", {"v": 1})
        await redis_repo.save("session-1", {"v": 2})

        result = await redis_repo.get("session-1")
        assert result["v"] == 2

    @pytest.mark.asyncio
    async def test_checkpoint_stores_phase(self, redis_repo) -> None:
        await redis_repo.save("session-1", {"data": "initial"})
        await redis_repo.checkpoint("session-1", "research", "Done researching")

        state = await redis_repo.get("session-1")
        assert "checkpoints" in state
        assert len(state["checkpoints"]) == 1
        assert state["checkpoints"][0]["phase"] == "research"

    @pytest.mark.asyncio
    async def test_checkpoint_appends(self, redis_repo) -> None:
        await redis_repo.save("session-1", {})
        await redis_repo.checkpoint("session-1", "research", "Research done")
        await redis_repo.checkpoint("session-1", "impl", "Code done")

        state = await redis_repo.get("session-1")
        assert len(state["checkpoints"]) == 2

    @pytest.mark.asyncio
    async def test_list_sessions(self, redis_repo) -> None:
        await redis_repo.save("s1", {"a": 1})
        await redis_repo.save("s2", {"b": 2})

        sessions = await redis_repo.list_sessions()
        assert set(sessions) == {"s1", "s2"}

    @pytest.mark.asyncio
    async def test_delete_removes_session(self, redis_repo) -> None:
        await redis_repo.save("s1", {"a": 1})
        await redis_repo.delete("s1")

        assert await redis_repo.get("s1") is None
        sessions = await redis_repo.list_sessions()
        assert "s1" not in sessions

    @pytest.mark.asyncio
    async def test_delete_nonexistent_no_error(self, redis_repo) -> None:
        await redis_repo.delete("nonexistent")  # Should not raise


class TestRedisAgentStateCircuitBreaker:
    """Tests for circuit breaker fallback behavior."""

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.mark.asyncio
    async def test_fallback_on_circuit_open(self) -> None:
        from mcp_server_langgraph.repositories.redis_agent_state import RedisAgentStateRepository

        mock_redis = make_mock_redis()

        breaker = pybreaker.CircuitBreaker(
            fail_max=1,
            reset_timeout=60,
            name="test_agent_state_breaker",
        )

        repo = RedisAgentStateRepository(mock_redis, session_ttl_seconds=3600, circuit_breaker=breaker)

        # Force the breaker open by tripping it with sync failures
        def _sync_fail():
            raise ConnectionError("Redis down")

        for _ in range(2):
            try:
                breaker.call(_sync_fail)
            except (ConnectionError, pybreaker.CircuitBreakerError):
                pass

        assert breaker.current_state == "open"

        # Breaker is open — operations fall back to in-memory
        await repo.save("fallback-session", {"data": "fallback"})
        result = await repo.get("fallback-session")

        assert result is not None
        assert result["data"] == "fallback"
