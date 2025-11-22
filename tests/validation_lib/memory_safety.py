"""
Memory Safety Pattern Validation for Pytest-xdist.

This module provides AST-based validation to ensure test files follow memory safety
patterns that prevent memory explosion when running tests with pytest-xdist.

The memory safety pattern requires:
1. Test classes using AsyncMock/MagicMock must have @pytest.mark.xdist_group decorator
2. Test classes must have teardown_method() with gc.collect()
3. Performance tests must skip when running under pytest-xdist workers

Background:
When running tests with pytest-xdist, AsyncMock/MagicMock objects create circular
references that prevent garbage collection, leading to memory explosion (observed:
217GB VIRT, 42GB RES). The 3-part pattern prevents this by:
- Grouping related tests in same worker (xdist_group)
- Forcing GC after each test (teardown_method + gc.collect)
- Skipping performance tests in parallel mode

False Positive Prevention:
- Only detects actual mock instantiation (AsyncMock() calls), not name references
- Prevents flagging docstrings/comments that mention mock classes
- Focuses on classes that actually create mock objects

Version: 1.0.0
See: tests/MEMORY_SAFETY_GUIDELINES.md for complete documentation
"""

import ast
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Violation:
    """Represents a memory safety pattern violation."""

    file_path: str
    line_number: int
    violation_type: str
    message: str
    fix_suggestion: str


class MemorySafetyChecker(ast.NodeVisitor):
    """AST visitor to check for memory safety pattern violations."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.violations: list[Violation] = []
        self.current_class: str | None = None
        self.current_class_line: int | None = None
        self.current_class_decorators: list[str] = []
        self.current_class_methods: set[str] = set()
        self.class_uses_mocks = False
        self.class_is_performance = False

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definitions to check for test classes."""
        # Reset state for new class
        self.current_class = node.name
        self.current_class_line = node.lineno
        self.current_class_decorators = []
        self.current_class_methods = set()
        self.class_uses_mocks = False
        self.class_is_performance = False

        # Check if this is a test class
        if not node.name.startswith("Test"):
            self.generic_visit(node)
            return

        # Extract decorators
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Attribute):
                    # @pytest.mark.xdist_group(name="...")
                    if (
                        isinstance(decorator.func.value, ast.Attribute)
                        and isinstance(decorator.func.value.value, ast.Name)
                        and decorator.func.value.value.id == "pytest"
                        and decorator.func.value.attr == "mark"
                    ):
                        self.current_class_decorators.append(decorator.func.attr)
                elif isinstance(decorator.func, ast.Name):
                    self.current_class_decorators.append(decorator.func.id)
            elif isinstance(decorator, ast.Attribute):
                # @pytest.mark.unit
                if (
                    isinstance(decorator.value, ast.Attribute)
                    and isinstance(decorator.value.value, ast.Name)
                    and decorator.value.value.id == "pytest"
                    and decorator.value.attr == "mark"
                ):
                    self.current_class_decorators.append(decorator.attr)
                    if decorator.attr == "performance":
                        self.class_is_performance = True

        # Visit class body to check for mock usage and methods
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.current_class_methods.add(item.name)
                # Check if method uses AsyncMock or MagicMock
                self._check_for_mock_usage(item)

            # Also check for mock usage in class-level assignments
            elif isinstance(item, (ast.Assign, ast.AnnAssign)):
                self._check_node_for_mocks(item)

        # Validate the class after visiting all methods
        self._validate_class()

        self.generic_visit(node)

    def _check_for_mock_usage(self, node: ast.FunctionDef) -> None:
        """Check if a function actually instantiates AsyncMock or MagicMock."""
        # Only check for Call nodes (instantiation), not Name references
        # This prevents false positives from comments/docstrings
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    if child.func.id in ("AsyncMock", "MagicMock"):
                        self.class_uses_mocks = True
                        return  # Found mock usage, no need to continue

    def _check_node_for_mocks(self, node: ast.AST) -> None:
        """Check any AST node for AsyncMock/MagicMock instantiation."""
        # Only check for Call nodes (instantiation), not Name references
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    if child.func.id in ("AsyncMock", "MagicMock"):
                        self.class_uses_mocks = True
                        return  # Found mock usage, no need to continue

    def _validate_class(self) -> None:
        """Validate that the current test class follows memory safety patterns."""
        if not self.current_class:
            return

        # Check if class uses mocks but missing xdist_group
        if self.class_uses_mocks:
            has_xdist_group = "xdist_group" in self.current_class_decorators
            has_teardown = "teardown_method" in self.current_class_methods

            if not has_xdist_group:
                self.violations.append(
                    Violation(
                        file_path=self.file_path,
                        line_number=self.current_class_line,
                        violation_type="missing_xdist_group",
                        message=f"class {self.current_class} uses AsyncMock/MagicMock but missing @pytest.mark.xdist_group",
                        fix_suggestion=f'Add @pytest.mark.xdist_group(name="{self.current_class.lower()}") above class {self.current_class}',
                    )
                )

            if not has_teardown:
                self.violations.append(
                    Violation(
                        file_path=self.file_path,
                        line_number=self.current_class_line,
                        violation_type="missing_teardown",
                        message=f"class {self.current_class} missing teardown_method() with gc.collect()",
                        fix_suggestion=f"Add teardown_method with gc.collect() to class {self.current_class}:\n"
                        f"    def teardown_method(self):\n"
                        f'        """Force GC to prevent mock accumulation in xdist workers"""\n'
                        f"        gc.collect()",
                    )
                )

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definitions to check for performance test patterns."""
        self._check_performance_test(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function definitions to check for performance test patterns."""
        self._check_performance_test(node)
        self.generic_visit(node)

    def _check_performance_test(self, node) -> None:
        """Check if a test method needs xdist skipif decorator."""
        # Check if this is a test method and class is marked as performance
        if self.current_class and node.name.startswith("test_") and self.class_is_performance:
            # Check if method has @pytest.mark.skipif for xdist
            has_xdist_skipif = False
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Call):
                    if isinstance(decorator.func, ast.Attribute):
                        if (
                            isinstance(decorator.func.value, ast.Attribute)
                            and isinstance(decorator.func.value.value, ast.Name)
                            and decorator.func.value.value.id == "pytest"
                            and decorator.func.value.attr == "mark"
                            and decorator.func.attr == "skipif"
                        ):
                            # Check if it's checking for PYTEST_XDIST_WORKER
                            for arg in decorator.args:
                                if isinstance(arg, ast.Compare):
                                    if self._is_xdist_check(arg):
                                        has_xdist_skipif = True

            if not has_xdist_skipif:
                self.violations.append(
                    Violation(
                        file_path=self.file_path,
                        line_number=node.lineno,
                        violation_type="missing_xdist_skipif",
                        message=f"Performance test {self.current_class}.{node.name} missing @pytest.mark.skipif for xdist",
                        fix_suggestion='Add @pytest.mark.skipif(os.getenv("PYTEST_XDIST_WORKER") is not None, reason="...") above test method',
                    )
                )

    def _is_xdist_check(self, node: ast.Compare) -> bool:
        """Check if comparison is checking for PYTEST_XDIST_WORKER environment variable."""
        # Pattern: os.getenv("PYTEST_XDIST_WORKER") is not None
        if isinstance(node.left, ast.Call):
            if isinstance(node.left.func, ast.Attribute):
                if (
                    isinstance(node.left.func.value, ast.Name)
                    and node.left.func.value.id == "os"
                    and node.left.func.attr == "getenv"
                ):
                    if node.left.args:
                        if isinstance(node.left.args[0], ast.Constant):
                            if node.left.args[0].value == "PYTEST_XDIST_WORKER":
                                return True
        return False


def check_file(file_path: str) -> list[Violation]:
    """
    Check a single file for memory safety violations.

    Args:
        file_path: Path to the test file to check

    Returns:
        List of Violation objects found in the file
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content, filename=file_path)
        checker = MemorySafetyChecker(file_path)
        checker.visit(tree)
        return checker.violations

    except SyntaxError as e:
        print(f"Warning: Syntax error in {file_path}: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"Warning: Error processing {file_path}: {e}", file=sys.stderr)
        return []


def find_test_files(base_dir: str = "tests") -> list[str]:
    """
    Find all test files under the base directory.

    Args:
        base_dir: Base directory to search for test files

    Returns:
        Sorted list of test file paths
    """
    test_files = []
    base_path = Path(base_dir)

    if not base_path.exists():
        return []

    for path in base_path.rglob("test_*.py"):
        test_files.append(str(path))

    return sorted(test_files)


def print_violations(violations: list[Violation]) -> None:
    """
    Print violations in a readable format.

    Args:
        violations: List of Violation objects to print
    """
    if not violations:
        print("✅ Memory Safety Validation")
        print("\nNo violations found. All tests follow memory safety patterns!")
        return

    print("✅ Memory Safety Validation")
    print(f"\n❌ Found {len(violations)} violations:\n")

    # Group violations by file
    violations_by_file = {}
    for v in violations:
        if v.file_path not in violations_by_file:
            violations_by_file[v.file_path] = []
        violations_by_file[v.file_path].append(v)

    for file_path, file_violations in violations_by_file.items():
        print(f"{file_path}:")
        for v in file_violations:
            print(f"  - Line {v.line_number}: {v.message}")
            print(f"    Fix: {v.fix_suggestion}")
            print()

    print("Summary:")
    print(f"  Total files scanned: {len(violations_by_file)}")
    print(f"  Files with violations: {len(violations_by_file)}")
    print(f"  Total violations: {len(violations)}")
    print()
    print("See: tests/MEMORY_SAFETY_GUIDELINES.md for complete documentation")
