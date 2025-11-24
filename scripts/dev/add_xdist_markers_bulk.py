#!/usr/bin/env python3
"""
Bulk add xdist markers and gc.collect() to test files.

Converts function-based tests using MagicMock/AsyncMock into class-based tests
with proper memory safety patterns for pytest-xdist.

Usage:
    python scripts/dev/add_xdist_markers_bulk.py tests/unit/storage/test_conversation_store_async.py
"""

import argparse
import ast
import re
from pathlib import Path


def should_add_gc_import(content: str) -> bool:
    """Check if 'import gc' needs to be added."""
    return "import gc" not in content and "from gc import" not in content


def needs_xdist_marker(file_path: Path) -> tuple[bool, list[str]]:
    """
    Check if file needs xdist markers by detecting MagicMock/AsyncMock usage.

    Returns:
        (needs_markers, test_function_names)
    """
    with open(file_path) as f:
        content = f.read()

    # Check for MagicMock or AsyncMock usage
    has_mocks = "MagicMock" in content or "AsyncMock" in content

    if not has_mocks:
        return False, []

    # Parse to find test functions
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return False, []

    test_functions = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            test_functions.append(node.name)

    return bool(test_functions), test_functions


def transform_to_class_based(content: str, group_name: str, test_functions: list[str]) -> str:
    """
    Transform function-based tests to class-based with xdist markers.

    Args:
        content: Original file content
        group_name: Name for xdist_group
        test_functions: List of test function names to convert

    Returns:
        Transformed content
    """
    lines = content.split("\n")

    # Add gc import if needed
    if should_add_gc_import(content):
        # Find import section (after docstring, before first def/class)
        insert_idx = 0
        in_docstring = False
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('"""') or stripped.startswith("'''"):
                in_docstring = not in_docstring
            elif not in_docstring and (stripped.startswith("import ") or stripped.startswith("from ")):
                insert_idx = i + 1
            elif not in_docstring and (stripped.startswith("def ") or stripped.startswith("class ")):
                break

        # Insert gc import after other imports
        if insert_idx > 0:
            lines.insert(insert_idx, "import gc")

    # Find first test function
    first_test_idx = None
    for i, line in enumerate(lines):
        if any(line.strip().startswith(f"def {func}(") for func in test_functions):
            first_test_idx = i
            break

    if first_test_idx is None:
        return content  # No test functions found

    # Calculate indentation
    indent = "    "

    # Insert class definition and teardown before first test
    class_lines = [
        "",
        f'@pytest.mark.xdist_group(name="{group_name}")',
        f"class Test{group_name.replace('_', ' ').title().replace(' ', '')}:",
        f'{indent}"""Test class with xdist memory safety."""',
        "",
        f"{indent}def teardown_method(self):",
        f'{indent}{indent}"""Force GC to prevent mock accumulation in xdist workers"""',
        f"{indent}{indent}gc.collect()",
        "",
    ]

    # Insert class header
    lines[first_test_idx:first_test_idx] = class_lines

    # Add self parameter and indent all test functions
    result_lines = []
    in_test_function = False
    function_indent = 0

    for line in lines:
        # Check if this is a test function definition
        is_test_def = any(line.strip().startswith(f"def {func}(") for func in test_functions)

        if is_test_def:
            in_test_function = True
            function_indent = len(line) - len(line.lstrip())
            # Add self parameter
            line = line.replace("def test_", f"{indent}def test_").replace("():", "(self):")
            if "self" not in line:
                line = line.replace("):", ", self):" if "(" in line else "(self):")

        # Indent function body
        if in_test_function and line.strip():
            if line.strip().startswith("def ") and not is_test_def:
                in_test_function = False
            else:
                if not is_test_def and line[function_indent : function_indent + 4] != "    ":
                    line = " " * function_indent + indent + line[function_indent:]

        result_lines.append(line)

    return "\n".join(result_lines)


def main():
    parser = argparse.ArgumentParser(description="Add xdist markers to test files")
    parser.add_argument("files", nargs="+", help="Test files to process")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without writing")
    args = parser.parse_args()

    for file_path_str in args.files:
        file_path = Path(file_path_str)

        if not file_path.exists():
            print(f"⚠️  Skipping {file_path} (does not exist)")
            continue

        needs_markers, test_functions = needs_xdist_marker(file_path)

        if not needs_markers:
            print(f"✅ {file_path} - No changes needed")
            continue

        print(f"🔄 Processing {file_path} ({len(test_functions)} test functions)...")

        # Generate group name from file name
        group_name = file_path.stem.replace("test_", "")

        with open(file_path) as f:
            original_content = f.read()

        transformed_content = transform_to_class_based(original_content, group_name, test_functions)

        if args.dry_run:
            print(f"   Would transform {len(test_functions)} test functions")
            print(f"   Group name: {group_name}")
        else:
            with open(file_path, "w") as f:
                f.write(transformed_content)
            print(f"   ✓ Transformed {len(test_functions)} test functions")
            print(f"   ✓ Added xdist_group marker: {group_name}")
            print("   ✓ Added gc.collect() teardown")

    print(f"\n✅ Processed {len(args.files)} files")


if __name__ == "__main__":
    main()
