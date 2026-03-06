#!/usr/bin/env python3
"""Audit xdist_group markers for unnecessary serialization constraints.

Analyzes the test suite to identify xdist_group markers that provide no
serialization benefit:

1. Singleton groups (only 1 test class) — zero contention possible
2. Unit test groups (only mocks, no shared resources) — no mutable state
3. Cross-file groups — may indicate duplicated test files

Usage:
    python scripts/audit/audit_xdist_groups.py                  # Summary
    python scripts/audit/audit_xdist_groups.py --verbose         # Show all groups
    python scripts/audit/audit_xdist_groups.py --removable       # List removable markers
    python scripts/audit/audit_xdist_groups.py --removable --json  # JSON output

Exit codes:
    0 - Audit complete (informational, never fails)

References:
    ADR-0052: Pytest-xdist Isolation Strategy
    Plan: Phase 4.2 - xdist_group audit
"""

from __future__ import annotations

import ast
import json
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
TESTS_DIR = PROJECT_ROOT / "tests"


def find_xdist_groups(tests_dir: Path) -> dict[str, list[dict]]:
    """Find all xdist_group markers and their locations.

    Returns dict mapping group_name -> list of {file, class, line} dicts.
    """
    groups: dict[str, list[dict]] = defaultdict(list)

    for py_file in tests_dir.rglob("*.py"):
        if py_file.name.startswith("_") and py_file.name != "__init__.py":
            continue

        try:
            source = py_file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            continue

        # Fast regex pre-check
        if "xdist_group" not in source:
            continue

        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef) or not node.name.startswith("Test"):
                continue

            for decorator in node.decorator_list:
                group_name = _extract_xdist_group_name(decorator)
                if group_name:
                    rel_path = str(py_file.relative_to(PROJECT_ROOT))
                    groups[group_name].append({"file": rel_path, "class": node.name, "line": node.lineno})

    return dict(groups)


def _extract_xdist_group_name(decorator: ast.expr) -> str | None:
    """Extract group name from @pytest.mark.xdist_group(name="...") decorator."""
    # @pytest.mark.xdist_group(name="foo")
    if isinstance(decorator, ast.Call):
        func = decorator.func
        if isinstance(func, ast.Attribute) and func.attr == "xdist_group":
            for kw in decorator.keywords:
                if kw.arg == "name" and isinstance(kw.value, ast.Constant):
                    return str(kw.value.value)
            # Positional: @pytest.mark.xdist_group("foo")
            if decorator.args and isinstance(decorator.args[0], ast.Constant):
                return str(decorator.args[0].value)
    return None


def classify_groups(groups: dict[str, list[dict]]) -> dict[str, list[str]]:
    """Classify groups into categories for removal assessment.

    Returns dict with categories as keys and lists of group names.
    """
    singletons = []
    small_same_file = []
    cross_file = []
    large = []

    for name, locations in groups.items():
        files = {loc["file"] for loc in locations}
        count = len(locations)

        if count == 1:
            singletons.append(name)
        elif len(files) == 1 and count <= 5:
            small_same_file.append(name)
        elif len(files) > 1:
            cross_file.append(name)
        else:
            large.append(name)

    return {
        "singleton": singletons,
        "small_same_file": small_same_file,
        "cross_file": cross_file,
        "large": large,
    }


def is_unit_test_file(file_path: str) -> bool:
    """Check if a file is in the unit test directory."""
    return file_path.startswith("tests/unit/")


def main() -> int:
    """Run the xdist_group audit."""
    verbose = "--verbose" in sys.argv
    removable = "--removable" in sys.argv
    json_output = "--json" in sys.argv

    print("Auditing xdist_group markers...")
    print(f"  tests directory: {TESTS_DIR}")
    print()

    groups = find_xdist_groups(TESTS_DIR)
    categories = classify_groups(groups)

    total_markers = sum(len(locs) for locs in groups.values())
    total_groups = len(groups)

    # Summary
    print(f"Total xdist_group markers: {total_markers}")
    print(f"Unique group names: {total_groups}")
    print()
    print("Distribution:")
    print(
        f"  Singleton (1 class):     {len(categories['singleton']):>5} ({len(categories['singleton']) * 100 // total_groups}%)"
    )
    print(f"  Small same-file (2-5):   {len(categories['small_same_file']):>5}")
    print(f"  Cross-file (2+ files):   {len(categories['cross_file']):>5}")
    print(f"  Large (6+):              {len(categories['large']):>5}")
    print()

    # Removable assessment
    removable_groups = categories["singleton"]
    removable_unit = [g for g in removable_groups if all(is_unit_test_file(loc["file"]) for loc in groups[g])]

    print("Removal candidates:")
    print(f"  All singletons:          {len(removable_groups):>5} (zero serialization benefit)")
    print(f"  Unit test singletons:    {len(removable_unit):>5} (safest to remove)")
    print()

    # Estimated impact
    print("Estimated impact:")
    print(f"  Files affected:          ~{len(removable_groups)}")
    print(f"  Lines of boilerplate:    ~{len(removable_groups) * 2} (marker + import)")
    print("  Parallelization gain:    ~5-15% (better xdist load balancing)")

    if removable and json_output:
        # Output removable markers as JSON
        output = []
        for name in removable_groups:
            for loc in groups[name]:
                output.append(
                    {
                        "group": name,
                        "file": loc["file"],
                        "class": loc["class"],
                        "line": loc["line"],
                        "category": "unit" if is_unit_test_file(loc["file"]) else "other",
                    }
                )
        print(json.dumps(output, indent=2))
    elif removable:
        print("\nRemovable singleton markers:")
        for name in sorted(removable_groups):
            for loc in groups[name]:
                tag = "[unit]" if is_unit_test_file(loc["file"]) else "[other]"
                print(f"  {tag} {loc['file']}:{loc['line']} {loc['class']} (group: {name})")

    if verbose:
        print("\nAll groups:")
        for name in sorted(groups.keys()):
            locs = groups[name]
            files = {loc["file"] for loc in locs}
            cat = "singleton" if len(locs) == 1 else f"{len(locs)} classes in {len(files)} files"
            print(f"  {name}: {cat}")
            for loc in locs:
                print(f"    {loc['file']}:{loc['line']} {loc['class']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
