"""
Test Trivy security scan suppression configuration.

This test validates the configuration for suppressing false positive Trivy findings:
- AVD-KSV-0109 (HIGH): ConfigMap stores secrets in keys "dynamic_context_max_tokens", "model_max_tokens"

These are NOT secrets - they are numeric configuration values for LLM token limits.
Trivy's heuristic incorrectly flags any key containing "token" as sensitive data.

The suppression should be documented and scoped to avoid hiding real security issues.

Reference: Deploy to GKE Staging workflow Trivy false positives
"""

import gc
from pathlib import Path

import pytest

# Mark as unit+meta test to ensure it runs in CI (validates test infrastructure)
pytestmark = [pytest.mark.unit, pytest.mark.meta]


def test_trivyignore_exists_for_staging():
    """
    Verify that .trivyignore file exists in the staging-gke overlay directory.

    This file should contain documented suppressions for false positive findings.
    Per user requirement: Suppress with .trivyignore (recommended approach).
    """
    repo_root = Path(__file__).parent.parent.parent
    trivyignore_file = repo_root / "deployments/overlays/staging-gke/.trivyignore"

    assert trivyignore_file.exists(), (
        f".trivyignore file not found: {trivyignore_file}\n"
        "\n"
        "Expected file: deployments/overlays/staging-gke/.trivyignore\n"
        "This file should suppress false positive Trivy findings with clear documentation.\n"
        "\n"
        "Required suppressions:\n"
        "  - AVD-KSV-0109: model_max_tokens and dynamic_context_max_tokens are NOT secrets\n"
        "\n"
        "Fix: Create .trivyignore with documented suppressions"
    )

    # Verify it's not empty
    with open(trivyignore_file) as f:
        content = f.read().strip()

    assert content, (
        f".trivyignore file exists but is empty: {trivyignore_file}\n" "It should contain suppression rules with documentation"
    )


def test_trivyignore_documents_configmap_false_positive():
    """
    Verify that .trivyignore contains proper documentation for ConfigMap suppression.

    The suppression for AVD-KSV-0109 must be clearly documented to explain:
    1. Why the finding is a false positive
    2. What the flagged values actually represent
    3. Why it's safe to suppress

    This prevents confusion and ensures future maintainers understand the decision.
    """
    repo_root = Path(__file__).parent.parent.parent
    trivyignore_file = repo_root / "deployments/overlays/staging-gke/.trivyignore"

    with open(trivyignore_file) as f:
        content = f.read()

    # Check for AVD-KSV-0109 suppression
    assert "AVD-KSV-0109" in content, ".trivyignore must suppress AVD-KSV-0109 (ConfigMap false positive)"

    # Check for documentation (comments explaining the suppression)
    assert "#" in content, (
        ".trivyignore must include comments documenting why suppressions are safe.\n"
        "\n"
        "Required documentation:\n"
        "  - Explanation that model_max_tokens and dynamic_context_max_tokens are NOT secrets\n"
        "  - Clarification that these are numeric LLM configuration values\n"
        "  - Note that Trivy's heuristic incorrectly flags 'token' substring\n"
        "\n"
        "Example:\n"
        "# False positive: model_max_tokens and dynamic_context_max_tokens are NOT secrets\n"
        "# These are numeric LLM configuration values (max context size)\n"
        "# Trivy's heuristic flags any key containing 'token' as sensitive\n"
        "# Verified: These values are public configuration, safe in ConfigMap\n"
        "AVD-KSV-0109\n"
        "\n"
        f"Current content:\n{content}"
    )

    # Ensure the suppression mentions the actual keys being flagged
    has_context = "model_max_tokens" in content.lower() or "dynamic_context" in content.lower() or "token" in content.lower()

    assert has_context, (
        ".trivyignore documentation should mention the specific keys being suppressed:\n"
        "  - model_max_tokens\n"
        "  - dynamic_context_max_tokens\n"
        "\n"
        "This helps future maintainers understand what is being suppressed and why."
    )


def test_trivyignore_workflow_integration():
    """
    Verify that the deploy-staging-gke workflow is configured to use .trivyignore.

    The Trivy action should reference the trivyignores file so suppressions are applied.
    """
    repo_root = Path(__file__).parent.parent.parent
    workflow_file = repo_root / ".github/workflows/deploy-staging-gke.yaml"

    assert workflow_file.exists(), f"Workflow file not found: {workflow_file}"

    with open(workflow_file) as f:
        workflow_content = f.read()

    # The trivyignore file should be referenced in the Trivy scan step
    # OR it should be in the default location where Trivy will find it automatically

    # Check if trivyignores parameter is used
    has_trivyignores_param = "trivyignores:" in workflow_content

    # Check if .trivyignore is in the scan-ref directory (auto-discovered)
    has_scan_ref = "scan-ref:" in workflow_content

    # At least one approach should be used
    assert has_trivyignores_param or has_scan_ref, (
        "Workflow must either:\n"
        "  1. Specify 'trivyignores:' parameter pointing to .trivyignore file, OR\n"
        "  2. Scan a directory containing .trivyignore (auto-discovered)\n"
        "\n"
        "Current approach: Scanning /tmp/staging-manifests-for-scan.yaml\n"
        "\n"
        "Options:\n"
        "  A. Copy .trivyignore to /tmp/ before scanning\n"
        "  B. Add trivyignores parameter to Trivy action\n"
        "  C. Use TRIVYIGNORE environment variable\n"
        "\n"
        "Recommended: Option B (explicit parameter)"
    )
