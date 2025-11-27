#!/usr/bin/env python3
"""
Pre-commit hook: Banned Import Validator

Detects and prevents usage of deprecated or problematic import patterns.

This hook prevents regressions like:
- import toml (deprecated in Python 3.11+, use tomllib/tomli)
- import imp (removed in Python 3.12+, use importlib)
- Other deprecated modules

Usage:
    As a pre-commit hook (see .pre-commit-config.yaml)
    Or standalone: python .pre-commit-hooks/check_banned_imports.py file1.py file2.py

Exit codes:
    0: No banned imports found
    1: Found banned imports
"""

import ast
import sys
from pathlib import Path

# Banned import patterns with replacement suggestions
BANNED_IMPORTS = {
    "toml": {
        "reason": "Deprecated (use built-in tomllib for Python 3.11+)",
        "fix": "import tomllib",
    },
    "tomli": {
        "reason": "Not needed (Python 3.11+ has tomllib in stdlib, project minimum is 3.11)",
        "fix": "import tomllib",
    },
    "imp": {
        "reason": "Removed in Python 3.12+ (use importlib instead)",
        "fix": "import importlib\nimportlib.import_module('module_name')",
    },
    "asyncore": {
        "reason": "Deprecated in Python 3.6, removed in Python 3.12+ (use asyncio)",
        "fix": "import asyncio",
    },
    "asynchat": {
        "reason": "Deprecated in Python 3.6, removed in Python 3.12+ (use asyncio)",
        "fix": "import asyncio",
    },
}


class BannedImportChecker(ast.NodeVisitor):
    """AST visitor to find banned import statements"""

    def __init__(self, filename: str):
        self.filename = filename
        self.violations: list[tuple[int, str, str]] = []  # (line_no, module, message)

    def visit_Import(self, node: ast.Import) -> None:
        """Check regular import statements"""
        for alias in node.names:
            module_name = alias.name.split(".")[0]  # Get root module
            if module_name in BANNED_IMPORTS:
                self._add_violation(node.lineno, module_name, f"import {alias.name}")

        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Check from...import statements"""
        if node.module:
            module_name = node.module.split(".")[0]  # Get root module
            if module_name in BANNED_IMPORTS:
                imported_names = ", ".join(alias.name for alias in node.names)
                self._add_violation(node.lineno, module_name, f"from {node.module} import {imported_names}")

        self.generic_visit(node)

    def _add_violation(self, line_no: int, module: str, import_statement: str):
        """Record a banned import violation"""
        ban_info = BANNED_IMPORTS[module]
        message = (
            f"{self.filename}:{line_no}: Banned import '{module}'\n"
            f"    Statement: {import_statement}\n"
            f"    Reason: {ban_info['reason']}\n"
            f"    Fix: {ban_info['fix']}"
        )
        self.violations.append((line_no, module, message))


def check_file(filepath: Path) -> list[str]:
    """
    Check a single Python file for banned imports

    Args:
        filepath: Path to Python file to check

    Returns:
        List of violation messages (empty if no violations)
    """
    try:
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(filepath))

        checker = BannedImportChecker(str(filepath))
        checker.visit(tree)

        return [msg for _, _, msg in checker.violations]

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
        print("Usage: check_banned_imports.py FILE [FILE ...]", file=sys.stderr)
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
        print("\n❌ Banned Import Violations Found:\n", file=sys.stderr)
        for i, violation in enumerate(all_violations, 1):
            print(f"{i}. {violation}\n", file=sys.stderr)

        print(
            f"\nFound {len(all_violations)} banned import(s). Please update to use recommended replacements.\n",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
