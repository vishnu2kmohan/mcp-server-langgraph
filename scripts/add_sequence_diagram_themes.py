#!/usr/bin/env python3
"""
Add theme initialization to Mermaid sequence diagrams.

Adds ColorBrewer2-based theme to sequence diagrams that lack %%{init:...}%%.
"""

import sys
from pathlib import Path
from typing import Tuple

# Standard ColorBrewer2 theme for sequence diagrams
SEQUENCE_THEME = (
    "%%{init: {'theme':'base', 'themeVariables': { "
    "'primaryColor':'#8dd3c7','primaryTextColor':'#333',"
    "'primaryBorderColor':'#2a9d8f','lineColor':'#fb8072',"
    "'secondaryColor':'#fdb462','tertiaryColor':'#b3de69'}}}%%"
)


def add_theme_to_sequence_diagrams(content: str) -> Tuple[str, bool]:
    """
    Add theme initialization to sequence diagrams missing it.

    Returns:
        Tuple of (updated_content, was_modified)
    """
    modified = False
    lines = content.split("\n")
    result_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]
        result_lines.append(line)

        # Check if this is a mermaid block start
        if line.strip() == "```mermaid":
            # Check next line to see if it's a sequenceDiagram
            if i + 1 < len(lines) and lines[i + 1].strip() == "sequenceDiagram":
                # Check if there's already a theme init (%%{init:...}%%)
                has_theme = False
                if i + 2 < len(lines) and "%%{init:" in lines[i + 2]:
                    has_theme = True

                if not has_theme:
                    # Add the sequenceDiagram line
                    i += 1
                    result_lines.append(lines[i])
                    # Add theme init
                    result_lines.append(f"    {SEQUENCE_THEME}")
                    modified = True

        i += 1

    return "\n".join(result_lines), modified


def process_file(file_path: Path, dry_run: bool = False) -> bool:
    """
    Process a single .mdx file.

    Returns:
        True if file was modified
    """
    try:
        content = file_path.read_text(encoding="utf-8")

        # Only process if it contains sequenceDiagram
        if "sequenceDiagram" not in content:
            return False

        updated_content, modified = add_theme_to_sequence_diagrams(content)

        if modified:
            if dry_run:
                print(f"[DRY RUN] Would add theme to: {file_path}")
            else:
                file_path.write_text(updated_content, encoding="utf-8")
                print(f"✓ Added theme: {file_path}")
            return True

        return False

    except Exception as e:
        print(f"✗ Error processing {file_path}: {e}", file=sys.stderr)
        return False


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Add theme initialization to Mermaid sequence diagrams")
    parser.add_argument("path", nargs="?", default="docs", help="Path to docs directory")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be changed without modifying files")

    args = parser.parse_args()

    docs_path = Path(args.path)
    if not docs_path.exists():
        print(f"Error: Path '{docs_path}' does not exist", file=sys.stderr)
        sys.exit(1)

    # Find all .mdx files
    mdx_files = [f for f in docs_path.rglob("*.mdx") if ".mintlify/templates" not in str(f)]

    print(f"Scanning {len(mdx_files)} .mdx files for sequence diagrams without themes...")
    if args.dry_run:
        print("[DRY RUN MODE - No files will be modified]\n")

    modified_count = 0
    for file_path in sorted(mdx_files):
        if process_file(file_path, args.dry_run):
            modified_count += 1

    print(f"\n{'Would add theme to' if args.dry_run else 'Added theme to'}: {modified_count} file(s)")

    if args.dry_run and modified_count > 0:
        print("\nRun without --dry-run to apply changes")


if __name__ == "__main__":
    main()
