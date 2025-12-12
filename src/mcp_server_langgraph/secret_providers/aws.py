"""
AWS Secrets Manager Provider

Provides secrets from AWS Secrets Manager.
"""

import os

from .base import SecretNotFoundError, SecretsProvider, SecretsProviderError


class AWSSecretsProvider(SecretsProvider):
    """Secrets provider for AWS Secrets Manager.

    Uses boto3 to interact with AWS Secrets Manager.

    Example:
        provider = AWSSecretsProvider(region_name="us-east-1")
        value = await provider.get_secret("prod/database/password")
    """

    def __init__(
        self,
        region_name: str | None = None,
        profile_name: str | None = None,
    ) -> None:
        """Initialize the AWS Secrets Manager provider.

        Args:
            region_name: AWS region. Defaults to AWS_DEFAULT_REGION env var
            profile_name: AWS profile name. Defaults to AWS_PROFILE env var
        """
        self._region = region_name or os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
        self._profile = profile_name or os.environ.get("AWS_PROFILE")
        self._client: object | None = None

    def _get_client(self) -> object:
        """Get or create the boto3 Secrets Manager client.

        Returns:
            Configured boto3 client

        Raises:
            SecretsProviderError: If boto3 is not installed
        """
        if self._client is None:
            try:
                import boto3

                session_kwargs = {"region_name": self._region}
                if self._profile:
                    session_kwargs["profile_name"] = self._profile

                session = boto3.Session(**session_kwargs)
                self._client = session.client("secretsmanager")
            except ImportError:
                raise SecretsProviderError(
                    "boto3 package is required for AWS Secrets Manager. Install with: pip install boto3"
                )

        return self._client

    async def get_secret(self, name: str) -> str:
        """Get a secret from AWS Secrets Manager.

        Args:
            name: The secret name or ARN

        Returns:
            The secret value

        Raises:
            SecretNotFoundError: If the secret doesn't exist
            SecretsProviderError: For other errors
        """
        try:
            client = self._get_client()
            response = client.get_secret_value(SecretId=name)
            return response.get("SecretString", "")
        except Exception as e:
            error_str = str(e)
            if "ResourceNotFoundException" in error_str:
                raise SecretNotFoundError(name)
            raise SecretsProviderError(f"Failed to get secret {name}: {e}") from e

    async def set_secret(self, name: str, value: str) -> None:
        """Set or update a secret in AWS Secrets Manager.

        Args:
            name: The secret name
            value: The secret value

        Raises:
            SecretsProviderError: If the operation fails
        """
        try:
            client = self._get_client()
            try:
                client.put_secret_value(SecretId=name, SecretString=value)
            except Exception:
                # Secret might not exist, create it
                client.create_secret(Name=name, SecretString=value)
        except Exception as e:
            raise SecretsProviderError(f"Failed to set secret {name}: {e}") from e

    async def delete_secret(self, name: str) -> None:
        """Delete a secret from AWS Secrets Manager.

        Args:
            name: The secret name to delete

        Raises:
            SecretNotFoundError: If the secret doesn't exist
            SecretsProviderError: For other errors
        """
        try:
            client = self._get_client()
            client.delete_secret(SecretId=name, ForceDeleteWithoutRecovery=True)
        except Exception as e:
            if "ResourceNotFoundException" in str(e):
                raise SecretNotFoundError(name)
            raise SecretsProviderError(f"Failed to delete secret {name}: {e}") from e

    async def list_secrets(self, prefix: str | None = None) -> list[str]:
        """List secrets in AWS Secrets Manager.

        Args:
            prefix: Optional name prefix to filter secrets

        Returns:
            List of secret names

        Raises:
            SecretsProviderError: If the operation fails
        """
        try:
            client = self._get_client()
            paginator = client.get_paginator("list_secrets")
            secrets = []

            for page in paginator.paginate():
                for secret in page.get("SecretList", []):
                    name = secret.get("Name", "")
                    if prefix is None or name.startswith(prefix):
                        secrets.append(name)

            return secrets
        except Exception as e:
            raise SecretsProviderError(f"Failed to list secrets: {e}") from e

    async def is_available(self) -> bool:
        """Check if AWS Secrets Manager is available.

        Returns:
            True if AWS Secrets Manager is reachable
        """
        try:
            client = self._get_client()
            client.list_secrets(MaxResults=1)
            return True
        except Exception:
            return False
