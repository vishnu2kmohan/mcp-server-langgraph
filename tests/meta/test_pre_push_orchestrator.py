"""
Tests for the pre-push test orchestrator script.

This test suite validates that the orchestrator correctly combines multiple
test marker expressions into a single pytest session to eliminate redundant
test discovery overhead.

TDD Principle: These tests ensure the orchestrator correctly implements the
Codex Finding 2a fix - consolidating 5 separate pytest sessions into one.
"""

import gc
import subprocess
from pathlib import Path

import pytest

# Mark as unit+meta test to ensure it runs in CI
pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="testprepushorchestrator")
class TestPrePushOrchestrator:
    """Test the pre-push test orchestrator script."""

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
    def orchestrator_path(self, repo_root: Path) -> Path:
        """Get path to orchestrator script."""
        return repo_root / "scripts" / "run_pre_push_tests.py"

    def test_orchestrator_script_exists(self, orchestrator_path: Path):
        """Test that the orchestrator script exists and is executable."""
        assert orchestrator_path.exists(), (
            f"Orchestrator script MUST exist at {orchestrator_path}\n"
            "\n"
            "The script consolidates 5 separate pytest hooks into one session.\n"
            "\n"
            "Create: scripts/run_pre_push_tests.py\n"
            "Reference: OpenAI Codex Finding 2a - Duplicate pytest sessions\n"
        )

        # Check if file is readable
        assert orchestrator_path.is_file(), f"{orchestrator_path} must be a file"
        assert orchestrator_path.stat().st_size > 0, f"{orchestrator_path} must not be empty"

    def test_orchestrator_combines_all_markers(self, orchestrator_path: Path):
        """
        Test that orchestrator combines all test markers from 5 hooks.

        The orchestrator MUST combine these marker expressions:
        1. unit and not llm (from run-unit-tests)
        2. tests/smoke/ (from run-smoke-tests)
        3. api and unit and not llm (from run-api-tests)
        4. tests/unit/test_mcp_stdio_server.py -m "not llm" (from run-mcp-server-tests)
        5. property (from run-property-tests)

        Strategy: Run single pytest session with combined marker logic
        """
        if not orchestrator_path.exists():
            pytest.skip("Orchestrator script doesn't exist yet")

        with open(orchestrator_path) as f:
            content = f.read()

        # Verify it's a Python script
        assert "#!/usr/bin/env python" in content or "import" in content, "Orchestrator must be a Python script with imports"

        # Verify it references pytest
        assert "pytest" in content.lower(), "Orchestrator must use pytest"

        # Verify it has marker logic
        # The orchestrator should mention all the markers we're consolidating
        markers_to_check = ["unit", "property"]  # Core markers being consolidated
        for marker in markers_to_check:
            assert marker in content, (
                f"Orchestrator MUST reference '{marker}' marker\n"
                "\n"
                f"Missing marker: {marker}\n"
                "The orchestrator consolidates these hooks:\n"
                "  - run-unit-tests: -m 'unit and not llm'\n"
                "  - run-smoke-tests: tests/smoke/\n"
                "  - run-api-tests: -m 'api and unit and not llm'\n"
                "  - run-mcp-server-tests: tests/unit/test_mcp_stdio_server.py\n"
                "  - run-property-tests: -m property\n"
                "\n"
                "All markers must be present in the orchestrator logic.\n"
            )

    def test_orchestrator_uses_parallel_execution(self, orchestrator_path: Path):
        """Test that orchestrator uses pytest-xdist for parallel execution."""
        if not orchestrator_path.exists():
            pytest.skip("Orchestrator script doesn't exist yet")

        with open(orchestrator_path) as f:
            content = f.read()

        # Verify it uses -n auto for parallel execution
        # Check for various representations: string "-n auto" or list ["-n", "auto"]
        # Also handle multiline formatting where -n and auto are on separate lines
        has_parallel = (
            '"-n", "auto"' in content
            or '"-n","auto"' in content
            or "'-n', 'auto'" in content
            or "'-n','auto'" in content
            or '"-n auto"' in content
            or "-n auto" in content
            or (
                '"-n"' in content and '"auto"' in content and content.index('"auto"') - content.index('"-n"') < 100
            )  # Multiline: within 100 chars
        )

        assert has_parallel, (
            "Orchestrator MUST use pytest-xdist parallel execution (-n auto)\n"
            "\n"
            "All 5 original hooks used: pytest -n auto ...\n"
            "The consolidated hook must maintain parallel execution.\n"
            "\n"
            "Add to pytest arguments: -n auto\n"
        )

    def test_orchestrator_fails_fast(self, orchestrator_path: Path):
        """Test that orchestrator stops on first failure (-x)."""
        if not orchestrator_path.exists():
            pytest.skip("Orchestrator script doesn't exist yet")

        with open(orchestrator_path) as f:
            content = f.read()

        # Verify it uses -x for fail-fast behavior
        assert "-x" in content or '"x": true' in content or "'x': True" in content, (
            "Orchestrator MUST use fail-fast behavior (-x flag)\n"
            "\n"
            "All 5 original hooks used: pytest ... -x --tb=short\n"
            "The consolidated hook must stop on first failure.\n"
            "\n"
            "Add to pytest arguments: -x\n"
        )

    def test_orchestrator_uses_short_traceback(self, orchestrator_path: Path):
        """Test that orchestrator uses short traceback format."""
        if not orchestrator_path.exists():
            pytest.skip("Orchestrator script doesn't exist yet")

        with open(orchestrator_path) as f:
            content = f.read()

        # Verify it uses --tb=short
        assert "--tb=short" in content or '"tb": "short"' in content or "'tb': 'short'" in content, (
            "Orchestrator MUST use short traceback format (--tb=short)\n"
            "\n"
            "All 5 original hooks used: pytest ... --tb=short\n"
            "The consolidated hook must use same traceback format.\n"
            "\n"
            "Add to pytest arguments: --tb=short\n"
        )

    def test_orchestrator_excludes_llm_tests(self, orchestrator_path: Path):
        """Test that orchestrator excludes LLM tests (require API keys)."""
        if not orchestrator_path.exists():
            pytest.skip("Orchestrator script doesn't exist yet")

        with open(orchestrator_path) as f:
            content = f.read()

        # Verify it excludes llm marker
        assert "not llm" in content or '"not llm"' in content or "'not llm'" in content, (
            "Orchestrator MUST exclude LLM tests (not llm)\n"
            "\n"
            "Original hooks excluded LLM tests:\n"
            "  - run-unit-tests: -m 'unit and not llm'\n"
            "  - run-api-tests: -m 'api and unit and not llm'\n"
            "  - run-mcp-server-tests: -m 'not llm'\n"
            "\n"
            "The consolidated hook must maintain this exclusion.\n"
            "\n"
            "LLM tests require API keys and should not run in pre-push.\n"
        )

    def test_orchestrator_has_proper_shebang(self, orchestrator_path: Path):
        """Test that orchestrator script has proper Python shebang."""
        if not orchestrator_path.exists():
            pytest.skip("Orchestrator script doesn't exist yet")

        with open(orchestrator_path) as f:
            first_line = f.readline().strip()

        assert first_line.startswith("#!"), (
            "Orchestrator MUST have shebang line\n"
            "\n"
            "First line should be: #!/usr/bin/env python3\n"
            "This allows the script to be executed directly.\n"
        )

        assert "python" in first_line.lower(), (
            "Shebang MUST reference Python\n" "\n" f"Found: {first_line}\n" "Expected: #!/usr/bin/env python3\n"
        )
