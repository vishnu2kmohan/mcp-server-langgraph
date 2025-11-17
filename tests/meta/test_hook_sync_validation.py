"""
Meta-validation: Ensure Git hooks match CI/CD configuration exactly.

This test suite ensures that:
1. Pre-push hook uses `-n auto` for all pytest calls (matches CI)
2. Pre-push hook has MyPy configured as blocking (matches CI)
3. Post-commit hook uses project-managed Python runtime (uv run)
4. Hook configurations stay in sync with CI/CD workflows

TDD Principle: These tests prevent configuration drift between local hooks and CI.
They MUST pass to ensure consistent validation behavior everywhere.

Related:
- tests/meta/test_local_ci_parity.py - Overall CI/local parity
- tests/meta/test_pytest_xdist_enforcement.py - xdist enforcement
- .git/hooks/pre-push - Pre-push hook implementation
- .github/workflows/ci.yaml - CI workflow configuration
"""

import gc
import re
import subprocess
from pathlib import Path
from typing import List

import pytest

# Mark as unit+meta test to ensure it runs in CI (validates test infrastructure)
pytestmark = [pytest.mark.unit, pytest.mark.meta]


@pytest.mark.xdist_group(name="testprepushhooksync")
class TestPrePushHookSync:
    """Validate pre-push hook configuration matches CI expectations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def repo_root(self) -> Path:
        """Get repository root directory."""
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True, timeout=60
        )
        return Path(result.stdout.strip())

    @pytest.fixture
    def pre_push_hook_path(self, repo_root: Path) -> Path:
        """Get path to pre-push hook (handles git worktrees)."""
        # Use git rev-parse to get common git directory (handles worktrees)
        result = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"], capture_output=True, text=True, check=True, timeout=60, cwd=repo_root
        )
        git_common_dir = Path(result.stdout.strip())
        # If path is relative, make it relative to repo_root
        if not git_common_dir.is_absolute():
            git_common_dir = repo_root / git_common_dir
        return git_common_dir / "hooks" / "pre-push"

    @pytest.fixture
    def pre_push_hook_content(self, pre_push_hook_path: Path) -> str:
        """Read pre-push hook content."""
        assert pre_push_hook_path.exists(), (
            "Pre-push hook does not exist at .git/hooks/pre-push\n"
            "Run 'make git-hooks' or 'pre-commit install --hook-type pre-push'"
        )
        return pre_push_hook_path.read_text()

    def test_all_pytest_calls_use_n_auto(self, pre_push_hook_content: str):
        """
        Test that all pytest invocations use -n auto for parallel execution.

        Rationale:
        - CI uses `-n auto` to adapt to available GitHub runner cores
        - Local pre-push should match for consistent behavior
        - Using fixed worker counts (e.g., -n 4) causes:
          * Different parallel execution patterns locally vs CI
          * Missed pytest-xdist isolation bugs
          * Inconsistent test timing and resource usage

        Expected: All pytest commands must use `-n auto`
        """
        # Find all pytest invocation lines
        pytest_lines = [
            line for line in pre_push_hook_content.split("\n") if "pytest" in line and not line.strip().startswith("#")
        ]

        assert len(pytest_lines) > 0, "No pytest invocations found in pre-push hook"

        # Check each pytest invocation
        for line in pytest_lines:
            # Skip lines that are just variable definitions or comments
            if "=" in line and "pytest" in line.split("=")[0]:
                continue

            # Check if this is a pytest command (not a variable reference)
            if "uv run pytest" in line or line.strip().startswith("pytest"):
                assert "-n auto" in line, (
                    f"Pre-push hook must use '-n auto' for all pytest calls to match CI\n"
                    f"Found: {line.strip()}\n"
                    f"Expected: pytest -n auto ...\n"
                    f"\n"
                    f"Why this matters:\n"
                    f"- CI uses '-n auto' to adapt to runner cores\n"
                    f"- Fixed worker counts (e.g., -n 4) cause:\n"
                    f"  * Different parallel execution patterns locally vs CI\n"
                    f"  * Missed pytest-xdist isolation bugs\n"
                    f"  * Inconsistent test timing and resource usage\n"
                    f"\n"
                    f"Fix: Change all 'pytest -n 4' to 'pytest -n auto' in .git/hooks/pre-push"
                )

    def test_mypy_is_blocking(self, pre_push_hook_content: str):
        """
        Test that MyPy type checking is configured as blocking (critical).

        Rationale:
        - CI blocks on MyPy errors (no continue-on-error flag)
        - Local pre-push must match to prevent CI surprises
        - Warning-only MyPy locally means:
          * Developers push code with type errors
          * CI fails unexpectedly
          * Requires force-push fixes
          * Wastes time and breaks flow

        Expected: MyPy validation must have critical=true (blocking)
        """
        # Find MyPy validation section
        mypy_validation_pattern = r'run_validation\s+"[^"]*[Mm]y[Pp]y[^"]*"\s+[^}]+?(\w+)\s*#.*?critical'
        matches = list(re.finditer(mypy_validation_pattern, pre_push_hook_content, re.DOTALL))

        assert len(matches) > 0, (
            "No MyPy validation found in pre-push hook\n" "Expected: run_validation with MyPy in the description"
        )

        for match in matches:
            critical_flag = match.group(1)
            assert critical_flag == "true", (
                f"MyPy must be blocking (critical=true) to match CI behavior\n"
                f"Found: {match.group(0).strip()}\n"
                f"Critical flag: {critical_flag}\n"
                f"\n"
                f"Why this matters:\n"
                f"- CI blocks on MyPy errors (fails build if types are wrong)\n"
                f"- Local pre-push warning-only means:\n"
                f"  * Developers push code that fails CI\n"
                f"  * Surprise failures in GitHub Actions\n"
                f"  * Wasted time and context switching\n"
                f"\n"
                f"Fix: Change 'false # Temporarily non-critical' to 'true # Blocks on type errors'"
            )

    def test_no_hardcoded_worker_counts(self, pre_push_hook_content: str):
        """
        Test that pre-push hook does not use hardcoded worker counts like -n 4.

        This is a negative test to catch regressions where someone might
        add a new pytest call with a fixed worker count.
        """
        # Find all pytest invocations with -n followed by a number
        hardcoded_pattern = r'pytest\s+[^"\n]*-n\s+\d+'
        matches = list(re.finditer(hardcoded_pattern, pre_push_hook_content))

        if matches:
            failing_lines = "\n".join([m.group(0) for m in matches])
            pytest.fail(
                f"Pre-push hook contains hardcoded worker counts (e.g., -n 4)\n"
                f"Found:\n{failing_lines}\n"
                f"\n"
                f"Fix: Replace all hardcoded counts with '-n auto' to match CI"
            )


@pytest.mark.xdist_group(name="testpostcommithooksync")
class TestPostCommitHookSync:
    """Validate post-commit hook uses project-managed Python runtime."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def repo_root(self) -> Path:
        """Get repository root directory."""
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True, timeout=60
        )
        return Path(result.stdout.strip())

    @pytest.fixture
    def post_commit_hook_path(self, repo_root: Path) -> Path:
        """Get path to post-commit hook."""
        return repo_root / ".git" / "hooks" / "post-commit"

    @pytest.fixture
    def post_commit_hook_content(self, post_commit_hook_path: Path) -> str:
        """Read post-commit hook content."""
        if not post_commit_hook_path.exists():
            pytest.skip("Post-commit hook does not exist (optional)")
        return post_commit_hook_path.read_text()

    def test_uses_uv_run_python(self, post_commit_hook_content: str):
        """
        Test that post-commit hook uses 'uv run python' instead of bare 'python'.

        Rationale:
        - Project uses uv for dependency management
        - Bare 'python' uses global interpreter (may have wrong deps)
        - 'uv run python' ensures project-managed runtime
        - Consistency across all automation

        Expected: All python invocations use 'uv run python'
        """
        # Find all python invocations
        python_lines = [
            line for line in post_commit_hook_content.split("\n") if "python" in line and not line.strip().startswith("#")
        ]

        for line in python_lines:
            # Skip shebang lines
            if line.strip().startswith("#!"):
                continue

            # Check for bare python usage (not preceded by 'uv run')
            if re.search(r"\bpython\b", line) and "uv run python" not in line:
                assert False, (
                    f"Post-commit hook must use 'uv run python' for consistency\n"
                    f"Found: {line.strip()}\n"
                    f"\n"
                    f"Why this matters:\n"
                    f"- Bare 'python' uses global interpreter\n"
                    f"- May have wrong dependencies or Python version\n"
                    f"- 'uv run python' ensures project-managed runtime\n"
                    f"- Consistency with other automation\n"
                    f"\n"
                    f"Fix: Replace 'python' with 'uv run python' in .git/hooks/post-commit"
                )


@pytest.mark.xdist_group(name="testhooktemplatesync")
class TestHookTemplateSync:
    """Validate hook templates stay in sync or are properly removed."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def repo_root(self) -> Path:
        """Get repository root directory."""
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True, timeout=60
        )
        return Path(result.stdout.strip())

    @pytest.fixture
    def template_hook_path(self, repo_root: Path) -> Path:
        """Get path to template pre-push hook."""
        return repo_root / "scripts" / "git-hooks" / "pre-push"

    def test_template_matches_or_documented(self, repo_root: Path, template_hook_path: Path):
        """
        Test that template hook is either in sync with actual hook or documented as obsolete.

        Rationale:
        - scripts/git-hooks/pre-push is a tracked template
        - If it differs from .git/hooks/pre-push, it's confusing
        - Either keep them in sync or remove the template
        - Add documentation explaining the state

        This test will pass if:
        1. Template doesn't exist (removed as obsolete), OR
        2. Template contains a deprecation notice, OR
        3. Template matches actual hook configuration
        """
        if not template_hook_path.exists():
            # Template removed - that's fine
            return

        template_content = template_hook_path.read_text()

        # Check if template has deprecation notice
        deprecation_keywords = ["obsolete", "deprecated", "legacy", "do not use"]
        has_deprecation = any(keyword in template_content.lower() for keyword in deprecation_keywords)

        if has_deprecation:
            # Template is documented as obsolete - that's fine
            return

        # If template exists and is not marked obsolete, it should match actual hook
        actual_hook_path = repo_root / ".git" / "hooks" / "pre-push"
        if actual_hook_path.exists():
            actual_content = actual_hook_path.read_text()

            # Check for key configuration markers
            template_uses_n_auto = "-n auto" in template_content
            actual_uses_n_auto = "-n auto" in actual_content

            assert template_uses_n_auto == actual_uses_n_auto, (
                f"Template hook and actual hook have different pytest worker configurations\n"
                f"Template (-n auto): {template_uses_n_auto}\n"
                f"Actual (-n auto): {actual_uses_n_auto}\n"
                f"\n"
                f"Fix options:\n"
                f"1. Sync template to match actual hook\n"
                f"2. Remove template if obsolete\n"
                f"3. Add deprecation notice to template\n"
            )
