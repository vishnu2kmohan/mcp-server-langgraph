"""
Structured Note-Taking

Manages NOTES.md for persistent agent memory across sessions.

Provides structured note storage with categorization, tagging,
and search capabilities for agentic workflows.

Usage:
    from mcp_server_langgraph.memory.notes import NotesManager

    manager = NotesManager(notes_path=Path("./NOTES.md"))
    note = manager.add_note(content="Important finding", category="research")
    manager.persist()
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from mcp_server_langgraph.core.feature_flags import feature_gated


class Note(BaseModel):
    """A structured note for agent memory."""

    id: str = Field(description="Unique note identifier")
    content: str = Field(description="Note content")
    category: str = Field(default="general", description="Note category")
    tags: list[str] = Field(default_factory=list, description="Note tags")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Creation timestamp",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )

    def to_markdown(self) -> str:
        """Convert note to markdown format.

        Returns:
            Markdown-formatted note string
        """
        lines = [
            f"## {self.id}",
            f"**Category:** {self.category}",
        ]

        if self.tags:
            lines.append(f"**Tags:** {', '.join(self.tags)}")

        lines.append(f"**Created:** {self.created_at.isoformat()}")
        lines.append("")
        lines.append(self.content)
        lines.append("")

        return "\n".join(lines)


class NotesManager:
    """Manager for structured notes with persistence.

    Handles note storage, retrieval, and persistence to
    NOTES.md file for cross-session memory.
    """

    def __init__(self, notes_path: Path | None = None) -> None:
        """Initialize notes manager.

        Args:
            notes_path: Path to NOTES.md file
        """
        self.notes_path = notes_path or Path("./NOTES.md")
        self._notes: dict[str, Note] = {}

    @feature_gated("enable_agentic_memory", "Agentic Memory")
    def add_note(
        self,
        content: str,
        category: str = "general",
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Note:
        """Add a new note.

        Args:
            content: Note content
            category: Note category
            tags: Optional tags
            metadata: Optional metadata

        Returns:
            Created Note object

        Raises:
            FeatureDisabledError: If agentic memory is disabled
        """
        note_id = f"note-{uuid.uuid4().hex[:8]}"
        note = Note(
            id=note_id,
            content=content,
            category=category,
            tags=tags or [],
            metadata=metadata or {},
        )
        self._notes[note_id] = note
        return note

    def get_note(self, note_id: str) -> Note | None:
        """Get a note by ID.

        Args:
            note_id: Note identifier

        Returns:
            Note if found, None otherwise
        """
        return self._notes.get(note_id)

    def delete_note(self, note_id: str) -> None:
        """Delete a note by ID.

        Args:
            note_id: Note identifier
        """
        self._notes.pop(note_id, None)

    def list_notes(self, category: str | None = None) -> list[Note]:
        """List all notes, optionally filtered by category.

        Args:
            category: Optional category filter

        Returns:
            List of notes
        """
        notes = list(self._notes.values())
        if category:
            notes = [n for n in notes if n.category == category]
        return notes

    def search(self, query: str) -> list[Note]:
        """Search notes by content.

        Args:
            query: Search query

        Returns:
            List of matching notes
        """
        if not query:
            return self.list_notes()

        query_lower = query.lower()
        results = []
        for note in self._notes.values():
            if query_lower in note.content.lower():
                results.append(note)
        return results

    def clear(self) -> None:
        """Clear all notes."""
        self._notes.clear()

    def persist(self) -> None:
        """Persist notes to NOTES.md file."""
        lines = [
            "# Agent Notes",
            "",
            f"*Last updated: {datetime.now(UTC).isoformat()}*",
            "",
        ]

        for note in sorted(self._notes.values(), key=lambda n: n.created_at):
            lines.append(note.to_markdown())

        # Also persist as JSON for reliable loading
        json_data = {"notes": [note.model_dump(mode="json") for note in self._notes.values()]}

        self.notes_path.write_text("\n".join(lines))

        # Write JSON sidecar for reliable round-trip
        json_path = self.notes_path.with_suffix(".json")
        json_path.write_text(json.dumps(json_data, indent=2, default=str))

    def load(self) -> None:
        """Load notes from NOTES.md file."""
        json_path = self.notes_path.with_suffix(".json")

        if json_path.exists():
            # Load from JSON sidecar for reliability
            data = json.loads(json_path.read_text())
            for note_data in data.get("notes", []):
                # Parse datetime string back to datetime
                if "created_at" in note_data and isinstance(note_data["created_at"], str):
                    note_data["created_at"] = datetime.fromisoformat(note_data["created_at"])
                note = Note(**note_data)
                self._notes[note.id] = note
        elif self.notes_path.exists():
            # Fallback: parse markdown (less reliable)
            self._parse_markdown(self.notes_path.read_text())

    def _parse_markdown(self, content: str) -> None:
        """Parse notes from markdown content.

        Args:
            content: Markdown content
        """
        # Simple parsing: find ## note-xxx sections
        pattern = r"## (note-[\w]+)\n\*\*Category:\*\* (\w+)\n"
        matches = re.findall(pattern, content)

        for note_id, category in matches:
            # Extract content between sections
            section_start = content.find(f"## {note_id}")
            next_section = content.find("\n## ", section_start + 1)
            if next_section == -1:
                next_section = len(content)

            section = content[section_start:next_section]
            lines = section.split("\n")

            # Find content (after blank line)
            content_lines = []
            in_content = False
            for line in lines:
                if in_content and line.strip():
                    content_lines.append(line)
                elif not line.strip() and not in_content:
                    in_content = True

            note_content = "\n".join(content_lines)
            if note_content:
                note = Note(id=note_id, content=note_content, category=category)
                self._notes[note_id] = note
