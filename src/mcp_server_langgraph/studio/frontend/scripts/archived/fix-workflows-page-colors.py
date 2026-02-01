#!/usr/bin/env python3
"""
Fix WorkflowsPage colors to align with Radix design system.

Per STYLE.md:
- Steps 9-10: Solid colors (buttons, badges, icons)
- Steps 11-12: Text colors
- Dark mode text should use step 11
"""

import re
from pathlib import Path

WORKFLOWS_PAGE = Path(__file__).parent.parent / "src" / "pages" / "WorkflowsPage.tsx"

# Text color fixes
TEXT_FIXES = [
    # Undo/redo buttons - step 10 to 11
    (r"\btext-neutral-10\b", "text-neutral-11"),
    # Warning text - step 10 to 11
    (r"\btext-warning-10\b", "text-warning-11"),
]

# Dark mode text fixes - consolidate to step 11
DARK_TEXT_FIXES = [
    (r"\bdark:text-error-7\b", "dark:text-error-11"),
    (r"\bdark:text-primary-7\b", "dark:text-primary-11"),
    (r"\bdark:text-success-7\b", "dark:text-success-11"),
    (r"\bdark:text-warning-9\b", "dark:text-warning-11"),
    (r"\bdark:text-grafana-5\b", "dark:text-grafana-11"),
    (r"\bdark:text-insight-9\b", "dark:text-insight-11"),
]

# Button background fixes - step 10 to step 9
BG_FIXES = [
    (r"\bbg-success-10\b", "bg-success-9"),
    (r"\bhover:bg-success-11\b", "hover:bg-success-10"),
    (r"\bbg-primary-10\b", "bg-primary-9"),
    (r"\bhover:bg-primary-11\b", "hover:bg-primary-10"),
]

# Duplicate bg class cleanup (remove second bg class)
DUPLICATE_FIXES = [
    # "bg-error-3 text-error-11 bg-error-4" -> "bg-error-3 text-error-11"
    (r"bg-error-3 (text-error-11) bg-error-4", r"bg-error-3 \1"),
    (r"bg-primary-3 (text-primary-11) bg-primary-4", r"bg-primary-3 \1"),
    (r"bg-success-3 (text-success-11) bg-success-4", r"bg-success-3 \1"),
    # Also handle "bg-X-3 bg-X-4" patterns
    (r"bg-error-3 bg-error-4", "bg-error-3"),
    (r"bg-primary-3 bg-primary-4", "bg-primary-3"),
    (r"bg-success-3 bg-success-4", "bg-success-3"),
]


def fix_file(filepath: Path, dry_run: bool = False) -> int:
    """Fix a single file. Returns number of replacements made."""
    content = filepath.read_text()
    changes = 0

    all_fixes = TEXT_FIXES + DARK_TEXT_FIXES + BG_FIXES + DUPLICATE_FIXES

    for pattern, replacement in all_fixes:
        new_content, count = re.subn(pattern, replacement, content)
        if count > 0:
            changes += count
            content = new_content

    if changes > 0 and not dry_run:
        filepath.write_text(content)

    return changes


def main() -> int:
    import sys

    dry_run = "--dry-run" in sys.argv

    if dry_run:
        print("DRY RUN - no files will be modified\n")

    if not WORKFLOWS_PAGE.exists():
        print(f"Error: {WORKFLOWS_PAGE} not found")
        return 1

    changes = fix_file(WORKFLOWS_PAGE, dry_run=dry_run)
    if changes > 0:
        print(f"{'Would fix' if dry_run else 'Fixed'} WorkflowsPage.tsx: {changes} replacements")
    else:
        print("No changes needed")

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
