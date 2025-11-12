#!/usr/bin/env python3
"""
Code Block Language Validator

Validates that all fenced code blocks have language identifiers.

Checks:
1. All code blocks (```) have language tags
2. Inline code (`code`) is ignored
3. Code blocks in MDX components are validated

Exit codes:
- 0: All validations passed
- 1: Code blocks without language tags found
- 2: Critical error
"""

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set, Tuple


class CodeBlockError(Exception):
    """Base exception for code block validation errors."""

    pass


class MissingLanguageError(CodeBlockError):
    """Exception raised when a code block is missing a language tag."""

    def __init__(self, file_path: str, line_number: int, snippet: str):
        self.file_path = file_path
        self.line_number = line_number
        self.snippet = snippet
        super().__init__(
            f"Code block without language in {file_path} at line {line_number}"
        )


@dataclass
class ValidationResult:
    """Result of code block validation."""

    is_valid: bool
    errors: List[CodeBlockError] = field(default_factory=list)
    warnings: List[Exception] = field(default_factory=list)
    stats: Dict[str, int] = field(default_factory=dict)

    @property
    def exit_code(self) -> int:
        """Get exit code for CLI."""
        if not self.is_valid:
            return 1
        return 0


class CodeBlockValidator:
    """Validates code block language tags in MDX files."""

    # Patterns to exclude from validation
    EXCLUDE_PATTERNS = [
        ".mintlify/templates/",  # Template files
        "node_modules/",  # Dependencies
        ".git/",  # Git directory
        "__pycache__/",  # Python cache
        ".pytest_cache/",  # Pytest cache
    ]

    # Regex pattern for fenced code blocks
    # Matches: ```language or ``` (without language)
    # Also handles attributes like ```python {1,3-5}
    CODE_BLOCK_PATTERN = re.compile(
        r'^(\s*)```(\w+)?([^\n]*)\n(.*?)^(\s*)```',
        re.MULTILINE | re.DOTALL
    )

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
        errors: List[CodeBlockError] = []
        stats: Dict[str, int] = {
            "total_files": 0,
            "total_code_blocks": 0,
            "blocks_without_language": 0,
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

        stats["blocks_without_language"] = len(errors)

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
    ) -> List[CodeBlockError]:
        """Validate code blocks in a single file."""
        errors = []

        try:
            content = file_path.read_text()
        except Exception:
            return errors

        # Find all code blocks
        for match in self.CODE_BLOCK_PATTERN.finditer(content):
            stats["total_code_blocks"] += 1

            indent = match.group(1)
            language = match.group(2)
            attributes = match.group(3)
            code_content = match.group(4)

            # Check if language is missing
            if not language or language.strip() == '':
                # Get line number (approximate)
                line_number = content[:match.start()].count('\n') + 1

                # Get snippet of code (first 50 chars)
                snippet = code_content[:50].strip()
                if len(code_content) > 50:
                    snippet += "..."

                errors.append(
                    MissingLanguageError(relative_path, line_number, snippet)
                )

        return errors

    def print_report(self, result: ValidationResult) -> None:
        """Print validation report to stdout."""
        print("\n" + "=" * 80)
        print("💻 Code Block Language Validation Report")
        print("=" * 80)

        # Statistics
        print("\n📊 Statistics:")
        print(f"  Total files scanned: {result.stats.get('total_files', 0)}")
        print(f"  Total code blocks: {result.stats.get('total_code_blocks', 0)}")
        print(
            f"  Blocks without language: {result.stats.get('blocks_without_language', 0)}"
        )

        # Errors
        if result.errors:
            print(f"\n❌ Errors ({len(result.errors)}):")

            # Group by file
            errors_by_file = {}
            for error in result.errors:
                if isinstance(error, MissingLanguageError):
                    if error.file_path not in errors_by_file:
                        errors_by_file[error.file_path] = []
                    errors_by_file[error.file_path].append(
                        (error.line_number, error.snippet)
                    )

            for file_path, blocks in sorted(errors_by_file.items()):
                print(f"\n  📄 {file_path}:")
                for line_number, snippet in blocks:
                    print(f"    ❌ Line {line_number}: {snippet}")

            print("\n  💡 Solution:")
            print("     Add language identifier to code blocks:")
            print("     ```python")
            print("     # Your code here")
            print("     ```")
            print("\n     Common languages:")
            print(
                "     python, javascript, typescript, bash, yaml, json, sql, dockerfile"
            )

        # Summary
        print("\n" + "=" * 80)
        if result.is_valid:
            print("✅ All code blocks have language identifiers!")
        else:
            print("❌ Validation failed - add language tags to code blocks above")
        print("=" * 80 + "\n")


def main():
    """Main CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate code block language tags in MDX files"
    )
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
    validator = CodeBlockValidator(args.docs_dir)
    result = validator.validate()

    # Print report
    if not args.quiet:
        validator.print_report(result)

    # Exit with appropriate code
    sys.exit(result.exit_code)


if __name__ == "__main__":
    main()
