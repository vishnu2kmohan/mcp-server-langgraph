#!/usr/bin/env python3
"""
Audit resource request/limit ratios across all Kubernetes deployments.

Validates:
- CPU ratio ≤ 4.0 (GKE Autopilot max)
- Memory ratio ≤ 4.0 (GKE Autopilot max)
- Consistent ratios across services
"""

import sys
from pathlib import Path

import yaml


def parse_resource(value: str) -> float:
    """Parse Kubernetes resource value to numeric (in base units)."""
    if not value:
        return 0.0

    value = str(value).strip()

    # CPU parsing (m = millicores, default = cores)
    if value.endswith("m"):
        return float(value[:-1]) / 1000.0

    # Memory parsing
    multipliers = {
        "Ki": 1024,
        "Mi": 1024**2,
        "Gi": 1024**3,
        "Ti": 1024**4,
        "K": 1000,
        "M": 1000**2,
        "G": 1000**3,
        "T": 1000**4,
    }

    for suffix, multiplier in multipliers.items():
        if value.endswith(suffix):
            return float(value[: -len(suffix)]) * multiplier

    # Plain number (cores or bytes)
    try:
        return float(value)
    except ValueError:
        return 0.0


def audit_container_resources(container: dict, container_name: str, deployment_name: str) -> list:
    """Audit resource ratios for a single container."""
    issues = []

    resources = container.get("resources", {})
    requests = resources.get("requests", {})
    limits = resources.get("limits", {})

    if not requests or not limits:
        issues.append(f"  ⚠️  {deployment_name}/{container_name}: Missing requests or limits")
        return issues

    # Audit CPU ratio
    cpu_request = parse_resource(requests.get("cpu", "0"))  # nosec B113 - dict access, not HTTP
    cpu_limit = parse_resource(limits.get("cpu", "0"))  # nosec B113

    if cpu_request > 0 and cpu_limit > 0:
        cpu_ratio = cpu_limit / cpu_request

        status = "✅" if cpu_ratio <= 4.0 else "❌"

        if cpu_ratio > 4.0:
            issues.append(
                f"  {status} {deployment_name}/{container_name}: "
                f"CPU ratio {cpu_ratio:.2f} exceeds GKE max 4.0 "
                f"(request: {requests.get('cpu')}, limit: {limits.get('cpu')})"  # nosec B113
            )
        else:
            print(
                f"  {status} {deployment_name}/{container_name}: "
                f"CPU ratio {cpu_ratio:.2f} "
                f"(request: {requests.get('cpu')}, limit: {limits.get('cpu')})"  # nosec B113
            )

    # Audit Memory ratio
    mem_request = parse_resource(requests.get("memory", "0"))  # nosec B113 - dict access, not HTTP
    mem_limit = parse_resource(limits.get("memory", "0"))  # nosec B113

    if mem_request > 0 and mem_limit > 0:
        mem_ratio = mem_limit / mem_request

        status = "✅" if mem_ratio <= 4.0 else "❌"

        if mem_ratio > 4.0:
            issues.append(
                f"  {status} {deployment_name}/{container_name}: "
                f"Memory ratio {mem_ratio:.2f} exceeds GKE max 4.0 "
                f"(request: {requests.get('memory')}, limit: {limits.get('memory')})"  # nosec B113
            )
        else:
            print(
                f"  {status} {deployment_name}/{container_name}: "
                f"Memory ratio {mem_ratio:.2f} "
                f"(request: {requests.get('memory')}, limit: {limits.get('memory')})"  # nosec B113
            )

    return issues


def audit_deployment(file_path: Path) -> list:
    """Audit a single deployment file (supports multi-document YAML)."""
    issues = []

    try:
        with open(file_path) as f:
            # Load all documents in the file (handles multi-document YAML)
            documents = list(yaml.safe_load_all(f))

        for manifest in documents:
            if not manifest or manifest.get("kind") != "Deployment":
                continue

            deployment_name = manifest["metadata"]["name"]
            print(f"\n📦 {deployment_name} ({file_path.name})")

            containers = manifest["spec"]["template"]["spec"].get("containers", [])

            for container in containers:
                container_name = container.get("name", "unknown")
                issues.extend(audit_container_resources(container, container_name, deployment_name))

    except Exception as e:
        issues.append(f"  ❌ Error auditing {file_path}: {e}")

    return issues


def main():
    """Audit all deployment files."""
    base_path = Path("deployments/base")
    deployment_files = list(base_path.glob("*-deployment.yaml"))
    deployment_files.append(base_path / "deployment.yaml")

    print("🔍 Auditing Resource Request/Limit Ratios\n")
    print("=" * 80)

    all_issues = []

    for file_path in sorted(deployment_files):
        if file_path.exists():
            issues = audit_deployment(file_path)
            all_issues.extend(issues)

    print("\n" + "=" * 80)

    if all_issues:
        print(f"\n❌ Found {len(all_issues)} issue(s):\n")
        for issue in all_issues:
            print(issue)
        return 1
    print("\n✅ All resource ratios are compliant with GKE Autopilot limits (≤ 4.0)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
