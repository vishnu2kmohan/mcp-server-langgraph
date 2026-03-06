"""
TDD Tests for write_file tool

These tests define the expected behavior for the write_file tool.
Written FIRST before implementation (RED phase).

Note: Some tests are skipped pending implementation of corresponding features.
See: ADR-XXX for write_file tool roadmap.
"""

import gc
from pathlib import Path
from typing import Iterator
from unittest.mock import MagicMock, patch

import pytest


pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="write_file_tool")
class TestWriteFileTool:
    """Test suite for write_file tool."""

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
        """Create an existing file in the workspace."""
        file_path = temp_workspace / "existing.txt"
        file_path.write_text("original content")
        return file_path

    @pytest.fixture
    def sandbox_enabled_settings(self) -> Iterator[MagicMock]:
        """Mock settings to enable sandbox write operations.

        The write_file tool requires:
        - enable_code_execution = True
        - environment in SANDBOX_ENVIRONMENTS or enable_sandbox_tools = True
        """
        mock_settings = MagicMock()
        mock_settings.enable_code_execution = True
        mock_settings.environment = "test"
        mock_settings.enable_sandbox_tools = True
        mock_settings.code_execution_timeout = 30

        with patch("mcp_server_langgraph.tools.write_file_tools.settings", mock_settings):
            yield mock_settings

    def _create_mock_sandbox_runner(self, temp_workspace: Path) -> MagicMock:
        """Create a mock sandbox runner that writes files directly."""
        mock_result = MagicMock()
        mock_result.stdout = "File written successfully"
        mock_result.stderr = ""
        mock_result.exit_code = 0
        mock_result.timed_out = False
        mock_result.error_message = None

        def write_file_impl(path: str, content_to_write: str, create_directories: bool = True) -> MagicMock:
            """Mock implementation that actually writes the file."""
            full_path = temp_workspace / path if not Path(path).is_absolute() else Path(path)
            if create_directories:
                full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content_to_write)
            return mock_result

        mock_runner = MagicMock()
        mock_runner.run_write_file.side_effect = write_file_impl
        return mock_runner

    # =========================================================================
    # Core Functionality Tests
    # =========================================================================

    @pytest.mark.unit
    def test_write_file_creates_new_file(self, temp_workspace: Path, sandbox_enabled_settings: MagicMock):
        """GIVEN a valid path and content
        WHEN write_file is called
        THEN a new file is created with the content"""
        from mcp_server_langgraph.tools.write_file_tools import write_file

        file_path = temp_workspace / "new_file.txt"
        content = "Hello, World!"

        mock_runner = self._create_mock_sandbox_runner(temp_workspace)

        with (
            patch(
                "mcp_server_langgraph.tools.write_file_tools.get_workspace_root",
                return_value=temp_workspace,
            ),
            patch(
                "mcp_server_langgraph.tools.write_file_tools.get_sandbox_runner",
                return_value=mock_runner,
            ),
        ):
            result = write_file.invoke({"file_path": str(file_path), "content": content})

        assert file_path.exists()
        assert file_path.read_text() == content
        assert "successfully" in result.lower() or "completed" in result.lower()

    @pytest.mark.unit
    def test_write_file_overwrites_existing_file(
        self, temp_workspace: Path, existing_file: Path, sandbox_enabled_settings: MagicMock
    ):
        """GIVEN an existing file path and new content
        WHEN write_file is called
        THEN the file is overwritten with new content"""
        from mcp_server_langgraph.tools.write_file_tools import write_file

        new_content = "new content replaces original"
        mock_runner = self._create_mock_sandbox_runner(temp_workspace)

        with (
            patch(
                "mcp_server_langgraph.tools.write_file_tools.get_workspace_root",
                return_value=temp_workspace,
            ),
            patch(
                "mcp_server_langgraph.tools.write_file_tools.get_sandbox_runner",
                return_value=mock_runner,
            ),
        ):
            result = write_file.invoke({"file_path": str(existing_file), "content": new_content})

        assert existing_file.read_text() == new_content
        assert "successfully" in result.lower() or "completed" in result.lower()

    @pytest.mark.unit
    def test_write_file_creates_parent_directories(self, temp_workspace: Path, sandbox_enabled_settings: MagicMock):
        """GIVEN a path with non-existent parent directories
        WHEN write_file is called with create_directories=True
        THEN parent directories are created"""
        from mcp_server_langgraph.tools.write_file_tools import write_file

        file_path = temp_workspace / "deep" / "nested" / "path" / "file.txt"
        content = "content in nested path"
        mock_runner = self._create_mock_sandbox_runner(temp_workspace)

        with (
            patch(
                "mcp_server_langgraph.tools.write_file_tools.get_workspace_root",
                return_value=temp_workspace,
            ),
            patch(
                "mcp_server_langgraph.tools.write_file_tools.get_sandbox_runner",
                return_value=mock_runner,
            ),
        ):
            write_file.invoke(
                {
                    "file_path": str(file_path),
                    "content": content,
                    "create_directories": True,
                }
            )

        assert file_path.exists()
        assert file_path.read_text() == content

    # =========================================================================
    # Security Tests
    # =========================================================================

    @pytest.mark.unit
    def test_write_file_rejects_path_traversal(self, temp_workspace: Path, sandbox_enabled_settings: MagicMock):
        """GIVEN a path with traversal attack (../)
        WHEN write_file is called
        THEN it is rejected with an error"""
        from mcp_server_langgraph.tools.write_file_tools import write_file

        malicious_path = temp_workspace / ".." / ".." / "etc" / "passwd"

        with patch(
            "mcp_server_langgraph.tools.write_file_tools.get_workspace_root",
            return_value=temp_workspace,
        ):
            result = write_file.invoke({"file_path": str(malicious_path), "content": "malicious"})

        assert "error" in result.lower()
        # Ensure the file was NOT created
        assert not Path("/etc/passwd_test").exists()

    @pytest.mark.unit
    def test_write_file_rejects_absolute_paths_outside_workspace(
        self, temp_workspace: Path, sandbox_enabled_settings: MagicMock
    ):
        """GIVEN an absolute path outside the workspace
        WHEN write_file is called
        THEN it is rejected with an error"""
        from mcp_server_langgraph.tools.write_file_tools import write_file

        outside_path = "/tmp/outside_workspace.txt"

        with patch(
            "mcp_server_langgraph.tools.write_file_tools.get_workspace_root",
            return_value=temp_workspace,
        ):
            result = write_file.invoke({"file_path": outside_path, "content": "should not be written"})

        assert "error" in result.lower()
        assert not Path(outside_path).exists()

    @pytest.mark.unit
    def test_write_file_respects_size_limit(self, temp_workspace: Path, sandbox_enabled_settings: MagicMock):
        """GIVEN content exceeding the size limit
        WHEN write_file is called
        THEN it is rejected with an error"""
        from mcp_server_langgraph.tools.write_file_tools import write_file

        file_path = temp_workspace / "large_file.txt"
        # Create content larger than 1MB default limit
        large_content = "x" * (1024 * 1024 + 1)

        with patch(
            "mcp_server_langgraph.tools.write_file_tools.get_workspace_root",
            return_value=temp_workspace,
        ):
            result = write_file.invoke({"file_path": str(file_path), "content": large_content})

        assert "error" in result.lower()
        assert "size" in result.lower() or "exceeds" in result.lower()
        assert not file_path.exists()

    @pytest.mark.unit
    def test_write_file_rejects_dangerous_system_paths(self, temp_workspace: Path, sandbox_enabled_settings: MagicMock):
        """GIVEN a path to system directories
        WHEN write_file is called
        THEN it is rejected"""
        from mcp_server_langgraph.tools.write_file_tools import write_file

        dangerous_paths = [
            "/etc/passwd",
            "/root/.bashrc",
            str(Path.home() / ".ssh" / "authorized_keys"),
        ]

        for dangerous_path in dangerous_paths:
            with patch(
                "mcp_server_langgraph.tools.write_file_tools.get_workspace_root",
                return_value=temp_workspace,
            ):
                result = write_file.invoke({"file_path": dangerous_path, "content": "malicious"})

            assert "error" in result.lower(), f"Should reject {dangerous_path}"

    # =========================================================================
    # Backup Tests
    # =========================================================================

    @pytest.mark.unit
    def test_write_file_creates_backup_before_overwrite(
        self, temp_workspace: Path, existing_file: Path, sandbox_enabled_settings: MagicMock
    ):
        """GIVEN an existing file and create_backup=True
        WHEN write_file overwrites the file
        THEN a backup is created with .bak extension"""
        from mcp_server_langgraph.tools.write_file_tools import write_file

        original_content = existing_file.read_text()
        new_content = "new content replaces original"
        mock_runner = self._create_mock_sandbox_runner(temp_workspace)

        with (
            patch(
                "mcp_server_langgraph.tools.write_file_tools.get_workspace_root",
                return_value=temp_workspace,
            ),
            patch(
                "mcp_server_langgraph.tools.write_file_tools.get_sandbox_runner",
                return_value=mock_runner,
            ),
        ):
            # Note: create_backup parameter doesn't exist yet - this test defines expected behavior
            # We verify backup creation below, not the result
            write_file.invoke(
                {
                    "file_path": str(existing_file),
                    "content": new_content,
                    "create_backup": True,  # This parameter doesn't exist yet
                }
            )

        # Verify backup was created
        backup_file = existing_file.with_suffix(existing_file.suffix + ".bak")
        assert backup_file.exists(), f"Backup file not created at {backup_file}"
        assert backup_file.read_text() == original_content, "Backup should contain original content"
        # Verify original was overwritten
        assert existing_file.read_text() == new_content

    # =========================================================================
    # Extension Validation Tests
    # =========================================================================

    @pytest.mark.unit
    def test_write_file_allows_safe_extensions(self, temp_workspace: Path, sandbox_enabled_settings: MagicMock):
        """GIVEN files with safe extensions
        WHEN write_file is called
        THEN files are created successfully"""
        from mcp_server_langgraph.tools.write_file_tools import write_file

        safe_extensions = [".py", ".md", ".txt", ".json", ".yaml", ".yml", ".toml"]
        mock_runner = self._create_mock_sandbox_runner(temp_workspace)

        with (
            patch(
                "mcp_server_langgraph.tools.write_file_tools.get_workspace_root",
                return_value=temp_workspace,
            ),
            patch(
                "mcp_server_langgraph.tools.write_file_tools.get_sandbox_runner",
                return_value=mock_runner,
            ),
        ):
            for ext in safe_extensions:
                file_path = temp_workspace / f"test_file{ext}"
                write_file.invoke({"file_path": str(file_path), "content": f"content for {ext}"})
                assert file_path.exists(), f"Should allow {ext}"
                file_path.unlink()  # Cleanup

    @pytest.mark.unit
    def test_write_file_rejects_dangerous_extensions(self, temp_workspace: Path, sandbox_enabled_settings: MagicMock):
        """GIVEN files with dangerous extensions
        WHEN write_file is called
        THEN files are rejected"""
        from mcp_server_langgraph.tools.write_file_tools import write_file

        # Dangerous extensions that could be executable
        dangerous_extensions = [".exe", ".sh", ".bat", ".cmd", ".ps1"]

        with patch(
            "mcp_server_langgraph.tools.write_file_tools.get_workspace_root",
            return_value=temp_workspace,
        ):
            for ext in dangerous_extensions:
                file_path = temp_workspace / f"script{ext}"
                result = write_file.invoke({"file_path": str(file_path), "content": "malicious script"})
                # Extension should be blocked with error message
                assert "error" in result.lower(), f"Should reject {ext}"
                assert not file_path.exists(), f"File with {ext} should not be created"

    # =========================================================================
    # Edge Cases
    # =========================================================================

    @pytest.mark.unit
    def test_write_file_handles_empty_content(self, temp_workspace: Path, sandbox_enabled_settings: MagicMock):
        """GIVEN empty content
        WHEN write_file is called
        THEN an empty file is created"""
        from mcp_server_langgraph.tools.write_file_tools import write_file

        file_path = temp_workspace / "empty.txt"
        mock_runner = self._create_mock_sandbox_runner(temp_workspace)

        with (
            patch(
                "mcp_server_langgraph.tools.write_file_tools.get_workspace_root",
                return_value=temp_workspace,
            ),
            patch(
                "mcp_server_langgraph.tools.write_file_tools.get_sandbox_runner",
                return_value=mock_runner,
            ),
        ):
            write_file.invoke({"file_path": str(file_path), "content": ""})

        assert file_path.exists()
        assert file_path.read_text() == ""

    @pytest.mark.unit
    def test_write_file_handles_unicode_content(self, temp_workspace: Path, sandbox_enabled_settings: MagicMock):
        """GIVEN unicode content
        WHEN write_file is called
        THEN content is preserved correctly"""
        from mcp_server_langgraph.tools.write_file_tools import write_file

        file_path = temp_workspace / "unicode.txt"
        unicode_content = "Hello, 世界! 🎉 Привет мир! مرحبا"
        mock_runner = self._create_mock_sandbox_runner(temp_workspace)

        with (
            patch(
                "mcp_server_langgraph.tools.write_file_tools.get_workspace_root",
                return_value=temp_workspace,
            ),
            patch(
                "mcp_server_langgraph.tools.write_file_tools.get_sandbox_runner",
                return_value=mock_runner,
            ),
        ):
            write_file.invoke({"file_path": str(file_path), "content": unicode_content})

        assert file_path.exists()
        assert file_path.read_text(encoding="utf-8") == unicode_content

    @pytest.mark.unit
    def test_write_file_handles_special_characters_in_path(self, temp_workspace: Path, sandbox_enabled_settings: MagicMock):
        """GIVEN a filename with spaces and special characters
        WHEN write_file is called
        THEN file is created with correct name"""
        from mcp_server_langgraph.tools.write_file_tools import write_file

        file_path = temp_workspace / "file with spaces (1).txt"
        content = "content"
        mock_runner = self._create_mock_sandbox_runner(temp_workspace)

        with (
            patch(
                "mcp_server_langgraph.tools.write_file_tools.get_workspace_root",
                return_value=temp_workspace,
            ),
            patch(
                "mcp_server_langgraph.tools.write_file_tools.get_sandbox_runner",
                return_value=mock_runner,
            ),
        ):
            write_file.invoke({"file_path": str(file_path), "content": content})

        assert file_path.exists()

    # =========================================================================
    # Feature Flag Tests
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.xfail(strict=True, reason="Feature flag integration not yet implemented")
    def test_write_file_respects_feature_flag(self, temp_workspace: Path):
        """GIVEN the write_file feature flag is disabled
        WHEN write_file is called
        THEN it raises FeatureDisabledError"""
        # This test verifies the feature flag integration
        # Actual behavior depends on how the tool is registered
        pass  # Will be implemented with feature flag integration


@pytest.mark.xdist_group(name="write_file_tool_integration")
class TestWriteFileToolIntegration:
    """Integration tests for write_file tool with OpenFGA."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_write_file_requires_permission(self, tmp_path: Path):
        """GIVEN a user without write permission
        WHEN write_file is called
        THEN it is rejected"""
        # This test would require OpenFGA integration
        # Placeholder for when permission system is integrated
        pass
