"""
Tests for Structured Note-Taking & Agentic Memory

PR 11: Implements NOTES.md management and phase summaries
for persistent memory across agent sessions.
"""

from __future__ import annotations

import gc
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

pytestmark = pytest.mark.unit

if TYPE_CHECKING:
    pass


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


@pytest.mark.unit
@pytest.mark.memory
@pytest.mark.xdist_group(name="memory_notes")
class TestNotesManager:
    """Tests for NotesManager."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_notes_manager_initialization(self, tmp_path: Path) -> None:
        """Test initializing notes manager."""
        from mcp_server_langgraph.memory.notes import NotesManager

        notes_file = tmp_path / "NOTES.md"
        manager = NotesManager(notes_path=notes_file)

        assert manager.notes_path == notes_file
        assert len(manager.list_notes()) == 0

    def test_add_note(self, tmp_path: Path) -> None:
        """Test adding a note."""
        from mcp_server_langgraph.memory.notes import NotesManager

        notes_file = tmp_path / "NOTES.md"
        manager = NotesManager(notes_path=notes_file)

        note = manager.add_note(
            content="First note content",
            category="general",
        )

        assert note.id is not None
        assert note.content == "First note content"
        assert len(manager.list_notes()) == 1

    def test_get_note_by_id(self, tmp_path: Path) -> None:
        """Test retrieving a note by ID."""
        from mcp_server_langgraph.memory.notes import NotesManager

        notes_file = tmp_path / "NOTES.md"
        manager = NotesManager(notes_path=notes_file)

        note = manager.add_note(content="Test content")
        retrieved = manager.get_note(note.id)

        assert retrieved is not None
        assert retrieved.id == note.id
        assert retrieved.content == "Test content"

    def test_get_nonexistent_note_returns_none(self, tmp_path: Path) -> None:
        """Test getting a nonexistent note returns None."""
        from mcp_server_langgraph.memory.notes import NotesManager

        notes_file = tmp_path / "NOTES.md"
        manager = NotesManager(notes_path=notes_file)

        result = manager.get_note("nonexistent-id")

        assert result is None

    def test_delete_note(self, tmp_path: Path) -> None:
        """Test deleting a note."""
        from mcp_server_langgraph.memory.notes import NotesManager

        notes_file = tmp_path / "NOTES.md"
        manager = NotesManager(notes_path=notes_file)

        note = manager.add_note(content="To be deleted")
        assert len(manager.list_notes()) == 1

        manager.delete_note(note.id)

        assert len(manager.list_notes()) == 0
        assert manager.get_note(note.id) is None

    def test_list_notes_by_category(self, tmp_path: Path) -> None:
        """Test listing notes by category."""
        from mcp_server_langgraph.memory.notes import NotesManager

        notes_file = tmp_path / "NOTES.md"
        manager = NotesManager(notes_path=notes_file)

        manager.add_note(content="Research note 1", category="research")
        manager.add_note(content="Research note 2", category="research")
        manager.add_note(content="General note", category="general")

        research_notes = manager.list_notes(category="research")
        general_notes = manager.list_notes(category="general")

        assert len(research_notes) == 2
        assert len(general_notes) == 1

    def test_search_notes_by_content(self, tmp_path: Path) -> None:
        """Test searching notes by content."""
        from mcp_server_langgraph.memory.notes import NotesManager

        notes_file = tmp_path / "NOTES.md"
        manager = NotesManager(notes_path=notes_file)

        manager.add_note(content="Python is great")
        manager.add_note(content="JavaScript is also useful")
        manager.add_note(content="Python and JavaScript together")

        results = manager.search("Python")

        assert len(results) == 2

    def test_persist_notes_to_file(self, tmp_path: Path) -> None:
        """Test persisting notes to NOTES.md file."""
        from mcp_server_langgraph.memory.notes import NotesManager

        notes_file = tmp_path / "NOTES.md"
        manager = NotesManager(notes_path=notes_file)

        manager.add_note(content="Persisted note", category="test")
        manager.persist()

        assert notes_file.exists()
        content = notes_file.read_text()
        assert "Persisted note" in content

    def test_load_notes_from_file(self, tmp_path: Path) -> None:
        """Test loading notes from existing NOTES.md file."""
        from mcp_server_langgraph.memory.notes import NotesManager

        notes_file = tmp_path / "NOTES.md"
        # Create manager, add note, persist
        manager1 = NotesManager(notes_path=notes_file)
        manager1.add_note(content="Saved note", category="test")
        manager1.persist()

        # Create new manager that loads from file
        manager2 = NotesManager(notes_path=notes_file)
        manager2.load()

        notes = manager2.list_notes()
        assert len(notes) == 1
        assert notes[0].content == "Saved note"

    def test_clear_all_notes(self, tmp_path: Path) -> None:
        """Test clearing all notes."""
        from mcp_server_langgraph.memory.notes import NotesManager

        notes_file = tmp_path / "NOTES.md"
        manager = NotesManager(notes_path=notes_file)

        manager.add_note(content="Note 1")
        manager.add_note(content="Note 2")
        assert len(manager.list_notes()) == 2

        manager.clear()

        assert len(manager.list_notes()) == 0


@pytest.mark.unit
@pytest.mark.memory
@pytest.mark.xdist_group(name="memory_checkpoints")
class TestCheckpoint:
    """Tests for Checkpoint data model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_checkpoint_creation(self) -> None:
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
    """Tests for CheckpointManager."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_checkpoint_manager_initialization(self, tmp_path: Path) -> None:
        """Test initializing checkpoint manager."""
        from mcp_server_langgraph.memory.checkpoints import CheckpointManager

        manager = CheckpointManager(storage_dir=tmp_path)

        assert manager.storage_dir == tmp_path
        assert len(manager.list_checkpoints()) == 0

    def test_create_checkpoint(self, tmp_path: Path) -> None:
        """Test creating a checkpoint."""
        from mcp_server_langgraph.memory.checkpoints import CheckpointManager

        manager = CheckpointManager(storage_dir=tmp_path)

        checkpoint = manager.create_checkpoint(
            phase="phase-1",
            summary="Completed initial setup",
        )

        assert checkpoint.id is not None
        assert checkpoint.phase == "phase-1"
        assert checkpoint.summary == "Completed initial setup"

    def test_get_checkpoint_by_id(self, tmp_path: Path) -> None:
        """Test retrieving a checkpoint by ID."""
        from mcp_server_langgraph.memory.checkpoints import CheckpointManager

        manager = CheckpointManager(storage_dir=tmp_path)

        checkpoint = manager.create_checkpoint(
            phase="phase-1",
            summary="Test checkpoint",
        )
        retrieved = manager.get_checkpoint(checkpoint.id)

        assert retrieved is not None
        assert retrieved.id == checkpoint.id

    def test_get_latest_checkpoint(self, tmp_path: Path) -> None:
        """Test getting the latest checkpoint."""
        from mcp_server_langgraph.memory.checkpoints import CheckpointManager
        import time

        manager = CheckpointManager(storage_dir=tmp_path)

        manager.create_checkpoint(phase="phase-1", summary="First")
        time.sleep(0.01)  # Ensure different timestamps
        latest = manager.create_checkpoint(phase="phase-2", summary="Second")

        retrieved = manager.get_latest_checkpoint()

        assert retrieved is not None
        assert retrieved.id == latest.id
        assert retrieved.phase == "phase-2"

    def test_list_checkpoints_by_phase(self, tmp_path: Path) -> None:
        """Test listing checkpoints by phase."""
        from mcp_server_langgraph.memory.checkpoints import CheckpointManager

        manager = CheckpointManager(storage_dir=tmp_path)

        manager.create_checkpoint(phase="implementation", summary="Impl 1")
        manager.create_checkpoint(phase="testing", summary="Test 1")
        manager.create_checkpoint(phase="implementation", summary="Impl 2")

        impl_checkpoints = manager.list_checkpoints(phase="implementation")
        test_checkpoints = manager.list_checkpoints(phase="testing")

        assert len(impl_checkpoints) == 2
        assert len(test_checkpoints) == 1

    def test_checkpoint_persistence(self, tmp_path: Path) -> None:
        """Test checkpoint persistence to storage."""
        from mcp_server_langgraph.memory.checkpoints import CheckpointManager

        manager1 = CheckpointManager(storage_dir=tmp_path)
        manager1.create_checkpoint(phase="test", summary="Persistent checkpoint")
        manager1.persist()

        manager2 = CheckpointManager(storage_dir=tmp_path)
        manager2.load()

        checkpoints = manager2.list_checkpoints()
        assert len(checkpoints) == 1
        assert checkpoints[0].summary == "Persistent checkpoint"

    def test_delete_checkpoint(self, tmp_path: Path) -> None:
        """Test deleting a checkpoint."""
        from mcp_server_langgraph.memory.checkpoints import CheckpointManager

        manager = CheckpointManager(storage_dir=tmp_path)

        checkpoint = manager.create_checkpoint(phase="test", summary="To delete")
        assert len(manager.list_checkpoints()) == 1

        manager.delete_checkpoint(checkpoint.id)

        assert len(manager.list_checkpoints()) == 0

    def test_summarize_session(self, tmp_path: Path) -> None:
        """Test generating session summary from checkpoints."""
        from mcp_server_langgraph.memory.checkpoints import CheckpointManager

        manager = CheckpointManager(storage_dir=tmp_path)

        manager.create_checkpoint(phase="research", summary="Researched architecture")
        manager.create_checkpoint(phase="implementation", summary="Implemented core")
        manager.create_checkpoint(phase="testing", summary="All tests pass")

        summary = manager.summarize_session()

        assert "research" in summary.lower()
        assert "implementation" in summary.lower()
        assert "testing" in summary.lower()


@pytest.mark.unit
@pytest.mark.memory
@pytest.mark.xdist_group(name="memory_notes_search")
class TestNotesManagerSearch:
    """Additional tests for notes search functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_search_empty_query_returns_all_notes(self, tmp_path: Path) -> None:
        """Test that empty search query returns all notes."""
        from mcp_server_langgraph.memory.notes import NotesManager

        notes_file = tmp_path / "NOTES.md"
        manager = NotesManager(notes_path=notes_file)

        manager.add_note(content="Note 1")
        manager.add_note(content="Note 2")
        manager.add_note(content="Note 3")

        results = manager.search("")

        assert len(results) == 3

    def test_search_case_insensitive(self, tmp_path: Path) -> None:
        """Test that search is case insensitive."""
        from mcp_server_langgraph.memory.notes import NotesManager

        notes_file = tmp_path / "NOTES.md"
        manager = NotesManager(notes_path=notes_file)

        manager.add_note(content="PYTHON is great")
        manager.add_note(content="python is awesome")
        manager.add_note(content="Python is versatile")

        results = manager.search("python")
        assert len(results) == 3

        results = manager.search("PYTHON")
        assert len(results) == 3

    def test_search_no_matches(self, tmp_path: Path) -> None:
        """Test search with no matching notes."""
        from mcp_server_langgraph.memory.notes import NotesManager

        notes_file = tmp_path / "NOTES.md"
        manager = NotesManager(notes_path=notes_file)

        manager.add_note(content="Python is great")
        manager.add_note(content="JavaScript is useful")

        results = manager.search("Rust")

        assert len(results) == 0

    def test_search_partial_match(self, tmp_path: Path) -> None:
        """Test search matches partial words."""
        from mcp_server_langgraph.memory.notes import NotesManager

        notes_file = tmp_path / "NOTES.md"
        manager = NotesManager(notes_path=notes_file)

        manager.add_note(content="Programming is fun")
        manager.add_note(content="Reprogramming the system")

        results = manager.search("gram")

        assert len(results) == 2

    def test_search_with_special_characters(self, tmp_path: Path) -> None:
        """Test search handles special characters."""
        from mcp_server_langgraph.memory.notes import NotesManager

        notes_file = tmp_path / "NOTES.md"
        manager = NotesManager(notes_path=notes_file)

        manager.add_note(content="Error: FileNotFoundError at line 42")
        manager.add_note(content="Success: All tests pass!")

        results = manager.search("Error:")

        assert len(results) == 1
        assert "FileNotFoundError" in results[0].content


@pytest.mark.unit
@pytest.mark.memory
@pytest.mark.xdist_group(name="memory_notes_timestamps")
class TestNotesManagerTimestamps:
    """Tests for note timestamp handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_notes_sorted_by_timestamp_in_persist(self, tmp_path: Path) -> None:
        """Test that notes are sorted by created_at when persisted."""
        from mcp_server_langgraph.memory.notes import NotesManager
        import time

        notes_file = tmp_path / "NOTES.md"
        manager = NotesManager(notes_path=notes_file)

        # Add notes with small delays to get different timestamps
        manager.add_note(content="First note")
        time.sleep(0.01)
        manager.add_note(content="Second note")
        time.sleep(0.01)
        manager.add_note(content="Third note")

        manager.persist()

        content = notes_file.read_text()
        first_pos = content.find("First note")
        second_pos = content.find("Second note")
        third_pos = content.find("Third note")

        # Earlier notes should appear first
        assert first_pos < second_pos < third_pos

    def test_timestamp_preserved_after_load(self, tmp_path: Path) -> None:
        """Test that timestamps are preserved after load from JSON."""
        from mcp_server_langgraph.memory.notes import NotesManager

        notes_file = tmp_path / "NOTES.md"
        manager1 = NotesManager(notes_path=notes_file)

        note = manager1.add_note(content="Timestamped note")
        original_timestamp = note.created_at
        manager1.persist()

        manager2 = NotesManager(notes_path=notes_file)
        manager2.load()

        loaded_notes = manager2.list_notes()
        assert len(loaded_notes) == 1
        # Allow for small timezone differences in parsing
        assert abs((loaded_notes[0].created_at - original_timestamp).total_seconds()) < 1

    def test_notes_with_explicit_timestamps(self, tmp_path: Path) -> None:
        """Test creating notes with explicit timestamps."""
        from mcp_server_langgraph.memory.notes import Note, NotesManager

        notes_file = tmp_path / "NOTES.md"
        manager = NotesManager(notes_path=notes_file)

        from datetime import datetime

        past = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        # Manually create note with explicit timestamp
        note = Note(
            id="note-past",
            content="Historical note",
            created_at=past,
        )

        manager._notes[note.id] = note
        manager.persist()
        manager.load()

        loaded = manager.get_note("note-past")
        assert loaded is not None
        # Verify year is preserved
        assert loaded.created_at.year == 2024


@pytest.mark.unit
@pytest.mark.memory
@pytest.mark.xdist_group(name="memory_notes_large")
class TestNotesManagerLargeContent:
    """Tests for handling large notes and many notes."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_large_note_content(self, tmp_path: Path) -> None:
        """Test handling notes with large content."""
        from mcp_server_langgraph.memory.notes import NotesManager

        notes_file = tmp_path / "NOTES.md"
        manager = NotesManager(notes_path=notes_file)

        # Create a large note (10KB)
        large_content = "Lorem ipsum " * 1000  # ~12KB
        note = manager.add_note(content=large_content)

        manager.persist()

        # Reload and verify
        manager2 = NotesManager(notes_path=notes_file)
        manager2.load()

        loaded = manager2.get_note(note.id)
        assert loaded is not None
        assert len(loaded.content) == len(large_content)

    def test_many_notes(self, tmp_path: Path) -> None:
        """Test handling many notes."""
        from mcp_server_langgraph.memory.notes import NotesManager

        notes_file = tmp_path / "NOTES.md"
        manager = NotesManager(notes_path=notes_file)

        # Add 100 notes
        for i in range(100):
            manager.add_note(
                content=f"Note number {i}",
                category=f"category-{i % 10}",
            )

        assert len(manager.list_notes()) == 100

        manager.persist()

        # Reload and verify
        manager2 = NotesManager(notes_path=notes_file)
        manager2.load()

        assert len(manager2.list_notes()) == 100

    def test_note_with_multiline_content(self, tmp_path: Path) -> None:
        """Test notes with multiline content."""
        from mcp_server_langgraph.memory.notes import NotesManager

        notes_file = tmp_path / "NOTES.md"
        manager = NotesManager(notes_path=notes_file)

        multiline = """First line
Second line
Third line with code:
```python
def hello():
    print("Hello")
```
End of note"""

        note = manager.add_note(content=multiline)
        manager.persist()

        manager2 = NotesManager(notes_path=notes_file)
        manager2.load()

        loaded = manager2.get_note(note.id)
        assert loaded is not None
        assert "First line" in loaded.content
        assert "def hello" in loaded.content

    def test_note_with_markdown_formatting(self, tmp_path: Path) -> None:
        """Test notes with markdown formatting."""
        from mcp_server_langgraph.memory.notes import NotesManager

        notes_file = tmp_path / "NOTES.md"
        manager = NotesManager(notes_path=notes_file)

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

        note = manager.add_note(content=markdown_content)
        manager.persist()

        manager2 = NotesManager(notes_path=notes_file)
        manager2.load()

        loaded = manager2.get_note(note.id)
        assert loaded is not None
        assert "# Header" in loaded.content
        assert "**Bold**" in loaded.content


@pytest.mark.unit
@pytest.mark.memory
@pytest.mark.xdist_group(name="memory_notes_markdown_parsing")
class TestNotesManagerMarkdownParsing:
    """Tests for markdown parsing edge cases."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_parse_markdown_fallback(self, tmp_path: Path) -> None:
        """Test markdown parsing when JSON sidecar is missing."""
        from mcp_server_langgraph.memory.notes import NotesManager

        notes_file = tmp_path / "NOTES.md"

        # Create markdown-only file (no JSON sidecar)
        markdown_content = """# Agent Notes

*Last updated: 2024-01-01T00:00:00*

## note-abc123
**Category:** research

**Created:** 2024-01-01T00:00:00

This is the note content.

## note-def456
**Category:** general

**Created:** 2024-01-02T00:00:00

Another note here.
"""
        notes_file.write_text(markdown_content)

        manager = NotesManager(notes_path=notes_file)
        manager.load()

        notes = manager.list_notes()
        assert len(notes) >= 1  # Should parse at least some notes

    def test_load_from_empty_file(self, tmp_path: Path) -> None:
        """Test loading from empty notes file."""
        from mcp_server_langgraph.memory.notes import NotesManager

        notes_file = tmp_path / "NOTES.md"
        notes_file.write_text("")

        manager = NotesManager(notes_path=notes_file)
        manager.load()

        assert len(manager.list_notes()) == 0

    def test_load_from_nonexistent_file(self, tmp_path: Path) -> None:
        """Test loading when file doesn't exist."""
        from mcp_server_langgraph.memory.notes import NotesManager

        notes_file = tmp_path / "nonexistent.md"

        manager = NotesManager(notes_path=notes_file)
        manager.load()  # Should not raise

        assert len(manager.list_notes()) == 0

    def test_note_with_tags_in_markdown(self, tmp_path: Path) -> None:
        """Test notes with tags are properly formatted in markdown."""
        from mcp_server_langgraph.memory.notes import NotesManager

        notes_file = tmp_path / "NOTES.md"
        manager = NotesManager(notes_path=notes_file)

        note = manager.add_note(
            content="Tagged note",
            tags=["important", "architecture", "review"],
        )

        markdown = note.to_markdown()

        assert "important" in markdown
        assert "architecture" in markdown
        assert "review" in markdown
        assert "Tags:" in markdown

    def test_note_without_tags_omits_tags_line(self, tmp_path: Path) -> None:
        """Test notes without tags don't include empty Tags line."""
        from mcp_server_langgraph.memory.notes import NotesManager

        notes_file = tmp_path / "NOTES.md"
        manager = NotesManager(notes_path=notes_file)

        note = manager.add_note(content="No tags here")

        markdown = note.to_markdown()

        # Tags line should not appear for empty tags
        lines = markdown.split("\n")
        tags_lines = [line for line in lines if line.startswith("**Tags:**")]
        assert len(tags_lines) == 0

    def test_delete_nonexistent_note_no_error(self, tmp_path: Path) -> None:
        """Test deleting nonexistent note doesn't raise error."""
        from mcp_server_langgraph.memory.notes import NotesManager

        notes_file = tmp_path / "NOTES.md"
        manager = NotesManager(notes_path=notes_file)

        # Should not raise
        manager.delete_note("nonexistent-note-id")

        assert len(manager.list_notes()) == 0
