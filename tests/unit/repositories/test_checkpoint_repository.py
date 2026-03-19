"""
Tests for Checkpoint Repository

TDD: These tests define the contract for storing and retrieving phase checkpoints.
Supports both InMemory (testing) and Postgres (production) implementations.
"""

from __future__ import annotations

import gc
from datetime import UTC, datetime, timedelta

import pytest

from mcp_server_langgraph.memory.checkpoints import Checkpoint

pytestmark = [pytest.mark.unit, pytest.mark.repository]


def _make_checkpoint(
    checkpoint_id: str = "checkpoint-test-1",
    phase: str = "research",
    summary: str = "Completed research phase",
    artifacts: list[str] | None = None,
    created_at: datetime | None = None,
    session_id: str | None = None,
    user_id: str | None = None,
) -> Checkpoint:
    """Create a test checkpoint with sensible defaults."""
    return Checkpoint(
        id=checkpoint_id,
        phase=phase,
        summary=summary,
        artifacts=artifacts or [],
        created_at=created_at or datetime.now(UTC),
        session_id=session_id,
        user_id=user_id,
    )


@pytest.fixture
def in_memory_repo():
    """Create an in-memory checkpoint repository for testing."""
    from mcp_server_langgraph.repositories.checkpoint import InMemoryCheckpointRepository

    return InMemoryCheckpointRepository()


class TestCheckpointRepositoryInterface:
    """Tests for CheckpointRepository abstract interface."""

    def teardown_method(self) -> None:
        gc.collect()

    def test_repository_base_class_exists(self) -> None:
        from mcp_server_langgraph.repositories.checkpoint import CheckpointRepository

        assert CheckpointRepository is not None

    def test_abstract_methods_defined(self) -> None:
        from mcp_server_langgraph.repositories.checkpoint import CheckpointRepository

        expected = {"create", "get", "get_latest", "list", "delete", "clear", "summarize", "list_by_user", "delete_by_user"}
        assert expected.issubset(CheckpointRepository.__abstractmethods__)


class TestInMemoryCheckpointRepository:
    """Tests for InMemoryCheckpointRepository."""

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.mark.asyncio
    async def test_create_stores_checkpoint(self, in_memory_repo) -> None:
        cp = _make_checkpoint()
        result = await in_memory_repo.create(cp)

        assert result.id == cp.id
        assert result.phase == cp.phase

    @pytest.mark.asyncio
    async def test_get_retrieves_checkpoint(self, in_memory_repo) -> None:
        cp = _make_checkpoint()
        await in_memory_repo.create(cp)

        result = await in_memory_repo.get(cp.id)
        assert result is not None
        assert result.id == cp.id

    @pytest.mark.asyncio
    async def test_get_returns_none_for_missing(self, in_memory_repo) -> None:
        result = await in_memory_repo.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_latest_returns_most_recent(self, in_memory_repo) -> None:
        base_time = datetime(2025, 1, 1, tzinfo=UTC)
        await in_memory_repo.create(_make_checkpoint(checkpoint_id="cp-old", created_at=base_time))
        await in_memory_repo.create(_make_checkpoint(checkpoint_id="cp-new", created_at=base_time + timedelta(hours=1)))

        latest = await in_memory_repo.get_latest()
        assert latest is not None
        assert latest.id == "cp-new"

    @pytest.mark.asyncio
    async def test_get_latest_returns_none_when_empty(self, in_memory_repo) -> None:
        result = await in_memory_repo.get_latest()
        assert result is None

    @pytest.mark.asyncio
    async def test_get_latest_scoped_by_user_id(self, in_memory_repo) -> None:
        base_time = datetime(2025, 1, 1, tzinfo=UTC)
        await in_memory_repo.create(_make_checkpoint(checkpoint_id="cp-a1", user_id="user-A", created_at=base_time))
        await in_memory_repo.create(
            _make_checkpoint(checkpoint_id="cp-b1", user_id="user-B", created_at=base_time + timedelta(hours=1))
        )
        await in_memory_repo.create(
            _make_checkpoint(checkpoint_id="cp-a2", user_id="user-A", created_at=base_time + timedelta(hours=2))
        )

        latest = await in_memory_repo.get_latest(user_id="user-A")
        assert latest is not None
        assert latest.id == "cp-a2"

    @pytest.mark.asyncio
    async def test_list_returns_all(self, in_memory_repo) -> None:
        for i in range(3):
            await in_memory_repo.create(_make_checkpoint(checkpoint_id=f"cp-{i}"))

        checkpoints = await in_memory_repo.list()
        assert len(checkpoints) == 3

    @pytest.mark.asyncio
    async def test_list_filters_by_phase(self, in_memory_repo) -> None:
        await in_memory_repo.create(_make_checkpoint(checkpoint_id="cp-1", phase="research"))
        await in_memory_repo.create(_make_checkpoint(checkpoint_id="cp-2", phase="research"))
        await in_memory_repo.create(_make_checkpoint(checkpoint_id="cp-3", phase="implementation"))

        checkpoints = await in_memory_repo.list(phase="research")
        assert len(checkpoints) == 2
        assert all(c.phase == "research" for c in checkpoints)

    @pytest.mark.asyncio
    async def test_list_filters_by_user_id(self, in_memory_repo) -> None:
        await in_memory_repo.create(_make_checkpoint(checkpoint_id="cp-1", user_id="user-A"))
        await in_memory_repo.create(_make_checkpoint(checkpoint_id="cp-2", user_id="user-B"))

        checkpoints = await in_memory_repo.list(user_id="user-A")
        assert len(checkpoints) == 1

    @pytest.mark.asyncio
    async def test_list_with_limit_and_offset(self, in_memory_repo) -> None:
        base_time = datetime(2025, 1, 1, tzinfo=UTC)
        for i in range(5):
            await in_memory_repo.create(_make_checkpoint(checkpoint_id=f"cp-{i}", created_at=base_time + timedelta(seconds=i)))

        checkpoints = await in_memory_repo.list(limit=2, offset=1)
        assert len(checkpoints) == 2

    @pytest.mark.asyncio
    async def test_list_sorted_desc(self, in_memory_repo) -> None:
        base_time = datetime(2025, 1, 1, tzinfo=UTC)
        await in_memory_repo.create(_make_checkpoint(checkpoint_id="oldest", created_at=base_time))
        await in_memory_repo.create(_make_checkpoint(checkpoint_id="newest", created_at=base_time + timedelta(hours=1)))

        checkpoints = await in_memory_repo.list()
        assert checkpoints[0].id == "newest"

    @pytest.mark.asyncio
    async def test_delete_removes_checkpoint(self, in_memory_repo) -> None:
        cp = _make_checkpoint()
        await in_memory_repo.create(cp)

        result = await in_memory_repo.delete(cp.id)
        assert result is True
        assert await in_memory_repo.get(cp.id) is None

    @pytest.mark.asyncio
    async def test_delete_returns_false_for_missing(self, in_memory_repo) -> None:
        result = await in_memory_repo.delete("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_clear_removes_all(self, in_memory_repo) -> None:
        for i in range(3):
            await in_memory_repo.create(_make_checkpoint(checkpoint_id=f"cp-{i}"))

        await in_memory_repo.clear()
        checkpoints = await in_memory_repo.list()
        assert len(checkpoints) == 0

    @pytest.mark.asyncio
    async def test_summarize_generates_summary(self, in_memory_repo) -> None:
        base_time = datetime(2025, 1, 1, tzinfo=UTC)
        await in_memory_repo.create(
            _make_checkpoint(checkpoint_id="cp-1", phase="research", summary="Found patterns", created_at=base_time)
        )
        await in_memory_repo.create(
            _make_checkpoint(
                checkpoint_id="cp-2",
                phase="implementation",
                summary="Built feature",
                created_at=base_time + timedelta(hours=1),
            )
        )

        summary = await in_memory_repo.summarize()
        assert "Research" in summary
        assert "Found patterns" in summary
        assert "Implementation" in summary

    @pytest.mark.asyncio
    async def test_summarize_empty(self, in_memory_repo) -> None:
        summary = await in_memory_repo.summarize()
        assert "No checkpoints" in summary

    @pytest.mark.asyncio
    async def test_list_by_user(self, in_memory_repo) -> None:
        await in_memory_repo.create(_make_checkpoint(checkpoint_id="cp-1", user_id="user-A"))
        await in_memory_repo.create(_make_checkpoint(checkpoint_id="cp-2", user_id="user-A"))
        await in_memory_repo.create(_make_checkpoint(checkpoint_id="cp-3", user_id="user-B"))

        checkpoints = await in_memory_repo.list_by_user("user-A")
        assert len(checkpoints) == 2
        assert all(c.user_id == "user-A" for c in checkpoints)

    @pytest.mark.asyncio
    async def test_delete_by_user(self, in_memory_repo) -> None:
        await in_memory_repo.create(_make_checkpoint(checkpoint_id="cp-1", user_id="user-A"))
        await in_memory_repo.create(_make_checkpoint(checkpoint_id="cp-2", user_id="user-A"))
        await in_memory_repo.create(_make_checkpoint(checkpoint_id="cp-3", user_id="user-B"))

        count = await in_memory_repo.delete_by_user("user-A")
        assert count == 2
        assert await in_memory_repo.get("cp-1") is None
        assert await in_memory_repo.get("cp-3") is not None


class TestCheckpointRepositoryCrossUserAuthorization:
    """Negative cross-user authorization tests."""

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.mark.asyncio
    async def test_list_by_user_isolates_users(self, in_memory_repo) -> None:
        await in_memory_repo.create(_make_checkpoint(checkpoint_id="cp-1", user_id="user-A"))
        await in_memory_repo.create(_make_checkpoint(checkpoint_id="cp-2", user_id="user-B"))

        checkpoints = await in_memory_repo.list_by_user("user-A")
        assert all(c.user_id != "user-B" for c in checkpoints)

    @pytest.mark.asyncio
    async def test_delete_by_user_does_not_delete_other_users(self, in_memory_repo) -> None:
        await in_memory_repo.create(_make_checkpoint(checkpoint_id="cp-1", user_id="user-A"))
        await in_memory_repo.create(_make_checkpoint(checkpoint_id="cp-2", user_id="user-B"))

        await in_memory_repo.delete_by_user("user-A")
        assert await in_memory_repo.get("cp-2") is not None

    @pytest.mark.asyncio
    async def test_get_latest_scoped_by_user_does_not_leak(self, in_memory_repo) -> None:
        base_time = datetime(2025, 1, 1, tzinfo=UTC)
        await in_memory_repo.create(
            _make_checkpoint(
                checkpoint_id="cp-b",
                user_id="user-B",
                created_at=base_time + timedelta(hours=10),  # Much newer
            )
        )
        await in_memory_repo.create(_make_checkpoint(checkpoint_id="cp-a", user_id="user-A", created_at=base_time))

        latest = await in_memory_repo.get_latest(user_id="user-A")
        assert latest is not None
        assert latest.id == "cp-a"
        assert latest.user_id == "user-A"
