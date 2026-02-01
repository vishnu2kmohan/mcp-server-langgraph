#!/usr/bin/env python3
"""
Comprehensive Design System Violation Fixer

Fixes all categories of design system violations:
1. Color: Legacy neutral-XXX → Radix 1-12 scale
2. Z-index: Non-token values → token values
3. Spacing: Arbitrary spacing → design tokens (p-[20px] → p-5)
4. Animation: Arbitrary durations → design tokens (duration-[200ms] → duration-200)
5. Typography: Arbitrary font sizes → design tokens (text-[14px] → text-sm)
6. Border Radius: Arbitrary radius → design tokens (rounded-[8px] → rounded-lg)
7. Shadow: Arbitrary shadows → design tokens (shadow-[...] → shadow-md)
8. Opacity: Arbitrary opacity → design tokens (opacity-[0.5] → opacity-50)

Usage:
  python scripts/fix-design-system-violations.py [--dry-run] [--category=color]

Categories: color, zindex, spacing, animation, typography, border, shadow, opacity, all (default: all)

Examples:
  python scripts/fix-design-system-violations.py --dry-run
  python scripts/fix-design-system-violations.py --category=spacing
  python scripts/fix-design-system-violations.py --category=color --dry-run
"""

import re
import sys
from pathlib import Path

DRY_RUN = "--dry-run" in sys.argv
CATEGORY = next((a.split("=")[1] for a in sys.argv if a.startswith("--category=")), "all")

# =============================================================================
# COLOR: Legacy Neutral → Radix 1-12 Mappings
# =============================================================================

# Radix semantic steps:
#   1-2: App backgrounds
#   3-5: Interactive backgrounds (hover: 4, active: 5)
#   6-8: Borders and separators
#   9-10: Solid backgrounds (buttons, badges)
#   11-12: Text (secondary: 11, primary: 12)

NEUTRAL_MAP = {
    "50": "1",
    "100": "2",
    "200": "3",
    "300": "5",
    "400": "9",
    "500": "10",
    "600": "11",
    "700": "11",
    "800": "12",
    "900": "12",
    "950": "12",
}


def build_color_replacements() -> list[tuple[re.Pattern[str], str]]:
    """Build comprehensive color replacement patterns."""
    replacements = []

    prefixes = [
        "text",
        "bg",
        "border",
        "ring",
        "divide",
        "outline",
        "from",
        "to",
        "via",  # Gradients
        "stroke",
        "fill",  # SVG
        "placeholder",
        "decoration",
        "border-t",
        "border-b",
        "border-l",
        "border-r",  # Directional borders
        "border-x",
        "border-y",
    ]

    # State prefixes (can be combined)
    states = ["", "hover:", "focus:", "active:", "disabled:", "dark:", "dark:hover:", "dark:focus:"]

    for state in states:
        for prefix in prefixes:
            for old, new in NEUTRAL_MAP.items():
                pattern = re.compile(rf"\b{state}{prefix}-neutral-{old}\b")
                replacements.append((pattern, f"{state}{prefix}-neutral-{new}"))

    # Focus ring offset
    for old, new in NEUTRAL_MAP.items():
        pattern = re.compile(rf"\bfocus:ring-offset-neutral-{old}\b")
        replacements.append((pattern, f"focus:ring-offset-neutral-{new}"))
        pattern = re.compile(rf"\bdark:focus:ring-offset-neutral-{old}\b")
        replacements.append((pattern, f"dark:focus:ring-offset-neutral-{new}"))

    # Placeholder with text- prefix
    for old, new in NEUTRAL_MAP.items():
        pattern = re.compile(rf"\bplaceholder:text-neutral-{old}\b")
        replacements.append((pattern, f"placeholder:text-neutral-{new}"))

    return replacements


COLOR_REPLACEMENTS = build_color_replacements()

# =============================================================================
# Z-INDEX: Non-token → Token Mappings
# =============================================================================
# Token values: 0, 10, 50, 55, 60, 65, 70, 75

ZINDEX_MAP = {
    "20": "10",
    "30": "50",
    "40": "50",
    "100": "75",
    "999": "75",
    "1000": "75",
}


def build_zindex_replacements() -> list[tuple[re.Pattern[str], str]]:
    """Build z-index replacement patterns."""
    replacements = []
    for old, new in ZINDEX_MAP.items():
        pattern = re.compile(rf"\bz-{old}\b")
        replacements.append((pattern, f"z-{new}"))
    return replacements


ZINDEX_REPLACEMENTS = build_zindex_replacements()

# =============================================================================
# SPACING: Arbitrary spacing → Design Tokens
# =============================================================================
# Tailwind spacing scale: 1=4px, 2=8px, 3=12px, 4=16px, 5=20px, 6=24px, etc.

SPACING_MAP = {
    # px to token (divide by 4)
    "4px": "1",
    "8px": "2",
    "12px": "3",
    "16px": "4",
    "20px": "5",
    "24px": "6",
    "28px": "7",
    "32px": "8",
    "36px": "9",
    "40px": "10",
    "44px": "11",
    "48px": "12",
    "56px": "14",
    "64px": "16",
    "80px": "20",
    "96px": "24",
    "112px": "28",
    "128px": "32",
    "144px": "36",
    "160px": "40",
    # rem to token (multiply by 4)
    "0.25rem": "1",
    "0.5rem": "2",
    "0.75rem": "3",
    "1rem": "4",
    "1.25rem": "5",
    "1.5rem": "6",
    "1.75rem": "7",
    "2rem": "8",
    "2.25rem": "9",
    "2.5rem": "10",
    "2.75rem": "11",
    "3rem": "12",
    "3.5rem": "14",
    "4rem": "16",
    "5rem": "20",
    "6rem": "24",
    "7rem": "28",
    "8rem": "32",
    "9rem": "36",
    "10rem": "40",
}


def build_spacing_replacements() -> list[tuple[re.Pattern[str], str]]:
    """Build spacing replacement patterns."""
    replacements = []
    prefixes = ["p", "px", "py", "pt", "pr", "pb", "pl", "m", "mx", "my", "mt", "mr", "mb", "ml", "gap", "gap-x", "gap-y"]

    for prefix in prefixes:
        for old, new in SPACING_MAP.items():
            pattern = re.compile(rf"\b{prefix}-\[{re.escape(old)}\]")
            replacements.append((pattern, f"{prefix}-{new}"))

    return replacements


SPACING_REPLACEMENTS = build_spacing_replacements()

# =============================================================================
# ANIMATION: Arbitrary durations → Design Tokens
# =============================================================================
# Tailwind duration scale: 75, 100, 150, 200, 300, 500, 700, 1000

ANIMATION_MAP = {
    # ms to token
    "75ms": "75",
    "100ms": "100",
    "150ms": "150",
    "200ms": "200",
    "300ms": "300",
    "500ms": "500",
    "700ms": "700",
    "1000ms": "1000",
    # s to token (convert to ms)
    "0.075s": "75",
    "0.1s": "100",
    "0.15s": "150",
    "0.2s": "200",
    "0.3s": "300",
    "0.5s": "500",
    "0.7s": "700",
    "1s": "1000",
}


def build_animation_replacements() -> list[tuple[re.Pattern[str], str]]:
    """Build animation duration replacement patterns."""
    replacements = []

    for old, new in ANIMATION_MAP.items():
        pattern = re.compile(rf"\bduration-\[{re.escape(old)}\]")
        replacements.append((pattern, f"duration-{new}"))

    return replacements


ANIMATION_REPLACEMENTS = build_animation_replacements()

# =============================================================================
# TYPOGRAPHY: Arbitrary font sizes → Design Tokens
# =============================================================================
# Tailwind font size scale:
#   xs=12px, sm=14px, base=16px, lg=18px, xl=20px
#   2xl=24px, 3xl=30px, 4xl=36px, 5xl=48px, 6xl=60px

TYPOGRAPHY_MAP = {
    # px to token (map to closest Tailwind size)
    "10px": "xs",
    "11px": "xs",
    "12px": "xs",
    "13px": "sm",
    "14px": "sm",
    "15px": "base",
    "16px": "base",
    "17px": "lg",
    "18px": "lg",
    "19px": "xl",
    "20px": "xl",
    "22px": "2xl",
    "24px": "2xl",
    "28px": "3xl",
    "30px": "3xl",
    "32px": "4xl",
    "36px": "4xl",
    "40px": "5xl",
    "48px": "5xl",
    "56px": "6xl",
    "60px": "6xl",
    # rem to token
    "0.625rem": "xs",
    "0.75rem": "xs",
    "0.875rem": "sm",
    "1rem": "base",
    "1.125rem": "lg",
    "1.25rem": "xl",
    "1.5rem": "2xl",
    "1.875rem": "3xl",
    "2.25rem": "4xl",
    "3rem": "5xl",
    "3.75rem": "6xl",
}


def build_typography_replacements() -> list[tuple[re.Pattern[str], str]]:
    """Build typography font-size replacement patterns."""
    replacements = []

    for old, new in TYPOGRAPHY_MAP.items():
        pattern = re.compile(rf"\btext-\[{re.escape(old)}\]")
        replacements.append((pattern, f"text-{new}"))

    return replacements


TYPOGRAPHY_REPLACEMENTS = build_typography_replacements()

# =============================================================================
# BORDER RADIUS: Arbitrary border-radius → Design Tokens
# =============================================================================
# Tailwind border-radius scale:
#   none=0, sm=2px, DEFAULT=4px, md=6px, lg=8px, xl=12px, 2xl=16px, 3xl=24px, full=9999px

BORDER_RADIUS_MAP = {
    # px to token
    "0px": "none",
    "1px": "sm",
    "2px": "sm",
    "3px": "DEFAULT",
    "4px": "DEFAULT",
    "5px": "md",
    "6px": "md",
    "7px": "lg",
    "8px": "lg",
    "10px": "xl",
    "12px": "xl",
    "14px": "2xl",
    "16px": "2xl",
    "20px": "3xl",
    "24px": "3xl",
    # rem to token
    "0.125rem": "sm",
    "0.25rem": "DEFAULT",
    "0.375rem": "md",
    "0.5rem": "lg",
    "0.75rem": "xl",
    "1rem": "2xl",
    "1.5rem": "3xl",
}


def build_border_radius_replacements() -> list[tuple[re.Pattern[str], str]]:
    """Build border-radius replacement patterns."""
    replacements = []
    prefixes = [
        "rounded",
        "rounded-t",
        "rounded-r",
        "rounded-b",
        "rounded-l",
        "rounded-tl",
        "rounded-tr",
        "rounded-br",
        "rounded-bl",
    ]

    for prefix in prefixes:
        for old, new in BORDER_RADIUS_MAP.items():
            pattern = re.compile(rf"\b{prefix}-\[{re.escape(old)}\]")
            if new == "DEFAULT":
                replacements.append((pattern, prefix))
            else:
                replacements.append((pattern, f"{prefix}-{new}"))

    return replacements


BORDER_RADIUS_REPLACEMENTS = build_border_radius_replacements()

# =============================================================================
# SHADOW: Arbitrary shadow → Design Tokens
# =============================================================================
# Token shadows: none, sm, DEFAULT, md, lg, xl, 2xl
# Custom tokens: soft, elevated, modal

# Note: Shadow auto-fix is complex due to the variety of shadow values.
# We provide common mappings for known patterns.
SHADOW_MAP = {
    # Common subtle shadow patterns → shadow-soft or shadow-sm
    "0_1px_2px_rgba(0,0,0,0.05)": "sm",
    "0_1px_3px_rgba(0,0,0,0.1)": "soft",
    "0_2px_4px_rgba(0,0,0,0.1)": "soft",
    # Medium shadows → shadow-md or shadow-elevated
    "0_4px_6px_rgba(0,0,0,0.1)": "md",
    "0_4px_8px_rgba(0,0,0,0.1)": "elevated",
    "0_4px_12px_rgba(0,0,0,0.15)": "elevated",
    # Large shadows → shadow-lg
    "0_10px_15px_rgba(0,0,0,0.1)": "lg",
    "0_8px_16px_rgba(0,0,0,0.15)": "lg",
    # Extra large → shadow-xl or shadow-modal
    "0_20px_25px_rgba(0,0,0,0.1)": "xl",
    "0_16px_48px_rgba(0,0,0,0.25)": "modal",
    "0_25px_50px_rgba(0,0,0,0.25)": "2xl",
    # None
    "none": "none",
}


def build_shadow_replacements() -> list[tuple[re.Pattern[str], str]]:
    """Build shadow replacement patterns."""
    replacements = []

    for old, new in SHADOW_MAP.items():
        # Replace underscores with spaces for the pattern (Tailwind uses underscores)
        pattern = re.compile(rf"\bshadow-\[{re.escape(old)}\]")
        replacements.append((pattern, f"shadow-{new}"))

    return replacements


SHADOW_REPLACEMENTS = build_shadow_replacements()

# =============================================================================
# OPACITY: Arbitrary opacity → Design Tokens
# =============================================================================
# Tailwind opacity scale: 0, 5, 10, 20, 25, 30, 40, 50, 60, 70, 75, 80, 90, 95, 100

OPACITY_MAP = {
    # Decimal to token (multiply by 100)
    "0": "0",
    "0.05": "5",
    "0.1": "10",
    "0.2": "20",
    "0.25": "25",
    "0.3": "30",
    "0.4": "40",
    "0.5": "50",
    "0.6": "60",
    "0.7": "70",
    "0.75": "75",
    "0.8": "80",
    "0.9": "90",
    "0.95": "95",
    "1": "100",
    # Short decimals
    ".05": "5",
    ".1": "10",
    ".2": "20",
    ".25": "25",
    ".3": "30",
    ".4": "40",
    ".5": "50",
    ".6": "60",
    ".7": "70",
    ".75": "75",
    ".8": "80",
    ".9": "90",
    ".95": "95",
}


def build_opacity_replacements() -> list[tuple[re.Pattern[str], str]]:
    """Build opacity replacement patterns."""
    replacements = []

    for old, new in OPACITY_MAP.items():
        # Match[str] opacity-[X]
        pattern = re.compile(rf"\bopacity-\[{re.escape(old)}\]")
        replacements.append((pattern, f"opacity-{new}"))
        # Match[str] color/[X] modifier
        pattern = re.compile(rf"/\[{re.escape(old)}\]")
        replacements.append((pattern, f"/{new}"))

    return replacements


OPACITY_REPLACEMENTS = build_opacity_replacements()

# =============================================================================
# FILE PROCESSING
# =============================================================================


def process_file(filepath: Path, replacements: list[tuple[re.Pattern[str], str]], category: str) -> tuple[int, list[str]]:
    """Process a single file with given replacements."""
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception as e:
        return 0, [f"Error reading {filepath}: {e}"]

    original = content
    changes = []
    total_count = 0

    for pattern, replacement in replacements:
        matches = pattern.findall(content)
        if matches:
            count = len(matches)
            total_count += count
            content = pattern.sub(replacement, content)
            changes.append(f"  {pattern.pattern} → {replacement} ({count}x)")

    if content != original:
        if not DRY_RUN:
            filepath.write_text(content, encoding="utf-8")
        return total_count, changes

    return 0, []


def get_files(extensions: list[str]) -> list[Path]:
    """Get all source files with given extensions, excluding tests/stories."""
    src_dir = Path("src")
    if not src_dir.exists():
        return []

    files = []
    for ext in extensions:
        files.extend(
            [
                f
                for f in src_dir.rglob(f"*.{ext}")
                if "node_modules" not in str(f) and ".test." not in f.name and ".stories." not in f.name
            ]
        )
    return sorted(set(files))


def run_fixes(category: str, replacements: list[tuple[re.Pattern[str], str]], extensions: list[str]) -> int:
    """Run fixes for a category."""
    files = get_files(extensions)

    print(f"\n{'=' * 60}")
    print(f"  {category.upper()} FIXES")
    print(f"{'=' * 60}")
    print(f"Files to scan: {len(files)}")

    total_replacements = 0
    modified_files = 0

    for filepath in files:
        count, changes = process_file(filepath, replacements, category)
        if count > 0:
            modified_files += 1
            total_replacements += count
            print(f"\n{filepath}: {count} replacements")
            for change in changes[:5]:  # Show first 5 changes
                print(change)
            if len(changes) > 5:
                print(f"  ... and {len(changes) - 5} more")

    print(f"\n{'-' * 40}")
    print(f"  Files modified: {modified_files}")
    print(f"  Total replacements: {total_replacements}")

    return total_replacements


# =============================================================================
# MAIN
# =============================================================================


def main() -> None:
    print("=" * 60)
    print("  Design System Violation Fixer")
    if DRY_RUN:
        print("  DRY RUN - No files will be modified")
    print("=" * 60)

    total = 0

    if CATEGORY in ("color", "all"):
        total += run_fixes("color", COLOR_REPLACEMENTS, ["tsx", "ts", "css"])

    if CATEGORY in ("zindex", "all"):
        total += run_fixes("z-index", ZINDEX_REPLACEMENTS, ["tsx", "ts", "css"])

    if CATEGORY in ("spacing", "all"):
        total += run_fixes("spacing", SPACING_REPLACEMENTS, ["tsx", "ts", "css"])

    if CATEGORY in ("animation", "all"):
        total += run_fixes("animation", ANIMATION_REPLACEMENTS, ["tsx", "ts", "css"])

    if CATEGORY in ("typography", "all"):
        total += run_fixes("typography", TYPOGRAPHY_REPLACEMENTS, ["tsx", "ts", "css"])

    if CATEGORY in ("border", "all"):
        total += run_fixes("border-radius", BORDER_RADIUS_REPLACEMENTS, ["tsx", "ts", "css"])

    if CATEGORY in ("shadow", "all"):
        total += run_fixes("shadow", SHADOW_REPLACEMENTS, ["tsx", "ts", "css"])

    if CATEGORY in ("opacity", "all"):
        total += run_fixes("opacity", OPACITY_REPLACEMENTS, ["tsx", "ts", "css"])

    print(f"\n{'=' * 60}")
    print(f"  COMPLETE - Total: {total} replacements")
    if DRY_RUN:
        print("  Run without --dry-run to apply changes")
    print("=" * 60)

    if total > 0:
        print("\nNext steps:")
        print("1. npm run lint")
        print("2. npm run audit:design-system")
        print("3. npm run build")


if __name__ == "__main__":
    main()
