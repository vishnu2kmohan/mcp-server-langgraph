#!/usr/bin/env python3
"""
Validate that all pytest markers used in test files are registered in pyproject.toml.

This prevents the error: "PytestUnknownMarkWarning: Unknown pytest.mark.X"

Exit codes:
    0 - All markers are registered
    1 - Found unregistered markers
"""

import re
import sys
from pathlib import Path
from typing import Set

try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # Fallback for Python < 3.11


def get_registered_markers() -> Set[str]:
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


def get_used_markers() -> Set[str]:
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


def main():
    """Main validation logic."""
    print("🔍 Validating pytest markers...")

    registered = get_registered_markers()
    used = get_used_markers()

    unregistered = used - registered

    if unregistered:
        print(f"\n❌ Found {len(unregistered)} unregistered pytest markers:")
        for marker in sorted(unregistered):
            print(f"   - {marker}")

        print("\n📝 To fix, add these markers to pyproject.toml under [tool.pytest.ini_options]:")
        print("markers = [")
        for marker in sorted(unregistered):
            print(f'    "{marker}: Description of {marker} marker",')
        print("]")

        sys.exit(1)

    print(f"✅ All {len(used)} used markers are registered")
    print(f"   Registered: {len(registered)} markers")
    print(f"   Used: {len(used)} markers")
    sys.exit(0)


if __name__ == "__main__":
    main()
