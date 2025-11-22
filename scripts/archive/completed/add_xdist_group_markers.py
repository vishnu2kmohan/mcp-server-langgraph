#!/usr/bin/env python3
"""
Automatically add @pytest.mark.xdist_group markers to test files.

This script adds xdist_group markers to test classes that are missing them,
preventing pytest-xdist from splitting test classes across different workers.

Usage:
    python scripts/add_xdist_group_markers.py [--dry-run] [--file FILE]

Examples:
    # Preview changes without modifying files
    python scripts/add_xdist_group_markers.py --dry-run

    # Add markers to all files
    python scripts/add_xdist_group_markers.py

    # Add markers to specific file
    python scripts/add_xdist_group_markers.py --file tests/api/test_health.py
"""

import argparse
import re
import sys
from pathlib import Path


def determine_group_name(file_path: Path) -> str:
    """
    Determine appropriate xdist_group name based on file path.

    Args:
        file_path: Path to test file

    Returns:
        Group name for xdist_group marker
    """
    path_str = str(file_path)

    # Map directory patterns to group names
    if "/api/" in path_str:
        return "api_tests"
    elif "/security/" in path_str:
        return "security_tests"
    elif "/integration/" in path_str:
        return "integration_tests"
    elif "/e2e/" in path_str:
        return "e2e_tests"
    elif "/deployment/" in path_str:
        return "deployment_tests"
    elif "/resilience/" in path_str:
        return "resilience_tests"
    elif "/meta/" in path_str:
        return "meta_tests"
    elif "/builder/" in path_str:
        return "builder_tests"
    elif "/core/" in path_str:
        return "core_tests"
    elif "/kubernetes/" in path_str:
        return "kubernetes_tests"
    elif "/infrastructure/" in path_str:
        return "infrastructure_tests"
    elif "/unit/" in path_str:
        # Use filename-based group for unit tests (more granular)
        filename = file_path.stem
        return f"unit_{filename}"
    else:
        # Default: use filename
        filename = file_path.stem
        return f"test_{filename}"


def needs_xdist_group(class_def: str) -> bool:
    """
    Check if a test class needs an xdist_group marker.

    Args:
        class_def: Class definition and decorators

    Returns:
        True if class needs xdist_group marker
    """
    # Already has xdist_group
    if "@pytest.mark.xdist_group" in class_def:
        return False

    # Is a test class
    if not re.search(r"class\s+Test\w+", class_def):
        return False

    return True


def add_xdist_marker_to_file(file_path: Path, dry_run: bool = False) -> tuple[bool, int]:
    """
    Add xdist_group markers to test classes in a file.

    Args:
        file_path: Path to test file
        dry_run: If True, don't modify files

    Returns:
        Tuple of (was_modified, num_classes_updated)
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"❌ Error reading {file_path}: {e}", file=sys.stderr)
        return False, 0

    lines = content.split("\n")
    classes_updated = 0
    group_name = determine_group_name(file_path)

    # Track which lines to insert markers before
    markers_to_insert = {}

    i = 0
    while i < len(lines):
        line = lines[i]

        # Look for class definitions
        if re.match(r"^\s*class\s+Test\w+", line):
            # Check decorators before class
            j = i - 1
            has_xdist_group = False

            # Look backwards through decorators
            while j >= 0 and (lines[j].strip().startswith("@") or lines[j].strip() == ""):
                if "@pytest.mark.xdist_group" in lines[j]:
                    has_xdist_group = True
                    break
                j -= 1

            if not has_xdist_group:
                # Determine indentation level
                indent = len(line) - len(line.lstrip())
                indent_str = " " * indent

                # Add xdist_group marker before class definition
                xdist_marker = f'{indent_str}@pytest.mark.xdist_group(name="{group_name}")'
                markers_to_insert[i] = xdist_marker
                classes_updated += 1

        i += 1

    if classes_updated == 0:
        return False, 0

    # Build modified content with markers inserted
    modified_lines = []
    for i, line in enumerate(lines):
        if i in markers_to_insert:
            modified_lines.append(markers_to_insert[i])
        modified_lines.append(line)

    modified_content = "\n".join(modified_lines)

    if dry_run:
        print(f"🔍 Would modify {file_path}: {classes_updated} classes")
        return True, classes_updated
    else:
        try:
            file_path.write_text(modified_content, encoding="utf-8")
            print(f"✅ Modified {file_path}: {classes_updated} classes")
            return True, classes_updated
        except Exception as e:
            print(f"❌ Error writing {file_path}: {e}", file=sys.stderr)
            return False, 0


def find_test_files_needing_markers(repo_root: Path) -> list[Path]:
    """
    Find all test files that need xdist_group markers.

    Args:
        repo_root: Repository root directory

    Returns:
        List of test file paths
    """
    test_dir = repo_root / "tests"
    test_files = []

    for test_file in test_dir.rglob("test_*.py"):
        # Skip conftest.py and other non-test files
        if test_file.name == "conftest.py":
            continue

        # Read file to check for test classes
        try:
            content = test_file.read_text(encoding="utf-8")
            if re.search(r"^\s*class\s+Test\w+", content, re.MULTILINE):
                test_files.append(test_file)
        except Exception:
            continue

    return sorted(test_files)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Add @pytest.mark.xdist_group markers to test files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--dry-run", action="store_true", help="Show what would be changed without modifying files")
    parser.add_argument("--file", type=Path, help="Add markers to specific file only")

    args = parser.parse_args()

    # Get repository root
    repo_root = Path(__file__).parent.parent

    if args.file:
        # Process single file
        if not args.file.exists():
            print(f"❌ File not found: {args.file}", file=sys.stderr)
            return 1

        was_modified, classes_updated = add_xdist_marker_to_file(args.file, dry_run=args.dry_run)

        if was_modified:
            if args.dry_run:
                print(f"\n✅ Dry run complete. Would update {classes_updated} classes in {args.file}")
            else:
                print(f"\n✅ Successfully updated {classes_updated} classes in {args.file}")
            return 0
        else:
            print(f"\nℹ️  No changes needed for {args.file}")
            return 0

    # Process all test files
    test_files = find_test_files_needing_markers(repo_root)

    if not test_files:
        print("❌ No test files found", file=sys.stderr)
        return 1

    print(f"Found {len(test_files)} test files to process\n")

    files_modified = 0
    total_classes = 0

    for test_file in test_files:
        was_modified, classes_updated = add_xdist_marker_to_file(test_file, dry_run=args.dry_run)
        if was_modified:
            files_modified += 1
            total_classes += classes_updated

    # Print summary
    print("\n" + "=" * 70)
    print("SUMMARY: xdist_group Marker Addition")
    print("=" * 70)
    print(f"Files processed:     {len(test_files)}")
    print(f"Files modified:      {files_modified}")
    print(f"Classes updated:     {total_classes}")
    print("=" * 70)

    if args.dry_run:
        print("\n⚠️  DRY RUN - No files were modified")
        print("Run without --dry-run to apply changes")
    else:
        if files_modified > 0:
            print(f"\n✅ Successfully added xdist_group markers to {files_modified} files")
        else:
            print("\n✅ All files already have xdist_group markers")

    return 0


if __name__ == "__main__":
    sys.exit(main())
