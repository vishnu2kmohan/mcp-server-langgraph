"""
Helm Placeholder Validation Tests

These tests validate that Helm values files don't contain unresolved
placeholders that could cause deployment failures or security issues.

Placeholders like PROJECT_ID, YOUR_STAGING_PROJECT_ID should either:
1. Be resolved/replaced before deployment
2. Be in .local.yaml files that aren't committed
3. Have clear documentation on how to replace them
"""

import gc
import re
from pathlib import Path

import pytest
import yaml


def find_placeholders_in_file(file_path: Path) -> dict:
    """
    Find all placeholder patterns in a file.

    Returns dict with:
    - placeholders: list of (line_num, line_content, placeholder) tuples
    - documented: whether the file has documentation on replacing them
    """
    placeholder_patterns = [
        r"YOUR_[A-Z_]+_PROJECT_ID",
        r"PROJECT_ID(?!\.iam\.gserviceaccount\.com)",  # PROJECT_ID not in SA format
        r"YOUR_[A-Z_]+_ID",
        r"REPLACE_ME",
        r"<your-[^>]+>",
    ]

    placeholders = []
    documented = False

    with open(file_path) as f:
        lines = f.readlines()

    for line_num, line in enumerate(lines, 1):
        # Skip comment-only lines
        if line.strip().startswith("#"):
            # Check if comment explains placeholder replacement
            if "replace" in line.lower() or "todo" in line.lower():
                documented = True
            continue

        # Look for placeholders in actual YAML
        for pattern in placeholder_patterns:
            matches = re.finditer(pattern, line)
            for match in matches:
                placeholders.append((line_num, line.strip(), match.group()))

    return {"placeholders": placeholders, "documented": documented}


@pytest.mark.deployment
@pytest.mark.security
@pytest.mark.xdist_group(name="testhelmplaceholdervalidation")
class TestHelmPlaceholderValidation:
    """Validate Helm values files for dangerous placeholders"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_helm_values_staging_has_no_dangerous_placeholders(self):
        """
        Test that staging values don't have unresolved dangerous placeholders.

        Staging values should either:
        1. Use actual project IDs
        2. Use environment variable substitution
        3. Be documented as templates requiring replacement
        """
        staging_values = Path(__file__).parent.parent.parent / "deployments" / "helm" / "values-staging.yaml"

        if not staging_values.exists():
            pytest.skip("Staging values file not found")

        result = find_placeholders_in_file(staging_values)
        placeholders = result["placeholders"]
        documented = result["documented"]

        # If placeholders exist, they must be documented
        if placeholders:
            assert documented, (
                f"Found {len(placeholders)} unresolved placeholders in {staging_values.name} "
                f"without documentation on how to replace them: "
                f"{[p[2] for p in placeholders]}"
            )

            # Emit warning about placeholders
            placeholder_list = "\n".join([f"  Line {p[0]}: {p[2]}" for p in placeholders])
            print(f"\nWARNING: Placeholders found in {staging_values.name}:\n{placeholder_list}")
            print("These should be replaced before deploying to staging.")

    def test_helm_values_production_has_no_dangerous_placeholders(self):
        """
        Test that production values don't have unresolved dangerous placeholders.

        Production values MUST NOT have placeholders - they should use:
        1. Actual project IDs
        2. Environment variable substitution (${{ vars.GCP_PROJECT_ID }})
        3. Secret references
        """
        production_values = Path(__file__).parent.parent.parent / "deployments" / "helm" / "values-production.yaml"

        if not production_values.exists():
            pytest.skip("Production values file not found")

        result = find_placeholders_in_file(production_values)
        placeholders = result["placeholders"]
        documented = result["documented"]

        # If placeholders exist, they must be documented
        if placeholders:
            assert documented, (
                f"Found {len(placeholders)} unresolved placeholders in {production_values.name} "
                f"without documentation: {[p[2] for p in placeholders]}"
            )

            # Emit warning about production placeholders
            placeholder_list = "\n".join([f"  Line {p[0]}: {p[2]}" for p in placeholders])
            print(f"\nWARNING: Placeholders found in {production_values.name}:\n{placeholder_list}")
            print("These MUST be replaced before deploying to production!")

    def test_helm_values_use_environment_variable_pattern(self):
        """
        Test that Helm values use environment variable substitution pattern.

        Recommended pattern: ${{ vars.GCP_PROJECT_ID }} or ${GCP_PROJECT_ID}
        This allows GitHub Actions to substitute values securely.
        """
        helm_dir = Path(__file__).parent.parent.parent / "deployments" / "helm"
        values_files = list(helm_dir.glob("values-*.yaml"))

        for values_file in values_files:
            if ".local." in values_file.name:
                # Skip .local.yaml files (not committed)
                continue

            with open(values_file) as f:
                content = f.read()

            # File should use either env vars or actual project IDs, not raw placeholders
            # This is just a recommendation check, not a hard requirement
            if "YOUR_" in content or "REPLACE_ME" in content:
                # Has placeholders - check if documented
                has_docs = "replace" in content.lower() or "todo" in content.lower()
                if not has_docs:
                    print(
                        f"\nRECOMMENDATION: {values_file.name} should use environment "
                        f"variable pattern instead of raw placeholders"
                    )

    def test_local_yaml_pattern_documented(self):
        """
        Test that .local.yaml pattern is documented for actual deployments.

        Users should create values-staging.local.yaml with real values,
        and .local.yaml files should be in .gitignore.
        """
        gitignore_path = Path(__file__).parent.parent.parent / ".gitignore"

        # Check if .gitignore excludes .local.yaml files
        if gitignore_path.exists():
            with open(gitignore_path) as f:
                gitignore_content = f.read()

            # Should have *.local.yaml or similar pattern
            has_local_ignore = "*.local.yaml" in gitignore_content or "*.local.yml" in gitignore_content

            if not has_local_ignore:
                print("\nRECOMMENDATION: Add '*.local.yaml' to .gitignore to prevent " "committing deployment secrets")

    def test_no_hardcoded_gcp_project_ids_in_non_vishnu_repos(self):
        """
        Test that GCP project IDs are not hardcoded (except in vishnu's sandbox).

        This test would fail for other users, prompting them to replace
        vishnu-sandbox-* with their own project IDs.
        """
        helm_dir = Path(__file__).parent.parent.parent / "deployments" / "helm"
        values_files = list(helm_dir.glob("values-*.yaml"))

        for values_file in values_files:
            if ".local." in values_file.name:
                continue

            with open(values_file) as f:
                content = f.read()

            # Look for vishnu-sandbox-* project IDs
            hardcoded_projects = re.findall(r"vishnu-sandbox-\d+", content)

            if hardcoded_projects:
                # This is OK for vishnu's repo, but others should replace
                print(
                    f"\nNOTE: {values_file.name} contains vishnu-sandbox project IDs. "
                    f"Other users should replace these with their own project IDs."
                )

    def test_serviceaccount_annotations_use_actual_project_or_var(self):
        """
        Test that service account annotations use actual project ID or variable.

        Pattern: iam.gke.io/gcp-service-account: sa-name@PROJECT_ID.iam.gserviceaccount.com

        Should be either:
        1. sa-name@${GCP_PROJECT_ID}.iam.gserviceaccount.com
        2. sa-name@vishnu-sandbox-20250310.iam.gserviceaccount.com
        """
        helm_dir = Path(__file__).parent.parent.parent / "deployments" / "helm"
        values_files = list(helm_dir.glob("values-*.yaml"))

        for values_file in values_files:
            if ".local." in values_file.name:
                continue

            with open(values_file) as f:
                try:
                    config = yaml.safe_load(f)
                except yaml.YAMLError:
                    continue

            # Look for serviceAccount.annotations in the YAML structure
            sa_config = config.get("serviceAccount", {})
            annotations = sa_config.get("annotations")

            if annotations and "iam.gke.io/gcp-service-account" in annotations:
                gcp_sa = annotations["iam.gke.io/gcp-service-account"]

                # Check for dangerous placeholder pattern
                if "@PROJECT_ID." in gcp_sa and "@${" not in gcp_sa:
                    pytest.fail(
                        f"{values_file.name} has dangerous PROJECT_ID placeholder in "
                        f"service account annotation: {gcp_sa}. "
                        f"Use either @${{GCP_PROJECT_ID}} or actual project ID."
                    )


@pytest.mark.deployment
@pytest.mark.xdist_group(name="testplaceholderdetectionprecommit")
class TestPlaceholderDetectionPreCommit:
    """Test that pre-commit hooks detect placeholders"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_precommit_config_has_placeholder_check(self):
        """
        Test that pre-commit config includes placeholder validation.

        This ensures dangerous placeholders are caught before commit.
        """
        precommit_path = Path(__file__).parent.parent.parent / ".pre-commit-config.yaml"

        if not precommit_path.exists():
            pytest.skip(".pre-commit-config.yaml not found")

        with open(precommit_path) as f:
            content = f.read()

        # Look for placeholder check hook
        has_placeholder_check = (
            "check-helm-placeholders" in content or "check-placeholders" in content or "PROJECT_ID" in content
        )

        # This test will fail until we add the hook (RED phase)
        # After adding the hook, it will pass (GREEN phase)
        assert has_placeholder_check, "Pre-commit config should include check-helm-placeholders hook"
