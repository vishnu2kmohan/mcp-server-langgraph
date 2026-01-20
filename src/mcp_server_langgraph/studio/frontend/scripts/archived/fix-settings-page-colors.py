#!/usr/bin/env python3
"""
Fix SettingsPage colors to align with Radix design system.

Per STYLE.md:
- Steps 9-10: Solid colors (buttons, badges, icons)
- Steps 11-12: Text colors
- Dark mode text should use step 11
- Dark mode borders should use step 7
"""

import re
from pathlib import Path

SETTINGS_PAGE = Path(__file__).parent.parent / "src" / "pages" / "SettingsPage.tsx"

# Text color fixes - step 10 to step 11
TEXT_FIXES = [
    (r'\btext-neutral-10\b', 'text-neutral-11'),
    (r'\btext-error-10\b', 'text-error-11'),
]

# Button background fixes - step 10 to step 9
BG_FIXES = [
    (r'\bbg-primary-10\b', 'bg-primary-9'),
    (r'\bhover:bg-primary-11\b', 'hover:bg-primary-10'),
    (r'\bbg-success-10\b', 'bg-success-9'),
    (r'\bhover:bg-success-11\b', 'hover:bg-success-10'),
]

# Dark mode text fixes - consolidate to step 11
DARK_TEXT_FIXES = [
    (r'\bdark:text-error-7\b', 'dark:text-error-11'),
    (r'\bdark:text-success-7\b', 'dark:text-success-11'),
    (r'\bdark:text-warning-6\b', 'dark:text-warning-11'),
    (r'\bdark:text-insight-4\b', 'dark:text-insight-11'),
    (r'\bdark:text-primary-4\b', 'dark:text-primary-11'),
]

# Dark mode border fixes - step 11 to step 7
DARK_BORDER_FIXES = [
    (r'\bdark:border-warning-11\b', 'dark:border-warning-7'),
    (r'\bdark:border-error-11\b', 'dark:border-error-7'),
    (r'\bdark:border-insight-11\b', 'dark:border-insight-7'),
    (r'\bdark:border-primary-11\b', 'dark:border-primary-7'),
]

# Duplicate bg class cleanup
DUPLICATE_BG_FIXES = [
    # "bg-error-3 text-error-11 bg-error-4" -> "bg-error-3 text-error-11"
    (r'bg-error-3 (text-error-11) bg-error-4', r'bg-error-3 \1'),
    (r'bg-success-3 (text-success-11) bg-success-4', r'bg-success-3 \1'),
    # "bg-warning-3 bg-warning-3" -> "bg-warning-3"
    (r'bg-warning-3 bg-warning-3\b', 'bg-warning-3'),
    # "bg-primary-1 bg-primary-4" -> "bg-primary-1" (theme selection)
    (r'bg-primary-1 bg-primary-4\b', 'bg-primary-1'),
]

def fix_file(filepath: Path, dry_run: bool = False) -> int:
    """Fix a single file. Returns number of replacements made."""
    content = filepath.read_text()
    changes = 0

    all_fixes = TEXT_FIXES + BG_FIXES + DARK_TEXT_FIXES + DARK_BORDER_FIXES + DUPLICATE_BG_FIXES

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

    if not SETTINGS_PAGE.exists():
        print(f"Error: {SETTINGS_PAGE} not found")
        return 1

    changes = fix_file(SETTINGS_PAGE, dry_run=dry_run)
    if changes > 0:
        print(f"{'Would fix' if dry_run else 'Fixed'} SettingsPage.tsx: {changes} replacements")
    else:
        print("No changes needed")

    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
