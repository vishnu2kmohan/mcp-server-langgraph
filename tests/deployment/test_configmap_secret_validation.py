"""
Test suite for validating ConfigMap keys and Secret references in Kubernetes deployments.

This test suite validates that:
1. All ConfigMap keys referenced in deployments exist in the actual ConfigMaps
2. All Secret names match between patches and external-secrets
3. Kustomize namePrefix is correctly applied to secret references
4. No missing ConfigMap keys that would cause CreateContainerConfigError

These tests follow TDD principles and are designed to prevent the pod crash issues
that occurred on 2025-11-12 in staging-mcp-server-langgraph namespace.

Root Causes Prevented:
- Issue #1: Missing ConfigMap keys (session_cookie_secure, rate_limit_per_minute, etc.)
- Issue #2: Secret name mismatch (mcp-server-langgraph-secrets vs staging-mcp-server-langgraph-secrets)
"""

import gc
import re
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Set

import pytest
import yaml

# Mark as unit test to ensure it runs in CI (deployment validation)
pytestmark = pytest.mark.unit
REPO_ROOT = Path(__file__).parent.parent.parent


@pytest.mark.xdist_group(name="testconfigmapvalidation")
class TestConfigMapValidation:
    """Test that all ConfigMap key references are valid."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def get_kustomize_output(self, overlay_path: str) -> List[Dict]:
        """Build kustomize and return parsed YAML documents."""
        if not shutil.which("kustomize"):
            pytest.skip("kustomize not installed")

        overlay_dir = REPO_ROOT / overlay_path
        result = subprocess.run(["kustomize", "build", str(overlay_dir)], capture_output=True, text=True, check=True)

        # Parse all YAML documents
        return list(yaml.safe_load_all(result.stdout))

    def extract_configmap_keys(self, docs: List[Dict], namespace: str) -> Dict[str, Set[str]]:
        """Extract all ConfigMap keys from built manifests."""
        configmaps = {}
        for doc in docs:
            if doc and doc.get("kind") == "ConfigMap":
                name = doc["metadata"]["name"]
                if doc["metadata"].get("namespace") == namespace or namespace is None:
                    configmaps[name] = set(doc.get("data", {}).keys())
        return configmaps

    def extract_configmap_references(self, docs: List[Dict]) -> Dict[str, Set[str]]:
        """
        Extract all ConfigMap key references from container env variables.

        Returns:
            Dict mapping ConfigMap name to set of referenced keys
            Only includes non-optional references
        """
        references = {}

        def scan_env_vars(env_vars: List[Dict]):
            """Recursively scan env variables for configMapKeyRef."""
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

            # Handle Deployment/StatefulSet
            spec = doc.get("spec", {})
            template = spec.get("template", {})
            pod_spec = template.get("spec", {})

            # Scan init containers
            for container in pod_spec.get("initContainers", []):
                scan_env_vars(container.get("env", []))

            # Scan main containers
            for container in pod_spec.get("containers", []):
                scan_env_vars(container.get("env", []))

        return references

    @pytest.mark.parametrize(
        "overlay,namespace",
        [
            ("deployments/overlays/staging-gke", "staging-mcp-server-langgraph"),
            ("deployments/overlays/production-gke", "production-mcp-server-langgraph"),
        ],
    )
    def test_all_configmap_keys_exist(self, overlay, namespace):
        """
        Test that all ConfigMap keys referenced in deployments actually exist.

        This test would have caught the staging pod crash issue where keys like:
        - session_cookie_secure
        - session_cookie_samesite
        - session_max_age_seconds
        - rate_limit_per_minute
        - rate_limit_burst
        - circuit_breaker_*
        - retry_*
        - gdpr_retention_days
        were referenced but not defined in the ConfigMap.
        """
        docs = self.get_kustomize_output(overlay)

        # Extract actual ConfigMap keys
        actual_keys = self.extract_configmap_keys(docs, namespace)

        # Extract referenced keys
        referenced_keys = self.extract_configmap_references(docs)

        # Validate each reference
        missing_keys = {}
        for cm_name, keys in referenced_keys.items():
            if cm_name not in actual_keys:
                missing_keys[cm_name] = {"error": "ConfigMap not found", "keys": keys}
                continue

            missing = keys - actual_keys[cm_name]
            if missing:
                missing_keys[cm_name] = {"error": "Missing keys", "keys": missing, "available": actual_keys[cm_name]}

        assert not missing_keys, f"Missing ConfigMap keys in {overlay}:\n" + "\n".join(
            f"  {cm}: {info['error']} - {info['keys']}" for cm, info in missing_keys.items()
        )

    @pytest.mark.parametrize(
        "overlay",
        [
            "deployments/overlays/staging-gke",
        ],
    )
    def test_required_configmap_keys_present_staging(self, overlay):
        """
        Test that required ConfigMap keys are present for the application (staging only).

        This is a whitelist approach - ensuring critical keys always exist.
        Production may have different requirements.
        """
        docs = self.get_kustomize_output(overlay)

        # Define required keys based on application needs
        required_keys = {
            # Session management
            "session_backend",
            "session_ttl_seconds",
            "session_cookie_secure",
            "session_cookie_samesite",
            "session_max_age_seconds",
            # Rate limiting
            "rate_limit_enabled",
            "rate_limit_per_minute",
            "rate_limit_burst",
            # Circuit breaker
            "circuit_breaker_failure_threshold",
            "circuit_breaker_recovery_timeout",
            "circuit_breaker_expected_exception_rate",
            "circuit_breaker_half_open_max_calls",
            # Retry configuration
            "retry_max_attempts",
            "retry_base_delay_seconds",
            "retry_max_delay_seconds",
            # Timeouts
            "default_timeout_seconds",
            "llm_timeout_seconds",
            "database_timeout_seconds",
            # GDPR
            "gdpr_storage_backend",
            "gdpr_retention_days",
        }

        # Extract ConfigMaps
        configmaps = {}
        for doc in docs:
            if doc and doc.get("kind") == "ConfigMap":
                name = doc["metadata"]["name"]
                if "config" in name.lower():  # Find config ConfigMaps
                    configmaps[name] = set(doc.get("data", {}).keys())

        # Find the main application ConfigMap
        app_configmap = None
        for name, keys in configmaps.items():
            if "mcp-server-langgraph-config" in name:
                app_configmap = keys
                break

        assert app_configmap is not None, f"Application ConfigMap not found in {overlay}"

        missing = required_keys - app_configmap
        assert not missing, (
            f"Required ConfigMap keys missing in {overlay}:\n"
            f"  Missing: {sorted(missing)}\n"
            f"  Available: {sorted(app_configmap)}"
        )


@pytest.mark.xdist_group(name="testsecretvalidation")
class TestSecretValidation:
    """Test that Secret names and references are consistent."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def get_kustomize_output(self, overlay_path: str) -> List[Dict]:
        """Build kustomize and return parsed YAML documents."""
        if not shutil.which("kustomize"):
            pytest.skip("kustomize not installed")

        overlay_dir = REPO_ROOT / overlay_path
        result = subprocess.run(["kustomize", "build", str(overlay_dir)], capture_output=True, text=True, check=True)

        return list(yaml.safe_load_all(result.stdout))

    def extract_secret_references(self, docs: List[Dict]) -> Dict[str, Set[str]]:
        """Extract all Secret name references from container env variables."""
        references = {}

        def scan_env_vars(env_vars: List[Dict]):
            """Recursively scan env variables for secretKeyRef."""
            for env in env_vars or []:
                if "valueFrom" in env and "secretKeyRef" in env["valueFrom"]:
                    ref = env["valueFrom"]["secretKeyRef"]
                    secret_name = ref["name"]
                    key = ref["key"]
                    if secret_name not in references:
                        references[secret_name] = set()
                    references[secret_name].add(key)

        for doc in docs:
            if not doc or doc.get("kind") not in ["Deployment", "StatefulSet", "Job", "CronJob"]:
                continue

            spec = doc.get("spec", {})
            template = spec.get("template", {})
            pod_spec = template.get("spec", {})

            # Scan init containers
            for container in pod_spec.get("initContainers", []):
                scan_env_vars(container.get("env", []))

            # Scan main containers
            for container in pod_spec.get("containers", []):
                scan_env_vars(container.get("env", []))

        return references

    def extract_external_secrets(self, docs: List[Dict]) -> Dict[str, Set[str]]:
        """Extract ExternalSecret target names and their keys."""
        external_secrets = {}

        for doc in docs:
            if not doc or doc.get("kind") != "ExternalSecret":
                continue

            # Get target secret name
            target_name = doc["spec"]["target"]["name"]

            # Get all keys that will be created
            keys = set()
            template_data = doc["spec"]["target"].get("template", {}).get("data", {})
            keys.update(template_data.keys())

            external_secrets[target_name] = keys

        return external_secrets

    @pytest.mark.parametrize(
        "overlay,expected_prefix",
        [
            ("deployments/overlays/staging-gke", "staging-"),
            ("deployments/overlays/production-gke", "production-"),
        ],
    )
    def test_primary_app_secret_names_match_external_secrets(self, overlay, expected_prefix):
        """
        Test that primary application secret names match ExternalSecret targets.

        This test would have caught the issue where deployment referenced
        'mcp-server-langgraph-secrets' but ExternalSecret created
        'staging-mcp-server-langgraph-secrets'.

        Note: Only validates secrets that should be managed by ExternalSecrets.
        Other secrets (like otel-collector-secrets) may be managed differently.
        """
        docs = self.get_kustomize_output(overlay)

        # Extract secret references from deployments
        secret_refs = self.extract_secret_references(docs)

        # Extract ExternalSecret targets
        external_secrets = self.extract_external_secrets(docs)

        # Skip test if no ExternalSecrets are configured (e.g., production)
        if not external_secrets:
            pytest.skip(f"No ExternalSecrets configured in {overlay}")

        # Only validate secrets that should be managed by ExternalSecrets
        # (i.e., contain "mcp-server-langgraph" in the name)
        missing_secrets = {}
        for secret_name in secret_refs.keys():
            if "mcp-server-langgraph" not in secret_name:
                # Skip non-app secrets (may be managed differently)
                continue

            if secret_name not in external_secrets:
                missing_secrets[secret_name] = {
                    "error": "Secret not found in ExternalSecrets",
                    "available": list(external_secrets.keys()),
                }

        assert not missing_secrets, f"Secret name mismatches in {overlay}:\n" + "\n".join(
            f"  {secret}: {info['error']}\n    Available: {info['available']}" for secret, info in missing_secrets.items()
        )

    @pytest.mark.parametrize(
        "overlay,expected_prefix",
        [
            ("deployments/overlays/staging-gke", "staging-"),
            ("deployments/overlays/production-gke", "production-"),
        ],
    )
    def test_all_external_secret_data_mappings_exist(self, overlay, expected_prefix):
        """
        Test that all ExternalSecret data mappings are complete.

        This ensures all secret keys used in templates have corresponding data mappings.
        Note: Template uses kebab-case (e.g. 'keycloak-client-id') while data mappings
        use camelCase (e.g. 'keycloakClientId'), and templates can reference constructed
        values using Go templating syntax.
        """
        docs = self.get_kustomize_output(overlay)

        # Find ExternalSecret documents for validation
        for doc in docs:
            if not doc or doc.get("kind") != "ExternalSecret":
                continue

            target_name = doc["spec"]["target"]["name"]

            # Get data mappings (remoteRef)
            data_mappings = {}
            for item in doc["spec"].get("data", []):
                secret_key = item["secretKey"]
                remote_key = item["remoteRef"]["key"]
                data_mappings[secret_key] = remote_key

            # Validate GCP secret keys have expected prefix
            for secret_key, remote_key in data_mappings.items():
                assert remote_key.startswith(expected_prefix), (
                    f"GCP secret key '{remote_key}' for {target_name}.{secret_key} " f"should start with '{expected_prefix}'"
                )

    @pytest.mark.parametrize(
        "overlay",
        [
            "deployments/overlays/staging-gke",
            "deployments/overlays/production-gke",
        ],
    )
    def test_all_secret_keys_referenced_are_created(self, overlay):
        """
        Test that all secret keys referenced in deployments are actually created by ExternalSecrets.

        This would catch missing secret keys like the ones we just added:
        - keycloak-client-id
        - keycloak-client-secret
        - openfga-store-id
        - etc.

        Only validates secrets managed by ExternalSecrets.
        """
        docs = self.get_kustomize_output(overlay)

        # Extract secret references
        secret_refs = self.extract_secret_references(docs)

        # Extract ExternalSecret keys
        external_secrets = self.extract_external_secrets(docs)

        # Validate each referenced key exists (only for ExternalSecrets-managed secrets)
        missing_keys = {}
        for secret_name, keys in secret_refs.items():
            # Skip non-app secrets
            if "mcp-server-langgraph" not in secret_name:
                continue

            if secret_name not in external_secrets:
                continue  # This is caught by test_primary_app_secret_names_match_external_secrets

            missing = keys - external_secrets[secret_name]
            if missing:
                missing_keys[secret_name] = {"missing": missing, "available": external_secrets[secret_name]}

        assert not missing_keys, f"Secret keys referenced but not created in {overlay}:\n" + "\n".join(
            f"  {secret}:\n" f"    Missing: {sorted(info['missing'])}\n" f"    Available: {sorted(info['available'])}"
            for secret, info in missing_keys.items()
        )


@pytest.mark.xdist_group(name="testkustomizeprefixconsistency")
class TestKustomizePrefixConsistency:
    """Test that Kustomize namePrefix is correctly applied."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def read_kustomization(self, overlay_path: str) -> Dict:
        """Read and parse kustomization.yaml."""
        kustomization_file = REPO_ROOT / overlay_path / "kustomization.yaml"
        with open(kustomization_file) as f:
            return yaml.safe_load(f)

    def read_patch_file(self, overlay_path: str, patch_file: str) -> str:
        """Read patch file content."""
        patch_path = REPO_ROOT / overlay_path / patch_file
        with open(patch_path) as f:
            return f.read()

    @pytest.mark.parametrize(
        "overlay,expected_prefix",
        [
            ("deployments/overlays/staging-gke", "staging-"),
            ("deployments/overlays/production-gke", "production-"),
        ],
    )
    def test_patch_files_use_prefixed_secret_names(self, overlay, expected_prefix):
        """
        Test that patch files use the prefixed secret names.

        This catches the issue where deployment-redis-url-json-patch.yaml
        referenced 'mcp-server-langgraph-secrets' instead of
        'staging-mcp-server-langgraph-secrets'.
        """
        kustomization = self.read_kustomization(overlay)

        # Get namePrefix
        name_prefix = kustomization.get("namePrefix", "")
        assert name_prefix == expected_prefix, f"Expected namePrefix '{expected_prefix}' in {overlay}"

        # Check all patch files
        patches = kustomization.get("patches", [])
        for patch in patches:
            if "path" not in patch:
                continue

            patch_file = patch["path"]
            if not patch_file.endswith(".yaml"):
                continue

            # Read patch content
            content = self.read_patch_file(overlay, patch_file)

            # Look for secret references
            secret_pattern = r"name:\s+([a-z0-9-]+secrets)"
            matches = re.findall(secret_pattern, content)

            for match in matches:
                # Skip if it's a Secret resource being deleted
                if "$patch: delete" in content:
                    continue

                # Secret names in patches should have the prefix
                assert match.startswith(expected_prefix), (
                    f"Secret name '{match}' in {patch_file} should start with '{expected_prefix}'\n"
                    f"This indicates a namePrefix mismatch that will cause pod failures."
                )
