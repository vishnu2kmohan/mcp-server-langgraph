#!/usr/bin/env python3
"""
Fix react-refresh/only-export-components warnings.

These warnings occur when files export utility functions alongside components.
The fix is to add eslint-disable-next-line comments before the export.
"""

import re
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent / "src"

# Files and line numbers with warnings (from npm run lint output)
WARNINGS = [
    # Round 2 - remaining warnings
    ("components/Chat/ChatMessage.tsx", [26, 42, 61, 79, 95]),
    ("components/Chat/CodeBlock.tsx", [37, 55]),
    ("components/Chat/ConfidenceIndicator.tsx", [26, 50]),
    ("components/Chat/ExecutionModeIndicator.tsx", [30]),
    ("components/Chat/ResponseRating.tsx", [35, 60]),
    ("components/DevTools/DevToolsPanel.tsx", [96]),
    ("components/DevTools/TimelineBar.tsx", [132]),
]

def fix_file(filepath: Path, line_numbers: list[int], dry_run: bool = False) -> int:
    """Add eslint-disable-next-line before exports at specified lines."""
    if not filepath.exists():
        print(f"  Skipping {filepath.name} (not found)")
        return 0

    lines = filepath.read_text().splitlines(keepends=True)
    changes = 0
    offset = 0  # Track offset as we insert lines

    for line_num in sorted(line_numbers):
        idx = line_num - 1 + offset  # Adjust for 0-based and offset
        if idx < 0 or idx >= len(lines):
            continue

        line = lines[idx]

        # Check if already has disable comment
        if idx > 0 and "eslint-disable" in lines[idx - 1]:
            continue

        # Check if this is an export of a function/const
        if re.match(r'\s*(export\s+)?(const|function|let|var)\s+', line):
            # Get the indentation
            indent = re.match(r'^(\s*)', line).group(1)
            disable_comment = f"{indent}// eslint-disable-next-line react-refresh/only-export-components\n"
            lines.insert(idx, disable_comment)
            offset += 1
            changes += 1

    if changes > 0 and not dry_run:
        filepath.write_text("".join(lines))

    return changes

def main() -> int:
    import sys
    dry_run = "--dry-run" in sys.argv

    if dry_run:
        print("DRY RUN - no files will be modified\n")

    total_changes = 0
    for rel_path, line_numbers in WARNINGS:
        filepath = BASE_DIR / rel_path
        changes = fix_file(filepath, line_numbers, dry_run=dry_run)
        if changes > 0:
            print(f"{'Would fix' if dry_run else 'Fixed'} {rel_path}: {changes} exports")
            total_changes += changes
        else:
            print(f"No changes needed for {rel_path}")

    print(f"\nTotal: {total_changes} exports fixed")
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
