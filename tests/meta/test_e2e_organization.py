"""
Meta-tests validating E2E test organization and tooling correctness.

These tests ensure:
1. E2E journey tests are in the correct location (tests/e2e/)
2. E2E completion tracking script references the correct path
3. E2E test markers are properly configured
4. E2E infrastructure helpers are properly organized

Reference: Testing Infrastructure Validation (2025-11-21)
Finding: Broken E2E tracking tooling - script pointed to wrong path
"""

import ast
import gc
import re
from pathlib import Path

import pytest

# Mark as unit+meta test to ensure it runs in CI (validates test infrastructure)
pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="teste2eorganization")
class TestE2EOrganization:
    """Validate that E2E tests are correctly organized and tooling works."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_e2e_journey_file_exists_in_correct_location(self):
        """
        Validate test_full_user_journey.py exists in tests/e2e/.

        FINDING: E2E journey tests were incorrectly located in tests/integration/e2e/
        causing the check_e2e_completion.py script to fail.

        References:
        - tests/e2e/test_full_user_journey.py - Main E2E journey test file
        - scripts/check_e2e_completion.py - E2E completion tracking script
        """
        e2e_journey_file = Path(__file__).parent.parent / "e2e" / "test_full_user_journey.py"

        assert e2e_journey_file.exists(), (
            f"E2E journey test file not found at {e2e_journey_file}. "
            f"Expected location: tests/e2e/test_full_user_journey.py"
        )

        # Validate it's a real test file with content
        content = e2e_journey_file.read_text()
        assert "async def test_" in content, "File exists but doesn't appear to contain E2E tests"
        # Accept either module-level pytestmark or class/method-level decorator
        has_e2e_marker = "pytestmark = pytest.mark.e2e" in content or "@pytest.mark.e2e" in content
        assert has_e2e_marker, (
            "E2E journey tests should have pytest.mark.e2e marker "
            "(either 'pytestmark = pytest.mark.e2e' or '@pytest.mark.e2e')"
        )

    def test_check_e2e_completion_script_references_correct_path(self):
        """
        Validate scripts/check_e2e_completion.py points to correct E2E test file.

        FINDING: Script was hardcoded to tests/e2e/test_full_user_journey.py but
        file was actually at tests/integration/e2e/test_full_user_journey.py.

        References:
        - scripts/check_e2e_completion.py:17 - E2E_TEST_FILE path constant
        """
        script_path = Path(__file__).parent.parent.parent / "scripts" / "check_e2e_completion.py"

        assert script_path.exists(), f"check_e2e_completion.py not found at {script_path}"

        content = script_path.read_text()

        # Parse AST to find E2E_TEST_FILE constant
        tree = ast.parse(content)

        e2e_test_file_value = None
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "E2E_TEST_FILE":
                        # Extract the path from the assignment
                        # Should be: REPO_ROOT / "tests" / "e2e" / "test_full_user_journey.py"
                        e2e_test_file_value = ast.unparse(node.value)
                        break

        assert e2e_test_file_value is not None, "E2E_TEST_FILE constant not found in check_e2e_completion.py"

        # Validate the path includes correct segments (ast.unparse uses single quotes)
        assert "'tests'" in e2e_test_file_value, f"E2E_TEST_FILE should reference 'tests' directory: {e2e_test_file_value}"
        assert "'e2e'" in e2e_test_file_value, f"E2E_TEST_FILE should reference 'e2e' directory: {e2e_test_file_value}"
        assert (
            "'test_full_user_journey.py'" in e2e_test_file_value
        ), f"E2E_TEST_FILE should reference test_full_user_journey.py: {e2e_test_file_value}"

        # Should NOT include "integration" in the path
        assert (
            "'integration'" not in e2e_test_file_value
        ), f"E2E_TEST_FILE should NOT include 'integration' directory (legacy location): {e2e_test_file_value}"

    def test_e2e_infrastructure_helpers_exist(self):
        """
        Validate E2E infrastructure helpers remain accessible.

        E2E infrastructure (helpers, real clients, keycloak config) should
        remain in tests/e2e/ as shared utilities.

        References:
        - tests/e2e/helpers.py - E2E test helper functions
        - tests/e2e/real_clients.py - Real client implementations
        - tests/e2e/keycloak-test-realm.json - Keycloak test configuration
        """
        e2e_dir = Path(__file__).parent.parent / "e2e"

        helpers_file = e2e_dir / "helpers.py"
        assert helpers_file.exists(), f"E2E helpers file not found at {helpers_file}"

        real_clients_file = e2e_dir / "real_clients.py"
        assert real_clients_file.exists(), f"E2E real clients file not found at {real_clients_file}"

        keycloak_config = e2e_dir / "keycloak-test-realm.json"
        assert keycloak_config.exists(), f"Keycloak test realm config not found at {keycloak_config}"

    def test_no_e2e_journeys_in_integration_directory(self):
        """
        Validate that E2E journey tests are NOT in tests/integration/e2e/.

        This directory structure was confusing - integration tests should
        not contain E2E subdirectories.

        PREVENTION: Ensure we don't regress back to the old structure.
        """
        old_location = Path(__file__).parent.parent / "integration" / "e2e"

        if old_location.exists():
            # If directory exists, ensure it doesn't have test_full_user_journey.py
            journey_file = old_location / "test_full_user_journey.py"
            assert not journey_file.exists(), (
                f"test_full_user_journey.py found in legacy location {old_location}. "
                f"E2E journey tests should be in tests/e2e/, not tests/integration/e2e/."
            )

    def test_e2e_completion_script_can_find_test_file(self):
        """
        Integration test: Validate the check_e2e_completion.py script can actually
        find and read the E2E journey test file.

        This test imports the script and validates it doesn't raise FileNotFoundError.
        """
        import sys
        from pathlib import Path

        # Add scripts directory to path temporarily
        scripts_dir = Path(__file__).parent.parent.parent / "scripts"
        sys.path.insert(0, str(scripts_dir))

        try:
            # Import the module - this will execute the module-level code
            # We'll catch any import errors related to missing files
            from check_e2e_completion import E2E_TEST_FILE

            # Validate the resolved path exists
            assert E2E_TEST_FILE.exists(), f"check_e2e_completion.py's E2E_TEST_FILE path doesn't exist: {E2E_TEST_FILE}"

            # Validate it's readable
            content = E2E_TEST_FILE.read_text()
            assert len(content) > 0, f"E2E test file at {E2E_TEST_FILE} is empty"

        finally:
            # Clean up sys.path
            if str(scripts_dir) in sys.path:
                sys.path.remove(str(scripts_dir))
