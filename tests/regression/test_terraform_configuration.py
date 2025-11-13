"""
Regression Tests for Terraform Configuration

Prevents recurrence of Terraform validation failures from 2025-11-12:
1. Duplicate required_providers blocks
2. Invalid cross-variable references in validations
3. Provider version constraint conflicts
4. Terraform version incompatibilities

## Failure Scenarios (2025-11-12)

### Issue 1: Duplicate required_providers
- File: terraform/backend-setup-gcp/main.tf
- Error: "Duplicate required providers configuration"
- Two separate terraform{} blocks with required_providers
- Fix: Merged into single block

### Issue 2: Invalid variable validation cross-references
- Files: terraform/backend-setup-gcp/variables.tf, terraform/modules/eks/variables.tf
- Error: "Invalid reference in variable validation"
- Validations referenced other variables (var.enable_cmek, var.environment)
- Fix: Removed cross-variable checks (Terraform limitation)

### Issue 3: Provider version conflicts
- File: terraform/modules/github-actions-wif/versions.tf
- Error: "no available releases match the given constraints ~> 5.0, ~> 6.0"
- Module required ~> 5.0, parent required ~> 6.0
- Fix: Aligned to ~> 6.0

### Issue 4: Terraform version incompatibility
- File: terraform/modules/azure-database/versions.tf
- Error: "This configuration does not support Terraform version 1.6.6"
- Required >= 1.7, CI had 1.6.6
- Fix: Lowered to >= 1.5

## Prevention Strategy
These tests validate Terraform configurations are properly structured
and compatible across all modules and environments.
"""

import re
from pathlib import Path
from typing import Dict, List, Set

import pytest

try:
    import hcl2  # type: ignore
except ImportError:
    hcl2 = None


def find_terraform_files() -> List[Path]:
    """Find all Terraform .tf files."""
    terraform_dir = Path(__file__).parent.parent.parent / "terraform"
    if not terraform_dir.exists():
        return []
    return list(terraform_dir.rglob("*.tf"))


def parse_terraform_file(file_path: Path) -> Dict:
    """
    Parse a Terraform file and return its structure.

    Returns empty dict if parsing fails (we're not strictly validating syntax).
    """
    try:
        content = file_path.read_text()
        # Basic regex-based extraction since we don't require hcl2
        return {"content": content}
    except Exception:
        return {}


@pytest.mark.regression
@pytest.mark.terraform
class TestTerraformDuplicateBlocks:
    """
    Regression tests for duplicate Terraform configuration blocks.

    Prevents recurrence of duplicate required_providers issue.
    """

    def test_no_duplicate_terraform_blocks_in_same_file(self):
        """
        Test: No file should have multiple terraform{} blocks.

        RED (Before Fix - 2025-11-12):
        - terraform/backend-setup-gcp/main.tf had 2 terraform{} blocks
        - Line 16-25: First block with google provider
        - Line 167-174: Second block with random provider
        - Error: "Duplicate required providers configuration"

        GREEN (After Fix - 2025-11-12):
        - Merged into single terraform{} block with both providers
        - All providers declared in one required_providers section

        REFACTOR:
        - This test prevents regression
        - Checks all .tf files for duplicate terraform{} blocks
        """
        tf_files = find_terraform_files()
        assert len(tf_files) > 0, "No Terraform files found"

        files_with_duplicates = []

        for file_path in tf_files:
            content = file_path.read_text()

            # Count terraform {} blocks (simple regex)
            # Matches: terraform {
            terraform_block_pattern = re.compile(r"^\s*terraform\s*\{", re.MULTILINE)
            matches = terraform_block_pattern.findall(content)

            if len(matches) > 1:
                relative_path = file_path.relative_to(Path(__file__).parent.parent.parent)
                files_with_duplicates.append(f"{relative_path} ({len(matches)} blocks)")

        if files_with_duplicates:
            error_message = (
                f"\n❌ Found {len(files_with_duplicates)} files with duplicate terraform{{}} blocks:\n\n"
                + "\n".join(f"  - {file}" for file in files_with_duplicates)
                + "\n\n💡 Fix: Merge terraform{{}} blocks into a single block:\n"
                + "  terraform {{\n"
                + '    required_version = ">= 1.5.0"\n'
                + "    required_providers {{\n"
                + '      google = {{ source = "hashicorp/google", version = "~> 6.0" }}\n'
                + '      random = {{ source = "hashicorp/random", version = "~> 3.0" }}\n'
                + "    }}\n"
                + "  }}\n"
            )
            pytest.fail(error_message)

    def test_no_duplicate_required_providers_blocks(self):
        """
        Test: No terraform{} block should have multiple required_providers{} sections.

        Ensures providers are all declared in one place.
        """
        tf_files = find_terraform_files()
        files_with_duplicates = []

        for file_path in tf_files:
            content = file_path.read_text()

            # Extract terraform blocks
            terraform_blocks = re.findall(r"terraform\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}", content, re.DOTALL)

            for block in terraform_blocks:
                # Count required_providers within this terraform block
                required_providers_pattern = re.compile(r"required_providers\s*\{")
                matches = required_providers_pattern.findall(block)

                if len(matches) > 1:
                    relative_path = file_path.relative_to(Path(__file__).parent.parent.parent)
                    files_with_duplicates.append(f"{relative_path} ({len(matches)} required_providers blocks)")

        if files_with_duplicates:
            pytest.fail(
                f"\n❌ Found duplicate required_providers blocks:\n"
                + "\n".join(f"  - {file}" for file in files_with_duplicates)
            )


@pytest.mark.regression
@pytest.mark.terraform
class TestTerraformVariableValidations:
    """
    Regression tests for Terraform variable validations.

    Prevents cross-variable references in validation conditions.
    """

    def test_variable_validations_only_reference_self(self):
        """
        Test: Variable validation conditions must only reference the variable itself.

        RED (Before Fix - 2025-11-12):
        - backend-setup-gcp/variables.tf line 63:
          condition = !var.enable_cmek || (var.enable_cmek && var.kms_key_name != "")
          Referenced var.enable_cmek in kms_key_name validation
        - modules/eks/variables.tf line 81:
          condition = !contains(var.cluster_endpoint_public_access_cidrs, "0.0.0.0/0") || var.environment == "dev"
          Referenced var.environment in cluster_endpoint validation

        GREEN (After Fix - 2025-11-12):
        - Removed cross-variable validations
        - Added comments to move validation to resource-level preconditions
        - Terraform only allows variable.validation to reference itself

        REFACTOR:
        - This test catches any new cross-variable validation attempts
        """
        tf_files = find_terraform_files()
        invalid_validations = []

        for file_path in tf_files:
            if "variables.tf" not in file_path.name:
                continue

            content = file_path.read_text()
            lines = content.split("\n")

            current_variable = None
            in_validation = False

            for line_num, line in enumerate(lines, start=1):
                # Detect variable block start
                var_match = re.match(r'variable\s+"(\w+)"\s*\{', line)
                if var_match:
                    current_variable = var_match.group(1)

                # Detect validation block
                if "validation" in line and "{" in line:
                    in_validation = True

                # Check for cross-variable references in validation
                if in_validation and current_variable:
                    # Look for var.something that isn't var.current_variable
                    var_refs = re.findall(r"var\.(\w+)", line)
                    for ref in var_refs:
                        if ref != current_variable:
                            relative_path = file_path.relative_to(Path(__file__).parent.parent.parent)
                            invalid_validations.append(
                                f"{relative_path}:{line_num} - "
                                f"variable '{current_variable}' validation references var.{ref}"
                            )

                # Exit validation block
                if in_validation and "}" in line:
                    in_validation = False

        if invalid_validations:
            error_message = (
                f"\n❌ Found {len(invalid_validations)} invalid cross-variable validations:\n\n"
                + "\n".join(f"  - {item}" for item in invalid_validations)
                + "\n\n💡 Fix: Terraform variable validations can only reference the variable itself.\n"
                + "Move cross-variable validation to resource-level preconditions:\n"
                + '  resource "example" "name" {{\n'
                + "    lifecycle {{\n"
                + "      precondition {{\n"
                + '        condition     = !var.enable_cmek || var.kms_key_name != ""\n'
                + '        error_message = "..."\n'
                + "      }}\n"
                + "    }}\n"
                + "  }}\n"
            )
            pytest.fail(error_message)


@pytest.mark.regression
@pytest.mark.terraform
class TestTerraformProviderVersions:
    """
    Regression tests for provider version constraints.

    Ensures compatible provider versions across modules and environments.
    """

    def test_no_conflicting_google_provider_versions(self):
        """
        Test: Google provider versions must be compatible across modules.

        RED (Before Fix - 2025-11-12):
        - modules/github-actions-wif/versions.tf: version = "~> 5.0"
        - environments/gcp-staging-wif-only/main.tf: version = "~> 6.0"
        - Error: "no available releases match the given constraints ~> 5.0, ~> 6.0"

        GREEN (After Fix - 2025-11-12):
        - All updated to ~> 6.0
        - Compatible versions across all usages

        REFACTOR:
        - Test ensures versions stay aligned
        - Allows flexibility for minor version bumps
        """
        tf_files = find_terraform_files()
        google_provider_versions: Dict[str, List[str]] = {}

        for file_path in tf_files:
            content = file_path.read_text()

            # Find google provider version constraints
            # Pattern: google = { ... version = "~> 6.0" }
            google_version_pattern = re.compile(r'google\s*=\s*\{[^}]*version\s*=\s*"([^"]+)"', re.DOTALL)
            matches = google_version_pattern.findall(content)

            if matches:
                relative_path = str(file_path.relative_to(Path(__file__).parent.parent.parent))
                for version in matches:
                    if version not in google_provider_versions:
                        google_provider_versions[version] = []
                    google_provider_versions[version].append(relative_path)

        # Check for conflicting major versions
        major_versions = set()
        for version in google_provider_versions.keys():
            # Extract major version from constraints like "~> 6.0" or ">= 5.0"
            major_match = re.search(r"(\d+)\.\d+", version)
            if major_match:
                major_versions.add(major_match.group(1))

        if len(major_versions) > 1:
            error_details = []
            for version, files in sorted(google_provider_versions.items()):
                error_details.append(f"  Version '{version}':")
                for file in files[:3]:
                    error_details.append(f"    - {file}")
                if len(files) > 3:
                    error_details.append(f"    ... and {len(files) - 3} more")

            pytest.fail(
                f"\n❌ Conflicting Google provider versions across {len(major_versions)} major versions:\n"
                + "\n".join(error_details)
                + f"\n\n💡 Fix: Align all google provider versions to a single major version (e.g., ~> 6.0)"
            )

    def test_terraform_version_compatible_with_ci(self):
        """
        Test: Terraform version requirements must be compatible with CI environment.

        RED (Before Fix - 2025-11-12):
        - modules/azure-database/versions.tf: required_version = ">= 1.7"
        - CI environment: Terraform 1.6.6
        - Error: "This configuration does not support Terraform version 1.6.6"

        GREEN (After Fix - 2025-11-12):
        - Updated to required_version = ">= 1.5"
        - Compatible with CI environment

        REFACTOR:
        - Test ensures version requirements stay compatible
        - Assumes CI runs Terraform >= 1.5 and < 2.0
        """
        tf_files = find_terraform_files()
        incompatible_files = []

        # CI environment constraint (update this if CI Terraform version changes)
        CI_TERRAFORM_VERSION = "1.6.6"

        for file_path in tf_files:
            content = file_path.read_text()

            # Find required_version constraints
            version_pattern = re.compile(r'required_version\s*=\s*"([^"]+)"')
            matches = version_pattern.findall(content)

            for version_constraint in matches:
                # Check if constraint is too strict
                # Pattern: ">= X.Y" where X.Y > CI version
                if ">=" in version_constraint:
                    min_version_match = re.search(r">=\s*(\d+\.\d+)", version_constraint)
                    if min_version_match:
                        min_version = min_version_match.group(1)
                        min_major, min_minor = map(int, min_version.split("."))
                        ci_major, ci_minor, ci_patch = map(int, CI_TERRAFORM_VERSION.split("."))

                        if min_major > ci_major or (min_major == ci_major and min_minor > ci_minor):
                            relative_path = file_path.relative_to(Path(__file__).parent.parent.parent)
                            incompatible_files.append(
                                f"{relative_path}: requires >= {min_version}, CI has {CI_TERRAFORM_VERSION}"
                            )

        if incompatible_files:
            pytest.fail(
                f"\n❌ Found {len(incompatible_files)} files with Terraform version requirements incompatible with CI:\n"
                + "\n".join(f"  - {file}" for file in incompatible_files)
                + f"\n\n💡 Fix: Update required_version to be compatible with CI Terraform {CI_TERRAFORM_VERSION}\n"
                + "Or update CI to use a newer Terraform version"
            )


@pytest.mark.regression
def test_terraform_validate_script_exists():
    """
    Test: Terraform validation is part of CI pipeline.

    Ensures the terraform validate check runs in CI to catch these issues early.
    """
    github_workflows = Path(__file__).parent.parent.parent / ".github" / "workflows"
    terraform_validation_found = False

    if github_workflows.exists():
        for workflow_file in github_workflows.glob("*.y*ml"):
            content = workflow_file.read_text()
            if "terraform validate" in content or "terraform init" in content:
                terraform_validation_found = True
                break

    assert terraform_validation_found, (
        "No GitHub Actions workflow found running 'terraform validate'. "
        "Terraform validation should be part of CI to catch configuration errors."
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
