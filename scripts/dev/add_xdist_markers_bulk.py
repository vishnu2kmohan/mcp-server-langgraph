#!/usr/bin/env python3
"""
Bulk add xdist markers and gc.collect() to test files.

Converts function-based tests using MagicMock/AsyncMock into class-based tests
with proper memory safety patterns for pytest-xdist.

Usage:
    python scripts/dev/add_xdist_markers_bulk.py tests/unit/storage/test_conversation_store_async.py
    python scripts/dev/add_xdist_markers_bulk.py --dry-run tests/unit/*.py

This script:
1. Detects test files using MagicMock/AsyncMock
2. Wraps test functions in a class with @pytest.mark.xdist_group
3. Adds teardown_method with gc.collect()
4. Preserves decorators (@pytest.mark.asyncio, @pytest.mark.parametrize, etc.)
5. Adds 'self' as the FIRST parameter (correct for methods)
6. Properly indents function bodies

IMPORTANT: Always review the output before committing. This script modifies
test files and can produce invalid Python if the source structure is unexpected.
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
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name.startswith("test_"):
            # Check if function is already in a class
            # Simple heuristic: check if it's a top-level function
            # (proper check would require parent tracking)
            test_functions.append(node.name)

    return bool(test_functions), test_functions


def extract_function_block(lines: list[str], start_idx: int, is_async: bool = False) -> tuple[list[str], int]:
    """
    Extract a complete function block including decorators.

    Returns:
        (decorator_lines + function_lines, end_index)
    """
    # Find decorators before the function
    decorator_start = start_idx
    for i in range(start_idx - 1, -1, -1):
        stripped = lines[i].strip()
        if stripped.startswith("@"):
            decorator_start = i
        elif stripped and not stripped.startswith("#"):
            break

    # Find function end (next unindented line or EOF)
    func_def_line = lines[start_idx]
    base_indent = len(func_def_line) - len(func_def_line.lstrip())

    end_idx = start_idx + 1
    while end_idx < len(lines):
        line = lines[end_idx]
        if not line.strip():  # Empty line
            end_idx += 1
            continue
        line_indent = len(line) - len(line.lstrip())
        if line_indent <= base_indent and line.strip():
            # New definition at same or lower indentation
            break
        end_idx += 1

    return lines[decorator_start:end_idx], end_idx


def add_self_parameter(func_def: str) -> str:
    """
    Add 'self' as the first parameter to a function definition.

    Handles:
    - def test_foo(): -> def test_foo(self):
    - def test_foo(arg1, arg2): -> def test_foo(self, arg1, arg2):
    - async def test_foo(): -> async def test_foo(self):
    """
    # Match function definition pattern
    pattern = r"^(\s*)(async\s+)?def\s+(\w+)\((.*)\)(\s*(?:->.*)?):(.*)$"
    match = re.match(pattern, func_def, re.DOTALL)

    if not match:
        return func_def  # Can't parse, return as-is

    indent_str, async_part, func_name, params, return_type, rest = match.groups()
    async_part = async_part or ""

    # Add self as first parameter
    params = params.strip()
    if params:
        new_params = f"self, {params}"
    else:
        new_params = "self"

    return_type = return_type or ""
    return f"{indent_str}{async_part}def {func_name}({new_params}){return_type}:{rest}"


def transform_to_class_based(content: str, group_name: str, test_functions: list[str]) -> str:
    """
    Transform function-based tests to class-based with xdist markers.

    Uses a multi-pass approach:
    1. Add gc import if needed
    2. Find all test function blocks
    3. Create class wrapper with xdist marker
    4. Indent function blocks and add self parameter
    5. Add teardown_method

    Args:
        content: Original file content
        group_name: Name for xdist_group
        test_functions: List of test function names to convert

    Returns:
        Transformed content
    """
    lines = content.split("\n")

    # Track test function locations
    test_blocks: list[tuple[int, int, list[str]]] = []  # (start, end, block_lines)

    # Find all test function blocks
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Check if this is a test function definition
        is_func = False
        is_async = False
        for func_name in test_functions:
            if stripped.startswith(f"def {func_name}("):
                is_func = True
                break
            elif stripped.startswith(f"async def {func_name}("):
                is_func = True
                is_async = True
                break

        if is_func:
            block_lines, end_idx = extract_function_block(lines, i, is_async)
            # Check for decorators before this line
            dec_start = i
            for j in range(i - 1, -1, -1):
                if lines[j].strip().startswith("@"):
                    dec_start = j
                elif lines[j].strip() and not lines[j].strip().startswith("#"):
                    break

            if dec_start < i:
                block_lines = lines[dec_start:end_idx]
                test_blocks.append((dec_start, end_idx, block_lines))
            else:
                test_blocks.append((i, end_idx, block_lines))
            i = end_idx
        else:
            i += 1

    if not test_blocks:
        return content  # No test functions found

    # Build new content: start with everything before the first test function
    first_test_start = test_blocks[0][0]
    result_lines = lines[:first_test_start]

    # Add gc import if not present
    if should_add_gc_import("\n".join(result_lines)):
        # Find a good place to add the import
        insert_idx = 0
        for i, line in enumerate(result_lines):
            if line.strip().startswith("import ") or line.strip().startswith("from "):
                insert_idx = i + 1
        result_lines.insert(insert_idx, "import gc")

    # Generate class name from group name
    class_name = "Test" + "".join(word.capitalize() for word in group_name.replace("_", " ").split())

    # Add class definition
    result_lines.append("")
    result_lines.append(f'@pytest.mark.xdist_group(name="{group_name}")')
    result_lines.append(f"class {class_name}:")
    result_lines.append('    """Test class with xdist memory safety."""')
    result_lines.append("")
    result_lines.append("    def teardown_method(self):")
    result_lines.append('        """Force GC to prevent mock accumulation in xdist workers"""')
    result_lines.append("        gc.collect()")
    result_lines.append("")

    # Add transformed test functions
    for _start, _end, block_lines in test_blocks:
        for line in block_lines:
            if not line.strip():
                result_lines.append("")
            elif line.strip().startswith("def ") or line.strip().startswith("async def "):
                # Add self parameter and indent
                transformed = add_self_parameter(line)
                result_lines.append("    " + transformed.lstrip())
            elif line.strip().startswith("@"):
                # Indent decorator
                result_lines.append("    " + line.lstrip())
            else:
                # Indent function body
                result_lines.append("    " + line)

    # Find the end of the last test block and add any remaining content
    last_test_end = test_blocks[-1][1]
    remaining_lines = lines[last_test_end:]

    # Filter out lines that belong to test functions we've already processed
    result_lines.extend(remaining_lines)

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
            # Validate syntax
            try:
                ast.parse(transformed_content)
                print("   ✓ Syntax valid")
            except SyntaxError as e:
                print(f"   ✗ Syntax error: {e}")
        else:
            # Validate syntax before writing
            try:
                ast.parse(transformed_content)
            except SyntaxError as e:
                print(f"   ✗ Syntax error after transformation: {e}")
                print("   ⚠️  Skipping write to prevent invalid file")
                continue

            with open(file_path, "w") as f:
                f.write(transformed_content)
            print(f"   ✓ Transformed {len(test_functions)} test functions")
            print(f"   ✓ Added xdist_group marker: {group_name}")
            print("   ✓ Added gc.collect() teardown")

    print(f"\n✅ Processed {len(args.files)} files")


if __name__ == "__main__":
    main()
