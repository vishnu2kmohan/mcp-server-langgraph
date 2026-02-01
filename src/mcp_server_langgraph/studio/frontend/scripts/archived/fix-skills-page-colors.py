#!/usr/bin/env python3
"""
Fix SkillsPage colors to align with Radix design system.

Per STYLE.md:
- Legacy semantic tokens → Radix tokens
- Steps 9-10: Solid colors (buttons, badges, icons)
- Steps 11-12: Text colors
"""

import re
from pathlib import Path

SKILLS_PAGE = Path(__file__).parent.parent / "src" / "pages" / "SkillsPage.tsx"

# Surface/background tokens
SURFACE_FIXES = [
    (r"\bbg-surface-primary\b", "bg-neutral-1"),
    (r"\bbg-surface-secondary\b", "bg-neutral-2"),
    (r"\bbg-surface-tertiary\b", "bg-neutral-3"),
]

# Border tokens
BORDER_FIXES = [
    (r"\bborder-border-primary\b", "border-neutral-6"),
]

# Text tokens - primary/secondary/tertiary
TEXT_FIXES = [
    (r"\btext-text-primary\b", "text-neutral-12"),
    (r"\btext-text-secondary\b", "text-neutral-11"),
    (r"\btext-text-tertiary\b", "text-neutral-9"),
]

# Accent tokens
ACCENT_FIXES = [
    (r"\btext-accent-primary\b", "text-primary-9"),
    (r"\bbg-accent-primary\b", "bg-primary-9"),
    (r"\bfocus:ring-accent-primary\b", "focus:ring-primary-7"),
    (r"\bhover:border-accent-primary\b", "hover:border-primary-7"),
]

# Semantic color tokens for errors/success
# Note: For icons use step 9, for text use step 11
SEMANTIC_FIXES = [
    # Error text → error-11, but icon colors stay at 9
    (r"\btext-semantic-error\b", "text-error-9"),  # Most usages are icons
    (r"\bbg-semantic-error\b", "bg-error-9"),
    # Success
    (r"\btext-semantic-success\b", "text-success-9"),  # Most usages are icons
]


def fix_file(filepath: Path, dry_run: bool = False) -> int:
    """Fix a single file. Returns number of replacements made."""
    content = filepath.read_text()
    original = content
    changes = 0

    all_fixes = SURFACE_FIXES + BORDER_FIXES + TEXT_FIXES + ACCENT_FIXES + SEMANTIC_FIXES

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

    if not SKILLS_PAGE.exists():
        print(f"Error: {SKILLS_PAGE} not found")
        return 1

    changes = fix_file(SKILLS_PAGE, dry_run=dry_run)
    if changes > 0:
        print(f"{'Would fix' if dry_run else 'Fixed'} SkillsPage.tsx: {changes} replacements")
    else:
        print("No changes needed")

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
