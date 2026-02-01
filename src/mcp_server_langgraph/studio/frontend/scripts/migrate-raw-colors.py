#!/usr/bin/env python3
# DEPRECATED: Use the unified design-system.py tool instead.
# Run: python scripts/design-system.py fix --dry-run
# See: python scripts/design-system.py --help

"""
Migrate raw Tailwind colors to semantic Radix colors.

Maps color families to semantic tokens:
- red/rose -> error-*
- green/emerald/lime -> success-*
- yellow/amber -> warning-*
- blue/indigo/sky -> primary-*
- violet/purple -> insight-*
- cyan/teal -> info-*
- orange -> grafana-*
- gray/slate/zinc/stone -> neutral-*

Radix scale mapping (1-12):
- 100/50 -> 3 (subtle backgrounds)
- 200 -> 4 (hovered backgrounds)
- 300 -> 5 (active/selected)
- 400 -> 6-7 (borders)
- 500 -> 9 (solid colors)
- 600 -> 10 (solid hover)
- 700 -> 11 (low contrast text)
- 800 -> 12 (high contrast text)
- 900 -> 3-4 (dark mode backgrounds)
"""

import re
import sys
from pathlib import Path

# Mapping from Tailwind numeric scale to Radix scale
TAILWIND_TO_RADIX = {
    "50": "2",
    "100": "3",
    "200": "4",
    "300": "5",
    "400": "7",
    "500": "9",
    "600": "10",
    "700": "11",
    "800": "12",
    "900": "12",  # 900 in dark mode contexts maps to high contrast
    "950": "12",
}

# Special handling for dark mode backgrounds (900/X opacity)
DARK_BG_MAP = {
    "900/10": "3",
    "900/20": "3",
    "900/30": "4",
    "900/40": "4",
    "900/50": "5",
}

# Color family to semantic token mapping
COLOR_FAMILY_MAP = {
    # Error colors
    "red": "error",
    "rose": "error",
    # Success colors
    "green": "success",
    "emerald": "success",
    "lime": "success",
    # Warning colors
    "yellow": "warning",
    "amber": "warning",
    # Primary colors (brand)
    "blue": "primary",
    "indigo": "primary",
    "sky": "primary",
    # Insight/AI colors
    "violet": "insight",
    "purple": "insight",
    # Info colors
    "cyan": "info",
    "teal": "info",
    # Grafana/monitoring colors
    "orange": "grafana",
    # Neutral colors
    "gray": "neutral",
    "slate": "neutral",
    "zinc": "neutral",
    "stone": "neutral",
    "fuchsia": "insight",  # Map to insight as well
    "pink": "error",  # Pink is often used for errors/warnings
}


def migrate_color(match: re.Match[str]) -> str:
    """Convert a raw Tailwind color to semantic Radix color."""
    full_match = match.group(0)
    prefix = match.group(1)  # e.g., "bg-", "text-", "border-"
    color = match.group(2)  # e.g., "indigo"
    shade = match.group(3)  # e.g., "500" or "900/30"

    # Get semantic color family
    semantic_color = COLOR_FAMILY_MAP.get(color)
    if not semantic_color:
        return full_match  # Don't change unknown colors

    # Check for dark mode background patterns first
    if shade in DARK_BG_MAP:
        radix_step = DARK_BG_MAP[shade]
    else:
        # Strip opacity suffix for lookup if present
        base_shade = shade.split("/")[0]
        radix_step = TAILWIND_TO_RADIX.get(base_shade)
        if not radix_step:
            return full_match  # Don't change unknown shades

    return f"{prefix}{semantic_color}-{radix_step}"


def process_file(file_path: Path, dry_run: bool = False) -> tuple[int, list[str]]:
    """Process a single file and return (change_count, changes)."""
    content = file_path.read_text()
    original = content

    # Pattern[str] to match raw Tailwind colors
    # Captures: (prefix)(color-family)(shade with optional opacity)
    # Examples: bg-indigo-500, text-violet-700, border-blue-300, bg-violet-900/30
    pattern = re.compile(
        r"((?:bg|text|border|ring|divide|outline|shadow|from|to|via|fill|stroke|decoration|accent|caret|placeholder)-)"
        r"(red|rose|green|emerald|lime|yellow|amber|blue|indigo|sky|violet|purple|cyan|teal|orange|fuchsia|pink)"
        r"-(\d+(?:/\d+)?)"
    )

    changes = []

    def replace_and_track(match: re.Match[str]) -> str:
        new_value = migrate_color(match)
        if new_value != match.group(0):
            changes.append(f"  {match.group(0)} -> {new_value}")
        return new_value

    content = pattern.sub(replace_and_track, content)

    if content != original:
        if not dry_run:
            file_path.write_text(content)
        return len(changes), changes

    return 0, []


def main() -> None:
    dry_run = "--dry-run" in sys.argv
    verbose = "-v" in sys.argv or "--verbose" in sys.argv

    # Get source directory
    src_dir = Path(__file__).parent.parent / "src"

    if not src_dir.exists():
        print(f"Error: Source directory not found: {src_dir}")
        sys.exit(1)

    # Find all TypeScript/TSX files
    files = list(src_dir.rglob("*.tsx")) + list(src_dir.rglob("*.ts"))
    files = [f for f in files if "node_modules" not in str(f)]

    total_changes = 0
    files_changed = 0

    print(f"{'[DRY RUN] ' if dry_run else ''}Migrating raw Tailwind colors to semantic Radix colors...")
    print(f"Scanning {len(files)} files...\n")

    for file_path in sorted(files):
        count, changes = process_file(file_path, dry_run)
        if count > 0:
            files_changed += 1
            total_changes += count
            rel_path = file_path.relative_to(src_dir.parent)
            print(f"{'Would update' if dry_run else 'Updated'} {rel_path} ({count} changes)")
            if verbose:
                for change in changes:
                    print(change)

    print(f"\n{'Would update' if dry_run else 'Updated'} {total_changes} color references in {files_changed} files")

    if dry_run and total_changes > 0:
        print("\nRun without --dry-run to apply changes.")


if __name__ == "__main__":
    main()
