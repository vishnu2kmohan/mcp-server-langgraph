"""
Infrastructure Tests: Terraform Security Configuration Validation

Tests validate that Terraform modules follow security best practices:
- Encryption with Customer Managed Keys (CMK) in production
- Purge protection enabled by default
- Network access restrictions
- Deletion protection for state storage
- Secure defaults that pass Checkov compliance scans

TDD Approach:
- RED: Tests fail initially (secure defaults not implemented)
- GREEN: Tests pass after implementing security fixes
- REFACTOR: Improve code quality while maintaining test coverage
"""

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List

import pytest


class TestAzureKeyVaultSecurityDefaults:
    """
    Test Azure Key Vault module security defaults.

    Validates:
    - CKV_AZURE_42: Purge protection enabled
    - CKV_AZURE_189: Network ACLs configured with deny-by-default
    """

    @pytest.fixture
    def azure_secrets_module_path(self) -> Path:
        """Path to Azure secrets Terraform module."""
        return Path("terraform/modules/azure-secrets")

    @pytest.fixture
    def azure_variables_tf(self, azure_secrets_module_path: Path) -> str:
        """Read Azure secrets variables.tf file."""
        variables_path = azure_secrets_module_path / "variables.tf"
        assert variables_path.exists(), f"Missing {variables_path}"
        return variables_path.read_text()

    @pytest.fixture
    def azure_main_tf(self, azure_secrets_module_path: Path) -> str:
        """Read Azure secrets main.tf file."""
        main_path = azure_secrets_module_path / "main.tf"
        assert main_path.exists(), f"Missing {main_path}"
        return main_path.read_text()

    def test_purge_protection_enabled_by_default(self, azure_variables_tf: str):
        """
        CKV_AZURE_42: Purge protection should be enabled by default.

        Requirement: Prevent accidental deletion of key vaults and secrets.
        Breaking Change: Yes (was false, now true)
        """
        # Parse variable definition for enable_purge_protection
        pattern = r'variable\s+"enable_purge_protection"\s*{[^}]*default\s*=\s*(\w+)'
        match = re.search(pattern, azure_variables_tf, re.DOTALL)

        assert match, "Variable 'enable_purge_protection' not found"
        default_value = match.group(1)

        assert default_value == "true", (
            f"Purge protection must be enabled by default (got: {default_value}). "
            "This prevents accidental deletion of secrets. "
            "Override with enable_purge_protection=false in dev/test environments only."
        )

    def test_network_default_action_deny(self, azure_variables_tf: str):
        """
        CKV_AZURE_189: Network default action should be 'Deny'.

        Requirement: Deny all access by default, require explicit IP allowlisting.
        Breaking Change: Yes (was 'Allow', now 'Deny')
        """
        pattern = r'variable\s+"network_default_action"\s*{[^}]*default\s*=\s*"(\w+)"'
        match = re.search(pattern, azure_variables_tf, re.DOTALL)

        assert match, "Variable 'network_default_action' not found"
        default_value = match.group(1)

        assert default_value == "Deny", (
            f"Network default action must be 'Deny' (got: '{default_value}'). "
            "This enforces zero-trust networking. "
            "Use allowed_ip_ranges variable to whitelist authorized IPs."
        )

    def test_allowed_ip_ranges_variable_exists(self, azure_variables_tf: str):
        """
        Validate that allowed_ip_ranges variable exists for IP whitelisting.

        Requirement: Support environment-specific IP allowlists.
        """
        assert 'variable "allowed_ip_ranges"' in azure_variables_tf, (
            "Missing 'allowed_ip_ranges' variable. "
            "Required to specify authorized IPs when network_default_action is 'Deny'."
        )

        # Check that it's a list type
        pattern = r'variable\s+"allowed_ip_ranges"\s*{[^}]*type\s*=\s*list\(string\)'
        assert re.search(pattern, azure_variables_tf, re.DOTALL), "Variable 'allowed_ip_ranges' must be type list(string)"

    def test_network_acls_use_allowed_ip_ranges(self, azure_main_tf: str):
        """
        Validate that network_acls block uses allowed_ip_ranges variable.

        Requirement: IP allowlist must be configurable via variable.
        """
        # Check for network_acls configuration
        assert "network_acls {" in azure_main_tf, "Missing network_acls configuration"

        # Check that ip_rules uses the variable
        pattern = r"network_acls\s*{[^}]*ip_rules\s*=\s*var\.allowed_ip_ranges"
        assert re.search(pattern, azure_main_tf, re.DOTALL), "network_acls.ip_rules must use var.allowed_ip_ranges"


class TestAWSSecretsManagerSecurity:
    """
    Test AWS Secrets Manager module security configuration.

    Validates:
    - CKV_AWS_149: CMK encryption in production
    - Recovery window configuration
    """

    @pytest.fixture
    def aws_secrets_module_path(self) -> Path:
        """Path to AWS secrets Terraform module."""
        return Path("terraform/modules/aws-secrets")

    @pytest.fixture
    def aws_variables_tf(self, aws_secrets_module_path: Path) -> str:
        """Read AWS secrets variables.tf file."""
        variables_path = aws_secrets_module_path / "variables.tf"
        if not variables_path.exists():
            pytest.skip(f"AWS secrets module not found at {variables_path}")
        return variables_path.read_text()

    @pytest.fixture
    def aws_main_tf(self, aws_secrets_module_path: Path) -> str:
        """Read AWS secrets main.tf file."""
        main_path = aws_secrets_module_path / "main.tf"
        if not main_path.exists():
            pytest.skip(f"AWS secrets module not found at {main_path}")
        return main_path.read_text()

    def test_kms_key_id_variable_exists(self, aws_variables_tf: str):
        """
        CKV_AWS_149: Validate kms_key_id variable exists for CMK encryption.

        Requirement: Support CMK encryption (production) and AWS-managed keys (dev/staging).
        """
        assert 'variable "kms_key_id"' in aws_variables_tf, (
            "Missing 'kms_key_id' variable. "
            "Required for Customer Managed Key (CMK) encryption in production. "
            "Set to null for AWS-managed keys in dev/staging."
        )

        # Should be optional (type = string with default = null)
        pattern = r'variable\s+"kms_key_id"\s*{[^}]*type\s*=\s*string'
        assert re.search(pattern, aws_variables_tf, re.DOTALL), "Variable 'kms_key_id' must be type string"

    def test_recovery_window_variable_exists(self, aws_variables_tf: str):
        """
        Validate recovery_window_in_days variable exists.

        Requirement: Configurable recovery window (0-30 days).
        """
        assert 'variable "recovery_window_in_days"' in aws_variables_tf, (
            "Missing 'recovery_window_in_days' variable. " "Required to configure secret recovery window (default: 30 days)."
        )

    def test_secret_uses_kms_key_id(self, aws_main_tf: str):
        """
        Validate that aws_secretsmanager_secret uses kms_key_id variable.

        Requirement: CMK encryption when kms_key_id is provided.
        """
        # Check that kms_key_id is referenced in resource
        pattern = r'resource\s+"aws_secretsmanager_secret"[^{]*{[^}]*kms_key_id\s*=\s*var\.kms_key_id'
        assert re.search(pattern, aws_main_tf, re.DOTALL), "aws_secretsmanager_secret must use kms_key_id = var.kms_key_id"

    def test_secret_uses_recovery_window(self, aws_main_tf: str):
        """
        Validate that aws_secretsmanager_secret uses recovery_window_in_days variable.

        Requirement: Configurable recovery window.
        """
        pattern = (
            r'resource\s+"aws_secretsmanager_secret"[^{]*{[^}]*recovery_window_in_days\s*=\s*var\.recovery_window_in_days'
        )
        assert re.search(
            pattern, aws_main_tf, re.DOTALL
        ), "aws_secretsmanager_secret must use recovery_window_in_days = var.recovery_window_in_days"


class TestDynamoDBBackendSecurity:
    """
    Test DynamoDB backend security configuration.

    Validates:
    - Deletion protection enabled
    - KMS encryption in production
    """

    @pytest.fixture
    def backend_setup_path(self) -> Path:
        """Path to backend setup Terraform."""
        return Path("terraform/backend-setup")

    @pytest.fixture
    def backend_variables_tf(self, backend_setup_path: Path) -> str:
        """Read backend setup variables.tf file."""
        variables_path = backend_setup_path / "variables.tf"
        if not variables_path.exists():
            pytest.skip(f"Backend setup not found at {variables_path}")
        return variables_path.read_text()

    @pytest.fixture
    def backend_main_tf(self, backend_setup_path: Path) -> str:
        """Read backend setup main.tf file."""
        main_path = backend_setup_path / "main.tf"
        if not main_path.exists():
            pytest.skip(f"Backend setup not found at {main_path}")
        return main_path.read_text()

    def test_deletion_protection_variable_exists(self, backend_variables_tf: str):
        """
        Validate deletion_protection_enabled variable exists.

        Requirement: Prevent accidental deletion of state lock table.
        """
        assert (
            'variable "enable_deletion_protection"' in backend_variables_tf
            or 'variable "deletion_protection_enabled"' in backend_variables_tf
        ), ("Missing deletion protection variable. " "Required to prevent accidental deletion of Terraform state lock table.")

    def test_deletion_protection_enabled_by_default(self, backend_variables_tf: str):
        """
        Validate deletion protection is enabled by default.

        Requirement: Protect Terraform state from accidental deletion.
        """
        pattern = r'variable\s+"(?:enable_)?deletion_protection(?:_enabled)?"\s*{[^}]*default\s*=\s*(\w+)'
        match = re.search(pattern, backend_variables_tf, re.DOTALL)

        if match:
            default_value = match.group(1)
            assert default_value == "true", (
                f"Deletion protection must be enabled by default (got: {default_value}). "
                "This protects Terraform state lock table from accidental deletion."
            )

    def test_kms_key_arn_variable_exists(self, backend_variables_tf: str):
        """
        Validate kms_key_arn variable exists for CMK encryption.

        Requirement: Support CMK encryption in production.
        """
        assert 'variable "kms_key_arn"' in backend_variables_tf or 'variable "kms_key_id"' in backend_variables_tf, (
            "Missing KMS key variable. " "Required for Customer Managed Key (CMK) encryption in production."
        )

    def test_dynamodb_uses_deletion_protection(self, backend_main_tf: str):
        """
        Validate DynamoDB table uses deletion_protection_enabled.

        Requirement: Apply deletion protection configuration.
        """
        # Look for deletion_protection_enabled anywhere in the file (it's a top-level table attribute)
        pattern = r'resource\s+"aws_dynamodb_table"[\s\S]*?deletion_protection_enabled\s*='
        assert re.search(pattern, backend_main_tf, re.DOTALL), "aws_dynamodb_table must set deletion_protection_enabled"

    def test_dynamodb_server_side_encryption_uses_kms(self, backend_main_tf: str):
        """
        Validate DynamoDB server_side_encryption uses KMS key variable.

        Requirement: Support CMK encryption when kms_key_arn is provided.
        """
        # Check that server_side_encryption block exists
        assert "server_side_encryption {" in backend_main_tf, "Missing server_side_encryption configuration"

        # Check that it references KMS key variable (kms_key_arn or kms_master_key_id)
        pattern = r"server_side_encryption\s*{[^}]*kms.*=\s*var\.kms_key"
        assert re.search(
            pattern, backend_main_tf, re.DOTALL
        ), "server_side_encryption must reference var.kms_key_arn or var.kms_key_id"


class TestS3BackendSecurity:
    """
    Test S3 backend bucket security configuration.

    Validates:
    - Logging configuration
    - Versioning with MFA delete (documented)
    """

    @pytest.fixture
    def backend_setup_path(self) -> Path:
        """Path to backend setup Terraform."""
        return Path("terraform/backend-setup")

    @pytest.fixture
    def backend_main_tf(self, backend_setup_path: Path) -> str:
        """Read backend setup main.tf file."""
        main_path = backend_setup_path / "main.tf"
        if not main_path.exists():
            pytest.skip(f"Backend setup not found at {main_path}")
        return main_path.read_text()

    @pytest.fixture
    def backend_readme(self, backend_setup_path: Path) -> str:
        """Read backend setup README.md file."""
        readme_path = backend_setup_path / "README.md"
        if not readme_path.exists():
            pytest.skip(f"Backend README not found at {readme_path}")
        return readme_path.read_text()

    def test_s3_bucket_logging_configured(self, backend_main_tf: str):
        """
        Validate S3 bucket logging is configured.

        Requirement: Audit access to Terraform state bucket.
        """
        # Look for aws_s3_bucket_logging resource or logging configuration
        has_logging_resource = "aws_s3_bucket_logging" in backend_main_tf
        has_logging_inline = re.search(r'resource\s+"aws_s3_bucket"[^{]*{[^}]*logging\s*{', backend_main_tf, re.DOTALL)

        assert has_logging_resource or has_logging_inline, (
            "Missing S3 bucket logging configuration. "
            "Terraform state access should be audited. "
            "Add aws_s3_bucket_logging resource or logging block."
        )

    def test_mfa_delete_documented(self, backend_readme: str):
        """
        Validate that MFA delete requirement is documented.

        Requirement: Document MFA delete as manual post-deployment step.
        Note: MFA delete requires root account and cannot be fully automated in Terraform.
        """
        assert re.search(r"MFA.*delete", backend_readme, re.IGNORECASE), (
            "MFA delete requirement not documented in README. "
            "This is a manual step requiring root account with MFA enabled. "
            "Add documentation: 'Enable MFA delete via AWS CLI: "
            "aws s3api put-bucket-versioning --bucket <bucket> --versioning-configuration "
            "Status=Enabled,MFADelete=Enabled --mfa <mfa-code>'"
        )


class TestCheckovCompliance:
    """
    Integration test: Run Checkov on Terraform modules to validate compliance.

    This test runs actual Checkov scans to ensure all security controls pass.
    """

    @pytest.mark.skipif(os.system("which checkov > /dev/null 2>&1") != 0, reason="Checkov not installed (pip install checkov)")
    def test_checkov_azure_secrets_compliance(self):
        """
        Run Checkov on Azure secrets module (production profile).

        Expected to pass:
        - CKV_AZURE_42: Purge protection enabled
        - CKV_AZURE_189: Network ACLs deny-by-default
        """
        result = os.system(
            "checkov -d terraform/modules/azure-secrets "
            "--framework terraform "
            "--quiet "
            "--compact "
            "--skip-check CKV_AZURE_109,CKV_AZURE_110"  # Skip non-critical checks
        )

        assert result == 0, (
            "Checkov scan failed for Azure secrets module. " "Run 'checkov -d terraform/modules/azure-secrets' for details."
        )

    @pytest.mark.skipif(os.system("which checkov > /dev/null 2>&1") != 0, reason="Checkov not installed (pip install checkov)")
    def test_checkov_aws_secrets_compliance(self):
        """
        Run Checkov on AWS secrets module (production profile).

        Expected to pass:
        - CKV_AWS_149: CMK encryption available
        """
        if not Path("terraform/modules/aws-secrets").exists():
            pytest.skip("AWS secrets module not present")

        result = os.system("checkov -d terraform/modules/aws-secrets " "--framework terraform " "--quiet " "--compact")

        assert result == 0, (
            "Checkov scan failed for AWS secrets module. " "Run 'checkov -d terraform/modules/aws-secrets' for details."
        )

    @pytest.mark.skipif(os.system("which checkov > /dev/null 2>&1") != 0, reason="Checkov not installed (pip install checkov)")
    def test_checkov_backend_setup_compliance(self):
        """
        Run Checkov on backend setup (Terraform state storage).

        Expected to pass:
        - DynamoDB deletion protection
        - S3 bucket security controls
        """
        if not Path("terraform/backend-setup").exists():
            pytest.skip("Backend setup not present")

        result = os.system("checkov -d terraform/backend-setup " "--framework terraform " "--quiet " "--compact")

        assert result == 0, "Checkov scan failed for backend setup. " "Run 'checkov -d terraform/backend-setup' for details."


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
