#!/usr/bin/env python3
"""
Pre-commit hook: Detect unconfigured AsyncMock instances.

This script identifies AsyncMock() instances that lack explicit return_value
or side_effect configuration, which can cause subtle bugs in authorization
checks and parallel test execution.

Configuration Detection:
- Constructor kwargs: AsyncMock(return_value=..., side_effect=..., spec=...)
- Post-creation assignment: mock.return_value = ... or mock.side_effect = ...
- Spec configuration: AsyncMock(spec=SomeClass) is considered configured

False Positive Prevention:
- Supports # noqa: async-mock-config inline suppression
- Recognizes constructor keyword arguments
- Scopes analysis to function boundaries

Exit codes:
    0: All AsyncMock instances are properly configured
    1: Found unconfigured AsyncMock instances (blocking)

Usage:
    python scripts/check_async_mock_configuration.py [files...]
"""
import ast
import sys
from pathlib import Path
from typing import List, Tuple


class AsyncMockDetector(ast.NodeVisitor):
    """AST visitor to detect unconfigured AsyncMock instances."""

    def __init__(self, filepath: str, source_lines: List[str]):
        self.filepath = filepath
        self.source_lines = source_lines
        self.issues: List[Tuple[int, str]] = []
        self.async_mock_vars: dict[str, int] = {}  # var_name -> line_number

    def has_noqa_comment(self, lineno: int) -> bool:
        """Check if a line has # noqa: async-mock-config comment."""
        if lineno <= 0 or lineno > len(self.source_lines):
            return False
        line = self.source_lines[lineno - 1]  # Convert 1-indexed to 0-indexed
        return "# noqa: async-mock-config" in line or "#noqa: async-mock-config" in line or "# noqa" in line

    def visit_Assign(self, node: ast.Assign) -> None:
        """Visit assignment nodes to detect AsyncMock() creation."""
        # Check if right side is AsyncMock() call
        if isinstance(node.value, ast.Call):
            if self._is_async_mock_call(node.value):
                # Check if AsyncMock is configured via constructor kwargs
                is_configured_in_constructor = self._has_config_kwargs(node.value)

                # Record all target variable names (only if not configured in constructor)
                if not is_configured_in_constructor:
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            self.async_mock_vars[target.id] = node.lineno
                        elif isinstance(target, ast.Attribute):
                            # Handle mock_obj.method = AsyncMock()
                            var_name = self._get_full_attr_name(target)
                            if var_name:
                                self.async_mock_vars[var_name] = node.lineno

        self.generic_visit(node)

    def visit_Expr(self, node: ast.Expr) -> None:
        """Visit expression nodes to detect return_value/side_effect configuration."""
        if isinstance(node.value, ast.Assign):
            # This shouldn't happen, but handle it anyway
            self.visit_Assign(node.value)
        elif isinstance(node.value, ast.Attribute):
            # Check for mock.return_value = ... or mock.side_effect = ...
            attr = node.value
            if isinstance(attr, ast.Attribute):
                if attr.attr in ("return_value", "side_effect"):
                    # Remove this mock from unconfigured list
                    base_name = self._get_base_name(attr.value)
                    if base_name and base_name in self.async_mock_vars:
                        del self.async_mock_vars[base_name]

        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definitions."""
        # Save current state
        prev_async_mock_vars = self.async_mock_vars.copy()

        # Visit function body
        self.generic_visit(node)

        # Check for unconfigured mocks at end of function
        for var_name, line_num in self.async_mock_vars.items():
            # Skip if line has noqa comment
            if self.has_noqa_comment(line_num):
                continue

            # Check if this mock is configured anywhere in the function
            configured = self._check_if_configured_in_scope(node, var_name)
            if not configured:
                self.issues.append((line_num, f"AsyncMock '{var_name}' created but not configured"))

        # Restore state (scoped to function)
        self.async_mock_vars = prev_async_mock_vars

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function definitions."""
        self.visit_FunctionDef(node)

    def _is_async_mock_call(self, node: ast.Call) -> bool:
        """Check if node is AsyncMock() call."""
        if isinstance(node.func, ast.Name) and node.func.id == "AsyncMock":
            return True
        return False

    def _has_config_kwargs(self, node: ast.Call) -> bool:
        """Check if AsyncMock() call has return_value or side_effect kwargs."""
        for keyword in node.keywords:
            if keyword.arg in ("return_value", "side_effect", "spec", "spec_set"):
                return True
        return False

    def _get_full_attr_name(self, node: ast.Attribute) -> str | None:
        """Get full attribute name like 'mock.method'."""
        parts = []
        current = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
            return ".".join(reversed(parts))
        return None

    def _get_base_name(self, node: ast.expr) -> str | None:
        """Get base variable name from expression."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return self._get_base_name(node.value)
        return None

    def _check_if_configured_in_scope(self, scope_node: ast.FunctionDef, var_name: str) -> bool:
        """Check if AsyncMock variable is configured with return_value/side_effect in scope."""
        for stmt in ast.walk(scope_node):
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Attribute):
                        base = self._get_base_name(target.value)
                        if base == var_name and target.attr in ("return_value", "side_effect"):
                            return True
        return False


def check_file(filepath: str) -> List[Tuple[int, str]]:
    """Check a single file for unconfigured AsyncMock instances."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # Parse content and split into lines
        source_lines = content.splitlines()
        tree = ast.parse(content, filename=filepath)

        detector = AsyncMockDetector(filepath, source_lines)
        detector.visit(tree)
        return detector.issues

    except SyntaxError as e:
        print(f"⚠️  Syntax error in {filepath}: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"⚠️  Error checking {filepath}: {e}", file=sys.stderr)
        return []


def main() -> int:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: check_async_mock_configuration.py <file> [<file> ...]", file=sys.stderr)
        return 1

    files = sys.argv[1:]
    all_issues = []

    for filepath in files:
        # Only check test files
        if not filepath.startswith("tests/") or not filepath.endswith(".py"):
            continue

        issues = check_file(filepath)
        if issues:
            all_issues.extend([(filepath, line, msg) for line, msg in issues])

    if all_issues:
        print("❌ Found unconfigured AsyncMock instances:\n", file=sys.stderr)
        for filepath, line_num, message in all_issues:
            print(f"  {filepath}:{line_num} - {message}", file=sys.stderr)

        print("\n📖 Fix: Add explicit return_value or side_effect configuration:", file=sys.stderr)
        print("   Option 1 - Constructor kwargs: mock = AsyncMock(return_value=value)", file=sys.stderr)
        print("   Option 2 - Post-creation: mock.method.return_value = expected_value", file=sys.stderr)
        print("   Option 3 - Spec: mock = AsyncMock(spec=SomeClass)", file=sys.stderr)
        print("   Option 4 - Suppress: mock = AsyncMock()  # noqa: async-mock-config", file=sys.stderr)
        print("\nSee: tests/ASYNC_MOCK_GUIDELINES.md for best practices\n", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
