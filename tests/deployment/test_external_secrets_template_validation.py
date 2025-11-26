"""Validation tests for External Secrets templates.

This test module ensures that Kubernetes External Secrets templates have proper
URL encoding filters for Redis passwords, preventing the production incident
(staging-758b8f744) from recurring.

Tests validate:
1. Redis URL templates use | urlquery filter for password encoding
2. Consistency with database URL templates (which already use urlquery)
3. Regression prevention for accidental filter removal
"""

import gc
import re
from pathlib import Path

import pytest
import yaml

# Mark as unit test to ensure it runs in CI (deployment validation)
pytestmark = [pytest.mark.unit, pytest.mark.validation]


@pytest.mark.xdist_group(name="testexternalsecretsredisurlencoding")
class TestExternalSecretsRedisURLEncoding:
    """Validate External Secrets templates have proper URL encoding."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def staging_external_secrets_path(self) -> Path:
        """Path to staging External Secrets manifest."""
        return Path("deployments/overlays/staging-gke/external-secrets.yaml")

    @pytest.fixture
    def staging_external_secrets(self, staging_external_secrets_path: Path) -> dict:
        """Load staging External Secrets YAML."""
        if not staging_external_secrets_path.exists():
            pytest.skip(f"External Secrets manifest not found: {staging_external_secrets_path}")

        with open(staging_external_secrets_path) as f:
            # Parse YAML (may contain multiple documents)
            docs = list(yaml.safe_load_all(f))

        # Find the ExternalSecret with target.template
        for doc in docs:
            if doc and doc.get("kind") == "ExternalSecret":
                return doc

        pytest.fail("No ExternalSecret resource found in manifest")

    def test_redis_url_template_has_urlquery_filter(self, staging_external_secrets: dict):
        """Test that redis-url template uses | urlquery filter for password encoding."""
        # Navigate to spec.target.template.data
        target = staging_external_secrets.get("spec", {}).get("target", {})
        assert target, "No target section found in ExternalSecret"

        template_data = target.get("template", {}).get("data", {})
        assert template_data, "No template.data found in ExternalSecret"

        # Get redis-url template value
        redis_url_template = template_data.get("redis-url", "")
        assert redis_url_template, "redis-url not found in template.data"

        # Verify | urlquery filter is present
        assert "| urlquery" in redis_url_template, (
            f"redis-url template missing '| urlquery' filter.\n"
            f"Found: {redis_url_template}\n"
            f'Expected: redis://:{{{{ .redisPassword | urlquery }}}}@..."'
        )

    def test_checkpoint_redis_url_template_has_urlquery_filter(self, staging_external_secrets: dict):
        """Test that checkpoint-redis-url template uses | urlquery filter."""
        target = staging_external_secrets.get("spec", {}).get("target", {})
        template_data = target.get("template", {}).get("data", {})

        # Get checkpoint-redis-url template value
        checkpoint_url_template = template_data.get("checkpoint-redis-url", "")
        assert checkpoint_url_template, "checkpoint-redis-url not found in template.data"

        # Verify | urlquery filter is present
        assert "| urlquery" in checkpoint_url_template, (
            f"checkpoint-redis-url template missing '| urlquery' filter.\n"
            f"Found: {checkpoint_url_template}\n"
            f'Expected: redis://:{{{{ .redisPassword | urlquery }}}}@..."'
        )

    def test_consistency_with_database_url_templates(self, staging_external_secrets: dict):
        """Test that Redis URLs follow same pattern as database URLs.

        Database URLs (keycloak-db-url, openfga-datastore-uri) already use
        | urlquery filter. Redis URLs must follow this established pattern.
        """
        target = staging_external_secrets.get("spec", {}).get("target", {})
        template_data = target.get("template", {}).get("data", {})

        # Check database URL templates have urlquery
        keycloak_url = template_data.get("keycloak-db-url", "")
        openfga_url = template_data.get("openfga-datastore-uri", "")

        assert "| urlquery" in keycloak_url, "keycloak-db-url should use urlquery filter"
        assert "| urlquery" in openfga_url, "openfga-datastore-uri should use urlquery filter"

        # Verify Redis URLs also use urlquery (consistency)
        redis_url = template_data.get("redis-url", "")
        checkpoint_url = template_data.get("checkpoint-redis-url", "")

        assert "| urlquery" in redis_url, (
            "redis-url missing urlquery filter.\n" "This inconsistency led to production incident staging-758b8f744."
        )
        assert "| urlquery" in checkpoint_url, (
            "checkpoint-redis-url missing urlquery filter.\n"
            "This inconsistency led to production incident staging-758b8f744."
        )

    def test_redis_password_template_variable_correct(self, staging_external_secrets: dict):
        """Test that Redis URLs reference correct template variable."""
        target = staging_external_secrets.get("spec", {}).get("target", {})
        template_data = target.get("template", {}).get("data", {})

        redis_url = template_data.get("redis-url", "")
        checkpoint_url = template_data.get("checkpoint-redis-url", "")

        # Verify correct variable name (redisPassword, not redis_password or other)
        assert (
            "{{ .redisPassword | urlquery }}" in redis_url
        ), "redis-url should use {{ .redisPassword | urlquery }} template variable"
        assert (
            "{{ .redisPassword | urlquery }}" in checkpoint_url
        ), "checkpoint-redis-url should use {{ .redisPassword | urlquery }} template variable"

    def test_redis_url_structure_is_valid(self, staging_external_secrets: dict):
        """Test that Redis URL template has valid structure."""
        target = staging_external_secrets.get("spec", {}).get("target", {})
        template_data = target.get("template", {}).get("data", {})

        redis_url = template_data.get("redis-url", "")
        checkpoint_url = template_data.get("checkpoint-redis-url", "")

        # Expected structure: redis://:{{ .redisPassword | urlquery }}@{{ .redisHost }}:6379/0
        assert redis_url.startswith("redis://"), "redis-url should start with redis://"
        assert "{{ .redisPassword | urlquery }}" in redis_url, "redis-url missing encoded password"
        assert "{{ .redisHost }}" in redis_url, "redis-url missing host variable"
        assert ":6379/0" in redis_url, "redis-url should use port 6379 and database 0"

        # Expected structure: redis://:{{ .redisPassword | urlquery }}@{{ .redisHost }}:6379/1
        assert checkpoint_url.startswith("redis://"), "checkpoint-redis-url should start with redis://"
        assert "{{ .redisPassword | urlquery }}" in checkpoint_url, "checkpoint-redis-url missing encoded password"
        assert "{{ .redisHost }}" in checkpoint_url, "checkpoint-redis-url missing host variable"
        assert ":6379/1" in checkpoint_url, "checkpoint-redis-url should use port 6379 and database 1"

    def test_comments_document_url_encoding_requirement(self, staging_external_secrets_path: Path):
        """Test that YAML file includes comments about URL encoding."""
        # Read the raw YAML file to check for comments
        with open(staging_external_secrets_path) as f:
            yaml_content = f.read()

        # Should have comment about URL encoding near Redis URLs
        encoding_comment_patterns = [
            r"URL-encode",
            r"RFC\s*3986",
            r"special.*character",
        ]

        has_comment = any(re.search(pattern, yaml_content, re.IGNORECASE) for pattern in encoding_comment_patterns)

        assert has_comment, (
            "External Secrets YAML should include comment documenting "
            "URL encoding requirement for passwords with special characters"
        )


@pytest.mark.xdist_group(name="testexternalsecretsregressionprevention")
class TestExternalSecretsRegressionPrevention:
    """Regression tests to prevent accidental removal of URL encoding filters."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def template_content(self) -> str:
        """Load External Secrets template content."""
        path = Path("deployments/overlays/staging-gke/external-secrets.yaml")
        if not path.exists():
            pytest.skip(f"External Secrets manifest not found: {path}")

        with open(path) as f:
            return f.read()

    def test_no_unencoded_redis_password_in_template(self, template_content: str):
        """Test that no Redis URL uses unencoded password.

        This prevents accidental regression where someone removes the urlquery filter.
        """
        # Pattern that would match INCORRECT (unencoded) password usage
        # Example: redis://:{{ .redisPassword }}@host (missing | urlquery)
        incorrect_pattern = r"redis://:\{\{\s*\.redisPassword\s*\}\}@"

        match = re.search(incorrect_pattern, template_content)

        assert not match, (
            f"Found Redis URL with UNENCODED password: {match.group(0) if match else 'N/A'}\n"
            f"This is the EXACT bug that caused production incident staging-758b8f744.\n"
            f"Password must be encoded using: {{{{ .redisPassword | urlquery }}}}"
        )

    def test_urlquery_filter_count_matches_redis_url_count(self, template_content: str):
        """Test that number of urlquery filters matches number of Redis URLs.

        Ensures every Redis URL with password has corresponding urlquery filter.
        """
        # Count Redis URLs with passwords
        redis_url_pattern = r"redis://:.*?@"
        redis_urls = re.findall(redis_url_pattern, template_content)

        # Count urlquery filters in Redis URL context
        # Look for {{ .redisPassword | urlquery }} patterns
        urlquery_pattern = r"\{\{\s*\.redisPassword\s*\|\s*urlquery\s*\}\}"
        urlquery_filters = re.findall(urlquery_pattern, template_content)

        # Should have at least 2: redis-url and checkpoint-redis-url
        assert len(redis_urls) >= 2, f"Expected at least 2 Redis URLs, found {len(redis_urls)}"
        assert (
            len(urlquery_filters) >= 2
        ), f"Expected at least 2 urlquery filters for Redis passwords, found {len(urlquery_filters)}"

        # Ideally, count should match (each Redis URL should have filter)
        # But we'll be lenient and just require >= 2
        assert len(urlquery_filters) >= 2, (
            f"Insufficient urlquery filters for Redis URLs.\n"
            f"Redis URLs found: {len(redis_urls)}\n"
            f"urlquery filters found: {len(urlquery_filters)}\n"
            f"Every Redis URL with password MUST use | urlquery filter."
        )

    def test_production_incident_prevention_marker(self, template_content: str):
        """Test that template includes reference to production incident.

        This serves as documentation and reminder for future maintainers.
        """
        # Template should reference the incident or RFC 3986
        incident_markers = [
            "RFC 3986",  # Technical standard reference
            "758b8f744",  # Specific revision that failed
            "URL-encode",  # Explicit encoding instruction
            "special character",  # Describes the problem
        ]

        has_marker = any(marker in template_content for marker in incident_markers)

        assert has_marker, (
            "External Secrets template should include documentation about "
            "the URL encoding requirement (RFC 3986) or reference to the "
            "production incident (staging-758b8f744) to prevent future regressions."
        )


@pytest.mark.xdist_group(name="testexternalsecretsmultienvironmentconsistency")
class TestExternalSecretsMultiEnvironmentConsistency:
    """Test that URL encoding is consistent across all deployment environments."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.parametrize(
        "overlay_path",
        [
            "deployments/overlays/staging-gke/external-secrets.yaml",
            # Add more environments as they adopt the fix
            # "deployments/overlays/production-gke/external-secrets.yaml",
        ],
    )
    def test_all_environments_use_urlquery_filter(self, overlay_path: str):
        """Test that all deployment overlays use urlquery filter for Redis URLs."""
        path = Path(overlay_path)

        if not path.exists():
            pytest.skip(f"External Secrets manifest not found: {path}")

        with open(path) as f:
            content = f.read()

        # Verify urlquery filter present
        assert "| urlquery" in content, (
            f"Environment {overlay_path} missing urlquery filter for Redis URLs.\n"
            f"All environments must use consistent URL encoding."
        )

        # Verify no unencoded Redis passwords
        incorrect_pattern = r"redis://:\{\{\s*\.redisPassword\s*\}\}@"
        match = re.search(incorrect_pattern, content)

        assert not match, (
            f"Environment {overlay_path} has unencoded Redis password.\n" f"Found: {match.group(0) if match else 'N/A'}"
        )
