"""
Regression tests for ServiceAccount naming consistency.

This module prevents regression of the ServiceAccount naming issue discovered
in CI Run #19311976718 where overlay ServiceAccounts were missing the -sa suffix,
causing Workload Identity binding failures.

TDD Approach:
1. Test that all base ServiceAccounts follow naming convention
2. Test that overlay ServiceAccounts match base naming (after removing env prefix)
3. Test that critical components have correct naming
4. Test validation script catches naming errors

Regression Prevention:
- Run #19311976718: ServiceAccount 'preview-openfga-sa' missing annotation
  Root cause: ServiceAccount was named 'openfga' instead of 'openfga-sa'
- Run #19311976718: 5 deployment validation failures
  Root cause: Naming inconsistencies between base and overlays
"""

import gc
import subprocess

import pytest
import yaml
from tests.helpers.path_helpers import get_repo_root

# Mark as unit test to ensure it runs in CI
pytestmark = [pytest.mark.unit, pytest.mark.validation]

REPO_ROOT = get_repo_root()
BASE_SA_PATH = REPO_ROOT / "deployments" / "base" / "serviceaccounts.yaml"
STAGING_OVERLAY = REPO_ROOT / "deployments" / "overlays" / "preview-gke"
PRODUCTION_OVERLAY = REPO_ROOT / "deployments" / "overlays" / "production-gke"


@pytest.mark.xdist_group(name="testbaseserviceaccountnaming")
class TestBaseServiceAccountNaming:
    """Test base ServiceAccount naming conventions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_all_base_serviceaccounts_have_sa_suffix(self):
        """All base ServiceAccounts must end with -sa suffix."""
        with open(BASE_SA_PATH) as f:
            docs = list(yaml.safe_load_all(f))

        service_accounts = [doc for doc in docs if doc and doc.get("kind") == "ServiceAccount"]

        assert len(service_accounts) > 0, "No ServiceAccounts found in base"

        for sa in service_accounts:
            name = sa["metadata"]["name"]
            assert name.endswith("-sa"), f"ServiceAccount '{name}' must end with -sa suffix"

    def test_critical_infrastructure_components_exist(self):
        """Critical infrastructure components have ServiceAccounts in base."""
        with open(BASE_SA_PATH) as f:
            docs = list(yaml.safe_load_all(f))

        sa_names = {doc["metadata"]["name"] for doc in docs if doc and doc.get("kind") == "ServiceAccount"}

        required_components = {
            "postgres-sa",  # Database
            "redis-sa",  # Cache/Sessions
            "openfga-sa",  # Authorization (THE REGRESSION)
            "keycloak-sa",  # Authentication (THE REGRESSION)
        }

        for component in required_components:
            assert component in sa_names, f"Required ServiceAccount '{component}' not found in base"


@pytest.mark.xdist_group(name="testoverlayserviceaccountnaming")
class TestOverlayServiceAccountNaming:
    """Test overlay ServiceAccount naming matches base."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_staging_openfga_serviceaccount_has_sa_suffix(self):
        """
        Regression test for Run #19311976718.

        The overlay ServiceAccount for OpenFGA must be named 'openfga-sa',
        not 'openfga'. After kustomization patches, it becomes 'preview-openfga-sa'.
        """
        sa_file = STAGING_OVERLAY / "serviceaccount-openfga.yaml"
        assert sa_file.exists(), f"ServiceAccount file not found: {sa_file}"

        with open(sa_file) as f:
            doc = yaml.safe_load(f)

        assert doc["kind"] == "ServiceAccount"
        name = doc["metadata"]["name"]

        # Must be exactly "openfga-sa" (not "openfga")
        assert name == "openfga-sa", f"Expected 'openfga-sa', got '{name}'"

    def test_staging_keycloak_serviceaccount_has_sa_suffix(self):
        """
        Regression test for Run #19311976718.

        The overlay ServiceAccount for Keycloak must be named 'keycloak-sa',
        not 'keycloak'. After kustomization patches, it becomes 'preview-keycloak-sa'.
        """
        sa_file = STAGING_OVERLAY / "serviceaccount-keycloak.yaml"
        assert sa_file.exists(), f"ServiceAccount file not found: {sa_file}"

        with open(sa_file) as f:
            doc = yaml.safe_load(f)

        assert doc["kind"] == "ServiceAccount"
        name = doc["metadata"]["name"]

        # Must be exactly "keycloak-sa" (not "keycloak")
        assert name == "keycloak-sa", f"Expected 'keycloak-sa', got '{name}'"

    def test_all_overlay_serviceaccounts_match_base_or_allowed(self):
        """
        All overlay ServiceAccounts must either:
        1. Match a base ServiceAccount (after removing env prefix), OR
        2. Be in the overlay-only allowed list
        """
        # Load base ServiceAccount names
        with open(BASE_SA_PATH) as f:
            docs = list(yaml.safe_load_all(f))
        base_names = {doc["metadata"]["name"] for doc in docs if doc and doc.get("kind") == "ServiceAccount"}

        # Overlay-only ServiceAccounts that don't need to match base
        overlay_only_allowed = {
            "mcp-server-langgraph",  # Main application SA
            "external-secrets-operator",  # External Secrets Operator
            "otel-collector",  # OpenTelemetry Collector
        }

        # Check all overlay ServiceAccounts
        for overlay_dir in [STAGING_OVERLAY, PRODUCTION_OVERLAY]:
            if not overlay_dir.exists():
                continue

            for sa_file in overlay_dir.glob("serviceaccount*.yaml"):
                with open(sa_file) as f:
                    for doc in yaml.safe_load_all(f):
                        if not doc or doc.get("kind") != "ServiceAccount":
                            continue

                        sa_name = doc["metadata"]["name"]

                        # Remove environment prefix
                        clean_name = sa_name
                        for prefix in ["preview-", "production-", "dev-", "test-"]:
                            if clean_name.startswith(prefix):
                                clean_name = clean_name[len(prefix) :]
                                break

                        # Skip overlay-only ServiceAccounts
                        if clean_name in overlay_only_allowed:
                            continue

                        # Must match base naming
                        assert clean_name in base_names, (
                            f"ServiceAccount '{sa_name}' (clean: '{clean_name}') in {sa_file.name} doesn't match base. Available: {base_names}"
                        )


@pytest.mark.xdist_group(name="testworkloadidentityannotations")
class TestWorkloadIdentityAnnotations:
    """Test that critical ServiceAccounts have Workload Identity annotations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_staging_openfga_has_workload_identity(self):
        """OpenFGA ServiceAccount must have Workload Identity annotation."""
        sa_file = STAGING_OVERLAY / "serviceaccount-openfga.yaml"

        with open(sa_file) as f:
            doc = yaml.safe_load(f)

        annotations = doc["metadata"].get("annotations", {})
        assert "iam.gke.io/gcp-service-account" in annotations, "OpenFGA ServiceAccount missing Workload Identity annotation"

        # Verify it's not empty
        wi_annotation = annotations["iam.gke.io/gcp-service-account"]
        assert len(wi_annotation) > 0, "Workload Identity annotation is empty"
        assert "@" in wi_annotation, "Workload Identity annotation must be a GCP service account email"

    def test_staging_keycloak_has_workload_identity(self):
        """Keycloak ServiceAccount must have Workload Identity annotation."""
        sa_file = STAGING_OVERLAY / "serviceaccount-keycloak.yaml"

        with open(sa_file) as f:
            doc = yaml.safe_load(f)

        annotations = doc["metadata"].get("annotations", {})
        assert "iam.gke.io/gcp-service-account" in annotations, "Keycloak ServiceAccount missing Workload Identity annotation"

        # Verify it's not empty
        wi_annotation = annotations["iam.gke.io/gcp-service-account"]
        assert len(wi_annotation) > 0, "Workload Identity annotation is empty"
        assert "@" in wi_annotation, "Workload Identity annotation must be a GCP service account email"


@pytest.mark.xdist_group(name="testvalidationscript")
class TestValidationScript:
    """Test that the validation script works correctly."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_validation_script_passes_on_correct_naming(self):
        """Validation script should pass when all ServiceAccounts are correctly named."""
        result = subprocess.run(
            ["python", "scripts/validators/validate_serviceaccount_names.py"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            timeout=60,
        )

        # Should exit with code 0 (success)
        assert result.returncode == 0, f"Validation script failed:\n{result.stdout}\n{result.stderr}"

    def test_validation_script_is_executable(self):
        """Validation script should be executable."""
        script_path = REPO_ROOT / "scripts" / "validators" / "validate_serviceaccount_names.py"
        assert script_path.exists(), "Validation script not found"

        # Check if file is executable (Unix permissions)
        import os
        import stat

        file_stat = os.stat(script_path)
        is_executable = bool(file_stat.st_mode & stat.S_IXUSR)

        assert is_executable, "Validation script is not executable (missing +x permission)"


@pytest.mark.xdist_group(name="testregressionprevention")
class TestRegressionPrevention:
    """Tests that prevent specific regression scenarios."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_cannot_create_serviceaccount_without_sa_suffix_in_overlays(self):
        """
        Prevent regression: ServiceAccounts in overlays matching base components
        must use the -sa suffix.

        This test would catch if someone creates serviceaccount-openfga.yaml
        with name: openfga instead of name: openfga-sa
        """
        # Load base component names (without -sa suffix)
        with open(BASE_SA_PATH) as f:
            docs = list(yaml.safe_load_all(f))
        base_components = {
            doc["metadata"]["name"].replace("-sa", "") for doc in docs if doc and doc.get("kind") == "ServiceAccount"
        }

        # Check overlays
        for overlay_dir in [STAGING_OVERLAY, PRODUCTION_OVERLAY]:
            if not overlay_dir.exists():
                continue

            for sa_file in overlay_dir.glob("serviceaccount*.yaml"):
                with open(sa_file) as f:
                    for doc in yaml.safe_load_all(f):
                        if not doc or doc.get("kind") != "ServiceAccount":
                            continue

                        sa_name = doc["metadata"]["name"]

                        # If this ServiceAccount name (without suffix) matches a base component,
                        # it MUST have the -sa suffix
                        name_without_suffix = sa_name.replace("-sa", "")

                        if name_without_suffix in base_components and not sa_name.endswith("-sa"):
                            pytest.fail(
                                f"REGRESSION DETECTED: ServiceAccount '{sa_name}' in {sa_file.name} "
                                f"matches base component '{name_without_suffix}' but is missing -sa suffix. "
                                f"This caused Run #19311976718 failure. "
                                f"Change to: {sa_name}-sa"
                            )
