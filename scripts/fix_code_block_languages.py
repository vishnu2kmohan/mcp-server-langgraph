#!/usr/bin/env python3
"""
Automatically add language tags to code blocks in markdown files.

This script fixes markdown code blocks that are missing language specifiers,
which improves syntax highlighting and documentation quality.

Usage:
    python scripts/fix_code_block_languages.py [--dry-run] [--file FILE] [--dir DIR]

Examples:
    # Dry run (show changes without applying)
    python scripts/fix_code_block_languages.py --dry-run

    # Fix specific file
    python scripts/fix_code_block_languages.py --file README.md

    # Fix all markdown files in directory
    python scripts/fix_code_block_languages.py --dir docs/

    # Fix all markdown files in project (default)
    python scripts/fix_code_block_languages.py
"""

import argparse
import re
import sys
from pathlib import Path
from typing import List, Tuple


class CodeBlockFixer:
    """Fixes code blocks missing language tags in markdown files"""

    # Common patterns to detect language from code content
    LANGUAGE_PATTERNS = {
        "python": [
            r"^import\s+\w+",
            r"^from\s+\w+\s+import",
            r"^def\s+\w+\(",
            r"^class\s+\w+",
            r"^@\w+",  # Decorators
            r"^\s+yield\s+",
            r"^\s+return\s+",
        ],
        "bash": [
            r"^#!\s*/bin/(bash|sh)",
            r"^\$\s+",  # Shell prompt
            r"^(sudo|apt|yum|brew|pip|npm|docker|git)\s+",
            r"^(echo|cd|ls|pwd|mkdir|rm|cp|mv)\s+",
            r"^export\s+\w+=",
        ],
        "javascript": [
            r"^(const|let|var)\s+\w+\s*=",
            r"^function\s+\w+\(",
            r"^class\s+\w+\s*{",
            r"^import\s+.+\s+from\s+['\"]",
            r"^export\s+(default|const|function|class)",
        ],
        "typescript": [
            r"^interface\s+\w+\s*{",
            r"^type\s+\w+\s*=",
            r"^enum\s+\w+\s*{",
            r":\s*(string|number|boolean|void)\s*[;=)]",
        ],
        "yaml": [
            r"^\w+:",
            r"^-\s+\w+:",
            r"^\s+-\s+name:",
            r"^version:\s+",
            r"^apiVersion:",
        ],
        "json": [
            r"^\s*\{",
            r"^\s*\[",
            r'"\w+":\s*["\[{]',
        ],
        "sql": [
            r"^(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP)\s+",
            r"^(FROM|WHERE|JOIN|GROUP BY|ORDER BY)\s+",
        ],
        "dockerfile": [
            r"^FROM\s+",
            r"^RUN\s+",
            r"^COPY\s+",
            r"^ENV\s+\w+=",
            r"^WORKDIR\s+",
        ],
        "go": [
            r"^package\s+\w+",
            r"^func\s+\w+\(",
            r"^type\s+\w+\s+struct\s*{",
            r"^import\s+\(",
        ],
        "rust": [
            r"^fn\s+\w+\(",
            r"^pub\s+(fn|struct|enum|trait)",
            r"^use\s+\w+::",
            r"^impl\s+",
        ],
        "xml": [
            r"^<\?xml",
            r"^<\w+[>\s]",
        ],
        "html": [
            r"^<!DOCTYPE\s+html",
            r"^<html",
            r"^<head",
            r"^<body",
        ],
    }

    def __init__(self, dry_run: bool = False):
        """
        Initialize the fixer.

        Args:
            dry_run: If True, show changes without applying them
        """
        self.dry_run = dry_run
        self.stats = {
            "files_processed": 0,
            "files_modified": 0,
            "blocks_fixed": 0,
            "blocks_by_language": {},
        }

    def detect_language(self, code: str) -> str:
        """
        Detect programming language from code content.

        Args:
            code: Code block content

        Returns:
            Detected language or empty string if unknown
        """
        # Check patterns for each language
        for language, patterns in self.LANGUAGE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, code, re.MULTILINE | re.IGNORECASE):
                    return language

        # Default heuristics
        if code.strip().startswith("{") or code.strip().startswith("["):
            return "json"
        if re.search(r"^\w+:\s*\w+", code, re.MULTILINE):
            return "yaml"

        return ""  # Unknown language

    def fix_code_blocks(self, content: str) -> Tuple[str, int]:
        """
        Fix code blocks in markdown content.

        Args:
            content: Markdown file content

        Returns:
            Tuple of (fixed content, number of blocks fixed)
        """
        blocks_fixed = 0

        # Find code blocks with no language tag
        pattern = r"^```\s*\n(.*?)\n```"

        def replace_block(match):
            nonlocal blocks_fixed
            code = match.group(1)

            # Detect language
            language = self.detect_language(code)

            if language:
                blocks_fixed += 1
                self.stats["blocks_by_language"][language] = self.stats["blocks_by_language"].get(language, 0) + 1
                return f"```{language}\n{code}\n```"

            # Unknown language - leave as is but count it
            return match.group(0)

        fixed_content = re.sub(pattern, replace_block, content, flags=re.MULTILINE | re.DOTALL)

        return fixed_content, blocks_fixed

    def process_file(self, file_path: Path) -> bool:
        """
        Process a single markdown file.

        Args:
            file_path: Path to markdown file

        Returns:
            True if file was modified, False otherwise
        """
        try:
            # Read file
            with open(file_path, "r", encoding="utf-8") as f:
                original_content = f.read()

            # Fix code blocks
            fixed_content, blocks_fixed = self.fix_code_blocks(original_content)

            # Update stats
            self.stats["files_processed"] += 1

            if blocks_fixed > 0:
                print(f"  {file_path}: Fixed {blocks_fixed} code block(s)")

                if not self.dry_run:
                    # Write back
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(fixed_content)

                self.stats["files_modified"] += 1
                self.stats["blocks_fixed"] += blocks_fixed
                return True

            return False

        except Exception as e:
            print(f"  ERROR processing {file_path}: {e}")
            return False

    def process_directory(self, directory: Path, pattern: str = "**/*.md") -> None:
        """
        Process all markdown files in a directory.

        Args:
            directory: Directory to process
            pattern: Glob pattern for files to process
        """
        print(f"\nProcessing directory: {directory}")
        print(f"Pattern: {pattern}")
        if self.dry_run:
            print("DRY RUN MODE - No files will be modified")
        print("")

        for file_path in sorted(directory.glob(pattern)):
            if file_path.is_file():
                self.process_file(file_path)

    def print_summary(self) -> None:
        """Print processing summary"""
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"Files processed:  {self.stats['files_processed']}")
        print(f"Files modified:   {self.stats['files_modified']}")
        print(f"Total blocks fixed: {self.stats['blocks_fixed']}")

        if self.stats["blocks_by_language"]:
            print("\nBlocks fixed by language:")
            for lang, count in sorted(self.stats["blocks_by_language"].items()):
                print(f"  {lang:15s}: {count}")

        if self.dry_run:
            print("\n⚠️  DRY RUN - No changes were made")
            print("   Run without --dry-run to apply changes")
        else:
            print("\n✅ Changes applied successfully")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Fix markdown code blocks missing language tags",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without modifying files",
    )

    parser.add_argument(
        "--file",
        type=Path,
        help="Process single file",
    )

    parser.add_argument(
        "--dir",
        type=Path,
        help="Process all markdown files in directory (recursive)",
    )

    parser.add_argument(
        "--pattern",
        default="**/*.md",
        help="Glob pattern for files (default: **/*.md)",
    )

    args = parser.parse_args()

    # Create fixer
    fixer = CodeBlockFixer(dry_run=args.dry_run)

    # Process based on arguments
    if args.file:
        # Single file
        if not args.file.exists():
            print(f"ERROR: File not found: {args.file}")
            return 1

        print(f"\nProcessing file: {args.file}")
        if args.dry_run:
            print("DRY RUN MODE - No files will be modified\n")

        fixer.process_file(args.file)

    elif args.dir:
        # Directory
        if not args.dir.exists():
            print(f"ERROR: Directory not found: {args.dir}")
            return 1

        fixer.process_directory(args.dir, args.pattern)

    else:
        # Default: current directory
        fixer.process_directory(Path("."), args.pattern)

    # Print summary
    fixer.print_summary()

    return 0


if __name__ == "__main__":
    sys.exit(main())
