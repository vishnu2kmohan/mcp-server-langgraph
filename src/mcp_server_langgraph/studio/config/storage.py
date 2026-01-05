"""StudioConfigStorage for storing STUDIO.md configurations.

Provides storage and retrieval of parsed STUDIO.md configurations:
- In-memory storage for development/testing
- Cache integration for performance
- Hash-based change detection

In production, this can be extended to use PostgreSQL and Redis.

ADR Reference: adr/adr-0092-hierarchical-capability-architecture.md
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Any, Protocol


class StorageCacheProtocol(Protocol):
    """Protocol for storage cache implementations."""

    async def get(self, key: str) -> Any | None:
        """Get a value from cache."""
        ...

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set a value in cache."""
        ...

    async def invalidate(self, key: str) -> None:
        """Invalidate a cache key."""
        ...


@dataclass
class StoredStudioConfig:
    """A stored STUDIO.md configuration.

    Attributes:
        id: Unique identifier for the stored config
        scope: Capability scope level
        scope_id: Identifier for the scope (org_id, project_id, etc.)
        config: The parsed configuration as a dictionary
        config_hash: SHA-256 hash of the config for change detection
        created_at: When the config was first stored
        updated_at: When the config was last updated
    """

    id: str
    scope: str
    scope_id: str | None
    config: dict[str, Any]
    config_hash: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class StudioConfigStorage:
    """Storage for STUDIO.md configurations.

    Provides CRUD operations for stored configurations with
    optional caching support.

    This implementation uses in-memory storage suitable for
    development and testing. In production, this would be
    backed by PostgreSQL with Redis caching.

    Attributes:
        cache: Optional cache implementation for faster lookups
    """

    def __init__(
        self,
        cache: StorageCacheProtocol | None = None,
    ) -> None:
        """Initialize the StudioConfigStorage.

        Args:
            cache: Optional cache implementation
        """
        self._cache = cache
        # In-memory storage for development/testing
        # Key: (scope, scope_id)
        self._storage: dict[tuple[str, str | None], StoredStudioConfig] = {}

    def _make_cache_key(self, scope: str, scope_id: str | None) -> str:
        """Create a cache key from scope and scope_id.

        Args:
            scope: The capability scope
            scope_id: The scope identifier

        Returns:
            Cache key string
        """
        return f"studio_config:{scope}:{scope_id or 'default'}"

    def compute_hash(self, config: dict[str, Any]) -> str:
        """Compute SHA-256 hash of a configuration.

        Args:
            config: The configuration dictionary

        Returns:
            Hex-encoded SHA-256 hash
        """
        # Sort keys for deterministic serialization
        config_str = json.dumps(config, sort_keys=True, default=str)
        return hashlib.sha256(config_str.encode()).hexdigest()

    async def get(
        self,
        scope: str,
        scope_id: str | None = None,
    ) -> StoredStudioConfig | None:
        """Get a stored configuration by scope.

        Checks cache first if available, then falls back to storage.

        Args:
            scope: The capability scope
            scope_id: The scope identifier

        Returns:
            StoredStudioConfig if found, None otherwise
        """
        cache_key = self._make_cache_key(scope, scope_id)

        # Check cache first
        if self._cache is not None:
            cached = await self._cache.get(cache_key)
            if isinstance(cached, StoredStudioConfig):
                result: StoredStudioConfig = cached
                return result

        # Check in-memory storage
        key = (scope, scope_id)
        config = self._storage.get(key)

        # Update cache if found
        if config is not None and self._cache is not None:
            await self._cache.set(cache_key, config)

        return config

    async def save(
        self,
        config: StoredStudioConfig,
    ) -> None:
        """Save a configuration.

        Overwrites any existing config with the same scope/scope_id.
        Updates the cache if available.

        Args:
            config: The configuration to save
        """
        key = (config.scope, config.scope_id)

        # Update timestamps
        now = datetime.now(UTC)
        if config.created_at is None:
            # Check if we're updating an existing config
            existing = self._storage.get(key)
            if existing is not None and existing.created_at is not None:
                config = StoredStudioConfig(
                    id=config.id,
                    scope=config.scope,
                    scope_id=config.scope_id,
                    config=config.config,
                    config_hash=config.config_hash,
                    created_at=existing.created_at,
                    updated_at=now,
                )
            else:
                config = StoredStudioConfig(
                    id=config.id,
                    scope=config.scope,
                    scope_id=config.scope_id,
                    config=config.config,
                    config_hash=config.config_hash,
                    created_at=now,
                    updated_at=now,
                )

        # Store in memory
        self._storage[key] = config

        # Update cache
        if self._cache is not None:
            cache_key = self._make_cache_key(config.scope, config.scope_id)
            await self._cache.set(cache_key, config)

    async def delete(
        self,
        scope: str,
        scope_id: str | None = None,
    ) -> None:
        """Delete a configuration.

        Removes from both storage and cache.

        Args:
            scope: The capability scope
            scope_id: The scope identifier
        """
        key = (scope, scope_id)

        # Remove from storage
        if key in self._storage:
            del self._storage[key]

        # Invalidate cache
        if self._cache is not None:
            cache_key = self._make_cache_key(scope, scope_id)
            await self._cache.invalidate(cache_key)

    async def list_by_scope(
        self,
        scope: str,
    ) -> list[StoredStudioConfig]:
        """List all configurations for a scope.

        Args:
            scope: The capability scope

        Returns:
            List of stored configurations
        """
        return [config for (stored_scope, _), config in self._storage.items() if stored_scope == scope]

    async def has_changed(
        self,
        scope: str,
        scope_id: str | None,
        new_config: dict[str, Any],
    ) -> bool:
        """Check if a configuration has changed.

        Compares hash of new config with stored hash.

        Args:
            scope: The capability scope
            scope_id: The scope identifier
            new_config: The new configuration to compare

        Returns:
            True if config has changed, False otherwise
        """
        existing = await self.get(scope, scope_id)
        if existing is None:
            return True

        new_hash = self.compute_hash(new_config)
        return existing.config_hash != new_hash
