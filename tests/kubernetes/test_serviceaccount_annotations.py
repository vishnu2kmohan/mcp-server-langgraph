"""
Test suite to validate that Kubernetes ServiceAccount annotations contain no placeholders.

These tests ensure that cloud identity annotations (IRSA for AWS, Workload Identity for GKE/Azure)
are properly configured with real values before deployment.

Following TDD Red-Green-Refactor:
- RED: These tests should FAIL initially (placeholders exist)
- GREEN: After implementing variable substitution, tests should PASS
- REFACTOR: Improve validation logic as needed
"""

import os
import re
from pathlib import Path

import pytest
import yaml

# Define project root relative to test file
PROJECT_ROOT = Path(__file__).parent.parent.parent
DEPLOYMENTS_DIR = PROJECT_ROOT / "deployments"


class TestServiceAccountAnnotations:
    """Test that ServiceAccount annotations contain no placeholder values."""

    PLACEHOLDER_PATTERNS = {
        "aws": [
            r"\bACCOUNT_ID\b",
            r"\bENVIRONMENT\b",
            r"arn:aws:iam::ACCOUNT_ID:",
        ],
        "gcp": [
            r"\bPROJECT_ID\b",
            r"@PROJECT_ID\.iam\.gserviceaccount\.com",
        ],
        "azure": [
            r"\bAZURE_CLIENT_ID\b",
            r"\bCLIENT_ID\b",
            r"00000000-0000-0000-0000-000000000000",
        ],
    }

    def _find_yaml_files(self, directory: Path):
        """Recursively find all YAML files."""
        yaml_files = []
        for path in directory.rglob("*.yaml"):
            if ".git" not in path.parts:
                yaml_files.append(path)
        for path in directory.rglob("*.yml"):
            if ".git" not in path.parts:
                yaml_files.append(path)
        return yaml_files

    def _load_yaml_file(self, file_path: Path):
        """Load YAML file and return all documents."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                # Load all YAML documents in the file
                return list(yaml.safe_load_all(f))
        except Exception as e:
            pytest.fail(f"Error loading YAML file {file_path}: {e}")

    def _check_serviceaccount_annotations(self, doc, file_path: Path):
        """Check a single YAML document for ServiceAccount placeholder annotations."""
        violations = []

        if not isinstance(doc, dict):
            return violations

        # Check if this is a ServiceAccount
        if doc.get("kind") != "ServiceAccount":
            return violations

        # Get annotations
        annotations = doc.get("metadata", {}).get("annotations", {})
        if not annotations:
            return violations

        # Check AWS IRSA annotations
        for key, value in annotations.items():
            if "eks.amazonaws.com/role-arn" in key:
                for pattern in self.PLACEHOLDER_PATTERNS["aws"]:
                    if re.search(pattern, str(value)):
                        violations.append(
                            {
                                "file": str(file_path.relative_to(PROJECT_ROOT)),
                                "kind": "ServiceAccount",
                                "name": doc.get("metadata", {}).get("name", "unknown"),
                                "annotation": key,
                                "value": value,
                                "issue": f"AWS IRSA annotation contains placeholder matching: {pattern}",
                            }
                        )

            # Check GCP Workload Identity annotations
            if "iam.gke.io/gcp-service-account" in key:
                for pattern in self.PLACEHOLDER_PATTERNS["gcp"]:
                    if re.search(pattern, str(value)):
                        violations.append(
                            {
                                "file": str(file_path.relative_to(PROJECT_ROOT)),
                                "kind": "ServiceAccount",
                                "name": doc.get("metadata", {}).get("name", "unknown"),
                                "annotation": key,
                                "value": value,
                                "issue": f"GCP Workload Identity annotation contains placeholder matching: {pattern}",
                            }
                        )

            # Check Azure Workload Identity annotations
            if "azure.workload.identity/client-id" in key:
                for pattern in self.PLACEHOLDER_PATTERNS["azure"]:
                    if re.search(pattern, str(value)):
                        violations.append(
                            {
                                "file": str(file_path.relative_to(PROJECT_ROOT)),
                                "kind": "ServiceAccount",
                                "name": doc.get("metadata", {}).get("name", "unknown"),
                                "annotation": key,
                                "value": value,
                                "issue": f"Azure Workload Identity annotation contains placeholder matching: {pattern}",
                            }
                        )

        return violations

    def test_base_serviceaccount_no_placeholders(self):
        """
        Test that base ServiceAccount has no placeholder annotations.

        RED: Should FAIL - base ServiceAccount has ACCOUNT_ID, PROJECT_ID, AZURE_CLIENT_ID
        GREEN: Should PASS - after using variables or removing default placeholders
        """
        base_sa_file = DEPLOYMENTS_DIR / "base" / "serviceaccount.yaml"

        if not base_sa_file.exists():
            pytest.skip(f"Base ServiceAccount not found: {base_sa_file}")

        documents = self._load_yaml_file(base_sa_file)
        all_violations = []

        for doc in documents:
            violations = self._check_serviceaccount_annotations(doc, base_sa_file)
            all_violations.extend(violations)

        if all_violations:
            error_msg = "\n\nPlaceholder violations in base ServiceAccount:\n"
            for v in all_violations:
                error_msg += f"\n  {v['file']}"
                error_msg += f"\n    ServiceAccount: {v['name']}"
                error_msg += f"\n    Annotation: {v['annotation']}"
                error_msg += f"\n    Value: {v['value']}"
                error_msg += f"\n    Issue: {v['issue']}\n"

            pytest.fail(error_msg)

    def test_aws_overlay_serviceaccount_no_placeholders(self):
        """
        Test that AWS overlay ServiceAccount patches have no placeholders.

        RED: Should FAIL - AWS overlay has ACCOUNT_ID and ENVIRONMENT placeholders
        GREEN: Should PASS - after variable substitution
        """
        aws_overlays = [
            DEPLOYMENTS_DIR / "kubernetes" / "overlays" / "aws" / "serviceaccount-patch.yaml",
        ]

        all_violations = []

        for overlay_file in aws_overlays:
            if not overlay_file.exists():
                continue

            documents = self._load_yaml_file(overlay_file)

            for doc in documents:
                violations = self._check_serviceaccount_annotations(doc, overlay_file)
                all_violations.extend(violations)

        if all_violations:
            error_msg = "\n\nPlaceholder violations in AWS ServiceAccount overlays:\n"
            for v in all_violations:
                error_msg += f"\n  {v['file']}"
                error_msg += f"\n    ServiceAccount: {v['name']}"
                error_msg += f"\n    Annotation: {v['annotation']}"
                error_msg += f"\n    Value: {v['value']}"
                error_msg += f"\n    Issue: {v['issue']}\n"

            pytest.fail(error_msg)

    def test_gcp_overlay_serviceaccount_no_placeholders(self):
        """
        Test that GCP overlay ServiceAccount patches have no placeholders.

        RED: Should FAIL - GCP overlay has PROJECT_ID placeholder
        GREEN: Should PASS - after variable substitution
        """
        gcp_overlays = [
            DEPLOYMENTS_DIR / "overlays" / "production-gke" / "serviceaccount-patch.yaml",
        ]

        all_violations = []

        for overlay_file in gcp_overlays:
            if not overlay_file.exists():
                continue

            documents = self._load_yaml_file(overlay_file)

            for doc in documents:
                violations = self._check_serviceaccount_annotations(doc, overlay_file)
                all_violations.extend(violations)

        if all_violations:
            error_msg = "\n\nPlaceholder violations in GCP ServiceAccount overlays:\n"
            for v in all_violations:
                error_msg += f"\n  {v['file']}"
                error_msg += f"\n    ServiceAccount: {v['name']}"
                error_msg += f"\n    Annotation: {v['annotation']}"
                error_msg += f"\n    Value: {v['value']}"
                error_msg += f"\n    Issue: {v['issue']}\n"

            pytest.fail(error_msg)


class TestKustomizeVariableSubstitution:
    """Test that Kustomize configurations support variable substitution."""

    def test_kustomization_has_vars_or_replacements(self):
        """
        Test that kustomization.yaml files use vars or replacements for dynamic values.

        RED: Should FAIL - kustomization files don't use variable substitution
        GREEN: Should PASS - after implementing vars/replacements
        """
        kustomization_files = list(DEPLOYMENTS_DIR.rglob("kustomization.yaml"))

        # We expect at least the overlay kustomization files to exist
        assert len(kustomization_files) > 0, "No kustomization.yaml files found"

        # For now, just verify files exist - actual var implementation will be in GREEN phase
        # This test will be enhanced to check for specific var definitions
        pass  # Placeholder for future enhancement


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
