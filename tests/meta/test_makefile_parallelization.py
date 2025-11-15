"""
Meta-test to validate that Makefile test targets are properly parallelized.

TDD Approach:
1. Write this test FIRST to enforce parallelization (RED)
2. Add `-n auto` to Makefile targets (GREEN)
3. Verify this test passes (REFACTOR)

This ensures we never accidentally remove parallelization from test targets.
"""

import gc
import re
from pathlib import Path

import pytest


@pytest.mark.xdist_group(name="testmakefileparallelization")
class TestMakefileParallelization:
    """Validate that test targets in Makefile use pytest-xdist for parallelization."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.unit
    def test_test_ci_uses_parallel_execution(self):
        """
        test-ci should use -n auto for parallel execution to match CI behavior.

        GIVEN: The test-ci target in Makefile
        WHEN: Reading the Makefile
        THEN: test-ci should include -n auto flag
        """
        makefile = Path("Makefile")
        assert makefile.exists(), "Makefile not found"

        content = makefile.read_text()

        # Find test-ci target
        test_ci_pattern = r"test-ci:.*?\n\t.*?\$\(PYTEST\)([^\n]+)"
        match = re.search(test_ci_pattern, content, re.DOTALL)

        assert match, "test-ci target not found in Makefile"

        pytest_args = match.group(1)
        assert "-n auto" in pytest_args, (
            f"test-ci should use '-n auto' for parallel execution\n"
            f"Found: {pytest_args}\n"
            f"Expected: Should contain '-n auto'"
        )

    @pytest.mark.unit
    def test_test_mcp_server_uses_parallel_execution(self):
        """
        test-mcp-server should use -n auto for parallel execution.

        GIVEN: The test-mcp-server target in Makefile
        WHEN: Reading the Makefile
        THEN: test-mcp-server should include -n auto flag
        """
        makefile = Path("Makefile")
        content = makefile.read_text()

        # Find test-mcp-server target
        pattern = r"test-mcp-server:.*?\n\t.*?\$\(PYTEST\)([^\n]+)"
        match = re.search(pattern, content, re.DOTALL)

        assert match, "test-mcp-server target not found in Makefile"

        pytest_args = match.group(1)
        assert "-n auto" in pytest_args, (
            f"test-mcp-server should use '-n auto' for parallel execution\n" f"Found: {pytest_args}"
        )

    @pytest.mark.unit
    def test_test_new_uses_parallel_execution(self):
        """
        test-new should use -n auto for parallel execution.

        GIVEN: The test-new target in Makefile
        WHEN: Reading the Makefile
        THEN: test-new should include -n auto flag
        """
        makefile = Path("Makefile")
        content = makefile.read_text()

        # Find test-new target
        pattern = r"test-new:.*?\n\t.*?\$\(PYTEST\)([^\n]+)"
        match = re.search(pattern, content, re.DOTALL)

        assert match, "test-new target not found in Makefile"

        pytest_args = match.group(1)
        assert "-n auto" in pytest_args, f"test-new should use '-n auto' for parallel execution\n" f"Found: {pytest_args}"

    @pytest.mark.unit
    def test_test_integration_local_uses_parallel_execution(self):
        """
        test-integration-local should use -n auto for parallel execution.

        GIVEN: The test-integration-local target in Makefile
        WHEN: Reading the Makefile
        THEN: test-integration-local should include -n auto flag
        """
        makefile = Path("Makefile")
        content = makefile.read_text()

        # Find test-integration-local target
        pattern = r"test-integration-local:.*?\n\t.*?\$\(PYTEST\)([^\n]+)"
        match = re.search(pattern, content, re.DOTALL)

        assert match, "test-integration-local target not found in Makefile"

        pytest_args = match.group(1)
        assert "-n auto" in pytest_args, (
            f"test-integration-local should use '-n auto' for parallel execution\n" f"Found: {pytest_args}"
        )

    @pytest.mark.unit
    def test_test_e2e_uses_parallel_execution(self):
        """
        test-e2e should use -n auto for parallel execution.

        GIVEN: The test-e2e target in Makefile
        WHEN: Reading the Makefile
        THEN: test-e2e should include -n auto flag
        """
        makefile = Path("Makefile")
        content = makefile.read_text()

        # Find test-e2e target (it has multiple lines before pytest call)
        pattern = r"test-e2e:.*?\$\(PYTEST\)([^\n]+)"
        match = re.search(pattern, content, re.DOTALL)

        assert match, "test-e2e target not found in Makefile"

        pytest_args = match.group(1)
        assert "-n auto" in pytest_args, f"test-e2e should use '-n auto' for parallel execution\n" f"Found: {pytest_args}"

    @pytest.mark.unit
    def test_parallelized_targets_mention_parallel_in_output(self):
        """
        Parallelized targets should mention 'parallel' in their echo messages for clarity.

        GIVEN: Parallelized test targets (test-ci, test-mcp-server, test-new, etc.)
        WHEN: Reading their echo messages
        THEN: Should mention 'parallel execution' or similar for user awareness
        """
        makefile = Path("Makefile")
        content = makefile.read_text()

        targets_to_check = [
            "test-ci",
            "test-mcp-server",
            "test-new",
            "test-integration-local",
            "test-e2e",
        ]

        for target in targets_to_check:
            # Find the target and its first echo statement
            pattern = rf"{target}:.*?\n\t@echo \"([^\"]+)\""
            match = re.search(pattern, content)

            assert match, f"{target} target not found in Makefile"

            echo_message = match.group(1)
            assert "parallel" in echo_message.lower(), (
                f"{target} should mention 'parallel' in its echo message for clarity\n"
                f"Found: {echo_message}\n"
                f"Expected: Should contain 'parallel' (case-insensitive)"
            )


@pytest.mark.xdist_group(name="testmakefileparallelizationbestpractices")
class TestMakefileParallelizationBestPractices:
    """Validate best practices for parallelized test targets."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.unit
    def test_all_unit_test_targets_are_parallelized(self):
        """
        All test targets that run unit tests should use -n auto.

        GIVEN: Test targets that run unit tests (marked with -m unit)
        WHEN: Reading the Makefile
        THEN: All such targets should use -n auto for optimal performance
        """
        makefile = Path("Makefile")
        content = makefile.read_text()

        # Find all pytest commands with -m unit marker
        # Use word boundary to match complete target names
        pattern = r"^([\w-]+):\s*\n(?:.*?\n)*?\t[^#\n]*\$\(PYTEST\)([^\n]*-m\s+unit[^\n]*)"
        matches = re.findall(pattern, content, re.MULTILINE)

        targets_without_parallel = []
        for target_name, pytest_args in matches:
            if "-n auto" not in pytest_args:
                targets_without_parallel.append(target_name)

        # Known exceptions that should run serially
        exceptions = [
            "test-unit-fast",  # Deprecated target
            "test-debug",  # Uses --pdb, must be serial
            "test-fast",  # Already parallelized according to analysis
            "fast",  # Alias or variant
        ]

        targets_without_parallel = [t for t in targets_without_parallel if t not in exceptions]

        assert not targets_without_parallel, (
            f"The following unit test targets should use '-n auto':\n"
            f"{', '.join(targets_without_parallel)}\n"
            f"\nUnit tests benefit significantly from parallel execution.\n"
            f"Add '-n auto' to the pytest command for better performance."
        )
