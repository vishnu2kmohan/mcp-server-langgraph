#!/usr/bin/env python3
"""
Comprehensive migration script for legacy Tailwind dark mode patterns to Radix semantic colors.

Radix Colors v3.0.0+ uses .dark class selector - colors auto-switch.

Radix 1-12 Scale Reference:
  1-2:   App backgrounds
  3-5:   Interactive backgrounds (hover, active)
  6-8:   Borders
  9-10:  Solid colors (buttons, badges)
  11-12: Text (secondary, primary)

Usage: python scripts/migrate-to-radix.py [--dry-run]
"""

import re
import sys
from pathlib import Path

DRY_RUN = "--dry-run" in sys.argv

# Mapping of legacy patterns to Radix semantic colors
REPLACEMENTS = [
    # ==========================================================================
    # PHASE 1: BACKGROUND COLORS (light dark:dark patterns)
    # ==========================================================================
    # Pure white/black backgrounds
    (r"bg-white\s+dark:bg-neutral-900", "bg-neutral-1"),
    (r"bg-white\s+dark:bg-gray-900", "bg-neutral-1"),
    (r"bg-white\s+dark:bg-neutral-800", "bg-neutral-1"),
    # Light backgrounds (50-200 scale)
    (r"bg-neutral-50\s+dark:bg-neutral-900", "bg-neutral-1"),
    (r"bg-neutral-50\s+dark:bg-neutral-800", "bg-neutral-2"),
    (r"bg-neutral-100\s+dark:bg-neutral-900", "bg-neutral-2"),
    (r"bg-neutral-100\s+dark:bg-neutral-800", "bg-neutral-3"),
    (r"bg-neutral-100\s+dark:bg-neutral-700", "bg-neutral-4"),
    (r"bg-neutral-200\s+dark:bg-neutral-800", "bg-neutral-4"),
    (r"bg-neutral-200\s+dark:bg-neutral-700", "bg-neutral-5"),
    # Semantic background colors with opacity
    (r"bg-(primary|success|warning|error|info|insight)-50\s+dark:bg-\1-900/\d+", r"bg-\1-3"),
    (r"bg-(primary|success|warning|error|info|insight)-100\s+dark:bg-\1-900/\d+", r"bg-\1-3"),
    (r"bg-(primary|success|warning|error|info|insight)-100\s+dark:bg-\1-800/\d+", r"bg-\1-4"),
    (r"bg-(primary|success|warning|error|info|insight)-200\s+dark:bg-\1-800/\d+", r"bg-\1-5"),
    (r"bg-(primary|success|warning|error|info|insight)-200\s+dark:bg-\1-700/\d+", r"bg-\1-5"),
    # Gradient from/to patterns
    (r"from-neutral-50\s+to-neutral-100\s+dark:from-neutral-900\s+dark:to-neutral-800", "from-neutral-1 to-neutral-2"),
    (
        r"from-(primary|success|warning|error|info|insight)-50\s+to-\1-100\s+dark:from-\1-900\s+dark:to-\1-800",
        r"from-\1-1 to-\1-2",
    ),
    (
        r"dark:from-(primary|success|warning|error|info|insight|neutral)-900/\d+\s+dark:to-(primary|success|warning|error|info|insight|neutral)-900/\d+",
        "",
    ),
    # ==========================================================================
    # PHASE 2: TEXT COLORS
    # ==========================================================================
    # High contrast text (headings, body) - neutral
    (r"text-neutral-900\s+dark:text-neutral-100", "text-neutral-12"),
    (r"text-neutral-900\s+dark:text-neutral-50", "text-neutral-12"),
    (r"text-neutral-900\s+dark:text-white", "text-neutral-12"),
    (r"text-neutral-800\s+dark:text-neutral-100", "text-neutral-12"),
    (r"text-neutral-800\s+dark:text-neutral-200", "text-neutral-12"),
    # Secondary text - neutral
    (r"text-neutral-700\s+dark:text-neutral-300", "text-neutral-11"),
    (r"text-neutral-700\s+dark:text-neutral-200", "text-neutral-11"),
    (r"text-neutral-600\s+dark:text-neutral-400", "text-neutral-11"),
    (r"text-neutral-600\s+dark:text-neutral-300", "text-neutral-11"),
    # Muted/placeholder text - neutral
    (r"text-neutral-500\s+dark:text-neutral-400", "text-neutral-10"),
    (r"text-neutral-500\s+dark:text-neutral-300", "text-neutral-10"),
    (r"text-neutral-400\s+dark:text-neutral-500", "text-neutral-9"),
    (r"text-neutral-400\s+dark:text-neutral-300", "text-neutral-9"),
    # Semantic text colors
    (r"text-(primary|success|warning|error|info|insight|grafana)-900\s+dark:text-\1-100", r"text-\1-12"),
    (r"text-(primary|success|warning|error|info|insight|grafana)-800\s+dark:text-\1-200", r"text-\1-11"),
    (r"text-(primary|success|warning|error|info|insight|grafana)-800\s+dark:text-\1-300", r"text-\1-11"),
    (r"text-(primary|success|warning|error|info|insight|grafana)-700\s+dark:text-\1-300", r"text-\1-11"),
    (r"text-(primary|success|warning|error|info|insight|grafana)-700\s+dark:text-\1-400", r"text-\1-11"),
    (r"text-(primary|success|warning|error|info|insight|grafana)-600\s+dark:text-\1-400", r"text-\1-11"),
    (r"text-(primary|success|warning|error|info|insight|grafana)-600\s+dark:text-\1-300", r"text-\1-11"),
    (r"text-(primary|success|warning|error|info|insight|grafana)-500\s+dark:text-\1-400", r"text-\1-9"),
    (r"text-(primary|success|warning|error|info|insight|grafana)-500\s+dark:text-\1-300", r"text-\1-9"),
    # ==========================================================================
    # PHASE 3: BORDER COLORS
    # ==========================================================================
    (r"border-neutral-200\s+dark:border-neutral-700", "border-neutral-6"),
    (r"border-neutral-200\s+dark:border-neutral-600", "border-neutral-6"),
    (r"border-neutral-200\s+dark:border-neutral-800", "border-neutral-6"),
    (r"border-neutral-300\s+dark:border-neutral-600", "border-neutral-6"),
    (r"border-neutral-300\s+dark:border-neutral-700", "border-neutral-7"),
    (r"border-neutral-300\s+dark:border-neutral-800", "border-neutral-7"),
    # Semantic border colors
    (r"border-(primary|success|warning|error|info|insight|grafana)-200\s+dark:border-\1-700", r"border-\1-6"),
    (r"border-(primary|success|warning|error|info|insight|grafana)-200\s+dark:border-\1-800", r"border-\1-6"),
    (r"border-(primary|success|warning|error|info|insight|grafana)-300\s+dark:border-\1-700", r"border-\1-7"),
    (r"border-(primary|success|warning|error|info|insight|grafana)-500\s+dark:border-\1-400", r"border-\1-9"),
    # ==========================================================================
    # PHASE 4: HOVER STATES
    # ==========================================================================
    # Background hovers
    (r"hover:bg-neutral-100\s+dark:hover:bg-neutral-700", "hover:bg-neutral-4"),
    (r"hover:bg-neutral-100\s+dark:hover:bg-neutral-800", "hover:bg-neutral-3"),
    (r"hover:bg-neutral-50\s+dark:hover:bg-neutral-800", "hover:bg-neutral-3"),
    (r"hover:bg-neutral-200\s+dark:hover:bg-neutral-600", "hover:bg-neutral-5"),
    (r"hover:bg-neutral-200\s+dark:hover:bg-neutral-700", "hover:bg-neutral-5"),
    (r"hover:bg-neutral-5\s+dark:hover:bg-neutral-700", "hover:bg-neutral-5"),
    # Semantic hover colors
    (r"hover:bg-(primary|success|warning|error|info|insight|grafana)-100\s+dark:hover:bg-\1-800/\d+", r"hover:bg-\1-4"),
    (r"hover:bg-(primary|success|warning|error|info|insight|grafana)-100\s+dark:hover:bg-\1-700", r"hover:bg-\1-4"),
    (r"hover:bg-(primary|success|warning|error|info|insight|grafana)-200\s+dark:hover:bg-\1-700", r"hover:bg-\1-5"),
    (r"hover:bg-(primary|success|warning|error|info|insight|grafana)-200\s+dark:hover:bg-\1-800/\d+", r"hover:bg-\1-5"),
    # Text hovers
    (r"hover:text-neutral-900\s+dark:hover:text-neutral-100", "hover:text-neutral-12"),
    (r"hover:text-neutral-800\s+dark:hover:text-neutral-200", "hover:text-neutral-12"),
    (r"hover:text-neutral-700\s+dark:hover:text-neutral-300", "hover:text-neutral-11"),
    # ==========================================================================
    # PHASE 5: FOCUS STATES
    # ==========================================================================
    (r"focus:border-primary-500\s+dark:focus:border-primary-400", "focus:border-primary-9"),
    (r"focus:ring-primary-500\s+dark:focus:ring-primary-400", "focus:ring-primary-9"),
    (r"focus:ring-primary-500/20\s+dark:focus:ring-primary-400/20", "focus:ring-primary-9/20"),
    # ==========================================================================
    # PHASE 6: PLACEHOLDERS
    # ==========================================================================
    (r"placeholder:text-neutral-400\s+dark:placeholder:text-neutral-500", "placeholder:text-neutral-9"),
    (r"placeholder:text-neutral-500\s+dark:placeholder:text-neutral-400", "placeholder:text-neutral-9"),
    (r"placeholder-neutral-400\s+dark:placeholder-neutral-500", "placeholder-neutral-9"),
    (r"placeholder-neutral-500\s+dark:placeholder-neutral-400", "placeholder-neutral-9"),
    # ==========================================================================
    # PHASE 7: DIVIDERS (bg-neutral-XXX patterns commonly used for dividers)
    # ==========================================================================
    (r"bg-neutral-300\s+dark:bg-neutral-600", "bg-neutral-6"),
    (r"bg-neutral-200\s+dark:bg-neutral-700", "bg-neutral-6"),
    (r"bg-neutral-100\s+dark:bg-neutral-700", "bg-neutral-5"),
    # ==========================================================================
    # PHASE 8: ORPHAN CLEANUP (standalone dark: patterns)
    # ==========================================================================
    # These are dark: patterns that exist without a paired light pattern
    (r"\s+dark:bg-neutral-900(/\d+)?", ""),
    (r"\s+dark:bg-neutral-800(/\d+)?", ""),
    (r"\s+dark:bg-neutral-700(/\d+)?", ""),
    (r"\s+dark:text-neutral-100", ""),
    (r"\s+dark:text-neutral-200", ""),
    (r"\s+dark:text-neutral-300", ""),
    (r"\s+dark:border-neutral-700", ""),
    (r"\s+dark:border-neutral-800", ""),
    (r"\s+dark:hover:bg-neutral-700", ""),
    (r"\s+dark:hover:bg-neutral-800", ""),
    (r"\s+dark:hover:text-neutral-300", ""),
    (r"\s+dark:hover:text-neutral-200", ""),
    # Semantic orphans
    (r"\s+dark:text-(primary|success|warning|error|info|insight|grafana)-400", ""),
    (r"\s+dark:bg-(primary|success|warning|error|info|insight|grafana)-900/\d+", ""),
    # ==========================================================================
    # PHASE 9: ADDITIONAL PATTERNS FOUND IN AUDIT
    # ==========================================================================
    # dark:text-white patterns
    (r"\s+dark:text-white", ""),
    # Standalone dark:bg-{color}-900 patterns (without opacity)
    (r"\s+dark:bg-(primary|success|warning|error|info|insight|grafana)-900\b", ""),
    (r"\s+dark:bg-(primary|success|warning|error|info|insight|grafana)-950(/\d+)?", ""),
    (r"\s+dark:bg-(primary|success|warning|error|info|insight|grafana)-800\b", ""),
    (r"\s+dark:bg-(primary|success|warning|error|info|insight|grafana)-600\b", ""),
    # Standalone dark:text-{color}-XXX patterns
    (r"\s+dark:text-(primary|success|warning|error|info|insight|grafana)-300", ""),
    (r"\s+dark:text-(primary|success|warning|error|info|insight|grafana)-200", ""),
    (r"\s+dark:text-(primary|success|warning|error|info|insight|grafana)-100", ""),
    (r"\s+dark:text-neutral-500", ""),
    (r"\s+dark:text-neutral-400", ""),
    # Additional border orphans
    (r"\s+dark:border-(primary|success|warning|error|info|insight|grafana)-800", ""),
    (r"\s+dark:border-neutral-500", ""),
    (r"\s+dark:border-neutral-600", ""),
    (r"\s+dark:border-t-neutral-700", ""),
    # Additional background orphans with bg-neutral-600
    (r"\s+dark:bg-neutral-600", ""),
    # ==========================================================================
    # PHASE 10: FINAL CLEANUP
    # ==========================================================================
    # Opacity patterns with trailing /
    (r"\s+dark:text-(primary|success|warning|error|info|insight|grafana)-400/\d*", ""),
    (r"\s+dark:text-(primary|success|warning|error|info|insight|grafana)-300/\d*", ""),
    (r"\s+dark:bg-insight-/\d*", ""),
    (r"\s+dark:bg-black/\d+", ""),
    # Remaining neutral patterns
    (r"\s+dark:bg-neutral-950", ""),
    (r"\s+dark:bg-neutral-900\b", ""),
    (r"\s+dark:bg-neutral-700", ""),
    # Primary/semantic solid colors (500/600 range)
    (r"\s+dark:bg-(primary|success|warning|error|info|insight|grafana)-500", ""),
    (r"\s+dark:border-(primary|success|warning|error|info|insight|grafana)-400", ""),
    (r"\s+dark:border-(primary|success|warning|error|info|insight|grafana)-600", ""),
    # Chat bubble custom classes
    (r"\s+dark:bg-chat-user-bubble-dark", ""),
    (r"\s+dark:bg-chat-ai-bubble-dark", ""),
    # Final neutral text cleanup
    (r"\s+dark:text-neutral-100", ""),
    # ==========================================================================
    # PHASE 11: CVA ARRAY PATTERNS (standalone items in arrays)
    # ==========================================================================
    # Standalone dark:bg-neutral-XXX in arrays
    (r'"dark:bg-neutral-700"', ""),
    (r'"dark:bg-neutral-800"', ""),
    (r'"dark:bg-neutral-900/50"', ""),
    (r'"dark:bg-(primary|success|warning|error|info|insight|grafana)-900/50"', ""),
    (r'"dark:bg-(primary|success|warning|error|info|insight|grafana)-600"', ""),
    (r'"dark:text-neutral-200"', ""),
    (r'"dark:text-neutral-300"', ""),
    (r'"dark:text-neutral-100"', ""),
    # Button hover patterns
    (r"\s+dark:bg-primary-600 dark:hover:bg-primary-500", ""),
    (r"\s+dark:hover:bg-primary-500", ""),
    # Checkbox/radio checked patterns
    (r"\s+checked:dark:bg-primary-600 checked:dark:border-primary-600", ""),
    # Border error pattern
    (r"\s+dark:border-error-500", ""),
    # Prose dark variant (keep this - it's a prose plugin class)
    # (r'dark:prose-invert', ''),  # Keep - Tailwind prose plugin
]


def process_file(filepath: Path) -> tuple[int, list[str]]:
    """Process a single file and return (replacement_count, changes)."""
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception as e:
        return 0, [f"Error reading {filepath}: {e}"]

    original_content = content
    changes = []
    total_replacements = 0

    for pattern, replacement in REPLACEMENTS:
        new_content, count = re.subn(pattern, replacement, content)
        if count > 0:
            changes.append(f"  {pattern[:50]}... -> {replacement}: {count}")
            total_replacements += count
            content = new_content

    if content != original_content:
        if not DRY_RUN:
            filepath.write_text(content, encoding="utf-8")

    return total_replacements, changes


def main() -> None:
    src_dir = Path("src")

    if not src_dir.exists():
        print(f"Error: {src_dir} directory not found")
        sys.exit(1)

    print("=" * 60)
    print("COMPREHENSIVE Radix Colors Migration")
    if DRY_RUN:
        print("DRY RUN - No files will be modified")
    print("=" * 60)
    print()

    # Find all TypeScript/TSX files
    files = list(src_dir.rglob("*.tsx")) + list(src_dir.rglob("*.ts"))

    # Exclude node_modules and test files for clarity
    files = [f for f in files if "node_modules" not in str(f)]

    total_files = 0
    total_replacements = 0

    for filepath in sorted(files):
        count, changes = process_file(filepath)
        if count > 0:
            total_files += 1
            total_replacements += count
            print(f"{filepath}: {count} replacements")
            for change in changes[:5]:  # Limit output
                print(change)
            if len(changes) > 5:
                print(f"  ... and {len(changes) - 5} more")

    print()
    print("=" * 60)
    print(f"Migration complete: {total_replacements} replacements in {total_files} files")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Run: npm run build")
    print("2. Run: npm run lint")
    print("3. Run: npm run test")
    print("4. Test dark/light mode switching visually")


if __name__ == "__main__":
    main()
