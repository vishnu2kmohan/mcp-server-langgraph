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
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(result.stdout.strip())

    @pytest.fixture
    def makefile_path(self, repo_root: Path) -> Path:
        """Get path to Makefile."""
        return repo_root / "Makefile"

    @pytest.fixture
    def pre_push_hook_path(self, repo_root: Path) -> Path:
        """Get path to pre-push hook."""
        return repo_root / ".git" / "hooks" / "pre-push"

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
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
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
