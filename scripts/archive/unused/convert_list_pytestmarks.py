#!/usr/bin/env python3
"""
Convert list-based pytestmark declarations to single-marker format.

The validation script requires: pytestmark = pytest.mark.xxx
Not: pytestmark = [pytest.mark.xxx, pytest.mark.yyy]
"""

import re
from pathlib import Path


def convert_file(file_path: Path) -> bool:
    """Convert list-based pytestmark to single marker. Returns True if changed."""
    content = file_path.read_text()
    original_content = content

    # Pattern to match list-based pytestmark at module level
    # pytestmark = [pytest.mark.xxx, pytest.mark.yyy, ...]
    list_pattern = re.compile(r"^pytestmark\s*=\s*\[(.*?)\]", re.MULTILINE | re.DOTALL)

    match = list_pattern.search(content)
    if not match:
        return False

    markers_str = match.group(1)

    # Extract marker names from the list
    marker_pattern = re.compile(r"pytest\.mark\.(\w+)")
    markers = marker_pattern.findall(markers_str)

    if not markers:
        return False

    # Determine primary marker based on priority
    # Priority: integration > e2e > unit > api > other
    priority_order = ["integration", "e2e", "unit", "api", "smoke", "meta", "security", "property", "regression", "deployment"]

    primary_marker = None
    for priority_marker in priority_order:
        if priority_marker in markers:
            primary_marker = priority_marker
            break

    # If no priority marker found, use the first marker
    if not primary_marker:
        primary_marker = markers[0]

    # Replace list-based pytestmark with single marker
    new_pytestmark = f"pytestmark = pytest.mark.{primary_marker}"
    content = list_pattern.sub(new_pytestmark, content, count=1)

    if content != original_content:
        file_path.write_text(content)
        return True

    return False


def main():
    """Convert all list-based pytestmarks."""
    tests_dir = Path("tests")
    test_files = list(tests_dir.rglob("test_*.py"))
    test_files.extend(tests_dir.rglob("*_test.py"))

    converted_count = 0
    for file_path in test_files:
        if convert_file(file_path):
            converted_count += 1
            print(f"✓ {file_path.name}")

    print(f"\n✅ Converted {converted_count} files from list to single-marker format")
    return 0


if __name__ == "__main__":
    exit(main())
