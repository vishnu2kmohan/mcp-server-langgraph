"""
Integration Tests for PostgresCheckpointRepository.

Tests the PostgreSQL implementation of the checkpoint repository
with real database connections.

Phase 4: PostgreSQL Repositories (SQLAlchemy AsyncSession)
"""

from __future__ import annotations

import gc
import socket
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from tests.constants import (
    TEST_POSTGRES_HOST,
    TEST_POSTGRES_PASSWORD,
    TEST_POSTGRES_PORT,
    TEST_POSTGRES_USER,
)

pytestmark = [pytest.mark.integration, pytest.mark.repository]


def create_test_checkpoint(
    user_id: str | None = None,
    phase: str = "research",
    summary: str = "Completed research phase",
) -> Checkpoint:  # noqa: F821
    from mcp_server_langgraph.memory.checkpoints import Checkpoint

    return Checkpoint(
        id=f"cp-{uuid.uuid4().hex[:8]}",
        phase=phase,
        summary=summary,
        user_id=user_id or f"user:{uuid.uuid4().hex[:8]}",
    )


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.xdist_group(name="testpostgrescheckpointrepo")
@pytest.mark.skip_isolation_check
class TestPostgresCheckpointRepository:
    """Test PostgresCheckpointRepository with real PostgreSQL."""

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.fixture
    async def async_engine(self):
        try:
            with socket.create_connection((TEST_POSTGRES_HOST, TEST_POSTGRES_PORT), timeout=2):
                pass
        except (ConnectionRefusedError, TimeoutError, OSError):
            pytest.skip(f"PostgreSQL not available at {TEST_POSTGRES_HOST}:{TEST_POSTGRES_PORT}")

        import mcp_server_langgraph.repositories.postgres_models.agentic  # noqa: F401

        database_url = (
            f"postgresql+asyncpg://{TEST_POSTGRES_USER}:{TEST_POSTGRES_PASSWORD}"
            f"@{TEST_POSTGRES_HOST}:{TEST_POSTGRES_PORT}/compliance_test"
        )
        engine = create_async_engine(database_url, echo=False, pool_pre_ping=True)
        yield engine
        await engine.dispose()

    @pytest.fixture
    async def repo(self, async_engine: AsyncEngine):
        from sqlalchemy import text

        from mcp_server_langgraph.repositories.postgres_checkpoint import PostgresCheckpointRepository

        async with async_engine.begin() as conn:
            await conn.execute(text("DELETE FROM phase_checkpoints"))

        session_factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
        return PostgresCheckpointRepository(session_factory)

    async def test_create_and_get_checkpoint(self, repo):
        cp = create_test_checkpoint()
        created = await repo.create(cp)
        assert created.id == cp.id

        retrieved = await repo.get(cp.id)
        assert retrieved is not None
        assert retrieved.phase == "research"

    async def test_get_latest(self, repo):
        import asyncio

        cp1 = create_test_checkpoint(phase="research", summary="First")
        await repo.create(cp1)
        await asyncio.sleep(0.01)  # Ensure different timestamps
        cp2 = create_test_checkpoint(phase="analysis", summary="Second")
        await repo.create(cp2)

        latest = await repo.get_latest()
        assert latest is not None
        assert latest.phase == "analysis"

    async def test_list_by_phase(self, repo):
        cp1 = create_test_checkpoint(phase="research")
        cp2 = create_test_checkpoint(phase="analysis")
        await repo.create(cp1)
        await repo.create(cp2)

        cps = await repo.list(phase="research")
        assert len(cps) >= 1
        assert all(c.phase == "research" for c in cps)

    async def test_list_by_user(self, repo):
        user_id = f"user:{uuid.uuid4().hex[:8]}"
        cp = create_test_checkpoint(user_id=user_id)
        await repo.create(cp)

        cps = await repo.list_by_user(user_id)
        assert len(cps) == 1

    async def test_delete_by_user(self, repo):
        user_id = f"user:{uuid.uuid4().hex[:8]}"
        cp1 = create_test_checkpoint(user_id=user_id)
        cp2 = create_test_checkpoint(user_id=user_id)
        await repo.create(cp1)
        await repo.create(cp2)

        count = await repo.delete_by_user(user_id)
        assert count == 2

    async def test_summarize(self, repo):
        cp1 = create_test_checkpoint(phase="research", summary="Did research")
        cp2 = create_test_checkpoint(phase="analysis", summary="Did analysis")
        await repo.create(cp1)
        await repo.create(cp2)

        summary = await repo.summarize()
        assert "research" in summary.lower() or "Research" in summary
        assert "analysis" in summary.lower() or "Analysis" in summary

    async def test_cross_user_isolation(self, repo):
        user_a = f"user:alice-{uuid.uuid4().hex[:8]}"
        user_b = f"user:bob-{uuid.uuid4().hex[:8]}"
        await repo.create(create_test_checkpoint(user_id=user_a, summary="Alice CP"))
        await repo.create(create_test_checkpoint(user_id=user_b, summary="Bob CP"))

        alice_cps = await repo.list_by_user(user_a)
        assert len(alice_cps) == 1
        assert alice_cps[0].summary == "Alice CP"

    async def test_delete_checkpoint(self, repo):
        cp = create_test_checkpoint()
        await repo.create(cp)

        deleted = await repo.delete(cp.id)
        assert deleted is True
        assert await repo.get(cp.id) is None
