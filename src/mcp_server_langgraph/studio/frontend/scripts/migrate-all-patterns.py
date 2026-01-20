#!/usr/bin/env python3
"""
Comprehensive migration of ALL legacy Tailwind patterns to Radix semantic colors.
Includes test files, stories, and dark: prefix patterns.

Usage: python scripts/migrate-all-patterns.py
"""

import re
from typing import Any, Pattern
import sys
from pathlib import Path

DRY_RUN = "--dry-run" in sys.argv

# =============================================================================
# REPLACEMENT PATTERNS
# =============================================================================

REPLACEMENTS = [
    # =========================================================================
    # Legacy neutral-XXX patterns (100-950 → 1-12)
    # =========================================================================
    # Text
    (r'\btext-neutral-900\b', 'text-neutral-12'),
    (r'\btext-neutral-800\b', 'text-neutral-12'),
    (r'\btext-neutral-700\b', 'text-neutral-11'),
    (r'\btext-neutral-600\b', 'text-neutral-11'),
    (r'\btext-neutral-500\b', 'text-neutral-10'),
    (r'\btext-neutral-400\b', 'text-neutral-9'),
    (r'\btext-neutral-300\b', 'text-neutral-9'),
    (r'\btext-neutral-200\b', 'text-neutral-9'),
    (r'\btext-neutral-100\b', 'text-neutral-9'),

    # Background
    (r'\bbg-neutral-950\b', 'bg-neutral-2'),
    (r'\bbg-neutral-900\b', 'bg-neutral-2'),
    (r'\bbg-neutral-800\b', 'bg-neutral-3'),
    (r'\bbg-neutral-700\b', 'bg-neutral-4'),
    (r'\bbg-neutral-600\b', 'bg-neutral-5'),
    (r'\bbg-neutral-500\b', 'bg-neutral-5'),
    (r'\bbg-neutral-400\b', 'bg-neutral-4'),
    (r'\bbg-neutral-300\b', 'bg-neutral-3'),
    (r'\bbg-neutral-200\b', 'bg-neutral-3'),
    (r'\bbg-neutral-100\b', 'bg-neutral-2'),
    (r'\bbg-neutral-50\b', 'bg-neutral-1'),

    # Border
    (r'\bborder-neutral-800\b', 'border-neutral-7'),
    (r'\bborder-neutral-700\b', 'border-neutral-7'),
    (r'\bborder-neutral-600\b', 'border-neutral-6'),
    (r'\bborder-neutral-500\b', 'border-neutral-6'),
    (r'\bborder-neutral-400\b', 'border-neutral-6'),
    (r'\bborder-neutral-300\b', 'border-neutral-5'),
    (r'\bborder-neutral-200\b', 'border-neutral-5'),
    (r'\bborder-neutral-100\b', 'border-neutral-5'),

    # Hover backgrounds
    (r'\bhover:bg-neutral-900\b', 'hover:bg-neutral-3'),
    (r'\bhover:bg-neutral-800\b', 'hover:bg-neutral-4'),
    (r'\bhover:bg-neutral-700\b', 'hover:bg-neutral-5'),
    (r'\bhover:bg-neutral-600\b', 'hover:bg-neutral-5'),
    (r'\bhover:bg-neutral-500\b', 'hover:bg-neutral-5'),
    (r'\bhover:bg-neutral-400\b', 'hover:bg-neutral-4'),
    (r'\bhover:bg-neutral-300\b', 'hover:bg-neutral-4'),
    (r'\bhover:bg-neutral-200\b', 'hover:bg-neutral-4'),
    (r'\bhover:bg-neutral-100\b', 'hover:bg-neutral-3'),
    (r'\bhover:bg-neutral-50\b', 'hover:bg-neutral-3'),

    # Focus
    (r'\bfocus:bg-neutral-700\b', 'focus:bg-neutral-4'),
    (r'\bfocus:bg-neutral-100\b', 'focus:bg-neutral-3'),
    (r'\bfocus:bg-neutral-50\b', 'focus:bg-neutral-3'),
    (r'\bfocus:border-neutral-500\b', 'focus:border-neutral-8'),
    (r'\bfocus:border-neutral-400\b', 'focus:border-neutral-7'),

    # =========================================================================
    # dark: prefix patterns - REMOVE (Radix auto-switches)
    # =========================================================================
    # dark:text-neutral-XXX → remove (keep the light mode version)
    (r'\s+dark:text-neutral-\d+', ''),
    (r'\s+dark:bg-neutral-\d+(/\d+)?', ''),
    (r'\s+dark:border-neutral-\d+', ''),
    (r'\s+dark:hover:bg-neutral-\d+', ''),
    (r'\s+dark:hover:text-neutral-\d+', ''),
    (r'\s+dark:focus:bg-neutral-\d+', ''),
    (r'\s+dark:focus:border-neutral-\d+', ''),
    (r'\s+dark:placeholder-neutral-\d+', ''),

    # Standalone dark: patterns in arrays (with quotes)
    (r'"dark:text-neutral-\d+"', ''),
    (r'"dark:bg-neutral-\d+(/\d+)?"', ''),
    (r'"dark:border-neutral-\d+"', ''),
    (r'"dark:hover:bg-neutral-\d+"', ''),
    (r'"dark:hover:text-neutral-\d+"', ''),

    # =========================================================================
    # bg-white → bg-neutral-1 (for dark mode support)
    # =========================================================================
    (r'\bbg-white\b', 'bg-neutral-1'),

    # =========================================================================
    # Placeholder patterns
    # =========================================================================
    (r'\bplaceholder-neutral-500\b', 'placeholder-neutral-9'),
    (r'\bplaceholder-neutral-400\b', 'placeholder-neutral-9'),
    (r'\bplaceholder:text-neutral-500\b', 'placeholder:text-neutral-9'),
    (r'\bplaceholder:text-neutral-400\b', 'placeholder:text-neutral-9'),

    # =========================================================================
    # Ring and divide
    # =========================================================================
    (r'\bring-neutral-500\b', 'ring-neutral-8'),
    (r'\bring-neutral-400\b', 'ring-neutral-7'),
    (r'\bring-neutral-300\b', 'ring-neutral-6'),
    (r'\bring-neutral-200\b', 'ring-neutral-5'),
    (r'\bdivide-neutral-200\b', 'divide-neutral-5'),
    (r'\bdivide-neutral-300\b', 'divide-neutral-6'),
    (r'\bdivide-neutral-700\b', 'divide-neutral-6'),
]

# Compile patterns once
COMPILED = [(re.compile(p), r) for p, r in REPLACEMENTS]


def process_file(filepath: Path) -> tuple[int, bool]:
    """Process a single file."""
    try:
        content = filepath.read_text(encoding='utf-8')
    except Exception:
        return 0, False

    original = content
    total = 0

    for pattern, replacement in COMPILED:
        content, count = pattern.subn(replacement, content)
        total += count

    # Clean up orphan commas from removed dark: patterns
    # "class1", , "class2" → "class1", "class2"
    content = re.sub(r',\s*,', ',', content)

    if content != original:
        if not DRY_RUN:
            filepath.write_text(content, encoding='utf-8')
        return total, True
    return 0, False


def main() -> None:
    src_dir = Path("src")
    if not src_dir.exists():
        print("Error: src/ directory not found")
        sys.exit(1)

    print("=" * 60)
    print("Comprehensive Pattern[str] Migration (all files)")
    if DRY_RUN:
        print("DRY RUN - No files will be modified")
    print("=" * 60)

    # ALL TSX/TS files including tests and stories
    files = list(src_dir.rglob("*.tsx")) + list(src_dir.rglob("*.ts"))
    files = [f for f in files if "node_modules" not in str(f)]

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


if __name__ == "__main__":
    main()
