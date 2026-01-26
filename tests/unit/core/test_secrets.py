"""
Core Secrets Provider Tests

Comprehensive tests for the secrets provider abstraction in core/secrets.py.
Tests cover InMemorySecretsProvider, cloud provider detection, factory function,
and singleton management.

Reference: TDD workflow - Write tests FIRST, then verify they define expected behavior.
"""

import gc
import os
from unittest.mock import MagicMock, patch

import pytest

from mcp_server_langgraph.core.secrets import (
    AWSSecretsManagerProvider,
    AzureKeyVaultProvider,
    GCPSecretManagerProvider,
    InMemorySecretsProvider,
    SecretsProvider,
    create_secrets_provider,
    detect_cloud_provider,
    get_secrets_provider,
    reset_secrets_provider,
    set_secrets_provider,
)

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_core_secrets")
class TestSecretsProviderProtocol:
    """Tests for the SecretsProvider protocol definition."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_protocol_defines_set_secret(self) -> None:
        """GIVEN SecretsProvider protocol
        WHEN inspecting methods
        THEN should have set_secret method
        """
        assert hasattr(SecretsProvider, "set_secret")

    def test_protocol_defines_get_secret(self) -> None:
        """GIVEN SecretsProvider protocol
        WHEN inspecting methods
        THEN should have get_secret method
        """
        assert hasattr(SecretsProvider, "get_secret")

    def test_protocol_defines_delete_secret(self) -> None:
        """GIVEN SecretsProvider protocol
        WHEN inspecting methods
        THEN should have delete_secret method
        """
        assert hasattr(SecretsProvider, "delete_secret")


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_core_secrets")
class TestInMemorySecretsProvider:
    """Tests for InMemorySecretsProvider implementation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_set_and_get_secret(self) -> None:
        """GIVEN InMemorySecretsProvider
        WHEN setting and getting a secret
        THEN should return the stored value
        """
        provider = InMemorySecretsProvider()
        await provider.set_secret("test-key", "test-value")
        result = await provider.get_secret("test-key")
        assert result == "test-value"

    @pytest.mark.asyncio
    async def test_get_nonexistent_secret_returns_none(self) -> None:
        """GIVEN InMemorySecretsProvider
        WHEN getting a secret that doesn't exist
        THEN should return None
        """
        provider = InMemorySecretsProvider()
        result = await provider.get_secret("nonexistent-key")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_secret(self) -> None:
        """GIVEN InMemorySecretsProvider with a stored secret
        WHEN deleting the secret
        THEN secret should no longer exist
        """
        provider = InMemorySecretsProvider()
        await provider.set_secret("delete-key", "value")
        await provider.delete_secret("delete-key")
        result = await provider.get_secret("delete-key")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_secret_no_error(self) -> None:
        """GIVEN InMemorySecretsProvider
        WHEN deleting a secret that doesn't exist
        THEN should not raise an error
        """
        provider = InMemorySecretsProvider()
        # Should not raise
        await provider.delete_secret("nonexistent-key")

    @pytest.mark.asyncio
    async def test_overwrite_secret(self) -> None:
        """GIVEN InMemorySecretsProvider with a stored secret
        WHEN setting the same key with a new value
        THEN should overwrite the old value
        """
        provider = InMemorySecretsProvider()
        await provider.set_secret("key", "value1")
        await provider.set_secret("key", "value2")
        result = await provider.get_secret("key")
        assert result == "value2"

    @pytest.mark.asyncio
    async def test_multiple_secrets(self) -> None:
        """GIVEN InMemorySecretsProvider
        WHEN storing multiple secrets
        THEN all should be retrievable independently
        """
        provider = InMemorySecretsProvider()
        await provider.set_secret("key1", "value1")
        await provider.set_secret("key2", "value2")
        await provider.set_secret("key3", "value3")

        assert await provider.get_secret("key1") == "value1"
        assert await provider.get_secret("key2") == "value2"
        assert await provider.get_secret("key3") == "value3"


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_core_secrets")
class TestAWSSecretsManagerProvider:
    """Tests for AWSSecretsManagerProvider implementation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_init_with_defaults(self) -> None:
        """GIVEN no parameters
        WHEN creating AWSSecretsManagerProvider
        THEN should use default values
        """
        with patch.dict(os.environ, {}, clear=True):
            provider = AWSSecretsManagerProvider()
            assert provider.region == "us-east-1"
            assert provider.prefix == "mcp-server/"

    def test_init_with_custom_region(self) -> None:
        """GIVEN custom region parameter
        WHEN creating AWSSecretsManagerProvider
        THEN should use custom region
        """
        provider = AWSSecretsManagerProvider(region="eu-west-1")
        assert provider.region == "eu-west-1"

    def test_init_with_env_region(self) -> None:
        """GIVEN AWS_REGION environment variable
        WHEN creating AWSSecretsManagerProvider
        THEN should use environment region
        """
        with patch.dict(os.environ, {"AWS_REGION": "ap-southeast-1"}):
            provider = AWSSecretsManagerProvider()
            assert provider.region == "ap-southeast-1"

    def test_init_with_custom_prefix(self) -> None:
        """GIVEN custom prefix parameter
        WHEN creating AWSSecretsManagerProvider
        THEN should use custom prefix
        """
        provider = AWSSecretsManagerProvider(prefix="custom/prefix/")
        assert provider.prefix == "custom/prefix/"

    def test_full_name_with_prefix(self) -> None:
        """GIVEN AWSSecretsManagerProvider with prefix
        WHEN calling _full_name
        THEN should return prefixed name
        """
        provider = AWSSecretsManagerProvider(prefix="test-app/")
        assert provider._full_name("my-secret") == "test-app/my-secret"

    @pytest.mark.asyncio
    async def test_get_client_creates_boto3_client(self) -> None:
        """GIVEN AWSSecretsManagerProvider
        WHEN calling _get_client
        THEN should create boto3 secretsmanager client
        """
        provider = AWSSecretsManagerProvider(region="us-west-2")

        mock_client = MagicMock()
        with patch("boto3.client", return_value=mock_client) as mock_boto3:
            client = provider._get_client()
            mock_boto3.assert_called_once_with("secretsmanager", region_name="us-west-2")
            assert client is mock_client

    @pytest.mark.asyncio
    async def test_get_client_caches_client(self) -> None:
        """GIVEN AWSSecretsManagerProvider
        WHEN calling _get_client multiple times
        THEN should return cached client
        """
        provider = AWSSecretsManagerProvider()

        mock_client = MagicMock()
        with patch("boto3.client", return_value=mock_client) as mock_boto3:
            client1 = provider._get_client()
            client2 = provider._get_client()
            assert client1 is client2
            mock_boto3.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_secret_creates_new_secret(self) -> None:
        """GIVEN AWSSecretsManagerProvider
        WHEN setting a new secret
        THEN should call create_secret
        """
        provider = AWSSecretsManagerProvider(prefix="")

        mock_client = MagicMock()
        mock_client.exceptions.ResourceExistsException = Exception

        with patch.object(provider, "_get_client", return_value=mock_client):
            await provider.set_secret("test-secret", "secret-value")

            mock_client.create_secret.assert_called_once_with(Name="test-secret", SecretString="secret-value")

    @pytest.mark.asyncio
    async def test_set_secret_updates_existing_secret(self) -> None:
        """GIVEN AWSSecretsManagerProvider with existing secret
        WHEN setting the same secret
        THEN should call put_secret_value after ResourceExistsException
        """
        provider = AWSSecretsManagerProvider(prefix="")

        mock_client = MagicMock()

        class ResourceExistsException(Exception):
            pass

        mock_client.exceptions.ResourceExistsException = ResourceExistsException
        mock_client.create_secret.side_effect = ResourceExistsException()

        with patch.object(provider, "_get_client", return_value=mock_client):
            await provider.set_secret("existing-secret", "new-value")

            mock_client.put_secret_value.assert_called_once_with(SecretId="existing-secret", SecretString="new-value")

    @pytest.mark.asyncio
    async def test_get_secret_returns_value(self) -> None:
        """GIVEN AWSSecretsManagerProvider
        WHEN getting an existing secret
        THEN should return the secret value
        """
        provider = AWSSecretsManagerProvider(prefix="")

        mock_client = MagicMock()
        mock_client.get_secret_value.return_value = {"SecretString": "retrieved-value"}

        with patch.object(provider, "_get_client", return_value=mock_client):
            result = await provider.get_secret("my-secret")

            assert result == "retrieved-value"
            mock_client.get_secret_value.assert_called_once_with(SecretId="my-secret")

    @pytest.mark.asyncio
    async def test_get_secret_returns_none_for_not_found(self) -> None:
        """GIVEN AWSSecretsManagerProvider
        WHEN getting a non-existent secret
        THEN should return None
        """
        provider = AWSSecretsManagerProvider(prefix="")

        mock_client = MagicMock()

        class ResourceNotFoundException(Exception):
            pass

        mock_client.exceptions.ResourceNotFoundException = ResourceNotFoundException
        mock_client.get_secret_value.side_effect = ResourceNotFoundException()

        with patch.object(provider, "_get_client", return_value=mock_client):
            result = await provider.get_secret("nonexistent")
            assert result is None

    @pytest.mark.asyncio
    async def test_delete_secret_with_force_delete(self) -> None:
        """GIVEN AWSSecretsManagerProvider
        WHEN deleting a secret
        THEN should call delete_secret with ForceDeleteWithoutRecovery
        """
        provider = AWSSecretsManagerProvider(prefix="")

        mock_client = MagicMock()

        with patch.object(provider, "_get_client", return_value=mock_client):
            await provider.delete_secret("delete-me")

            mock_client.delete_secret.assert_called_once_with(SecretId="delete-me", ForceDeleteWithoutRecovery=True)

    @pytest.mark.asyncio
    async def test_delete_secret_ignores_not_found(self) -> None:
        """GIVEN AWSSecretsManagerProvider
        WHEN deleting a non-existent secret
        THEN should not raise an error
        """
        provider = AWSSecretsManagerProvider(prefix="")

        mock_client = MagicMock()

        class ResourceNotFoundException(Exception):
            pass

        mock_client.exceptions.ResourceNotFoundException = ResourceNotFoundException
        mock_client.delete_secret.side_effect = ResourceNotFoundException()

        with patch.object(provider, "_get_client", return_value=mock_client):
            # Should not raise
            await provider.delete_secret("nonexistent")


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_core_secrets")
class TestAzureKeyVaultProvider:
    """Tests for AzureKeyVaultProvider implementation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_init_with_vault_url(self) -> None:
        """GIVEN vault_url parameter
        WHEN creating AzureKeyVaultProvider
        THEN should use provided URL
        """
        provider = AzureKeyVaultProvider(vault_url="https://test.vault.azure.net")
        assert provider.vault_url == "https://test.vault.azure.net"

    def test_init_with_env_vault_url(self) -> None:
        """GIVEN AZURE_KEY_VAULT_URL environment variable
        WHEN creating AzureKeyVaultProvider
        THEN should use environment URL
        """
        with patch.dict(os.environ, {"AZURE_KEY_VAULT_URL": "https://env.vault.azure.net"}):
            provider = AzureKeyVaultProvider()
            assert provider.vault_url == "https://env.vault.azure.net"

    def test_init_without_vault_url_raises_error(self) -> None:
        """GIVEN no vault_url configured
        WHEN creating AzureKeyVaultProvider
        THEN should raise ValueError
        """
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                AzureKeyVaultProvider()
            assert "AZURE_KEY_VAULT_URL" in str(exc_info.value)

    def test_sanitize_name_replaces_slashes(self) -> None:
        """GIVEN AzureKeyVaultProvider
        WHEN sanitizing a name with slashes
        THEN should replace with hyphens
        """
        provider = AzureKeyVaultProvider(vault_url="https://test.vault.azure.net")
        assert provider._sanitize_name("path/to/secret") == "path-to-secret"

    def test_sanitize_name_replaces_underscores(self) -> None:
        """GIVEN AzureKeyVaultProvider
        WHEN sanitizing a name with underscores
        THEN should replace with hyphens
        """
        provider = AzureKeyVaultProvider(vault_url="https://test.vault.azure.net")
        assert provider._sanitize_name("secret_name") == "secret-name"

    def test_sanitize_name_combined(self) -> None:
        """GIVEN AzureKeyVaultProvider
        WHEN sanitizing a name with mixed characters
        THEN should replace all invalid characters
        """
        provider = AzureKeyVaultProvider(vault_url="https://test.vault.azure.net")
        assert provider._sanitize_name("my/secret_name") == "my-secret-name"

    @pytest.mark.asyncio
    async def test_get_client_creates_azure_client(self) -> None:
        """GIVEN AzureKeyVaultProvider
        WHEN calling _get_client
        THEN should create and cache Azure SecretClient
        """
        provider = AzureKeyVaultProvider(vault_url="https://test.vault.azure.net")

        mock_secret_client = MagicMock()

        # Test that the client is cached properly
        provider._client = None
        provider._client = mock_secret_client

        client = provider._get_client()
        assert client is mock_secret_client

        # Verify caching - should return same instance
        client2 = provider._get_client()
        assert client2 is client

    @pytest.mark.asyncio
    async def test_set_secret_calls_azure_set_secret(self) -> None:
        """GIVEN AzureKeyVaultProvider
        WHEN setting a secret
        THEN should call Azure set_secret
        """
        provider = AzureKeyVaultProvider(vault_url="https://test.vault.azure.net")

        mock_client = MagicMock()

        with patch.object(provider, "_get_client", return_value=mock_client):
            await provider.set_secret("my_secret", "my-value")

            mock_client.set_secret.assert_called_once_with("my-secret", "my-value")

    @pytest.mark.asyncio
    async def test_get_secret_returns_value(self) -> None:
        """GIVEN AzureKeyVaultProvider
        WHEN getting an existing secret
        THEN should return the secret value
        """
        provider = AzureKeyVaultProvider(vault_url="https://test.vault.azure.net")

        mock_client = MagicMock()
        mock_secret = MagicMock()
        mock_secret.value = "azure-secret-value"
        mock_client.get_secret.return_value = mock_secret

        with patch.object(provider, "_get_client", return_value=mock_client):
            result = await provider.get_secret("my-secret")

            assert result == "azure-secret-value"

    @pytest.mark.asyncio
    async def test_get_secret_returns_none_for_not_found(self) -> None:
        """GIVEN AzureKeyVaultProvider
        WHEN getting a non-existent secret
        THEN should return None
        """
        provider = AzureKeyVaultProvider(vault_url="https://test.vault.azure.net")

        mock_client = MagicMock()

        # Import the actual exception for mocking
        from azure.core.exceptions import ResourceNotFoundError

        mock_client.get_secret.side_effect = ResourceNotFoundError("Not found")

        with patch.object(provider, "_get_client", return_value=mock_client):
            result = await provider.get_secret("nonexistent")
            assert result is None

    @pytest.mark.asyncio
    async def test_delete_secret_calls_begin_delete(self) -> None:
        """GIVEN AzureKeyVaultProvider
        WHEN deleting a secret
        THEN should call begin_delete_secret and wait for result
        """
        provider = AzureKeyVaultProvider(vault_url="https://test.vault.azure.net")

        mock_client = MagicMock()
        mock_poller = MagicMock()
        mock_client.begin_delete_secret.return_value = mock_poller

        with patch.object(provider, "_get_client", return_value=mock_client):
            await provider.delete_secret("delete_me")

            mock_client.begin_delete_secret.assert_called_once_with("delete-me")
            mock_poller.result.assert_called_once()


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_core_secrets")
class TestGCPSecretManagerProvider:
    """Tests for GCPSecretManagerProvider implementation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_init_with_project_id(self) -> None:
        """GIVEN project_id parameter
        WHEN creating GCPSecretManagerProvider
        THEN should use provided project ID
        """
        provider = GCPSecretManagerProvider(project_id="my-project")
        assert provider.project_id == "my-project"

    def test_init_with_env_project_id(self) -> None:
        """GIVEN GOOGLE_CLOUD_PROJECT environment variable
        WHEN creating GCPSecretManagerProvider
        THEN should use environment project ID
        """
        with patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "env-project"}):
            provider = GCPSecretManagerProvider()
            assert provider.project_id == "env-project"

    def test_init_without_project_id_raises_error(self) -> None:
        """GIVEN no project_id configured
        WHEN creating GCPSecretManagerProvider
        THEN should raise ValueError
        """
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                GCPSecretManagerProvider()
            assert "GOOGLE_CLOUD_PROJECT" in str(exc_info.value)

    def test_secret_path_formats_correctly(self) -> None:
        """GIVEN GCPSecretManagerProvider
        WHEN calling _secret_path
        THEN should return correct path format
        """
        provider = GCPSecretManagerProvider(project_id="my-project")
        path = provider._secret_path("my-secret")
        assert path == "projects/my-project/secrets/my-secret"

    def test_secret_version_path_default(self) -> None:
        """GIVEN GCPSecretManagerProvider
        WHEN calling _secret_version_path without version
        THEN should return path with 'latest' version
        """
        provider = GCPSecretManagerProvider(project_id="my-project")
        path = provider._secret_version_path("my-secret")
        assert path == "projects/my-project/secrets/my-secret/versions/latest"

    def test_secret_version_path_specific_version(self) -> None:
        """GIVEN GCPSecretManagerProvider
        WHEN calling _secret_version_path with specific version
        THEN should return path with that version
        """
        provider = GCPSecretManagerProvider(project_id="my-project")
        path = provider._secret_version_path("my-secret", version="3")
        assert path == "projects/my-project/secrets/my-secret/versions/3"

    @pytest.mark.asyncio
    async def test_get_client_creates_gcp_client(self) -> None:
        """GIVEN GCPSecretManagerProvider
        WHEN calling _get_client
        THEN should create and cache GCP SecretManagerServiceClient
        """
        provider = GCPSecretManagerProvider(project_id="my-project")

        mock_client = MagicMock()

        # Test that the client is cached properly
        provider._client = None
        provider._client = mock_client

        client = provider._get_client()
        assert client is mock_client

        # Verify caching - should return same instance
        client2 = provider._get_client()
        assert client2 is client

    @pytest.mark.asyncio
    async def test_set_secret_creates_and_adds_version(self) -> None:
        """GIVEN GCPSecretManagerProvider
        WHEN setting a secret
        THEN should create secret and add version
        """
        provider = GCPSecretManagerProvider(project_id="my-project")

        mock_client = MagicMock()

        with patch.object(provider, "_get_client", return_value=mock_client):
            await provider.set_secret("my-secret", "my-value")

            # Verify create_secret was called
            mock_client.create_secret.assert_called_once()
            call_args = mock_client.create_secret.call_args
            assert call_args.kwargs["request"]["parent"] == "projects/my-project"
            assert call_args.kwargs["request"]["secret_id"] == "my-secret"

            # Verify add_secret_version was called
            mock_client.add_secret_version.assert_called_once()
            version_args = mock_client.add_secret_version.call_args
            assert version_args.kwargs["request"]["parent"] == "projects/my-project/secrets/my-secret"
            assert version_args.kwargs["request"]["payload"]["data"] == b"my-value"

    @pytest.mark.asyncio
    async def test_set_secret_handles_already_exists(self) -> None:
        """GIVEN GCPSecretManagerProvider with existing secret
        WHEN setting the same secret
        THEN should only add new version
        """
        provider = GCPSecretManagerProvider(project_id="my-project")

        mock_client = MagicMock()

        # Import exception for mocking
        from google.api_core.exceptions import AlreadyExists

        mock_client.create_secret.side_effect = AlreadyExists("Already exists")

        with patch.object(provider, "_get_client", return_value=mock_client):
            await provider.set_secret("existing-secret", "new-value")

            # add_secret_version should still be called
            mock_client.add_secret_version.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_secret_returns_value(self) -> None:
        """GIVEN GCPSecretManagerProvider
        WHEN getting an existing secret
        THEN should return the decoded secret value
        """
        provider = GCPSecretManagerProvider(project_id="my-project")

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.payload.data = b"gcp-secret-value"
        mock_client.access_secret_version.return_value = mock_response

        with patch.object(provider, "_get_client", return_value=mock_client):
            result = await provider.get_secret("my-secret")

            assert result == "gcp-secret-value"
            mock_client.access_secret_version.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_secret_returns_none_for_not_found(self) -> None:
        """GIVEN GCPSecretManagerProvider
        WHEN getting a non-existent secret
        THEN should return None
        """
        provider = GCPSecretManagerProvider(project_id="my-project")

        mock_client = MagicMock()

        from google.api_core.exceptions import NotFound

        mock_client.access_secret_version.side_effect = NotFound("Not found")

        with patch.object(provider, "_get_client", return_value=mock_client):
            result = await provider.get_secret("nonexistent")
            assert result is None

    @pytest.mark.asyncio
    async def test_delete_secret_calls_delete_secret(self) -> None:
        """GIVEN GCPSecretManagerProvider
        WHEN deleting a secret
        THEN should call delete_secret with correct path
        """
        provider = GCPSecretManagerProvider(project_id="my-project")

        mock_client = MagicMock()

        with patch.object(provider, "_get_client", return_value=mock_client):
            await provider.delete_secret("my-secret")

            mock_client.delete_secret.assert_called_once()
            call_args = mock_client.delete_secret.call_args
            assert call_args.kwargs["request"]["name"] == "projects/my-project/secrets/my-secret"

    @pytest.mark.asyncio
    async def test_delete_secret_ignores_not_found(self) -> None:
        """GIVEN GCPSecretManagerProvider
        WHEN deleting a non-existent secret
        THEN should not raise an error
        """
        provider = GCPSecretManagerProvider(project_id="my-project")

        mock_client = MagicMock()

        from google.api_core.exceptions import NotFound

        mock_client.delete_secret.side_effect = NotFound("Not found")

        with patch.object(provider, "_get_client", return_value=mock_client):
            # Should not raise
            await provider.delete_secret("nonexistent")


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_core_secrets")
class TestDetectCloudProvider:
    """Tests for detect_cloud_provider function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_detects_aws_from_execution_env(self) -> None:
        """GIVEN AWS_EXECUTION_ENV set
        WHEN detecting cloud provider
        THEN should return 'aws'
        """
        with patch.dict(os.environ, {"AWS_EXECUTION_ENV": "AWS_ECS_FARGATE"}, clear=True):
            assert detect_cloud_provider() == "aws"

    def test_detects_aws_from_lambda(self) -> None:
        """GIVEN AWS_LAMBDA_FUNCTION_NAME set
        WHEN detecting cloud provider
        THEN should return 'aws'
        """
        with patch.dict(os.environ, {"AWS_LAMBDA_FUNCTION_NAME": "my-function"}, clear=True):
            assert detect_cloud_provider() == "aws"

    def test_detects_aws_from_secrets_prefix(self) -> None:
        """GIVEN AWS_SECRETS_PREFIX set
        WHEN detecting cloud provider
        THEN should return 'aws'
        """
        with patch.dict(os.environ, {"AWS_SECRETS_PREFIX": "myapp/"}, clear=True):
            assert detect_cloud_provider() == "aws"

    def test_detects_azure_from_key_vault_url(self) -> None:
        """GIVEN AZURE_KEY_VAULT_URL set
        WHEN detecting cloud provider
        THEN should return 'azure'
        """
        with patch.dict(
            os.environ,
            {"AZURE_KEY_VAULT_URL": "https://test.vault.azure.net"},
            clear=True,
        ):
            assert detect_cloud_provider() == "azure"

    def test_detects_azure_from_app_service(self) -> None:
        """GIVEN WEBSITE_INSTANCE_ID set (Azure App Service)
        WHEN detecting cloud provider
        THEN should return 'azure'
        """
        with patch.dict(os.environ, {"WEBSITE_INSTANCE_ID": "instance-123"}, clear=True):
            assert detect_cloud_provider() == "azure"

    def test_detects_gcp_from_project(self) -> None:
        """GIVEN GOOGLE_CLOUD_PROJECT set
        WHEN detecting cloud provider
        THEN should return 'gcp'
        """
        with patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "my-project"}, clear=True):
            assert detect_cloud_provider() == "gcp"

    def test_detects_gcp_from_cloud_run(self) -> None:
        """GIVEN K_SERVICE set (Cloud Run)
        WHEN detecting cloud provider
        THEN should return 'gcp'
        """
        with patch.dict(os.environ, {"K_SERVICE": "my-service"}, clear=True):
            assert detect_cloud_provider() == "gcp"

    def test_returns_local_when_no_cloud_detected(self) -> None:
        """GIVEN no cloud environment variables set
        WHEN detecting cloud provider
        THEN should return 'local'
        """
        with patch.dict(os.environ, {}, clear=True):
            assert detect_cloud_provider() == "local"


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_core_secrets")
class TestCreateSecretsProvider:
    """Tests for create_secrets_provider factory function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()
        reset_secrets_provider()

    def test_creates_inmemory_for_local(self) -> None:
        """GIVEN provider='local'
        WHEN creating secrets provider
        THEN should return InMemorySecretsProvider
        """
        provider = create_secrets_provider("local")
        assert isinstance(provider, InMemorySecretsProvider)

    def test_creates_inmemory_for_unknown(self) -> None:
        """GIVEN unknown provider name
        WHEN creating secrets provider
        THEN should return InMemorySecretsProvider
        """
        provider = create_secrets_provider("unknown")
        assert isinstance(provider, InMemorySecretsProvider)

    def test_creates_aws_provider(self) -> None:
        """GIVEN provider='aws'
        WHEN creating secrets provider
        THEN should return AWSSecretsManagerProvider
        """
        with patch.dict(os.environ, {"AWS_SECRETS_PREFIX": "test/"}):
            provider = create_secrets_provider("aws")
            assert isinstance(provider, AWSSecretsManagerProvider)

    def test_creates_aws_provider_fallback_on_import_error(self) -> None:
        """GIVEN provider='aws' but boto3 not available
        WHEN creating secrets provider
        THEN should fall back to InMemorySecretsProvider
        """
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(
                AWSSecretsManagerProvider,
                "__init__",
                side_effect=ImportError("boto3 not installed"),
            ):
                provider = create_secrets_provider("aws")
                assert isinstance(provider, InMemorySecretsProvider)

    def test_creates_azure_provider(self) -> None:
        """GIVEN provider='azure' with vault URL configured
        WHEN creating secrets provider
        THEN should return AzureKeyVaultProvider
        """
        with patch.dict(os.environ, {"AZURE_KEY_VAULT_URL": "https://test.vault.azure.net"}):
            provider = create_secrets_provider("azure")
            assert isinstance(provider, AzureKeyVaultProvider)

    def test_creates_azure_provider_fallback_on_import_error(self) -> None:
        """GIVEN provider='azure' but azure SDK not available
        WHEN creating secrets provider
        THEN should fall back to InMemorySecretsProvider
        """
        with patch.object(
            AzureKeyVaultProvider,
            "__init__",
            side_effect=ImportError("azure SDK not installed"),
        ):
            provider = create_secrets_provider("azure")
            assert isinstance(provider, InMemorySecretsProvider)

    def test_creates_azure_provider_fallback_on_value_error(self) -> None:
        """GIVEN provider='azure' but no vault URL
        WHEN creating secrets provider
        THEN should fall back to InMemorySecretsProvider
        """
        with patch.dict(os.environ, {}, clear=True):
            provider = create_secrets_provider("azure")
            assert isinstance(provider, InMemorySecretsProvider)

    def test_creates_gcp_provider(self) -> None:
        """GIVEN provider='gcp' with project configured
        WHEN creating secrets provider
        THEN should return GCPSecretManagerProvider
        """
        with patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "my-project"}):
            provider = create_secrets_provider("gcp")
            assert isinstance(provider, GCPSecretManagerProvider)

    def test_creates_gcp_provider_fallback_on_import_error(self) -> None:
        """GIVEN provider='gcp' but google SDK not available
        WHEN creating secrets provider
        THEN should fall back to InMemorySecretsProvider
        """
        with patch.object(
            GCPSecretManagerProvider,
            "__init__",
            side_effect=ImportError("google SDK not installed"),
        ):
            provider = create_secrets_provider("gcp")
            assert isinstance(provider, InMemorySecretsProvider)

    def test_creates_gcp_provider_fallback_on_value_error(self) -> None:
        """GIVEN provider='gcp' but no project configured
        WHEN creating secrets provider
        THEN should fall back to InMemorySecretsProvider
        """
        with patch.dict(os.environ, {}, clear=True):
            provider = create_secrets_provider("gcp")
            assert isinstance(provider, InMemorySecretsProvider)

    def test_auto_detects_from_environment(self) -> None:
        """GIVEN no provider specified but AWS env set
        WHEN creating secrets provider
        THEN should auto-detect and return AWS provider
        """
        with patch.dict(
            os.environ,
            {"AWS_EXECUTION_ENV": "test", "SECRETS_PROVIDER": ""},
            clear=True,
        ):
            provider = create_secrets_provider()
            assert isinstance(provider, AWSSecretsManagerProvider)

    def test_respects_secrets_provider_env_var(self) -> None:
        """GIVEN SECRETS_PROVIDER env var set
        WHEN creating secrets provider
        THEN should use specified provider
        """
        with patch.dict(os.environ, {"SECRETS_PROVIDER": "local"}, clear=True):
            provider = create_secrets_provider()
            assert isinstance(provider, InMemorySecretsProvider)


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_core_secrets")
class TestSecretsProviderSingleton:
    """Tests for singleton management functions."""

    def setup_method(self) -> None:
        """Reset singleton before each test."""
        reset_secrets_provider()

    def teardown_method(self) -> None:
        """Reset singleton and force GC after each test."""
        reset_secrets_provider()
        gc.collect()

    def test_get_secrets_provider_creates_instance(self) -> None:
        """GIVEN no existing provider
        WHEN calling get_secrets_provider
        THEN should create and return a provider
        """
        with patch.dict(os.environ, {}, clear=True):
            provider = get_secrets_provider()
            assert provider is not None

    def test_get_secrets_provider_returns_cached_instance(self) -> None:
        """GIVEN provider already created
        WHEN calling get_secrets_provider again
        THEN should return same instance
        """
        with patch.dict(os.environ, {}, clear=True):
            provider1 = get_secrets_provider()
            provider2 = get_secrets_provider()
            assert provider1 is provider2

    def test_set_secrets_provider_overrides_default(self) -> None:
        """GIVEN custom provider
        WHEN calling set_secrets_provider
        THEN get_secrets_provider should return custom provider
        """
        custom_provider = InMemorySecretsProvider()
        set_secrets_provider(custom_provider)

        result = get_secrets_provider()
        assert result is custom_provider

    def test_reset_secrets_provider_clears_singleton(self) -> None:
        """GIVEN existing provider
        WHEN calling reset_secrets_provider
        THEN next get should create new instance
        """
        with patch.dict(os.environ, {}, clear=True):
            provider1 = get_secrets_provider()
            reset_secrets_provider()
            provider2 = get_secrets_provider()
            assert provider1 is not provider2
