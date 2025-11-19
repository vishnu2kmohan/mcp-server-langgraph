#!/usr/bin/env python3
"""
GKE Autopilot Compliance Validator

Validates Kubernetes manifests against GKE Autopilot constraints and best practices.
Ensures deployments comply with LimitRange policies before they're applied to the cluster.

Usage:
    python scripts/validate_gke_autopilot_compliance.py [overlay-path]

Exit codes:
    0: All validations passed
    1: Validation failures found
"""

import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml


class ValidationError(Exception):
    """Custom exception for validation errors"""

    pass


class GKEAutopilotValidator:
    """Validator for GKE Autopilot compliance"""

    # GKE Autopilot LimitRange constraints
    MAX_CPU_RATIO = 4.0
    MAX_MEMORY_RATIO = 4.0
    MIN_CPU_REQUEST = "50m"
    MAX_CPU_LIMIT = "4"
    MIN_MEMORY_REQUEST = "64Mi"
    MAX_MEMORY_LIMIT = "8Gi"

    def __init__(self, overlay_path: str):
        self.overlay_path = Path(overlay_path)
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def parse_cpu(self, cpu_str: str) -> float:
        """Parse CPU string to millicores"""
        if not cpu_str:
            return 0.0
        if cpu_str.endswith("m"):
            return float(cpu_str[:-1])
        return float(cpu_str) * 1000

    def parse_memory(self, mem_str: str) -> float:
        """Parse memory string to MiB"""
        if not mem_str:
            return 0.0

        units = {
            "Ki": 1 / 1024,
            "Mi": 1,
            "Gi": 1024,
            "Ti": 1024 * 1024,
            "K": 1 / 1024,
            "M": 1,
            "G": 1024,
            "T": 1024 * 1024,
        }

        for unit, multiplier in units.items():
            if mem_str.endswith(unit):
                return float(mem_str[: -len(unit)]) * multiplier

        # Assume bytes if no unit
        return float(mem_str) / (1024 * 1024)

    def build_kustomize(self) -> list[dict[str, Any]]:
        """Build kustomize overlay and return parsed manifests"""
        try:
            result = subprocess.run(
                ["kubectl", "kustomize", str(self.overlay_path)], capture_output=True, text=True, check=True
            )
            # Parse multi-document YAML
            manifests = list(yaml.safe_load_all(result.stdout))
            return [m for m in manifests if m is not None]
        except subprocess.CalledProcessError as e:
            raise ValidationError(f"Failed to build kustomize: {e.stderr}")
        except yaml.YAMLError as e:
            raise ValidationError(f"Failed to parse YAML: {e}")

    def validate_cpu_ratio(self, deployment_name: str, container_name: str, request: str, limit: str) -> None:
        """Validate CPU limit/request ratio"""
        req_cpu = self.parse_cpu(request)
        lim_cpu = self.parse_cpu(limit)

        if req_cpu == 0:
            self.errors.append(f"{deployment_name}/{container_name}: CPU request not specified")
            return

        if lim_cpu == 0:
            self.errors.append(f"{deployment_name}/{container_name}: CPU limit not specified")
            return

        ratio = lim_cpu / req_cpu
        if ratio > self.MAX_CPU_RATIO:
            self.errors.append(
                f"{deployment_name}/{container_name}: CPU limit/request ratio "
                f"{ratio:.2f} exceeds max {self.MAX_CPU_RATIO} "
                f"(request: {request}, limit: {limit})"
            )

    def validate_memory_ratio(self, deployment_name: str, container_name: str, request: str, limit: str) -> None:
        """Validate memory limit/request ratio"""
        req_mem = self.parse_memory(request)
        lim_mem = self.parse_memory(limit)

        if req_mem == 0:
            self.warnings.append(f"{deployment_name}/{container_name}: Memory request not specified")
            return

        if lim_mem == 0:
            self.warnings.append(f"{deployment_name}/{container_name}: Memory limit not specified")
            return

        ratio = lim_mem / req_mem
        if ratio > self.MAX_MEMORY_RATIO:
            self.errors.append(
                f"{deployment_name}/{container_name}: Memory limit/request ratio "
                f"{ratio:.2f} exceeds max {self.MAX_MEMORY_RATIO} "
                f"(request: {request}, limit: {limit})"
            )

    def validate_env_vars(self, deployment_name: str, container_name: str, env_vars: list[dict[str, Any]]) -> None:
        """Validate environment variables don't have conflicting sources"""
        for env in env_vars:
            name = env.get("name", "unknown")
            has_value = "value" in env
            has_value_from = "valueFrom" in env

            if has_value and has_value_from:
                self.errors.append(
                    f"{deployment_name}/{container_name}: Env var '{name}' has both 'value' and 'valueFrom' specified"
                )

            # Check for empty valueFrom
            if has_value_from and not env["valueFrom"]:
                self.errors.append(f"{deployment_name}/{container_name}: Env var '{name}' has empty 'valueFrom'")

            # Check valueFrom has exactly one source
            if has_value_from and env["valueFrom"]:
                sources = [k for k in env["valueFrom"].keys() if k != "optional"]
                if len(sources) > 1:
                    self.errors.append(
                        f"{deployment_name}/{container_name}: Env var '{name}' has multiple valueFrom sources: {sources}"
                    )
                elif len(sources) == 0:
                    self.errors.append(
                        f"{deployment_name}/{container_name}: Env var '{name}' has valueFrom but no source specified"
                    )

    def validate_readonly_filesystem(
        self, deployment_name: str, container_name: str, security_context: dict[str, Any], volume_mounts: list[dict[str, Any]]
    ) -> None:
        """Validate readOnlyRootFilesystem has appropriate volume mounts"""
        readonly_fs = security_context.get("readOnlyRootFilesystem", False)

        if readonly_fs:
            mount_paths = {vm["mountPath"] for vm in volume_mounts}

            # Common writable paths that should be mounted
            recommended_mounts = ["/tmp", "/var/tmp"]  # nosec B108: Checking K8s mount paths, not using temp files
            missing_mounts = [path for path in recommended_mounts if path not in mount_paths]

            if missing_mounts:
                self.warnings.append(
                    f"{deployment_name}/{container_name}: readOnlyRootFilesystem is true "
                    f"but missing recommended mounts: {missing_mounts}"
                )

    def validate_deployment(self, manifest: dict[str, Any]) -> None:
        """Validate a Deployment manifest"""
        kind = manifest.get("kind")
        if kind not in ["Deployment", "StatefulSet", "DaemonSet"]:
            return

        metadata = manifest.get("metadata", {})
        name = metadata.get("name", "unknown")
        spec = manifest.get("spec", {})
        template = spec.get("template", {})
        pod_spec = template.get("spec", {})
        containers = pod_spec.get("containers", [])

        for container in containers:
            container_name = container.get("name", "unknown")
            resources = container.get("resources", {})
            requests = resources.get("requests", {})
            limits = resources.get("limits", {})

            # Validate CPU ratio
            cpu_request = requests.get("cpu")  # nosec B113: dict.get(), not HTTP requests library
            cpu_limit = limits.get("cpu")
            if cpu_request and cpu_limit:
                self.validate_cpu_ratio(name, container_name, cpu_request, cpu_limit)

            # Validate Memory ratio
            mem_request = requests.get("memory")  # nosec B113: dict.get(), not HTTP requests library
            mem_limit = limits.get("memory")
            if mem_request and mem_limit:
                self.validate_memory_ratio(name, container_name, mem_request, mem_limit)

            # Validate environment variables
            env_vars = container.get("env", [])
            if env_vars:
                self.validate_env_vars(name, container_name, env_vars)

            # Validate readOnlyRootFilesystem
            security_context = container.get("securityContext", {})
            volume_mounts = container.get("volumeMounts", [])
            self.validate_readonly_filesystem(name, container_name, security_context, volume_mounts)

    def validate(self) -> bool:
        """Run all validations and return True if passed"""
        print(f"Validating {self.overlay_path}...")

        try:
            manifests = self.build_kustomize()
        except ValidationError as e:
            print(f"❌ ERROR: {e}")
            return False

        for manifest in manifests:
            self.validate_deployment(manifest)

        # Print results
        if self.warnings:
            print("\n⚠️  WARNINGS:")
            for warning in self.warnings:
                print(f"  - {warning}")

        if self.errors:
            print("\n❌ ERRORS:")
            for error in self.errors:
                print(f"  - {error}")
            return False

        print("\n✅ All validations passed!")
        return True


def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        overlay_path = sys.argv[1]
    else:
        # Default to validating all overlays
        overlay_path = "deployments/overlays"

    overlay = Path(overlay_path)

    if not overlay.exists():
        print(f"❌ ERROR: Path {overlay_path} does not exist")
        sys.exit(1)

    # If it's a directory with subdirectories, validate each overlay
    if overlay.is_dir() and not (overlay / "kustomization.yaml").exists():
        overlays = [d for d in overlay.iterdir() if d.is_dir() and (d / "kustomization.yaml").exists()]
        if not overlays:
            print(f"❌ ERROR: No kustomization.yaml found in {overlay_path}")
            sys.exit(1)

        all_passed = True
        for ov in overlays:
            validator = GKEAutopilotValidator(str(ov))
            if not validator.validate():
                all_passed = False
            print()

        sys.exit(0 if all_passed else 1)
    else:
        # Single overlay
        validator = GKEAutopilotValidator(overlay_path)
        success = validator.validate()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
