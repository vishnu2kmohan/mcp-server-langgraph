"""
Test suite to validate that External Secrets configurations contain no placeholders.

These tests ensure that ExternalSecret and SecretStore resources are properly configured
with real project IDs, account IDs, and environment names before deployment.

Following TDD Red-Green-Refactor:
- RED: These tests should FAIL initially (placeholders exist)
- GREEN: After implementing variable substitution, tests should PASS
- REFACTOR: Improve validation logic as needed
"""

import gc
import re
from pathlib import Path

import pytest
import yaml


# Define project root relative to test file
PROJECT_ROOT = Path(__file__).parent.parent.parent
DEPLOYMENTS_DIR = PROJECT_ROOT / "deployments"


@pytest.mark.unit
@pytest.mark.kubernetes
@pytest.mark.xdist_group(name="testexternalsecretsvalidation")
class TestExternalSecretsValidation:
    """Test that ExternalSecret and SecretStore resources have no placeholders."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    PLACEHOLDER_PATTERNS = {
        "aws": [
            r"\bACCOUNT_ID\b",
            r"\bENVIRONMENT\b(?!/)",  # ENVIRONMENT but not in paths like /ENVIRONMENT/
            r"arn:aws:iam::ACCOUNT_ID:",
            r"/ENVIRONMENT/",  # In secret paths
        ],
        "gcp": [
            r"\bYOUR_PROJECT_ID\b",
            r"\bPROJECT_ID\b",
            r'"PROJECT_ID"',
        ],
        "azure": [
            r"\bAZURE_CLIENT_ID\b",
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
            with open(file_path, encoding="utf-8") as f:
                return list(yaml.safe_load_all(f))
        except Exception:
            # Skip files that can't be parsed as YAML
            return []

    def _check_external_secret_placeholders(self, doc, file_path: Path, cloud_provider: str):
        """Check a single YAML document for ExternalSecret/SecretStore placeholders."""
        violations = []

        if not isinstance(doc, dict):
            return violations

        # Check if this is an ExternalSecret or SecretStore
        kind = doc.get("kind", "")
        if kind not in ["ExternalSecret", "SecretStore", "ClusterSecretStore"]:
            return violations

        # Convert document to string for pattern matching
        doc_str = yaml.dump(doc)

        # Check for placeholders
        for pattern in self.PLACEHOLDER_PATTERNS.get(cloud_provider, []):
            matches = re.finditer(pattern, doc_str)
            for match in matches:
                violations.append(
                    {
                        "file": str(file_path.relative_to(PROJECT_ROOT)),
                        "kind": kind,
                        "name": doc.get("metadata", {}).get("name", "unknown"),
                        "cloud": cloud_provider,
                        "placeholder": match.group(),
                        "issue": f"Contains placeholder pattern: {pattern}",
                    }
                )

        return violations

    def test_aws_external_secrets_no_placeholders(self):
        """
        Test that AWS ExternalSecrets have no ACCOUNT_ID or ENVIRONMENT placeholders.

        RED: Should FAIL - AWS overlay has ACCOUNT_ID and ENVIRONMENT in role ARNs and secret paths
        GREEN: Should PASS - after variable substitution
        """
        aws_overlay_dir = DEPLOYMENTS_DIR / "kubernetes" / "overlays" / "aws"

        if not aws_overlay_dir.exists():
            pytest.skip(f"AWS overlay directory not found: {aws_overlay_dir}")

        # Find external-secrets.yaml
        external_secrets_files = list(aws_overlay_dir.glob("*external-secrets*.yaml"))

        if not external_secrets_files:
            pytest.skip("No AWS external secrets configuration found")

        all_violations = []

        for secrets_file in external_secrets_files:
            documents = self._load_yaml_file(secrets_file)

            for doc in documents:
                violations = self._check_external_secret_placeholders(doc, secrets_file, "aws")
                all_violations.extend(violations)

        if all_violations:
            error_msg = "\n\nPlaceholder violations in AWS ExternalSecrets:\n"
            for v in all_violations:
                error_msg += f"\n  {v['file']}"
                error_msg += f"\n    Kind: {v['kind']}"
                error_msg += f"\n    Name: {v['name']}"
                error_msg += f"\n    Placeholder: {v['placeholder']}"
                error_msg += f"\n    Issue: {v['issue']}\n"

            pytest.fail(error_msg)

    def test_gcp_external_secrets_no_placeholders(self):
        """
        Test that GCP ExternalSecrets have no PROJECT_ID placeholders.

        RED: Should FAIL - GCP overlay has YOUR_PROJECT_ID placeholder
        GREEN: Should PASS - after variable substitution
        """
        gcp_overlay_dirs = [
            DEPLOYMENTS_DIR / "overlays" / "production-gke",
            DEPLOYMENTS_DIR / "kubernetes" / "overlays" / "gcp",
        ]

        all_violations = []

        for overlay_dir in gcp_overlay_dirs:
            if not overlay_dir.exists():
                continue

            external_secrets_files = list(overlay_dir.glob("*external-secrets*.yaml"))

            for secrets_file in external_secrets_files:
                documents = self._load_yaml_file(secrets_file)

                for doc in documents:
                    violations = self._check_external_secret_placeholders(doc, secrets_file, "gcp")
                    all_violations.extend(violations)

        if all_violations:
            error_msg = "\n\nPlaceholder violations in GCP ExternalSecrets:\n"
            for v in all_violations:
                error_msg += f"\n  {v['file']}"
                error_msg += f"\n    Kind: {v['kind']}"
                error_msg += f"\n    Name: {v['name']}"
                error_msg += f"\n    Placeholder: {v['placeholder']}"
                error_msg += f"\n    Issue: {v['issue']}\n"

            pytest.fail(error_msg)

    def test_azure_external_secrets_no_placeholders(self):
        """
        Test that Azure ExternalSecrets have no CLIENT_ID placeholders.

        RED: Should FAIL - Azure overlay may have CLIENT_ID placeholders
        GREEN: Should PASS - after variable substitution
        """
        azure_overlay_dir = DEPLOYMENTS_DIR / "kubernetes" / "overlays" / "azure"

        if not azure_overlay_dir.exists():
            pytest.skip(f"Azure overlay directory not found: {azure_overlay_dir}")

        external_secrets_files = list(azure_overlay_dir.glob("*external-secrets*.yaml"))

        if not external_secrets_files:
            pytest.skip("No Azure external secrets configuration found")

        all_violations = []

        for secrets_file in external_secrets_files:
            documents = self._load_yaml_file(secrets_file)

            for doc in documents:
                violations = self._check_external_secret_placeholders(doc, secrets_file, "azure")
                all_violations.extend(violations)

        if all_violations:
            error_msg = "\n\nPlaceholder violations in Azure ExternalSecrets:\n"
            for v in all_violations:
                error_msg += f"\n  {v['file']}"
                error_msg += f"\n    Kind: {v['kind']}"
                error_msg += f"\n    Name: {v['name']}"
                error_msg += f"\n    Placeholder: {v['placeholder']}"
                error_msg += f"\n    Issue: {v['issue']}\n"

            pytest.fail(error_msg)


@pytest.mark.xdist_group(name="testexternalsecretsserviceaccounts")
class TestExternalSecretsServiceAccounts:
    """Test that External Secrets Operator ServiceAccounts are properly configured."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_external_secrets_sa_has_cloud_identity(self):
        """
        Test that External Secrets Operator ServiceAccount has proper cloud identity.

        This ensures the operator can authenticate to cloud secret stores.

        RED: Should FAIL - ServiceAccount has placeholder role ARNs
        GREEN: Should PASS - after proper configuration
        """
        # Find external-secrets ServiceAccounts in overlays
        overlay_dirs = [
            DEPLOYMENTS_DIR / "kubernetes" / "overlays" / "aws",
            DEPLOYMENTS_DIR / "overlays" / "production-gke",
            DEPLOYMENTS_DIR / "kubernetes" / "overlays" / "azure",
        ]

        found_configs = False
        violations = []

        for overlay_dir in overlay_dirs:
            if not overlay_dir.exists():
                continue

            # Look for external-secrets related files
            yaml_files = list(overlay_dir.glob("*external-secrets*.yaml"))

            for yaml_file in yaml_files:
                try:
                    with open(yaml_file, encoding="utf-8") as f:
                        content = f.read()

                    # Check for placeholder patterns
                    if "ACCOUNT_ID" in content or "PROJECT_ID" in content or "AZURE_CLIENT_ID" in content:
                        violations.append(
                            {
                                "file": str(yaml_file.relative_to(PROJECT_ROOT)),
                                "issue": "External Secrets configuration contains identity placeholders",
                            }
                        )
                        found_configs = True

                except Exception:
                    continue

        if not found_configs:
            pytest.skip("No External Secrets configurations found")

        if violations:
            error_msg = "\n\nExternal Secrets identity configuration issues:\n"
            for v in violations:
                error_msg += f"\n  {v['file']}"
                error_msg += f"\n    Issue: {v['issue']}\n"

            pytest.fail(error_msg)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
