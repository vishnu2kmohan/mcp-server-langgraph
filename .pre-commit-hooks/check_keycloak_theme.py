#!/usr/bin/env python3
"""
Pre-commit hook: Keycloak Theme Validator

Validates Keycloak theme files to prevent common issues:
- Invalid theme.properties syntax (meta property format)
- Missing required asset files (icons, logos, CSS)
- Duplicate CSS pseudo-element selectors

This hook prevents regressions like:
- FreeMarker template errors from invalid meta=favicon
- Multiple icons appearing due to duplicate ::before selectors
- Missing assets causing 404 errors

Usage:
    As a pre-commit hook (see .pre-commit-config.yaml)
    Or standalone: python .pre-commit-hooks/check_keycloak_theme.py

Exit codes:
    0: All validations passed
    1: Found validation errors
"""

import re
import sys
from collections import Counter
from pathlib import Path

# Theme root directory
THEME_ROOT = Path("docker/keycloak/themes")

# Required files for each theme type
REQUIRED_FILES = {
    "login": [
        "theme.properties",
        "resources/css/login.css",
        "resources/img/icon.svg",
    ],
}


class ThemeValidationError:
    """Represents a theme validation error"""

    def __init__(self, file_path: Path, line_no: int, message: str, fix: str):
        self.file_path = file_path
        self.line_no = line_no
        self.message = message
        self.fix = fix

    def __str__(self) -> str:
        location = f"{self.file_path}"
        if self.line_no > 0:
            location += f":{self.line_no}"
        return f"{location}: {self.message}\n    Fix: {self.fix}"


def validate_theme_properties(theme_path: Path) -> list[ThemeValidationError]:
    """
    Validate theme.properties file syntax

    Checks:
    - meta property uses correct format: meta=name==content
    - No bare meta=value (causes FreeMarker errors)
    """
    errors = []
    props_file = theme_path / "theme.properties"

    if not props_file.exists():
        return errors

    content = props_file.read_text(encoding="utf-8")

    for line_no, line in enumerate(content.splitlines(), 1):
        # Skip comments and empty lines
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # Check for invalid meta property format
        # Valid: meta=viewport==width=device-width
        # Invalid: meta=favicon (no == separator)
        if stripped.startswith("meta="):
            value = stripped[5:]  # After "meta="
            if "==" not in value:
                errors.append(
                    ThemeValidationError(
                        file_path=props_file,
                        line_no=line_no,
                        message=f"Invalid meta property format: '{stripped}'",
                        fix="Use format 'meta=name==content' or use specific property (favicon=path)",
                    )
                )

    return errors


def validate_css_pseudo_elements(theme_path: Path) -> list[ThemeValidationError]:
    """
    Validate CSS files don't have duplicate pseudo-element selectors

    Checks for multiple definitions of the same ::before or ::after selector
    that could cause duplicate icons or other visual issues.
    """
    errors = []
    css_dir = theme_path / "resources" / "css"

    if not css_dir.exists():
        return errors

    for css_file in css_dir.glob("*.css"):
        content = css_file.read_text(encoding="utf-8")

        # Find all pseudo-element selectors
        # Pattern: selector::before or selector::after
        # Captures selector INCLUDING ::before/::after to distinguish them
        pseudo_pattern = re.compile(r"([^\s{,]+::(before|after))\s*\{", re.MULTILINE)
        matches = [m[0] for m in pseudo_pattern.findall(content)]

        # Count occurrences
        counts = Counter(matches)

        for selector, count in counts.items():
            if count > 1:
                # Find line numbers for all occurrences
                pattern = re.compile(re.escape(selector))
                line_numbers = []
                for line_no, line in enumerate(content.splitlines(), 1):
                    if pattern.search(line):
                        line_numbers.append(str(line_no))

                errors.append(
                    ThemeValidationError(
                        file_path=css_file,
                        line_no=int(line_numbers[0]) if line_numbers else 0,
                        message=f"Duplicate pseudo-element '{selector}' defined {count} times (lines: {', '.join(line_numbers)})",
                        fix="Consolidate into a single selector definition",
                    )
                )

    return errors


def validate_required_files(theme_path: Path, theme_type: str) -> list[ThemeValidationError]:
    """
    Validate that all required theme files exist

    Args:
        theme_path: Path to the theme directory
        theme_type: Type of theme (login, account, etc.)
    """
    errors = []

    if theme_type not in REQUIRED_FILES:
        return errors

    for required_file in REQUIRED_FILES[theme_type]:
        file_path = theme_path / required_file
        if not file_path.exists():
            errors.append(
                ThemeValidationError(
                    file_path=file_path,
                    line_no=0,
                    message=f"Required file missing: {required_file}",
                    fix=f"Create the file: {file_path}",
                )
            )

    return errors


def validate_theme(theme_name: str, theme_type: str) -> list[ThemeValidationError]:
    """
    Validate a complete Keycloak theme

    Args:
        theme_name: Name of the theme (e.g., "agent-studio")
        theme_type: Type of theme page (e.g., "login")

    Returns:
        List of validation errors
    """
    theme_path = THEME_ROOT / theme_name / theme_type

    if not theme_path.exists():
        return []

    errors = []
    errors.extend(validate_theme_properties(theme_path))
    errors.extend(validate_css_pseudo_elements(theme_path))
    errors.extend(validate_required_files(theme_path, theme_type))

    return errors


def main(argv: list[str] = None) -> int:
    """
    Main entry point for pre-commit hook

    Args:
        argv: Command line arguments (ignored - validates all themes)

    Returns:
        0 if all checks pass, 1 if violations found
    """
    all_errors: list[ThemeValidationError] = []

    # Find all themes
    if not THEME_ROOT.exists():
        # No themes directory - nothing to validate
        return 0

    for theme_dir in THEME_ROOT.iterdir():
        if not theme_dir.is_dir():
            continue

        theme_name = theme_dir.name

        # Validate each theme type (login, account, etc.)
        for theme_type_dir in theme_dir.iterdir():
            if not theme_type_dir.is_dir():
                continue

            theme_type = theme_type_dir.name
            errors = validate_theme(theme_name, theme_type)
            all_errors.extend(errors)

    if all_errors:
        print("\n❌ Keycloak Theme Validation Errors:\n", file=sys.stderr)
        for i, error in enumerate(all_errors, 1):
            print(f"{i}. {error}\n", file=sys.stderr)

        print(
            f"\nFound {len(all_errors)} theme validation error(s). Please fix before committing.\n",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
