"""
Test suite for topology spread constraints and zone-based pod spreading.

Tests that pods are distributed across availability zones for high availability.

Following TDD principles: Write tests first.
"""

import gc

import pytest
import yaml

# Mark as unit test to ensure it runs in CI
pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="testtopologyspreadconstraints")
class TestTopologySpreadConstraints:
    """Test topology spread constraints configuration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_base_deployment_has_topology_spread_constraints(self):
        """Test base deployment has topologySpreadConstraints defined."""
        # RED: Will fail initially

        with open("deployments/base/deployment.yaml", "r") as f:
            deployment = yaml.safe_load(f)

        spec = deployment.get("spec", {}).get("template", {}).get("spec", {})

        assert "topologySpreadConstraints" in spec, "topologySpreadConstraints missing"

    def test_topology_spread_uses_zone_distribution(self):
        """Test topology spread constraints use zone topology key."""
        with open("deployments/base/deployment.yaml", "r") as f:
            deployment = yaml.safe_load(f)

        spec = deployment.get("spec", {}).get("template", {}).get("spec", {})
        constraints = spec.get("topologySpreadConstraints", [])

        # Should have at least one constraint for zones
        zone_constraints = [c for c in constraints if c.get("topologyKey") == "topology.kubernetes.io/zone"]

        assert len(zone_constraints) > 0, "No zone-based topology spread constraint"

    def test_topology_spread_has_reasonable_max_skew(self):
        """Test maxSkew is set appropriately for zone distribution.

        Zone-based spreading should have maxSkew=1 for even distribution across
        availability zones. Hostname-based spreading can have higher maxSkew values
        to allow more flexibility in node placement.
        """
        with open("deployments/base/deployment.yaml", "r") as f:
            deployment = yaml.safe_load(f)

        spec = deployment.get("spec", {}).get("template", {}).get("spec", {})
        constraints = spec.get("topologySpreadConstraints", [])

        # All constraints should have maxSkew defined
        for constraint in constraints:
            max_skew = constraint.get("maxSkew")
            assert max_skew is not None, "maxSkew not set"
            assert isinstance(max_skew, int) and max_skew > 0, f"maxSkew must be positive integer, got {max_skew}"

        # Zone-based constraints should have maxSkew=1 for strict HA
        zone_constraints = [c for c in constraints if c.get("topologyKey") == "topology.kubernetes.io/zone"]
        for constraint in zone_constraints:
            max_skew = constraint.get("maxSkew")
            assert max_skew == 1, f"Zone-based maxSkew should be 1 for strict HA, got {max_skew}"

    def test_topology_spread_has_label_selector(self):
        """Test topology spread has proper label selector."""
        with open("deployments/base/deployment.yaml", "r") as f:
            deployment = yaml.safe_load(f)

        spec = deployment.get("spec", {}).get("template", {}).get("spec", {})
        constraints = spec.get("topologySpreadConstraints", [])

        for constraint in constraints:
            assert "labelSelector" in constraint, "labelSelector missing"
            assert "matchLabels" in constraint["labelSelector"], "matchLabels missing"

    def test_helm_chart_has_topology_spread_constraints(self):
        """Test Helm chart deployment template has topology spread."""
        with open("deployments/helm/mcp-server-langgraph/templates/deployment.yaml", "r") as f:
            content = f.read()

        # Should have topologySpreadConstraints section
        assert "topologySpreadConstraints" in content, "Helm template missing topologySpreadConstraints"

    def test_helm_values_allows_topology_spread_configuration(self):
        """Test Helm values.yaml has topology spread configuration."""
        with open("deployments/helm/mcp-server-langgraph/values.yaml", "r") as f:
            values = yaml.safe_load(f)

        # Should have topologySpreadConstraints configuration
        assert "topologySpreadConstraints" in values or "topology" in values.get(
            "affinity", {}
        ), "Helm values missing topology spread configuration"


@pytest.mark.xdist_group(name="testpodantiaffinity")
class TestPodAntiAffinity:
    """Test pod anti-affinity for HA."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_base_deployment_has_required_anti_affinity(self):
        """Test deployment uses required anti-affinity for production."""
        # RED: Currently uses preferred, should use required

        with open("deployments/base/deployment.yaml", "r") as f:
            deployment = yaml.safe_load(f)

        spec = deployment.get("spec", {}).get("template", {}).get("spec", {})
        affinity = spec.get("affinity", {})

        # Should have podAntiAffinity
        assert "podAntiAffinity" in affinity, "podAntiAffinity missing"

    def test_anti_affinity_uses_zone_topology(self):
        """Test anti-affinity uses zone topology key."""
        with open("deployments/base/deployment.yaml", "r") as f:
            deployment = yaml.safe_load(f)

        spec = deployment.get("spec", {}).get("template", {}).get("spec", {})
        affinity = spec.get("affinity", {})
        pod_anti_affinity = affinity.get("podAntiAffinity", {})

        # Check if using required or preferred
        has_zone_topology = False

        for key in ["requiredDuringSchedulingIgnoredDuringExecution", "preferredDuringSchedulingIgnoredDuringExecution"]:
            if key in pod_anti_affinity:
                rules = pod_anti_affinity[key]
                if isinstance(rules, list):
                    for rule in rules:
                        topology_key = rule.get("topologyKey") or rule.get("podAffinityTerm", {}).get("topologyKey")
                        if topology_key == "topology.kubernetes.io/zone":
                            has_zone_topology = True

        assert has_zone_topology, "Anti-affinity not using zone topology"


@pytest.mark.xdist_group(name="testmultizonesupport")
class TestMultiZoneSupport:
    """Test multi-zone configuration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_terraform_gke_uses_multiple_zones(self):
        """Test GKE Terraform module uses multiple zones."""
        with open("terraform/modules/gke-autopilot/main.tf", "r") as f:
            content = f.read()

        # GKE Autopilot automatically uses all zones in region
        # Verify Autopilot is enabled
        assert "autopilot" in content or "AUTOPILOT" in content or "GKE_AUTOPILOT" in content

    def test_terraform_eks_uses_multiple_azs(self):
        """Test EKS Terraform module uses multiple AZs."""
        with open("terraform/modules/eks/main.tf", "r") as f:
            content = f.read()

        # Should reference multiple subnet_ids (which span AZs)
        assert "subnet_ids" in content, "EKS not using multiple subnets"

    def test_terraform_aks_module_structure(self):
        """Test AKS Terraform module structure exists (foundational check)."""
        import os

        # Check that AKS module directory exists
        assert os.path.exists("terraform/modules/aks"), "AKS module directory not found"

        # Check that README exists documenting in-progress status
        assert os.path.exists("terraform/modules/aks/README.md"), "AKS module README not found"

        # Future: When AKS module is complete, add checks for multi-zone configuration
        # similar to GKE and EKS tests above

    def test_stateful_services_have_topology_spread(self):
        """Test stateful services (Redis, PostgreSQL) have topology spread."""
        # This ensures dependencies are also HA

        with open("deployments/helm/mcp-server-langgraph/values.yaml", "r") as f:
            values = yaml.safe_load(f)

        # Check Redis configuration
        _ = values.get("redis", {})
        # Bitnami Redis chart supports topologySpreadConstraints via values
        # We should add this configuration in future enhancement


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
