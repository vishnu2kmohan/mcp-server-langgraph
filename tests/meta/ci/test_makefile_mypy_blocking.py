"""
Test that Makefile MyPy validation is blocking (fails on errors)

This test ensures local/CI parity by verifying that MyPy errors block
the validate-pre-push target in the Makefile.

Following TDD principles: Write test first, then fix Makefile

Regression prevention for validation audit finding:
- MyPy is non-blocking locally but blocking in CI
- Creates "works locally, fails CI" scenario
"""

import gc
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def read_all_makefiles() -> str:
    """Read Makefile content including all modular includes from make/*.mk"""
    makefile = Path("Makefile")
    assert makefile.exists(), "Makefile not found"
    content = makefile.read_text()

    # Also read all modular makefiles in make/ directory
    make_dir = Path("make")
    if make_dir.exists():
        for mk_file in sorted(make_dir.glob("*.mk")):
            content += "\n" + mk_file.read_text()
    return content


@pytest.mark.xdist_group(name="makefile_mypy_blocking")
class TestMakefileMyPyBlocking:
    """Test that Makefile treats MyPy errors as blocking"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_makefile_mypy_is_blocking(self):
        """
        Test that validate-pre-push target fails when MyPy finds errors.

        RED Phase: This test will FAIL initially because Makefile has:
            || echo "⚠️  MyPy found type errors (non-blocking)"

        GREEN Phase: After fixing Makefile to:
            || (echo "✗ MyPy errors" && exit 1)

        The test should PASS.
        """
        # Read Makefile content including modular includes
        makefile_content = read_all_makefiles()

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
        MyPy can be included directly or via referenced sub-targets like
        validate-pre-push-full, validate-pre-push-quick, or _validate-pre-push-phases-1-2.
        """
        makefile_content = read_all_makefiles()

        # Check that validate-pre-push target exists
        assert "validate-pre-push:" in makefile_content, "validate-pre-push target not found in Makefile"

        # Check that MyPy is run somewhere in the validation chain
        # The modular Makefile uses _validate-pre-push-phases-1-2 which contains mypy
        phases_pattern = r"_validate-pre-push-phases-1-2:.*?mypy"
        full_pattern = r"validate-pre-push-full:.*?mypy"
        quick_pattern = r"validate-pre-push-quick:.*?mypy"
        direct_pattern = r"validate-pre-push:.*?mypy"

        has_mypy = (
            re.search(phases_pattern, makefile_content, re.DOTALL | re.IGNORECASE)
            or re.search(full_pattern, makefile_content, re.DOTALL | re.IGNORECASE)
            or re.search(quick_pattern, makefile_content, re.DOTALL | re.IGNORECASE)
            or re.search(direct_pattern, makefile_content, re.DOTALL | re.IGNORECASE)
        )

        if not has_mypy:
            pytest.fail(
                "validate-pre-push chain does not include MyPy type checking!\n"
                "MyPy should be part of comprehensive pre-push validation\n"
                "Add: MyPy type checking step to validate-pre-push or its sub-targets"
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
        makefile_content = read_all_makefiles()

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
        makefile_content = read_all_makefiles()

        # Search for MyPy execution in validate-pre-push sub-targets and shared internal targets
        # MyPy is in the shared _validate-pre-push-phases-1-2 target
        mypy_lines = []
        in_relevant_target = False
        for line in makefile_content.split("\n"):
            if any(
                x in line for x in ["validate-pre-push-full:", "validate-pre-push-quick:", "_validate-pre-push-phases-1-2:"]
            ):
                in_relevant_target = True
            elif in_relevant_target and line and not line.startswith("\t") and not line.startswith(" "):
                # End of target (next target or section starts)
                if line.startswith("#") or line.startswith("##"):
                    in_relevant_target = False
            elif in_relevant_target and "mypy" in line.lower():
                mypy_lines.append(line)

        if not mypy_lines:
            pytest.fail("No MyPy execution found in validate-pre-push sub-targets")

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
