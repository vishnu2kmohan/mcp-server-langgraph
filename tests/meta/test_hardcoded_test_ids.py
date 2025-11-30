"""
Test that integration tests use worker-safe ID helpers (pytest-xdist isolation)

This test ensures integration tests use get_user_id() and get_api_key_id()
helpers instead of hardcoded IDs, preventing pytest-xdist worker pollution.

Following TDD principles: Write test first, then fix code

Regression prevention for validation audit finding:
- 2 integration tests have hardcoded user IDs
- Should use worker-safe helpers: get_user_id(), get_api_key_id()
"""

import gc
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="hardcoded_test_ids")
class TestHardcodedTestIDs:
    """Test that integration tests don't have hardcoded test IDs"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_no_hardcoded_user_ids_in_compliance_tests(self):
        """
        Test that compliance integration tests use get_user_id() helper.

        RED Phase: Will FAIL because tests have:
        - user_id="test_pref_user"
        - user_id="test_conv_user"

        GREEN Phase: After replacing with get_user_id("pref_user"), should PASS

        Hardcoded IDs cause pytest-xdist worker pollution where tests
        running in parallel share the same IDs and corrupt each other's data.
        """
        # Files that should use worker-safe IDs
        files_to_check = [
            Path("tests/integration/compliance/test_postgres_preferences_store.py"),
            Path("tests/integration/compliance/test_postgres_conversation_store.py"),
        ]

        violations = []

        for file_path in files_to_check:
            if not file_path.exists():
                continue

            content = file_path.read_text()

            # Check for hardcoded user_id patterns
            # Pattern: user_id="test_something" or user_id='test_something'
            hardcoded_patterns = [
                r'user_id\s*=\s*["\']test_[^"\']+["\']',
                r'api_key_id\s*=\s*["\']test_[^"\']+["\']',
                r'user_id\s*=\s*["\'][^"\']*test[^"\']*["\']',
            ]

            for pattern in hardcoded_patterns:
                matches = re.finditer(pattern, content)
                for match in matches:
                    # Get line number
                    line_num = content[: match.start()].count("\n") + 1

                    # Check if it's using the helper function
                    line_content = content.split("\n")[line_num - 1]
                    if "get_user_id(" in line_content or "get_api_key_id(" in line_content:
                        # Good - using helper
                        continue

                    violations.append(
                        {
                            "file": str(file_path),
                            "line": line_num,
                            "content": match.group(0),
                            "full_line": line_content.strip(),
                        }
                    )

        if violations:
            violation_details = "\n".join([f"  {v['file']}:{v['line']} - {v['content']}" for v in violations])

            pytest.fail(
                f"Found {len(violations)} hardcoded test IDs!\n"
                f"{violation_details}\n\n"
                f"Hardcoded IDs cause pytest-xdist worker pollution:\n"
                f"- Tests running in parallel share same IDs\n"
                f"- Data corruption across workers\n"
                f"- Intermittent test failures\n\n"
                f"Fix: Use worker-safe ID helpers:\n"
                f"  from tests.conftest import get_user_id, get_api_key_id\n"
                f"  user_id = get_user_id('pref_user')  # instead of 'test_pref_user'\n"
                f"  api_key_id = get_api_key_id('key1')  # instead of 'test_key_1'\n"
            )

    def test_worker_safe_helpers_exist(self):
        """
        Test that worker-safe ID helper functions exist in conftest.py
        """
        conftest = Path("tests/conftest.py")
        assert conftest.exists(), "tests/conftest.py not found"

        content = conftest.read_text()

        # Check that helpers are defined
        assert "def get_user_id(" in content, (
            "get_user_id() helper not found in conftest.py!\nThis helper is required for worker-safe test IDs"
        )

        assert "def get_api_key_id(" in content, (
            "get_api_key_id() helper not found in conftest.py!\nThis helper is required for worker-safe test IDs"
        )

    def test_cleanup_queries_use_worker_specific_pattern(self):
        """
        Test that cleanup queries use worker-specific patterns.

        XDIST ISOLATION FIX (2025-11-30): Cleanup queries must use worker-specific
        patterns like 'user:test_{worker_id}_%' to prevent race conditions when
        multiple xdist workers clean up each other's data.

        The pattern is built dynamically using os.getenv("PYTEST_XDIST_WORKER", "gw0")
        and passed as a parameterized query ($1) to avoid SQL injection.
        """
        files_to_check = [
            Path("tests/integration/compliance/test_postgres_preferences_store.py"),
            Path("tests/integration/compliance/test_postgres_conversation_store.py"),
        ]

        for file_path in files_to_check:
            if not file_path.exists():
                continue

            content = file_path.read_text()

            # Check for worker-specific cleanup pattern:
            # 1. Must use PYTEST_XDIST_WORKER environment variable
            # 2. Must use parameterized query ($1) for safety
            assert "PYTEST_XDIST_WORKER" in content, (
                f"{file_path}: Cleanup queries must use PYTEST_XDIST_WORKER for worker isolation\n"
                "This prevents race conditions in pytest-xdist parallel execution"
            )
            assert "LIKE $1" in content, (
                f"{file_path}: Cleanup queries must use parameterized pattern ($1)\n"
                "This ensures safe, worker-specific cleanup without SQL injection"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
