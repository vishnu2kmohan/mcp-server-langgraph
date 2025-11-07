"""
Test fixture organization and best practices.

This test module validates that test fixtures follow best practices:
- No duplicate autouse fixtures across different files
- All session/module-scoped autouse fixtures should be in conftest.py
- Fixture names are unique or intentionally scoped
"""

import ast
import os
from pathlib import Path
from typing import Dict, List, Set, Tuple


def find_autouse_fixtures(test_dir: Path) -> Dict[str, List[Tuple[str, int]]]:
    """
    Scan all Python test files for autouse fixtures.

    Returns:
        Dictionary mapping fixture names to list of (file_path, line_number) tuples
    """
    autouse_fixtures: Dict[str, List[Tuple[str, int]]] = {}

    for test_file in test_dir.rglob("*.py"):
        if test_file.name.startswith("_"):
            continue

        try:
            with open(test_file, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=str(test_file))
        except SyntaxError:
            continue  # Skip files with syntax errors

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check for @pytest.fixture decorator
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call):
                        # Handle @pytest.fixture(...) with arguments
                        if hasattr(decorator.func, "attr") and decorator.func.attr == "fixture":
                            # Check for autouse=True in keyword arguments
                            for keyword in decorator.keywords:
                                if keyword.arg == "autouse" and isinstance(keyword.value, ast.Constant):
                                    if keyword.value.value is True:
                                        fixture_name = node.name
                                        file_path = str(test_file.relative_to(test_dir))
                                        line_num = node.lineno

                                        if fixture_name not in autouse_fixtures:
                                            autouse_fixtures[fixture_name] = []
                                        autouse_fixtures[fixture_name].append((file_path, line_num))

    return autouse_fixtures


def test_no_duplicate_autouse_fixtures():
    """
    Test that autouse fixtures are not duplicated across test files.

    TDD RED phase: This test should FAIL initially if duplicate fixtures exist.
    After consolidating fixtures into conftest.py, this test should PASS.

    Best practice: Module/session-scoped autouse fixtures should be defined
    in conftest.py to avoid initialization conflicts and improve clarity.
    """
    test_dir = Path(__file__).parent
    autouse_fixtures = find_autouse_fixtures(test_dir)

    # Find fixtures with multiple definitions
    duplicates: Dict[str, List[Tuple[str, int]]] = {}
    for fixture_name, locations in autouse_fixtures.items():
        if len(locations) > 1:
            # Allow duplicate fixtures if they're all in conftest.py files
            non_conftest = [loc for loc in locations if not loc[0].endswith("conftest.py")]
            if non_conftest:
                duplicates[fixture_name] = locations

    # Build error message
    if duplicates:
        error_lines = [
            "Found duplicate autouse fixtures across test files:",
            "",
            "Best practice: Module/session-scoped autouse fixtures should be in conftest.py",
            "",
        ]

        for fixture_name, locations in sorted(duplicates.items()):
            error_lines.append(f"Fixture '{fixture_name}' defined in {len(locations)} locations:")
            for file_path, line_num in locations:
                error_lines.append(f"  - {file_path}:{line_num}")
            error_lines.append("")

        error_lines.extend(
            [
                "To fix this issue:",
                "1. Move the autouse fixture to tests/conftest.py (session-scoped)",
                "2. Remove duplicate definitions from individual test files",
                "3. Re-run this test to verify the fix",
            ]
        )

        raise AssertionError("\n".join(error_lines))


def test_autouse_fixtures_documented():
    """
    Test that all autouse fixtures have proper documentation.

    Autouse fixtures run automatically, so they should be well-documented
    to explain why they run and what they do.
    """
    test_dir = Path(__file__).parent
    autouse_fixtures = find_autouse_fixtures(test_dir)

    undocumented: List[Tuple[str, str, int]] = []

    for fixture_name, locations in autouse_fixtures.items():
        for file_path, line_num in locations:
            full_path = test_dir / file_path
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                # Check if the function has a docstring
                # Look for the next few lines after the def line
                if line_num < len(lines):
                    # Get function line and next few lines
                    func_line_idx = line_num - 1  # Convert to 0-based index
                    next_lines = lines[func_line_idx : func_line_idx + 5]

                    # Check if there's a docstring in the next few lines
                    has_docstring = any('"""' in line or "'''" in line for line in next_lines[1:4])

                    if not has_docstring:
                        undocumented.append((fixture_name, file_path, line_num))
            except (IOError, IndexError):
                continue

    if undocumented:
        error_lines = [
            "Found autouse fixtures without documentation:",
            "",
            "Autouse fixtures run automatically, so they must be documented.",
            "",
        ]

        for fixture_name, file_path, line_num in undocumented:
            error_lines.append(f"  - {fixture_name} in {file_path}:{line_num}")

        raise AssertionError("\n".join(error_lines))


if __name__ == "__main__":
    # Allow running this test directly for debugging
    test_no_duplicate_autouse_fixtures()
    test_autouse_fixtures_documented()
    print("✅ All fixture organization tests passed!")
