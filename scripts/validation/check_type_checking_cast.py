#!/usr/bin/env python3
"""
Pre-commit validation script for TYPE_CHECKING cast() usage.

Detects cases where cast() uses types that are only imported under
TYPE_CHECKING blocks without using string forward references.

Problem:
    from typing import TYPE_CHECKING, cast
    if TYPE_CHECKING:
        from module import SomeType

    # This fails at runtime because SomeType is not defined:
    cast(SomeType, value)  # NameError!

    # This works because string references are evaluated lazily:
    cast("SomeType", value)  # OK

Usage:
    python scripts/validation/check_type_checking_cast.py [path]

    # In pre-commit:
    - repo: local
      hooks:
        - id: check-type-checking-cast
          name: Check TYPE_CHECKING cast usage
          entry: python scripts/validation/check_type_checking_cast.py
          language: python
          types: [python]
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path


class TypeCheckingCastChecker(ast.NodeVisitor):
    """AST visitor to detect unsafe cast() with TYPE_CHECKING imports."""

    def __init__(self, filepath: str) -> None:
        self.filepath = filepath
        self.type_checking_imports: set[str] = set()
        self.errors: list[tuple[int, int, str]] = []
        self._in_type_checking = False

    def visit_If(self, node: ast.If) -> None:
        """Track if we're inside a TYPE_CHECKING block."""
        # Check if this is `if TYPE_CHECKING:`
        if isinstance(node.test, ast.Name) and node.test.id == "TYPE_CHECKING":
            self._in_type_checking = True
            self.generic_visit(node)
            self._in_type_checking = False
        else:
            self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        """Track imports inside TYPE_CHECKING blocks."""
        if self._in_type_checking:
            for alias in node.names:
                name = alias.asname if alias.asname else alias.name
                # Handle dotted imports (module.submodule)
                self.type_checking_imports.add(name.split(".")[0])
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Track from imports inside TYPE_CHECKING blocks."""
        if self._in_type_checking:
            for alias in node.names:
                name = alias.asname if alias.asname else alias.name
                self.type_checking_imports.add(name)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Check cast() calls for unsafe type references."""
        # Check if this is a cast() call
        is_cast = False
        if isinstance(node.func, ast.Name) and node.func.id == "cast":
            is_cast = True
        elif isinstance(node.func, ast.Attribute) and node.func.attr == "cast":
            is_cast = True

        if is_cast and node.args:
            first_arg = node.args[0]
            self._check_type_arg(first_arg, node.lineno, node.col_offset)

        self.generic_visit(node)

    def _check_type_arg(self, node: ast.expr, lineno: int, col_offset: int) -> None:
        """Check if a type argument uses TYPE_CHECKING-only imports unsafely."""
        # String literals are safe (forward references)
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return

        # Collect all names used in the type expression
        names = self._extract_names(node)

        # Check if any name is from TYPE_CHECKING imports
        for name in names:
            if name in self.type_checking_imports:
                self.errors.append((
                    lineno,
                    col_offset,
                    f"cast() uses '{name}' which is only imported under TYPE_CHECKING. "
                    f"Use string forward reference: cast(\"{name}[...]\", value)",
                ))
                break

    def _extract_names(self, node: ast.expr) -> set[str]:
        """Extract all Name references from a type expression."""
        names: set[str] = set()

        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Subscript):
            names.update(self._extract_names(node.value))
            names.update(self._extract_names(node.slice))
        elif isinstance(node, ast.Attribute):
            # For module.Type, we care about the module name
            if isinstance(node.value, ast.Name):
                names.add(node.value.id)
        elif isinstance(node, ast.Tuple):
            for elt in node.elts:
                names.update(self._extract_names(elt))
        elif isinstance(node, ast.BinOp):
            # Union types: X | Y
            names.update(self._extract_names(node.left))
            names.update(self._extract_names(node.right))

        return names


def check_file(filepath: Path) -> list[tuple[int, int, str]]:
    """Check a Python file for unsafe cast() usage.

    Args:
        filepath: Path to Python file

    Returns:
        List of (line, column, message) tuples for each error
    """
    try:
        content = filepath.read_text()
        tree = ast.parse(content, filename=str(filepath))
    except SyntaxError as e:
        return [(e.lineno or 0, e.offset or 0, f"Syntax error: {e.msg}")]

    checker = TypeCheckingCastChecker(str(filepath))
    checker.visit(tree)
    return checker.errors


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

    # Skip test files and __pycache__
    files_to_check = [
        f for f in files_to_check
        if "__pycache__" not in str(f)
    ]

    all_errors: list[tuple[Path, int, int, str]] = []

    for filepath in files_to_check:
        errors = check_file(filepath)
        for line, col, msg in errors:
            all_errors.append((filepath, line, col, msg))

    if all_errors:
        print("TYPE_CHECKING cast() validation errors:")
        print("=" * 60)
        for filepath, line, col, msg in all_errors:
            print(f"{filepath}:{line}:{col}: {msg}")
        print(f"\nFound {len(all_errors)} error(s)")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
