"""
Tests for Agent State Repository

TDD: These tests define the contract for storing and retrieving ephemeral agent state.
Supports both InMemory (testing) and Redis (production) implementations.
"""

from __future__ import annotations

import gc

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.repository]


@pytest.fixture
def in_memory_repo():
    """Create an in-memory agent state repository for testing."""
    from mcp_server_langgraph.repositories.agent_state import InMemoryAgentStateRepository

    return InMemoryAgentStateRepository()


class TestAgentStateRepositoryInterface:
    """Tests for AgentStateRepository abstract interface."""

    def teardown_method(self) -> None:
        gc.collect()

    def test_repository_base_class_exists(self) -> None:
        from mcp_server_langgraph.repositories.agent_state import AgentStateRepository

        assert AgentStateRepository is not None

    def test_abstract_methods_defined(self) -> None:
        from mcp_server_langgraph.repositories.agent_state import AgentStateRepository

        expected = {"save", "get", "checkpoint", "list_sessions", "delete"}
        assert expected.issubset(AgentStateRepository.__abstractmethods__)


class TestInMemoryAgentStateRepository:
    """Tests for InMemoryAgentStateRepository."""

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.mark.asyncio
    async def test_save_and_get(self, in_memory_repo) -> None:
        state = {"progress": "50%", "current_step": 3}
        await in_memory_repo.save("session-1", state)

        result = await in_memory_repo.get("session-1")
        assert result is not None
        assert result["progress"] == "50%"

    @pytest.mark.asyncio
    async def test_get_returns_none_for_missing(self, in_memory_repo) -> None:
        result = await in_memory_repo.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_save_overwrites_existing(self, in_memory_repo) -> None:
        await in_memory_repo.save("session-1", {"v": 1})
        await in_memory_repo.save("session-1", {"v": 2})

        result = await in_memory_repo.get("session-1")
        assert result is not None
        assert result["v"] == 2

    @pytest.mark.asyncio
    async def test_checkpoint_stores_phase_data(self, in_memory_repo) -> None:
        await in_memory_repo.save("session-1", {"data": "initial"})
        await in_memory_repo.checkpoint("session-1", "research", "Completed research")

        state = await in_memory_repo.get("session-1")
        assert state is not None
        assert "checkpoints" in state
        assert len(state["checkpoints"]) == 1
        assert state["checkpoints"][0]["phase"] == "research"

    @pytest.mark.asyncio
    async def test_checkpoint_appends_to_existing(self, in_memory_repo) -> None:
        await in_memory_repo.save("session-1", {"data": "initial"})
        await in_memory_repo.checkpoint("session-1", "research", "Research done")
        await in_memory_repo.checkpoint("session-1", "implementation", "Code done")

        state = await in_memory_repo.get("session-1")
        assert state is not None
        assert len(state["checkpoints"]) == 2

    @pytest.mark.asyncio
    async def test_checkpoint_creates_state_if_missing(self, in_memory_repo) -> None:
        await in_memory_repo.checkpoint("new-session", "init", "Starting")

        state = await in_memory_repo.get("new-session")
        assert state is not None
        assert len(state["checkpoints"]) == 1

    @pytest.mark.asyncio
    async def test_list_sessions(self, in_memory_repo) -> None:
        await in_memory_repo.save("session-1", {"data": "a"})
        await in_memory_repo.save("session-2", {"data": "b"})
        await in_memory_repo.save("session-3", {"data": "c"})

        sessions = await in_memory_repo.list_sessions()
        assert set(sessions) == {"session-1", "session-2", "session-3"}

    @pytest.mark.asyncio
    async def test_list_sessions_empty(self, in_memory_repo) -> None:
        sessions = await in_memory_repo.list_sessions()
        assert sessions == []

    @pytest.mark.asyncio
    async def test_delete_removes_session(self, in_memory_repo) -> None:
        await in_memory_repo.save("session-1", {"data": "a"})
        await in_memory_repo.delete("session-1")

        assert await in_memory_repo.get("session-1") is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_no_error(self, in_memory_repo) -> None:
        # Should not raise
        await in_memory_repo.delete("nonexistent")

    @pytest.mark.asyncio
    async def test_delete_removes_from_session_list(self, in_memory_repo) -> None:
        await in_memory_repo.save("session-1", {"data": "a"})
        await in_memory_repo.save("session-2", {"data": "b"})

        await in_memory_repo.delete("session-1")

        sessions = await in_memory_repo.list_sessions()
        assert "session-1" not in sessions
        assert "session-2" in sessions
