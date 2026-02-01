#!/usr/bin/env python3
"""
Fix hard-coded colors in frontend codebase.

Maps hex colors to Radix color token equivalents and applies fixes.
Designed for one-time migration, preserving code structure.

Usage:
    python scripts/fix-hardcoded-colors.py --dry-run  # Preview changes
    python scripts/fix-hardcoded-colors.py            # Apply changes
"""

import re
import sys
from pathlib import Path
from typing import NamedTuple


class ColorMapping(NamedTuple):
    """Mapping from hex color to Radix token."""

    hex_color: str
    css_var: str  # CSS custom property e.g., var(--neutral-9)
    tailwind: str  # Tailwind class equivalent e.g., neutral-9
    description: str


# Hex to Radix token mappings based on Tailwind config
# Using the exact hex values from the design system
HEX_TO_RADIX: list[ColorMapping] = [
    # Neutral scale (gray tones)
    ColorMapping("#ffffff", "var(--neutral-1)", "neutral-1", "white/background"),
    ColorMapping("#f5f5f5", "var(--neutral-2)", "neutral-2", "subtle background"),
    ColorMapping("#f3f4f6", "var(--neutral-2)", "neutral-2", "subtle background"),
    ColorMapping("#e5e7eb", "var(--neutral-5)", "neutral-5", "border/separator"),
    ColorMapping("#e2e8f0", "var(--neutral-5)", "neutral-5", "border/separator"),
    ColorMapping("#d1d5db", "var(--neutral-6)", "neutral-6", "subtle border"),
    ColorMapping("#9ca3af", "var(--neutral-9)", "neutral-9", "muted text"),
    ColorMapping("#6b7280", "var(--neutral-10)", "neutral-10", "secondary text"),
    ColorMapping("#4b5563", "var(--neutral-11)", "neutral-11", "text"),
    ColorMapping("#374151", "var(--neutral-6)", "neutral-6", "dark border"),
    ColorMapping("#1f2937", "var(--neutral-12)", "neutral-12", "dark background/text"),
    ColorMapping("#111827", "var(--neutral-12)", "neutral-12", "darkest"),
    ColorMapping("#000000", "var(--neutral-12)", "neutral-12", "black"),
    # Primary/Info scale (blue tones)
    ColorMapping("#3b82f6", "var(--info-9)", "info-9", "info/primary"),
    ColorMapping("#3B82F6", "var(--info-9)", "info-9", "info/primary"),
    ColorMapping("#6366f1", "var(--primary-9)", "primary-9", "primary accent"),
    ColorMapping("#2563eb", "var(--primary-10)", "primary-10", "primary dark"),
    # Warning scale (yellow/orange tones)
    ColorMapping("#f59e0b", "var(--warning-9)", "warning-9", "warning"),
    ColorMapping("#f97316", "var(--warning-10)", "warning-10", "warning dark"),
    # Error scale (red tones)
    ColorMapping("#ef4444", "var(--error-9)", "error-9", "error"),
    ColorMapping("#dc2626", "var(--error-10)", "error-10", "error dark"),
    # Success scale (green tones)
    ColorMapping("#10b981", "var(--success-9)", "success-9", "success"),
    ColorMapping("#059669", "var(--success-10)", "success-10", "success dark"),
    # Purple/Insight tones
    ColorMapping("#8b5cf6", "var(--insight-9)", "insight-9", "insight/AI"),
]

# Files to fix with their specific patterns
FILES_TO_FIX = [
    "src/components/Chat/InteractiveChart.tsx",
    "src/components/Artifacts/HTMLArtifact.tsx",
    "src/components/Trace/TraceCanvas.tsx",
    "src/components/ErrorRecovery/ErrorRecoveryPanel.tsx",
    "src/components/Artifacts/ArtifactExporter.tsx",
    "src/components/Artifacts/ChartArtifact.tsx",
    "src/components/Artifacts/InteractiveSVGArtifact.tsx",
    "src/components/Chat/InteractiveMermaidDiagram.tsx",
    "src/components/Workflow/WorkflowCanvas.tsx",
    "src/components/ErrorBoundary/AIErrorBoundary.tsx",
]


def find_hex_colors(content: str) -> list[tuple[str, int, int]]:
    """Find all hex color occurrences with their positions."""
    pattern = r'["\']#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})["\']'
    matches = []
    for match in re.finditer(pattern, content):
        hex_color = match.group(0).strip("\"'")
        matches.append((hex_color, match.start(), match.end()))
    return matches


def get_replacement(hex_color: str) -> str | None:
    """Get the CSS var replacement for a hex color."""
    hex_lower = hex_color.lower()
    for mapping in HEX_TO_RADIX:
        if mapping.hex_color.lower() == hex_lower:
            return mapping.css_var
    return None


def fix_file(file_path: Path, dry_run: bool = True) -> list[str]:
    """Fix hard-coded colors in a single file."""
    if not file_path.exists():
        return [f"  SKIP: {file_path} not found"]

    content = file_path.read_text()
    original_content = content
    changes: list[str] = []

    # Find and replace hex colors
    hex_matches = find_hex_colors(content)
    for hex_color, start, end in reversed(hex_matches):  # Reverse to preserve positions
        replacement = get_replacement(hex_color)
        if replacement:
            # Check context - is this in a style prop or inline?
            before = content[max(0, start - 50) : start]
            if "style=" in before or "Style" in before or "color:" in before.lower():
                # This is a style context, use CSS var
                old_text = content[start:end]
                # Replace the quoted hex with the CSS var (keeping appropriate quotes)
                quote_char = old_text[0]
                new_text = f"{quote_char}{replacement}{quote_char}"
                content = content[:start] + new_text + content[end:]
                changes.append(f"  Line ~{content[:start].count(chr(10)) + 1}: {old_text} -> {new_text}")

    if content != original_content:
        if not dry_run:
            file_path.write_text(content)
            changes.insert(0, f"FIXED: {file_path}")
        else:
            changes.insert(0, f"WOULD FIX: {file_path}")
    else:
        changes = [f"  NO CHANGES: {file_path}"]

    return changes


def main() -> int:
    """Main entry point."""
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv

    # Find frontend directory
    script_dir = Path(__file__).parent
    frontend_dir = script_dir.parent

    if not (frontend_dir / "package.json").exists():
        print("ERROR: Must run from frontend directory")
        return 1

    print(f"{'DRY RUN - ' if dry_run else ''}Fixing hard-coded colors...")
    print(f"Frontend directory: {frontend_dir}")
    print()

    total_changes = 0
    for relative_path in FILES_TO_FIX:
        file_path = frontend_dir / relative_path
        changes = fix_file(file_path, dry_run)
        for change in changes:
            print(change)
        if any("FIXED" in c or "WOULD FIX" in c for c in changes):
            total_changes += 1
        print()

    print(f"{'Would fix' if dry_run else 'Fixed'} {total_changes} files")
    if dry_run:
        print("\nRun without --dry-run to apply changes")

    return 0


if __name__ == "__main__":
    sys.exit(main())
