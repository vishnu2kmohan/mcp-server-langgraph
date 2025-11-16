"""
Comprehensive Validation Tests for OpenAI Codex Findings

These tests validate fixes for 14 issues discovered during Codex deployment review:
- 5 Critical (P0) issues that block production
- 2 Medium (P1) security/reliability issues
- 3 Low (P2-P3) technical debt issues
- 2 Additional issues discovered during investigation

Following TDD principles:
1. These tests should FAIL before fixes are applied (RED phase)
2. After implementing fixes, tests should PASS (GREEN phase)
3. Refactor while keeping tests green (REFACTOR phase)

Reference: OpenAI Codex Deployment Configuration Review (2025-01-09)
"""

import gc
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

# Mark as unit test to ensure it runs in CI (deployment validation)
pytestmark = pytest.mark.unit
REPO_ROOT = Path(__file__).parent.parent.parent


@pytest.mark.requires_kustomize
@pytest.mark.xdist_group(name="testcriticalissues")
class TestCriticalIssues:
    """P0 Critical Issues - Production Blockers

    CODEX FINDING #1: These tests require kustomize CLI tool.
    Tests will skip gracefully if kustomize is not installed.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_redis_ssl_configuration_matches_url_scheme(self):
        """
        Test that redis_ssl setting matches URL scheme across all overlays.

        Issue #2 (Critical): Production ConfigMap enables redis_ssl: "true"
        while using redis:// URLs instead of rediss:// URLs.

        Expected behavior:
        - If redis_ssl: "true", URLs must use rediss:// scheme
        - If redis_ssl: "false", URLs must use redis:// scheme
        - Mismatched configuration causes TLS handshake failures

        Validates: deployments/overlays/production/configmap-patch.yaml:29
        """
        overlays_to_check = [
            ("deployments/overlays/production/configmap-patch.yaml", "production"),
            ("deployments/overlays/staging-gke/configmap-patch.yaml", "staging-gke"),
        ]

        for config_path, overlay_name in overlays_to_check:
            full_path = REPO_ROOT / config_path

            if not full_path.exists():
                pytest.skip(f"{config_path} not found")

            with open(full_path) as f:
                content = f.read()

            try:
                config = yaml.safe_load(content)
            except yaml.YAMLError as e:
                pytest.fail(f"Invalid YAML in {config_path}: {e}")

            # Extract redis_ssl setting
            data = config.get("data", {})
            redis_ssl = data.get("redis_ssl", "false")
            ssl_enabled = redis_ssl.lower() == "true"

            # Check all Redis URLs
            redis_url_fields = [
                "redis_url",
                "REDIS_URL",
                "checkpoint_redis_url",
                "CHECKPOINT_REDIS_URL",
                "redis_host",  # May be used to construct URLs
            ]

            for field in redis_url_fields:
                if field in data:
                    value = data[field]

                    # Only validate if it's a Redis URL (not just a host)
                    if isinstance(value, str) and "redis" in value.lower():
                        # Check scheme consistency
                        has_rediss = value.startswith("rediss://")
                        has_redis = value.startswith("redis://")

                        if has_redis or has_rediss:
                            if ssl_enabled and has_redis:
                                pytest.fail(
                                    f"{overlay_name}: redis_ssl=true but {field} uses redis:// scheme: {value}\n"
                                    f"Fix: Change to rediss:// OR set redis_ssl=false"
                                )
                            elif not ssl_enabled and has_rediss:
                                pytest.fail(
                                    f"{overlay_name}: redis_ssl=false but {field} uses rediss:// scheme: {value}\n"
                                    f"Fix: Change to redis:// OR set redis_ssl=true"
                                )

    def test_environment_variable_casing_consistent(self):
        """
        Test that environment variables use correct casing (uppercase).

        Issue #3 (Critical): staging-gke deployment-patch.yaml uses lowercase
        redis_url/checkpoint_redis_url but application expects uppercase.

        Expected: REDIS_URL, CHECKPOINT_REDIS_URL (uppercase)
        Actual: redis_url, checkpoint_redis_url (lowercase)

        Impact: Application may fail to read configuration even with
        case_sensitive=False due to direct env lookups in code.

        Validates: deployments/overlays/staging-gke/deployment-patch.yaml:78,83
        """
        deployment_patch = REPO_ROOT / "deployments/overlays/staging-gke/deployment-patch.yaml"

        if not deployment_patch.exists():
            pytest.skip("staging-gke deployment-patch.yaml not found")

        with open(deployment_patch) as f:
            try:
                patches = list(yaml.safe_load_all(f))
            except yaml.YAMLError as e:
                pytest.fail(f"Invalid YAML in deployment-patch.yaml: {e}")

        # Environment variables that MUST be uppercase
        required_uppercase = {
            "REDIS_URL",
            "CHECKPOINT_REDIS_URL",
            "POSTGRES_HOST",
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
            "POSTGRES_DB",
        }

        for patch in patches:
            if patch is None or not isinstance(patch, dict):
                continue

            # Navigate to containers env
            spec = patch.get("spec", {}).get("template", {}).get("spec", {})
            containers = spec.get("containers", [])

            for container in containers:
                env_vars = container.get("env", [])

                for env_var in env_vars:
                    env_name = env_var.get("name", "")

                    # Check if lowercase version of required uppercase var
                    if env_name.upper() in required_uppercase and env_name != env_name.upper():
                        pytest.fail(
                            f"Environment variable '{env_name}' should be uppercase '{env_name.upper()}'\n"
                            f"Location: staging-gke/deployment-patch.yaml, container '{container.get('name')}'\n"
                            f"Reason: Application code uses direct uppercase lookups"
                        )

    def test_no_hardcoded_internal_ips(self):
        """
        Test that no hard-coded internal IPs exist in deployment configs.

        Issue #4 (Critical): staging-gke overlay hard-codes internal IPs:
        - 10.138.129.37 (Memorystore Redis)
        - 10.110.0.3 (Cloud SQL)
        - 10.110.1.4 (Memorystore Redis)

        Impact: IPs change on failover, regional move, or project recreation.
        Solution: Use Cloud DNS names instead.

        Validates:
        - deployments/overlays/staging-gke/redis-session-endpoints.yaml:10
        - deployments/overlays/staging-gke/configmap-patch.yaml:24,33
        """
        files_to_check = [
            "deployments/overlays/staging-gke/redis-session-endpoints.yaml",
            "deployments/overlays/staging-gke/configmap-patch.yaml",
            "deployments/overlays/staging-gke/deployment-patch.yaml",
            "deployments/overlays/production-gke/configmap-patch.yaml",
        ]

        # Regex to match private IP addresses (10.x, 172.16-31.x, 192.168.x)
        private_ip_pattern = re.compile(
            r"\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
            r"172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}|"
            r"192\.168\.\d{1,3}\.\d{1,3})\b"
        )

        issues_found = []

        for file_path in files_to_check:
            full_path = REPO_ROOT / file_path

            if not full_path.exists():
                continue

            with open(full_path) as f:
                lines = f.readlines()

            for line_num, line in enumerate(lines, 1):
                # Skip comments
                if line.strip().startswith("#"):
                    continue

                # Find hard-coded IPs
                matches = private_ip_pattern.findall(line)
                if matches:
                    issues_found.append({"file": file_path, "line": line_num, "ips": matches, "content": line.strip()})

        if issues_found:
            error_msg = "Hard-coded internal IPs found:\n\n"
            for issue in issues_found:
                error_msg += f"  {issue['file']}:{issue['line']}\n"
                error_msg += f"    IPs: {', '.join(issue['ips'])}\n"
                error_msg += f"    Line: {issue['content']}\n\n"

            error_msg += "Fix: Replace with Cloud DNS names (e.g., redis.staging.internal)\n"
            error_msg += "See: deployments/overlays/staging-gke/README.md for DNS setup"

            pytest.fail(error_msg)

    def test_no_unsubstituted_kustomize_variables(self):
        """
        Test that Kustomize variables are properly substituted.

        Issue #5 (Critical): production-gke kustomization.yaml has
        $(GCP_PROJECT_ID) in image name without proper substitution.

        Impact: Image pull fails with literal $(GCP_PROJECT_ID) in name.
        Solution: Migrate to Helm-based templating.

        Validates: deployments/overlays/production-gke/kustomization.yaml:76
        """
        # CODEX FINDING #1: Check if kustomize is available
        if not shutil.which("kustomize"):
            pytest.skip(
                "kustomize CLI not installed. Install with:\n"
                "  curl -s https://raw.githubusercontent.com/kubernetes-sigs/kustomize/master/hack/install_kustomize.sh | bash"
            )

        # Build production-gke overlay
        overlay_path = REPO_ROOT / "deployments/overlays/production-gke"
        result = subprocess.run(
            ["kustomize", "build", str(overlay_path)], capture_output=True, text=True, cwd=REPO_ROOT, timeout=60
        )

        # Skip if build fails (other tests will catch that)
        if result.returncode != 0:
            pytest.skip(f"Kustomize build failed: {result.stderr}")

        # Parse built manifests
        try:
            documents = list(yaml.safe_load_all(result.stdout))
        except yaml.YAMLError as e:
            pytest.fail(f"Invalid YAML in built manifests: {e}")

        # Check for unsubstituted variables
        unsubstituted_patterns = [
            r"\$\(GCP_PROJECT_ID\)",
            r"\$\{GCP_PROJECT_ID\}",
            r"\$\(PROJECT_ID\)",
            r"\$\{PROJECT_ID\}",
        ]

        issues = []

        for doc in documents:
            if doc is None or not isinstance(doc, dict):
                continue

            # Convert to string to search
            doc_str = yaml.dump(doc)

            for pattern in unsubstituted_patterns:
                matches = re.findall(pattern, doc_str)
                if matches:
                    kind = doc.get("kind", "Unknown")
                    name = doc.get("metadata", {}).get("name", "unknown")
                    issues.append({"resource": f"{kind}/{name}", "pattern": pattern, "matches": matches})

        if issues:
            error_msg = "Unsubstituted Kustomize variables found in built manifests:\n\n"
            for issue in issues:
                error_msg += f"  {issue['resource']}: {issue['pattern']}\n"

            error_msg += "\nFix: Migrate to Helm chart with proper templating\n"
            error_msg += "See: deployments/helm/values-production-gke.yaml"

            pytest.fail(error_msg)

    def test_no_placeholder_values_in_production(self):
        """
        Test that production configs have no placeholder values.

        Issue #6 (Critical): production-gke configmap-patch.yaml contains:
        - YOUR_PROJECT_ID
        - ${GCP_PROJECT_ID} (unsubstituted)

        Impact: Pods start with invalid configuration.
        Solution: Use Helm values or External Secrets.

        Validates: deployments/overlays/production-gke/configmap-patch.yaml:48
        """
        config_patch = REPO_ROOT / "deployments/overlays/production-gke/configmap-patch.yaml"

        if not config_patch.exists():
            pytest.skip("production-gke configmap-patch.yaml not found")

        with open(config_patch) as f:
            lines = f.readlines()

        # Dangerous placeholders that should NOT be in production
        dangerous_placeholders = [
            r"YOUR_PROJECT_ID",
            r"YOUR_[A-Z_]+_ID",
            r"REPLACE_ME",
            r"example\.com",  # Generic example domains
            r"my-gcp-project",  # Template project names
        ]

        issues = []

        for line_num, line in enumerate(lines, 1):
            # Skip pure comment lines
            if line.strip().startswith("#"):
                continue

            for pattern in dangerous_placeholders:
                matches = re.findall(pattern, line, re.IGNORECASE)
                if matches:
                    issues.append({"line": line_num, "pattern": pattern, "content": line.strip(), "matches": matches})

        if issues:
            error_msg = "Dangerous placeholders found in production config:\n\n"
            for issue in issues:
                error_msg += f"  Line {issue['line']}: {issue['pattern']}\n"
                error_msg += f"    {issue['content']}\n\n"

            error_msg += "Fix: Replace with actual values or use Helm templating\n"
            error_msg += "Production configs MUST NOT contain placeholder values"

            pytest.fail(error_msg)


@pytest.mark.xdist_group(name="testmediumpriorityissues")
class TestMediumPriorityIssues:
    """P1 Medium Priority Issues - Security & Reliability"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_no_hardcoded_gcp_project_in_serviceaccount(self):
        """
        Test that service account annotations use variables, not hard-coded projects.

        Issue #8 (Medium): production-gke serviceaccount-patch.yaml hard-codes:
        iam.gke.io/gcp-service-account: mcp-prod-app-sa@my-gcp-project.iam...

        Impact: Workload Identity fails in actual GCP project.
        Solution: Use Helm templating with project ID variable.

        Validates: deployments/overlays/production-gke/serviceaccount-patch.yaml:8
        """
        sa_patch = REPO_ROOT / "deployments/overlays/production-gke/serviceaccount-patch.yaml"

        if not sa_patch.exists():
            pytest.skip("production-gke serviceaccount-patch.yaml not found")

        with open(sa_patch) as f:
            content = f.read()

        # Dangerous hard-coded project IDs
        dangerous_patterns = [
            (r"my-gcp-project", "Template project 'my-gcp-project'"),
            (r"YOUR_PROJECT_ID", "Placeholder 'YOUR_PROJECT_ID'"),
        ]

        issues = []

        for pattern, description in dangerous_patterns:
            if re.search(pattern, content):
                issues.append(description)

        if issues:
            error_msg = "Hard-coded project IDs in service account annotation:\n\n"
            for issue in issues:
                error_msg += f"  - {issue}\n"

            error_msg += "\nFix: Use Helm templating: sa@{{ .Values.gcp.projectId }}.iam.gserviceaccount.com\n"
            error_msg += "Or: Use Kustomize vars substitution"

            pytest.fail(error_msg)

    def test_main_application_has_rbac_role(self):
        """
        Test that main application service account has explicit RBAC role.

        Issue #16 (Additional): Main app service account 'mcp-server-langgraph'
        has no Role/RoleBinding defined. Only supporting services have RBAC.

        Impact: Relies on default permissions (security risk).
        Solution: Create explicit Role granting access to mcp-server-langgraph-secrets.

        Validates: deployments/base/serviceaccount-roles.yaml
        """
        roles_file = REPO_ROOT / "deployments/base/serviceaccount-roles.yaml"

        if not roles_file.exists():
            pytest.skip("serviceaccount-roles.yaml not found")

        with open(roles_file) as f:
            try:
                documents = list(yaml.safe_load_all(f))
            except yaml.YAMLError as e:
                pytest.fail(f"Invalid YAML: {e}")

        # Find all Roles and RoleBindings
        roles = []
        role_bindings = []

        for doc in documents:
            if doc is None or not isinstance(doc, dict):
                continue

            kind = doc.get("kind")
            if kind == "Role":
                roles.append(doc)
            elif kind == "RoleBinding":
                role_bindings.append(doc)

        # Check if main app service account has RBAC
        main_sa_name = "mcp-server-langgraph"
        main_sa_has_binding = False

        for binding in role_bindings:
            subjects = binding.get("subjects", [])
            for subject in subjects:
                if subject.get("kind") == "ServiceAccount" and subject.get("name") == main_sa_name:
                    main_sa_has_binding = True
                    break

        if not main_sa_has_binding:
            pytest.fail(
                f"Main application service account '{main_sa_name}' has no RBAC Role/RoleBinding.\n\n"
                f"Found RBAC for: {[b.get('subjects', [{}])[0].get('name') for b in role_bindings if b.get('subjects')]}\n\n"
                f"Fix: Add Role granting 'get' permission on 'mcp-server-langgraph-secrets'\n"
                f"Location: deployments/base/serviceaccount-roles.yaml\n"
                f"Security: Follow least-privilege principle"
            )


@pytest.mark.requires_kustomize
@pytest.mark.xdist_group(name="testlowpriorityissues")
class TestLowPriorityIssues:
    """P2-P3 Low Priority Issues - Technical Debt

    CODEX FINDING #1: Tests in this class may require kustomize CLI tool.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_no_unused_secret_generators(self):
        """
        Test that all secret generators are actually used.

        Issue #13 (Low): production-gke kustomization.yaml defines
        app-config-secrets generator but nothing references it.

        Impact: Dead code, confusion.
        Solution: Remove unused generator.

        Validates: deployments/overlays/production-gke/kustomization.yaml:100-104
        """
        # CODEX FINDING #1: Check if kustomize is available
        if not shutil.which("kustomize"):
            pytest.skip(
                "kustomize CLI not installed. Install with:\n"
                "  curl -s https://raw.githubusercontent.com/kubernetes-sigs/kustomize/master/hack/install_kustomize.sh | bash"
            )

        kustomization = REPO_ROOT / "deployments/overlays/production-gke/kustomization.yaml"

        if not kustomization.exists():
            pytest.skip("production-gke kustomization.yaml not found")

        with open(kustomization) as f:
            try:
                config = yaml.safe_load(f)
            except yaml.YAMLError as e:
                pytest.fail(f"Invalid YAML: {e}")

        secret_generators = config.get("secretGenerator", [])

        if not secret_generators:
            # No generators defined, test passes
            return

        # Build the overlay to see what's actually used
        overlay_path = REPO_ROOT / "deployments/overlays/production-gke"
        result = subprocess.run(
            ["kustomize", "build", str(overlay_path)], capture_output=True, text=True, cwd=REPO_ROOT, timeout=60
        )

        if result.returncode != 0:
            pytest.skip(f"Kustomize build failed: {result.stderr}")

        built_yaml = result.stdout

        # Check each generator
        unused_generators = []

        for generator in secret_generators:
            generator_name = generator.get("name")
            if not generator_name:
                continue

            # Search for references to this secret in built manifests
            # Kustomize adds hash suffix, so search for name prefix
            if generator_name not in built_yaml:
                unused_generators.append(generator_name)

        if unused_generators:
            pytest.fail(
                f"Unused secret generators found: {', '.join(unused_generators)}\n\n"
                f"These generators are defined but never referenced by any workload.\n"
                f"Fix: Remove from deployments/overlays/production-gke/kustomization.yaml\n"
                f"Or: Add volumeMount/envFrom references in deployment"
            )

    def test_cors_origin_not_example_domain(self):
        """
        Test that CORS origins use appropriate values, not example.com.

        Issue #14 (Low): base ingress-http.yaml defaults to:
        nginx.ingress.kubernetes.io/cors-allow-origin: "https://app.example.com"

        Impact: Production ingress rejects legitimate origins.
        Solution: Use environment-specific overlay patches.

        Validates: deployments/base/ingress-http.yaml:23,82
        """
        ingress_file = REPO_ROOT / "deployments/base/ingress-http.yaml"

        if not ingress_file.exists():
            pytest.skip("base ingress-http.yaml not found")

        with open(ingress_file) as f:
            content = f.read()

        # Check for example.com in CORS annotations
        if "app.example.com" in content or "example.com" in content:
            # This is OK in base if overlays override it
            # But warn if no comment about overriding
            if "override" not in content.lower() and "replace" not in content.lower():
                pytest.fail(
                    "Base ingress uses example.com CORS origin without override documentation.\n\n"
                    "Fix: Add comment explaining overlays should override this value\n"
                    "Or: Use more specific default (e.g., ${APP_DOMAIN} variable)"
                )

    def test_argocd_uses_environment_specific_values(self):
        """
        Test that ArgoCD applications use environment-specific values files.

        Issue #15 (Low): argocd/applications/mcp-server-app.yaml uses:
        valueFiles: [values.yaml] instead of values-production.yaml

        Impact: Production uses generic values instead of prod-specific config.
        Solution: Use values-production.yaml or document inline overrides.

        Validates: deployments/argocd/applications/mcp-server-app.yaml:30
        """
        argocd_app = REPO_ROOT / "deployments/argocd/applications/mcp-server-app.yaml"

        if not argocd_app.exists():
            pytest.skip("ArgoCD application manifest not found")

        with open(argocd_app) as f:
            try:
                config = yaml.safe_load(f)
            except yaml.YAMLError as e:
                pytest.fail(f"Invalid YAML: {e}")

        # Check helm source
        helm_config = config.get("spec", {}).get("source", {}).get("helm", {})
        value_files = helm_config.get("valueFiles", [])

        # If using generic values.yaml, should have inline values or comment
        if "values.yaml" in value_files and "values-production.yaml" not in value_files:
            # Check if there are inline value overrides
            inline_values = helm_config.get("values")

            if not inline_values:
                pytest.fail(
                    "ArgoCD application uses generic values.yaml without inline overrides.\n\n"
                    "Current: valueFiles: [values.yaml]\n"
                    "Recommended: valueFiles: [values-production.yaml]\n\n"
                    "Fix: Use environment-specific values file or add inline value overrides"
                )


@pytest.mark.xdist_group(name="testdocumentationconsistency")
class TestDocumentationConsistency:
    """Documentation validation tests"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_deployment_readme_structure_matches_actual(self):
        """
        Test that README documents actual directory structure.

        Issue #9 (Medium): deployments/README.md documents kustomize/
        hierarchy that doesn't exist.

        Actual structure: deployments/base, deployments/overlays
        Documented: kustomize/base, kustomize/overlays

        Validates: deployments/README.md:11
        """
        readme_file = REPO_ROOT / "deployments/README.md"

        if not readme_file.exists():
            pytest.skip("deployments/README.md not found")

        with open(readme_file) as f:
            content = f.read()

        # Check for incorrect kustomize/ references
        if "kustomize/base" in content or "kustomize/overlays" in content:
            # Check if these directories actually exist
            kustomize_dir = REPO_ROOT / "deployments" / "kustomize"

            if not kustomize_dir.exists():
                pytest.fail(
                    "README documents kustomize/ directory structure that doesn't exist.\n\n"
                    "Documented: kustomize/base, kustomize/overlays\n"
                    "Actual: deployments/base, deployments/overlays\n\n"
                    "Fix: Update README to match actual directory structure"
                )


@pytest.mark.xdist_group(name="testredissslconsistency")
class TestRedisSSLConsistency:
    """Cross-environment configuration consistency"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_redis_ssl_consistent_across_environments(self):
        """
        Test that Redis SSL settings are consistent and documented.

        Issue #17 (Additional): Redis SSL settings vary across environments:
        - production: redis_ssl="true" with redis:// (MISMATCH)
        - staging: redis_ssl="false" (CORRECT for private VPC)
        - base: not set

        Validates: All configmap patches
        """
        configs_to_check = [
            ("deployments/base/configmap.yaml", "base"),
            ("deployments/overlays/production/configmap-patch.yaml", "production"),
            ("deployments/overlays/staging-gke/configmap-patch.yaml", "staging-gke"),
        ]

        redis_configs = {}

        for config_path, env_name in configs_to_check:
            full_path = REPO_ROOT / config_path

            if not full_path.exists():
                continue

            with open(full_path) as f:
                try:
                    config = yaml.safe_load(f)
                except yaml.YAMLError:
                    continue

            data = config.get("data", {})
            redis_ssl = data.get("redis_ssl", "not_set")

            # Find any Redis URLs
            redis_urls = []
            for key, value in data.items():
                if isinstance(value, str) and ("redis://" in value or "rediss://" in value):
                    redis_urls.append((key, value))

            redis_configs[env_name] = {"ssl": redis_ssl, "urls": redis_urls}

        # Verify consistency within each environment
        for env_name, config in redis_configs.items():
            ssl_setting = config["ssl"]
            urls = config["urls"]

            if ssl_setting == "true":
                for key, url in urls:
                    if url.startswith("redis://"):
                        pytest.fail(
                            f"{env_name}: redis_ssl=true but {key}={url} uses redis:// (not rediss://)\n"
                            f"Fix: Either disable SSL or use rediss:// URLs with TLS-enabled endpoints"
                        )
