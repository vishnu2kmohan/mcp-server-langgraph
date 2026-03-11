"""Unit tests for Makefile test parallelism behavior.

These tests validate that PYTEST_PARALLEL_FLAG is computed correctly
under various environment configurations.

TDD Note: These tests should FAIL initially (RED phase) until the Makefile
is updated with the parallelism logic in Phase 0.3 (GREEN phase).
"""

import os
import subprocess

import pytest

pytestmark = pytest.mark.unit


def _xdist_available() -> bool:
    """Check if pytest-xdist is installed."""
    try:
        import xdist  # noqa: F401

        return True
    except ImportError:
        return False


@pytest.mark.unit
class TestMakefileParallelism:
    """Test Makefile parallel flag computation."""

    @pytest.fixture(autouse=True)
    def setup_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Clear parallelism-related env vars before each test."""
        for var in ("PYTEST_SEQUENTIAL", "PYTEST_WORKERS"):
            monkeypatch.delenv(var, raising=False)

    def _get_parallel_flag(self, env_overrides: dict[str, str] | None = None) -> tuple[str, int]:
        """Extract PYTEST_PARALLEL_FLAG using dedicated print target.

        Uses `make print-pytest-parallel-flag` for cross-platform stability
        (works on both GNU make and BSD make).

        Returns:
            Tuple of (flag_value, return_code)
        """
        env = os.environ.copy()
        if env_overrides:
            env.update(env_overrides)
        result = subprocess.run(
            ["make", "print-pytest-parallel-flag"],
            capture_output=True,
            text=True,
            env=env,
            cwd=os.getcwd(),
            timeout=30,  # Always include timeout per review finding
        )
        # Output is just the flag value (e.g., "-n auto" or "")
        flag = result.stdout.strip()
        return flag, result.returncode

    def test_print_target_exists(self) -> None:
        """Verify the print-pytest-parallel-flag target exists."""
        flag, returncode = self._get_parallel_flag()
        assert returncode == 0, "make print-pytest-parallel-flag failed: target may not exist"

    def test_default_uses_n_auto_when_xdist_available(self) -> None:
        """Default behavior uses -n auto if xdist is installed."""
        flag, returncode = self._get_parallel_flag()
        assert returncode == 0, "make command failed"
        if _xdist_available():
            assert flag == "-n auto", f"xdist available but got '{flag}' instead of '-n auto'"
        else:
            assert flag == "", f"xdist unavailable but flag is '{flag}' instead of empty"

    def test_sequential_mode_disables_parallel(self) -> None:
        """PYTEST_SEQUENTIAL=1 results in no -n flag."""
        flag, returncode = self._get_parallel_flag({"PYTEST_SEQUENTIAL": "1"})
        assert returncode == 0, "make command failed"
        assert flag == "", f"PYTEST_SEQUENTIAL=1 should disable parallelism, got '{flag}'"

    def test_workers_override_respected(self) -> None:
        """PYTEST_WORKERS overrides auto when xdist available."""
        flag, returncode = self._get_parallel_flag({"PYTEST_WORKERS": "4"})
        assert returncode == 0, "make command failed"
        if _xdist_available():
            assert flag == "-n 4", f"xdist available but PYTEST_WORKERS=4 gave '{flag}'"
        else:
            assert flag == "", f"xdist unavailable, PYTEST_WORKERS should be ignored, got '{flag}'"

    def test_sequential_takes_precedence_over_workers(self) -> None:
        """PYTEST_SEQUENTIAL=1 overrides PYTEST_WORKERS."""
        flag, returncode = self._get_parallel_flag(
            {
                "PYTEST_SEQUENTIAL": "1",
                "PYTEST_WORKERS": "4",
            }
        )
        assert returncode == 0, "make command failed"
        assert flag == "", f"PYTEST_SEQUENTIAL should take precedence, got '{flag}'"

    def test_invalid_workers_falls_back_to_auto(self) -> None:
        """Invalid PYTEST_WORKERS value falls back to -n auto."""
        flag, returncode = self._get_parallel_flag({"PYTEST_WORKERS": "invalid"})
        assert returncode == 0, "make command failed"
        if _xdist_available():
            assert flag == "-n auto", f"invalid PYTEST_WORKERS should fall back to auto, got '{flag}'"

    def test_zero_workers_falls_back_to_auto(self) -> None:
        """PYTEST_WORKERS=0 is invalid and falls back to -n auto."""
        flag, returncode = self._get_parallel_flag({"PYTEST_WORKERS": "0"})
        assert returncode == 0, "make command failed"
        if _xdist_available():
            assert flag == "-n auto", f"PYTEST_WORKERS=0 should fall back to auto, got '{flag}'"

    def test_negative_workers_falls_back_to_auto(self) -> None:
        """PYTEST_WORKERS=-1 is invalid and falls back to -n auto."""
        flag, returncode = self._get_parallel_flag({"PYTEST_WORKERS": "-1"})
        assert returncode == 0, "make command failed"
        if _xdist_available():
            assert flag == "-n auto", f"PYTEST_WORKERS=-1 should fall back to auto, got '{flag}'"

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()
