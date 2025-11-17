#!/usr/bin/env python3
"""
Fix Mermaid sequence diagrams by removing invalid classDef statements.

classDef and class statements are only valid in flowcharts/graphs, not sequenceDiagrams.
This script removes these invalid statements from all sequence diagram blocks.
"""

import sys
from pathlib import Path
from typing import Tuple


def fix_sequence_diagram(content: str) -> Tuple[str, bool]:
    """
    Remove classDef and class statements from sequenceDiagram blocks.

    Returns:
        Tuple of (fixed_content, was_modified)
    """
    modified = False
    result_lines = []
    in_mermaid = False
    in_sequence = False
    skip_classdef_section = False

    lines = content.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]

        # Detect mermaid block start
        if line.strip() == "```mermaid":
            in_mermaid = True
            in_sequence = False
            result_lines.append(line)
            i += 1
            continue

        # Detect mermaid block end
        if in_mermaid and line.strip() == "```":
            in_mermaid = False
            in_sequence = False
            skip_classdef_section = False
            result_lines.append(line)
            i += 1
            continue

        # Check if this is a sequenceDiagram
        if in_mermaid and line.strip() == "sequenceDiagram":
            in_sequence = True
            result_lines.append(line)
            i += 1
            continue

        # Skip classDef and class lines in sequence diagrams
        if in_mermaid and in_sequence:
            stripped = line.strip()

            # Start of classDef section (usually preceded by blank line)
            if stripped.startswith("classDef "):
                modified = True
                skip_classdef_section = True
                i += 1
                continue

            # class assignment lines
            if stripped.startswith("class ") and skip_classdef_section:
                modified = True
                i += 1
                continue

            # Empty line might signal end of classDef section
            if not stripped and skip_classdef_section:
                # Check if next line is also classDef-related
                if i + 1 < len(lines):
                    next_stripped = lines[i + 1].strip()
                    if not (next_stripped.startswith("classDef ") or next_stripped.startswith("class ")):
                        skip_classdef_section = False
                        # Don't add this blank line if it was separating classDef section
                        if result_lines and result_lines[-1].strip():
                            result_lines.append(line)
                        i += 1
                        continue

            # Not a classDef line, keep it
            if not skip_classdef_section:
                result_lines.append(line)
            else:
                modified = True

        else:
            # Not in a sequence diagram mermaid block
            result_lines.append(line)

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

        # Only process if it contains classDef
        if "classDef" not in content:
            return False

        fixed_content, modified = fix_sequence_diagram(content)

        if modified:
            if dry_run:
                print(f"[DRY RUN] Would fix: {file_path}")
            else:
                file_path.write_text(fixed_content, encoding="utf-8")
                print(f"✓ Fixed: {file_path}")
            return True

        return False

    except Exception as e:
        print(f"✗ Error processing {file_path}: {e}", file=sys.stderr)
        return False


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Fix Mermaid sequence diagrams by removing invalid classDef statements")
    parser.add_argument("path", nargs="?", default="docs", help="Path to docs directory")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be changed without modifying files")

    args = parser.parse_args()

    docs_path = Path(args.path)
    if not docs_path.exists():
        print(f"Error: Path '{docs_path}' does not exist", file=sys.stderr)
        sys.exit(1)

    # Find all .mdx files with sequence diagrams
    mdx_files = [f for f in docs_path.rglob("*.mdx") if ".mintlify/templates" not in str(f)]

    print(f"Scanning {len(mdx_files)} .mdx files for sequence diagram issues...")
    if args.dry_run:
        print("[DRY RUN MODE - No files will be modified]\n")

    fixed_count = 0
    for file_path in sorted(mdx_files):
        if process_file(file_path, args.dry_run):
            fixed_count += 1

    print(f"\n{'Would fix' if args.dry_run else 'Fixed'}: {fixed_count} file(s)")

    if args.dry_run and fixed_count > 0:
        print("\nRun without --dry-run to apply changes")


if __name__ == "__main__":
    main()
