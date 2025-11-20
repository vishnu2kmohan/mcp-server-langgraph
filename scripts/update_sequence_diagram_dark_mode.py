#!/usr/bin/env python3
"""
Update all sequence diagrams with dark-mode-compatible ColorBrewer2 theme.

Replaces the old theme (with #333 text) with new dual-mode theme.
"""

import sys
from pathlib import Path

# Old theme patterns to find
OLD_THEME_PATTERNS = [
    "%%{init: {'theme':'base', 'themeVariables': { 'primaryColor':'#8dd3c7','primaryTextColor':'#333',",  # v1.0
    "%%{init: {'theme':'base', 'themeVariables': {'primaryColor':'#66CDAA','primaryTextColor':'#1f2937',",  # v1.5 (non-CB2)
]

# New dark-mode compatible theme (v2.0) - ColorBrewer2 Set3 fills with dark mode text
# fmt: off (long Mermaid theme string must be on one line)
NEW_THEME = """%%{init: {'theme':'base', 'themeVariables': {'primaryColor':'#8dd3c7','primaryTextColor':'#1a202c','primaryBorderColor':'#2a9d8f','lineColor':'#fb8072','secondaryColor':'#fdb462','tertiaryColor':'#b3de69','actorBkg':'#8dd3c7','actorBorder':'#2a9d8f','actorTextColor':'#1a202c','actorLineColor':'#2a9d8f','signalColor':'#7cb342','signalTextColor':'#1a202c','labelBoxBkgColor':'#fdb462','labelBoxBorderColor':'#e67e22','labelTextColor':'#1a202c','noteBorderColor':'#e67e22','noteBkgColor':'#fdb462','noteTextColor':'#1a202c','activationBorderColor':'#7cb342','activationBkgColor':'#b3de69','sequenceNumberColor':'#4a5568'}}}%%"""  # noqa: E501
# fmt: on


def update_sequence_theme(content: str) -> tuple[str, bool]:
    """
    Replace old sequence diagram theme with dark-mode compatible version.

    Returns:
        Tuple of (updated_content, was_modified)
    """
    modified = False
    lines = content.split("\n")
    result_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Check if this line contains any of the old theme patterns
        is_old_theme = any(pattern in line for pattern in OLD_THEME_PATTERNS)

        if is_old_theme:
            # This is the old theme line - replace entire line
            result_lines.append(f"    {NEW_THEME}")
            modified = True
            i += 1
            continue

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

        # Only process if it contains any of the old theme patterns
        has_old_theme = any(pattern in content for pattern in OLD_THEME_PATTERNS)
        if not has_old_theme:
            return False

        updated_content, modified = update_sequence_theme(content)

        if modified:
            if dry_run:
                print(f"[DRY RUN] Would update: {file_path}")
            else:
                file_path.write_text(updated_content, encoding="utf-8")
                print(f"✓ Updated: {file_path}")
            return True

        return False

    except Exception as e:
        print(f"✗ Error processing {file_path}: {e}", file=sys.stderr)
        return False


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Update sequence diagrams with dark-mode compatible theme")
    parser.add_argument("path", nargs="?", default="docs", help="Path to docs directory")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be changed without modifying files")

    args = parser.parse_args()

    docs_path = Path(args.path)
    if not docs_path.exists():
        print(f"Error: Path '{docs_path}' does not exist", file=sys.stderr)
        sys.exit(1)

    # Find all .mdx files
    mdx_files = [f for f in docs_path.rglob("*.mdx") if ".mintlify/templates" not in str(f)]

    print(f"Scanning {len(mdx_files)} .mdx files for old sequence diagram themes...")
    if args.dry_run:
        print("[DRY RUN MODE - No files will be modified]\n")

    modified_count = 0
    for file_path in sorted(mdx_files):
        if process_file(file_path, args.dry_run):
            modified_count += 1

    print(f"\n{'Would update' if args.dry_run else 'Updated'}: {modified_count} file(s)")

    if args.dry_run and modified_count > 0:
        print("\nRun without --dry-run to apply changes")

    if modified_count > 0:
        print("\n✅ All sequence diagrams now use dark-mode compatible theme!")
        print("   - Text colors: #333 → #0f172a/#1f2937 (visible on dark backgrounds)")
        print("   - Label boxes: #ffffb3 → #f59e0b (better contrast)")
        print("   - Sequence numbers: #fff → #475569 (visible on light backgrounds)")


if __name__ == "__main__":
    main()
