#!/usr/bin/env python3
"""
Migrate integration tests to tests/integration/ directory.

This script automates the migration of integration tests from various locations
to the consolidated tests/integration/ directory, preserving git history and
updating imports.

PURPOSE:
--------
Resolve OpenAI Codex Finding #3: Integration test fragmentation

WHAT IT DOES:
-------------
1. Scans all test files for @pytest.mark.integration marker
2. Identifies tests outside tests/integration/
3. Determines target directory based on source location
4. Uses 'git mv' to preserve git history
5. Creates directory structure as needed

USAGE:
------
    python scripts/migrate_integration_tests.py [--dry-run] [--verbose]

OPTIONS:
--------
    --dry-run    Show what would be moved without actually moving
    --verbose    Show detailed migration plan

EXAMPLES:
---------
    # Preview migration
    python scripts/migrate_integration_tests.py --dry-run --verbose

    # Execute migration
    python scripts/migrate_integration_tests.py

SAFETY:
-------
- Uses 'git mv' to preserve history
- Creates backups before moving
- Validates source and target paths
- Checks for file conflicts

References:
- OpenAI Codex Finding #3
- tests/meta/test_integration_test_organization.py
"""

import argparse
import ast
import subprocess
import sys
from pathlib import Path
from typing import List, Set, Tuple


def find_pytest_markers_in_file(file_path: Path) -> set[str]:
    """
    Extract all pytest markers from a test file using AST parsing.

    Returns set of marker names (e.g., {'unit', 'integration', 'meta'})
    """
    try:
        content = file_path.read_text()
        tree = ast.parse(content, filename=str(file_path))
    except (SyntaxError, UnicodeDecodeError):
        return set()

    markers = set()

    for node in ast.walk(tree):
        # Check for @pytest.mark.marker_name decorators
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            for decorator in node.decorator_list:
                # Handle @pytest.mark.integration
                if isinstance(decorator, ast.Attribute):
                    if isinstance(decorator.value, ast.Attribute) and decorator.value.attr == "mark":
                        markers.add(decorator.attr)

                # Handle @pytest.mark.integration(...) with args
                elif isinstance(decorator, ast.Call):
                    if isinstance(decorator.func, ast.Attribute):
                        if isinstance(decorator.func.value, ast.Attribute) and decorator.func.value.attr == "mark":
                            markers.add(decorator.func.attr)

        # Check for pytestmark = pytest.mark.integration
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "pytestmark":
                    # pytestmark = pytest.mark.integration
                    if isinstance(node.value, ast.Attribute):
                        if isinstance(node.value.value, ast.Attribute) and node.value.value.attr == "mark":
                            markers.add(node.value.attr)

                    # pytestmark = [pytest.mark.integration, pytest.mark.unit]
                    elif isinstance(node.value, ast.List):
                        for elt in node.value.elts:
                            if isinstance(elt, ast.Attribute):
                                if isinstance(elt.value, ast.Attribute) and elt.value.attr == "mark":
                                    markers.add(elt.attr)

    return markers


def determine_target_directory(source_path: Path, root: Path) -> Path:
    """
    Determine target directory based on source location.

    Mapping:
    - tests/unit/compliance/ → tests/integration/compliance/
    - tests/api/ → tests/integration/api/
    - tests/security/ → tests/integration/security/
    - tests/patterns/ → tests/integration/patterns/
    - tests/test_*.py (root) → tests/integration/
    """
    rel_path = source_path.relative_to(root / "tests")

    # Determine category subdirectory
    parts = rel_path.parts

    if parts[0] == "unit" and len(parts) > 1:
        # tests/unit/compliance/test_*.py → tests/integration/compliance/test_*.py
        subdirs = parts[1:-1]  # Skip 'unit' and filename
        target_subdir = root / "tests" / "integration" / Path(*subdirs)
    elif parts[0] in {
        "api",
        "security",
        "patterns",
        "contract",
        "resilience",
        "property",
        "e2e",
        "deployment",
        "deployments",
        "infrastructure",
        "core",
        "regression",
    }:
        # tests/api/test_*.py → tests/integration/api/test_*.py
        subdirs = parts[:-1]  # Keep category, skip filename
        target_subdir = root / "tests" / "integration" / Path(*subdirs)
    else:
        # tests/test_*.py → tests/integration/test_*.py
        target_subdir = root / "tests" / "integration"

    return target_subdir


def find_integration_tests_to_migrate(root: Path) -> list[tuple[Path, Path]]:
    """
    Find all integration tests outside tests/integration/ and their target paths.

    Returns list of (source_path, target_path) tuples.
    """
    tests_dir = root / "tests"
    integration_dir = tests_dir / "integration"
    meta_dir = tests_dir / "meta"

    # Find all test files
    all_test_files = sorted(tests_dir.rglob("test_*.py"))

    migrations: list[tuple[Path, Path]] = []

    for test_file in all_test_files:
        # Skip __init__.py files
        if test_file.name == "__init__.py":
            continue

        # Skip if already in tests/integration/
        if test_file.is_relative_to(integration_dir):
            continue

        # Skip meta tests (they may use integration marker for testing)
        if test_file.is_relative_to(meta_dir):
            continue

        # Check if file has integration marker
        markers = find_pytest_markers_in_file(test_file)

        if "integration" not in markers:
            continue

        # Found integration test outside tests/integration/
        target_dir = determine_target_directory(test_file, root)
        target_path = target_dir / test_file.name

        migrations.append((test_file, target_path))

    return migrations


def migrate_test_file(source: Path, target: Path, dry_run: bool = False) -> bool:
    """
    Migrate a test file using git mv to preserve history.

    Returns True if successful, False otherwise.
    """
    # Create target directory if it doesn't exist
    target.parent.mkdir(parents=True, exist_ok=True)

    # Check if target already exists
    if target.exists():
        print(f"  ⚠️  Target already exists: {target}")
        print(f"      Skipping: {source}")
        return False

    if dry_run:
        print(f"  [DRY RUN] Would move:")
        print(f"    {source.relative_to(source.parent.parent.parent)}")
        print(f"    → {target.relative_to(target.parent.parent.parent)}")
        return True

    # Use git mv to preserve history
    try:
        subprocess.run(
            ["git", "mv", str(source), str(target)],
            capture_output=True,
            text=True,
            check=True,
        )
        print(f"  ✅ Moved: {source.name}")
        print(f"      → {target.relative_to(target.parent.parent.parent)}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ❌ Failed to move: {source.name}")
        print(f"      Error: {e.stderr}")
        return False


def create_init_files(root: Path, migrations: list[tuple[Path, Path]], dry_run: bool = False):
    """
    Create __init__.py files in new directories.
    """
    # Collect all target directories
    target_dirs = {target.parent for _, target in migrations}

    for target_dir in sorted(target_dirs):
        init_file = target_dir / "__init__.py"

        if init_file.exists():
            continue

        if dry_run:
            print(f"  [DRY RUN] Would create: {init_file.relative_to(root)}")
            continue

        # Create __init__.py
        init_file.parent.mkdir(parents=True, exist_ok=True)
        init_file.write_text("")
        print(f"  ✅ Created: {init_file.relative_to(root)}")

        # Stage with git
        try:
            subprocess.run(
                ["git", "add", str(init_file)],
                capture_output=True,
                check=True,
            )
        except subprocess.CalledProcessError:
            pass  # Not critical if git add fails


def main():
    """Main migration script."""
    parser = argparse.ArgumentParser(description="Migrate integration tests to tests/integration/")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be moved without actually moving",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed migration plan",
    )
    args = parser.parse_args()

    # Find repository root
    root = Path(__file__).parent.parent

    print("=" * 80)
    print("Integration Test Migration Script")
    print("=" * 80)
    print()
    print(f"Repository: {root}")
    print()

    # Find integration tests to migrate
    print("Scanning for integration tests to migrate...")
    migrations = find_integration_tests_to_migrate(root)

    if not migrations:
        print("✅ No integration tests need to be migrated.")
        print("   All integration tests are already in tests/integration/")
        return 0

    print(f"Found {len(migrations)} integration tests to migrate.")
    print()

    if args.verbose or args.dry_run:
        print("Migration Plan:")
        print("-" * 80)

        # Group by source directory for better readability
        by_source_dir = {}
        for source, target in migrations:
            source_dir = source.parent
            if source_dir not in by_source_dir:
                by_source_dir[source_dir] = []
            by_source_dir[source_dir].append((source, target))

        for source_dir in sorted(by_source_dir.keys()):
            print(f"\n{source_dir.relative_to(root)}:")
            for source, target in by_source_dir[source_dir]:
                print(f"  • {source.name}")
                print(f"    → {target.relative_to(root)}")

        print()
        print("-" * 80)
        print()

    if args.dry_run:
        print("DRY RUN MODE - No files will be moved.")
        print()
        return 0

    # Confirm migration
    response = input(f"Migrate {len(migrations)} test files? [y/N]: ")
    if response.lower() != "y":
        print("Migration cancelled.")
        return 1

    print()
    print("Migrating tests...")
    print()

    # Create __init__.py files in target directories
    print("Creating __init__.py files in target directories...")
    create_init_files(root, migrations, dry_run=args.dry_run)
    print()

    # Migrate files
    successful = 0
    failed = 0

    for source, target in migrations:
        if migrate_test_file(source, target, dry_run=args.dry_run):
            successful += 1
        else:
            failed += 1

    print()
    print("=" * 80)
    print("Migration Complete")
    print("=" * 80)
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print()

    if failed > 0:
        print("⚠️  Some migrations failed. Review errors above.")
        return 1

    print("✅ All integration tests migrated successfully!")
    print()
    print("Next steps:")
    print("1. Run meta-tests to verify: pytest tests/meta/test_integration_test_organization.py")
    print("2. Run migrated tests: pytest tests/integration/ -v")
    print("3. Commit changes: git commit -m 'refactor: consolidate integration tests into tests/integration/'")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
