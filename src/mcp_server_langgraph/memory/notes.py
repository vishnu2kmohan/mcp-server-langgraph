"""
Structured Note-Taking

Manages structured notes for persistent agent memory across sessions.

Delegates storage to a NotesRepository backend (InMemory or Postgres).
The dual NOTES.md/NOTES.json file format is deprecated — persist()/load()
are no-ops when using a non-file repository backend.

Usage:
    from mcp_server_langgraph.memory.notes import NotesManager

    manager = NotesManager()
    note = await manager.add_note(content="Important finding", category="research")
"""

from __future__ import annotations

import logging
import re
import uuid
import warnings
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from mcp_server_langgraph.core.feature_flags import feature_gated

if TYPE_CHECKING:
    from mcp_server_langgraph.repositories.notes import NotesRepository

logger = logging.getLogger(__name__)


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
    # Phase 4 fields for memory reference resolution
    session_id: str | None = Field(
        default=None,
        description="Session ID for OpenFGA authorization (session:viewer check)",
    )
    user_id: str | None = Field(
        default=None,
        description="User ID who created the note",
    )
    title: str | None = Field(
        default=None,
        description="Display title for the note (used in [[memory:id]] refs)",
    )
    slug: str | None = Field(
        default=None,
        description="URL-friendly slug for friendly reference syntax",
    )

    def to_markdown(self) -> str:
        """Convert note to markdown format."""
        heading = self.title if self.title else self.id
        lines = [
            f"## {heading}",
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
    """Manager for structured notes with repository-backed persistence.

    Delegates all storage operations to a NotesRepository.
    Business logic (feature gating, authorization) remains here.
    """

    def __init__(
        self,
        notes_path: Path | None = None,
        repository: NotesRepository | None = None,
    ) -> None:
        """Initialize notes manager.

        Args:
            notes_path: Deprecated. Path to NOTES.md file (ignored when repository provided)
            repository: Optional NotesRepository. Defaults via get_notes_repository()
        """
        self.notes_path = notes_path or Path("./NOTES.md")

        if repository is not None:
            self._repository = repository
        else:
            from mcp_server_langgraph.core.dependencies import get_notes_repository

            self._repository = get_notes_repository()

    @feature_gated("enable_agentic_memory", "Agentic Memory")
    async def add_note(
        self,
        content: str,
        category: str = "general",
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        session_id: str | None = None,
        user_id: str | None = None,
        title: str | None = None,
        slug: str | None = None,
    ) -> Note:
        """Add a new note.

        Args:
            content: Note content
            category: Note category
            tags: Optional tags
            metadata: Optional metadata
            session_id: Optional session ID for authorization
            user_id: Optional user ID for ownership
            title: Optional display title
            slug: Optional URL-friendly slug

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
            session_id=session_id,
            user_id=user_id,
            title=title,
            slug=slug,
        )
        return await self._repository.create(note)

    async def get_note(self, note_id: str, *, actor_user_id: str | None = None) -> Note | None:
        """Get a note by ID, with optional ownership enforcement."""
        note = await self._repository.get(note_id)
        if note and actor_user_id and note.user_id and note.user_id != actor_user_id:
            return None
        return note

    async def delete_note(self, note_id: str, *, actor_user_id: str | None = None) -> None:
        """Delete a note by ID, with optional ownership enforcement."""
        if actor_user_id:
            note = await self._repository.get(note_id)
            if note and note.user_id and note.user_id != actor_user_id:
                return
        await self._repository.delete(note_id)

    async def list_notes(
        self,
        category: str | None = None,
        session_id: str | None = None,
        user_id: str | None = None,
    ) -> list[Note]:
        """List all notes, optionally filtered."""
        return await self._repository.list(category=category, session_id=session_id, user_id=user_id)

    async def search(self, query: str, *, actor_user_id: str | None = None) -> list[Note]:
        """Search notes by content, with optional ownership filtering."""
        notes = await self._repository.search(query)
        if actor_user_id:
            notes = [n for n in notes if n.user_id is None or n.user_id == actor_user_id]
        return notes

    async def clear(self) -> None:
        """Clear all notes."""
        await self._repository.clear()

    def persist(self) -> None:
        """Deprecated: No-op when using repository backend."""
        warnings.warn(
            "NotesManager.persist() is deprecated. Notes are persisted via repository backend.",
            DeprecationWarning,
            stacklevel=2,
        )

    def load(self) -> None:
        """Deprecated: No-op when using repository backend."""
        warnings.warn(
            "NotesManager.load() is deprecated. Notes are loaded via repository backend.",
            DeprecationWarning,
            stacklevel=2,
        )

    def _parse_markdown(self, content: str) -> None:
        """Deprecated: Parse notes from markdown content.

        Retained only for legacy data migration utility.
        """
        warnings.warn(
            "NotesManager._parse_markdown() is deprecated.",
            DeprecationWarning,
            stacklevel=2,
        )
        pattern = r"## (note-[\w]+)\n\*\*Category:\*\* (\w+)\n"
        matches = re.findall(pattern, content)

        for note_id, category in matches:
            section_start = content.find(f"## {note_id}")
            next_section = content.find("\n## ", section_start + 1)
            if next_section == -1:
                next_section = len(content)

            section = content[section_start:next_section]
            lines = section.split("\n")

            content_lines = []
            in_content = False
            for line in lines:
                if in_content and line.strip():
                    content_lines.append(line)
                elif not line.strip() and not in_content:
                    in_content = True

            note_content = "\n".join(content_lines)
            if note_content:
                logger.debug("Parsed legacy note: %s", note_id)
