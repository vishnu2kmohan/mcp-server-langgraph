"""
TDD Tests for edit_file tool

These tests define the expected behavior for the edit_file tool.
Written FIRST before implementation (RED phase).

Note: Some tests are skipped pending implementation of corresponding features.
See: ADR-XXX for edit_file tool roadmap.
"""

import gc
from pathlib import Path
from typing import Iterator
from unittest.mock import MagicMock, patch

import pytest


pytestmark = pytest.mark.unit


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

    @pytest.fixture
    def sandbox_enabled_settings(self) -> Iterator[MagicMock]:
        """Mock settings to enable sandbox edit operations.

        The edit_file tool requires:
        - enable_code_execution = True
        - environment in SANDBOX_ENVIRONMENTS or enable_sandbox_tools = True
        """
        mock_settings = MagicMock()
        mock_settings.enable_code_execution = True
        mock_settings.environment = "test"
        mock_settings.enable_sandbox_tools = True
        mock_settings.code_execution_timeout = 30

        with patch("mcp_server_langgraph.tools.edit_file_tools.settings", mock_settings):
            yield mock_settings

    def _create_mock_sandbox_runner(self, temp_workspace: Path) -> MagicMock:
        """Create a mock sandbox runner that performs edits directly with validation."""

        def run_edit_impl(path: str, old_string: str, new_string: str, replace_all: bool = False) -> MagicMock:
            """Mock implementation that validates and edits the file."""
            full_path = temp_workspace / path if not Path(path).is_absolute() else Path(path)

            mock_result = MagicMock()
            mock_result.stderr = ""
            mock_result.timed_out = False
            mock_result.error_message = None

            # Validate file exists
            if not full_path.exists():
                mock_result.stdout = ""
                mock_result.exit_code = 1
                mock_result.error_message = f"Error: File does not exist: {path}"
                return mock_result

            content = full_path.read_text()

            # Validate old_string exists in file
            if old_string not in content:
                mock_result.stdout = ""
                mock_result.exit_code = 1
                mock_result.error_message = f"Error: String not found in file: {old_string[:50]}"
                return mock_result

            # Perform the edit
            if replace_all:
                new_content = content.replace(old_string, new_string)
            else:
                new_content = content.replace(old_string, new_string, 1)
            full_path.write_text(new_content)

            mock_result.stdout = "Edit completed successfully"
            mock_result.exit_code = 0
            return mock_result

        mock_runner = MagicMock()
        mock_runner.run_edit_file.side_effect = run_edit_impl
        return mock_runner

    # =========================================================================
    # Core Functionality Tests
    # =========================================================================

    @pytest.mark.unit
    def test_edit_file_applies_replacement(
        self, temp_workspace: Path, existing_file: Path, sandbox_enabled_settings: MagicMock
    ):
        """GIVEN a file with specific content
        WHEN edit_file is called with old_string and new_string
        THEN the old_string is replaced with new_string"""
        from mcp_server_langgraph.tools.edit_file_tools import edit_file

        mock_runner = self._create_mock_sandbox_runner(temp_workspace)

        with (
            patch(
                "mcp_server_langgraph.tools.edit_file_tools.get_workspace_root",
                return_value=temp_workspace,
            ),
            patch(
                "mcp_server_langgraph.tools.edit_file_tools.get_sandbox_runner",
                return_value=mock_runner,
            ),
        ):
            result = edit_file.invoke(
                {
                    "file_path": str(existing_file),
                    "old_string": "Hello, World!",
                    "new_string": "Greetings, Universe!",
                }
            )

        assert existing_file.read_text().startswith("Greetings, Universe!")
        assert "successfully" in result.lower() or "completed" in result.lower()

    @pytest.mark.unit
    def test_edit_file_replaces_only_once_by_default(
        self, temp_workspace: Path, file_with_duplicates: Path, sandbox_enabled_settings: MagicMock
    ):
        """GIVEN a file with duplicate patterns
        WHEN edit_file is called with replace_all=False (default)
        THEN only the first occurrence is replaced"""
        from mcp_server_langgraph.tools.edit_file_tools import edit_file

        mock_runner = self._create_mock_sandbox_runner(temp_workspace)

        with (
            patch(
                "mcp_server_langgraph.tools.edit_file_tools.get_workspace_root",
                return_value=temp_workspace,
            ),
            patch(
                "mcp_server_langgraph.tools.edit_file_tools.get_sandbox_runner",
                return_value=mock_runner,
            ),
        ):
            edit_file.invoke(
                {
                    "file_path": str(file_with_duplicates),
                    "old_string": "foo",
                    "new_string": "XXX",
                }
            )

        content = file_with_duplicates.read_text()
        # Should replace first occurrence only
        assert content.count("XXX") == 1
        assert content.count("foo") == 2  # Two remaining

    @pytest.mark.unit
    def test_edit_file_with_replace_all_flag(
        self, temp_workspace: Path, file_with_duplicates: Path, sandbox_enabled_settings: MagicMock
    ):
        """GIVEN a file with duplicate patterns
        WHEN edit_file is called with replace_all=True
        THEN all occurrences are replaced"""
        from mcp_server_langgraph.tools.edit_file_tools import edit_file

        mock_runner = self._create_mock_sandbox_runner(temp_workspace)

        with (
            patch(
                "mcp_server_langgraph.tools.edit_file_tools.get_workspace_root",
                return_value=temp_workspace,
            ),
            patch(
                "mcp_server_langgraph.tools.edit_file_tools.get_sandbox_runner",
                return_value=mock_runner,
            ),
        ):
            edit_file.invoke(
                {
                    "file_path": str(file_with_duplicates),
                    "old_string": "foo",
                    "new_string": "XXX",
                    "replace_all": True,
                }
            )

        content = file_with_duplicates.read_text()
        assert content.count("XXX") == 3
        assert content.count("foo") == 0

    # =========================================================================
    # Validation Tests
    # =========================================================================

    @pytest.mark.unit
    def test_edit_file_rejects_nonexistent_file(self, temp_workspace: Path, sandbox_enabled_settings: MagicMock):
        """GIVEN a path to a non-existent file
        WHEN edit_file is called
        THEN it returns an error"""
        from mcp_server_langgraph.tools.edit_file_tools import edit_file

        nonexistent = temp_workspace / "does_not_exist.txt"
        mock_runner = self._create_mock_sandbox_runner(temp_workspace)

        with (
            patch(
                "mcp_server_langgraph.tools.edit_file_tools.get_workspace_root",
                return_value=temp_workspace,
            ),
            patch(
                "mcp_server_langgraph.tools.edit_file_tools.get_sandbox_runner",
                return_value=mock_runner,
            ),
        ):
            result = edit_file.invoke(
                {
                    "file_path": str(nonexistent),
                    "old_string": "foo",
                    "new_string": "bar",
                }
            )

        assert "error" in result.lower()
        assert "exist" in result.lower() or "not found" in result.lower()

    @pytest.mark.unit
    def test_edit_file_rejects_missing_old_string(
        self, temp_workspace: Path, existing_file: Path, sandbox_enabled_settings: MagicMock
    ):
        """GIVEN a file that doesn't contain the old_string
        WHEN edit_file is called
        THEN it returns an error"""
        from mcp_server_langgraph.tools.edit_file_tools import edit_file

        mock_runner = self._create_mock_sandbox_runner(temp_workspace)

        with (
            patch(
                "mcp_server_langgraph.tools.edit_file_tools.get_workspace_root",
                return_value=temp_workspace,
            ),
            patch(
                "mcp_server_langgraph.tools.edit_file_tools.get_sandbox_runner",
                return_value=mock_runner,
            ),
        ):
            result = edit_file.invoke(
                {
                    "file_path": str(existing_file),
                    "old_string": "this text does not exist in file",
                    "new_string": "replacement",
                }
            )

        assert "error" in result.lower()
        assert "not found" in result.lower() or "does not exist" in result.lower()

    @pytest.mark.unit
    def test_edit_file_warns_on_ambiguous_match(
        self, temp_workspace: Path, file_with_duplicates: Path, sandbox_enabled_settings: MagicMock
    ):
        """GIVEN a file with multiple occurrences of old_string
        WHEN edit_file is called with replace_all=False
        THEN it replaces first occurrence but may warn about multiple matches"""
        from mcp_server_langgraph.tools.edit_file_tools import edit_file

        mock_runner = self._create_mock_sandbox_runner(temp_workspace)

        with (
            patch(
                "mcp_server_langgraph.tools.edit_file_tools.get_workspace_root",
                return_value=temp_workspace,
            ),
            patch(
                "mcp_server_langgraph.tools.edit_file_tools.get_sandbox_runner",
                return_value=mock_runner,
            ),
        ):
            edit_file.invoke(
                {
                    "file_path": str(file_with_duplicates),
                    "old_string": "foo",
                    "new_string": "XXX",
                    "replace_all": False,
                }
            )

        # Should still work (replace first)
        content = file_with_duplicates.read_text()
        assert "XXX" in content
        # May include warning about multiple matches
        # This is implementation-dependent

    # =========================================================================
    # Backup Tests
    # =========================================================================

    @pytest.mark.unit
    def test_edit_file_creates_backup(self, temp_workspace: Path, existing_file: Path, sandbox_enabled_settings: MagicMock):
        """GIVEN an existing file and create_backup=True
        WHEN edit_file modifies the file
        THEN a backup is created with .bak extension"""
        from mcp_server_langgraph.tools.edit_file_tools import edit_file

        original_content = existing_file.read_text()
        mock_runner = self._create_mock_sandbox_runner(temp_workspace)

        with (
            patch(
                "mcp_server_langgraph.tools.edit_file_tools.get_workspace_root",
                return_value=temp_workspace,
            ),
            patch(
                "mcp_server_langgraph.tools.edit_file_tools.get_sandbox_runner",
                return_value=mock_runner,
            ),
        ):
            # Invoke tool - we verify backup creation below, not the result
            edit_file.invoke(
                {
                    "file_path": str(existing_file),
                    "old_string": "Hello",
                    "new_string": "Goodbye",
                    "create_backup": True,
                }
            )

        # Verify backup was created
        backup_file = existing_file.with_suffix(existing_file.suffix + ".bak")
        assert backup_file.exists(), f"Backup file not created at {backup_file}"
        assert backup_file.read_text() == original_content, "Backup should contain original content"

    # =========================================================================
    # Encoding Tests
    # =========================================================================

    @pytest.mark.unit
    def test_edit_file_preserves_encoding(self, temp_workspace: Path, sandbox_enabled_settings: MagicMock):
        """GIVEN a file with unicode content
        WHEN edit_file modifies the file
        THEN the encoding is preserved"""
        from mcp_server_langgraph.tools.edit_file_tools import edit_file

        unicode_file = temp_workspace / "unicode.txt"
        unicode_file.write_text("Hello, 世界! 🎉 Привет мир!", encoding="utf-8")
        mock_runner = self._create_mock_sandbox_runner(temp_workspace)

        with (
            patch(
                "mcp_server_langgraph.tools.edit_file_tools.get_workspace_root",
                return_value=temp_workspace,
            ),
            patch(
                "mcp_server_langgraph.tools.edit_file_tools.get_sandbox_runner",
                return_value=mock_runner,
            ),
        ):
            edit_file.invoke(
                {
                    "file_path": str(unicode_file),
                    "old_string": "Hello",
                    "new_string": "你好",
                }
            )

        content = unicode_file.read_text(encoding="utf-8")
        assert "你好" in content
        assert "世界" in content
        assert "🎉" in content

    @pytest.mark.unit
    def test_edit_file_handles_multiline_replacement(self, temp_workspace: Path, sandbox_enabled_settings: MagicMock):
        """GIVEN a file with multiline content
        WHEN edit_file replaces a multiline section
        THEN the replacement is applied correctly"""
        from mcp_server_langgraph.tools.edit_file_tools import edit_file

        multiline_file = temp_workspace / "multiline.txt"
        multiline_file.write_text("Line 1\nLine 2\nLine 3\nLine 4")
        mock_runner = self._create_mock_sandbox_runner(temp_workspace)

        with (
            patch(
                "mcp_server_langgraph.tools.edit_file_tools.get_workspace_root",
                return_value=temp_workspace,
            ),
            patch(
                "mcp_server_langgraph.tools.edit_file_tools.get_sandbox_runner",
                return_value=mock_runner,
            ),
        ):
            edit_file.invoke(
                {
                    "file_path": str(multiline_file),
                    "old_string": "Line 2\nLine 3",
                    "new_string": "New Line A\nNew Line B\nNew Line C",
                }
            )

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
                result = edit_file.invoke(
                    {
                        "file_path": str(temp_workspace / ".." / "outside.txt"),
                        "old_string": "content",
                        "new_string": "hacked",
                    }
                )

            assert "error" in result.lower()
        finally:
            if parent_file.exists():
                parent_file.unlink()

    @pytest.mark.unit
    def test_edit_file_rejects_absolute_paths_outside_workspace(self, temp_workspace: Path):
        """GIVEN an absolute path outside the workspace
        WHEN edit_file is called
        THEN it is rejected"""
        from mcp_server_langgraph.tools.edit_file_tools import edit_file

        with patch(
            "mcp_server_langgraph.tools.edit_file_tools.get_workspace_root",
            return_value=temp_workspace,
        ):
            result = edit_file.invoke(
                {
                    "file_path": "/tmp/outside_workspace.txt",
                    "old_string": "foo",
                    "new_string": "bar",
                }
            )

        assert "error" in result.lower()

    # =========================================================================
    # Edge Cases
    # =========================================================================

    @pytest.mark.unit
    def test_edit_file_handles_empty_old_string(self, temp_workspace: Path, existing_file: Path):
        """GIVEN an empty old_string
        WHEN edit_file is called
        THEN it returns an error (empty string would match everywhere)"""
        from mcp_server_langgraph.tools.edit_file_tools import edit_file

        with patch(
            "mcp_server_langgraph.tools.edit_file_tools.get_workspace_root",
            return_value=temp_workspace,
        ):
            result = edit_file.invoke(
                {
                    "file_path": str(existing_file),
                    "old_string": "",
                    "new_string": "something",
                }
            )

        assert "error" in result.lower()

    @pytest.mark.unit
    def test_edit_file_handles_same_old_and_new_string(
        self, temp_workspace: Path, existing_file: Path, sandbox_enabled_settings: MagicMock
    ):
        """GIVEN old_string equals new_string
        WHEN edit_file is called
        THEN it handles gracefully (no-op or warning)"""
        from mcp_server_langgraph.tools.edit_file_tools import edit_file

        original_content = existing_file.read_text()
        mock_runner = self._create_mock_sandbox_runner(temp_workspace)

        with (
            patch(
                "mcp_server_langgraph.tools.edit_file_tools.get_workspace_root",
                return_value=temp_workspace,
            ),
            patch(
                "mcp_server_langgraph.tools.edit_file_tools.get_sandbox_runner",
                return_value=mock_runner,
            ),
        ):
            edit_file.invoke(
                {
                    "file_path": str(existing_file),
                    "old_string": "Hello",
                    "new_string": "Hello",
                }
            )

        # Content should be unchanged
        assert existing_file.read_text() == original_content


@pytest.mark.xdist_group(name="edit_file_tool_integration")
class TestEditFileToolIntegration:
    """Integration tests for edit_file tool with OpenFGA."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_edit_file_requires_permission(self, tmp_path: Path):
        """GIVEN a user without edit permission
        WHEN edit_file is called
        THEN it is rejected"""
        # Placeholder for OpenFGA integration
        pass
