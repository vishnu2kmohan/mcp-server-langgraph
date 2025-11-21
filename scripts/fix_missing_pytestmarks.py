#!/usr/bin/env python3
"""
Script to automatically add missing pytestmark declarations to test files.

This script:
1. Identifies test files missing pytestmark declarations
2. Categorizes them based on file path and content analysis
3. Adds appropriate pytestmark declarations at module level
4. Adds memory safety patterns for files using AsyncMock/MagicMock
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict


class TestFileAnalyzer:
    """Analyzes test files to determine appropriate pytest markers and required patterns."""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.content = file_path.read_text()
        self.lines = self.content.splitlines()

    def get_marker_from_path(self) -> str:
        """Determine marker based on file path."""
        path_str = str(self.file_path)

        # Path-based categorization (ordered by specificity)
        if "/integration/" in path_str:
            return "integration"
        elif "/e2e/" in path_str:
            return "e2e"
        elif "/unit/" in path_str:
            return "unit"
        elif "/api/" in path_str and "/integration/api/" not in path_str:
            return "api"
        elif "/smoke/" in path_str:
            return "smoke"
        elif "/meta/" in path_str:
            return "meta"
        elif "/security/" in path_str and "/integration/security/" not in path_str:
            return "security"
        elif "/property/" in path_str:
            return "property"
        elif "/regression/" in path_str:
            return "regression"
        elif "/kubernetes/" in path_str or "/deployment/" in path_str:
            return "deployment"
        elif "/resilience/" in path_str:
            return "unit"
        elif "/monitoring/" in path_str:
            return "unit"
        elif "/infrastructure/" in path_str:
            return "infrastructure"
        elif "/compliance/" in path_str:
            return "integration"
        elif "/cli/" in path_str:
            return "unit"
        elif "/builder/" in path_str:
            return "unit"
        elif "/core/" in path_str:
            return "unit"
        elif "/llm/" in path_str:
            return "unit"
        elif "/tools/" in path_str:
            return "unit"
        elif "/scripts/" in path_str:
            return "meta"
        elif "/validation_lib/" in path_str:
            return "unit"

        # Default to unit
        return "unit"

    def uses_mocks(self) -> bool:
        """Check if file uses AsyncMock or MagicMock."""
        return "AsyncMock" in self.content or "MagicMock" in self.content

    def has_pytestmark(self) -> bool:
        """Check if file already has pytestmark declaration."""
        # Check for both single and list formats
        return bool(re.search(r"^pytestmark\s*=", self.content, re.MULTILINE))

    def has_test_classes(self) -> list[str]:
        """Find all test class names in the file."""
        try:
            tree = ast.parse(self.content)
            classes = []
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    if node.name.startswith("Test"):
                        classes.append(node.name)
            return classes
        except SyntaxError:
            return re.findall(r"class (Test\w+)", self.content)

    def has_xdist_group(self) -> bool:
        """Check if file already has xdist_group decorator."""
        return "@pytest.mark.xdist_group" in self.content

    def has_teardown_method(self) -> bool:
        """Check if file already has teardown_method."""
        return "def teardown_method" in self.content

    def get_module_level_insert_position(self) -> int:
        """
        Find the position to insert module-level code (after imports, before any code).

        Returns line number (1-indexed) where pytestmark should be inserted.
        """
        try:
            tree = ast.parse(self.content)
        except SyntaxError:
            # Fallback to simple heuristic if parsing fails
            return self._get_insert_position_fallback()

        # Find last MODULE-LEVEL import only (not imports inside functions/classes)
        # Module-level nodes are direct children of the Module node
        last_import_line = 0
        for node in tree.body:  # Only iterate over module-level nodes
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if hasattr(node, "lineno"):
                    last_import_line = max(last_import_line, node.lineno)

        # Return position after last import (1-indexed from AST)
        return last_import_line

    def _get_insert_position_fallback(self) -> int:
        """Fallback method using regex when AST parsing fails."""
        last_import = 0
        for i, line in enumerate(self.lines, 1):
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")) and not stripped.startswith("#"):
                last_import = i
        return last_import


class TestFileFixer:
    """Fixes test files by adding pytestmark and memory safety patterns."""

    def __init__(self, file_path: Path, marker: str, needs_memory_safety: bool):
        self.file_path = file_path
        self.marker = marker
        self.needs_memory_safety = needs_memory_safety
        self.analyzer = TestFileAnalyzer(file_path)

    def add_pytestmark(self) -> str:
        """Add pytestmark declaration to the file at module level."""
        lines = self.analyzer.lines.copy()
        insert_line = self.analyzer.get_module_level_insert_position()

        # Prepare pytestmark line
        pytestmark_line = f"pytestmark = pytest.mark.{self.marker}"

        # Insert after the last import line with proper spacing
        # insert_line is 1-indexed, convert to 0-indexed for list insertion
        insert_pos = insert_line

        # Check if we need blank lines
        needs_blank_before = insert_pos > 0 and lines[insert_pos - 1].strip() != ""
        needs_blank_after = insert_pos < len(lines) and lines[insert_pos].strip() != ""

        # Build lines to insert
        insert_lines = []
        if needs_blank_before:
            insert_lines.append("")
        insert_lines.append(pytestmark_line)
        if needs_blank_after:
            insert_lines.append("")

        # Insert at position
        for i, line in enumerate(insert_lines):
            lines.insert(insert_pos + i, line)

        return "\n".join(lines)

    def add_memory_safety_pattern(self, content: str) -> str:
        """Add memory safety pattern to test classes using AsyncMock/MagicMock."""
        test_classes = self.analyzer.has_test_classes()

        if not test_classes or self.analyzer.has_xdist_group():
            return content

        lines = content.splitlines()

        # Track if we need to add gc import
        needs_gc_import = "import gc" not in content

        # Find and modify test classes
        modified_lines = []
        i = 0

        while i < len(lines):
            line = lines[i]

            # Check if this line defines a test class
            found_class = False
            for class_name in test_classes:
                if f"class {class_name}" in line:
                    # Add xdist_group decorator
                    indent = len(line) - len(line.lstrip())
                    group_name = self.marker + "_tests"
                    decorator = f'{" " * indent}@pytest.mark.xdist_group(name="{group_name}")'
                    modified_lines.append(decorator)
                    modified_lines.append(line)

                    # Add teardown_method if not present
                    if not self.analyzer.has_teardown_method():
                        # Skip to class body
                        i += 1
                        while i < len(lines):
                            next_line = lines[i]

                            # Skip docstring
                            if '"""' in next_line or "'''" in next_line:
                                modified_lines.append(next_line)
                                i += 1
                                continue

                            # Found first method or non-empty line in class body
                            if next_line.strip() and not next_line.strip().startswith("#"):
                                # Insert teardown_method
                                class_indent = indent + 4
                                modified_lines.append(f'{" " * class_indent}def teardown_method(self):')
                                modified_lines.append(
                                    f'{" " * class_indent}    """Force GC to prevent mock accumulation in xdist workers"""'
                                )
                                modified_lines.append(f'{" " * class_indent}    gc.collect()')
                                modified_lines.append("")
                                modified_lines.append(next_line)
                                break
                            else:
                                modified_lines.append(next_line)

                            i += 1

                    found_class = True
                    break

            if not found_class:
                modified_lines.append(line)

            i += 1

        content = "\n".join(modified_lines)

        # Add gc import if needed
        if needs_gc_import and self.needs_memory_safety:
            lines = content.splitlines()
            # Find first import
            for i, line in enumerate(lines):
                if line.startswith(("import ", "from ")):
                    lines.insert(i, "import gc")
                    break
            content = "\n".join(lines)

        return content

    def fix(self) -> str:
        """Apply all fixes to the file."""
        # Step 1: Add pytestmark
        content = self.add_pytestmark()

        # Step 2: Add memory safety pattern if needed
        if self.needs_memory_safety:
            content = self.add_memory_safety_pattern(content)

        return content


def analyze_all_files(files: list[Path]) -> dict[str, list[tuple[Path, bool]]]:
    """
    Analyze all files and categorize them.

    Returns:
        Dict mapping marker name to list of (file_path, needs_memory_safety) tuples
    """
    categorization = defaultdict(list)

    for file_path in files:
        analyzer = TestFileAnalyzer(file_path)

        # Skip if already has pytestmark
        if analyzer.has_pytestmark():
            continue

        # Determine marker
        marker = analyzer.get_marker_from_path()

        # Check if needs memory safety
        needs_memory_safety = analyzer.uses_mocks() and not analyzer.has_xdist_group() and not analyzer.has_teardown_method()

        categorization[marker].append((file_path, needs_memory_safety))

    return categorization


def print_summary(categorization: dict[str, list[tuple[Path, bool]]]):
    """Print categorization summary."""
    print("\n📊 Categorization Summary")
    print("=" * 80)

    total_files = 0
    total_memory_safety = 0

    for marker in sorted(categorization.keys()):
        files = categorization[marker]
        memory_safety_count = sum(1 for _, needs_ms in files if needs_ms)
        total_files += len(files)
        total_memory_safety += memory_safety_count

        print(f"\n{marker}: {len(files)} files")
        if memory_safety_count > 0:
            print(f"  └─ {memory_safety_count} need memory safety patterns")

    print(f"\n{'=' * 80}")
    print(f"Total: {total_files} files")
    print(f"Memory safety patterns needed: {total_memory_safety} files")
    print()


def fix_all_files(categorization: dict[str, list[tuple[Path, bool]]]) -> int:
    """Fix all files and return count of fixed files."""
    fixed_count = 0

    for marker, files in categorization.items():
        print(f"\n🔧 Fixing {marker} tests ({len(files)} files)...")

        for file_path, needs_memory_safety in files:
            try:
                fixer = TestFileFixer(file_path, marker, needs_memory_safety)
                fixed_content = fixer.fix()

                # Write back to file
                file_path.write_text(fixed_content)
                fixed_count += 1

                status = "✓"
                if needs_memory_safety:
                    status += " (+ memory safety)"

                print(f"  {status} {file_path.name}")

            except Exception as e:
                print(f"  ✗ {file_path.name}: {e}")

    return fixed_count


def main():
    """Main entry point."""
    print("🔍 Finding test files missing pytestmark declarations...")

    # Get all test files from validation script
    tests_dir = Path("tests")
    test_files = list(tests_dir.rglob("test_*.py"))
    test_files.extend(tests_dir.rglob("*_test.py"))

    # Analyze all files
    print(f"\n📝 Analyzing {len(test_files)} test files...")
    categorization = analyze_all_files(test_files)

    if not categorization:
        print("\n✅ All test files already have pytestmark declarations!")
        return 0

    # Print summary
    print_summary(categorization)

    # Ask for confirmation
    response = input("🚀 Proceed with fixes? [y/N]: ").strip().lower()
    if response != "y":
        print("❌ Aborted.")
        return 1

    # Fix all files
    print("\n" + "=" * 80)
    fixed_count = fix_all_files(categorization)

    print("\n" + "=" * 80)
    print(f"✅ Fixed {fixed_count} files!")
    print("\n💡 Next steps:")
    print("  1. Run: python scripts/validate_pytest_markers.py")
    print("  2. Commit changes")

    return 0


if __name__ == "__main__":
    exit(main())
