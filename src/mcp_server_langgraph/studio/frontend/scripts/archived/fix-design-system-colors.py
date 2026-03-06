#!/usr/bin/env python3
# DEPRECATED: Use the unified design-system.py tool instead.
# Run: python scripts/design-system.py fix --dry-run
# See: python scripts/design-system.py --help

"""
Bulk fix script for design system color violations.

This script replaces raw Tailwind color references with Radix semantic tokens
to ensure consistent dark/light mode support.

Replacements:
- text-white -> text-neutral-12 (or text-{semantic}-contrast for buttons)
- text-black -> text-neutral-1
- bg-white -> bg-neutral-1
- bg-black -> bg-neutral-12
- bg-black/50 -> bg-neutral-12/50 (preserves opacity)
- dark:text-white -> (removed, Radix handles dark mode)
- dark:text-black -> (removed, Radix handles dark mode)

Usage:
    python scripts/fix-design-system-colors.py [--dry-run] [--verbose]

Exit codes:
    0: Success (files fixed or no violations)
    1: Error during processing
"""

import argparse
import re
import sys
from pathlib import Path
from typing import NamedTuple

# Frontend source directory
FRONTEND_SRC = Path(__file__).parent.parent / "src"

# File extensions to process
EXTENSIONS = {".tsx", ".ts", ".jsx", ".js"}

# Files/directories to skip
SKIP_PATTERNS = {
    "node_modules",
    "dist",
    ".storybook",
    "coverage",
    "__snapshots__",
}


class Replacement(NamedTuple):
    """A color replacement rule"""

    pattern: str
    replacement: str
    description: str


class Violation(NamedTuple):
    """A detected violation"""

    file: Path
    line_no: int
    line: str
    pattern: str
    replacement: str


# Replacement rules (order matters - more specific first)
REPLACEMENTS = [
    # Remove redundant dark mode overrides (Radix handles dark mode)
    Replacement(r"\s*dark:text-white\b", "", "Remove redundant dark:text-white"),
    Replacement(r"\s*dark:text-black\b", "", "Remove redundant dark:text-black"),
    Replacement(r"\s*dark:bg-white\b", "", "Remove redundant dark:bg-white"),
    Replacement(r"\s*dark:bg-black\b", "", "Remove redundant dark:bg-black"),
    # Background colors with opacity
    Replacement(r"\bbg-black/(\d+)", r"bg-neutral-12/\1", "Replace bg-black/N with bg-neutral-12/N"),
    Replacement(r"\bbg-white/(\d+)", r"bg-neutral-1/\1", "Replace bg-white/N with bg-neutral-1/N"),
    # Solid colors
    Replacement(r"\btext-white\b", "text-neutral-12", "Replace text-white with text-neutral-12"),
    Replacement(r"\btext-black\b", "text-neutral-1", "Replace text-black with text-neutral-1"),
    Replacement(r"\bbg-white\b", "bg-neutral-1", "Replace bg-white with bg-neutral-1"),
    Replacement(r"\bbg-black\b", "bg-neutral-12", "Replace bg-black with bg-neutral-12"),
    # Border colors
    Replacement(r"\bborder-white\b", "border-neutral-1", "Replace border-white with border-neutral-1"),
    Replacement(r"\bborder-black\b", "border-neutral-12", "Replace border-black with border-neutral-12"),
    # Ring colors
    Replacement(r"\bring-white\b", "ring-neutral-1", "Replace ring-white with ring-neutral-1"),
    Replacement(r"\bring-black\b", "ring-neutral-12", "Replace ring-black with ring-neutral-12"),
]


def should_skip_file(file_path: Path) -> bool:
    """Check if file should be skipped"""
    return any(skip in file_path.parts for skip in SKIP_PATTERNS)


def find_violations(content: str, file_path: Path) -> list[Violation]:
    """Find all violations in file content"""
    violations = []
    lines = content.splitlines()

    for line_no, line in enumerate(lines, 1):
        for rule in REPLACEMENTS:
            if re.search(rule.pattern, line):
                violations.append(
                    Violation(
                        file=file_path,
                        line_no=line_no,
                        line=line.strip(),
                        pattern=rule.pattern,
                        replacement=rule.replacement,
                    )
                )

    return violations


def apply_fixes(content: str) -> tuple[str, int]:
    """Apply all fixes to content"""
    fix_count = 0

    for rule in REPLACEMENTS:
        new_content, count = re.subn(rule.pattern, rule.replacement, content)
        if count > 0:
            fix_count += count
            content = new_content

    return content, fix_count


def process_file(file_path: Path, dry_run: bool = False, verbose: bool = False) -> tuple[int, list[Violation]]:
    """Process a single file"""
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
        return 0, []

    violations = find_violations(content, file_path)

    if not violations:
        return 0, []

    if verbose:
        print(f"\n{file_path}:")
        for v in violations:
            print(f"  Line {v.line_no}: {v.line[:80]}...")

    if dry_run:
        return len(violations), violations

    new_content, fix_count = apply_fixes(content)

    if fix_count > 0:
        try:
            file_path.write_text(new_content, encoding="utf-8")
            if verbose:
                print(f"  → Fixed {fix_count} violation(s)")
        except Exception as e:
            print(f"Error writing {file_path}: {e}", file=sys.stderr)
            return 0, violations

    return fix_count, violations


def main(argv: list[str] | None = None) -> int:
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Fix design system color violations in frontend code")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show violations without fixing them",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed output",
    )
    parser.add_argument(
        "files",
        nargs="*",
        type=Path,
        help="Specific files to process (default: all frontend src)",
    )

    args = parser.parse_args(argv)

    # Determine files to process
    if args.files:
        files = [f for f in args.files if f.suffix in EXTENSIONS and f.exists()]
    else:
        if not FRONTEND_SRC.exists():
            print(f"Frontend source directory not found: {FRONTEND_SRC}", file=sys.stderr)
            return 1
        files = [f for f in FRONTEND_SRC.rglob("*") if f.suffix in EXTENSIONS and not should_skip_file(f)]

    total_violations = 0
    total_fixes = 0
    files_with_violations = 0
    all_violations: list[Violation] = []

    for file_path in sorted(files):
        fix_count, violations = process_file(file_path, args.dry_run, args.verbose)
        if violations:
            files_with_violations += 1
            total_violations += len(violations)
            all_violations.extend(violations)
        if fix_count:
            total_fixes += fix_count

    # Summary
    print("\n" + "=" * 60)
    if args.dry_run:
        print(f"DRY RUN - Would fix {total_violations} violation(s) in {files_with_violations} file(s)")
    else:
        print(f"Fixed {total_fixes} violation(s) in {files_with_violations} file(s)")

    if all_violations and args.verbose:
        print("\nViolation breakdown:")
        pattern_counts: dict[str, int] = {}
        for v in all_violations:
            desc = next((r.description for r in REPLACEMENTS if r.pattern == v.pattern), v.pattern)
            pattern_counts[desc] = pattern_counts.get(desc, 0) + 1
        for desc, count in sorted(pattern_counts.items(), key=lambda x: -x[1]):
            print(f"  {count:4d}  {desc}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
