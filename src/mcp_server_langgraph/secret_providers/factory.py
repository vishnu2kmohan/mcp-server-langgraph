"""
Secrets Provider Factory

Factory function for creating the appropriate secrets provider
based on configuration.
"""

import os

from .base import SecretsProvider

# Cache for the provider singleton
_provider_cache: SecretsProvider | None = None


def get_secrets_provider() -> SecretsProvider:
    """Get the configured secrets provider.

    The provider is determined by the SECRETS_PROVIDER environment variable:
    - "openbao" or "vault": OpenBao/HashiCorp Vault
    - "aws": AWS Secrets Manager
    - "gcp": Google Cloud Secret Manager
    - "azure": Azure Key Vault
    - "environment" or not set: Environment variables (default)

    Returns:
        The configured SecretsProvider instance

    Raises:
        ValueError: If an unknown provider is specified

    Example:
        provider = get_secrets_provider()
        value = await provider.get_secret("my-secret")
    """
    global _provider_cache

    if _provider_cache is not None:
        return _provider_cache

    provider_type = os.environ.get("SECRETS_PROVIDER", "environment").lower()

    if provider_type in ("environment", "env", ""):
        from .environment import EnvironmentProvider

        _provider_cache = EnvironmentProvider()

    elif provider_type in ("openbao", "vault", "hashicorp"):
        from .openbao import OpenBaoProvider

        _provider_cache = OpenBaoProvider()

    elif provider_type == "aws":
        from .aws import AWSSecretsProvider

        _provider_cache = AWSSecretsProvider()

    elif provider_type == "gcp":
        from .gcp import GCPSecretsProvider

        _provider_cache = GCPSecretsProvider()

    elif provider_type == "azure":
        from .azure import AzureKeyVaultProvider

        _provider_cache = AzureKeyVaultProvider()

    else:
        raise ValueError(
            f"Unknown secrets provider: {provider_type}. Valid options: environment, openbao, vault, aws, gcp, azure"
        )

    return _provider_cache


def _clear_provider_cache() -> None:
    """Clear the provider cache (for testing purposes)."""
    global _provider_cache
    _provider_cache = None
