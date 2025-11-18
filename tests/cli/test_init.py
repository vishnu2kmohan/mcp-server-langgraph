"""
Tests for CLI project initialization.

Tests cover:
- Project creation with different templates
- Directory structure validation
- Error handling for existing directories
- Invalid template validation
"""

import gc
import tempfile
from pathlib import Path

import pytest

from mcp_server_langgraph.cli.init import init_project


# ==============================================================================
# Project Creation Tests
# ==============================================================================


@pytest.mark.unit
def test_init_project_creates_quickstart_template_successfully():
    """Test init_project() with quickstart template creates project."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir) / "test_project"

        # Act
        init_project(str(project_path), template="quickstart")

        # Assert
        assert project_path.exists()
        assert (project_path / "src").exists()
        assert (project_path / "tests").exists()


@pytest.mark.unit
def test_init_project_creates_production_template_successfully():
    """Test init_project() with production template creates project."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir) / "test_project"

        # Act
        init_project(str(project_path), template="production")

        # Assert
        assert project_path.exists()


@pytest.mark.unit
def test_init_project_creates_enterprise_template_successfully():
    """Test init_project() with enterprise template creates project."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir) / "test_project"

        # Act
        init_project(str(project_path), template="enterprise")

        # Assert
        assert project_path.exists()


@pytest.mark.unit
def test_init_project_uses_production_template_by_default():
    """Test init_project() defaults to production template when not specified."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir) / "test_project"

        # Act
        init_project(str(project_path))

        # Assert
        assert project_path.exists()


# ==============================================================================
# Error Handling Tests
# ==============================================================================


@pytest.mark.unit
def test_init_project_raises_error_when_directory_exists():
    """Test init_project() raises FileExistsError when directory already exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir) / "existing_project"
        project_path.mkdir()

        # Act & Assert
        with pytest.raises(FileExistsError, match="already exists"):
            init_project(str(project_path))


@pytest.mark.unit
def test_init_project_raises_error_for_invalid_template():
    """Test init_project() raises ValueError for invalid template name."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir) / "test_project"

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid template"):
            init_project(str(project_path), template="invalid_template")  # type: ignore


# ==============================================================================
# Directory Structure Tests
# ==============================================================================


@pytest.mark.unit
def test_quickstart_template_creates_correct_directory_structure():
    """Test quickstart template creates expected directory structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir) / "test_project"

        # Act
        init_project(str(project_path), template="quickstart")

        # Assert - Verify expected directories
        assert (project_path / "src").is_dir()
        assert (project_path / "tests").is_dir()


@pytest.mark.unit
def test_init_project_accepts_string_path():
    """Test init_project() accepts string path (not just Path object)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_name = "string_path_project"
        project_path = Path(tmpdir) / project_name

        # Act - Pass string, not Path
        init_project(str(project_path), template="quickstart")

        # Assert
        assert project_path.exists()


@pytest.mark.unit
def test_init_project_creates_nested_parent_directories():
    """Test init_project() creates parent directories if needed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        nested_path = Path(tmpdir) / "parent" / "child" / "project"

        # Act
        init_project(str(nested_path), template="quickstart")

        # Assert
        assert nested_path.exists()
        assert (nested_path / "src").exists()
