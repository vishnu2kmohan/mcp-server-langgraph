#!/usr/bin/env python3
"""
Fix closing code fence language tags in Markdown/MDX files.

This script removes language identifiers from closing code fences, which is
a syntax error. Closing fences should always be bare ``` without any language tag.

Usage:
    python scripts/fix_closing_fence_tags.py [--dry-run] [--path PATH]

Examples:
    # Preview changes without modifying files
    python scripts/fix_closing_fence_tags.py --dry-run

    # Fix all MDX files in docs/
    python scripts/fix_closing_fence_tags.py --path docs

    # Fix specific file
    python scripts/fix_closing_fence_tags.py --path docs/getting-started/quickstart.mdx
"""

import argparse
import re
import sys
from pathlib import Path
from typing import List, Tuple


class ClosingFenceFixer:
    """Fix closing code fence language tags using state machine."""

    def __init__(self, dry_run: bool = False):
        """
        Initialize fixer.

        Args:
            dry_run: If True, don't modify files, just report
        """
        self.dry_run = dry_run
        self.stats = {
            "files_processed": 0,
            "files_modified": 0,
            "fences_fixed": 0,
        }

    def fix_file(self, file_path: Path) -> bool:
        """
        Fix closing fence tags in a single file.

        Args:
            file_path: Path to the file

        Returns:
            True if file was modified
        """
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            print(f"❌ Error reading {file_path}: {e}", file=sys.stderr)
            return False

        fixed_content, fixes = self._fix_content(content)

        self.stats["files_processed"] += 1

        if fixes:
            self.stats["files_modified"] += 1
            self.stats["fences_fixed"] += len(fixes)

            if self.dry_run:
                print(f"🔍 Would fix {file_path}:")
                for line_num, old_fence, new_fence in fixes:
                    print(f"   Line {line_num}: '{old_fence}' → '{new_fence}'")
            else:
                try:
                    file_path.write_text(fixed_content, encoding="utf-8")
                    print(f"✅ Fixed {file_path}:")
                    for line_num, old_fence, new_fence in fixes:
                        print(f"   Line {line_num}: '{old_fence}' → '{new_fence}'")
                except Exception as e:
                    print(f"❌ Error writing {file_path}: {e}", file=sys.stderr)
                    return False

            return True

        return False

    def _fix_content(self, content: str) -> tuple[str, list[tuple[int, str, str]]]:
        """
        Fix closing fence tags in content using state machine.

        Args:
            content: File content

        Returns:
            Tuple of (fixed_content, list of fixes)
            Each fix is (line_number, old_fence, new_fence)
        """
        lines = content.split("\n")
        fixed_lines = []
        fixes = []
        in_code_block = False

        for i, line in enumerate(lines, start=1):
            # Check if this line starts with ```
            if line.lstrip().startswith("```"):
                fence_match = re.match(r"^(\s*)```(\S+)?\s*$", line)

                if fence_match:
                    indent = fence_match.group(1)
                    lang_tag = fence_match.group(2)

                    if not in_code_block:
                        # Opening fence - can have language tag (leave as-is)
                        fixed_lines.append(line)
                        in_code_block = True
                    else:
                        # Closing fence - must NOT have language tag
                        if lang_tag:
                            # Found a closing fence with language tag - FIX IT
                            old_fence = line
                            new_fence = f"{indent}```"
                            fixed_lines.append(new_fence)
                            fixes.append((i, old_fence, new_fence))
                        else:
                            # Already correct - no language tag
                            fixed_lines.append(line)
                        in_code_block = False
                else:
                    # Line starts with ``` but doesn't match our pattern (malformed)
                    fixed_lines.append(line)
            else:
                # Not a fence line
                fixed_lines.append(line)

        fixed_content = "\n".join(fixed_lines)
        return fixed_content, fixes

    def print_summary(self):
        """Print processing summary."""
        print("\n" + "=" * 70)
        print("SUMMARY: Closing Fence Language Tag Fixes")
        print("=" * 70)
        print(f"Files processed:     {self.stats['files_processed']}")
        print(f"Files modified:      {self.stats['files_modified']}")
        print(f"Closing fences fixed: {self.stats['fences_fixed']}")
        print("=" * 70)

        if self.dry_run:
            print("\n⚠️  DRY RUN - No files were modified")
            print("Run without --dry-run to apply changes")
        else:
            if self.stats["fences_fixed"] > 0:
                print(f"\n✅ Successfully fixed {self.stats['fences_fixed']} closing fence tags")
            else:
                print("\n✅ No issues found - all closing fences are correct")


def find_markdown_files(path: Path) -> list[Path]:
    """
    Find all Markdown/MDX files in path.

    Args:
        path: File or directory path

    Returns:
        List of file paths
    """
    if path.is_file():
        if path.suffix in {".md", ".mdx"}:
            return [path]
        print(f"⚠️  {path} is not a Markdown file", file=sys.stderr)
        return []
    if path.is_dir():
        md_files = list(path.rglob("*.md")) + list(path.rglob("*.mdx"))
        return sorted(md_files)
    print(f"❌ Path not found: {path}", file=sys.stderr)
    return []


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Fix closing code fence language tags in Markdown/MDX files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview changes without modifying files
  python scripts/fix_closing_fence_tags.py --dry-run

  # Fix all MDX files in docs/
  python scripts/fix_closing_fence_tags.py --path docs

  # Fix specific file
  python scripts/fix_closing_fence_tags.py --path docs/getting-started/quickstart.mdx

Why this matters:
  Closing code fences should be bare ``` without language tags.
  This is standard Markdown/MDX syntax:

  Correct:
    ```python
    print("hello")
    ```

  Wrong:
    ```python
    print("hello")
    ```python  ← Language tag on closing fence (INVALID)
        """,
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=Path("docs"),
        help="File or directory to process (default: docs/)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without modifying files",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output",
    )

    args = parser.parse_args()

    # Find files to process
    files = find_markdown_files(args.path)

    if not files:
        print("❌ No Markdown files to process", file=sys.stderr)
        sys.exit(1)

    if args.verbose:
        print(f"Found {len(files)} Markdown files to process\n")

    # Process files
    fixer = ClosingFenceFixer(dry_run=args.dry_run)

    for file_path in files:
        fixer.fix_file(file_path)

    # Print summary
    fixer.print_summary()

    # Exit code
    if fixer.stats["fences_fixed"] > 0 and args.dry_run:
        sys.exit(1)  # Issues found in dry-run mode
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
