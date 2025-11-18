"""
Test suite for critical Kubernetes deployment issues identified by security audit.

Following TDD Red-Green-Refactor:
- RED: These tests should FAIL initially (critical issues exist)
- GREEN: After fixes, tests should PASS
- REFACTOR: Improve validation logic as needed

Critical issues tested:
1. NetworkPolicy uses non-standard namespace labels and blocks external egress
2. Deployment zone spreading breaks single-zone clusters
3. Secret.yaml with placeholder values included in base kustomization
4. OpenFGA deployment references missing secret key
5. GKE production overlay namespace mismatch
"""

import gc
from pathlib import Path
from typing import Any, Dict

import pytest
import yaml


# Mark as unit test to ensure it runs in CI (deployment validation)
pytestmark = pytest.mark.unit
# Define project root relative to test file
PROJECT_ROOT = Path(__file__).parent.parent.parent
DEPLOYMENTS_BASE = PROJECT_ROOT / "deployments" / "base"
DEPLOYMENTS_PROD_GKE = PROJECT_ROOT / "deployments" / "overlays" / "production-gke"


@pytest.mark.xdist_group(name="testcriticalnetworkpolicyissues")
class TestCriticalNetworkPolicyIssues:
    """Test NetworkPolicy uses standard labels and permits required egress."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def _load_yaml_file(self, file_path: Path) -> dict[str, Any]:
        """Load YAML file and return parsed content."""
        with open(file_path, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def test_networkpolicy_uses_standard_namespace_labels(self):
        """
        RED: NetworkPolicy uses non-standard 'name' label for namespace selection.
        GREEN: Should use 'kubernetes.io/metadata.name' standard label.

        Issue: deployments/base/networkpolicy.yaml:19 uses 'name: ingress-nginx'
        Fix: Use 'kubernetes.io/metadata.name: ingress-nginx'
        """
        network_policy_path = DEPLOYMENTS_BASE / "networkpolicy.yaml"

        if not network_policy_path.exists():
            pytest.skip(f"NetworkPolicy not found: {network_policy_path}")

        policy = self._load_yaml_file(network_policy_path)

        violations = []

        # Check ingress rules
        for idx, ingress_rule in enumerate(policy["spec"].get("ingress", [])):
            from_rules = ingress_rule.get("from", [])
            for from_idx, from_rule in enumerate(from_rules):
                namespace_selector = from_rule.get("namespaceSelector", {})
                match_labels = namespace_selector.get("matchLabels", {})

                # Check for non-standard 'name' label
                if "name" in match_labels:
                    violations.append(
                        {
                            "location": f"spec.ingress[{idx}].from[{from_idx}]",
                            "label": "name",
                            "value": match_labels["name"],
                            "fix": f"Use 'kubernetes.io/metadata.name: {match_labels['name']}'",
                        }
                    )

        # Check egress rules
        for idx, egress_rule in enumerate(policy["spec"].get("egress", [])):
            to_rules = egress_rule.get("to", [])
            for to_idx, to_rule in enumerate(to_rules):
                namespace_selector = to_rule.get("namespaceSelector", {})
                match_labels = namespace_selector.get("matchLabels", {})

                # Check for non-standard 'name' label
                if "name" in match_labels:
                    violations.append(
                        {
                            "location": f"spec.egress[{idx}].to[{to_idx}]",
                            "label": "name",
                            "value": match_labels["name"],
                            "fix": f"Use 'kubernetes.io/metadata.name: {match_labels['name']}'",
                        }
                    )

        if violations:
            error_msg = "\n\nNetworkPolicy uses non-standard namespace labels:\n"
            error_msg += f"File: {network_policy_path.relative_to(PROJECT_ROOT)}\n"
            for v in violations:
                error_msg += f"\n  Location: {v['location']}"
                error_msg += f"\n    Non-standard label: {v['label']}: {v['value']}"
                error_msg += f"\n    Fix: {v['fix']}\n"

            pytest.fail(error_msg)

    def test_networkpolicy_permits_external_llm_api_egress(self):
        """
        RED: NetworkPolicy blocks egress to external LLM APIs (Anthropic, OpenAI, etc).
        GREEN: Should allow egress to public internet via ipBlock or remove namespaceSelector: {}.

        Issue: Line 72 uses 'namespaceSelector: {}' which only matches in-cluster namespaces
        Fix: Add explicit ipBlock rules for 0.0.0.0/0 or document cloud-specific egress
        """
        network_policy_path = DEPLOYMENTS_BASE / "networkpolicy.yaml"

        if not network_policy_path.exists():
            pytest.skip(f"NetworkPolicy not found: {network_policy_path}")

        policy = self._load_yaml_file(network_policy_path)

        # Check for egress rules that allow external HTTPS (443)
        egress_rules = policy["spec"].get("egress", [])

        # Look for rules allowing port 443
        https_egress_rules = []
        for rule in egress_rules:
            ports = rule.get("ports", [])
            for port in ports:
                if port.get("port") == 443 and port.get("protocol") == "TCP":
                    https_egress_rules.append(rule)

        if not https_egress_rules:
            pytest.fail(
                f"\n\nNetworkPolicy does not allow HTTPS egress (port 443)\n"
                f"File: {network_policy_path.relative_to(PROJECT_ROOT)}\n"
                f"Required for external LLM API calls (Anthropic, OpenAI, Google)"
            )

        # Check if HTTPS rules allow external traffic
        has_external_egress = False
        problems = []

        for rule in https_egress_rules:
            to_rules = rule.get("to", [])

            # If 'to' is empty, it allows all destinations - that's OK
            if not to_rules:
                has_external_egress = True
                break

            for to_rule in to_rules:
                # Check for ipBlock (allows external IPs)
                if "ipBlock" in to_rule:
                    has_external_egress = True
                    break

                # namespaceSelector: {} only matches in-cluster namespaces
                if "namespaceSelector" in to_rule:
                    namespace_selector = to_rule["namespaceSelector"]
                    # Empty selector {} matches all namespaces IN the cluster only
                    if namespace_selector == {}:
                        problems.append("Uses 'namespaceSelector: {}' which only matches in-cluster namespaces")

        if not has_external_egress:
            error_msg = "\n\nNetworkPolicy does not permit egress to external LLM APIs:\n"
            error_msg += f"File: {network_policy_path.relative_to(PROJECT_ROOT)}\n"
            for problem in problems:
                error_msg += f"\n  - {problem}"
            error_msg += "\n\nFix: Add ipBlock rule for external access:"
            error_msg += "\n  - to:"
            error_msg += "\n    - ipBlock:"
            error_msg += "\n        cidr: 0.0.0.0/0"
            error_msg += "\n        except:"
            error_msg += "\n        - 169.254.169.254/32  # Block metadata service"
            error_msg += "\n    ports:"
            error_msg += "\n    - protocol: TCP"
            error_msg += "\n      port: 443\n"

            pytest.fail(error_msg)


@pytest.mark.xdist_group(name="testcriticaltopologyspreadissues")
class TestCriticalTopologySpreadIssues:
    """Test that topology spread constraints don't break single-zone clusters."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def _load_yaml_file(self, file_path: Path) -> dict[str, Any]:
        """Load YAML file and return parsed content."""
        with open(file_path, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def test_deployment_zone_spreading_allows_single_zone(self):
        """
        RED: Deployment requires multiple zones, breaking single-zone clusters.
        GREEN: Zone spreading should be preferredDuringScheduling or in production overlay only.

        Issue: deployment.yaml:550 uses 'whenUnsatisfiable: DoNotSchedule' for zones
        Issue: deployment.yaml:571 uses 'requiredDuringSchedulingIgnoredDuringExecution' for zones
        Fix: Change to 'ScheduleAnyway' or move to production overlay
        """
        deployment_path = DEPLOYMENTS_BASE / "deployment.yaml"

        if not deployment_path.exists():
            pytest.skip(f"Deployment not found: {deployment_path}")

        deployment = self._load_yaml_file(deployment_path)

        violations = []

        # Check topologySpreadConstraints
        topology_constraints = deployment["spec"]["template"]["spec"].get("topologySpreadConstraints", [])

        for idx, constraint in enumerate(topology_constraints):
            topology_key = constraint.get("topologyKey", "")
            when_unsatisfiable = constraint.get("whenUnsatisfiable", "")

            # Zone spreading with DoNotSchedule breaks single-zone clusters
            if "zone" in topology_key and when_unsatisfiable == "DoNotSchedule":
                violations.append(
                    {
                        "type": "topologySpreadConstraints",
                        "index": idx,
                        "topology_key": topology_key,
                        "when_unsatisfiable": when_unsatisfiable,
                        "issue": "DoNotSchedule breaks single-zone clusters (dev, autopilot)",
                        "fix": "Use 'whenUnsatisfiable: ScheduleAnyway' or move to production overlay",
                    }
                )

        # Check podAntiAffinity
        affinity = deployment["spec"]["template"]["spec"].get("affinity", {})
        pod_anti_affinity = affinity.get("podAntiAffinity", {})
        required_anti_affinity = pod_anti_affinity.get("requiredDuringSchedulingIgnoredDuringExecution", [])

        for idx, rule in enumerate(required_anti_affinity):
            topology_key = rule.get("topologyKey", "")

            # Required zone anti-affinity breaks single-zone clusters
            if "zone" in topology_key:
                violations.append(
                    {
                        "type": "podAntiAffinity.required",
                        "index": idx,
                        "topology_key": topology_key,
                        "issue": "Required anti-affinity breaks single-zone clusters",
                        "fix": "Move to 'preferredDuringSchedulingIgnoredDuringExecution' or production overlay",
                    }
                )

        if violations:
            error_msg = "\n\nDeployment has zone spreading that breaks single-zone clusters:\n"
            error_msg += f"File: {deployment_path.relative_to(PROJECT_ROOT)}\n"
            for v in violations:
                error_msg += f"\n  Type: {v['type']}[{v['index']}]"
                error_msg += f"\n    Topology: {v['topology_key']}"
                if "when_unsatisfiable" in v:
                    error_msg += f"\n    When unsatisfiable: {v['when_unsatisfiable']}"
                error_msg += f"\n    Issue: {v['issue']}"
                error_msg += f"\n    Fix: {v['fix']}\n"

            pytest.fail(error_msg)


@pytest.mark.xdist_group(name="testcriticalsecretissues")
class TestCriticalSecretIssues:
    """Test that secrets with placeholders are not in base kustomization."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def _load_yaml_file(self, file_path: Path) -> Any:
        """Load YAML file and return parsed content."""
        with open(file_path, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def test_secret_placeholders_not_in_base_kustomization(self):
        """
        RED: secret.yaml with REPLACE_WITH_* placeholders is in base kustomization.
        GREEN: Secret should be removed from base or replaced with ExternalSecret template.

        Issue: deployments/base/secret.yaml:15 has placeholders, included in kustomization
        Fix: Remove from base kustomization or use ExternalSecret
        """
        kustomization_path = DEPLOYMENTS_BASE / "kustomization.yaml"
        secret_path = DEPLOYMENTS_BASE / "secret.yaml"

        if not kustomization_path.exists():
            pytest.skip(f"Kustomization not found: {kustomization_path}")

        kustomization = self._load_yaml_file(kustomization_path)
        resources = kustomization.get("resources", [])

        # Check if secret.yaml is in resources
        if "secret.yaml" in resources:
            # Now check if it has placeholders
            if secret_path.exists():
                secret = self._load_yaml_file(secret_path)
                string_data = secret.get("stringData", {})

                placeholders_found = []
                for key, value in string_data.items():
                    if isinstance(value, str) and "REPLACE_WITH" in value:
                        placeholders_found.append({"key": key, "value": value})

                if placeholders_found:
                    error_msg = "\n\nSecret with placeholder values is in base kustomization:\n"
                    error_msg += f"File: {kustomization_path.relative_to(PROJECT_ROOT)}\n"
                    error_msg += f"Secret: {secret_path.relative_to(PROJECT_ROOT)}\n"
                    error_msg += "\nPlaceholders found:\n"
                    for p in placeholders_found:
                        error_msg += f"  - {p['key']}: {p['value']}\n"
                    error_msg += "\nSecurity Risk: Applying base directly creates live secrets with placeholder values!\n"
                    error_msg += "\nFix options:"
                    error_msg += "\n  1. Remove 'secret.yaml' from base/kustomization.yaml resources"
                    error_msg += "\n  2. Replace with ExternalSecret template (recommended)"
                    error_msg += "\n  3. Gate behind opt-in component\n"

                    pytest.fail(error_msg)

    def test_openfga_deployment_has_required_secret_key(self):
        """
        RED: OpenFGA deployment references openfga-datastore-uri key that doesn't exist.
        GREEN: Secret should include openfga-datastore-uri key.

        Issue: openfga-deployment.yaml:88 expects openfga-datastore-uri
        Issue: secret.yaml doesn't define this key
        Fix: Add openfga-datastore-uri to secret or use constructed URI
        """
        openfga_deployment_path = DEPLOYMENTS_BASE / "openfga-deployment.yaml"
        secret_path = DEPLOYMENTS_BASE / "secret.yaml"

        if not openfga_deployment_path.exists():
            pytest.skip(f"OpenFGA deployment not found: {openfga_deployment_path}")

        openfga_deployment = self._load_yaml_file(openfga_deployment_path)

        # Find the openfga-datastore-uri secret reference
        containers = openfga_deployment["spec"]["template"]["spec"]["containers"]

        references_datastore_uri = False
        for container in containers:
            env_vars = container.get("env", [])
            for env_var in env_vars:
                value_from = env_var.get("valueFrom", {})
                secret_key_ref = value_from.get("secretKeyRef", {})
                if secret_key_ref.get("key") == "openfga-datastore-uri":
                    references_datastore_uri = True
                    break

        if references_datastore_uri:
            # Check if secret has this key
            if secret_path.exists():
                secret = self._load_yaml_file(secret_path)
                string_data = secret.get("stringData", {})
                data = secret.get("data", {})

                if "openfga-datastore-uri" not in string_data and "openfga-datastore-uri" not in data:
                    error_msg = "\n\nOpenFGA deployment references missing secret key:\n"
                    error_msg += f"Deployment: {openfga_deployment_path.relative_to(PROJECT_ROOT)}\n"
                    error_msg += f"Secret: {secret_path.relative_to(PROJECT_ROOT)}\n"
                    error_msg += "\nMissing key: openfga-datastore-uri\n"
                    error_msg += "\nImpact: OpenFGA will crash on startup\n"
                    error_msg += "\nFix: Add to secret.yaml stringData:"
                    error_msg += (
                        '\n  openfga-datastore-uri: "postgres://postgres:password@postgres:5432/openfga?sslmode=disable"\n'
                    )
                    error_msg += "  (or use ExternalSecret for production)\n"

                    pytest.fail(error_msg)


@pytest.mark.xdist_group(name="testcriticalnamespaceissues")
class TestCriticalNamespaceIssues:
    """Test that production GKE overlay has consistent namespace references."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def _load_yaml_file(self, file_path: Path) -> dict[str, Any]:
        """Load YAML file and return parsed content."""
        with open(file_path, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def test_production_gke_namespace_consistency(self):
        """
        RED: Production GKE overlay has namespace mismatch.
        GREEN: All resources should use the same namespace.

        Issue: namespace.yaml creates 'production-mcp-server-langgraph'
        Issue: network-policy.yaml uses 'mcp-production'
        Issue: resource-quotas.yaml uses 'mcp-production'
        Fix: Align namespace names across all files
        """
        namespace_path = DEPLOYMENTS_PROD_GKE / "namespace.yaml"
        network_policy_path = DEPLOYMENTS_PROD_GKE / "network-policy.yaml"
        resource_quotas_path = DEPLOYMENTS_PROD_GKE / "resource-quotas.yaml"

        if not namespace_path.exists():
            pytest.skip(f"Production GKE overlay not found: {DEPLOYMENTS_PROD_GKE}")

        # Get the namespace name from namespace.yaml
        namespace_resource = self._load_yaml_file(namespace_path)
        expected_namespace = namespace_resource["metadata"]["name"]

        violations = []

        # Check network-policy.yaml
        if network_policy_path.exists():
            # NetworkPolicy file may contain multiple documents
            with open(network_policy_path) as f:
                docs = yaml.safe_load_all(f)
                for doc_idx, doc in enumerate(docs):
                    if doc and "metadata" in doc:
                        actual_namespace = doc["metadata"].get("namespace", "")
                        if actual_namespace and actual_namespace != expected_namespace:
                            violations.append(
                                {
                                    "file": "network-policy.yaml",
                                    "document": doc_idx,
                                    "kind": doc.get("kind", "Unknown"),
                                    "expected": expected_namespace,
                                    "actual": actual_namespace,
                                }
                            )

        # Check resource-quotas.yaml
        if resource_quotas_path.exists():
            with open(resource_quotas_path) as f:
                docs = yaml.safe_load_all(f)
                for doc_idx, doc in enumerate(docs):
                    if doc and "metadata" in doc:
                        actual_namespace = doc["metadata"].get("namespace", "")
                        if actual_namespace and actual_namespace != expected_namespace:
                            violations.append(
                                {
                                    "file": "resource-quotas.yaml",
                                    "document": doc_idx,
                                    "kind": doc.get("kind", "Unknown"),
                                    "expected": expected_namespace,
                                    "actual": actual_namespace,
                                }
                            )

        if violations:
            error_msg = "\n\nProduction GKE overlay has namespace mismatch:\n"
            error_msg += f"Expected namespace (from namespace.yaml): {expected_namespace}\n"
            for v in violations:
                error_msg += f"\n  File: {v['file']}"
                error_msg += f"\n    Kind: {v['kind']}"
                error_msg += f"\n    Actual namespace: {v['actual']}"
                error_msg += f"\n    Expected: {v['expected']}\n"
            error_msg += "\nImpact: NetworkPolicy and ResourceQuota not applied to actual namespace!\n"
            error_msg += f"\nFix: Change namespace references to '{expected_namespace}'\n"

            pytest.fail(error_msg)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
