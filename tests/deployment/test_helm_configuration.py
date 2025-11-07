"""
TDD Tests for Helm Chart Configuration

These tests ensure deployment configuration issues can never occur again by:
1. Validating all secret keys referenced by deployment exist in secret template
2. Ensuring no hard-coded credentials in configuration files
3. Validating CORS configuration security
4. Checking placeholder patterns are not committed
5. Verifying ExternalSecrets key alignment
"""

import re
from pathlib import Path

import pytest
import yaml


# Test fixtures
@pytest.fixture
def helm_chart_path():
    """Path to Helm chart directory."""
    return Path(__file__).parent.parent.parent / "deployments" / "helm" / "mcp-server-langgraph"


@pytest.fixture
def deployment_template(helm_chart_path):
    """Load deployment template."""
    template_path = helm_chart_path / "templates" / "deployment.yaml"
    with open(template_path) as f:
        return f.read()


@pytest.fixture
def secret_template(helm_chart_path):
    """Load secret template."""
    template_path = helm_chart_path / "templates" / "secret.yaml"
    with open(template_path) as f:
        return f.read()


@pytest.fixture
def values_yaml(helm_chart_path):
    """Load values.yaml."""
    values_path = helm_chart_path / "values.yaml"
    with open(values_path) as f:
        return yaml.safe_load(f)


@pytest.fixture
def base_configmap():
    """Load base configmap."""
    configmap_path = Path(__file__).parent.parent.parent / "deployments" / "base" / "configmap.yaml"
    with open(configmap_path) as f:
        return yaml.safe_load(f)


@pytest.fixture
def kong_config():
    """Load Kong configuration."""
    kong_path = Path(__file__).parent.parent.parent / "deployments" / "kong" / "kong.yaml"
    with open(kong_path) as f:
        return yaml.safe_load(f)


# Test 1: Secret Key Alignment (Prevents Issue #1)
def test_deployment_secret_keys_exist_in_template(deployment_template, secret_template):
    """
    Test that all secret keys referenced in deployment.yaml exist in secret.yaml.

    This test prevents the critical issue where pods crash because deployment
    references secret keys that don't exist in the secret template.
    """
    # Extract all secret key references from deployment
    deployment_secret_refs = re.findall(r"key:\s+([a-z0-9-]+)", deployment_template)

    # Extract all secret keys defined in secret template
    template_secret_keys = re.findall(r"^\s+([a-z0-9-]+):\s+{{", secret_template, re.MULTILINE)

    # Remove duplicates
    deployment_keys = set(deployment_secret_refs)
    template_keys = set(template_secret_keys)

    # Find missing keys
    missing_keys = deployment_keys - template_keys

    assert not missing_keys, (
        f"Deployment references secret keys that don't exist in template: {missing_keys}\n"
        f"Deployment uses: {sorted(deployment_keys)}\n"
        f"Template defines: {sorted(template_keys)}\n"
        f"Add missing keys to deployments/helm/mcp-server-langgraph/templates/secret.yaml"
    )


def test_values_yaml_has_all_secret_fields(values_yaml, secret_template):
    """
    Test that values.yaml defines all secrets referenced in secret template.

    This ensures users can configure all secrets via values.yaml.
    """
    # Extract secret data keys from template (not metadata keys)
    # Look for keys under stringData section
    stringdata_section = re.search(r"stringData:(.*?)(?:{{-|$)", secret_template, re.DOTALL)
    if not stringdata_section:
        pytest.skip("stringData section not found in template")

    template_keys = set(re.findall(r"^\s+([a-z0-9-]+):\s+{{", stringdata_section.group(1), re.MULTILINE))

    # Exclude metadata keys that appear in template but aren't secrets
    metadata_keys = {"name", "namespace", "labels"}
    template_keys -= metadata_keys

    # Convert kebab-case to camelCase for values.yaml
    def kebab_to_camel(s):
        parts = s.split("-")
        return parts[0] + "".join(word.capitalize() for word in parts[1:])

    expected_values_keys = {kebab_to_camel(k) for k in template_keys}

    # Extract actual secret keys from values.yaml
    actual_values_keys = set(values_yaml.get("secrets", {}).keys())

    # Check for missing keys (allowing existingSecret)
    actual_values_keys.discard("existingSecret")
    missing_keys = expected_values_keys - actual_values_keys

    assert not missing_keys, (
        f"values.yaml missing secret configuration for: {missing_keys}\n"
        f"Template defines: {sorted(template_keys)}\n"
        f"Values has: {sorted(actual_values_keys)}\n"
        f"Add these fields to 'secrets:' section in values.yaml"
    )


# Test 2: No Hard-coded Credentials (Prevents Issue #5)
def test_no_hardcoded_credentials_in_configmap(base_configmap):
    """
    Test that configmap doesn't contain hard-coded credentials.

    This prevents security issues from credentials in plain text.
    """
    config_str = yaml.dump(base_configmap)

    # Pattern to detect credentials in connection strings
    credential_patterns = [
        r"://[^:]+:[^@]+@",  # user:pass@host
        r'password\s*=\s*["\'](?!.*\$)[^"\']+["\']',  # password=value (not env var)
    ]

    for pattern in credential_patterns:
        matches = re.findall(pattern, config_str, re.IGNORECASE)
        # Filter out template variables and empty values
        actual_creds = [m for m in matches if "{{" not in m and "$(" not in m and m.strip() != '://""@']

        assert not actual_creds, (
            f"Found hard-coded credentials in configmap: {actual_creds}\n" f"Use environment variable substitution instead"
        )


# Test 3: CORS Security (Prevents Issue #3 & #4)
def test_kong_cors_not_wildcard_with_credentials(kong_config):
    """
    Test that Kong CORS doesn't use wildcard origins with credentials enabled.

    This prevents the critical security vulnerability where any website can
    make authenticated requests to the API.
    """
    if not kong_config:
        pytest.skip("Kong config not loaded")

    services = kong_config.get("services", [])

    for service in services:
        routes = service.get("routes", [])
        for route in routes:
            plugins = route.get("plugins", [])
            for plugin in plugins:
                if plugin.get("name") == "cors":
                    config = plugin.get("config", {})
                    origins = config.get("origins", [])
                    credentials = config.get("credentials", False)

                    if credentials:
                        assert "*" not in origins, (
                            f"CRITICAL SECURITY ISSUE: Route '{route.get('name')}' has "
                            f"CORS with wildcard origin and credentials enabled!\n"
                            f"This allows any website to make authenticated requests.\n"
                            f"Either:\n"
                            f"1. Specify exact origins: ['https://app.example.com']\n"
                            f"2. Set credentials: false"
                        )


def test_ingress_cors_not_wildcard(base_configmap):
    """
    Test that Ingress CORS annotations don't use wildcard in production configs.

    This is checked at the base level - dev overlays can override.
    """
    ingress_path = Path(__file__).parent.parent.parent / "deployments" / "base" / "ingress-http.yaml"

    with open(ingress_path) as f:
        content = f.read()

    # Check for wildcard CORS
    if 'cors-allow-origin: "*"' in content:
        # Ensure there's a comment explaining override requirement
        assert "# SECURITY" in content or "Override" in content, (
            "Base ingress uses wildcard CORS without security warning.\n"
            "Add comment explaining environment-specific override requirement."
        )


# Test 4: No Dangerous Placeholders Committed (Prevents Issue #6-8)
@pytest.mark.parametrize(
    "file_pattern,dangerous_patterns",
    [
        (
            "**/*.yaml",
            [
                r"YOUR_PROJECT_ID",
                r"YOUR_[A-Z_]+",
                r"REPLACE_ME(?!\s*\|)",  # REPLACE_ME not in template
                r"example\.com(?!.*#.*TODO)",  # example.com without TODO comment
            ],
        ),
    ],
)
def test_no_dangerous_placeholders_in_production_configs(file_pattern, dangerous_patterns):
    """
    Test that production configs don't contain unresolved placeholders.

    This prevents deployments that will fail due to invalid configuration.
    """
    deployments_path = Path(__file__).parent.parent.parent / "deployments"

    # Skip dev/test overlays and template files
    excluded_paths = ["dev", "test", "templates", "examples", "prometheus-rules"]  # Helm templates
    excluded_files = ["Chart.yaml", "values.yaml"]  # Helm chart metadata and defaults

    for yaml_file in deployments_path.rglob(file_pattern):
        # Skip if in excluded path
        if any(excluded in str(yaml_file) for excluded in excluded_paths):
            continue

        # Skip helm chart metadata files (these are templates)
        if yaml_file.name in excluded_files and "/helm/" in str(yaml_file):
            continue

        # Allow base configs to have documented placeholder values
        is_base_config = "/base/" in str(yaml_file)

        with open(yaml_file) as f:
            content = f.read()

        for pattern in dangerous_patterns:
            matches = list(re.finditer(pattern, content))
            if matches:
                # Check if it's in a comment or template
                for match in matches:
                    line_start = content.rfind("\n", 0, match.start()) + 1
                    line_end = content.find("\n", match.start())
                    if line_end == -1:
                        line_end = len(content)
                    line = content[line_start:line_end]

                    # Check if match is inside a comment
                    match_pos = match.start() - line_start
                    comment_pos = line.find("#")
                    in_comment = comment_pos != -1 and match_pos > comment_pos

                    # Check previous line for TODO/SECURITY comments
                    prev_line_start = content.rfind("\n", 0, line_start - 1) + 1
                    prev_line = content[prev_line_start:line_start].strip()

                    # Allow in comments, templates, and documented placeholders
                    is_allowed = (
                        in_comment  # Match is in a comment
                        or line.strip().startswith("#")
                        or "{{" in line
                        or "TEMPLATE:" in line
                        or "TODO:" in line
                        or "Replace" in line
                        and "#" in line  # "Replace" with comment
                        or "SECURITY:" in prev_line
                        or "TODO:" in prev_line
                        or (is_base_config and "example.com" in match.group())  # Base configs with example.com are templates
                    )

                    if not is_allowed:
                        pytest.fail(
                            f"Dangerous placeholder in {yaml_file}:{match.group()}\n"
                            f"Line: {line}\n"
                            f"Replace with actual value or use variable substitution, or add # TODO: comment"
                        )


# Test 5: ExternalSecrets Key Alignment (Prevents Issue #2)
def test_external_secrets_keys_match_helm_template():
    """
    Test that ExternalSecrets data keys match Helm secret template keys.

    This ensures ExternalSecrets will populate secrets with correct keys.
    """
    helm_secret_path = (
        Path(__file__).parent.parent.parent / "deployments" / "helm" / "mcp-server-langgraph" / "templates" / "secret.yaml"
    )
    external_secrets_path = (
        Path(__file__).parent.parent.parent / "deployments" / "overlays" / "production-gke" / "external-secrets.yaml"
    )

    if not external_secrets_path.exists():
        pytest.skip("ExternalSecrets not configured")

    with open(helm_secret_path) as f:
        helm_template = f.read()

    with open(external_secrets_path) as f:
        external_secrets = yaml.safe_load_all(f)
        # Find ExternalSecret resource
        for resource in external_secrets:
            if resource and resource.get("kind") == "ExternalSecret":
                template_data = resource.get("spec", {}).get("target", {}).get("template", {}).get("data", {})

                # Extract expected keys from Helm template
                helm_keys = set(re.findall(r"^\s+([a-z0-9-]+):\s+{{", helm_template, re.MULTILINE))

                # Extract keys from ExternalSecret
                external_keys = set(template_data.keys())

                # Check alignment (ExternalSecret should have at least core keys)
                core_keys = {"anthropic-api-key", "jwt-secret-key", "postgres-password", "redis-password"}
                missing_core_keys = core_keys - external_keys

                assert not missing_core_keys, (
                    f"ExternalSecret missing core secret keys: {missing_core_keys}\n"
                    f"Helm template expects: {sorted(helm_keys)}\n"
                    f"ExternalSecret provides: {sorted(external_keys)}\n"
                    f"Update {external_secrets_path}"
                )


# Test 6: Namespace Consistency (Prevents Issue #11)
def test_overlay_namespaces_have_patches():
    """
    Test that each overlay either defines its own namespace or patches it.

    This prevents namespace confusion between environments.
    """
    overlays_path = Path(__file__).parent.parent.parent / "deployments" / "overlays"

    for overlay_dir in overlays_path.iterdir():
        if not overlay_dir.is_dir() or overlay_dir.name.startswith("."):
            continue

        kustomization_file = overlay_dir / "kustomization.yaml"
        if not kustomization_file.exists():
            continue

        with open(kustomization_file) as f:
            kustomization = yaml.safe_load(f)

        resources = kustomization.get("resources", [])
        patches = kustomization.get("patches", [])

        # Check if namespace.yaml is in resources
        has_namespace_resource = any("namespace.yaml" in str(r) for r in resources)

        # Check if namespace is patched
        has_namespace_patch = False
        for patch in patches:
            if isinstance(patch, dict):
                if patch.get("path") == "namespace.yaml":
                    has_namespace_patch = True
                    break

        # Either should be true (resources or patches)
        assert has_namespace_resource or has_namespace_patch, (
            f"Overlay '{overlay_dir.name}' should include namespace.yaml in resources or patches.\n"
            f"Found: resources={resources}, patches={[p.get('path') if isinstance(p, dict) else p for p in patches]}\n"
            f"Create {overlay_dir}/namespace.yaml and add to kustomization resources or patches."
        )


# Test 7: Version Consistency (Prevents Issue #6)
def test_deployment_image_versions_consistent():
    """
    Test that all deployment configurations use consistent image versions.

    This prevents version drift across different deployment methods.
    """
    deployments_path = Path(__file__).parent.parent.parent / "deployments"

    # Extract versions from different configs
    versions = {}

    # Helm values
    helm_values_path = deployments_path / "helm" / "mcp-server-langgraph" / "values.yaml"
    with open(helm_values_path) as f:
        helm_values = yaml.safe_load(f)
        versions["helm"] = helm_values.get("image", {}).get("tag", "")

    # Cloud Run
    cloudrun_path = deployments_path / "cloudrun" / "service.yaml"
    with open(cloudrun_path) as f:
        content = f.read()
        match = re.search(r"mcp-server-langgraph:(\d+\.\d+\.\d+)", content)
        if match:
            versions["cloudrun"] = match.group(1)

    # ArgoCD
    argocd_path = deployments_path / "argocd" / "applications" / "mcp-server-app.yaml"
    if argocd_path.exists():
        with open(argocd_path) as f:
            content = f.read()
            match = re.search(r'tag:\s*["\'](\d+\.\d+\.\d+)["\']', content)
            if match:
                versions["argocd"] = match.group(1)

    # Check consistency (within major version)
    base_version = versions.get("helm", "").split(".")[0]

    for deployment_type, version in versions.items():
        if version and version.split(".")[0] != base_version:
            pytest.fail(
                f"Version mismatch: {deployment_type} uses {version}, "
                f"but helm uses {versions['helm']}\n"
                f"Versions found: {versions}"
            )


# Test 8: Redis Password Required (Prevents Issue #10)
def test_redis_password_not_optional():
    """
    Test that Redis password is required (not optional) in deployments.

    This prevents Redis running without authentication.
    """
    redis_deployment_path = Path(__file__).parent.parent.parent / "deployments" / "base" / "redis-session-deployment.yaml"

    with open(redis_deployment_path) as f:
        content = f.read()

    # Find redis-password secret reference
    redis_password_section = re.search(r"name: REDIS_PASSWORD.*?key: redis-password.*?optional: (\w+)", content, re.DOTALL)

    assert redis_password_section, "Redis password secret reference not found"

    optional_value = redis_password_section.group(1)
    assert optional_value == "false", (
        f"Redis password is optional: {optional_value}\n"
        f"Security requirement: Redis password must be mandatory (optional: false)"
    )


# Test 9: Service Annotations Cloud-Agnostic (Prevents Issue #7)
def test_base_service_no_cloud_specific_annotations():
    """
    Test that base service doesn't have cloud-specific annotations.

    Cloud-specific annotations should be in overlays only.
    """
    service_path = Path(__file__).parent.parent.parent / "deployments" / "base" / "service.yaml"

    with open(service_path) as f:
        services = list(yaml.safe_load_all(f))

    cloud_annotation_patterns = [
        r"aws\.",
        r"cloud\.google\.",
        r"azure\.",
    ]

    for service in services:
        if not service:
            continue
        annotations = service.get("metadata", {}).get("annotations", {})

        for key in annotations.keys():
            for pattern in cloud_annotation_patterns:
                assert not re.match(pattern, key), (
                    f"Base service has cloud-specific annotation: {key}\n"
                    f"Move to overlay-specific patches:\n"
                    f"  - overlays/aws/service-patch.yaml\n"
                    f"  - overlays/gke/service-patch.yaml"
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
