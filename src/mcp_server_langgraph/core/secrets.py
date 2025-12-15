"""
Secrets Provider

Provides secure storage for sensitive credentials like API keys and OAuth2 tokens.
Supports multiple backends:
- InMemory: For development/testing (not suitable for production)
- AWS Secrets Manager: For AWS deployments
- Azure Key Vault: For Azure deployments
- GCP Secret Manager: For GCP deployments

Auto-detection selects the appropriate provider based on environment.
"""

import logging
import os
from typing import Any, Protocol, cast

logger = logging.getLogger(__name__)


class SecretsProvider(Protocol):
    """Protocol for secrets provider implementations."""

    async def set_secret(self, secret_id: str, value: str) -> None:
        """Store a secret value."""
        ...

    async def get_secret(self, secret_id: str) -> str | None:
        """Retrieve a secret value."""
        ...

    async def delete_secret(self, secret_id: str) -> None:
        """Delete a secret value."""
        ...


class InMemorySecretsProvider:
    """
    In-memory secrets provider for development/testing.

    WARNING: Not suitable for production use!
    Secrets are stored in memory and lost on restart.
    """

    def __init__(self) -> None:
        """Initialize the in-memory store."""
        self._secrets: dict[str, str] = {}

    async def set_secret(self, secret_id: str, value: str) -> None:
        """Store a secret value."""
        self._secrets[secret_id] = value

    async def get_secret(self, secret_id: str) -> str | None:
        """Retrieve a secret value."""
        return self._secrets.get(secret_id)

    async def delete_secret(self, secret_id: str) -> None:
        """Delete a secret value."""
        self._secrets.pop(secret_id, None)


class AWSSecretsManagerProvider:
    """
    AWS Secrets Manager provider for production AWS deployments.

    Requires:
    - boto3 installed (pip install boto3)
    - AWS credentials configured (IAM role, environment variables, or AWS config)

    Environment variables:
    - AWS_REGION: AWS region for Secrets Manager
    - AWS_SECRETS_PREFIX: Optional prefix for secret names (default: "mcp-server/")
    """

    def __init__(
        self,
        region: str | None = None,
        prefix: str = "mcp-server/",
    ) -> None:
        """
        Initialize AWS Secrets Manager provider.

        Args:
            region: AWS region (defaults to AWS_REGION env var)
            prefix: Prefix for all secret names
        """
        self.region = region or os.getenv("AWS_REGION", "us-east-1")
        self.prefix = prefix
        self._client = None

    def _get_client(self) -> Any:
        """Get or create boto3 Secrets Manager client."""
        if self._client is None:
            import boto3

            self._client = boto3.client("secretsmanager", region_name=self.region)
        return self._client

    def _full_name(self, secret_id: str) -> str:
        """Get full secret name with prefix."""
        return f"{self.prefix}{secret_id}"

    async def set_secret(self, secret_id: str, value: str) -> None:
        """Store a secret in AWS Secrets Manager."""
        import asyncio

        client = self._get_client()
        full_name = self._full_name(secret_id)

        def _set() -> None:
            try:
                client.create_secret(Name=full_name, SecretString=value)
            except client.exceptions.ResourceExistsException:
                client.put_secret_value(SecretId=full_name, SecretString=value)

        await asyncio.get_event_loop().run_in_executor(None, _set)

    async def get_secret(self, secret_id: str) -> str | None:
        """Retrieve a secret from AWS Secrets Manager."""
        import asyncio

        client = self._get_client()
        full_name = self._full_name(secret_id)

        def _get() -> str | None:
            try:
                response = client.get_secret_value(SecretId=full_name)
                return cast(str | None, response.get("SecretString"))
            except client.exceptions.ResourceNotFoundException:
                return None

        return await asyncio.get_event_loop().run_in_executor(None, _get)

    async def delete_secret(self, secret_id: str) -> None:
        """Delete a secret from AWS Secrets Manager."""
        import asyncio

        client = self._get_client()
        full_name = self._full_name(secret_id)

        def _delete() -> None:
            try:
                client.delete_secret(
                    SecretId=full_name,
                    ForceDeleteWithoutRecovery=True,
                )
            except client.exceptions.ResourceNotFoundException:
                pass  # Already deleted

        await asyncio.get_event_loop().run_in_executor(None, _delete)


class AzureKeyVaultProvider:
    """
    Azure Key Vault provider for production Azure deployments.

    Requires:
    - azure-keyvault-secrets and azure-identity installed
    - Azure credentials configured (Managed Identity or environment variables)

    Environment variables:
    - AZURE_KEY_VAULT_URL: Key Vault URL (e.g., https://myvault.vault.azure.net)
    """

    def __init__(
        self,
        vault_url: str | None = None,
    ) -> None:
        """
        Initialize Azure Key Vault provider.

        Args:
            vault_url: Key Vault URL (defaults to AZURE_KEY_VAULT_URL env var)
        """
        self.vault_url = vault_url or os.getenv("AZURE_KEY_VAULT_URL")
        if not self.vault_url:
            raise ValueError("Azure Key Vault URL required. Set AZURE_KEY_VAULT_URL environment variable.")
        self._client = None

    def _get_client(self) -> Any:
        """Get or create Azure Key Vault client."""
        if self._client is None:
            from azure.identity import DefaultAzureCredential
            from azure.keyvault.secrets import SecretClient

            credential = DefaultAzureCredential()
            self._client = SecretClient(vault_url=self.vault_url, credential=credential)
        return self._client

    def _sanitize_name(self, secret_id: str) -> str:
        """Sanitize secret name for Azure Key Vault (only alphanumeric and hyphens)."""
        return secret_id.replace("/", "-").replace("_", "-")

    async def set_secret(self, secret_id: str, value: str) -> None:
        """Store a secret in Azure Key Vault."""
        import asyncio

        client = self._get_client()
        name = self._sanitize_name(secret_id)

        def _set() -> None:
            client.set_secret(name, value)

        await asyncio.get_event_loop().run_in_executor(None, _set)

    async def get_secret(self, secret_id: str) -> str | None:
        """Retrieve a secret from Azure Key Vault."""
        import asyncio

        from azure.core.exceptions import ResourceNotFoundError

        client = self._get_client()
        name = self._sanitize_name(secret_id)

        def _get() -> str | None:
            try:
                secret = client.get_secret(name)
                return cast(str | None, secret.value)
            except ResourceNotFoundError:
                return None

        return await asyncio.get_event_loop().run_in_executor(None, _get)

    async def delete_secret(self, secret_id: str) -> None:
        """Delete a secret from Azure Key Vault."""
        import asyncio

        from azure.core.exceptions import ResourceNotFoundError

        client = self._get_client()
        name = self._sanitize_name(secret_id)

        def _delete() -> None:
            try:
                poller = client.begin_delete_secret(name)
                poller.result()
            except ResourceNotFoundError:
                pass  # Already deleted

        await asyncio.get_event_loop().run_in_executor(None, _delete)


class GCPSecretManagerProvider:
    """
    GCP Secret Manager provider for production GCP deployments.

    Requires:
    - google-cloud-secret-manager installed
    - GCP credentials configured (Workload Identity or service account)

    Environment variables:
    - GOOGLE_CLOUD_PROJECT: GCP project ID
    """

    def __init__(
        self,
        project_id: str | None = None,
    ) -> None:
        """
        Initialize GCP Secret Manager provider.

        Args:
            project_id: GCP project ID (defaults to GOOGLE_CLOUD_PROJECT env var)
        """
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        if not self.project_id:
            raise ValueError("GCP project ID required. Set GOOGLE_CLOUD_PROJECT environment variable.")
        self._client = None

    def _get_client(self) -> Any:
        """Get or create GCP Secret Manager client."""
        if self._client is None:
            from google.cloud import secretmanager

            self._client = secretmanager.SecretManagerServiceClient()
        return self._client

    def _secret_path(self, secret_id: str) -> str:
        """Get full secret path."""
        return f"projects/{self.project_id}/secrets/{secret_id}"

    def _secret_version_path(self, secret_id: str, version: str = "latest") -> str:
        """Get full secret version path."""
        return f"{self._secret_path(secret_id)}/versions/{version}"

    async def set_secret(self, secret_id: str, value: str) -> None:
        """Store a secret in GCP Secret Manager."""
        import asyncio

        from google.api_core.exceptions import AlreadyExists

        client = self._get_client()

        def _set() -> None:
            parent = f"projects/{self.project_id}"
            secret_path = self._secret_path(secret_id)

            # Try to create the secret first
            try:
                client.create_secret(
                    request={
                        "parent": parent,
                        "secret_id": secret_id,
                        "secret": {"replication": {"automatic": {}}},
                    }
                )
            except AlreadyExists:
                pass  # Secret already exists

            # Add a new version with the value
            client.add_secret_version(
                request={
                    "parent": secret_path,
                    "payload": {"data": value.encode("utf-8")},
                }
            )

        await asyncio.get_event_loop().run_in_executor(None, _set)

    async def get_secret(self, secret_id: str) -> str | None:
        """Retrieve a secret from GCP Secret Manager."""
        import asyncio

        from google.api_core.exceptions import NotFound

        client = self._get_client()
        version_path = self._secret_version_path(secret_id)

        def _get() -> str | None:
            try:
                response = client.access_secret_version(request={"name": version_path})
                return cast(str, response.payload.data.decode("utf-8"))
            except NotFound:
                return None

        return await asyncio.get_event_loop().run_in_executor(None, _get)

    async def delete_secret(self, secret_id: str) -> None:
        """Delete a secret from GCP Secret Manager."""
        import asyncio

        from google.api_core.exceptions import NotFound

        client = self._get_client()
        secret_path = self._secret_path(secret_id)

        def _delete() -> None:
            try:
                client.delete_secret(request={"name": secret_path})
            except NotFound:
                pass  # Already deleted

        await asyncio.get_event_loop().run_in_executor(None, _delete)


# ==============================================================================
# Factory and Auto-Detection
# ==============================================================================


def detect_cloud_provider() -> str:
    """
    Detect the current cloud provider based on environment.

    Returns:
        Provider name: "aws", "azure", "gcp", or "local"
    """
    # AWS detection
    if os.getenv("AWS_EXECUTION_ENV") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
        return "aws"
    if os.getenv("AWS_SECRETS_PREFIX"):
        return "aws"

    # Azure detection
    if os.getenv("AZURE_KEY_VAULT_URL"):
        return "azure"
    if os.getenv("WEBSITE_INSTANCE_ID"):  # Azure App Service
        return "azure"

    # GCP detection
    if os.getenv("GOOGLE_CLOUD_PROJECT"):
        return "gcp"
    if os.getenv("K_SERVICE"):  # Cloud Run
        return "gcp"

    return "local"


def create_secrets_provider(provider: str | None = None) -> SecretsProvider:
    """
    Create a secrets provider based on configuration or auto-detection.

    Args:
        provider: Provider name ("aws", "azure", "gcp", "local") or None for auto-detect

    Returns:
        Configured SecretsProvider instance
    """
    if provider is None:
        provider = os.getenv("SECRETS_PROVIDER", "").lower() or detect_cloud_provider()

    if provider == "aws":
        try:
            return AWSSecretsManagerProvider(
                prefix=os.getenv("AWS_SECRETS_PREFIX", "mcp-server/"),
            )
        except ImportError:
            logger.warning("boto3 not installed, falling back to in-memory secrets")
            return InMemorySecretsProvider()

    elif provider == "azure":
        try:
            return AzureKeyVaultProvider()
        except (ImportError, ValueError) as e:
            logger.warning(f"Azure Key Vault not available ({e}), falling back to in-memory secrets")
            return InMemorySecretsProvider()

    elif provider == "gcp":
        try:
            return GCPSecretManagerProvider()
        except (ImportError, ValueError) as e:
            logger.warning(f"GCP Secret Manager not available ({e}), falling back to in-memory secrets")
            return InMemorySecretsProvider()

    else:
        return InMemorySecretsProvider()


# Singleton instance
_secrets_provider: SecretsProvider | None = None


def get_secrets_provider() -> SecretsProvider:
    """
    Get the secrets provider instance.

    Auto-detects the appropriate provider based on environment if not already set.
    """
    global _secrets_provider

    if _secrets_provider is None:
        _secrets_provider = create_secrets_provider()
        provider_name = type(_secrets_provider).__name__
        logger.info(f"Secrets provider initialized: {provider_name}")

    return _secrets_provider


def set_secrets_provider(provider: SecretsProvider) -> None:
    """
    Set a custom secrets provider.

    Use this to inject a production secrets manager.
    """
    global _secrets_provider
    _secrets_provider = provider


def reset_secrets_provider() -> None:
    """Reset the secrets provider (for testing)."""
    global _secrets_provider
    _secrets_provider = None
