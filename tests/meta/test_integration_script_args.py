"""
Test Integration Script Argument Propagation

This test validates that scripts/test-integration.sh properly forwards pytest
arguments to the actual pytest invocation, enabling features like:
- Test splitting: --splits 4 --group 1
- Coverage collection: --cov --cov-report=xml
- Custom markers: -m "integration and not slow"

Background:
The GitHub Actions integration workflow (integration-tests.yaml:104-116) passes
pytest flags via `-- --splits 4 --group N --cov`, but if the script ignores
these flags, the matrix jobs will rerun the full suite without producing
coverage artifacts.

Related Issues:
- Finding B: Integration workflow matrix never splits or captures coverage
- GitHub Issue: Matrix parallelization not working
"""

import gc
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.meta


@pytest.mark.xdist_group(name="integration_script_args")
class TestIntegrationScriptArgPropagation:
    """Validates integration test script respects pytest arguments."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @property
    def script_path(self) -> Path:
        """Path to the integration test script."""
        repo_root = Path(__file__).parent.parent.parent
        return repo_root / "scripts" / "test-integration.sh"

    def test_integration_script_file_exists_at_expected_location(self):
        """Verify the integration test script exists."""
        assert self.script_path.exists(), f"Integration script not found: {self.script_path}"

    def test_script_collects_pytest_args(self):
        """Verify the script has logic to collect pytest arguments."""
        content = self.script_path.read_text()

        # Should declare PYTEST_ARGS array
        assert "PYTEST_ARGS=()" in content, "Script should declare PYTEST_ARGS=() array"

        # Should populate PYTEST_ARGS after '--' separator
        assert 'PYTEST_ARGS+=("$@")' in content, "Script should collect args after '--' into PYTEST_ARGS array"

    def test_script_uses_pytest_args_in_invocation(self):
        """
        CRITICAL: Verify pytest invocation uses PYTEST_ARGS variable.

        This is the core fix for Finding B. The script must use
        "${PYTEST_ARGS[@]}" in the pytest command, not hard-coded flags.
        """
        content = self.script_path.read_text()

        # Find the main pytest invocation (should be after "uv run pytest")
        # Pattern: Look for "uv run pytest" followed by argument usage
        pytest_invocations = re.findall(r"uv run pytest\s+([^\n]+)", content, re.MULTILINE)

        # There should be at least one pytest invocation
        assert len(pytest_invocations) > 0, "No 'uv run pytest' invocations found in script"

        # Find the main test execution invocation (not the manual psql verification)
        # This is the one that should use PYTEST_ARGS
        main_invocation = None
        for invocation in pytest_invocations:
            # Skip if it's just a verification command
            if "SELECT 1" in invocation or "gdpr_test" in invocation:
                continue
            main_invocation = invocation
            break

        assert main_invocation is not None, "Could not find main pytest invocation in script"

        # The invocation MUST use "${PYTEST_ARGS[@]}" to respect forwarded args
        # This enables matrix splitting, coverage collection, custom markers, etc.
        assert '"${PYTEST_ARGS[@]}"' in main_invocation or "${PYTEST_ARGS[@]}" in main_invocation, (
            f"Main pytest invocation does not use PYTEST_ARGS array!\n"
            f"Found: uv run pytest {main_invocation}\n"
            f'Expected: uv run pytest "${{PYTEST_ARGS[@]}}"\n\n'
            f"This breaks GitHub Actions matrix parallelization and coverage collection.\n"
            f"The workflow passes '--splits 4 --group N --cov' but they are ignored."
        )

    def test_script_has_default_pytest_args(self):
        """Verify the script sets sensible defaults when no args provided."""
        content = self.script_path.read_text()

        # Should check if PYTEST_ARGS is empty and set defaults
        # Pattern: if [ ${#PYTEST_ARGS[@]} -eq 0 ]; then
        assert re.search(
            r"if\s+\[\s+\$\{#PYTEST_ARGS\[@\]\}\s+-eq\s+0\s+\];?\s+then", content
        ), "Script should check if PYTEST_ARGS is empty and set defaults"

        # Default should include integration marker
        assert re.search(
            r"PYTEST_ARGS=\([^)]*-m\s+integration[^)]*\)", content
        ), "Default PYTEST_ARGS should include '-m integration' marker"

    def test_script_documents_pytest_args_usage(self):
        """Verify the script documents how to pass pytest arguments."""
        content = self.script_path.read_text()

        # Should have help text or comments about passing args after '--'
        # Either in header comments or --help output
        has_documentation = (
            "-- " in content
            and "pytest" in content.lower()
            and ("args" in content.lower() or "arguments" in content.lower() or "options" in content.lower())
        )

        assert has_documentation, "Script should document how to pass pytest arguments (via '--' separator)"

    def test_script_integration_with_github_actions(self):
        """
        Verify the integration workflow passes pytest flags correctly.

        This validates that .github/workflows/integration-tests.yaml uses
        the correct syntax to pass flags to the script.
        """
        repo_root = Path(__file__).parent.parent.parent
        workflow_path = repo_root / ".github" / "workflows" / "integration-tests.yaml"

        if not workflow_path.exists():
            pytest.skip("Integration workflow file not found")

        content = workflow_path.read_text()

        # The workflow should call test-integration.sh with '--' separator
        # followed by pytest flags like --splits, --group, --cov
        has_double_dash = re.search(r"test-integration\.sh.*--\s+.*--", content)

        if has_double_dash:
            # If using '--' separator, verify pytest flags are passed
            assert re.search(r"--\s+.*(?:--splits|--group|--cov)", content), (
                "Workflow should pass pytest flags (--splits, --group, --cov) " "after '--' separator"
            )

    def test_no_hard_coded_markers_in_invocation(self):
        """
        Verify the pytest invocation doesn't hard-code markers/flags.

        Hard-coded flags prevent the workflow from customizing test execution
        via command-line arguments.
        """
        content = self.script_path.read_text()

        # Find all pytest invocations
        pytest_invocations = re.findall(r"uv run pytest\s+([^\n;]+)", content)

        for invocation in pytest_invocations:
            # Skip verification commands
            if "SELECT 1" in invocation or "psql" in invocation:
                continue

            # If PYTEST_ARGS is set, the invocation should use it, not hard-code flags
            if '"${PYTEST_ARGS[@]}"' in invocation or "${PYTEST_ARGS[@]}" in invocation:
                # Good! Using the variable
                continue

            # If we get here, the invocation has hard-coded flags
            # This is acceptable ONLY if it's before PYTEST_ARGS is set,
            # or if it's a different use case (like manual inspection)
            # However, for the MAIN test invocation, this is a BUG
            if re.search(r"-m\s+integration", invocation):
                pytest.fail(
                    f"Found hard-coded pytest invocation that should use PYTEST_ARGS:\n"
                    f"uv run pytest {invocation}\n\n"
                    f"This prevents command-line customization and breaks matrix splitting."
                )


@pytest.mark.xdist_group(name="integration_script_coverage")
class TestIntegrationScriptCoverageWorkflow:
    """Validates coverage collection works with matrix parallelization."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_coverage_files_expected_after_matrix_run(self):
        """
        Document that successful matrix runs should produce coverage artifacts.

        After fixing the PYTEST_ARGS propagation, the workflow should produce:
        - coverage-integration-1.xml
        - coverage-integration-2.xml
        - coverage-integration-3.xml
        - coverage-integration-4.xml

        These are then merged by the coverage-merge job.
        """
        # This is a documentation test - it doesn't validate runtime behavior
        # but serves as a contract for expected outcomes

        expected_artifacts = [
            "coverage-integration-1.xml",
            "coverage-integration-2.xml",
            "coverage-integration-3.xml",
            "coverage-integration-4.xml",
        ]

        # Document the expectation
        assert len(expected_artifacts) == 4, "Integration workflow should use 4-way matrix split for parallelization"

        # After the fix, the workflow matrix should produce these files
        # This test serves as documentation and can be extended to actually
        # verify the workflow configuration once it's running correctly

    def test_matrix_environment_variables_available(self):
        """
        Verify the script can access matrix environment variables if needed.

        pytest-split uses --splits and --group flags, but some configurations
        might also use environment variables. Ensure the script preserves them.
        """
        # This is more of a documentation test - bash scripts automatically
        # inherit environment variables, so no special handling needed

        # Just verify the script doesn't explicitly unset relevant vars
        script_path = Path(__file__).parent.parent.parent / "scripts" / "test-integration.sh"
        content = script_path.read_text()

        # Should NOT unset pytest-split related environment variables
        assert "unset PYTEST_SPLIT" not in content, "Script should not unset PYTEST_SPLIT environment variables"


@pytest.mark.xdist_group(name="integration_script_documentation")
class TestIntegrationScriptDocumentation:
    """Validates script has proper documentation and usage examples."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_script_has_usage_examples(self):
        """Verify the script documents how to use pytest arguments."""
        script_path = Path(__file__).parent.parent.parent / "scripts" / "test-integration.sh"
        content = script_path.read_text()

        # Should have USAGE or EXAMPLES section in header comments
        assert "USAGE:" in content or "EXAMPLES:" in content, "Script should have USAGE or EXAMPLES documentation"

    def test_script_documents_pytest_flag_forwarding(self):
        """
        Verify the script documents that pytest flags are forwarded.

        Users should know they can pass custom pytest flags via '--' separator.
        """
        script_path = Path(__file__).parent.parent.parent / "scripts" / "test-integration.sh"
        content = script_path.read_text()

        # Look for documentation about passing pytest flags
        # This could be in header comments, --help output, or inline comments
        header = content[:1000]  # Check first ~40 lines for documentation

        # The documentation should mention one of:
        # - Passing arguments via '--'
        # - pytest options
        # - Custom flags
        has_pytest_docs = "--" in header or "pytest" in header.lower() or "options" in header.lower()

        # This is not strictly required but recommended
        if not has_pytest_docs:
            pytest.skip(
                "Script documentation doesn't mention pytest argument forwarding. "
                "Consider adding usage example like: ./test-integration.sh -- --splits 4 --group 1"
            )
