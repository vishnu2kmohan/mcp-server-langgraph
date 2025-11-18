#!/usr/bin/env python3
"""Fix subprocess.run() calls to include timeout parameter using AST-based transformation.

This script uses libcst for proper code transformation that preserves formatting.
"""

import sys
from pathlib import Path
from typing import List


try:
    import libcst as cst
except ImportError:
    print("Error: libcst not installed. Installing...")
    import subprocess

    subprocess.run([sys.executable, "-m", "pip", "install", "libcst"], check=True, timeout=60)
    import libcst as cst


class SubprocessTimeoutTransformer(cst.CSTTransformer):
    """Transformer that adds timeout=60 to subprocess.run() calls without timeout."""

    def __init__(self):
        self.modifications = 0

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:
        """Add timeout parameter to subprocess.run() calls if missing."""
        # Check if this is a subprocess.run() call
        if isinstance(updated_node.func, cst.Attribute):
            if (
                updated_node.func.attr.value == "run"
                and isinstance(updated_node.func.value, cst.Name)
                and updated_node.func.value.value == "subprocess"
            ):
                # Check if timeout already exists
                has_timeout = any(arg.keyword and arg.keyword.value == "timeout" for arg in updated_node.args)

                if not has_timeout:
                    # Add timeout=60 as the last keyword argument
                    new_arg = cst.Arg(
                        keyword=cst.Name("timeout"),
                        value=cst.Integer("60"),
                        equal=cst.AssignEqual(
                            whitespace_before=cst.SimpleWhitespace(""),
                            whitespace_after=cst.SimpleWhitespace(""),
                        ),
                    )

                    # Add comma and proper spacing
                    new_args = list(updated_node.args) + [new_arg]
                    updated_node = updated_node.with_changes(args=new_args)
                    self.modifications += 1

        return updated_node


def fix_file(file_path: Path) -> int:
    """Fix subprocess.run() calls in a single file.

    Returns:
        Number of modifications made
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            source_code = f.read()
    except (OSError, UnicodeDecodeError) as e:
        print(f"Warning: Could not read {file_path}: {e}")
        return 0

    try:
        # Parse the source code into a CST
        tree = cst.parse_module(source_code)
    except cst.ParserSyntaxError as e:
        print(f"Warning: Could not parse {file_path}: {e}")
        return 0

    # Transform the tree
    transformer = SubprocessTimeoutTransformer()
    modified_tree = tree.visit(transformer)

    if transformer.modifications > 0:
        # Write back the modified code
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(modified_tree.code)

    return transformer.modifications


def main():
    """Find and fix all test files with subprocess.run() calls."""
    repo_root = Path(__file__).parent.parent
    tests_dir = repo_root / "tests"

    # Find all test files
    test_files: list[Path] = []
    for pattern in ["test_*.py", "*_test.py"]:
        test_files.extend(tests_dir.rglob(pattern))

    print(f"Scanning {len(test_files)} test file(s)...")

    total_files_modified = 0
    total_modifications = 0

    for test_file in sorted(test_files):
        mods = fix_file(test_file)
        if mods > 0:
            total_files_modified += 1
            total_modifications += mods
            print(f"Fixed {test_file.relative_to(repo_root)}: {mods} call(s)")

    print(f"\n=== SUMMARY ===")
    print(f"Modified {total_files_modified} file(s)")
    print(f"Fixed {total_modifications} subprocess.run() call(s)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
