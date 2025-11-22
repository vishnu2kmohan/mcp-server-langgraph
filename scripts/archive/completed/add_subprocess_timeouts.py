#!/usr/bin/env python3
"""Add timeout parameters to subprocess.run() calls that are missing them.

This script automatically adds timeout=60 to all subprocess.run() calls in test files
that don't already have a timeout parameter.

Related: OpenAI Codex Finding #6 - Subprocess test safeguards
"""

import ast
import sys
from pathlib import Path


class SubprocessTimeoutAdder(ast.NodeTransformer):
    """AST transformer to add timeout parameter to subprocess.run() calls."""

    def __init__(self):
        self.modifications = []
        self.current_file = None

    def visit_Call(self, node):
        # Check if this is a subprocess.run() call
        is_subprocess_run = False

        if isinstance(node.func, ast.Attribute):
            if node.func.attr == "run" and isinstance(node.func.value, ast.Name) and node.func.value.id == "subprocess":
                is_subprocess_run = True

        if is_subprocess_run:
            # Check if timeout keyword already exists
            has_timeout = any(kw.arg == "timeout" for kw in node.keywords if kw.arg)

            if not has_timeout:
                # Add timeout=60 keyword argument
                timeout_kwarg = ast.keyword(arg="timeout", value=ast.Constant(value=60))
                node.keywords.append(timeout_kwarg)
                self.modifications.append(node.lineno)

        self.generic_visit(node)
        return node


def add_timeouts_to_file(file_path: Path) -> tuple[bool, list[int]]:
    """Add timeout parameters to subprocess.run() calls in a file.

    Returns:
        Tuple of (modified, line_numbers)
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            source = f.read()

        tree = ast.parse(source, filename=str(file_path))
    except (SyntaxError, UnicodeDecodeError):
        return False, []

    transformer = SubprocessTimeoutAdder()
    transformer.current_file = file_path
    new_tree = transformer.visit(tree)

    if transformer.modifications:
        # Unparse and write back
        import astor  # type: ignore

        try:
            new_source = astor.to_source(new_tree)
        except Exception:
            # Fallback: if astor fails, try ast.unparse (Python 3.9+)
            new_source = ast.unparse(new_tree)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_source)

        return True, transformer.modifications

    return False, []


def main():
    """Process all test files and add missing timeout parameters."""
    tests_dir = Path(__file__).parent.parent / "tests"
    test_files = list(tests_dir.rglob("test_*.py"))

    modified_files = []
    total_modifications = 0

    print(f"Scanning {len(test_files)} test files...")

    for test_file in test_files:
        modified, line_numbers = add_timeouts_to_file(test_file)

        if modified:
            modified_files.append(str(test_file.relative_to(tests_dir.parent)))
            total_modifications += len(line_numbers)
            print(f"✓ {test_file.relative_to(tests_dir)}: Added timeout to {len(line_numbers)} calls")

    print("\nSummary:")
    print(f"  Modified files: {len(modified_files)}")
    print(f"  Total timeout parameters added: {total_modifications}")

    if modified_files:
        print("\nModified files:")
        for file in modified_files:
            print(f"  - {file}")

    return 0 if total_modifications == 0 else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ImportError as e:
        print(f"ERROR: Required module not available: {e}")
        print("Install with: pip install astor")
        sys.exit(2)
