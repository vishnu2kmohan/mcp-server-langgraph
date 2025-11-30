"""
Test validation optimizations to prevent duplicate execution and ensure parity.

This test module validates the fixes for Codex findings related to test infrastructure
inefficiencies discovered in the comprehensive audit (2025-11-23).

TDD Approach:
1. RED: Write tests that fail with current implementation
2. GREEN: Implement fixes to make tests pass
3. REFACTOR: Clean up code while keeping tests green
"""

import gc
import re
import subprocess
from pathlib import Path

import pytest
import yaml


pytestmark = [pytest.mark.meta, pytest.mark.unit]


@pytest.mark.xdist_group(name="validator_deduplication")
class TestValidatorDeduplication:
    """
    Test that validators don't run twice via validate-fast wrapper AND individual hooks.

    Codex Finding #1: Pre-push hooks run validators twice
    - validate-fast.py executes 11 scripts as a wrapper
    - 4 of those scripts (validate_pytest_config, check_test_memory_safety,
      check_async_mock_usage, validate_test_ids) are ALSO registered as
      individual hooks in .pre-commit-config.yaml
    - Result: These 4 validators execute twice on every git push

    Solution: Remove duplicate scripts from validate_fast.py and rely on
    individual hooks for better fail-fast behavior and clearer error messages.
    """

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def repo_root(self) -> Path:
        """Get repository root directory"""
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
        return Path(result.stdout.strip())

    @pytest.fixture
    def validate_fast_scripts(self, repo_root: Path) -> list[str]:
        """Parse SCRIPTS list from validate_fast.py"""
        validate_fast_file = repo_root / "scripts" / "validators" / "validate_fast.py"
        content = validate_fast_file.read_text()

        # Extract SCRIPTS list using regex
        scripts_match = re.search(r"SCRIPTS = \[(.*?)\]", content, re.DOTALL)
        assert scripts_match, "Could not find SCRIPTS list in validate_fast.py"

        # Extract script paths from the list
        scripts_block = scripts_match.group(1)
        script_paths = re.findall(r'"([^"]+\.py)"', scripts_block)

        # Return just the filenames (not full paths)
        return [Path(script).name for script in script_paths]

    @pytest.fixture
    def individual_hooks(self, repo_root: Path) -> set[str]:
        """Parse individual hook IDs from .pre-commit-config.yaml"""
        precommit_file = repo_root / ".pre-commit-config.yaml"
        with precommit_file.open() as f:
            config = yaml.safe_load(f)

        # Find all hooks in the 'local' repo section
        hook_ids = set()
        for repo in config.get("repos", []):
            if repo.get("repo") == "local":
                for hook in repo.get("hooks", []):
                    hook_id = hook.get("id", "")
                    # We care about validation hooks that might overlap
                    if any(keyword in hook_id for keyword in ["validate", "check", "test"]):
                        hook_ids.add(hook_id)

        return hook_ids

    def test_no_duplicate_validators(self, validate_fast_scripts: list[str], individual_hooks: set[str]):
        """
        Validate that no script in validate_fast.py is also an individual hook.

        This test ensures we don't run the same validator twice:
        - Once via validate-fast wrapper (runs all scripts in SCRIPTS list)
        - Once as an individual hook in .pre-commit-config.yaml

        Expected duplicates that SHOULD be removed from validate_fast.py:
        - validate_pytest_config.py → individual hook: validate-pytest-config
        - check_test_memory_safety.py → individual hook: check-test-memory-safety
        - check_async_mock_usage.py → individual hook: check-async-mock-usage
        - validate_test_ids.py → individual hook: validate-test-ids
        """
        # Map script filenames to their expected hook IDs
        script_to_hook = {
            "validate_pytest_config.py": "validate-pytest-config",
            "check_test_memory_safety.py": "check-test-memory-safety",
            "check_async_mock_usage.py": "check-async-mock-usage",
            "validate_test_ids.py": "validate-test-ids",
        }

        # Find duplicates
        duplicates = []
        for script in validate_fast_scripts:
            expected_hook_id = script_to_hook.get(script)
            if expected_hook_id and expected_hook_id in individual_hooks:
                duplicates.append((script, expected_hook_id))

        # Assert no duplicates
        assert not duplicates, (
            f"Found {len(duplicates)} validators running twice:\n"
            + "\n".join(f"  - {script} (validate-fast) == {hook_id} (individual hook)" for script, hook_id in duplicates)
            + "\n\nSolution: Remove these scripts from validate_fast.py SCRIPTS list. "
            "Keep them as individual hooks for better fail-fast behavior."
        )

    def test_validate_fast_script_count(self, validate_fast_scripts: list[str]):
        """
        Ensure validate-fast has the expected number of scripts after deduplication.

        Original: 11 scripts (including 4 duplicates)
        Expected after fix: 7 scripts (removed 4 duplicates)
        """
        expected_count = 7
        actual_count = len(validate_fast_scripts)

        assert actual_count == expected_count, (
            f"validate_fast.py should have {expected_count} scripts after "
            f"removing duplicates, but found {actual_count}.\n"
            f"Scripts: {validate_fast_scripts}"
        )


@pytest.mark.xdist_group(name="makefile_prepush_parity")
class TestMakefilePrePushParity:
    """
    Test that 'make validate-pre-push' matches actual pre-push hook behavior.

    Codex Finding #2: Makefile pre-push target skips validators that hook runs
    - Makefile sets SKIP=...validate-pytest-config,check-test-memory-safety,...
    - Actual pre-push hook executes these validators
    - Result: "Passed make validate-pre-push" ≠ "Will pass git push"

    Solution: Remove skipped validators from SKIP list so Makefile matches hook.
    """

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def repo_root(self) -> Path:
        """Get repository root directory"""
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
        return Path(result.stdout.strip())

    @pytest.fixture
    def makefile_skip_list(self, repo_root: Path) -> set[str]:
        """Extract SKIP list from Makefile validate-pre-push targets"""
        makefile = repo_root / "Makefile"
        content = makefile.read_text()

        # Find all SKIP= declarations in validate-pre-push targets
        skip_pattern = r"SKIP=([^\s]+)"
        matches = re.findall(skip_pattern, content)

        # Combine all SKIP lists (should be identical across targets)
        all_skipped = set()
        for match in matches:
            skipped_hooks = match.split(",")
            all_skipped.update(skipped_hooks)

        return all_skipped

    @pytest.fixture
    def precommit_hook_ids(self, repo_root: Path) -> set[str]:
        """Get all hook IDs from .pre-commit-config.yaml at pre-push stage"""
        precommit_file = repo_root / ".pre-commit-config.yaml"
        with precommit_file.open() as f:
            config = yaml.safe_load(f)

        hook_ids = set()
        for repo in config.get("repos", []):
            for hook in repo.get("hooks", []):
                # Check if hook runs at pre-push stage
                stages = hook.get("stages", ["pre-commit"])  # Default stage
                if "pre-push" in stages or not stages:  # Empty means all stages
                    hook_id = hook.get("id")
                    if hook_id:
                        hook_ids.add(hook_id)

        return hook_ids

    def test_makefile_does_not_skip_active_hooks(self, makefile_skip_list: set[str], precommit_hook_ids: set[str]):
        """
        Validate that Makefile doesn't skip hooks that run in actual pre-push.

        This test ensures make validate-pre-push provides accurate validation
        that matches what git push will actually execute.

        Problematic SKIP entries (should be removed):
        - validate-pytest-config (runs in actual pre-push hook)
        - check-test-memory-safety (runs in actual pre-push hook)
        - check-async-mock-usage (runs in actual pre-push hook)
        - validate-test-ids (runs in actual pre-push hook)

        Acceptable SKIP entries (already run manually in Makefile):
        - uv-lock-check (explicitly run as separate step)
        - uv-pip-check (explicitly run as separate step)
        - mypy (explicitly run as separate step)
        - run-pre-push-tests (explicitly run as separate step)
        """
        # Hooks that are acceptable to skip (run manually in Makefile)
        acceptable_skips = {
            "uv-lock-check",  # Makefile line 677, 728
            "uv-pip-check",  # Makefile line 680, 731
            "mypy",  # Makefile line 690, 741
            "run-pre-push-tests",  # Makefile line 700, 751
        }

        # Find hooks skipped in Makefile but run in actual pre-push
        problematic_skips = []
        for skip in makefile_skip_list:
            if skip in precommit_hook_ids and skip not in acceptable_skips:
                problematic_skips.append(skip)

        assert not problematic_skips, (
            f"Makefile skips {len(problematic_skips)} hooks that run in actual pre-push:\n"
            + "\n".join(f"  - {hook}" for hook in sorted(problematic_skips))
            + "\n\nThis creates false confidence: 'make validate-pre-push' passes but 'git push' fails.\n"
            "Solution: Remove these from SKIP list in Makefile (lines 711, 763)."
        )

    def test_makefile_skip_list_is_minimal(self, makefile_skip_list: set[str]):
        """
        Ensure Makefile SKIP list contains only necessary entries.

        After fix, SKIP list should only contain hooks explicitly run as
        separate manual steps in the Makefile.
        """
        expected_skips = {
            "uv-lock-check",
            "uv-pip-check",
            "mypy",
            "run-pre-push-tests",
        }

        assert makefile_skip_list == expected_skips, (
            f"Makefile SKIP list should only contain {expected_skips}, "
            f"but found {makefile_skip_list}.\n"
            f"Extra: {makefile_skip_list - expected_skips}\n"
            f"Missing: {expected_skips - makefile_skip_list}"
        )
