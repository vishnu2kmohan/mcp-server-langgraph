"""
GCP Secret Manager Provider

Provides secrets from Google Cloud Secret Manager.
"""

import os

from .base import SecretNotFoundError, SecretsProvider, SecretsProviderError


class GCPSecretsProvider(SecretsProvider):
    """Secrets provider for Google Cloud Secret Manager.

    Uses the google-cloud-secret-manager library.

    Example:
        provider = GCPSecretsProvider(project_id="my-project")
        value = await provider.get_secret("database-password")
    """

    def __init__(
        self,
        project_id: str | None = None,
    ) -> None:
        """Initialize the GCP Secret Manager provider.

        Args:
            project_id: GCP project ID. Defaults to GOOGLE_CLOUD_PROJECT env var
        """
        self._project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT", "")
        self._client: object | None = None

    def _get_client(self) -> object:
        """Get or create the Secret Manager client.

        Returns:
            Configured SecretManagerServiceClient

        Raises:
            SecretsProviderError: If the package is not installed
        """
        if self._client is None:
            try:
                from google.cloud import secretmanager

                self._client = secretmanager.SecretManagerServiceClient()
            except ImportError:
                raise SecretsProviderError(
                    "google-cloud-secret-manager package is required for GCP. "
                    "Install with: pip install google-cloud-secret-manager"
                )

        return self._client

    def _get_secret_path(self, name: str, version: str = "latest") -> str:
        """Build the full secret path.

        Args:
            name: The secret name
            version: The secret version (default: "latest")

        Returns:
            Full secret path in GCP format
        """
        return f"projects/{self._project_id}/secrets/{name}/versions/{version}"

    async def get_secret(self, name: str) -> str:
        """Get a secret from GCP Secret Manager.

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
            response = client.access_secret_version(request={"name": self._get_secret_path(name)})
            return response.payload.data.decode("UTF-8")
        except Exception as e:
            error_str = str(e)
            if "NOT_FOUND" in error_str or "404" in error_str:
                raise SecretNotFoundError(name)
            raise SecretsProviderError(f"Failed to get secret {name}: {e}") from e

    async def set_secret(self, name: str, value: str) -> None:
        """Set or update a secret in GCP Secret Manager.

        Args:
            name: The secret name
            value: The secret value

        Raises:
            SecretsProviderError: If the operation fails
        """
        try:
            client = self._get_client()
            parent = f"projects/{self._project_id}"

            # Try to create the secret first
            try:
                client.create_secret(
                    request={
                        "parent": parent,
                        "secret_id": name,
                        "secret": {"replication": {"automatic": {}}},
                    }
                )
            except Exception:
                # Secret might already exist
                pass

            # Add the secret version
            secret_path = f"projects/{self._project_id}/secrets/{name}"
            client.add_secret_version(
                request={
                    "parent": secret_path,
                    "payload": {"data": value.encode("UTF-8")},
                }
            )
        except Exception as e:
            raise SecretsProviderError(f"Failed to set secret {name}: {e}") from e

    async def delete_secret(self, name: str) -> None:
        """Delete a secret from GCP Secret Manager.

        Args:
            name: The secret name to delete

        Raises:
            SecretNotFoundError: If the secret doesn't exist
            SecretsProviderError: For other errors
        """
        try:
            client = self._get_client()
            secret_path = f"projects/{self._project_id}/secrets/{name}"
            client.delete_secret(request={"name": secret_path})
        except Exception as e:
            if "NOT_FOUND" in str(e):
                raise SecretNotFoundError(name)
            raise SecretsProviderError(f"Failed to delete secret {name}: {e}") from e

    async def list_secrets(self, prefix: str | None = None) -> list[str]:
        """List secrets in GCP Secret Manager.

        Args:
            prefix: Optional name prefix to filter secrets

        Returns:
            List of secret names

        Raises:
            SecretsProviderError: If the operation fails
        """
        try:
            client = self._get_client()
            parent = f"projects/{self._project_id}"

            secrets = []
            for secret in client.list_secrets(request={"parent": parent}):
                # Extract just the secret name from the full path
                name = secret.name.split("/")[-1]
                if prefix is None or name.startswith(prefix):
                    secrets.append(name)

            return secrets
        except Exception as e:
            raise SecretsProviderError(f"Failed to list secrets: {e}") from e

    async def is_available(self) -> bool:
        """Check if GCP Secret Manager is available.

        Returns:
            True if GCP Secret Manager is reachable
        """
        try:
            client = self._get_client()
            parent = f"projects/{self._project_id}"
            # Try to list secrets (limited to 1)
            list(client.list_secrets(request={"parent": parent, "page_size": 1}))
            return True
        except Exception:
            return False
