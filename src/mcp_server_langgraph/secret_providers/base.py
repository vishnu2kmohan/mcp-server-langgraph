"""
Secrets Provider Base Classes

Abstract base class for secrets providers and common exceptions.
"""

from abc import ABC, abstractmethod


class SecretsProviderError(Exception):
    """Base exception for secrets provider errors."""

    pass


class SecretNotFoundError(SecretsProviderError):
    """Raised when a requested secret is not found."""

    def __init__(self, secret_name: str, message: str | None = None) -> None:
        self.secret_name = secret_name
        if message is None:
            message = f"Secret not found: {secret_name}"
        super().__init__(message)


class SecretsProvider(ABC):
    """Abstract base class for secrets providers.

    All secrets providers must implement these methods to allow
    seamless switching between different secrets backends.
    """

    @abstractmethod
    async def get_secret(self, name: str) -> str:
        """Get a secret value by name.

        Args:
            name: The name/path of the secret

        Returns:
            The secret value as a string

        Raises:
            SecretNotFoundError: If the secret doesn't exist
            SecretsProviderError: For other provider errors
        """
        pass

    @abstractmethod
    async def set_secret(self, name: str, value: str) -> None:
        """Set or update a secret value.

        Args:
            name: The name/path of the secret
            value: The secret value to store

        Raises:
            SecretsProviderError: If the operation fails
        """
        pass

    @abstractmethod
    async def delete_secret(self, name: str) -> None:
        """Delete a secret.

        Args:
            name: The name/path of the secret to delete

        Raises:
            SecretNotFoundError: If the secret doesn't exist
            SecretsProviderError: For other provider errors
        """
        pass

    @abstractmethod
    async def list_secrets(self, prefix: str | None = None) -> list[str]:
        """List available secrets.

        Args:
            prefix: Optional prefix to filter secrets

        Returns:
            List of secret names

        Raises:
            SecretsProviderError: If the operation fails
        """
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the secrets provider is available.

        Returns:
            True if the provider is available and functional
        """
        pass
