"""
Tests for File Rewind (Phase 3.3)

Following TDD: Write tests FIRST, then implementation.

This module tests the FileRewind capability which restores files
to their previous state using the FileJournal.
"""

from __future__ import annotations

import gc
import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    pass

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="file_rewind")
class TestFileRewindImport:
    """Test FileRewind can be imported."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_file_rewind_importable(self) -> None:
        """FileRewind should be importable."""
        from mcp_server_langgraph.core.file_rewind import FileRewind

        assert FileRewind is not None

    def test_rewind_result_importable(self) -> None:
        """RewindResult should be importable."""
        from mcp_server_langgraph.core.file_rewind import RewindResult

        assert RewindResult is not None


@pytest.mark.xdist_group(name="file_rewind")
class TestFileRewindCreatedFiles:
    """Test rewinding created files (deletion)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_rewind_deletes_created_file(self) -> None:
        """Rewind should delete files that were created."""
        from mcp_server_langgraph.core.file_journal import (
            FileOperation,
            reset_file_journal,
        )
        from mcp_server_langgraph.core.file_rewind import FileRewind

        reset_file_journal()

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "new_file.txt"

            # Simulate: checkpoint, create file, rewind
            rewind = FileRewind()
            checkpoint_id = await rewind.checkpoint("message-123")

            # Create the file
            file_path.write_text("new content")
            assert file_path.exists()

            # Record the creation
            await rewind.record_create(checkpoint_id, str(file_path))

            # Rewind - file should be deleted
            result = await rewind.rewind_to(checkpoint_id)

            assert not file_path.exists()
            assert str(file_path) in result.restored_files

    @pytest.mark.asyncio
    async def test_rewind_handles_already_deleted(self) -> None:
        """Rewind should handle case where file was already deleted."""
        from mcp_server_langgraph.core.file_journal import reset_file_journal
        from mcp_server_langgraph.core.file_rewind import FileRewind

        reset_file_journal()

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "new_file.txt"

            rewind = FileRewind()
            checkpoint_id = await rewind.checkpoint("message-123")

            # Record creation but file doesn't exist (already cleaned up)
            await rewind.record_create(checkpoint_id, str(file_path))

            # Rewind should not error
            result = await rewind.rewind_to(checkpoint_id)
            assert result is not None


@pytest.mark.xdist_group(name="file_rewind")
class TestFileRewindModifiedFiles:
    """Test rewinding modified files (restoration)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_rewind_restores_modified_file(self) -> None:
        """Rewind should restore modified files to original content."""
        from mcp_server_langgraph.core.file_journal import reset_file_journal
        from mcp_server_langgraph.core.file_rewind import FileRewind

        reset_file_journal()

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "existing_file.txt"
            original_content = "original content"
            new_content = "modified content"

            # Create file with original content
            file_path.write_text(original_content)

            rewind = FileRewind()
            checkpoint_id = await rewind.checkpoint("message-123")

            # Record the modification with original content
            await rewind.record_modify(
                checkpoint_id,
                str(file_path),
                original_content.encode(),
            )

            # Modify the file
            file_path.write_text(new_content)
            assert file_path.read_text() == new_content

            # Rewind - file should be restored
            result = await rewind.rewind_to(checkpoint_id)

            assert file_path.read_text() == original_content
            assert str(file_path) in result.restored_files


@pytest.mark.xdist_group(name="file_rewind")
class TestFileRewindDeletedFiles:
    """Test rewinding deleted files (recreation)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_rewind_recreates_deleted_file(self) -> None:
        """Rewind should recreate files that were deleted."""
        from mcp_server_langgraph.core.file_journal import reset_file_journal
        from mcp_server_langgraph.core.file_rewind import FileRewind

        reset_file_journal()

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "to_delete.txt"
            original_content = b"content before deletion"

            # Create file
            file_path.write_bytes(original_content)

            rewind = FileRewind()
            checkpoint_id = await rewind.checkpoint("message-123")

            # Record the deletion with original content
            await rewind.record_delete(checkpoint_id, str(file_path), original_content)

            # Delete the file
            file_path.unlink()
            assert not file_path.exists()

            # Rewind - file should be recreated
            result = await rewind.rewind_to(checkpoint_id)

            assert file_path.exists()
            assert file_path.read_bytes() == original_content
            assert str(file_path) in result.restored_files


@pytest.mark.xdist_group(name="file_rewind")
class TestFileRewindMultipleChanges:
    """Test rewinding multiple file changes."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_rewind_multiple_operations(self) -> None:
        """Rewind should handle multiple different operations."""
        from mcp_server_langgraph.core.file_journal import reset_file_journal
        from mcp_server_langgraph.core.file_rewind import FileRewind

        reset_file_journal()

        with tempfile.TemporaryDirectory() as tmpdir:
            created_file = Path(tmpdir) / "created.txt"
            modified_file = Path(tmpdir) / "modified.txt"
            deleted_file = Path(tmpdir) / "deleted.txt"

            # Setup: modified_file and deleted_file exist initially
            modified_file.write_text("original modified")
            deleted_file.write_bytes(b"original deleted")

            rewind = FileRewind()
            checkpoint_id = await rewind.checkpoint("message-123")

            # Record operations
            await rewind.record_create(checkpoint_id, str(created_file))
            await rewind.record_modify(
                checkpoint_id, str(modified_file), b"original modified"
            )
            await rewind.record_delete(
                checkpoint_id, str(deleted_file), b"original deleted"
            )

            # Simulate the operations
            created_file.write_text("new file")
            modified_file.write_text("changed modified")
            deleted_file.unlink()

            # Verify current state
            assert created_file.exists()
            assert modified_file.read_text() == "changed modified"
            assert not deleted_file.exists()

            # Rewind all
            result = await rewind.rewind_to(checkpoint_id)

            # Verify restoration
            assert not created_file.exists()  # Was created, now deleted
            assert modified_file.read_text() == "original modified"  # Restored
            assert deleted_file.exists()  # Was deleted, now recreated
            assert deleted_file.read_bytes() == b"original deleted"

            assert len(result.restored_files) == 3

    @pytest.mark.asyncio
    async def test_rewind_in_reverse_order(self) -> None:
        """Rewind should process changes in reverse chronological order."""
        from mcp_server_langgraph.core.file_journal import reset_file_journal
        from mcp_server_langgraph.core.file_rewind import FileRewind

        reset_file_journal()

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "multi_modify.txt"
            file_path.write_text("v1")

            rewind = FileRewind()
            checkpoint_id = await rewind.checkpoint("message-123")

            # Multiple modifications to same file
            await rewind.record_modify(checkpoint_id, str(file_path), b"v1")
            file_path.write_text("v2")

            await rewind.record_modify(checkpoint_id, str(file_path), b"v2")
            file_path.write_text("v3")

            # Rewind should restore to original (v1)
            result = await rewind.rewind_to(checkpoint_id)

            # First recorded content should be final restored content
            assert file_path.read_text() == "v1"


@pytest.mark.xdist_group(name="file_rewind")
class TestFileRewindResult:
    """Test RewindResult details."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_result_includes_errors(self) -> None:
        """RewindResult should include any errors encountered."""
        from mcp_server_langgraph.core.file_journal import reset_file_journal
        from mcp_server_langgraph.core.file_rewind import FileRewind

        reset_file_journal()

        rewind = FileRewind()
        checkpoint_id = await rewind.checkpoint("message-123")

        # Record modification for non-writable path (will fail on rewind)
        await rewind.record_modify(
            checkpoint_id, "/root/protected/file.txt", b"content"
        )

        result = await rewind.rewind_to(checkpoint_id)

        # Should have error for protected file
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_result_success_flag(self) -> None:
        """RewindResult should have success flag."""
        from mcp_server_langgraph.core.file_journal import reset_file_journal
        from mcp_server_langgraph.core.file_rewind import FileRewind

        reset_file_journal()

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "simple.txt"
            file_path.write_text("original")

            rewind = FileRewind()
            checkpoint_id = await rewind.checkpoint("message-123")

            await rewind.record_modify(checkpoint_id, str(file_path), b"original")
            file_path.write_text("modified")

            result = await rewind.rewind_to(checkpoint_id)

            assert result.success is True
            assert len(result.errors) == 0
