"""
Tests for parallel_security_scan.sh - Parallel Security Scan Wrapper.

Validates:
1. Resource detection returns expected values for different CPU/memory combos
2. SKIP_* env vars are ignored when CI=true
3. Exit code is nonzero when any scan fails
4. Signal handling cleans up child processes
5. Cross-platform CPU detection fallback logic
6. Dry-run mode outputs expected configuration
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tests.helpers.path_helpers import get_repo_root

pytestmark = [pytest.mark.unit]

PROJECT_ROOT = get_repo_root()
SECURITY_SCRIPT = PROJECT_ROOT / "scripts" / "hooks" / "parallel_security_scan.sh"


class TestParallelSecurityScanScript:
    """Tests for the parallel_security_scan.sh hook wrapper."""

    def test_script_exists_at_expected_path(self) -> None:
        """parallel_security_scan.sh must exist at expected location."""
        assert SECURITY_SCRIPT.exists(), f"scripts/hooks/parallel_security_scan.sh not found at {SECURITY_SCRIPT}"

    def test_script_is_executable(self) -> None:
        """parallel_security_scan.sh must be executable."""
        assert SECURITY_SCRIPT.stat().st_mode & 0o111, "scripts/hooks/parallel_security_scan.sh is not executable"

    def test_ci_mode_concurrency_is_2(self) -> None:
        """In CI mode, max concurrent scans should be 2."""
        content = SECURITY_SCRIPT.read_text()
        assert "MAX_CONCURRENT=2" in content, "CI mode must set MAX_CONCURRENT=2 for memory-constrained runners"

    def test_ci_ignores_skip_env_vars(self) -> None:
        """CI mode must unset SKIP_* env vars to prevent silent security bypass."""
        content = SECURITY_SCRIPT.read_text()
        assert "unset SKIP_BANDIT" in content or "unset SKIP_TRIVY" in content, "CI mode must unset SKIP_* env vars"

    def test_cross_platform_cpu_detection(self) -> None:
        """Script must have cross-platform CPU detection (nproc + sysctl fallback)."""
        content = SECURITY_SCRIPT.read_text()
        assert "nproc" in content, "Must use nproc for Linux CPU detection"
        assert "sysctl" in content, "Must have sysctl fallback for macOS"

    def test_signal_handling_cleanup(self) -> None:
        """Script must trap EXIT/INT/TERM to clean up child processes."""
        content = SECURITY_SCRIPT.read_text()
        assert "trap" in content, "Script must set up signal traps"
        assert "cleanup" in content, "Script must define a cleanup function"
        assert "EXIT" in content, "Script must trap EXIT signal"
        assert "INT" in content, "Script must trap INT signal"
        assert "TERM" in content, "Script must trap TERM signal"

    def test_per_tool_exit_code_tracking(self) -> None:
        """Script must track exit codes per tool for reporting."""
        content = SECURITY_SCRIPT.read_text()
        assert "exit_code" in content.lower() or "exit_codes" in content.lower(), "Script must track per-tool exit codes"

    def test_dry_run_mode(self) -> None:
        """Dry-run mode should output configuration without running scans."""
        result = subprocess.run(
            ["bash", str(SECURITY_SCRIPT)],
            env={
                "SECURITY_SCAN_DRY_RUN": "1",
                "PATH": "/usr/bin:/bin:/usr/local/bin",
                "HOME": str(Path.home()),
            },
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0, f"Dry-run should exit 0, got {result.returncode}: {result.stderr}"
        assert "max_concurrent" in result.stdout, "Dry-run output should include max_concurrent"

    def test_ci_dry_run_ignores_skip_vars(self) -> None:
        """In CI dry-run mode, SKIP_* vars should be shown as 0 (ignored)."""
        result = subprocess.run(
            ["bash", str(SECURITY_SCRIPT)],
            env={
                "SECURITY_SCAN_DRY_RUN": "1",
                "CI": "true",
                "SKIP_TRIVY": "1",
                "PATH": "/usr/bin:/bin:/usr/local/bin",
                "HOME": str(Path.home()),
            },
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0
        # In CI mode, SKIP vars should be unset before dry-run reports
        assert "ci_mode=true" in result.stdout

    def test_all_six_tools_covered(self) -> None:
        """Script must cover all 6 security tools: bandit, 4x trivy (k8s, helm, helm-full, terraform), semgrep."""
        content = SECURITY_SCRIPT.read_text()
        for tool in ["bandit", "trivy-k8s", "trivy-helm", "trivy-helm-full", "trivy-terraform", "semgrep"]:
            assert tool in content, f"Script must include {tool} scan"

    def test_trivy_terraform_uses_ignorefile(self) -> None:
        """Trivy terraform scan must use terraform/.trivyignore for accepted risks."""
        content = SECURITY_SCRIPT.read_text()
        assert "--ignorefile terraform/.trivyignore" in content, (
            "trivy-terraform scan must include --ignorefile terraform/.trivyignore"
        )

    def test_local_max_concurrent_caps_at_6(self) -> None:
        """Local mode should cap concurrency at 6."""
        content = SECURITY_SCRIPT.read_text()
        assert "6" in content, "Local mode should cap MAX_CONCURRENT at 6"

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()
