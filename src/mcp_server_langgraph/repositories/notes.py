"""
Notes Repository

Abstract interface and in-memory implementation for structured note storage.
Supports Postgres backend via PostgresNotesRepository (separate module).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp_server_langgraph.memory.notes import Note


class NotesRepository(ABC):
    """Abstract base class for notes repository."""

    @abstractmethod
    async def create(self, note: Note) -> Note:
        """Store a new note.

        Args:
            note: The note to store

        Returns:
            The stored note
        """
        pass

    @abstractmethod
    async def get(self, note_id: str) -> Note | None:
        """Get a note by ID.

        Args:
            note_id: The note ID to retrieve

        Returns:
            The note if found, None otherwise
        """
        pass

    @abstractmethod
    async def delete(self, note_id: str) -> bool:
        """Delete a note by ID.

        Args:
            note_id: The note ID to delete

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def list(
        self,
        *,
        category: str | None = None,
        session_id: str | None = None,
        user_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Note]:
        """List notes with optional filtering and pagination.

        Args:
            category: Optional category filter
            session_id: Optional session ID filter
            user_id: Optional user ID filter
            limit: Maximum number of notes to return
            offset: Number of notes to skip

        Returns:
            List of notes sorted by created_at DESC
        """
        pass

    @abstractmethod
    async def count(
        self,
        *,
        category: str | None = None,
        session_id: str | None = None,
        user_id: str | None = None,
    ) -> int:
        """Count notes matching filters.

        Args:
            category: Optional category filter
            session_id: Optional session ID filter
            user_id: Optional user ID filter

        Returns:
            Count of matching notes
        """
        pass

    @abstractmethod
    async def search(self, query: str, *, limit: int = 100) -> list[Note]:
        """Search notes by content.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of matching notes
        """
        pass

    @abstractmethod
    async def clear(self) -> None:
        """Remove all notes."""
        pass

    @abstractmethod
    async def list_by_user(self, user_id: str) -> list[Note]:
        """List all notes for a user (GDPR export).

        Args:
            user_id: The user ID to filter by

        Returns:
            List of notes for the user
        """
        pass

    @abstractmethod
    async def delete_by_user(self, user_id: str) -> int:
        """Delete all notes for a user (GDPR deletion).

        Args:
            user_id: The user ID to delete notes for

        Returns:
            Count of deleted notes
        """
        pass


class InMemoryNotesRepository(NotesRepository):
    """In-memory implementation for testing."""

    def __init__(self) -> None:
        self._notes: dict[str, Note] = {}

    async def create(self, note: Note) -> Note:
        self._notes[note.id] = note
        return note

    async def get(self, note_id: str) -> Note | None:
        return self._notes.get(note_id)

    async def delete(self, note_id: str) -> bool:
        if note_id in self._notes:
            del self._notes[note_id]
            return True
        return False

    def _filtered(
        self,
        *,
        category: str | None = None,
        session_id: str | None = None,
        user_id: str | None = None,
    ) -> list[Note]:
        """Apply filters to notes collection."""
        notes = list(self._notes.values())
        if category:
            notes = [n for n in notes if n.category == category]
        if session_id:
            notes = [n for n in notes if n.session_id == session_id]
        if user_id:
            notes = [n for n in notes if n.user_id == user_id]
        return notes

    async def list(
        self,
        *,
        category: str | None = None,
        session_id: str | None = None,
        user_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Note]:
        notes = self._filtered(category=category, session_id=session_id, user_id=user_id)
        # Sort by created_at DESC
        notes.sort(key=lambda n: n.created_at, reverse=True)
        return notes[offset : offset + limit]

    async def count(
        self,
        *,
        category: str | None = None,
        session_id: str | None = None,
        user_id: str | None = None,
    ) -> int:
        return len(self._filtered(category=category, session_id=session_id, user_id=user_id))

    async def search(self, query: str, *, limit: int = 100) -> list[Note]:
        if not query:
            return list(self._notes.values())[:limit]

        query_lower = query.lower()
        results = [n for n in self._notes.values() if query_lower in n.content.lower()]
        return results[:limit]

    async def clear(self) -> None:
        self._notes.clear()

    async def list_by_user(self, user_id: str) -> list[Note]:
        return [n for n in self._notes.values() if n.user_id == user_id]

    async def delete_by_user(self, user_id: str) -> int:
        to_delete = [nid for nid, n in self._notes.items() if n.user_id == user_id]
        for nid in to_delete:
            del self._notes[nid]
        return len(to_delete)
