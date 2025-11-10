"""
Tests for sleep duration linter (prevents test performance regressions).

TDD: These tests are written FIRST before implementing the linter.
"""

import gc
import os

import pytest


@pytest.mark.xdist_group(name="meta_tests")
class TestSleepDurationLinter:
    """Test sleep duration linter functionality."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_linter_detects_long_sleep_in_unit_test(self):
        """Linter should detect time.sleep() > 0.5s in unit tests."""
        from scripts.check_test_sleep_duration import check_file

        # Simulated unit test file content
        test_content = """
import time
import pytest

@pytest.mark.unit
def test_something():
    time.sleep(1.0)  # ❌ Too long for unit test
    assert True
"""

        violations = check_file(test_content, "test_example.py", is_unit=True)
        assert len(violations) == 1
        assert "1.0" in violations[0]
        assert "unit tests" in violations[0].lower()

    def test_linter_allows_short_sleep_in_unit_test(self):
        """Linter should allow time.sleep() <= 0.5s in unit tests."""
        from scripts.check_test_sleep_duration import check_file

        test_content = """
import time

def test_something():
    time.sleep(0.1)  # ✅ Acceptable for unit test
    assert True
"""

        violations = check_file(test_content, "test_example.py", is_unit=True)
        assert len(violations) == 0

    def test_linter_detects_long_sleep_in_integration_test(self):
        """Linter should detect time.sleep() > 2.0s in integration tests."""
        from scripts.check_test_sleep_duration import check_file

        test_content = """
import time
import pytest

@pytest.mark.integration
def test_something():
    time.sleep(3.0)  # ❌ Too long for integration test
    assert True
"""

        violations = check_file(test_content, "test_example.py", is_unit=False)
        assert len(violations) == 1
        assert "3.0" in violations[0]
        assert "integration tests" in violations[0].lower()

    def test_linter_allows_long_sleep_in_integration_test(self):
        """Linter should allow time.sleep() <= 2.0s in integration tests."""
        from scripts.check_test_sleep_duration import check_file

        test_content = """
import time

@pytest.mark.integration
def test_something():
    time.sleep(1.5)  # ✅ Acceptable for integration test
    assert True
"""

        violations = check_file(test_content, "test_example.py", is_unit=False)
        assert len(violations) == 0

    def test_linter_detects_asyncio_sleep(self):
        """Linter should detect asyncio.sleep() violations."""
        from scripts.check_test_sleep_duration import check_file

        test_content = """
import asyncio
import pytest

@pytest.mark.unit
@pytest.mark.asyncio
async def test_something():
    await asyncio.sleep(2.0)  # ❌ Too long for unit test
    assert True
"""

        violations = check_file(test_content, "test_example.py", is_unit=True)
        assert len(violations) == 1
        assert "2.0" in violations[0]

    def test_linter_detects_multiple_violations(self):
        """Linter should detect multiple violations in one file."""
        from scripts.check_test_sleep_duration import check_file

        test_content = """
import time

def test_one():
    time.sleep(1.0)  # ❌ Violation 1

def test_two():
    time.sleep(1.5)  # ❌ Violation 2
"""

        violations = check_file(test_content, "test_example.py", is_unit=True)
        assert len(violations) == 2

    def test_linter_ignores_comments(self):
        """Linter should ignore sleep calls in comments."""
        from scripts.check_test_sleep_duration import check_file

        test_content = """
def test_something():
    # time.sleep(10.0)  <- This is commented out
    assert True
"""

        violations = check_file(test_content, "test_example.py", is_unit=True)
        assert len(violations) == 0

    def test_linter_reports_line_numbers(self):
        """Linter should report accurate line numbers."""
        from scripts.check_test_sleep_duration import check_file

        test_content = """import time

def test_something():
    time.sleep(1.0)  # Line 4
"""

        violations = check_file(test_content, "test_example.py", is_unit=True)
        assert len(violations) == 1
        assert "line 4" in violations[0].lower()

    def test_linter_checks_actual_test_files(self):
        """Linter should successfully check real test files."""
        import os

        from scripts.check_test_sleep_duration import check_test_files

        # Check our optimized test files
        test_files = [
            "tests/property/test_cache_properties.py",
            "tests/core/test_cache.py",
            "tests/resilience/test_fallback.py",
            "tests/resilience/test_timeout.py",
            "tests/resilience/test_bulkhead.py",
        ]

        for test_file in test_files:
            if os.path.exists(test_file):
                violations = check_test_files([test_file])
                # After our optimizations, these should have no violations
                assert len(violations) == 0, (
                    f"{test_file} should have no sleep violations after optimization, " f"but found: {violations}"
                )
