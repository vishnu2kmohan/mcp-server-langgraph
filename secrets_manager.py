"""
Infisical integration for secure secrets management
"""
import os
from typing import Dict, Any, Optional
from infisical_client import InfisicalClient, ClientSettings, AuthenticationOptions, UniversalAuthMethod
from observability import tracer, logger


class SecretsManager:
    """
    Infisical-based secrets manager

    Provides secure retrieval and caching of secrets with automatic rotation support.
    """

    def __init__(
        self,
        site_url: str = "https://app.infisical.com",
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        project_id: Optional[str] = None,
        environment: str = "dev"
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
        self._cache: Dict[str, Any] = {}

        # Use environment variables if not provided
        client_id = client_id or os.getenv("INFISICAL_CLIENT_ID")
        client_secret = client_secret or os.getenv("INFISICAL_CLIENT_SECRET")

        if not client_id or not client_secret:
            logger.warning(
                "Infisical credentials not provided, using fallback mode"
            )
            self.client = None
            return

        # Configure Infisical client
        try:
            self.client = InfisicalClient(ClientSettings(
                site_url=site_url,
                auth=AuthenticationOptions(
                    universal_auth=UniversalAuthMethod(
                        client_id=client_id,
                        client_secret=client_secret
                    )
                )
            ))

            logger.info(
                "Infisical secrets manager initialized",
                extra={
                    "site_url": site_url,
                    "environment": environment
                }
            )
        except Exception as e:
            logger.error(
                f"Failed to initialize Infisical client: {e}",
                exc_info=True
            )
            self.client = None

    def get_secret(
        self,
        key: str,
        path: str = "/",
        use_cache: bool = True,
        fallback: Optional[str] = None
    ) -> Optional[str]:
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
        with tracer.start_as_current_span("secrets.get_secret") as span:
            span.set_attribute("secret.key", key)
            span.set_attribute("secret.path", path)

            cache_key = f"{path}:{key}"

            # Check cache first
            if use_cache and cache_key in self._cache:
                logger.debug(
                    "Secret retrieved from cache",
                    extra={"key": key}
                )
                return self._cache[cache_key]

            # Fallback if client not initialized
            if not self.client:
                logger.warning(
                    f"Infisical client not available, using fallback for {key}"
                )
                # Try environment variable first
                env_value = os.getenv(key)
                if env_value:
                    return env_value
                return fallback

            try:
                secret = self.client.get_secret(
                    secret_name=key,
                    project_id=self.project_id,
                    environment=self.environment,
                    path=path
                )

                value = secret.secret_value

                # Cache the value
                if use_cache:
                    self._cache[cache_key] = value

                logger.info(
                    "Secret retrieved from Infisical",
                    extra={
                        "key": key,
                        "path": path
                    }
                )

                span.set_attribute("secret.found", True)
                return value

            except Exception as e:
                logger.error(
                    f"Failed to retrieve secret '{key}': {e}",
                    extra={"key": key, "path": path},
                    exc_info=True
                )
                span.record_exception(e)
                span.set_attribute("secret.found", False)

                # Try environment variable fallback
                env_value = os.getenv(key)
                if env_value:
                    logger.info(f"Using environment variable fallback for {key}")
                    return env_value

                return fallback

    def get_all_secrets(
        self,
        path: str = "/",
        use_cache: bool = True
    ) -> Dict[str, str]:
        """
        Get all secrets from a path

        Args:
            path: Secret path
            use_cache: Whether to use cached values

        Returns:
            Dictionary of all secrets
        """
        with tracer.start_as_current_span("secrets.get_all_secrets"):
            if not self.client:
                logger.warning("Infisical client not available")
                return {}

            try:
                secrets = self.client.list_secrets(
                    project_id=self.project_id,
                    environment=self.environment,
                    path=path
                )

                result = {
                    secret.secret_key: secret.secret_value
                    for secret in secrets
                }

                # Cache all secrets
                if use_cache:
                    for key, value in result.items():
                        cache_key = f"{path}:{key}"
                        self._cache[cache_key] = value

                logger.info(
                    "Retrieved all secrets from path",
                    extra={
                        "path": path,
                        "count": len(result)
                    }
                )

                return result

            except Exception as e:
                logger.error(
                    f"Failed to retrieve secrets from path '{path}': {e}",
                    exc_info=True
                )
                return {}

    def create_secret(
        self,
        key: str,
        value: str,
        path: str = "/",
        secret_comment: Optional[str] = None
    ) -> bool:
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
        with tracer.start_as_current_span("secrets.create_secret"):
            if not self.client:
                logger.error("Infisical client not available")
                return False

            try:
                self.client.create_secret(
                    secret_name=key,
                    secret_value=value,
                    project_id=self.project_id,
                    environment=self.environment,
                    path=path,
                    secret_comment=secret_comment
                )

                # Update cache
                cache_key = f"{path}:{key}"
                self._cache[cache_key] = value

                logger.info(
                    "Secret created in Infisical",
                    extra={"key": key, "path": path}
                )

                return True

            except Exception as e:
                logger.error(
                    f"Failed to create secret '{key}': {e}",
                    exc_info=True
                )
                return False

    def update_secret(
        self,
        key: str,
        value: str,
        path: str = "/"
    ) -> bool:
        """
        Update an existing secret

        Args:
            key: Secret key name
            value: New secret value
            path: Secret path

        Returns:
            True if successful
        """
        with tracer.start_as_current_span("secrets.update_secret"):
            if not self.client:
                logger.error("Infisical client not available")
                return False

            try:
                self.client.update_secret(
                    secret_name=key,
                    secret_value=value,
                    project_id=self.project_id,
                    environment=self.environment,
                    path=path
                )

                # Update cache
                cache_key = f"{path}:{key}"
                self._cache[cache_key] = value

                logger.info(
                    "Secret updated in Infisical",
                    extra={"key": key, "path": path}
                )

                return True

            except Exception as e:
                logger.error(
                    f"Failed to update secret '{key}': {e}",
                    exc_info=True
                )
                return False

    def delete_secret(
        self,
        key: str,
        path: str = "/"
    ) -> bool:
        """
        Delete a secret

        Args:
            key: Secret key name
            path: Secret path

        Returns:
            True if successful
        """
        with tracer.start_as_current_span("secrets.delete_secret"):
            if not self.client:
                logger.error("Infisical client not available")
                return False

            try:
                self.client.delete_secret(
                    secret_name=key,
                    project_id=self.project_id,
                    environment=self.environment,
                    path=path
                )

                # Remove from cache
                cache_key = f"{path}:{key}"
                self._cache.pop(cache_key, None)

                logger.info(
                    "Secret deleted from Infisical",
                    extra={"key": key, "path": path}
                )

                return True

            except Exception as e:
                logger.error(
                    f"Failed to delete secret '{key}': {e}",
                    exc_info=True
                )
                return False

    def invalidate_cache(self, key: Optional[str] = None):
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
            logger.info(f"Cache invalidated for secret: {key}")
        else:
            self._cache.clear()
            logger.info("All secret cache invalidated")


# Singleton instance
_secrets_manager: Optional[SecretsManager] = None


def get_secrets_manager() -> SecretsManager:
    """Get or create the global secrets manager instance"""
    global _secrets_manager

    if _secrets_manager is None:
        _secrets_manager = SecretsManager(
            site_url=os.getenv("INFISICAL_SITE_URL", "https://app.infisical.com"),
            environment=os.getenv("ENVIRONMENT", "dev")
        )

    return _secrets_manager
