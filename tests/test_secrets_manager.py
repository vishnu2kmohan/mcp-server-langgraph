"""Unit tests for secrets_manager.py - Infisical Integration"""
import pytest
import os
from unittest.mock import MagicMock, patch, PropertyMock


@pytest.mark.unit
@pytest.mark.infisical
class TestSecretsManager:
    """Test SecretsManager class"""

    @patch('secrets_manager.InfisicalClient')
    def test_init_with_credentials(self, mock_client):
        """Test initialization with provided credentials"""
        from secrets_manager import SecretsManager

        manager = SecretsManager(
            site_url="https://app.infisical.com",
            client_id="test-client-id",
            client_secret="test-client-secret",
            project_id="test-project",
            environment="prod"
        )

        assert manager.site_url == "https://app.infisical.com"
        assert manager.project_id == "test-project"
        assert manager.environment == "prod"
        assert manager.client is not None
        mock_client.assert_called_once()

    @patch('secrets_manager.InfisicalClient')
    def test_init_without_credentials(self, mock_client):
        """Test initialization without credentials falls back gracefully"""
        from secrets_manager import SecretsManager

        manager = SecretsManager()

        assert manager.client is None

    @patch('secrets_manager.InfisicalClient')
    @patch.dict(os.environ, {
        'INFISICAL_CLIENT_ID': 'env-client-id',
        'INFISICAL_CLIENT_SECRET': 'env-client-secret',
        'INFISICAL_PROJECT_ID': 'env-project-id'
    })
    def test_init_from_environment(self, mock_client):
        """Test initialization reads from environment variables"""
        from secrets_manager import SecretsManager

        manager = SecretsManager()

        assert manager.project_id == "env-project-id"
        assert manager.client is not None
        mock_client.assert_called_once()

    @patch('secrets_manager.InfisicalClient')
    def test_init_client_error(self, mock_client):
        """Test initialization handles client creation errors"""
        from secrets_manager import SecretsManager

        mock_client.side_effect = Exception("Connection failed")

        manager = SecretsManager(
            client_id="test-id",
            client_secret="test-secret"
        )

        assert manager.client is None

    @patch('secrets_manager.InfisicalClient')
    def test_get_secret_success(self, mock_client):
        """Test successfully retrieving a secret"""
        from secrets_manager import SecretsManager

        mock_secret = MagicMock()
        mock_secret.secret_value = "secret-value-123"

        mock_instance = MagicMock()
        mock_instance.get_secret.return_value = mock_secret
        mock_client.return_value = mock_instance

        manager = SecretsManager(
            client_id="test-id",
            client_secret="test-secret",
            project_id="test-project"
        )

        value = manager.get_secret("API_KEY")

        assert value == "secret-value-123"
        mock_instance.get_secret.assert_called_once_with(
            secret_name="API_KEY",
            project_id="test-project",
            environment="dev",
            path="/"
        )

    @patch('secrets_manager.InfisicalClient')
    def test_get_secret_with_path(self, mock_client):
        """Test retrieving secret from specific path"""
        from secrets_manager import SecretsManager

        mock_secret = MagicMock()
        mock_secret.secret_value = "path-secret-value"

        mock_instance = MagicMock()
        mock_instance.get_secret.return_value = mock_secret
        mock_client.return_value = mock_instance

        manager = SecretsManager(
            client_id="test-id",
            client_secret="test-secret",
            project_id="test-project"
        )

        value = manager.get_secret("DB_PASSWORD", path="/database")

        assert value == "path-secret-value"
        call_args = mock_instance.get_secret.call_args
        assert call_args[1]["path"] == "/database"

    @patch('secrets_manager.InfisicalClient')
    def test_get_secret_caching(self, mock_client):
        """Test secret caching works"""
        from secrets_manager import SecretsManager

        mock_secret = MagicMock()
        mock_secret.secret_value = "cached-value"

        mock_instance = MagicMock()
        mock_instance.get_secret.return_value = mock_secret
        mock_client.return_value = mock_instance

        manager = SecretsManager(
            client_id="test-id",
            client_secret="test-secret",
            project_id="test-project"
        )

        # First call - should hit Infisical
        value1 = manager.get_secret("API_KEY", use_cache=True)
        assert value1 == "cached-value"
        assert mock_instance.get_secret.call_count == 1

        # Second call - should use cache
        value2 = manager.get_secret("API_KEY", use_cache=True)
        assert value2 == "cached-value"
        assert mock_instance.get_secret.call_count == 1  # Not called again

    @patch('secrets_manager.InfisicalClient')
    def test_get_secret_no_cache(self, mock_client):
        """Test getting secret without caching"""
        from secrets_manager import SecretsManager

        mock_secret = MagicMock()
        mock_secret.secret_value = "no-cache-value"

        mock_instance = MagicMock()
        mock_instance.get_secret.return_value = mock_secret
        mock_client.return_value = mock_instance

        manager = SecretsManager(
            client_id="test-id",
            client_secret="test-secret",
            project_id="test-project"
        )

        # First call
        value1 = manager.get_secret("API_KEY", use_cache=False)
        assert mock_instance.get_secret.call_count == 1

        # Second call - should hit Infisical again
        value2 = manager.get_secret("API_KEY", use_cache=False)
        assert mock_instance.get_secret.call_count == 2

    @patch('secrets_manager.InfisicalClient')
    @patch.dict(os.environ, {'TEST_SECRET': 'env-fallback-value'})
    def test_get_secret_fallback_to_env(self, mock_client):
        """Test fallback to environment variable when client unavailable"""
        from secrets_manager import SecretsManager

        manager = SecretsManager()  # No credentials, client is None

        value = manager.get_secret("TEST_SECRET")

        assert value == "env-fallback-value"

    @patch('secrets_manager.InfisicalClient')
    def test_get_secret_fallback_to_default(self, mock_client):
        """Test fallback to default value when not found"""
        from secrets_manager import SecretsManager

        manager = SecretsManager()  # No credentials

        value = manager.get_secret(
            "NONEXISTENT_KEY",
            fallback="default-value"
        )

        assert value == "default-value"

    @patch('secrets_manager.InfisicalClient')
    def test_get_secret_error_uses_fallback(self, mock_client):
        """Test error in retrieval uses fallback"""
        from secrets_manager import SecretsManager

        mock_instance = MagicMock()
        mock_instance.get_secret.side_effect = Exception("Infisical error")
        mock_client.return_value = mock_instance

        manager = SecretsManager(
            client_id="test-id",
            client_secret="test-secret",
            project_id="test-project"
        )

        value = manager.get_secret("API_KEY", fallback="error-fallback")

        assert value == "error-fallback"

    @patch('secrets_manager.InfisicalClient')
    @patch.dict(os.environ, {'API_KEY': 'env-value'})
    def test_get_secret_error_tries_env_first(self, mock_client):
        """Test error tries environment variable before fallback"""
        from secrets_manager import SecretsManager

        mock_instance = MagicMock()
        mock_instance.get_secret.side_effect = Exception("Infisical error")
        mock_client.return_value = mock_instance

        manager = SecretsManager(
            client_id="test-id",
            client_secret="test-secret",
            project_id="test-project"
        )

        value = manager.get_secret("API_KEY", fallback="default")

        assert value == "env-value"

    @patch('secrets_manager.InfisicalClient')
    def test_create_secret_success(self, mock_client):
        """Test creating a new secret"""
        from secrets_manager import SecretsManager

        mock_instance = MagicMock()
        mock_instance.create_secret.return_value = MagicMock()
        mock_client.return_value = mock_instance

        manager = SecretsManager(
            client_id="test-id",
            client_secret="test-secret",
            project_id="test-project"
        )

        manager.create_secret("NEW_KEY", "new-value")

        mock_instance.create_secret.assert_called_once()

    @patch('secrets_manager.InfisicalClient')
    def test_update_secret_success(self, mock_client):
        """Test updating an existing secret"""
        from secrets_manager import SecretsManager

        mock_instance = MagicMock()
        mock_instance.update_secret.return_value = MagicMock()
        mock_client.return_value = mock_instance

        manager = SecretsManager(
            client_id="test-id",
            client_secret="test-secret",
            project_id="test-project"
        )

        manager.update_secret("EXISTING_KEY", "updated-value")

        mock_instance.update_secret.assert_called_once()

    @patch('secrets_manager.InfisicalClient')
    def test_delete_secret_success(self, mock_client):
        """Test deleting a secret"""
        from secrets_manager import SecretsManager

        mock_instance = MagicMock()
        mock_instance.delete_secret.return_value = MagicMock()
        mock_client.return_value = mock_instance

        manager = SecretsManager(
            client_id="test-id",
            client_secret="test-secret",
            project_id="test-project"
        )

        manager.delete_secret("OLD_KEY")

        mock_instance.delete_secret.assert_called_once()

    @patch('secrets_manager.InfisicalClient')
    def test_clear_cache(self, mock_client):
        """Test cache clearing"""
        from secrets_manager import SecretsManager

        mock_secret = MagicMock()
        mock_secret.secret_value = "cached"

        mock_instance = MagicMock()
        mock_instance.get_secret.return_value = mock_secret
        mock_client.return_value = mock_instance

        manager = SecretsManager(
            client_id="test-id",
            client_secret="test-secret",
            project_id="test-project"
        )

        # Cache a value
        manager.get_secret("KEY1")
        assert len(manager._cache) == 1

        # Clear cache
        manager.clear_cache()
        assert len(manager._cache) == 0


@pytest.mark.integration
@pytest.mark.infisical
class TestSecretsManagerIntegration:
    """Integration tests for Infisical (requires running Infisical instance)"""

    @pytest.mark.skip(reason="Requires running Infisical instance with credentials")
    def test_full_secret_lifecycle(self):
        """Test complete secret lifecycle with real Infisical"""
        from secrets_manager import SecretsManager

        # This requires real Infisical credentials
        manager = SecretsManager(
            client_id=os.getenv("TEST_INFISICAL_CLIENT_ID"),
            client_secret=os.getenv("TEST_INFISICAL_CLIENT_SECRET"),
            project_id=os.getenv("TEST_INFISICAL_PROJECT_ID"),
            environment="dev"
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
