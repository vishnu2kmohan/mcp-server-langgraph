"""
Regression Tests for Pod Deployment Issues

These tests prevent recurrence of production pod crashes by validating:
1. GKE Autopilot resource ratio compliance
2. Environment variable configuration validity
3. ReadOnlyRootFilesystem volume mount completeness
4. OTEL Collector configuration syntax

Related Issues:
- Keycloak CrashLoopBackOff due to readOnlyRootFilesystem (2025-11-12)
- OTEL Collector GKE Autopilot ratio violation (2025-11-12)
- OTEL Collector config syntax errors (2025-11-12)

Test Execution:
    pytest tests/regression/test_pod_deployment_regression.py -v
"""

import gc
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

from tests.fixtures.tool_fixtures import requires_tool

pytestmark = pytest.mark.integration


# Test configuration - Environment-agnostic path resolution
def _find_project_root() -> Path:
    """
    Find project root by searching for markers (.git, pyproject.toml).

    This works in any environment:
    - Local development (from source directory)
    - Docker containers (from /app)
    - CI/CD environments
    """
    current = Path(__file__).resolve().parent
    markers = [".git", "pyproject.toml", "setup.py"]

    while current != current.parent:
        if any((current / marker).exists() for marker in markers):
            return current
        current = current.parent

    raise RuntimeError("Cannot find project root - no .git or pyproject.toml found")


REPO_ROOT = _find_project_root()
OVERLAYS_DIR = REPO_ROOT / "deployments" / "overlays"


def get_all_overlays() -> list[Path]:
    """
    Get all kustomize overlay directories.

    Returns empty list if overlays directory doesn't exist (e.g., in minimal Docker builds).
    This allows tests to be skipped gracefully instead of failing at collection time.
    """
    if not OVERLAYS_DIR.exists():
        return []
    return [d for d in OVERLAYS_DIR.iterdir() if d.is_dir() and (d / "kustomization.yaml").exists()]


@requires_tool("kubectl")
def build_kustomize(overlay_path: Path) -> list[dict[str, Any]]:
    """Build kustomize overlay and return parsed manifests"""
    result = subprocess.run(
        ["kubectl", "kustomize", str(overlay_path)], capture_output=True, text=True, check=True, timeout=60
    )
    manifests = list(yaml.safe_load_all(result.stdout))
    return [m for m in manifests if m is not None]


def parse_cpu(cpu_str: str) -> float:
    """Parse CPU string to millicores"""
    if not cpu_str:
        return 0.0
    if cpu_str.endswith("m"):
        return float(cpu_str[:-1])
    return float(cpu_str) * 1000


def parse_memory(mem_str: str) -> float:
    """Parse memory string to MiB"""
    if not mem_str:
        return 0.0

    units = {
        "Ki": 1 / 1024,
        "Mi": 1,
        "Gi": 1024,
        "Ti": 1024 * 1024,
        "K": 1 / 1024,
        "M": 1,
        "G": 1024,
        "T": 1024 * 1024,
    }

    for unit, multiplier in units.items():
        if mem_str.endswith(unit):
            return float(mem_str[: -len(unit)]) * multiplier

    return float(mem_str) / (1024 * 1024)


def get_deployments_from_manifests(manifests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter deployment-like resources from manifests"""
    return [m for m in manifests if m.get("kind") in ["Deployment", "StatefulSet", "DaemonSet"]]


def get_containers_from_deployment(deployment: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract containers from deployment manifest"""
    return deployment.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])


@pytest.mark.xdist_group(name="testgkeautopilotcompliance")
class TestGKEAutopilotCompliance:
    """Tests for GKE Autopilot LimitRange compliance"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.parametrize("overlay", get_all_overlays(), ids=lambda x: x.name)
    def test_cpu_limit_request_ratio(self, overlay: Path):
        """
        Regression test for: OTEL Collector CPU ratio violation

        GKE Autopilot enforces max CPU limit/request ratio of 4.0.
        This test prevents deployments that exceed this ratio.

        Related: OTEL Collector crash (2025-11-12)
        Error: "cpu max limit to request ratio per Container is 4, but provided ratio is 5.000000"
        """
        MAX_RATIO = 4.0
        manifests = build_kustomize(overlay)
        deployments = get_deployments_from_manifests(manifests)

        for deployment in deployments:
            deployment_name = deployment["metadata"]["name"]
            containers = get_containers_from_deployment(deployment)

            for container in containers:
                container_name = container["name"]
                resources = container.get("resources", {})
                requests = resources.get("requests", {})
                limits = resources.get("limits", {})

                cpu_request = requests.get("cpu")
                cpu_limit = limits.get("cpu")

                # Skip if no CPU resources specified
                if not cpu_request or not cpu_limit:
                    continue

                req_cpu = parse_cpu(cpu_request)
                lim_cpu = parse_cpu(cpu_limit)
                ratio = lim_cpu / req_cpu

                assert ratio <= MAX_RATIO, (
                    f"{deployment_name}/{container_name} in {overlay.name}: "
                    f"CPU ratio {ratio:.2f} exceeds GKE Autopilot max {MAX_RATIO} "
                    f"(request: {cpu_request}, limit: {cpu_limit})"
                )

    @pytest.mark.parametrize("overlay", get_all_overlays(), ids=lambda x: x.name)
    def test_memory_limit_request_ratio(self, overlay: Path):
        """GKE Autopilot enforces max memory limit/request ratio of 4.0"""
        MAX_RATIO = 4.0
        manifests = build_kustomize(overlay)
        deployments = get_deployments_from_manifests(manifests)

        for deployment in deployments:
            deployment_name = deployment["metadata"]["name"]
            containers = get_containers_from_deployment(deployment)

            for container in containers:
                container_name = container["name"]
                resources = container.get("resources", {})
                requests = resources.get("requests", {})
                limits = resources.get("limits", {})

                mem_request = requests.get("memory")
                mem_limit = limits.get("memory")

                if not mem_request or not mem_limit:
                    continue

                req_mem = parse_memory(mem_request)
                lim_mem = parse_memory(mem_limit)
                ratio = lim_mem / req_mem

                assert ratio <= MAX_RATIO, (
                    f"{deployment_name}/{container_name} in {overlay.name}: "
                    f"Memory ratio {ratio:.2f} exceeds GKE Autopilot max {MAX_RATIO}"
                )


@pytest.mark.xdist_group(name="testenvironmentvariableconfiguration")
class TestEnvironmentVariableConfiguration:
    """Tests for environment variable configuration validity"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.parametrize("overlay", get_all_overlays(), ids=lambda x: x.name)
    def test_no_conflicting_env_sources(self, overlay: Path):
        """
        Regression test for: mcp-server-langgraph env var validation errors

        Kubernetes does not allow env vars to have both 'value' and 'valueFrom'.
        This test prevents such configurations from being deployed.

        Related: mcp-server-langgraph deployment error (2025-11-12)
        Error: "may not have more than one field specified at a time"
        """
        manifests = build_kustomize(overlay)
        deployments = get_deployments_from_manifests(manifests)

        for deployment in deployments:
            deployment_name = deployment["metadata"]["name"]
            containers = get_containers_from_deployment(deployment)

            for container in containers:
                container_name = container["name"]
                env_vars = container.get("env", [])

                for env in env_vars:
                    env_name = env.get("name", "unknown")
                    has_value = "value" in env
                    has_value_from = "valueFrom" in env

                    assert not (has_value and has_value_from), (
                        f"{deployment_name}/{container_name}/{env_name} in {overlay.name}: "
                        f"Env var has both 'value' and 'valueFrom' specified"
                    )

    @pytest.mark.parametrize("overlay", get_all_overlays(), ids=lambda x: x.name)
    def test_valuefrom_has_single_source(self, overlay: Path):
        """Env vars with valueFrom must have exactly one source (configMapKeyRef, secretKeyRef, etc.)"""
        manifests = build_kustomize(overlay)
        deployments = get_deployments_from_manifests(manifests)

        for deployment in deployments:
            deployment_name = deployment["metadata"]["name"]
            containers = get_containers_from_deployment(deployment)

            for container in containers:
                container_name = container["name"]
                env_vars = container.get("env", [])

                for env in env_vars:
                    env_name = env.get("name", "unknown")
                    value_from = env.get("valueFrom")

                    if not value_from:
                        continue

                    # Count non-optional keys in valueFrom
                    sources = [k for k in value_from.keys() if k != "optional"]

                    assert len(sources) == 1, (
                        f"{deployment_name}/{container_name}/{env_name} in {overlay.name}: "
                        f"valueFrom must have exactly one source, found: {sources}"
                    )


@pytest.mark.xdist_group(name="testreadonlyrootfilesystem")
class TestReadOnlyRootFilesystem:
    """Tests for readOnlyRootFilesystem configuration"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.parametrize("overlay", get_all_overlays(), ids=lambda x: x.name)
    def test_readonly_fs_has_tmp_mount(self, overlay: Path):
        """
        Regression test for: Keycloak readOnlyRootFilesystem crashes

        When readOnlyRootFilesystem is true, containers must have
        appropriate writable volume mounts (at minimum /tmp).

        Related: Keycloak CrashLoopBackOff (2025-11-12)
        Error: "java.nio.file.ReadOnlyFileSystemException"
        """
        manifests = build_kustomize(overlay)
        deployments = get_deployments_from_manifests(manifests)

        for deployment in deployments:
            deployment_name = deployment["metadata"]["name"]
            containers = get_containers_from_deployment(deployment)

            for container in containers:
                container_name = container["name"]
                security_context = container.get("securityContext", {})
                readonly_fs = security_context.get("readOnlyRootFilesystem", False)

                if not readonly_fs:
                    continue

                volume_mounts = container.get("volumeMounts", [])
                mount_paths = {vm["mountPath"] for vm in volume_mounts}

                # At minimum, /tmp should be mounted
                assert "/tmp" in mount_paths, (
                    f"{deployment_name}/{container_name} in {overlay.name}: "
                    f"readOnlyRootFilesystem is true but /tmp is not mounted"
                )


@pytest.mark.xdist_group(name="testotelcollectorconfiguration")
class TestOTELCollectorConfiguration:
    """Tests for OTEL Collector configuration validity"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_otel_collector_config_syntax(self):
        """
        Regression test for: OTEL Collector configuration syntax errors

        Validates that OTEL Collector configuration does not contain
        invalid syntax or deprecated configuration keys.

        Related: OTEL Collector CrashLoopBackOff (2025-11-12)
        Error: "invalid uri: SERVICE_VERSION:-unknown"
        Error: "invalid keys: retry_on_failure, use_insecure"
        """
        # Find OTEL Collector config files
        config_files = list(REPO_ROOT.glob("**/otel-collector-config*.yaml"))

        for config_file in config_files:
            with open(config_file) as f:
                content = f.read()

            # Check for bash-style env var syntax (should use ${env:VAR} instead)
            assert ":-" not in content, (
                f"{config_file}: Contains bash-style env var syntax ':-'. " "Use static values or ${{env:VAR}} syntax instead."
            )

            # Check for deprecated googlecloud exporter keys
            if "googlecloud:" in content:
                # These keys are deprecated/invalid in newer versions
                assert (
                    "use_insecure:" not in content
                ), f"{config_file}: Contains deprecated 'use_insecure' key in googlecloud exporter"
                assert (
                    "retry_on_failure:" not in content
                ), f"{config_file}: Contains deprecated 'retry_on_failure' key in googlecloud exporter"


@pytest.mark.requires_kubectl
@pytest.mark.xdist_group(name="testkustomizebuildvalidity")
class TestKustomizeBuildValidity:
    """Tests that kustomize builds are valid"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.parametrize("overlay", get_all_overlays(), ids=lambda x: x.name)
    @requires_tool("kubectl")
    def test_kustomize_builds_successfully(self, overlay: Path):
        """Kustomize build must succeed without errors"""
        result = subprocess.run(["kubectl", "kustomize", str(overlay)], capture_output=True, text=True, timeout=60)

        assert result.returncode == 0, f"Kustomize build failed for {overlay.name}:\n{result.stderr}"

    @pytest.mark.parametrize("overlay", get_all_overlays(), ids=lambda x: x.name)
    @requires_tool("kubectl")
    def test_manifests_pass_dry_run(self, overlay: Path):
        """
        Manifests must pass kubectl dry-run validation

        This catches errors that would prevent deployment, such as:
        - Invalid field values
        - Missing required fields
        - Schema violations
        """
        result = subprocess.run(["kubectl", "kustomize", str(overlay)], capture_output=True, text=True, timeout=60)

        if result.returncode != 0:
            pytest.skip(f"Kustomize build failed for {overlay.name}")

        # Apply with dry-run to validate
        dry_run_result = subprocess.run(
            ["kubectl", "apply", "--dry-run=client", "-f", "-"],
            input=result.stdout,
            capture_output=True,
            text=True,
            timeout=60,
        )

        # Allow errors for missing cluster resources (namespaces, CRDs, etc.)
        # but fail on validation errors
        if dry_run_result.returncode != 0:
            error_output = dry_run_result.stderr.lower()

            # Skip if Kubernetes cluster is unavailable (CI environment without cluster)
            connection_errors = ["connection refused", "failed to download openapi", "unable to connect"]
            if any(err in error_output for err in connection_errors):
                pytest.skip("Kubernetes cluster not available for dry-run validation (CI environment)")

            error_lines = dry_run_result.stderr.split("\n")
            validation_errors = [line for line in error_lines if "invalid" in line.lower() or "error" in line.lower()]

            # Filter out acceptable errors
            real_errors = [
                err
                for err in validation_errors
                if "the server doesn't have a resource type" not in err.lower() and "namespace" not in err.lower()
            ]

            assert not real_errors, f"Dry-run validation failed for {overlay.name}:\n" + "\n".join(real_errors)


@pytest.mark.integration
@pytest.mark.xdist_group(name="testpodstartupintegration")
class TestPodStartupIntegration:
    """
    Integration tests for pod startup (requires cluster access)

    These tests are marked with @pytest.mark.integration and should be run
    in a test environment before deploying to staging/production.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_keycloak_pods_start_without_crash(self):
        """
        Integration test: Verify Keycloak pods start successfully

        This test should be run in a test cluster before deploying changes.
        """
        pytest.skip("Integration test - requires cluster access")

    def test_otel_collector_pods_start_without_crash(self):
        """
        Integration test: Verify OTEL Collector pods start successfully

        This test should be run in a test cluster before deploying changes.
        """
        pytest.skip("Integration test - requires cluster access")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
