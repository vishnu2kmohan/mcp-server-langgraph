"""
Tests for Notes Repository

TDD: These tests define the contract for storing and retrieving notes.
Supports both InMemory (testing) and Postgres (production) implementations.
"""

from __future__ import annotations

import gc
from datetime import UTC, datetime, timedelta

import pytest

from mcp_server_langgraph.memory.notes import Note

pytestmark = [pytest.mark.unit, pytest.mark.repository]


def _make_note(
    note_id: str = "note-test-1",
    content: str = "Test note content",
    category: str = "general",
    tags: list[str] | None = None,
    session_id: str | None = None,
    user_id: str | None = None,
    created_at: datetime | None = None,
    title: str | None = None,
    slug: str | None = None,
) -> Note:
    """Create a test note with sensible defaults."""
    return Note(
        id=note_id,
        content=content,
        category=category,
        tags=tags or [],
        session_id=session_id,
        user_id=user_id,
        created_at=created_at or datetime.now(UTC),
        title=title,
        slug=slug,
    )


@pytest.fixture
def in_memory_repo():
    """Create an in-memory notes repository for testing."""
    from mcp_server_langgraph.repositories.notes import InMemoryNotesRepository

    return InMemoryNotesRepository()


class TestNotesRepositoryInterface:
    """Tests for NotesRepository abstract interface."""

    def teardown_method(self) -> None:
        gc.collect()

    def test_repository_base_class_exists(self) -> None:
        from mcp_server_langgraph.repositories.notes import NotesRepository

        assert NotesRepository is not None

    def test_repository_has_create_method(self) -> None:
        from mcp_server_langgraph.repositories.notes import NotesRepository

        assert hasattr(NotesRepository, "create")

    def test_repository_has_get_method(self) -> None:
        from mcp_server_langgraph.repositories.notes import NotesRepository

        assert hasattr(NotesRepository, "get")

    def test_repository_has_delete_method(self) -> None:
        from mcp_server_langgraph.repositories.notes import NotesRepository

        assert hasattr(NotesRepository, "delete")

    def test_repository_has_list_method(self) -> None:
        from mcp_server_langgraph.repositories.notes import NotesRepository

        assert hasattr(NotesRepository, "list")

    def test_repository_has_count_method(self) -> None:
        from mcp_server_langgraph.repositories.notes import NotesRepository

        assert hasattr(NotesRepository, "count")

    def test_repository_has_search_method(self) -> None:
        from mcp_server_langgraph.repositories.notes import NotesRepository

        assert hasattr(NotesRepository, "search")

    def test_repository_has_clear_method(self) -> None:
        from mcp_server_langgraph.repositories.notes import NotesRepository

        assert hasattr(NotesRepository, "clear")

    def test_repository_has_list_by_user_method(self) -> None:
        from mcp_server_langgraph.repositories.notes import NotesRepository

        assert hasattr(NotesRepository, "list_by_user")

    def test_repository_has_delete_by_user_method(self) -> None:
        from mcp_server_langgraph.repositories.notes import NotesRepository

        assert hasattr(NotesRepository, "delete_by_user")

    def test_abstract_methods_defined(self) -> None:
        from mcp_server_langgraph.repositories.notes import NotesRepository

        expected = {"create", "get", "delete", "list", "count", "search", "clear", "list_by_user", "delete_by_user"}
        assert expected.issubset(NotesRepository.__abstractmethods__)


class TestInMemoryNotesRepository:
    """Tests for InMemoryNotesRepository."""

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.mark.asyncio
    async def test_create_stores_note(self, in_memory_repo) -> None:
        note = _make_note()
        result = await in_memory_repo.create(note)

        assert result.id == note.id
        assert result.content == note.content

    @pytest.mark.asyncio
    async def test_get_retrieves_note(self, in_memory_repo) -> None:
        note = _make_note()
        await in_memory_repo.create(note)

        result = await in_memory_repo.get(note.id)

        assert result is not None
        assert result.id == note.id
        assert result.content == note.content

    @pytest.mark.asyncio
    async def test_get_returns_none_for_missing(self, in_memory_repo) -> None:
        result = await in_memory_repo.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_removes_note(self, in_memory_repo) -> None:
        note = _make_note()
        await in_memory_repo.create(note)

        result = await in_memory_repo.delete(note.id)

        assert result is True
        assert await in_memory_repo.get(note.id) is None

    @pytest.mark.asyncio
    async def test_delete_returns_false_for_missing(self, in_memory_repo) -> None:
        result = await in_memory_repo.delete("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_list_returns_all_notes(self, in_memory_repo) -> None:
        for i in range(3):
            await in_memory_repo.create(_make_note(note_id=f"note-{i}"))

        notes = await in_memory_repo.list()
        assert len(notes) == 3

    @pytest.mark.asyncio
    async def test_list_filters_by_category(self, in_memory_repo) -> None:
        await in_memory_repo.create(_make_note(note_id="n1", category="research"))
        await in_memory_repo.create(_make_note(note_id="n2", category="research"))
        await in_memory_repo.create(_make_note(note_id="n3", category="general"))

        notes = await in_memory_repo.list(category="research")
        assert len(notes) == 2
        assert all(n.category == "research" for n in notes)

    @pytest.mark.asyncio
    async def test_list_filters_by_session_id(self, in_memory_repo) -> None:
        await in_memory_repo.create(_make_note(note_id="n1", session_id="sess-A"))
        await in_memory_repo.create(_make_note(note_id="n2", session_id="sess-A"))
        await in_memory_repo.create(_make_note(note_id="n3", session_id="sess-B"))

        notes = await in_memory_repo.list(session_id="sess-A")
        assert len(notes) == 2

    @pytest.mark.asyncio
    async def test_list_filters_by_user_id(self, in_memory_repo) -> None:
        await in_memory_repo.create(_make_note(note_id="n1", user_id="user-A"))
        await in_memory_repo.create(_make_note(note_id="n2", user_id="user-B"))

        notes = await in_memory_repo.list(user_id="user-A")
        assert len(notes) == 1
        assert notes[0].user_id == "user-A"

    @pytest.mark.asyncio
    async def test_list_with_limit(self, in_memory_repo) -> None:
        for i in range(5):
            await in_memory_repo.create(_make_note(note_id=f"note-{i}"))

        notes = await in_memory_repo.list(limit=3)
        assert len(notes) == 3

    @pytest.mark.asyncio
    async def test_list_with_offset(self, in_memory_repo) -> None:
        base_time = datetime(2025, 1, 1, tzinfo=UTC)
        for i in range(5):
            await in_memory_repo.create(_make_note(note_id=f"note-{i}", created_at=base_time + timedelta(seconds=i)))

        notes = await in_memory_repo.list(offset=2)
        assert len(notes) == 3

    @pytest.mark.asyncio
    async def test_list_sorted_by_created_at_desc(self, in_memory_repo) -> None:
        base_time = datetime(2025, 1, 1, tzinfo=UTC)
        await in_memory_repo.create(_make_note(note_id="oldest", created_at=base_time))
        await in_memory_repo.create(_make_note(note_id="middle", created_at=base_time + timedelta(hours=1)))
        await in_memory_repo.create(_make_note(note_id="newest", created_at=base_time + timedelta(hours=2)))

        notes = await in_memory_repo.list()
        assert notes[0].id == "newest"
        assert notes[2].id == "oldest"

    @pytest.mark.asyncio
    async def test_count_returns_total(self, in_memory_repo) -> None:
        for i in range(3):
            await in_memory_repo.create(_make_note(note_id=f"note-{i}"))

        count = await in_memory_repo.count()
        assert count == 3

    @pytest.mark.asyncio
    async def test_count_with_filters(self, in_memory_repo) -> None:
        await in_memory_repo.create(_make_note(note_id="n1", category="research", user_id="u1"))
        await in_memory_repo.create(_make_note(note_id="n2", category="research", user_id="u2"))
        await in_memory_repo.create(_make_note(note_id="n3", category="general", user_id="u1"))

        assert await in_memory_repo.count(category="research") == 2
        assert await in_memory_repo.count(user_id="u1") == 2
        assert await in_memory_repo.count(category="research", user_id="u1") == 1

    @pytest.mark.asyncio
    async def test_search_by_content(self, in_memory_repo) -> None:
        await in_memory_repo.create(_make_note(note_id="n1", content="Python async patterns"))
        await in_memory_repo.create(_make_note(note_id="n2", content="JavaScript promises"))
        await in_memory_repo.create(_make_note(note_id="n3", content="Python type hints"))

        results = await in_memory_repo.search("Python")
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_search_case_insensitive(self, in_memory_repo) -> None:
        await in_memory_repo.create(_make_note(note_id="n1", content="FastAPI framework"))

        results = await in_memory_repo.search("fastapi")
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_search_with_limit(self, in_memory_repo) -> None:
        for i in range(5):
            await in_memory_repo.create(_make_note(note_id=f"n{i}", content="common term"))

        results = await in_memory_repo.search("common", limit=3)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_search_empty_query_returns_all(self, in_memory_repo) -> None:
        await in_memory_repo.create(_make_note(note_id="n1"))
        await in_memory_repo.create(_make_note(note_id="n2"))

        results = await in_memory_repo.search("")
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_clear_removes_all(self, in_memory_repo) -> None:
        for i in range(3):
            await in_memory_repo.create(_make_note(note_id=f"note-{i}"))

        await in_memory_repo.clear()

        notes = await in_memory_repo.list()
        assert len(notes) == 0

    @pytest.mark.asyncio
    async def test_list_by_user(self, in_memory_repo) -> None:
        await in_memory_repo.create(_make_note(note_id="n1", user_id="user-A"))
        await in_memory_repo.create(_make_note(note_id="n2", user_id="user-A"))
        await in_memory_repo.create(_make_note(note_id="n3", user_id="user-B"))

        notes = await in_memory_repo.list_by_user("user-A")
        assert len(notes) == 2
        assert all(n.user_id == "user-A" for n in notes)

    @pytest.mark.asyncio
    async def test_delete_by_user(self, in_memory_repo) -> None:
        await in_memory_repo.create(_make_note(note_id="n1", user_id="user-A"))
        await in_memory_repo.create(_make_note(note_id="n2", user_id="user-A"))
        await in_memory_repo.create(_make_note(note_id="n3", user_id="user-B"))

        count = await in_memory_repo.delete_by_user("user-A")

        assert count == 2
        assert await in_memory_repo.get("n1") is None
        assert await in_memory_repo.get("n2") is None
        assert await in_memory_repo.get("n3") is not None


class TestNotesRepositoryCrossUserAuthorization:
    """Negative cross-user authorization tests."""

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.mark.asyncio
    async def test_list_by_user_does_not_return_other_users_notes(self, in_memory_repo) -> None:
        await in_memory_repo.create(_make_note(note_id="n1", user_id="user-A", content="Secret A"))
        await in_memory_repo.create(_make_note(note_id="n2", user_id="user-B", content="Secret B"))

        notes = await in_memory_repo.list_by_user("user-A")
        assert len(notes) == 1
        assert notes[0].user_id == "user-A"
        assert all(n.user_id != "user-B" for n in notes)

    @pytest.mark.asyncio
    async def test_delete_by_user_does_not_delete_other_users_notes(self, in_memory_repo) -> None:
        await in_memory_repo.create(_make_note(note_id="n1", user_id="user-A"))
        await in_memory_repo.create(_make_note(note_id="n2", user_id="user-B"))

        await in_memory_repo.delete_by_user("user-A")

        assert await in_memory_repo.get("n2") is not None

    @pytest.mark.asyncio
    async def test_list_filtered_by_user_isolates_users(self, in_memory_repo) -> None:
        await in_memory_repo.create(_make_note(note_id="n1", user_id="user-A", category="research"))
        await in_memory_repo.create(_make_note(note_id="n2", user_id="user-B", category="research"))

        notes = await in_memory_repo.list(user_id="user-A", category="research")
        assert len(notes) == 1
        assert notes[0].user_id == "user-A"
