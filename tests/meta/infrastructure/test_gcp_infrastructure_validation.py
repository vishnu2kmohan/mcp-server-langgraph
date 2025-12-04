"""
Meta-tests for GCP Infrastructure Validation.

These tests ensure consistency between:
- GitHub Actions workflows (GKE cluster names, service accounts)
- Terraform configurations (service account definitions)
- Environment variables and secrets

Following TDD principles - tests define expected infrastructure state.

CODEX FINDING (2025-11-30):
GCP compliance scan failed because:
1. Cluster name mismatch: workflow used 'mcp-prod-gke' but Terraform uses 'production-mcp-server-langgraph-gke'
2. Missing compliance-scanner service account in Terraform WIF module
3. Inconsistent provider naming (github-provider vs github-actions-provider)

Prevention: These tests validate Terraform and workflow consistency before merge.
"""

import gc
import re

import pytest
from tests.helpers.path_helpers import get_repo_root

# Mark as unit+meta test to ensure it runs in CI
pytestmark = pytest.mark.unit

REPO_ROOT = get_repo_root()
TERRAFORM_WIF_DIR = REPO_ROOT / "terraform" / "environments" / "gcp-staging-wif-only"
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"


@pytest.mark.meta
@pytest.mark.xdist_group(name="testgcpinfrastructurevalidation")
class TestGCPServiceAccountConsistency:
    """Validate that workflow service accounts exist in Terraform."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def terraform_service_accounts(self) -> set[str]:
        """Extract service account IDs from Terraform WIF module."""
        main_tf = TERRAFORM_WIF_DIR / "main.tf"

        if not main_tf.exists():
            pytest.skip("Terraform WIF module not found")

        content = main_tf.read_text()

        # Extract account_id values from service_accounts block
        # Pattern matches: account_id = "service-account-name"
        pattern = r'account_id\s*=\s*"([^"]+)"'
        matches = re.findall(pattern, content)

        return set(matches)

    @pytest.fixture
    def workflow_service_accounts(self) -> dict[str, list[tuple[str, int]]]:
        """Extract service account references from workflows.

        Returns dict mapping SA name to list of (workflow, line_number) tuples.
        """
        sa_refs: dict[str, list[tuple[str, int]]] = {}

        for workflow_file in WORKFLOWS_DIR.glob("*.yaml"):
            content = workflow_file.read_text()
            lines = content.splitlines()

            for line_num, line in enumerate(lines, start=1):
                # Match patterns like: compliance-scanner@project.iam.gserviceaccount.com
                # or: format('compliance-scanner@{0}...')
                matches = re.findall(r"([a-z0-9-]+)@\{?0?\}?\.iam\.gserviceaccount\.com", line)
                for sa_name in matches:
                    if sa_name not in sa_refs:
                        sa_refs[sa_name] = []
                    sa_refs[sa_name].append((workflow_file.name, line_num))

        return sa_refs

    def test_workflow_service_accounts_defined_in_terraform(
        self, terraform_service_accounts: set[str], workflow_service_accounts: dict[str, list[tuple[str, int]]]
    ):
        """
        Ensure all service accounts referenced in workflows are defined in Terraform.

        CODEX FINDING: compliance-scanner was referenced in workflow but not in Terraform.
        This test would have caught it.
        """
        missing = []

        for sa_name, locations in workflow_service_accounts.items():
            # Check if SA is defined in Terraform
            # Account IDs in Terraform use hyphens, workflow references may use underscores
            terraform_variants = {sa_name, sa_name.replace("-", "_"), sa_name.replace("_", "-")}

            if not terraform_variants.intersection(terraform_service_accounts):
                for workflow, line_num in locations:
                    missing.append(f"{workflow}:{line_num} - {sa_name}@*.iam.gserviceaccount.com")

        # Known exceptions: SAs managed outside this module
        known_external_sas = {"github-actions"}  # Base SA from different module
        missing = [m for m in missing if not any(ext in m for ext in known_external_sas)]

        assert not missing, (
            f"Found {len(missing)} service account(s) referenced in workflows but not in Terraform.\\n"
            f"Add these to terraform/environments/gcp-staging-wif-only/main.tf:\\n"
            + "\\n".join(f"  - {m}" for m in missing[:10])
        )


@pytest.mark.meta
@pytest.mark.xdist_group(name="testgkeclusterconsistency")
class TestGKEClusterNameConsistency:
    """Validate GKE cluster name consistency across workflows."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def cluster_references(self) -> list[tuple[str, int, str]]:
        """Extract all GKE cluster references from workflows.

        Returns list of (workflow_file, line_number, cluster_name) tuples.
        """
        refs = []

        for workflow_file in WORKFLOWS_DIR.glob("*.yaml"):
            content = workflow_file.read_text()
            lines = content.splitlines()

            for line_num, line in enumerate(lines, start=1):
                # Match get-credentials commands with explicit cluster names
                match = re.search(r"get-credentials\s+([a-z0-9-]+)", line)
                if match:
                    refs.append((workflow_file.name, line_num, match.group(1)))

        return refs

    def test_no_hardcoded_cluster_names(self, cluster_references: list[tuple[str, int, str]]):
        """
        Ensure workflows use environment variables for cluster names, not hardcoded values.

        CODEX FINDING: gcp-compliance-scan.yaml had hardcoded 'mcp-prod-gke' cluster name.
        This test ensures all cluster names use ${{ env.GKE_CLUSTER }} or similar.
        """
        violations = []

        for workflow, line_num, cluster_name in cluster_references:
            # Check if this is a hardcoded value (not a variable reference)
            if not cluster_name.startswith("$"):
                violations.append(f"{workflow}:{line_num} - hardcoded cluster: '{cluster_name}'")

        assert not violations, (
            f"Found {len(violations)} hardcoded GKE cluster name(s).\\n"
            f"Use environment variables instead: ${{{{ env.GKE_CLUSTER }}}}\\n"
            + "\\n".join(f"  - {v}" for v in violations[:10])
        )

    def test_cluster_names_use_standardized_pattern(self):
        """
        Verify all workflows use standardized cluster naming pattern.

        Expected pattern: environment-mcp-server-langgraph-gke
        Examples:
        - production-mcp-server-langgraph-gke
        - staging-mcp-server-langgraph-gke
        - dev-mcp-server-langgraph-gke
        """
        expected_pattern = re.compile(r"(production|staging|dev)-mcp-server-langgraph-gke")

        # Find all GKE_CLUSTER defaults in workflows
        violations = []

        for workflow_file in WORKFLOWS_DIR.glob("*.yaml"):
            content = workflow_file.read_text()
            lines = content.splitlines()

            for line_num, line in enumerate(lines, start=1):
                # Match default cluster names: GKE_CLUSTER || 'cluster-name'
                match = re.search(r"GKE_CLUSTER\s*\|\|\s*['\"]([^'\"]+)['\"]", line)
                if match:
                    cluster_name = match.group(1)
                    if not expected_pattern.match(cluster_name):
                        violations.append(f"{workflow_file.name}:{line_num} - '{cluster_name}' doesn't match pattern")

        assert not violations, (
            f"Found {len(violations)} cluster name(s) not matching standard pattern.\\n"
            f"Expected: (production|staging|dev)-mcp-server-langgraph-gke\\n" + "\\n".join(f"  - {v}" for v in violations)
        )


@pytest.mark.meta
@pytest.mark.xdist_group(name="testwifproviderconsistency")
class TestWIFProviderConsistency:
    """Validate Workload Identity Provider naming consistency."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_wif_provider_naming_consistent(self):
        """
        Ensure WIF provider naming is consistent across workflows.

        CODEX FINDING: Some workflows used 'github-provider' while Terraform uses 'github-actions-provider'.
        """
        provider_refs: dict[str, list[tuple[str, int]]] = {}

        for workflow_file in WORKFLOWS_DIR.glob("*.yaml"):
            content = workflow_file.read_text()
            lines = content.splitlines()

            for line_num, line in enumerate(lines, start=1):
                # Match provider references in WIF paths
                match = re.search(r"/providers/([a-z0-9-]+)", line)
                if match:
                    provider_name = match.group(1)
                    if provider_name not in provider_refs:
                        provider_refs[provider_name] = []
                    provider_refs[provider_name].append((workflow_file.name, line_num))

        # All should use the same provider name
        if len(provider_refs) > 1:
            expected_provider = "github-actions-provider"
            violations = []

            for provider, locations in provider_refs.items():
                if provider != expected_provider:
                    for workflow, line_num in locations:
                        violations.append(f"{workflow}:{line_num} - uses '{provider}' instead of '{expected_provider}'")

            assert not violations, (
                f"Found {len(violations)} inconsistent WIF provider reference(s).\\n"
                f"All should use '{expected_provider}':\\n" + "\\n".join(f"  - {v}" for v in violations[:10])
            )


@pytest.mark.meta
@pytest.mark.xdist_group(name="testterraformworkflowparity")
class TestTerraformWorkflowParity:
    """Validate that Terraform outputs match workflow expectations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_terraform_outputs_include_all_expected_secrets(self):
        """
        Ensure Terraform outputs include all service account emails needed by workflows.
        """
        outputs_tf = TERRAFORM_WIF_DIR / "outputs.tf"

        if not outputs_tf.exists():
            pytest.skip("Terraform outputs file not found")

        content = outputs_tf.read_text()

        # Expected output keys (based on workflow expectations)
        expected_outputs = [
            "GCP_STAGING_SA_EMAIL",
            "GCP_PRODUCTION_SA_EMAIL",
            "GCP_TERRAFORM_SA_EMAIL",
            "GCP_COMPLIANCE_SA_EMAIL",
            "GCP_WIF_PROVIDER",
        ]

        missing_outputs = []
        for expected in expected_outputs:
            if expected not in content:
                missing_outputs.append(expected)

        assert not missing_outputs, (
            f"Terraform outputs.tf missing {len(missing_outputs)} expected output(s):\\n"
            + "\\n".join(f"  - {o}" for o in missing_outputs)
            + "\\n\\nWorkflows expect these in github_secrets output block."
        )
