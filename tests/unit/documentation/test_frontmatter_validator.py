"""
Unit tests for frontmatter validator.

Tests validate that:
1. All MDX files have valid YAML frontmatter
2. Required fields (title, description) are present
3. Frontmatter is properly formatted
4. Optional fields are validated when present
"""

import pytest
from pathlib import Path
from scripts.validators.frontmatter_validator import (
    FrontmatterValidator,
    FrontmatterError,
    MissingFrontmatterError,
    MissingRequiredFieldError,
    InvalidYAMLError,
)


class TestFrontmatterValidator:
    """Test suite for FrontmatterValidator."""

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
        assert len(result.errors) == 1
        assert isinstance(result.errors[0], MissingRequiredFieldError)
        assert "title" in str(result.errors[0]).lower()

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
        assert len(result.errors) == 1
        assert isinstance(result.errors[0], MissingRequiredFieldError)
        assert "description" in str(result.errors[0]).lower()

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
        assert len(result.errors) == 1
        assert "title" in str(result.errors[0]).lower()
        assert "empty" in str(result.errors[0]).lower()

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
        assert len(result.errors) == 1
        assert "description" in str(result.errors[0]).lower()

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
        assert len(result.errors) == 3

    def test_optional_fields_allowed(self, tmp_path):
        """Test that optional fields are allowed and don't cause errors."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "with-optional.mdx").write_text(
            """---
title: "Page Title"
description: "Page description"
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
---
# Content
"""
        )
        (docs_dir / "valid2.mdx").write_text(
            """---
title: "Valid 2"
description: "Description 2"
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
