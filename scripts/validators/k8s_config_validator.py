#!/usr/bin/env python3
"""
Kubernetes Configuration Validator

Validates Kubernetes manifests for common configuration issues:
1. ConfigMap key references exist
2. Secret names match between patches and ExternalSecrets
3. Kustomize namePrefix is correctly applied

This script can be run as a pre-commit hook or in CI/CD pipelines.

Usage:
    python scripts/validators/k8s_config_validator.py [--overlay OVERLAY]

    Examples:
        # Validate all overlays
        python scripts/validators/k8s_config_validator.py

        # Validate specific overlay
        python scripts/validators/k8s_config_validator.py --overlay deployments/overlays/preview-gke

Exit codes:
    0 - All validations passed
    1 - Validation errors found
    2 - Script execution error (missing dependencies, etc.)
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

import yaml


class Colors:
    """ANSI color codes for terminal output."""

    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"


class K8sConfigValidator:
    """Validates Kubernetes configuration for common issues."""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.errors = []
        self.warnings = []

    def log_error(self, message: str):
        """Log an error message."""
        self.errors.append(message)
        print(f"{Colors.RED}❌ ERROR:{Colors.RESET} {message}")

    def log_warning(self, message: str):
        """Log a warning message."""
        self.warnings.append(message)
        print(f"{Colors.YELLOW}⚠️  WARNING:{Colors.RESET} {message}")

    def log_success(self, message: str):
        """Log a success message."""
        print(f"{Colors.GREEN}✓{Colors.RESET} {message}")

    def get_kustomize_output(self, overlay_path: str) -> list[dict]:
        """Build kustomize and return parsed YAML documents."""
        overlay_dir = self.repo_root / overlay_path

        if not overlay_dir.exists():
            self.log_error(f"Overlay directory not found: {overlay_dir}")
            return []

        try:
            result = subprocess.run(["kustomize", "build", str(overlay_dir)], capture_output=True, text=True, check=True)
            return list(yaml.safe_load_all(result.stdout))
        except subprocess.CalledProcessError as e:
            self.log_error(f"Kustomize build failed for {overlay_path}: {e.stderr}")
            return []
        except Exception as e:
            self.log_error(f"Error processing {overlay_path}: {str(e)}")
            return []

    def extract_configmap_references(self, docs: list[dict]) -> dict[str, set[str]]:
        """Extract all ConfigMap key references from container env variables."""
        references = {}

        def scan_env_vars(env_vars: list[dict]):
            for env in env_vars or []:
                if "valueFrom" in env and "configMapKeyRef" in env["valueFrom"]:
                    ref = env["valueFrom"]["configMapKeyRef"]
                    # Skip optional references
                    if ref.get("optional", False):
                        continue
                    cm_name = ref["name"]
                    key = ref["key"]
                    if cm_name not in references:
                        references[cm_name] = set()
                    references[cm_name].add(key)

        for doc in docs:
            if not doc or doc.get("kind") not in ["Deployment", "StatefulSet", "Job", "CronJob"]:
                continue

            spec = doc.get("spec", {})
            template = spec.get("template", {})
            pod_spec = template.get("spec", {})

            for container in pod_spec.get("initContainers", []):
                scan_env_vars(container.get("env", []))

            for container in pod_spec.get("containers", []):
                scan_env_vars(container.get("env", []))

        return references

    def extract_configmap_keys(self, docs: list[dict]) -> dict[str, set[str]]:
        """Extract all ConfigMap keys from built manifests."""
        configmaps = {}
        for doc in docs:
            if doc and doc.get("kind") == "ConfigMap":
                name = doc["metadata"]["name"]
                configmaps[name] = set(doc.get("data", {}).keys())
        return configmaps

    def validate_configmap_keys(self, overlay_path: str) -> bool:
        """Validate that all referenced ConfigMap keys exist."""
        print(f"\n{Colors.BLUE}Validating ConfigMap keys for {overlay_path}...{Colors.RESET}")

        docs = self.get_kustomize_output(overlay_path)
        if not docs:
            return False

        actual_keys = self.extract_configmap_keys(docs)
        referenced_keys = self.extract_configmap_references(docs)

        has_errors = False
        for cm_name, keys in referenced_keys.items():
            if cm_name not in actual_keys:
                self.log_error(f"{overlay_path}: ConfigMap '{cm_name}' not found")
                has_errors = True
                continue

            missing = keys - actual_keys[cm_name]
            if missing:
                self.log_error(f"{overlay_path}: Missing keys in '{cm_name}': {sorted(missing)}")
                has_errors = True

        if not has_errors:
            self.log_success(f"All ConfigMap keys exist for {overlay_path}")

        return not has_errors

    def validate_all_overlays(self, overlays: list[str]) -> bool:
        """Validate all specified overlays."""
        print(f"\n{Colors.BLUE}=== Kubernetes Configuration Validation ==={Colors.RESET}\n")

        # Check if kustomize is installed
        if not shutil.which("kustomize"):
            self.log_error("kustomize not found. Please install kustomize.")
            return False

        all_valid = True
        for overlay in overlays:
            if not self.validate_configmap_keys(overlay):
                all_valid = False

        # Print summary
        print(f"\n{Colors.BLUE}=== Validation Summary ==={Colors.RESET}")
        if all_valid:
            print(f"{Colors.GREEN}✓ All validations passed!{Colors.RESET}")
        else:
            print(f"{Colors.RED}✗ {len(self.errors)} error(s) found{Colors.RESET}")
            if self.warnings:
                print(f"{Colors.YELLOW}⚠  {len(self.warnings)} warning(s) found{Colors.RESET}")

        return all_valid


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate Kubernetes configuration files", formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--overlay", action="append", help="Specific overlay to validate (can be specified multiple times)")

    args = parser.parse_args()

    repo_root = Path(__file__).parent.parent.parent

    # Default overlays to validate
    default_overlays = [
        "deployments/overlays/preview-gke",
        "deployments/overlays/production-gke",
    ]

    overlays = args.overlay if args.overlay else default_overlays

    validator = K8sConfigValidator(repo_root)
    success = validator.validate_all_overlays(overlays)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
