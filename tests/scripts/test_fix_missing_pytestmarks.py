"""
Unit tests for scripts/fix_missing_pytestmarks.py

These tests validate that the script correctly handles multi-line import statements
and does not insert pytestmark declarations inside import blocks.

Regression prevention for commit a57fcc95 (2025-11-20) where pytestmark was
incorrectly inserted inside multi-line imports, causing SyntaxError in 16 test files.

Test ID: TEST-SCR-001
"""

import ast
import gc
import sys
from pathlib import Path
from textwrap import dedent

import pytest

# Add scripts directory to path so we can import the script
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
from fix_missing_pytestmarks import FileAnalyzer, FileFixer

pytestmark = pytest.mark.meta


@pytest.mark.meta
@pytest.mark.unit
@pytest.mark.xdist_group(name="test_fix_pytestmarks_script")
class TestModuleLevelInsertPosition:
    """Test get_module_level_insert_position handles multi-line imports correctly."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_insert_after_single_line_imports(self, tmp_path):
        """Test insertion after single-line imports (basic case).

        Test ID: TEST-SCR-001-01
        """
        test_file = tmp_path / "test_single.py"
        test_file.write_text(
            dedent(
                """
            import gc
            import pytest

            def test_something():
                pass
        """
            )
        )

        analyzer = FileAnalyzer(test_file)
        position = analyzer.get_module_level_insert_position()

        # Should be after line 3 (import pytest) - Note: dedent() adds leading newline
        assert position == 3, f"Expected position 3, got {position}"

    def test_insert_after_multiline_import_last(self, tmp_path):
        """Test insertion after multi-line import as last import (BUG CASE).

        This is the exact scenario that caused the bug in commit a57fcc95.
        The script used node.lineno (line 3) instead of node.end_lineno (line 6),
        causing pytestmark to be inserted inside the import parentheses.

        Test ID: TEST-SCR-001-02
        """
        test_file = tmp_path / "test_multiline.py"
        test_file.write_text(
            dedent(
                """
            import gc
            import pytest
            from datetime import (
                datetime,
                timezone
            )

            def test_something():
                pass
        """
            )
        )

        analyzer = FileAnalyzer(test_file)
        position = analyzer.get_module_level_insert_position()

        # Should be after line 7 (closing paren), NOT line 4 (from datetime)
        # Note: dedent() adds leading newline, so line numbers are +1
        assert position == 7, (
            f"Expected position 7 (after closing paren), got {position}. " f"Pytestmark would be inserted inside import block!"
        )

    def test_insert_after_multiline_import_middle(self, tmp_path):
        """Test insertion after multi-line import with more imports after.

        Test ID: TEST-SCR-001-03
        """
        test_file = tmp_path / "test_multiline_middle.py"
        test_file.write_text(
            dedent(
                """
            import gc
            from datetime import (
                datetime,
                timezone
            )
            import pytest

            def test_something():
                pass
        """
            )
        )

        analyzer = FileAnalyzer(test_file)
        position = analyzer.get_module_level_insert_position()

        # Should be after line 7 (import pytest), which is last import
        # Note: dedent() adds leading newline, so line numbers are +1
        assert position == 7, f"Expected position 7, got {position}"

    def test_insert_after_multiple_multiline_imports(self, tmp_path):
        """Test insertion after multiple multi-line import statements.

        Test ID: TEST-SCR-001-04
        """
        test_file = tmp_path / "test_multiple_multiline.py"
        test_file.write_text(
            dedent(
                """
            import gc
            from datetime import (
                datetime,
                timezone
            )
            from typing import (
                Any,
                Dict,
                List
            )

            def test_something():
                pass
        """
            )
        )

        analyzer = FileAnalyzer(test_file)
        position = analyzer.get_module_level_insert_position()

        # Should be after line 11 (closing paren of last import)
        # Note: dedent() adds leading newline, so line numbers are +1
        assert position == 11, f"Expected position 11, got {position}"

    def test_insert_after_docstring_and_imports(self, tmp_path):
        """Test insertion after module docstring and imports.

        Test ID: TEST-SCR-001-05
        """
        test_file = tmp_path / "test_docstring.py"
        test_file.write_text(
            dedent(
                '''
            """Module docstring."""

            import gc
            from datetime import (
                datetime,
                timezone
            )

            def test_something():
                pass
        '''
            )
        )

        analyzer = FileAnalyzer(test_file)
        position = analyzer.get_module_level_insert_position()

        # Should be after line 8 (closing paren of import)
        # Note: dedent() adds leading newline, so line numbers are +1
        assert position == 8, f"Expected position 8, got {position}"

    def test_insert_with_no_imports(self, tmp_path):
        """Test insertion when file has no imports (edge case).

        Test ID: TEST-SCR-001-06
        """
        test_file = tmp_path / "test_no_imports.py"
        test_file.write_text(
            dedent(
                """
            def test_something():
                pass
        """
            )
        )

        analyzer = FileAnalyzer(test_file)
        position = analyzer.get_module_level_insert_position()

        # Should return 0 when no imports found
        assert position == 0, f"Expected position 0, got {position}"

    def test_insert_with_very_long_multiline_import(self, tmp_path):
        """Test insertion after very long multi-line import (many items).

        Test ID: TEST-SCR-001-07
        """
        test_file = tmp_path / "test_long_import.py"
        test_file.write_text(
            dedent(
                """
            import pytest
            from mcp_server_langgraph.core.exceptions import (
                AuthenticationError,
                AuthorizationError,
                BulkheadRejectedError,
                CircuitBreakerOpenError,
                ComplianceError,
                ConfigurationError,
                ConstraintViolationError,
                DataIntegrityError,
                DataNotFoundError,
                ErrorCategory,
                ExternalServiceError,
            )

            def test_something():
                pass
        """
            )
        )

        analyzer = FileAnalyzer(test_file)
        position = analyzer.get_module_level_insert_position()

        # Should be after line 15 (closing paren)
        # Note: dedent() adds leading newline, so line numbers are +1
        assert position == 15, f"Expected position 15, got {position}"


@pytest.mark.meta
@pytest.mark.unit
@pytest.mark.xdist_group(name="test_fix_pytestmarks_integration")
class TestPytestmarkIntegration:
    """Integration tests for complete pytestmark insertion workflow."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_generated_code_is_syntactically_valid_multiline_import(self, tmp_path):
        """Integration test: ensure generated code with multi-line imports is valid.

        This is the critical test that would have caught the bug in commit a57fcc95.

        Test ID: TEST-SCR-001-08
        """
        test_file = tmp_path / "test_integration.py"
        test_file.write_text(
            dedent(
                """
            import gc
            from datetime import (
                datetime,
                timezone
            )

            def test_something():
                pass
        """
            )
        )

        fixer = FileFixer(test_file, "unit", needs_memory_safety=False)
        fixed_content = fixer.add_pytestmark()

        # Verify syntax is valid
        try:
            ast.parse(fixed_content)
        except SyntaxError as e:
            pytest.fail(f"Generated invalid Python syntax:\n" f"Error: {e}\n" f"Generated code:\n{fixed_content}")

        # Verify pytestmark is on correct line (after closing paren, not inside)
        lines = fixed_content.splitlines()
        pytestmark_lines = [i for i, line in enumerate(lines) if "pytestmark" in line]

        assert len(pytestmark_lines) == 1, f"Expected 1 pytestmark line, found {len(pytestmark_lines)}"

        pytestmark_line_num = pytestmark_lines[0]

        # Pytestmark should be after line 5 (closing paren is at index 4, 0-based)
        # and definitely NOT inside the import block (lines 2-5)
        assert pytestmark_line_num > 5, (
            f"pytestmark found at line {pytestmark_line_num}, " f"which is inside or at the import block (lines 2-5)"
        )

    def test_generated_code_preserves_existing_code(self, tmp_path):
        """Test that adding pytestmark doesn't corrupt existing code.

        Test ID: TEST-SCR-001-09
        """
        original_code = dedent(
            """
            import gc
            from typing import (
                Any,
                Dict
            )

            def test_example():
                assert True
        """
        )

        test_file = tmp_path / "test_preserve.py"
        test_file.write_text(original_code)

        fixer = FileFixer(test_file, "unit", needs_memory_safety=False)
        fixed_content = fixer.add_pytestmark()

        # Original function should still be present and unchanged
        assert "def test_example():" in fixed_content
        assert "assert True" in fixed_content
        assert "from typing import (" in fixed_content
        assert "Any," in fixed_content
        assert "Dict" in fixed_content

    def test_multiple_multiline_imports_generates_valid_syntax(self, tmp_path):
        """Test complex case with multiple multi-line imports.

        Test ID: TEST-SCR-001-10
        """
        test_file = tmp_path / "test_complex.py"
        test_file.write_text(
            dedent(
                """
            from datetime import (
                datetime,
                timezone
            )
            from typing import (
                Any,
                Dict,
                List,
                Optional
            )
            from collections.abc import (
                Callable,
                Iterator
            )

            def test_complex():
                pass
        """
            )
        )

        fixer = FileFixer(test_file, "unit", needs_memory_safety=False)
        fixed_content = fixer.add_pytestmark()

        # Verify syntax is valid
        try:
            ast.parse(fixed_content)
        except SyntaxError as e:
            pytest.fail(f"Generated invalid Python syntax: {e}\n{fixed_content}")

        # Verify pytestmark is AFTER all imports, not inside any of them
        lines = fixed_content.splitlines()
        pytestmark_lines = [i for i, line in enumerate(lines) if "pytestmark" in line]
        assert len(pytestmark_lines) == 1

        pytestmark_line = pytestmark_lines[0]
        # Last import closes at line 14 (0-based index 13)
        assert pytestmark_line > 14, (
            f"pytestmark at line {pytestmark_line} is too early, " f"should be after line 14 (last import closing paren)"
        )

    def test_handles_inline_comments_in_multiline_import(self, tmp_path):
        """Test multi-line import with inline comments.

        Test ID: TEST-SCR-001-11
        """
        test_file = tmp_path / "test_comments.py"
        test_file.write_text(
            dedent(
                """
            import pytest
            from mcp_server_langgraph.core.exceptions import (  # noqa: E501
                AuthenticationError,  # Auth errors
                AuthorizationError,   # Authz errors
            )

            def test_something():
                pass
        """
            )
        )

        fixer = FileFixer(test_file, "unit", needs_memory_safety=False)
        fixed_content = fixer.add_pytestmark()

        # Verify syntax is valid
        try:
            ast.parse(fixed_content)
        except SyntaxError as e:
            pytest.fail(f"Generated invalid Python syntax: {e}\n{fixed_content}")

        # Verify comments are preserved
        assert "# noqa: E501" in fixed_content
        assert "# Auth errors" in fixed_content


@pytest.mark.meta
@pytest.mark.unit
@pytest.mark.xdist_group(name="test_fix_pytestmarks_edge_cases")
class TestEdgeCases:
    """Test edge cases and error conditions."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_file_with_syntax_error_uses_fallback(self, tmp_path):
        """Test that files with syntax errors use fallback method.

        Test ID: TEST-SCR-001-12
        """
        test_file = tmp_path / "test_syntax_error.py"
        test_file.write_text(
            dedent(
                """
            import pytest
            from foo import (  # Missing closing paren!
                bar
            # This is invalid syntax

            def test_something():
                pass
        """
            )
        )

        analyzer = FileAnalyzer(test_file)
        # Should not crash, should use fallback method
        position = analyzer.get_module_level_insert_position()

        # Fallback should return some reasonable position
        assert isinstance(position, int)
        assert position >= 0

    def test_empty_file(self, tmp_path):
        """Test handling of empty file.

        Test ID: TEST-SCR-001-13
        """
        test_file = tmp_path / "test_empty.py"
        test_file.write_text("")

        analyzer = FileAnalyzer(test_file)
        position = analyzer.get_module_level_insert_position()

        # Should return 0 for empty file
        assert position == 0

    def test_only_docstring_no_imports(self, tmp_path):
        """Test file with only module docstring, no imports.

        Test ID: TEST-SCR-001-14
        """
        test_file = tmp_path / "test_docstring_only.py"
        test_file.write_text(
            dedent(
                '''
            """
            Module docstring.
            """

            def test_something():
                pass
        '''
            )
        )

        analyzer = FileAnalyzer(test_file)
        position = analyzer.get_module_level_insert_position()

        # Should return 0 when no imports found
        assert position == 0
