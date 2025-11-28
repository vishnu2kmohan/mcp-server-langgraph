"""
Test suite for validating Kubernetes manifest builds using Kustomize.

This test suite validates that:
1. All Kustomize overlays build successfully without errors
2. Generated manifests contain valid YAML
3. Critical resources are present in the built manifests
4. No placeholder/unsubstituted variables remain in critical fields

Following TDD principles - these tests should FAIL before fixes are applied.
"""

import gc
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from tests.fixtures.tool_fixtures import requires_tool

# Mark as unit test to ensure it runs in CI
# Note: usefixtures is included here (not at module end) to avoid pytestmark redefinition
pytestmark = [pytest.mark.unit, pytest.mark.validation, pytest.mark.usefixtures("check_kustomize_installed")]

# Define paths to all Kustomize overlays
REPO_ROOT = Path(__file__).parent.parent.parent
OVERLAYS = [
    "deployments/base",
    "deployments/overlays/staging-gke",
    "deployments/overlays/production-gke",
    "deployments/argocd/base",
]


@pytest.mark.requires_kustomize
@pytest.mark.xdist_group(name="testkustomizebuilds")
class TestKustomizeBuilds:
    """Test that all Kustomize overlays build successfully.

    CODEX FINDING #1: These tests require kustomize CLI tool.
    Tests will skip gracefully if kustomize is not installed.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.parametrize("overlay_path", OVERLAYS)
    @requires_tool("kustomize")
    def test_overlay_builds_without_errors(self, overlay_path):
        """
        Test that kustomize build completes without errors.

        This will catch:
        - YAML syntax errors
        - Missing resource references
        - Invalid patch targets
        - Namespace definition issues
        """
        # CODEX FINDING #1: Check if kustomize is available
        if not shutil.which("kustomize"):
            pytest.skip(
                "kustomize CLI not installed. Install with:\n"
                "  curl -s https://raw.githubusercontent.com/kubernetes-sigs/kustomize/master/hack/install_kustomize.sh | bash"
            )

        full_path = REPO_ROOT / overlay_path

        # Run kustomize build
        result = subprocess.run(
            ["kustomize", "build", str(full_path)], capture_output=True, text=True, cwd=REPO_ROOT, timeout=60
        )

        # Assert build succeeded
        assert result.returncode == 0, (
            f"Kustomize build failed for {overlay_path}\n" f"STDOUT: {result.stdout}\n" f"STDERR: {result.stderr}"
        )

        # Assert output is not empty
        assert result.stdout.strip(), f"Kustomize build produced no output for {overlay_path}"

    @pytest.mark.parametrize("overlay_path", OVERLAYS)
    @requires_tool("kustomize")
    def test_built_manifests_are_valid_yaml(self, overlay_path):
        """
        Test that built manifests parse as valid YAML.

        This will catch:
        - YAML syntax errors
        - Invalid character sequences
        - Malformed documents
        """
        # CODEX FINDING #1: Check if kustomize is available
        if not shutil.which("kustomize"):
            pytest.skip(
                "kustomize CLI not installed. Install with:\n"
                "  curl -s https://raw.githubusercontent.com/kubernetes-sigs/kustomize/master/hack/install_kustomize.sh | bash"
            )

        full_path = REPO_ROOT / overlay_path

        # Build the overlay
        result = subprocess.run(
            ["kustomize", "build", str(full_path)], capture_output=True, text=True, cwd=REPO_ROOT, timeout=60
        )

        # Skip if build failed (covered by other test)
        if result.returncode != 0:
            pytest.skip(f"Build failed for {overlay_path}, skipping YAML validation")

        # Parse all YAML documents
        try:
            documents = list(yaml.safe_load_all(result.stdout))
            assert len(documents) > 0, f"No YAML documents found in {overlay_path}"

            # Verify each document is a dict (valid K8s manifest)
            for i, doc in enumerate(documents):
                if doc is None:  # Empty document separator
                    continue
                assert isinstance(doc, dict), f"Document {i} in {overlay_path} is not a valid Kubernetes manifest"
                assert "apiVersion" in doc, f"Document {i} missing apiVersion in {overlay_path}"
                assert "kind" in doc, f"Document {i} missing kind in {overlay_path}"

        except yaml.YAMLError as e:
            pytest.fail(f"Invalid YAML in {overlay_path}: {e}")


@pytest.mark.xdist_group(name="teststaginggkeoverlay")
class TestStagingGKEOverlay:
    """Specific tests for staging-gke overlay configuration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @requires_tool("kustomize")
    def _build_overlay(self):
        """Helper to build staging overlay."""
        overlay_path = REPO_ROOT / "deployments/overlays/staging-gke"
        result = subprocess.run(
            ["kustomize", "build", str(overlay_path)], capture_output=True, text=True, cwd=REPO_ROOT, timeout=60
        )
        if result.returncode != 0:
            pytest.skip(f"Build failed: {result.stderr}")
        return list(yaml.safe_load_all(result.stdout))

    def test_namespace_consistency_for_staging_matches_expected_namespace(self):
        """
        Test that all resources use the correct namespace.

        Expected: staging-mcp-server-langgraph
        Common mistake: mcp-staging (hardcoded)

        Validates Finding #4: Service Account namespace mismatches
        """
        documents = self._build_overlay()
        expected_namespace = "staging-mcp-server-langgraph"

        for doc in documents:
            if doc is None or not isinstance(doc, dict):
                continue

            # Check metadata.namespace
            if "metadata" in doc and "namespace" in doc["metadata"]:
                actual_ns = doc["metadata"]["namespace"]

                # Allow system namespaces
                if actual_ns in ["kube-system", "istio-system", "cert-manager"]:
                    continue

                assert actual_ns == expected_namespace, (
                    f"{doc['kind']}/{doc['metadata'].get('name', 'unknown')} "
                    f"has wrong namespace: {actual_ns} (expected {expected_namespace})"
                )

    def test_redis_statefulset_deleted_correctly(self):
        """
        Test that Redis StatefulSet is properly deleted (not Deployment).

        Validates Finding #3: Staging Redis deletion using wrong kind

        After fix: Redis StatefulSet should NOT appear in staging overlay
        (because it's deleted and replaced with cloud-managed Redis)
        """
        documents = self._build_overlay()

        # Check that no Redis StatefulSet exists
        for doc in documents:
            if doc is None or not isinstance(doc, dict):
                continue

            if doc.get("kind") == "StatefulSet":
                name = doc.get("metadata", {}).get("name", "")
                assert "redis" not in name.lower(), (
                    f"Redis StatefulSet '{name}' still exists in staging overlay. "
                    f"It should be deleted (using cloud-managed Redis)."
                )

    def test_network_policy_postgres_port(self):
        """
        Test that NetworkPolicy allows PostgreSQL on correct port 5432.

        Validates Finding #6: Cloud SQL ports using 3307 instead of 5432

        Common mistake: Port 3307 (MySQL) instead of 5432 (PostgreSQL)
        """
        documents = self._build_overlay()

        for doc in documents:
            if doc is None or not isinstance(doc, dict):
                continue

            if doc.get("kind") == "NetworkPolicy":
                # Check egress rules for database ports
                spec = doc.get("spec", {})
                egress_rules = spec.get("egress", [])

                for rule in egress_rules:
                    ports = rule.get("ports", [])
                    for port_spec in ports:
                        port = port_spec.get("port")

                        # If port 3307 is found, fail (that's MySQL, not Postgres)
                        if port == 3307:
                            pytest.fail(
                                f"NetworkPolicy '{doc['metadata']['name']}' uses port 3307 (MySQL). "
                                f"PostgreSQL uses port 5432."
                            )


@pytest.mark.xdist_group(name="testproductiongkeoverlay")
class TestProductionGKEOverlay:
    """Specific tests for production-gke overlay configuration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @requires_tool("kustomize")
    def _build_overlay(self):
        """Helper to build production overlay."""
        overlay_path = REPO_ROOT / "deployments/overlays/production-gke"
        result = subprocess.run(
            ["kustomize", "build", str(overlay_path)], capture_output=True, text=True, cwd=REPO_ROOT, timeout=60
        )
        if result.returncode != 0:
            pytest.skip(f"Build failed: {result.stderr}")
        return list(yaml.safe_load_all(result.stdout))

    def test_namespace_consistency_for_production_matches_expected_namespace(self):
        """
        Test that all resources use the correct namespace.

        Expected: production-mcp-server-langgraph
        Common mistake: mcp-production (hardcoded)

        Validates Finding #10: PDB namespace mismatch
        """
        documents = self._build_overlay()
        expected_namespace = "production-mcp-server-langgraph"

        for doc in documents:
            if doc is None or not isinstance(doc, dict):
                continue

            # Check metadata.namespace
            if "metadata" in doc and "namespace" in doc["metadata"]:
                actual_ns = doc["metadata"]["namespace"]

                # Allow system namespaces
                if actual_ns in ["kube-system", "istio-system", "cert-manager", "monitoring"]:
                    continue

                assert actual_ns == expected_namespace, (
                    f"{doc['kind']}/{doc['metadata'].get('name', 'unknown')} "
                    f"has wrong namespace: {actual_ns} (expected {expected_namespace})"
                )

    def test_cloud_sql_proxy_health_checks(self):
        """
        Test that Cloud SQL Proxy has health check flags when probes are defined.

        Validates Finding #7: Missing health check flags in production

        If container has httpGet probes on port 9801, it must have:
        - --health-check
        - --http-port=9801
        - --http-address=0.0.0.0
        """
        documents = self._build_overlay()

        for doc in documents:
            if doc is None or not isinstance(doc, dict):
                continue

            if doc.get("kind") == "Deployment":
                spec = doc.get("spec", {}).get("template", {}).get("spec", {})
                containers = spec.get("containers", [])

                for container in containers:
                    # Look for Cloud SQL Proxy container
                    if "cloud-sql-proxy" in container.get("image", ""):
                        args = container.get("args", [])

                        # Check for health probes
                        liveness = container.get("livenessProbe", {})
                        readiness = container.get("readinessProbe", {})

                        has_http_probe = liveness.get("httpGet") is not None or readiness.get("httpGet") is not None

                        if has_http_probe:
                            # Must have health check flags
                            assert "--health-check" in args, (
                                f"Cloud SQL Proxy in {doc['metadata']['name']} has HTTP probes "
                                f"but missing --health-check flag"
                            )

                            # Check for --http-port flag
                            http_port_found = any("--http-port" in arg for arg in args)
                            assert http_port_found, (
                                f"Cloud SQL Proxy in {doc['metadata']['name']} has HTTP probes "
                                f"but missing --http-port flag"
                            )

    def test_no_unsubstituted_variables_in_images(self):
        """
        Test that image references don't contain unsubstituted variables.

        Validates Finding #8: GCP_PROJECT_ID substitution

        Common mistake: $(GCP_PROJECT_ID) or ${GCP_PROJECT_ID} left in image names
        """
        documents = self._build_overlay()

        for doc in documents:
            if doc is None or not isinstance(doc, dict):
                continue

            if doc.get("kind") in ["Deployment", "StatefulSet", "DaemonSet", "Job", "CronJob"]:
                spec = doc.get("spec", {}).get("template", {}).get("spec", {})
                containers = spec.get("containers", []) + spec.get("initContainers", [])

                for container in containers:
                    image = container.get("image", "")

                    # Check for unsubstituted variables
                    if "$(GCP_PROJECT_ID)" in image or "${GCP_PROJECT_ID}" in image:
                        pytest.fail(
                            f"Container '{container.get('name')}' in {doc['metadata']['name']} "
                            f"has unsubstituted variable in image: {image}"
                        )


@pytest.mark.xdist_group(name="testbaseresources")
class TestBaseResources:
    """Tests for base Kustomize resources."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @requires_tool("kustomize")
    def _build_base(self):
        """Helper to build base."""
        base_path = REPO_ROOT / "deployments/base"
        result = subprocess.run(
            ["kustomize", "build", str(base_path)], capture_output=True, text=True, cwd=REPO_ROOT, timeout=60
        )
        if result.returncode != 0:
            pytest.skip(f"Build failed: {result.stderr}")
        return list(yaml.safe_load_all(result.stdout))

    def test_no_orphaned_resource_quotas(self):
        """
        Test that ResourceQuotas only exist for namespaces that are defined.

        Validates Finding #2: ResourceQuota for undefined monitoring namespace

        If a ResourceQuota references a namespace, that namespace must be
        defined in the same kustomization or a dependency.
        """
        documents = self._build_base()

        # Collect all defined namespaces
        defined_namespaces = set()
        for doc in documents:
            if doc is None or not isinstance(doc, dict):
                continue
            if doc.get("kind") == "Namespace":
                name = doc.get("metadata", {}).get("name")
                if name:
                    defined_namespaces.add(name)

        # Check ResourceQuotas
        for doc in documents:
            if doc is None or not isinstance(doc, dict):
                continue

            if doc.get("kind") == "ResourceQuota":
                namespace = doc.get("metadata", {}).get("namespace")
                quota_name = doc.get("metadata", {}).get("name", "unknown")

                # ResourceQuota namespace must be defined
                if namespace and namespace not in defined_namespaces:
                    # Skip if it's a system namespace (assumed to exist)
                    if namespace in ["kube-system", "default", "kube-public", "kube-node-lease"]:
                        continue

                    pytest.fail(
                        f"ResourceQuota '{quota_name}' references undefined namespace '{namespace}'. "
                        f"Either define the namespace or move this quota to an overlay."
                    )


@pytest.mark.xdist_group(name="testservicemeshconfig")
class TestServiceMeshConfig:
    """Tests for Istio/service mesh configuration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_istio_config_no_inline_comments_in_strings(self):
        """
        Test that Istio config doesn't have inline comments in YAML strings.

        Validates Finding #11: Istio inline comments in host strings

        Common mistake:
          hosts:
            - "mcp.example.com  # TODO: Replace"

        This makes the host literally include the comment text.
        """
        istio_config = REPO_ROOT / "deployments/service-mesh/istio/istio-config.yaml"

        if not istio_config.exists():
            pytest.skip("Istio config not found")

        with open(istio_config) as f:
            content = f.read()

        # Parse YAML
        try:
            documents = list(yaml.safe_load_all(content))
        except yaml.YAMLError as e:
            pytest.fail(f"Invalid YAML in istio-config.yaml: {e}")

        # Check for inline comments in host strings
        for doc in documents:
            if doc is None or not isinstance(doc, dict):
                continue

            # Recursively check for hosts fields
            def check_hosts(obj, path=""):
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        new_path = f"{path}.{key}" if path else key
                        if key == "hosts" and isinstance(value, list):
                            # Check each host
                            for host in value:
                                if isinstance(host, str) and "#" in host:
                                    pytest.fail(
                                        f"Istio config at {new_path} has inline comment in host string: {host}\n"
                                        f"Move the comment to a separate line above the host."
                                    )
                        else:
                            check_hosts(value, new_path)
                elif isinstance(obj, list):
                    for i, item in enumerate(obj):
                        check_hosts(item, f"{path}[{i}]")

            check_hosts(doc)


# Fixtures for reusable test setup
@pytest.fixture(scope="session")
@requires_tool("kustomize")
def check_kustomize_installed():
    """Ensure kustomize is installed before running tests."""
    result = subprocess.run(["kustomize", "version"], capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        pytest.fail(
            "kustomize is not installed. Install it with:\n"
            "  curl -s 'https://raw.githubusercontent.com/kubernetes-sigs/kustomize/master/hack/install_kustomize.sh' | bash"
        )
