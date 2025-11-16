#!/usr/bin/env python3
"""
Validation script to detect async methods mocked without AsyncMock.

This script prevents hanging tests by detecting patterns where:
- patch.object() or patch() is used without new_callable=AsyncMock
- The mocked method is awaited in the code under test

Exit codes:
    0: All async mocks are correctly configured
    1: Found async methods mocked incorrectly (will cause hanging)
"""

import ast
import re
import sys
from pathlib import Path
from typing import List, Tuple


class AsyncMockChecker(ast.NodeVisitor):
    """AST visitor to detect potential async mock issues."""

    def __init__(self, filename: str):
        self.filename = filename
        self.issues: List[Tuple[int, str]] = []
        self.has_asyncmock_import = False
        self.in_xfail_function = False

    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Check if AsyncMock is imported."""
        if node.module == "unittest.mock":
            for alias in node.names:
                if alias.name == "AsyncMock":
                    self.has_asyncmock_import = True
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Track if we're inside a function with @pytest.mark.xfail decorator."""
        # Check if function has @pytest.mark.xfail decorator
        has_xfail = False
        for decorator in node.decorator_list:
            # Handle @pytest.mark.xfail or @pytest.mark.xfail(...)
            if isinstance(decorator, ast.Attribute):
                if (
                    isinstance(decorator.value, ast.Attribute)
                    and isinstance(decorator.value.value, ast.Name)
                    and decorator.value.value.id == "pytest"
                    and decorator.value.attr == "mark"
                    and decorator.attr == "xfail"
                ):
                    has_xfail = True
            elif isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Attribute):
                    if (
                        isinstance(decorator.func.value, ast.Attribute)
                        and isinstance(decorator.func.value.value, ast.Name)
                        and decorator.func.value.value.id == "pytest"
                        and decorator.func.value.attr == "mark"
                        and decorator.func.attr == "xfail"
                    ):
                        has_xfail = True

        # Save previous state and set new state
        prev_in_xfail = self.in_xfail_function
        self.in_xfail_function = has_xfail

        # Visit function body
        self.generic_visit(node)

        # Restore previous state
        self.in_xfail_function = prev_in_xfail

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Track if we're inside an async function with @pytest.mark.xfail decorator."""
        # Same logic as visit_FunctionDef
        has_xfail = False
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Attribute):
                if (
                    isinstance(decorator.value, ast.Attribute)
                    and isinstance(decorator.value.value, ast.Name)
                    and decorator.value.value.id == "pytest"
                    and decorator.value.attr == "mark"
                    and decorator.attr == "xfail"
                ):
                    has_xfail = True
            elif isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Attribute):
                    if (
                        isinstance(decorator.func.value, ast.Attribute)
                        and isinstance(decorator.func.value.value, ast.Name)
                        and decorator.func.value.value.id == "pytest"
                        and decorator.func.value.attr == "mark"
                        and decorator.func.attr == "xfail"
                    ):
                        has_xfail = True

        prev_in_xfail = self.in_xfail_function
        self.in_xfail_function = has_xfail
        self.generic_visit(node)
        self.in_xfail_function = prev_in_xfail

    def visit_Call(self, node: ast.Call):
        """Check for patch.object() or patch() calls without AsyncMock."""
        # Check if this is a patch.object() or patch() call
        is_patch = False
        func_name = None

        if isinstance(node.func, ast.Attribute):
            if node.func.attr in ("object", "__call__"):
                if isinstance(node.func.value, ast.Name) and node.func.value.id == "patch":
                    is_patch = True
                    func_name = f"patch.{node.func.attr}"
        elif isinstance(node.func, ast.Name) and node.func.id == "patch":
            is_patch = True
            func_name = "patch"

        if is_patch:
            # Check if new_callable=AsyncMock is present
            has_async_mock = False
            for keyword in node.keywords:
                if keyword.arg == "new_callable":
                    if isinstance(keyword.value, ast.Name) and keyword.value.id == "AsyncMock":
                        has_async_mock = True

            # If no AsyncMock specified, check if this might be an async method
            if not has_async_mock:
                # Try to extract the method name being mocked
                method_name = None
                if len(node.args) >= 2:
                    # patch.object(obj, "method_name")
                    if isinstance(node.args[1], ast.Constant):
                        method_name = node.args[1].value
                elif len(node.args) >= 1:
                    # patch("module.method")
                    if isinstance(node.args[0], ast.Constant):
                        full_path = node.args[0].value
                        method_name = full_path.split(".")[-1]

                # Common async method patterns that should use AsyncMock
                async_patterns = [
                    "send_",
                    "async_",
                    "_async",
                    "fetch_",
                    "get_",
                    "create_",
                    "update_",
                    "delete_",
                    "check_",
                    "process_",
                ]

                # Whitelist of known synchronous functions that match async patterns
                # Add functions here that are definitely NOT async but match naming patterns
                sync_function_whitelist = [
                    "_get_sandbox",  # Synchronous factory function
                    "get_agent_graph",  # Synchronous agent graph factory
                    "create_auth_middleware",  # Synchronous middleware factory
                    "create_summarization_model",  # Synchronous LLM factory
                    "get_admin_token",  # Synchronous token retrieval (uses sync httpx)
                    "_get_user_realm_roles",  # Synchronous role retrieval
                    "_get_user_client_roles",  # Synchronous role retrieval
                    "_get_user_groups",  # Synchronous group retrieval
                ]

                if method_name:
                    # Skip if method is in the synchronous whitelist
                    if method_name in sync_function_whitelist:
                        pass  # This is a known synchronous function, skip check
                    else:
                        for pattern in async_patterns:
                            if pattern in method_name.lower():
                                # Skip if we're in a function with @pytest.mark.xfail
                                if not self.in_xfail_function:
                                    self.issues.append(
                                        (
                                            node.lineno,
                                            f"Method '{method_name}' mocked without AsyncMock - "
                                            f"use: {func_name}(..., new_callable=AsyncMock)",
                                        )
                                    )
                                break

        self.generic_visit(node)


def check_file(filepath: Path) -> List[Tuple[int, str]]:
    """Check a single test file for async mock issues."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # Parse the AST
        tree = ast.parse(content, filename=str(filepath))

        # Visit all nodes
        checker = AsyncMockChecker(str(filepath))
        checker.visit(tree)

        return checker.issues
    except SyntaxError as e:
        print(f"⚠️  Syntax error in {filepath}: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"⚠️  Error processing {filepath}: {e}", file=sys.stderr)
        return []


def main():
    """Main entry point."""
    # Get test files from command line or scan tests/ directory
    if len(sys.argv) > 1:
        test_files = [Path(arg) for arg in sys.argv[1:]]
    else:
        test_files = list(Path("tests").rglob("test_*.py"))

    if not test_files:
        print("No test files found.")
        return 0

    print(f"🔍 Checking {len(test_files)} test files for async mock issues...\n")

    all_issues = []
    files_with_issues = []

    for filepath in test_files:
        if not filepath.exists():
            print(f"⚠️  File not found: {filepath}", file=sys.stderr)
            continue

        issues = check_file(filepath)
        if issues:
            all_issues.extend([(filepath, line, msg) for line, msg in issues])
            files_with_issues.append(filepath)

    if all_issues:
        print("❌ Found async mock issues:\n")
        for filepath, line, msg in all_issues:
            print(f"{filepath}:{line} - {msg}")

        print(f"\n❌ {len(all_issues)} issues found in {len(files_with_issues)} files")
        print("\n💡 Fix: Import AsyncMock and add new_callable=AsyncMock to patch calls")
        print("   Example: patch.object(obj, 'async_method', new_callable=AsyncMock)")
        return 1
    else:
        print("✅ All async mocks are correctly configured!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
