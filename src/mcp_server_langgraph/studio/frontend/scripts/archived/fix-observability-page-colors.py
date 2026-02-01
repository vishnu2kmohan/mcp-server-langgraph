#!/usr/bin/env python3
"""
Fix ObservabilityPage colors to align with Radix design system.

Per STYLE.md:
- Steps 9-10: Solid colors (buttons, badges, icons)
- Steps 11-12: Text colors
- Dark mode text should use step 11
- Dark mode borders/rings should use step 7
"""

import re
from pathlib import Path

OBSERVABILITY_PAGE = Path(__file__).parent.parent / "src" / "pages" / "ObservabilityPage.tsx"

# Text color fixes - step 10 to step 11
TEXT_FIXES = [
    (r"\btext-neutral-10\b", "text-neutral-11"),
    (r"\btext-warning-10\b", "text-warning-11"),
    (r"\btext-success-10\b", "text-success-11"),
    (r"\btext-error-10\b", "text-error-11"),
]

# Dark mode text fixes - consolidate to step 11
DARK_TEXT_FIXES = [
    (r"\bdark:text-error-7\b", "dark:text-error-11"),
    (r"\bdark:text-error-9\b", "dark:text-error-11"),
    (r"\bdark:text-success-7\b", "dark:text-success-11"),
    (r"\bdark:text-primary-7\b", "dark:text-primary-11"),
    (r"\bdark:text-primary-5\b", "dark:text-primary-11"),
    (r"\bdark:text-warning-9\b", "dark:text-warning-11"),
    (r"\bdark:text-warning-6\b", "dark:text-warning-11"),
    (r"\bdark:text-grafana-5\b", "dark:text-grafana-11"),
    (r"\bdark:text-grafana-4\b", "dark:text-grafana-11"),
]

# Dark mode ring/border fixes - step 11 to step 7
DARK_RING_FIXES = [
    (r"\bdark:ring-primary-11\b", "dark:ring-primary-7"),
]

# Duplicate bg class cleanup (remove second bg class)
DUPLICATE_BG_FIXES = [
    # "bg-error-3 text-error-11 bg-error-4" -> "bg-error-3 text-error-11"
    (r"bg-error-3 (text-error-11) bg-error-4", r"bg-error-3 \1"),
    (r"bg-primary-3 (text-primary-11) bg-primary-4", r"bg-primary-3 \1"),
    (r"bg-success-3 (text-success-11) bg-success-4", r"bg-success-3 \1"),
    (r"bg-warning-3 (text-warning-11) bg-warning-4", r"bg-warning-3 \1"),
    # Also handle patterns with dark mode variants in between
    (r"bg-error-3 bg-error-4 (text-error-11)", r"bg-error-3 \1"),
    (r"bg-primary-3 bg-primary-4 (text-primary-11)", r"bg-primary-3 \1"),
    (r"bg-success-3 bg-success-4 (text-success-11)", r"bg-success-3 \1"),
]


def fix_file(filepath: Path, dry_run: bool = False) -> int:
    """Fix a single file. Returns number of replacements made."""
    content = filepath.read_text()
    changes = 0

    all_fixes = TEXT_FIXES + DARK_TEXT_FIXES + DARK_RING_FIXES + DUPLICATE_BG_FIXES

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

    if not OBSERVABILITY_PAGE.exists():
        print(f"Error: {OBSERVABILITY_PAGE} not found")
        return 1

    changes = fix_file(OBSERVABILITY_PAGE, dry_run=dry_run)
    if changes > 0:
        print(f"{'Would fix' if dry_run else 'Fixed'} ObservabilityPage.tsx: {changes} replacements")
    else:
        print("No changes needed")

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
