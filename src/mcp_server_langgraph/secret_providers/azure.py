"""
Azure Key Vault Provider

Provides secrets from Azure Key Vault.
"""

import os
from typing import Any

from .base import SecretNotFoundError, SecretsProvider, SecretsProviderError


class AzureKeyVaultProvider(SecretsProvider):
    """Secrets provider for Azure Key Vault.

    Uses the azure-keyvault-secrets and azure-identity libraries.

    Example:
        provider = AzureKeyVaultProvider(
            vault_url="https://my-vault.vault.azure.net"
        )
        value = await provider.get_secret("database-password")
    """

    def __init__(
        self,
        vault_url: str | None = None,
    ) -> None:
        """Initialize the Azure Key Vault provider.

        Args:
            vault_url: Key Vault URL. Defaults to AZURE_KEY_VAULT_URL env var
        """
        self._vault_url = vault_url or os.environ.get("AZURE_KEY_VAULT_URL", "")
        self._client: Any = None

    def _get_client(self) -> Any:
        """Get or create the Key Vault client.

        Returns:
            Configured SecretClient

        Raises:
            SecretsProviderError: If required packages are not installed
        """
        if self._client is None:
            try:
                from azure.identity import DefaultAzureCredential
                from azure.keyvault.secrets import SecretClient

                credential = DefaultAzureCredential()
                self._client = SecretClient(vault_url=self._vault_url, credential=credential)
            except ImportError:
                raise SecretsProviderError(
                    "azure-keyvault-secrets and azure-identity packages are required "
                    "for Azure Key Vault. Install with: "
                    "pip install azure-keyvault-secrets azure-identity"
                )

        return self._client

    async def get_secret(self, name: str) -> str:
        """Get a secret from Azure Key Vault.

        Args:
            name: The secret name

        Returns:
            The secret value

        Raises:
            SecretNotFoundError: If the secret doesn't exist
            SecretsProviderError: For other errors
        """
        try:
            client = self._get_client()
            secret = client.get_secret(name)
            return secret.value or ""
        except Exception as e:
            error_str = str(e)
            if "SecretNotFound" in error_str or "404" in error_str:
                raise SecretNotFoundError(name)
            raise SecretsProviderError(f"Failed to get secret {name}: {e}") from e

    async def set_secret(self, name: str, value: str) -> None:
        """Set or update a secret in Azure Key Vault.

        Args:
            name: The secret name
            value: The secret value

        Raises:
            SecretsProviderError: If the operation fails
        """
        try:
            client = self._get_client()
            client.set_secret(name, value)
        except Exception as e:
            raise SecretsProviderError(f"Failed to set secret {name}: {e}") from e

    async def delete_secret(self, name: str) -> None:
        """Delete a secret from Azure Key Vault.

        This performs a soft delete. The secret can be recovered within
        the retention period.

        Args:
            name: The secret name to delete

        Raises:
            SecretNotFoundError: If the secret doesn't exist
            SecretsProviderError: For other errors
        """
        try:
            client = self._get_client()
            poller = client.begin_delete_secret(name)
            poller.wait()
        except Exception as e:
            if "SecretNotFound" in str(e):
                raise SecretNotFoundError(name)
            raise SecretsProviderError(f"Failed to delete secret {name}: {e}") from e

    async def list_secrets(self, prefix: str | None = None) -> list[str]:
        """List secrets in Azure Key Vault.

        Args:
            prefix: Optional name prefix to filter secrets

        Returns:
            List of secret names

        Raises:
            SecretsProviderError: If the operation fails
        """
        try:
            client = self._get_client()
            secrets = []

            for secret_properties in client.list_properties_of_secrets():
                name = secret_properties.name
                if prefix is None or name.startswith(prefix):
                    secrets.append(name)

            return secrets
        except Exception as e:
            raise SecretsProviderError(f"Failed to list secrets: {e}") from e

    async def is_available(self) -> bool:
        """Check if Azure Key Vault is available.

        Returns:
            True if Azure Key Vault is reachable
        """
        try:
            client = self._get_client()
            # Try to list secrets (we'll just start the iteration)
            list(client.list_properties_of_secrets())[:1]
            return True
        except Exception:
            return False
