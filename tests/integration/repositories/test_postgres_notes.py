"""
Integration Tests for PostgresNotesRepository.

Tests the PostgreSQL implementation of the notes repository
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


def create_test_note(
    user_id: str | None = None,
    category: str = "research",
    content: str = "Test note content",
) -> Note:  # noqa: F821
    from mcp_server_langgraph.memory.notes import Note

    return Note(
        id=f"note-{uuid.uuid4().hex[:8]}",
        content=content,
        category=category,
        tags=["test"],
        user_id=user_id or f"user:{uuid.uuid4().hex[:8]}",
    )


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.xdist_group(name="testpostgresnotesrepo")
@pytest.mark.skip_isolation_check
class TestPostgresNotesRepository:
    """Test PostgresNotesRepository with real PostgreSQL."""

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

        from mcp_server_langgraph.repositories.postgres_notes import PostgresNotesRepository

        async with async_engine.begin() as conn:
            await conn.execute(text("DELETE FROM notes"))

        session_factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
        return PostgresNotesRepository(session_factory)

    async def test_create_and_get_note(self, repo):
        note = create_test_note()
        created = await repo.create(note)
        assert created.id == note.id

        retrieved = await repo.get(note.id)
        assert retrieved is not None
        assert retrieved.content == note.content
        assert retrieved.category == "research"

    async def test_delete_note(self, repo):
        note = create_test_note()
        await repo.create(note)

        deleted = await repo.delete(note.id)
        assert deleted is True

        retrieved = await repo.get(note.id)
        assert retrieved is None

    async def test_list_notes_by_category(self, repo):
        note1 = create_test_note(category="research")
        note2 = create_test_note(category="analysis")
        await repo.create(note1)
        await repo.create(note2)

        notes = await repo.list(category="research")
        assert len(notes) >= 1
        assert all(n.category == "research" for n in notes)

    async def test_list_notes_by_user(self, repo):
        user_id = f"user:{uuid.uuid4().hex[:8]}"
        note = create_test_note(user_id=user_id)
        await repo.create(note)

        notes = await repo.list_by_user(user_id)
        assert len(notes) == 1
        assert notes[0].user_id == user_id

    async def test_delete_by_user(self, repo):
        user_id = f"user:{uuid.uuid4().hex[:8]}"
        note1 = create_test_note(user_id=user_id)
        note2 = create_test_note(user_id=user_id)
        await repo.create(note1)
        await repo.create(note2)

        count = await repo.delete_by_user(user_id)
        assert count == 2

    async def test_cross_user_isolation(self, repo):
        user_a = f"user:alice-{uuid.uuid4().hex[:8]}"
        user_b = f"user:bob-{uuid.uuid4().hex[:8]}"
        note_a = create_test_note(user_id=user_a, content="Alice's note")
        note_b = create_test_note(user_id=user_b, content="Bob's note")
        await repo.create(note_a)
        await repo.create(note_b)

        alice_notes = await repo.list_by_user(user_a)
        assert len(alice_notes) == 1
        assert alice_notes[0].content == "Alice's note"

    async def test_count_notes(self, repo):
        note1 = create_test_note(category="research")
        note2 = create_test_note(category="research")
        note3 = create_test_note(category="analysis")
        await repo.create(note1)
        await repo.create(note2)
        await repo.create(note3)

        count = await repo.count(category="research")
        assert count == 2

    async def test_search_notes(self, repo):
        note = create_test_note(content="quantum computing advances in 2026")
        await repo.create(note)

        results = await repo.search("quantum computing")
        assert len(results) >= 1

    async def test_get_nonexistent_returns_none(self, repo):
        result = await repo.get("nonexistent-id")
        assert result is None

    async def test_delete_nonexistent_returns_false(self, repo):
        result = await repo.delete("nonexistent-id")
        assert result is False
