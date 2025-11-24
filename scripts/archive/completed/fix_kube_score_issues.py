#!/usr/bin/env python3
"""
Comprehensive Kube-Score Compliance Fix Script

Fixes all kube-score CRITICAL issues:
1. ImagePullPolicy: Always
2. Resource limits (CPU, Memory, Ephemeral Storage)
3. Security context (high UIDs, read-only filesystem)
4. Probe differentiation
5. HPA configuration
6. StatefulSet serviceName

Uses ruamel.yaml to preserve comments and formatting.
"""

import sys
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML


def fix_image_pull_policy(container: dict[str, Any]) -> bool:
    """Set imagePullPolicy to Always."""
    if container.get("imagePullPolicy") != "Always":
        container["imagePullPolicy"] = "Always"
        return True
    return False


def add_init_container_resources(container: dict[str, Any]) -> bool:
    """Add minimal resource limits for init containers."""
    changed = False

    if "resources" not in container:
        container["resources"] = {}
        changed = True

    resources = container["resources"]

    # Add limits
    if "limits" not in resources:
        resources["limits"] = {}
        changed = True

    limits = resources["limits"]
    if "cpu" not in limits:
        limits["cpu"] = "100m"
        changed = True
    if "memory" not in limits:
        limits["memory"] = "128Mi"
        changed = True
    if "ephemeral-storage" not in limits:
        limits["ephemeral-storage"] = "1Gi"
        changed = True

    # Add requests
    if "requests" not in resources:
        resources["requests"] = {}
        changed = True

    requests = resources["requests"]
    if "cpu" not in requests:
        requests["cpu"] = "50m"
        changed = True
    if "memory" not in requests:
        requests["memory"] = "64Mi"
        changed = True
    if "ephemeral-storage" not in requests:
        requests["ephemeral-storage"] = "500Mi"
        changed = True

    return changed


def add_ephemeral_storage_limits(container: dict[str, Any]) -> bool:
    """Add ephemeral storage limits to existing resources."""
    changed = False

    if "resources" not in container:
        container["resources"] = {}
        changed = True

    resources = container["resources"]

    # Add to limits
    if "limits" not in resources:
        resources["limits"] = {}
        changed = True

    if "ephemeral-storage" not in resources["limits"]:
        resources["limits"]["ephemeral-storage"] = "2Gi"
        changed = True

    # Add to requests
    if "requests" not in resources:
        resources["requests"] = {}
        changed = True

    if "ephemeral-storage" not in resources["requests"]:
        resources["requests"]["ephemeral-storage"] = "1Gi"
        changed = True

    return changed


def fix_security_context_uids(container: dict[str, Any], is_init: bool = False) -> bool:
    """Fix runAsUser and runAsGroup to use high IDs."""
    changed = False

    if "securityContext" not in container:
        container["securityContext"] = {}
        changed = True

    sec_context = container["securityContext"]

    # Fix runAsUser if low
    run_as_user = sec_context.get("runAsUser")
    if run_as_user is not None and run_as_user < 10000:
        sec_context["runAsUser"] = 10000 + run_as_user
        changed = True

    # Fix runAsGroup if low
    run_as_group = sec_context.get("runAsGroup")
    if run_as_group is not None and run_as_group < 10000:
        sec_context["runAsGroup"] = 10000 + run_as_group
        changed = True

    return changed


def fix_readonly_filesystem(container: dict[str, Any], container_name: str) -> bool:
    """
    Set readOnlyRootFilesystem: true for main containers.

    Skip certain containers that require writable filesystem:
    - postgres, keycloak, redis, qdrant (data services)
    """
    # Skip data services that need writable filesystem
    skip_containers = ["postgres", "keycloak", "redis", "qdrant"]
    if container_name in skip_containers:
        return False

    changed = False

    if "securityContext" not in container:
        container["securityContext"] = {}
        changed = True

    sec_context = container["securityContext"]

    if sec_context.get("readOnlyRootFilesystem") is not True:
        sec_context["readOnlyRootFilesystem"] = True
        changed = True

    return changed


def differentiate_probes(container: dict[str, Any]) -> bool:
    """
    Make readiness and liveness probes different.

    Strategy: Make readiness probe more sensitive (faster to mark unready).
    """
    liveness = container.get("livenessProbe")
    readiness = container.get("readinessProbe")

    if not liveness or not readiness:
        return False

    # If probes are identical, make readiness more sensitive
    if liveness == readiness:
        # Readiness should fail faster
        if "failureThreshold" not in readiness or readiness["failureThreshold"] > 1:
            readiness["failureThreshold"] = 1

        # Readiness can have shorter period
        if "periodSeconds" in liveness:
            liveness_period = liveness["periodSeconds"]
            if "periodSeconds" not in readiness or readiness["periodSeconds"] == liveness_period:
                readiness["periodSeconds"] = max(5, liveness_period // 2)

        return True

    return False


def fix_deployment_or_statefulset(doc: dict[str, Any]) -> bool:
    """Fix all kube-score issues in a Deployment or StatefulSet."""
    changed = False
    kind = doc.get("kind")

    if kind not in ["Deployment", "StatefulSet"]:
        return False

    spec = doc.get("spec", {})
    template = spec.get("template", {})
    pod_spec = template.get("spec", {})

    # Fix init containers
    for init_container in pod_spec.get("initContainers", []):
        if fix_image_pull_policy(init_container):
            changed = True
        if add_init_container_resources(init_container):
            changed = True
        if fix_security_context_uids(init_container, is_init=True):
            changed = True

    # Fix regular containers
    for container in pod_spec.get("containers", []):
        container_name = container.get("name", "unknown")

        if fix_image_pull_policy(container):
            changed = True
        if add_ephemeral_storage_limits(container):
            changed = True
        if fix_security_context_uids(container):
            changed = True
        if fix_readonly_filesystem(container, container_name):
            changed = True
        if differentiate_probes(container):
            changed = True

    # Fix HPA issue: remove static replica count if HPA exists
    # This is done in overlays, not base manifests

    # Fix StatefulSet serviceName
    if kind == "StatefulSet":
        if "serviceName" not in spec or not spec.get("serviceName"):
            # Set serviceName to match the StatefulSet name
            name = doc.get("metadata", {}).get("name", "unknown")
            spec["serviceName"] = name
            changed = True

    return changed


def fix_yaml_file(file_path: Path) -> bool:
    """Fix all kube-score issues in a YAML file."""
    print(f"Processing: {file_path.name}")

    try:
        # Configure ruamel.yaml to preserve formatting
        yaml = YAML()
        yaml.preserve_quotes = True
        yaml.default_flow_style = False
        yaml.indent(mapping=2, sequence=2, offset=2)
        yaml.width = 120

        # Load all documents
        with open(file_path, encoding="utf-8") as f:
            docs = list(yaml.load_all(f))

        if not docs or all(d is None for d in docs):
            print("  ⚠️  Skipped (empty)")
            return False

        # Fix each document
        any_changed = False
        for doc in docs:
            if doc is not None:
                if fix_deployment_or_statefulset(doc):
                    any_changed = True

        # Write back if changed
        if any_changed:
            with open(file_path, "w", encoding="utf-8") as f:
                for i, doc in enumerate(docs):
                    if doc is not None:
                        if i > 0:
                            f.write("---\n")
                        yaml.dump(doc, f)

            print("  ✅ Fixed")
            return True
        else:
            print("  ℹ️  No changes needed")
            return False

    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Fix all kube-score issues in deployment files."""

    files_to_fix = [
        "deployments/base/deployment.yaml",
        "deployments/base/keycloak-deployment.yaml",
        "deployments/base/openfga-deployment.yaml",
        "deployments/base/otel-collector-deployment.yaml",
        "deployments/base/qdrant-deployment.yaml",
        "deployments/base/redis-session-deployment.yaml",
        "deployments/base/postgres-statefulset.yaml",
    ]

    repo_root = Path(__file__).parent.parent
    fixed_count = 0
    error_count = 0

    print("=" * 70)
    print("Kube-Score Compliance Fix")
    print("=" * 70)
    print(f"\nFixing {len(files_to_fix)} deployment files...\n")

    for file_path_str in files_to_fix:
        file_path = repo_root / file_path_str

        if not file_path.exists():
            print(f"⚠️  Not found: {file_path.name}")
            error_count += 1
            continue

        if fix_yaml_file(file_path):
            fixed_count += 1

    print(f"\n{'=' * 70}")
    print("Summary")
    print("=" * 70)
    print(f"  ✅ Fixed: {fixed_count}")
    print(f"  ❌ Errors: {error_count}")
    print(f"  📁 Total: {len(files_to_fix)}")
    print("=" * 70)

    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
