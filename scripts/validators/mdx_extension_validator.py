#!/usr/bin/env python3
"""
MDX Extension Validator

Validates that all documentation files in docs/ directory use .mdx extension.
This prevents the issue where .md files in docs/ are not properly rendered
by Mintlify.

Exit codes:
- 0: All validations passed
- 1: Invalid .md files found in docs/
- 2: Critical error (missing docs directory)
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path


class ExtensionError(Exception):
    """Base exception for extension validation errors."""

    pass


class InvalidExtensionError(ExtensionError):
    """Exception raised when a .md file is found in docs/."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        super().__init__(f"Invalid extension: {file_path} (use .mdx in docs/ directory)")


@dataclass
class ValidationResult:
    """Result of extension validation."""

    is_valid: bool
    errors: list[ExtensionError] = field(default_factory=list)
    warnings: list[Exception] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)

    @property
    def exit_code(self) -> int:
        """Get exit code for CLI."""
        if not self.is_valid:
            return 1
        return 0


class MDXExtensionValidator:
    """Validates that all files in docs/ use .mdx extension."""

    # Patterns to exclude from validation
    EXCLUDE_PATTERNS = [
        ".mintlify/",  # Mintlify internal files
        "node_modules/",  # Dependencies
        ".git/",  # Git directory
        "__pycache__/",  # Python cache
        ".pytest_cache/",  # Pytest cache
        "venv/",  # Virtual environment
        ".venv/",  # Virtual environment
    ]

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
        errors: list[ExtensionError] = []
        stats: dict[str, int] = {
            "total_mdx_files": 0,
            "invalid_md_files": 0,
            "total_files_scanned": 0,
        }

        if not self.docs_dir.exists():
            # If docs dir doesn't exist, return valid (nothing to validate)
            return ValidationResult(is_valid=True, stats=stats)

        # Find all .mdx and .md files
        mdx_files = self._find_files("*.mdx")
        md_files = self._find_files("*.md")

        stats["total_mdx_files"] = len(mdx_files)
        stats["total_files_scanned"] = len(mdx_files) + len(md_files)

        # Check for .md files (these are invalid in docs/)
        for md_file in md_files:
            relative_path = md_file.relative_to(self.docs_dir)
            errors.append(InvalidExtensionError(str(relative_path)))
            stats["invalid_md_files"] += 1

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            stats=stats,
        )

    def _find_files(self, pattern: str) -> set[Path]:
        """
        Find all files matching pattern, excluding specified directories.

        Args:
            pattern: Glob pattern (e.g., "*.md", "*.mdx")

        Returns:
            Set of matching file paths
        """
        files = set()

        for file_path in self.docs_dir.rglob(pattern):
            # Check if file should be excluded
            relative_path = file_path.relative_to(self.docs_dir)
            if any(pattern in str(relative_path) for pattern in self.EXCLUDE_PATTERNS):
                continue

            files.add(file_path)

        return files

    def print_report(self, result: ValidationResult) -> None:
        """Print validation report to stdout."""
        print("\n" + "=" * 80)
        print("📝 MDX Extension Validation Report")
        print("=" * 80)

        # Statistics
        print("\n📊 Statistics:")
        print(f"  Total files scanned: {result.stats.get('total_files_scanned', 0)}")
        print(f"  Valid .mdx files: {result.stats.get('total_mdx_files', 0)}")
        print(f"  Invalid .md files: {result.stats.get('invalid_md_files', 0)}")

        # Errors
        if result.errors:
            print(f"\n❌ Errors ({len(result.errors)}):")
            print("\n  The following files use .md extension instead of .mdx:")
            for error in result.errors:
                if isinstance(error, InvalidExtensionError):
                    print(f"    ❌ {error.file_path}")
            print("\n  💡 Solution: Convert .md files to .mdx or move them outside docs/")
            print("     Example: mv file.md file.mdx")

        # Summary
        print("\n" + "=" * 80)
        if result.is_valid:
            print("✅ All files use correct .mdx extension!")
        else:
            print("❌ Validation failed - found .md files in docs/ directory")
            print("   All documentation files in docs/ must use .mdx extension")
        print("=" * 80 + "\n")


def main():
    """Main CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Validate that all files in docs/ use .mdx extension")
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
    validator = MDXExtensionValidator(args.docs_dir)
    result = validator.validate()

    # Print report
    if not args.quiet:
        validator.print_report(result)

    # Exit with appropriate code
    sys.exit(result.exit_code)


if __name__ == "__main__":
    main()
