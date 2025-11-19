"""
Unit tests for memory safety validation library.

This test file validates the shared validation logic used by:
- scripts/check_test_memory_safety.py (pre-commit hook)
- tests/meta/test_pytest_xdist_enforcement.py (meta-tests)

Following TDD: These tests are written FIRST, before the implementation.
"""

import gc
from pathlib import Path
from textwrap import dedent

import pytest

from tests.validation_lib import memory_safety


@pytest.mark.unit
@pytest.mark.meta
@pytest.mark.xdist_group(name="validator_unit_tests")
class TestMemorySafetyValidator:
    """Unit tests for memory safety validation logic."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_detects_missing_xdist_group_marker(self, tmp_path: Path) -> None:
        """Test detection of test class using mocks without xdist_group marker."""
        test_file = tmp_path / "test_bad.py"
        test_file.write_text(
            dedent(
                """
                from unittest.mock import AsyncMock

                class TestSomething:
                    def test_method(self):
                        mock = AsyncMock()  # Uses AsyncMock but no xdist_group
                        assert mock
                """
            )
        )

        violations = memory_safety.check_file(str(test_file))

        assert len(violations) > 0
        assert any("xdist_group" in v.message for v in violations)

    def test_detects_missing_teardown_method(self, tmp_path: Path) -> None:
        """Test detection of test class missing teardown_method with gc.collect()."""
        test_file = tmp_path / "test_bad.py"
        test_file.write_text(
            dedent(
                """
                from unittest.mock import MagicMock
                import pytest

                @pytest.mark.xdist_group(name="test_group")
                class TestSomething:
                    def test_method(self):
                        mock = MagicMock()  # Has xdist_group but no teardown_method
                        assert mock
                """
            )
        )

        violations = memory_safety.check_file(str(test_file))

        assert len(violations) > 0
        assert any("teardown" in v.message.lower() for v in violations)

    def test_allows_valid_memory_safety_pattern(self, tmp_path: Path) -> None:
        """Test that valid memory safety pattern passes validation."""
        test_file = tmp_path / "test_good.py"
        test_file.write_text(
            dedent(
                """
                import gc
                from unittest.mock import AsyncMock
                import pytest

                @pytest.mark.xdist_group(name="test_group")
                class TestSomething:
                    def teardown_method(self):
                        gc.collect()

                    def test_method(self):
                        mock = AsyncMock()
                        assert mock
                """
            )
        )

        violations = memory_safety.check_file(str(test_file))

        assert len(violations) == 0, f"Expected no violations, got: {violations}"

    def test_ignores_classes_not_using_mocks(self, tmp_path: Path) -> None:
        """Test that classes not using AsyncMock/MagicMock are not flagged."""
        test_file = tmp_path / "test_no_mocks.py"
        test_file.write_text(
            dedent(
                """
                class TestSomething:
                    def test_method(self):
                        # No mocks used, so xdist_group not required
                        assert True
                """
            )
        )

        violations = memory_safety.check_file(str(test_file))

        assert len(violations) == 0

    def test_detects_performance_test_missing_xdist_skipif(self, tmp_path: Path) -> None:
        """Test detection of performance test missing skipif for xdist."""
        test_file = tmp_path / "test_perf.py"
        test_file.write_text(
            dedent(
                """
                import gc
                import pytest
                from unittest.mock import AsyncMock

                @pytest.mark.performance
                @pytest.mark.xdist_group(name="perf_tests")
                class TestPerformance:
                    def teardown_method(self):
                        gc.collect()

                    def test_performance_metric(self):
                        # Performance test should skip in xdist mode
                        mock = AsyncMock()
                        # ... performance testing logic ...
                        assert mock
                """
            )
        )

        violations = memory_safety.check_file(str(test_file))

        assert len(violations) > 0
        assert any("skipif" in v.message.lower() for v in violations)

    def test_allows_performance_test_with_xdist_skipif(self, tmp_path: Path) -> None:
        """Test that performance test with skipif passes validation."""
        test_file = tmp_path / "test_perf_good.py"
        test_file.write_text(
            dedent(
                """
                import gc
                import os
                import pytest
                from unittest.mock import AsyncMock

                @pytest.mark.performance
                @pytest.mark.xdist_group(name="perf_tests")
                class TestPerformance:
                    def teardown_method(self):
                        gc.collect()

                    @pytest.mark.skipif(
                        os.getenv("PYTEST_XDIST_WORKER") is not None,
                        reason="Performance tests skipped in parallel mode"
                    )
                    def test_performance_metric(self):
                        mock = AsyncMock()
                        assert mock
                """
            )
        )

        violations = memory_safety.check_file(str(test_file))

        assert len(violations) == 0, f"Expected no violations, got: {violations}"

    def test_violation_dataclass_structure(self, tmp_path: Path) -> None:
        """Test that Violation objects have expected structure."""
        test_file = tmp_path / "test_bad.py"
        test_file.write_text(
            dedent(
                """
                from unittest.mock import AsyncMock

                class TestSomething:
                    def test_method(self):
                        mock = AsyncMock()
                        assert mock
                """
            )
        )

        violations = memory_safety.check_file(str(test_file))

        assert len(violations) > 0
        violation = violations[0]

        # Check Violation has expected attributes
        assert hasattr(violation, "file_path")
        assert hasattr(violation, "line_number")
        assert hasattr(violation, "violation_type")
        assert hasattr(violation, "message")
        assert hasattr(violation, "fix_suggestion")

        assert violation.file_path == str(test_file)
        assert violation.line_number > 0
        assert violation.violation_type in ["missing_xdist_group", "missing_teardown", "missing_xdist_skipif"]
        assert len(violation.message) > 0
        assert len(violation.fix_suggestion) > 0

    def test_handles_syntax_errors_gracefully(self, tmp_path: Path) -> None:
        """Test that validator handles files with syntax errors gracefully."""
        test_file = tmp_path / "test_syntax_error.py"
        test_file.write_text(
            dedent(
                """
                def test_something(:  # Syntax error - missing parameter name
                    assert True
                """
            )
        )

        # Should not raise exception, should return empty list or handle gracefully
        violations = memory_safety.check_file(str(test_file))

        # Either empty violations or graceful error handling
        assert isinstance(violations, list)

    def test_detects_async_mock_instantiation_not_references(self, tmp_path: Path) -> None:
        """Test that only AsyncMock() instantiation is detected, not name references."""
        test_file = tmp_path / "test_references.py"
        test_file.write_text(
            dedent(
                """
                # This comment mentions AsyncMock but shouldn't trigger
                class TestSomething:
                    def test_method(self):
                        # AsyncMock in docstring shouldn't trigger
                        assert True  # No actual AsyncMock instantiation
                """
            )
        )

        violations = memory_safety.check_file(str(test_file))

        # Should have NO violations because AsyncMock is never instantiated
        assert len(violations) == 0

    def test_detects_magic_mock_in_addition_to_async_mock(self, tmp_path: Path) -> None:
        """Test that both AsyncMock and MagicMock are detected."""
        test_file = tmp_path / "test_magic_mock.py"
        test_file.write_text(
            dedent(
                """
                from unittest.mock import MagicMock

                class TestSomething:
                    def test_method(self):
                        mock = MagicMock()  # Should be detected
                        assert mock
                """
            )
        )

        violations = memory_safety.check_file(str(test_file))

        assert len(violations) > 0
        assert any("MagicMock" in v.message or "xdist_group" in v.message for v in violations)


@pytest.mark.unit
@pytest.mark.meta
class TestMemorySafetyHelpers:
    """Test helper functions in memory safety validator."""

    def test_find_test_files_returns_sorted_list(self, tmp_path: Path) -> None:
        """Test that find_test_files returns sorted list of test files."""
        # Create test files
        (tmp_path / "test_a.py").write_text("# test file")
        (tmp_path / "test_z.py").write_text("# test file")
        (tmp_path / "test_b.py").write_text("# test file")
        (tmp_path / "not_a_test.py").write_text("# not a test")

        files = memory_safety.find_test_files(str(tmp_path))

        # Should find only test_*.py files, sorted alphabetically
        assert len(files) == 3
        assert files[0].endswith("test_a.py")
        assert files[1].endswith("test_b.py")
        assert files[2].endswith("test_z.py")

    def test_find_test_files_handles_missing_directory(self) -> None:
        """Test that find_test_files handles missing directory gracefully."""
        files = memory_safety.find_test_files("/nonexistent/directory")

        assert files == []

    def test_print_violations_shows_helpful_output(self, capsys, tmp_path: Path) -> None:
        """Test that print_violations produces helpful output."""
        test_file = tmp_path / "test_bad.py"

        violations = [
            memory_safety.Violation(
                file_path=str(test_file),
                line_number=10,
                violation_type="missing_xdist_group",
                message="Test class missing @pytest.mark.xdist_group",
                fix_suggestion="Add @pytest.mark.xdist_group(name='test_group')",
            )
        ]

        memory_safety.print_violations(violations)

        captured = capsys.readouterr()

        # Should show file path, line number, message, and fix suggestion
        assert str(test_file) in captured.out
        assert "Line 10" in captured.out
        assert "missing @pytest.mark.xdist_group" in captured.out
        assert "Add @pytest.mark.xdist_group" in captured.out

    def test_print_violations_shows_success_when_no_violations(self, capsys) -> None:
        """Test that print_violations shows success message when no violations."""
        memory_safety.print_violations([])

        captured = capsys.readouterr()

        assert "No violations found" in captured.out or "✅" in captured.out
