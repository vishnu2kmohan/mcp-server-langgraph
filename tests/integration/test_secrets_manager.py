"""Unit tests for secrets_manager.py - Infisical Integration"""

import gc
import os
from unittest.mock import MagicMock, patch

import pytest


# Check if infisical-python is available
try:
    from infisical_client import InfisicalClient  # noqa: F401

    INFISICAL_AVAILABLE = True
except ImportError:
    INFISICAL_AVAILABLE = False

# Skip all tests in this module if infisical-python is not installed
pytestmark = pytest.mark.skipif(not INFISICAL_AVAILABLE, reason="infisical-python not installed (optional dependency)")


@pytest.mark.unit
@pytest.mark.infisical
@pytest.mark.xdist_group(name="secrets_manager_tests")
class TestSecretsManager:
    """Test SecretsManager class"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @patch("mcp_server_langgraph.secrets.manager.InfisicalClient")
    def test_init_with_credentials(self, mock_client):
        """Test initialization with provided credentials"""
        from mcp_server_langgraph.secrets.manager import SecretsManager

        manager = SecretsManager(
            site_url="https://app.infisical.com",
            client_id="test-client-id",
            client_secret="test-client-secret",
            project_id="test-project",
            environment="prod",
        )

        assert manager.site_url == "https://app.infisical.com"
        assert manager.project_id == "test-project"
        assert manager.environment == "prod"
        assert manager.client is not None
        mock_client.assert_called_once()

    @patch("mcp_server_langgraph.secrets.manager.InfisicalClient")
    def test_init_without_credentials(self, mock_client):
        """Test initialization without credentials falls back gracefully"""
        from mcp_server_langgraph.secrets.manager import SecretsManager

        manager = SecretsManager()

        assert manager.client is None

    @patch("mcp_server_langgraph.secrets.manager.InfisicalClient")
    @patch.dict(
        os.environ,
        {
            "INFISICAL_CLIENT_ID": "env-client-id",
            "INFISICAL_CLIENT_SECRET": "env-client-secret",
            "INFISICAL_PROJECT_ID": "env-project-id",
        },
    )
    def test_init_from_environment(self, mock_client):
        """Test initialization reads from environment variables"""
        from mcp_server_langgraph.secrets.manager import SecretsManager

        manager = SecretsManager()

        assert manager.project_id == "env-project-id"
        assert manager.client is not None
        mock_client.assert_called_once()

    @patch("mcp_server_langgraph.secrets.manager.InfisicalClient")
    def test_init_client_error(self, mock_client):
        """Test initialization handles client creation errors"""
        from mcp_server_langgraph.secrets.manager import SecretsManager

        mock_client.side_effect = Exception("Connection failed")

        manager = SecretsManager(client_id="test-id", client_secret="test-secret")

        assert manager.client is None

    @patch("mcp_server_langgraph.secrets.manager.InfisicalClient")
    def test_get_secret_success(self, mock_client):
        """Test successfully retrieving a secret"""
        from mcp_server_langgraph.secrets.manager import SecretsManager

        mock_secret = MagicMock()
        mock_secret.secret_value = "secret-value-123"

        mock_instance = MagicMock()
        mock_instance.get_secret.return_value = mock_secret
        mock_client.return_value = mock_instance

        manager = SecretsManager(client_id="test-id", client_secret="test-secret", project_id="test-project")

        value = manager.get_secret("API_KEY")

        assert value == "secret-value-123"
        mock_instance.get_secret.assert_called_once_with(
            secret_name="API_KEY", project_id="test-project", environment="dev", path="/"
        )

    @patch("mcp_server_langgraph.secrets.manager.InfisicalClient")
    def test_get_secret_with_path(self, mock_client):
        """Test retrieving secret from specific path"""
        from mcp_server_langgraph.secrets.manager import SecretsManager

        mock_secret = MagicMock()
        mock_secret.secret_value = "path-secret-value"

        mock_instance = MagicMock()
        mock_instance.get_secret.return_value = mock_secret
        mock_client.return_value = mock_instance

        manager = SecretsManager(client_id="test-id", client_secret="test-secret", project_id="test-project")

        value = manager.get_secret("DB_PASSWORD", path="/database")

        assert value == "path-secret-value"
        call_args = mock_instance.get_secret.call_args
        assert call_args[1]["path"] == "/database"

    @patch("mcp_server_langgraph.secrets.manager.InfisicalClient")
    def test_get_secret_caching(self, mock_client):
        """Test secret caching works"""
        from mcp_server_langgraph.secrets.manager import SecretsManager

        mock_secret = MagicMock()
        mock_secret.secret_value = "cached-value"

        mock_instance = MagicMock()
        mock_instance.get_secret.return_value = mock_secret
        mock_client.return_value = mock_instance

        manager = SecretsManager(client_id="test-id", client_secret="test-secret", project_id="test-project")

        # First call - should hit Infisical
        value1 = manager.get_secret("API_KEY", use_cache=True)
        assert value1 == "cached-value"
        assert mock_instance.get_secret.call_count == 1

        # Second call - should use cache
        value2 = manager.get_secret("API_KEY", use_cache=True)
        assert value2 == "cached-value"
        assert mock_instance.get_secret.call_count == 1  # Not called again

    @patch("mcp_server_langgraph.secrets.manager.InfisicalClient")
    def test_get_secret_no_cache(self, mock_client):
        """Test getting secret without caching"""
        from mcp_server_langgraph.secrets.manager import SecretsManager

        mock_secret = MagicMock()
        mock_secret.secret_value = "no-cache-value"

        mock_instance = MagicMock()
        mock_instance.get_secret.return_value = mock_secret
        mock_client.return_value = mock_instance

        manager = SecretsManager(client_id="test-id", client_secret="test-secret", project_id="test-project")

        # First call
        manager.get_secret("API_KEY", use_cache=False)
        assert mock_instance.get_secret.call_count == 1

        # Second call - should hit Infisical again
        manager.get_secret("API_KEY", use_cache=False)
        assert mock_instance.get_secret.call_count == 2

    @patch("mcp_server_langgraph.secrets.manager.InfisicalClient")
    @patch.dict(os.environ, {"TEST_SECRET": "env-fallback-value"})
    def test_get_secret_fallback_to_env(self, mock_client):
        """Test fallback to environment variable when client unavailable"""
        from mcp_server_langgraph.secrets.manager import SecretsManager

        manager = SecretsManager()  # No credentials, client is None

        value = manager.get_secret("TEST_SECRET")

        assert value == "env-fallback-value"

    @patch("mcp_server_langgraph.secrets.manager.InfisicalClient")
    def test_get_secret_fallback_to_default(self, mock_client):
        """Test fallback to default value when not found"""
        from mcp_server_langgraph.secrets.manager import SecretsManager

        manager = SecretsManager()  # No credentials

        value = manager.get_secret("NONEXISTENT_KEY", fallback="default-value")

        assert value == "default-value"

    @patch("mcp_server_langgraph.secrets.manager.InfisicalClient")
    def test_get_secret_error_uses_fallback(self, mock_client):
        """Test error in retrieval uses fallback"""
        from mcp_server_langgraph.secrets.manager import SecretsManager

        mock_instance = MagicMock()
        mock_instance.get_secret.side_effect = Exception("Infisical error")
        mock_client.return_value = mock_instance

        manager = SecretsManager(client_id="test-id", client_secret="test-secret", project_id="test-project")

        value = manager.get_secret("API_KEY", fallback="error-fallback")

        assert value == "error-fallback"

    @patch("mcp_server_langgraph.secrets.manager.InfisicalClient")
    @patch.dict(os.environ, {"API_KEY": "env-value"})
    def test_get_secret_error_tries_env_first(self, mock_client):
        """Test error tries environment variable before fallback"""
        from mcp_server_langgraph.secrets.manager import SecretsManager

        mock_instance = MagicMock()
        mock_instance.get_secret.side_effect = Exception("Infisical error")
        mock_client.return_value = mock_instance

        manager = SecretsManager(client_id="test-id", client_secret="test-secret", project_id="test-project")

        value = manager.get_secret("API_KEY", fallback="default")

        assert value == "env-value"

    @patch("mcp_server_langgraph.secrets.manager.InfisicalClient")
    def test_create_secret_success(self, mock_client):
        """Test creating a new secret"""
        from mcp_server_langgraph.secrets.manager import SecretsManager

        mock_instance = MagicMock()
        mock_instance.create_secret.return_value = MagicMock()
        mock_client.return_value = mock_instance

        manager = SecretsManager(client_id="test-id", client_secret="test-secret", project_id="test-project")

        manager.create_secret("NEW_KEY", "new-value")

        mock_instance.create_secret.assert_called_once()

    @patch("mcp_server_langgraph.secrets.manager.InfisicalClient")
    def test_update_secret_success(self, mock_client):
        """Test updating an existing secret"""
        from mcp_server_langgraph.secrets.manager import SecretsManager

        mock_instance = MagicMock()
        mock_instance.update_secret.return_value = MagicMock()
        mock_client.return_value = mock_instance

        manager = SecretsManager(client_id="test-id", client_secret="test-secret", project_id="test-project")

        manager.update_secret("EXISTING_KEY", "updated-value")

        mock_instance.update_secret.assert_called_once()

    @patch("mcp_server_langgraph.secrets.manager.InfisicalClient")
    def test_delete_secret_success(self, mock_client):
        """Test deleting a secret"""
        from mcp_server_langgraph.secrets.manager import SecretsManager

        mock_instance = MagicMock()
        mock_instance.delete_secret.return_value = MagicMock()
        mock_client.return_value = mock_instance

        manager = SecretsManager(client_id="test-id", client_secret="test-secret", project_id="test-project")

        manager.delete_secret("OLD_KEY")

        mock_instance.delete_secret.assert_called_once()

    @patch("mcp_server_langgraph.secrets.manager.InfisicalClient")
    def test_get_all_secrets_success(self, mock_client):
        """Test retrieving all secrets from a path"""
        from mcp_server_langgraph.secrets.manager import SecretsManager

        mock_secret1 = MagicMock()
        mock_secret1.secret_key = "KEY1"
        mock_secret1.secret_value = "value1"

        mock_secret2 = MagicMock()
        mock_secret2.secret_key = "KEY2"
        mock_secret2.secret_value = "value2"

        mock_instance = MagicMock()
        mock_instance.list_secrets.return_value = [mock_secret1, mock_secret2]
        mock_client.return_value = mock_instance

        manager = SecretsManager(client_id="test-id", client_secret="test-secret", project_id="test-project")

        secrets = manager.get_all_secrets(path="/app")

        assert secrets == {"KEY1": "value1", "KEY2": "value2"}
        mock_instance.list_secrets.assert_called_once()

    @patch("mcp_server_langgraph.secrets.manager.InfisicalClient")
    def test_get_all_secrets_no_client(self, mock_client):
        """Test get_all_secrets without Infisical client"""
        from mcp_server_langgraph.secrets.manager import SecretsManager

        manager = SecretsManager()  # No client

        secrets = manager.get_all_secrets()

        assert secrets == {}

    @patch("mcp_server_langgraph.secrets.manager.InfisicalClient")
    def test_get_all_secrets_error(self, mock_client):
        """Test get_all_secrets handles errors"""
        from mcp_server_langgraph.secrets.manager import SecretsManager

        mock_instance = MagicMock()
        mock_instance.list_secrets.side_effect = Exception("API error")
        mock_client.return_value = mock_instance

        manager = SecretsManager(client_id="test-id", client_secret="test-secret", project_id="test-project")

        secrets = manager.get_all_secrets()

        assert secrets == {}

    @patch("mcp_server_langgraph.secrets.manager.InfisicalClient")
    def test_create_secret_no_client(self, mock_client):
        """Test create_secret without Infisical client"""
        from mcp_server_langgraph.secrets.manager import SecretsManager

        manager = SecretsManager()  # No client

        result = manager.create_secret("KEY", "value")

        assert result is False

    @patch("mcp_server_langgraph.secrets.manager.InfisicalClient")
    def test_create_secret_error(self, mock_client):
        """Test create_secret handles errors"""
        from mcp_server_langgraph.secrets.manager import SecretsManager

        mock_instance = MagicMock()
        mock_instance.create_secret.side_effect = Exception("Create failed")
        mock_client.return_value = mock_instance

        manager = SecretsManager(client_id="test-id", client_secret="test-secret", project_id="test-project")

        result = manager.create_secret("KEY", "value")

        assert result is False

    @patch("mcp_server_langgraph.secrets.manager.InfisicalClient")
    def test_update_secret_no_client(self, mock_client):
        """Test update_secret without Infisical client"""
        from mcp_server_langgraph.secrets.manager import SecretsManager

        manager = SecretsManager()  # No client

        result = manager.update_secret("KEY", "value")

        assert result is False

    @patch("mcp_server_langgraph.secrets.manager.InfisicalClient")
    def test_update_secret_error(self, mock_client):
        """Test update_secret handles errors"""
        from mcp_server_langgraph.secrets.manager import SecretsManager

        mock_instance = MagicMock()
        mock_instance.update_secret.side_effect = Exception("Update failed")
        mock_client.return_value = mock_instance

        manager = SecretsManager(client_id="test-id", client_secret="test-secret", project_id="test-project")

        result = manager.update_secret("KEY", "value")

        assert result is False

    @patch("mcp_server_langgraph.secrets.manager.InfisicalClient")
    def test_delete_secret_no_client(self, mock_client):
        """Test delete_secret without Infisical client"""
        from mcp_server_langgraph.secrets.manager import SecretsManager

        manager = SecretsManager()  # No client

        result = manager.delete_secret("KEY")

        assert result is False

    @patch("mcp_server_langgraph.secrets.manager.InfisicalClient")
    def test_delete_secret_error(self, mock_client):
        """Test delete_secret handles errors"""
        from mcp_server_langgraph.secrets.manager import SecretsManager

        mock_instance = MagicMock()
        mock_instance.delete_secret.side_effect = Exception("Delete failed")
        mock_client.return_value = mock_instance

        manager = SecretsManager(client_id="test-id", client_secret="test-secret", project_id="test-project")

        result = manager.delete_secret("KEY")

        assert result is False


@pytest.mark.integration
@pytest.mark.infisical
@pytest.mark.xdist_group(name="secrets_manager_tests")
class TestSecretsManagerIntegration:
    """Integration tests for Infisical (requires running Infisical instance)"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.skipif(
        not all(
            [
                os.getenv("TEST_INFISICAL_CLIENT_ID"),
                os.getenv("TEST_INFISICAL_CLIENT_SECRET"),
                os.getenv("TEST_INFISICAL_PROJECT_ID"),
            ]
        ),
        reason="Requires Infisical credentials (TEST_INFISICAL_CLIENT_ID, TEST_INFISICAL_CLIENT_SECRET, TEST_INFISICAL_PROJECT_ID)",
    )
    def test_full_secret_lifecycle(self):
        """
        Test complete secret lifecycle with real Infisical.

        Runs only when Infisical credentials are provided via environment variables:
        - TEST_INFISICAL_CLIENT_ID
        - TEST_INFISICAL_CLIENT_SECRET
        - TEST_INFISICAL_PROJECT_ID
        """
        from mcp_server_langgraph.secrets.manager import SecretsManager

        # Use real Infisical credentials from environment
        manager = SecretsManager(
            client_id=os.getenv("TEST_INFISICAL_CLIENT_ID"),
            client_secret=os.getenv("TEST_INFISICAL_CLIENT_SECRET"),
            project_id=os.getenv("TEST_INFISICAL_PROJECT_ID"),
            environment="dev",
        )

        # Create secret
        manager.create_secret("TEST_KEY", "test-value")

        # Retrieve secret
        value = manager.get_secret("TEST_KEY", use_cache=False)
        assert value == "test-value"

        # Update secret
        manager.update_secret("TEST_KEY", "updated-value")
        value = manager.get_secret("TEST_KEY", use_cache=False)
        assert value == "updated-value"

        # Delete secret
        manager.delete_secret("TEST_KEY")
