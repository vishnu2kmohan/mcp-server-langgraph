#!/usr/bin/env python3
"""
TDD Tests for Placeholder Validation in Deployment Overlays

Ensures that production-ready overlays don't contain unresolved placeholders
that would cause runtime failures.

Codex Finding #3 (P0 Blocker): production-gke overlay emits placeholders after build
"""

import re
import subprocess
from pathlib import Path

import pytest
import yaml

from tests.fixtures.tool_fixtures import requires_tool
from tests.helpers.path_helpers import get_repo_root

# Mark as unit test to ensure it runs in CI (deployment validation)
pytestmark = [pytest.mark.unit, pytest.mark.validation]
REPO_ROOT = get_repo_root()
PRODUCTION_OVERLAYS = [
    REPO_ROOT / "deployments" / "overlays" / "production-gke",
    REPO_ROOT / "deployments" / "overlays" / "production",
]

# Dangerous placeholder patterns that should never appear in built manifests
# Note: example.com is excluded as it's a reasonable default in base layer
# Production overlays should override Ingress hosts to use actual domains
DANGEROUS_PLACEHOLDERS = [
    r"PLACEHOLDER_GCP_PROJECT_ID",
    r"PLACEHOLDER_SET_VIA_ENV",
    r"PRODUCTION_DOMAIN",
    r"TODO:(?!.*Ingress)",  # TODO except for Ingress-related
    r"FIXME:",
    r"REPLACE_ME",
    r"YOUR_\w+",
    r"ACCOUNT_ID\.dkr\.ecr",  # AWS ECR template
    # example.com excluded - base layer template value is acceptable
]


@requires_tool("kustomize")
def build_overlay(overlay_path: Path) -> str:
    """Build Kustomize overlay and return manifest as string."""
    result = subprocess.run(
        ["kubectl", "kustomize", str(overlay_path)], capture_output=True, text=True, cwd=REPO_ROOT, timeout=60
    )

    if result.returncode != 0:
        pytest.fail(f"Kustomize build failed for {overlay_path.name}:\nSTDERR: {result.stderr}\nSTDOUT: {result.stdout}")

    return result.stdout


def extract_placeholders(manifest_text: str, patterns: list[str]) -> set[str]:
    """
    Extract placeholder values from manifest text.

    Returns set of (pattern, matched_value, line_number) tuples.
    """
    findings = set()
    lines = manifest_text.split("\n")

    for line_num, line in enumerate(lines, 1):
        # Skip comments
        if line.strip().startswith("#"):
            continue

        for pattern in patterns:
            matches = re.finditer(pattern, line, re.IGNORECASE)
            for match in matches:
                # Check if it's part of a comment on the same line
                comment_pos = line.find("#")
                if comment_pos != -1 and match.start() > comment_pos:
                    continue  # Skip if placeholder is in inline comment

                findings.add((pattern, match.group(0), line_num, line.strip()))

    return findings


# Codex Finding #3 (P0 Blocker): Test for placeholder leakage
@pytest.mark.parametrize("overlay_path", PRODUCTION_OVERLAYS)
def test_production_overlay_no_placeholders(overlay_path: Path):
    """
    Test that production overlays don't contain unresolved placeholders.

    Codex Finding #3 (P0): production-gke emits PLACEHOLDER_GCP_PROJECT_ID,
    PLACEHOLDER_SET_VIA_ENV, and PRODUCTION_DOMAIN after kustomize build.

    Red phase: This test will fail until placeholders are replaced with
    actual values or Kustomize replacements.

    Green phase: After fixing placeholder handling, no dangerous patterns
    should appear in the built manifest.
    """
    if not overlay_path.exists():
        pytest.skip(f"Overlay {overlay_path.name} does not exist")

    # Build the overlay
    manifest = build_overlay(overlay_path)

    # Extract placeholders
    findings = extract_placeholders(manifest, DANGEROUS_PLACEHOLDERS)

    if findings:
        # Format findings for clear error message
        error_msg = f"\n{'=' * 80}\n"
        error_msg += f"PLACEHOLDER LEAKAGE DETECTED in {overlay_path.name}\n"
        error_msg += f"{'=' * 80}\n\n"
        error_msg += "The following placeholders were found in the built manifest:\n\n"

        for pattern, value, line_num, line_content in sorted(findings, key=lambda x: x[2]):
            error_msg += f"  Line {line_num}: {value}\n"
            error_msg += f"    Pattern: {pattern}\n"
            error_msg += f"    Context: {line_content}\n\n"

        error_msg += "\nImpact:\n"
        error_msg += "  - Deploying with placeholders causes runtime failures\n"
        error_msg += "  - Services fail to start due to invalid configuration\n"
        error_msg += "  - Workload Identity fails with invalid service account\n"
        error_msg += "  - OpenTelemetry export fails with invalid project ID\n\n"

        error_msg += "Fixes:\n"
        error_msg += "  1. Use Kustomize replacements to inject values at build time\n"
        error_msg += "  2. Define actual values in overlay config files\n"
        error_msg += "  3. Use environment variables in CI/CD pipeline\n"
        error_msg += f"  4. See: deployments/overlays/{overlay_path.name}/README.md\n"

        pytest.fail(error_msg)


@pytest.mark.parametrize("overlay_path", PRODUCTION_OVERLAYS)
def test_workload_identity_service_account_valid(overlay_path: Path):
    """
    Test that Workload Identity service account annotations are valid.

    Validates that ServiceAccount has proper GCP service account format:
    {sa-name}@{project-id}.iam.gserviceaccount.com
    """
    if not overlay_path.exists():
        pytest.skip(f"Overlay {overlay_path.name} does not exist")

    manifest = build_overlay(overlay_path)
    docs = list(yaml.safe_load_all(manifest))

    for doc in docs:
        if not doc or doc.get("kind") != "ServiceAccount":
            continue

        annotations = doc.get("metadata", {}).get("annotations", {})
        wi_annotation = annotations.get("iam.gke.io/gcp-service-account")

        if wi_annotation:
            # Should match: name@project-id.iam.gserviceaccount.com
            pattern = r"^[\w-]+@[\w-]+\.iam\.gserviceaccount\.com$"
            assert re.match(pattern, wi_annotation), (
                f"Invalid Workload Identity service account format: {wi_annotation}\n"
                f"Expected: service-account@project-id.iam.gserviceaccount.com\n"
                f"Must not contain PLACEHOLDER values"
            )


@pytest.mark.parametrize("overlay_path", PRODUCTION_OVERLAYS)
def test_environment_variables_no_placeholders(overlay_path: Path):
    """
    Test that Deployment environment variables don't contain placeholders.

    Validates that env vars in Deployments have actual values, not placeholders.
    """
    if not overlay_path.exists():
        pytest.skip(f"Overlay {overlay_path.name} does not exist")

    manifest = build_overlay(overlay_path)
    docs = list(yaml.safe_load_all(manifest))

    placeholder_envs = []

    for doc in docs:
        if not doc or doc.get("kind") not in ["Deployment", "StatefulSet"]:
            continue

        name = doc.get("metadata", {}).get("name")
        containers = doc.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])

        for container in containers:
            container_name = container.get("name")
            envs = container.get("env", [])

            for env in envs:
                env_name = env.get("name")
                env_value = env.get("value", "")

                # Skip if value is from secret/configmap
                if env.get("valueFrom"):
                    continue

                # Check for placeholders in value
                for pattern in DANGEROUS_PLACEHOLDERS:
                    if re.search(pattern, str(env_value), re.IGNORECASE):
                        placeholder_envs.append(
                            f"{doc.get('kind')}/{name} container={container_name} env={env_name} value={env_value}"
                        )

    assert not placeholder_envs, (
        "Found environment variables with placeholder values:\n"
        + "\n".join(f"  - {env}" for env in placeholder_envs)
        + "\n\nUse Kustomize replacements or actual values"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
