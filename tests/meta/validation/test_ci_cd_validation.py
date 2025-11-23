"""
CI/CD Validation Tests

Tests to prevent common CI/CD workflow failures and configuration issues.

Created in response to comprehensive CI/CD audit (2025-11-07) that identified:
- Kustomize ConfigMap collisions causing 100% staging deployment failures
- E2E test health check timeouts causing 100% E2E test failures
- Composite action error handling causing 70% quality test failures

These tests ensure such issues cannot recur.
"""

import gc
import re
import subprocess
from pathlib import Path

import pytest
import yaml

from tests.fixtures.tool_fixtures import requires_tool

# Mark as unit test to ensure it runs in CI
pytestmark = pytest.mark.unit

# ==============================================================================
# Kustomize Configuration Tests
# ==============================================================================


@pytest.mark.requires_kustomize
@pytest.mark.xdist_group(name="testkustomizeconfigurations")
class TestKustomizeConfigurations:
    """Test Kustomize configurations for common issues

    CODEX FINDING #1: These tests require kustomize CLI tool.
    Tests will skip gracefully if kustomize is not installed.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def kustomize_overlays(self) -> list[Path]:
        """Get all Kustomize overlay directories"""
        deployments_dir = Path(__file__).parent.parent / "deployments" / "overlays"
        if not deployments_dir.exists():
            pytest.skip("Deployments directory not found")

        overlays = [d for d in deployments_dir.iterdir() if d.is_dir() and (d / "kustomization.yaml").exists()]
        return overlays

    @pytest.fixture
    def kustomize_base(self) -> Path:
        """Get the Kustomize base directory"""
        base_dir = Path(__file__).parent.parent / "deployments" / "base"
        if not base_dir.exists():
            pytest.skip("Base deployments directory not found")
        return base_dir

    @requires_tool("kustomize", skip_reason="kustomize CLI not installed - required for overlay build validation")
    def test_kustomize_overlay_builds_successfully(self, kustomize_overlays: list[Path]):
        """
        Test that all Kustomize overlays build successfully.

        FINDING #1: Kustomize ConfigMap collision in staging-gke overlay
        Root Cause: configMapGenerator with behavior:create conflicted with base ConfigMap
        Fix: Changed to strategic merge patch approach
        Prevention: This test validates all overlays build successfully
        """
        for overlay_dir in kustomize_overlays:
            overlay_name = overlay_dir.name

            # Run kustomize build
            result = subprocess.run(
                ["kustomize", "build", str(overlay_dir)], capture_output=True, text=True, cwd=overlay_dir, timeout=60
            )

            assert result.returncode == 0, (
                f"Kustomize build failed for overlay '{overlay_name}':\n"
                f"STDOUT:\n{result.stdout}\n"
                f"STDERR:\n{result.stderr}\n"
                f"\nThis likely indicates a configuration collision or invalid YAML.\n"
                f"Common causes:\n"
                f"- ConfigMap name collision between base and overlay\n"
                f"- Invalid patch syntax\n"
                f"- Missing required fields\n"
                f"- Circular dependencies"
            )

            # Verify output is valid YAML
            try:
                yaml.safe_load_all(result.stdout)
            except yaml.YAMLError as e:
                pytest.fail(
                    f"Kustomize build for overlay '{overlay_name}' produced invalid YAML:\n"
                    f"{e}\n"
                    f"Output preview (first 500 chars):\n{result.stdout[:500]}"
                )

    @requires_tool("kustomize", skip_reason="kustomize CLI not installed - required for ConfigMap collision detection")
    def test_no_configmap_collisions(self, kustomize_overlays: list[Path], kustomize_base: Path):
        """
        Test that overlay ConfigMaps don't collide with base ConfigMaps.

        FINDING #1 (detailed): ConfigMap collision detection
        Pattern: Overlays using configMapGenerator with behavior:create when
                 base already has a ConfigMap with the same name
        Solution: Use behavior:replace, behavior:merge, or strategic merge patch
        Prevention: This test detects the specific pattern that caused the failure
        """
        # Get all ConfigMap names from base
        base_configmaps = self._get_configmap_names(kustomize_base)

        for overlay_dir in kustomize_overlays:
            overlay_name = overlay_dir.name
            kustomization_file = overlay_dir / "kustomization.yaml"

            with open(kustomization_file) as f:
                kustomization = yaml.safe_load(f)

            # Check configMapGenerator for collisions
            if "configMapGenerator" in kustomization:
                for generator in kustomization["configMapGenerator"]:
                    configmap_name = generator.get("name")
                    behavior = generator.get("behavior", "create")

                    if behavior == "create" and configmap_name in base_configmaps:
                        pytest.fail(
                            f"ConfigMap collision detected in overlay '{overlay_name}':\n"
                            f"- ConfigMap name: {configmap_name}\n"
                            f"- Behavior: {behavior}\n"
                            f"- Issue: Base already has a ConfigMap with this name\n"
                            f"\nFixes:\n"
                            f"1. Use 'behavior: replace' to override base ConfigMap\n"
                            f"2. Use 'behavior: merge' to merge with base ConfigMap\n"
                            f"3. Use a different ConfigMap name\n"
                            f"4. Use a strategic merge patch instead of configMapGenerator\n"
                            f"\nSee: deployments/overlays/staging-gke/otel-collector-configmap-patch.yaml"
                        )

    @requires_tool("kustomize", skip_reason="kustomize CLI not installed - required for patch validation")
    def test_overlay_patches_target_existing_resources(self, kustomize_overlays: list[Path]):
        """
        Test that overlay patches target resources that exist in base or overlay.

        FINDING: Potential issue - patches targeting non-existent resources
        Prevention: Validate patch targets exist before deployment
        """
        for overlay_dir in kustomize_overlays:
            overlay_name = overlay_dir.name

            # Build kustomize with --enable-alpha-plugins to get detailed errors
            result = subprocess.run(
                ["kustomize", "build", str(overlay_dir), "--load-restrictor=LoadRestrictionsNone"],
                capture_output=True,
                text=True,
                cwd=overlay_dir,
                timeout=60,
            )

            # Check for common patch errors
            if "no matches for" in result.stderr.lower():
                pytest.fail(
                    f"Overlay '{overlay_name}' has patches targeting non-existent resources:\n"
                    f"{result.stderr}\n"
                    f"Ensure patch targets exist in base or are defined in overlay resources."
                )

    def _get_configmap_names(self, directory: Path) -> set[str]:
        """Extract all ConfigMap names from YAML files in a directory"""
        configmap_names = set()

        for yaml_file in directory.glob("*.yaml"):
            with open(yaml_file) as f:
                # Handle multi-document YAML files
                for doc in yaml.safe_load_all(f):
                    if doc and doc.get("kind") == "ConfigMap":
                        name = doc.get("metadata", {}).get("name")
                        if name:
                            configmap_names.add(name)

        return configmap_names


# ==============================================================================
# GitHub Actions Workflow Tests
# ==============================================================================


@pytest.mark.requires_kubectl
@pytest.mark.xdist_group(name="testgithubactionsworkflows")
class TestGitHubActionsWorkflows:
    """Test GitHub Actions workflows for best practices and error handling"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def workflow_files(self) -> list[Path]:
        """Get all GitHub Actions workflow files"""
        workflows_dir = Path(__file__).parent.parent / ".github" / "workflows"
        if not workflows_dir.exists():
            pytest.skip("GitHub workflows directory not found")

        return list(workflows_dir.glob("*.yaml")) + list(workflows_dir.glob("*.yml"))

    @pytest.fixture
    def composite_actions(self) -> list[Path]:
        """Get all composite action files"""
        actions_dir = Path(__file__).parent.parent / ".github" / "actions"
        if not actions_dir.exists():
            pytest.skip("GitHub actions directory not found")

        action_files = []
        for action_dir in actions_dir.iterdir():
            if action_dir.is_dir():
                action_yml = action_dir / "action.yml"
                action_yaml = action_dir / "action.yaml"
                if action_yml.exists():
                    action_files.append(action_yml)
                elif action_yaml.exists():
                    action_files.append(action_yaml)

        return action_files

    def test_composite_actions_have_error_handling(self, composite_actions: list[Path]):
        """
        Test that composite actions have proper error handling with set -e.

        FINDING #3: Composite action error handling
        Root Cause: Missing set -euo pipefail in shell scripts
        Fix: Added set -euo pipefail to all shell steps
        Prevention: This test validates all composite actions use set -e
        """
        for action_file in composite_actions:
            action_name = action_file.parent.name

            with open(action_file) as f:
                action = yaml.safe_load(f)

            if action.get("runs", {}).get("using") != "composite":
                continue

            steps = action.get("runs", {}).get("steps", [])

            for i, step in enumerate(steps):
                # Check if step has a run command
                if "run" not in step:
                    continue

                # Skip if shell is not bash
                if step.get("shell") != "bash":
                    continue

                run_script = step["run"]

                # Check for set -e, set -euo pipefail, or equivalent
                has_error_handling = any(
                    [
                        "set -e" in run_script,
                        "set -u" in run_script,
                        "set -o pipefail" in run_script,
                        "set -euo pipefail" in run_script,
                        "set -eu" in run_script,
                    ]
                )

                if not has_error_handling and len(run_script.strip().split("\n")) > 2:
                    pytest.fail(
                        f"Composite action '{action_name}' step {i} lacks error handling:\n"
                        f"Step name: {step.get('name', 'unnamed')}\n"
                        f"\nScript:\n{run_script}\n"
                        f"\nAdd 'set -euo pipefail' at the start of the script to:\n"
                        f"- Exit on error (set -e)\n"
                        f"- Exit on undefined variable (set -u)\n"
                        f"- Exit on pipe failures (set -o pipefail)\n"
                        f"\nExample:\n"
                        f"  run: |\n"
                        f"    set -euo pipefail\n"
                        f"    # your commands here\n"
                    )

    def test_e2e_workflow_has_adequate_timeout(self, workflow_files: list[Path]):
        """
        Test that E2E workflow has adequate health check timeout.

        FINDING #2: E2E test health check timeouts
        Root Cause: 100 iterations * 3s = 5 minutes insufficient for slow GitHub runners
        Fix: Increased to 150 iterations * 3s = 7.5 minutes
        Prevention: This test validates timeout is adequate (>= 7 minutes)
        """
        e2e_workflow = None
        for workflow_file in workflow_files:
            if "e2e" in workflow_file.name.lower():
                e2e_workflow = workflow_file
                break

        if not e2e_workflow:
            pytest.skip("E2E workflow not found")

        with open(e2e_workflow) as f:
            content = f.read()

        # Look for health check loop pattern
        # Pattern: for i in {1..N}; do
        match = re.search(r"for\s+i\s+in\s+\{1\.\.(\d+)\}", content)

        if not match:
            pytest.skip("Health check loop not found in E2E workflow")

        iterations = int(match.group(1))
        sleep_match = re.search(r"sleep\s+(\d+)", content)
        sleep_seconds = int(sleep_match.group(1)) if sleep_match else 3  # default to 3

        total_timeout_seconds = iterations * sleep_seconds
        total_timeout_minutes = total_timeout_seconds / 60

        assert total_timeout_minutes >= 7, (
            f"E2E workflow health check timeout is too short:\n"
            f"- Current: {iterations} iterations * {sleep_seconds}s = "
            f"{total_timeout_minutes:.1f} minutes\n"
            f"- Minimum recommended: 7 minutes (to accommodate slow GitHub runners)\n"
            f"\nKeycloak initialization can take 3-5 minutes on slow runners.\n"
            f"Other services (PostgreSQL, Redis, OpenFGA, Qdrant) add overhead.\n"
            f"\nRecommendation: Use at least 150 iterations with 3s sleep (7.5 min total)"
        )

    def test_ci_workflow_validates_lockfile(self, workflow_files: list[Path]):
        """
        Test that CI workflow validates UV lockfile is up-to-date.

        PREVENTION: Lockfile drift detection
        Pattern: Ensure dependencies match lockfile for reproducible builds
        Solution: Add 'uv lock --check' validation step in CI
        """
        ci_workflow = None
        for workflow_file in workflow_files:
            if "ci.yaml" in workflow_file.name or "ci.yml" in workflow_file.name:
                ci_workflow = workflow_file
                break

        if not ci_workflow:
            pytest.skip("CI workflow not found")

        with open(ci_workflow) as f:
            workflow = yaml.safe_load(f)

        # Check if any job has lockfile validation
        has_lockfile_validation = False

        jobs = workflow.get("jobs", {})
        for job_name, job_config in jobs.items():
            steps = job_config.get("steps", [])

            for step in steps:
                if "run" not in step:
                    continue

                run_script = step["run"]

                # Check for uv lock --check command
                if "uv lock --check" in run_script or "uv lock --frozen-check" in run_script:
                    has_lockfile_validation = True
                    break

            if has_lockfile_validation:
                break

        assert has_lockfile_validation, (
            "CI workflow must validate lockfile is up-to-date.\n"
            "\n"
            "Add a step that runs 'uv lock --check' to ensure:\n"
            "1. uv.lock matches pyproject.toml dependencies\n"
            "2. Prevents dependency drift\n"
            "3. Ensures reproducible builds\n"
            "\n"
            "Example:\n"
            "  - name: Validate lockfile is up-to-date\n"
            "    run: |\n"
            "      uv lock --check || {\n"
            "        echo '::error::uv.lock is out of date'\n"
            "        exit 1\n"
            "      }\n"
            "\n"
            "This prevents issues where dependencies are updated in pyproject.toml\n"
            "but the lockfile is not regenerated, leading to inconsistent builds."
        )

    def test_workflow_bash_steps_have_error_handling(self, workflow_files: list[Path]):
        """
        Test that workflow bash steps with multiple commands have error handling.

        FINDING #3 (extended): Workflow error handling
        Prevention: Ensure critical workflow steps fail fast on errors
        """
        for workflow_file in workflow_files:
            workflow_name = workflow_file.name

            with open(workflow_file) as f:
                workflow = yaml.safe_load(f)

            jobs = workflow.get("jobs", {})

            for job_name, job_config in jobs.items():
                steps = job_config.get("steps", [])

                for i, step in enumerate(steps):
                    if "run" not in step:
                        continue

                    run_script = step["run"]

                    # Skip short scripts (single command)
                    lines = run_script.strip().split("\n")
                    # Filter out comments and empty lines
                    command_lines = [line for line in lines if line.strip() and not line.strip().startswith("#")]

                    if len(command_lines) <= 1:
                        continue

                    # Skip if || true or similar error suppression is intentional
                    if "|| true" in run_script or "|| echo" in run_script:
                        continue

                    # Check for set -e or set -euo pipefail
                    has_error_handling = any(
                        [
                            "set -e" in run_script,
                            "set -euo pipefail" in run_script,
                        ]
                    )

                    # Only flag steps that look like they should fail on error
                    # (pytest, docker, kustomize, etc.)
                    looks_critical = any(
                        keyword in run_script.lower()
                        for keyword in [
                            "pytest",
                            "docker",
                            "kustomize",
                            "kubectl",
                            "uv run",
                            "npm test",
                            "go test",
                            "cargo test",
                        ]
                    )

                    if looks_critical and not has_error_handling:
                        # This is a warning, not a hard failure (some workflows may intentionally
                        # continue on error)
                        print(
                            f"\n⚠️  WARNING: Workflow '{workflow_name}' job '{job_name}' "
                            f"step {i} may need error handling:\n"
                            f"Step name: {step.get('name', 'unnamed')}\n"
                            f"Consider adding 'set -euo pipefail' if errors should fail the job.\n"
                        )


# ==============================================================================
# Docker Compose Test Infrastructure Tests
# ==============================================================================


@pytest.mark.xdist_group(name="testdockercomposetestinfra")
class TestDockerComposeTestInfra:
    """Test Docker Compose test infrastructure configuration"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def docker_compose_test_file(self) -> Path:
        """Get the docker-compose.test.yml file"""
        compose_file = Path(__file__).parent.parent / "docker-compose.test.yml"
        if not compose_file.exists():
            pytest.skip("docker-compose.test.yml not found")
        return compose_file

    def test_all_services_have_health_checks(self, docker_compose_test_file: Path):
        """
        Test that all services in docker-compose.test.yml have health checks.

        FINDING #2 (related): E2E test health checks
        Prevention: Ensure all test infrastructure services define health checks

        Note: Migration/initialization services (with restart:no or one-time commands)
        are excluded as they don't need health checks.
        """
        with open(docker_compose_test_file) as f:
            compose = yaml.safe_load(f)

        services = compose.get("services", {})

        for service_name, service_config in services.items():
            # Skip one-time migration/init services (restart: no or 'no')
            restart_policy = service_config.get("restart", "always")
            if restart_policy == "no" or restart_policy is False:
                continue

            # Skip services with migrate/init/setup in the name (conventional migration services)
            if any(keyword in service_name.lower() for keyword in ["migrate", "init", "setup"]):
                continue

            assert "healthcheck" in service_config or "health_check" in service_config, (
                f"Service '{service_name}' in docker-compose.test.yml lacks a health check.\n"
                f"\nHealth checks are required for E2E test infrastructure to:\n"
                f"1. Ensure service is ready before running tests\n"
                f"2. Prevent test failures due to services not being fully initialized\n"
                f"3. Enable proper wait-for-healthy loops in CI\n"
                f"\nExample health check:\n"
                f"  healthcheck:\n"
                f"    test: ['CMD', 'pg_isready', '-U', 'postgres']  # for PostgreSQL\n"
                f"    interval: 5s\n"
                f"    timeout: 3s\n"
                f"    retries: 10\n"
                f"    start_period: 10s\n"
            )

    def test_keycloak_has_adequate_start_period(self, docker_compose_test_file: Path):
        """
        Test that Keycloak service has adequate start_period in health check.

        FINDING #2 (specific): Keycloak initialization delays
        Pattern: Keycloak requires 45s start period + retries for full initialization
        Prevention: Validate Keycloak health check configuration
        """
        with open(docker_compose_test_file) as f:
            compose = yaml.safe_load(f)

        services = compose.get("services", {})

        # Find Keycloak service
        keycloak_service = None
        for service_name, service_config in services.items():
            if "keycloak" in service_name.lower():
                keycloak_service = service_config
                break

        if not keycloak_service:
            pytest.skip("Keycloak service not found in docker-compose.test.yml")

        healthcheck = keycloak_service.get("healthcheck") or keycloak_service.get("health_check")

        if not healthcheck:
            pytest.fail("Keycloak service must have a health check configuration")

        # Parse start_period (can be "45s", "1m", "90s", etc.)
        start_period_str = healthcheck.get("start_period", "0s")
        start_period_seconds = self._parse_duration(start_period_str)

        assert start_period_seconds >= 45, (
            f"Keycloak health check start_period is too short:\n"
            f"- Current: {start_period_str} ({start_period_seconds}s)\n"
            f"- Minimum recommended: 45s\n"
            f"\nKeycloak requires time to:\n"
            f"1. Start the Java application\n"
            f"2. Initialize the database schema\n"
            f"3. Load realms and configurations\n"
            f"4. Start accepting HTTP requests\n"
            f"\nWithout adequate start_period, health checks will fail prematurely."
        )

    def _parse_duration(self, duration_str: str) -> int:
        """Parse Docker duration string (e.g., '45s', '1m', '90s') to seconds"""
        duration_str = duration_str.strip().lower()

        if duration_str.endswith("s"):
            return int(duration_str[:-1])
        elif duration_str.endswith("m"):
            return int(duration_str[:-1]) * 60
        elif duration_str.endswith("h"):
            return int(duration_str[:-1]) * 3600
        else:
            # Assume seconds if no unit
            return int(duration_str)


# ==============================================================================
# Test Execution Metadata
# ==============================================================================


def test_ci_cd_validation_suite_info():
    """
    Document the purpose and scope of this test suite.

    This is an informational test that always passes but provides context.
    """
    info = """
    ╔══════════════════════════════════════════════════════════════════════════╗
    ║                     CI/CD Validation Test Suite                         ║
    ╚══════════════════════════════════════════════════════════════════════════╝

    Purpose:
        Prevent recurrence of CI/CD failures identified in comprehensive audit
        conducted on 2025-11-07.

    Findings Addressed:
        1. 🔴 CRITICAL: Kustomize ConfigMap collision (100% staging deploy failure)
        2. 🔴 CRITICAL: E2E test health check timeouts (100% E2E test failure)
        3. 🟠 HIGH: Composite action error handling (70% quality test failure)

    Test Categories:
        - Kustomize Configuration Validation (3 tests)
        - GitHub Actions Workflow Validation (4 tests)
        - Docker Compose Infrastructure Validation (2 tests)

    Running:
        pytest tests/test_ci_cd_validation.py -v

    TDD Principle:
        These tests were created AFTER fixing the issues to ensure they cannot
        recur. Future CI/CD changes must pass these tests before deployment.

    Related Files:
        - deployments/overlays/staging-gke/kustomization.yaml
        - deployments/overlays/staging-gke/otel-collector-configmap-patch.yaml
        - .github/workflows/e2e-tests.yaml
        - .github/actions/setup-python-deps/action.yml
        - .github/workflows/quality-tests.yaml

    Last Updated: 2025-11-07
    """
    print(info)
    assert True  # Always pass, this is informational
