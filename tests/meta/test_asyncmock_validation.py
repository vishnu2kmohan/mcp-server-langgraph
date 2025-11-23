"""
Tests for AsyncMock validation pre-commit hook.

Ensures that AsyncMock is always instantiated, never assigned as a class.

Test Coverage:
- Detects AsyncMock class assignments
- Allows AsyncMock instance creation
- Provides helpful error messages
- Handles edge cases (comments, strings, etc.)
"""

import subprocess
import tempfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="testasyncmockvalidation")
class TestAsyncMockValidation:
    """Tests for AsyncMock usage validation"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        import gc

        gc.collect()

    def test_detects_asyncmock_class_assignment(self):
        """Should detect and reject AsyncMock class assignments"""
        bad_code = """
import asyncmock
from unittest.mock import AsyncMock

mock_conn.fetchval = AsyncMock  # noqa: async-mock-config(return_value=1)
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(bad_code)
            f.flush()

            result = subprocess.run(
                ["python", "scripts/validation/check_asyncmock_usage.py", f.name],
                capture_output=True,
                text=True,
                timeout=60,
            )

            assert result.returncode != 0
            assert "AsyncMock" in result.stdout
            Path(f.name).unlink()

    def test_allows_asyncmock_instance_creation(self):
        """Should allow AsyncMock instance creation"""
        good_code = """
from unittest.mock import AsyncMock

mock_conn.fetchval = AsyncMock(return_value=1)
mock_conn.close = AsyncMock()
mock_conn.method = AsyncMock(side_effect=Exception("error"))
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(good_code)
            f.flush()

            result = subprocess.run(
                ["python", "scripts/validation/check_asyncmock_usage.py", f.name],
                capture_output=True,
                text=True,
                timeout=60,
            )

            assert result.returncode == 0
            Path(f.name).unlink()

    def test_ignores_asyncmock_in_comments(self):
        """Should ignore AsyncMock in comments"""
        code_with_comment = """
from unittest.mock import AsyncMock

# This is a comment about AsyncMock
mock_obj = AsyncMock()  # Create instance, not AsyncMock class
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code_with_comment)
            f.flush()

            result = subprocess.run(
                ["python", "scripts/validation/check_asyncmock_usage.py", f.name],
                capture_output=True,
                text=True,
                timeout=60,
            )

            assert result.returncode == 0
            Path(f.name).unlink()

    def test_ignores_asyncmock_in_strings(self):
        """Should ignore AsyncMock in strings"""
        code_with_string = """
from unittest.mock import AsyncMock

description = "Use AsyncMock for mocking"
mock_obj = AsyncMock()
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code_with_string)
            f.flush()

            result = subprocess.run(
                ["python", "scripts/validation/check_asyncmock_usage.py", f.name],
                capture_output=True,
                text=True,
                timeout=60,
            )

            assert result.returncode == 0
            Path(f.name).unlink()
