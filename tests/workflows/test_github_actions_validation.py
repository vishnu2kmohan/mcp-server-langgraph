"""
Workflow Validation Tests - Prevent GitHub Actions Regressions

This test suite validates GitHub Actions workflows to prevent the 10 critical issues
identified in the OpenAI Codex review. Following TDD principles, these tests were
written BEFORE fixing the issues to ensure they catch regressions.

Test Coverage:
1. release.yaml - Helm version handling (no 'v' prefix)
2. release.yaml - PyPI build tool installation
3. deploy-production-gke.yaml - Release event type
4. ci.yaml - Docker build dependencies
5. setup-python-deps - Input handling
6. Link checker workflow duplication
7. Validate deployments workflow duplication
8. Scheduled jobs secret gating
9. Workflow YAML syntax validation
10. Workflow event trigger validation

Author: Claude Code (TDD implementation)
Created: 2025-11-06
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


@pytest.fixture
def release_workflow(workflows_dir: Path) -> dict:
    """Load and parse release.yaml workflow."""
    release_file = workflows_dir / "release.yaml"
    assert release_file.exists(), "release.yaml not found"

    with open(release_file) as f:
        return yaml.safe_load(f)


@pytest.fixture
def deploy_prod_workflow(workflows_dir: Path) -> dict:
    """Load and parse deploy-production-gke.yaml workflow."""
    deploy_file = workflows_dir / "deploy-production-gke.yaml"
    assert deploy_file.exists(), "deploy-production-gke.yaml not found"

    with open(deploy_file) as f:
        return yaml.safe_load(f)


@pytest.fixture
def ci_workflow(workflows_dir: Path) -> dict:
    """Load and parse ci.yaml workflow."""
    ci_file = workflows_dir / "ci.yaml"
    assert ci_file.exists(), "ci.yaml not found"

    with open(ci_file) as f:
        return yaml.safe_load(f)


@pytest.fixture
def setup_python_deps_action(actions_dir: Path) -> dict:
    """Load and parse setup-python-deps action."""
    action_file = actions_dir / "setup-python-deps" / "action.yml"
    assert action_file.exists(), "setup-python-deps/action.yml not found"

    with open(action_file) as f:
        return yaml.safe_load(f)


# ==============================================================================
# Test 1: release.yaml - Helm Version Handling (No 'v' Prefix)
# ==============================================================================


def test_release_yaml_helm_version_no_v_prefix(workflows_dir: Path):
    """
    Test that release.yaml uses sanitized version (without 'v' prefix) for Helm packaging.

    Issue: Helm rejects versions with leading 'v' per SemVer 2 spec.
    Location: .github/workflows/release.yaml:275, 286

    Expected:
    - helm package should use ${{ steps.version.outputs.full }}
    - helm push should use sanitized version in filename
    - Should NOT use raw ${{ github.ref_name }} which contains 'v' prefix
    """
    release_file = workflows_dir / "release.yaml"
    with open(release_file) as f:
        content = f.read()

    # Check for helm package command (may be multi-line with variables)
    helm_package_match = re.search(r'helm package .*? --version ["\$]', content, re.DOTALL)
    assert helm_package_match, "helm package command not found"

    # Check the context around helm package for version usage
    helm_package_section = content[max(0, helm_package_match.start() - 500) : helm_package_match.end() + 500]

    # Should not use raw github.ref_name directly in helm package command
    assert not re.search(r"helm package.*--version.*github\.ref_name", helm_package_section, re.DOTALL), (
        "helm package uses raw github.ref_name (contains 'v' prefix)\n"
        "Should use: steps.version.outputs.full (sanitized version)"
    )

    # Verify it uses sanitized version (either directly or via variable)
    uses_sanitized = "steps.version.outputs.full" in helm_package_section or (
        'VERSION="${{ steps.version.outputs.full }}"' in content and '"$VERSION"' in helm_package_section
    )
    assert uses_sanitized, "helm package should use sanitized version (steps.version.outputs.full or variable derived from it)"

    # Check for helm push command (may use variable)
    helm_push_match = re.search(r"helm push.*?mcp-server-langgraph-.*?\.tgz", content, re.DOTALL)
    assert helm_push_match, "helm push command not found"

    helm_push_section = content[max(0, helm_push_match.start() - 500) : helm_push_match.end() + 500]

    # Should not use raw github.ref_name in filename
    assert not re.search(r"mcp-server-langgraph-\$\{\{\s*github\.ref_name\s*\}\}", helm_push_section), (
        "helm push uses raw github.ref_name in filename (contains 'v' prefix)\n"
        "Should use: sanitized version (steps.version.outputs.full or derived variable)"
    )

    # Verify sanitized version is used (directly or via variable)
    uses_sanitized_push = (
        "steps.version.outputs.full" in helm_push_section
        or "steps.helm_package.outputs.version" in helm_push_section
        or ('VERSION="${{ steps.version.outputs.full }}"' in content and "${VERSION}" in helm_push_section)
    )
    assert uses_sanitized_push, "helm push should use sanitized version in filename"


# ==============================================================================
# Test 2: release.yaml - PyPI Build Tool Installation
# ==============================================================================


def test_release_yaml_pypi_build_tools_installation(workflows_dir: Path):
    """
    Test that release.yaml installs build tools to the active Python interpreter.

    Issue: 'uv tool install build' creates isolated environment, not accessible via 'python -m build'
    Location: .github/workflows/release.yaml:332-344

    Expected:
    - Should use 'uv pip install --system build twine' OR 'uv run python -m build'
    - Should NOT use 'uv tool install' followed by bare 'python -m build'
    """
    release_file = workflows_dir / "release.yaml"
    with open(release_file) as f:
        content = f.read()

    # Check if using uv tool install (problematic pattern)
    if "uv tool install build" in content:
        # If using uv tool install, must use uv run for execution
        assert "uv run python -m build" in content or "uv run twine" in content, (
            "Found 'uv tool install build' but not using 'uv run python -m build'\n"
            "Either use 'uv pip install --system build twine' OR 'uv run' for execution"
        )

    # Preferred pattern: uv pip install --system
    # Allow either this or uv run pattern
    has_system_install = "uv pip install --system" in content and "build" in content
    has_uv_run_build = "uv run python -m build" in content or "uv run twine" in content

    assert has_system_install or has_uv_run_build, (
        "PyPI build tools not installed correctly.\n"
        "Expected: 'uv pip install --system build twine' OR 'uv run python -m build'"
    )


# ==============================================================================
# Test 3: deploy-production-gke.yaml - Release Event Type
# ==============================================================================


def test_deploy_production_event_type_is_published(deploy_prod_workflow: dict):
    """
    Test that deploy-production-gke.yaml uses correct release event type.

    Issue: GitHub releases fire with action 'published', not 'released'
    Location: .github/workflows/deploy-production-gke.yaml:17-19

    Expected:
    - on.release.types should contain ['published']
    - Should NOT use ['released'] which never matches
    """
    assert "release" in deploy_prod_workflow.get("on", {}), "deploy-production-gke.yaml should trigger on release events"

    release_config = deploy_prod_workflow["on"]["release"]
    event_types = release_config.get("types", [])

    assert "published" in event_types, (
        f"deploy-production-gke.yaml should use 'published' event type, found: {event_types}\n"
        f"GitHub releases fire with 'published' action, not 'released'"
    )

    assert "released" not in event_types, (
        f"deploy-production-gke.yaml should NOT use 'released' event type, found: {event_types}\n"
        f"The 'released' type has inconsistent behavior and may never trigger"
    )


# ==============================================================================
# Test 4: ci.yaml - Docker Build Dependencies
# ==============================================================================


def test_ci_yaml_docker_build_depends_on_tests(ci_workflow: dict):
    """
    Test that ci.yaml docker-build job depends on test completion.

    Issue: docker-build runs in parallel with tests, can push images even if tests fail
    Location: .github/workflows/ci.yaml:274-405

    Expected:
    - docker-build job should have 'needs: [test]' or 'needs: [test, pre-commit]'
    - Prevents pushing broken images when tests fail
    """
    jobs = ci_workflow.get("jobs", {})
    assert "docker-build" in jobs, "docker-build job not found in ci.yaml"

    docker_build_job = jobs["docker-build"]
    needs = docker_build_job.get("needs", [])

    # Normalize needs to list
    if isinstance(needs, str):
        needs = [needs]

    assert "test" in needs, (
        f"docker-build job should depend on 'test' job, found needs: {needs}\n" f"This prevents pushing images when tests fail"
    )


# ==============================================================================
# Test 5: setup-python-deps - Input Handling
# ==============================================================================


def test_setup_python_deps_input_handling(setup_python_deps_action: dict):
    """
    Test that setup-python-deps action properly handles or removes legacy inputs.

    Issue: Action defines install-dev/install-test inputs but ignores them
    Location: .github/actions/setup-python-deps/action.yml:11-19, 69-70

    Expected:
    - Either implement install-dev/install-test inputs properly
    - OR remove these inputs entirely (preferred)
    - Should use 'extras' parameter instead
    """
    inputs = setup_python_deps_action.get("inputs", {})

    # Check if legacy inputs still exist
    has_install_dev = "install-dev" in inputs
    has_install_test = "install-test" in inputs

    if has_install_dev or has_install_test:
        # If legacy inputs exist, they must be implemented in the action steps
        steps = setup_python_deps_action.get("runs", {}).get("steps", [])
        action_code = "\n".join(step.get("run", "") for step in steps if "run" in step)

        # Check if inputs are actually used
        if has_install_dev:
            assert "${{ inputs.install-dev }}" in action_code, (
                "'install-dev' input defined but not used in action implementation\n"
                "Either implement it properly or remove the input"
            )

        if has_install_test:
            assert "${{ inputs.install-test }}" in action_code, (
                "'install-test' input defined but not used in action implementation\n"
                "Either implement it properly or remove the input"
            )

    # Preferred: Use 'extras' parameter instead
    assert "extras" in inputs, (
        "setup-python-deps should support 'extras' parameter for dependency groups\n" "Example: extras: 'dev builder'"
    )


# ==============================================================================
# Test 6: Link Checker Workflow Duplication
# ==============================================================================


def test_no_duplicate_link_checker_workflows(workflow_files: Dict[str, Path]):
    """
    Test that there are no duplicate link checker workflows.

    Issue: Both link-checker.yaml and docs-link-check.yml exist with overlapping functionality
    Location: .github/workflows/link-checker.yaml, docs-link-check.yml

    Expected:
    - Only one link checker workflow should exist
    - Should have clear, non-overlapping responsibilities
    """
    link_checker_files = [name for name in workflow_files.keys() if "link" in name.lower() and "check" in name.lower()]

    assert len(link_checker_files) <= 1, (
        f"Found {len(link_checker_files)} link checker workflows: {link_checker_files}\n"
        f"Consolidate into a single workflow to avoid duplication and confusion"
    )


# ==============================================================================
# Test 7: Validate Deployments Workflow Duplication
# ==============================================================================


def test_no_duplicate_validate_deployment_workflows(workflow_files: Dict[str, Path]):
    """
    Test that validate-deployments workflows have clear separation of concerns.

    Issue: Both validate-deployments.yaml and validate-deployments.yml exist with overlap
    Location: .github/workflows/validate-deployments.yaml, validate-deployments.yml

    Expected:
    - Either consolidate into one workflow
    - OR clearly separate responsibilities (e.g., infra vs k8s)
    - Should not have overlapping validation logic
    """
    validate_deployment_files = [
        name for name in workflow_files.keys() if "validate" in name.lower() and "deployment" in name.lower()
    ]

    if len(validate_deployment_files) > 1:
        # If multiple files exist, they should have distinct names indicating purpose
        # e.g., validate-deployments.yaml (infrastructure) and validate-kubernetes.yaml (K8s)
        names_lower = [name.lower() for name in validate_deployment_files]

        # Check for clear differentiation in naming
        has_clear_separation = any("kubernetes" in name or "k8s" in name or "infra" in name for name in names_lower)

        assert has_clear_separation or len(validate_deployment_files) == 1, (
            f"Found {len(validate_deployment_files)} deployment validation workflows: {validate_deployment_files}\n"
            f"Either consolidate into one OR use distinct names like:\n"
            f"  - validate-deployments.yaml (infrastructure: Docker, DB, VPC)\n"
            f"  - validate-kubernetes.yaml (K8s manifests: Helm, Kustomize)"
        )


# ==============================================================================
# Test 8: Scheduled Jobs Secret Gating
# ==============================================================================


def test_scheduled_jobs_gated_by_secrets(workflow_files: Dict[str, Path]):
    """
    Test that scheduled jobs requiring GCP secrets are properly gated.

    Issue: Scheduled jobs fail noisily in forks without WIF secrets
    Location: .github/workflows/gcp-drift-detection.yaml, cost-tracking.yaml

    Expected:
    - Jobs requiring GCP_WIF_PROVIDER should check for secret existence
    - Should only run in main repository with proper configuration
    - Should fail gracefully with clear message if secrets missing
    """
    gcp_workflows = ["gcp-drift-detection.yaml", "cost-tracking.yaml"]

    for workflow_name in gcp_workflows:
        if workflow_name not in workflow_files:
            continue  # Skip if workflow doesn't exist

        workflow_file = workflow_files[workflow_name]
        with open(workflow_file) as f:
            workflow_content = f.read()

        # Check if workflow uses GCP WIF secrets
        uses_wif = "GCP_WIF_PROVIDER" in workflow_content or "workload_identity_provider" in workflow_content

        if uses_wif:
            # Should have secret existence check
            has_secret_check = any(
                [
                    "secrets.GCP_WIF_PROVIDER" in workflow_content and "!=" in workflow_content,
                    "vars.GCP_WIF_PROVIDER" in workflow_content and "!=" in workflow_content,
                    "github.repository ==" in workflow_content,  # Repository check
                ]
            )

            assert has_secret_check, (
                f"{workflow_name} uses GCP WIF secrets but doesn't gate execution\n"
                f"Add secret existence check to prevent noisy failures in forks:\n"
                f"  if: secrets.GCP_WIF_PROVIDER != '' && github.repository == 'owner/repo'"
            )


# ==============================================================================
# Test 9: Workflow YAML Syntax Validation
# ==============================================================================


def test_workflow_yaml_syntax_valid(workflow_files: Dict[str, Path]):
    """
    Test that all workflow files have valid YAML syntax.

    Expected:
    - All .yaml and .yml files should parse without errors
    - Should not have malformed YAML structures
    """
    errors = []

    for name, filepath in workflow_files.items():
        try:
            with open(filepath) as f:
                yaml.safe_load(f)
        except yaml.YAMLError as e:
            errors.append(f"{name}: {str(e)}")

    assert not errors, "Found YAML syntax errors in workflows:\n" + "\n".join(f"  - {err}" for err in errors)


# ==============================================================================
# Test 10: Workflow Event Trigger Validation
# ==============================================================================


def test_workflow_event_triggers_valid(workflow_files: Dict[str, Path]):
    """
    Test that all workflow event triggers use valid GitHub Actions event types.

    Expected:
    - Event types should match GitHub Actions API
    - Common mistakes: 'released' instead of 'published', invalid check_suite types
    """
    # Valid event types per GitHub Actions documentation
    VALID_RELEASE_TYPES = {"published", "unpublished", "created", "edited", "deleted", "prereleased"}
    VALID_CHECK_SUITE_TYPES = {"completed", "requested", "rerequested"}
    VALID_PR_TYPES = {
        "opened",
        "synchronize",
        "reopened",
        "closed",
        "edited",
        "labeled",
        "unlabeled",
        "assigned",
        "unassigned",
    }

    errors = []

    for name, filepath in workflow_files.items():
        with open(filepath) as f:
            workflow = yaml.safe_load(f)

        if not workflow or "on" not in workflow:
            continue

        on_config = workflow["on"]
        if isinstance(on_config, str):
            continue  # Simple event like 'push'

        # Check release event types
        if "release" in on_config and isinstance(on_config["release"], dict):
            types = on_config["release"].get("types", [])
            invalid_types = set(types) - VALID_RELEASE_TYPES
            if invalid_types:
                errors.append(
                    f"{name}: Invalid release event types: {invalid_types}\n" f"  Valid types: {VALID_RELEASE_TYPES}"
                )

        # Check check_suite event types
        if "check_suite" in on_config and isinstance(on_config["check_suite"], dict):
            types = on_config["check_suite"].get("types", [])
            invalid_types = set(types) - VALID_CHECK_SUITE_TYPES
            if invalid_types:
                errors.append(
                    f"{name}: Invalid check_suite event types: {invalid_types}\n" f"  Valid types: {VALID_CHECK_SUITE_TYPES}"
                )

        # Check pull_request event types
        if "pull_request" in on_config and isinstance(on_config["pull_request"], dict):
            types = on_config["pull_request"].get("types", [])
            invalid_types = set(types) - VALID_PR_TYPES
            if invalid_types:
                errors.append(
                    f"{name}: Invalid pull_request event types: {invalid_types}\n" f"  Valid types: {VALID_PR_TYPES}"
                )

    assert not errors, "Found invalid event trigger types:\n" + "\n".join(f"  - {err}" for err in errors)


# ==============================================================================
# Summary Test
# ==============================================================================


def test_workflow_validation_summary(workflow_files: Dict[str, Path]):
    """
    Summary test to provide overview of workflow validation coverage.

    This test always passes but prints useful information about the test suite.
    """
    print("\n" + "=" * 80)
    print("WORKFLOW VALIDATION TEST SUITE SUMMARY")
    print("=" * 80)
    print(f"\n📁 Workflows tested: {len(workflow_files)}")
    print(f"   Files: {', '.join(sorted(workflow_files.keys()))}")
    print("\n✅ Test Coverage:")
    print("   1. Helm version handling (no 'v' prefix)")
    print("   2. PyPI build tool installation")
    print("   3. Release event type validation")
    print("   4. Docker build job dependencies")
    print("   5. Action input handling")
    print("   6. Link checker workflow deduplication")
    print("   7. Deployment validation workflow organization")
    print("   8. Scheduled job secret gating")
    print("   9. YAML syntax validation")
    print("   10. Event trigger validation")
    print("\n🎯 Purpose:")
    print("   Prevent the 10 critical GitHub Actions workflow issues identified")
    print("   in the OpenAI Codex review from recurring.")
    print("\n📚 TDD Approach:")
    print("   RED Phase:   Tests written first (should fail)")
    print("   GREEN Phase: Code fixed to make tests pass")
    print("   REFACTOR:    Code improved while tests remain green")
    print("=" * 80 + "\n")
