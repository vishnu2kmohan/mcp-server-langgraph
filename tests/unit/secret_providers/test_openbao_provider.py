"""
OpenBao Secrets Provider Tests

Tests for OpenBao/HashiCorp Vault secrets provider.
"""

import gc
import os
from unittest.mock import patch

import pytest

from mcp_server_langgraph.secret_providers.base import SecretNotFoundError

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_openbao_provider")
class TestOpenBaoProviderConfiguration:
    """Tests for OpenBao provider configuration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_creates_with_default_address(self) -> None:
        """GIVEN no address specified
        WHEN creating OpenBaoProvider
        THEN should use default localhost address
        """
        from mcp_server_langgraph.secret_providers.openbao import OpenBaoProvider

        provider = OpenBaoProvider()
        assert provider.address == "http://localhost:8200"

    def test_creates_with_custom_address(self) -> None:
        """GIVEN custom address
        WHEN creating OpenBaoProvider
        THEN should use custom address
        """
        from mcp_server_langgraph.secret_providers.openbao import OpenBaoProvider

        provider = OpenBaoProvider(address="https://vault.example.com:8200")
        assert provider.address == "https://vault.example.com:8200"

    def test_reads_address_from_environment(self) -> None:
        """GIVEN OPENBAO_ADDR environment variable
        WHEN creating OpenBaoProvider
        THEN should use environment address
        """
        from mcp_server_langgraph.secret_providers.openbao import OpenBaoProvider

        with patch.dict(os.environ, {"OPENBAO_ADDR": "https://env-vault.example.com"}):
            provider = OpenBaoProvider()
            assert provider.address == "https://env-vault.example.com"

    def test_reads_token_from_environment(self) -> None:
        """GIVEN OPENBAO_TOKEN environment variable
        WHEN creating OpenBaoProvider
        THEN should use environment token
        """
        from mcp_server_langgraph.secret_providers.openbao import OpenBaoProvider

        with patch.dict(os.environ, {"OPENBAO_TOKEN": "s.test-token"}):
            provider = OpenBaoProvider()
            assert provider._token == "s.test-token"

    def test_accepts_explicit_token(self) -> None:
        """GIVEN explicit token parameter
        WHEN creating OpenBaoProvider
        THEN should use explicit token
        """
        from mcp_server_langgraph.secret_providers.openbao import OpenBaoProvider

        provider = OpenBaoProvider(token="s.explicit-token")
        assert provider._token == "s.explicit-token"

    def test_default_mount_path(self) -> None:
        """GIVEN no mount path specified
        WHEN creating OpenBaoProvider
        THEN should use default 'secret' mount
        """
        from mcp_server_langgraph.secret_providers.openbao import OpenBaoProvider

        provider = OpenBaoProvider()
        assert provider.mount_path == "secret"

    def test_custom_mount_path(self) -> None:
        """GIVEN custom mount path
        WHEN creating OpenBaoProvider
        THEN should use custom mount path
        """
        from mcp_server_langgraph.secret_providers.openbao import OpenBaoProvider

        provider = OpenBaoProvider(mount_path="kv-v2")
        assert provider.mount_path == "kv-v2"


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_openbao_provider")
class TestOpenBaoProviderGetSecret:
    """Tests for OpenBao get_secret operation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_secret_returns_value(self) -> None:
        """GIVEN existing secret in OpenBao
        WHEN calling get_secret
        THEN should return secret value
        """
        from mcp_server_langgraph.secret_providers.openbao import OpenBaoProvider

        provider = OpenBaoProvider(token="test-token")

        with patch.object(provider, "_client") as mock_client:
            mock_client.secrets.kv.v2.read_secret_version.return_value = {"data": {"data": {"value": "secret-value"}}}

            result = await provider.get_secret("my-secret")
            assert result == "secret-value"

    @pytest.mark.asyncio
    async def test_get_secret_raises_not_found(self) -> None:
        """GIVEN non-existent secret
        WHEN calling get_secret
        THEN should raise SecretNotFoundError
        """
        from mcp_server_langgraph.secret_providers.openbao import OpenBaoProvider

        provider = OpenBaoProvider(token="test-token")

        with patch.object(provider, "_client") as mock_client:
            mock_client.secrets.kv.v2.read_secret_version.side_effect = Exception("secret not found")

            with pytest.raises(SecretNotFoundError) as exc_info:
                await provider.get_secret("non-existent")
            assert exc_info.value.secret_name == "non-existent"

    @pytest.mark.asyncio
    async def test_get_secret_with_path(self) -> None:
        """GIVEN secret with path
        WHEN calling get_secret with path
        THEN should use full path
        """
        from mcp_server_langgraph.secret_providers.openbao import OpenBaoProvider

        provider = OpenBaoProvider(token="test-token")

        with patch.object(provider, "_client") as mock_client:
            mock_client.secrets.kv.v2.read_secret_version.return_value = {"data": {"data": {"value": "nested-secret"}}}

            result = await provider.get_secret("app/database/password")
            assert result == "nested-secret"
            mock_client.secrets.kv.v2.read_secret_version.assert_called_once()


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_openbao_provider")
class TestOpenBaoProviderSetSecret:
    """Tests for OpenBao set_secret operation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_set_secret_creates_new(self) -> None:
        """GIVEN new secret
        WHEN calling set_secret
        THEN should create secret
        """
        from mcp_server_langgraph.secret_providers.openbao import OpenBaoProvider

        provider = OpenBaoProvider(token="test-token")

        with patch.object(provider, "_client") as mock_client:
            await provider.set_secret("new-secret", "new-value")
            mock_client.secrets.kv.v2.create_or_update_secret.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_secret_updates_existing(self) -> None:
        """GIVEN existing secret
        WHEN calling set_secret
        THEN should update secret
        """
        from mcp_server_langgraph.secret_providers.openbao import OpenBaoProvider

        provider = OpenBaoProvider(token="test-token")

        with patch.object(provider, "_client") as mock_client:
            await provider.set_secret("existing-secret", "updated-value")
            mock_client.secrets.kv.v2.create_or_update_secret.assert_called_once()


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_openbao_provider")
class TestOpenBaoProviderIsAvailable:
    """Tests for OpenBao availability check."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_is_available_returns_true_when_connected(self) -> None:
        """GIVEN OpenBao is reachable
        WHEN calling is_available
        THEN should return True
        """
        from mcp_server_langgraph.secret_providers.openbao import OpenBaoProvider

        provider = OpenBaoProvider(token="test-token")

        with patch.object(provider, "_client") as mock_client:
            mock_client.sys.read_health_status.return_value = {"initialized": True}
            result = await provider.is_available()
            assert result is True

    @pytest.mark.asyncio
    async def test_is_available_returns_false_when_disconnected(self) -> None:
        """GIVEN OpenBao is not reachable
        WHEN calling is_available
        THEN should return False
        """
        from mcp_server_langgraph.secret_providers.openbao import OpenBaoProvider

        provider = OpenBaoProvider(token="test-token")

        with patch.object(provider, "_client") as mock_client:
            mock_client.sys.read_health_status.side_effect = Exception("Connection failed")
            result = await provider.is_available()
            assert result is False
