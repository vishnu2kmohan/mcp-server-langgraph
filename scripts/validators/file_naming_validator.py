#!/usr/bin/env python3
"""
File Naming Convention Validator for Documentation.

Enforces lowercase kebab-case naming for all .mdx files in docs/ directory.
Prevents UPPERCASE, snake_case, and camelCase filenames.

Usage:
    python scripts/validators/file_naming_validator.py
    python scripts/validators/file_naming_validator.py --path docs/
    python scripts/validators/file_naming_validator.py --check-file docs/my-file.mdx
"""

import argparse
import re
import sys
from pathlib import Path

# Conventional files that are allowed to have UPPERCASE names
CONVENTIONAL_FILES = {
    "README.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "LICENSE.md",
    "CODE_OF_CONDUCT.md",
    "SECURITY.md",
    "TESTING.md",
    "ROADMAP.md",
    "MIGRATION.md",
}


def is_conventional_file(file_path: Path) -> bool:
    """
    Check if file is a conventional file (allowed to be UPPERCASE).

    Args:
        file_path: Path to the file

    Returns:
        True if file is conventional (README.md, LICENSE, etc.)
    """
    return file_path.name in CONVENTIONAL_FILES


def is_kebab_case(filename: str) -> bool:
    """
    Check if filename follows kebab-case convention.

    Valid kebab-case:
    - All lowercase
    - Hyphens allowed (but not at start/end)
    - Numbers allowed
    - File extension allowed

    Invalid:
    - UPPERCASE or MixedCase
    - Underscores (_)
    - Spaces
    - Leading or trailing hyphens

    Args:
        filename: The filename to check (including extension)

    Returns:
        True if filename is valid kebab-case
    """
    # Remove extension for checking
    stem = Path(filename).stem

    # Empty filename is invalid
    if not stem:
        return False

    # Hidden files (starting with .) are allowed
    if stem.startswith("."):
        return True

    # Check for leading or trailing hyphens
    if stem.startswith("-") or stem.endswith("-"):
        return False

    # Kebab-case pattern: lowercase letters, numbers, and hyphens
    # No underscores, no uppercase, no spaces
    pattern = r"^[a-z0-9]+(-[a-z0-9]+)*$"

    return bool(re.match(pattern, stem))


def to_kebab_case(filename: str) -> str:
    """
    Convert filename to kebab-case suggestion.

    Args:
        filename: Original filename

    Returns:
        Suggested kebab-case filename
    """
    stem = Path(filename).stem
    extension = Path(filename).suffix

    # Replace underscores with hyphens
    suggested = stem.replace("_", "-")

    # Convert to lowercase
    suggested = suggested.lower()

    # Replace multiple hyphens with single hyphen
    suggested = re.sub(r"-+", "-", suggested)

    # Remove leading/trailing hyphens
    suggested = suggested.strip("-")

    return f"{suggested}{extension}"


def validate_filename_convention(file_path: Path) -> list[str]:
    """
    Validate that filename follows kebab-case convention.

    Rules:
    1. All .mdx files in docs/ must be lowercase kebab-case
    2. No .md files allowed in docs/ (must use .mdx)
    3. Conventional files (README.md, LICENSE, etc.) are exempt
    4. Files outside docs/ are not validated

    Args:
        file_path: Path to the file to validate

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    # Skip conventional files
    if is_conventional_file(file_path):
        return errors

    # Only validate files in docs/ directory
    if "docs/" not in str(file_path) or "/docs/" not in str(file_path):
        # Also check if path starts with docs/
        if not str(file_path).startswith("docs/"):
            return errors

    filename = file_path.name
    extension = file_path.suffix

    # Rule: No .md files in docs/ directory (must use .mdx)
    if extension == ".md":
        errors.append(
            f"{file_path}: .md files not allowed in docs/ directory. "
            f"Convert to .mdx format. See: docs/references/documentation-authoring-guide"
        )
        return errors

    # Skip non-.mdx files (allow other file types like images, etc.)
    if extension != ".mdx":
        return errors

    # Check if filename is kebab-case
    if not is_kebab_case(filename):
        suggested = to_kebab_case(filename)
        errors.append(f"{file_path}: Filename should be lowercase kebab-case. " f"Suggested: {suggested}")

        # Provide specific guidance
        stem = Path(filename).stem

        if "_" in stem:
            errors.append(f"{file_path}: Use hyphens (-) not underscores (_) in filenames")

        if any(c.isupper() for c in stem):
            errors.append(f"{file_path}: Filename should be all lowercase")

        if " " in stem:
            errors.append(f"{file_path}: Filename should not contain spaces")

    return errors


def find_invalid_filenames(
    directory: Path,
    pattern: str = "**/*.mdx",
    exclude_patterns: list[str] = None,
) -> list[tuple[Path, list[str]]]:
    """
    Find all files with invalid naming conventions in directory.

    Args:
        directory: Directory to search
        pattern: Glob pattern for files to check
        exclude_patterns: List of patterns to exclude

    Returns:
        List of tuples: (file_path, list_of_errors)
    """
    if exclude_patterns is None:
        exclude_patterns = [
            "**/node_modules/**",
            "**/.venv/**",
            "**/__pycache__/**",
            "**/.*/**",  # Hidden directories
        ]

    invalid_files = []

    for file_path in directory.glob(pattern):
        # Skip excluded patterns
        if any(file_path.match(exclude) for exclude in exclude_patterns):
            continue

        errors = validate_filename_convention(file_path)
        if errors:
            invalid_files.append((file_path, errors))

    return invalid_files


def main():
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(description="Validate file naming conventions for documentation")
    parser.add_argument(
        "--path",
        type=Path,
        default=Path("docs"),
        help="Directory to validate (default: docs/)",
    )
    parser.add_argument(
        "--check-file",
        type=Path,
        help="Check a single file instead of entire directory",
    )
    parser.add_argument(
        "--pattern",
        default="**/*.mdx",
        help="Glob pattern for files to check (default: **/*.mdx)",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Suggest fixes (dry-run, doesn't rename files)",
    )

    args = parser.parse_args()

    # Single file check
    if args.check_file:
        errors = validate_filename_convention(args.check_file)
        if errors:
            print(f"❌ {args.check_file}:")
            for error in errors:
                print(f"   {error}")
            return 1
        else:
            print(f"✅ {args.check_file}: Valid")
            return 0

    # Directory check
    if not args.path.exists():
        print(f"❌ Error: Directory {args.path} does not exist")
        return 1

    print(f"🔍 Validating file naming conventions in {args.path}/")
    print(f"   Pattern: {args.pattern}")
    print()

    invalid_files = find_invalid_filenames(args.path, args.pattern)

    if not invalid_files:
        print("✅ All files follow kebab-case naming convention!")
        return 0

    print(f"❌ Found {len(invalid_files)} files with invalid naming:\n")

    for file_path, errors in invalid_files:
        print(f"❌ {file_path}:")
        for error in errors:
            print(f"   {error}")
        print()

    if args.fix:
        print("\n💡 Suggested fixes:")
        for file_path, _ in invalid_files:
            suggested = to_kebab_case(file_path.name)
            if suggested != file_path.name:
                new_path = file_path.parent / suggested
                print(f"   git mv {file_path} {new_path}")

    print("\n📋 Summary:")
    print(f"   Total files checked: {len(list(args.path.glob(args.pattern)))}")
    print(f"   Invalid files: {len(invalid_files)}")
    print("\n💡 Tip: Run with --fix to see suggested git mv commands")
    print("\n📚 See: docs/references/documentation-authoring-guide")

    return 1


if __name__ == "__main__":
    sys.exit(main())
