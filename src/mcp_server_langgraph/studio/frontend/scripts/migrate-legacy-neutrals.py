#!/usr/bin/env python3
# DEPRECATED: Use the unified design-system.py tool instead.
# Run: python scripts/design-system.py fix --dry-run
# See: python scripts/design-system.py --help

"""
Efficient migration of legacy Tailwind neutral colors to Radix semantic colors.

Radix 1-12 Scale:
  1-2:   App backgrounds
  3-5:   Interactive backgrounds (hover, active)
  6-8:   Borders
  9-10:  Solid colors (buttons, badges)
  11-12: Text (secondary, primary)

Usage: python scripts/migrate-legacy-neutrals.py [--dry-run]

Memory-efficient: Processes files one at a time, compiles regex once.
"""

import os
import re
import sys
from pathlib import Path

DRY_RUN = "--dry-run" in sys.argv

# =============================================================================
# REPLACEMENT MAPPINGS (old → new)
# =============================================================================

# Text colors: high numbers → high Radix steps
TEXT_MAP = {
    "900": "12", "800": "12",  # High contrast
    "700": "11", "600": "11",  # Secondary
    "500": "10", "400": "9",   # Muted
    "300": "9", "200": "9", "100": "9",  # Very muted
}

# Background colors: high numbers → low Radix steps (inverted for surfaces)
BG_MAP = {
    "950": "2", "900": "2",    # Darkest surfaces
    "800": "3", "700": "4",    # Dark surfaces
    "600": "5", "500": "5",    # Medium
    "400": "4", "300": "3",    # Light (in context of dark theme)
    "200": "3", "100": "2", "50": "1",  # Lightest
}

# Border colors: map to 5-7 range
BORDER_MAP = {
    "800": "7", "700": "7",    # Strong
    "600": "6", "500": "6",    # Default
    "400": "6", "300": "5",    # Subtle
    "200": "5", "100": "5",    # Very subtle
}

# Hover backgrounds: interactive states
HOVER_BG_MAP = {
    "900": "3", "800": "4", "700": "5",
    "600": "5", "500": "5", "400": "4",
    "300": "4", "200": "4", "100": "3", "50": "3",
}

# =============================================================================
# BUILD COMPILED REGEX PATTERNS (done once at startup)
# =============================================================================

def build_replacements() -> dict[str, str]:
    """Build list of (compiled_pattern, replacement) tuples."""
    replacements = []

    # Text colors
    for old, new in TEXT_MAP.items():
        pattern = re.compile(rf'\btext-neutral-{old}\b')
        replacements.append((pattern, f'text-neutral-{new}'))

    # Background colors
    for old, new in BG_MAP.items():
        pattern = re.compile(rf'\bbg-neutral-{old}\b')
        replacements.append((pattern, f'bg-neutral-{new}'))

    # Border colors
    for old, new in BORDER_MAP.items():
        pattern = re.compile(rf'\bborder-neutral-{old}\b')
        replacements.append((pattern, f'border-neutral-{new}'))

    # Hover backgrounds
    for old, new in HOVER_BG_MAP.items():
        pattern = re.compile(rf'\bhover:bg-neutral-{old}\b')
        replacements.append((pattern, f'hover:bg-neutral-{new}'))

    # Focus states
    replacements.extend([
        (re.compile(r'\bfocus:bg-neutral-700\b'), 'focus:bg-neutral-4'),
        (re.compile(r'\bfocus:bg-neutral-100\b'), 'focus:bg-neutral-3'),
        (re.compile(r'\bfocus:bg-neutral-50\b'), 'focus:bg-neutral-3'),
        (re.compile(r'\bfocus:border-neutral-500\b'), 'focus:border-neutral-8'),
        (re.compile(r'\bfocus:border-neutral-400\b'), 'focus:border-neutral-7'),
    ])

    # Placeholder colors
    replacements.extend([
        (re.compile(r'\bplaceholder-neutral-500\b'), 'placeholder-neutral-9'),
        (re.compile(r'\bplaceholder-neutral-400\b'), 'placeholder-neutral-9'),
        (re.compile(r'\bplaceholder:text-neutral-500\b'), 'placeholder:text-neutral-9'),
        (re.compile(r'\bplaceholder:text-neutral-400\b'), 'placeholder:text-neutral-9'),
    ])

    # Divide colors
    replacements.extend([
        (re.compile(r'\bdivide-neutral-200\b'), 'divide-neutral-5'),
        (re.compile(r'\bdivide-neutral-300\b'), 'divide-neutral-6'),
        (re.compile(r'\bdivide-neutral-700\b'), 'divide-neutral-6'),
    ])

    # Ring colors
    replacements.extend([
        (re.compile(r'\bring-neutral-500\b'), 'ring-neutral-8'),
        (re.compile(r'\bring-neutral-400\b'), 'ring-neutral-7'),
        (re.compile(r'\bring-neutral-300\b'), 'ring-neutral-6'),
        (re.compile(r'\bring-neutral-200\b'), 'ring-neutral-5'),
    ])

    # bg-white → bg-neutral-1 (only when not part of another word)
    replacements.append(
        (re.compile(r'\bbg-white\b'), 'bg-neutral-1')
    )

    return replacements


REPLACEMENTS = build_replacements()


def process_file(filepath: Path) -> tuple[int, bool]:
    """
    Process a single file, applying all replacements.
    Returns (replacement_count, was_modified).
    """
    try:
        content = filepath.read_text(encoding='utf-8')
    except Exception as e:
        print(f"  Error reading {filepath}: {e}")
        return 0, False

    original = content
    total_count = 0

    # Apply all replacements in one pass through the list
    for pattern, replacement in REPLACEMENTS:
        content, count = pattern.subn(replacement, content)
        total_count += count

    if content != original:
        if not DRY_RUN:
            filepath.write_text(content, encoding='utf-8')
        return total_count, True

    return 0, False


def main() -> None:
    src_dir = Path("src")
    if not src_dir.exists():
        print("Error: src/ directory not found")
        sys.exit(1)

    print("=" * 60)
    print("Legacy Neutral Colors → Radix Migration")
    if DRY_RUN:
        print("DRY RUN - No files will be modified")
    print("=" * 60)
    print()

    # Find TSX files, excluding tests and stories
    files = [
        f for f in src_dir.rglob("*.tsx")
        if "node_modules" not in str(f)
        and ".test." not in f.name
        and ".stories." not in f.name
    ]

    print(f"Files to process: {len(files)}")

    total_replacements = 0
    modified_files = 0

    for filepath in sorted(files):
        count, modified = process_file(filepath)
        if modified:
            modified_files += 1
            total_replacements += count
            print(f"  {filepath}: {count} replacements")

    print()
    print("=" * 60)
    print(f"Migration complete!")
    print(f"  Files modified: {modified_files}")
    print(f"  Total replacements: {total_replacements}")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. npm run lint")
    print("2. npm run build")
    print("3. Visual test dark/light mode")


if __name__ == "__main__":
    main()
