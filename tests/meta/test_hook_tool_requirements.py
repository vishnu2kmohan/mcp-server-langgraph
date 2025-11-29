"""
Meta-validation: Ensure hooks fail when required tools are missing.

This test suite ensures that:
1. mise.toml exists and specifies all required tools
2. Pre-commit hooks FAIL (not skip) when tools are missing
3. Clear error messages guide developers to install missing tools

TDD Principle: These tests define the expected behavior BEFORE implementation.
The hooks should fail everywhere (not just CI) to force all developers to
install the required toolchain via mise.

Reference: Pre-commit/Pre-push Hook & CI Pipeline Remediation Plan (P0-3)
Decision: "Fail everywhere" - Hooks always exit 1 if tools missing
"""

import gc
import re
import subprocess
from pathlib import Path

import tomllib

import pytest

# Mark as unit+meta test to ensure it runs in CI (validates test infrastructure)
pytestmark = pytest.mark.unit


# ══════════════════════════════════════════════════════════════════════════════
# Required Tools - Single Source of Truth
# ══════════════════════════════════════════════════════════════════════════════

REQUIRED_TOOLS = {
    "helm": "Validates Helm chart syntax (deployments/helm/)",
    "kubectl": "Validates Kustomize overlays (deployments/kubernetes/)",
    "trivy": "Security scans on Kubernetes manifests",
    "terraform": "Validates Terraform configurations (deployments/terraform/)",
    "actionlint": "Validates GitHub Actions workflow syntax",
    "node": "Required for Mintlify docs validation",
}

# Hook IDs that require external tools
TOOL_DEPENDENT_HOOKS = {
    "helm-lint": "helm",
    "validate-cloud-overlays": "kubectl",
    "trivy-scan-k8s-manifests": "trivy",
    "mintlify-broken-links-check": "node",
}


@pytest.mark.xdist_group(name="test_hook_tool_requirements")
class TestMiseToolchain:
    """Validate mise.toml configuration for developer toolchain."""

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
            timeout=60,
        )
        return Path(result.stdout.strip())

    @pytest.fixture
    def mise_toml_path(self, repo_root: Path) -> Path:
        """Get path to mise.toml."""
        return repo_root / "mise.toml"

    @pytest.fixture
    def mise_config(self, mise_toml_path: Path) -> dict:
        """Parse mise.toml configuration."""
        if not mise_toml_path.exists():
            pytest.fail(
                f"mise.toml not found at {mise_toml_path}\n"
                "This file is required for developer toolchain management.\n"
                "See: Pre-commit/Pre-push Hook & CI Pipeline Remediation Plan (P0-3)"
            )
        with open(mise_toml_path, "rb") as f:
            return tomllib.load(f)

    def test_mise_toml_exists(self, mise_toml_path: Path) -> None:
        """
        mise.toml MUST exist for tool management.

        This file ensures all developers have the same tool versions installed,
        eliminating "works on my machine" issues with helm, kubectl, trivy, etc.
        """
        assert mise_toml_path.exists(), (
            f"mise.toml not found at {mise_toml_path}\n\n"
            "This file is required for developer toolchain management.\n"
            "It should define versions for: helm, kubectl, trivy, actionlint, node\n\n"
            "Reference: Pre-commit/Pre-push Hook & CI Pipeline Remediation Plan (P0-3)"
        )

    def test_mise_toml_includes_all_required_tools(self, mise_config: dict) -> None:
        """
        mise.toml MUST specify all required tools.

        Required tools:
        - helm: Validates Helm chart syntax
        - kubectl: Validates Kustomize overlays
        - trivy: Security scans on K8s manifests
        - actionlint: Validates GitHub Actions
        - node: Required for Mintlify docs
        """
        tools_section = mise_config.get("tools", {})

        missing_tools = []
        for tool, purpose in REQUIRED_TOOLS.items():
            if tool not in tools_section:
                missing_tools.append(f"  - {tool}: {purpose}")

        if missing_tools:
            pytest.fail(
                "mise.toml is missing required tools:\n" + "\n".join(missing_tools) + "\n\n"
                "All tools are required for local validation to match CI.\n"
                "Add them to the [tools] section of mise.toml."
            )

    def test_mise_toml_has_valid_tool_versions(self, mise_config: dict) -> None:
        """
        mise.toml tool versions MUST be valid semver-like strings.

        This prevents typos like 'helm = true' instead of 'helm = "3.14"'.
        """
        tools_section = mise_config.get("tools", {})

        invalid_versions = []
        for tool in REQUIRED_TOOLS:
            if tool in tools_section:
                version = tools_section[tool]
                # Version should be a string with at least one digit
                if not isinstance(version, str) or not re.search(r"\d", version):
                    invalid_versions.append(f"  - {tool} = {version!r} (expected version string like '3.14')")

        if invalid_versions:
            pytest.fail(
                "mise.toml has invalid tool versions:\n" + "\n".join(invalid_versions) + "\n\n"
                "Tool versions should be semver-like strings (e.g., '3.14', '1.29.0')."
            )


@pytest.mark.xdist_group(name="test_hook_tool_requirements")
class TestHookToolBehavior:
    """Validate that hooks FAIL when required tools are missing."""

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
            timeout=60,
        )
        return Path(result.stdout.strip())

    @pytest.fixture
    def precommit_config_path(self, repo_root: Path) -> Path:
        """Get path to .pre-commit-config.yaml."""
        return repo_root / ".pre-commit-config.yaml"

    @pytest.fixture
    def precommit_config_content(self, precommit_config_path: Path) -> str:
        """Read .pre-commit-config.yaml content."""
        return precommit_config_path.read_text()

    def test_hooks_do_not_exit_zero_unconditionally(self, precommit_config_content: str) -> None:
        """
        Tool-dependent hooks MUST NOT exit 0 unconditionally when tools missing.

        The pattern 'exit 0' without CI check means the hook silently skips,
        allowing commits/pushes without validation. This causes CI failures
        that could have been caught locally.

        Expected pattern (FAIL everywhere):
        ```
        if ! command -v TOOL; then
            echo "ERROR: TOOL required. Install via: mise install"
            exit 1
        fi
        ```

        Forbidden pattern (silent skip):
        ```
        if ! command -v TOOL; then
            echo "Skipping..."
            exit 0  # BAD: Silent skip allows broken code through
        fi
        ```
        """
        issues = []

        for hook_id, tool in TOOL_DEPENDENT_HOOKS.items():
            # Find this hook's entry block in the config
            # Pattern: from "- id: <hook_id>" to next "- id:" or "- repo:"
            hook_pattern = rf"- id: {re.escape(hook_id)}.*?(?=\n  - id:|\n- repo:|\Z)"
            hook_match = re.search(hook_pattern, precommit_config_content, re.DOTALL)

            if not hook_match:
                issues.append(f"  - {hook_id}: Hook not found in config")
                continue

            hook_content = hook_match.group(0)

            # Check for unconditional exit 0 pattern (silent skip)
            # This is the BAD pattern we want to eliminate
            silent_skip_pattern = rf"command.*{re.escape(tool)}.*?exit 0"
            if re.search(silent_skip_pattern, hook_content, re.DOTALL | re.IGNORECASE):
                # Check if there's ALSO an exit 1 path (conditional skip OK)
                has_exit_1 = "exit 1" in hook_content

                if not has_exit_1:
                    issues.append(
                        f"  - {hook_id}: Uses 'exit 0' without 'exit 1' path. Hook silently skips when {tool} missing."
                    )

        if issues:
            pytest.fail(
                "Hooks with silent skip behavior detected:\n" + "\n".join(issues) + "\n\n"
                "These hooks exit 0 when tools are missing, allowing commits without validation.\n"
                "Change to exit 1 with clear error message:\n"
                "  if ! command -v TOOL; then\n"
                '    echo "ERROR: TOOL required. Install via: mise install"\n'
                "    exit 1\n"
                "  fi\n\n"
                "Reference: Pre-commit/Pre-push Hook & CI Pipeline Remediation Plan (P0-3)\n"
                "Decision: 'Fail everywhere' - Hooks always exit 1 if tools missing"
            )

    def test_hooks_provide_mise_install_guidance(self, precommit_config_content: str) -> None:
        """
        Hook error messages MUST guide developers to install via mise.

        When a tool is missing, the error should clearly state:
        1. Which tool is required
        2. How to install it (mise install)
        """
        issues = []

        for hook_id, tool in TOOL_DEPENDENT_HOOKS.items():
            hook_pattern = rf"- id: {re.escape(hook_id)}.*?(?=\n  - id:|\n- repo:|\Z)"
            hook_match = re.search(hook_pattern, precommit_config_content, re.DOTALL)

            if not hook_match:
                continue

            hook_content = hook_match.group(0)

            # Check for mise install guidance in error paths
            has_mise_guidance = "mise install" in hook_content.lower() or "mise" in hook_content.lower()

            # Only require guidance if hook checks for tool presence
            checks_for_tool = f"command -v {tool}" in hook_content or "command -v npm" in hook_content

            if checks_for_tool and not has_mise_guidance:
                issues.append(f"  - {hook_id}: Missing 'mise install' guidance when {tool} unavailable")

        if issues:
            pytest.fail(
                "Hooks missing mise install guidance:\n" + "\n".join(issues) + "\n\n"
                "Error messages should include:\n"
                '  echo "ERROR: TOOL required. Install via: mise install"\n'
                '  echo "  curl https://mise.run | sh && mise install"'
            )


@pytest.mark.xdist_group(name="test_hook_tool_requirements")
class TestMakefileSudoSafety:
    """Validate Makefile doesn't require sudo for tool installation."""

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
            timeout=60,
        )
        return Path(result.stdout.strip())

    @pytest.fixture
    def makefile_content(self, repo_root: Path) -> str:
        """Read Makefile content."""
        return (repo_root / "Makefile").read_text()

    def test_actionlint_install_does_not_require_sudo(self, makefile_content: str) -> None:
        """
        actionlint installation MUST NOT use sudo.

        The pattern 'sudo mv ... /usr/local/bin/' fails on:
        - Locked-down developer laptops
        - CI containers without sudo
        - Environments where /usr/local/bin is read-only

        Expected: Install to ~/.local/bin or use mise for tool management.

        Reference: Pre-commit/Pre-push Hook & CI Pipeline Remediation Plan (P0-4)
        """
        # Find actionlint installation section
        actionlint_pattern = r"actionlint.*?(?=\n[a-zA-Z_-]+:|\Z)"
        actionlint_match = re.search(actionlint_pattern, makefile_content, re.DOTALL | re.IGNORECASE)

        if actionlint_match:
            actionlint_section = actionlint_match.group(0)

            # Check for sudo usage
            if "sudo" in actionlint_section:
                pytest.fail(
                    "Makefile uses 'sudo' for actionlint installation.\n\n"
                    "This breaks on locked-down systems and CI containers.\n\n"
                    "Options:\n"
                    "1. Install to ~/.local/bin (no sudo required)\n"
                    "2. Use mise for tool management (preferred)\n"
                    "3. Check if tool is installed, fail with mise guidance if not\n\n"
                    "Example fix:\n"
                    "  if ! command -v actionlint; then\n"
                    '    echo "actionlint not found. Install with: mise install"\n'
                    "    exit 1\n"
                    "  fi\n\n"
                    "Reference: Pre-commit/Pre-push Hook & CI Pipeline Remediation Plan (P0-4)"
                )
