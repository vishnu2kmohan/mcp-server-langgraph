"""CapabilityCache for TTL-based capability resolution caching.

Provides caching layer for resolved capabilities to optimize
STUDIO.md resolution performance. Supports both in-memory fallback
and Redis backends.

Cache Key Pattern: capability:{scope}:{scope_id}

ADR Reference: adr/adr-0092-hierarchical-capability-architecture.md
"""

from __future__ import annotations

import json
import logging
from typing import Any

from mcp_server_langgraph.core.scopes import CapabilityScope

logger = logging.getLogger(__name__)


class CapabilityCache:
    """TTL-based cache for resolved capabilities.

    Supports both in-memory fallback (when Redis unavailable) and Redis
    backends for production deployments.

    Attributes:
        default_ttl: Default TTL in seconds for cached entries
        redis: Optional Redis client for distributed caching
    """

    DEFAULT_TTL = 300  # 5 minutes

    def __init__(
        self,
        redis: Any | None = None,
        default_ttl: int | None = None,
    ) -> None:
        """Initialize the capability cache.

        Args:
            redis: Optional async Redis client for distributed caching
            default_ttl: Default TTL in seconds (default: 300)
        """
        self.redis = redis
        self.default_ttl = default_ttl if default_ttl is not None else self.DEFAULT_TTL
        # In-memory fallback when Redis not available
        self._memory_cache: dict[str, Any] = {}

    async def get(self, key: str) -> Any | None:
        """Get a cached value by key.

        Tries Redis first if available, falls back to in-memory cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        if self.redis is not None:
            try:
                value = await self.redis.get(key)
                if value is not None:
                    return json.loads(value)
                return None
            except Exception as e:
                logger.warning(f"Redis get failed, falling back to memory: {e}")
                return self._memory_cache.get(key)
        return self._memory_cache.get(key)

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> None:
        """Set a cached value with TTL.

        Uses Redis if available, otherwise stores in memory.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Optional TTL in seconds (uses default_ttl if not specified)
        """
        effective_ttl = ttl if ttl is not None else self.default_ttl

        if self.redis is not None:
            try:
                serialized = json.dumps(value)
                await self.redis.setex(key, effective_ttl, serialized)
                return
            except Exception as e:
                logger.warning(f"Redis set failed, falling back to memory: {e}")

        # In-memory fallback (no TTL enforcement for simplicity)
        self._memory_cache[key] = value

    async def invalidate(self, key: str) -> None:
        """Invalidate (delete) a cached entry.

        Args:
            key: Cache key to invalidate
        """
        if self.redis is not None:
            try:
                await self.redis.delete(key)
            except Exception as e:
                logger.warning(f"Redis delete failed: {e}")

        # Always clear from memory cache too
        self._memory_cache.pop(key, None)

    def make_scope_key(
        self,
        scope: CapabilityScope,
        scope_id: str | None,
    ) -> str:
        """Generate a cache key for a scope.

        Args:
            scope: Capability scope
            scope_id: Optional scope identifier (e.g., project_id)

        Returns:
            Cache key in format: capability:{scope}:{scope_id}
        """
        effective_scope_id = scope_id if scope_id is not None else "_default"
        return f"capability:{scope.value}:{effective_scope_id}"

    async def get_for_scope(
        self,
        scope: CapabilityScope,
        scope_id: str | None,
    ) -> Any | None:
        """Get cached capabilities for a scope.

        Args:
            scope: Capability scope
            scope_id: Optional scope identifier

        Returns:
            Cached capabilities or None
        """
        key = self.make_scope_key(scope, scope_id)
        return await self.get(key)

    async def set_for_scope(
        self,
        scope: CapabilityScope,
        scope_id: str | None,
        capabilities: Any,
        ttl: int | None = None,
    ) -> None:
        """Cache capabilities for a scope.

        Args:
            scope: Capability scope
            scope_id: Optional scope identifier
            capabilities: Capabilities to cache
            ttl: Optional TTL in seconds
        """
        key = self.make_scope_key(scope, scope_id)
        await self.set(key, capabilities, ttl)

    async def invalidate_scope(
        self,
        scope: CapabilityScope,
        scope_id: str | None,
    ) -> None:
        """Invalidate cached capabilities for a scope.

        Args:
            scope: Capability scope
            scope_id: Optional scope identifier
        """
        key = self.make_scope_key(scope, scope_id)
        await self.invalidate(key)
