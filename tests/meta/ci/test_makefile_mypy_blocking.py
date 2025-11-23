"""
Test that Makefile MyPy validation is blocking (fails on errors)

This test ensures local/CI parity by verifying that MyPy errors block
the validate-pre-push target in the Makefile.

Following TDD principles: Write test first, then fix Makefile

Regression prevention for validation audit finding:
- MyPy is non-blocking locally but blocking in CI
- Creates "works locally, fails CI" scenario
"""

import re
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


class TestMakefileMyPyBlocking:
    """Test that Makefile treats MyPy errors as blocking"""

    def test_makefile_mypy_is_blocking(self):
        """
        Test that validate-pre-push target fails when MyPy finds errors.

        RED Phase: This test will FAIL initially because Makefile has:
            || echo "⚠️  MyPy found type errors (non-blocking)"

        GREEN Phase: After fixing Makefile to:
            || (echo "✗ MyPy errors" && exit 1)

        The test should PASS.
        """
        makefile_path = Path("Makefile")
        assert makefile_path.exists(), "Makefile not found"

        # Read Makefile content
        makefile_content = makefile_path.read_text()

        # Check the validate-pre-push target
        # The MyPy step should exit 1 on failure, not just warn

        # Pattern to find: MyPy execution line in validate-pre-push
        # Should have: && exit 1 on failure
        # Should NOT have: || echo "⚠️ ... (non-blocking)"

        # Check for non-blocking pattern (this is BAD)
        non_blocking_pattern = r"mypy.*\|\|\s*echo.*non-blocking"
        if re.search(non_blocking_pattern, makefile_content, re.IGNORECASE):
            pytest.fail(
                "Makefile has non-blocking MyPy validation!\n"
                "Found: || echo ... (non-blocking)\n\n"
                "This creates local/CI parity gap:\n"
                "- Local: MyPy errors are warnings only\n"
                "- CI: MyPy errors block builds\n\n"
                'Fix: Replace with: || (echo "✗ MyPy errors" && exit 1)\n'
                "Location: validate-pre-push target, MyPy step"
            )

        # Check for blocking pattern (this is GOOD)
        # MyPy should be followed by && echo success || (echo error && exit 1)
        blocking_pattern = r"mypy.*&&.*echo.*\|\|.*exit\s+1"
        if not re.search(blocking_pattern, makefile_content):
            pytest.fail(
                "Makefile does not have blocking MyPy validation!\n"
                "Expected pattern: mypy ... && echo success || (echo error && exit 1)\n\n"
                "Current state: MyPy may not be failing the build on errors\n\n"
                "Fix: Ensure MyPy failures exit with code 1"
            )

    def test_makefile_validate_pre_push_includes_mypy(self):
        """
        Test that validate-pre-push target includes MyPy type checking.

        Ensures MyPy is part of the comprehensive pre-push validation.
        """
        makefile_path = Path("Makefile")
        makefile_content = makefile_path.read_text()

        # Find the validate-pre-push target
        validate_pre_push_section = re.search(r"validate-pre-push:.*?^[a-zA-Z]", makefile_content, re.MULTILINE | re.DOTALL)

        if not validate_pre_push_section:
            pytest.fail("validate-pre-push target not found in Makefile")

        section_content = validate_pre_push_section.group(0)

        # Check that MyPy is mentioned in the target
        if "mypy" not in section_content.lower():
            pytest.fail(
                "validate-pre-push target does not include MyPy type checking!\n"
                "MyPy should be part of comprehensive pre-push validation\n"
                "Add: MyPy type checking step to validate-pre-push"
            )

    def test_makefile_phase_2_includes_mypy(self):
        """
        Test that PHASE 2 in validate-pre-push runs MyPy as critical check.

        The audit log shows validate-pre-push has 4 phases:
        - PHASE 1: Fast checks (lockfile, workflows)
        - PHASE 2: Type checking (MyPy - CRITICAL)
        - PHASE 3: Test suite
        - PHASE 4: Pre-commit hooks

        This test validates PHASE 2 structure.
        """
        makefile_path = Path("Makefile")
        makefile_content = makefile_path.read_text()

        # Find PHASE 2 section
        phase_2_pattern = r"PHASE 2.*?Type Checking.*?mypy"
        if not re.search(phase_2_pattern, makefile_content, re.IGNORECASE | re.DOTALL):
            pytest.fail(
                "PHASE 2 (Type Checking) not found or incorrectly structured!\n"
                "Expected: PHASE 2 section with MyPy as critical check\n"
                "Phase 2 should be blocking and clearly marked as critical"
            )

    def test_mypy_output_pattern_is_blocking(self):
        """
        Test that MyPy success/failure messages indicate blocking behavior.

        Good pattern: "✓ MyPy passed" or "✗ MyPy found type errors" with exit 1
        Bad pattern: "⚠️ MyPy found type errors (non-blocking)" without exit 1
        """
        makefile_path = Path("Makefile")
        makefile_content = makefile_path.read_text()

        # Search for MyPy execution in validate-pre-push
        mypy_lines = []
        in_validate_pre_push = False
        for line in makefile_content.split("\n"):
            if "validate-pre-push:" in line:
                in_validate_pre_push = True
            elif in_validate_pre_push and line and not line.startswith("\t") and not line.startswith(" "):
                # End of target
                break
            elif in_validate_pre_push and "mypy" in line.lower():
                mypy_lines.append(line)

        if not mypy_lines:
            pytest.fail("No MyPy execution found in validate-pre-push target")

        # Check each MyPy line for blocking behavior
        for line in mypy_lines:
            # Should have success/error handling with exit code
            if "echo" in line and "passed" in line.lower():
                # Success case - this is good
                continue
            elif "||" in line and "exit 1" not in line and "echo" in line:
                # Failure case without exit 1 - this is BAD
                pytest.fail(
                    f"MyPy validation is non-blocking!\n"
                    f"Line: {line.strip()}\n\n"
                    f"Failure handling should exit with code 1\n"
                    f"Fix: Add && exit 1 after error message"
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
