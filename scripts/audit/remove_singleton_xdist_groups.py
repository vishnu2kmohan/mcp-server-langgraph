#!/usr/bin/env python3
"""Remove singleton xdist_group markers from test files.

Removes @pytest.mark.xdist_group markers from test classes that are the
only class in their group (singletons). These markers provide zero
serialization benefit since there's nothing to serialize against.

Usage:
    python scripts/audit/remove_singleton_xdist_groups.py --dry-run      # Preview changes
    python scripts/audit/remove_singleton_xdist_groups.py                 # Apply changes
    python scripts/audit/remove_singleton_xdist_groups.py --unit-only     # Only unit tests

IMPORTANT: Does NOT remove teardown_method/gc.collect() — those serve a
separate purpose (memory management) and should be kept.

Exit codes:
    0 - Success
    1 - Errors encountered
"""

from __future__ import annotations

import ast
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
TESTS_DIR = PROJECT_ROOT / "tests"


def find_singleton_groups(tests_dir: Path, unit_only: bool = False) -> dict[str, list[dict]]:
    """Find all singleton xdist_group markers.

    Returns dict mapping group_name -> [single location dict].
    """
    all_groups: dict[str, list[dict]] = defaultdict(list)

    for py_file in tests_dir.rglob("*.py"):
        if py_file.name.startswith("_") and py_file.name != "__init__.py":
            continue

        try:
            source = py_file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            continue

        if "xdist_group" not in source:
            continue

        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue

        rel_path = str(py_file.relative_to(PROJECT_ROOT))

        if unit_only and not rel_path.startswith("tests/unit/"):
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef) or not node.name.startswith("Test"):
                continue

            for decorator in node.decorator_list:
                group_name = _extract_xdist_group_name(decorator)
                if group_name:
                    all_groups[group_name].append(
                        {
                            "file": rel_path,
                            "abs_path": str(py_file),
                            "class": node.name,
                            "line": node.lineno,
                            "decorator_line": decorator.lineno,
                        }
                    )

    # Filter to singletons only
    return {name: locs for name, locs in all_groups.items() if len(locs) == 1}


def _extract_xdist_group_name(decorator: ast.expr) -> str | None:
    """Extract group name from xdist_group decorator."""
    if isinstance(decorator, ast.Call):
        func = decorator.func
        if isinstance(func, ast.Attribute) and func.attr == "xdist_group":
            for kw in decorator.keywords:
                if kw.arg == "name" and isinstance(kw.value, ast.Constant):
                    return str(kw.value.value)
            if decorator.args and isinstance(decorator.args[0], ast.Constant):
                return str(decorator.args[0].value)
    return None


def remove_markers_from_file(file_path: str, decorator_lines: list[int], dry_run: bool = True) -> int:
    """Remove xdist_group decorator lines from a file.

    Processes lines in reverse order to avoid line-number shifting.
    Returns count of markers removed.
    """
    path = Path(file_path)
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)

    # Sort in reverse order to avoid line-number shifting
    removed = 0
    for decorator_line in sorted(decorator_lines, reverse=True):
        idx = decorator_line - 1
        if idx >= len(lines):
            continue
        if "xdist_group" not in lines[idx]:
            continue
        if not dry_run:
            del lines[idx]
        removed += 1

    if not dry_run and removed > 0:
        path.write_text("".join(lines), encoding="utf-8")

    return removed


def main() -> int:
    """Remove singleton xdist_group markers."""
    dry_run = "--dry-run" in sys.argv
    unit_only = "--unit-only" in sys.argv

    mode = "DRY RUN" if dry_run else "APPLY"
    scope = "unit tests only" if unit_only else "all tests"
    print(f"=== Remove Singleton xdist_groups ({mode}, {scope}) ===")
    print()

    singletons = find_singleton_groups(TESTS_DIR, unit_only=unit_only)

    if not singletons:
        print("No singleton xdist_group markers found.")
        return 0

    print(f"Found {len(singletons)} singleton groups to remove.")
    print()

    # Group markers by file for correct multi-marker removal
    file_markers: dict[str, list[tuple[int, str, str]]] = defaultdict(list)
    for group_name, locations in singletons.items():
        loc = locations[0]
        file_markers[loc["abs_path"]].append((loc["decorator_line"], loc["file"], group_name))

    modified_files = 0
    removed_markers = 0
    errors = 0

    for abs_path, markers in sorted(file_markers.items()):
        decorator_lines = [m[0] for m in markers]
        rel_path = markers[0][1]
        try:
            count = remove_markers_from_file(abs_path, decorator_lines, dry_run=dry_run)
            if count > 0:
                modified_files += 1
                removed_markers += count
                verb = "Would remove" if dry_run else "Removed"
                for line_no, _, group_name in sorted(markers):
                    print(f"  {verb}: {rel_path}:{line_no} (group: {group_name})")
        except Exception as e:
            print(f"  ERROR: {rel_path}: {e}")
            errors += 1

    print()
    verb = "Would modify" if dry_run else "Modified"
    print(f"{verb}: {modified_files} files, {removed_markers} markers")
    if errors:
        print(f"Errors: {errors}")

    if dry_run:
        print()
        print("Run without --dry-run to apply changes:")
        cmd = "python scripts/audit/remove_singleton_xdist_groups.py"
        if unit_only:
            cmd += " --unit-only"
        print(f"  {cmd}")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
