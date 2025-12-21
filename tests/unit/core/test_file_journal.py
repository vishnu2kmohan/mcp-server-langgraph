"""
Tests for File Journal (Phase 3.1)

Following TDD: Write tests FIRST, then implementation.

This module tests the FileJournal which tracks file operations
for rollback capability following Claude Agent SDK patterns.
"""

from __future__ import annotations

import gc
import os
import tempfile
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    pass

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="file_journal")
class TestFileJournalImport:
    """Test FileJournal can be imported."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_file_journal_importable(self) -> None:
        """FileJournal should be importable from core.file_journal."""
        from mcp_server_langgraph.core.file_journal import FileJournal

        assert FileJournal is not None

    def test_file_operation_enum_importable(self) -> None:
        """FileOperation enum should be importable."""
        from mcp_server_langgraph.core.file_journal import FileOperation

        assert FileOperation is not None

    def test_file_change_record_importable(self) -> None:
        """FileChangeRecord should be importable."""
        from mcp_server_langgraph.core.file_journal import FileChangeRecord

        assert FileChangeRecord is not None


@pytest.mark.xdist_group(name="file_journal")
class TestFileJournalCheckpoint:
    """Test checkpoint creation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_checkpoint_returns_id(self) -> None:
        """checkpoint should return a checkpoint ID."""
        from mcp_server_langgraph.core.file_journal import FileJournal

        journal = FileJournal()
        checkpoint_id = await journal.checkpoint("message-123")

        assert checkpoint_id is not None
        assert isinstance(checkpoint_id, str)
        assert len(checkpoint_id) > 0

    @pytest.mark.asyncio
    async def test_checkpoint_creates_unique_ids(self) -> None:
        """Multiple checkpoints should have unique IDs."""
        from mcp_server_langgraph.core.file_journal import FileJournal

        journal = FileJournal()
        id1 = await journal.checkpoint("message-1")
        id2 = await journal.checkpoint("message-2")

        assert id1 != id2

    @pytest.mark.asyncio
    async def test_checkpoint_with_message_id(self) -> None:
        """checkpoint should associate with message ID."""
        from mcp_server_langgraph.core.file_journal import FileJournal

        journal = FileJournal()
        checkpoint_id = await journal.checkpoint("message-123")

        # Verify message association
        assert await journal.get_checkpoint_message(checkpoint_id) == "message-123"


@pytest.mark.xdist_group(name="file_journal")
class TestFileJournalRecordChange:
    """Test recording file changes."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_record_create_operation(self) -> None:
        """record_change should track file creation."""
        from mcp_server_langgraph.core.file_journal import FileJournal, FileOperation

        journal = FileJournal()
        checkpoint_id = await journal.checkpoint("message-123")

        await journal.record_change(
            checkpoint_id=checkpoint_id,
            file_path="/tmp/test/new_file.txt",
            operation=FileOperation.CREATE,
            content_before=None,
        )

        changes = await journal.get_changes(checkpoint_id)
        assert len(changes) == 1
        assert changes[0].file_path == "/tmp/test/new_file.txt"
        assert changes[0].operation == FileOperation.CREATE

    @pytest.mark.asyncio
    async def test_record_modify_operation(self) -> None:
        """record_change should track file modification with content."""
        from mcp_server_langgraph.core.file_journal import FileJournal, FileOperation

        journal = FileJournal()
        checkpoint_id = await journal.checkpoint("message-123")

        original_content = b"original content"
        await journal.record_change(
            checkpoint_id=checkpoint_id,
            file_path="/tmp/test/existing.txt",
            operation=FileOperation.MODIFY,
            content_before=original_content,
        )

        changes = await journal.get_changes(checkpoint_id)
        assert len(changes) == 1
        assert changes[0].content_before == original_content

    @pytest.mark.asyncio
    async def test_record_delete_operation(self) -> None:
        """record_change should track file deletion."""
        from mcp_server_langgraph.core.file_journal import FileJournal, FileOperation

        journal = FileJournal()
        checkpoint_id = await journal.checkpoint("message-123")

        await journal.record_change(
            checkpoint_id=checkpoint_id,
            file_path="/tmp/test/deleted.txt",
            operation=FileOperation.DELETE,
            content_before=b"deleted content",
        )

        changes = await journal.get_changes(checkpoint_id)
        assert len(changes) == 1
        assert changes[0].operation == FileOperation.DELETE

    @pytest.mark.asyncio
    async def test_record_multiple_changes(self) -> None:
        """record_change should track multiple operations."""
        from mcp_server_langgraph.core.file_journal import FileJournal, FileOperation

        journal = FileJournal()
        checkpoint_id = await journal.checkpoint("message-123")

        await journal.record_change(
            checkpoint_id=checkpoint_id,
            file_path="/tmp/test/file1.txt",
            operation=FileOperation.CREATE,
            content_before=None,
        )
        await journal.record_change(
            checkpoint_id=checkpoint_id,
            file_path="/tmp/test/file2.txt",
            operation=FileOperation.MODIFY,
            content_before=b"old",
        )
        await journal.record_change(
            checkpoint_id=checkpoint_id,
            file_path="/tmp/test/file3.txt",
            operation=FileOperation.DELETE,
            content_before=b"deleted",
        )

        changes = await journal.get_changes(checkpoint_id)
        assert len(changes) == 3


@pytest.mark.xdist_group(name="file_journal")
class TestFileJournalGetChanges:
    """Test retrieving changes."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_changes_empty_checkpoint(self) -> None:
        """get_changes should return empty list for checkpoint with no changes."""
        from mcp_server_langgraph.core.file_journal import FileJournal

        journal = FileJournal()
        checkpoint_id = await journal.checkpoint("message-123")

        changes = await journal.get_changes(checkpoint_id)
        assert changes == []

    @pytest.mark.asyncio
    async def test_get_changes_unknown_checkpoint(self) -> None:
        """get_changes should return empty list for unknown checkpoint."""
        from mcp_server_langgraph.core.file_journal import FileJournal

        journal = FileJournal()
        changes = await journal.get_changes("unknown-checkpoint")

        assert changes == []

    @pytest.mark.asyncio
    async def test_get_changes_preserves_order(self) -> None:
        """get_changes should preserve chronological order."""
        from mcp_server_langgraph.core.file_journal import FileJournal, FileOperation

        journal = FileJournal()
        checkpoint_id = await journal.checkpoint("message-123")

        # Record changes in order
        for i in range(5):
            await journal.record_change(
                checkpoint_id=checkpoint_id,
                file_path=f"/tmp/test/file{i}.txt",
                operation=FileOperation.CREATE,
                content_before=None,
            )

        changes = await journal.get_changes(checkpoint_id)
        assert len(changes) == 5
        for i, change in enumerate(changes):
            assert change.file_path == f"/tmp/test/file{i}.txt"


@pytest.mark.xdist_group(name="file_journal")
class TestFileJournalClearCheckpoint:
    """Test clearing checkpoints."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_clear_checkpoint_removes_changes(self) -> None:
        """clear_checkpoint should remove all changes for checkpoint."""
        from mcp_server_langgraph.core.file_journal import FileJournal, FileOperation

        journal = FileJournal()
        checkpoint_id = await journal.checkpoint("message-123")

        await journal.record_change(
            checkpoint_id=checkpoint_id,
            file_path="/tmp/test/file.txt",
            operation=FileOperation.CREATE,
            content_before=None,
        )

        await journal.clear_checkpoint(checkpoint_id)

        changes = await journal.get_changes(checkpoint_id)
        assert changes == []

    @pytest.mark.asyncio
    async def test_clear_unknown_checkpoint_no_error(self) -> None:
        """clear_checkpoint should not raise for unknown checkpoint."""
        from mcp_server_langgraph.core.file_journal import FileJournal

        journal = FileJournal()
        # Should not raise
        await journal.clear_checkpoint("unknown-checkpoint")


@pytest.mark.xdist_group(name="file_journal")
class TestFileJournalSingleton:
    """Test singleton pattern for FileJournal."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_file_journal_returns_instance(self) -> None:
        """get_file_journal should return FileJournal instance."""
        from mcp_server_langgraph.core.file_journal import get_file_journal

        journal = get_file_journal()
        assert journal is not None

    def test_get_file_journal_returns_same_instance(self) -> None:
        """get_file_journal should return singleton."""
        from mcp_server_langgraph.core.file_journal import get_file_journal

        journal1 = get_file_journal()
        journal2 = get_file_journal()
        assert journal1 is journal2

    def test_reset_file_journal_creates_new_instance(self) -> None:
        """reset_file_journal should create new instance."""
        from mcp_server_langgraph.core.file_journal import (
            get_file_journal,
            reset_file_journal,
        )

        journal1 = get_file_journal()
        reset_file_journal()
        journal2 = get_file_journal()
        assert journal1 is not journal2
