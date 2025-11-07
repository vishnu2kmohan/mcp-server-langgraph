#!/usr/bin/env python3
"""
Script to remove duplicate init_test_observability fixtures from test files.

This script identifies and removes the duplicate autouse fixtures that were
consolidated into tests/conftest.py.
"""

import ast
import os
from pathlib import Path
from typing import List, Tuple


def find_fixture_definition(file_path: Path, fixture_name: str = "init_test_observability") -> Tuple[int, int]:
    """
    Find the line range of a fixture definition in a file.

    Returns:
        Tuple of (start_line, end_line) or (0, 0) if not found
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            tree = ast.parse(content, filename=str(file_path))
    except SyntaxError:
        print(f"  ❌ Syntax error in {file_path}, skipping")
        return (0, 0)

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if node.name == fixture_name:
                # Check if it's a pytest fixture with autouse=True
                is_autouse_fixture = False
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call):
                        if hasattr(decorator.func, "attr") and decorator.func.attr == "fixture":
                            for keyword in decorator.keywords:
                                if keyword.arg == "autouse" and isinstance(keyword.value, ast.Constant):
                                    if keyword.value.value is True:
                                        is_autouse_fixture = True

                if is_autouse_fixture:
                    # Find the decorator line (usually 1 line before the function)
                    decorator_line = node.lineno - 1
                    # Find the end of the function (including blank lines after)
                    end_line = node.end_lineno

                    # Read the file to find trailing blank lines
                    lines = content.split("\n")
                    while end_line < len(lines) and lines[end_line].strip() == "":
                        end_line += 1

                    return (decorator_line, end_line + 1)  # +1 for inclusive range

    return (0, 0)


def remove_fixture_from_file(file_path: Path, fixture_name: str = "init_test_observability") -> bool:
    """
    Remove the fixture definition from a file.

    Returns:
        True if fixture was removed, False otherwise
    """
    start_line, end_line = find_fixture_definition(file_path, fixture_name)

    if start_line == 0:
        return False

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Remove the fixture lines
        new_lines = lines[:start_line] + lines[end_line:]

        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

        print(f"  ✅ Removed fixture from {file_path} (lines {start_line + 1}-{end_line})")
        return True
    except Exception as e:
        print(f"  ❌ Error processing {file_path}: {e}")
        return False


def main():
    """Main function to remove duplicate fixtures."""
    test_dir = Path(__file__).parent.parent / "tests"

    # List of files known to have duplicate fixtures
    # (from test_fixture_organization.py output)
    files_with_duplicates = [
        "test_auth.py",
        "test_health_check.py",
        "test_rate_limiter.py",
        "property/test_auth_properties.py",
        "integration/test_tool_improvements.py",
        "integration/test_gdpr_endpoints.py",
        "integration/test_app_startup_validation.py",
        "integration/test_mcp_startup_validation.py",
        "unit/test_search_tools.py",
        "unit/test_mcp_stdio_server.py",
        "unit/test_parallel_executor_timeout.py",
        "unit/test_provider_credentials.py",
        "unit/test_security_practices.py",
        "unit/test_dependencies_wiring.py",
        "unit/test_cache_redis_config.py",
        "core/test_cache.py",
        "core/test_container.py",
        "middleware/test_rate_limiter.py",
        "builder/test_code_generator.py",
        "builder/test_builder_security.py",
        "infrastructure/test_database_ha.py",
        "infrastructure/test_external_secrets_rbac.py",
        "infrastructure/test_app_factory.py",
        "kubernetes/test_external_secrets.py",
        "builder/api/test_server.py",
    ]

    print("🔧 Removing duplicate init_test_observability fixtures...")
    print(f"   Base directory: {test_dir}")
    print()

    removed_count = 0
    for file_rel_path in files_with_duplicates:
        file_path = test_dir / file_rel_path
        if file_path.exists():
            if remove_fixture_from_file(file_path):
                removed_count += 1
        else:
            print(f"  ⚠️  File not found: {file_path}")

    print()
    print(f"✅ Removed {removed_count} duplicate fixtures from {len(files_with_duplicates)} files")
    print()
    print("Next steps:")
    print("  1. Run: pytest tests/test_fixture_organization.py::test_no_duplicate_autouse_fixtures")
    print("  2. Verify: All tests should still pass")
    print("  3. Commit: git add -A && git commit -m 'refactor: consolidate observability fixtures'")


if __name__ == "__main__":
    main()
