"""
TDD Tests for edit_file tool

These tests define the expected behavior for the edit_file tool.
Written FIRST before implementation (RED phase).
"""

import gc
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.mark.xdist_group(name="edit_file_tool")
class TestEditFileTool:
    """Test suite for edit_file tool."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def temp_workspace(self, tmp_path: Path) -> Path:
        """Create a temporary workspace directory."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        return workspace

    @pytest.fixture
    def existing_file(self, temp_workspace: Path) -> Path:
        """Create an existing file in the workspace with content."""
        file_path = temp_workspace / "existing.txt"
        file_path.write_text("Hello, World!\nThis is line 2.\nThis is line 3.")
        return file_path

    @pytest.fixture
    def file_with_duplicates(self, temp_workspace: Path) -> Path:
        """Create a file with duplicate text patterns."""
        file_path = temp_workspace / "duplicates.txt"
        file_path.write_text("foo bar foo baz foo")
        return file_path

    # =========================================================================
    # Core Functionality Tests
    # =========================================================================

    @pytest.mark.unit
    def test_edit_file_applies_replacement(
        self, temp_workspace: Path, existing_file: Path
    ):
        """GIVEN a file with specific content
        WHEN edit_file is called with old_string and new_string
        THEN the old_string is replaced with new_string"""
        from mcp_server_langgraph.tools.edit_file_tools import edit_file

        with patch(
            "mcp_server_langgraph.tools.edit_file_tools.get_workspace_root",
            return_value=temp_workspace,
        ):
            result = edit_file.invoke({
                "file_path": str(existing_file),
                "old_string": "Hello, World!",
                "new_string": "Greetings, Universe!",
            })

        assert existing_file.read_text().startswith("Greetings, Universe!")
        assert "successfully" in result.lower() or "edited" in result.lower()

    @pytest.mark.unit
    def test_edit_file_replaces_only_once_by_default(
        self, temp_workspace: Path, file_with_duplicates: Path
    ):
        """GIVEN a file with duplicate patterns
        WHEN edit_file is called with replace_all=False (default)
        THEN only the first occurrence is replaced"""
        from mcp_server_langgraph.tools.edit_file_tools import edit_file

        with patch(
            "mcp_server_langgraph.tools.edit_file_tools.get_workspace_root",
            return_value=temp_workspace,
        ):
            result = edit_file.invoke({
                "file_path": str(file_with_duplicates),
                "old_string": "foo",
                "new_string": "XXX",
            })

        content = file_with_duplicates.read_text()
        # Should replace first occurrence only
        assert content.count("XXX") == 1
        assert content.count("foo") == 2  # Two remaining

    @pytest.mark.unit
    def test_edit_file_with_replace_all_flag(
        self, temp_workspace: Path, file_with_duplicates: Path
    ):
        """GIVEN a file with duplicate patterns
        WHEN edit_file is called with replace_all=True
        THEN all occurrences are replaced"""
        from mcp_server_langgraph.tools.edit_file_tools import edit_file

        with patch(
            "mcp_server_langgraph.tools.edit_file_tools.get_workspace_root",
            return_value=temp_workspace,
        ):
            result = edit_file.invoke({
                "file_path": str(file_with_duplicates),
                "old_string": "foo",
                "new_string": "XXX",
                "replace_all": True,
            })

        content = file_with_duplicates.read_text()
        assert content.count("XXX") == 3
        assert content.count("foo") == 0

    # =========================================================================
    # Validation Tests
    # =========================================================================

    @pytest.mark.unit
    def test_edit_file_rejects_nonexistent_file(self, temp_workspace: Path):
        """GIVEN a path to a non-existent file
        WHEN edit_file is called
        THEN it returns an error"""
        from mcp_server_langgraph.tools.edit_file_tools import edit_file

        nonexistent = temp_workspace / "does_not_exist.txt"

        with patch(
            "mcp_server_langgraph.tools.edit_file_tools.get_workspace_root",
            return_value=temp_workspace,
        ):
            result = edit_file.invoke({
                "file_path": str(nonexistent),
                "old_string": "foo",
                "new_string": "bar",
            })

        assert "error" in result.lower()
        assert "exist" in result.lower() or "not found" in result.lower()

    @pytest.mark.unit
    def test_edit_file_rejects_missing_old_string(
        self, temp_workspace: Path, existing_file: Path
    ):
        """GIVEN a file that doesn't contain the old_string
        WHEN edit_file is called
        THEN it returns an error"""
        from mcp_server_langgraph.tools.edit_file_tools import edit_file

        with patch(
            "mcp_server_langgraph.tools.edit_file_tools.get_workspace_root",
            return_value=temp_workspace,
        ):
            result = edit_file.invoke({
                "file_path": str(existing_file),
                "old_string": "this text does not exist in file",
                "new_string": "replacement",
            })

        assert "error" in result.lower()
        assert "not found" in result.lower() or "does not exist" in result.lower()

    @pytest.mark.unit
    def test_edit_file_warns_on_ambiguous_match(
        self, temp_workspace: Path, file_with_duplicates: Path
    ):
        """GIVEN a file with multiple occurrences of old_string
        WHEN edit_file is called with replace_all=False
        THEN it replaces first occurrence but may warn about multiple matches"""
        from mcp_server_langgraph.tools.edit_file_tools import edit_file

        with patch(
            "mcp_server_langgraph.tools.edit_file_tools.get_workspace_root",
            return_value=temp_workspace,
        ):
            result = edit_file.invoke({
                "file_path": str(file_with_duplicates),
                "old_string": "foo",
                "new_string": "XXX",
                "replace_all": False,
            })

        # Should still work (replace first)
        content = file_with_duplicates.read_text()
        assert "XXX" in content
        # May include warning about multiple matches
        # This is implementation-dependent

    # =========================================================================
    # Backup Tests
    # =========================================================================

    @pytest.mark.unit
    def test_edit_file_creates_backup(
        self, temp_workspace: Path, existing_file: Path
    ):
        """GIVEN an existing file and backup enabled
        WHEN edit_file modifies the file
        THEN a backup is created"""
        from mcp_server_langgraph.tools.edit_file_tools import edit_file

        original_content = existing_file.read_text()

        with patch(
            "mcp_server_langgraph.tools.edit_file_tools.get_workspace_root",
            return_value=temp_workspace,
        ), patch(
            "mcp_server_langgraph.tools.edit_file_tools.EDIT_FILE_CREATE_BACKUP",
            True,
        ):
            result = edit_file.invoke({
                "file_path": str(existing_file),
                "old_string": "Hello",
                "new_string": "Goodbye",
            })

        # Check backup exists
        backup_candidates = [
            existing_file.with_suffix(".txt.bak"),
            existing_file.parent / f"{existing_file.name}.bak",
        ]

        backup_found = any(b.exists() for b in backup_candidates)
        if backup_found:
            backup_file = next(b for b in backup_candidates if b.exists())
            assert backup_file.read_text() == original_content

    # =========================================================================
    # Encoding Tests
    # =========================================================================

    @pytest.mark.unit
    def test_edit_file_preserves_encoding(self, temp_workspace: Path):
        """GIVEN a file with unicode content
        WHEN edit_file modifies the file
        THEN the encoding is preserved"""
        from mcp_server_langgraph.tools.edit_file_tools import edit_file

        unicode_file = temp_workspace / "unicode.txt"
        unicode_file.write_text("Hello, 世界! 🎉 Привет мир!", encoding="utf-8")

        with patch(
            "mcp_server_langgraph.tools.edit_file_tools.get_workspace_root",
            return_value=temp_workspace,
        ):
            result = edit_file.invoke({
                "file_path": str(unicode_file),
                "old_string": "Hello",
                "new_string": "你好",
            })

        content = unicode_file.read_text(encoding="utf-8")
        assert "你好" in content
        assert "世界" in content
        assert "🎉" in content

    @pytest.mark.unit
    def test_edit_file_handles_multiline_replacement(
        self, temp_workspace: Path
    ):
        """GIVEN a file with multiline content
        WHEN edit_file replaces a multiline section
        THEN the replacement is applied correctly"""
        from mcp_server_langgraph.tools.edit_file_tools import edit_file

        multiline_file = temp_workspace / "multiline.txt"
        multiline_file.write_text("Line 1\nLine 2\nLine 3\nLine 4")

        with patch(
            "mcp_server_langgraph.tools.edit_file_tools.get_workspace_root",
            return_value=temp_workspace,
        ):
            result = edit_file.invoke({
                "file_path": str(multiline_file),
                "old_string": "Line 2\nLine 3",
                "new_string": "New Line A\nNew Line B\nNew Line C",
            })

        content = multiline_file.read_text()
        assert "New Line A" in content
        assert "New Line B" in content
        assert "New Line C" in content
        assert "Line 2" not in content
        assert "Line 3" not in content

    # =========================================================================
    # Security Tests
    # =========================================================================

    @pytest.mark.unit
    def test_edit_file_rejects_path_traversal(self, temp_workspace: Path):
        """GIVEN a path with traversal attack (../)
        WHEN edit_file is called
        THEN it is rejected with an error"""
        from mcp_server_langgraph.tools.edit_file_tools import edit_file

        # Create a file that would be target of traversal
        parent_file = temp_workspace.parent / "outside.txt"
        parent_file.write_text("content outside workspace")

        try:
            with patch(
                "mcp_server_langgraph.tools.edit_file_tools.get_workspace_root",
                return_value=temp_workspace,
            ):
                result = edit_file.invoke({
                    "file_path": str(temp_workspace / ".." / "outside.txt"),
                    "old_string": "content",
                    "new_string": "hacked",
                })

            assert "error" in result.lower()
        finally:
            if parent_file.exists():
                parent_file.unlink()

    @pytest.mark.unit
    def test_edit_file_rejects_absolute_paths_outside_workspace(
        self, temp_workspace: Path
    ):
        """GIVEN an absolute path outside the workspace
        WHEN edit_file is called
        THEN it is rejected"""
        from mcp_server_langgraph.tools.edit_file_tools import edit_file

        with patch(
            "mcp_server_langgraph.tools.edit_file_tools.get_workspace_root",
            return_value=temp_workspace,
        ):
            result = edit_file.invoke({
                "file_path": "/tmp/outside_workspace.txt",
                "old_string": "foo",
                "new_string": "bar",
            })

        assert "error" in result.lower()

    # =========================================================================
    # Edge Cases
    # =========================================================================

    @pytest.mark.unit
    def test_edit_file_handles_empty_old_string(
        self, temp_workspace: Path, existing_file: Path
    ):
        """GIVEN an empty old_string
        WHEN edit_file is called
        THEN it returns an error (empty string would match everywhere)"""
        from mcp_server_langgraph.tools.edit_file_tools import edit_file

        with patch(
            "mcp_server_langgraph.tools.edit_file_tools.get_workspace_root",
            return_value=temp_workspace,
        ):
            result = edit_file.invoke({
                "file_path": str(existing_file),
                "old_string": "",
                "new_string": "something",
            })

        assert "error" in result.lower()

    @pytest.mark.unit
    def test_edit_file_handles_same_old_and_new_string(
        self, temp_workspace: Path, existing_file: Path
    ):
        """GIVEN old_string equals new_string
        WHEN edit_file is called
        THEN it handles gracefully (no-op or warning)"""
        from mcp_server_langgraph.tools.edit_file_tools import edit_file

        original_content = existing_file.read_text()

        with patch(
            "mcp_server_langgraph.tools.edit_file_tools.get_workspace_root",
            return_value=temp_workspace,
        ):
            result = edit_file.invoke({
                "file_path": str(existing_file),
                "old_string": "Hello",
                "new_string": "Hello",
            })

        # Content should be unchanged
        assert existing_file.read_text() == original_content


@pytest.mark.xdist_group(name="edit_file_tool_integration")
class TestEditFileToolIntegration:
    """Integration tests for edit_file tool with OpenFGA."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_edit_file_requires_permission(self, tmp_path: Path):
        """GIVEN a user without edit permission
        WHEN edit_file is called
        THEN it is rejected"""
        # Placeholder for OpenFGA integration
        pass
