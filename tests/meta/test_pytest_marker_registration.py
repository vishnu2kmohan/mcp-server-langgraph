"""
Meta-test: Pytest Marker Registration Validation

Ensures all pytest markers used in test files are registered in pyproject.toml.

This test prevents marker registration errors like:
    PytestUnknownMarkWarning: Unknown pytest.mark.foo
    'foo' not found in `markers` configuration option

See: https://docs.pytest.org/en/stable/how-to/mark.html
"""

import ast
import re
from pathlib import Path
from typing import Set

import pytest
import toml


def get_registered_markers() -> Set[str]:
    """
    Extract all registered markers from pyproject.toml

    Returns:
        Set of marker names (e.g., {'unit', 'integration', 'e2e'})
    """
    pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
    config = toml.load(pyproject_path)

    markers = config.get("tool", {}).get("pytest", {}).get("ini_options", {}).get("markers", [])

    # Extract marker name from "marker_name: description" format
    marker_names = set()
    for marker_def in markers:
        # Format is "marker_name: description"
        match = re.match(r"^([a-z_][a-z0-9_]*)\s*:", marker_def)
        if match:
            marker_names.add(match.group(1))

    return marker_names


def get_used_markers() -> Set[str]:
    """
    Scan all test files for @pytest.mark.* usage

    Returns:
        Set of marker names found in test files
    """
    tests_dir = Path(__file__).parent.parent
    marker_names = set()

    # Find all test files
    test_files = list(tests_dir.rglob("test_*.py"))

    for test_file in test_files:
        try:
            source = test_file.read_text()
            tree = ast.parse(source)

            # Find all decorator nodes
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    for decorator in node.decorator_list:
                        # Handle @pytest.mark.foo
                        if isinstance(decorator, ast.Attribute):
                            if (
                                isinstance(decorator.value, ast.Attribute)
                                and getattr(decorator.value.value, "id", None) == "pytest"
                                and decorator.value.attr == "mark"
                            ):
                                marker_names.add(decorator.attr)

                        # Handle @pytest.mark.foo()
                        elif isinstance(decorator, ast.Call):
                            func = decorator.func
                            if isinstance(func, ast.Attribute):
                                if (
                                    isinstance(func.value, ast.Attribute)
                                    and getattr(func.value.value, "id", None) == "pytest"
                                    and func.value.attr == "mark"
                                ):
                                    marker_names.add(func.attr)

        except Exception as e:
            # Log but don't fail on individual file parsing errors
            print(f"Warning: Failed to parse {test_file}: {e}")

    return marker_names


@pytest.mark.meta
@pytest.mark.unit
def test_all_used_markers_are_registered():
    """
    CRITICAL: Verify all pytest markers used in tests are registered in pyproject.toml

    This test prevents CI failures due to unregistered markers.

    Failure means:
    - A test file uses @pytest.mark.foo but foo is not in pyproject.toml
    - Solution: Add the marker to [tool.pytest.ini_options].markers in pyproject.toml
    """
    registered_markers = get_registered_markers()
    used_markers = get_used_markers()

    # Find markers that are used but not registered
    unregistered = used_markers - registered_markers

    # Known built-in markers that don't need registration
    builtin_markers = {
        "parametrize",
        "skip",
        "skipif",
        "xfail",
        "filterwarnings",
        "usefixtures",
        "tryfirst",
        "trylast",
    }

    # Exclude built-in markers
    unregistered = unregistered - builtin_markers

    assert not unregistered, (
        f"The following markers are used in tests but not registered in pyproject.toml:\n"
        f"  {sorted(unregistered)}\n\n"
        f"To fix, add them to [tool.pytest.ini_options].markers in pyproject.toml:\n"
        f"  markers = [\n"
        + "\n".join(f'    "{marker}: Description of {marker} tests",' for marker in sorted(unregistered))
        + "\n  ]\n\n"
        f"Registered markers: {sorted(registered_markers)}\n"
        f"Used markers: {sorted(used_markers)}"
    )


@pytest.mark.meta
@pytest.mark.unit
def test_no_unused_marker_registrations():
    """
    Optional: Warn about registered markers that are never used

    This helps keep pyproject.toml clean and identifies outdated markers.

    Note: This is a warning, not a failure. Unused markers may be intended
    for future use or external tooling.
    """
    registered_markers = get_registered_markers()
    used_markers = get_used_markers()

    unused = registered_markers - used_markers

    if unused:
        pytest.warns(
            UserWarning,
            match=f"The following markers are registered but never used: {sorted(unused)}",
        )


@pytest.mark.meta
@pytest.mark.unit
def test_marker_naming_conventions():
    """
    Validate marker naming follows conventions

    Conventions:
    - Lowercase with underscores (snake_case)
    - No hyphens or spaces
    - Descriptive names
    """
    registered_markers = get_registered_markers()

    invalid_markers = []
    for marker in registered_markers:
        # Check snake_case naming
        if not re.match(r"^[a-z][a-z0-9_]*$", marker):
            invalid_markers.append(marker)

    assert not invalid_markers, (
        f"The following markers don't follow naming conventions (snake_case):\n" f"  {sorted(invalid_markers)}"
    )
