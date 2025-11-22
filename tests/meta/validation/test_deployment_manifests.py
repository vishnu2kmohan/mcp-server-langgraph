"""
Test suite for validating Kubernetes deployment manifests.

This test suite validates deployment configurations to prevent common
misconfigurations identified by OpenAI Codex analysis.

Test Coverage:
- RBAC role configurations (resourceNames with list/watch)
- NetworkPolicy egress rules for required services
- Kustomize overlay buildability
- Helm chart validation and rendering
- Health probe path consistency
- Istio integration conditional checks
"""

import gc
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

from tests.conftest import requires_tool

# Mark as unit test to ensure it runs in CI
pytestmark = pytest.mark.unit

# Test fixtures and helpers


@pytest.fixture
def project_root() -> Path:
    """Return the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture
def deployments_base_dir(project_root: Path) -> Path:
    """Return the deployments/base directory."""
    return project_root / "deployments" / "base"


@pytest.fixture
def deployments_overlays_dir(project_root: Path) -> Path:
    """Return the deployments/overlays directory."""
    return project_root / "deployments" / "overlays"


@pytest.fixture
def helm_chart_dir(project_root: Path) -> Path:
    """Return the Helm chart directory."""
    return project_root / "deployments" / "helm" / "mcp-server-langgraph"


def load_yaml_file(file_path: Path) -> Any:
    """Load and parse a YAML file, handling multi-document YAML."""
    with open(file_path) as f:
        # Use safe_load_all to handle multi-document YAML
        docs = list(yaml.safe_load_all(f))
        return docs if len(docs) > 1 else docs[0]


def load_yaml_documents(file_path: Path) -> list[dict[str, Any]]:
    """Load all documents from a potentially multi-document YAML file."""
    with open(file_path) as f:
        return [doc for doc in yaml.safe_load_all(f) if doc is not None]


# Critical Issue Tests


@pytest.mark.xdist_group(name="testrbacconfiguration")
class TestRBACConfiguration:
    """Test RBAC role configurations for invalid patterns."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_rbac_roles_no_list_with_resource_names(self, deployments_base_dir: Path) -> None:
        """
        Test that RBAC roles don't combine list/watch verbs with resourceNames.

        Kubernetes RBAC doesn't support scoping list/watch operations by
        resourceNames. This test ensures we don't have this invalid combination.

        Critical Issue #1: deployments/base/serviceaccount-roles.yaml:12/49/85/121/157
        """
        roles_file = deployments_base_dir / "serviceaccount-roles.yaml"
        assert roles_file.exists(), f"RBAC roles file not found: {roles_file}"

        documents = load_yaml_documents(roles_file)

        invalid_rules = []

        for doc_idx, doc in enumerate(documents):
            if doc.get("kind") not in ["Role", "ClusterRole"]:
                continue

            role_name = doc.get("metadata", {}).get("name", f"doc-{doc_idx}")
            rules = doc.get("rules", [])

            for rule_idx, rule in enumerate(rules):
                resource_names = rule.get("resourceNames", [])
                verbs = rule.get("verbs", [])

                # Check for invalid combination
                if resource_names:
                    invalid_verbs = set(verbs) & {"list", "watch"}
                    if invalid_verbs:
                        invalid_rules.append(
                            {
                                "role": role_name,
                                "rule_index": rule_idx,
                                "invalid_verbs": list(invalid_verbs),
                                "resource_names": resource_names,
                                "resources": rule.get("resources", []),
                            }
                        )

        assert not invalid_rules, f"Found {len(invalid_rules)} RBAC rules with list/watch + resourceNames:\n" + "\n".join(
            [
                f"  - Role '{r['role']}' rule {r['rule_index']}: "
                f"verbs {r['invalid_verbs']} with resourceNames {r['resource_names']}"
                for r in invalid_rules
            ]
        )


@pytest.mark.xdist_group(name="testnetworkpolicy")
class TestNetworkPolicy:
    """Test NetworkPolicy configurations for completeness."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_network_policy_has_required_egress_rules(self, deployments_base_dir: Path) -> None:
        """
        Test that NetworkPolicy includes egress rules for all required services.

        Critical Issue #2: deployments/base/networkpolicy.yaml:42
        Missing egress rules for Keycloak, Redis, PostgreSQL, Qdrant.
        """
        netpol_file = deployments_base_dir / "networkpolicy.yaml"
        assert netpol_file.exists(), f"NetworkPolicy file not found: {netpol_file}"

        documents = load_yaml_documents(netpol_file)

        # Required service ports
        required_egress_ports = {
            53: "DNS",
            8080: "Keycloak",
            6379: "Redis",
            5432: "PostgreSQL",
            6333: "Qdrant",
            4317: "OpenTelemetry",
        }

        found_egress_ports = set()

        for doc in documents:
            if doc.get("kind") != "NetworkPolicy":
                continue

            egress_rules = doc.get("spec", {}).get("egress", [])

            for egress in egress_rules:
                ports = egress.get("ports", [])
                for port_spec in ports:
                    port = port_spec.get("port")
                    if port:
                        found_egress_ports.add(port)

        missing_ports = set(required_egress_ports.keys()) - found_egress_ports

        assert not missing_ports, "NetworkPolicy missing egress rules for required ports:\n" + "\n".join(
            [f"  - Port {port} ({required_egress_ports[port]})" for port in sorted(missing_ports)]
        )


@pytest.mark.requires_kustomize
@pytest.mark.xdist_group(name="testkustomizeoverlays")
class TestKustomizeOverlays:
    """Test that Kustomize overlays can build successfully.

    CODEX FINDING #1: These tests require kustomize CLI tool.
    Tests will skip gracefully if kustomize is not installed.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.parametrize("overlay", ["dev", "staging", "production"])
    @requires_tool("kustomize")
    def test_kustomize_overlay_builds(self, project_root: Path, overlay: str) -> None:
        """
        Test that Kustomize overlays build without errors.

        Critical Issue #4: deployments/overlays/dev/kustomization.yaml:28
        Patches reference resources not included in base.
        """
        # CODEX FINDING #1: Check if kustomize is available
        if not shutil.which("kustomize"):
            pytest.skip(
                "kustomize CLI not installed. Install with:\n"
                "  curl -s https://raw.githubusercontent.com/kubernetes-sigs/kustomize/master/hack/install_kustomize.sh | bash"
            )

        overlay_dir = project_root / "deployments" / "overlays" / overlay

        if not overlay_dir.exists():
            pytest.skip(f"Overlay {overlay} does not exist")

        result = subprocess.run(["kustomize", "build", str(overlay_dir)], capture_output=True, text=True, timeout=60)

        assert result.returncode == 0, (
            f"Kustomize build failed for overlay '{overlay}':\n" f"STDOUT:\n{result.stdout}\n" f"STDERR:\n{result.stderr}"
        )

        # Verify output contains valid YAML
        try:
            manifests = list(yaml.safe_load_all(result.stdout))
            assert len(manifests) > 0, f"No manifests generated for overlay '{overlay}'"
        except yaml.YAMLError as e:
            pytest.fail(f"Invalid YAML output from kustomize build: {e}")

    @pytest.mark.parametrize("overlay", ["aws", "gcp", "azure"])
    @requires_tool("kustomize")
    def test_cloud_provider_overlay_builds(self, project_root: Path, overlay: str) -> None:
        """
        Test that cloud provider overlays build successfully.

        Critical Issue #3: deployments/kubernetes/overlays/aws/kustomization.yaml:8
        Invalid base path (../../base should be ../../../base).
        """
        # CODEX FINDING #1: Check if kustomize is available
        if not shutil.which("kustomize"):
            pytest.skip(
                "kustomize CLI not installed. Install with:\n"
                "  curl -s https://raw.githubusercontent.com/kubernetes-sigs/kustomize/master/hack/install_kustomize.sh | bash"
            )

        overlay_dir = project_root / "deployments" / "kubernetes" / "overlays" / overlay

        if not overlay_dir.exists():
            pytest.skip(f"Cloud provider overlay {overlay} does not exist")

        result = subprocess.run(["kustomize", "build", str(overlay_dir)], capture_output=True, text=True, timeout=60)

        assert result.returncode == 0, (
            f"Kustomize build failed for cloud provider overlay '{overlay}':\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )


@pytest.mark.xdist_group(name="testbasekustomization")
class TestBaseKustomization:
    """Test base kustomization includes all required resources."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_base_kustomization_includes_all_manifests(self, deployments_base_dir: Path) -> None:
        """
        Test that base/kustomization.yaml includes all required manifest files.

        Critical Issue #1 (from Codex): Missing key manifests like ingress-http.yaml,
        otel-collector-deployment.yaml, limitrange.yaml, postgres-networkpolicy.yaml, etc.
        """
        kustomization_file = deployments_base_dir / "kustomization.yaml"
        assert kustomization_file.exists()

        kustomization = load_yaml_file(kustomization_file)
        resources = kustomization.get("resources", [])

        # Required manifest files that should be in resources
        required_manifests = [
            "ingress-http.yaml",
            "otel-collector-deployment.yaml",
            "limitrange.yaml",
            "resourcequota.yaml",
            "postgres-networkpolicy.yaml",
            "redis-networkpolicy.yaml",
        ]

        missing_manifests = [manifest for manifest in required_manifests if manifest not in resources]

        assert not missing_manifests, "Base kustomization.yaml missing required resources:\n" + "\n".join(
            [f"  - {manifest}" for manifest in missing_manifests]
        )


# High Priority Tests


@pytest.mark.requires_helm
@pytest.mark.xdist_group(name="testhelmchart")
class TestHelmChart:
    """Test Helm chart configurations.

    CODEX FINDING #1: These tests require helm CLI tool.
    Tests will skip gracefully if helm is not installed.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @requires_tool("helm")
    def test_helm_chart_lints_successfully(self, helm_chart_dir: Path) -> None:
        """
        Test that Helm chart passes helm lint validation.

        FIXED (2025-11-16): Helm dependency build resolved CODEX FINDING #7.
        Prometheus rules file parsing error was fixed by running helm dependency update/build.

        Note: Kustomize deployments (primary method) are unaffected.
        """
        # CODEX FINDING #1: Check if helm is available
        if not shutil.which("helm"):
            pytest.skip(
                "helm CLI not installed. Install with:\n"
                "  curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash"
            )

        if not helm_chart_dir.exists():
            pytest.skip("Helm chart directory does not exist")

        result = subprocess.run(["helm", "lint", str(helm_chart_dir)], capture_output=True, text=True, timeout=60)

        assert result.returncode == 0, f"Helm lint failed:\n" f"STDOUT:\n{result.stdout}\n" f"STDERR:\n{result.stderr}"

    @requires_tool("helm")
    def test_helm_chart_renders_successfully(self, helm_chart_dir: Path) -> None:
        """Test that Helm chart renders without errors.

        FIXED (2025-11-16): Helm dependency build resolved CODEX FINDING #7.
        Chart now renders successfully after dependencies were built.
        Ran 'helm dependency update' to resolve prometheus rules parsing errors.

        Depends on successful lint. See test_helm_chart_lints_successfully.
        """
        # CODEX FINDING #1: Check if helm is available
        if not shutil.which("helm"):
            pytest.skip(
                "helm CLI not installed. Install with:\n"
                "  curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash"
            )

        if not helm_chart_dir.exists():
            pytest.skip("Helm chart directory does not exist")

        result = subprocess.run(
            ["helm", "template", "test-release", str(helm_chart_dir)], capture_output=True, text=True, timeout=60
        )

        assert result.returncode == 0, f"Helm template failed:\n" f"STDOUT:\n{result.stdout}\n" f"STDERR:\n{result.stderr}"

    def test_helm_networkpolicy_template_exists_when_enabled(self, helm_chart_dir: Path) -> None:
        """
        Test that NetworkPolicy template exists when feature is enabled in values.

        High Priority Issue #7: networkPolicy.enabled: true but no template exists.
        """
        if not helm_chart_dir.exists():
            pytest.skip("Helm chart directory does not exist")

        values_file = helm_chart_dir / "values.yaml"
        assert values_file.exists()

        values = load_yaml_file(values_file)
        networkpolicy_enabled = values.get("networkPolicy", {}).get("enabled", False)

        if networkpolicy_enabled:
            template_file = helm_chart_dir / "templates" / "networkpolicy.yaml"
            assert template_file.exists(), (
                "networkPolicy.enabled is true in values.yaml but " "templates/networkpolicy.yaml does not exist"
            )

    def test_helm_health_probe_paths_match_app(self, helm_chart_dir: Path, deployments_base_dir: Path) -> None:
        """
        Test that Helm chart health probe paths match the canonical deployment.

        Medium Priority Issue #8: Helm uses /health but base uses /health/live.

        Note: Helm chart uses .Values.healthChecks structure, not .Values.livenessProbe.
        """
        if not helm_chart_dir.exists():
            pytest.skip("Helm chart directory does not exist")

        values_file = helm_chart_dir / "values.yaml"
        assert values_file.exists()

        values = load_yaml_file(values_file)

        # Expected health probe paths
        expected_liveness = "/health/live"
        expected_readiness = "/health/ready"
        expected_startup = "/health/startup"

        # Check livenessProbe (in healthChecks structure)
        liveness_path = values.get("healthChecks", {}).get("liveness", {}).get("path")
        assert liveness_path == expected_liveness, (
            f"Helm values.yaml healthChecks.liveness.path is '{liveness_path}', " f"should be '{expected_liveness}'"
        )

        # Check readinessProbe (in healthChecks structure)
        readiness_path = values.get("healthChecks", {}).get("readiness", {}).get("path")
        assert readiness_path == expected_readiness, (
            f"Helm values.yaml healthChecks.readiness.path is '{readiness_path}', " f"should be '{expected_readiness}'"
        )

        # Check startupProbe (in healthChecks structure)
        startup_path = values.get("healthChecks", {}).get("startup", {}).get("path")
        assert startup_path == expected_startup, (
            f"Helm values.yaml healthChecks.startup.path is '{startup_path}', " f"should be '{expected_startup}'"
        )

    def test_helm_istio_resources_have_conditional_checks(self, helm_chart_dir: Path) -> None:
        """
        Test that Istio resources have conditional capability checks.

        High Priority Issue #9: Istio enabled by default but no conditional checks.
        Charts fail on clusters without Istio CRDs.
        """
        if not helm_chart_dir.exists():
            pytest.skip("Helm chart directory does not exist")

        templates_dir = helm_chart_dir / "templates"
        if not templates_dir.exists():
            pytest.skip("Templates directory does not exist")

        # Istio resource kinds that require conditional checks
        istio_kinds = {
            "Gateway",
            "VirtualService",
            "DestinationRule",
            "PeerAuthentication",
        }

        templates_needing_checks = []

        for template_file in templates_dir.glob("*.yaml"):
            content = template_file.read_text()

            # Check if this template defines Istio resources
            has_istio_resources = False
            for kind in istio_kinds:
                if f"kind: {kind}" in content:
                    has_istio_resources = True
                    break

            if not has_istio_resources:
                continue

            # Check for Capabilities.APIVersions.Has check
            has_capability_check = ".Capabilities.APIVersions.Has" in content or "if .Values.serviceMesh.enabled" in content

            if not has_capability_check:
                templates_needing_checks.append(template_file.name)

        assert not templates_needing_checks, (
            "Istio templates missing conditional capability checks:\n"
            + "\n".join([f"  - {name}" for name in templates_needing_checks])
            + '\n\nAdd: {{- if .Capabilities.APIVersions.Has "networking.istio.io/v1beta1" }}'
        )


@pytest.mark.xdist_group(name="testcloudrunmanifest")
class TestCloudRunManifest:
    """Test Cloud Run service manifest configurations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_cloudrun_no_bash_variable_substitutions(self, project_root: Path) -> None:
        """
        Test that Cloud Run manifest doesn't contain unresolved bash variables.

        High Priority Issue #5: ${DOMAIN}, ${PROJECT_ID} won't expand in YAML.
        """
        cloudrun_file = project_root / "deployments" / "cloudrun" / "service.yaml"

        if not cloudrun_file.exists():
            pytest.skip("Cloud Run service.yaml does not exist")

        content = cloudrun_file.read_text()

        # Look for bash-style variable substitutions
        bash_vars = []
        for line_num, line in enumerate(content.splitlines(), 1):
            if "${" in line and "}" in line:
                # Extract variable name
                import re

                matches = re.findall(r"\$\{([^}]+)\}", line)
                for var_name in matches:
                    bash_vars.append({"line": line_num, "variable": var_name, "content": line.strip()})

        assert not bash_vars, (
            "Cloud Run service.yaml contains bash variable substitutions:\n"
            + "\n".join([f"  Line {v['line']}: ${{{v['variable']}}} in: {v['content']}" for v in bash_vars])
            + "\n\nUse Secret Manager valueFrom or template placeholders instead."
        )


@pytest.mark.xdist_group(name="testargocdapplication")
class TestArgoCDApplication:
    """Test ArgoCD application configurations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_argocd_helm_values_use_valid_schema(self, project_root: Path) -> None:
        """
        Test that ArgoCD application uses valid Helm chart value paths.

        High Priority Issue #6: Using externalHost instead of external.host.
        """
        argocd_file = project_root / "deployments" / "argocd" / "applications" / "mcp-server-app.yaml"

        if not argocd_file.exists():
            pytest.skip("ArgoCD application file does not exist")

        doc = load_yaml_file(argocd_file)

        # Check for invalid top-level fields in helm values
        helm_values = doc.get("spec", {}).get("source", {}).get("helm", {}).get("values", "")

        if helm_values:
            values_dict = yaml.safe_load(helm_values)

            # Invalid patterns to check for
            invalid_patterns = []

            postgresql = values_dict.get("postgresql", {})
            if "externalHost" in postgresql:
                invalid_patterns.append("postgresql.externalHost (should be postgresql.external.host)")
            if "existingSecret" in postgresql and "external" not in postgresql:
                invalid_patterns.append("postgresql.existingSecret (should be postgresql.external.existingSecret)")

            redis = values_dict.get("redis", {})
            if "externalHost" in redis:
                invalid_patterns.append("redis.externalHost (should be redis.external.host)")
            if "existingSecret" in redis and "external" not in redis:
                invalid_patterns.append("redis.existingSecret (should be redis.external.existingSecret)")

            assert not invalid_patterns, "ArgoCD application uses invalid Helm value paths:\n" + "\n".join(
                [f"  - {pattern}" for pattern in invalid_patterns]
            )


# Medium Priority Tests


@pytest.mark.xdist_group(name="testhealthprobeconsistency")
class TestHealthProbeConsistency:
    """Test health probe path consistency across deployments."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_optimized_deployment_health_probes(self, project_root: Path, deployments_base_dir: Path) -> None:
        """
        Test that optimized deployment uses canonical health probe paths.

        Medium Priority Issue #11: optimized/deployment.yaml uses /health instead of /health/live.
        """
        optimized_file = project_root / "deployments" / "optimized" / "deployment.yaml"

        if not optimized_file.exists():
            pytest.skip("Optimized deployment does not exist")

        documents = load_yaml_documents(optimized_file)

        # Expected paths
        expected_liveness = "/health/live"
        expected_readiness = "/health/ready"

        mismatched_probes = []

        for doc in documents:
            if doc.get("kind") != "Deployment":
                continue

            containers = doc.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])

            for container in containers:
                # Check liveness probe
                liveness = container.get("livenessProbe", {})
                liveness_path = liveness.get("httpGet", {}).get("path")
                if liveness_path and liveness_path != expected_liveness:
                    mismatched_probes.append(f"livenessProbe: {liveness_path} (should be {expected_liveness})")

                # Check readiness probe
                readiness = container.get("readinessProbe", {})
                readiness_path = readiness.get("httpGet", {}).get("path")
                if readiness_path and readiness_path != expected_readiness:
                    mismatched_probes.append(f"readinessProbe: {readiness_path} (should be {expected_readiness})")

        assert not mismatched_probes, "Optimized deployment has incorrect health probe paths:\n" + "\n".join(
            [f"  - {probe}" for probe in mismatched_probes]
        )


@pytest.mark.xdist_group(name="testdocumentation")
class TestDocumentation:
    """Test documentation accuracy."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_readme_uses_modern_kustomize_syntax(self, deployments_base_dir: Path) -> None:
        """
        Test that README examples use modern Kustomize syntax.

        Medium Priority Issue #10: README uses deprecated 'bases:' field.
        """
        readme_file = deployments_base_dir / "README.md"

        if not readme_file.exists():
            pytest.skip("Base README.md does not exist")

        content = readme_file.read_text()

        # Check for deprecated 'bases:' field in examples
        deprecated_usage = []
        for line_num, line in enumerate(content.splitlines(), 1):
            if "bases:" in line and "```" not in line:
                # Found usage of deprecated 'bases:' field
                deprecated_usage.append({"line": line_num, "content": line.strip()})

        assert not deprecated_usage, (
            "README.md uses deprecated Kustomize 'bases:' syntax:\n"
            + "\n".join([f"  Line {u['line']}: {u['content']}" for u in deprecated_usage])
            + "\n\nUse 'resources:' instead (modern Kustomize v2.1.0+)."
        )
