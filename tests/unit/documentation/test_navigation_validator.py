"""
Unit tests for documentation navigation validator.

Tests validate that:
1. All files referenced in docs.json exist
2. All production MDX files are in navigation
3. Template files are properly excluded
4. Navigation structure is valid JSON
"""

import json
from pathlib import Path
from typing import Dict, List, Set

import pytest

# Import will be created
from scripts.validators.navigation_validator import MissingFileError, NavigationError, NavigationValidator, OrphanedFileError


class TestNavigationValidator:
    """Test suite for NavigationValidator."""

    @pytest.fixture
    def validator(self, tmp_path):
        """Create validator with temporary directory."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        return NavigationValidator(docs_dir)

    @pytest.fixture
    def sample_docs_json(self):
        """Sample docs.json structure."""
        return {
            "navigation": {
                "tabs": [
                    {
                        "tab": "Documentation",
                        "groups": [
                            {
                                "group": "Getting Started",
                                "pages": [
                                    "getting-started/introduction",
                                    "getting-started/quickstart",
                                ],
                            }
                        ],
                    }
                ]
            }
        }

    def test_valid_navigation_passes(self, tmp_path):
        """Test that valid navigation with all files existing passes."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "getting-started").mkdir()
        (docs_dir / "getting-started" / "introduction.mdx").write_text("---\ntitle: Intro\n---\n# Introduction")
        (docs_dir / "getting-started" / "quickstart.mdx").write_text("---\ntitle: Quick\n---\n# Quickstart")

        docs_json = {
            "navigation": {
                "tabs": [
                    {
                        "tab": "Documentation",
                        "groups": [
                            {
                                "group": "Getting Started",
                                "pages": [
                                    "getting-started/introduction",
                                    "getting-started/quickstart",
                                ],
                            }
                        ],
                    }
                ]
            }
        }
        (docs_dir / "docs.json").write_text(json.dumps(docs_json))

        # Act
        validator = NavigationValidator(docs_dir)
        result = validator.validate()

        # Assert
        assert result.is_valid
        assert len(result.errors) == 0
        assert len(result.warnings) == 0

    def test_missing_file_detected(self, tmp_path):
        """Test that missing files are detected."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        docs_json = {
            "navigation": {
                "tabs": [
                    {
                        "tab": "Documentation",
                        "groups": [
                            {
                                "group": "Getting Started",
                                "pages": ["getting-started/missing"],
                            }
                        ],
                    }
                ]
            }
        }
        (docs_dir / "docs.json").write_text(json.dumps(docs_json))

        # Act
        validator = NavigationValidator(docs_dir)
        result = validator.validate()

        # Assert
        assert not result.is_valid
        assert len(result.errors) == 1
        assert isinstance(result.errors[0], MissingFileError)
        assert "getting-started/missing.mdx" in str(result.errors[0])

    def test_orphaned_file_detected(self, tmp_path):
        """Test that orphaned production files are detected."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "orphaned.mdx").write_text("---\ntitle: Orphaned\n---\n# Orphaned File")

        docs_json = {"navigation": {"tabs": []}}
        (docs_dir / "docs.json").write_text(json.dumps(docs_json))

        # Act
        validator = NavigationValidator(docs_dir)
        result = validator.validate()

        # Assert
        assert not result.is_valid
        assert len(result.errors) == 1
        assert isinstance(result.errors[0], OrphanedFileError)
        assert "orphaned.mdx" in str(result.errors[0])

    def test_template_files_excluded(self, tmp_path):
        """Test that template files are properly excluded from orphan detection."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        templates_dir = docs_dir / ".mintlify" / "templates"
        templates_dir.mkdir(parents=True)
        (templates_dir / "template.mdx").write_text("---\ntitle: Template\n---\n# Template")

        docs_json = {"navigation": {"tabs": []}}
        (docs_dir / "docs.json").write_text(json.dumps(docs_json))

        # Act
        validator = NavigationValidator(docs_dir)
        result = validator.validate()

        # Assert
        assert result.is_valid
        assert len(result.errors) == 0

    def test_invalid_json_structure(self, tmp_path):
        """Test that invalid JSON structure is detected."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "docs.json").write_text("{invalid json}")

        # Act & Assert
        validator = NavigationValidator(docs_dir)
        result = validator.validate()
        assert not result.is_valid
        assert len(result.errors) == 1
        assert "JSON" in str(result.errors[0]).upper()

    def test_duplicate_pages_detected(self, tmp_path):
        """Test that duplicate page references are detected."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "page.mdx").write_text("---\ntitle: Page\n---\n# Page")

        docs_json = {
            "navigation": {
                "tabs": [
                    {
                        "tab": "Tab1",
                        "groups": [
                            {"group": "Group1", "pages": ["page"]},
                            {"group": "Group2", "pages": ["page"]},  # Duplicate
                        ],
                    }
                ]
            }
        }
        (docs_dir / "docs.json").write_text(json.dumps(docs_json))

        # Act
        validator = NavigationValidator(docs_dir)
        result = validator.validate()

        # Assert
        assert len(result.warnings) >= 1
        assert any("multiple" in str(w).lower() for w in result.warnings)

    def test_get_all_referenced_pages(self, sample_docs_json):
        """Test extraction of all referenced pages from navigation."""
        # Arrange
        # Use validator without tmp_path to avoid filesystem operations
        from pathlib import Path

        from scripts.validators.navigation_validator import NavigationValidator

        # Create a minimal validator instance (path doesn't matter for this test)
        validator = NavigationValidator(Path("/tmp"))

        # Act
        pages = validator._get_all_referenced_pages(sample_docs_json)

        # Assert
        assert len(pages) == 2
        assert "getting-started/introduction" in pages
        assert "getting-started/quickstart" in pages

    def test_get_all_mdx_files(self, tmp_path):
        """Test discovery of all MDX files."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "file1.mdx").write_text("# File 1")
        subdir = docs_dir / "subdir"
        subdir.mkdir()
        (subdir / "file2.mdx").write_text("# File 2")

        # Act
        validator = NavigationValidator(docs_dir)
        files = validator._get_all_mdx_files()

        # Assert
        assert len(files) == 2
        assert any("file1.mdx" in str(f) for f in files)
        assert any("file2.mdx" in str(f) for f in files)

    def test_exclude_patterns_work(self, tmp_path):
        """Test that exclude patterns properly filter files."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        # Create files that should be excluded
        templates_dir = docs_dir / ".mintlify" / "templates"
        templates_dir.mkdir(parents=True)
        (templates_dir / "template.mdx").write_text("# Template")

        node_modules = docs_dir / "node_modules"
        node_modules.mkdir()
        (node_modules / "module.mdx").write_text("# Module")

        # Create file that should be included
        (docs_dir / "valid.mdx").write_text("# Valid")

        docs_json = {"navigation": {"tabs": [{"tab": "T", "groups": [{"group": "G", "pages": ["valid"]}]}]}}
        (docs_dir / "docs.json").write_text(json.dumps(docs_json))

        # Act
        validator = NavigationValidator(docs_dir)
        result = validator.validate()

        # Assert
        assert result.is_valid
        assert len(result.errors) == 0

    def test_cli_exit_codes(self, tmp_path):
        """Test that CLI returns proper exit codes."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "orphaned.mdx").write_text("# Orphaned")
        (docs_dir / "docs.json").write_text('{"navigation": {"tabs": []}}')

        # Act
        validator = NavigationValidator(docs_dir)
        result = validator.validate()

        # Assert
        assert result.exit_code != 0  # Should fail with orphaned file

    def test_statistics_collection(self, tmp_path):
        """Test that validator collects statistics."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "getting-started").mkdir()
        (docs_dir / "getting-started" / "intro.mdx").write_text("# Intro")

        docs_json = {
            "navigation": {
                "tabs": [
                    {
                        "tab": "Docs",
                        "groups": [{"group": "Start", "pages": ["getting-started/intro"]}],
                    }
                ]
            }
        }
        (docs_dir / "docs.json").write_text(json.dumps(docs_json))

        # Act
        validator = NavigationValidator(docs_dir)
        result = validator.validate()

        # Assert
        assert result.stats["total_pages"] == 1
        assert result.stats["total_mdx_files"] == 1
        assert result.stats["orphaned_files"] == 0
        assert result.stats["missing_files"] == 0
