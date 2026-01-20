#!/usr/bin/env python3
"""
Fix VectorsPage colors to align with Radix design system.

Per STYLE.md:
- Steps 9-10: Solid colors (buttons, badges, icons)
- Steps 11-12: Text colors
- Dark mode text should use step 11
- Dark mode borders should use step 7
"""

import re
from pathlib import Path

VECTORS_PAGE = Path(__file__).parent.parent / "src" / "pages" / "VectorsPage.tsx"

# Text color fixes - step 10 to step 11
TEXT_FIXES = [
    (r'\btext-neutral-10\b', 'text-neutral-11'),
]

# Button background fixes - step 10 to step 9
BG_FIXES = [
    (r'\bbg-primary-10\b', 'bg-primary-9'),
    (r'\bhover:bg-primary-11\b', 'hover:bg-primary-10'),
    (r'\bbg-success-10\b', 'bg-success-9'),
    (r'\bhover:bg-success-11\b', 'hover:bg-success-10'),
    (r'\bbg-insight-10\b', 'bg-insight-9'),
    (r'\bhover:bg-insight-11\b', 'hover:bg-insight-10'),
]

# Dark mode text fixes - consolidate to step 11
DARK_TEXT_FIXES = [
    (r'\bdark:text-error-7\b', 'dark:text-error-11'),
    (r'\bdark:text-success-7\b', 'dark:text-success-11'),
    (r'\bdark:text-insight-9\b', 'dark:text-insight-11'),
]

# Dark mode border fixes - step 11 to step 7
DARK_BORDER_FIXES = [
    (r'\bdark:border-error-11\b', 'dark:border-error-7'),
    (r'\bdark:border-success-11\b', 'dark:border-success-7'),
]

def fix_file(filepath: Path, dry_run: bool = False) -> int:
    """Fix a single file. Returns number of replacements made."""
    content = filepath.read_text()
    changes = 0

    all_fixes = TEXT_FIXES + BG_FIXES + DARK_TEXT_FIXES + DARK_BORDER_FIXES

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

    if not VECTORS_PAGE.exists():
        print(f"Error: {VECTORS_PAGE} not found")
        return 1

    changes = fix_file(VECTORS_PAGE, dry_run=dry_run)
    if changes > 0:
        print(f"{'Would fix' if dry_run else 'Fixed'} VectorsPage.tsx: {changes} replacements")
    else:
        print("No changes needed")

    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
