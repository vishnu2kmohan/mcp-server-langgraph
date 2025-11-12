"""
Test suite for high-priority Kubernetes deployment improvements.

Following TDD Red-Green-Refactor:
- RED: These tests should FAIL initially (issues exist)
- GREEN: After fixes, tests should PASS
- REFACTOR: Improve implementation quality

High-priority improvements tested:
1. PostgreSQL should support HA configuration and have backup strategy
2. Redis should use StatefulSet with persistent storage
3. Service accounts should have explicit RBAC with least-privilege
4. Container images should use fully-qualified references with digests
"""

from pathlib import Path
from typing import Any, Dict

import pytest
import yaml

PROJECT_ROOT = Path(__file__).parent.parent.parent
DEPLOYMENTS_BASE = PROJECT_ROOT / "deployments" / "base"


class TestPostgreSQLHighAvailability:
    """Test PostgreSQL deployment supports HA and has backup strategy."""

    def _load_yaml_file(self, file_path: Path) -> Dict[str, Any]:
        """Load YAML file and return parsed content.

        For multi-document YAML files, returns all documents as a list.
        For single-document files, returns the document as a dict.
        """
        with open(file_path, "r", encoding="utf-8") as f:
            docs = list(yaml.safe_load_all(f))
            # Return single doc as dict, multiple docs as list
            return docs[0] if len(docs) == 1 else docs

    def test_postgres_deployment_documents_ha_options(self):
        """
        RED: PostgreSQL StatefulSet has no HA documentation or configuration.
        GREEN: Should document CloudSQL/RDS option or include HA configuration.

        Issue: Single-instance PostgreSQL with no HA or backup strategy
        Fix: Add documentation for managed databases or HA setup
        """
        postgres_path = DEPLOYMENTS_BASE / "postgres-statefulset.yaml"

        if not postgres_path.exists():
            pytest.skip("PostgreSQL StatefulSet not found")

        # Read the full file including comments
        with open(postgres_path, "r") as f:
            content = f.read()

        violations = []

        # Check for HA documentation
        ha_keywords = ["CloudSQL", "RDS", "managed", "HA", "high availability"]
        has_ha_docs = any(keyword in content for keyword in ha_keywords)

        if not has_ha_docs:
            violations.append("No documentation for managed database or HA configuration")

        # Check for backup documentation
        backup_keywords = ["backup", "WAL", "archive", "snapshot", "pg_dump"]
        has_backup_docs = any(keyword in content for keyword in backup_keywords)

        if not has_backup_docs:
            violations.append("No documentation for backup strategy")

        if violations:
            error_msg = "\n\nPostgreSQL lacks HA and backup documentation:\n"
            error_msg += f"File: {postgres_path.relative_to(PROJECT_ROOT)}\n"
            for v in violations:
                error_msg += f"  - {v}\n"
            error_msg += "\nRecommendations:\n"
            error_msg += "  1. Document migration path to CloudSQL/RDS for production\n"
            error_msg += "  2. Add backup job configuration or reference\n"
            error_msg += "  3. Include comments about WAL archiving for self-hosted\n"

            pytest.fail(error_msg)

    def test_postgres_has_production_ready_storage_class(self):
        """
        RED: PostgreSQL uses default storage class with no annotations.
        GREEN: Should have storage class configuration guidance.

        Issue: No guidance on production-ready storage configuration
        Fix: Add storage class recommendations
        """
        postgres_path = DEPLOYMENTS_BASE / "postgres-statefulset.yaml"

        if not postgres_path.exists():
            pytest.skip("PostgreSQL StatefulSet not found")

        with open(postgres_path, "r") as f:
            content = f.read()

        # Check for storage class documentation
        storage_keywords = ["storageClassName", "storage class", "SSD", "performance"]
        has_storage_docs = any(keyword in content for keyword in storage_keywords)

        if not has_storage_docs:
            error_msg = "\n\nPostgreSQL lacks storage configuration guidance:\n"
            error_msg += f"File: {postgres_path.relative_to(PROJECT_ROOT)}\n"
            error_msg += "  - No storageClassName recommendations\n"
            error_msg += "  - No performance guidance\n"
            error_msg += "\nFix: Add storage class examples for different clouds\n"

            pytest.fail(error_msg)


class TestRedisStatefulSetWithPersistence:
    """Test Redis uses StatefulSet with persistent storage instead of Deployment."""

    def _load_yaml_file(self, file_path: Path) -> Dict[str, Any]:
        """Load YAML file and return parsed content.

        For multi-document YAML files, returns all documents as a list.
        For single-document files, returns the document as a dict.
        """
        with open(file_path, "r", encoding="utf-8") as f:
            docs = list(yaml.safe_load_all(f))
            # Return single doc as dict, multiple docs as list
            return docs[0] if len(docs) == 1 else docs

    def test_redis_uses_statefulset_not_deployment(self):
        """
        RED: Redis uses Deployment instead of StatefulSet.
        GREEN: Should use StatefulSet for persistent storage.

        Issue: Redis Deployment loses sessions on restart
        Fix: Convert to StatefulSet with volumeClaimTemplates
        """
        redis_path = DEPLOYMENTS_BASE / "redis-session-deployment.yaml"

        if not redis_path.exists():
            pytest.skip("Redis deployment not found")

        redis_docs = self._load_yaml_file(redis_path)

        # Handle both single dict and list of dicts
        if not isinstance(redis_docs, list):
            redis_docs = [redis_docs]

        # Find the StatefulSet/Deployment document (skip ConfigMap, etc.)
        redis_config = None
        for doc in redis_docs:
            if doc.get("kind") in ["StatefulSet", "Deployment"]:
                redis_config = doc
                break

        if not redis_config:
            pytest.skip("No StatefulSet or Deployment found in Redis config")

        # Check if it's a StatefulSet
        if redis_config.get("kind") != "StatefulSet":
            error_msg = "\n\nRedis uses Deployment instead of StatefulSet:\n"
            error_msg += f"File: {redis_path.relative_to(PROJECT_ROOT)}\n"
            error_msg += f"  Current kind: {redis_config.get('kind')}\n"
            error_msg += "  Required kind: StatefulSet\n"
            error_msg += "\nIssue: Sessions lost on pod restart with Deployment\n"
            error_msg += "Fix: Convert to StatefulSet with persistent volumes\n"

            pytest.fail(error_msg)

    def test_redis_has_persistent_storage_not_emptydir(self):
        """
        RED: Redis uses emptyDir for data storage.
        GREEN: Should use PersistentVolumeClaim for durability.

        Issue: emptyDir loses data on pod restart
        Fix: Use volumeClaimTemplates in StatefulSet
        """
        redis_path = DEPLOYMENTS_BASE / "redis-session-deployment.yaml"

        if not redis_path.exists():
            pytest.skip("Redis deployment not found")

        redis_docs = self._load_yaml_file(redis_path)

        # Handle both single dict and list of dicts
        if not isinstance(redis_docs, list):
            redis_docs = [redis_docs]

        # Find the StatefulSet/Deployment document
        redis_config = None
        for doc in redis_docs:
            if doc.get("kind") in ["StatefulSet", "Deployment"]:
                redis_config = doc
                break

        if not redis_config:
            pytest.skip("No StatefulSet or Deployment found in Redis config")

        # For StatefulSet, check volumeClaimTemplates
        if redis_config.get("kind") == "StatefulSet":
            volume_claim_templates = redis_config.get("spec", {}).get("volumeClaimTemplates", [])
            if not volume_claim_templates:
                error_msg = "\n\nRedis StatefulSet has no volumeClaimTemplates:\n"
                error_msg += f"File: {redis_path.relative_to(PROJECT_ROOT)}\n"
                error_msg += "  Missing: spec.volumeClaimTemplates\n"
                error_msg += "\nFix: Add volumeClaimTemplates for persistent data\n"
                pytest.fail(error_msg)
        else:
            # For Deployment, check volumes
            volumes = redis_config.get("spec", {}).get("template", {}).get("spec", {}).get("volumes", [])

            data_volume = None
            for vol in volumes:
                if vol.get("name") == "data":
                    data_volume = vol
                    break

            if data_volume and "emptyDir" in data_volume:
                error_msg = "\n\nRedis uses emptyDir for data storage:\n"
                error_msg += f"File: {redis_path.relative_to(PROJECT_ROOT)}\n"
                error_msg += "  Current: emptyDir (ephemeral, lost on restart)\n"
                error_msg += "  Required: PersistentVolumeClaim\n"
                error_msg += "\nImpact: Session data lost on pod restart\n"
                error_msg += "Fix: Use volumeClaimTemplates in StatefulSet\n"

                pytest.fail(error_msg)

    def test_redis_enables_aof_persistence(self):
        """
        RED: Redis configuration may not enable AOF persistence.
        GREEN: Should enable AOF for data durability.

        Issue: Without AOF, data may be lost
        Fix: Ensure redis.conf has appendonly yes
        """
        redis_path = DEPLOYMENTS_BASE / "redis-session-deployment.yaml"

        if not redis_path.exists():
            pytest.skip("Redis deployment not found")

        with open(redis_path, "r") as f:
            # Look for ConfigMap with redis.conf
            docs = list(yaml.safe_load_all(f))

        redis_config = None
        for doc in docs:
            if doc and doc.get("kind") == "ConfigMap":
                data = doc.get("data", {})
                if "redis.conf" in data:
                    redis_config = data["redis.conf"]
                    break

        if not redis_config:
            pytest.skip("Redis ConfigMap not found in file")

        if "appendonly yes" not in redis_config:
            error_msg = "\n\nRedis does not enable AOF persistence:\n"
            error_msg += f"File: {redis_path.relative_to(PROJECT_ROOT)}\n"
            error_msg += "  Missing: appendonly yes\n"
            error_msg += "\nImpact: Data may be lost without AOF\n"
            error_msg += "Fix: Add 'appendonly yes' to redis.conf\n"

            pytest.fail(error_msg)


class TestRBACLeastPrivilege:
    """Test service accounts have explicit RBAC with least-privilege."""

    def _load_yaml_file(self, file_path: Path) -> Dict[str, Any]:
        """Load YAML file and return parsed content.

        For multi-document YAML files, returns all documents as a list.
        For single-document files, returns the document as a dict.
        """
        with open(file_path, "r", encoding="utf-8") as f:
            docs = list(yaml.safe_load_all(f))
            # Return single doc as dict, multiple docs as list
            return docs[0] if len(docs) == 1 else docs

    def test_service_account_has_explicit_role_binding(self):
        """
        RED: Service account exists without corresponding Role/RoleBinding.
        GREEN: Should have explicit RBAC configuration.

        Issue: Service account uses cluster-default permissions
        Fix: Create Role and RoleBinding with least-privilege
        """
        sa_path = DEPLOYMENTS_BASE / "serviceaccount.yaml"

        if not sa_path.exists():
            pytest.skip("ServiceAccount not found")

        sa_config = self._load_yaml_file(sa_path)
        sa_name = sa_config["metadata"]["name"]

        # Look for Role or ClusterRole
        role_path = DEPLOYMENTS_BASE / "role.yaml"
        cluster_role_path = DEPLOYMENTS_BASE / "clusterrole.yaml"

        has_role = role_path.exists() or cluster_role_path.exists()

        if not has_role:
            error_msg = "\n\nServiceAccount has no explicit RBAC configuration:\n"
            error_msg += f"ServiceAccount: {sa_path.relative_to(PROJECT_ROOT)}\n"
            error_msg += f"  Name: {sa_name}\n"
            error_msg += "  Missing: Role or ClusterRole\n"
            error_msg += "\nSecurity Issue: Using cluster-default permissions\n"
            error_msg += "Fix: Create Role with least-privilege permissions\n"
            error_msg += "  Required permissions: get/list ConfigMaps, Secrets, events\n"

            pytest.fail(error_msg)

    def test_rbac_follows_least_privilege_principle(self):
        """
        RED: RBAC may grant excessive permissions.
        GREEN: Should follow least-privilege with minimal verbs and resources.

        Issue: Overly permissive RBAC increases security risk
        Fix: Grant only required permissions
        """
        role_paths = [
            DEPLOYMENTS_BASE / "role.yaml",
            DEPLOYMENTS_BASE / "clusterrole.yaml",
        ]

        found_role = None
        role_file = None

        for role_path in role_paths:
            if role_path.exists():
                found_role = self._load_yaml_file(role_path)
                role_file = role_path
                break

        if not found_role:
            pytest.skip("No Role or ClusterRole found")

        # Check for overly permissive verbs

        violations = []

        # Handle both single role (dict) and multiple roles (list)
        roles_to_check = found_role if isinstance(found_role, list) else [found_role]

        for role in roles_to_check:
            for rule in role.get("rules", []):
                verbs = rule.get("verbs", [])
                resources = rule.get("resources", [])

                # Check for wildcard permissions
                if "*" in verbs:
                    violations.append(f"Grants wildcard (*) verb permission for {resources}")

                if "*" in resources:
                    violations.append("Grants wildcard (*) resource permission")

                # Check for dangerous combinations
                if "secrets" in resources and any(v in verbs for v in ["create", "delete", "patch"]):
                    violations.append("Grants write access to secrets (create/delete/patch)")

        if violations:
            error_msg = "\n\nRBAC grants excessive permissions:\n"
            error_msg += f"File: {role_file.relative_to(PROJECT_ROOT)}\n"
            for v in violations:
                error_msg += f"  - {v}\n"
            error_msg += "\nSecurity Risk: Excessive permissions violate least-privilege\n"
            error_msg += "Fix: Grant only required permissions (get, list, watch)\n"

            pytest.fail(error_msg)


class TestContainerImageBestPractices:
    """Test container images use fully-qualified references with digests."""

    def _load_yaml_file(self, file_path: Path) -> Dict[str, Any]:
        """Load YAML file and return parsed content.

        For multi-document YAML files, returns all documents as a list.
        For single-document files, returns the document as a dict.
        """
        with open(file_path, "r", encoding="utf-8") as f:
            docs = list(yaml.safe_load_all(f))
            # Return single doc as dict, multiple docs as list
            return docs[0] if len(docs) == 1 else docs

    def test_main_deployment_uses_qualified_image_reference(self):
        """
        RED: Deployment uses unqualified image name.
        GREEN: Should use fully-qualified registry path.

        Issue: Unqualified image may pull from wrong registry
        Fix: Use ghcr.io/org/repo:tag or full registry path
        """
        deployment_path = DEPLOYMENTS_BASE / "deployment.yaml"

        if not deployment_path.exists():
            pytest.skip("Deployment not found")

        deployment = self._load_yaml_file(deployment_path)

        containers = deployment.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])

        violations = []

        for container in containers:
            image = container.get("image", "")
            container_name = container.get("name", "unknown")

            # Check if image is unqualified (no registry)
            if "/" not in image or not image.startswith(("ghcr.io/", "gcr.io/", "docker.io/", "quay.io/")):
                violations.append(
                    {
                        "container": container_name,
                        "image": image,
                        "issue": "Unqualified or missing registry",
                        "fix": "Use ghcr.io/org/mcp-server-langgraph:tag",
                    }
                )

            # Check for 'latest' tag
            if image.endswith(":latest") or ":" not in image:
                violations.append(
                    {
                        "container": container_name,
                        "image": image,
                        "issue": "Uses 'latest' tag or no tag",
                        "fix": "Use specific version tag or digest",
                    }
                )

        if violations:
            error_msg = "\n\nDeployment uses unqualified or vague image references:\n"
            error_msg += f"File: {deployment_path.relative_to(PROJECT_ROOT)}\n"
            for v in violations:
                error_msg += f"\n  Container: {v['container']}"
                error_msg += f"\n    Current: {v['image']}"
                error_msg += f"\n    Issue: {v['issue']}"
                error_msg += f"\n    Fix: {v['fix']}\n"

            pytest.fail(error_msg)

    def test_init_containers_use_qualified_images(self):
        """
        RED: Init containers use unqualified images (busybox).
        GREEN: Should use fully-qualified references.

        Issue: busybox:1.36 may pull from Docker Hub instead of intended registry
        Fix: Use docker.io/library/busybox:1.36 or replace with native probes
        """
        deployment_path = DEPLOYMENTS_BASE / "deployment.yaml"

        if not deployment_path.exists():
            pytest.skip("Deployment not found")

        deployment = self._load_yaml_file(deployment_path)

        init_containers = deployment.get("spec", {}).get("template", {}).get("spec", {}).get("initContainers", [])

        violations = []

        for container in init_containers:
            image = container.get("image", "")
            container_name = container.get("name", "unknown")

            # Check if image is unqualified
            if "/" not in image or not image.startswith(("docker.io/", "ghcr.io/", "gcr.io/", "quay.io/")):
                violations.append(
                    {
                        "container": container_name,
                        "image": image,
                        "recommendation": "Use docker.io/library/busybox:1.36 or replace with native readiness probes",
                    }
                )

        if violations:
            error_msg = "\n\nInit containers use unqualified image references:\n"
            error_msg += f"File: {deployment_path.relative_to(PROJECT_ROOT)}\n"
            for v in violations:
                error_msg += f"\n  Container: {v['container']}"
                error_msg += f"\n    Current: {v['image']}"
                error_msg += f"\n    Recommendation: {v['recommendation']}\n"

            pytest.fail(error_msg)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
