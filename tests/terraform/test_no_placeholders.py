"""
Test suite to validate that Terraform configurations contain no placeholder values.

These tests ensure that sensitive configuration values like ACCOUNT_ID, PROJECT_ID,
and ENVIRONMENT are replaced with actual values before deployment.

Following TDD Red-Green-Refactor:
- RED: These tests should FAIL initially (placeholders exist)
- GREEN: After implementing variable substitution, tests should PASS
- REFACTOR: Improve validation logic as needed
"""

import gc
import re
from pathlib import Path

import pytest

# Define project root relative to test file
PROJECT_ROOT = Path(__file__).parent.parent.parent
TERRAFORM_DIR = PROJECT_ROOT / "terraform"


@pytest.mark.xdist_group(name="testterraformplaceholders")
class TestTerraformPlaceholders:
    """Test that Terraform files contain no placeholder values."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    PLACEHOLDER_PATTERNS = [
        r"\bACCOUNT_ID\b",
        r"\bPROJECT_ID\b",
        r"\bENVIRONMENT\b(?![\w-])",  # Not followed by word chars (avoid ENVIRONMENT_NAME)
        r"\bYOUR_PROJECT_ID\b",
        r"\bYOUR_ACCOUNT_ID\b",
        r"\bAZURE_CLIENT_ID\b",
        r'\bCLIENT_ID\b(?=\s|$|")',  # CLIENT_ID as standalone value
        r"00000000-0000-0000-0000-000000000000",  # Dummy GUID
    ]

    # Files that are templates or documentation (allowed to have placeholders)
    EXCLUDED_FILES = {
        "README.md",
        "TEMPLATE.md",
        ".env.template",
        "example.tfvars",
    }

    # Directories to exclude from scanning
    EXCLUDED_DIRS = {
        ".git",
        ".terraform",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
    }

    def _find_terraform_files(self, directory: Path):
        """Recursively find all Terraform files."""
        terraform_files = []

        for path in directory.rglob("*"):
            # Skip excluded directories
            if any(excluded in path.parts for excluded in self.EXCLUDED_DIRS):
                continue

            # Skip excluded files
            if path.name in self.EXCLUDED_FILES:
                continue

            # Check for Terraform files
            if path.is_file() and path.suffix in [".tf", ".tfvars"]:
                terraform_files.append(path)

        return terraform_files

    def _scan_file_for_placeholders(self, file_path: Path):
        """Scan a single file for placeholder patterns."""
        violations = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, start=1):
                    # Skip comments
                    if line.strip().startswith("#") or line.strip().startswith("//"):
                        continue

                    # Skip validation error messages (they may reference placeholders as examples)
                    if "error_message" in line:
                        continue

                    for pattern in self.PLACEHOLDER_PATTERNS:
                        matches = re.finditer(pattern, line)
                        for match in matches:
                            violations.append(
                                {
                                    "file": str(file_path.relative_to(PROJECT_ROOT)),
                                    "line": line_num,
                                    "column": match.start() + 1,
                                    "placeholder": match.group(),
                                    "context": line.strip()[:100],
                                }
                            )
        except Exception as e:
            pytest.fail(f"Error reading file {file_path}: {e}")

        return violations

    def test_no_placeholders_in_terraform_modules(self):
        """
        Test that terraform/modules contains no placeholder values.

        RED: Should FAIL - modules have ACCOUNT_ID, PROJECT_ID placeholders
        GREEN: Should PASS - after variable substitution implemented
        """
        modules_dir = TERRAFORM_DIR / "modules"

        if not modules_dir.exists():
            pytest.skip(f"Modules directory not found: {modules_dir}")

        terraform_files = self._find_terraform_files(modules_dir)
        assert len(terraform_files) > 0, "No Terraform files found in modules"

        all_violations = []
        for tf_file in terraform_files:
            violations = self._scan_file_for_placeholders(tf_file)
            all_violations.extend(violations)

        if all_violations:
            error_msg = "\n\nPlaceholder violations found in Terraform modules:\n"
            for v in all_violations:
                error_msg += f"\n  {v['file']}:{v['line']}:{v['column']}"
                error_msg += f"\n    Found: {v['placeholder']}"
                error_msg += f"\n    Context: {v['context']}\n"

            pytest.fail(error_msg)

    def test_no_placeholders_in_terraform_environments(self):
        """
        Test that terraform/environments contains no placeholder values.

        RED: Should FAIL - environments have placeholder defaults
        GREEN: Should PASS - after real values configured
        """
        environments_dir = TERRAFORM_DIR / "environments"

        if not environments_dir.exists():
            pytest.skip(f"Environments directory not found: {environments_dir}")

        terraform_files = self._find_terraform_files(environments_dir)
        assert len(terraform_files) > 0, "No Terraform files found in environments"

        all_violations = []
        for tf_file in terraform_files:
            violations = self._scan_file_for_placeholders(tf_file)
            all_violations.extend(violations)

        if all_violations:
            error_msg = "\n\nPlaceholder violations found in Terraform environments:\n"
            for v in all_violations:
                error_msg += f"\n  {v['file']}:{v['line']}:{v['column']}"
                error_msg += f"\n    Found: {v['placeholder']}"
                error_msg += f"\n    Context: {v['context']}\n"

            pytest.fail(error_msg)


@pytest.mark.xdist_group(name="testeksendpointsecurity")
class TestEKSEndpointSecurity:
    """Test that EKS API endpoints are not publicly accessible from 0.0.0.0/0."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_eks_endpoint_not_open_to_internet(self):
        """
        Test that EKS cluster endpoints are not accessible from 0.0.0.0/0.

        RED: Should FAIL - currently defaults to ["0.0.0.0/0"]
        GREEN: Should PASS - after restricting to specific CIDR blocks
        """
        eks_files = list(TERRAFORM_DIR.rglob("**/eks/**/*.tf"))
        eks_files.extend(list(TERRAFORM_DIR.rglob("**/prod/**/*.tf")))

        violations = []

        for tf_file in eks_files:
            if not tf_file.is_file():
                continue

            try:
                with open(tf_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    lines = content.split("\n")

                    # Look for public access configuration
                    in_public_access_block = False
                    for line_num, line in enumerate(lines, start=1):
                        # Skip comments and error messages
                        if line.strip().startswith("#") or "error_message" in line:
                            continue

                        if "cluster_endpoint_public_access_cidrs" in line:
                            in_public_access_block = True

                        if in_public_access_block and "0.0.0.0/0" in line and "default" in line:
                            violations.append(
                                {
                                    "file": str(tf_file.relative_to(PROJECT_ROOT)),
                                    "line": line_num,
                                    "issue": "EKS endpoint allows public access from 0.0.0.0/0",
                                    "context": line.strip(),
                                }
                            )
                            in_public_access_block = False

                        # Reset if we hit a closing brace
                        if in_public_access_block and "]" in line:
                            in_public_access_block = False

            except Exception as e:
                pytest.fail(f"Error reading file {tf_file}: {e}")

        if violations:
            error_msg = "\n\nEKS endpoint security violations found:\n"
            for v in violations:
                error_msg += f"\n  {v['file']}:{v['line']}"
                error_msg += f"\n    Issue: {v['issue']}"
                error_msg += f"\n    Context: {v['context']}\n"

            pytest.fail(error_msg)

    def test_eks_endpoint_cidr_validation_exists(self):
        """
        Test that EKS module has validation preventing 0.0.0.0/0 in production.

        RED: Should FAIL - no validation currently exists
        GREEN: Should PASS - after adding validation blocks
        """
        eks_module_vars = TERRAFORM_DIR / "modules" / "eks" / "variables.tf"

        if not eks_module_vars.exists():
            pytest.skip(f"EKS module variables not found: {eks_module_vars}")

        with open(eks_module_vars, "r", encoding="utf-8") as f:
            content = f.read()

        # Check for validation block in cluster_endpoint_public_access_cidrs variable
        has_validation = "validation {" in content and "cluster_endpoint_public_access_cidrs" in content

        assert has_validation, (
            "EKS module should have validation to prevent 0.0.0.0/0 in " "cluster_endpoint_public_access_cidrs variable"
        )


@pytest.mark.xdist_group(name="testgkenetworksecurity")
class TestGKENetworkSecurity:
    """Test that GKE control plane has proper network security."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_gke_prod_private_endpoint_enabled(self):
        """
        Test that GKE production uses private endpoint.

        RED: Should FAIL - currently enable_private_endpoint = false
        GREEN: Should PASS - after enabling private endpoint
        """
        gke_prod_vars = TERRAFORM_DIR / "environments" / "gcp-prod" / "variables.tf"

        if not gke_prod_vars.exists():
            pytest.skip(f"GKE prod variables not found: {gke_prod_vars}")

        with open(gke_prod_vars, "r", encoding="utf-8") as f:
            content = f.read()
            lines = content.split("\n")

        # Find enable_private_endpoint variable
        in_private_endpoint_block = False
        private_endpoint_value = None

        for line in lines:
            if 'variable "enable_private_endpoint"' in line:
                in_private_endpoint_block = True

            if in_private_endpoint_block and "default" in line and "=" in line:
                # Extract boolean value
                if "true" in line.lower():
                    private_endpoint_value = True
                elif "false" in line.lower():
                    private_endpoint_value = False
                in_private_endpoint_block = False

        assert private_endpoint_value is True, (
            "GKE production should have enable_private_endpoint = true for security. "
            f"Currently set to: {private_endpoint_value}"
        )

    def test_gke_prod_authorized_networks_restricted(self):
        """
        Test that GKE authorized networks are restricted to specific VPC CIDRs.

        RED: Should FAIL - currently allows entire 10.0.0.0/8 space
        GREEN: Should PASS - after restricting to specific /16 or /24 ranges
        """
        gke_prod_vars = TERRAFORM_DIR / "environments" / "gcp-prod" / "variables.tf"

        if not gke_prod_vars.exists():
            pytest.skip(f"GKE prod variables not found: {gke_prod_vars}")

        with open(gke_prod_vars, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Check for overly broad CIDR blocks in actual configuration (not comments)
        overly_broad_cidrs = [
            "10.0.0.0/8",  # 16.7M IPs
            "172.16.0.0/12",  # 1M IPs
            "192.168.0.0/16",  # 65K IPs
        ]

        violations = []
        for line_num, line in enumerate(lines, start=1):
            # Skip comments
            if line.strip().startswith("#"):
                continue

            # Check if line contains cidr_block assignment
            if "cidr_block" in line and "=" in line:
                for cidr in overly_broad_cidrs:
                    if cidr in line:
                        violations.append(cidr)

        assert len(violations) == 0, (
            f"GKE production authorized networks should not use overly broad CIDR blocks. "
            f"Found: {violations}. Use specific /16 or /24 ranges for your VPC instead."
        )

    def test_gke_module_authorized_networks_validation(self):
        """
        Test that GKE module validates non-empty CIDRs when enabled.

        RED: Should FAIL - no validation currently exists
        GREEN: Should PASS - after adding validation
        """
        gke_module_vars = TERRAFORM_DIR / "modules" / "gke-autopilot" / "variables.tf"

        if not gke_module_vars.exists():
            pytest.skip(f"GKE module variables not found: {gke_module_vars}")

        with open(gke_module_vars, "r", encoding="utf-8") as f:
            content = f.read()

        # Check for validation block for master_authorized_networks_cidrs
        has_validation = (
            "validation {" in content
            and "master_authorized_networks_cidrs" in content
            and "enable_master_authorized_networks" in content
        )

        assert has_validation, (
            "GKE module should validate that master_authorized_networks_cidrs is "
            "non-empty when enable_master_authorized_networks is true"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
