"""
Test suite for validating Service Account configuration and separation.

This test suite validates that:
1. Service Accounts follow principle of least privilege
2. Different components use separate Service Accounts
3. Workload Identity bindings are correctly configured
4. RBAC permissions are appropriately scoped

Following TDD principles - these tests should FAIL before fixes are applied.
"""

import gc
import subprocess
from collections import defaultdict
from pathlib import Path

import pytest
import yaml

# Mark as unit test to ensure it runs in CI
pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).parent.parent.parent


@pytest.mark.xdist_group(name="testserviceaccountseparation")
class TestServiceAccountSeparation:
    """Test that different components use separate Service Accounts."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def base_resources(self):
        """Load all base resources."""
        base_path = REPO_ROOT / "deployments/base"
        result = subprocess.run(["kustomize", "build", str(base_path)], capture_output=True, text=True, cwd=REPO_ROOT)
        if result.returncode != 0:
            pytest.skip(f"Base build failed: {result.stderr}")

        return list(yaml.safe_load_all(result.stdout))

    def test_components_use_separate_service_accounts(self, base_resources):
        """
        Test that different components use separate Service Accounts.

        Validates Finding (High Priority): Service Account separation

        Components that should have separate SAs:
        - Main application (mcp-server-langgraph)
        - PostgreSQL (if self-hosted)
        - Redis (if self-hosted)
        - Keycloak
        - OpenFGA
        - Qdrant

        After fix, each component should have its own ServiceAccount.
        """
        # Collect workloads and their service accounts
        workload_to_sa = {}

        for doc in base_resources:
            if doc is None or not isinstance(doc, dict):
                continue

            kind = doc.get("kind")
            if kind in ["Deployment", "StatefulSet"]:
                name = doc.get("metadata", {}).get("name", "unknown")
                sa = doc.get("spec", {}).get("template", {}).get("spec", {}).get("serviceAccountName")

                if sa:
                    workload_to_sa[name] = sa

        # Group by service account
        sa_to_workloads = defaultdict(list)
        for workload, sa in workload_to_sa.items():
            sa_to_workloads[sa].append(workload)

        # After fix: Each infrastructure component should have its own SA
        expected_separate_components = ["postgres", "redis", "keycloak", "openfga", "qdrant"]

        violations = []

        for component in expected_separate_components:
            # Find workloads for this component
            component_workloads = [w for w in workload_to_sa.keys() if component in w.lower()]

            if not component_workloads:
                continue  # Component not deployed

            # Each component workload should have its own SA
            for workload in component_workloads:
                sa = workload_to_sa[workload]

                # Check if SA is shared with other non-related workloads
                sharing_workloads = [w for w in sa_to_workloads[sa] if w != workload and component not in w.lower()]

                if sharing_workloads:
                    violations.append(
                        f"Component '{workload}' shares ServiceAccount '{sa}' with {sharing_workloads}. "
                        f"Each component should have its own SA for least-privilege access."
                    )

        # This test will FAIL initially (before implementing SA separation)
        assert not violations, "\n".join(violations)

    def test_service_accounts_exist_for_components(self, base_resources):
        """
        Test that ServiceAccount resources are defined for each component.

        After implementing SA separation, we should have:
        - postgres-sa
        - redis-sa
        - keycloak-sa
        - openfga-sa
        - qdrant-sa
        - mcp-server-langgraph (main app)
        """
        # Collect ServiceAccount names
        service_accounts = []
        for doc in base_resources:
            if doc is None or not isinstance(doc, dict):
                continue

            if doc.get("kind") == "ServiceAccount":
                name = doc.get("metadata", {}).get("name")
                if name:
                    service_accounts.append(name)

        # Expected SAs (after implementing separation)
        expected_sas = ["postgres-sa", "redis-sa", "keycloak-sa", "openfga-sa", "qdrant-sa"]

        # Check which components are actually deployed
        workloads = [
            doc.get("metadata", {}).get("name", "")
            for doc in base_resources
            if doc and doc.get("kind") in ["Deployment", "StatefulSet"]
        ]

        missing_sas = []
        for expected_sa in expected_sas:
            component = expected_sa.replace("-sa", "")

            # Check if component is deployed
            component_deployed = any(component in w.lower() for w in workloads)

            if component_deployed and expected_sa not in service_accounts:
                missing_sas.append(expected_sa)

        # This test will FAIL initially (before creating separate SAs)
        assert not missing_sas, (
            f"Missing ServiceAccounts for deployed components: {missing_sas}. " f"Found SAs: {service_accounts}"
        )


@pytest.mark.xdist_group(name="testworkloadidentitybindings")
class TestWorkloadIdentityBindings:
    """Test Workload Identity configuration for GKE."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def staging_service_accounts(self):
        """Load ServiceAccounts from staging overlay."""
        overlay_path = REPO_ROOT / "deployments/overlays/staging-gke"
        result = subprocess.run(["kustomize", "build", str(overlay_path)], capture_output=True, text=True, cwd=REPO_ROOT)
        if result.returncode != 0:
            pytest.skip(f"Staging build failed: {result.stderr}")

        documents = list(yaml.safe_load_all(result.stdout))
        return [doc for doc in documents if doc and doc.get("kind") == "ServiceAccount"]

    @pytest.fixture
    def production_service_accounts(self):
        """Load ServiceAccounts from production overlay."""
        overlay_path = REPO_ROOT / "deployments/overlays/production-gke"
        result = subprocess.run(["kustomize", "build", str(overlay_path)], capture_output=True, text=True, cwd=REPO_ROOT)
        if result.returncode != 0:
            pytest.skip(f"Production build failed: {result.stderr}")

        documents = list(yaml.safe_load_all(result.stdout))
        return [doc for doc in documents if doc and doc.get("kind") == "ServiceAccount"]

    def test_staging_workload_identity_annotation_format(self, staging_service_accounts):
        """
        Test that Workload Identity annotations use correct format.

        Format: iam.gke.io/gcp-service-account: <gsa>@<project>.iam.gserviceaccount.com
        """
        for sa in staging_service_accounts:
            annotations = sa.get("metadata", {}).get("annotations", {})
            wi_annotation = annotations.get("iam.gke.io/gcp-service-account")

            if wi_annotation:
                # Check format
                assert "@" in wi_annotation, (
                    f"ServiceAccount '{sa['metadata']['name']}' has invalid Workload Identity "
                    f"annotation: {wi_annotation}. Expected format: <gsa>@<project>.iam.gserviceaccount.com"
                )

                assert ".iam.gserviceaccount.com" in wi_annotation, (
                    f"ServiceAccount '{sa['metadata']['name']}' has invalid Workload Identity "
                    f"annotation: {wi_annotation}. Expected format: <gsa>@<project>.iam.gserviceaccount.com"
                )

                # Check for unsubstituted variables
                assert "${" not in wi_annotation and "$(" not in wi_annotation, (
                    f"ServiceAccount '{sa['metadata']['name']}' has unsubstituted variable "
                    f"in Workload Identity annotation: {wi_annotation}"
                )

    def test_production_workload_identity_annotation_format(self, production_service_accounts):
        """
        Test that Workload Identity annotations use correct format in production.
        """
        for sa in production_service_accounts:
            annotations = sa.get("metadata", {}).get("annotations", {})
            wi_annotation = annotations.get("iam.gke.io/gcp-service-account")

            if wi_annotation:
                # Check format
                assert "@" in wi_annotation, (
                    f"ServiceAccount '{sa['metadata']['name']}' has invalid Workload Identity "
                    f"annotation: {wi_annotation}. Expected format: <gsa>@<project>.iam.gserviceaccount.com"
                )

                assert ".iam.gserviceaccount.com" in wi_annotation, (
                    f"ServiceAccount '{sa['metadata']['name']}' has invalid Workload Identity "
                    f"annotation: {wi_annotation}. Expected format: <gsa>@<project>.iam.gserviceaccount.com"
                )

                # Check for unsubstituted variables
                assert "${" not in wi_annotation and "$(" not in wi_annotation, (
                    f"ServiceAccount '{sa['metadata']['name']}' has unsubstituted variable "
                    f"in Workload Identity annotation: {wi_annotation}"
                )

    def test_critical_components_have_workload_identity(self, staging_service_accounts):
        """
        Test that components needing GCP access have Workload Identity configured.

        Components that need GCP access:
        - Main app (for Secret Manager, Cloud SQL, etc.)
        - OpenFGA (for Cloud SQL)
        - Keycloak (for Cloud SQL)
        - External Secrets Operator
        """
        critical_sa_patterns = ["mcp-server-langgraph", "openfga", "keycloak", "external-secrets"]

        for pattern in critical_sa_patterns:
            matching_sas = [sa for sa in staging_service_accounts if pattern in sa.get("metadata", {}).get("name", "").lower()]

            for sa in matching_sas:
                annotations = sa.get("metadata", {}).get("annotations", {})
                wi_annotation = annotations.get("iam.gke.io/gcp-service-account")

                assert wi_annotation, (
                    f"ServiceAccount '{sa['metadata']['name']}' is missing Workload Identity "
                    f"annotation 'iam.gke.io/gcp-service-account'. This component needs GCP access."
                )


@pytest.mark.xdist_group(name="testrbacconfiguration")
class TestRBACConfiguration:
    """Test RBAC (Roles and RoleBindings) configuration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def base_resources(self):
        """Load all base resources."""
        base_path = REPO_ROOT / "deployments/base"
        result = subprocess.run(["kustomize", "build", str(base_path)], capture_output=True, text=True, cwd=REPO_ROOT)
        if result.returncode != 0:
            pytest.skip(f"Base build failed: {result.stderr}")

        return list(yaml.safe_load_all(result.stdout))

    def test_roles_follow_least_privilege(self, base_resources):
        """
        Test that RBAC Roles follow principle of least privilege.

        Checks for overly permissive patterns:
        - verbs: ["*"] (all verbs)
        - resources: ["*"] (all resources)
        - apiGroups: ["*"] (all API groups)
        """
        violations = []

        for doc in base_resources:
            if doc is None or not isinstance(doc, dict):
                continue

            kind = doc.get("kind")
            if kind in ["Role", "ClusterRole"]:
                name = doc.get("metadata", {}).get("name", "unknown")
                rules = doc.get("rules", [])

                for rule_idx, rule in enumerate(rules):
                    # Check for wildcard verbs
                    if "*" in rule.get("verbs", []):
                        violations.append(f"{kind} '{name}' rule[{rule_idx}] uses wildcard verbs: {rule['verbs']}")

                    # Check for wildcard resources
                    if "*" in rule.get("resources", []):
                        violations.append(f"{kind} '{name}' rule[{rule_idx}] uses wildcard resources: {rule['resources']}")

                    # Check for wildcard API groups
                    if "*" in rule.get("apiGroups", []):
                        violations.append(f"{kind} '{name}' rule[{rule_idx}] uses wildcard apiGroups: {rule['apiGroups']}")

        if violations:
            import warnings

            warnings.warn("Potentially overly permissive RBAC rules (consider restricting):\n" + "\n".join(violations))

    def test_role_bindings_reference_existing_service_accounts(self, base_resources):
        """
        Test that RoleBindings reference ServiceAccounts that exist.
        """
        # Collect ServiceAccounts
        service_accounts = set()
        for doc in base_resources:
            if doc and doc.get("kind") == "ServiceAccount":
                name = doc.get("metadata", {}).get("name")
                namespace = doc.get("metadata", {}).get("namespace", "default")
                if name:
                    service_accounts.add((namespace, name))

        # Check RoleBindings
        violations = []
        for doc in base_resources:
            if doc is None or not isinstance(doc, dict):
                continue

            kind = doc.get("kind")
            if kind in ["RoleBinding", "ClusterRoleBinding"]:
                binding_name = doc.get("metadata", {}).get("name", "unknown")
                subjects = doc.get("subjects", [])

                for subject in subjects:
                    if subject.get("kind") == "ServiceAccount":
                        sa_name = subject.get("name")
                        sa_namespace = subject.get("namespace", "default")

                        if (sa_namespace, sa_name) not in service_accounts:
                            violations.append(
                                f"{kind} '{binding_name}' references non-existent "
                                f"ServiceAccount '{sa_name}' in namespace '{sa_namespace}'"
                            )

        assert not violations, "\n".join(violations)
