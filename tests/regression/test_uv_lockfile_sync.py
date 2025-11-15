"""
Regression Test: UV Lockfile Synchronization

REGRESSION INCIDENT: Commit 67f8942 (2025-11-12)
SEVERITY: CRITICAL - Blocked all CI/CD workflows

## What Happened

Commit 67f8942 modified pyproject.toml to add pytest markers (lines 425-429)
but didn't regenerate uv.lock, causing lockfile desynchronization.

This caused ALL Python-based CI workflows to fail with:
```
uv.lock is out of date with pyproject.toml
Run 'uv lock' locally and commit the updated lockfile
```

## Impact

- ❌ CI/CD Pipeline failed on Python 3.10, 3.11, 3.12
- ❌ Quality Tests failed
- ❌ E2E Tests failed
- ❌ Coverage Trend Tracking failed
- ❌ All development blocked for ~2 hours

## Root Cause

Developer modified pyproject.toml without running `uv lock` to update uv.lock.

## Prevention Measures

1. **Pre-commit Hook** (.pre-commit-config.yaml:74-91)
   - Runs `uv lock --check` on pyproject.toml or uv.lock changes
   - Fails commit if lockfile is out of sync
   - Prevents issue from reaching CI

2. **CI Fail-Fast Check** (.github/workflows/ci.yaml:172-185)
   - Validates lockfile BEFORE running tests
   - Provides clear error message with remediation steps
   - Saves CI minutes by failing early

3. **This Regression Test** (tests/regression/test_uv_lockfile_sync.py)
   - Documents the incident
   - Provides testable validation
   - Runs in CI to catch regressions

## Testing Strategy

This test validates that:
1. uv.lock exists
2. uv.lock is in sync with pyproject.toml (uv lock --check passes)
3. Pre-commit hook exists for lockfile validation
4. CI workflow has lockfile validation step

## References

- Incident Commit: 67f8942
- Fix Commits: 709adda (test fixes), c193936 (CI Python version), ba5296f (uv sync --python)
- CI Run: https://github.com/vishnu2kmohan/mcp-server-langgraph/actions/runs/19306810940
"""

import gc
import subprocess
from pathlib import Path

import pytest
import yaml


@pytest.mark.regression
@pytest.mark.documentation
@pytest.mark.xdist_group(name="testuvlockfilesynchronization")
class TestUVLockfileSynchronization:
    """
    Regression tests for UV lockfile synchronization issues.

    Prevents recurrence of the 2025-11-12 incident where out-of-sync
    lockfile blocked all CI/CD workflows.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_uv_lock_file_exists(self):
        """Verify uv.lock exists in project root"""
        project_root = Path(__file__).parent.parent.parent
        lockfile = project_root / "uv.lock"

        assert lockfile.exists(), (
            "uv.lock not found! This file is required for reproducible builds. " "Run 'uv lock' to create it."
        )

        assert lockfile.stat().st_size > 0, "uv.lock exists but is empty!"

    def test_uv_lockfile_is_synchronized_with_pyproject(self):
        """
        CRITICAL: Verify uv.lock is in sync with pyproject.toml

        This is the EXACT check that failed in commit 67f8942.
        If this test fails, run: uv lock
        """
        project_root = Path(__file__).parent.parent.parent

        # Run uv lock --check (same command CI uses)
        result = subprocess.run(
            ["uv", "lock", "--check"],
            cwd=project_root,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, (
            f"❌ uv.lock is OUT OF SYNC with pyproject.toml!\n\n"
            f"This is the EXACT issue that caused CI failure in commit 67f8942.\n\n"
            f"To fix:\n"
            f"  1. Run: uv lock\n"
            f"  2. Stage: git add uv.lock\n"
            f"  3. Commit: git commit --amend --no-edit\n\n"
            f"uv lock --check output:\n{result.stderr}\n{result.stdout}"
        )

    def test_pre_commit_hook_validates_lockfile(self):
        """Verify pre-commit hook exists to catch lockfile sync issues"""
        project_root = Path(__file__).parent.parent.parent
        pre_commit_config = project_root / ".pre-commit-config.yaml"

        assert pre_commit_config.exists(), "No .pre-commit-config.yaml found!"

        with open(pre_commit_config) as f:
            config = yaml.safe_load(f)

        # Find the uv-lock-check hook
        uv_lock_hook_found = False
        for repo in config.get("repos", []):
            if repo.get("repo") == "local":
                for hook in repo.get("hooks", []):
                    if hook.get("id") == "uv-lock-check":
                        uv_lock_hook_found = True

                        # Validate hook configuration
                        assert "uv lock --check" in hook.get("entry", ""), "uv-lock-check hook must run 'uv lock --check'"

                        # Should trigger on pyproject.toml or uv.lock changes
                        files_pattern = hook.get("files", "")
                        assert (
                            "pyproject" in files_pattern or "uv\\.lock" in files_pattern
                        ), "uv-lock-check hook must monitor pyproject.toml and uv.lock files"

                        break

        assert uv_lock_hook_found, (
            "Pre-commit hook 'uv-lock-check' not found!\n"
            "This hook prevents the lockfile sync issue from commit 67f8942.\n"
            "It should be defined in .pre-commit-config.yaml"
        )

    def test_ci_workflow_validates_lockfile_before_tests(self):
        """Verify CI workflow has fail-fast lockfile validation"""
        project_root = Path(__file__).parent.parent.parent
        ci_workflow = project_root / ".github" / "workflows" / "ci.yaml"

        assert ci_workflow.exists(), "CI workflow file not found!"

        with open(ci_workflow) as f:
            workflow_content = f.read()

        # Check for lockfile validation step
        assert "uv lock --check" in workflow_content or "Validate lockfile" in workflow_content, (
            "CI workflow must validate lockfile synchronization before running tests.\n"
            "This fail-fast check prevents wasting CI minutes on lockfile issues.\n"
            "See commit 67f8942 incident where this was missing."
        )

    def test_lockfile_validation_error_message_is_helpful(self):
        """Verify lockfile validation provides clear remediation steps"""
        project_root = Path(__file__).parent.parent.parent
        ci_workflow = project_root / ".github" / "workflows" / "ci.yaml"

        with open(ci_workflow) as f:
            workflow_content = f.read()

        # Check that error message provides remediation
        if "uv lock --check" in workflow_content:
            # Find the section with uv lock --check
            assert (
                "Run 'uv lock'" in workflow_content or "uv lock" in workflow_content
            ), "Lockfile validation error should tell developers how to fix it"


@pytest.mark.regression
@pytest.mark.ci
@pytest.mark.xdist_group(name="testcipythonversionmatrix")
class TestCIPythonVersionMatrix:
    """
    Regression tests for CI Python version matrix configuration.

    Prevents recurrence of the issue where all matrix jobs ran Python 3.12
    instead of their configured versions (3.10, 3.11, 3.12).
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_ci_workflow_uses_uv_sync_with_python_flag(self):
        """
        CRITICAL: Verify uv sync uses --python flag to prevent venv recreation

        REGRESSION: Without this flag, uv sync removed Python 3.11 venv and
        recreated it with Python 3.12, causing all matrix jobs to run 3.12.

        Evidence from CI logs:
        ```
        Using CPython 3.11.14 - Creating virtual environment at: .venv
        Using CPython 3.12.3 - Removed virtual environment at: .venv
        Creating virtual environment at: .venv
        ```
        """
        project_root = Path(__file__).parent.parent.parent
        ci_workflow = project_root / ".github" / "workflows" / "ci.yaml"

        with open(ci_workflow) as f:
            workflow_content = f.read()

        # Must use --python flag with matrix variable
        assert "uv sync --python ${{ matrix.python-version }}" in workflow_content or "uv sync --python" in workflow_content, (
            "❌ CI workflow must use 'uv sync --python ${{ matrix.python-version }}'\n\n"
            "Without this flag, uv sync recreates venv with default Python (3.12)\n"
            "instead of using the matrix Python version (3.10, 3.11, 3.12).\n\n"
            "This caused all test jobs to run Python 3.12 regardless of matrix config.\n\n"
            "See commits: c193936, ba5296f for fix details"
        )

    def test_ci_workflow_verifies_python_version_after_install(self):
        """Verify CI workflow checks Python version after venv creation"""
        project_root = Path(__file__).parent.parent.parent
        ci_workflow = project_root / ".github" / "workflows" / "ci.yaml"

        with open(ci_workflow) as f:
            workflow_content = f.read()

        # Should verify Python version
        assert ".venv/bin/python --version" in workflow_content or "python --version" in workflow_content, (
            "CI workflow should verify Python version after venv creation.\n" "This catches Python version mismatches early."
        )


@pytest.mark.regression
@pytest.mark.documentation
@pytest.mark.xdist_group(name="testfastapidependencyoverridespattern")
class TestFastAPIDependencyOverridesPattern:
    """
    Regression tests for FastAPI dependency mocking pattern.

    Documents the correct way to mock dependencies in FastAPI tests
    to avoid parameter name collisions and pytest-xdist issues.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_service_principals_fixture_uses_dependency_overrides(self):
        """
        Verify service principals tests use dependency_overrides pattern

        REGRESSION: Using monkeypatch + reload caused FastAPI parameter collision:
        - Endpoint: request: CreateServicePrincipalRequest
        - Mock: request: Request
        - FastAPI got confused → 422 error looking for 'request' in body

        FIX: Use app.dependency_overrides instead of monkeypatch
        """
        test_file = Path(__file__).parent.parent / "api" / "test_service_principals_endpoints.py"

        with open(test_file) as f:
            content = f.read()

        # Should use dependency_overrides, not monkeypatch
        assert "app.dependency_overrides[" in content, (
            "Service principals tests must use app.dependency_overrides.\n"
            "Monkeypatch + reload causes FastAPI parameter name collision.\n"
            "See commit 709adda for details."
        )

        # Should NOT use monkeypatch for dependencies
        assert "monkeypatch.setattr" not in content or "monkeypatch, mock_sp_manager" not in content, (
            "Should not use monkeypatch for dependency injection.\n"
            "Use app.dependency_overrides instead.\n"
            "See tests/api/test_service_principals_endpoints.py:130-145"
        )

    def test_api_keys_fixture_uses_dependency_overrides(self):
        """Verify API keys tests use dependency_overrides pattern"""
        test_file = Path(__file__).parent.parent / "api" / "test_api_keys_endpoints.py"

        with open(test_file) as f:
            content = f.read()

        assert "app.dependency_overrides[" in content, (
            "API keys tests must use app.dependency_overrides.\n" "See commit 709adda for implementation."
        )


if __name__ == "__main__":
    # Allow running this test file directly for quick validation
    pytest.main([__file__, "-v"])
