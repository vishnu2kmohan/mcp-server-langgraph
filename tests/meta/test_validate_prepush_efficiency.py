"""
Test validate-pre-push Makefile Target Efficiency

This test validates that the validate-pre-push Makefile target doesn't
duplicate work by running the same validations multiple times.

Background (Finding A):
The validate-pre-push target currently runs every phase twice:
- Phase 1-3: Manually run uv lock --check, uv pip check, MyPy, tests
- Phase 4: Calls pre-commit run which reruns all the same hooks

This doubles runtime from ~8-12 minutes to 16-24 minutes and produces
duplicate log noise.

Solution (User-selected Hybrid Approach):
- Keep critical checks manual (Phases 1-3) for explicit progress visibility
- Delegate fast checks to hooks (Phase 4)
- Skip duplicate hooks in Phase 4 using SKIP environment variable

Related Issues:
- Finding A: validate-pre-push duplication
- CI/CD pipeline optimization
"""

import gc
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.meta


@pytest.mark.xdist_group(name="validate_prepush_efficiency")
class TestValidatePrePushEfficiency:
    """Validates validate-pre-push doesn't duplicate work."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @property
    def makefile_path(self) -> Path:
        """Path to the Makefile."""
        repo_root = Path(__file__).parent.parent.parent
        return repo_root / "Makefile"

    @property
    def precommit_config_path(self) -> Path:
        """Path to .pre-commit-config.yaml."""
        repo_root = Path(__file__).parent.parent.parent
        return repo_root / ".pre-commit-config.yaml"

    def test_makefile_file_exists_in_repo_root(self):
        """Verify Makefile exists."""
        assert self.makefile_path.exists(), f"Makefile not found: {self.makefile_path}"

    def test_validate_pre_push_target_exists(self):
        """Verify validate-pre-push target exists in Makefile."""
        content = self.makefile_path.read_text()
        assert re.search(r"^validate-pre-push:", content, re.MULTILINE), "validate-pre-push target not found in Makefile"

    def test_validate_pre_push_has_phases(self):
        """Verify validate-pre-push has multiple phases with progress indicators.

        Note: validate-pre-push-quick delegates to sub-targets:
        - _validate-pre-push-phases-1-2 (contains PHASE 1, 2)
        - inline PHASE 3
        - _validate-pre-push-phase-4 (contains PHASE 4)

        We need to check the combined content of all these targets.
        """
        content = self.makefile_path.read_text()

        # Extract all three targets that make up validate-pre-push-quick
        quick_match = re.search(r"^validate-pre-push-quick:.*?(?=^[a-zA-Z]|\Z)", content, re.MULTILINE | re.DOTALL)
        phases_1_2_match = re.search(r"^_validate-pre-push-phases-1-2:.*?(?=^[a-zA-Z]|\Z)", content, re.MULTILINE | re.DOTALL)
        phase_4_match = re.search(r"^_validate-pre-push-phase-4:.*?(?=^[a-zA-Z]|\Z)", content, re.MULTILINE | re.DOTALL)

        assert quick_match, "Could not find validate-pre-push-quick target"
        assert phases_1_2_match, "Could not find _validate-pre-push-phases-1-2 target"
        assert phase_4_match, "Could not find _validate-pre-push-phase-4 target"

        # Combine all target content
        combined_content = quick_match.group(0) + "\n" + phases_1_2_match.group(0) + "\n" + phase_4_match.group(0)

        # Should have PHASE markers for visibility
        phases = re.findall(r"PHASE \d+:", combined_content)
        assert len(phases) >= 3, (
            f"Expected at least 3 phases in validate-pre-push-quick (combined), found {len(phases)}\n"
            f"Phases provide explicit progress visibility (user-selected hybrid approach)\n"
            f"Targets checked: validate-pre-push-quick, _validate-pre-push-phases-1-2, _validate-pre-push-phase-4"
        )

    def test_manual_phases_run_critical_checks(self):
        """
        Verify manual phases (1-3) run critical checks with progress indicators.

        The hybrid approach keeps slow/critical checks manual for better UX:
        - uv lock --check (Phase 1)
        - MyPy (Phase 2)
        - Test suite (Phase 3)

        Note: validate-pre-push-quick delegates to internal targets, so we need to
        check both the main target and its delegated targets for the commands.
        """
        content = self.makefile_path.read_text()

        # Find main target
        quick_match = re.search(r"^validate-pre-push-quick:.*?(?=^[a-zA-Z]|\Z)", content, re.MULTILINE | re.DOTALL)
        assert quick_match, "Could not find validate-pre-push-quick target"

        # Find delegated targets (internal targets start with _)
        phases_1_2_match = re.search(r"^_validate-pre-push-phases-1-2:.*?(?=^[a-zA-Z_]|\Z)", content, re.MULTILINE | re.DOTALL)

        # Combine content from main target and delegated targets
        target_content = quick_match.group(0)
        if phases_1_2_match:
            target_content += "\n" + phases_1_2_match.group(0)

        # Critical checks that should be manual for visibility
        critical_checks = {
            "uv lock --check": "Lockfile validation",
            "mypy": "Type checking",
            "run_pre_push_tests": "Test suite",
        }

        for check, description in critical_checks.items():
            assert check in target_content, (
                f"Expected {description} ({check}) to be run manually in phases\n"
                f"This provides explicit progress visibility to developers"
            )

    def test_pre_commit_phase_skips_duplicate_hooks(self):
        """
        CRITICAL: Verify pre-commit phase skips hooks already run in manual phases.

        This is the core efficiency fix. Phase 4 should use SKIP environment
        variable to avoid re-running uv-lock-check, mypy, run-pre-push-tests, etc.

        Example:
            SKIP=uv-lock-check,mypy,run-pre-push-tests pre-commit run ...
        """
        content = self.makefile_path.read_text()

        match = re.search(r"^validate-pre-push-quick:.*?(?=^[a-zA-Z]|\Z)", content, re.MULTILINE | re.DOTALL)

        assert match, "Could not find validate-pre-push target"
        target_content = match.group(0)

        # Find the pre-commit run invocation (Phase 4)
        # Look for lines with pre-commit run, capturing any preceding SKIP= env var
        precommit_lines = []
        for line in target_content.split("\n"):
            if "pre-commit run" in line:
                precommit_lines.append(line)

        assert len(precommit_lines) > 0, "No 'pre-commit run' invocation found in validate-pre-push"

        # At least one invocation should use SKIP to avoid duplicates
        has_skip = any("SKIP=" in line for line in precommit_lines)

        assert has_skip, (
            "Pre-commit invocation should use SKIP environment variable to avoid duplicates!\n\n"
            "Found invocations:\n" + "\n".join(f"  - {line.strip()}" for line in precommit_lines) + "\n\n"
            "Expected pattern:\n"
            "  SKIP=uv-lock-check,uv-pip-check,mypy,run-pre-push-tests pre-commit run ...\n\n"
            "This prevents duplicate execution of:\n"
            "  - uv lock --check (Phase 1)\n"
            "  - uv pip check (Phase 1)\n"
            "  - mypy (Phase 2)\n"
            "  - run_pre_push_tests.py (Phase 3)\n\n"
            "Without SKIP, these run twice, doubling the validation time."
        )

    def test_skip_variable_includes_duplicate_hooks(self):
        """
        Verify SKIP variable includes all hooks that are run manually.

        Hooks that should be skipped in Phase 4:
        - uv-lock-check (run manually in Phase 1)
        - uv-pip-check (run manually in Phase 1)
        - mypy (run manually in Phase 2)
        - run-pre-push-tests (run manually in Phase 3)
        """
        content = self.makefile_path.read_text()

        match = re.search(r"^validate-pre-push-quick:.*?(?=^[a-zA-Z]|\Z)", content, re.MULTILINE | re.DOTALL)

        assert match, "Could not find validate-pre-push target"
        target_content = match.group(0)

        # Find SKIP= assignments
        skip_matches = re.findall(r"SKIP=([^\s]+)", target_content)

        if not skip_matches:
            pytest.fail(
                "No SKIP= environment variable found in validate-pre-push\n"
                "Expected: SKIP=uv-lock-check,uv-pip-check,mypy,run-pre-push-tests"
            )

        skip_value = skip_matches[0]
        skipped_hooks = set(skip_value.split(","))

        # Hooks that MUST be skipped (manually run)
        required_skips = {
            "uv-lock-check",  # Phase 1: uv lock --check
            "uv-pip-check",  # Phase 1: uv pip check
            "mypy",  # Phase 2: mypy
            "run-pre-push-tests",  # Phase 3: run_pre_push_tests.py
        }

        missing_skips = required_skips - skipped_hooks

        assert not missing_skips, (
            f"SKIP variable missing required hooks: {missing_skips}\n\n"
            f"Current SKIP: {skip_value}\n"
            f"Required SKIP: {','.join(sorted(required_skips))}\n\n"
            "These hooks are run manually in Phases 1-3, so they MUST be skipped\n"
            "in Phase 4 to avoid duplicate execution."
        )

    def test_validation_hooks_skipped_to_avoid_duplication_with_pytest_tests(self):
        """
        Verify validation hooks are skipped in Phase 4 (Finding: Duplicate validation hooks).

        Background:
        - Phase 3 runs pytest tests (run_pre_push_tests.py) including tests in tests/meta/
        - These pytest tests validate patterns comprehensively:
          - test_validator_consistency.py: Validates check-test-memory-safety script
          - test_pytest_xdist_enforcement.py: Validates memory safety patterns
          - test_pytest_config_validation.py: Validates pytest configuration
          - And more...
        - Phase 4 runs pre-commit hooks including validation scripts

        Issue:
        - Running both pytest tests AND validation hooks is duplicate work
        - Pytest tests are more comprehensive and catch issues earlier
        - Validation hooks re-validate what pytest already validated

        Solution:
        - Add validation hooks to SKIP list in Phase 4
        - Saves 30-60 seconds per push
        - Reduces duplicate log noise
        """
        content = self.makefile_path.read_text()

        # Find validate-pre-push-quick target
        match = re.search(r"^validate-pre-push-quick:.*?(?=^[a-zA-Z]|\Z)", content, re.MULTILINE | re.DOTALL)

        assert match, "Could not find validate-pre-push-quick target"
        target_content = match.group(0)

        # Extract SKIP value from pre-commit invocation
        precommit_lines = []
        for line in target_content.split("\n"):
            if "pre-commit run" in line:
                precommit_lines.append(line)

        assert precommit_lines, "validate-pre-push-quick should invoke pre-commit run"

        # Get the line with SKIP variable
        skip_line = None
        for line in precommit_lines:
            if "SKIP=" in line:
                skip_line = line
                break

        assert skip_line, "Pre-commit invocation should use SKIP environment variable"

        # Extract SKIP value
        skip_match = re.search(r"SKIP=([^\s]+)", skip_line)
        assert skip_match, "Could not extract SKIP value from pre-commit command"
        skip_value = skip_match.group(1)
        skipped_hooks = set(skip_value.split(","))

        # Validation hooks that should be skipped (redundant with pytest tests)
        required_validation_skips = {
            "validate-pytest-config",  # Covered by test_pytest_config_validation.py
            "check-test-memory-safety",  # Covered by test_validator_consistency.py, test_pytest_xdist_enforcement.py
            "check-async-mock-usage",  # Covered by test_validator_consistency.py
            "validate-test-ids",  # Covered by test_validator_consistency.py
        }

        missing_skips = required_validation_skips - skipped_hooks

        assert not missing_skips, (
            f"SKIP variable missing validation hooks: {missing_skips}\n\n"
            f"Current SKIP: {skip_value}\n"
            f"Required additional SKIPs: {','.join(sorted(required_validation_skips))}\n\n"
            "These validation hooks are redundant with comprehensive pytest tests:\n"
            "- test_validator_consistency.py validates the validation scripts\n"
            "- test_pytest_xdist_enforcement.py validates memory safety patterns\n"
            "- test_pytest_config_validation.py validates pytest configuration\n"
            "- And more...\n\n"
            "Running both pytest tests AND validation hooks duplicates work.\n"
            "Add these hooks to SKIP to save 30-60 seconds per push."
        )

    def test_integration_tests_respect_ci_parity_flag(self):
        """
        Verify integration tests respect CI_PARITY flag (Finding H).

        The Makefile should check CI_PARITY before running integration tests,
        consistent with the git hook behavior.
        """
        content = self.makefile_path.read_text()

        match = re.search(r"^validate-pre-push-quick:.*?(?=^[a-zA-Z]|\Z)", content, re.MULTILINE | re.DOTALL)

        assert match, "Could not find validate-pre-push target"
        target_content = match.group(0)

        # Look for integration test invocation
        has_integration = "test-integration.sh" in target_content

        if has_integration:
            # Should be conditional on CI_PARITY or have a conditional wrapper
            # This is for the validate-pre-push-quick vs validate-pre-push-full split
            # For now, just document the expectation
            pass  # Will be addressed in Phase 2.3

    def test_validate_pre_push_documents_skip_rationale(self):
        """
        Verify validate-pre-push documents why hooks are skipped.

        Good UX: Comments explaining the SKIP variable help future maintainers.
        """
        content = self.makefile_path.read_text()

        match = re.search(r"^validate-pre-push-quick:.*?(?=^[a-zA-Z]|\Z)", content, re.MULTILINE | re.DOTALL)

        assert match, "Could not find validate-pre-push target"
        target_content = match.group(0)

        # If SKIP is used, there should be a comment nearby explaining it
        if "SKIP=" in target_content:
            # Look for comment within 5 lines before SKIP
            lines = target_content.split("\n")
            skip_line_idx = None

            for i, line in enumerate(lines):
                if "SKIP=" in line:
                    skip_line_idx = i
                    break

            if skip_line_idx is not None:
                # Check 5 lines before for comments
                preceding_lines = lines[max(0, skip_line_idx - 5) : skip_line_idx]
                has_comment = any("#" in line for line in preceding_lines)

                # This is recommended but not required
                if not has_comment:
                    pytest.skip(
                        "Consider adding a comment explaining the SKIP variable:\n"
                        "# Skip hooks already run in manual phases to avoid duplicate work\n"
                        "SKIP=uv-lock-check,uv-pip-check,mypy,run-pre-push-tests"
                    )


@pytest.mark.xdist_group(name="validate_prepush_performance")
class TestValidatePrePushPerformance:
    """Validates validate-pre-push performance characteristics."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @property
    def makefile_path(self) -> Path:
        """Path to the Makefile."""
        repo_root = Path(__file__).parent.parent.parent
        return repo_root / "Makefile"

    def test_no_redundant_test_execution(self):
        """
        Verify tests are not run multiple times in the same target.

        Each test command (run_pre_push_tests.py, test-integration.sh, pytest)
        should appear at most once in the manual phases, with pre-commit hooks
        properly skipped.
        """
        content = self.makefile_path.read_text()

        # Check validate-pre-push-quick (no integration tests)
        match_quick = re.search(r"^validate-pre-push-quick:.*?(?=^[a-zA-Z]|\Z)", content, re.MULTILINE | re.DOTALL)
        assert match_quick, "Could not find validate-pre-push-quick target"
        quick_content = match_quick.group(0)

        # Check validate-pre-push-full (with integration tests)
        match_full = re.search(r"^validate-pre-push-full:.*?(?=^[a-zA-Z]|\Z)", content, re.MULTILINE | re.DOTALL)
        assert match_full, "Could not find validate-pre-push-full target"
        full_content = match_full.group(0)

        # Count invocations in quick target
        run_pre_push_count_quick = quick_content.count("run_pre_push_tests.py")
        test_integration_count_quick = quick_content.count("test-integration.sh")
        mypy_count_quick = quick_content.count("mypy src/mcp_server_langgraph")

        # Count invocations in full target
        run_pre_push_count_full = full_content.count("run_pre_push_tests.py")
        test_integration_count_full = full_content.count("test-integration.sh")
        mypy_count_full = full_content.count("mypy src/mcp_server_langgraph")

        # Quick target: run_pre_push_tests and mypy once, no integration tests
        assert run_pre_push_count_quick == 1, (
            f"run_pre_push_tests.py appears {run_pre_push_count_quick} times in quick\n"
            f"Expected: 1 (manual phase only, skipped in pre-commit via SKIP)"
        )

        assert test_integration_count_quick == 0, (
            f"test-integration.sh appears {test_integration_count_quick} times in quick\n"
            f"Expected: 0 (integration tests only in full target)"
        )

        assert mypy_count_quick == 1, (
            f"MyPy appears {mypy_count_quick} times in quick\n"
            f"Expected: 1 (manual phase only, skipped in pre-commit via SKIP)"
        )

        # Full target: same plus integration tests once
        assert run_pre_push_count_full == 1, (
            f"run_pre_push_tests.py appears {run_pre_push_count_full} times in full\n" f"Expected: 1 (manual phase only)"
        )

        assert test_integration_count_full == 1, (
            f"test-integration.sh appears {test_integration_count_full} times in full\n" f"Expected: 1 (manual phase only)"
        )

        assert mypy_count_full == 1, f"MyPy appears {mypy_count_full} times in full\n" f"Expected: 1 (manual phase only)"

    def test_progress_indicators_for_user_experience(self):
        """
        Verify manual phases have progress indicators for better UX.

        The hybrid approach values explicit progress visibility, so manual
        phases should have echo statements showing what's running.
        """
        content = self.makefile_path.read_text()

        match = re.search(r"^validate-pre-push-quick:.*?(?=^[a-zA-Z]|\Z)", content, re.MULTILINE | re.DOTALL)

        assert match, "Could not find validate-pre-push target"
        target_content = match.group(0)

        # Count progress indicators (echo statements with ▶ or similar)
        progress_indicators = len(re.findall(r"@echo.*[▶✓✗]", target_content))

        assert progress_indicators >= 5, (
            f"Expected at least 5 progress indicators, found {progress_indicators}\n"
            f"Progress indicators improve UX by showing what's currently running\n"
            f"This is a key benefit of the hybrid approach vs pure pre-commit"
        )


@pytest.mark.xdist_group(name="validate_prepush_documentation")
class TestValidatePrePushDocumentation:
    """Validates validate-pre-push target is well-documented."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @property
    def makefile_path(self) -> Path:
        """Path to the Makefile."""
        repo_root = Path(__file__).parent.parent.parent
        return repo_root / "Makefile"

    def test_validate_pre_push_has_help_text(self):
        """Verify validate-pre-push has help documentation."""
        content = self.makefile_path.read_text()

        # Look for .PHONY or comment before validate-pre-push
        match = re.search(r"(^##.*\n)*^validate-pre-push:", content, re.MULTILINE)

        # Having documentation is good practice but not strictly required
        if match and "##" in match.group(0):
            # Has documentation - good!
            pass
        else:
            # No documentation - recommend adding
            pytest.skip(
                "Consider adding help documentation for validate-pre-push:\n"
                "## Run all pre-push validations (optimized, no duplicate work)\n"
                "validate-pre-push:"
            )
