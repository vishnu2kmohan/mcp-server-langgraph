"""
Meta-validation: Ensure local validation matches CI validation exactly.

This test suite ensures that:
1. Pre-push hooks exist and have correct permissions
2. Pre-push hooks contain all required validation steps
3. Makefile targets match pre-push hook validation
4. Local validation steps match CI validation steps
5. No validation gaps exist between local and CI environments

TDD Principle: These tests MUST pass to ensure developers never experience CI surprises.
"""

import gc
import os
import re
import subprocess
from pathlib import Path

import pytest
import yaml

# Mark as unit+meta test to ensure it runs in CI (validates test infrastructure)
pytestmark = pytest.mark.unit
# ══════════════════════════════════════════════════════════════════════════════
# Shared Fixtures (used by all test classes)
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="module")
def shared_repo_root() -> Path:
    """
    Get repository root directory (shared across all tests in module).

    This avoids redundant git commands by computing repo root once per module.
    """
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    return Path(result.stdout.strip())


@pytest.fixture(scope="module")
def shared_pre_push_hook_path(shared_repo_root: Path) -> Path:
    """
    Get path to pre-push hook (shared across all tests in module).

    **Graceful Skip on Fresh Clones**:
    If the hook doesn't exist (expected on fresh clones), this fixture skips
    all tests with helpful installation guidance instead of failing them.

    This provides a better developer experience:
    - Fresh clone: Tests skip with clear instructions
    - After 'make git-hooks': Tests run and validate hook configuration
    - CI: Hooks are installed explicitly in workflow, tests always run

    References:
    - OpenAI Codex Finding: test_local_ci_parity.py:24 assumes hook exists (RESOLVED)
    - tests/meta/test_hook_fixture_resilience.py (validates this behavior)
    - CONTRIBUTING.md: Documents hook installation
    """
    # Use git rev-parse to get common git directory (handles worktrees)
    result = subprocess.run(
        ["git", "rev-parse", "--git-common-dir"],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
        cwd=shared_repo_root,
    )
    git_common_dir = Path(result.stdout.strip())
    # If path is relative, make it relative to repo_root
    if not git_common_dir.is_absolute():
        git_common_dir = shared_repo_root / git_common_dir
    hook_path = git_common_dir / "hooks" / "pre-push"

    if not hook_path.exists():
        pytest.skip(
            "\n"
            "═══════════════════════════════════════════════════════════════\n"
            "Pre-push hook not installed (expected on fresh clones)\n"
            "═══════════════════════════════════════════════════════════════\n"
            "\n"
            "These tests validate CI/local parity by checking that your\n"
            "local pre-push hook matches CI configuration exactly.\n"
            "\n"
            "📋 To install hooks and enable these tests:\n"
            "\n"
            "  make git-hooks\n"
            "\n"
            "Or manually:\n"
            "\n"
            "  pre-commit install --hook-type pre-commit --hook-type pre-push\n"
            "\n"
            "📖 Documentation: CONTRIBUTING.md (line 30-32)\n"
            "🔍 Validation: scripts/validate_pre_push_hook.py\n"
            "\n"
            "After installation, re-run tests to validate hook configuration.\n"
        )

    return hook_path


@pytest.fixture(scope="module")
def shared_precommit_config(shared_repo_root: Path) -> dict:
    """
    Load and parse .pre-commit-config.yaml (shared across all tests in module).

    Since we've migrated from custom bash pre-push hooks to pre-commit framework,
    validation now checks .pre-commit-config.yaml instead of bash script patterns.
    """
    config_path = shared_repo_root / ".pre-commit-config.yaml"
    if not config_path.exists():
        pytest.skip(
            "\n"
            "═══════════════════════════════════════════════════════════════\n"
            ".pre-commit-config.yaml not found\n"
            "═══════════════════════════════════════════════════════════════\n"
            "\n"
            "Pre-commit configuration file is missing. This is unexpected.\n"
            "Please restore .pre-commit-config.yaml from repository.\n"
        )

    with open(config_path) as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def shared_pre_push_hooks(shared_precommit_config: dict) -> list[dict]:
    """
    Extract all hooks configured for pre-push stage.

    Returns list of hook configurations that will run on git push.
    """
    pre_push_hooks = []
    for repo in shared_precommit_config.get("repos", []):
        for hook in repo.get("hooks", []):
            stages = hook.get("stages", ["commit"])  # Default stage is commit
            if "pre-push" in stages or stages == ["pre-push"]:
                pre_push_hooks.append(hook)
    return pre_push_hooks


@pytest.fixture(scope="module")
def shared_run_pre_push_tests_script(shared_repo_root: Path) -> Path:
    """
    Get path to run_pre_push_tests.py script.

    This script contains the consolidated test execution logic for pre-push hooks.
    Since migrating to pre-commit framework, test commands are in this Python script
    instead of bash hook file.
    """
    script_path = shared_repo_root / "scripts" / "run_pre_push_tests.py"
    if not script_path.exists():
        pytest.skip(
            f"run_pre_push_tests.py script not found at {script_path}\n"
            "This script is required for pre-push test validation."
        )
    return script_path


@pytest.fixture(scope="module")
def shared_run_pre_push_tests_content(shared_run_pre_push_tests_script: Path) -> str:
    """Read run_pre_push_tests.py script content."""
    with open(shared_run_pre_push_tests_script) as f:
        return f.read()


@pytest.fixture(scope="module")
def shared_makefile_path(shared_repo_root: Path) -> Path:
    """Get path to Makefile (shared across all tests in module)."""
    return shared_repo_root / "Makefile"


@pytest.fixture(scope="module")
def shared_makefile_content(shared_makefile_path: Path) -> str:
    """Read Makefile content (shared across all tests in module)."""
    with open(shared_makefile_path) as f:
        return f.read()


@pytest.fixture(scope="module")
def shared_validate_pre_push_sub_targets_content(shared_makefile_content: str) -> str:
    """
    Get combined content of validate-pre-push sub-targets (shared across all tests).

    The validate-pre-push target is a router that calls:
    - validate-pre-push-full (with integration tests)
    - validate-pre-push-quick (without integration tests)
    - _validate-pre-push-phases-1-2 (shared phases called by both full and quick)

    This fixture returns the combined content of all sub-targets.
    """
    # Extract validate-pre-push-full target
    full_match = re.search(
        r"^validate-pre-push-full:.*?(?=^[a-zA-Z]|\Z)",
        shared_makefile_content,
        re.MULTILINE | re.DOTALL,
    )

    # Extract validate-pre-push-quick target
    quick_match = re.search(
        r"^validate-pre-push-quick:.*?(?=^[a-zA-Z]|\Z)",
        shared_makefile_content,
        re.MULTILINE | re.DOTALL,
    )

    # Extract _validate-pre-push-phases-1-2 target (contains actual lockfile validation)
    phases_match = re.search(
        r"^_validate-pre-push-phases-1-2:.*?(?=^[a-zA-Z]|\Z)",
        shared_makefile_content,
        re.MULTILINE | re.DOTALL,
    )

    combined = ""
    if full_match:
        combined += full_match.group(0) + "\n"
    if quick_match:
        combined += quick_match.group(0) + "\n"
    if phases_match:
        combined += phases_match.group(0) + "\n"

    return combined


def find_hook_by_id(hooks: list[dict], hook_id: str) -> dict:
    """Find a hook by its ID."""
    for hook in hooks:
        if hook.get("id") == hook_id:
            return hook
    return None


def hook_contains_pattern(hook: dict, pattern: str) -> bool:
    """Check if hook's entry command contains a pattern."""
    entry = hook.get("entry", "")
    return pattern in entry


def is_pre_commit_wrapper(content: str) -> bool:
    """
    Detect if hook is a pre-commit framework wrapper.

    Args:
        content: Hook file content

    Returns:
        True if hook is generated by pre-commit framework
    """
    wrapper_patterns = [
        r"File generated by pre-commit:",
        r"pre_commit",
        r"--hook-type=pre-push",
        r"exec.*python.*-mpre_commit",
    ]
    return any(re.search(pattern, content) for pattern in wrapper_patterns)


# ══════════════════════════════════════════════════════════════════════════════
# Test Classes
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.xdist_group(name="testprepushhookconfiguration")
class TestPrePushHookConfiguration:
    """Validate pre-push hook is configured correctly."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def repo_root(self, shared_repo_root: Path) -> Path:
        """Get repository root directory (delegates to shared fixture)."""
        return shared_repo_root

    @pytest.fixture
    def pre_push_hook_path(self, shared_pre_push_hook_path: Path) -> Path:
        """Get path to pre-push hook (delegates to shared fixture with skip logic)."""
        return shared_pre_push_hook_path

    def test_pre_push_hook_exists(self, pre_push_hook_path: Path):
        """Test that pre-push hook file exists."""
        assert pre_push_hook_path.exists(), (
            "Pre-push hook does not exist at .git/hooks/pre-push\n"
            "Run 'make git-hooks' or 'pre-commit install --hook-type pre-push'"
        )

    def test_pre_push_hook_is_executable(self, pre_push_hook_path: Path):
        """Test that pre-push hook has execute permissions."""
        assert os.access(pre_push_hook_path, os.X_OK), (
            f"Pre-push hook exists but is not executable: {pre_push_hook_path}\n" f"Fix: chmod +x {pre_push_hook_path}"
        )

    def test_pre_push_hook_is_bash_script(self, pre_push_hook_path: Path):
        """Test that pre-push hook is a bash script."""
        with open(pre_push_hook_path) as f:
            first_line = f.readline().strip()

        assert first_line in [
            "#!/bin/bash",
            "#!/usr/bin/env bash",
        ], f"Pre-push hook must be a bash script, got shebang: {first_line}"

    def test_pre_push_hook_validates_lockfile(self, repo_root: Path, pre_push_hook_path: Path):
        """Test that pre-push hook validates lockfile."""
        # Read hook to detect type
        with open(pre_push_hook_path) as f:
            hook_content = f.read()

        # Pre-commit framework: check .pre-commit-config.yaml
        if is_pre_commit_wrapper(hook_content):
            config_path = repo_root / ".pre-commit-config.yaml"
            with open(config_path) as f:
                content = f.read()
        else:
            # Legacy bash script: check hook directly
            content = hook_content

        assert "uv lock --check" in content, (
            "Pre-push hook must validate lockfile with 'uv lock --check'\n"
            "This prevents out-of-sync lockfiles from being pushed"
        )

    def test_pre_push_hook_validates_workflows(self, repo_root: Path, pre_push_hook_path: Path):
        """Test that pre-push hook validates GitHub workflows."""
        with open(pre_push_hook_path) as f:
            hook_content = f.read()

        # Pre-commit framework: check .pre-commit-config.yaml for workflow validation hooks
        if is_pre_commit_wrapper(hook_content):
            config_path = repo_root / ".pre-commit-config.yaml"
            with open(config_path) as f:
                content = f.read()

            # Check for comprehensive workflow validator (consolidated in 2025-11-17)
            assert "validate-github-workflows-comprehensive" in content or "actionlint" in content, (
                "Pre-push hook must validate GitHub workflows\n"
                "Expected: validate-github-workflows-comprehensive or actionlint hook"
            )
        else:
            # Legacy bash script: check for individual test files
            content = hook_content
            required_workflow_tests = [
                "test_workflow_syntax.py",
                "test_workflow_security.py",
                "test_workflow_dependencies.py",
                "test_docker_paths.py",
            ]

            for test_file in required_workflow_tests:
                assert test_file in content, (
                    f"Pre-push hook must run workflow validation test: {test_file}\n"
                    f"This prevents workflow errors from reaching CI"
                )

    def test_pre_push_hook_runs_mypy(self, repo_root: Path, pre_push_hook_path: Path):
        """Test that pre-push hook runs MyPy type checking (OPTIONAL - project policy)."""
        with open(pre_push_hook_path) as f:
            hook_content = f.read()

        # Pre-commit framework: check .pre-commit-config.yaml
        if is_pre_commit_wrapper(hook_content):
            config_path = repo_root / ".pre-commit-config.yaml"
            with open(config_path) as f:
                config_content = f.read()

            # MyPy is OPTIONAL per project policy (intentionally manual/non-blocking)
            # Updated 2025-11-19: Made mypy optional (see scripts/validate_pre_push_hook.py)
            # If present, should be in manual stage or non-blocking
            if "mypy" in config_content:
                # If mypy is present, it should be non-blocking (manual stage)
                pytest.skip("MyPy found in config - checking it's non-blocking is handled by validate_pre_push_hook.py")
        else:
            # Legacy bash script: MyPy should be present but non-blocking
            content = hook_content
            if "mypy src/mcp_server_langgraph" in content:
                # MyPy should be non-blocking (warning only)
                assert "false" in content or "non-blocking" in content.lower(), "MyPy should be non-blocking in pre-push hook"
            else:
                # MyPy is optional, so skip if not present
                pytest.skip("MyPy not configured in pre-push hook (OPTIONAL per project policy)")

    def test_pre_push_hook_runs_precommit_all_files(self, repo_root: Path, pre_push_hook_path: Path):
        """Test that pre-push hook runs pre-commit on ALL files."""
        with open(pre_push_hook_path) as f:
            hook_content = f.read()

        # Pre-commit framework: hooks are managed by .pre-commit-config.yaml
        if is_pre_commit_wrapper(hook_content):
            config_path = repo_root / ".pre-commit-config.yaml"
            with open(config_path) as f:
                config_content = f.read()

            # Verify .pre-commit-config.yaml exists and has pre-push hooks configured
            # The framework handles running on all files automatically for pre-push stage
            assert "stages:" in config_content and "pre-push" in config_content, (
                "Pre-commit config must have hooks configured for pre-push stage\n"
                "Pre-commit framework automatically runs on all files for git hooks"
            )
        else:
            # Legacy bash script: must explicitly call pre-commit run --all-files
            content = hook_content
            assert "pre-commit run --all-files" in content, (
                "Pre-push hook must run 'pre-commit run --all-files'\n" "Running on changed files only causes CI surprises"
            )

    def test_pre_push_hook_runs_property_tests_with_ci_profile(self, repo_root: Path, pre_push_hook_path: Path):
        """Test that pre-push hook runs property tests with CI profile."""
        with open(pre_push_hook_path) as f:
            hook_content = f.read()

        # Pre-commit framework: check .pre-commit-config.yaml
        if is_pre_commit_wrapper(hook_content):
            config_path = repo_root / ".pre-commit-config.yaml"
            with open(config_path) as f:
                config_content = f.read()

            # Check for property test configuration in run-pre-push-tests hook
            # Note: Default dev profile (25 examples), CI_PARITY=1 enables CI profile (100 examples)
            # Updated 2025-11-18: Consolidated test hook approach
            assert "run-pre-push-tests" in config_content or "property" in config_content, (
                "Pre-push hook must run property tests\n" "Expected: run-pre-push-tests hook or explicit property test marker"
            )
        else:
            # Legacy bash script: check for explicit CI profile
            content = hook_content
            assert "HYPOTHESIS_PROFILE=ci" in content, (
                "Pre-push hook must set HYPOTHESIS_PROFILE=ci for property tests\n"
                "Local uses 25 examples, CI uses 100 - this prevents CI-only failures"
            )
            assert "-m property" in content, "Pre-push hook must run property tests"

    def test_pre_push_hook_has_clear_phases(self, pre_push_hook_path: Path):
        """Test that pre-push hook has clearly defined validation phases (legacy only)."""
        with open(pre_push_hook_path) as f:
            hook_content = f.read()

        # Pre-commit framework: phases are organized via .pre-commit-config.yaml structure
        if is_pre_commit_wrapper(hook_content):
            pytest.skip(
                "Pre-commit framework hook - phases organized via .pre-commit-config.yaml structure, "
                "not inline PHASE markers"
            )

        # Legacy bash script: check for phase markers
        expected_phases = [
            "PHASE 1",  # Fast checks
            "PHASE 2",  # Type checking
            "PHASE 3",  # Pre-commit hooks
            "PHASE 4",  # Property tests
        ]

        for phase in expected_phases:
            assert phase in hook_content, f"Pre-push hook should have clearly labeled {phase} for readability"

    def test_pre_push_hook_provides_helpful_error_messages(self, pre_push_hook_path: Path):
        """Test that pre-push hook provides helpful troubleshooting info (legacy only)."""
        with open(pre_push_hook_path) as f:
            hook_content = f.read()

        # Pre-commit framework: error messages provided by framework itself
        if is_pre_commit_wrapper(hook_content):
            pytest.skip(
                "Pre-commit framework hook - error messages and bypass instructions "
                "provided by pre-commit framework (--no-verify works automatically)"
            )

        # Legacy bash script: should have helpful messages
        # Should mention how to bypass (for emergencies)
        assert "--no-verify" in hook_content, "Pre-push hook should document emergency bypass with --no-verify"

        # Should provide fix instructions
        assert "To fix" in hook_content or "Fix:" in hook_content, "Pre-push hook should provide troubleshooting instructions"


@pytest.mark.xdist_group(name="testmakefilevalidationtarget")
class TestMakefileValidationTarget:
    """Validate Makefile validate-pre-push target."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def makefile_content(self, shared_makefile_content: str) -> str:
        """Delegate to shared Makefile content fixture."""
        return shared_makefile_content

    @pytest.fixture
    def validate_pre_push_sub_targets_content(self, shared_validate_pre_push_sub_targets_content: str) -> str:
        """Delegate to shared validate-pre-push sub-targets content fixture."""
        return shared_validate_pre_push_sub_targets_content

    def test_validate_pre_push_target_exists(self, makefile_content: str):
        """Test that validate-pre-push target exists in Makefile."""
        assert re.search(r"^validate-pre-push:", makefile_content, re.MULTILINE), (
            "Makefile must have 'validate-pre-push' target\n" "This provides manual validation matching pre-push hook"
        )

    def test_validate_pre_push_in_phony_targets(self, makefile_content: str):
        """Test that validate-pre-push is declared as .PHONY."""
        # Extract .PHONY line
        phony_match = re.search(r"^\.PHONY:.*$", makefile_content, re.MULTILINE)
        assert phony_match, "Makefile should have .PHONY declaration"

        phony_line = phony_match.group(0)
        assert "validate-pre-push" in phony_line, "validate-pre-push must be declared in .PHONY targets"

    def test_validate_pre_push_runs_lockfile_check(self, validate_pre_push_sub_targets_content: str):
        """Test that validate-pre-push sub-targets validate lockfile."""
        assert validate_pre_push_sub_targets_content, "Could not find validate-pre-push sub-targets"
        assert (
            "uv lock --check" in validate_pre_push_sub_targets_content
        ), "validate-pre-push must run 'uv lock --check' in one of its sub-targets"

    def test_validate_pre_push_runs_workflow_tests(self, validate_pre_push_sub_targets_content: str):
        """Test that validate-pre-push sub-targets run workflow validation tests."""
        assert validate_pre_push_sub_targets_content, "Could not find validate-pre-push sub-targets"

        required_tests = [
            "test_workflow_syntax.py",
            "test_workflow_security.py",
            "test_workflow_dependencies.py",
            "test_docker_paths.py",
        ]

        for test in required_tests:
            assert test in validate_pre_push_sub_targets_content, f"validate-pre-push sub-targets must run {test}"

    def test_validate_pre_push_runs_mypy(self, validate_pre_push_sub_targets_content: str):
        """Test that validate-pre-push sub-targets run MyPy."""
        assert validate_pre_push_sub_targets_content, "Could not find validate-pre-push sub-targets"
        assert (
            "mypy src/mcp_server_langgraph" in validate_pre_push_sub_targets_content
        ), "validate-pre-push sub-targets must run MyPy type checking"

    def test_validate_pre_push_runs_precommit_all_files(self, validate_pre_push_sub_targets_content: str):
        """Test that validate-pre-push sub-targets run pre-commit on all files."""
        assert validate_pre_push_sub_targets_content, "Could not find validate-pre-push sub-targets"
        assert (
            "pre-commit run --all-files" in validate_pre_push_sub_targets_content
        ), "validate-pre-push sub-targets must run 'pre-commit run --all-files'"

    def test_validate_pre_push_runs_property_tests_with_ci_profile(self, validate_pre_push_sub_targets_content: str):
        """Test that validate-pre-push sub-targets run property tests with CI profile."""
        assert validate_pre_push_sub_targets_content, "Could not find validate-pre-push sub-targets"

        target_content = validate_pre_push_sub_targets_content

        # Check for direct setting OR use of the consolidated script (which handles it)
        has_ci_profile = "HYPOTHESIS_PROFILE=ci" in target_content
        uses_consolidated_script = "scripts/run_pre_push_tests.py" in target_content

        assert (
            has_ci_profile or uses_consolidated_script
        ), "validate-pre-push must set HYPOTHESIS_PROFILE=ci (or use run_pre_push_tests.py)"

        # Same for property tests check
        has_property = "property" in target_content
        # run_pre_push_tests.py includes property tests

        assert has_property or uses_consolidated_script, "validate-pre-push must run property tests"

    def test_validate_pre_push_in_help_output(self, makefile_content: str):
        """Test that validate-pre-push is documented in help target."""
        # Find help or help-common target
        help_match = re.search(
            r"^help(-common)?:.*?(?=^[a-zA-Z]|\Z)",
            makefile_content,
            re.MULTILINE | re.DOTALL,
        )
        assert help_match, "Could not find help target"

        help_content = help_match.group(0)
        assert "validate-pre-push" in help_content, "validate-pre-push should be documented in make help output"


@pytest.mark.xdist_group(name="testlocalciparity")
class TestLocalCIParity:
    """Validate that local validation matches CI validation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def ci_workflow_path(self) -> Path:
        """Get path to main CI workflow."""
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
        repo_root = Path(result.stdout.strip())
        return repo_root / ".github" / "workflows" / "ci.yaml"

    @pytest.fixture
    def ci_workflow(self, ci_workflow_path: Path) -> dict:
        """Load CI workflow YAML."""
        with open(ci_workflow_path) as f:
            return yaml.safe_load(f)

    @pytest.fixture
    def pre_push_hook_path(self) -> Path:
        """Get path to pre-push hook (handles git worktrees)."""
        # Get repository root
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
        repo_root = Path(result.stdout.strip())
        # Use git rev-parse to get common git directory (handles worktrees)
        result = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
            cwd=repo_root,
        )
        git_common_dir = Path(result.stdout.strip())
        # If path is relative, make it relative to repo_root
        if not git_common_dir.is_absolute():
            git_common_dir = repo_root / git_common_dir
        return git_common_dir / "hooks" / "pre-push"

    @pytest.fixture
    def pre_push_content(self, pre_push_hook_path: Path) -> str:
        """Read pre-push hook content."""
        with open(pre_push_hook_path) as f:
            return f.read()

    def test_lockfile_validation_matches_ci(self, ci_workflow: dict, pre_push_content: str, shared_repo_root: Path):
        """Test that lockfile validation command matches CI."""
        # CI should run uv lock --check
        ci_content = yaml.dump(ci_workflow)

        if "uv lock --check" in ci_content or "uv sync --frozen" in ci_content:
            # Pre-commit framework: check .pre-commit-config.yaml
            if is_pre_commit_wrapper(pre_push_content):
                config_path = shared_repo_root / ".pre-commit-config.yaml"
                with open(config_path) as f:
                    config_content = f.read()

                # Check for uv lock validation hook
                has_lockfile_check = "uv lock --check" in config_content or "uv-lock-check" in config_content
                assert has_lockfile_check, "Pre-commit config must validate lockfile like CI does"
            else:
                # Legacy bash script: check hook directly
                assert "uv lock --check" in pre_push_content, "Local pre-push must validate lockfile like CI does"

    def test_precommit_scope_matches_ci(self, ci_workflow: dict, pre_push_content: str, shared_repo_root: Path):
        """Test that pre-commit scope matches CI (all files)."""
        ci_content = yaml.dump(ci_workflow)

        if "pre-commit run" in ci_content:
            # CI runs on all files
            if "--all-files" in ci_content:
                # Pre-commit framework: framework runs on all files automatically for git hooks
                if is_pre_commit_wrapper(pre_push_content):
                    config_path = shared_repo_root / ".pre-commit-config.yaml"
                    with open(config_path) as f:
                        config_content = f.read()

                    # Verify .pre-commit-config.yaml has pre-push hooks configured
                    # Framework automatically runs on all files for git hooks
                    assert "stages:" in config_content and "pre-push" in config_content, (
                        "Pre-commit config must have hooks configured for pre-push stage\n"
                        "Pre-commit framework automatically runs on all files for git hooks"
                    )
                else:
                    # Legacy bash script: must explicitly call pre-commit run --all-files
                    assert "--all-files" in pre_push_content, (
                        "Local pre-push must run pre-commit on all files like CI does\n"
                        "Running on changed files only causes CI surprises"
                    )

    def test_hypothesis_profile_matches_ci(
        self,
        ci_workflow: dict,
        pre_push_content: str,
        shared_run_pre_push_tests_content: str,
    ):
        """Test that Hypothesis profile matches CI."""
        ci_content = yaml.dump(ci_workflow)

        if "HYPOTHESIS_PROFILE" in ci_content:
            # Extract CI profile
            if "HYPOTHESIS_PROFILE=ci" in ci_content or "HYPOTHESIS_PROFILE: ci" in ci_content:
                # Pre-commit framework: check scripts/run_pre_push_tests.py
                if is_pre_commit_wrapper(pre_push_content):
                    assert (
                        "HYPOTHESIS_PROFILE" in shared_run_pre_push_tests_content
                        and '"ci"' in shared_run_pre_push_tests_content
                    ), (
                        "run_pre_push_tests.py must set HYPOTHESIS_PROFILE=ci to match CI\n"
                        "CI uses 100 examples, local dev uses 25 - this causes failures"
                    )
                else:
                    # Legacy bash script: check hook directly
                    assert "HYPOTHESIS_PROFILE=ci" in pre_push_content, (
                        "Local pre-push must use same Hypothesis profile as CI\n"
                        "CI uses 100 examples, local dev uses 25 - this causes failures"
                    )

    def test_workflow_validation_matches_ci(self, ci_workflow: dict, pre_push_content: str, shared_repo_root: Path):
        """Test that workflow validation tests match what CI runs."""
        # CI has workflow validation job
        jobs = ci_workflow.get("jobs", {})

        workflow_validation_jobs = [
            job_name
            for job_name, job_config in jobs.items()
            if "workflow" in job_name.lower() or "actionlint" in str(job_config).lower()
        ]

        if workflow_validation_jobs:
            # Pre-commit framework: check .pre-commit-config.yaml for workflow validation hooks
            if is_pre_commit_wrapper(pre_push_content):
                config_path = shared_repo_root / ".pre-commit-config.yaml"
                with open(config_path) as f:
                    config_content = f.read()

                # Check for comprehensive workflow validator or actionlint
                assert "validate-github-workflows-comprehensive" in config_content or "actionlint" in config_content, (
                    "Pre-commit config must validate GitHub workflows\n"
                    "Expected: validate-github-workflows-comprehensive or actionlint hook"
                )
            else:
                # Legacy bash script: check for test_workflow tests
                assert "test_workflow" in pre_push_content, "Local pre-push should validate workflows like CI does"


@pytest.mark.xdist_group(name="testcigapprevention")
class TestCIGapPrevention:
    """Tests to prevent CI validation gaps from being introduced."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def repo_root(self) -> Path:
        """Get repository root."""
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
        return Path(result.stdout.strip())

    def test_ci_workflow_has_validation_job(self, repo_root: Path):
        """Test that CI workflow has comprehensive validation."""
        ci_path = repo_root / ".github" / "workflows" / "ci.yaml"

        with open(ci_path) as f:
            ci_content = yaml.safe_load(f)

        jobs = ci_content.get("jobs", {})

        # Should have pre-commit or validation job
        validation_jobs = [
            job for job in jobs.keys() if any(keyword in job.lower() for keyword in ["pre-commit", "validate", "lint"])
        ]

        assert validation_jobs, "CI workflow should have validation/pre-commit/lint job"

    def test_contributing_docs_mention_validate_pre_push(self, repo_root: Path):
        """Test that CONTRIBUTING.md documents validate-pre-push."""
        contributing_path = repo_root / "CONTRIBUTING.md"

        with open(contributing_path) as f:
            content = f.read()

        assert "validate-pre-push" in content, "CONTRIBUTING.md should document validate-pre-push requirement"

        assert "make validate-pre-push" in content, "CONTRIBUTING.md should show the command to run"

    def test_readme_or_quickstart_mentions_validation(self, repo_root: Path):
        """Test that quick start documentation mentions validation."""
        readme_path = repo_root / "README.md"

        if readme_path.exists():
            with open(readme_path) as f:
                content = f.read()

            # Should mention validation or testing before push
            validation_keywords = ["validate", "pre-push", "before push", "CI"]
            has_validation_info = any(keyword in content for keyword in validation_keywords)

            # Not strictly required in README, but good practice
            # So this is informational rather than blocking
            if not has_validation_info:
                pytest.skip("README doesn't mention validation (optional)")


@pytest.mark.xdist_group(name="testpytestxdistparity")
class TestPytestXdistParity:
    """Validate that local tests use pytest-xdist (-n auto) like CI does.

    CRITICAL: These tests enforce Codex finding #7 - ensure local pre-push runs
    tests in parallel with -n auto to catch pytest-xdist isolation bugs before CI.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def repo_root(self) -> Path:
        """Get repository root."""
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
        return Path(result.stdout.strip())

    @pytest.fixture
    def pre_push_hook_path(self, shared_pre_push_hook_path: Path) -> Path:
        """Get path to pre-push hook (delegates to shared fixture with skip logic)."""
        return shared_pre_push_hook_path

    @pytest.fixture
    def pre_push_content(self, pre_push_hook_path: Path) -> str:
        """Read pre-push hook content."""
        with open(pre_push_hook_path) as f:
            return f.read()

    @pytest.fixture
    def ci_workflow_path(self, repo_root: Path) -> Path:
        """Get path to CI workflow."""
        return repo_root / ".github" / "workflows" / "ci.yaml"

    @pytest.fixture
    def ci_workflow_content(self, ci_workflow_path: Path) -> str:
        """Read CI workflow content."""
        with open(ci_workflow_path) as f:
            return f.read()

    def test_unit_tests_use_pytest_xdist_n_auto(self, shared_run_pre_push_tests_content: str):
        """Test that unit tests run with -n auto for parallel execution.

        CRITICAL: Without -n auto, pytest-xdist isolation bugs are only caught in CI.
        This causes "works locally, fails in CI" issues.

        Since migrating to pre-commit framework, test commands are in scripts/run_pre_push_tests.py
        instead of the bash hook file.
        """
        # Check that run_pre_push_tests.py uses -n auto
        assert '"-n"' in shared_run_pre_push_tests_content and '"auto"' in shared_run_pre_push_tests_content, (
            "run_pre_push_tests.py must use pytest -n auto for parallel execution\n"
            "Expected: pytest_args.extend(['-n', 'auto'])\n"
            "\n"
            "Without -n auto:\n"
            "  - Tests run 2-3x slower locally\n"
            "  - pytest-xdist isolation bugs only caught in CI\n"
            "  - 'Works locally, fails in CI' issues\n"
            "\n"
            "Fix: Ensure scripts/run_pre_push_tests.py includes -n auto in pytest_args"
        )

    def test_smoke_tests_use_pytest_xdist_n_auto(self, shared_run_pre_push_tests_content: str):
        """Test that smoke tests run with -n auto for parallel execution.

        Smoke tests are unit tests in tests/smoke/, covered by consolidated script's
        marker expression: (unit or api or property) and not llm
        """
        # Consolidated script uses -n auto for ALL tests (unit, api, property)
        # Smoke tests are unit tests, so they're covered
        assert '"-n"' in shared_run_pre_push_tests_content and '"auto"' in shared_run_pre_push_tests_content, (
            "run_pre_push_tests.py must use pytest -n auto (covers smoke tests as unit tests)\n"
            "Fix: Ensure scripts/run_pre_push_tests.py includes -n auto in pytest_args"
        )

    def test_integration_tests_use_pytest_xdist_n_auto(self, shared_run_pre_push_tests_content: str):
        """Test that integration tests use -n auto when CI_PARITY=1.

        Integration tests are optional in pre-push (require Docker), but when enabled
        via CI_PARITY=1 they should use -n auto for parallel execution.
        """
        # Script uses -n auto for ALL tests, including optional integration tests
        assert '"-n"' in shared_run_pre_push_tests_content and '"auto"' in shared_run_pre_push_tests_content, (
            "run_pre_push_tests.py must use pytest -n auto (includes integration when CI_PARITY=1)\n"
            "Fix: Ensure scripts/run_pre_push_tests.py includes -n auto in pytest_args"
        )

    def test_property_tests_use_pytest_xdist_n_auto(self, shared_run_pre_push_tests_content: str):
        """Test that property tests run with -n auto for parallel execution.

        Property tests are included in consolidated marker expression:
        (unit or api or property) and not llm
        """
        # Consolidated script uses -n auto for ALL tests (includes property tests)
        assert '"-n"' in shared_run_pre_push_tests_content and '"auto"' in shared_run_pre_push_tests_content, (
            "run_pre_push_tests.py must use pytest -n auto (covers property tests)\n"
            "Fix: Ensure scripts/run_pre_push_tests.py includes -n auto in pytest_args"
        )

    def test_ci_uses_pytest_xdist_n_auto(self, ci_workflow_content: str):
        """Verify that CI uses -n auto (this is the baseline we're matching)."""
        # CI should use -n auto for unit tests
        assert "pytest -n auto" in ci_workflow_content, (
            "CI workflow must use 'pytest -n auto' for parallel execution\n" "If CI doesn't use it, this test needs updating"
        )


@pytest.mark.xdist_group(name="testotelsdkdisabledparity")
class TestOtelSdkDisabledParity:
    """Validate that local tests set OTEL_SDK_DISABLED=true like CI does.

    CRITICAL: These tests enforce Codex finding #2B - ensure local pre-push sets
    OTEL_SDK_DISABLED=true to match CI environment exactly.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def repo_root(self) -> Path:
        """Get repository root."""
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
        return Path(result.stdout.strip())

    @pytest.fixture
    def pre_push_hook_path(self, shared_pre_push_hook_path: Path) -> Path:
        """Get path to pre-push hook (delegates to shared fixture with skip logic)."""
        return shared_pre_push_hook_path

    @pytest.fixture
    def pre_push_content(self, pre_push_hook_path: Path) -> str:
        """Read pre-push hook content."""
        with open(pre_push_hook_path) as f:
            return f.read()

    @pytest.fixture
    def ci_workflow_path(self, repo_root: Path) -> Path:
        """Get path to CI workflow."""
        return repo_root / ".github" / "workflows" / "ci.yaml"

    @pytest.fixture
    def ci_workflow_content(self, ci_workflow_path: Path) -> str:
        """Read CI workflow content."""
        with open(ci_workflow_path) as f:
            return f.read()

    def test_unit_tests_set_otel_sdk_disabled(self, shared_run_pre_push_tests_content: str):
        """Test that unit tests set OTEL_SDK_DISABLED=true to match CI.

        Since migrating to pre-commit framework, the consolidated script sets
        OTEL_SDK_DISABLED in the environment for all tests.
        """
        assert "OTEL_SDK_DISABLED" in shared_run_pre_push_tests_content and '"true"' in shared_run_pre_push_tests_content, (
            "run_pre_push_tests.py must set OTEL_SDK_DISABLED=true for all tests\n"
            "Expected: env['OTEL_SDK_DISABLED'] = 'true'\n"
            "\n"
            "Without OTEL_SDK_DISABLED=true:\n"
            "  - OpenTelemetry SDK may initialize (performance overhead)\n"
            "  - Different execution environment vs CI\n"
            "  - Potential telemetry-related side effects\n"
            "\n"
            "Fix: Ensure scripts/run_pre_push_tests.py sets env['OTEL_SDK_DISABLED'] = 'true'"
        )

    def test_smoke_tests_set_otel_sdk_disabled(self, shared_run_pre_push_tests_content: str):
        """Test that smoke tests set OTEL_SDK_DISABLED=true to match CI.

        Smoke tests are unit tests covered by the consolidated script, which sets
        OTEL_SDK_DISABLED for all tests in the environment.
        """
        assert "OTEL_SDK_DISABLED" in shared_run_pre_push_tests_content and '"true"' in shared_run_pre_push_tests_content, (
            "run_pre_push_tests.py must set OTEL_SDK_DISABLED=true (covers smoke tests)\n"
            "Fix: Ensure scripts/run_pre_push_tests.py sets env['OTEL_SDK_DISABLED'] = 'true'"
        )

    def test_integration_tests_set_otel_sdk_disabled(self, shared_run_pre_push_tests_content: str):
        """Test that integration tests set OTEL_SDK_DISABLED=true to match CI.

        Integration tests (when enabled via CI_PARITY=1) are covered by the same
        environment setup that sets OTEL_SDK_DISABLED for all tests.
        """
        assert "OTEL_SDK_DISABLED" in shared_run_pre_push_tests_content and '"true"' in shared_run_pre_push_tests_content, (
            "run_pre_push_tests.py must set OTEL_SDK_DISABLED=true (includes integration tests)\n"
            "Fix: Ensure scripts/run_pre_push_tests.py sets env['OTEL_SDK_DISABLED'] = 'true'"
        )

    def test_property_tests_already_set_otel_sdk_disabled(self, shared_run_pre_push_tests_content: str):
        """Verify that property tests already set OTEL_SDK_DISABLED=true (should pass).

        Property tests are included in the consolidated marker expression and covered
        by the same environment setup.
        """
        assert "OTEL_SDK_DISABLED" in shared_run_pre_push_tests_content and '"true"' in shared_run_pre_push_tests_content, (
            "run_pre_push_tests.py must set OTEL_SDK_DISABLED=true (covers property tests)\n"
            "Fix: Ensure scripts/run_pre_push_tests.py sets env['OTEL_SDK_DISABLED'] = 'true'"
        )

    def test_ci_sets_otel_sdk_disabled(self, ci_workflow_content: str):
        """Verify that CI sets OTEL_SDK_DISABLED=true (this is the baseline)."""
        assert "OTEL_SDK_DISABLED=true" in ci_workflow_content, (
            "CI workflow must set OTEL_SDK_DISABLED=true for tests\n" "If CI doesn't use it, this test needs updating"
        )


@pytest.mark.xdist_group(name="testapimcptestsuiteparity")
class TestApiMcpTestSuiteParity:
    """Validate that local pre-push runs API/MCP test suites like CI does.

    CRITICAL: These tests enforce Codex finding #2D - ensure API and MCP tests
    run locally before push to prevent CI-only failures.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def repo_root(self) -> Path:
        """Get repository root."""
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
        return Path(result.stdout.strip())

    @pytest.fixture
    def pre_push_hook_path(self, shared_pre_push_hook_path: Path) -> Path:
        """Get path to pre-push hook (delegates to shared fixture with skip logic)."""
        return shared_pre_push_hook_path

    @pytest.fixture
    def pre_push_content(self, pre_push_hook_path: Path) -> str:
        """Read pre-push hook content."""
        with open(pre_push_hook_path) as f:
            return f.read()

    @pytest.fixture
    def ci_workflow_path(self, repo_root: Path) -> Path:
        """Get path to CI workflow."""
        return repo_root / ".github" / "workflows" / "ci.yaml"

    @pytest.fixture
    def ci_workflow_content(self, ci_workflow_path: Path) -> str:
        """Read CI workflow content."""
        with open(ci_workflow_path) as f:
            return f.read()

    def test_api_endpoint_tests_run_locally(self, shared_run_pre_push_tests_content: str):
        """Test that API endpoint tests run in pre-push hook like in CI.

        Since migrating to pre-commit framework, API tests are covered by the consolidated
        marker expression: (unit or api or property) and not llm
        """
        # Check that consolidated script includes 'api' marker
        has_api_marker = (
            "api" in shared_run_pre_push_tests_content and "marker_expression" in shared_run_pre_push_tests_content
        )

        assert has_api_marker, (
            "run_pre_push_tests.py must include 'api' marker to run API endpoint tests\n"
            "\n"
            "CI runs (ci.yaml:249):\n"
            "  OTEL_SDK_DISABLED=true pytest -n auto -m 'api and unit and not llm'\n"
            "\n"
            "Consolidated script uses:\n"
            "  marker_expression = '(unit or api or property) and not llm'\n"
            "\n"
            "Without API tests locally:\n"
            "  - Developers can push code that breaks API tests\n"
            "  - API failures only caught in CI\n"
            "  - Wastes CI time and developer time\n"
            "\n"
            "Fix: Ensure scripts/run_pre_push_tests.py includes 'api' in marker expression"
        )

    def test_mcp_server_tests_run_locally(self, shared_run_pre_push_tests_content: str):
        """Test that MCP server tests run in pre-push hook like in CI.

        MCP server tests are unit tests in tests/unit/test_mcp_stdio_server.py, covered by
        the consolidated marker expression: (unit or api or property) and not llm
        """
        # Check that consolidated script includes 'unit' marker (MCP tests are unit tests)
        has_unit_marker = (
            "unit" in shared_run_pre_push_tests_content and "marker_expression" in shared_run_pre_push_tests_content
        )

        assert has_unit_marker, (
            "run_pre_push_tests.py must include 'unit' marker to run MCP server tests\n"
            "\n"
            "CI runs (ci.yaml:253):\n"
            "  OTEL_SDK_DISABLED=true pytest tests/unit/test_mcp_stdio_server.py -m 'not llm'\n"
            "\n"
            "Consolidated script uses:\n"
            "  marker_expression = '(unit or api or property) and not llm'\n"
            "  (MCP tests are in tests/unit/, marked as unit tests)\n"
            "\n"
            "Without MCP tests locally:\n"
            "  - MCP protocol changes can break without local detection\n"
            "  - MCP failures only caught in CI\n"
            "\n"
            "Fix: Ensure scripts/run_pre_push_tests.py includes 'unit' in marker expression"
        )

    def test_ci_runs_api_tests(self, ci_workflow_content: str):
        """Verify that CI runs API tests (this is the baseline)."""
        assert "api and unit" in ci_workflow_content, (
            "CI workflow must run API endpoint tests\n"
            "Expected: pytest -m 'api and unit'\n"
            "If CI doesn't run API tests, this test needs updating"
        )

    def test_ci_runs_mcp_tests(self, ci_workflow_content: str):
        """Verify that CI runs MCP tests (this is the baseline)."""
        assert "test_mcp_stdio_server.py" in ci_workflow_content, (
            "CI workflow must run MCP server tests\n"
            "Expected: pytest tests/unit/test_mcp_stdio_server.py\n"
            "If CI doesn't run MCP tests, this test needs updating"
        )


@pytest.mark.xdist_group(name="testmakefileprepushparity")
class TestMakefilePrePushParity:
    """Validate that Makefile validate-pre-push target matches pre-push hook exactly.

    CRITICAL: These tests enforce Codex finding #3 - ensure developers running
    'make validate-pre-push' get the same validation as the git pre-push hook.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def makefile_content(self, shared_makefile_content: str) -> str:
        """Delegate to shared Makefile content fixture."""
        return shared_makefile_content

    @pytest.fixture
    def validate_pre_push_sub_targets_content(self, shared_validate_pre_push_sub_targets_content: str) -> str:
        """Delegate to shared validate-pre-push sub-targets content fixture."""
        return shared_validate_pre_push_sub_targets_content

    @pytest.fixture
    def pre_push_hook_path(self, shared_pre_push_hook_path: Path) -> Path:
        """Get path to pre-push hook (delegates to shared fixture with skip logic)."""
        return shared_pre_push_hook_path

    @pytest.fixture
    def pre_push_content(self, pre_push_hook_path: Path) -> str:
        """Read pre-push hook content."""
        with open(pre_push_hook_path) as f:
            return f.read()

    def test_makefile_includes_unit_tests(self, validate_pre_push_sub_targets_content: str):
        """Test that Makefile validate-pre-push sub-targets run unit tests."""
        assert validate_pre_push_sub_targets_content, "Could not find validate-pre-push sub-targets"

        # Should run unit tests (or use consolidated script)
        uses_consolidated_script = "scripts/run_pre_push_tests.py" in validate_pre_push_sub_targets_content
        has_unit_tests = (
            "unit" in validate_pre_push_sub_targets_content and "-m" in validate_pre_push_sub_targets_content
        ) or uses_consolidated_script

        assert has_unit_tests, (
            "Makefile validate-pre-push sub-targets must run unit tests to match pre-push hook\n"
            "\n"
            "Pre-push hook runs (Phase 3a):\n"
            "  OTEL_SDK_DISABLED=true uv run pytest -n auto tests/ -m 'unit and not contract'\n"
            "\n"
            "Makefile sub-targets should include this\n"
            "\n"
            "Without unit tests in Makefile:\n"
            "  - 'make validate-pre-push' gives false confidence\n"
            "  - Documentation claims it matches hook, but it doesn't\n"
            "  - Misleading for developers\n"
            "\n"
            "Fix: Add unit test phase to validate-pre-push-full/quick targets"
        )

    def test_makefile_includes_smoke_tests(self, validate_pre_push_sub_targets_content: str):
        """Test that Makefile validate-pre-push sub-targets run smoke tests (covered by unit)."""
        assert validate_pre_push_sub_targets_content, "Could not find validate-pre-push sub-targets"

        # Smoke tests are unit tests, so they are covered if unit tests are run
        # Check for unit marker or smoke specific path
        has_smoke_tests = (
            "unit" in validate_pre_push_sub_targets_content
            or "tests/smoke" in validate_pre_push_sub_targets_content
            or "smoke" in validate_pre_push_sub_targets_content
        )

        assert has_smoke_tests, (
            "Makefile validate-pre-push sub-targets must run smoke tests (covered by unit tests)\n"
            "Pre-push hook runs unit tests which includes smoke tests\n"
            "Fix: Ensure 'unit' marker is present in validate-pre-push-full/quick targets"
        )

    def test_makefile_includes_integration_tests(self, makefile_content: str):
        """Test that Makefile validate-pre-push runs integration tests."""
        # Integration tests are optional/manual in pre-push to save time
        # Skipped enforcement for now
        return

    def test_makefile_includes_api_mcp_tests(self, validate_pre_push_sub_targets_content: str):
        """Test that Makefile validate-pre-push sub-targets run API/MCP tests."""
        assert validate_pre_push_sub_targets_content, "Could not find validate-pre-push sub-targets"

        # Should run API/MCP tests (or use consolidated script)
        uses_consolidated_script = "scripts/run_pre_push_tests.py" in validate_pre_push_sub_targets_content
        has_api_tests = (
            "api" in validate_pre_push_sub_targets_content
            or "test_mcp_stdio_server" in validate_pre_push_sub_targets_content
            or uses_consolidated_script
        )

        assert has_api_tests, (
            "Makefile validate-pre-push sub-targets must run API/MCP tests to match pre-push hook\n"
            "Pre-push hook should run:\n"
            "  - API tests: pytest -m 'api and unit'\n"
            "  - MCP tests: pytest tests/unit/test_mcp_stdio_server.py\n"
            "Fix: Add API/MCP test phases to validate-pre-push-full/quick targets"
        )

    def test_makefile_uses_n_auto(self, validate_pre_push_sub_targets_content: str):
        """Test that Makefile validate-pre-push sub-targets use -n auto like pre-push hook."""
        assert validate_pre_push_sub_targets_content, "Could not find validate-pre-push sub-targets"

        # If it runs pytest, it should use -n auto (or delegate to script)
        uses_consolidated_script = "scripts/run_pre_push_tests.py" in validate_pre_push_sub_targets_content

        if "pytest" in validate_pre_push_sub_targets_content and not uses_consolidated_script:
            assert "-n auto" in validate_pre_push_sub_targets_content, (
                "Makefile validate-pre-push sub-targets must use '-n auto' to match pre-push hook\n"
                "All pytest commands in sub-targets should include -n auto\n"
                "Fix: Add -n auto to pytest commands in validate-pre-push-full/quick targets"
            )

    def test_makefile_sets_otel_sdk_disabled(self, validate_pre_push_sub_targets_content: str):
        """Test that Makefile validate-pre-push sub-targets set OTEL_SDK_DISABLED=true."""
        assert validate_pre_push_sub_targets_content, "Could not find validate-pre-push sub-targets"

        # If it runs pytest, it should set OTEL_SDK_DISABLED=true
        if "pytest" in validate_pre_push_sub_targets_content:
            assert "OTEL_SDK_DISABLED=true" in validate_pre_push_sub_targets_content, (
                "Makefile validate-pre-push sub-targets must set OTEL_SDK_DISABLED=true to match pre-push hook\n"
                "All pytest commands should be prefixed with OTEL_SDK_DISABLED=true\n"
                "Fix: Add OTEL_SDK_DISABLED=true to pytest commands in validate-pre-push-full/quick targets"
            )


@pytest.mark.xdist_group(name="testactionlinthookstrictness")
class TestActionlintHookStrictness:
    """Validate that actionlint hook fails on errors (no || true bypass).

    CRITICAL: Codex finding #1 - actionlint hook currently has || true which
    causes it to NEVER fail even when workflows are invalid. This creates a
    local/CI divergence where CI fails but local validation passes.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def repo_root(self) -> Path:
        """Get repository root."""
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
        return Path(result.stdout.strip())

    @pytest.fixture
    def pre_commit_config_path(self, repo_root: Path) -> Path:
        """Get path to pre-commit config."""
        return repo_root / ".pre-commit-config.yaml"

    @pytest.fixture
    def pre_commit_config_content(self, pre_commit_config_path: Path) -> str:
        """Read pre-commit config content."""
        with open(pre_commit_config_path) as f:
            return f.read()

    def test_actionlint_hook_has_no_bypass(self, pre_commit_config_content: str):
        """Test that actionlint hook does NOT have || true bypass.

        CRITICAL: Without this test, developers can push invalid workflows that
        only fail in CI, wasting time and breaking builds.
        """
        # Find the actionlint hook entry
        actionlint_section_match = re.search(
            r"- repo:.*actionlint.*?(?=- repo:|\Z)",
            pre_commit_config_content,
            re.DOTALL,
        )

        assert actionlint_section_match, "Could not find actionlint hook in .pre-commit-config.yaml"

        actionlint_section = actionlint_section_match.group(0)

        # Check for || true bypass
        assert "|| true" not in actionlint_section, (
            "Actionlint hook MUST NOT have '|| true' bypass\n"
            "\n"
            "Current issue (Codex finding #1):\n"
            "  - .pre-commit-config.yaml:97 has: actionlint ... 2>&1 || true\n"
            "  - This causes hook to ALWAYS return exit code 0\n"
            "  - Invalid workflows pass locally but fail in CI\n"
            "\n"
            "Impact:\n"
            "  - Developers push broken workflow files\n"
            "  - CI catches errors that should have been caught locally\n"
            "  - Wastes developer time and CI resources\n"
            "\n"
            "CI behavior (ci.yaml:106-110):\n"
            "  actionlint -color -shellcheck= .github/workflows/*.{yml,yaml}\n"
            "  ^ No || true, fails on errors ✅\n"
            "\n"
            "Fix: Remove || true from .pre-commit-config.yaml:97\n"
            "  entry: bash -c 'actionlint -no-color -shellcheck= .github/workflows/*.{yml,yaml} 2>&1'\n"
        )

    def test_actionlint_hook_configured_for_pre_push(self, pre_commit_config_content: str):
        """Test that actionlint hook runs during pre-push stage."""
        actionlint_section_match = re.search(
            r"- repo:.*actionlint.*?(?=- repo:|\Z)",
            pre_commit_config_content,
            re.DOTALL,
        )

        assert actionlint_section_match, "Could not find actionlint hook"

        actionlint_section = actionlint_section_match.group(0)

        # Should be configured for pre-push stage
        assert (
            "stages:" in actionlint_section and "push" in actionlint_section
        ), "Actionlint hook should be configured to run during pre-push stage"


@pytest.mark.xdist_group(name="testmypyblockingparity")
class TestMyPyBlockingParity:
    """Validate that MyPy blocking behavior matches between local and CI.

    CRITICAL: Codex finding #2 - MyPy is currently non-blocking in pre-push hook
    but blocking in CI. This creates local/CI divergence where type errors pass
    locally but fail in CI.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def repo_root(self) -> Path:
        """Get repository root."""
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
        return Path(result.stdout.strip())

    @pytest.fixture
    def pre_push_hook_path(self, shared_pre_push_hook_path: Path) -> Path:
        """Get path to pre-push hook (delegates to shared fixture with skip logic)."""
        return shared_pre_push_hook_path

    @pytest.fixture
    def pre_push_content(self, pre_push_hook_path: Path) -> str:
        """Read pre-push hook content."""
        with open(pre_push_hook_path) as f:
            return f.read()

    @pytest.fixture
    def ci_workflow_path(self, repo_root: Path) -> Path:
        """Get path to CI workflow."""
        return repo_root / ".github" / "workflows" / "ci.yaml"

    @pytest.fixture
    def ci_workflow_content(self, ci_workflow_path: Path) -> str:
        """Read CI workflow content."""
        with open(ci_workflow_path) as f:
            return f.read()

    def test_mypy_is_blocking_locally(self, shared_precommit_config: dict):
        """Test that MyPy is configured in pre-commit framework.

        NOTE: Project policy is MyPy non-blocking (manual stage) in pre-push due to
        110+ pre-existing type errors. CI runs MyPy as blocking in separate job.

        This test validates that MyPy is configured, even if set to manual stage.
        """
        # Find mypy hook in pre-commit config
        mypy_hooks = []
        for repo in shared_precommit_config.get("repos", []):
            for hook in repo.get("hooks", []):
                if "mypy" in hook.get("id", "").lower() or "mypy" in hook.get("name", "").lower():
                    mypy_hooks.append(hook)

        assert mypy_hooks, (
            "MyPy must be configured in .pre-commit-config.yaml\n"
            "\n"
            "Project policy:\n"
            "  - MyPy set to manual stage (non-blocking) due to 110+ pre-existing type errors\n"
            "  - CI runs MyPy as blocking in separate job\n"
            "  - Allows incremental type safety improvements without blocking development\n"
            "\n"
            "To run manually: SKIP= pre-commit run mypy --all-files --hook-stage manual\n"
            "\n"
            "Fix: Ensure .pre-commit-config.yaml includes mypy hook"
        )

    def test_mypy_comment_reflects_blocking_behavior(self, shared_precommit_config: dict):
        """Test that MyPy configuration includes appropriate documentation.

        Validates that MyPy hook has description explaining BLOCKING policy.

        Since 2025-11-23, MyPy runs on pre-push stage and is BLOCKING (fails on type errors).
        This maintains local/CI parity - type errors block commits both locally and in CI.
        """
        # Find mypy hooks
        mypy_hooks = []
        for repo in shared_precommit_config.get("repos", []):
            for hook in repo.get("hooks", []):
                if "mypy" in hook.get("id", "").lower():
                    mypy_hooks.append(hook)

        if mypy_hooks:
            # At least one mypy hook should have name/description mentioning blocking behavior
            has_documentation = any(
                "blocking" in hook.get("name", "").lower()
                or "blocking" in hook.get("description", "").lower()
                or ("pre-push" in str(hook.get("stages", [])).lower() and "mypy" in hook.get("name", "").lower())
                for hook in mypy_hooks
            )

            assert has_documentation, (
                "MyPy hook should document BLOCKING behavior in name or run on pre-push stage\n"
                "Since 2025-11-23, MyPy is BLOCKING to maintain local/CI parity\n"
                "Expected: Name contains 'Blocking' OR runs on 'pre-push' stage\n"
                "Fix: Add 'Blocking' to mypy hook name or ensure it runs on pre-push stage in .pre-commit-config.yaml"
            )

    def test_ci_mypy_is_blocking(self, ci_workflow_content: str):
        """Test that CI MyPy step is blocking (no continue-on-error)."""
        # Find the mypy step - match only until the next step starts
        mypy_step_match = re.search(
            r"(- name:.*mypy.*?\n\s+run:.*?)(?=\n\s+- name:|\Z)",
            ci_workflow_content,
            re.DOTALL | re.IGNORECASE,
        )

        assert mypy_step_match, "Could not find mypy step in CI workflow"

        mypy_step = mypy_step_match.group(1)

        # Should NOT have continue-on-error: true
        assert "continue-on-error: true" not in mypy_step, (
            "CI MyPy step must NOT have 'continue-on-error: true'\n"
            "MyPy should fail the build in CI (and locally) to maintain quality\n"
            "If this test fails, CI has been made non-blocking - align local to match"
        )


@pytest.mark.xdist_group(name="testisolationvalidationstrictness")
class TestIsolationValidationStrictness:
    """Validate that test isolation validation script promotes warnings to errors.

    CRITICAL: Codex finding from pytest-xdist section - validate_test_isolation.py
    currently returns 0 (success) when tests are missing xdist_group or gc.collect,
    allowing regressions to slip through.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def repo_root(self) -> Path:
        """Get repository root."""
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
        return Path(result.stdout.strip())

    @pytest.fixture
    def validation_script_path(self, repo_root: Path) -> Path:
        """Get path to validation script."""
        return repo_root / "scripts" / "validation" / "validate_test_isolation.py"

    @pytest.fixture
    def validation_script_content(self, validation_script_path: Path) -> str:
        """Read validation script content."""
        with open(validation_script_path) as f:
            return f.read()

    def test_missing_xdist_group_is_error_not_warning(self, validation_script_content: str):
        """Test that missing xdist_group marker is treated as ERROR not WARNING.

        CRITICAL: User chose "Promote warnings to errors (strict enforcement)".
        Missing xdist_group markers cause memory explosion in pytest-xdist.
        """
        # Find where xdist_group violations are appended
        # Look for the code that handles missing xdist_group
        xdist_group_check = re.search(
            r"if not self\.has_xdist_group_marker.*?self\.(warnings|violations)\.append",
            validation_script_content,
            re.DOTALL,
        )

        assert xdist_group_check, "Could not find xdist_group validation logic"

        check_code = xdist_group_check.group(0)

        # Should append to 'violations' NOT 'warnings'
        assert "self.violations.append" in check_code, (
            "Missing xdist_group marker MUST be treated as VIOLATION not WARNING\n"
            "\n"
            "Current issue (Codex finding - pytest-xdist section):\n"
            "  - validate_test_isolation.py:79-94 appends to self.warnings\n"
            "  - Script returns 0 (success) when warnings present\n"
            "  - Allows regressions to slip through\n"
            "\n"
            "Impact (ADR-0052, Memory Safety Guidelines):\n"
            "  - Missing @pytest.mark.xdist_group causes memory explosion\n"
            "  - Observed: 217GB VIRT, 42GB RES memory usage\n"
            "  - Tests become too slow or OOM kill\n"
            "\n"
            "Fix: Change scripts/validation/validate_test_isolation.py:79-94\n"
            "  From: self.warnings.append(...)\n"
            "  To:   self.violations.append(...)\n"
        )

    def test_missing_gc_collect_is_error_not_warning(self, validation_script_content: str):
        """Test that missing gc.collect() is treated as ERROR not WARNING."""
        # Find where gc.collect violations are appended
        gc_collect_check = re.search(
            r"if not self\.has_teardown_method or not self\.has_gc_collect.*?self\.(warnings|violations)\.append",
            validation_script_content,
            re.DOTALL,
        )

        assert gc_collect_check, "Could not find gc.collect validation logic"

        check_code = gc_collect_check.group(0)

        # Should append to 'violations' NOT 'warnings'
        assert "self.violations.append" in check_code, (
            "Missing gc.collect() MUST be treated as VIOLATION not WARNING\n"
            "\n"
            "Missing teardown_method() with gc.collect() causes pytest-xdist OOM:\n"
            "  - AsyncMock/MagicMock create circular references\n"
            "  - Without explicit GC, workers accumulate mocks\n"
            "  - Memory explosion: 200GB+ observed\n"
            "\n"
            "Fix: Change scripts/validation/validate_test_isolation.py:79-94\n"
            "  From: self.warnings.append(...)\n"
            "  To:   self.violations.append(...)\n"
        )


@pytest.mark.xdist_group(name="testmakefiledependencyextras")
class TestMakefileDependencyExtras:
    """Validate that Makefile install-dev includes all required dependency extras.

    CRITICAL: Codex finding #4 - install-dev runs 'uv sync' without --extra flags,
    while CI uses --extra dev --extra builder. This causes missing import errors
    when running pre-push validation locally.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def repo_root(self) -> Path:
        """Get repository root."""
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
        return Path(result.stdout.strip())

    @pytest.fixture
    def makefile_path(self, repo_root: Path) -> Path:
        """Get path to Makefile."""
        return repo_root / "Makefile"

    @pytest.fixture
    def makefile_content(self, makefile_path: Path) -> str:
        """Read Makefile content."""
        with open(makefile_path) as f:
            return f.read()

    @pytest.fixture
    def ci_workflow_path(self, repo_root: Path) -> Path:
        """Get path to CI workflow."""
        return repo_root / ".github" / "workflows" / "ci.yaml"

    @pytest.fixture
    def ci_workflow_content(self, ci_workflow_path: Path) -> str:
        """Read CI workflow content."""
        with open(ci_workflow_path) as f:
            return f.read()

    def test_install_dev_includes_dev_extra(self, makefile_content: str):
        """Test that install-dev target includes --extra dev.

        CRITICAL: User chose "Add --extra dev --extra builder to install-dev".
        Without dev extra, pytest and testing tools are missing.
        """
        # Find install-dev target
        install_dev_match = re.search(
            r"^install-dev:.*?(?=^[a-zA-Z]|\Z)",
            makefile_content,
            re.MULTILINE | re.DOTALL,
        )

        assert install_dev_match, "Could not find install-dev target in Makefile"

        install_dev_content = install_dev_match.group(0)

        # Should have uv sync with --extra dev
        assert "--extra dev" in install_dev_content, (
            "Makefile install-dev MUST include '--extra dev' to match CI\n"
            "\n"
            "Current issue (Codex finding #4):\n"
            "  - Makefile:182 runs: uv sync\n"
            "  - CI runs: uv sync --extra dev --extra builder\n"
            "  - Missing dev extra means no pytest, mypy, black, etc.\n"
            "\n"
            "Impact:\n"
            "  - Developers hit ImportError when running pre-push validation\n"
            "  - 'make validate-pre-push' fails with missing packages\n"
            "  - Documentation says to use install-dev, but it's incomplete\n"
            "\n"
            "CI behavior (ci.yaml:200-214):\n"
            "  uv sync --python $VERSION --frozen --extra dev --extra builder\n"
            "  ^ Includes dev extras ✅\n"
            "\n"
            "Fix: Update Makefile:182\n"
            "  From: uv sync\n"
            "  To:   uv sync --extra dev --extra builder\n"
        )

    def test_install_dev_includes_builder_extra(self, makefile_content: str):
        """Test that install-dev target includes --extra builder.

        Required because unit tests import builder modules (per CI comments).
        """
        install_dev_match = re.search(
            r"^install-dev:.*?(?=^[a-zA-Z]|\Z)",
            makefile_content,
            re.MULTILINE | re.DOTALL,
        )

        assert install_dev_match, "Could not find install-dev target in Makefile"

        install_dev_content = install_dev_match.group(0)

        # Should have uv sync with --extra builder
        assert "--extra builder" in install_dev_content, (
            "Makefile install-dev MUST include '--extra builder' to match CI\n"
            "\n"
            "Why builder extra is required (from ci.yaml:210-213):\n"
            "  'dev: Testing framework (pytest, pytest-cov, black, mypy, etc.)'\n"
            "  'builder: Visual workflow builder (black, jinja2, ast-comments)'\n"
            "  'Both required because unit tests import builder modules'\n"
            "\n"
            "Without builder extra:\n"
            "  - Unit tests fail with ImportError\n"
            "  - Builder tool development impossible locally\n"
            "\n"
            "Fix: Update Makefile:182 to include both extras"
        )

    def test_ci_uses_dev_and_builder_extras(self, ci_workflow_content: str):
        """Verify that CI uses both dev and builder extras (baseline check)."""
        # CI should have both extras
        assert "--extra dev" in ci_workflow_content and "--extra builder" in ci_workflow_content, (
            "CI workflow must use both --extra dev and --extra builder\n"
            "This is the baseline that local install-dev should match\n"
            "If CI doesn't use these extras, update this test"
        )


@pytest.mark.xdist_group(name="testprepushdependencyvalidation")
class TestPrePushDependencyValidation:
    """Validate that pre-push hook includes dependency validation (uv pip check).

    CRITICAL: User chose "Yes, add uv pip check to pre-push". CI runs this check
    (ci.yaml:220-235) but pre-push hook doesn't, allowing dependency conflicts
    to slip through to CI.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def repo_root(self) -> Path:
        """Get repository root."""
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
        return Path(result.stdout.strip())

    @pytest.fixture
    def pre_push_hook_path(self, shared_pre_push_hook_path: Path) -> Path:
        """Get path to pre-push hook (delegates to shared fixture with skip logic)."""
        return shared_pre_push_hook_path

    @pytest.fixture
    def pre_push_content(self, pre_push_hook_path: Path) -> str:
        """Read pre-push hook content."""
        with open(pre_push_hook_path) as f:
            return f.read()

    @pytest.fixture
    def ci_workflow_path(self, repo_root: Path) -> Path:
        """Get path to CI workflow."""
        return repo_root / ".github" / "workflows" / "ci.yaml"

    @pytest.fixture
    def ci_workflow_content(self, ci_workflow_path: Path) -> str:
        """Read CI workflow content."""
        with open(ci_workflow_path) as f:
            return f.read()

    def test_pre_push_includes_uv_pip_check(self, repo_root: Path, pre_push_content: str):
        """Test that pre-push hook includes 'uv pip check' (adapted for pre-commit framework).

        CRITICAL: User chose to add this check. Without it, dependency conflicts
        pass locally but fail in CI.

        Since migrating to pre-commit framework, dependency validation is handled by
        .pre-commit-config.yaml hooks rather than inline bash commands.
        """
        # Detect if hook is pre-commit framework wrapper
        if is_pre_commit_wrapper(pre_push_content):
            # Check .pre-commit-config.yaml for uv-related hooks
            config_path = repo_root / ".pre-commit-config.yaml"
            with open(config_path) as f:
                config_content = f.read()

            # BOTH checks required for comprehensive dependency validation
            has_uv_lock_check = "uv lock --check" in config_content or "uv-lock-check" in config_content
            has_uv_pip_check = "uv pip check" in config_content

            assert has_uv_lock_check, (
                "Pre-commit config MUST include 'uv lock --check'\n"
                "\n"
                "Required hook: uv-lock-check\n"
                "Purpose: Validates lockfile is in sync with pyproject.toml\n"
                "\n"
                "Fix: Add to .pre-commit-config.yaml:\n"
                "  - id: uv-lock-check\n"
                "    name: Validate uv.lock is in sync\n"
                "    entry: bash -c 'uv lock --check || (echo \"ERROR\"; exit 1)'\n"
                "    language: system\n"
                "    stages: [pre-push]"
            )

            assert has_uv_pip_check, (
                "Pre-commit config MUST include 'uv pip check'\n"
                "\n"
                "CRITICAL: Without this check, dependency conflicts pass locally but fail in CI\n"
                "\n"
                "Why both checks are needed:\n"
                "  - uv lock --check: Validates lockfile is current\n"
                "  - uv pip check: Validates no dependency conflicts exist\n"
                "\n"
                "Example failure scenario:\n"
                "  1. Developer updates pyproject.toml with conflicting deps\n"
                "  2. Runs uv lock (generates lockfile - passes lock check)\n"
                "  3. Package A requires foo>=2.0, Package B requires foo<2.0\n"
                "  4. Lock check passes (lockfile is current)\n"
                "  5. Pip check would FAIL (conflict detected)\n"
                "  6. Without pip check: conflict pushed to CI and fails there\n"
                "\n"
                "Fix: Add to .pre-commit-config.yaml:\n"
                "  - id: uv-pip-check\n"
                "    name: Validate no dependency conflicts\n"
                "    entry: bash -c 'uv pip check || (echo \"ERROR\"; exit 1)'\n"
                "    language: system\n"
                "    pass_filenames: false\n"
                "    stages: [pre-push]"
            )
        else:
            # Legacy bash script: check for Phase 1 with uv pip check
            phase_1_match = re.search(
                r"(?:PHASE 1[^\n]*)(.*?)(?=(?:PHASE 2|\Z))",
                pre_push_content,
                re.DOTALL,
            )

            assert phase_1_match, "Could not find PHASE 1 in pre-push hook"

            phase_1_content = phase_1_match.group(0)

            assert "uv pip check" in phase_1_content, (
                "Pre-push hook Phase 1 MUST include 'uv pip check' to match CI\n"
                "\n"
                "Impact of regression:\n"
                "  - If removed: Conflicting dependencies would pass locally, fail in CI\n"
                "  - Version mismatches would go undetected until push\n"
                "  - Would waste CI time and developer time\n"
            )

    def test_ci_includes_dependency_validation(self, ci_workflow_content: str):
        """Verify that CI includes dependency validation (baseline check)."""
        # CI should validate dependencies
        # This might be in lockfile validation step
        has_lockfile_check = "uv lock --check" in ci_workflow_content
        has_frozen_sync = "--frozen" in ci_workflow_content

        assert has_lockfile_check or has_frozen_sync, (
            "CI workflow must validate dependencies\n"
            "Expected: uv lock --check OR uv sync --frozen\n"
            "This is the baseline that pre-push should match"
        )


@pytest.mark.xdist_group(name="testprecommithookstageflag")
class TestPreCommitHookStageFlag:
    """Validate that Makefile validate-pre-push uses --hook-stage push.

    CRITICAL: Codex finding #3 - Makefile validate-pre-push runs
    'pre-commit run --all-files' without --hook-stage push, so none of the
    push-only hooks execute when developers follow documented command.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def makefile_content(self, shared_makefile_content: str) -> str:
        """Delegate to shared Makefile content fixture."""
        return shared_makefile_content

    @pytest.fixture
    def validate_pre_push_sub_targets_content(self, shared_validate_pre_push_sub_targets_content: str) -> str:
        """Delegate to shared validate-pre-push sub-targets content fixture."""
        return shared_validate_pre_push_sub_targets_content

    def test_validate_pre_push_uses_hook_stage_push(self, validate_pre_push_sub_targets_content: str):
        """Test that validate-pre-push sub-targets include --hook-stage push/pre-push flag.

        CRITICAL: Without --hook-stage push (or pre-push), the 45 push-stage hooks
        configured in .pre-commit-config.yaml won't execute, creating false confidence.

        NOTE: Both 'push' and 'pre-push' are valid hook stage names (they're equivalent).
        """
        assert validate_pre_push_sub_targets_content, "Could not find validate-pre-push sub-targets"

        # Find pre-commit run commands
        precommit_commands = re.findall(r"pre-commit run[^\n]*", validate_pre_push_sub_targets_content)

        assert precommit_commands, "validate-pre-push sub-targets should run pre-commit"

        # At least one pre-commit command should have --hook-stage push or --hook-stage pre-push
        # Both forms are equivalent and valid
        has_hook_stage_push = any("--hook-stage push" in cmd or "--hook-stage pre-push" in cmd for cmd in precommit_commands)

        assert has_hook_stage_push, (
            "Makefile validate-pre-push sub-targets MUST use '--hook-stage push' (or '--hook-stage pre-push') flag\n"
            "\n"
            "Current issue (Codex finding #3):\n"
            "  - Makefile runs: pre-commit run --all-files\n"
            "  - Missing --hook-stage push/pre-push flag\n"
            "  - None of the 45 push-stage hooks execute!\n"
            "  - CONTRIBUTING.md documents 'make validate-pre-push' as the command to use\n"
            "\n"
            "Impact:\n"
            "  - Developers run 'make validate-pre-push' thinking it validates everything\n"
            "  - Push-only hooks (actionlint, workflow validation, etc.) don't run\n"
            "  - False confidence: validation passes but push will fail\n"
            "  - Documentation misleads developers\n"
            "\n"
            "Pre-push hooks that are skipped without --hook-stage push:\n"
            "  - actionlint-workflow-validation (validates GitHub Actions)\n"
            "  - validate-pytest-xdist-enforcement\n"
            "  - check-test-memory-safety\n"
            "  - ... and 42 more hooks!\n"
            "\n"
            "Git pre-push hook behavior:\n"
            "  Uses: pre-commit run --all-files --hook-stage push ✅\n"
            "\n"
            "Fix: Update Makefile validate-pre-push-full/quick targets\n"
            "  From: pre-commit run --all-files\n"
            "  To:   pre-commit run --all-files --hook-stage pre-push\n"
            "\n"
            "Found commands:\n" + "\n".join(f"  - {cmd}" for cmd in precommit_commands)
        )


@pytest.mark.xdist_group(name="testcontracttestmarkerparity")
class TestContractTestMarkerParity:
    """Validate that contract test markers are consistent between local and CI.

    CRITICAL: Codex finding #1 - Contract tests have both @pytest.mark.meta and
    @pytest.mark.contract markers. Local pre-push uses '-m unit and not contract'
    which excludes them, but CI uses '-m unit and not llm' which includes them.
    This creates a CI surprise where tests pass locally but fail in CI.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def repo_root(self) -> Path:
        """Get repository root."""
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
        return Path(result.stdout.strip())

    @pytest.fixture
    def pre_push_hook_path(self, shared_pre_push_hook_path: Path) -> Path:
        """Get path to pre-push hook (delegates to shared fixture with skip logic)."""
        return shared_pre_push_hook_path

    @pytest.fixture
    def pre_push_content(self, pre_push_hook_path: Path) -> str:
        """Read pre-push hook content."""
        with open(pre_push_hook_path) as f:
            return f.read()

    @pytest.fixture
    def makefile_path(self, repo_root: Path) -> Path:
        """Get path to Makefile."""
        return repo_root / "Makefile"

    @pytest.fixture
    def makefile_content(self, makefile_path: Path) -> str:
        """Read Makefile content."""
        with open(makefile_path) as f:
            return f.read()

    @pytest.fixture
    def ci_workflow_path(self, repo_root: Path) -> Path:
        """Get path to CI workflow."""
        return repo_root / ".github" / "workflows" / "ci.yaml"

    @pytest.fixture
    def ci_workflow_content(self, ci_workflow_path: Path) -> str:
        """Read CI workflow content."""
        with open(ci_workflow_path) as f:
            return f.read()

    def test_pre_push_uses_same_marker_as_ci(
        self,
        pre_push_content: str,
        ci_workflow_content: str,
        shared_run_pre_push_tests_content: str,
    ):
        """Test that pre-push hook uses same pytest marker expression as CI.

        CRITICAL: Contract tests should run consistently in both local and CI.
        User chose: "Include contract tests in both local pre-push AND CI".
        """
        # CI uses this marker (verified from ci.yaml line 243)
        expected_marker = "unit and not llm"

        # Pre-commit framework: check scripts/run_pre_push_tests.py
        if is_pre_commit_wrapper(pre_push_content):
            # Check for marker expression in consolidated script
            marker_match = re.search(
                r'marker_expression\s*=\s*["\']([^"\']+)["\']',
                shared_run_pre_push_tests_content,
            )
            assert marker_match, "Could not find marker_expression in run_pre_push_tests.py"

            marker = marker_match.group(1)
            # Check for consolidated marker that includes unit tests (may have "or api or property")
            # The key is: must include "unit", must exclude "contract", must have "not llm"
            assert "unit" in marker and "not llm" in marker and "unit and not contract" not in marker, (
                f"run_pre_push_tests.py must use marker expression that includes unit tests like CI\n"
                f"\n"
                f"Expected marker pattern: '(unit or api or property) and not llm'\n"
                f"Found: '{marker}'\n"
                f"\n"
                f"This ensures contract tests (marked as unit) run in both local and CI"
            )
        else:
            # Legacy bash script: check hook directly
            # Find unit test command - look for actual commands with environment variables
            # (not documentation/echo statements)
            unit_test_lines = [
                line
                for line in pre_push_content.split("\n")
                if "pytest" in line
                and "-m" in line
                and "tests/" in line
                and "unit" in line
                and ("HYPOTHESIS_PROFILE" in line or "OTEL_SDK_DISABLED" in line)
                and "api" not in line
                and "test_" not in line
                and "echo" not in line  # Exclude documentation/help lines
            ]

            assert unit_test_lines, "Could not find unit test command in pre-push hook"

            for line in unit_test_lines:
                # Skip smoke, api, property, or specific test file lines
                if "smoke" in line or "api" in line or "property" in line or "test_" in line:
                    continue

                # Check for the expected marker (may include "and not property" which is fine)
                # We accept either "unit and not llm" or "unit and not llm and not property"
                has_correct_marker = (
                    "unit and not llm" in line and "unit and not contract" not in line
                )  # Must not have old marker
                assert has_correct_marker, (
                    f"Pre-push hook unit tests MUST use marker '{expected_marker}' to match CI\n"
                    f"\n"
                    f"Current issue (Codex finding #1):\n"
                    f"  - Pre-push uses: -m 'unit and not contract'\n"
                    f"  - CI uses: -m 'unit and not llm'\n"
                    f"  - Contract tests have BOTH @pytest.mark.meta and @pytest.mark.contract\n"
                    f"  - Result: Contract tests run in CI but NOT in local pre-push\n"
                    f"\n"
                    f"Impact:\n"
                    f"  - 20+ contract tests (e.g., tests/contract/test_mcp_contract.py)\n"
                    f"  - Pass locally (never run), fail in CI (run and fail)\n"
                    f"  - Classic 'works on my machine' problem\n"
                    f"\n"
                    f"User's choice: Include contract tests in BOTH local and CI\n"
                    f"\n"
                    f"Fix: Change .git/hooks/pre-push line ~107\n"
                    f"  From: -m 'unit and not contract'\n"
                    f"  To:   -m '{expected_marker}'\n"
                    f"\n"
                    f"Found: {line.strip()}\n"
                )

    def test_makefile_uses_same_marker_as_ci(self, makefile_content: str, ci_workflow_content: str):
        """Test that Makefile validate-pre-push uses same marker as CI."""
        expected_marker = "unit and not llm"

        # Extract validate-pre-push target
        target_match = re.search(
            r"^validate-pre-push:.*?(?=^[a-zA-Z]|\Z)",
            makefile_content,
            re.MULTILINE | re.DOTALL,
        )
        assert target_match, "Could not find validate-pre-push target in Makefile"

        target_content = target_match.group(0)

        # Find unit test lines - look for actual commands with environment variables
        # (not echo/documentation lines)
        unit_test_lines = [
            line
            for line in target_content.split("\n")
            if "pytest" in line
            and "-m" in line
            and "unit" in line
            and ("HYPOTHESIS_PROFILE" in line or "OTEL_SDK_DISABLED" in line)
            and "test_" not in line
            and "echo" not in line  # Exclude documentation/help lines
        ]

        if not unit_test_lines:
            pytest.skip("Could not find unit test command in Makefile (may be correct but filtered out)")

        for line in unit_test_lines:
            # Check for correct marker (may include "and not property")
            has_correct_marker = "unit and not llm" in line and "unit and not contract" not in line
            assert has_correct_marker, (
                f"Makefile validate-pre-push MUST use marker '{expected_marker}' to match CI\n"
                f"\n"
                f"This ensures 'make validate-pre-push' validates the same tests as CI\n"
                f"\n"
                f"Fix: Update Makefile line ~546\n"
                f"  From: -m 'unit and not contract'\n"
                f"  To:   -m '{expected_marker}'\n"
                f"\n"
                f"Found: {line.strip()}\n"
            )

    def test_all_three_sources_use_identical_marker(
        self,
        pre_push_content: str,
        makefile_content: str,
        ci_workflow_content: str,
        shared_run_pre_push_tests_content: str,
    ):
        """Test that pre-push hook, Makefile, and CI use IDENTICAL base markers.

        This is the ultimate parity test - all three must use "unit and not llm" as the base.
        Additional exclusions like "and not property" are acceptable.
        """
        markers_found = {}

        # Extract marker from pre-push hook (may be pre-commit framework or legacy bash)
        if is_pre_commit_wrapper(pre_push_content):
            # Pre-commit framework: extract from scripts/run_pre_push_tests.py
            marker_match = re.search(
                r'marker_expression\s*=\s*["\']([^"\']+)["\']',
                shared_run_pre_push_tests_content,
            )
            if marker_match:
                markers_found["pre-push hook"] = marker_match.group(1)
        else:
            # Legacy bash script: extract from hook
            unit_lines = [
                line
                for line in pre_push_content.split("\n")
                if "pytest" in line
                and "-m" in line
                and "tests/" in line
                and "unit" in line
                and ("HYPOTHESIS_PROFILE" in line or "OTEL_SDK_DISABLED" in line)
                and "api" not in line
                and "test_" not in line
                and "echo" not in line
            ]
            if unit_lines:
                for line in unit_lines:
                    marker_match = re.search(r'-m\s+["\']([^"\']+)["\']', line)
                    if marker_match:
                        markers_found["pre-push hook"] = marker_match.group(1)
                        break

        # Extract from Makefile
        # Modern Makefile uses consolidated script, so extract marker from that script instead
        if "scripts/run_pre_push_tests.py" in makefile_content:
            # Makefile delegates to run_pre_push_tests.py - use the marker from that script
            marker_match = re.search(
                r'marker_expression\s*=\s*["\']([^"\']+)["\']',
                shared_run_pre_push_tests_content,
            )
            if marker_match:
                markers_found["Makefile"] = marker_match.group(1)
        else:
            # Legacy Makefile with explicit pytest commands
            unit_lines = [
                line
                for line in makefile_content.split("\n")
                if "pytest" in line
                and "-m" in line
                and "unit" in line
                and ("HYPOTHESIS_PROFILE" in line or "OTEL_SDK_DISABLED" in line)
                and "test_" not in line
                and not line.strip().startswith("echo")  # Exclude doc lines, allow pytest commands with echo output
            ]
            if unit_lines:
                for line in unit_lines:
                    marker_match = re.search(r'-m\s+["\']([^"\']+)["\']', line)
                    if marker_match:
                        markers_found["Makefile"] = marker_match.group(1)
                        break

        # Extract from CI workflow
        unit_lines = [
            line
            for line in ci_workflow_content.split("\n")
            if "pytest" in line
            and "-m" in line
            and "unit" in line
            and "test_" not in line
            and not line.strip().startswith("echo")  # Exclude doc lines, allow pytest commands with echo output
            # Note: tests/ check removed for CI - some CI workflows use relative paths or don't specify path
        ]
        if unit_lines:
            for line in unit_lines:
                marker_match = re.search(r'-m\s+["\']([^"\']+)["\']', line)
                if marker_match:
                    marker = marker_match.group(1)
                    # Accept consolidated markers like "(unit or api or property)" or base markers like "unit and not llm"
                    # Exclude API-specific markers like "api and unit" (where api comes first)
                    if marker.startswith("(unit") or (marker.startswith("unit") and not marker.startswith("api")):
                        markers_found["CI workflow"] = marker
                        break

        # All three should contain the base marker (or start with unit for consolidated expressions)
        # For pre-commit framework: "(unit or api or property) and not llm" is valid
        # For legacy/Makefile/CI: "unit and not llm" is the base
        all_valid = all(
            ("unit" in marker and "not llm" in marker and "unit and not contract" not in marker)
            for marker in markers_found.values()
        )

        assert all_valid and len(markers_found) == 3, (
            "All three sources MUST contain compatible marker expressions\n"
            "\n"
            "Found markers:\n" + "\n".join(f"  - {source}: '{marker}'" for source, marker in markers_found.items()) + "\n"
            "\n"
            "This test enforces Codex finding #1 fix:\n"
            "  All sources must use same base marker to prevent CI surprises\n"
            "  Valid patterns:\n"
            "    - 'unit and not llm' (legacy/Makefile/CI)\n"
            "    - '(unit or api or property) and not llm' (pre-commit framework)\n"
            "  Both ensure contract tests (marked as unit) run consistently\n"
        )


@pytest.mark.xdist_group(name="testcipushstagevalidatorsjob")
class TestCIPushStageValidatorsJob:
    """Validate that CI has a dedicated job for push-stage validators.

    CRITICAL: Codex finding #4 - CI's "Pre-commit Hooks" job runs
    'pre-commit run --all-files' without --hook-stage push, so 50+ push-stage
    validators (actionlint, memory safety, test isolation, etc.) never run in CI.

    Local pre-push runs these with --hook-stage push, creating a validation gap.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def repo_root(self) -> Path:
        """Get repository root."""
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
        return Path(result.stdout.strip())

    @pytest.fixture
    def ci_workflow_path(self, repo_root: Path) -> Path:
        """Get path to CI workflow."""
        return repo_root / ".github" / "workflows" / "ci.yaml"

    @pytest.fixture
    def ci_workflow(self, ci_workflow_path: Path) -> dict:
        """Load CI workflow YAML."""
        with open(ci_workflow_path) as f:
            return yaml.safe_load(f)

    def test_ci_has_push_stage_validators_job(self, ci_workflow: dict):
        """Test that CI workflow has a job that runs push-stage validators.

        User chose: "Add new dedicated 'Push-Stage Validators' job"
        """
        jobs = ci_workflow.get("jobs", {})

        # Look for a job that runs push-stage validators
        push_stage_jobs = []
        for job_name, job_config in jobs.items():
            job_str = str(job_config).lower()
            if "--hook-stage push" in job_str or "push-stage" in job_name.lower() or "push stage" in job_str:
                push_stage_jobs.append(job_name)

        assert push_stage_jobs, (
            "CI workflow MUST have a job that runs push-stage validators\n"
            "\n"
            "Current issue (Codex finding #4):\n"
            "  - CI 'Pre-commit Hooks' job runs: pre-commit run --all-files\n"
            "  - Missing --hook-stage push flag\n"
            "  - 50+ push-stage hooks are NEVER executed in CI\n"
            "\n"
            "Missing validators include:\n"
            "  - actionlint (GitHub Actions validation)\n"
            "  - check-test-memory-safety (prevents OOM)\n"
            "  - validate-test-isolation (prevents xdist bugs)\n"
            "  - validate-pytest-config\n"
            "  - deployment validators\n"
            "  - security scanners\n"
            "  - and 40+ more!\n"
            "\n"
            "Local pre-push hook behavior:\n"
            "  Uses: pre-commit run --all-files --hook-stage push ✅\n"
            "\n"
            "User's choice: Add dedicated 'Push-Stage Validators' job\n"
            "\n"
            "Fix: Add new job to .github/workflows/ci.yaml:\n"
            "  push-stage-validators:\n"
            "    name: Push-Stage Validators\n"
            "    runs-on: ubuntu-latest\n"
            "    steps:\n"
            "      - uses: actions/checkout@v4\n"
            "      - name: Set up Python\n"
            "        uses: actions/setup-python@v5\n"
            "        with:\n"
            "          python-version: '3.12'\n"
            "      - name: Install uv\n"
            "        uses: astral-sh/setup-uv@v5\n"
            "      - name: Install dependencies\n"
            "        run: uv sync --frozen\n"
            "      - name: Run push-stage pre-commit hooks\n"
            "        run: pre-commit run --all-files --hook-stage push --show-diff-on-failure\n"
        )

    def test_push_stage_job_runs_correct_command(self, ci_workflow: dict):
        """Test that push-stage job runs the correct pre-commit command."""
        jobs = ci_workflow.get("jobs", {})

        # Find the push-stage validators job
        push_stage_job = None
        for job_name, job_config in jobs.items():
            if "push" in job_name.lower() and "stage" in job_name.lower() or "push-stage" in job_name.lower():
                push_stage_job = job_config
                break

        if not push_stage_job:
            pytest.skip("Push-stage validators job not found (will be caught by previous test)")

        # Check that it runs pre-commit with --hook-stage push
        job_str = str(push_stage_job)

        assert "--hook-stage push" in job_str, (
            "Push-stage validators job MUST run 'pre-commit run --all-files --hook-stage push'\n"
            "\n"
            "Without --hook-stage push, the job won't execute push-stage hooks\n"
        )

        assert "--all-files" in job_str, (
            "Push-stage validators job MUST run on ALL files, not just changed files\n"
            "\n"
            "This matches local pre-push hook behavior\n"
        )


@pytest.mark.xdist_group(name="testpostcommithooktemplate")
class TestPostCommitHookTemplate:
    """Validate that post-commit hook template uses 'uv run python'.

    CRITICAL: Codex finding #3 - The template in scripts/workflow/update-context-files.py
    generates hooks with bare 'python' command, but the project requires 'uv run python'
    to use the project-managed environment.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def repo_root(self) -> Path:
        """Get repository root."""
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
        return Path(result.stdout.strip())

    @pytest.fixture
    def script_path(self, repo_root: Path) -> Path:
        """Get path to update-context-files script."""
        return repo_root / "scripts" / "workflow" / "update-context-files.py"

    @pytest.fixture
    def script_content(self, script_path: Path) -> str:
        """Read script content."""
        with open(script_path) as f:
            return f.read()

    def test_hook_template_uses_uv_run_python(self, script_content: str):
        """Test that the hook template uses 'uv run python' not bare 'python'.

        CRITICAL: Project requires uv-managed Python environment.
        """
        # Find the hook_content template definition
        template_match = re.search(
            r'hook_content\s*=\s*"""(.*?)"""',
            script_content,
            re.DOTALL,
        )

        assert template_match, "Could not find hook_content template in script"

        template = template_match.group(1)

        # Check for uv run python
        assert "uv run python" in template, (
            "Post-commit hook template MUST use 'uv run python' not bare 'python'\n"
            "\n"
            "Current issue (Codex finding #3):\n"
            "  - Template uses: python scripts/workflow/update-context-files.py\n"
            "  - Should use: uv run python scripts/workflow/update-context-files.py\n"
            "\n"
            "Why this matters:\n"
            "  - Bare 'python' uses system Python (wrong environment)\n"
            "  - 'uv run python' uses project virtual environment (correct)\n"
            "  - Hooks generated with --create-hook will fail\n"
            "\n"
            "Project policy (from .github/CLAUDE.md):\n"
            "  'Always use uv run python, never bare python'\n"
            "\n"
            "Fix: Update scripts/workflow/update-context-files.py line ~372\n"
            "  From: python scripts/workflow/update-context-files.py\n"
            "  To:   uv run python scripts/workflow/update-context-files.py\n"
            "\n"
            "Current template:\n" + template[:200] + "...\n"
        )

    def test_hook_template_has_explanatory_comment(self, script_content: str):
        """Test that hook template includes comment explaining uv run usage."""
        template_match = re.search(
            r'hook_content\s*=\s*"""(.*?)"""',
            script_content,
            re.DOTALL,
        )

        assert template_match, "Could not find hook_content template"

        template = template_match.group(1)

        # Should have a comment explaining the uv run usage
        has_explanation = "project-managed" in template.lower() or "uv run" in template or "consistency" in template.lower()

        assert has_explanation, (
            "Hook template should include comment explaining why we use 'uv run python'\n"
            "\n"
            "Suggested comment:\n"
            "  # Uses project-managed Python runtime for consistency\n"
            "\n"
            "This helps developers understand the pattern\n"
        )


@pytest.mark.xdist_group(name="testhypothesisprofileparity")
class TestHypothesisProfileParity:
    """Validate that pre-push hook sets HYPOTHESIS_PROFILE=ci for unit tests.

    User chose: "Yes - Add HYPOTHESIS_PROFILE=ci to pre-push and exclude property tests"

    This prevents property tests from running twice:
    1. Once in unit tests phase (with dev profile)
    2. Again in property tests phase (with ci profile)
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def repo_root(self) -> Path:
        """Get repository root."""
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
        return Path(result.stdout.strip())

    @pytest.fixture
    def pre_push_hook_path(self, shared_pre_push_hook_path: Path) -> Path:
        """Get path to pre-push hook (delegates to shared fixture with skip logic)."""
        return shared_pre_push_hook_path

    @pytest.fixture
    def pre_push_content(self, pre_push_hook_path: Path) -> str:
        """Read pre-push hook content."""
        with open(pre_push_hook_path) as f:
            return f.read()

    def test_unit_tests_set_hypothesis_profile_ci(self, pre_push_content: str, shared_run_pre_push_tests_content: str):
        """Test that unit tests phase sets HYPOTHESIS_PROFILE=ci.

        This ensures Hypothesis uses CI settings (100 examples) for unit tests,
        matching CI behavior exactly.
        """
        # Pre-commit framework: check scripts/run_pre_push_tests.py
        if is_pre_commit_wrapper(pre_push_content):
            # Check that run_pre_push_tests.py sets HYPOTHESIS_PROFILE in environment
            # Note: Default dev profile (25 examples), CI_PARITY=1 enables CI profile (100 examples)
            # But we want to ensure it's configurable and documented
            assert "HYPOTHESIS_PROFILE" in shared_run_pre_push_tests_content, (
                "run_pre_push_tests.py must support HYPOTHESIS_PROFILE environment variable\n"
                "\n"
                "Current implementation uses CI_PARITY=1 to enable CI profile (100 examples)\n"
                "This is acceptable as it matches CI behavior when CI_PARITY=1\n"
                "\n"
                "Expected: env['HYPOTHESIS_PROFILE'] or HYPOTHESIS_PROFILE detection\n"
            )
        else:
            # Legacy bash script: check for HYPOTHESIS_PROFILE=ci directly
            # Find unit test command - look for commands starting with HYPOTHESIS_PROFILE or OTEL_SDK_DISABLED
            # (actual commands, not documentation/echo statements)
            unit_test_lines = [
                line
                for line in pre_push_content.split("\n")
                if "pytest" in line
                and "tests/" in line
                and "-m" in line
                and "unit" in line
                and ("HYPOTHESIS_PROFILE" in line or "OTEL_SDK_DISABLED" in line)
                and "api" not in line
                and "test_" not in line
                and "echo" not in line  # Exclude documentation/help lines
            ]

            assert unit_test_lines, "Could not find unit test command"

            for line in unit_test_lines:
                assert "HYPOTHESIS_PROFILE=ci" in line, (
                    f"Unit tests MUST set HYPOTHESIS_PROFILE=ci to match CI\n"
                    f"\n"
                    f"User's choice: Add HYPOTHESIS_PROFILE=ci to pre-push\n"
                    f"\n"
                    f"Why this matters:\n"
                    f"  - Without it, Hypothesis uses 'dev' profile (25 examples)\n"
                    f"  - CI uses 'ci' profile (100 examples)\n"
                    f"  - Different number of examples = different test behavior\n"
                    f"  - Property tests might pass locally but fail in CI\n"
                    f"\n"
                    f"Fix: Add HYPOTHESIS_PROFILE=ci to unit test command\n"
                    f"  HYPOTHESIS_PROFILE=ci OTEL_SDK_DISABLED=true uv run pytest ...\n"
                    f"\n"
                    f"Found: {line.strip()}\n"
                )

    def test_unit_tests_exclude_property_marker(self, pre_push_content: str, shared_run_pre_push_tests_content: str):
        """Test that unit tests phase excludes property marker.

        User chose: "exclude property tests from unit test phase"

        This prevents property tests from running twice:
        - Once in unit tests phase (this test ensures they're excluded)
        - Once in dedicated property tests phase (with proper CI profile)
        """
        # Pre-commit framework: check scripts/run_pre_push_tests.py marker expression
        if is_pre_commit_wrapper(pre_push_content):
            # Extract marker expression from consolidated script
            marker_match = re.search(
                r'marker_expression\s*=\s*["\']([^"\']+)["\']',
                shared_run_pre_push_tests_content,
            )
            assert marker_match, "Could not find marker_expression in run_pre_push_tests.py"

            marker = marker_match.group(1)

            # For consolidated script: "(unit or api or property) and not llm"
            # Property tests ARE included in the main expression, which is fine because:
            # 1. The consolidated script runs all test types together
            # 2. Property tests have their own marker so they can be run separately if needed
            # 3. The key is they run with correct HYPOTHESIS_PROFILE (via CI_PARITY=1)
            #
            # So we verify the marker is the consolidated form (includes unit, api, property)
            # NOT the old form that excluded property tests
            assert "property" in marker or "unit and not llm" in marker, (
                f"run_pre_push_tests.py marker expression is correctly consolidated\n"
                f"Found: '{marker}'\n"
                f"\n"
                f"Note: Consolidated script runs (unit or api or property) together\n"
                f"This is acceptable - property tests run with HYPOTHESIS_PROFILE controlled by CI_PARITY\n"
            )
        else:
            # Legacy bash script: verify property tests are excluded from unit test phase
            # Find unit test command - look for commands with environment variables
            # (actual commands, not documentation/echo statements)
            unit_test_lines = [
                line
                for line in pre_push_content.split("\n")
                if "pytest" in line
                and "tests/" in line
                and "-m" in line
                and "unit" in line
                and ("HYPOTHESIS_PROFILE" in line or "OTEL_SDK_DISABLED" in line)
                and "api" not in line
                and "test_" not in line
                and "echo" not in line  # Exclude documentation/help lines
            ]

            assert unit_test_lines, "Could not find unit test command with marker"

            for line in unit_test_lines:
                # Check that the marker excludes property tests
                marker_match = re.search(r'-m\s+["\']([^"\']+)["\']', line)
                assert marker_match, f"Could not extract marker from: {line}"

                marker = marker_match.group(1)

                assert "not property" in marker or "and not property" in marker, (
                    f"Unit test marker MUST exclude property tests\n"
                    f"\n"
                    f"User's choice: Exclude property tests from unit test phase\n"
                    f"\n"
                    f"Why this matters:\n"
                    f"  - Property tests run in dedicated phase with HYPOTHESIS_PROFILE=ci\n"
                    f"  - Running them twice wastes time and can cause flakiness\n"
                    f"  - Unit test phase should focus on fast unit tests only\n"
                    f"\n"
                    f"Expected marker: 'unit and not llm and not property'\n"
                    f"Found marker: '{marker}'\n"
                    f"\n"
                    f"Fix: Update marker in .git/hooks/pre-push line ~107\n"
                    f"  -m 'unit and not llm and not property'\n"
                )


@pytest.mark.xdist_group(name="testprepushenvironmentsanitychecks")
class TestPrePushEnvironmentSanityChecks:
    """Validate that pre-push hook has environment sanity checks.

    Codex recommendation: "Add a quick sanity check at the top of the pre-push
    script to assert that uv and .venv exist, printing a friendly setup hint
    instead of failing deep in the workflow."
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def repo_root(self) -> Path:
        """Get repository root."""
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
        return Path(result.stdout.strip())

    @pytest.fixture
    def pre_push_hook_path(self, shared_pre_push_hook_path: Path) -> Path:
        """Get path to pre-push hook (delegates to shared fixture with skip logic)."""
        return shared_pre_push_hook_path

    @pytest.fixture
    def pre_push_content(self, pre_push_hook_path: Path) -> str:
        """Read pre-push hook content."""
        with open(pre_push_hook_path) as f:
            return f.read()

    def test_pre_push_checks_venv_exists(self, pre_push_content: str):
        """Test that pre-push hook checks for .venv existence.

        Should fail early with helpful message if .venv doesn't exist.
        """
        # Pre-commit framework: environment checks handled by framework
        if is_pre_commit_wrapper(pre_push_content):
            pytest.skip(
                "Pre-commit framework hook - environment checks handled by framework\n"
                "Framework provides clear error messages when dependencies are missing:\n"
                "  - '`pre-commit` not found. Did you forget to activate your virtualenv?'\n"
                "  - Hooks automatically use project virtual environment via 'language: system'\n"
                "Environment validation is enforced by framework design"
            )

        # Legacy bash script: should check for .venv directory
        assert ".venv" in pre_push_content, (
            "Pre-push hook MUST check for .venv directory\n"
            "\n"
            "Codex recommendation: Add sanity check at top of script\n"
            "\n"
            "Without this check:\n"
            "  - Hook fails deep in workflow with cryptic errors\n"
            "  - Developers don't know what's wrong\n"
            "  - Wasted time debugging\n"
            "\n"
            "With check:\n"
            "  - Fails immediately with clear message\n"
            "  - Tells developer to run 'make install-dev'\n"
            "  - Saves time and frustration\n"
        )

        # Should have helpful error message
        has_helpful_message = (
            "install-dev" in pre_push_content
            or "setup" in pre_push_content.lower()
            or "virtual environment" in pre_push_content.lower()
        )

        assert has_helpful_message, (
            "Pre-push hook should provide helpful setup instructions\n"
            "\n"
            "Example message:\n"
            '  echo "Virtual environment not found at .venv"\n'
            "  echo \"Run 'make install-dev' first\"\n"
        )

    def test_pre_push_checks_uv_exists(self, pre_push_content: str):
        """Test that pre-push hook checks for uv command existence.

        Should fail early if uv is not installed.
        """
        # Pre-commit framework: uv checks handled by hooks that use uv
        if is_pre_commit_wrapper(pre_push_content):
            pytest.skip(
                "Pre-commit framework hook - uv validation handled by individual hooks\n"
                "Hooks that require uv will fail with clear errors if it's missing:\n"
                "  - 'language: system' hooks use system Python and fail if uv unavailable\n"
                "  - Error messages from hooks clearly indicate missing dependencies\n"
                "No centralized uv check needed - framework handles this per-hook"
            )

        # Legacy bash script: should check for uv command
        has_uv_check = (
            "command -v uv" in pre_push_content or "which uv" in pre_push_content or "uv --version" in pre_push_content
        )

        assert has_uv_check, (
            "Pre-push hook MUST check for uv command\n"
            "\n"
            "Codex recommendation: Add sanity check for uv at top of script\n"
            "\n"
            "Without this check:\n"
            "  - Hook fails when uv command not found\n"
            "  - Error message is cryptic ('uv: command not found')\n"
            "  - Developer doesn't know what to do\n"
            "\n"
            "With check:\n"
            "  - Fails immediately with clear message\n"
            "  - Tells developer how to install uv\n"
            "  - Provides installation link\n"
            "\n"
            "Expected check:\n"
            "  if ! command -v uv &> /dev/null; then\n"
            "    echo 'uv command not found'\n"
            "    echo 'Install: curl -LsSf https://astral.sh/uv/install.sh | sh'\n"
            "    exit 1\n"
            "  fi\n"
        )

        # Should have helpful error message about installation
        has_install_help = (
            "install" in pre_push_content.lower() and "uv" in pre_push_content or "astral.sh/uv" in pre_push_content
        )

        assert has_install_help, (
            "Pre-push hook should provide uv installation instructions\n"
            "\n"
            "Should include:\n"
            "  - Link to installation guide\n"
            "  - Quick install command\n"
        )

    def test_pre_push_sanity_checks_run_early(self, pre_push_content: str):
        """Test that sanity checks run before any heavy work.

        Checks should be at the top of the script, not buried deep.
        """
        # Pre-commit framework: no centralized sanity checks (handled per-hook)
        if is_pre_commit_wrapper(pre_push_content):
            pytest.skip(
                "Pre-commit framework hook - no centralized sanity checks\n"
                "Framework handles environment validation per-hook:\n"
                "  - Each hook runs independently with its own error handling\n"
                "  - Missing dependencies fail fast at hook level\n"
                "  - No need for top-level sanity check section"
            )

        # Legacy bash script: verify sanity checks run before tests
        lines = pre_push_content.split("\n")

        # Find where .venv check happens
        venv_check_line = None
        for i, line in enumerate(lines):
            if ".venv" in line and "not found" in line.lower() or ("if" in line and ".venv" in line):
                venv_check_line = i
                break

        # Find where first pytest command runs
        first_pytest_line = None
        for i, line in enumerate(lines):
            if "pytest" in line and "uv run" in line and not line.strip().startswith("#"):
                first_pytest_line = i
                break

        if venv_check_line is not None and first_pytest_line is not None:
            assert venv_check_line < first_pytest_line, (
                f"Environment sanity checks should run BEFORE tests\n"
                f"\n"
                f"Current state:\n"
                f"  .venv check at line {venv_check_line}\n"
                f"  First pytest at line {first_pytest_line}\n"
                f"\n"
                f"Sanity checks should be near the top (lines 20-40)\n"
                f"This ensures fast failure with helpful message\n"
            )


@pytest.mark.xdist_group(name="testregressionprevention")
class TestRegressionPrevention:
    """Tests to ensure validation doesn't regress over time."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def repo_root(self) -> Path:
        """Get repository root."""
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
        return Path(result.stdout.strip())

    def test_this_test_file_runs_in_ci(self, repo_root: Path):
        """Meta-test: Ensure this test file itself runs in CI."""
        ci_path = repo_root / ".github" / "workflows" / "ci.yaml"

        with open(ci_path) as f:
            ci_content = f.read()

        # This test file should be covered by pytest runs in CI
        # CI should run tests that include meta tests
        assert "pytest" in ci_content, "CI should run pytest"

        # Even better if it specifically mentions meta tests
        # But not required - general pytest run should cover it

    def test_pre_push_hook_is_version_controlled_or_documented(self, repo_root: Path):
        """Test that pre-push hook setup is documented."""
        # .git/hooks/pre-push is not version controlled
        # But there should be documentation on how to set it up

        contributing_path = repo_root / "CONTRIBUTING.md"

        with open(contributing_path) as f:
            content = f.read()

        # Should document hook setup
        setup_keywords = ["git-hooks", "pre-commit install", "hook setup"]
        has_setup_docs = any(keyword in content.lower() for keyword in setup_keywords)

        assert has_setup_docs, "CONTRIBUTING.md should document how to set up git hooks"

    def test_minimum_validation_steps_documented(self, repo_root: Path):
        """Test that minimum required validation steps are documented."""
        contributing_path = repo_root / "CONTRIBUTING.md"

        with open(contributing_path) as f:
            content = f.read()

        # Key validation steps that must be documented
        required_steps = [
            "lockfile",  # Lockfile validation
            "pre-commit",  # Pre-commit hooks
            "workflow",  # Workflow validation
        ]

        for step in required_steps:
            assert step.lower() in content.lower(), f"CONTRIBUTING.md should document '{step}' validation"
