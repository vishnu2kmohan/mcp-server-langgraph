"""
Secrets Factory Tests

Tests for the secrets provider factory function.
"""

import gc
import os
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_secrets_factory")
class TestSecretsProviderFactory:
    """Tests for get_secrets_provider factory function."""

    def setup_method(self) -> None:
        """Clear provider cache before each test."""
        from mcp_server_langgraph.secret_providers.factory import _clear_provider_cache

        _clear_provider_cache()

    def teardown_method(self) -> None:
        """Force GC and clear cache after tests."""
        from mcp_server_langgraph.secret_providers.factory import _clear_provider_cache

        _clear_provider_cache()
        gc.collect()

    def test_returns_environment_provider_by_default(self) -> None:
        """GIVEN no provider configured
        WHEN calling get_secrets_provider
        THEN should return EnvironmentProvider
        """
        from mcp_server_langgraph.secret_providers.factory import get_secrets_provider
        from mcp_server_langgraph.secret_providers.environment import EnvironmentProvider

        provider = get_secrets_provider()
        assert isinstance(provider, EnvironmentProvider)

    def test_returns_openbao_when_configured(self) -> None:
        """GIVEN SECRETS_PROVIDER=openbao
        WHEN calling get_secrets_provider
        THEN should return OpenBaoProvider
        """
        from mcp_server_langgraph.secret_providers.factory import get_secrets_provider
        from mcp_server_langgraph.secret_providers.openbao import OpenBaoProvider

        with patch.dict(
            os.environ,
            {
                "SECRETS_PROVIDER": "openbao",
                "OPENBAO_TOKEN": "test-token",
            },
        ):
            provider = get_secrets_provider()
            assert isinstance(provider, OpenBaoProvider)

    def test_returns_aws_when_configured(self) -> None:
        """GIVEN SECRETS_PROVIDER=aws
        WHEN calling get_secrets_provider
        THEN should return AWSSecretsProvider
        """
        from mcp_server_langgraph.secret_providers.factory import get_secrets_provider
        from mcp_server_langgraph.secret_providers.aws import AWSSecretsProvider

        with patch.dict(os.environ, {"SECRETS_PROVIDER": "aws"}):
            provider = get_secrets_provider()
            assert isinstance(provider, AWSSecretsProvider)

    def test_returns_gcp_when_configured(self) -> None:
        """GIVEN SECRETS_PROVIDER=gcp
        WHEN calling get_secrets_provider
        THEN should return GCPSecretsProvider
        """
        from mcp_server_langgraph.secret_providers.factory import get_secrets_provider
        from mcp_server_langgraph.secret_providers.gcp import GCPSecretsProvider

        with patch.dict(os.environ, {"SECRETS_PROVIDER": "gcp"}):
            provider = get_secrets_provider()
            assert isinstance(provider, GCPSecretsProvider)

    def test_returns_azure_when_configured(self) -> None:
        """GIVEN SECRETS_PROVIDER=azure
        WHEN calling get_secrets_provider
        THEN should return AzureKeyVaultProvider
        """
        from mcp_server_langgraph.secret_providers.factory import get_secrets_provider
        from mcp_server_langgraph.secret_providers.azure import AzureKeyVaultProvider

        with patch.dict(
            os.environ,
            {
                "SECRETS_PROVIDER": "azure",
                "AZURE_KEY_VAULT_URL": "https://test.vault.azure.net",
            },
        ):
            provider = get_secrets_provider()
            assert isinstance(provider, AzureKeyVaultProvider)

    def test_raises_for_unknown_provider(self) -> None:
        """GIVEN unknown SECRETS_PROVIDER value
        WHEN calling get_secrets_provider
        THEN should raise ValueError
        """
        from mcp_server_langgraph.secret_providers.factory import get_secrets_provider

        with patch.dict(os.environ, {"SECRETS_PROVIDER": "unknown"}):
            with pytest.raises(ValueError) as exc_info:
                get_secrets_provider()
            assert "unknown" in str(exc_info.value).lower()

    def test_caches_provider_instance(self) -> None:
        """GIVEN provider already created
        WHEN calling get_secrets_provider again
        THEN should return same instance
        """
        from mcp_server_langgraph.secret_providers.factory import (
            get_secrets_provider,
            _clear_provider_cache,
        )

        _clear_provider_cache()  # Clear any existing cache

        provider1 = get_secrets_provider()
        provider2 = get_secrets_provider()

        assert provider1 is provider2

        _clear_provider_cache()  # Cleanup


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_secrets_factory")
class TestEnvironmentProvider:
    """Tests for EnvironmentProvider fallback."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_secret_from_environment(self) -> None:
        """GIVEN environment variable set
        WHEN calling get_secret
        THEN should return environment value
        """
        from mcp_server_langgraph.secret_providers.environment import EnvironmentProvider

        provider = EnvironmentProvider()

        with patch.dict(os.environ, {"TEST_SECRET": "secret-value"}):
            result = await provider.get_secret("TEST_SECRET")
            assert result == "secret-value"

    @pytest.mark.asyncio
    async def test_get_secret_not_found(self) -> None:
        """GIVEN environment variable not set
        WHEN calling get_secret
        THEN should raise SecretNotFoundError
        """
        from mcp_server_langgraph.secret_providers.environment import EnvironmentProvider
        from mcp_server_langgraph.secret_providers.base import SecretNotFoundError

        provider = EnvironmentProvider()

        with pytest.raises(SecretNotFoundError):
            await provider.get_secret("NON_EXISTENT_VAR_12345")

    @pytest.mark.asyncio
    async def test_is_always_available(self) -> None:
        """GIVEN EnvironmentProvider
        WHEN calling is_available
        THEN should always return True
        """
        from mcp_server_langgraph.secret_providers.environment import EnvironmentProvider

        provider = EnvironmentProvider()
        result = await provider.is_available()
        assert result is True

    @pytest.mark.asyncio
    async def test_list_secrets_returns_env_keys(self) -> None:
        """GIVEN EnvironmentProvider
        WHEN calling list_secrets with prefix
        THEN should return matching env var names
        """
        from mcp_server_langgraph.secret_providers.environment import EnvironmentProvider

        provider = EnvironmentProvider()

        with patch.dict(
            os.environ,
            {
                "APP_SECRET_1": "val1",
                "APP_SECRET_2": "val2",
                "OTHER_VAR": "other",
            },
        ):
            result = await provider.list_secrets(prefix="APP_SECRET_")
            assert "APP_SECRET_1" in result
            assert "APP_SECRET_2" in result
            assert "OTHER_VAR" not in result
