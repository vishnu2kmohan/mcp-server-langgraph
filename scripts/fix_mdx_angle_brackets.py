#!/usr/bin/env python3
"""
Fix MDX angle bracket issues by escaping < and > characters before/after numbers.

This prevents MDX parsing errors like:
"Unexpected character `1` (U+0031) before name, expected a character that
can start a name, such as a letter, `$`, or `_`"

Usage:
    python scripts/fix_mdx_angle_brackets.py [--dry-run]
"""

import re
import sys
from pathlib import Path


def fix_angle_brackets(content: str) -> tuple[str, int]:
    """
    Replace unescaped angle brackets before/after numbers with HTML entities.

    Returns:
        Tuple of (fixed_content, num_replacements)
    """
    replacements = 0

    # Pattern 1: < followed by a number (e.g., "<100K", "<10", "<1M")
    # Only replace if not already an HTML entity or inside a tag
    def replace_lt(match):
        nonlocal replacements
        # Check if already escaped
        if match.group(0).startswith("&lt;"):
            return match.group(0)
        replacements += 1
        return match.group(0).replace("<", "&lt;")

    # Pattern 2: > followed by a number (e.g., ">1M", ">100K", ">30s")
    def replace_gt(match):
        nonlocal replacements
        # Check if already escaped
        if match.group(0).startswith("&gt;"):
            return match.group(0)
        replacements += 1
        return match.group(0).replace(">", "&gt;")

    # Fix < before numbers (not inside code blocks or already escaped)
    # Negative lookbehind to avoid matching &lt; or inside tags
    content = re.sub(r"(?<!&lt;)(?<![<`])(<)(\d)", replace_lt, content)

    # Fix > before numbers (not inside code blocks or already escaped)
    content = re.sub(r"(?<!&gt;)(?<![>`])(>)(\d)", replace_gt, content)

    return content, replacements


def should_skip_file(filepath: Path) -> bool:
    """Check if file should be skipped."""
    # Skip files in certain directories
    skip_dirs = {".git", "node_modules", ".venv", "__pycache__"}
    if any(part in skip_dirs for part in filepath.parts):
        return True

    # Only process .mdx files
    if filepath.suffix != ".mdx":
        return True

    return False


def process_file(filepath: Path, dry_run: bool = False) -> tuple[bool, int]:
    """
    Process a single MDX file.

    Returns:
        Tuple of (was_modified, num_replacements)
    """
    try:
        content = filepath.read_text(encoding="utf-8")
        fixed_content, num_replacements = fix_angle_brackets(content)

        if num_replacements > 0:
            if not dry_run:
                filepath.write_text(fixed_content, encoding="utf-8")
            return True, num_replacements

        return False, 0
    except Exception as e:
        print(f"Error processing {filepath}: {e}", file=sys.stderr)
        return False, 0


def main():
    """Main entry point."""
    dry_run = "--dry-run" in sys.argv

    # Find all MDX files
    docs_dir = Path(__file__).parent.parent / "docs"
    if not docs_dir.exists():
        print(f"Error: docs directory not found at {docs_dir}", file=sys.stderr)
        return 1

    mdx_files = list(docs_dir.rglob("*.mdx"))
    mdx_files = [f for f in mdx_files if not should_skip_file(f)]

    print(f"Found {len(mdx_files)} MDX files")
    if dry_run:
        print("DRY RUN - No files will be modified")
    print()

    total_modified = 0
    total_replacements = 0

    for filepath in sorted(mdx_files):
        modified, num_replacements = process_file(filepath, dry_run=dry_run)
        if modified:
            relative_path = filepath.relative_to(docs_dir)
            status = "[DRY RUN] Would fix" if dry_run else "Fixed"
            print(f"{status}: {relative_path} ({num_replacements} replacements)")
            total_modified += 1
            total_replacements += num_replacements

    print()
    if total_modified > 0:
        status = "would be modified" if dry_run else "modified"
        print(f"Summary: {total_modified} files {status}, {total_replacements} total replacements")
        if dry_run:
            print("\nRun without --dry-run to apply changes")
    else:
        print("No files need modification")

    return 0


if __name__ == "__main__":
    sys.exit(main())
