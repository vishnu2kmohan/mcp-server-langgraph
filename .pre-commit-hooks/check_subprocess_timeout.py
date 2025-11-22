#!/usr/bin/env python3
"""
Pre-commit hook: Subprocess Timeout Enforcer

Ensures all subprocess.run() calls include a timeout parameter to prevent test hangs.

This hook prevents the regression of https://github.com/vishnu2kmohan/mcp-server-langgraph/issues/XXX
where 119 subprocess.run() calls lacked timeouts, creating potential for indefinite test hangs.

Usage:
    As a pre-commit hook (see .pre-commit-config.yaml)
    Or standalone: python .pre-commit-hooks/check_subprocess_timeout.py file1.py file2.py

Exit codes:
    0: All subprocess.run() calls have timeout parameter
    1: Found subprocess.run() calls without timeout parameter
"""

import ast
import sys
from pathlib import Path


class SubprocessTimeoutChecker(ast.NodeVisitor):
    """AST visitor to find subprocess.run() calls without timeout parameter"""

    def __init__(self, filename: str):
        self.filename = filename
        self.violations: list[tuple[int, str]] = []

    def visit_Call(self, node: ast.Call) -> None:
        """Check if this is a subprocess.run() call without timeout"""
        # Check if this is a subprocess.run() call
        is_subprocess_run = False

        # Pattern 1: subprocess.run(...)
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == "run" and isinstance(node.func.value, ast.Name) and node.func.value.id == "subprocess":
                is_subprocess_run = True

        if is_subprocess_run:
            # Check if timeout parameter is present
            has_timeout = False

            # Check keyword arguments
            for keyword in node.keywords:
                if keyword.arg == "timeout":
                    has_timeout = True
                    break

            if not has_timeout:
                # Record violation
                line_no = node.lineno
                # Try to get some context (first few tokens)
                violation_msg = f"{self.filename}:{line_no}: subprocess.run() call without timeout parameter"
                self.violations.append((line_no, violation_msg))

        # Continue visiting child nodes
        self.generic_visit(node)


def check_file(filepath: Path) -> list[str]:
    """
    Check a single Python file for subprocess.run() calls without timeout

    Args:
        filepath: Path to Python file to check

    Returns:
        List of violation messages (empty if no violations)
    """
    try:
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(filepath))

        checker = SubprocessTimeoutChecker(str(filepath))
        checker.visit(tree)

        return [msg for _, msg in checker.violations]

    except SyntaxError:
        # Skip files with syntax errors (they'll be caught by other hooks)
        return []
    except Exception as e:
        # Log but don't fail on unexpected errors
        print(f"Warning: Failed to parse {filepath}: {e}", file=sys.stderr)
        return []


def main(argv: list[str] = None) -> int:
    """
    Main entry point for pre-commit hook

    Args:
        argv: Command line arguments (file paths to check)

    Returns:
        0 if all checks pass, 1 if violations found
    """
    argv = argv or sys.argv[1:]

    if not argv:
        print("Usage: check_subprocess_timeout.py FILE [FILE ...]", file=sys.stderr)
        return 1

    all_violations = []

    for filepath_str in argv:
        filepath = Path(filepath_str)

        # Only check Python files
        if filepath.suffix != ".py":
            continue

        # Skip if file doesn't exist
        if not filepath.exists():
            continue

        violations = check_file(filepath)
        all_violations.extend(violations)

    if all_violations:
        print("\n❌ Subprocess Timeout Violations Found:\n", file=sys.stderr)
        for violation in all_violations:
            print(f"  {violation}", file=sys.stderr)

        print(
            "\n"
            "All subprocess.run() calls must include a timeout parameter to prevent test hangs.\n"
            "\n"
            "Fix: Add timeout parameter (minimum 30 seconds for CLI commands):\n"
            "  subprocess.run([...], timeout=60)  # 60 seconds\n"
            "\n"
            "Or use the safe helper:\n"
            "  from tests.helpers.subprocess_helpers import run_cli_tool\n"
            "  run_cli_tool(['command', 'args'])\n"
            "\n"
            f"Found {len(all_violations)} violation(s). Please fix before committing.\n",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
