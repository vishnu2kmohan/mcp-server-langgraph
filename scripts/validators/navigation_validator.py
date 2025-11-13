#!/usr/bin/env python3
"""
Documentation Navigation Validator

Validates that:
1. All files referenced in docs.json exist
2. All production MDX files are included in navigation
3. No duplicate page references
4. Navigation JSON structure is valid

Exit codes:
- 0: All validations passed
- 1: Validation errors found
- 2: Critical error (invalid JSON, missing docs.json)
"""

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set


class NavigationError(Exception):
    """Base exception for navigation validation errors."""

    pass


class MissingFileError(NavigationError):
    """Exception raised when a referenced file doesn't exist."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        super().__init__(f"Missing file referenced in navigation: {file_path}")


class OrphanedFileError(NavigationError):
    """Exception raised when a production file is not in navigation."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        super().__init__(f"Orphaned file not in navigation: {file_path}")


class InvalidJSONError(NavigationError):
    """Exception raised when docs.json is invalid."""

    pass


class DuplicatePageWarning(Exception):
    """Warning for duplicate page references."""

    def __init__(self, page: str):
        self.page = page
        super().__init__(f"Page referenced multiple times: {page}")


@dataclass
class ValidationResult:
    """Result of navigation validation."""

    is_valid: bool
    errors: List[NavigationError] = field(default_factory=list)
    warnings: List[Exception] = field(default_factory=list)
    stats: Dict[str, int] = field(default_factory=dict)

    @property
    def exit_code(self) -> int:
        """Get exit code for CLI."""
        if not self.is_valid:
            return 1
        return 0


class NavigationValidator:
    """Validates documentation navigation consistency."""

    # Patterns to exclude from orphan detection
    EXCLUDE_PATTERNS = [
        ".mintlify/templates/",  # Template files
        "node_modules/",  # Dependencies
        ".git/",  # Git directory
        "__pycache__/",  # Python cache
        ".pytest_cache/",  # Pytest cache
    ]

    def __init__(self, docs_dir: Path):
        """
        Initialize validator.

        Args:
            docs_dir: Path to docs directory containing docs.json
        """
        self.docs_dir = Path(docs_dir)
        self.docs_json_path = self.docs_dir / "docs.json"

    def validate(self) -> ValidationResult:
        """
        Run all validation checks.

        Returns:
            ValidationResult with errors, warnings, and statistics
        """
        errors: List[NavigationError] = []
        warnings: List[Exception] = []
        stats: Dict[str, int] = {}

        # Load docs.json
        try:
            docs_json = self._load_docs_json()
        except NavigationError as e:
            return ValidationResult(
                is_valid=False,
                errors=[e],
                warnings=[],
                stats={"total_pages": 0, "total_mdx_files": 0},
            )

        # Get all referenced pages
        referenced_pages = self._get_all_referenced_pages(docs_json)
        stats["total_pages"] = len(referenced_pages)

        # Check for duplicate references
        duplicates = self._find_duplicates(referenced_pages)
        for page in duplicates:
            warnings.append(DuplicatePageWarning(page))

        # Get all MDX files
        all_mdx_files = self._get_all_mdx_files()
        stats["total_mdx_files"] = len(all_mdx_files)

        # Check that all referenced files exist
        missing_files = self._find_missing_files(referenced_pages)
        errors.extend([MissingFileError(f) for f in missing_files])
        stats["missing_files"] = len(missing_files)

        # Check for orphaned files (not in navigation)
        orphaned_files = self._find_orphaned_files(all_mdx_files, referenced_pages)
        errors.extend([OrphanedFileError(f) for f in orphaned_files])
        stats["orphaned_files"] = len(orphaned_files)

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            stats=stats,
        )

    def _load_docs_json(self) -> Dict:
        """Load and parse docs.json."""
        if not self.docs_json_path.exists():
            raise InvalidJSONError(f"docs.json not found at {self.docs_json_path}")

        try:
            with open(self.docs_json_path, "r") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise InvalidJSONError(f"Invalid JSON in docs.json: {e}")

    def _get_all_referenced_pages(self, docs_json: Dict) -> List[str]:
        """Extract all page references from docs.json navigation."""
        pages = []

        navigation = docs_json.get("navigation", {})
        tabs = navigation.get("tabs", [])

        for tab in tabs:
            groups = tab.get("groups", [])
            for group in groups:
                group_pages = group.get("pages", [])
                pages.extend(group_pages)

        return pages

    def _get_all_mdx_files(self) -> Set[Path]:
        """Get all MDX files in docs directory, excluding templates."""
        mdx_files = set()

        for mdx_path in self.docs_dir.rglob("*.mdx"):
            # Check if file should be excluded
            relative_path = mdx_path.relative_to(self.docs_dir)
            if any(pattern in str(relative_path) for pattern in self.EXCLUDE_PATTERNS):
                continue

            mdx_files.add(mdx_path)

        return mdx_files

    def _find_missing_files(self, referenced_pages: List[str]) -> List[str]:
        """Find files referenced in navigation that don't exist."""
        missing = []

        for page in referenced_pages:
            file_path = self.docs_dir / f"{page}.mdx"
            if not file_path.exists():
                missing.append(f"{page}.mdx")

        return missing

    def _find_orphaned_files(self, all_mdx_files: Set[Path], referenced_pages: List[str]) -> List[str]:
        """Find MDX files not referenced in navigation."""
        # Convert referenced pages to absolute paths
        referenced_paths = set()
        for page in referenced_pages:
            file_path = self.docs_dir / f"{page}.mdx"
            if file_path.exists():
                referenced_paths.add(file_path)

        # Also exclude docs.json itself
        referenced_paths.add(self.docs_json_path)

        # Find orphaned files
        orphaned = []
        for mdx_file in all_mdx_files:
            if mdx_file not in referenced_paths:
                relative = mdx_file.relative_to(self.docs_dir)
                orphaned.append(str(relative))

        return orphaned

    def _find_duplicates(self, pages: List[str]) -> List[str]:
        """Find duplicate page references."""
        seen = set()
        duplicates = []

        for page in pages:
            if page in seen:
                duplicates.append(page)
            seen.add(page)

        return duplicates

    def print_report(self, result: ValidationResult) -> None:
        """Print validation report to stdout."""
        print("\n" + "=" * 80)
        print("📚 Documentation Navigation Validation Report")
        print("=" * 80)

        # Statistics
        print("\n📊 Statistics:")
        print(f"  Total pages in navigation: {result.stats.get('total_pages', 0)}")
        print(f"  Total MDX files found: {result.stats.get('total_mdx_files', 0)}")
        print(f"  Missing files: {result.stats.get('missing_files', 0)}")
        print(f"  Orphaned files: {result.stats.get('orphaned_files', 0)}")

        # Errors
        if result.errors:
            print(f"\n❌ Errors ({len(result.errors)}):")
            for error in result.errors:
                if isinstance(error, MissingFileError):
                    print(f"  ❌ Missing: {error.file_path}")
                elif isinstance(error, OrphanedFileError):
                    print(f"  ❌ Orphaned: {error.file_path}")
                else:
                    print(f"  ❌ {error}")

        # Warnings
        if result.warnings:
            print(f"\n⚠️  Warnings ({len(result.warnings)}):")
            for warning in result.warnings:
                if isinstance(warning, DuplicatePageWarning):
                    print(f"  ⚠️  Duplicate: {warning.page}")
                else:
                    print(f"  ⚠️  {warning}")

        # Summary
        print("\n" + "=" * 80)
        if result.is_valid:
            print("✅ All validations passed!")
        else:
            print("❌ Validation failed - please fix the errors above")
        print("=" * 80 + "\n")


def main():
    """Main CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Validate documentation navigation consistency")
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
    validator = NavigationValidator(args.docs_dir)
    result = validator.validate()

    # Print report
    if not args.quiet:
        validator.print_report(result)

    # Exit with appropriate code
    sys.exit(result.exit_code)


if __name__ == "__main__":
    main()
