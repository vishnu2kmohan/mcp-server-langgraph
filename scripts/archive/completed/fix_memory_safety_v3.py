#!/usr/bin/env python3
"""
Production-grade auto-fix for pytest-xdist memory safety violations.

Robustly adds required memory safety patterns to ALL test classes:
1. @pytest.mark.xdist_group(name="classname") decorator
2. teardown_method() with gc.collect()

This version uses a hybrid approach:
- AST parsing to understand code structure and avoid syntax errors
- Line-by-line reconstruction to maintain exact formatting
- Careful handling of edge cases (docstrings, decorators, indentation)

Usage:
    python scripts/fix_memory_safety_v3.py [file1.py file2.py ...]

    # Fix all test files
    python scripts/fix_memory_safety_v3.py

    # Fix specific files
    python scripts/fix_memory_safety_v3.py tests/unit/test_tools_catalog.py
"""

import ast
import sys
from pathlib import Path
from typing import List, Optional, Tuple


class MemorySafetyAnalyzer(ast.NodeVisitor):
    """Analyze test files to identify classes needing memory safety fixes."""

    def __init__(self):
        self.test_classes: list[tuple[str, int, bool, bool]] = []  # (name, lineno, has_marker, has_teardown)
        self.has_gc_import = False
        self.last_import_line = 0
        self.current_class = None
        self.current_class_methods = set()

    def visit_Import(self, node: ast.Import) -> None:
        """Track imports."""
        self.last_import_line = max(self.last_import_line, node.lineno)
        for alias in node.names:
            if alias.name == "gc":
                self.has_gc_import = True
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Track from imports."""
        self.last_import_line = max(self.last_import_line, node.lineno)
        if node.module == "gc":
            self.has_gc_import = True
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Analyze test classes for required patterns."""
        if not node.name.startswith("Test"):
            self.generic_visit(node)
            return

        # Check for xdist_group marker
        has_marker = False
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call):
                if self._is_xdist_group_marker(decorator):
                    has_marker = True
                    break

        # Check for teardown_method
        has_teardown = False
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if item.name == "teardown_method":
                    has_teardown = self._has_gc_collect(item)
                    break

        self.test_classes.append((node.name, node.lineno, has_marker, has_teardown))
        self.generic_visit(node)

    def _is_xdist_group_marker(self, node: ast.Call) -> bool:
        """Check if decorator is xdist_group marker."""
        if isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Attribute):
                if (
                    isinstance(node.func.value.value, ast.Name)
                    and node.func.value.value.id == "pytest"
                    and node.func.value.attr == "mark"
                    and node.func.attr == "xdist_group"
                ):
                    return True
        return False

    def _has_gc_collect(self, node: ast.FunctionDef) -> bool:
        """Check if function calls gc.collect()."""
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Attribute):
                    if isinstance(child.func.value, ast.Name) and child.func.value.id == "gc" and child.func.attr == "collect":
                        return True
        return False


def fix_file(file_path: Path) -> bool:
    """Fix memory safety violations in a single file.

    Returns:
        True if changes were made, False otherwise
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()
            lines = content.splitlines(keepends=True)

        # Parse AST to analyze what needs fixing
        tree = ast.parse(content, filename=str(file_path))
        analyzer = MemorySafetyAnalyzer()
        analyzer.visit(tree)

        # Track if we made any changes
        modified = False
        classes_to_fix = [
            (name, lineno, marker, teardown)
            for name, lineno, marker, teardown in analyzer.test_classes
            if not (marker and teardown)
        ]

        if not classes_to_fix:
            return False  # No changes needed

        modified = True

        # Process each test class that needs fixes (in reverse order to maintain line numbers)
        for class_name, class_lineno, has_marker, has_teardown in reversed(classes_to_fix):
            class_line_idx = class_lineno - 1  # Convert to 0-based index

            # Add xdist_group marker if missing
            if not has_marker:
                # Get indentation from class line
                class_line = lines[class_line_idx]
                indent = len(class_line) - len(class_line.lstrip())
                marker_line = " " * indent + f'@pytest.mark.xdist_group(name="{class_name.lower()}")\n'
                lines.insert(class_line_idx, marker_line)
                class_line_idx += 1  # Adjust index after insertion

            # Add teardown_method if missing
            if not has_teardown:
                # Find insertion point (after class definition line and docstring)
                insert_idx = class_line_idx + 1

                # Skip over class docstring if present
                while insert_idx < len(lines):
                    line = lines[insert_idx].strip()

                    # Empty line - skip
                    if not line:
                        insert_idx += 1
                        continue

                    # Docstring start
                    if line.startswith('"""') or line.startswith("'''"):
                        quote = '"""' if line.startswith('"""') else "'''"
                        # Single-line docstring
                        if line.count(quote) >= 2:
                            insert_idx += 1
                            break
                        # Multi-line docstring - find end
                        insert_idx += 1
                        while insert_idx < len(lines):
                            if quote in lines[insert_idx]:
                                insert_idx += 1
                                break
                            insert_idx += 1
                        break
                    # No docstring, insert here
                    break

                # Get class body indentation (class indent + 4 spaces)
                class_line = lines[class_line_idx]
                class_indent = len(class_line) - len(class_line.lstrip())
                method_indent = " " * (class_indent + 4)

                # Create teardown_method
                teardown_lines = [
                    "\n",
                    method_indent + "def teardown_method(self) -> None:\n",
                    method_indent + '    """Force GC to prevent mock accumulation in xdist workers"""\n',
                    method_indent + "    gc.collect()\n",
                    "\n",
                ]

                # Insert teardown method
                for line in reversed(teardown_lines):
                    lines.insert(insert_idx, line)

        # NOTE: gc import is handled by scripts/add_gc_import.py
        # This script only handles xdist markers and teardown methods

        # Write back (we already set modified = True if there were classes to fix)
        if modified:
            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
            return True

        return False

    except SyntaxError as e:
        print(f"⚠️  Syntax error in {file_path}: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"⚠️  Error processing {file_path}: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return False


def find_test_files(base_dir: str = "tests") -> list[Path]:
    """Find all test files under the base directory."""
    base_path = Path(base_dir)
    if not base_path.exists():
        return []
    return sorted(base_path.rglob("test_*.py"))


def main() -> int:
    """Main entry point."""
    # Determine which files to fix
    if len(sys.argv) > 1:
        # Specific files mode
        files_to_fix = [Path(f) for f in sys.argv[1:] if f.endswith(".py")]
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
            try:
                repo_root = Path(__file__).parent.parent
                rel_path = file_path.relative_to(repo_root)
            except (ValueError, NameError):
                rel_path = file_path
            print(f"✓ Fixed {rel_path}")

    print(f"\n✅ Fixed {fixed_count} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
