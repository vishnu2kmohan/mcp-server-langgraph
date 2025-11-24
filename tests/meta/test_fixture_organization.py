"""
Test fixture organization and best practices.

This test module validates that test fixtures follow best practices:
- No duplicate autouse fixtures across different files
- All session/module-scoped autouse fixtures should be in conftest.py
- Fixture names are unique or intentionally scoped
- Validation covers ALL test directories (unit, integration, e2e, meta, regression, etc.)

CRITICAL: This test must scan the FULL tests/ tree, not just tests/meta/!
Without full tree scanning, duplicate fixtures in tests/unit, tests/e2e, etc. are never detected.
"""

import ast
from pathlib import Path

import pytest

# Mark as unit test to ensure it runs in CI
pytestmark = pytest.mark.unit


def find_autouse_fixtures(test_dir: Path) -> dict[str, list[tuple[str, int]]]:
    """
    Scan all Python test files for autouse fixtures.

    Returns:
        Dictionary mapping fixture names to list of (file_path, line_number) tuples
    """
    autouse_fixtures: dict[str, list[tuple[str, int]]] = {}

    for test_file in test_dir.rglob("*.py"):
        if test_file.name.startswith("_"):
            continue

        try:
            with open(test_file, encoding="utf-8") as f:
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


def test_fixture_scan_covers_full_test_tree():
    """
    CRITICAL: Validate that fixture organization tests scan the FULL tests/ directory.

    This test ensures we don't have the bug where fixture validation only scans
    tests/meta/ and misses duplicates in tests/unit/, tests/e2e/, tests/integration/, etc.

    Background:
    - Original implementation used `Path(__file__).parent` (tests/meta/)
    - This missed 16+ duplicate autouse fixtures in other test directories
    - Fix: Use `Path(__file__).parent.parent` (tests/ root)

    This is a meta-test that validates the other tests are checking the right scope.
    """
    # The test file is at tests/meta/test_fixture_organization.py
    this_file = Path(__file__)
    assert this_file.name == "test_fixture_organization.py", "Unexpected test file name"

    # The parent should be tests/meta/
    meta_dir = this_file.parent
    assert meta_dir.name == "meta", f"Expected parent to be 'meta', got '{meta_dir.name}'"

    # The grandparent should be tests/
    tests_root = meta_dir.parent
    assert tests_root.name == "tests", f"Expected grandparent to be 'tests', got '{tests_root.name}'"

    # The tests used in this module should scan from tests/ root, not tests/meta/
    # This is verified by checking that find_autouse_fixtures is called with tests/ root

    # Verify that tests/ root contains expected subdirectories
    expected_subdirs = {"unit", "integration", "e2e", "meta", "fixtures"}
    actual_subdirs = {p.name for p in tests_root.iterdir() if p.is_dir() and not p.name.startswith("_")}

    missing = expected_subdirs - actual_subdirs
    assert not missing, (
        f"Expected test subdirectories missing: {missing}\n"
        f"Tests root: {tests_root}\n"
        f"This suggests the tests/ directory structure has changed."
    )

    # Verify the other tests in this module use the correct scope
    # They should use Path(__file__).parent.parent (tests/), not Path(__file__).parent (tests/meta/)
    with open(__file__, encoding="utf-8") as f:
        content = f.read()

    # Count occurrences of the pattern
    wrong_pattern_count = content.count("test_dir = Path(__file__).parent\n")
    correct_pattern_count = content.count("test_dir = Path(__file__).parent.parent")

    if wrong_pattern_count > 0:
        raise AssertionError(
            f"Found {wrong_pattern_count} instances of 'test_dir = Path(__file__).parent' "
            f"in {__file__}\n\n"
            f"This limits scanning to tests/meta/ only, missing duplicates in:\n"
            f"  - tests/unit/\n"
            f"  - tests/e2e/\n"
            f"  - tests/integration/\n"
            f"  - tests/regression/\n\n"
            f"FIX: Change to 'test_dir = Path(__file__).parent.parent' to scan full tests/ tree\n\n"
            f"Expected usage:\n"
            f"  test_dir = Path(__file__).parent.parent  # tests/ root\n"
            f"  autouse_fixtures = find_autouse_fixtures(test_dir)"
        )

    assert correct_pattern_count >= 2, (
        f"Expected at least 2 instances of correct pattern 'Path(__file__).parent.parent' "
        f"(one for each test function), but found {correct_pattern_count}\n\n"
        f"This test file should scan the full tests/ tree, not just tests/meta/"
    )


def test_no_duplicate_autouse_fixtures():
    """
    Test that autouse fixtures are not duplicated across test files.

    TDD RED phase: This test should FAIL initially if duplicate fixtures exist.
    After consolidating fixtures into conftest.py, this test should PASS.

    Best practice: Module/session-scoped autouse fixtures should be defined
    in conftest.py to avoid initialization conflicts and improve clarity.
    """
    test_dir = Path(__file__).parent.parent  # tests/ root, not tests/meta/
    autouse_fixtures = find_autouse_fixtures(test_dir)

    # Find fixtures with multiple definitions
    duplicates: dict[str, list[tuple[str, int]]] = {}
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
    test_dir = Path(__file__).parent.parent  # tests/ root, not tests/meta/
    autouse_fixtures = find_autouse_fixtures(test_dir)

    undocumented: list[tuple[str, str, int]] = []

    for fixture_name, locations in autouse_fixtures.items():
        for file_path, line_num in locations:
            full_path = test_dir / file_path
            try:
                with open(full_path, encoding="utf-8") as f:
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
            except (OSError, IndexError):
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
