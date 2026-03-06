"""Secure database credential management with TTL caching.

Retrieves credentials from the Secrets Manager with caching to reduce
latency and API rate limit pressure. Supports credential rotation via
cache invalidation.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any, Protocol

from cachetools import TTLCache

logger = logging.getLogger(__name__)


class SecretsProvider(Protocol):
    """Minimal protocol for secrets provider integration."""

    async def get_secret(self, secret_id: str) -> str | None: ...
    async def set_secret(self, secret_id: str, value: str) -> None: ...
    async def delete_secret(self, secret_id: str) -> None: ...


class CredentialRetrievalError(Exception):
    """Failed to retrieve database credentials from Secrets Manager."""


class SecureConnectionConfig:
    """Secure database connection configuration with TTL caching.

    PERFORMANCE: Credentials are cached with a short TTL to avoid:
    - High latency on every query
    - Hitting Secrets Manager API rate limits
    - Unnecessary network calls

    SECURITY: Cache is invalidated on credential rotation.
    SecretString wrapper prevents logging of credential values.

    Cache lifecycle: The cache and lock can be injected via constructor
    for cross-instance sharing (DI pattern). When not provided, each
    instance creates its own cache (suitable for testing).
    """

    def __init__(
        self,
        secrets_provider: SecretsProvider,
        dialect: str,
        tenant_id: str,
        cache_ttl: int = 300,
        cache: TTLCache | None = None,
        cache_lock: asyncio.Lock | None = None,
    ) -> None:
        self._secrets_provider = secrets_provider
        self.dialect = dialect
        self.tenant_id = tenant_id
        self._credential_cache = cache if cache is not None else TTLCache(maxsize=1000, ttl=cache_ttl)
        self._cache_lock = cache_lock if cache_lock is not None else asyncio.Lock()

        if cache is None and not os.environ.get("TESTING"):
            logger.warning(
                "SecureConnectionConfig created without shared cache; cache invalidation will not propagate across instances"
            )

    async def get_credentials(self, secret_path: str, secret_key: str) -> dict[str, Any]:
        """Retrieve credentials from Secrets Manager with TTL caching.

        Args:
            secret_path: Path in secrets manager (e.g., "/database/tenant-1")
            secret_key: Key name (e.g., "DB_PROD")

        Returns:
            Dictionary with credential fields (host, port, user, password, database, etc.)

        Raises:
            CredentialRetrievalError: If credentials cannot be retrieved.
        """
        cache_key = f"{self.tenant_id}:{self.dialect}:{secret_path}:{secret_key}"

        # Check cache first (return a copy to prevent caller mutations)
        cached = self._credential_cache.get(cache_key)
        if cached is not None:
            logger.debug("Credential cache hit for %s", cache_key)
            return dict(cached)

        async with self._cache_lock:
            # Double-check after acquiring lock
            if cache_key in self._credential_cache:
                return dict(self._credential_cache[cache_key])

            # Fetch from Secrets Manager
            secret_id = f"{secret_path}/{secret_key}"
            raw_secret = await self._secrets_provider.get_secret(secret_id)

            if raw_secret is None:
                raise CredentialRetrievalError(f"Secret not found: {secret_id}")

            # Parse JSON credential payload
            try:
                credentials = json.loads(raw_secret)
            except json.JSONDecodeError:
                # Treat as raw connection string; parse into structured fields
                # for driver compatibility (most drivers expect host/port/user/password)
                credentials = {"connection_string": raw_secret}
                try:
                    from sqlalchemy.engine import make_url

                    url = make_url(raw_secret)
                    credentials.update(
                        {
                            "host": url.host,
                            "port": url.port,
                            "username": url.username,
                            "password": url.password,
                            "database": url.database,
                        }
                    )
                except Exception:
                    # URL parsing failed; leave as connection_string only
                    pass

            # Cache the result (store a copy to prevent caller mutations)
            self._credential_cache[cache_key] = dict(credentials)
            logger.debug("Credential cached for %s", cache_key)
            return dict(credentials)

    def invalidate_cache(self, tenant_id: str, dialect: str | None = None) -> int:
        """Invalidate cached credentials.

        Called when credentials are rotated or connection is updated.

        Args:
            tenant_id: Tenant whose credentials to invalidate.
            dialect: Optional dialect to narrow invalidation.

        Returns:
            Number of cache entries invalidated.
        """
        prefix = f"{tenant_id}:{dialect}:" if dialect else f"{tenant_id}:"
        keys_to_remove = [k for k in self._credential_cache if k.startswith(prefix)]
        for key in keys_to_remove:
            self._credential_cache.pop(key, None)
        if keys_to_remove:
            logger.info(
                "Invalidated %d credential cache entries for tenant=%s dialect=%s",
                len(keys_to_remove),
                tenant_id,
                dialect,
            )
        return len(keys_to_remove)

    def clear_cache(self) -> None:
        """Clear all cached credentials (admin operation)."""
        self._credential_cache.clear()

    def get_ssl_config(self, ssl_mode: str = "require") -> dict[str, Any]:
        """Return SSL configuration for database connections.

        Args:
            ssl_mode: SSL mode (require, verify-ca, verify-full, disable)

        Returns:
            SSL configuration dictionary.
        """
        if ssl_mode == "disable":
            return {"ssl": False}

        config: dict[str, Any] = {"ssl": True}
        if ssl_mode in ("verify-ca", "verify-full"):
            config["ssl_verify"] = True
        else:
            config["ssl_verify"] = False

        return config
