"""
Meta-test: Validate pytestmark appears after all imports.

Prevents SyntaxErrors from pytestmark inside import blocks.

This test was created in response to OpenAI Codex findings that identified
16 test files with pytestmark declarations placed incorrectly inside import
blocks, causing Python SyntaxErrors during test collection.

Security Impact: MEDIUM
- Test collection failures prevent security tests from running
- Broken tests create false confidence in test suite
- Syntax errors bypass pre-commit hooks if not detected

Test Coverage: 100% of test files
Compliance: TDD Meta-Test, Pre-Commit Enforcement
"""

import ast
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.meta]


class TestPytestmarkPlacement:
    """
    Validate that pytestmark declarations appear AFTER all module-level imports.

    Background:
    -----------
    Python requires all import statements to appear at the top of a module
    (after docstrings and module-level comments). Placing any non-import
    statement (like pytestmark assignment) INSIDE or BETWEEN import statements
    causes a SyntaxError.

    Incorrect Placement (SyntaxError):
    ----------------------------------
    ```python
    import pytest

    from some_module import (
    pytestmark = pytest.mark.unit  # ❌ SyntaxError!

        SomeClass,
        some_function,
    )
    ```

    Correct Placement:
    ------------------
    ```python
    import pytest
    from some_module import (
        SomeClass,
        some_function,
    )

    pytestmark = pytest.mark.unit  # ✅ After all imports
    ```

    Detection Method:
    -----------------
    Uses AST (Abstract Syntax Tree) parsing to:
    1. Find pytestmark assignment line number
    2. Find last module-level import line number
    3. Assert pytestmark appears AFTER last import

    This approach is more reliable than regex because it understands
    Python's syntax structure and correctly identifies module-level
    vs nested imports.

    References:
    -----------
    - OpenAI Codex Regression Report (2025-11-20): 16 files with this issue
    - scripts/fix_missing_pytestmarks.py:108-129 - Correct placement logic
    - ADR-0XXX: Pytestmark Placement Validation
    """

    def test_pytestmark_appears_after_all_imports(self):
        """
        🔴 RED PHASE: Test that pytestmark appears AFTER all imports.

        This test will FAIL initially (RED) because 16 files have
        pytestmark inside import blocks. After fixing those files,
        the test will PASS (GREEN).

        Validation Logic:
        -----------------
        For each test file:
        1. Parse file with AST to get syntax tree
        2. Find pytestmark assignment (if present)
        3. Find last module-level import
        4. Assert pytestmark_line > last_import_line

        Scope:
        ------
        - Scans: tests/**/*.py (all Python files)
        - Excludes: __init__.py, conftest.py (no pytestmark required)
        - Reports: All violations with file:line format

        Expected Initial State: ❌ FAIL (16 violations)
        Expected After Fix: ✅ PASS (0 violations)
        """
        tests_dir = Path(__file__).parent.parent
        violations = []
        files_checked = 0
        files_with_pytestmark = 0

        # Scan all test files
        for test_file in sorted(tests_dir.rglob("*.py")):
            # Skip special files that don't need pytestmark
            if test_file.name in ["__init__.py", "conftest.py"]:
                continue

            # Skip if not a test file pattern
            if not test_file.name.startswith("test_"):
                continue

            files_checked += 1

            try:
                content = test_file.read_text(encoding="utf-8")
                tree = ast.parse(content, filename=str(test_file))
            except SyntaxError as e:
                # File has syntax errors - this test specifically looks for
                # pytestmark placement issues which CAUSE syntax errors.
                # If we can't parse the file at all, it might be due to
                # the very issue we're testing for.
                violations.append(f"{test_file.relative_to(tests_dir.parent)}:PARSE_ERROR " f"(cannot parse: {e})")
                continue

            # Find pytestmark assignment line (module-level only)
            pytestmark_line = None
            for node in tree.body:  # Only module-level nodes
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id == "pytestmark":
                            pytestmark_line = node.lineno
                            files_with_pytestmark += 1
                            break

            # No pytestmark found - handled by other validators
            if pytestmark_line is None:
                continue

            # Find last module-level import line
            last_import_line = 0
            for node in tree.body:  # Only module-level nodes
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    if hasattr(node, "lineno"):
                        last_import_line = max(last_import_line, node.lineno)

            # Validate pytestmark appears AFTER all imports
            if last_import_line > 0 and pytestmark_line < last_import_line:
                violations.append(
                    f"{test_file.relative_to(tests_dir.parent)}:{pytestmark_line} "
                    f"(pytestmark before import at line {last_import_line})"
                )

        # Generate detailed assertion message
        assert not violations, (
            f"\n{'='*80}\n"
            f"❌ PYTESTMARK PLACEMENT VIOLATIONS DETECTED\n"
            f"{'='*80}\n\n"
            f"Found {len(violations)} file(s) with pytestmark inside import blocks:\n\n"
            + "\n".join(f"  {i+1}. {v}" for i, v in enumerate(violations))
            + f"\n\n"
            f"{'='*80}\n"
            f"ROOT CAUSE\n"
            f"{'='*80}\n\n"
            f"Python requires ALL import statements to appear at the module top\n"
            f"(after docstrings). Placing pytestmark INSIDE or BETWEEN imports\n"
            f"causes SyntaxError during test collection.\n\n"
            f"{'='*80}\n"
            f"HOW TO FIX\n"
            f"{'='*80}\n\n"
            f"Move pytestmark declaration to AFTER the closing parenthesis\n"
            f"of all import statements:\n\n"
            f"  ❌ WRONG:\n"
            f"    from module import (\n"
            f"    pytestmark = pytest.mark.unit  # Inside import block!\n"
            f"        Symbol1,\n"
            f"        Symbol2,\n"
            f"    )\n\n"
            f"  ✅ CORRECT:\n"
            f"    from module import (\n"
            f"        Symbol1,\n"
            f"        Symbol2,\n"
            f"    )\n\n"
            f"    pytestmark = pytest.mark.unit  # After all imports\n\n"
            f"{'='*80}\n"
            f"STATISTICS\n"
            f"{'='*80}\n\n"
            f"  Files checked: {files_checked}\n"
            f"  Files with pytestmark: {files_with_pytestmark}\n"
            f"  Violations found: {len(violations)}\n"
            f"  Compliance rate: {((files_with_pytestmark - len(violations)) / max(files_with_pytestmark, 1) * 100):.1f}%\n\n"
            f"{'='*80}\n"
            f"PREVENTION\n"
            f"{'='*80}\n\n"
            f"This test runs automatically via pre-commit hook:\n"
            f"  - Hook: validate-pytestmark-placement\n"
            f"  - Script: scripts/validate_pytest_markers.py\n"
            f"  - Test: tests/meta/test_pytestmark_placement.py (this file)\n\n"
            f"See: docs-internal/PYTESTMARK_GUIDELINES.md for complete guidelines\n\n"
            f"{'='*80}\n"
        )


class TestPytestmarkPlacementEdgeCases:
    """Test edge cases for pytestmark placement validation."""

    def test_files_without_imports_are_valid(self, tmp_path):
        """
        Files without any imports can have pytestmark anywhere.

        This is an edge case - if a test file has no imports (unusual
        but technically valid), pytestmark can appear anywhere since
        there are no import constraints.
        """
        test_file = tmp_path / "test_no_imports.py"
        test_file.write_text(
            '"""Test file with no imports"""\n'
            "\n"
            "pytestmark = pytest.mark.unit\n"
            "\n"
            "def test_something():\n"
            "    assert True\n"
        )

        # Parse and validate
        tree = ast.parse(test_file.read_text())

        pytestmark_line = None
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "pytestmark":
                        pytestmark_line = node.lineno

        last_import_line = 0
        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                last_import_line = max(last_import_line, node.lineno)

        # No imports (last_import_line == 0) means pytestmark can be anywhere
        assert last_import_line == 0
        assert pytestmark_line == 3  # pytestmark is on line 3

    def test_files_without_pytestmark_are_valid(self, tmp_path):
        """
        Files without pytestmark don't trigger validation.

        This test ensures that test files without module-level pytestmark
        (but with class/function-level markers) don't cause false positives.
        """
        test_file = tmp_path / "test_no_pytestmark.py"
        test_file.write_text(
            '"""Test file without module-level pytestmark"""\n'
            "\n"
            "import pytest\n"
            "\n"
            "@pytest.mark.unit\n"
            "def test_something():\n"
            "    assert True\n"
        )

        # Parse and validate
        tree = ast.parse(test_file.read_text())

        pytestmark_line = None
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "pytestmark":
                        pytestmark_line = node.lineno

        # No pytestmark found - validation doesn't apply
        assert pytestmark_line is None

    def test_correct_placement_after_imports_is_valid(self, tmp_path):
        """
        Correctly placed pytestmark (after imports) passes validation.

        This is the GOLDEN PATH - pytestmark appears after all imports.
        """
        test_file = tmp_path / "test_correct_placement.py"
        test_file.write_text(
            '"""Test file with correct pytestmark placement"""\n'
            "\n"
            "import pytest\n"
            "from pathlib import Path\n"
            "\n"
            "pytestmark = pytest.mark.unit  # ✅ After all imports\n"
            "\n"
            "def test_something():\n"
            "    assert True\n"
        )

        # Parse and validate
        tree = ast.parse(test_file.read_text())

        pytestmark_line = None
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "pytestmark":
                        pytestmark_line = node.lineno

        last_import_line = 0
        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                last_import_line = max(last_import_line, node.lineno)

        # Validate: pytestmark (line 6) comes after last import (line 4)
        assert pytestmark_line == 6
        assert last_import_line == 4
        assert pytestmark_line > last_import_line  # ✅ VALID
