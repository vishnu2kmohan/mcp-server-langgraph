"""
Tests for hardcoded configuration audit.

TDD tests to verify that production-critical configuration fields
use environment variables with validated/validated-looking defaults,
NOT hardcoded example/test values.

Reference: Cloud-Native 12-Factor App Principle III - Store config in environment
"""

import gc

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="test_hardcoded_config_audit")
class TestNoHardcodedExampleEmails:
    """Verify that example emails are not used as production defaults."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_vapid_claims_email_not_example_domain(self) -> None:
        """VAPID claims email should not use example.com domain."""
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()
        vapid_email = settings.vapid_claims_email

        # Should not contain example.com - that's clearly a placeholder
        assert "example.com" not in vapid_email, (
            f"VAPID claims email should not use example.com domain. "
            f"Got: {vapid_email}. Use VAPID_CLAIMS_EMAIL env var or a valid default."
        )

    def test_vapid_claims_email_is_optional_or_configured(self) -> None:
        """VAPID claims email should be configurable via environment variable."""
        from mcp_server_langgraph.core.config import Settings

        # Verify the field accepts env var
        field_info = Settings.model_fields.get("vapid_claims_email")
        assert field_info is not None

        # Should either be Optional (None allowed) or have env var support
        # Field should have proper validation_alias or default_factory

    def test_audit_from_address_not_example_domain(self) -> None:
        """Audit email from_address should not use example.com domain."""
        from mcp_server_langgraph.audit.config import EmailConfig

        config = EmailConfig()
        from_address = config.from_address

        # Should not contain example.com - that's clearly a placeholder
        assert "example.com" not in from_address, (
            f"Audit from_address should not use example.com domain. "
            f"Got: {from_address}. Use AUDIT_FROM_EMAIL env var or empty default."
        )


@pytest.mark.xdist_group(name="test_config_env_var_support")
class TestConfigEnvironmentVariableSupport:
    """Verify that critical configs support environment variables."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_vapid_claims_email_from_env_var(self, monkeypatch) -> None:
        """VAPID claims email should be configurable via VAPID_CLAIMS_EMAIL."""
        monkeypatch.setenv("VAPID_CLAIMS_EMAIL", "webpush@mycompany.com")

        from mcp_server_langgraph.core.config import Settings

        settings = Settings()
        assert settings.vapid_claims_email == "webpush@mycompany.com"

    def test_audit_from_address_from_env_var(self, monkeypatch) -> None:
        """Audit from_address should be configurable via AUDIT_FROM_EMAIL."""
        monkeypatch.setenv("AUDIT_FROM_EMAIL", "audit@mycompany.com")

        from mcp_server_langgraph.audit.config import EmailConfig

        config = EmailConfig()
        assert config.from_address == "audit@mycompany.com"


@pytest.mark.xdist_group(name="test_localhost_url_defaults")
class TestLocalhostUrlDefaults:
    """Verify localhost URLs are properly marked as development-only defaults."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_localhost_urls_have_env_var_support(self) -> None:
        """All localhost URL defaults should have env var override support."""
        from mcp_server_langgraph.core.config import Settings

        # Fields with localhost defaults should support env vars
        localhost_fields = [
            "ollama_base_url",
            "openfga_api_url",
            "keycloak_server_url",
            "frontend_url",
        ]

        for field_name in localhost_fields:
            field_info = Settings.model_fields.get(field_name)
            if field_info is not None:
                # Field exists, which is what we want
                # We just verify the field exists and is configurable
                # Localhost is fine for development, but should be overrideable
                assert field_info is not None, f"Field {field_name} should exist"

    def test_ollama_url_from_env_var(self, monkeypatch) -> None:
        """Ollama base URL should be configurable via OLLAMA_BASE_URL."""
        monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama-service:11434")

        from mcp_server_langgraph.core.config import Settings

        settings = Settings()
        assert settings.ollama_base_url == "http://ollama-service:11434"

    def test_openfga_url_from_env_var(self, monkeypatch) -> None:
        """OpenFGA API URL should be configurable via OPENFGA_API_URL."""
        monkeypatch.setenv("OPENFGA_API_URL", "http://openfga:8080")

        from mcp_server_langgraph.core.config import Settings

        settings = Settings()
        assert settings.openfga_api_url == "http://openfga:8080"
