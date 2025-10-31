#!/usr/bin/env python3
"""
Rename SCREAMING_SNAKE_CASE markdown files to kebab-case.

Preserves git history by using git mv.
"""

import subprocess
from pathlib import Path
from typing import List, Tuple

# Files that should keep SCREAMING_SNAKE_CASE (conventional names)
KEEP_AS_IS = {
    "README.md",
    "LICENSE",
    "LICENSE.md",
    "CHANGELOG.md",
    "SECURITY.md",
    "CODE_OF_CONDUCT.md",
    "CONTRIBUTING.md",
    "CODEOWNERS",
    "PULL_REQUEST_TEMPLATE.md",
    "REPOSITORY_STRUCTURE.md",  # Documented in ROOT_DIRECTORY_POLICY
    "FUNDING.yaml",
}


def to_kebab_case(name: str) -> str:
    """Convert SCREAMING_SNAKE_CASE to kebab-case."""
    return name.replace("_", "-").lower()


def find_screaming_snake_files(directories: List[Path]) -> List[Path]:
    """Find all SCREAMING_SNAKE_CASE markdown files."""
    files = []
    for directory in directories:
        if not directory.exists():
            continue
        for file_path in directory.rglob("*.md"):
            filename = file_path.name
            # Check if it's SCREAMING_SNAKE_CASE (has uppercase and underscores)
            if ("_" in filename or filename.isupper()) and filename not in KEEP_AS_IS:
                # Skip if it's already in kebab-case or lowercase
                if filename.islower() or "-" in filename:
                    continue
                files.append(file_path)
    return files


def rename_file(file_path: Path, dry_run: bool = False) -> Tuple[bool, str]:
    """
    Rename a file using git mv.

    Returns:
        Tuple of (success, message)
    """
    try:
        old_name = file_path.name
        new_name = to_kebab_case(old_name)

        if old_name == new_name:
            return False, "Already in kebab-case"

        new_path = file_path.parent / new_name

        if new_path.exists():
            return False, f"Target already exists: {new_path}"

        if dry_run:
            print(f"[DRY RUN] Would rename: {file_path} → {new_path}")
            return True, "Would rename"

        # Use git mv to preserve history
        result = subprocess.run(["git", "mv", str(file_path), str(new_path)], capture_output=True, text=True)

        if result.returncode != 0:
            return False, f"git mv failed: {result.stderr}"

        print(f"✓ Renamed: {file_path.name} → {new_name}")
        return True, "Renamed"

    except Exception as e:
        return False, str(e)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Rename SCREAMING_SNAKE_CASE markdown files to kebab-case")
    parser.add_argument("directories", nargs="+", help="Directories to search")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be renamed without changing files")

    args = parser.parse_args()

    directories = [Path(d) for d in args.directories]

    print("Searching for SCREAMING_SNAKE_CASE files...")
    if args.dry_run:
        print("[DRY RUN MODE - No files will be renamed]\n")

    files_to_rename = find_screaming_snake_files(directories)

    if not files_to_rename:
        print("No SCREAMING_SNAKE_CASE files found.")
        return

    print(f"Found {len(files_to_rename)} files to rename\n")

    renamed_count = 0
    skipped_count = 0
    error_count = 0

    for file_path in sorted(files_to_rename):
        success, message = rename_file(file_path, args.dry_run)
        if success:
            renamed_count += 1
        elif "Already" in message or "Would rename" in message:
            skipped_count += 1
        else:
            error_count += 1
            print(f"✗ Error: {file_path} - {message}")

    print(f"\n{'Would rename' if args.dry_run else 'Renamed'}: {renamed_count} files")
    if skipped_count > 0:
        print(f"Skipped: {skipped_count} files")
    if error_count > 0:
        print(f"Errors: {error_count} files")


if __name__ == "__main__":
    main()
