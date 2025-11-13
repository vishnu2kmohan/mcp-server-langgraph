"""
Unit tests for image validator.

Tests validate that:
1. All images referenced in MDX files exist
2. Image paths are correct (relative or absolute)
3. Image formats are supported
4. Broken image references are detected
"""

from pathlib import Path

import pytest

from scripts.validators.image_validator import ImageError, ImageValidator, InvalidImageFormatError, MissingImageError


class TestImageValidator:
    """Test suite for ImageValidator."""

    @pytest.fixture
    def validator(self, tmp_path):
        """Create validator with temporary directory."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        return ImageValidator(docs_dir)

    def test_valid_images_pass(self, tmp_path):
        """Test that MDX files with valid image references pass."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        images_dir = docs_dir / "images"
        images_dir.mkdir()

        # Create test image
        (images_dir / "test.png").write_bytes(b"PNG")

        # Create MDX file with valid image reference
        (docs_dir / "page.mdx").write_text(
            """---
title: "Test"
description: "Test"
---

![Test Image](/images/test.png)
"""
        )

        # Act
        validator = ImageValidator(docs_dir)
        result = validator.validate()

        # Assert
        assert result.is_valid
        assert len(result.errors) == 0
        assert result.stats["total_images"] == 1
        assert result.stats["broken_images"] == 0

    def test_missing_image_detected(self, tmp_path):
        """Test that missing images are detected."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        (docs_dir / "page.mdx").write_text(
            """---
title: "Test"
description: "Test"
---

![Missing Image](/images/missing.png)
"""
        )

        # Act
        validator = ImageValidator(docs_dir)
        result = validator.validate()

        # Assert
        assert not result.is_valid
        assert len(result.errors) == 1
        assert isinstance(result.errors[0], MissingImageError)
        assert "missing.png" in str(result.errors[0])

    def test_relative_image_paths(self, tmp_path):
        """Test that relative image paths are resolved correctly."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        guides_dir = docs_dir / "guides"
        guides_dir.mkdir()
        images_dir = docs_dir / "images"
        images_dir.mkdir()

        (images_dir / "diagram.png").write_bytes(b"PNG")

        (guides_dir / "setup.mdx").write_text(
            """---
title: "Setup"
description: "Setup guide"
---

![Diagram](../images/diagram.png)
"""
        )

        # Act
        validator = ImageValidator(docs_dir)
        result = validator.validate()

        # Assert
        assert result.is_valid
        assert len(result.errors) == 0

    def test_multiple_images_in_file(self, tmp_path):
        """Test that all images in a file are validated."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        images_dir = docs_dir / "images"
        images_dir.mkdir()

        (images_dir / "img1.png").write_bytes(b"PNG")
        (images_dir / "img2.jpg").write_bytes(b"JPG")

        (docs_dir / "page.mdx").write_text(
            """---
title: "Test"
description: "Test"
---

![Image 1](/images/img1.png)
![Image 2](/images/img2.jpg)
![Missing](/images/missing.png)
"""
        )

        # Act
        validator = ImageValidator(docs_dir)
        result = validator.validate()

        # Assert
        assert not result.is_valid
        assert len(result.errors) == 1  # Only missing.png
        assert result.stats["total_images"] == 3
        assert result.stats["broken_images"] == 1

    def test_template_files_excluded(self, tmp_path):
        """Test that template files are excluded from validation."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        templates_dir = docs_dir / ".mintlify" / "templates"
        templates_dir.mkdir(parents=True)

        (templates_dir / "template.mdx").write_text(
            """---
title: "Template"
---

![Template Image](/images/template.png)
"""
        )

        # Act
        validator = ImageValidator(docs_dir)
        result = validator.validate()

        # Assert
        assert result.is_valid  # Templates excluded
        assert result.stats["total_files"] == 0

    def test_mdx_image_syntax(self, tmp_path):
        """Test that MDX-specific image syntax is supported."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        images_dir = docs_dir / "images"
        images_dir.mkdir()

        (images_dir / "logo.svg").write_bytes(b"SVG")

        (docs_dir / "page.mdx").write_text(
            """---
title: "Test"
description: "Test"
---

<img src="/images/logo.svg" alt="Logo" />
"""
        )

        # Act
        validator = ImageValidator(docs_dir)
        result = validator.validate()

        # Assert
        assert result.is_valid
        assert result.stats["total_images"] == 1

    def test_supported_formats(self, tmp_path):
        """Test that common image formats are supported."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        images_dir = docs_dir / "images"
        images_dir.mkdir()

        # Create images with different formats
        (images_dir / "test.png").write_bytes(b"PNG")
        (images_dir / "test.jpg").write_bytes(b"JPG")
        (images_dir / "test.jpeg").write_bytes(b"JPEG")
        (images_dir / "test.svg").write_bytes(b"SVG")
        (images_dir / "test.gif").write_bytes(b"GIF")
        (images_dir / "test.webp").write_bytes(b"WEBP")

        (docs_dir / "page.mdx").write_text(
            """---
title: "Test"
description: "Test"
---

![PNG](/images/test.png)
![JPG](/images/test.jpg)
![JPEG](/images/test.jpeg)
![SVG](/images/test.svg)
![GIF](/images/test.gif)
![WEBP](/images/test.webp)
"""
        )

        # Act
        validator = ImageValidator(docs_dir)
        result = validator.validate()

        # Assert
        assert result.is_valid
        assert result.stats["total_images"] == 6

    def test_external_images_ignored(self, tmp_path):
        """Test that external HTTP(S) images are ignored."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        (docs_dir / "page.mdx").write_text(
            """---
title: "Test"
description: "Test"
---

![External](https://example.com/image.png)
![Also External](http://example.com/logo.svg)
"""
        )

        # Act
        validator = ImageValidator(docs_dir)
        result = validator.validate()

        # Assert
        assert result.is_valid  # External images not validated
        assert result.stats["total_images"] == 0  # External images not counted

    def test_statistics_accurate(self, tmp_path):
        """Test that statistics are accurately collected."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        images_dir = docs_dir / "images"
        images_dir.mkdir()

        (images_dir / "valid.png").write_bytes(b"PNG")

        (docs_dir / "page1.mdx").write_text(
            """---
title: "Page 1"
description: "Test"
---

![Valid](/images/valid.png)
"""
        )

        (docs_dir / "page2.mdx").write_text(
            """---
title: "Page 2"
description: "Test"
---

![Missing](/images/missing.png)
![Also Missing](/images/missing2.png)
"""
        )

        # Act
        validator = ImageValidator(docs_dir)
        result = validator.validate()

        # Assert
        assert result.stats["total_files"] == 2
        assert result.stats["total_images"] == 3
        assert result.stats["broken_images"] == 2

    def test_nested_directories(self, tmp_path):
        """Test that images in nested directories are validated."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        nested_images = docs_dir / "guides" / "images"
        nested_images.mkdir(parents=True)

        (nested_images / "nested.png").write_bytes(b"PNG")

        guides_dir = docs_dir / "guides"
        (guides_dir / "page.mdx").write_text(
            """---
title: "Guide"
description: "Test"
---

![Nested](images/nested.png)
"""
        )

        # Act
        validator = ImageValidator(docs_dir)
        result = validator.validate()

        # Assert
        assert result.is_valid
        assert result.stats["total_images"] == 1
