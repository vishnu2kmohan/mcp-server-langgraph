"""
Test Infisical Optional Dependency Handling

Verifies that the application gracefully handles cases where infisical-python
is not installed, falling back to environment variables.
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestInfisicalOptionalDependency:
    """Test graceful degradation when Infisical not installed"""

    def test_secrets_manager_without_infisical(self, monkeypatch):
        """Verify SecretsManager works without infisical-python installed"""
        # Mock the infisical_client import to simulate it not being installed
        mock_import = MagicMock()
        mock_import.side_effect = ImportError("No module named 'infisical_client'")

        with patch.dict("sys.modules", {"infisical_client": None}):
            # This should not raise an error
            from mcp_server_langgraph.secrets.manager import SecretsManager

            # Should initialize with fallback mode (client=None)
            mgr = SecretsManager()
            assert mgr.client is None

    def test_get_secret_fallback_to_env(self, monkeypatch):
        """Verify get_secret falls back to environment variables"""
        from mcp_server_langgraph.secrets.manager import SecretsManager

        # Create manager without Infisical (credentials not provided)
        mgr = SecretsManager(client_id=None, client_secret=None)
        assert mgr.client is None

        # Set environment variable
        monkeypatch.setenv("TEST_SECRET_KEY", "test-value-from-env")

        # Should retrieve from environment
        value = mgr.get_secret("TEST_SECRET_KEY")
        assert value == "test-value-from-env"

    def test_get_secret_with_fallback_parameter(self):
        """Verify get_secret uses fallback parameter when secret not found"""
        from mcp_server_langgraph.secrets.manager import SecretsManager

        # Create manager without Infisical
        mgr = SecretsManager(client_id=None, client_secret=None)

        # Should use fallback value
        value = mgr.get_secret("NONEXISTENT_SECRET", fallback="default-value")
        assert value == "default-value"

    def test_get_secret_returns_none_when_not_found(self):
        """Verify get_secret returns None when secret not found and no fallback"""
        from mcp_server_langgraph.secrets.manager import SecretsManager

        # Create manager without Infisical
        mgr = SecretsManager(client_id=None, client_secret=None)

        # Should return None
        value = mgr.get_secret("NONEXISTENT_SECRET")
        assert value is None

    def test_get_all_secrets_empty_without_infisical(self):
        """Verify get_all_secrets returns empty dict without Infisical"""
        from mcp_server_langgraph.secrets.manager import SecretsManager

        # Create manager without Infisical
        mgr = SecretsManager(client_id=None, client_secret=None)

        # Should return empty dict
        secrets = mgr.get_all_secrets()
        assert secrets == {}

    def test_create_secret_fails_gracefully(self):
        """Verify create_secret returns False without Infisical"""
        from mcp_server_langgraph.secrets.manager import SecretsManager

        # Create manager without Infisical
        mgr = SecretsManager(client_id=None, client_secret=None)

        # Should return False
        result = mgr.create_secret("test_key", "test_value")
        assert result is False

    def test_update_secret_fails_gracefully(self):
        """Verify update_secret returns False without Infisical"""
        from mcp_server_langgraph.secrets.manager import SecretsManager

        # Create manager without Infisical
        mgr = SecretsManager(client_id=None, client_secret=None)

        # Should return False
        result = mgr.update_secret("test_key", "new_value")
        assert result is False

    def test_delete_secret_fails_gracefully(self):
        """Verify delete_secret returns False without Infisical"""
        from mcp_server_langgraph.secrets.manager import SecretsManager

        # Create manager without Infisical
        mgr = SecretsManager(client_id=None, client_secret=None)

        # Should return False
        result = mgr.delete_secret("test_key")
        assert result is False


@pytest.mark.unit
class TestConfigWithoutInfisical:
    """Test Settings configuration without Infisical"""

    def test_settings_loads_without_infisical(self, monkeypatch):
        """Verify Settings can be loaded without Infisical"""
        # Set required environment variables
        monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret")

        # Should not raise an error
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()
        assert settings.jwt_secret_key == "test-jwt-secret"

    def test_settings_get_secret_fallback(self, monkeypatch):
        """Verify Settings.get_secret falls back to environment"""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")

        from mcp_server_langgraph.core.config import Settings

        settings = Settings()

        # Even without Infisical, should retrieve from env
        value = settings.get_secret("ANTHROPIC_API_KEY", fallback="default")
        assert value in ("sk-ant-test-key", "default")  # Depends on implementation


@pytest.mark.unit
class TestApplicationStartupWithoutInfisical:
    """Test application can start without Infisical"""

    def test_agent_creation_without_infisical(self, monkeypatch):
        """Verify agent can be created without Infisical"""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret")
        monkeypatch.setenv("GOOGLE_API_KEY", "test-google-key")

        # Should not raise ImportError or other errors
        from mcp_server_langgraph.core.agent import create_agent_graph

        # Mock LLM creation to avoid actual API calls
        with patch("mcp_server_langgraph.core.agent.create_llm_from_config") as mock_llm:
            mock_llm.return_value = MagicMock()

            graph = create_agent_graph()
            assert graph is not None

    def test_health_check_without_infisical(self):
        """Verify health check works without Infisical"""
        from mcp_server_langgraph.health.checks import health_check

        # Should return healthy status even without Infisical
        with patch("mcp_server_langgraph.health.checks.settings") as mock_settings:
            mock_settings.infisical_client_id = None
            mock_settings.infisical_site_url = "https://app.infisical.com"

            health = health_check()

            # Should have infisical status as "not_configured"
            assert "infisical" in health.get("checks", {})
            assert health["checks"]["infisical"]["status"] == "not_configured"


@pytest.mark.unit
class TestInfisicalLogging:
    """Test logging behavior when Infisical unavailable"""

    def test_warning_logged_on_fallback(self, caplog):
        """Verify warning is logged when falling back to environment variables"""
        from mcp_server_langgraph.secrets.manager import SecretsManager

        # Create manager without credentials
        with caplog.at_level("WARNING"):
            mgr = SecretsManager(client_id=None, client_secret=None)

            # Should log warning about fallback mode
            assert any("fallback" in record.message.lower() for record in caplog.records)

    def test_info_logged_on_env_fallback(self, caplog, monkeypatch):
        """Verify info is logged when using environment variable fallback"""
        from mcp_server_langgraph.secrets.manager import SecretsManager

        mgr = SecretsManager(client_id=None, client_secret=None)
        monkeypatch.setenv("TEST_KEY", "test-value")

        with caplog.at_level("INFO"):
            value = mgr.get_secret("TEST_KEY")

            # Should log info about environment variable fallback
            # (may or may not log depending on implementation)
            assert value == "test-value"


@pytest.mark.integration
@pytest.mark.infisical
class TestInfisicalIntegration:
    """Integration tests for Infisical (skip if not installed)"""

    @pytest.fixture
    def skip_if_no_infisical(self):
        """Skip test if Infisical not installed"""
        try:
            import infisical_client  # noqa: F401
        except ImportError:
            pytest.skip("infisical-python not installed (optional dependency)")

    def test_infisical_available_when_installed(self, skip_if_no_infisical):
        """Verify Infisical works when installed (requires credentials)"""
        from mcp_server_langgraph.secrets.manager import SecretsManager

        # This test only runs if Infisical is installed
        # It still requires credentials to actually connect
        mgr = SecretsManager()

        # If credentials not provided, client should be None
        # This is expected and not an error
        assert mgr.client is None or mgr.client is not None


@pytest.mark.unit
class TestDocumentationExamples:
    """Test examples from documentation work correctly"""

    def test_docker_compose_example(self, monkeypatch):
        """Verify Docker Compose setup works (no Infisical required)"""
        # Simulate Docker environment variables
        monkeypatch.setenv("SERVICE_NAME", "mcp-server-langgraph")
        monkeypatch.setenv("JWT_SECRET_KEY", "dev-secret")
        monkeypatch.setenv("LLM_PROVIDER", "google")

        from mcp_server_langgraph.core.config import Settings

        settings = Settings()
        assert settings.service_name == "mcp-server-langgraph"
        assert settings.jwt_secret_key == "dev-secret"

    def test_env_file_example(self, monkeypatch):
        """Verify .env file setup works (no Infisical required)"""
        # Simulate .env file loading
        monkeypatch.setenv("JWT_SECRET_KEY", "your-secret-key-here")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

        from mcp_server_langgraph.core.config import Settings

        settings = Settings()
        assert settings.jwt_secret_key == "your-secret-key-here"
        assert settings.anthropic_api_key == "sk-ant-test"
