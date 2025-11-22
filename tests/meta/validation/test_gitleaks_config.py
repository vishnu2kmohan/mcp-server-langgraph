#!/usr/bin/env python3
"""
Tests for gitleaks configuration to prevent false positives.

Following TDD principles:
1. RED: These tests verify gitleaks config excludes documentation examples
2. GREEN: Create .gitleaks.toml with proper allowlists
3. REFACTOR: Update workflows to use the config
"""

import gc
import subprocess
from pathlib import Path

import pytest

# Mark as unit test to ensure it runs in CI
pytestmark = pytest.mark.unit


def get_repo_root() -> Path:
    """Find repository root with marker validation."""
    current = Path(__file__).parent
    markers = [".git", "pyproject.toml"]
    while current != current.parent:
        if any((current / m).exists() for m in markers):
            return current
        current = current.parent
    raise RuntimeError("Cannot find repo root")


@pytest.mark.xdist_group(name="testgitleaksconfig")
class TestGitleaksConfig:
    """Test gitleaks configuration and allowlist."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_gitleaks_config_exists(self):
        """
        Test that .gitleaks.toml configuration file exists.

        This test will initially FAIL because the config doesn't exist yet.
        After fix, gitleaks should use this config to avoid false positives.
        """
        # Resolve repo root from tests/meta/validation/test_gitleaks_config.py
        repo_root = get_repo_root()
        config_file = repo_root / ".gitleaks.toml"
        assert config_file.exists(), ".gitleaks.toml configuration should exist"

    def test_gitleaks_config_valid_toml(self):
        """Test that .gitleaks.toml is valid TOML syntax."""
        repo_root = get_repo_root()
        config_file = repo_root / ".gitleaks.toml"

        if not config_file.exists():
            pytest.skip(".gitleaks.toml not yet created")

        try:
            import tomllib
        except ImportError:
            import tomli as tomllib

        with open(config_file, "rb") as f:
            config = tomllib.load(f)

        assert config is not None, "Gitleaks config should parse as valid TOML"
        assert isinstance(config, dict), "Gitleaks config should be a dictionary"

    def test_gitleaks_ignores_documentation_examples(self):
        """
        Test that gitleaks doesn't flag documentation examples as secrets.

        The .openai/codex-instructions.md file contains example code showing
        what NOT to do (hardcoded secrets). These should be allowlisted.
        """
        codex_file = get_repo_root() / ".openai" / "codex-instructions.md"

        if not codex_file.exists():
            pytest.skip("Codex instructions file not found")

        # Run gitleaks detect with config (should not fail on documentation)
        result = subprocess.run(
            ["gitleaks", "detect", "--config", ".gitleaks.toml", "--no-git", "--source", "."],
            cwd=get_repo_root(),
            capture_output=True,
            text=True,
            timeout=60,
        )

        # Should either succeed (0) or fail but NOT due to documentation examples
        if result.returncode != 0:
            # Check if failures are from documentation
            assert (
                ".openai/codex-instructions.md" not in result.stdout
            ), "Documentation examples should be allowlisted in .gitleaks.toml"

    def test_gitleaks_ignores_venv_directories(self):
        """Test that gitleaks config excludes .venv and similar directories."""
        repo_root = get_repo_root()
        config_file = repo_root / ".gitleaks.toml"

        if not config_file.exists():
            pytest.skip(".gitleaks.toml not yet created")

        try:
            import tomllib
        except ImportError:
            import tomli as tomllib

        with open(config_file, "rb") as f:
            config = tomllib.load(f)

        # Check for path exclusions
        paths = config.get("allowlist", {}).get("paths", [])

        # Should exclude common directories with dependencies
        expected_exclusions = [
            ".venv",
            "venv",
            "node_modules",
        ]

        for exclusion in expected_exclusions:
            assert any(exclusion in path for path in paths), f"Gitleaks config should exclude {exclusion} directory"

    def test_gitleaks_ignores_generated_clients(self):
        """Test that gitleaks config excludes generated client code."""
        repo_root = get_repo_root()
        config_file = repo_root / ".gitleaks.toml"

        if not config_file.exists():
            pytest.skip(".gitleaks.toml not yet created")

        try:
            import tomllib
        except ImportError:
            import tomli as tomllib

        with open(config_file, "rb") as f:
            config = tomllib.load(f)

        # Check for path exclusions
        paths = config.get("allowlist", {}).get("paths", [])

        # Should exclude generated code
        assert any("clients" in path for path in paths), "Gitleaks config should exclude generated client directories"

    def test_gitleaks_detects_real_secrets(self):
        """
        Test that gitleaks still detects real secrets (not a false negative factory).

        This ensures our allowlist doesn't go too far and miss real issues.
        """
        # Create a temporary file with a real-looking secret
        # IMPORTANT: Use a filename that is NOT in the .gitleaks.toml allowlist
        # (test_*.tmp is allowlisted, so we use .validation instead)
        test_file = get_repo_root() / "gitleaks-validation-file.txt"

        try:
            test_file.write_text(
                """
# This is a test file for secret detection
API_KEY=sk-1234567890abcdefghijklmnopqrstuvwxyz123456
DATABASE_PASSWORD=SuperSecretPassword123!
"""
            )

            # Run gitleaks on the entire directory (--source expects a directory, not a file)
            result = subprocess.run(
                ["gitleaks", "detect", "--config", ".gitleaks.toml", "--no-git"],
                cwd=get_repo_root(),
                capture_output=True,
                text=True,
                timeout=60,
            )

            # Should detect secrets in the test file
            assert (
                result.returncode != 0 or "gitleaks-validation-file.txt" in result.stdout
            ), f"Gitleaks should detect real secrets in {test_file.name}"

        finally:
            # Clean up test file
            if test_file.exists():
                test_file.unlink()


@pytest.mark.xdist_group(name="testgitleaksworkflowintegration")
class TestGitleaksWorkflowIntegration:
    """Test that GitHub workflows use gitleaks config correctly."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_validate_kubernetes_workflow_uses_gitleaks_config(self):
        """Test that validate-kubernetes.yaml workflow uses .gitleaks.toml."""
        workflow_file = get_repo_root() / ".github" / "workflows" / "validate-kubernetes.yaml"

        if not workflow_file.exists():
            pytest.skip("Workflow file not found")

        content = workflow_file.read_text()

        # Should reference the gitleaks config
        assert "--config" in content or ".gitleaks.toml" in content, "validate-kubernetes.yaml should use gitleaks config file"

    def test_gcp_compliance_workflow_uses_gitleaks_config(self):
        """Test that gcp-compliance-scan.yaml workflow uses .gitleaks.toml."""
        workflow_file = get_repo_root() / ".github" / "workflows" / "gcp-compliance-scan.yaml"

        if not workflow_file.exists():
            pytest.skip("Workflow file not found")

        content = workflow_file.read_text()

        # Should reference the gitleaks config
        assert "--config" in content or ".gitleaks.toml" in content, "gcp-compliance-scan.yaml should use gitleaks config file"


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "gitleaks: tests for gitleaks configuration")
    config.addinivalue_line("markers", "integration: integration tests")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
