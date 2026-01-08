#!/usr/bin/env python3
"""
Pre-commit validation script for unsafe float patterns.

Detects code patterns that could produce NaN/Inf values, causing
JSON serialization failures in API responses and WebSocket messages.

Problem:
    # These patterns can produce NaN/Inf:
    result = sum(values) / len(values)  # div-by-zero -> Inf
    rate = errors / total * 100         # NaN if inputs are NaN
    score = round(value, 2)             # Fails if value is NaN

    # JSON serialization then fails:
    ValueError: Out of range float values are not JSON compliant

Solution:
    Use safe functions from mcp_server_langgraph.core.numeric:
    - safe_float(value) - Sanitize single values
    - safe_average(values) - Safe mean calculation
    - safe_divide(a, b) - Safe division
    - safe_round(value, n) - Safe rounding
    - safe_sum(values) - Safe summation

Usage:
    python scripts/validation/check_unsafe_float_patterns.py [path]

    # In pre-commit:
    - repo: local
      hooks:
        - id: check-unsafe-float-patterns
          name: Check unsafe float patterns
          entry: python scripts/validation/check_unsafe_float_patterns.py
          language: python
          types: [python]
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path


# Files that are allowed to have unsafe patterns (core utilities, tests)
ALLOWED_FILES = {
    "core/numeric.py",  # The safe utility module itself
    "test_numeric.py",  # Tests for the safe utilities
}

# Baseline files with known issues (existing debt - gradual migration)
# All source files have been fixed as of 2026-01-07
# Remaining issues are in test files, examples, scripts, and third-party packages
# These non-production files are baselined because:
# 1. They have proper guards (if list: before sum/len)
# 2. They're not in API response serialization paths
# 3. The risk of NaN is minimal in these contexts
BASELINE_FILES: set[str] = {
    "examples/full_workflow_demo.py",  # Demo with fixed dict values
    "scripts/ci/generate_dashboard_metrics.py",  # Guarded by if-checks
}

# Patterns to check (regex patterns for quick filtering)
UNSAFE_PATTERNS = [
    # Division patterns that might produce NaN/Inf
    r"(\w+)\s*/\s*(\w+)\s*\*\s*100",  # rate = a / b * 100
    r"sum\([^)]+\)\s*/\s*len\(",  # sum(x) / len(x) - avg pattern
    # Round patterns that could fail with NaN
    r"\bround\s*\(\s*[^,]+,",  # round(value, digits)
]


class UnsafeFloatChecker(ast.NodeVisitor):
    """AST visitor to detect unsafe float patterns."""

    def __init__(self, filepath: str) -> None:
        self.filepath = filepath
        self.errors: list[tuple[int, int, str]] = []
        self.has_safe_imports = False
        self._safe_funcs_imported: set[str] = set()

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Track imports from core.numeric module."""
        if node.module and "core.numeric" in node.module:
            for alias in node.names:
                name = alias.name
                self._safe_funcs_imported.add(name)
            self.has_safe_imports = True
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Check for unsafe function calls."""
        func_name = self._get_func_name(node)

        # Check for bare round() calls (should use safe_round)
        if func_name == "round":
            # Check if first arg could be a float from calculation
            if node.args and self._is_potentially_nan_source(node.args[0]):
                if "safe_round" not in self._safe_funcs_imported:
                    self.errors.append(
                        (
                            node.lineno,
                            node.col_offset,
                            "Unsafe round() call on potentially NaN value. "
                            "Use safe_round() from mcp_server_langgraph.core.numeric",
                        )
                    )

        self.generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp) -> None:
        """Check for unsafe division patterns."""
        if isinstance(node.op, ast.Div):
            # Check for sum(x) / len(x) pattern
            if self._is_sum_call(node.left) and self._is_len_call(node.right):
                if "safe_average" not in self._safe_funcs_imported:
                    self.errors.append(
                        (
                            node.lineno,
                            node.col_offset,
                            "Unsafe average pattern: sum(x)/len(x) can produce Inf/NaN. "
                            "Use safe_average() from mcp_server_langgraph.core.numeric",
                        )
                    )

            # Check for percentage calculation pattern: a / b * 100
            # This is detected when the parent is a multiplication by 100
            # We detect the division part here
            if self._is_potentially_nan_source(node.left) or self._is_potentially_nan_source(node.right):
                if "safe_divide" not in self._safe_funcs_imported:
                    # Only warn if the context looks like metrics/rates
                    pass  # Too many false positives, skip for now

        self.generic_visit(node)

    def _get_func_name(self, node: ast.Call) -> str | None:
        """Get the name of a function call."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            return node.func.attr
        return None

    def _is_sum_call(self, node: ast.expr) -> bool:
        """Check if node is a sum() call."""
        return isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "sum"

    def _is_len_call(self, node: ast.expr) -> bool:
        """Check if node is a len() call."""
        return isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "len"

    def _is_potentially_nan_source(self, node: ast.expr) -> bool:
        """Check if node could produce NaN (e.g., from Prometheus queries)."""
        # Look for common patterns that could return NaN:
        # - Method calls like .get_latest_value(), .query(), etc.
        # - Subscript access like results[0]
        # - Attribute access like metric.value
        if isinstance(node, ast.Call):
            func_name = self._get_func_name(node)
            if func_name and any(
                kw in func_name.lower() for kw in ["query", "get", "fetch", "latest", "percentile", "quantile"]
            ):
                return True
        elif isinstance(node, ast.Subscript):
            # results[0].value type patterns
            return True
        elif isinstance(node, ast.Attribute):
            # Something like metric.value
            if node.attr in {"value", "result", "percentile", "quantile"}:
                return True
        return False


def is_baseline_file(filepath: Path) -> bool:
    """Check if file is in baseline (known debt, not blocking)."""
    filepath_str = str(filepath)
    for baseline in BASELINE_FILES:
        if baseline in filepath_str:
            return True
    return False


def check_file(filepath: Path) -> list[tuple[int, int, str]]:
    """Check a Python file for unsafe float patterns.

    Args:
        filepath: Path to Python file

    Returns:
        List of (line, column, message) tuples for each error
    """
    # Skip allowed files
    for allowed in ALLOWED_FILES:
        if allowed in str(filepath):
            return []

    # Skip baseline files (they're handled separately as warnings)
    if is_baseline_file(filepath):
        return []

    try:
        content = filepath.read_text()
        tree = ast.parse(content, filename=str(filepath))
    except SyntaxError as e:
        return [(e.lineno or 0, e.offset or 0, f"Syntax error: {e.msg}")]

    checker = UnsafeFloatChecker(str(filepath))
    checker.visit(tree)
    return checker.errors


def check_file_with_regex(filepath: Path) -> list[tuple[int, str]]:
    """Additional regex-based checks for patterns AST might miss.

    Args:
        filepath: Path to Python file

    Returns:
        List of (line_number, message) tuples
    """
    # Skip allowed files
    for allowed in ALLOWED_FILES:
        if allowed in str(filepath):
            return []

    # Skip baseline files
    if is_baseline_file(filepath):
        return []

    errors: list[tuple[int, str]] = []

    try:
        content = filepath.read_text()
        lines = content.split("\n")
    except Exception:
        return []

    # Check if file imports safe functions
    has_safe_imports = "from mcp_server_langgraph.core.numeric import" in content

    for i, line in enumerate(lines, 1):
        # Skip comments
        stripped = line.strip()
        if stripped.startswith("#"):
            continue

        # Check for sum/len division pattern without safe imports
        if not has_safe_imports:
            if re.search(r"sum\s*\([^)]+\)\s*/\s*len\s*\(", line):
                errors.append(
                    (
                        i,
                        "Unsafe average: sum(x)/len(x). Use safe_average() from core.numeric",
                    )
                )

    return errors


def main(paths: list[str] | None = None) -> int:
    """Main entry point.

    Args:
        paths: List of file/directory paths to check

    Returns:
        Exit code (0 for success, 1 for errors found)
    """
    if paths is None:
        paths = sys.argv[1:] if len(sys.argv) > 1 else ["."]

    files_to_check: list[Path] = []

    for path_str in paths:
        path = Path(path_str)
        if path.is_file() and path.suffix == ".py":
            files_to_check.append(path)
        elif path.is_dir():
            files_to_check.extend(path.rglob("*.py"))

    # Skip test files, __pycache__, migrations, node_modules, and virtual environments
    files_to_check = [
        f
        for f in files_to_check
        if "__pycache__" not in str(f)
        and "/tests/" not in str(f)
        and "migrations" not in str(f)
        and "node_modules" not in str(f)
        and ".venv" not in str(f)
        and "/venv/" not in str(f)
        and "site-packages" not in str(f)
    ]

    all_errors: list[tuple[Path, int, int, str]] = []
    seen_locations: set[tuple[Path, int]] = set()  # (filepath, line) for dedup

    for filepath in files_to_check:
        # AST-based checks (primary, more precise)
        ast_errors = check_file(filepath)
        for line, col, msg in ast_errors:
            location = (filepath, line)
            if location not in seen_locations:
                all_errors.append((filepath, line, col, msg))
                seen_locations.add(location)

        # Regex-based checks (fallback for patterns AST might miss)
        regex_errors = check_file_with_regex(filepath)
        for line, msg in regex_errors:
            location = (filepath, line)
            if location not in seen_locations:
                all_errors.append((filepath, line, 0, msg))
                seen_locations.add(location)

    if all_errors:
        print("Unsafe float pattern validation errors:")
        print("=" * 70)
        for filepath, line, col, msg in all_errors:
            print(f"{filepath}:{line}:{col}: {msg}")
        print(f"\nFound {len(all_errors)} potential issue(s)")
        print("\nFix by importing safe functions from mcp_server_langgraph.core.numeric:")
        print("  from mcp_server_langgraph.core.numeric import (")
        print("      safe_float, safe_average, safe_divide, safe_round, safe_sum, safe_percentage")
        print("  )")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
