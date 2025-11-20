"""
Unit tests for frontmatter validator.

Tests validate that:
1. All MDX files have valid YAML frontmatter
2. Required fields (title, description) are present
3. Frontmatter is properly formatted
4. Optional fields are validated when present
"""

import gc
import sys
from pathlib import Path

import pytest

# Add scripts directory to path - environment-agnostic
_scripts_dir = Path(__file__).resolve().parent.parent.parent.parent / "scripts"
sys.path.insert(0, str(_scripts_dir))


from validators.frontmatter_validator import (  # noqa: E402
    FrontmatterValidator,
    InvalidYAMLError,
    MissingFrontmatterError,
    MissingRequiredFieldError,
)

# Mark as unit test to ensure it runs in CI
pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="testfrontmattervalidator")
class TestFrontmatterValidator:
    """Test suite for FrontmatterValidator."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def validator(self, tmp_path):
        """Create validator with temporary directory."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        return FrontmatterValidator(docs_dir)

    def test_valid_frontmatter_passes(self, tmp_path):
        """Test that MDX files with valid frontmatter pass."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "valid.mdx").write_text(
            """---
title: "Valid Page"
description: "This is a valid page"
icon: "book"
contentType: "guide"
seoTitle: "Valid Page SEO Title"
seoDescription: "This is a valid page for SEO"
keywords: ["valid", "test", "documentation"]
---

# Valid Page

Content here.
"""
        )

        # Act
        validator = FrontmatterValidator(docs_dir)
        result = validator.validate()

        # Assert
        assert result.is_valid
        assert len(result.errors) == 0
        assert result.stats["total_files"] == 1
        assert result.stats["valid_frontmatter"] == 1

    def test_missing_frontmatter_detected(self, tmp_path):
        """Test that files without frontmatter are detected."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "no-frontmatter.mdx").write_text("# No Frontmatter\n\nJust content.")

        # Act
        validator = FrontmatterValidator(docs_dir)
        result = validator.validate()

        # Assert
        assert not result.is_valid
        assert len(result.errors) == 1
        assert isinstance(result.errors[0], MissingFrontmatterError)

    def test_missing_title_detected(self, tmp_path):
        """Test that missing title field is detected."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "no-title.mdx").write_text(
            """---
description: "Has description but no title"
---

# Content
"""
        )

        # Act
        validator = FrontmatterValidator(docs_dir)
        result = validator.validate()

        # Assert
        assert not result.is_valid
        # Missing: title, icon, contentType, seoTitle, seoDescription, keywords (6 fields)
        assert len(result.errors) == 6
        assert any(isinstance(e, MissingRequiredFieldError) and "title" in str(e).lower() for e in result.errors)

    def test_missing_description_detected(self, tmp_path):
        """Test that missing description field is detected."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "no-desc.mdx").write_text(
            """---
title: "Has title but no description"
---

# Content
"""
        )

        # Act
        validator = FrontmatterValidator(docs_dir)
        result = validator.validate()

        # Assert
        assert not result.is_valid
        # Missing: description, icon, contentType, seoTitle, seoDescription, keywords (6 fields)
        assert len(result.errors) == 6
        assert any(isinstance(e, MissingRequiredFieldError) and "description" in str(e).lower() for e in result.errors)

    def test_invalid_yaml_detected(self, tmp_path):
        """Test that invalid YAML frontmatter is detected."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "bad-yaml.mdx").write_text(
            """---
title: "Unclosed quote
description: Valid description
---

# Content
"""
        )

        # Act
        validator = FrontmatterValidator(docs_dir)
        result = validator.validate()

        # Assert
        assert not result.is_valid
        assert len(result.errors) >= 1
        assert any(isinstance(e, InvalidYAMLError) for e in result.errors)

    def test_empty_title_detected(self, tmp_path):
        """Test that empty title is detected as invalid."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "empty-title.mdx").write_text(
            """---
title: ""
description: "Valid description"
---

# Content
"""
        )

        # Act
        validator = FrontmatterValidator(docs_dir)
        result = validator.validate()

        # Assert
        assert not result.is_valid
        # Missing: title (empty), icon, contentType, seoTitle, seoDescription, keywords (6 fields)
        assert len(result.errors) == 6
        assert any("title" in str(e).lower() for e in result.errors)

    def test_empty_description_detected(self, tmp_path):
        """Test that empty description is detected as invalid."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "empty-desc.mdx").write_text(
            """---
title: "Valid title"
description: ""
---

# Content
"""
        )

        # Act
        validator = FrontmatterValidator(docs_dir)
        result = validator.validate()

        # Assert
        assert not result.is_valid
        # Missing: description (empty), icon, contentType, seoTitle, seoDescription, keywords (6 fields)
        assert len(result.errors) == 6
        assert any("description" in str(e).lower() for e in result.errors)

    def test_template_files_excluded(self, tmp_path):
        """Test that template files are excluded from validation."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        templates_dir = docs_dir / ".mintlify" / "templates"
        templates_dir.mkdir(parents=True)
        (templates_dir / "template.mdx").write_text("# Template without frontmatter")

        # Act
        validator = FrontmatterValidator(docs_dir)
        result = validator.validate()

        # Assert
        assert result.is_valid  # Templates should be excluded
        assert result.stats["total_files"] == 0

    def test_multiple_errors_reported(self, tmp_path):
        """Test that multiple files with errors are all reported."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "file1.mdx").write_text("# No frontmatter 1")
        (docs_dir / "file2.mdx").write_text("# No frontmatter 2")
        (docs_dir / "file3.mdx").write_text(
            """---
title: "Missing description"
---
# Content
"""
        )

        # Act
        validator = FrontmatterValidator(docs_dir)
        result = validator.validate()

        # Assert
        assert not result.is_valid
        # file1: 1 error (no frontmatter)
        # file2: 1 error (no frontmatter)
        # file3: 6 errors (missing description, icon, contentType, seoTitle, seoDescription, keywords)
        assert len(result.errors) == 8

    def test_optional_fields_allowed(self, tmp_path):
        """Test that optional fields are allowed and don't cause errors."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "with-optional.mdx").write_text(
            """---
title: "Page Title"
description: "Page description"
icon: "book"
contentType: "guide"
seoTitle: "Page Title SEO"
seoDescription: "Page description for SEO"
keywords: ["test", "optional"]
author: "Test Author"
date: "2025-01-01"
tags: ["tag1", "tag2"]
---

# Content
"""
        )

        # Act
        validator = FrontmatterValidator(docs_dir)
        result = validator.validate()

        # Assert
        assert result.is_valid

    def test_statistics_accurate(self, tmp_path):
        """Test that statistics are accurately collected."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "valid1.mdx").write_text(
            """---
title: "Valid 1"
description: "Description 1"
icon: "book"
contentType: "guide"
seoTitle: "Valid 1 SEO"
seoDescription: "Description 1 for SEO"
keywords: ["valid", "test"]
---
# Content
"""
        )
        (docs_dir / "valid2.mdx").write_text(
            """---
title: "Valid 2"
description: "Description 2"
icon: "file"
contentType: "tutorial"
seoTitle: "Valid 2 SEO"
seoDescription: "Description 2 for SEO"
keywords: ["valid", "test", "tutorial"]
---
# Content
"""
        )
        (docs_dir / "invalid.mdx").write_text("# No frontmatter")

        # Act
        validator = FrontmatterValidator(docs_dir)
        result = validator.validate()

        # Assert
        assert result.stats["total_files"] == 3
        assert result.stats["valid_frontmatter"] == 2
        assert result.stats["invalid_frontmatter"] == 1

    def test_nested_files_validated(self, tmp_path):
        """Test that files in nested directories are validated."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        nested = docs_dir / "guides" / "advanced"
        nested.mkdir(parents=True)
        (nested / "nested.mdx").write_text("# No frontmatter")

        # Act
        validator = FrontmatterValidator(docs_dir)
        result = validator.validate()

        # Assert
        assert not result.is_valid
        assert len(result.errors) == 1
        assert "guides/advanced/nested.mdx" in str(result.errors[0])
