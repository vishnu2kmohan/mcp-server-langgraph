#!/usr/bin/env python3
"""
Fix ProjectsPage colors to align with Radix design system.

Per STYLE.md:
- Steps 9-10: Solid colors (buttons, badges, icons)
- Steps 11-12: Text colors
"""

import re
from pathlib import Path

PROJECTS_PAGE = Path(__file__).parent.parent / "src" / "pages" / "ProjectsPage.tsx"

# Text color fixes - step 10 to step 11 for text
TEXT_FIXES = [
    # Header text using step 10 should be 11
    (r'\btext-neutral-10\b', 'text-neutral-11'),

    # Primary/error text for buttons - 10 to 11
    (r'\btext-primary-10\b', 'text-primary-11'),
    (r'\btext-error-10\b', 'text-error-11'),

    # Dark mode text fixes - consolidate to step 11
    (r'\bdark:text-primary-7\b', 'dark:text-primary-11'),
    (r'\bdark:text-primary-5\b', 'dark:text-primary-11'),
    (r'\bdark:text-error-7\b', 'dark:text-error-11'),
    (r'\bdark:text-success-7\b', 'dark:text-success-11'),
]

# Button background fixes - step 10 to step 9
BG_FIXES = [
    (r'\bbg-primary-10\b', 'bg-primary-9'),
    (r'\bhover:bg-primary-11\b', 'hover:bg-primary-10'),
    (r'\bbg-error-10\b', 'bg-error-9'),
    (r'\bhover:bg-error-11\b', 'hover:bg-error-10'),
]

# Status badge cleanup - remove duplicate bg classes
BADGE_FIXES = [
    # "bg-success-3 text-success-11 bg-success-4" -> "bg-success-3 text-success-11"
    (r'bg-success-3 text-success-11 bg-success-4', 'bg-success-3 text-success-11'),
]

# Border fixes for dark mode
BORDER_FIXES = [
    (r'\bdark:border-primary-11\b', 'dark:border-primary-7'),
]

def fix_file(filepath: Path, dry_run: bool = False) -> int:
    """Fix a single file. Returns number of replacements made."""
    content = filepath.read_text()
    changes = 0

    all_fixes = TEXT_FIXES + BG_FIXES + BADGE_FIXES + BORDER_FIXES

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

    if not PROJECTS_PAGE.exists():
        print(f"Error: {PROJECTS_PAGE} not found")
        return 1

    changes = fix_file(PROJECTS_PAGE, dry_run=dry_run)
    if changes > 0:
        print(f"{'Would fix' if dry_run else 'Fixed'} ProjectsPage.tsx: {changes} replacements")
    else:
        print("No changes needed")

    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
