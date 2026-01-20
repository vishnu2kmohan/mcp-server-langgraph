#!/usr/bin/env python3
"""
Fix Button component variant violations.

This script scans for Button components with semantic text (Cancel, Delete, etc.)
and adds the appropriate variant prop if missing.

Usage:
    python scripts/fix-button-variants.py --dry-run   # Preview changes
    python scripts/fix-button-variants.py             # Apply changes
    python scripts/fix-button-variants.py --verbose   # Show all matches

Semantic Text → Variant Mapping:
    Cancel, Close, Back, Dismiss, No → variant="secondary"
    Delete, Remove, Clear, Destroy, Discard → variant="danger"
    Confirm, Approve, Accept, Save, Submit → variant="primary" (explicit)
    OK, Yes → variant="primary" (explicit)

Exit Codes:
    0: Success
    1: Errors occurred
"""

import argparse
import re
from typing import Any, Pattern, Match
import sys
from collections import defaultdict
from pathlib import Path

# =============================================================================
# Configuration
# =============================================================================

FRONTEND_SRC = Path(__file__).parent.parent / "src"

EXTENSIONS = {".tsx"}

SKIP_DIRS = {"node_modules", "dist", ".storybook", "coverage", "__snapshots__"}

SKIP_FILES = {
    "Button.tsx",
    "Button.test.tsx",
    "Button.stories.tsx",
}

# Semantic text to variant mapping
BUTTON_TEXT_TO_VARIANT: dict[str, str] = {
    # Secondary variants (Cancel/Close actions)
    "Cancel": "secondary",
    "Close": "secondary",
    "Back": "secondary",
    "Dismiss": "secondary",
    "No": "secondary",
    "Never mind": "secondary",
    "Not now": "secondary",
    # Danger variants (Destructive actions)
    "Delete": "danger",
    "Remove": "danger",
    "Clear": "danger",
    "Destroy": "danger",
    "Discard": "danger",
    "Reset": "danger",
    # Explicit primary variants (Confirmations)
    "Confirm": "primary",
    "Approve": "primary",
    "Accept": "primary",
    "Save": "primary",
    "Submit": "primary",
    "OK": "primary",
    "Yes": "primary",
    "Continue": "primary",
    "Proceed": "primary",
}


# =============================================================================
# Pattern[str] Matching
# =============================================================================

def should_skip(path: Path) -> bool:
    """Check if path should be skipped."""
    if any(skip in path.parts for skip in SKIP_DIRS):
        return True
    if path.name in SKIP_FILES:
        return True
    # Skip test and story files
    if ".test." in path.name or ".stories." in path.name:
        return True
    return False


def fix_button_variants(content: str, dry_run: bool = False) -> tuple[str, dict[str, int]]:
    """
    Fix Button components with semantic text to use appropriate variants.

    Returns:
        Tuple of (modified_content, fixes_dict)
    """
    fixes: dict[str, int] = defaultdict(int)
    original = content

    for text, variant in BUTTON_TEXT_TO_VARIANT.items():
        # Pattern[str]: <Button (without variant=) ... >Text</Button>
        # Captures: $1 = opening tag content, $2 = text
        pattern = re.compile(
            rf'(<Button\b)(?![^>]*\bvariant=)([^>]*>)\s*{re.escape(text)}\s*(</Button>)',
            re.IGNORECASE
        )

        def replacer(match: re.Match[str]) -> str:
            fixes[f"{text} → {variant}"] += 1
            return f'{match.group(1)} variant="{variant}"{match.group(2)}{text}{match.group(3)}'

        content = pattern.sub(replacer, content)

    return content, dict(fixes)


def fix_classname_color_overrides(content: str, dry_run: bool = False) -> tuple[str, dict[str, int]]:
    """
    Fix Button components with className color overrides to use variant prop.

    Examples:
        <Button className="bg-warning-9 ..."> → <Button variant="warning" className="...">
        <Button className="bg-error-9 ..."> → <Button variant="danger" className="...">

    Returns:
        Tuple of (modified_content, fixes_dict)
    """
    fixes: dict[str, int] = defaultdict(int)

    # Map color prefixes to variants
    color_to_variant = {
        "warning": "warning",
        "error": "danger",
        "success": "success",
        "primary": "primary",
    }

    for color, variant in color_to_variant.items():
        # Pattern[str]: <Button ... className="...bg-{color}-N..." ...>
        # Remove the bg-{color}-N class and add variant prop
        pattern = re.compile(
            rf'(<Button\b)(?![^>]*\bvariant=)([^>]*className=["\'])([^"\']*)\bbg-{color}-\d+([^"\']*["\'][^>]*>)',
        )

        def make_replacer(var: str, col: str):
            def replacer(match: re.Match[str]) -> str:
                fixes[f"bg-{col}-* → variant=\"{var}\""] += 1
                # Preserve other classes, remove the bg-color class
                other_classes = match.group(3) + match.group(4).rstrip('"\'>')
                # Clean up the className
                other_classes = re.sub(rf'\s*bg-{col}-\d+\s*', ' ', other_classes).strip()
                if other_classes:
                    return f'{match.group(1)} variant="{var}" className="{other_classes}">'
                else:
                    return f'{match.group(1)} variant="{var}">'
            return replacer

        content = pattern.sub(make_replacer(variant, color), content)

    return content, dict(fixes)


def process_file(file_path: Path, dry_run: bool = False, verbose: bool = False) -> dict:
    """Process a single file and apply fixes."""
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        return {"error": str(e)}

    original = content
    all_fixes: dict[str, int] = defaultdict(int)

    # Apply button variant fixes
    content, variant_fixes = fix_button_variants(content, dry_run)
    for key, count in variant_fixes.items():
        all_fixes[key] += count

    # Apply className color override fixes
    content, color_fixes = fix_classname_color_overrides(content, dry_run)
    for key, count in color_fixes.items():
        all_fixes[key] += count

    if content != original:
        if not dry_run:
            file_path.write_text(content, encoding="utf-8")
        return {"modified": True, "fixes": dict(all_fixes)}

    return {"modified": False}


# =============================================================================
# Main Entry Point
# =============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fix Button component variant violations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview without modifying files")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show all matches")
    parser.add_argument("files", nargs="*", help="Specific files to fix (default: all TSX files)")

    args = parser.parse_args()

    # Collect files
    if args.files:
        files = [Path(f) for f in args.files if Path(f).suffix in EXTENSIONS]
    else:
        files = list(FRONTEND_SRC.rglob("*.tsx"))

    files = [f for f in files if f.exists() and not should_skip(f)]

    total_fixes: dict[str, int] = defaultdict(int)
    files_modified = 0

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Button Variant Fix")
    print("=" * 60)
    print(f"Scanning {len(files)} files...\n")

    for file_path in files:
        result = process_file(file_path, dry_run=args.dry_run, verbose=args.verbose)

        if result.get("error"):
            print(f"  Error: {file_path.name}: {result['error']}", file=sys.stderr)
            continue

        if result.get("modified"):
            files_modified += 1
            rel_path = file_path.relative_to(FRONTEND_SRC)
            action = "Would fix" if args.dry_run else "Fixed"
            print(f"  {action}: {rel_path}")
            for fix_type, count in result.get("fixes", {}).items():
                total_fixes[fix_type] += count
                if args.verbose:
                    print(f"    - {fix_type}: {count}")

    # Summary
    print("\n" + "-" * 60)
    print("Summary:")
    print(f"  Files modified: {files_modified}")
    print(f"  Total fixes: {sum(total_fixes.values())}")

    if total_fixes:
        print("\n  By type:")
        for fix_type, count in sorted(total_fixes.items(), key=lambda x: -x[1]):
            print(f"    {fix_type}: {count}")

    if args.dry_run and files_modified > 0:
        print(f"\nRun without --dry-run to apply changes.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
