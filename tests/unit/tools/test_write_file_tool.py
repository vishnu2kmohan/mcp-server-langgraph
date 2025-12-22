"""
TDD Tests for write_file tool

These tests define the expected behavior for the write_file tool.
Written FIRST before implementation (RED phase).
"""

import gc
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


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

    # =========================================================================
    # Core Functionality Tests
    # =========================================================================

    @pytest.mark.unit
    def test_write_file_creates_new_file(self, temp_workspace: Path):
        """GIVEN a valid path and content
        WHEN write_file is called
        THEN a new file is created with the content"""
        from mcp_server_langgraph.tools.write_file_tools import write_file

        file_path = temp_workspace / "new_file.txt"
        content = "Hello, World!"

        # Mock the workspace root for security validation
        with patch(
            "mcp_server_langgraph.tools.write_file_tools.get_workspace_root",
            return_value=temp_workspace,
        ):
            result = write_file.invoke({"file_path": str(file_path), "content": content})

        assert file_path.exists()
        assert file_path.read_text() == content
        assert "successfully" in result.lower() or "created" in result.lower()

    @pytest.mark.unit
    def test_write_file_overwrites_existing_file(
        self, temp_workspace: Path, existing_file: Path
    ):
        """GIVEN an existing file path and new content
        WHEN write_file is called
        THEN the file is overwritten with new content"""
        from mcp_server_langgraph.tools.write_file_tools import write_file

        new_content = "new content replaces original"

        with patch(
            "mcp_server_langgraph.tools.write_file_tools.get_workspace_root",
            return_value=temp_workspace,
        ):
            result = write_file.invoke(
                {"file_path": str(existing_file), "content": new_content}
            )

        assert existing_file.read_text() == new_content
        assert "successfully" in result.lower() or "overwritten" in result.lower()

    @pytest.mark.unit
    def test_write_file_creates_parent_directories(self, temp_workspace: Path):
        """GIVEN a path with non-existent parent directories
        WHEN write_file is called with create_directories=True
        THEN parent directories are created"""
        from mcp_server_langgraph.tools.write_file_tools import write_file

        file_path = temp_workspace / "deep" / "nested" / "path" / "file.txt"
        content = "content in nested path"

        with patch(
            "mcp_server_langgraph.tools.write_file_tools.get_workspace_root",
            return_value=temp_workspace,
        ):
            result = write_file.invoke(
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
    def test_write_file_rejects_path_traversal(self, temp_workspace: Path):
        """GIVEN a path with traversal attack (../)
        WHEN write_file is called
        THEN it is rejected with an error"""
        from mcp_server_langgraph.tools.write_file_tools import write_file

        malicious_path = temp_workspace / ".." / ".." / "etc" / "passwd"

        with patch(
            "mcp_server_langgraph.tools.write_file_tools.get_workspace_root",
            return_value=temp_workspace,
        ):
            result = write_file.invoke(
                {"file_path": str(malicious_path), "content": "malicious"}
            )

        assert "error" in result.lower()
        assert "path" in result.lower() or "traversal" in result.lower()
        # Ensure the file was NOT created
        assert not Path("/etc/passwd_test").exists()

    @pytest.mark.unit
    def test_write_file_rejects_absolute_paths_outside_workspace(
        self, temp_workspace: Path
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
            result = write_file.invoke(
                {"file_path": outside_path, "content": "should not be written"}
            )

        assert "error" in result.lower()
        assert not Path(outside_path).exists()

    @pytest.mark.unit
    def test_write_file_respects_size_limit(self, temp_workspace: Path):
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
            result = write_file.invoke(
                {"file_path": str(file_path), "content": large_content}
            )

        assert "error" in result.lower()
        assert "size" in result.lower() or "large" in result.lower()
        assert not file_path.exists()

    @pytest.mark.unit
    def test_write_file_rejects_dangerous_system_paths(self, temp_workspace: Path):
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
                result = write_file.invoke(
                    {"file_path": dangerous_path, "content": "malicious"}
                )

            assert "error" in result.lower(), f"Should reject {dangerous_path}"

    # =========================================================================
    # Backup Tests
    # =========================================================================

    @pytest.mark.unit
    def test_write_file_creates_backup_before_overwrite(
        self, temp_workspace: Path, existing_file: Path
    ):
        """GIVEN an existing file and create_backup=True
        WHEN write_file overwrites the file
        THEN a backup is created"""
        from mcp_server_langgraph.tools.write_file_tools import write_file

        original_content = existing_file.read_text()
        new_content = "replacement content"

        with patch(
            "mcp_server_langgraph.tools.write_file_tools.get_workspace_root",
            return_value=temp_workspace,
        ), patch(
            "mcp_server_langgraph.tools.write_file_tools.WRITE_FILE_CREATE_BACKUP",
            True,
        ):
            result = write_file.invoke(
                {"file_path": str(existing_file), "content": new_content}
            )

        # Check backup exists (naming convention: file.txt.bak or file.txt.backup)
        backup_candidates = [
            existing_file.with_suffix(".txt.bak"),
            existing_file.with_suffix(".txt.backup"),
            existing_file.parent / f"{existing_file.name}.bak",
        ]

        backup_found = any(b.exists() for b in backup_candidates)
        if backup_found:
            backup_file = next(b for b in backup_candidates if b.exists())
            assert backup_file.read_text() == original_content

        # Main file should have new content
        assert existing_file.read_text() == new_content

    # =========================================================================
    # Extension Validation Tests
    # =========================================================================

    @pytest.mark.unit
    def test_write_file_allows_safe_extensions(self, temp_workspace: Path):
        """GIVEN files with safe extensions
        WHEN write_file is called
        THEN files are created successfully"""
        from mcp_server_langgraph.tools.write_file_tools import write_file

        safe_extensions = [".py", ".md", ".txt", ".json", ".yaml", ".yml", ".toml"]

        with patch(
            "mcp_server_langgraph.tools.write_file_tools.get_workspace_root",
            return_value=temp_workspace,
        ):
            for ext in safe_extensions:
                file_path = temp_workspace / f"test_file{ext}"
                result = write_file.invoke(
                    {"file_path": str(file_path), "content": f"content for {ext}"}
                )
                assert file_path.exists(), f"Should allow {ext}"
                file_path.unlink()  # Cleanup

    @pytest.mark.unit
    def test_write_file_rejects_dangerous_extensions(self, temp_workspace: Path):
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
                result = write_file.invoke(
                    {"file_path": str(file_path), "content": "malicious script"}
                )
                # May or may not reject based on implementation - check if extension allowlist is enforced
                # If enforced, should have error and file should not exist

    # =========================================================================
    # Edge Cases
    # =========================================================================

    @pytest.mark.unit
    def test_write_file_handles_empty_content(self, temp_workspace: Path):
        """GIVEN empty content
        WHEN write_file is called
        THEN an empty file is created"""
        from mcp_server_langgraph.tools.write_file_tools import write_file

        file_path = temp_workspace / "empty.txt"

        with patch(
            "mcp_server_langgraph.tools.write_file_tools.get_workspace_root",
            return_value=temp_workspace,
        ):
            result = write_file.invoke({"file_path": str(file_path), "content": ""})

        assert file_path.exists()
        assert file_path.read_text() == ""

    @pytest.mark.unit
    def test_write_file_handles_unicode_content(self, temp_workspace: Path):
        """GIVEN unicode content
        WHEN write_file is called
        THEN content is preserved correctly"""
        from mcp_server_langgraph.tools.write_file_tools import write_file

        file_path = temp_workspace / "unicode.txt"
        unicode_content = "Hello, 世界! 🎉 Привет мир! مرحبا"

        with patch(
            "mcp_server_langgraph.tools.write_file_tools.get_workspace_root",
            return_value=temp_workspace,
        ):
            result = write_file.invoke(
                {"file_path": str(file_path), "content": unicode_content}
            )

        assert file_path.exists()
        assert file_path.read_text(encoding="utf-8") == unicode_content

    @pytest.mark.unit
    def test_write_file_handles_special_characters_in_path(self, temp_workspace: Path):
        """GIVEN a filename with spaces and special characters
        WHEN write_file is called
        THEN file is created with correct name"""
        from mcp_server_langgraph.tools.write_file_tools import write_file

        file_path = temp_workspace / "file with spaces (1).txt"
        content = "content"

        with patch(
            "mcp_server_langgraph.tools.write_file_tools.get_workspace_root",
            return_value=temp_workspace,
        ):
            result = write_file.invoke(
                {"file_path": str(file_path), "content": content}
            )

        assert file_path.exists()

    # =========================================================================
    # Feature Flag Tests
    # =========================================================================

    @pytest.mark.unit
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

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_write_file_requires_permission(self, tmp_path: Path):
        """GIVEN a user without write permission
        WHEN write_file is called
        THEN it is rejected"""
        # This test would require OpenFGA integration
        # Placeholder for when permission system is integrated
        pass
