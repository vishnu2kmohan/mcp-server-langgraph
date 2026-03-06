"""
Extended tests for secrets manager - covering SecretString, cache invalidation, singleton.

TDD RED Phase: Tests for uncovered lines in manager.py
"""

import gc
import os
from unittest.mock import patch

import pytest

# Check if infisical-python is available
import importlib.util

INFISICAL_AVAILABLE = importlib.util.find_spec("infisical_client") is not None

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="secrets_manager_extended")
class TestSecretString:
    """Test SecretString wrapper class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_secret_string_str_returns_redacted(self) -> None:
        """GIVEN a SecretString with a value
        WHEN converting to string
        THEN should return redacted placeholder
        """
        from mcp_server_langgraph.secret_providers.manager import SecretString

        secret = SecretString("my-super-secret-key")
        assert str(secret) == "***REDACTED***"

    def test_secret_string_repr_returns_redacted(self) -> None:
        """GIVEN a SecretString with a value
        WHEN getting repr
        THEN should return redacted representation
        """
        from mcp_server_langgraph.secret_providers.manager import SecretString

        secret = SecretString("my-super-secret-key")
        assert repr(secret) == "SecretString('***REDACTED***')"

    def test_secret_string_get_secret_value_returns_actual(self) -> None:
        """GIVEN a SecretString with a value
        WHEN calling get_secret_value
        THEN should return the actual secret
        """
        from mcp_server_langgraph.secret_providers.manager import SecretString

        secret = SecretString("my-super-secret-key")
        assert secret.get_secret_value() == "my-super-secret-key"

    def test_secret_string_equality_same_value(self) -> None:
        """GIVEN two SecretStrings with the same value
        WHEN comparing equality
        THEN should be equal
        """
        from mcp_server_langgraph.secret_providers.manager import SecretString

        secret1 = SecretString("same-value")
        secret2 = SecretString("same-value")
        assert secret1 == secret2

    def test_secret_string_equality_different_value(self) -> None:
        """GIVEN two SecretStrings with different values
        WHEN comparing equality
        THEN should not be equal
        """
        from mcp_server_langgraph.secret_providers.manager import SecretString

        secret1 = SecretString("value1")
        secret2 = SecretString("value2")
        assert secret1 != secret2

    def test_secret_string_equality_with_non_secret(self) -> None:
        """GIVEN a SecretString and a regular string
        WHEN comparing equality
        THEN should not be equal
        """
        from mcp_server_langgraph.secret_providers.manager import SecretString

        secret = SecretString("value")
        assert secret != "value"
        assert secret != 123
        assert secret is not None

    def test_secret_string_hash_same_value(self) -> None:
        """GIVEN two SecretStrings with the same value
        WHEN getting hash
        THEN should have same hash (usable in sets/dicts)
        """
        from mcp_server_langgraph.secret_providers.manager import SecretString

        secret1 = SecretString("same-value")
        secret2 = SecretString("same-value")
        assert hash(secret1) == hash(secret2)

        # Can be used in sets
        secret_set = {secret1}
        assert secret2 in secret_set

    def test_secret_string_hash_different_values(self) -> None:
        """GIVEN two SecretStrings with different values
        WHEN getting hash
        THEN should have different hashes
        """
        from mcp_server_langgraph.secret_providers.manager import SecretString

        secret1 = SecretString("value1")
        secret2 = SecretString("value2")
        assert hash(secret1) != hash(secret2)


@pytest.mark.unit
@pytest.mark.xdist_group(name="secrets_manager_extended")
class TestSecretsManagerCacheInvalidation:
    """Test cache invalidation methods."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_invalidate_cache_specific_key(self) -> None:
        """GIVEN a SecretsManager with cached secrets
        WHEN invalidating a specific key
        THEN only that key should be removed from cache
        """
        from mcp_server_langgraph.secret_providers.manager import SecretsManager

        manager = SecretsManager()  # No client, uses fallback
        # Manually populate cache
        manager._cache["/:API_KEY"] = "api-value"
        manager._cache["/:DB_PASSWORD"] = "db-value"
        manager._cache["/app:API_KEY"] = "app-api-value"

        # Invalidate only API_KEY
        manager.invalidate_cache("API_KEY")

        # API_KEY entries should be gone
        assert "/:API_KEY" not in manager._cache
        assert "/app:API_KEY" not in manager._cache
        # DB_PASSWORD should remain
        assert "/:DB_PASSWORD" in manager._cache

    def test_invalidate_cache_all(self) -> None:
        """GIVEN a SecretsManager with cached secrets
        WHEN invalidating all cache
        THEN cache should be empty
        """
        from mcp_server_langgraph.secret_providers.manager import SecretsManager

        manager = SecretsManager()
        # Manually populate cache
        manager._cache["/:KEY1"] = "value1"
        manager._cache["/:KEY2"] = "value2"
        manager._cache["/app:KEY3"] = "value3"

        # Invalidate all
        manager.invalidate_cache()

        assert len(manager._cache) == 0


@pytest.mark.unit
@pytest.mark.xdist_group(name="secrets_manager_extended")
class TestSecretsManagerSingleton:
    """Test get_secrets_manager singleton function."""

    def setup_method(self) -> None:
        """Reset singleton before each test."""
        import mcp_server_langgraph.secret_providers.manager as manager_module

        manager_module._secrets_manager = None

    def teardown_method(self) -> None:
        """Reset singleton and force GC."""
        import mcp_server_langgraph.secret_providers.manager as manager_module

        manager_module._secrets_manager = None
        gc.collect()

    def test_get_secrets_manager_returns_singleton(self) -> None:
        """GIVEN get_secrets_manager called multiple times
        WHEN comparing instances
        THEN should return same instance
        """
        from mcp_server_langgraph.secret_providers.manager import get_secrets_manager

        manager1 = get_secrets_manager()
        manager2 = get_secrets_manager()

        assert manager1 is manager2

    @patch.dict(os.environ, {"INFISICAL_SITE_URL": "https://custom.infisical.io"})
    def test_get_secrets_manager_reads_environment(self) -> None:
        """GIVEN custom INFISICAL_SITE_URL in environment
        WHEN getting secrets manager
        THEN should use custom URL
        """
        from mcp_server_langgraph.secret_providers.manager import get_secrets_manager

        manager = get_secrets_manager()

        assert manager.site_url == "https://custom.infisical.io"


@pytest.mark.unit
@pytest.mark.xdist_group(name="secrets_manager_extended")
class TestSecretsManagerRepr:
    """Test SecretsManager string representations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_str_representation_safe(self) -> None:
        """GIVEN a SecretsManager
        WHEN converting to string
        THEN should show safe information without secrets
        """
        from mcp_server_langgraph.secret_providers.manager import SecretsManager

        manager = SecretsManager(
            site_url="https://app.infisical.com",
            project_id="test-project",
            environment="prod",
        )

        result = str(manager)

        assert "https://app.infisical.com" in result
        assert "test-project" in result
        assert "prod" in result
        # Should not contain any credentials
        assert "client_secret" not in result.lower()

    def test_repr_shows_client_status(self) -> None:
        """GIVEN a SecretsManager
        WHEN getting repr
        THEN should show client connection status
        """
        from mcp_server_langgraph.secret_providers.manager import SecretsManager

        manager = SecretsManager()  # No credentials, client is None

        result = repr(manager)

        assert "disconnected" in result

    @pytest.mark.skipif(
        not INFISICAL_AVAILABLE,
        reason="infisical-python not installed",
    )
    @patch("mcp_server_langgraph.secret_providers.manager.InfisicalClient")
    def test_repr_shows_connected_when_client_available(self, mock_client) -> None:
        """GIVEN a SecretsManager with working client
        WHEN getting repr
        THEN should show connected status
        """
        from mcp_server_langgraph.secret_providers.manager import SecretsManager

        manager = SecretsManager(
            client_id="test-id",
            client_secret="test-secret",
        )

        result = repr(manager)

        assert "connected" in result
