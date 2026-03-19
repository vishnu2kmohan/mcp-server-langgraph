"""
Tests for Structured Note-Taking & Agentic Memory

PR 11: Implements NOTES.md management and phase summaries
for persistent memory across agent sessions.

Refactored for async repository-backed managers.
"""

from __future__ import annotations

import gc
import warnings
from datetime import UTC, datetime

import pytest

from mcp_server_langgraph.repositories.checkpoint import InMemoryCheckpointRepository
from mcp_server_langgraph.repositories.notes import InMemoryNotesRepository

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.memory
@pytest.mark.xdist_group(name="memory_notes")
class TestNote:
    """Tests for Note data model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_note_creation_with_required_fields(self) -> None:
        """Test creating a note with required fields."""
        from mcp_server_langgraph.memory.notes import Note

        note = Note(
            id="note-1",
            content="This is a test note",
        )

        assert note.id == "note-1"
        assert note.content == "This is a test note"
        assert note.created_at is not None
        assert note.tags == []
        assert note.category == "general"

    def test_note_creation_with_all_fields(self) -> None:
        """Test creating a note with all fields."""
        from mcp_server_langgraph.memory.notes import Note

        now = datetime.now(UTC)
        note = Note(
            id="note-2",
            content="Complete note",
            category="architecture",
            tags=["design", "decisions"],
            created_at=now,
            metadata={"priority": "high"},
        )

        assert note.id == "note-2"
        assert note.content == "Complete note"
        assert note.category == "architecture"
        assert note.tags == ["design", "decisions"]
        assert note.created_at == now
        assert note.metadata["priority"] == "high"

    def test_note_to_markdown(self) -> None:
        """Test converting note to markdown format."""
        from mcp_server_langgraph.memory.notes import Note

        note = Note(
            id="note-3",
            content="Important finding about X",
            category="research",
            tags=["important"],
        )

        markdown = note.to_markdown()

        assert "## note-3" in markdown
        assert "Important finding about X" in markdown
        assert "research" in markdown
        assert "important" in markdown

    def test_note_creation_with_session_and_user(self) -> None:
        """Test creating a note with session_id and user_id for Phase 4 refs."""
        from mcp_server_langgraph.memory.notes import Note

        note = Note(
            id="note-session-1",
            content="Session-scoped note",
            session_id="session-abc-123",
            user_id="user-xyz-456",
        )

        assert note.session_id == "session-abc-123"
        assert note.user_id == "user-xyz-456"

    def test_note_creation_with_title_and_slug(self) -> None:
        """Test creating a note with title and slug for friendly refs."""
        from mcp_server_langgraph.memory.notes import Note

        note = Note(
            id="note-titled-1",
            content="Note with title",
            title="Architecture Decision",
            slug="architecture-decision",
        )

        assert note.title == "Architecture Decision"
        assert note.slug == "architecture-decision"

    def test_note_optional_fields_default_to_none(self) -> None:
        """Test that session_id, user_id, title, slug default to None."""
        from mcp_server_langgraph.memory.notes import Note

        note = Note(
            id="note-minimal",
            content="Minimal note",
        )

        assert note.session_id is None
        assert note.user_id is None
        assert note.title is None
        assert note.slug is None

    def test_note_with_all_phase4_fields(self) -> None:
        """Test creating a note with all Phase 4 prerequisite fields."""
        from mcp_server_langgraph.memory.notes import Note

        now = datetime.now(UTC)
        note = Note(
            id="note-full",
            content="Full Phase 4 note",
            category="memory",
            tags=["phase4", "refs"],
            created_at=now,
            metadata={"source": "test"},
            session_id="session-123",
            user_id="user-456",
            title="Full Note Title",
            slug="full-note-title",
        )

        assert note.id == "note-full"
        assert note.content == "Full Phase 4 note"
        assert note.category == "memory"
        assert note.session_id == "session-123"
        assert note.user_id == "user-456"
        assert note.title == "Full Note Title"
        assert note.slug == "full-note-title"

    def test_note_to_markdown_includes_title_when_present(self) -> None:
        """Test that markdown output includes title when provided."""
        from mcp_server_langgraph.memory.notes import Note

        note = Note(
            id="note-with-title",
            content="Content here",
            title="My Custom Title",
        )

        markdown = note.to_markdown()

        # Title should be used in heading instead of ID
        assert "My Custom Title" in markdown


@pytest.mark.unit
@pytest.mark.memory
@pytest.mark.xdist_group(name="memory_notes")
class TestNotesManager:
    """Tests for NotesManager with repository backend."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_notes_manager_initialization(self) -> None:
        """Test initializing notes manager with empty repository."""
        from mcp_server_langgraph.memory.notes import NotesManager

        manager = NotesManager(repository=InMemoryNotesRepository())

        notes = await manager.list_notes()
        assert len(notes) == 0

    async def test_add_note_persists_content(self) -> None:
        """Test adding a note stores it in repository."""
        from mcp_server_langgraph.memory.notes import NotesManager

        manager = NotesManager(repository=InMemoryNotesRepository())

        note = await manager.add_note(
            content="First note content",
            category="general",
        )

        assert note.id is not None
        assert note.content == "First note content"
        notes = await manager.list_notes()
        assert len(notes) == 1

    async def test_get_note_by_id(self) -> None:
        """Test retrieving a note by ID."""
        from mcp_server_langgraph.memory.notes import NotesManager

        manager = NotesManager(repository=InMemoryNotesRepository())

        note = await manager.add_note(content="Test content")
        retrieved = await manager.get_note(note.id)

        assert retrieved is not None
        assert retrieved.id == note.id
        assert retrieved.content == "Test content"

    async def test_get_nonexistent_note_returns_none(self) -> None:
        """Test getting a nonexistent note returns None."""
        from mcp_server_langgraph.memory.notes import NotesManager

        manager = NotesManager(repository=InMemoryNotesRepository())

        result = await manager.get_note("nonexistent-id")

        assert result is None

    async def test_delete_note_removes_from_storage(self) -> None:
        """Test deleting a note."""
        from mcp_server_langgraph.memory.notes import NotesManager

        manager = NotesManager(repository=InMemoryNotesRepository())

        note = await manager.add_note(content="To be deleted")
        notes = await manager.list_notes()
        assert len(notes) == 1

        await manager.delete_note(note.id)

        notes = await manager.list_notes()
        assert len(notes) == 0
        assert await manager.get_note(note.id) is None

    async def test_list_notes_by_category(self) -> None:
        """Test listing notes by category."""
        from mcp_server_langgraph.memory.notes import NotesManager

        manager = NotesManager(repository=InMemoryNotesRepository())

        await manager.add_note(content="Research note 1", category="research")
        await manager.add_note(content="Research note 2", category="research")
        await manager.add_note(content="General note", category="general")

        research_notes = await manager.list_notes(category="research")
        general_notes = await manager.list_notes(category="general")

        assert len(research_notes) == 2
        assert len(general_notes) == 1

    async def test_search_notes_by_content(self) -> None:
        """Test searching notes by content."""
        from mcp_server_langgraph.memory.notes import NotesManager

        manager = NotesManager(repository=InMemoryNotesRepository())

        await manager.add_note(content="Python is great")
        await manager.add_note(content="JavaScript is also useful")
        await manager.add_note(content="Python and JavaScript together")

        results = await manager.search("Python")

        assert len(results) == 2

    async def test_clear_all_notes(self) -> None:
        """Test clearing all notes."""
        from mcp_server_langgraph.memory.notes import NotesManager

        manager = NotesManager(repository=InMemoryNotesRepository())

        await manager.add_note(content="Note 1")
        await manager.add_note(content="Note 2")
        notes = await manager.list_notes()
        assert len(notes) == 2

        await manager.clear()

        notes = await manager.list_notes()
        assert len(notes) == 0

    async def test_add_note_with_session_and_user(self) -> None:
        """Test adding a note with session_id and user_id."""
        from mcp_server_langgraph.memory.notes import NotesManager

        manager = NotesManager(repository=InMemoryNotesRepository())

        note = await manager.add_note(
            content="Session-bound note",
            session_id="session-abc",
            user_id="user-xyz",
        )

        assert note.session_id == "session-abc"
        assert note.user_id == "user-xyz"

    async def test_add_note_with_title_and_slug(self) -> None:
        """Test adding a note with title and slug."""
        from mcp_server_langgraph.memory.notes import NotesManager

        manager = NotesManager(repository=InMemoryNotesRepository())

        note = await manager.add_note(
            content="Titled note content",
            title="My Important Note",
            slug="my-important-note",
        )

        assert note.title == "My Important Note"
        assert note.slug == "my-important-note"

    async def test_list_notes_by_session(self) -> None:
        """Test listing notes filtered by session_id."""
        from mcp_server_langgraph.memory.notes import NotesManager

        manager = NotesManager(repository=InMemoryNotesRepository())

        await manager.add_note(content="Session 1 note 1", session_id="session-1")
        await manager.add_note(content="Session 1 note 2", session_id="session-1")
        await manager.add_note(content="Session 2 note", session_id="session-2")
        await manager.add_note(content="No session note")

        session1_notes = await manager.list_notes(session_id="session-1")
        session2_notes = await manager.list_notes(session_id="session-2")

        assert len(session1_notes) == 2
        assert len(session2_notes) == 1

    async def test_list_notes_by_user(self) -> None:
        """Test listing notes filtered by user_id."""
        from mcp_server_langgraph.memory.notes import NotesManager

        manager = NotesManager(repository=InMemoryNotesRepository())

        await manager.add_note(content="User A note 1", user_id="user-a")
        await manager.add_note(content="User A note 2", user_id="user-a")
        await manager.add_note(content="User B note", user_id="user-b")

        user_a_notes = await manager.list_notes(user_id="user-a")
        user_b_notes = await manager.list_notes(user_id="user-b")

        assert len(user_a_notes) == 2
        assert len(user_b_notes) == 1

    def test_persist_emits_deprecation_warning(self) -> None:
        """Test that persist() emits a DeprecationWarning."""
        from mcp_server_langgraph.memory.notes import NotesManager

        manager = NotesManager(repository=InMemoryNotesRepository())

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            manager.persist()
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)

    def test_load_emits_deprecation_warning(self) -> None:
        """Test that load() emits a DeprecationWarning."""
        from mcp_server_langgraph.memory.notes import NotesManager

        manager = NotesManager(repository=InMemoryNotesRepository())

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            manager.load()
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)


@pytest.mark.unit
@pytest.mark.memory
@pytest.mark.xdist_group(name="memory_checkpoints")
class TestCheckpoint:
    """Tests for Checkpoint data model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_checkpoint_creation_saves_state(self) -> None:
        """Test creating a checkpoint."""
        from mcp_server_langgraph.memory.checkpoints import Checkpoint

        checkpoint = Checkpoint(
            id="checkpoint-1",
            phase="implementation",
            summary="Completed Phase 1 with 10 features",
        )

        assert checkpoint.id == "checkpoint-1"
        assert checkpoint.phase == "implementation"
        assert checkpoint.summary == "Completed Phase 1 with 10 features"
        assert checkpoint.created_at is not None
        assert checkpoint.artifacts == []

    def test_checkpoint_with_artifacts(self) -> None:
        """Test checkpoint with artifact references."""
        from mcp_server_langgraph.memory.checkpoints import Checkpoint

        checkpoint = Checkpoint(
            id="checkpoint-2",
            phase="testing",
            summary="All tests passing",
            artifacts=["test_results.json", "coverage.html"],
        )

        assert len(checkpoint.artifacts) == 2
        assert "test_results.json" in checkpoint.artifacts


@pytest.mark.unit
@pytest.mark.memory
@pytest.mark.xdist_group(name="memory_checkpoints")
class TestCheckpointManager:
    """Tests for CheckpointManager with repository backend."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_checkpoint_manager_initialization(self) -> None:
        """Test initializing checkpoint manager with empty repository."""
        from mcp_server_langgraph.memory.checkpoints import CheckpointManager

        manager = CheckpointManager(repository=InMemoryCheckpointRepository())

        checkpoints = await manager.list_checkpoints()
        assert len(checkpoints) == 0

    async def test_create_checkpoint_returns_id(self) -> None:
        """Test creating a checkpoint."""
        from mcp_server_langgraph.memory.checkpoints import CheckpointManager

        manager = CheckpointManager(repository=InMemoryCheckpointRepository())

        checkpoint = await manager.create_checkpoint(
            phase="phase-1",
            summary="Completed initial setup",
        )

        assert checkpoint.id is not None
        assert checkpoint.phase == "phase-1"
        assert checkpoint.summary == "Completed initial setup"

    async def test_get_checkpoint_by_id(self) -> None:
        """Test retrieving a checkpoint by ID."""
        from mcp_server_langgraph.memory.checkpoints import CheckpointManager

        manager = CheckpointManager(repository=InMemoryCheckpointRepository())

        checkpoint = await manager.create_checkpoint(
            phase="phase-1",
            summary="Test checkpoint",
        )
        retrieved = await manager.get_checkpoint(checkpoint.id)

        assert retrieved is not None
        assert retrieved.id == checkpoint.id

    async def test_get_latest_checkpoint(self) -> None:
        """Test getting the latest checkpoint."""
        import time

        from mcp_server_langgraph.memory.checkpoints import CheckpointManager

        manager = CheckpointManager(repository=InMemoryCheckpointRepository())

        await manager.create_checkpoint(phase="phase-1", summary="First")
        time.sleep(0.01)  # Ensure different timestamps
        latest = await manager.create_checkpoint(phase="phase-2", summary="Second")

        retrieved = await manager.get_latest_checkpoint()

        assert retrieved is not None
        assert retrieved.id == latest.id
        assert retrieved.phase == "phase-2"

    async def test_list_checkpoints_by_phase(self) -> None:
        """Test listing checkpoints by phase."""
        from mcp_server_langgraph.memory.checkpoints import CheckpointManager

        manager = CheckpointManager(repository=InMemoryCheckpointRepository())

        await manager.create_checkpoint(phase="implementation", summary="Impl 1")
        await manager.create_checkpoint(phase="testing", summary="Test 1")
        await manager.create_checkpoint(phase="implementation", summary="Impl 2")

        impl_checkpoints = await manager.list_checkpoints(phase="implementation")
        test_checkpoints = await manager.list_checkpoints(phase="testing")

        assert len(impl_checkpoints) == 2
        assert len(test_checkpoints) == 1

    async def test_delete_checkpoint_removes_state(self) -> None:
        """Test deleting a checkpoint."""
        from mcp_server_langgraph.memory.checkpoints import CheckpointManager

        manager = CheckpointManager(repository=InMemoryCheckpointRepository())

        checkpoint = await manager.create_checkpoint(phase="test", summary="To delete")
        checkpoints = await manager.list_checkpoints()
        assert len(checkpoints) == 1

        await manager.delete_checkpoint(checkpoint.id)

        checkpoints = await manager.list_checkpoints()
        assert len(checkpoints) == 0

    async def test_summarize_session_generates_overview(self) -> None:
        """Test generating session summary from checkpoints."""
        from mcp_server_langgraph.memory.checkpoints import CheckpointManager

        manager = CheckpointManager(repository=InMemoryCheckpointRepository())

        await manager.create_checkpoint(phase="research", summary="Researched architecture")
        await manager.create_checkpoint(phase="implementation", summary="Implemented core")
        await manager.create_checkpoint(phase="testing", summary="All tests pass")

        summary = await manager.summarize_session()

        assert "research" in summary.lower()
        assert "implementation" in summary.lower()
        assert "testing" in summary.lower()

    def test_persist_emits_deprecation_warning(self) -> None:
        """Test that persist() emits a DeprecationWarning."""
        from mcp_server_langgraph.memory.checkpoints import CheckpointManager

        manager = CheckpointManager(repository=InMemoryCheckpointRepository())

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            manager.persist()
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)

    def test_load_emits_deprecation_warning(self) -> None:
        """Test that load() emits a DeprecationWarning."""
        from mcp_server_langgraph.memory.checkpoints import CheckpointManager

        manager = CheckpointManager(repository=InMemoryCheckpointRepository())

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            manager.load()
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)


@pytest.mark.unit
@pytest.mark.memory
class TestNotesManagerSearch:
    """Additional tests for notes search functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_search_empty_query_returns_all_notes(self) -> None:
        """Test that empty search query returns all notes."""
        from mcp_server_langgraph.memory.notes import NotesManager

        manager = NotesManager(repository=InMemoryNotesRepository())

        await manager.add_note(content="Note 1")
        await manager.add_note(content="Note 2")
        await manager.add_note(content="Note 3")

        results = await manager.search("")

        assert len(results) == 3

    async def test_search_case_insensitive(self) -> None:
        """Test that search is case insensitive."""
        from mcp_server_langgraph.memory.notes import NotesManager

        manager = NotesManager(repository=InMemoryNotesRepository())

        await manager.add_note(content="PYTHON is great")
        await manager.add_note(content="python is awesome")
        await manager.add_note(content="Python is versatile")

        results = await manager.search("python")
        assert len(results) == 3

        results = await manager.search("PYTHON")
        assert len(results) == 3

    async def test_search_no_matches(self) -> None:
        """Test search with no matching notes."""
        from mcp_server_langgraph.memory.notes import NotesManager

        manager = NotesManager(repository=InMemoryNotesRepository())

        await manager.add_note(content="Python is great")
        await manager.add_note(content="JavaScript is useful")

        results = await manager.search("Rust")

        assert len(results) == 0

    async def test_search_partial_match(self) -> None:
        """Test search matches partial words."""
        from mcp_server_langgraph.memory.notes import NotesManager

        manager = NotesManager(repository=InMemoryNotesRepository())

        await manager.add_note(content="Programming is fun")
        await manager.add_note(content="Reprogramming the system")

        results = await manager.search("gram")

        assert len(results) == 2

    async def test_search_with_special_characters(self) -> None:
        """Test search handles special characters."""
        from mcp_server_langgraph.memory.notes import NotesManager

        manager = NotesManager(repository=InMemoryNotesRepository())

        await manager.add_note(content="Error: FileNotFoundError at line 42")
        await manager.add_note(content="Success: All tests pass!")

        results = await manager.search("Error:")

        assert len(results) == 1
        assert "FileNotFoundError" in results[0].content


@pytest.mark.unit
@pytest.mark.memory
class TestNotesManagerLargeContent:
    """Tests for handling large notes and many notes."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_large_note_content(self) -> None:
        """Test handling notes with large content."""
        from mcp_server_langgraph.memory.notes import NotesManager

        manager = NotesManager(repository=InMemoryNotesRepository())

        large_content = "Lorem ipsum " * 1000  # ~12KB
        note = await manager.add_note(content=large_content)

        loaded = await manager.get_note(note.id)
        assert loaded is not None
        assert len(loaded.content) == len(large_content)

    async def test_many_notes_handled_efficiently(self) -> None:
        """Test handling many notes."""
        from mcp_server_langgraph.memory.notes import NotesManager

        manager = NotesManager(repository=InMemoryNotesRepository())

        for i in range(100):
            await manager.add_note(
                content=f"Note number {i}",
                category=f"category-{i % 10}",
            )

        notes = await manager.list_notes()
        assert len(notes) == 100

    async def test_note_with_multiline_content(self) -> None:
        """Test notes with multiline content."""
        from mcp_server_langgraph.memory.notes import NotesManager

        manager = NotesManager(repository=InMemoryNotesRepository())

        multiline = """First line
Second line
Third line with code:
```python
def hello():
    print("Hello")
```
End of note"""

        note = await manager.add_note(content=multiline)

        loaded = await manager.get_note(note.id)
        assert loaded is not None
        assert "First line" in loaded.content
        assert "def hello" in loaded.content

    async def test_note_with_markdown_formatting(self) -> None:
        """Test notes with markdown formatting."""
        from mcp_server_langgraph.memory.notes import NotesManager

        manager = NotesManager(repository=InMemoryNotesRepository())

        markdown_content = """# Header
## Subheader

* Bullet 1
* Bullet 2

1. Numbered
2. List

**Bold** and *italic* text

> Blockquote

[Link](https://example.com)
"""

        note = await manager.add_note(content=markdown_content)

        loaded = await manager.get_note(note.id)
        assert loaded is not None
        assert "# Header" in loaded.content
        assert "**Bold**" in loaded.content


@pytest.mark.unit
@pytest.mark.memory
class TestNotesManagerMarkdownRendering:
    """Tests for Note.to_markdown() rendering."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_note_with_tags_in_markdown(self) -> None:
        """Test notes with tags are properly formatted in markdown."""
        from mcp_server_langgraph.memory.notes import Note

        note = Note(
            id="note-tags",
            content="Tagged note",
            tags=["important", "architecture", "review"],
        )

        markdown = note.to_markdown()

        assert "important" in markdown
        assert "architecture" in markdown
        assert "review" in markdown
        assert "Tags:" in markdown

    def test_note_without_tags_omits_tags_line(self) -> None:
        """Test notes without tags don't include empty Tags line."""
        from mcp_server_langgraph.memory.notes import Note

        note = Note(
            id="note-no-tags",
            content="No tags here",
        )

        markdown = note.to_markdown()

        # Tags line should not appear for empty tags
        lines = markdown.split("\n")
        tags_lines = [line for line in lines if line.startswith("**Tags:**")]
        assert len(tags_lines) == 0

    async def test_delete_nonexistent_note_no_error(self) -> None:
        """Test deleting nonexistent note doesn't raise error."""
        from mcp_server_langgraph.memory.notes import NotesManager

        manager = NotesManager(repository=InMemoryNotesRepository())

        # Should not raise
        await manager.delete_note("nonexistent-note-id")

        notes = await manager.list_notes()
        assert len(notes) == 0
