"""
Comprehensive validation tests for all Kubernetes best practices implementations.

Tests all 11 items to ensure configurations are valid and complete.
"""

import glob
import os
from pathlib import Path

import pytest
import yaml


class TestPhase1Validation:
    """Validate Phase 1: High Availability & Data Protection."""

    def test_azure_database_terraform_module_valid(self):
        """Test Azure Database Terraform module is valid."""
        module_path = "terraform/modules/azure-database"

        # Check all required files exist
        assert os.path.exists(f"{module_path}/main.tf")
        assert os.path.exists(f"{module_path}/variables.tf")
        assert os.path.exists(f"{module_path}/outputs.tf")
        assert os.path.exists(f"{module_path}/versions.tf")

        # Check main.tf has required resources
        with open(f"{module_path}/main.tf", "r") as f:
            content = f.read()
            assert "azurerm_postgresql_flexible_server" in content
            assert "high_availability" in content
            assert "geo_redundant_backup" in content
            assert "azurerm_monitor_metric_alert" in content

    def test_helm_external_database_configuration(self):
        """Test Helm chart has external database configuration."""
        with open("deployments/helm/mcp-server-langgraph/values.yaml", "r") as f:
            values = yaml.safe_load(f)

        postgres = values.get("postgresql", {})
        assert "external" in postgres
        assert "cloud" in postgres["external"]
        assert "cloudSql" in postgres["external"]["cloud"]
        assert "rds" in postgres["external"]["cloud"]
        assert "azure" in postgres["external"]["cloud"]

    def test_topology_spread_constraints_in_base(self):
        """Test topology spread constraints in base deployment."""
        with open("deployments/base/deployment.yaml", "r") as f:
            deployment = yaml.safe_load(f)

        spec = deployment["spec"]["template"]["spec"]
        assert "topologySpreadConstraints" in spec

        constraints = spec["topologySpreadConstraints"]
        assert len(constraints) >= 2

        # Check zone constraint
        zone_constraint = [c for c in constraints if c["topologyKey"] == "topology.kubernetes.io/zone"][0]
        assert zone_constraint["maxSkew"] == 1
        assert zone_constraint["whenUnsatisfiable"] == "DoNotSchedule"

    def test_topology_spread_in_helm_values(self):
        """Test topology spread constraints in Helm values."""
        with open("deployments/helm/mcp-server-langgraph/values.yaml", "r") as f:
            values = yaml.safe_load(f)

        assert "topologySpreadConstraints" in values
        assert len(values["topologySpreadConstraints"]) >= 2

    def test_velero_configurations_exist(self):
        """Test Velero configurations for all cloud providers."""
        assert os.path.exists("deployments/backup/velero-values-aws.yaml")
        assert os.path.exists("deployments/backup/velero-values-gcp.yaml")
        assert os.path.exists("deployments/backup/velero-values-azure.yaml")
        assert os.path.exists("deployments/backup/backup-schedule.yaml")
        assert os.path.exists("deployments/backup/RESTORE_PROCEDURE.md")

    def test_velero_backup_schedules(self):
        """Test Velero backup schedules are configured."""
        with open("deployments/backup/backup-schedule.yaml", "r") as f:
            docs = list(yaml.safe_load_all(f))

        # Should have daily, weekly, monthly schedules
        schedules = [d for d in docs if d.get("kind") == "Schedule"]
        assert len(schedules) >= 2


class TestPhase2Validation:
    """Validate Phase 2: Security Hardening."""

    def test_istio_enabled_in_helm_values(self):
        """Test Istio service mesh is enabled in Helm values."""
        with open("deployments/helm/mcp-server-langgraph/values.yaml", "r") as f:
            values = yaml.safe_load(f)

        assert values["serviceMesh"]["enabled"] is True
        assert values["serviceMesh"]["istio"]["injection"] == "enabled"
        assert values["serviceMesh"]["istio"]["peerAuthentication"]["enabled"] is True
        assert values["serviceMesh"]["istio"]["peerAuthentication"]["mode"] == "STRICT"

    def test_istio_config_has_mtls_strict(self):
        """Test Istio configuration has mTLS STRICT mode."""
        with open("deployments/service-mesh/istio/istio-config.yaml", "r") as f:
            docs = list(yaml.safe_load_all(f))

        # Find PeerAuthentication
        peer_auth = [d for d in docs if d.get("kind") == "PeerAuthentication"][0]
        assert peer_auth["spec"]["mtls"]["mode"] == "STRICT"

    def test_pod_security_standards_in_namespace(self):
        """Test Pod Security Standards are enforced."""
        with open("deployments/base/namespace.yaml", "r") as f:
            namespace = yaml.safe_load(f)

        labels = namespace["metadata"]["labels"]
        assert labels.get("pod-security.kubernetes.io/enforce") == "restricted"
        assert labels.get("pod-security.kubernetes.io/audit") == "restricted"
        assert labels.get("pod-security.kubernetes.io/warn") == "restricted"

    def test_istio_injection_enabled_in_namespace(self):
        """Test Istio injection is enabled in namespace."""
        with open("deployments/base/namespace.yaml", "r") as f:
            namespace = yaml.safe_load(f)

        labels = namespace["metadata"]["labels"]
        assert labels.get("istio-injection") == "enabled"

    def test_network_policies_exist_for_all_services(self):
        """Test network policies exist for all services."""
        assert os.path.exists("deployments/base/postgres-networkpolicy.yaml")
        assert os.path.exists("deployments/base/redis-networkpolicy.yaml")
        assert os.path.exists("deployments/base/keycloak-networkpolicy.yaml")
        assert os.path.exists("deployments/base/openfga-networkpolicy.yaml")

    def test_network_policies_have_ingress_egress(self):
        """Test network policies have both ingress and egress rules."""
        policies = [
            "deployments/base/postgres-networkpolicy.yaml",
            "deployments/base/redis-networkpolicy.yaml",
            "deployments/base/keycloak-networkpolicy.yaml",
            "deployments/base/openfga-networkpolicy.yaml",
        ]

        for policy_file in policies:
            with open(policy_file, "r") as f:
                policy = yaml.safe_load(f)

            assert "Ingress" in policy["spec"]["policyTypes"]
            assert "Egress" in policy["spec"]["policyTypes"]
            assert "ingress" in policy["spec"]
            assert "egress" in policy["spec"]


class TestPhase3Validation:
    """Validate Phase 3: Observability & Cost Management."""

    def test_loki_stack_configuration_exists(self):
        """Test Loki stack configuration exists."""
        assert os.path.exists("deployments/monitoring/loki-stack-values.yaml")

        with open("deployments/monitoring/loki-stack-values.yaml", "r") as f:
            values = yaml.safe_load(f)

        assert values["loki"]["enabled"] is True
        assert values["promtail"]["enabled"] is True
        assert values["loki"]["persistence"]["enabled"] is True

    def test_loki_retention_configured(self):
        """Test Loki has 30-day retention."""
        with open("deployments/monitoring/loki-stack-values.yaml", "r") as f:
            values = yaml.safe_load(f)

        retention = values["loki"]["config"]["chunk_store_config"]["max_look_back_period"]
        assert "720h" in retention or "30d" in retention

    def test_resource_quota_exists(self):
        """Test ResourceQuota configuration exists."""
        assert os.path.exists("deployments/base/resourcequota.yaml")

        with open("deployments/base/resourcequota.yaml", "r") as f:
            docs = list(yaml.safe_load_all(f))

        quotas = [d for d in docs if d.get("kind") == "ResourceQuota"]
        assert len(quotas) >= 1

    def test_limit_range_exists(self):
        """Test LimitRange configuration exists."""
        assert os.path.exists("deployments/base/limitrange.yaml")

        with open("deployments/base/limitrange.yaml", "r") as f:
            limitrange = yaml.safe_load(f)

        assert limitrange["kind"] == "LimitRange"
        assert len(limitrange["spec"]["limits"]) >= 2

    def test_resource_quota_has_cpu_memory_limits(self):
        """Test ResourceQuota has CPU and memory limits."""
        with open("deployments/base/resourcequota.yaml", "r") as f:
            docs = list(yaml.safe_load_all(f))

        quota = [d for d in docs if d.get("kind") == "ResourceQuota"][0]
        hard = quota["spec"]["hard"]

        assert "requests.cpu" in hard
        assert "limits.cpu" in hard
        assert "requests.memory" in hard
        assert "limits.memory" in hard

    def test_kubecost_configuration_exists(self):
        """Test Kubecost configuration exists."""
        assert os.path.exists("deployments/monitoring/kubecost-values.yaml")

        with open("deployments/monitoring/kubecost-values.yaml", "r") as f:
            values = yaml.safe_load(f)

        assert "kubecostProductConfigs" in values
        assert values["kubecostProductConfigs"]["clusterName"] == "production-mcp-server-langgraph"

    def test_kubecost_cloud_cost_enabled(self):
        """Test Kubecost has cloud cost monitoring enabled."""
        with open("deployments/monitoring/kubecost-values.yaml", "r") as f:
            values = yaml.safe_load(f)

        assert values.get("awsCloudCost", {}).get("enabled") is True
        assert values.get("gcpCloudCost", {}).get("enabled") is True
        assert values.get("azureCloudCost", {}).get("enabled") is True


class TestPhase4Validation:
    """Validate Phase 4: Infrastructure Optimization."""

    def test_karpenter_terraform_module_exists(self):
        """Test Karpenter Terraform module exists."""
        module_path = "terraform/modules/karpenter"

        assert os.path.exists(f"{module_path}/main.tf")
        assert os.path.exists(f"{module_path}/variables.tf")
        assert os.path.exists(f"{module_path}/outputs.tf")

    def test_karpenter_iam_roles_configured(self):
        """Test Karpenter IAM roles are configured."""
        with open("terraform/modules/karpenter/main.tf", "r") as f:
            content = f.read()

        assert "aws_iam_role" in content
        assert "karpenter_controller" in content
        assert "karpenter_node" in content

    def test_karpenter_provisioners_exist(self):
        """Test Karpenter provisioner configurations exist."""
        assert os.path.exists("deployments/karpenter/provisioner-default.yaml")

        with open("deployments/karpenter/provisioner-default.yaml", "r") as f:
            docs = list(yaml.safe_load_all(f))

        provisioners = [d for d in docs if d.get("kind") == "Provisioner"]
        assert len(provisioners) >= 2  # At least default and spot

    def test_karpenter_spot_interruption_handling(self):
        """Test Karpenter has spot interruption handling."""
        with open("terraform/modules/karpenter/main.tf", "r") as f:
            content = f.read()

        assert "aws_sqs_queue" in content
        assert "aws_cloudwatch_event_rule" in content
        assert "spot_interruption" in content.lower()

    def test_vpa_configurations_exist(self):
        """Test VPA configurations exist for all stateful services."""
        assert os.path.exists("deployments/base/postgres-vpa.yaml")
        assert os.path.exists("deployments/base/redis-vpa.yaml")
        assert os.path.exists("deployments/base/keycloak-vpa.yaml")

    def test_vpa_update_modes_configured(self):
        """Test VPA update modes are properly configured."""
        vpa_files = [
            ("deployments/base/postgres-vpa.yaml", "Recreate"),
            ("deployments/base/redis-vpa.yaml", "Auto"),
            ("deployments/base/keycloak-vpa.yaml", "Recreate"),
        ]

        for vpa_file, expected_mode in vpa_files:
            with open(vpa_file, "r") as f:
                vpa = yaml.safe_load(f)

            assert vpa["kind"] == "VerticalPodAutoscaler"
            assert vpa["spec"]["updatePolicy"]["updateMode"] == expected_mode

    def test_vpa_resource_constraints(self):
        """Test VPA has min/max resource constraints."""
        with open("deployments/base/postgres-vpa.yaml", "r") as f:
            vpa = yaml.safe_load(f)

        policy = vpa["spec"]["resourcePolicy"]["containerPolicies"][0]
        assert "minAllowed" in policy
        assert "maxAllowed" in policy
        assert "cpu" in policy["minAllowed"]
        assert "memory" in policy["minAllowed"]


class TestDocumentation:
    """Validate documentation is complete."""

    def test_implementation_guide_exists(self):
        """Test implementation guide exists."""
        assert os.path.exists("docs/kubernetes-best-practices-implementation.md")

    def test_implementation_summary_exists(self):
        """Test implementation summary exists."""
        assert os.path.exists("docs/IMPLEMENTATION_SUMMARY.md")

    def test_restore_procedure_exists(self):
        """Test restore procedure documentation exists."""
        assert os.path.exists("deployments/backup/RESTORE_PROCEDURE.md")


class TestYAMLSyntax:
    """Validate all YAML files have correct syntax."""

    def test_all_yaml_files_valid(self):
        """Test all YAML files can be parsed."""
        yaml_files = []

        # Find all YAML files
        for pattern in ["deployments/**/*.yaml", "deployments/**/*.yml"]:
            yaml_files.extend(glob.glob(pattern, recursive=True))

        errors = []
        for yaml_file in yaml_files:
            try:
                with open(yaml_file, "r") as f:
                    # Try to load all documents
                    list(yaml.safe_load_all(f))
            except yaml.YAMLError as e:
                errors.append(f"{yaml_file}: {e}")

        assert len(errors) == 0, "YAML syntax errors:\n" + "\n".join(errors)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
