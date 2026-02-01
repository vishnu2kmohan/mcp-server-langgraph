#!/usr/bin/env python3
# DEPRECATED: Use the unified design-system.py tool instead.
# Run: python scripts/design-system.py fix --dry-run
# See: python scripts/design-system.py --help

"""
Migrate ALL legacy Tailwind semantic color scales (50-950) to Radix scales (1-12).

This script handles ALL semantic colors, not just neutrals:
- warning-500 → warning-9
- success-500 → success-9
- error-500 → error-9
- info-500 → info-9
- primary-500 → primary-9
- insight-500 → insight-9
- grafana-500 → grafana-9

Mapping based on tailwind.config.ts legacy aliases:
  50  → 1
  100 → 2
  200 → 3
  300 → 4
  400 → 5
  500 → 9   (main interactive color)
  600 → 10
  700 → 11
  800 → 11
  900 → 12

Usage: python scripts/migrate-legacy-semantic-colors.py [--dry-run] [--verbose]
"""

import argparse
import re
import sys
from pathlib import Path
from collections import defaultdict

# Frontend source directory
FRONTEND_SRC = Path(__file__).parent.parent / "src"

# File extensions to process
EXTENSIONS = {".tsx", ".ts", ".jsx", ".js"}

# Directories to skip
SKIP_DIRS = {"node_modules", "dist", ".storybook", "coverage", "__snapshots__"}

# Semantic color names (excluding neutral which has its own script)
SEMANTIC_COLORS = ["warning", "success", "error", "info", "primary", "insight", "grafana"]

# Legacy to Radix mapping (based on tailwind.config.ts)
LEGACY_TO_RADIX = {
    "50": "1",
    "100": "2",
    "200": "3",
    "300": "4",
    "400": "5",
    "500": "9",  # Main solid color
    "600": "10",
    "700": "11",
    "800": "11",
    "900": "12",
    "950": "12",
}

# Tailwind utilities that use colors
UTILITIES = ["bg", "text", "border", "ring", "divide", "outline", "fill", "stroke"]


def build_patterns():
    """Build compiled regex patterns for all legacy colors."""
    patterns = []
    for color in SEMANTIC_COLORS:
        for legacy, radix in LEGACY_TO_RADIX.items():
            for util in UTILITIES:
                # Match[str] utility-color-legacyScale (e.g., bg-warning-500)
                pattern = re.compile(rf"\b{util}-{color}-{legacy}\b")
                replacement = f"{util}-{color}-{radix}"
                patterns.append((pattern, replacement, f"{util}-{color}-{legacy}"))
    return patterns


def should_skip(path: Path) -> bool:
    """Check if path should be skipped."""
    return any(skip in path.parts for skip in SKIP_DIRS)


def process_file(file_path: Path, patterns: list, dry_run: bool, verbose: bool) -> dict:
    """Process a single file. Returns dict of replacements made."""
    replacements = defaultdict(int)

    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"  Error reading {file_path}: {e}", file=sys.stderr)
        return replacements

    original = content

    for pattern, replacement, description in patterns:
        matches = pattern.findall(content)
        if matches:
            replacements[description] += len(matches)
            content = pattern.sub(replacement, content)

    if content != original:
        if verbose:
            for desc, count in replacements.items():
                print(f"  {file_path.name}: {desc} x{count}")

        if not dry_run:
            file_path.write_text(content, encoding="utf-8")

    return replacements


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate legacy semantic colors to Radix")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without applying")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed output")
    args = parser.parse_args()

    print(f"{'[DRY RUN] ' if args.dry_run else ''}Migrating legacy semantic colors to Radix...")
    print(f"Scanning: {FRONTEND_SRC}")

    patterns = build_patterns()
    total_replacements = defaultdict(int)
    files_modified = 0

    for ext in EXTENSIONS:
        for file_path in FRONTEND_SRC.rglob(f"*{ext}"):
            if should_skip(file_path):
                continue

            replacements = process_file(file_path, patterns, args.dry_run, args.verbose)
            if replacements:
                files_modified += 1
                for desc, count in replacements.items():
                    total_replacements[desc] += count

    # Summary
    print(f"\n{'=' * 60}")
    print(f"SUMMARY {'(DRY RUN)' if args.dry_run else ''}")
    print(f"{'=' * 60}")
    print(f"Files modified: {files_modified}")
    print(f"Total replacements: {sum(total_replacements.values())}")

    if total_replacements:
        print("\nReplacements by pattern:")
        for desc, count in sorted(total_replacements.items(), key=lambda x: -x[1]):
            print(f"  {desc}: {count}")

    if args.dry_run and total_replacements:
        print("\nRun without --dry-run to apply changes.")

    return 0 if not total_replacements or not args.dry_run else 0


if __name__ == "__main__":
    sys.exit(main())
