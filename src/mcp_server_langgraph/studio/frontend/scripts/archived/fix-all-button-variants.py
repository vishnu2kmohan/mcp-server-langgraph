#!/usr/bin/env python3
"""
Comprehensive Button variant fix script.

Adds explicit variant props to ALL buttons based on context:
1. Primary CTAs: Submit, Save, Create, Add, Apply, Confirm, etc.
2. Secondary actions: Cancel, Close, Back, Dismiss, etc.
3. Danger actions: Delete, Remove, Clear, Destroy, etc.
4. Ghost buttons: Toolbar buttons, icon-only buttons
5. Explicit primary for remaining ambiguous buttons

Usage:
    python scripts/fix-all-button-variants.py --dry-run   # Preview
    python scripts/fix-all-button-variants.py             # Apply
    python scripts/fix-all-button-variants.py --verbose   # Detailed output
"""

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

FRONTEND_SRC = Path(__file__).parent.parent / "src"
EXTENSIONS = {".tsx"}
SKIP_DIRS = {"node_modules", "dist", ".storybook", "coverage", "__snapshots__"}
SKIP_FILES = {"Button.tsx", "Button.test.tsx", "Button.stories.tsx"}

# =============================================================================
# Pattern[str] Definitions
# =============================================================================

# Text patterns that indicate specific variants
PRIMARY_TEXT = [
    "Submit",
    "Save",
    "Create",
    "Add",
    "Apply",
    "Confirm",
    "Continue",
    "Next",
    "Run",
    "Execute",
    "Start",
    "Enable",
    "Activate",
    "Connect",
    "Send",
    "Post",
    "Publish",
    "Deploy",
    "Install",
    "Update",
    "Upgrade",
    "Generate",
    "Build",
    "Compile",
    "Test",
    "Verify",
    "Validate",
    "OK",
    "Yes",
    "Accept",
    "Approve",
    "Grant",
    "Allow",
    "Proceed",
    "Go",
    "Login",
    "Sign in",
    "Sign up",
    "Register",
    "Join",
    "Subscribe",
    "Retry",
    "Try again",
    "Refresh",
    "Reload",
    "Sync",
    "Import",
    "Export",
]

SECONDARY_TEXT = [
    "Cancel",
    "Close",
    "Back",
    "Dismiss",
    "No",
    "Never mind",
    "Not now",
    "Skip",
    "Later",
    "Ignore",
    "Hide",
    "Collapse",
    "Minimize",
    "Maybe Later",
]

# Only truly destructive actions - NOT "Clear filters" etc.
DANGER_TEXT = [
    "Delete",
    "Remove",
    "Destroy",
    "Discard",
    "Revoke",
    "Terminate",
    "Kill",
    "Abort",
    "Reject",
    "Deny",
    "Uninstall",
    "Disconnect",
    "Logout",
    "Sign out",
    "Leave",
    "Exit",
]

# These look like "Clear" but are not destructive
CLEAR_EXCEPTIONS = ["Clear filter", "Clear filters", "Clear completed", "Clear search"]

SUCCESS_TEXT = [
    "Done",
    "Complete",
    "Finish",
    "Success",
]

WARNING_TEXT = [
    "Warning",
    "Caution",
    "Alert",
]


def should_skip(path: Path) -> bool:
    """Check if path should be skipped."""
    if any(skip in path.parts for skip in SKIP_DIRS):
        return True
    if path.name in SKIP_FILES:
        return True
    return bool(".test." in path.name or ".stories." in path.name)


def get_variant_for_text(text: str) -> str | None:
    """Determine variant based on button text."""
    text_lower = text.lower().strip()

    # Check clear exceptions first
    for exception in CLEAR_EXCEPTIONS:
        if exception.lower() in text_lower:
            return "secondary"  # Non-destructive clear actions

    for pattern in SECONDARY_TEXT:
        if pattern.lower() in text_lower:
            return "secondary"

    for pattern in DANGER_TEXT:
        if pattern.lower() in text_lower:
            return "danger"

    for pattern in SUCCESS_TEXT:
        if pattern.lower() in text_lower:
            return "success"

    for pattern in WARNING_TEXT:
        if pattern.lower() in text_lower:
            return "warning"

    for pattern in PRIMARY_TEXT:
        if pattern.lower() in text_lower:
            return "primary"

    return None


def fix_button_with_text(content: str) -> tuple[str, dict[str, int]]:
    """Fix buttons with identifiable text content."""
    fixes: dict[str, int] = defaultdict(int)

    # Pattern[str]: <Button ...>Text</Button> without variant
    # Matches single-word or multi-word button text
    pattern = re.compile(r"(<Button\b)(?![^>]*\bvariant=)([^>]*>)\s*([A-Z][a-zA-Z\s]*?)\s*(</Button>)", re.MULTILINE)

    def replacer(match: re.Match[str]) -> str:
        opening = match.group(1)
        attrs = match.group(2)
        text = match.group(3).strip()
        closing = match.group(4)

        variant = get_variant_for_text(text)
        if variant:
            fixes[f"{text} → {variant}"] += 1
            return f'{opening} variant="{variant}"{attrs}{text}{closing}'
        return match.group(0)

    content = pattern.sub(replacer, content)
    return content, dict(fixes)


def fix_icon_buttons(content: str) -> tuple[str, dict[str, int]]:
    """Add variant="ghost" to icon-only buttons without variant."""
    fixes: dict[str, int] = defaultdict(int)

    # Pattern[str]: <Button size="icon" ...> without variant
    pattern = re.compile(r'(<Button\b)(?![^>]*\bvariant=)([^>]*\bsize=["\']icon["\'][^>]*>)')

    def replacer(match: re.Match[str]) -> str:
        fixes["icon button → ghost"] += 1
        return f'{match.group(1)} variant="ghost"{match.group(2)}'

    content = pattern.sub(replacer, content)
    return content, dict(fixes)


def fix_toolbar_buttons(content: str) -> tuple[str, dict[str, int]]:
    """Add variant="ghost" to buttons in toolbar contexts."""
    fixes: dict[str, int] = defaultdict(int)

    # Pattern[str]: <Button size="sm" className="...p-1..." ...> (likely toolbar)
    # These are small buttons with minimal padding, typically in toolbars
    pattern = re.compile(
        r'(<Button\b)(?![^>]*\bvariant=)([^>]*\bsize=["\']sm["\'][^>]*className=["\'][^"\']*\bp-[01][.\d]*[^"\']*["\'][^>]*>)'
    )

    def replacer(match: re.Match[str]) -> str:
        fixes["toolbar button → ghost"] += 1
        return f'{match.group(1)} variant="ghost"{match.group(2)}'

    content = pattern.sub(replacer, content)
    return content, dict(fixes)


def fix_classname_overrides(content: str) -> tuple[str, dict[str, int]]:
    """Fix buttons with className color overrides."""
    fixes: dict[str, int] = defaultdict(int)

    color_to_variant = {
        "warning": "warning",
        "error": "danger",
        "success": "success",
        "primary": "primary",
        "info": "primary",
    }

    for color, variant in color_to_variant.items():
        # Pattern[str]: <Button className="...bg-{color}-N..." ...> without variant
        pattern = re.compile(
            rf'(<Button\b)(?![^>]*\bvariant=)([^>]*className=["\'])([^"\']*)\bbg-{color}-\d+([^"\']*["\'][^>]*>)',
        )

        def make_replacer(var: str, col: str):
            def replacer(match: re.Match[str]) -> str:
                fixes[f"bg-{col}-* → {var}"] += 1
                # Remove the bg-color class
                classes_before = match.group(3)
                classes_after = match.group(4).rstrip("\"'>").lstrip()
                all_classes = classes_before + classes_after
                # Clean up
                all_classes = re.sub(rf"\s*bg-{col}-\d+\s*", " ", all_classes).strip()
                if all_classes:
                    return f'{match.group(1)} variant="{var}" className="{all_classes}">'
                else:
                    return f'{match.group(1)} variant="{var}">'

            return replacer

        content = pattern.sub(make_replacer(variant, color), content)

    return content, dict(fixes)


def fix_remaining_buttons(content: str) -> tuple[str, dict[str, int]]:
    """Add explicit variant="primary" to remaining buttons without variant.

    Only applies to buttons that look like primary CTAs (capitalized text).
    """
    fixes: dict[str, int] = defaultdict(int)

    # Pattern[str]: <Button ...>CapitalizedText</Button> without variant
    # Only match if text starts with capital and looks like a CTA
    pattern = re.compile(
        r"(<Button\b)(?![^>]*\bvariant=)([^>]*>)\s*([A-Z][a-z]+(?:\s+[A-Za-z]+)*)\s*(</Button>)", re.MULTILINE
    )

    def replacer(match: re.Match[str]) -> str:
        text = match.group(3).strip()
        # Skip if text looks like a variable or complex expression
        if "{" in text or "}" in text or len(text) > 30:
            return match.group(0)
        fixes[f"'{text}' → primary (explicit)"] += 1
        return f'{match.group(1)} variant="primary"{match.group(2)}{text}{match.group(4)}'

    content = pattern.sub(replacer, content)
    return content, dict(fixes)


def process_file(file_path: Path, dry_run: bool = False) -> dict:
    """Process a single file and apply all fixes."""
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        return {"error": str(e)}

    original = content
    all_fixes: dict[str, int] = defaultdict(int)

    # Apply fixes in order of specificity
    for fix_func in [
        fix_button_with_text,
        fix_icon_buttons,
        fix_toolbar_buttons,
        fix_classname_overrides,
        # fix_remaining_buttons,  # Disabled - too aggressive
    ]:
        content, fixes = fix_func(content)
        for key, count in fixes.items():
            all_fixes[key] += count

    if content != original:
        if not dry_run:
            file_path.write_text(content, encoding="utf-8")
        return {"modified": True, "fixes": dict(all_fixes)}

    return {"modified": False}


def main() -> int:
    parser = argparse.ArgumentParser(description="Comprehensive Button variant fix")
    parser.add_argument("--dry-run", action="store_true", help="Preview without modifying")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show details")
    parser.add_argument("files", nargs="*", help="Specific files to fix")
    args = parser.parse_args()

    files = [Path(f) for f in args.files if Path(f).suffix in EXTENSIONS] if args.files else list(FRONTEND_SRC.rglob("*.tsx"))

    files = [f for f in files if f.exists() and not should_skip(f)]

    total_fixes: dict[str, int] = defaultdict(int)
    files_modified = 0

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Comprehensive Button Variant Fix")
    print("=" * 60)
    print(f"Scanning {len(files)} files...\n")

    for file_path in files:
        result = process_file(file_path, dry_run=args.dry_run)

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

    print("\n" + "-" * 60)
    print("Summary:")
    print(f"  Files modified: {files_modified}")
    print(f"  Total fixes: {sum(total_fixes.values())}")

    if total_fixes:
        print("\n  By type:")
        for fix_type, count in sorted(total_fixes.items(), key=lambda x: -x[1]):
            print(f"    {fix_type}: {count}")

    if args.dry_run and files_modified > 0:
        print("\nRun without --dry-run to apply changes.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
