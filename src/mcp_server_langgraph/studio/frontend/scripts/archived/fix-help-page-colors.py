#!/usr/bin/env python3
"""
Fix HelpPage and related help components to align with Radix design system.

Per STYLE.md:
- Steps 9-10: Solid colors (buttons, badges, icons)
- Steps 11-12: Text colors
- Dark mode text should use step 11
- Dark mode borders should use step 7
"""

import re
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent / "src"

FILES_TO_FIX = [
    BASE_DIR / "pages" / "HelpPage.tsx",
    BASE_DIR / "help" / "HelpPane.tsx",
    BASE_DIR / "help" / "KeyboardShortcuts.tsx",
]

# Text color fixes - step 10 to step 11
TEXT_FIXES = [
    (r"\btext-neutral-10\b", "text-neutral-11"),
]

# Dark mode text fixes - consolidate to step 11
DARK_TEXT_FIXES = [
    (r"\bdark:text-primary-7\b", "dark:text-primary-11"),
    (r"\bdark:text-success-7\b", "dark:text-success-11"),
    (r"\bdark:text-insight-9\b", "dark:text-insight-11"),
]

# Dark mode border fixes - step 11 to step 7
DARK_BORDER_FIXES = [
    (r"\bdark:hover:border-primary-11\b", "dark:hover:border-primary-7"),
]

# Duplicate bg class cleanup
DUPLICATE_BG_FIXES = [
    # "bg-primary-3 text-primary-11 bg-primary-4" -> "bg-primary-3 text-primary-11"
    (r"bg-primary-3 (text-primary-11) bg-primary-4", r"bg-primary-3 \1"),
    (r"bg-success-3 (text-success-11) bg-success-4", r"bg-success-3 \1"),
]


def fix_file(filepath: Path, dry_run: bool = False) -> int:
    """Fix a single file. Returns number of replacements made."""
    if not filepath.exists():
        return 0

    content = filepath.read_text()
    changes = 0

    all_fixes = TEXT_FIXES + DARK_TEXT_FIXES + DARK_BORDER_FIXES + DUPLICATE_BG_FIXES

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

    total_changes = 0
    for filepath in FILES_TO_FIX:
        if not filepath.exists():
            print(f"Skipping {filepath.name} (not found)")
            continue

        changes = fix_file(filepath, dry_run=dry_run)
        if changes > 0:
            print(f"{'Would fix' if dry_run else 'Fixed'} {filepath.name}: {changes} replacements")
            total_changes += changes
        else:
            print(f"No changes needed for {filepath.name}")

    print(f"\nTotal: {total_changes} replacements")
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
