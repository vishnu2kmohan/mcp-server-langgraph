"""
Meta-validation: Ensure Makefile validate-pre-push matches pre-push hook exactly.

This test suite ensures that:
1. Makefile validate-pre-push target includes all validation steps from pre-push hook
2. MyPy blocking behavior matches between Makefile and pre-push hook
3. All pytest commands use same flags (-n auto, OTEL_SDK_DISABLED=true)
4. Warning/error handling behavior is consistent

TDD Principle: These tests MUST pass to ensure `make validate-pre-push` provides
same validation as actual git push, preventing "works locally, fails on push" scenarios.

Issue: Makefile has drifted from pre-push hook, making it less strict and creating
false confidence when developers run `make validate-pre-push` before pushing.
"""

import gc
import re
import subprocess
from pathlib import Path
from typing import Dict, List

import pytest

# Mark as unit+meta test to ensure it runs in CI (validates test infrastructure)
pytestmark = [pytest.mark.unit, pytest.mark.meta]


@pytest.mark.xdist_group(name="testmakefileprepushparity")
class TestMakefilePrePushParity:
    """Validate Makefile validate-pre-push target matches pre-push hook."""

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
    def makefile_path(self, repo_root: Path) -> Path:
        """Get path to Makefile."""
        return repo_root / "Makefile"

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
    def makefile_content(self, makefile_path: Path) -> str:
        """Read Makefile content."""
        with open(makefile_path, "r") as f:
            return f.read()

    @pytest.fixture
    def pre_push_content(self, pre_push_hook_path: Path) -> str:
        """Read pre-push hook content."""
        with open(pre_push_hook_path, "r") as f:
            return f.read()

    @pytest.fixture
    def makefile_validate_target(self, makefile_content: str) -> str:
        """Extract validate-pre-push target content from Makefile."""
        # Match from validate-pre-push: to the next target (line starting with non-whitespace)
        # Targets in Makefile start at column 0 (no indentation)
        pattern = r"^validate-pre-push:.*?(?=^\S|\Z)"
        match = re.search(pattern, makefile_content, re.MULTILINE | re.DOTALL)
        assert match, "Could not find validate-pre-push target in Makefile"
        return match.group(0)

    def test_makefile_includes_uv_pip_check(self, makefile_validate_target: str, pre_push_content: str):
        """
        Test that Makefile validate-pre-push includes uv pip check.

        CRITICAL DRIFT: Pre-push hook includes 'uv pip check' in Phase 1 (line 90-91)
        to validate dependency tree, but Makefile validate-pre-push target omits it.

        Impact:
        - Developers running 'make validate-pre-push' don't catch dependency conflicts
        - Conflicting dependencies only discovered when pushing (pre-push hook blocks)
        - False confidence: "make validate-pre-push passed" doesn't mean push will work

        Pre-push hook Phase 1 (lines 89-91):
            run_validation "Dependency Tree Validation" \\
                "uv pip check"

        Makefile validate-pre-push Phase 1 (line 529):
            @uv lock --check && echo "✓ Lockfile valid" || ...
            # Missing: uv pip check!

        Fix: Add 'uv pip check' to Makefile Phase 1 after lockfile validation.
        """
        # Verify pre-push hook has it (baseline)
        assert "uv pip check" in pre_push_content, "Pre-push hook should have 'uv pip check' as baseline for this test"

        # Verify Makefile has it (the actual test)
        assert "uv pip check" in makefile_validate_target, (
            "Makefile validate-pre-push MUST include 'uv pip check' to match pre-push hook\n"
            "\n"
            "Current drift:\n"
            "  - Pre-push hook Phase 1 includes 'uv pip check' (line 90-91)\n"
            "  - Makefile validate-pre-push Phase 1 omits this check (line 529)\n"
            "  - Dependency conflicts pass 'make validate-pre-push', fail on push\n"
            "\n"
            "Impact:\n"
            "  - False confidence when running 'make validate-pre-push'\n"
            "  - Developers surprised when push is blocked by hook\n"
            "  - Wastes developer time debugging 'it worked locally'\n"
            "\n"
            "Fix: Add to Makefile after line 529 (after lockfile validation):\n"
            '  @echo "▶ Dependency Tree Validation..."\n'
            '  @uv pip check && echo "✓ Dependencies valid" || '
            '(echo "✗ Dependency conflicts detected" && exit 1)\n'
            '  @echo ""\n'
        )

    def test_makefile_mypy_is_blocking(self, makefile_validate_target: str, pre_push_content: str):
        """
        Test that Makefile MyPy step blocks on errors (not warning-only).

        CRITICAL DRIFT: Pre-push hook treats MyPy as CRITICAL and blocks on errors
        (line 107: true), but Makefile treats it as warning-only with || echo.

        Impact:
        - Type errors pass 'make validate-pre-push' but block actual push
        - Developers experience "works locally, fails on push" confusion
        - Pre-push hook is stricter than documented Makefile target

        Pre-push hook Phase 2 (lines 105-107):
            run_validation "MyPy Type Checking" \\
                "uv run mypy src/mcp_server_langgraph --no-error-summary" \\
                true  # Blocks on type errors - matches CI behavior

        Makefile validate-pre-push Phase 2 (line 539):
            @$(UV_RUN) mypy src/mcp_server_langgraph --no-error-summary && \\
                echo "✓ MyPy passed" || echo "⚠ MyPy found issues (non-blocking)"
            # ^^ Warning-only! Should block like pre-push hook

        Fix: Change Makefile line 539 to block on MyPy errors.
        """
        # Verify pre-push hook blocks on MyPy errors (baseline)
        # The pre-push hook has: run_validation "MyPy..." "command..." true
        # where 'true' means it's blocking/critical
        assert (
            'run_validation "MyPy Type Checking"' in pre_push_content
        ), "Pre-push hook should have MyPy validation as baseline"
        # Check that the validation is marked as critical (has 'true' as third param)
        # This is indicated by "true  # Blocks on type errors" comment
        assert (
            "true  # Blocks on type errors" in pre_push_content
        ), "Pre-push hook should have MyPy as blocking (true) for baseline"

        # Verify Makefile blocks on MyPy (the actual test)
        # Look for MyPy command in Makefile
        makefile_mypy_pattern = r"mypy src/mcp_server_langgraph.*"
        makefile_mypy_match = re.search(makefile_mypy_pattern, makefile_validate_target)
        assert makefile_mypy_match, "Could not find MyPy command in Makefile target"

        makefile_mypy_line = makefile_mypy_match.group(0)

        # Should NOT have "|| echo" which makes it non-blocking
        assert "|| echo" not in makefile_mypy_line, (
            "Makefile MyPy MUST block on errors to match pre-push hook\n"
            "\n"
            "Current drift:\n"
            "  - Pre-push hook: MyPy is CRITICAL, blocks on errors (line 107: true)\n"
            "  - Makefile: MyPy is warning-only '|| echo \"⚠ ... (non-blocking)\"' (line 539)\n"
            "  - Type errors pass 'make validate-pre-push', fail on push\n"
            "\n"
            "Impact:\n"
            "  - Developers think code is ready but push gets blocked\n"
            "  - 'make validate-pre-push' provides false confidence\n"
            "  - Inconsistent validation between Makefile and hook\n"
            "\n"
            "Pre-push hook behavior (lines 105-107):\n"
            '  run_validation "MyPy Type Checking" \\\n'
            '      "uv run mypy src/mcp_server_langgraph --no-error-summary" \\\n'
            "      true  # BLOCKS on errors\n"
            "\n"
            "Current Makefile (line 539):\n"
            '  @$(UV_RUN) mypy ... || echo "⚠ MyPy found issues (non-blocking)"\n'
            "                     ^^ Non-blocking!\n"
            "\n"
            "Fix: Change Makefile line 539 to:\n"
            "  @$(UV_RUN) mypy src/mcp_server_langgraph --no-error-summary && \\\n"
            '      echo "✓ MyPy passed" || (echo "✗ MyPy found type errors" && exit 1)\n'
        )

    def test_makefile_xdist_enforcement_uses_n_auto(self, makefile_validate_target: str, pre_push_content: str):
        """
        Test that Makefile xdist enforcement test uses -n auto flag.

        DRIFT: Pre-push hook runs xdist enforcement tests with -n auto (line 151),
        but Makefile omits this flag (line 564), reducing parity with actual validation.

        Impact:
        - xdist enforcement tests don't run in parallel in Makefile
        - Different test conditions between 'make validate-pre-push' and push
        - Potential for missing xdist-specific issues in Makefile run

        Pre-push hook (line 151):
            "OTEL_SDK_DISABLED=true uv run pytest -n auto tests/meta/test_pytest_xdist_enforcement.py ..."

        Makefile (line 564):
            @OTEL_SDK_DISABLED=true $(UV_RUN) pytest tests/meta/test_pytest_xdist_enforcement.py ...
            # Missing: -n auto

        Fix: Add '-n auto' to Makefile line 564.
        """
        # Verify pre-push hook has -n auto (baseline)
        xdist_enforcement_hook_pattern = r"pytest.*test_pytest_xdist_enforcement\.py[^\n]*"
        hook_match = re.search(xdist_enforcement_hook_pattern, pre_push_content)
        assert hook_match, "Could not find xdist enforcement test in pre-push hook"

        hook_command = hook_match.group(0)
        assert "-n auto" in hook_command, "Pre-push hook should use '-n auto' for xdist enforcement tests as baseline"

        # Verify Makefile has -n auto (the actual test)
        xdist_enforcement_make_pattern = r"pytest.*test_pytest_xdist_enforcement\.py[^\n]*"
        make_match = re.search(xdist_enforcement_make_pattern, makefile_validate_target)
        assert make_match, "Could not find xdist enforcement test in Makefile"

        make_command = make_match.group(0)
        assert "-n auto" in make_command, (
            "Makefile xdist enforcement test MUST use '-n auto' to match pre-push hook\n"
            "\n"
            "Current drift:\n"
            "  - Pre-push hook: Uses '-n auto' for parallel execution (line 151)\n"
            "  - Makefile: Omits '-n auto' flag (line 564)\n"
            "  - Different test execution conditions\n"
            "\n"
            "Impact:\n"
            "  - Tests don't run in same mode as pre-push hook\n"
            "  - Could miss xdist-specific isolation issues\n"
            "  - Reduced parity between Makefile and hook validation\n"
            "\n"
            "Pre-push hook (line 151):\n"
            "  OTEL_SDK_DISABLED=true uv run pytest -n auto tests/meta/test_pytest_xdist_enforcement.py ...\n"
            "                                       ^^^^^^^^ Parallel execution\n"
            "\n"
            "Current Makefile (line 564):\n"
            "  @OTEL_SDK_DISABLED=true $(UV_RUN) pytest tests/meta/test_pytest_xdist_enforcement.py ...\n"
            "                                           ^ Missing '-n auto'\n"
            "\n"
            "Fix: Add '-n auto' to Makefile line 564:\n"
            "  @OTEL_SDK_DISABLED=true $(UV_RUN) pytest -n auto tests/meta/test_pytest_xdist_enforcement.py ...\n"
        )

    def test_makefile_phase_2_title_matches_behavior(self, makefile_validate_target: str):
        """
        Test that Makefile Phase 2 title reflects actual behavior.

        DOCUMENTATION DRIFT: Makefile Phase 2 title says "(Warning Only)" but
        after fixing MyPy to be blocking, the title should reflect critical behavior.

        Current Makefile (line 535):
            PHASE 2: Type Checking (Warning Only)

        After MyPy fix (blocking behavior):
            PHASE 2: Type Checking (Critical - matches CI)

        Fix: Update Makefile line 535 title after making MyPy blocking.
        """
        # After MyPy is made blocking, this test will validate the title update
        # For now, this documents the expected change
        phase_2_pattern = r"PHASE 2: Type Checking[^\n]*"
        match = re.search(phase_2_pattern, makefile_validate_target)
        assert match, "Could not find PHASE 2 title in Makefile"

        phase_2_title = match.group(0)

        # Check if MyPy is blocking in the Makefile
        mypy_pattern = r"mypy src/mcp_server_langgraph.*"
        mypy_match = re.search(mypy_pattern, makefile_validate_target)
        assert mypy_match, "Could not find MyPy command"

        mypy_line = mypy_match.group(0)
        mypy_is_blocking = "|| echo" not in mypy_line

        if mypy_is_blocking:
            # If MyPy is blocking, title should NOT say "Warning Only"
            assert "Warning Only" not in phase_2_title, (
                "Makefile Phase 2 title MUST reflect critical behavior when MyPy blocks\n"
                "\n"
                "Current state:\n"
                "  - MyPy is blocking (correct)\n"
                "  - Title still says 'Warning Only' (incorrect)\n"
                "\n"
                "Fix: Update Makefile line 535:\n"
                '  From: @echo "PHASE 2: Type Checking (Warning Only)"\n'
                '  To:   @echo "PHASE 2: Type Checking (Critical - matches CI)"\n'
            )
        else:
            # If MyPy is warning-only, title should say so (current state)
            # This branch will execute until MyPy is fixed to be blocking
            pass  # Title correctly reflects warning-only behavior

    def test_makefile_uses_correct_hook_stage_name(self, makefile_validate_target: str):
        """
        Test that Makefile validate-pre-push uses correct --hook-stage value.

        CRITICAL BUG: Makefile line 698 uses '--hook-stage push' which is INVALID.
        The correct value is '--hook-stage pre-push'.

        Impact:
        - pre-commit silently skips ALL hooks configured for pre-push stage
        - validate-pre-push target provides NO actual validation
        - Complete CI/CD parity failure - local validation doesn't match CI
        - Developers get false confidence that code is ready to push

        Pre-commit valid stage names:
        - commit
        - merge-commit
        - push-commit
        - prepare-commit-msg
        - commit-msg
        - post-commit
        - manual
        - pre-push  ← CORRECT
        - post-checkout
        - post-merge
        - post-rewrite

        Current Makefile (line 698):
            @pre-commit run --all-files --hook-stage push --show-diff-on-failure
                                                      ^^^^ INVALID - should be 'pre-push'

        Fix: Change line 698 to use '--hook-stage pre-push'

        Reference: OpenAI Codex Finding 1a - validate-pre-push stage name
        """
        # Look for pre-commit run command with --hook-stage
        hook_stage_pattern = r"pre-commit run --all-files --hook-stage (\S+)"
        match = re.search(hook_stage_pattern, makefile_validate_target)

        assert match, (
            "Could not find 'pre-commit run --all-files --hook-stage' in Makefile validate-pre-push target\n"
            "\n"
            "Expected pattern: pre-commit run --all-files --hook-stage <STAGE_NAME>\n"
        )

        stage_name = match.group(1)

        assert stage_name == "pre-push", (
            f"Makefile validate-pre-push MUST use '--hook-stage pre-push' (found: '--hook-stage {stage_name}')\n"
            "\n"
            "CRITICAL BUG:\n"
            f"  - Current: --hook-stage {stage_name}\n"
            "  - Expected: --hook-stage pre-push\n"
            f"  - Impact: pre-commit silently skips all pre-push hooks ('{stage_name}' is invalid)\n"
            "\n"
            "Valid pre-commit stage names:\n"
            "  - commit, merge-commit, push-commit\n"
            "  - prepare-commit-msg, commit-msg, post-commit\n"
            "  - manual, pre-push, post-checkout, post-merge, post-rewrite\n"
            "\n"
            f"Why '{stage_name}' is invalid:\n"
            "  - Not in pre-commit's documented stage list\n"
            "  - pre-commit will silently skip ALL hooks configured for 'pre-push' stage\n"
            "  - Validation target runs without actually validating anything\n"
            "\n"
            "Current Makefile (line 698):\n"
            f"  @pre-commit run --all-files --hook-stage {stage_name} --show-diff-on-failure\n"
            "                                             ^^^^ INVALID\n"
            "\n"
            "Fix Makefile line 698:\n"
            "  @pre-commit run --all-files --hook-stage pre-push --show-diff-on-failure\n"
            "                                             ^^^^^^^^ CORRECT\n"
            "\n"
            "Evidence of silent failure:\n"
            "  - .pre-commit-config.yaml has hooks with 'stages: [pre-push]'\n"
            f"  - These hooks will NOT run when stage is '{stage_name}'\n"
            "  - Developer runs 'make validate-pre-push', sees success\n"
            "  - Actual 'git push' runs pre-push hooks and fails\n"
            "  - Result: 'works locally, fails on push' confusion\n"
            "\n"
            "Reference: OpenAI Codex Finding 1a\n"
        )


@pytest.mark.xdist_group(name="testmakefileefficiency")
class TestMakefileEfficiency:
    """Test that Makefile targets are optimized for developer productivity."""

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
    def makefile_path(self, repo_root: Path) -> Path:
        """Get path to Makefile."""
        return repo_root / "Makefile"

    @pytest.fixture
    def makefile_content(self, makefile_path: Path) -> str:
        """Read Makefile content."""
        with open(makefile_path, "r") as f:
            return f.read()

    def test_test_targets_do_not_have_redundant_uv_sync(self, makefile_content: str):
        """
        Test that test-* targets don't have redundant uv sync calls.

        PERFORMANCE BUG: Four test targets (test-unit, test-property, test-contract,
        test-regression) run 'uv sync' before pytest, adding 30-60s overhead PER target.

        Impact:
        - Developers running multiple test types waste 2-4 minutes per iteration
        - 'make test-property && make test-contract' wastes 60-120s on redundant syncs
        - UV_RUN (uv run) already auto-syncs on demand, making explicit syncs unnecessary
        - Slower test loops discourage TDD workflow

        Current Makefile:
        - test-unit (line 234): @uv sync --extra dev --extra code-execution --quiet
        - test-property (line 369): @uv sync --extra dev --extra code-execution --quiet
        - test-contract (line 375): @uv sync --extra dev --extra code-execution --quiet
        - test-regression (line 382): @uv sync --extra dev --extra code-execution --quiet

        Why redundant:
        - Makefile line 12 defines: UV_RUN := uv run
        - 'uv run' automatically syncs if needed (on-demand)
        - Explicit sync before each target means syncing 4x even if deps unchanged

        Fix:
        - Remove explicit 'uv sync' from test targets
        - Rely on UV_RUN's automatic sync (faster, only syncs when needed)
        - Add prerequisite check: fail fast if .venv missing with clear error message

        Reference: OpenAI Codex Finding 1b - Redundant uv sync
        """
        # Extract test targets that should NOT have uv sync
        test_targets = ["test-unit", "test-property", "test-contract", "test-regression"]

        for target_name in test_targets:
            # Extract target content (from target: to next target or end)
            pattern = rf"^{re.escape(target_name)}:.*?(?=^\S|\Z)"
            match = re.search(pattern, makefile_content, re.MULTILINE | re.DOTALL)

            assert match, f"Could not find {target_name} target in Makefile"

            target_content = match.group(0)

            # Check for explicit uv sync calls
            has_uv_sync = re.search(r"@?\s*uv sync", target_content)

            assert not has_uv_sync, (
                f"Makefile target '{target_name}' MUST NOT have explicit 'uv sync' calls\n"
                "\n"
                "PERFORMANCE BUG:\n"
                f"  - Target '{target_name}' runs 'uv sync' before pytest\n"
                "  - Adds 30-60 seconds overhead PER invocation\n"
                "  - UV_RUN (uv run) already syncs on demand automatically\n"
                "  - Explicit sync is redundant and slows developer iteration\n"
                "\n"
                "Impact:\n"
                "  - Running 'make test-property && make test-contract' wastes 60-120s\n"
                "  - Developers running all 4 targets waste 2-4 minutes per iteration\n"
                "  - Slower test loops discourage TDD workflow\n"
                "  - Same dependencies re-synced multiple times unnecessarily\n"
                "\n"
                f"Found in {target_name}:\n"
                f"  {has_uv_sync.group(0)}\n"
                "\n"
                "Why this is redundant:\n"
                "  - Makefile line 12: UV_RUN := uv run\n"
                "  - 'uv run' automatically syncs if .venv missing or outdated\n"
                "  - Only syncs when NEEDED (checks lockfile timestamps)\n"
                "  - Explicit sync ALWAYS runs, even when not needed\n"
                "\n"
                "Fix:\n"
                f"  1. Remove 'uv sync' line from {target_name} target\n"
                "  2. Rely on UV_RUN's automatic sync (line 12: $(UV_RUN) pytest ...)\n"
                "  3. Add prerequisite check (optional):\n"
                "       @test -d .venv || (echo '✗ No .venv found. Run: make install-dev' && exit 1)\n"
                "\n"
                "Before (slow - 30-60s overhead):\n"
                f"  {target_name}:\n"
                "      @echo 'Running tests...'\n"
                "      @uv sync --extra dev --extra code-execution --quiet  ← REMOVE THIS\n"
                "      $(PYTEST) -n auto -m marker -v\n"
                "\n"
                "After (fast - only syncs when needed):\n"
                f"  {target_name}:\n"
                "      @echo 'Running tests...'\n"
                "      @test -d .venv || (echo '✗ Run: make install-dev' && exit 1)\n"
                "      $(UV_RUN) pytest -n auto -m marker -v  ← UV_RUN auto-syncs\n"
                "\n"
                "Time savings:\n"
                "  - Single target: 30-60s faster (skip unnecessary sync)\n"
                "  - Four targets: 2-4 min faster (skip 4x syncs)\n"
                "  - Daily savings: 10-20 min for active TDD workflow\n"
                "\n"
                "Reference: OpenAI Codex Finding 1b\n"
            )


@pytest.mark.xdist_group(name="testmakefilevalidationconsistency")
class TestMakefileValidationConsistency:
    """Test that Makefile validation handles failures consistently."""

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
    def makefile_path(self, repo_root: Path) -> Path:
        """Get path to Makefile."""
        return repo_root / "Makefile"

    @pytest.fixture
    def makefile_content(self, makefile_path: Path) -> str:
        """Read Makefile content."""
        with open(makefile_path, "r") as f:
            return f.read()

    def test_makefile_critical_checks_exit_on_failure(self, makefile_content: str):
        """
        Test that critical checks in Makefile exit on failure.

        Validates that critical validation steps (lockfile, unit tests, etc.)
        use '&& echo success || (echo failure && exit 1)' pattern to stop
        execution on failure.

        Non-critical checks can use '|| echo warning' pattern.
        """
        # Extract validate-pre-push target
        pattern = r"^validate-pre-push:.*?(?=^\S|\Z)"
        match = re.search(pattern, makefile_content, re.MULTILINE | re.DOTALL)
        assert match, "Could not find validate-pre-push target"
        target_content = match.group(0)

        # Critical checks that MUST exit on failure
        critical_checks = [
            ("lockfile validation", r"uv lock --check"),
            ("unit tests", r"pytest.*-m.*unit"),
            ("smoke tests", r"pytest.*tests/smoke"),
            ("API tests", r"pytest.*-m.*api"),
            ("MCP tests", r"pytest.*test_mcp_stdio_server"),
            ("property tests", r"pytest.*-m property"),
        ]

        for check_name, check_pattern in critical_checks:
            check_match = re.search(check_pattern, target_content)
            if check_match:
                # Get the full line containing this check
                check_line = check_match.group(0)
                # Should have exit 1 somewhere after the command
                context_start = check_match.start()
                context_end = min(context_start + 200, len(target_content))
                context = target_content[context_start:context_end]

                assert "exit 1" in context, (
                    f"Critical check '{check_name}' MUST exit on failure\n"
                    f"\n"
                    f"Pattern: {check_pattern}\n"
                    f"Found command: {check_line}\n"
                    f"\n"
                    f"Critical checks must use:\n"
                    f'  @command && echo "✓ Success" || (echo "✗ Failed" && exit 1)\n'
                    f"\n"
                    f"NOT:\n"
                    f'  @command || echo "⚠ Warning (non-blocking)"\n'
                )
