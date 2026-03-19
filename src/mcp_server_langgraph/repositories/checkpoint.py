"""
Checkpoint Repository

Abstract interface and in-memory implementation for phase checkpoint storage.
Supports Postgres backend via PostgresCheckpointRepository (separate module).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp_server_langgraph.memory.checkpoints import Checkpoint


class CheckpointRepository(ABC):
    """Abstract base class for checkpoint repository."""

    @abstractmethod
    async def create(self, checkpoint: Checkpoint) -> Checkpoint:
        """Store a new checkpoint.

        Args:
            checkpoint: The checkpoint to store

        Returns:
            The stored checkpoint
        """
        pass

    @abstractmethod
    async def get(self, checkpoint_id: str) -> Checkpoint | None:
        """Get a checkpoint by ID.

        Args:
            checkpoint_id: The checkpoint ID to retrieve

        Returns:
            The checkpoint if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_latest(self, *, user_id: str | None = None) -> Checkpoint | None:
        """Get the most recent checkpoint.

        Args:
            user_id: Optional user ID to scope the query

        Returns:
            Latest checkpoint if any, None otherwise
        """
        pass

    @abstractmethod
    async def list(
        self,
        *,
        phase: str | None = None,
        user_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Checkpoint]:
        """List checkpoints with optional filtering and pagination.

        Args:
            phase: Optional phase filter
            user_id: Optional user ID filter
            limit: Maximum number of checkpoints to return
            offset: Number of checkpoints to skip

        Returns:
            List of checkpoints sorted by created_at DESC
        """
        pass

    @abstractmethod
    async def delete(self, checkpoint_id: str) -> bool:
        """Delete a checkpoint by ID.

        Args:
            checkpoint_id: The checkpoint ID to delete

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def clear(self) -> None:
        """Remove all checkpoints."""
        pass

    @abstractmethod
    async def summarize(self, *, user_id: str | None = None) -> str:
        """Generate a session summary from all checkpoints.

        Args:
            user_id: Optional user ID to scope the summary

        Returns:
            Session summary string
        """
        pass

    @abstractmethod
    async def list_by_user(self, user_id: str) -> list[Checkpoint]:
        """List all checkpoints for a user (GDPR export).

        Args:
            user_id: The user ID to filter by

        Returns:
            List of checkpoints for the user
        """
        pass

    @abstractmethod
    async def delete_by_user(self, user_id: str) -> int:
        """Delete all checkpoints for a user (GDPR deletion).

        Args:
            user_id: The user ID to delete checkpoints for

        Returns:
            Count of deleted checkpoints
        """
        pass


class InMemoryCheckpointRepository(CheckpointRepository):
    """In-memory implementation for testing."""

    def __init__(self) -> None:
        self._checkpoints: dict[str, Checkpoint] = {}

    async def create(self, checkpoint: Checkpoint) -> Checkpoint:
        self._checkpoints[checkpoint.id] = checkpoint
        return checkpoint

    async def get(self, checkpoint_id: str) -> Checkpoint | None:
        return self._checkpoints.get(checkpoint_id)

    async def get_latest(self, *, user_id: str | None = None) -> Checkpoint | None:
        candidates = list(self._checkpoints.values())
        if user_id:
            candidates = [c for c in candidates if c.user_id == user_id]
        if not candidates:
            return None
        return max(candidates, key=lambda c: c.created_at)

    def _filtered(
        self,
        *,
        phase: str | None = None,
        user_id: str | None = None,
    ) -> list[Checkpoint]:
        checkpoints = list(self._checkpoints.values())
        if phase:
            checkpoints = [c for c in checkpoints if c.phase == phase]
        if user_id:
            checkpoints = [c for c in checkpoints if c.user_id == user_id]
        return checkpoints

    async def list(
        self,
        *,
        phase: str | None = None,
        user_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Checkpoint]:
        checkpoints = self._filtered(phase=phase, user_id=user_id)
        checkpoints.sort(key=lambda c: c.created_at, reverse=True)
        return checkpoints[offset : offset + limit]

    async def delete(self, checkpoint_id: str) -> bool:
        if checkpoint_id in self._checkpoints:
            del self._checkpoints[checkpoint_id]
            return True
        return False

    async def clear(self) -> None:
        self._checkpoints.clear()

    async def summarize(self, *, user_id: str | None = None) -> str:
        candidates = list(self._checkpoints.values())
        if user_id:
            candidates = [c for c in candidates if c.user_id == user_id]

        if not candidates:
            return "No checkpoints recorded."

        checkpoints = sorted(candidates, key=lambda c: c.created_at)

        lines = ["# Session Summary", ""]
        for checkpoint in checkpoints:
            lines.append(f"## {checkpoint.phase.title()}")
            lines.append(checkpoint.summary)
            lines.append("")

        return "\n".join(lines)

    async def list_by_user(self, user_id: str) -> list[Checkpoint]:
        return [c for c in self._checkpoints.values() if c.user_id == user_id]

    async def delete_by_user(self, user_id: str) -> int:
        to_delete = [cid for cid, c in self._checkpoints.items() if c.user_id == user_id]
        for cid in to_delete:
            del self._checkpoints[cid]
        return len(to_delete)
