"""
Redis Cache Layer for Artifacts Storage.

Implements cache-aside pattern for hot artifacts:
- Cache hit: Return cached artifact without DB query
- Cache miss: Fetch from DB, populate cache
- Write-through: Invalidate cache on updates
- Graceful degradation: Fall back to DB on cache failure

Features:
- User-scoped cache keys (security)
- TTL-based expiration
- Circuit breaker integration (via CacheService)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from mcp_server_langgraph.core.cache import CacheService
    from mcp_server_langgraph.storage.artifacts.postgres_repository import (
        PostgresArtifactsRepository,
    )


logger = logging.getLogger(__name__)

# Default cache TTL for artifacts (5 minutes)
ARTIFACT_CACHE_TTL = 300


def _generate_artifact_cache_key(artifact_id: str, user_id: str) -> str:
    """
    Generate cache key for artifact.

    Security: Include user_id to prevent cross-user cache access.
    Version suffix ensures cache invalidation on schema changes.

    Args:
        artifact_id: Artifact ID
        user_id: User ID

    Returns:
        Cache key string
    """
    return f"artifact:{user_id}:{artifact_id}:v1"


def _generate_versions_cache_key(artifact_id: str, user_id: str) -> str:
    """
    Generate cache key for artifact versions.

    Version suffix ensures cache invalidation on schema changes.

    Args:
        artifact_id: Artifact ID
        user_id: User ID

    Returns:
        Cache key string
    """
    return f"artifact_versions:{user_id}:{artifact_id}:v1"


class RedisCachedArtifactsService:
    """
    Cache layer for artifacts using Redis.

    Wraps PostgresArtifactsRepository with cache-aside pattern.
    All cache operations are non-blocking with graceful degradation.
    """

    def __init__(
        self,
        repository: PostgresArtifactsRepository,
        cache: CacheService,
        ttl: int = ARTIFACT_CACHE_TTL,
    ) -> None:
        """
        Initialize cached service.

        Args:
            repository: PostgreSQL repository for artifacts
            cache: Redis cache service
            ttl: Cache TTL in seconds (default: 5 minutes)
        """
        self._repo = repository
        self._cache = cache
        self._ttl = ttl

    async def get(self, artifact_id: str, user_id: str) -> dict[str, Any] | None:
        """
        Get artifact with cache-aside pattern.

        Args:
            artifact_id: Artifact ID
            user_id: User ID (for ownership check)

        Returns:
            Artifact dict or None if not found
        """
        cache_key = _generate_artifact_cache_key(artifact_id, user_id)

        # Try cache first
        try:
            cached = await self._cache.aget(cache_key)
            if cached is not None:
                logger.debug(
                    "Cache hit for artifact",
                    extra={"artifact_id": artifact_id, "user_id": user_id},
                )
                return cast(dict[str, Any], cached)
        except Exception as e:
            logger.warning(
                "Cache get failed, falling back to DB",
                extra={"artifact_id": artifact_id, "error": str(e)},
            )

        # Cache miss - fetch from DB
        artifact = await self._repo.get(artifact_id, user_id=user_id)

        # Populate cache on miss
        if artifact is not None:
            try:
                await self._cache.aset(cache_key, artifact, ttl=self._ttl)
                logger.debug(
                    "Cached artifact",
                    extra={"artifact_id": artifact_id, "ttl": self._ttl},
                )
            except Exception as e:
                logger.warning(
                    "Cache set failed",
                    extra={"artifact_id": artifact_id, "error": str(e)},
                )

        return artifact

    async def create(self, data: dict[str, Any], user_id: str) -> dict[str, Any]:
        """
        Create artifact (write-through).

        Args:
            data: Artifact data
            user_id: User ID

        Returns:
            Created artifact metadata
        """
        # Write to DB first
        result = await self._repo.create(data, user_id=user_id)

        logger.info(
            "Created artifact",
            extra={"artifact_id": result.get("id"), "user_id": user_id},
        )

        return result

    async def update(self, artifact_id: str, data: dict[str, Any], user_id: str) -> dict[str, Any] | None:
        """
        Update artifact with cache invalidation.

        Args:
            artifact_id: Artifact ID
            data: Update data
            user_id: User ID

        Returns:
            Updated artifact metadata or None
        """
        cache_key = _generate_artifact_cache_key(artifact_id, user_id)
        versions_cache_key = _generate_versions_cache_key(artifact_id, user_id)

        # Invalidate cache first
        try:
            await self._cache.adelete(cache_key)
            await self._cache.adelete(versions_cache_key)
        except Exception as e:
            logger.warning(
                "Cache invalidation failed",
                extra={"artifact_id": artifact_id, "error": str(e)},
            )

        # Update in DB
        result = await self._repo.update(artifact_id, data, user_id=user_id)

        if result is not None:
            logger.info(
                "Updated artifact",
                extra={"artifact_id": artifact_id, "version": result.get("version")},
            )

        return result

    async def delete(self, artifact_id: str, user_id: str) -> bool:
        """
        Delete artifact with cache invalidation.

        Args:
            artifact_id: Artifact ID
            user_id: User ID

        Returns:
            True if deleted, False otherwise
        """
        cache_key = _generate_artifact_cache_key(artifact_id, user_id)
        versions_cache_key = _generate_versions_cache_key(artifact_id, user_id)

        # Invalidate cache
        try:
            await self._cache.adelete(cache_key)
            await self._cache.adelete(versions_cache_key)
        except Exception as e:
            logger.warning(
                "Cache invalidation failed on delete",
                extra={"artifact_id": artifact_id, "error": str(e)},
            )

        # Delete from DB
        result = await self._repo.delete(artifact_id, user_id=user_id)

        if result:
            logger.info(
                "Deleted artifact",
                extra={"artifact_id": artifact_id, "user_id": user_id},
            )

        return result

    async def list(
        self,
        user_id: str,
        session_id: str | None = None,
        limit: int = 20,
        cursor: str | None = None,
    ) -> tuple[list[dict[str, Any]], str | None, bool]:
        """
        List artifacts (bypasses cache for freshness).

        Args:
            user_id: User ID
            session_id: Optional session filter
            limit: Max items
            cursor: Pagination cursor

        Returns:
            Tuple of (items, next_cursor, has_more)
        """
        # List always hits DB for fresh results
        return await self._repo.list(
            user_id=user_id,
            session_id=session_id,
            limit=limit,
            cursor=cursor,
        )

    async def get_versions(self, artifact_id: str, user_id: str) -> list[dict[str, Any]] | None:  # type: ignore[valid-type]
        """
        Get version history with caching.

        Args:
            artifact_id: Artifact ID
            user_id: User ID

        Returns:
            List of version dicts or None
        """
        cache_key = _generate_versions_cache_key(artifact_id, user_id)

        # Try cache first
        try:
            cached = await self._cache.aget(cache_key)
            if cached is not None:
                logger.debug(
                    "Cache hit for artifact versions",
                    extra={"artifact_id": artifact_id},
                )
                return cast(list[dict[str, Any]], cached)
        except Exception as e:
            logger.warning(
                "Cache get failed for versions",
                extra={"artifact_id": artifact_id, "error": str(e)},
            )

        # Cache miss - fetch from DB
        versions = await self._repo.get_versions(artifact_id, user_id=user_id)

        # Populate cache on miss
        if versions is not None:
            try:  # type: ignore[unreachable]
                await self._cache.aset(cache_key, versions, ttl=self._ttl)
            except Exception as e:
                logger.warning(
                    "Cache set failed for versions",
                    extra={"artifact_id": artifact_id, "error": str(e)},
                )

        return versions

    async def fork(self, artifact_id: str, new_name: str | None, user_id: str) -> dict[str, Any] | None:
        """
        Fork artifact (no caching needed).

        Args:
            artifact_id: Source artifact ID
            new_name: Optional name for fork
            user_id: User ID

        Returns:
            Fork result or None
        """
        # Fork directly to DB
        result = await self._repo.fork(artifact_id, new_name, user_id=user_id)

        if result is not None:
            logger.info(
                "Forked artifact",
                extra={
                    "source_id": artifact_id,
                    "forked_id": result.get("id"),
                    "user_id": user_id,
                },
            )

        return result
