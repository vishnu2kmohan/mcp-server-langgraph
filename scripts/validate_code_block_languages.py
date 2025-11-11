#!/usr/bin/env python3
"""
Validate that all code blocks in Markdown/MDX files have language tags.

This script is designed to run as a pre-commit hook to prevent untagged
code blocks from being committed.

Usage:
    python scripts/validate_code_block_languages.py [files...]

Exit codes:
    0 - All code blocks have language tags
    1 - Found code blocks without language tags
"""

import argparse
import re
import sys
from pathlib import Path
from typing import List, Tuple


class CodeBlockValidator:
    """Validate language tags in Markdown/MDX code blocks."""

    # Regex to find code blocks without language tags
    UNTAGGED_BLOCK_PATTERN = re.compile(r"^```\s*$", re.MULTILINE)

    def __init__(self):
        """Initialize validator."""
        self.issues: List[Tuple[Path, int, str]] = []

    def validate_file(self, file_path: Path) -> bool:
        """
        Validate a single Markdown/MDX file.

        Args:
            file_path: Path to the file

        Returns:
            True if file is valid (all code blocks tagged)
        """
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            print(f"❌ Error reading {file_path}: {e}", file=sys.stderr)
            return False

        lines = content.split("\n")
        is_valid = True

        for i, line in enumerate(lines, start=1):
            if self.UNTAGGED_BLOCK_PATTERN.match(line):
                # Found untagged code block
                self.issues.append((file_path, i, line.strip()))
                is_valid = False

        return is_valid

    def print_issues(self):
        """Print validation issues."""
        if not self.issues:
            return

        print("\n❌ Found code blocks without language tags:\n", file=sys.stderr)

        for file_path, line_num, line_content in self.issues:
            print(f"{file_path}:{line_num}: {line_content}", file=sys.stderr)

        print(f"\n💡 Tip: Run the following command to auto-fix:", file=sys.stderr)
        print("    python scripts/add_code_block_languages.py <files>", file=sys.stderr)

    def has_issues(self) -> bool:
        """Check if any issues were found."""
        return len(self.issues) > 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Validate code block language tags in Markdown/MDX files")
    parser.add_argument("files", nargs="+", type=Path, help="Markdown/MDX files to validate")

    args = parser.parse_args()

    # Filter to only Markdown/MDX files
    md_files = [f for f in args.files if f.suffix in {".md", ".mdx"}]

    if not md_files:
        print("⏭️  No Markdown files to validate", file=sys.stderr)
        sys.exit(0)

    # Validate files
    validator = CodeBlockValidator()
    all_valid = True

    for file_path in md_files:
        if not validator.validate_file(file_path):
            all_valid = False

    # Print results
    if all_valid:
        print(f"✅ All code blocks have language tags ({len(md_files)} files checked)")
        sys.exit(0)
    else:
        validator.print_issues()
        print(f"\n❌ Validation failed: {len(validator.issues)} untagged code blocks found", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
