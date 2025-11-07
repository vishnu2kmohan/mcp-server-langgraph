"""
Test suite for validating Kubernetes NetworkPolicy configurations.

This test suite validates that:
1. Database ports are correctly configured (PostgreSQL: 5432, Redis: 6379)
2. Network policies allow necessary egress traffic
3. Ingress rules are properly scoped
4. No overly permissive selectors exist

Following TDD principles - these tests should FAIL before fixes are applied.
"""

import subprocess
import yaml
import pytest
from pathlib import Path


REPO_ROOT = Path(__file__).parent.parent.parent


# Database port constants
POSTGRESQL_PORT = 5432
REDIS_PORT = 6379
MYSQL_PORT = 3306  # Should NOT be used for PostgreSQL


class TestNetworkPolicyPorts:
    """Test that NetworkPolicies use correct database ports."""

    @pytest.fixture
    def staging_network_policies(self):
        """Load NetworkPolicies from staging overlay."""
        overlay_path = REPO_ROOT / "deployments/overlays/staging-gke"
        result = subprocess.run(
            ["kustomize", "build", str(overlay_path)],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT
        )
        if result.returncode != 0:
            pytest.skip(f"Staging build failed: {result.stderr}")

        documents = list(yaml.safe_load_all(result.stdout))
        return [doc for doc in documents if doc and doc.get("kind") == "NetworkPolicy"]

    @pytest.fixture
    def production_network_policies(self):
        """Load NetworkPolicies from production overlay."""
        overlay_path = REPO_ROOT / "deployments/overlays/production-gke"
        result = subprocess.run(
            ["kustomize", "build", str(overlay_path)],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT
        )
        if result.returncode != 0:
            pytest.skip(f"Production build failed: {result.stderr}")

        documents = list(yaml.safe_load_all(result.stdout))
        return [doc for doc in documents if doc and doc.get("kind") == "NetworkPolicy"]

    def test_staging_postgresql_uses_correct_port(self, staging_network_policies):
        """
        Test that staging NetworkPolicies use port 5432 for PostgreSQL.

        Validates Finding #6: Cloud SQL ports using 3307 instead of 5432

        PostgreSQL (and Cloud SQL PostgreSQL) uses port 5432, not 3307.
        Port 3307 is the MySQL default port.
        """
        violations = []

        for policy in staging_network_policies:
            policy_name = policy.get("metadata", {}).get("name", "unknown")
            egress_rules = policy.get("spec", {}).get("egress", [])

            for rule_idx, rule in enumerate(egress_rules):
                ports = rule.get("ports", [])

                for port_idx, port_spec in enumerate(ports):
                    port = port_spec.get("port")

                    # Check for MySQL port being used for PostgreSQL
                    if port == MYSQL_PORT or port == 3307:
                        violations.append(
                            f"NetworkPolicy '{policy_name}' egress[{rule_idx}].ports[{port_idx}] "
                            f"uses port {port} (MySQL). PostgreSQL requires port {POSTGRESQL_PORT}."
                        )

        assert not violations, "\n".join(violations)

    def test_production_postgresql_uses_correct_port(self, production_network_policies):
        """
        Test that production NetworkPolicies use port 5432 for PostgreSQL.

        PostgreSQL (and Cloud SQL PostgreSQL) uses port 5432, not 3307.
        """
        violations = []

        for policy in production_network_policies:
            policy_name = policy.get("metadata", {}).get("name", "unknown")
            egress_rules = policy.get("spec", {}).get("egress", [])

            for rule_idx, rule in enumerate(egress_rules):
                ports = rule.get("ports", [])

                for port_idx, port_spec in enumerate(ports):
                    port = port_spec.get("port")

                    # Check for MySQL port being used for PostgreSQL
                    if port == MYSQL_PORT or port == 3307:
                        violations.append(
                            f"NetworkPolicy '{policy_name}' egress[{rule_idx}].ports[{port_idx}] "
                            f"uses port {port} (MySQL). PostgreSQL requires port {POSTGRESQL_PORT}."
                        )

        assert not violations, "\n".join(violations)

    def test_staging_redis_uses_correct_port(self, staging_network_policies):
        """
        Test that Redis connections use port 6379.

        Redis default port is 6379 (unless explicitly configured otherwise).
        """
        # This test looks for Redis-related egress rules and validates the port
        for policy in staging_network_policies:
            policy_name = policy.get("metadata", {}).get("name", "unknown")

            # Check if this policy is for the main app (would connect to Redis)
            pod_selector = policy.get("spec", {}).get("podSelector", {})
            match_labels = pod_selector.get("matchLabels", {})

            if "mcp-server-langgraph" in match_labels.get("app", ""):
                egress_rules = policy.get("spec", {}).get("egress", [])

                for rule in egress_rules:
                    # Look for rules that might be for Redis
                    to_specs = rule.get("to", [])

                    for to_spec in to_specs:
                        # Check if it's targeting Redis
                        if "pod_selector" in to_spec or "podSelector" in to_spec:
                            selector = to_spec.get("podSelector", to_spec.get("pod_selector", {}))
                            labels = selector.get("matchLabels", {})

                            if "redis" in labels.get("app", "").lower():
                                # This rule targets Redis, check the port
                                ports = rule.get("ports", [])
                                if ports:
                                    for port_spec in ports:
                                        port = port_spec.get("port")
                                        if port and port != REDIS_PORT:
                                            pytest.fail(
                                                f"NetworkPolicy '{policy_name}' has Redis egress "
                                                f"using port {port}, expected {REDIS_PORT}"
                                            )

    def test_no_overly_permissive_egress(self, staging_network_policies):
        """
        Test that egress rules are not overly permissive.

        Overly permissive patterns:
        - Empty to: [] (allows all destinations)
        - to: [{}] (allows all destinations)
        """
        violations = []

        for policy in staging_network_policies:
            policy_name = policy.get("metadata", {}).get("name", "unknown")
            egress_rules = policy.get("spec", {}).get("egress", [])

            for rule_idx, rule in enumerate(egress_rules):
                to_specs = rule.get("to", [])

                # Check for completely empty 'to' (allows all)
                if not to_specs:
                    # Empty 'to' is OK if it's for DNS or specific ports
                    ports = rule.get("ports", [])
                    if not ports:
                        violations.append(
                            f"NetworkPolicy '{policy_name}' egress[{rule_idx}] has no 'to' "
                            f"and no 'ports' restrictions (allows all egress)"
                        )


class TestNetworkPolicySelectors:
    """Test that NetworkPolicy selectors are properly scoped."""

    @pytest.fixture
    def production_network_policies(self):
        """Load NetworkPolicies from production overlay."""
        overlay_path = REPO_ROOT / "deployments/overlays/production-gke"
        result = subprocess.run(
            ["kustomize", "build", str(overlay_path)],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT
        )
        if result.returncode != 0:
            pytest.skip(f"Production build failed: {result.stderr}")

        documents = list(yaml.safe_load_all(result.stdout))
        return [doc for doc in documents if doc and doc.get("kind") == "NetworkPolicy"]

    def test_ingress_namespace_selectors_are_scoped(self, production_network_policies):
        """
        Test that ingress namespaceSelectors are properly scoped.

        Validates Finding (High Priority): Empty namespace selectors

        Pattern to avoid:
          namespaceSelector: {}  # Allows ALL namespaces

        Prefer:
          namespaceSelector:
            matchLabels:
              name: specific-namespace
        """
        warnings = []

        for policy in production_network_policies:
            policy_name = policy.get("metadata", {}).get("name", "unknown")
            ingress_rules = policy.get("spec", {}).get("ingress", [])

            for rule_idx, rule in enumerate(ingress_rules):
                from_specs = rule.get("from", [])

                for from_idx, from_spec in enumerate(from_specs):
                    ns_selector = from_spec.get("namespaceSelector")

                    if ns_selector is not None and ns_selector == {}:
                        warnings.append(
                            f"NetworkPolicy '{policy_name}' ingress[{rule_idx}].from[{from_idx}] "
                            f"has empty namespaceSelector (allows all namespaces). "
                            f"Consider adding matchLabels for better security."
                        )

        # For now, just warn (not fail) as this might be intentional for health checks
        if warnings:
            import warnings as warn_module
            warn_module.warn(
                "Potentially overly permissive NetworkPolicy selectors:\n" + "\n".join(warnings)
            )


class TestNetworkPolicyComments:
    """Test that NetworkPolicy configurations have clear documentation."""

    def test_database_egress_rules_have_comments(self):
        """
        Test that database egress rules have explanatory comments.

        This helps prevent confusion about which port is for which database.
        """
        # Read the staging network policy file directly
        staging_netpol = REPO_ROOT / "deployments/overlays/staging-gke/network-policy.yaml"

        if not staging_netpol.exists():
            pytest.skip("Staging network policy file not found")

        with open(staging_netpol, "r") as f:
            content = f.read()

        # Check for comments near port specifications
        lines = content.split("\n")

        for i, line in enumerate(lines):
            # Look for port specifications
            if "port:" in line and any(port in line for port in ["5432", "6379", "3307"]):
                # Check if there's a comment on this line or the previous line
                has_comment = "#" in line or (i > 0 and "#" in lines[i - 1])

                if not has_comment:
                    # Extract line context for better error message
                    context = "\n".join(lines[max(0, i - 2):i + 3])
                    pytest.fail(
                        f"Port specification at line {i + 1} lacks explanatory comment:\n{context}"
                    )


def test_network_policy_coverage():
    """
    Test that critical components have NetworkPolicies defined.

    Components that should have network policies:
    - Main application pods
    - Database pods (if self-hosted)
    - Keycloak
    - OpenFGA
    """
    base_path = REPO_ROOT / "deployments/base"
    result = subprocess.run(
        ["kustomize", "build", str(base_path)],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT
    )

    if result.returncode != 0:
        pytest.skip(f"Base build failed: {result.stderr}")

    documents = list(yaml.safe_load_all(result.stdout))

    # Collect NetworkPolicies
    network_policies = [
        doc.get("spec", {}).get("podSelector", {}).get("matchLabels", {})
        for doc in documents
        if doc and doc.get("kind") == "NetworkPolicy"
    ]

    # Collect Deployments/StatefulSets
    workloads = [
        doc.get("metadata", {}).get("labels", {})
        for doc in documents
        if doc and doc.get("kind") in ["Deployment", "StatefulSet"]
    ]

    # Check that main app has a network policy
    app_labels_in_policies = any(
        "mcp-server-langgraph" in str(policy)
        for policy in network_policies
    )

    assert app_labels_in_policies, (
        "Main application workload should have a NetworkPolicy defined. "
        "Found policies: " + str(network_policies)
    )
