#!/usr/bin/env python3
"""Check for duplicate Alembic revision IDs.

This script prevents the accidental creation of migrations with duplicate
revision IDs, which causes Alembic to fail with "Multiple head revisions"
or "Revision X is present more than once" errors.

Usage:
    python scripts/check_alembic_duplicates.py

Exit codes:
    0 - No duplicates found
    1 - Duplicate revision IDs detected
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


def extract_revision_id(file_path: Path) -> str | None:
    """Extract revision ID from an Alembic migration file."""
    content = file_path.read_text()

    # Match: revision = "abc123" or revision: str = "abc123"
    match = re.search(r'revision[:\s].*?[=]\s*["\']([^"\']+)["\']', content)
    return match.group(1) if match else None


def check_duplicates(versions_dir: Path) -> list[tuple[str, list[str]]]:
    """Find duplicate revision IDs in migration files.

    Returns:
        List of (revision_id, [file1, file2, ...]) for duplicates
    """
    revision_to_files: dict[str, list[str]] = {}

    for migration_file in versions_dir.glob("*.py"):
        if migration_file.name.startswith("_"):
            continue  # Skip __pycache__ etc.

        revision_id = extract_revision_id(migration_file)
        if revision_id:
            if revision_id not in revision_to_files:
                revision_to_files[revision_id] = []
            revision_to_files[revision_id].append(migration_file.name)

    # Find duplicates (revision ID appears in more than one file)
    duplicates = [(rev_id, files) for rev_id, files in revision_to_files.items() if len(files) > 1]

    return duplicates


def main() -> int:
    """Main entry point."""
    # Find alembic versions directory
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    versions_dir = repo_root / "alembic" / "versions"

    if not versions_dir.exists():
        print(f"ERROR: Alembic versions directory not found: {versions_dir}")
        return 1

    duplicates = check_duplicates(versions_dir)

    if duplicates:
        print("ERROR: Duplicate Alembic revision IDs detected!")
        print()
        for rev_id, files in duplicates:
            print(f"  Revision '{rev_id}' found in:")
            for file in files:
                print(f"    - {file}")
        print()
        print("Fix: Rename one of the files and update its revision ID.")
        print("Use: uv run alembic revision --autogenerate -m 'description'")
        return 1

    print(f"OK: No duplicate revision IDs found ({len(list(versions_dir.glob('*.py')))} migrations)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
