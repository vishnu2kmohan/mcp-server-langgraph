#!/usr/bin/env python3
"""
Fix canvas text colors to align with Radix design system.

Per STYLE.md:
- Steps 9-10: Solid backgrounds (buttons, badges, indicators)
- Steps 11-12: Text colors

This script fixes text-* classes that incorrectly use steps 9-10 to use step 11.
Dark mode text should also use step 11 (not 4-5-7-9).
"""

import re
import sys
from pathlib import Path

# Files to process
CANVAS_DIR = Path(__file__).parent.parent / "src" / "canvas"

# Patterns to fix for TEXT colors (not bg, not border)
# Match[str] text-{color}-{step} where step is 9 or 10
TEXT_FIXES = [
    # Neutral text: 9, 10 → 11
    (r"\btext-neutral-9\b", "text-neutral-11"),
    (r"\btext-neutral-10\b", "text-neutral-11"),
    # Primary text: 9, 10 → 11
    (r"\btext-primary-9\b", "text-primary-11"),
    (r"\btext-primary-10\b", "text-primary-11"),
    # Success text: 10 → 11
    (r"\btext-success-10\b", "text-success-11"),
    # Warning text: 9, 10 → 11
    (r"\btext-warning-9\b", "text-warning-11"),
    (r"\btext-warning-10\b", "text-warning-11"),
    # Error text: 9, 10 → 11
    (r"\btext-error-9\b", "text-error-11"),
    (r"\btext-error-10\b", "text-error-11"),
    # Insight text: 9, 10 → 11
    (r"\btext-insight-9\b", "text-insight-11"),
    (r"\btext-insight-10\b", "text-insight-11"),
    # Info text: 9 → 11
    (r"\btext-info-9\b", "text-info-11"),
    # Grafana text: 10 → 11
    (r"\btext-grafana-10\b", "text-grafana-11"),
]

# Dark mode text fixes - unify to step 11
DARK_TEXT_FIXES = [
    # dark:text-*-4, 5, 7, 9 → 11
    (r"\bdark:text-neutral-[4-9]\b", "dark:text-neutral-11"),
    (r"\bdark:text-primary-[4-9]\b", "dark:text-primary-11"),
    (r"\bdark:text-success-[4-9]\b", "dark:text-success-11"),
    (r"\bdark:text-warning-[4-9]\b", "dark:text-warning-11"),
    (r"\bdark:text-error-[4-9]\b", "dark:text-error-11"),
    (r"\bdark:text-insight-[4-9]\b", "dark:text-insight-11"),
    (r"\bdark:text-info-[4-9]\b", "dark:text-info-11"),
    (r"\bdark:text-grafana-[4-9]\b", "dark:text-grafana-11"),
]

# Border fixes - steps 11-12 are for text, borders should use 6-8
BORDER_FIXES = [
    (r"\bdark:border-error-11\b", "dark:border-error-7"),
    (r"\bdark:border-primary-11\b", "dark:border-primary-7"),
    (r"\bdark:border-success-11\b", "dark:border-success-7"),
    (r"\bdark:border-warning-11\b", "dark:border-warning-7"),
]


def fix_file(filepath: Path, dry_run: bool = False) -> int:
    """Fix a single file. Returns number of replacements made."""
    content = filepath.read_text()
    original = content
    changes = 0

    all_fixes = TEXT_FIXES + DARK_TEXT_FIXES + BORDER_FIXES

    for pattern, replacement in all_fixes:
        new_content, count = re.subn(pattern, replacement, content)
        if count > 0:
            changes += count
            content = new_content

    if changes > 0 and not dry_run:
        filepath.write_text(content)

    return changes


def main() -> int:
    dry_run = "--dry-run" in sys.argv
    verbose = "-v" in sys.argv or "--verbose" in sys.argv

    if dry_run:
        print("DRY RUN - no files will be modified\n")

    total_changes = 0
    files_changed = 0

    for tsx_file in sorted(CANVAS_DIR.glob("*.tsx")):
        changes = fix_file(tsx_file, dry_run=dry_run)
        if changes > 0:
            files_changed += 1
            total_changes += changes
            print(f"{'Would fix' if dry_run else 'Fixed'} {tsx_file.name}: {changes} replacements")
        elif verbose:
            print(f"No changes: {tsx_file.name}")

    print(f"\n{'Would modify' if dry_run else 'Modified'} {files_changed} files with {total_changes} total replacements")

    return 0 if total_changes > 0 or dry_run else 1


if __name__ == "__main__":
    sys.exit(main())
