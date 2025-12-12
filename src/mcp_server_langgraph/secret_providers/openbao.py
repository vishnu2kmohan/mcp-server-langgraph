"""
OpenBao Secrets Provider

Provides secrets from OpenBao (or HashiCorp Vault) using the KV v2 secrets engine.
"""

import os

from .base import SecretNotFoundError, SecretsProvider, SecretsProviderError


class OpenBaoProvider(SecretsProvider):
    """Secrets provider for OpenBao/HashiCorp Vault.

    Uses the KV v2 secrets engine for secret storage and retrieval.

    Example:
        provider = OpenBaoProvider(
            address="https://vault.example.com:8200",
            token="s.my-token"
        )
        value = await provider.get_secret("app/database/password")
    """

    def __init__(
        self,
        address: str | None = None,
        token: str | None = None,
        mount_path: str = "secret",
        namespace: str | None = None,
    ) -> None:
        """Initialize the OpenBao provider.

        Args:
            address: OpenBao server address. Defaults to OPENBAO_ADDR env var
                    or http://localhost:8200
            token: Authentication token. Defaults to OPENBAO_TOKEN env var
            mount_path: KV secrets engine mount path. Defaults to "secret"
            namespace: Optional Vault namespace (Enterprise feature)
        """
        self._address = address or os.environ.get("OPENBAO_ADDR", "http://localhost:8200")
        self._token = token or os.environ.get("OPENBAO_TOKEN", "")
        self._mount_path = mount_path
        self._namespace = namespace
        self._client: object | None = None

    @property
    def address(self) -> str:
        """Get the OpenBao server address."""
        return self._address

    @property
    def mount_path(self) -> str:
        """Get the secrets engine mount path."""
        return self._mount_path

    def _get_client(self) -> object:
        """Get or create the HVAC client.

        Returns:
            Configured HVAC client instance

        Raises:
            SecretsProviderError: If hvac is not installed
        """
        if self._client is None:
            try:
                import hvac

                self._client = hvac.Client(
                    url=self._address,
                    token=self._token,
                    namespace=self._namespace,
                )
            except ImportError:
                raise SecretsProviderError("hvac package is required for OpenBao provider. Install with: pip install hvac")

        return self._client

    async def get_secret(self, name: str) -> str:
        """Get a secret from OpenBao.

        Args:
            name: The secret path (e.g., "app/database/password")

        Returns:
            The secret value

        Raises:
            SecretNotFoundError: If the secret doesn't exist
            SecretsProviderError: For other errors
        """
        try:
            client = self._get_client()
            response = client.secrets.kv.v2.read_secret_version(path=name, mount_point=self._mount_path)

            # Extract value from KV v2 response structure
            data = response.get("data", {}).get("data", {})
            if "value" in data:
                return data["value"]

            # If no "value" key, return the first value
            if data:
                return next(iter(data.values()))

            raise SecretNotFoundError(name)

        except SecretNotFoundError:
            raise
        except Exception as e:
            if "secret not found" in str(e).lower() or "404" in str(e):
                raise SecretNotFoundError(name)
            raise SecretsProviderError(f"Failed to get secret {name}: {e}") from e

    async def set_secret(self, name: str, value: str) -> None:
        """Set or update a secret in OpenBao.

        Args:
            name: The secret path
            value: The secret value to store

        Raises:
            SecretsProviderError: If the operation fails
        """
        try:
            client = self._get_client()
            client.secrets.kv.v2.create_or_update_secret(path=name, secret={"value": value}, mount_point=self._mount_path)
        except Exception as e:
            raise SecretsProviderError(f"Failed to set secret {name}: {e}") from e

    async def delete_secret(self, name: str) -> None:
        """Delete a secret from OpenBao.

        Args:
            name: The secret path to delete

        Raises:
            SecretNotFoundError: If the secret doesn't exist
            SecretsProviderError: For other errors
        """
        try:
            client = self._get_client()
            client.secrets.kv.v2.delete_metadata_and_all_versions(path=name, mount_point=self._mount_path)
        except Exception as e:
            if "secret not found" in str(e).lower() or "404" in str(e):
                raise SecretNotFoundError(name)
            raise SecretsProviderError(f"Failed to delete secret {name}: {e}") from e

    async def list_secrets(self, prefix: str | None = None) -> list[str]:
        """List secrets in OpenBao.

        Args:
            prefix: Optional path prefix to filter secrets

        Returns:
            List of secret paths

        Raises:
            SecretsProviderError: If the operation fails
        """
        try:
            client = self._get_client()
            path = prefix or ""
            response = client.secrets.kv.v2.list_secrets(path=path, mount_point=self._mount_path)

            keys = response.get("data", {}).get("keys", [])
            return keys

        except Exception as e:
            if "404" in str(e):
                return []
            raise SecretsProviderError(f"Failed to list secrets: {e}") from e

    async def is_available(self) -> bool:
        """Check if OpenBao is available.

        Returns:
            True if OpenBao is reachable and initialized
        """
        try:
            client = self._get_client()
            status = client.sys.read_health_status(method="GET")
            return status.get("initialized", False)
        except Exception:
            return False
