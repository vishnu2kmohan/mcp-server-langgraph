"""
File Journal for tracking file operations.

This module implements file change tracking for rollback capability
following Claude Agent SDK's file checkpointing pattern.

Key features:
- Checkpoint creation before file operations
- Recording file changes (create, modify, delete)
- Change history retrieval for rewind operations
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum


class FileOperation(Enum):
    """Type of file operation."""

    CREATE = "create"
    MODIFY = "modify"
    DELETE = "delete"


@dataclass
class FileChangeRecord:
    """
    Record of a single file change.

    Attributes:
        file_path: Absolute path to the file
        operation: Type of operation performed
        content_before: Original content for modify/delete (None for create)
        timestamp: When the change was recorded
    """

    file_path: str
    operation: FileOperation
    content_before: bytes | None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class Checkpoint:
    """
    A checkpoint representing a point-in-time snapshot.

    Attributes:
        checkpoint_id: Unique identifier for this checkpoint
        message_id: Associated message ID (for correlation)
        created_at: When the checkpoint was created
        changes: List of file changes since this checkpoint
    """

    checkpoint_id: str
    message_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    changes: list[FileChangeRecord] = field(default_factory=list)


class FileJournal:
    """
    Tracks file operations for rollback capability.

    The journal maintains checkpoints and records file changes,
    enabling rewind to previous states.

    Example:
        journal = FileJournal()

        # Before making changes
        checkpoint_id = await journal.checkpoint("message-123")

        # Record each file operation
        await journal.record_change(
            checkpoint_id=checkpoint_id,
            file_path="/path/to/file.txt",
            operation=FileOperation.MODIFY,
            content_before=original_content,
        )

        # Later, retrieve changes for rewind
        changes = await journal.get_changes(checkpoint_id)
    """

    def __init__(self) -> None:
        """Initialize the file journal."""
        self._checkpoints: dict[str, Checkpoint] = {}
        self._lock = asyncio.Lock()

    async def checkpoint(self, message_id: str) -> str:
        """
        Create a new checkpoint.

        Args:
            message_id: Message ID to associate with this checkpoint

        Returns:
            Unique checkpoint ID
        """
        async with self._lock:
            checkpoint_id = f"cp_{uuid.uuid4().hex[:12]}"
            self._checkpoints[checkpoint_id] = Checkpoint(
                checkpoint_id=checkpoint_id,
                message_id=message_id,
            )
            return checkpoint_id

    async def record_change(
        self,
        checkpoint_id: str,
        file_path: str,
        operation: FileOperation,
        content_before: bytes | None,
    ) -> None:
        """
        Record a file change for a checkpoint.

        Args:
            checkpoint_id: Checkpoint to associate the change with
            file_path: Absolute path to the file
            operation: Type of file operation
            content_before: Original content (required for modify/delete)
        """
        async with self._lock:
            checkpoint = self._checkpoints.get(checkpoint_id)
            if checkpoint is None:
                # Create checkpoint on-the-fly if not exists
                checkpoint = Checkpoint(
                    checkpoint_id=checkpoint_id,
                    message_id="unknown",
                )
                self._checkpoints[checkpoint_id] = checkpoint

            record = FileChangeRecord(
                file_path=file_path,
                operation=operation,
                content_before=content_before,
            )
            checkpoint.changes.append(record)

    async def get_changes(self, checkpoint_id: str) -> list[FileChangeRecord]:
        """
        Get all changes for a checkpoint.

        Args:
            checkpoint_id: Checkpoint to retrieve changes for

        Returns:
            List of file change records in chronological order
        """
        async with self._lock:
            checkpoint = self._checkpoints.get(checkpoint_id)
            if checkpoint is None:
                return []
            return list(checkpoint.changes)

    async def get_checkpoint_message(self, checkpoint_id: str) -> str | None:
        """
        Get the message ID associated with a checkpoint.

        Args:
            checkpoint_id: Checkpoint to look up

        Returns:
            Associated message ID, or None if checkpoint not found
        """
        async with self._lock:
            checkpoint = self._checkpoints.get(checkpoint_id)
            if checkpoint is None:
                return None
            return checkpoint.message_id

    async def clear_checkpoint(self, checkpoint_id: str) -> None:
        """
        Clear a checkpoint and its changes.

        This removes the checkpoint from memory. Use after successful
        completion or when rollback is no longer needed.

        Args:
            checkpoint_id: Checkpoint to clear
        """
        async with self._lock:
            self._checkpoints.pop(checkpoint_id, None)

    async def get_all_checkpoints(self) -> list[str]:
        """
        Get all active checkpoint IDs.

        Returns:
            List of checkpoint IDs
        """
        async with self._lock:
            return list(self._checkpoints.keys())


# Singleton instance
_file_journal: FileJournal | None = None
_singleton_lock: asyncio.Lock = asyncio.Lock()


def get_file_journal() -> FileJournal:
    """
    Get the singleton FileJournal instance.

    Returns:
        The shared FileJournal instance
    """
    global _file_journal
    if _file_journal is None:
        _file_journal = FileJournal()
    return _file_journal


def reset_file_journal() -> None:
    """
    Reset the singleton FileJournal.

    Primarily useful for testing to ensure a clean state.
    """
    global _file_journal
    _file_journal = None
