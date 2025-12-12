"""
Environment Secrets Provider

Provides secrets from environment variables.
This is the fallback provider when no external secrets manager is configured.
"""

import os

from .base import SecretNotFoundError, SecretsProvider


class EnvironmentProvider(SecretsProvider):
    """Secrets provider that reads from environment variables.

    This provider is always available and serves as the default fallback
    when no external secrets manager is configured.

    Example:
        provider = EnvironmentProvider()
        value = await provider.get_secret("DATABASE_PASSWORD")
    """

    def __init__(self, prefix: str | None = None) -> None:
        """Initialize the environment provider.

        Args:
            prefix: Optional prefix to add to all secret names
        """
        self._prefix = prefix or ""

    def _get_full_name(self, name: str) -> str:
        """Get the full environment variable name with optional prefix."""
        if self._prefix:
            return f"{self._prefix}{name}"
        return name

    async def get_secret(self, name: str) -> str:
        """Get a secret from environment variables.

        Args:
            name: The environment variable name (prefix will be added if configured)

        Returns:
            The environment variable value

        Raises:
            SecretNotFoundError: If the environment variable is not set
        """
        full_name = self._get_full_name(name)
        value = os.environ.get(full_name)

        if value is None:
            raise SecretNotFoundError(name)

        return value

    async def set_secret(self, name: str, value: str) -> None:
        """Set an environment variable.

        Note: This only affects the current process and its children.
        The change is not persistent across process restarts.

        Args:
            name: The environment variable name
            value: The value to set
        """
        full_name = self._get_full_name(name)
        os.environ[full_name] = value

    async def delete_secret(self, name: str) -> None:
        """Delete an environment variable.

        Args:
            name: The environment variable name to delete

        Raises:
            SecretNotFoundError: If the environment variable is not set
        """
        full_name = self._get_full_name(name)

        if full_name not in os.environ:
            raise SecretNotFoundError(name)

        del os.environ[full_name]

    async def list_secrets(self, prefix: str | None = None) -> list[str]:
        """List environment variables matching a prefix.

        Args:
            prefix: Optional prefix to filter environment variable names

        Returns:
            List of environment variable names matching the prefix
        """
        result = []
        search_prefix = prefix or ""

        if self._prefix:
            search_prefix = f"{self._prefix}{search_prefix}"

        for key in os.environ:
            if key.startswith(search_prefix):
                # Remove the provider prefix if present
                if self._prefix and key.startswith(self._prefix):
                    result.append(key[len(self._prefix) :])
                else:
                    result.append(key)

        return result

    async def is_available(self) -> bool:
        """Environment variables are always available.

        Returns:
            Always True
        """
        return True
