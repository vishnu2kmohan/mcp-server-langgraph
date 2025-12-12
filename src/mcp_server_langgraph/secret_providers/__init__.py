"""
Secrets Management Package

Provides a pluggable secrets management abstraction supporting multiple backends:
- Environment variables (default fallback)
- OpenBao/HashiCorp Vault
- AWS Secrets Manager
- GCP Secret Manager
- Azure Key Vault
"""

from .aws import AWSSecretsProvider
from .azure import AzureKeyVaultProvider
from .base import SecretNotFoundError, SecretsProvider, SecretsProviderError
from .environment import EnvironmentProvider
from .factory import get_secrets_provider
from .gcp import GCPSecretsProvider
from .openbao import OpenBaoProvider

__all__ = [
    # Base classes and exceptions
    "SecretsProvider",
    "SecretsProviderError",
    "SecretNotFoundError",
    # Providers
    "EnvironmentProvider",
    "OpenBaoProvider",
    "AWSSecretsProvider",
    "GCPSecretsProvider",
    "AzureKeyVaultProvider",
    # Factory
    "get_secrets_provider",
]
