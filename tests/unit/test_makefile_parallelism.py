"""Unit tests for Makefile test parallelism behavior.

These tests validate that PYTEST_PARALLEL_FLAG is computed correctly
under various environment configurations via the `print-pytest-parallel-flag`
Make target.

Phase 0.2 of the context-efficiency transfer plan.
"""

import os
import shutil
import subprocess

import pytest

pytestmark = pytest.mark.unit

_MAKE_AVAILABLE = shutil.which("make") is not None


def _xdist_available() -> bool:
    """Check if pytest-xdist is installed."""
    try:
        import xdist  # noqa: F401

        return True
    except ImportError:
        return False


@pytest.mark.unit
@pytest.mark.skipif(not _MAKE_AVAILABLE, reason="make is not available in this environment")
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
        # Ensure clean state
        env.pop("PYTEST_SEQUENTIAL", None)
        env.pop("PYTEST_WORKERS", None)
        if env_overrides:
            env.update(env_overrides)
        result = subprocess.run(
            ["make", "print-pytest-parallel-flag"],
            capture_output=True,
            text=True,
            env=env,
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            timeout=30,
        )
        flag = result.stdout.strip()
        return flag, result.returncode

    def test_default_uses_n_auto_when_xdist_available(self) -> None:
        """Default behavior uses -n auto if xdist is installed."""
        flag, returncode = self._get_parallel_flag()
        assert returncode == 0, f"make command failed: {flag}"
        if _xdist_available():
            assert flag == "-n auto", "xdist available but -n auto not set"
        else:
            assert flag == "", "xdist unavailable but flag is not empty"

    def test_sequential_mode_disables_parallel(self) -> None:
        """PYTEST_SEQUENTIAL=1 results in no -n flag."""
        flag, returncode = self._get_parallel_flag({"PYTEST_SEQUENTIAL": "1"})
        assert returncode == 0, f"make command failed: {flag}"
        assert flag == "", "PYTEST_SEQUENTIAL=1 should disable parallelism"

    def test_workers_override_respected(self) -> None:
        """PYTEST_WORKERS overrides auto when xdist available."""
        flag, returncode = self._get_parallel_flag({"PYTEST_WORKERS": "4"})
        assert returncode == 0, f"make command failed: {flag}"
        if _xdist_available():
            assert flag == "-n 4", "xdist available but PYTEST_WORKERS=4 not respected"
        else:
            assert flag == "", "xdist unavailable, PYTEST_WORKERS should be ignored"

    def test_sequential_takes_precedence_over_workers(self) -> None:
        """PYTEST_SEQUENTIAL=1 overrides PYTEST_WORKERS."""
        flag, returncode = self._get_parallel_flag(
            {
                "PYTEST_SEQUENTIAL": "1",
                "PYTEST_WORKERS": "4",
            }
        )
        assert returncode == 0, f"make command failed: {flag}"
        assert flag == "", "PYTEST_SEQUENTIAL should take precedence over PYTEST_WORKERS"

    def test_invalid_workers_falls_back_to_auto(self) -> None:
        """Invalid PYTEST_WORKERS value falls back to -n auto."""
        flag, returncode = self._get_parallel_flag({"PYTEST_WORKERS": "invalid"})
        assert returncode == 0, f"make command failed: {flag}"
        if _xdist_available():
            assert flag == "-n auto", "invalid PYTEST_WORKERS should fall back to auto"

    def test_zero_workers_falls_back_to_auto(self) -> None:
        """PYTEST_WORKERS=0 is invalid and falls back to -n auto."""
        flag, returncode = self._get_parallel_flag({"PYTEST_WORKERS": "0"})
        assert returncode == 0, f"make command failed: {flag}"
        if _xdist_available():
            assert flag == "-n auto", "PYTEST_WORKERS=0 should fall back to auto"
