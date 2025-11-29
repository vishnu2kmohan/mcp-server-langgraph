"""
Infisical integration for secure secrets management
"""

import hashlib
import logging
import os
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from opentelemetry.trace import Tracer

# Conditional import - infisical-python is an optional dependency
try:
    from infisical_client import AuthenticationOptions, ClientSettings, InfisicalClient, UniversalAuthMethod

    INFISICAL_AVAILABLE = True
except ImportError:
    INFISICAL_AVAILABLE = False

# Use standard library logging until observability is initialized
# This breaks the circular import: config -> secrets.manager -> telemetry -> config
_stdlib_logger = logging.getLogger(__name__)


def _get_logger() -> logging.Logger:
    """
    Get logger instance, preferring observability logger if initialized.

    This allows secrets manager to work before observability initialization.
    """
    try:
        from mcp_server_langgraph.observability.telemetry import get_logger, is_initialized

        if is_initialized():
            return get_logger()  # type: ignore[no-any-return]
    except (ImportError, RuntimeError):
        pass
    return _stdlib_logger


def _get_tracer() -> Optional["Tracer"]:
    """
    Get tracer instance if observability is initialized, otherwise return None.
    """
    try:
        from mcp_server_langgraph.observability.telemetry import get_tracer, is_initialized

        if is_initialized():
            return get_tracer()  # type: ignore[no-any-return]
    except (ImportError, RuntimeError):
        pass
    return None


# Log warning if infisical not available
if not INFISICAL_AVAILABLE:
    _stdlib_logger.warning(
        "infisical-python not installed - secrets will fall back to environment variables. "
        "Install with: pip install 'mcp-server-langgraph[secrets]'"
    )


class SecretsManager:
    """
    Infisical-based secrets manager

    Provides secure retrieval and caching of secrets with automatic rotation support.
    """

    def __init__(
        self,
        site_url: str = "https://app.infisical.com",
        client_id: str | None = None,
        client_secret: str | None = None,
        project_id: str | None = None,
        environment: str = "dev",
    ):
        """
        Initialize Infisical secrets manager

        Args:
            site_url: Infisical server URL
            client_id: Universal auth client ID
            client_secret: Universal auth client secret
            project_id: Project ID
            environment: Environment slug (dev, staging, prod)
        """
        self.site_url = site_url
        self.project_id = project_id or os.getenv("INFISICAL_PROJECT_ID")
        self.environment = environment
        self._cache: dict[str, Any] = {}

        # Use environment variables if not provided
        client_id = client_id or os.getenv("INFISICAL_CLIENT_ID")
        client_secret = client_secret or os.getenv("INFISICAL_CLIENT_SECRET")

        # Check if infisical-python is available
        if not INFISICAL_AVAILABLE:
            _get_logger().warning("infisical-python not installed, using fallback mode (environment variables)")
            self.client = None
            return

        if not client_id or not client_secret:
            _get_logger().warning("Infisical credentials not provided, using fallback mode")
            self.client = None
            return

        # Configure Infisical client
        try:
            self.client = InfisicalClient(
                ClientSettings(
                    site_url=site_url,
                    auth=AuthenticationOptions(
                        universal_auth=UniversalAuthMethod(client_id=client_id, client_secret=client_secret)
                    ),
                )
            )

            _get_logger().info(
                "Infisical secrets manager initialized", extra={"site_url": site_url, "environment": environment}
            )
        except Exception as e:
            _get_logger().error(f"Failed to initialize Infisical client: {e}", exc_info=True)
            self.client = None

    def get_secret(self, key: str, path: str = "/", use_cache: bool = True, fallback: str | None = None) -> str | None:
        """
        Get a secret from Infisical

        Args:
            key: Secret key name
            path: Secret path (default: root)
            use_cache: Whether to use cached value
            fallback: Fallback value if secret not found

        Returns:
            Secret value or fallback
        """
        tracer = _get_tracer()
        # Use tracing if available, otherwise proceed without it
        if tracer:
            with tracer.start_as_current_span("secrets.get_secret") as span:
                return self._get_secret_impl(key, path, use_cache, fallback, span)
        else:
            return self._get_secret_impl(key, path, use_cache, fallback, None)

    def _get_secret_impl(self, key: str, path: str, use_cache: bool, fallback: str | None, span: Any) -> str | None:
        """Implementation of get_secret with optional tracing span."""
        if span:
            span.set_attribute("secret.key", key)
            span.set_attribute("secret.path", path)

        cache_key = f"{path}:{key}"

        # Check cache first
        if use_cache and cache_key in self._cache:
            _get_logger().debug("Secret retrieved from cache", extra={"key": key})
            return self._cache[cache_key]  # type: ignore[no-any-return]

        # Fallback if client not initialized
        if not self.client:
            _get_logger().warning(
                "Infisical client not available, using fallback",
                extra={"key_hash": hashlib.sha256(key.encode()).hexdigest()[:8]},
            )
            # Try environment variable first
            env_value = os.getenv(key)
            if env_value:
                return env_value
            return fallback

        try:
            secret = self.client.get_secret(
                secret_name=key, project_id=self.project_id, environment=self.environment, path=path
            )

            value = secret.secret_value

            # Cache the value
            if use_cache:
                self._cache[cache_key] = value

            _get_logger().info("Secret retrieved from Infisical", extra={"key": key, "path": path})

            if span:
                span.set_attribute("secret.found", True)
            return value  # type: ignore[no-any-return]

        except Exception as e:
            _get_logger().error(
                "Failed to retrieve secret",
                extra={"key_hash": hashlib.sha256(key.encode()).hexdigest()[:8], "path": path, "error_type": type(e).__name__},
                exc_info=True,
            )
            if span:
                span.record_exception(e)
                span.set_attribute("secret.found", False)

            # Try environment variable fallback
            env_value = os.getenv(key)
            if env_value:
                _get_logger().info(
                    "Using environment variable fallback", extra={"key_hash": hashlib.sha256(key.encode()).hexdigest()[:8]}
                )
                return env_value

            return fallback

    def get_all_secrets(self, path: str = "/", use_cache: bool = True) -> dict[str, str]:
        """
        Get all secrets from a path

        Args:
            path: Secret path
            use_cache: Whether to use cached values

        Returns:
            Dictionary of all secrets
        """
        tracer = _get_tracer()
        if tracer:
            with tracer.start_as_current_span("secrets.get_all_secrets"):
                return self._get_all_secrets_impl(path, use_cache)
        else:
            return self._get_all_secrets_impl(path, use_cache)

    def _get_all_secrets_impl(self, path: str, use_cache: bool) -> dict[str, str]:
        """Implementation of get_all_secrets."""
        if not self.client:
            _get_logger().warning("Infisical client not available")
            return {}

        try:
            secrets = self.client.list_secrets(project_id=self.project_id, environment=self.environment, path=path)

            result = {secret.secret_key: secret.secret_value for secret in secrets}

            # Cache all secrets
            if use_cache:
                for key, value in result.items():
                    cache_key = f"{path}:{key}"
                    self._cache[cache_key] = value

            _get_logger().info("Retrieved all secrets from path", extra={"path": path, "count": len(result)})

            return result

        except Exception as e:
            _get_logger().error(f"Failed to retrieve secrets from path '{path}': {e}", exc_info=True)
            return {}

    def create_secret(self, key: str, value: str, path: str = "/", secret_comment: str | None = None) -> bool:
        """
        Create a new secret in Infisical

        Args:
            key: Secret key name
            value: Secret value
            path: Secret path
            secret_comment: Optional comment

        Returns:
            True if successful
        """
        if not self.client:
            _get_logger().error("Infisical client not available")
            return False

        try:
            self.client.create_secret(
                secret_name=key,
                secret_value=value,
                project_id=self.project_id,
                environment=self.environment,
                path=path,
                secret_comment=secret_comment,
            )

            # Update cache
            cache_key = f"{path}:{key}"
            self._cache[cache_key] = value

            _get_logger().info("Secret created in Infisical", extra={"key": key, "path": path})

            return True

        except Exception as e:
            _get_logger().error(f"Failed to create secret '{key}': {e}", exc_info=True)
            return False

    def update_secret(self, key: str, value: str, path: str = "/") -> bool:
        """
        Update an existing secret

        Args:
            key: Secret key name
            value: New secret value
            path: Secret path

        Returns:
            True if successful
        """
        if not self.client:
            _get_logger().error("Infisical client not available")
            return False

        try:
            self.client.update_secret(
                secret_name=key, secret_value=value, project_id=self.project_id, environment=self.environment, path=path
            )

            # Update cache
            cache_key = f"{path}:{key}"
            self._cache[cache_key] = value

            _get_logger().info("Secret updated in Infisical", extra={"key": key, "path": path})

            return True

        except Exception as e:
            _get_logger().error(f"Failed to update secret '{key}': {e}", exc_info=True)
            return False

    def delete_secret(self, key: str, path: str = "/") -> bool:
        """
        Delete a secret

        Args:
            key: Secret key name
            path: Secret path

        Returns:
            True if successful
        """
        if not self.client:
            _get_logger().error("Infisical client not available")
            return False

        try:
            self.client.delete_secret(secret_name=key, project_id=self.project_id, environment=self.environment, path=path)

            # Remove from cache
            cache_key = f"{path}:{key}"
            self._cache.pop(cache_key, None)

            _get_logger().info("Secret deleted from Infisical", extra={"key": key, "path": path})

            return True

        except Exception as e:
            _get_logger().error(f"Failed to delete secret '{key}': {e}", exc_info=True)
            return False

    def invalidate_cache(self, key: str | None = None) -> None:
        """
        Invalidate secret cache

        Args:
            key: Specific key to invalidate, or None for all
        """
        if key:
            # Remove all cache entries for this key
            keys_to_remove = [k for k in self._cache.keys() if k.endswith(f":{key}")]
            for k in keys_to_remove:
                self._cache.pop(k, None)
            _get_logger().info(f"Cache invalidated for secret: {key}")
        else:
            self._cache.clear()
            _get_logger().info("All secret cache invalidated")


# Singleton instance
_secrets_manager: SecretsManager | None = None


def get_secrets_manager() -> SecretsManager:
    """Get or create the global secrets manager instance"""
    global _secrets_manager

    if _secrets_manager is None:
        _secrets_manager = SecretsManager(
            site_url=os.getenv("INFISICAL_SITE_URL", "https://app.infisical.com"), environment=os.getenv("ENVIRONMENT", "dev")
        )

    return _secrets_manager
