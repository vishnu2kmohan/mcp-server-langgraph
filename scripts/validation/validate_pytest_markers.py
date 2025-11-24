#!/usr/bin/env python3
"""
Validate that all pytest markers used in test files are registered in pyproject.toml.

This prevents the error: "PytestUnknownMarkWarning: Unknown pytest.mark.X"

Also validates that pytestmark declarations appear AFTER all module-level imports,
preventing SyntaxError from misplaced pytestmark assignments.

Exit codes:
    0 - All markers are registered and correctly placed
    1 - Found unregistered markers or placement errors
"""

import ast
import re
import sys
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # Fallback for Python < 3.11


def get_registered_markers() -> set[str]:
    """Extract registered markers from pyproject.toml."""
    pyproject_path = Path("pyproject.toml")

    if not pyproject_path.exists():
        print("❌ pyproject.toml not found")
        sys.exit(1)

    with open(pyproject_path, "rb") as f:
        config = tomllib.load(f)

    markers_config = config.get("tool", {}).get("pytest", {}).get("ini_options", {}).get("markers", [])

    # Extract marker names (format is "marker_name: description")
    markers = set()
    for marker_line in markers_config:
        marker_name = marker_line.split(":")[0].strip()
        markers.add(marker_name)

    return markers


def get_used_markers() -> set[str]:
    """Find all pytest.mark.* usage in test files."""
    tests_dir = Path("tests")

    if not tests_dir.exists():
        print("❌ tests/ directory not found")
        sys.exit(1)

    # Pattern matches: @pytest.mark.marker_name or pytest.mark.marker_name()
    # But NOT in comments or docstrings
    marker_pattern = re.compile(r"^\s*@pytest\.mark\.(\w+)", re.MULTILINE)

    used_markers = set()

    for test_file in tests_dir.rglob("*.py"):
        content = test_file.read_text()

        # Remove comments and docstrings to avoid false positives
        # Simple approach: remove lines starting with # and content in """..."""
        lines = content.split("\n")
        code_lines = []
        in_docstring = False
        for line in lines:
            stripped = line.strip()
            # Toggle docstring state
            if '"""' in line:
                in_docstring = not in_docstring
                continue
            # Skip comment lines and docstring content
            if not in_docstring and not stripped.startswith("#"):
                code_lines.append(line)

        code_content = "\n".join(code_lines)

        for match in marker_pattern.finditer(code_content):
            marker_name = match.group(1)
            # Skip built-in markers
            if marker_name not in {"parametrize", "skip", "skipif", "xfail", "usefixtures", "filterwarnings"}:
                # Skip markers ending with underscore (likely documentation patterns like requires_*)
                if not marker_name.endswith("_"):
                    used_markers.add(marker_name)

    return used_markers


def get_test_files_without_markers() -> list[Path]:
    """Find test files missing pytestmark declarations."""
    tests_dir = Path("tests")

    if not tests_dir.exists():
        return []

    # Pattern matches: pytestmark = pytest.mark.xxx or pytestmark = [pytest.mark.xxx, ...] at module level
    # Handles both single-line and multi-line list declarations
    pytestmark_pattern = re.compile(r"^pytestmark\s*=\s*(\[|pytest\.mark\.\w+)", re.MULTILINE)

    files_without_markers = []

    for test_file in tests_dir.rglob("test_*.py"):
        # Skip __init__.py, conftest.py, and validation_lib files
        if test_file.name in ["__init__.py", "conftest.py"] or "validation_lib" in str(test_file):
            continue

        content = test_file.read_text()

        # Check if file has pytestmark declaration
        if not pytestmark_pattern.search(content):
            files_without_markers.append(test_file)

    return files_without_markers


def validate_pytestmark_placement() -> list[str]:
    """
    Validate that pytestmark appears AFTER all module-level imports.

    Uses AST parsing to detect pytestmark declarations placed inside or
    between import statements, which causes SyntaxError.

    Returns:
        List of error messages (empty if all files are valid)

    Example violation:
        import pytest
        pytestmark = pytest.mark.unit  # ❌ Before other imports
        from pathlib import Path       # SyntaxError!

    Correct placement:
        import pytest
        from pathlib import Path

        pytestmark = pytest.mark.unit  # ✅ After all imports
    """
    tests_dir = Path("tests")

    if not tests_dir.exists():
        return []

    violations = []

    for test_file in tests_dir.rglob("test_*.py"):
        # Skip special files
        if test_file.name in ["__init__.py", "conftest.py"]:
            continue

        try:
            content = test_file.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(test_file))
        except SyntaxError as e:
            # File has syntax errors - might be due to misplaced pytestmark
            violations.append(f"{test_file}:PARSE_ERROR (cannot parse: {e})")
            continue

        # Find pytestmark assignment line (module-level only)
        pytestmark_line = None
        for node in tree.body:  # Only module-level nodes
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "pytestmark":
                        pytestmark_line = node.lineno
                        break

        # No pytestmark found - handled by other validators
        if pytestmark_line is None:
            continue

        # Find last module-level import line
        last_import_line = 0
        for node in tree.body:  # Only module-level nodes
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if hasattr(node, "lineno"):
                    last_import_line = max(last_import_line, node.lineno)

        # Validate pytestmark appears AFTER all imports
        if last_import_line > 0 and pytestmark_line < last_import_line:
            violations.append(f"{test_file}:{pytestmark_line} " f"(pytestmark before import at line {last_import_line})")

    return violations


def main():
    """Main validation logic."""
    print("🔍 Validating pytest markers...")

    registered = get_registered_markers()
    used = get_used_markers()

    unregistered = used - registered

    # Check for test files missing pytestmark
    files_without_markers = get_test_files_without_markers()

    # Check for misplaced pytestmark (NEW!)
    placement_violations = validate_pytestmark_placement()

    has_errors = False

    if unregistered:
        has_errors = True
        print(f"\n❌ Found {len(unregistered)} unregistered pytest markers:")
        for marker in sorted(unregistered):
            print(f"   - {marker}")

        print("\n📝 To fix, add these markers to pyproject.toml under [tool.pytest.ini_options]:")
        print("markers = [")
        for marker in sorted(unregistered):
            print(f'    "{marker}: Description of {marker} marker",')
        print("]")

    if files_without_markers:
        has_errors = True
        print(f"\n❌ Found {len(files_without_markers)} test files without pytestmark:")
        for test_file in sorted(files_without_markers):
            print(f"   - {test_file}")

        print("\n📝 To fix, add module-level pytestmark to each file:")
        print("   pytestmark = pytest.mark.unit")
        print("   # or")
        print("   pytestmark = pytest.mark.integration")
        print("   # or")
        print("   pytestmark = pytest.mark.e2e")

    if placement_violations:
        has_errors = True
        print(f"\n❌ Found {len(placement_violations)} pytestmark placement errors:")
        for violation in sorted(placement_violations):
            print(f"   - {violation}")

        print("\n📝 To fix, move pytestmark AFTER all import statements:")
        print("   ❌ WRONG:")
        print("      import pytest")
        print("      pytestmark = pytest.mark.unit  # Before other imports!")
        print("      from pathlib import Path")
        print("")
        print("   ✅ CORRECT:")
        print("      import pytest")
        print("      from pathlib import Path")
        print("")
        print("      pytestmark = pytest.mark.unit  # After all imports")
        print("")
        print("   See: docs-internal/PYTESTMARK_GUIDELINES.md for details")

    if has_errors:
        sys.exit(1)

    print(f"✅ All {len(used)} used markers are registered")
    print("✅ All test files have pytestmark declarations")
    print("✅ All pytestmark declarations are correctly placed")
    print(f"   Registered: {len(registered)} markers")
    print(f"   Used: {len(used)} markers")
    sys.exit(0)


if __name__ == "__main__":
    main()
