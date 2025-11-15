#!/usr/bin/env python3
"""
Production-grade unified auto-fix for pytest-xdist memory safety violations.

This script uses AST parsing to correctly:
1. Add 'import gc' at module level (not inside methods)
2. Add @pytest.mark.xdist_group markers to test classes
3. Add teardown_method() with gc.collect() to test classes

Usage:
    python scripts/fix_memory_safety_unified.py [file1.py file2.py ...]
"""

import ast
import sys
from pathlib import Path
from typing import List, Set, Tuple


def fix_file(file_path: Path) -> bool:
    """Fix memory safety violations in a single file.

    Returns:
        True if changes were made, False otherwise
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Parse AST to analyze structure
        try:
            tree = ast.parse(content, filename=str(file_path))
        except SyntaxError as e:
            print(f"⚠️  Syntax error in {file_path}: {e}", file=sys.stderr)
            return False

        # Analyze what needs fixing
        has_gc_import = False
        last_import_node = None
        test_classes = []  # (node, name, has_marker, has_teardown)

        for node in ast.iter_child_nodes(tree):
            # Check for gc import at module level
            if isinstance(node, ast.Import):
                last_import_node = node
                for alias in node.names:
                    if alias.name == "gc":
                        has_gc_import = True
            elif isinstance(node, ast.ImportFrom):
                last_import_node = node
                if node.module == "gc":
                    has_gc_import = True

            # Check for test classes
            elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
                has_marker = any(
                    isinstance(dec, ast.Call)
                    and isinstance(dec.func, ast.Attribute)
                    and isinstance(dec.func.value, ast.Attribute)
                    and isinstance(dec.func.value.value, ast.Name)
                    and dec.func.value.value.id == "pytest"
                    and dec.func.value.attr == "mark"
                    and dec.func.attr == "xdist_group"
                    for dec in node.decorator_list
                )

                has_teardown = False
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == "teardown_method":
                        # Check if it has gc.collect()
                        for child in ast.walk(item):
                            if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
                                if (
                                    isinstance(child.func.value, ast.Name)
                                    and child.func.value.id == "gc"
                                    and child.func.attr == "collect"
                                ):
                                    has_teardown = True
                                    break
                        break

                test_classes.append((node, node.name, has_marker, has_teardown))

        # Check if any fixes needed
        classes_need_fixing = [(n, name, m, t) for n, name, m, t in test_classes if not (m and t)]
        if not classes_need_fixing and has_gc_import:
            return False  # Nothing to fix

        # Now modify the source code line by line
        lines = content.splitlines(keepends=True)
        if not lines:
            return False

        # Step 1: Add gc import if needed (do this first, at the top)
        if not has_gc_import and (classes_need_fixing or not test_classes):
            if last_import_node:
                # Insert after last import (line numbers are 1-indexed)
                insert_line = last_import_node.end_lineno
                lines.insert(insert_line, "import gc\n")
            else:
                # No imports found, add after module docstring
                insert_idx = 0
                if lines and lines[0].strip().startswith(('"""', "'''")):
                    quote = '"""' if '"""' in lines[0] else "'''"
                    if lines[0].count(quote) >= 2:
                        insert_idx = 1
                    else:
                        for i in range(1, len(lines)):
                            if quote in lines[i]:
                                insert_idx = i + 1
                                break
                lines.insert(insert_idx, "import gc\n")

        # Step 2: Add markers and teardown methods (work backwards to preserve line numbers)
        for class_node, class_name, has_marker, has_teardown in reversed(classes_need_fixing):
            class_line_idx = class_node.lineno - 1  # Convert to 0-indexed

            # Adjust for gc import we may have added
            if not has_gc_import:
                if last_import_node and class_node.lineno > last_import_node.end_lineno:
                    class_line_idx += 1
                elif not last_import_node:
                    class_line_idx += 1

            # Add xdist_group marker if missing
            if not has_marker:
                indent = len(lines[class_line_idx]) - len(lines[class_line_idx].lstrip())
                marker_line = " " * indent + f'@pytest.mark.xdist_group(name="{class_name.lower()}")\n'
                lines.insert(class_line_idx, marker_line)
                class_line_idx += 1  # Adjust for insertion

            # Add teardown_method if missing
            if not has_teardown:
                # Find insertion point after class line and docstring
                insert_idx = class_line_idx + 1

                # Skip empty lines and class docstring
                while insert_idx < len(lines):
                    line = lines[insert_idx].strip()
                    if not line:
                        insert_idx += 1
                        continue
                    if line.startswith(('"""', "'''")):
                        quote = '"""' if line.startswith('"""') else "'''"
                        if line.count(quote) >= 2:
                            insert_idx += 1
                            break
                        else:
                            insert_idx += 1
                            while insert_idx < len(lines):
                                if quote in lines[insert_idx]:
                                    insert_idx += 1
                                    break
                                insert_idx += 1
                            break
                    else:
                        break

                # Get class indentation
                class_indent = len(lines[class_line_idx]) - len(lines[class_line_idx].lstrip())
                method_indent = " " * (class_indent + 4)

                # Insert teardown method
                teardown_lines = [
                    "\n",
                    method_indent + "def teardown_method(self) -> None:\n",
                    method_indent + '    """Force GC to prevent mock accumulation in xdist workers"""\n',
                    method_indent + "    gc.collect()\n",
                    "\n",
                ]

                for line in reversed(teardown_lines):
                    lines.insert(insert_idx, line)

        # Write back
        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        return True

    except Exception as e:
        print(f"⚠️  Error processing {file_path}: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return False


def find_test_files(base_dir: str = "tests") -> List[Path]:
    """Find all test files under the base directory."""
    base_path = Path(base_dir)
    if not base_path.exists():
        return []
    return sorted(base_path.rglob("test_*.py"))


def main() -> int:
    """Main entry point."""
    # Determine which files to fix
    if len(sys.argv) > 1:
        files_to_fix = [Path(f) for f in sys.argv[1:] if f.endswith(".py")]
    else:
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
