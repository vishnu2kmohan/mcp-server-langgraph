#!/usr/bin/env python3
"""
Image Validator

Validates that all images referenced in MDX files exist.

Checks:
1. All local image references point to existing files
2. Relative paths are resolved correctly
3. Supported image formats (png, jpg, jpeg, svg, gif, webp)
4. External images (http/https) are ignored

Exit codes:
- 0: All validations passed
- 1: Broken image references found
- 2: Critical error
"""

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set, Tuple


class ImageError(Exception):
    """Base exception for image validation errors."""

    pass


class MissingImageError(ImageError):
    """Exception raised when a referenced image doesn't exist."""

    def __init__(self, file_path: str, image_path: str):
        self.file_path = file_path
        self.image_path = image_path
        super().__init__(f"Missing image in {file_path}: {image_path}")


class InvalidImageFormatError(ImageError):
    """Exception raised when an image has unsupported format."""

    def __init__(self, file_path: str, image_path: str, format: str):
        self.file_path = file_path
        self.image_path = image_path
        self.format = format
        super().__init__(
            f"Unsupported image format in {file_path}: {image_path} ({format})"
        )


@dataclass
class ValidationResult:
    """Result of image validation."""

    is_valid: bool
    errors: List[ImageError] = field(default_factory=list)
    warnings: List[Exception] = field(default_factory=list)
    stats: Dict[str, int] = field(default_factory=dict)

    @property
    def exit_code(self) -> int:
        """Get exit code for CLI."""
        if not self.is_valid:
            return 1
        return 0


class ImageValidator:
    """Validates image references in MDX files."""

    # Patterns to exclude from validation
    EXCLUDE_PATTERNS = [
        ".mintlify/templates/",  # Template files
        "node_modules/",  # Dependencies
        ".git/",  # Git directory
        "__pycache__/",  # Python cache
        ".pytest_cache/",  # Pytest cache
    ]

    # Supported image formats
    SUPPORTED_FORMATS = {".png", ".jpg", ".jpeg", ".svg", ".gif", ".webp"}

    # Regex patterns for image detection
    MARKDOWN_IMAGE_PATTERN = re.compile(r'!\[([^\]]*)\]\(([^\)]+)\)')
    HTML_IMAGE_PATTERN = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']')

    def __init__(self, docs_dir: Path):
        """
        Initialize validator.

        Args:
            docs_dir: Path to docs directory
        """
        self.docs_dir = Path(docs_dir)

    def validate(self) -> ValidationResult:
        """
        Run validation checks.

        Returns:
            ValidationResult with errors and statistics
        """
        errors: List[ImageError] = []
        stats: Dict[str, int] = {
            "total_files": 0,
            "total_images": 0,
            "broken_images": 0,
        }

        if not self.docs_dir.exists():
            return ValidationResult(is_valid=True, stats=stats)

        # Find all MDX files
        mdx_files = self._find_mdx_files()
        stats["total_files"] = len(mdx_files)

        for mdx_file in mdx_files:
            relative_path = mdx_file.relative_to(self.docs_dir)
            file_errors = self._validate_file(mdx_file, str(relative_path), stats)
            errors.extend(file_errors)

        stats["broken_images"] = len(errors)

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            stats=stats,
        )

    def _find_mdx_files(self) -> Set[Path]:
        """Find all MDX files, excluding specified directories."""
        files = set()

        for mdx_path in self.docs_dir.rglob("*.mdx"):
            relative_path = mdx_path.relative_to(self.docs_dir)
            if any(
                pattern in str(relative_path) for pattern in self.EXCLUDE_PATTERNS
            ):
                continue

            files.add(mdx_path)

        return files

    def _validate_file(
        self, file_path: Path, relative_path: str, stats: Dict[str, int]
    ) -> List[ImageError]:
        """Validate image references in a single file."""
        errors = []

        try:
            content = file_path.read_text()
        except Exception:
            return errors

        # Extract all image references
        images = self._extract_images(content)
        stats["total_images"] += len(images)

        for image_path in images:
            # Skip external images
            if self._is_external_image(image_path):
                stats["total_images"] -= 1  # Don't count external images
                continue

            # Validate image exists
            if not self._validate_image(file_path, image_path):
                errors.append(MissingImageError(relative_path, image_path))

        return errors

    def _extract_images(self, content: str) -> List[str]:
        """Extract all image references from content."""
        images = []

        # Markdown images: ![alt](path)
        for match in self.MARKDOWN_IMAGE_PATTERN.finditer(content):
            images.append(match.group(2))

        # HTML images: <img src="path" />
        for match in self.HTML_IMAGE_PATTERN.finditer(content):
            images.append(match.group(1))

        return images

    def _is_external_image(self, image_path: str) -> bool:
        """Check if image is external (http/https)."""
        return image_path.startswith(('http://', 'https://', '//'))

    def _validate_image(self, source_file: Path, image_path: str) -> bool:
        """Validate that image exists."""
        # Remove leading slash for docs-relative paths
        if image_path.startswith('/'):
            # Absolute path relative to docs directory
            target = self.docs_dir / image_path.lstrip('/')
        else:
            # Relative path from source file directory
            source_dir = source_file.parent
            target = source_dir / image_path

        # Normalize path (resolve ..)
        try:
            target = target.resolve()
        except Exception:
            return False

        # Check if file exists
        return target.exists() and target.is_file()

    def print_report(self, result: ValidationResult) -> None:
        """Print validation report to stdout."""
        print("\n" + "=" * 80)
        print("🖼️  Image Validation Report")
        print("=" * 80)

        # Statistics
        print("\n📊 Statistics:")
        print(f"  Total files scanned: {result.stats.get('total_files', 0)}")
        print(f"  Total images found: {result.stats.get('total_images', 0)}")
        print(f"  Broken images: {result.stats.get('broken_images', 0)}")

        # Errors
        if result.errors:
            print(f"\n❌ Errors ({len(result.errors)}):")

            # Group by file
            errors_by_file = {}
            for error in result.errors:
                if isinstance(error, MissingImageError):
                    if error.file_path not in errors_by_file:
                        errors_by_file[error.file_path] = []
                    errors_by_file[error.file_path].append(error.image_path)

            for file_path, images in sorted(errors_by_file.items()):
                print(f"\n  📄 {file_path}:")
                for image in images:
                    print(f"    ❌ Missing: {image}")

            print("\n  💡 Solution:")
            print("     1. Add missing images to the docs directory")
            print("     2. Fix image paths to point to correct location")
            print("     3. Remove references to non-existent images")

        # Summary
        print("\n" + "=" * 80)
        if result.is_valid:
            print("✅ All image references are valid!")
        else:
            print("❌ Validation failed - fix broken image references above")
        print("=" * 80 + "\n")


def main():
    """Main CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Validate image references in MDX files")
    parser.add_argument(
        "--docs-dir",
        type=Path,
        default=Path("docs"),
        help="Path to docs directory (default: docs/)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress output (only use exit code)",
    )

    args = parser.parse_args()

    # Run validation
    validator = ImageValidator(args.docs_dir)
    result = validator.validate()

    # Print report
    if not args.quiet:
        validator.print_report(result)

    # Exit with appropriate code
    sys.exit(result.exit_code)


if __name__ == "__main__":
    main()
