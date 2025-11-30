#!/usr/bin/env python3
"""
Frontmatter Validator

Validates that all MDX files have valid YAML frontmatter with required fields.

Required fields:
- title: Page title (must be non-empty string)
- description: Page description (must be non-empty string)
- icon: Icon identifier for the page (must be non-empty string)
- contentType: Type of content (must be one of: explanation, reference, tutorial, how-to, guide)

Exit codes:
- 0: All validations passed
- 1: Validation errors found
- 2: Critical error
"""

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml


class FrontmatterError(Exception):
    """Base exception for frontmatter validation errors."""

    pass


class MissingFrontmatterError(FrontmatterError):
    """Exception raised when frontmatter is missing."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        super().__init__(f"Missing frontmatter in {file_path}")


class MissingRequiredFieldError(FrontmatterError):
    """Exception raised when a required field is missing or empty."""

    def __init__(self, file_path: str, field: str):
        self.file_path = file_path
        self.field = field
        super().__init__(f"Missing or empty required field '{field}' in {file_path}")


class InvalidYAMLError(FrontmatterError):
    """Exception raised when frontmatter YAML is invalid."""

    def __init__(self, file_path: str, error: str):
        self.file_path = file_path
        self.yaml_error = error
        super().__init__(f"Invalid YAML in {file_path}: {error}")


class InvalidContentTypeError(FrontmatterError):
    """Exception raised when contentType has an invalid value."""

    def __init__(self, file_path: str, value: str, valid_types: list):
        self.file_path = file_path
        self.value = value
        self.valid_types = valid_types
        super().__init__(f"Invalid contentType '{value}' in {file_path}. Must be one of: {', '.join(valid_types)}")


@dataclass
class ValidationResult:
    """Result of frontmatter validation."""

    is_valid: bool
    errors: list[FrontmatterError] = field(default_factory=list)
    warnings: list[Exception] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)

    @property
    def exit_code(self) -> int:
        """Get exit code for CLI."""
        if not self.is_valid:
            return 1
        return 0


class FrontmatterValidator:
    """Validates MDX file frontmatter."""

    # Required fields in frontmatter
    REQUIRED_FIELDS = ["title", "description", "icon", "contentType", "seoTitle", "seoDescription", "keywords"]

    # Valid content types
    VALID_CONTENT_TYPES = ["explanation", "reference", "tutorial", "how-to", "guide"]

    # Patterns to exclude from validation
    EXCLUDE_PATTERNS = [
        ".mintlify/templates/",  # Template files
        "node_modules/",  # Dependencies
        ".git/",  # Git directory
        "__pycache__/",  # Python cache
        ".pytest_cache/",  # Pytest cache
    ]

    # Regex to extract frontmatter
    FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.MULTILINE | re.DOTALL)

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
        errors: list[FrontmatterError] = []
        stats: dict[str, int] = {
            "total_files": 0,
            "valid_frontmatter": 0,
            "invalid_frontmatter": 0,
        }

        if not self.docs_dir.exists():
            return ValidationResult(is_valid=True, stats=stats)

        # Find all MDX files
        mdx_files = self._find_mdx_files()

        for mdx_file in mdx_files:
            stats["total_files"] += 1
            relative_path = mdx_file.relative_to(self.docs_dir)

            # Validate frontmatter
            file_errors = self._validate_file(mdx_file, str(relative_path))
            if file_errors:
                errors.extend(file_errors)
                stats["invalid_frontmatter"] += 1
            else:
                stats["valid_frontmatter"] += 1

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            stats=stats,
        )

    def _find_mdx_files(self) -> set[Path]:
        """Find all MDX files, excluding specified directories."""
        files = set()

        for mdx_path in self.docs_dir.rglob("*.mdx"):
            # Check if file should be excluded
            relative_path = mdx_path.relative_to(self.docs_dir)
            if any(pattern in str(relative_path) for pattern in self.EXCLUDE_PATTERNS):
                continue

            files.add(mdx_path)

        return files

    def _validate_file(self, file_path: Path, relative_path: str) -> list[FrontmatterError]:
        """
        Validate frontmatter in a single file.

        Args:
            file_path: Absolute path to file
            relative_path: Relative path for error messages

        Returns:
            List of errors found (empty if valid)
        """
        errors = []

        # Read file content
        try:
            content = file_path.read_text()
        except Exception as e:
            errors.append(InvalidYAMLError(relative_path, f"Cannot read file: {e}"))
            return errors

        # Extract frontmatter
        match = self.FRONTMATTER_PATTERN.match(content)
        if not match:
            errors.append(MissingFrontmatterError(relative_path))
            return errors

        frontmatter_text = match.group(1)

        # Parse YAML
        try:
            frontmatter = yaml.safe_load(frontmatter_text)
        except yaml.YAMLError as e:
            errors.append(InvalidYAMLError(relative_path, str(e)))
            return errors

        # Check if frontmatter is a dict
        if not isinstance(frontmatter, dict):
            errors.append(InvalidYAMLError(relative_path, "Frontmatter must be a YAML object"))
            return errors

        # Validate required fields
        for field_name in self.REQUIRED_FIELDS:
            if (
                field_name not in frontmatter
                or not frontmatter[field_name]
                or (isinstance(frontmatter[field_name], str) and not frontmatter[field_name].strip())
            ):
                errors.append(MissingRequiredFieldError(relative_path, field_name))

        # Validate contentType value if present
        if "contentType" in frontmatter and frontmatter["contentType"]:
            content_type = frontmatter["contentType"].strip()
            if content_type not in self.VALID_CONTENT_TYPES:
                errors.append(InvalidContentTypeError(relative_path, content_type, self.VALID_CONTENT_TYPES))

        return errors

    def print_report(self, result: ValidationResult) -> None:
        """Print validation report to stdout."""
        print("\n" + "=" * 80)
        print("📋 Frontmatter Validation Report")
        print("=" * 80)

        # Statistics
        print("\n📊 Statistics:")
        print(f"  Total MDX files: {result.stats.get('total_files', 0)}")
        print(f"  Valid frontmatter: {result.stats.get('valid_frontmatter', 0)}")
        print(f"  Invalid frontmatter: {result.stats.get('invalid_frontmatter', 0)}")

        # Errors
        if result.errors:
            print(f"\n❌ Errors ({len(result.errors)}):")

            # Group errors by type
            missing_fm = [e for e in result.errors if isinstance(e, MissingFrontmatterError)]
            missing_fields = [e for e in result.errors if isinstance(e, MissingRequiredFieldError)]
            invalid_yaml = [e for e in result.errors if isinstance(e, InvalidYAMLError)]
            invalid_content_type = [e for e in result.errors if isinstance(e, InvalidContentTypeError)]

            if missing_fm:
                print(f"\n  Missing frontmatter ({len(missing_fm)}):")
                for error in missing_fm:
                    print(f"    ❌ {error.file_path}")

            if missing_fields:
                print(f"\n  Missing required fields ({len(missing_fields)}):")
                for error in missing_fields:
                    print(f"    ❌ {error.file_path}: missing '{error.field}'")

            if invalid_yaml:
                print(f"\n  Invalid YAML ({len(invalid_yaml)}):")
                for error in invalid_yaml:
                    print(f"    ❌ {error.file_path}")

            if invalid_content_type:
                print(f"\n  Invalid contentType ({len(invalid_content_type)}):")
                for error in invalid_content_type:
                    print(f"    ❌ {error.file_path}: '{error.value}' (valid: {', '.join(error.valid_types)})")

            print("\n  💡 Solution: Add frontmatter to MDX files:")
            print("     ---")
            print('     title: "Page Title"')
            print('     description: "Page description"')
            print('     icon: "book-open"')
            print('     contentType: "explanation"')
            print("     ---")

        # Summary
        print("\n" + "=" * 80)
        if result.is_valid:
            print("✅ All MDX files have valid frontmatter!")
        else:
            print("❌ Validation failed - fix frontmatter errors above")
        print("=" * 80 + "\n")


def main():
    """Main CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Validate MDX file frontmatter")
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
    validator = FrontmatterValidator(args.docs_dir)
    result = validator.validate()

    # Print report
    if not args.quiet:
        validator.print_report(result)

    # Exit with appropriate code
    sys.exit(result.exit_code)


if __name__ == "__main__":
    main()
