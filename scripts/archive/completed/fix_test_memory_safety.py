#!/usr/bin/env python3
"""
Auto-fix script for pytest-xdist memory safety violations.

This script automatically adds the required memory safety patterns to test classes:
1. @pytest.mark.xdist_group(name="classname") decorator
2. teardown_method() with gc.collect()

Usage:
    python scripts/fix_test_memory_safety.py [file1.py file2.py ...]

    # Fix all test files
    python scripts/fix_test_memory_safety.py

    # Fix specific files
    python scripts/fix_test_memory_safety.py tests/unit/test_tools_catalog.py

Background:
When running tests with pytest-xdist, AsyncMock/MagicMock objects create circular
references that prevent garbage collection, leading to memory explosion (observed:
217GB VIRT, 42GB RES). This script automatically applies the 3-part pattern:
- Grouping related tests in same worker (xdist_group)
- Forcing GC after each test (teardown_method + gc.collect)

See: tests/MEMORY_SAFETY_GUIDELINES.md for complete documentation
"""

import ast
import sys
from pathlib import Path
from typing import List, Optional, Set


class MemorySafetyFixer(ast.NodeVisitor):
    """AST visitor to fix memory safety pattern violations."""

    def __init__(self, file_path: str, content: str):
        self.file_path = file_path
        self.content = content
        self.lines = content.splitlines(keepends=True)
        self.changes: list[tuple] = []  # (line_number, action, data)
        self.current_class: str | None = None
        self.current_class_line: int | None = None
        self.current_class_methods: set[str] = set()
        self.class_uses_mocks = False
        self.has_gc_import = False

    def visit_Import(self, node: ast.Import) -> None:
        """Check for gc import."""
        for alias in node.names:
            if alias.name == "gc":
                self.has_gc_import = True
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Check for gc import in from statements."""
        if node.module == "gc":
            self.has_gc_import = True
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definitions to check for test classes."""
        # Reset state for new class
        self.current_class = node.name
        self.current_class_line = node.lineno
        self.current_class_methods = set()
        self.class_uses_mocks = False

        # Check if this is a test class
        if not node.name.startswith("Test"):
            self.generic_visit(node)
            return

        # Check decorators
        has_xdist_group = False
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Attribute):
                    if (
                        isinstance(decorator.func.value, ast.Attribute)
                        and isinstance(decorator.func.value.value, ast.Name)
                        and decorator.func.value.value.id == "pytest"
                        and decorator.func.value.attr == "mark"
                        and decorator.func.attr == "xdist_group"
                    ):
                        has_xdist_group = True

        # Visit class body to check for mock usage and methods
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.current_class_methods.add(item.name)
                # Check if method uses AsyncMock or MagicMock
                self._check_for_mock_usage(item)

            # Also check for mock usage in class-level assignments
            elif isinstance(item, (ast.Assign, ast.AnnAssign)):
                self._check_node_for_mocks(item)

        # Fix ALL test classes (not just those using mocks)
        # This matches the requirement from validate_test_isolation.py

        # Add xdist_group decorator if missing
        if not has_xdist_group:
            self.changes.append(
                (
                    self.current_class_line,
                    "add_xdist_group",
                    self.current_class.lower(),
                )
            )

        # Add teardown_method if missing
        if "teardown_method" not in self.current_class_methods:
            # Find the indentation of the class body
            first_method_line = None
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    first_method_line = item.lineno
                    break

            if first_method_line:
                # Get indentation from first method
                line = self.lines[first_method_line - 1]
                indent = len(line) - len(line.lstrip())
            else:
                # Default to 4 spaces
                indent = 4

            self.changes.append((self.current_class_line + 1, "add_teardown", indent))

        self.generic_visit(node)

    def _check_for_mock_usage(self, node: ast.FunctionDef) -> None:
        """Check if a function uses AsyncMock or MagicMock."""
        for child in ast.walk(node):
            if isinstance(child, ast.Name):
                if child.id in ("AsyncMock", "MagicMock"):
                    self.class_uses_mocks = True
            elif isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    if child.func.id in ("AsyncMock", "MagicMock"):
                        self.class_uses_mocks = True

    def _check_node_for_mocks(self, node: ast.AST) -> None:
        """Check any AST node for AsyncMock/MagicMock usage."""
        for child in ast.walk(node):
            if isinstance(child, ast.Name):
                if child.id in ("AsyncMock", "MagicMock"):
                    self.class_uses_mocks = True
            elif isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    if child.func.id in ("AsyncMock", "MagicMock"):
                        self.class_uses_mocks = True


def fix_file(file_path: str) -> bool:
    """Fix a single file for memory safety violations.

    Returns:
        True if changes were made, False otherwise
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content, filename=file_path)
        fixer = MemorySafetyFixer(file_path, content)
        fixer.visit(tree)

        if not fixer.changes:
            return False

        # Apply changes in reverse order (so line numbers stay valid)
        lines = content.splitlines(keepends=True)
        changes_by_line = {}
        for line_no, action, data in fixer.changes:
            if line_no not in changes_by_line:
                changes_by_line[line_no] = []
            changes_by_line[line_no].append((action, data))

        # Process changes
        new_lines = []
        i = 0
        while i < len(lines):
            line_no = i + 1  # 1-indexed

            # Check if we need to add decorators before this line
            if line_no in changes_by_line:
                for action, data in changes_by_line[line_no]:
                    if action == "add_xdist_group":
                        # Get indentation from current line
                        current_line = lines[i]
                        indent = len(current_line) - len(current_line.lstrip())
                        new_lines.append(" " * indent + f'@pytest.mark.xdist_group(name="{data}")\n')
                    elif action == "add_teardown":
                        # Insert teardown_method after class definition
                        indent_str = " " * data
                        new_lines.append("\n")
                        new_lines.append(indent_str + "def teardown_method(self) -> None:\n")
                        new_lines.append(indent_str + '    """Force GC to prevent mock accumulation in xdist workers"""\n')
                        new_lines.append(indent_str + "    gc.collect()\n")
                        new_lines.append("\n")

            new_lines.append(lines[i])
            i += 1

        # Add gc import if needed and not present
        if fixer.changes and not fixer.has_gc_import:
            # Find the last import line
            last_import_line = 0
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    if hasattr(node, "lineno"):
                        last_import_line = max(last_import_line, node.lineno)

            if last_import_line > 0:
                # Insert gc import after last import
                new_lines.insert(last_import_line, "import gc\n")
            else:
                # Insert at beginning
                new_lines.insert(0, "import gc\n")

        # Write back
        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

        return True

    except SyntaxError as e:
        print(f"Warning: Syntax error in {file_path}: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Warning: Error processing {file_path}: {e}", file=sys.stderr)
        return False


def find_test_files(base_dir: str = "tests") -> list[str]:
    """Find all test files under the base directory."""
    test_files = []
    base_path = Path(base_dir)

    if not base_path.exists():
        return []

    for path in base_path.rglob("test_*.py"):
        test_files.append(str(path))

    return sorted(test_files)


def main() -> int:
    """Main entry point."""
    # Determine which files to fix
    if len(sys.argv) > 1:
        # Specific files mode
        files_to_fix = [f for f in sys.argv[1:] if f.endswith(".py") and "test_" in f]
    else:
        # Standalone mode: fix all test files
        repo_root = Path(__file__).parent.parent
        files_to_fix = find_test_files(str(repo_root / "tests"))

    if not files_to_fix:
        print("No test files to fix.")
        return 0

    # Fix all files
    fixed_count = 0
    for file_path in files_to_fix:
        if fix_file(file_path):
            fixed_count += 1
            print(f"✓ Fixed {file_path}")

    print(f"\n✅ Fixed {fixed_count} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
