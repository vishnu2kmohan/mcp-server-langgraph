#!/usr/bin/env python3
"""
Automatically fix auth test classes missing setup_method() for MCP_SKIP_AUTH pollution prevention.

This script adds setup_method() to all auth-related test classes that are missing it.
"""

import ast
import sys
from pathlib import Path
from typing import List, Tuple


def find_auth_test_classes_missing_setup(file_path: Path) -> List[Tuple[str, int]]:
    """Find auth test classes missing setup_method."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content, filename=str(file_path))
        missing_classes = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
                # Check if this is an auth-related test class
                is_auth_class = False

                # Check if in auth-related file
                if any(keyword in str(file_path) for keyword in ["auth", "bearer", "jwt", "openfga"]):
                    is_auth_class = True

                # Check if class name contains auth keywords
                auth_keywords = ["Auth", "GetCurrentUser", "VerifyToken", "Bearer", "JWT"]
                if any(keyword in node.name for keyword in auth_keywords):
                    is_auth_class = True

                if is_auth_class:
                    # Check if setup_method exists
                    has_setup = any(isinstance(item, ast.FunctionDef) and item.name == "setup_method" for item in node.body)

                    if not has_setup:
                        missing_classes.append((node.name, node.lineno))

        return missing_classes

    except Exception as e:
        print(f"Error processing {file_path}: {e}", file=sys.stderr)
        return []


def add_setup_method(file_path: Path, class_name: str, class_lineno: int) -> bool:
    """Add setup_method to a test class."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Find the class definition line
        class_line_idx = class_lineno - 1

        # Find the next line after class definition (skip docstring if present)
        insert_idx = class_line_idx + 1

        # Skip docstring if present
        if insert_idx < len(lines) and '"""' in lines[insert_idx]:
            # Find end of docstring
            while insert_idx < len(lines) and not (lines[insert_idx].strip().endswith('"""') and insert_idx > class_line_idx):
                insert_idx += 1
            insert_idx += 1

        # Get indentation from the line after class
        if insert_idx < len(lines):
            # Look for existing method to get indentation
            for i in range(insert_idx, min(insert_idx + 10, len(lines))):
                if "def " in lines[i]:
                    indent = len(lines[i]) - len(lines[i].lstrip())
                    break
            else:
                indent = 4  # Default indentation
        else:
            indent = 4

        # Create setup_method code
        setup_code = f'''{' ' * indent}def setup_method(self):
{' ' * indent}    """Reset state BEFORE test to prevent MCP_SKIP_AUTH pollution"""
{' ' * indent}    import os
{' ' * indent}    import mcp_server_langgraph.auth.middleware as middleware_module
{' ' * indent}
{' ' * indent}    middleware_module._global_auth_middleware = None
{' ' * indent}    os.environ["MCP_SKIP_AUTH"] = "false"
{' ' * indent}
'''

        # Insert the setup_method
        lines.insert(insert_idx, setup_code)

        # Write back to file
        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

        return True

    except Exception as e:
        print(f"Error adding setup_method to {file_path}:{class_name}: {e}", file=sys.stderr)
        return False


def main():
    """Main function."""
    # Find all test files
    test_files = []
    for path in Path("tests").rglob("test_*.py"):
        test_files.append(path)

    fixed_count = 0
    total_count = 0

    for file_path in sorted(test_files):
        missing_classes = find_auth_test_classes_missing_setup(file_path)

        if missing_classes:
            print(f"\nFixing {file_path}:")
            for class_name, class_lineno in missing_classes:
                total_count += 1
                print(f"  Adding setup_method to {class_name} (line {class_lineno})")
                if add_setup_method(file_path, class_name, class_lineno):
                    fixed_count += 1

    print(f"\n✅ Fixed {fixed_count}/{total_count} auth test classes")

    return 0 if fixed_count == total_count else 1


if __name__ == "__main__":
    sys.exit(main())
