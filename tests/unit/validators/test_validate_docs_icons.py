#!/usr/bin/env python3
"""
Tests for icon validation functionality in validate_docs.py.

TDD RED Phase: These tests define expected behavior for icon validation.
Tests will fail until validate_docs.py is enhanced with icon validation.
"""

import gc
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="validate_docs_icons")
class TestIconValidation:
    """Test icon validation functionality."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_valid_single_quoted_icon_passes(self, tmp_path: Path):
        """Valid icons with single quotes should pass validation."""
        # Import here to avoid issues if module doesn't exist yet
        from scripts.validators.validate_docs import validate_icon_format

        # Valid single-quoted icon
        assert validate_icon_format("'rocket'") == (True, "rocket", None)
        assert validate_icon_format("'shield-halved'") == (True, "shield-halved", None)
        assert validate_icon_format("'file-lines'") == (True, "file-lines", None)

    def test_double_quoted_icon_fails(self, tmp_path: Path):
        """Icons with double quotes should fail validation."""
        from scripts.validators.validate_docs import validate_icon_format

        is_valid, icon, error = validate_icon_format('"rocket"')
        assert is_valid is False
        assert "double quotes" in error.lower()

    def test_unquoted_icon_fails(self, tmp_path: Path):
        """Unquoted icons should fail validation."""
        from scripts.validators.validate_docs import validate_icon_format

        is_valid, icon, error = validate_icon_format("rocket")
        assert is_valid is False
        assert "single quotes" in error.lower() or "unquoted" in error.lower()

    def test_invalid_icon_name_fails(self, tmp_path: Path):
        """Invalid icon names not in registry should fail validation."""
        from scripts.validators.validate_docs import validate_icon_format

        # Use an icon that's definitely not in the registry
        is_valid, icon, error = validate_icon_format("'not-a-real-icon-xyz123'")
        assert is_valid is False
        assert "not a valid font awesome" in error.lower() or "invalid icon" in error.lower()

    def test_empty_icon_fails(self, tmp_path: Path):
        """Empty icon values should fail validation."""
        from scripts.validators.validate_docs import validate_icon_format

        is_valid, icon, error = validate_icon_format("")
        assert is_valid is False

        is_valid, icon, error = validate_icon_format("''")
        assert is_valid is False


@pytest.mark.xdist_group(name="validate_docs_icons")
class TestIconRegistry:
    """Test icon registry contents."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_icon_registry_contains_common_icons(self):
        """Registry should contain commonly used Font Awesome 6.x icons."""
        from scripts.validators.validate_docs import get_valid_fontawesome_icons

        valid_icons = get_valid_fontawesome_icons()

        # Common icons that should be in Font Awesome 6.x (removed shield-check - not in FA6)
        common_icons = {
            "rocket",
            "shield",
            "shield-halved",
            "key",
            "lock",
            "database",
            "chart-line",
            "code",
            "book",
            "book-open",
            "file-lines",
            "docker",
            "dharmachakra",
            "google",
            "aws",
            "microsoft",
            "cubes",
            "tag",
            "clipboard-check",
            "life-ring",
            "arrow-up-right-dots",
            "diagram-project",
            "plug",
            "microchip",
            "scale-balanced",
            "clock",
            "flask",
            "bug",
            "bolt",
            "brain",
            "robot",
            "wrench",
            "server",
            "infinity",
            "layer-group",
            "sitemap",
        }
        for icon in common_icons:
            assert icon in valid_icons, f"Icon '{icon}' should be in Font Awesome 6.x registry"

    def test_icon_registry_is_set(self):
        """Registry should be a set for O(1) lookup."""
        from scripts.validators.validate_docs import get_valid_fontawesome_icons

        valid_icons = get_valid_fontawesome_icons()
        assert isinstance(valid_icons, (set, frozenset))

    def test_icon_registry_not_empty(self):
        """Registry should not be empty."""
        from scripts.validators.validate_docs import get_valid_fontawesome_icons

        valid_icons = get_valid_fontawesome_icons()
        assert len(valid_icons) > 0


@pytest.mark.xdist_group(name="validate_docs_icons")
class TestADRIconValidation:
    """Test ADR-specific icon validation."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_adr_file_requires_icon(self, tmp_path: Path):
        """ADR files in docs/architecture/ should require icons."""
        from scripts.validators.validate_docs import validate_adr_has_icon

        # ADR file without icon should fail
        adr_content = """---
title: "1. Test ADR"
description: "Architecture Decision Record: 1. Test ADR"
---
# Content
"""
        adr_file = tmp_path / "docs" / "architecture" / "adr-0001-test.mdx"
        adr_file.parent.mkdir(parents=True, exist_ok=True)
        adr_file.write_text(adr_content)

        is_valid, error = validate_adr_has_icon(adr_file)
        assert is_valid is False
        assert "missing icon" in error.lower()

    def test_adr_file_with_icon_passes(self, tmp_path: Path):
        """ADR files with icons should pass validation."""
        from scripts.validators.validate_docs import validate_adr_has_icon

        # ADR file with icon should pass
        adr_content = """---
title: "1. Test ADR"
description: "Architecture Decision Record: 1. Test ADR"
icon: 'file-lines'
---
# Content
"""
        adr_file = tmp_path / "docs" / "architecture" / "adr-0001-test.mdx"
        adr_file.parent.mkdir(parents=True, exist_ok=True)
        adr_file.write_text(adr_content)

        is_valid, error = validate_adr_has_icon(adr_file)
        assert is_valid is True
        assert error is None

    def test_non_adr_file_does_not_require_icon(self, tmp_path: Path):
        """Non-ADR files should not require icons (for now)."""
        from scripts.validators.validate_docs import validate_adr_has_icon

        # Non-ADR file without icon should pass (icon not required for all files)
        content = """---
title: "Some Guide"
description: "A guide document"
---
# Content
"""
        guide_file = tmp_path / "docs" / "guides" / "some-guide.mdx"
        guide_file.parent.mkdir(parents=True, exist_ok=True)
        guide_file.write_text(content)

        is_valid, error = validate_adr_has_icon(guide_file)
        assert is_valid is True


@pytest.mark.xdist_group(name="validate_docs_icons")
class TestIconValidationIntegration:
    """Integration tests for icon validation in MDX files."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_validate_mdx_files_catches_double_quotes(self, tmp_path: Path):
        """validate_mdx_files should catch double-quoted icons as errors."""
        from scripts.validators.validate_docs import validate_mdx_files

        # Create docs directory with a file using double quotes
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        mdx_file = docs_dir / "test.mdx"
        mdx_file.write_text("""---
title: "Test"
description: "A test"
icon: "rocket"
---
# Content
""")

        result = validate_mdx_files(docs_dir, validate_icons=True)
        assert result.is_valid is False
        assert len(result.icon_errors) > 0

    def test_validate_mdx_files_passes_valid_icons(self, tmp_path: Path):
        """validate_mdx_files should pass files with valid icons."""
        from scripts.validators.validate_docs import validate_mdx_files

        # Create docs directory with a file using single quotes
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        mdx_file = docs_dir / "test.mdx"
        mdx_file.write_text("""---
title: "Test"
description: "A test"
icon: 'rocket'
---
# Content
""")

        result = validate_mdx_files(docs_dir, validate_icons=True)
        # Should have no icon errors (might have other issues but not icons)
        assert len(result.icon_errors) == 0

    def test_validate_mdx_files_catches_missing_adr_icons(self, tmp_path: Path):
        """validate_mdx_files should catch ADR files missing icons."""
        from scripts.validators.validate_docs import validate_mdx_files

        # Create docs/architecture directory with ADR missing icon
        arch_dir = tmp_path / "docs" / "architecture"
        arch_dir.mkdir(parents=True)
        adr_file = arch_dir / "adr-0001-test.mdx"
        adr_file.write_text("""---
title: "1. Test ADR"
description: "Architecture Decision Record"
---
# Content
""")

        result = validate_mdx_files(tmp_path / "docs", validate_icons=True)
        assert result.is_valid is False
        assert len(result.icon_errors) > 0
        # Should mention missing icon
        assert any("missing" in str(e).lower() for e in result.icon_errors)
