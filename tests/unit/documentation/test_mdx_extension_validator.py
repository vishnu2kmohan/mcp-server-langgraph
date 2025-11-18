"""
Unit tests for MDX extension validator.

Tests validate that:
1. All files in docs/ directory use .mdx extension
2. No .md files exist in docs/ (except specific exclusions)
3. Template files are excluded from validation
4. Proper error reporting
"""

import gc
from pathlib import Path

import pytest

from scripts.validators.mdx_extension_validator import ExtensionError, InvalidExtensionError, MDXExtensionValidator


# Mark as unit test to ensure it runs in CI
pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="testmdxextensionvalidator")
class TestMDXExtensionValidator:
    """Test suite for MDXExtensionValidator."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def validator(self, tmp_path):
        """Create validator with temporary directory."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        return MDXExtensionValidator(docs_dir)

    def test_valid_mdx_files_pass(self, tmp_path):
        """Test that directory with only .mdx files passes."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "file1.mdx").write_text("# File 1")
        (docs_dir / "file2.mdx").write_text("# File 2")

        # Act
        validator = MDXExtensionValidator(docs_dir)
        result = validator.validate()

        # Assert
        assert result.is_valid
        assert len(result.errors) == 0
        assert result.stats["total_mdx_files"] == 2
        assert result.stats["invalid_md_files"] == 0

    def test_md_file_detected(self, tmp_path):
        """Test that .md files in docs/ are detected as errors."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "invalid.md").write_text("# Invalid")

        # Act
        validator = MDXExtensionValidator(docs_dir)
        result = validator.validate()

        # Assert
        assert not result.is_valid
        assert len(result.errors) == 1
        assert isinstance(result.errors[0], InvalidExtensionError)
        assert "invalid.md" in str(result.errors[0])

    def test_root_md_files_allowed(self, tmp_path):
        """Test that .md files in root are allowed (README.md, etc)."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        root_dir = tmp_path
        (root_dir / "README.md").write_text("# README")
        (root_dir / "CONTRIBUTING.md").write_text("# Contributing")

        # Act
        validator = MDXExtensionValidator(docs_dir)
        result = validator.validate()

        # Assert
        assert result.is_valid  # Root .md files should not affect docs/ validation

    def test_nested_md_files_detected(self, tmp_path):
        """Test that .md files in nested directories are detected."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        nested = docs_dir / "guides" / "deep"
        nested.mkdir(parents=True)
        (nested / "invalid.md").write_text("# Invalid")

        # Act
        validator = MDXExtensionValidator(docs_dir)
        result = validator.validate()

        # Assert
        assert not result.is_valid
        assert len(result.errors) == 1
        assert "guides/deep/invalid.md" in str(result.errors[0])

    def test_exclude_patterns_work(self, tmp_path):
        """Test that exclude patterns properly filter .md files."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        # Create .md files in excluded directories
        node_modules = docs_dir / "node_modules"
        node_modules.mkdir()
        (node_modules / "module.md").write_text("# Module")

        # Act
        validator = MDXExtensionValidator(docs_dir)
        result = validator.validate()

        # Assert
        assert result.is_valid  # Excluded files should not cause errors

    def test_multiple_md_files_all_reported(self, tmp_path):
        """Test that all .md files are reported, not just the first."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "file1.md").write_text("# File 1")
        (docs_dir / "file2.md").write_text("# File 2")
        (docs_dir / "file3.md").write_text("# File 3")

        # Act
        validator = MDXExtensionValidator(docs_dir)
        result = validator.validate()

        # Assert
        assert not result.is_valid
        assert len(result.errors) == 3

    def test_mixed_files_only_md_reported(self, tmp_path):
        """Test that only .md files are reported as errors when mixed with .mdx."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "valid.mdx").write_text("# Valid")
        (docs_dir / "invalid.md").write_text("# Invalid")

        # Act
        validator = MDXExtensionValidator(docs_dir)
        result = validator.validate()

        # Assert
        assert not result.is_valid
        assert len(result.errors) == 1
        assert "invalid.md" in str(result.errors[0])
        assert result.stats["total_mdx_files"] == 1

    def test_empty_docs_directory(self, tmp_path):
        """Test that empty docs directory is valid."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        # Act
        validator = MDXExtensionValidator(docs_dir)
        result = validator.validate()

        # Assert
        assert result.is_valid
        assert result.stats["total_mdx_files"] == 0
        assert result.stats["invalid_md_files"] == 0

    def test_cli_exit_codes(self, tmp_path):
        """Test that CLI returns proper exit codes."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "invalid.md").write_text("# Invalid")

        # Act
        validator = MDXExtensionValidator(docs_dir)
        result = validator.validate()

        # Assert
        assert result.exit_code != 0  # Should fail with .md file

    def test_statistics_accurate(self, tmp_path):
        """Test that statistics are accurately collected."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "file1.mdx").write_text("# File 1")
        (docs_dir / "file2.mdx").write_text("# File 2")
        (docs_dir / "invalid1.md").write_text("# Invalid 1")
        (docs_dir / "invalid2.md").write_text("# Invalid 2")

        # Act
        validator = MDXExtensionValidator(docs_dir)
        result = validator.validate()

        # Assert
        assert result.stats["total_mdx_files"] == 2
        assert result.stats["invalid_md_files"] == 2
        assert result.stats["total_files_scanned"] == 4

    def test_relative_paths_in_errors(self, tmp_path):
        """Test that errors contain relative paths, not absolute."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        nested = docs_dir / "nested"
        nested.mkdir()
        (nested / "invalid.md").write_text("# Invalid")

        # Act
        validator = MDXExtensionValidator(docs_dir)
        result = validator.validate()

        # Assert
        assert len(result.errors) == 1
        error_msg = str(result.errors[0])
        assert "nested/invalid.md" in error_msg
        assert str(tmp_path) not in error_msg  # Absolute path should not be in error
