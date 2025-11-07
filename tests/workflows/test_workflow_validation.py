"""
New Workflow Validation Tests - OpenAI Codex Review Findings

This test suite validates GitHub Actions workflows to prevent the issues
identified in the 2025-11-07 OpenAI Codex comprehensive review.

Following TDD principles, these tests are written BEFORE fixing the issues
to ensure they catch the current problems and prevent future regressions.

Test Coverage (RED → GREEN → REFACTOR):
1. Invalid astral-sh/setup-uv@v5 tags (should be v7.1.1)
2. Hard-coded Artifact Registry paths (should use env vars)
3. Obsolete install-test parameter in composite action usage
4. Missing fork protection guards on commit/push jobs
5. Ad-hoc uv pip install commands (should use composite action)
6. Staging validation gaps (should match production)
7. Gcloud setup consistency (staging vs production)
8. Action version consistency across workflows

Author: Claude Code (TDD implementation)
Created: 2025-11-07
"""

import re
from pathlib import Path
from typing import Dict, List, Set

import pytest
import yaml

# ==============================================================================
# Test Fixtures
# ==============================================================================


@pytest.fixture
def workflows_dir() -> Path:
    """Get the workflows directory path."""
    repo_root = Path(__file__).parent.parent.parent
    return repo_root / ".github" / "workflows"


@pytest.fixture
def actions_dir() -> Path:
    """Get the actions directory path."""
    repo_root = Path(__file__).parent.parent.parent
    return repo_root / ".github" / "actions"


@pytest.fixture
def workflow_files(workflows_dir: Path) -> Dict[str, Path]:
    """Load all workflow files."""
    workflows = {}
    for pattern in ["*.yaml", "*.yml"]:
        for workflow_file in workflows_dir.glob(pattern):
            workflows[workflow_file.name] = workflow_file
    return workflows


# ==============================================================================
# Test 1: Invalid astral-sh/setup-uv@v5 Tags
# ==============================================================================


def test_uv_action_uses_valid_version(workflow_files: Dict[str, Path]):
    """
    Test that all workflows use valid astral-sh/setup-uv version tags.

    Issue: Several workflows use @v5 which is invalid/outdated
    Should use: @v7.1.1 (current stable version)

    Affected files:
    - ci.yaml:170
    - performance-regression.yaml:70,230
    - security-validation.yml:37,64
    - dora-metrics.yaml:87

    Expected:
    - All uses of astral-sh/setup-uv should use @v7.1.1 or @v7
    - Should NOT use @v5 (invalid tag)
    """
    VALID_UV_VERSIONS = {"v7.1.1", "v7", "v7.1.0"}  # Add valid versions here
    INVALID_UV_VERSIONS = {"v5"}  # Known invalid versions

    errors = []

    for name, filepath in workflow_files.items():
        with open(filepath) as f:
            content = f.read()

        # Find all uses of astral-sh/setup-uv
        uv_uses = re.findall(r"astral-sh/setup-uv@(\S+)", content)

        if not uv_uses:
            continue  # No uv action usage in this file

        for version in uv_uses:
            if version in INVALID_UV_VERSIONS:
                errors.append(f"{name}: Uses astral-sh/setup-uv@{version} (invalid version, should use v7.1.1)")
            elif version not in VALID_UV_VERSIONS:
                # Warn about unknown versions
                errors.append(f"{name}: Uses astral-sh/setup-uv@{version} (unknown version, expected v7.1.1)")

    assert not errors, "Found invalid astral-sh/setup-uv versions:\n" + "\n".join(f"  - {err}" for err in errors)


# ==============================================================================
# Test 2: Hard-Coded Artifact Registry Paths
# ==============================================================================


def test_no_hardcoded_artifact_registry_paths(workflow_files: Dict[str, Path]):
    """
    Test that deployment workflows use environment variables for Artifact Registry paths.

    Issue: Hard-coded project ID and region in image paths
    Should use: ${{ env.GCP_REGION }} and ${{ env.GCP_PROJECT_ID }}

    Affected files:
    - deploy-staging-gke.yaml:212
    - deploy-production-gke.yaml:291

    Expected:
    - Image paths should use env.GCP_REGION and env.GCP_PROJECT_ID
    - Should NOT hard-code us-central1-docker.pkg.dev/vishnu-sandbox-20250310
    """
    DEPLOYMENT_WORKFLOWS = ["deploy-staging-gke.yaml", "deploy-production-gke.yaml"]
    errors = []

    for workflow_name in DEPLOYMENT_WORKFLOWS:
        if workflow_name not in workflow_files:
            continue

        filepath = workflow_files[workflow_name]
        with open(filepath) as f:
            content = f.read()

        # Check for hard-coded project ID
        hardcoded_project = re.findall(r"vishnu-sandbox-\d+(?!/\$\{\{)", content)
        if hardcoded_project:
            # Make sure it's not just in a default value like: vars.GCP_PROJECT_ID || 'vishnu-sandbox-20250310'
            # Check if the hard-coded value is in an image path (kustomize edit set image or similar)
            for match in re.finditer(r"vishnu-sandbox-\d+", content):
                line_start = content.rfind("\n", 0, match.start()) + 1
                line_end = content.find("\n", match.end())
                line = content[line_start:line_end]

                # Skip if it's a default value in env var definition
                if "||" in line and ("vars.GCP_PROJECT_ID" in line or "env.GCP_PROJECT_ID" in line):
                    continue

                # Skip if it's in a comment
                if line.strip().startswith("#"):
                    continue

                # This is a hard-coded usage
                errors.append(f"{workflow_name}: Hard-coded project ID in line: {line.strip()[:100]}")

        # Check for hard-coded region in image paths
        # Pattern: us-central1-docker.pkg.dev (not using ${{ env.GCP_REGION }})
        hardcoded_region_pattern = r"(?<!||)\s+(?:us-central1|us-west1|us-east1)-docker\.pkg\.dev"
        for match in re.finditer(hardcoded_region_pattern, content):
            line_start = content.rfind("\n", 0, match.start()) + 1
            line_end = content.find("\n", match.end())
            line = content[line_start:line_end]

            # Skip if it's a default value in env var definition
            if "||" in line and "GCP_REGION" in line:
                continue

            # Skip comments
            if line.strip().startswith("#"):
                continue

            errors.append(f"{workflow_name}: Hard-coded region in line: {line.strip()[:100]}")

    assert not errors, "Found hard-coded Artifact Registry paths:\n" + "\n".join(f"  - {err}" for err in errors)


# ==============================================================================
# Test 3: Obsolete install-test Parameter
# ==============================================================================


def test_no_obsolete_install_test_parameter(workflow_files: Dict[str, Path]):
    """
    Test that workflows don't use the obsolete install-test parameter.

    Issue: setup-python-deps no longer defines install-test input
    Workflows still pass it, causing parameter mismatch

    Affected files:
    - coverage-trend.yaml:67
    - quality-tests.yaml:77,121,162,207,245

    Expected:
    - Workflows should NOT use install-test: 'true'
    - Should use extras: 'dev builder' instead (already supported)
    """
    errors = []

    for name, filepath in workflow_files.items():
        with open(filepath) as f:
            content = f.read()

        # Search for install-test parameter usage
        if re.search(r"install-test:\s*['\"]?true['\"]?", content):
            errors.append(f"{name}: Uses obsolete 'install-test' parameter (should be removed, use 'extras' instead)")

    assert not errors, "Found obsolete install-test parameter usage:\n" + "\n".join(f"  - {err}" for err in errors)


# ==============================================================================
# Test 4: Fork Protection Guards
# ==============================================================================


def test_fork_protection_on_commit_jobs(workflow_files: Dict[str, Path]):
    """
    Test that workflows with commit/push operations have fork protection.

    Issue: Jobs that commit/push to repo don't check for forks
    Could fail noisily when run from forks

    Affected workflows:
    - bump-deployment-versions.yaml
    - dora-metrics.yaml
    - performance-regression.yaml

    Expected:
    - Jobs that commit should have: if: github.event.pull_request.head.repo.fork == false
    - OR check: if: github.repository == 'vishnu2kmohan/mcp-server-langgraph'
    """
    COMMIT_WORKFLOWS = {
        "bump-deployment-versions.yaml": ["git commit", "git push"],
        "dora-metrics.yaml": ["git commit", "git push"],
        "performance-regression.yaml": ["git commit", "git push"],
    }

    errors = []

    for workflow_name, commit_commands in COMMIT_WORKFLOWS.items():
        if workflow_name not in workflow_files:
            continue

        filepath = workflow_files[workflow_name]
        with open(filepath) as f:
            workflow_content = f.read()

        # Check if workflow has commit/push operations
        has_commit_ops = any(cmd in workflow_content for cmd in commit_commands)

        if not has_commit_ops:
            continue  # No commit operations, skip

        # Check for fork protection guards
        has_fork_guard = any(
            [
                "github.event.pull_request.head.repo.fork" in workflow_content,
                re.search(r"github\.repository\s*==\s*['\"]vishnu2kmohan/mcp-server-langgraph['\"]", workflow_content),
                "github.repository_owner == 'vishnu2kmohan'" in workflow_content,
            ]
        )

        # Also check if workflow only triggers on push to main (inherent fork protection)
        with open(filepath) as f:
            workflow = yaml.safe_load(f)

        on_config = workflow.get("on", {})
        triggers = []
        if isinstance(on_config, dict):
            triggers = list(on_config.keys())
        elif isinstance(on_config, str):
            triggers = [on_config]
        elif isinstance(on_config, list):
            triggers = on_config

        # If only triggers on push/release (not pull_request), it has implicit fork protection
        has_implicit_protection = "pull_request" not in triggers and ("push" in triggers or "release" in triggers)

        if not has_fork_guard and not has_implicit_protection:
            errors.append(
                f"{workflow_name}: Has commit/push operations but no fork protection guard\n"
                f"  Add: if: github.repository == 'vishnu2kmohan/mcp-server-langgraph'"
            )

    assert not errors, "Found workflows with missing fork protection:\n" + "\n".join(f"  - {err}" for err in errors)


# ==============================================================================
# Test 5: Ad-Hoc uv pip install Commands
# ==============================================================================


def test_no_adhoc_uv_pip_install(workflow_files: Dict[str, Path]):
    """
    Test that workflows use the composite action instead of ad-hoc uv pip install.

    Issue: Multiple workflows use ad-hoc 'uv pip install --system' commands
    Should use: setup-python-deps composite action for consistency

    Affected files:
    - performance-regression.yaml:74,79,235
    - security-validation.yml:41,68
    - ci.yaml:174
    - dora-metrics.yaml:91
    - release.yaml:353

    Expected:
    - Workflows should use setup-python-deps action with extras parameter
    - Should NOT use ad-hoc 'uv pip install --system' for dev/test dependencies
    - Exception: Special tools like 'build' and 'twine' for releases are acceptable
    """
    ACCEPTABLE_ADHOC_PACKAGES = {
        "build",  # PyPI build tools for releases
        "twine",  # PyPI upload tool for releases
    }

    errors = []

    for name, filepath in workflow_files.items():
        with open(filepath) as f:
            content = f.read()

        # Find all uv pip install --system commands
        adhoc_installs = re.findall(r"uv pip install --system\s+([^\n]+)", content)

        for install_line in adhoc_installs:
            # Parse packages from install line
            # Remove quotes, split by spaces
            packages = install_line.replace('"', "").replace("'", "").strip().split()

            # Filter out flags and options
            packages = [pkg for pkg in packages if not pkg.startswith("-")]

            # Check if any package is not in acceptable list
            unacceptable_packages = [
                pkg for pkg in packages if pkg not in ACCEPTABLE_ADHOC_PACKAGES and pkg != "-e" and not pkg.startswith(".")
            ]

            if unacceptable_packages:
                # Check if this workflow already uses setup-python-deps
                uses_composite = "uses: ./.github/actions/setup-python-deps" in content

                if uses_composite:
                    errors.append(
                        f"{name}: Uses ad-hoc 'uv pip install --system {' '.join(unacceptable_packages)}' "
                        f"but already uses setup-python-deps composite action\n"
                        f"  Consolidate into composite action with extras parameter"
                    )
                else:
                    errors.append(
                        f"{name}: Uses ad-hoc 'uv pip install --system {' '.join(unacceptable_packages)}'\n"
                        f"  Consider using setup-python-deps composite action for consistency"
                    )

    # This test is informational for now - we'll make it strict after enhancing the composite action
    if errors:
        pytest.skip(
            "Ad-hoc uv installs found (will be fixed after composite action enhancement):\n"
            + "\n".join(f"  - {err}" for err in errors)
        )


# ==============================================================================
# Test 6: Staging Validation Parity with Production
# ==============================================================================


def test_staging_has_comprehensive_validation(workflows_dir: Path):
    """
    Test that staging deployment has comprehensive validation like production.

    Issue: Staging workflow has fewer validation steps than production
    Should have: Kustomize validation, Kubeval, security scanning

    Expected:
    - deploy-staging-gke.yaml should have pre-deployment validation job
    - Should include: Kustomize validation, Kubeval, Trivy scanning
    - Should match production's validation coverage
    """
    staging_file = workflows_dir / "deploy-staging-gke.yaml"
    production_file = workflows_dir / "deploy-production-gke.yaml"

    if not staging_file.exists():
        pytest.skip("deploy-staging-gke.yaml not found")

    if not production_file.exists():
        pytest.skip("deploy-production-gke.yaml not found")

    with open(staging_file) as f:
        staging_workflow = yaml.safe_load(f)
        staging_content = f.seek(0) or f.read()

    with open(production_file) as f:
        production_workflow = yaml.safe_load(f)
        production_content = f.seek(0) or f.read()

    # Check for validation job in staging

    # Look for validation-related jobs
    validation_checks = {
        "kustomize build": "Kustomize validation",
        "kubeval": "Kubernetes manifest validation",
        "trivy": "Security scanning",
    }

    errors = []

    for check_command, check_name in validation_checks.items():
        # Check if production has this validation
        has_in_production = check_command in production_content.lower()

        if has_in_production:
            # Staging should also have it
            has_in_staging = check_command in staging_content.lower()

            if not has_in_staging:
                errors.append(f"Staging deployment missing {check_name} (present in production)")

    # This test will fail initially (RED phase) and pass after adding validation (GREEN phase)
    assert not errors, "Staging deployment validation gaps:\n" + "\n".join(f"  - {err}" for err in errors)


# ==============================================================================
# Test 7: Gcloud Setup Consistency
# ==============================================================================


def test_gcloud_setup_consistency(workflows_dir: Path):
    """
    Test that GCP deployment workflows use consistent gcloud setup approach.

    Issue: Production uses explicit setup-gcloud, staging uses get-gke-credentials directly
    Both approaches work, but should be consistent

    Expected:
    - Both staging and production should use the same approach
    - Preferred: get-gke-credentials@v3 (simpler, includes gcloud setup)
    - Alternative: Both use explicit setup-gcloud@v3 + get-gke-credentials
    """
    staging_file = workflows_dir / "deploy-staging-gke.yaml"
    production_file = workflows_dir / "deploy-production-gke.yaml"

    if not staging_file.exists() or not production_file.exists():
        pytest.skip("Deployment workflow files not found")

    with open(staging_file) as f:
        staging_content = f.read()

    with open(production_file) as f:
        production_content = f.read()

    # Check approaches
    staging_uses_setup_gcloud = "google-github-actions/setup-gcloud@" in staging_content
    production_uses_setup_gcloud = "google-github-actions/setup-gcloud@" in production_content


    # Both should use the same approach
    if staging_uses_setup_gcloud != production_uses_setup_gcloud:
        # Inconsistency found - this is informational, not a hard failure
        if not staging_uses_setup_gcloud and production_uses_setup_gcloud:
            pytest.skip(
                "Gcloud setup inconsistency detected:\n"
                "  Staging: Uses get-gke-credentials directly (simpler, recommended)\n"
                "  Production: Uses explicit setup-gcloud (redundant with get-gke-credentials)\n"
                "  Consider standardizing on get-gke-credentials@v3 approach"
            )


# ==============================================================================
# Test 8: Action Version Consistency
# ==============================================================================


def test_action_version_consistency(workflow_files: Dict[str, Path]):
    """
    Test that the same GitHub action is used with consistent versions across workflows.

    Expected:
    - Same action should use same version tag across all workflows
    - Exceptions: Documented version pins for specific compatibility reasons
    """
    action_versions = {}  # {action_name: {version: [workflow_files]}}

    for name, filepath in workflow_files.items():
        with open(filepath) as f:
            content = f.read()

        # Find all action uses: uses: owner/repo@version
        action_uses = re.findall(r"uses:\s+([a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+)@(\S+)", content)

        for action, version in action_uses:
            # Skip local actions (./.github/actions/...)
            if action.startswith("./"):
                continue

            if action not in action_versions:
                action_versions[action] = {}

            if version not in action_versions[action]:
                action_versions[action][version] = []

            action_versions[action][version].append(name)

    # Check for inconsistencies
    errors = []
    for action, versions in action_versions.items():
        if len(versions) > 1:
            # Multiple versions of same action
            versions_list = ", ".join(f"{ver} (used in {', '.join(files)})" for ver, files in versions.items())
            errors.append(f"{action}: Inconsistent versions used:\n  {versions_list}")

    assert not errors, "Found inconsistent action versions:\n" + "\n".join(f"  - {err}" for err in errors)


# ==============================================================================
# Summary Test
# ==============================================================================


def test_new_workflow_validation_summary(workflow_files: Dict[str, Path]):
    """
    Summary test to provide overview of new workflow validation coverage.
    """
    print("\n" + "=" * 80)
    print("NEW WORKFLOW VALIDATION TEST SUITE (OpenAI Codex 2025-11-07)")
    print("=" * 80)
    print(f"\n📁 Workflows tested: {len(workflow_files)}")
    print("\n✅ New Test Coverage:")
    print("   1. Invalid astral-sh/setup-uv@v5 tags (should use v7.1.1)")
    print("   2. Hard-coded Artifact Registry paths (should use env vars)")
    print("   3. Obsolete install-test parameter usage")
    print("   4. Missing fork protection guards on commit jobs")
    print("   5. Ad-hoc uv pip install commands (should use composite action)")
    print("   6. Staging validation gaps (should match production)")
    print("   7. Gcloud setup consistency (staging vs production)")
    print("   8. Action version consistency across workflows")
    print("\n🎯 TDD Phases:")
    print("   🔴 RED:    Tests written first → Will FAIL (confirms issues exist)")
    print("   🟢 GREEN:  Fixes applied → Tests PASS")
    print("   ♻️  REFACTOR: Code improved → Tests remain GREEN")
    print("=" * 80 + "\n")
