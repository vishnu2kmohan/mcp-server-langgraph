"""
File Rewind for restoring files to previous states.

This module implements file restoration capability following
Claude Agent SDK's rewind_files pattern.

Key features:
- Convenience methods for recording file operations
- Automatic restoration of files to checkpoint state
- Detailed results with error handling
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from mcp_server_langgraph.core.file_journal import (
    FileChangeRecord,
    FileJournal,
    FileOperation,
    get_file_journal,
)
from mcp_server_langgraph.observability.telemetry import logger


@dataclass
class RewindResult:
    """
    Result of a rewind operation.

    Attributes:
        success: Whether the rewind completed without critical errors
        restored_files: List of file paths that were restored
        errors: List of error messages for failed operations
        checkpoint_id: The checkpoint that was rewound to
    """

    success: bool
    restored_files: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    checkpoint_id: str = ""


class FileRewind:
    """
    High-level interface for file checkpointing and rewind.

    Wraps FileJournal with convenience methods and handles
    the actual file system operations for restoration.

    Example:
        rewind = FileRewind()

        # Before agent operations
        checkpoint_id = await rewind.checkpoint("message-123")

        # Record operations as they happen
        await rewind.record_create(checkpoint_id, "/path/new_file.txt")
        await rewind.record_modify(checkpoint_id, "/path/file.txt", original_bytes)

        # If user wants to undo
        result = await rewind.rewind_to(checkpoint_id)
        print(f"Restored {len(result.restored_files)} files")
    """

    def __init__(self, journal: FileJournal | None = None) -> None:
        """
        Initialize FileRewind with optional journal.

        Args:
            journal: Optional FileJournal instance (uses singleton if not provided)
        """
        self._journal = journal or get_file_journal()

    async def checkpoint(self, message_id: str) -> str:
        """
        Create a new checkpoint.

        Args:
            message_id: Message ID to associate with checkpoint

        Returns:
            Checkpoint ID for use with record_* and rewind_to
        """
        return await self._journal.checkpoint(message_id)

    async def record_create(self, checkpoint_id: str, file_path: str) -> None:
        """
        Record a file creation.

        For rewind, created files will be deleted.

        Args:
            checkpoint_id: Checkpoint to associate with
            file_path: Path to the created file
        """
        await self._journal.record_change(
            checkpoint_id=checkpoint_id,
            file_path=file_path,
            operation=FileOperation.CREATE,
            content_before=None,
        )

    async def record_modify(
        self,
        checkpoint_id: str,
        file_path: str,
        content_before: bytes,
    ) -> None:
        """
        Record a file modification.

        For rewind, the file will be restored to content_before.

        Args:
            checkpoint_id: Checkpoint to associate with
            file_path: Path to the modified file
            content_before: Original file content before modification
        """
        await self._journal.record_change(
            checkpoint_id=checkpoint_id,
            file_path=file_path,
            operation=FileOperation.MODIFY,
            content_before=content_before,
        )

    async def record_delete(
        self,
        checkpoint_id: str,
        file_path: str,
        content_before: bytes,
    ) -> None:
        """
        Record a file deletion.

        For rewind, the file will be recreated with content_before.

        Args:
            checkpoint_id: Checkpoint to associate with
            file_path: Path to the deleted file
            content_before: Original file content before deletion
        """
        await self._journal.record_change(
            checkpoint_id=checkpoint_id,
            file_path=file_path,
            operation=FileOperation.DELETE,
            content_before=content_before,
        )

    async def rewind_to(self, checkpoint_id: str) -> RewindResult:
        """
        Rewind all file changes since checkpoint.

        This performs the inverse of each recorded operation:
        - CREATE -> delete the file
        - MODIFY -> restore original content
        - DELETE -> recreate the file

        Changes are applied in reverse order to handle cases where
        the same file was modified multiple times.

        Args:
            checkpoint_id: Checkpoint to rewind to

        Returns:
            RewindResult with details of the operation
        """
        changes = await self._journal.get_changes(checkpoint_id)

        result = RewindResult(
            success=True,
            checkpoint_id=checkpoint_id,
        )

        if not changes:
            logger.info(f"No changes to rewind for checkpoint {checkpoint_id}")
            return result

        # Process in reverse order (most recent first)
        # This handles cases like: create file, modify file -> should delete, not restore
        # We need to track files we've already processed to handle multi-change scenarios
        processed_files: set[str] = set()

        for change in reversed(changes):
            if change.file_path in processed_files:
                # Skip - we've already restored this file to its earliest state
                continue

            try:
                self._restore_change(change)
                result.restored_files.append(change.file_path)
                processed_files.add(change.file_path)
            except Exception as e:
                error_msg = f"Failed to restore {change.file_path}: {e}"
                logger.error(error_msg)
                result.errors.append(error_msg)
                result.success = False

        # For success, we also need to process first changes (earliest state)
        # Reprocess from start to get to original state
        for change in changes:
            if change.file_path not in processed_files:
                continue  # Already handled or skipped

            # Already in processed, but we need to apply FIRST change's content
            # Find the first change for this file
            pass

        # Actually, let's simplify: for same-file multiple changes,
        # we want to restore to the FIRST recorded state (original).
        # Process all changes but track seen files, apply first content
        processed_files.clear()
        result.restored_files.clear()
        result.errors.clear()
        result.success = True

        for change in changes:
            if change.file_path in processed_files:
                # Already restored to original state
                continue

            try:
                self._restore_change(change)
                result.restored_files.append(change.file_path)
                processed_files.add(change.file_path)
            except Exception as e:
                error_msg = f"Failed to restore {change.file_path}: {e}"
                logger.error(error_msg)
                result.errors.append(error_msg)
                result.success = len(result.errors) == 0

        # Clear the checkpoint after rewind
        await self._journal.clear_checkpoint(checkpoint_id)

        logger.info(
            f"Rewind completed for checkpoint {checkpoint_id}",
            extra={
                "restored_count": len(result.restored_files),
                "error_count": len(result.errors),
            },
        )

        return result

    def _restore_change(self, change: FileChangeRecord) -> None:
        """
        Restore a single file change.

        Args:
            change: The change record to restore
        """
        path = Path(change.file_path)

        if change.operation == FileOperation.CREATE:
            # File was created -> delete it
            if path.exists():
                path.unlink()
                logger.debug(f"Deleted created file: {change.file_path}")
            else:
                logger.debug(f"File already gone: {change.file_path}")

        elif change.operation == FileOperation.MODIFY:
            # File was modified -> restore original content
            if change.content_before is not None:
                # Ensure parent directory exists
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(change.content_before)
                logger.debug(f"Restored modified file: {change.file_path}")
            else:
                logger.warning(f"No original content for modified file: {change.file_path}")

        elif change.operation == FileOperation.DELETE:
            # File was deleted -> recreate it
            if change.content_before is not None:
                # Ensure parent directory exists
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(change.content_before)
                logger.debug(f"Recreated deleted file: {change.file_path}")
            else:
                logger.warning(f"No content to recreate deleted file: {change.file_path}")
