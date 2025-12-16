"""
Cached MCP Connection Repository

Wraps the PostgresConnectionRepository with multi-layer caching (L1 + L2):
- L1: In-memory LRU cache for sub-10ms reads
- L2: Redis distributed cache for cross-instance consistency

Cache invalidation is automatic on write operations (create, update, delete).

Usage:
    from mcp_server_langgraph.repositories.cached_connections import CachedConnectionRepository

    # Wrap an existing repository
    repo = CachedConnectionRepository(postgres_repo)
"""

from datetime import datetime
from typing import Any

from mcp_server_langgraph.core.cache import (
    CACHE_TTLS,
    CacheService,
    generate_cache_key,
    get_cache,
)
from mcp_server_langgraph.repositories.connections import ConnectionRepository
from mcp_server_langgraph.storage.models import (
    MCPConnection,
    MCPConnectionCreate,
    MCPConnectionSummary,
    MCPConnectionUpdate,
)


class CachedConnectionRepository(ConnectionRepository):
    """
    Cached wrapper for ConnectionRepository.

    Provides transparent caching for read operations with automatic
    invalidation on writes. Delegates all operations to the underlying
    repository.

    Cache Keys:
    - connection:{id} - Individual connection details
    - connection_list:{owner_id}:{hash} - Paginated connection lists
    - connection_health:{id} - Connection health status

    Performance:
    - get(): L1 hit < 1ms, L2 hit < 10ms, DB miss ~50ms
    - list(): Cached for pagination cursor reuse
    """

    def __init__(
        self,
        delegate: ConnectionRepository,
        cache: CacheService | None = None,
    ) -> None:
        """
        Initialize cached repository.

        Args:
            delegate: The underlying connection repository
            cache: Cache service (uses global cache if not provided)
        """
        self._delegate = delegate
        self._cache = cache or get_cache()

    # ==========================================================================
    # Read Operations (Cached)
    # ==========================================================================

    async def get(self, connection_id: str) -> MCPConnection | None:
        """
        Get connection by ID with caching.

        Tries L1 → L2 → database. Caches result on miss.
        """
        cache_key = generate_cache_key(connection_id, prefix="connection")

        # Try cache first
        cached = self._cache.get(cache_key)
        if cached is not None:
            return MCPConnection(**cached) if isinstance(cached, dict) else cached

        # Cache miss: fetch from database
        connection = await self._delegate.get(connection_id)

        if connection is not None:
            # Cache the result
            self._cache.set(
                cache_key,
                connection.model_dump(),
                ttl=CACHE_TTLS["connection"],
            )

        return connection

    async def get_many(self, connection_ids: list[str]) -> list[MCPConnection]:
        """
        Get multiple connections with per-ID caching.

        Fetches cached connections individually, batch-fetches misses.
        """
        if not connection_ids:
            return []

        results: dict[str, MCPConnection] = {}
        missing_ids: list[str] = []

        # Check cache for each ID
        for conn_id in connection_ids:
            cache_key = generate_cache_key(conn_id, prefix="connection")
            cached = self._cache.get(cache_key)

            if cached is not None:
                conn = MCPConnection(**cached) if isinstance(cached, dict) else cached
                results[conn_id] = conn
            else:
                missing_ids.append(conn_id)

        # Fetch missing from database
        if missing_ids:
            db_connections = await self._delegate.get_many(missing_ids)
            for conn in db_connections:
                results[conn.id] = conn
                # Cache each fetched connection
                cache_key = generate_cache_key(conn.id, prefix="connection")
                self._cache.set(
                    cache_key,
                    conn.model_dump(),
                    ttl=CACHE_TTLS["connection"],
                )

        # Return in original order
        return [results[cid] for cid in connection_ids if cid in results]

    async def list(
        self,
        owner_id: str,
        cursor: str | None = None,
        limit: int = 20,
        search: str | None = None,
        status: str | None = None,
        auth_type: str | None = None,
        project_id: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[MCPConnectionSummary], str | None]:
        """
        List connections with caching for pagination.

        Caches first page of results for each owner. Subsequent pages
        and filtered queries are not cached (too variable).
        """
        # Only cache unfiltered first page (most common query)
        is_cacheable = (
            cursor is None and search is None and status is None and auth_type is None and project_id is None and limit <= 50
        )

        if is_cacheable:
            cache_key = generate_cache_key(
                owner_id,
                limit,
                sort_by,
                sort_order,
                prefix="connection_list",
            )
            cached = self._cache.get(cache_key)
            if cached is not None:
                items, next_cursor = cached
                # Ensure transport field has a default value for backward compatibility
                # with cached data that predates the transport field requirement
                return (
                    [
                        MCPConnectionSummary(**{**item, "transport": item.get("transport", "streamable_http")})
                        for item in items
                    ],
                    next_cursor,
                )

        # Fetch from database
        items, next_cursor = await self._delegate.list(
            owner_id=owner_id,
            cursor=cursor,
            limit=limit,
            search=search,
            status=status,
            auth_type=auth_type,
            project_id=project_id,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        # Cache first page results
        if is_cacheable:
            cache_key = generate_cache_key(
                owner_id,
                limit,
                sort_by,
                sort_order,
                prefix="connection_list",
            )
            self._cache.set(
                cache_key,
                ([item.model_dump() for item in items], next_cursor),
                ttl=CACHE_TTLS["connection"],
            )

        return items, next_cursor

    # ==========================================================================
    # Write Operations (Invalidate Cache)
    # ==========================================================================

    async def create(
        self,
        data: MCPConnectionCreate,
        owner_id: str,
    ) -> MCPConnection:
        """
        Create connection and invalidate owner's list cache.
        """
        connection = await self._delegate.create(data, owner_id)

        # Invalidate list cache for this owner
        self._cache.clear(f"connection_list:{owner_id}:*")

        return connection

    async def update(
        self,
        connection_id: str,
        data: MCPConnectionUpdate,
    ) -> MCPConnection | None:
        """
        Update connection and invalidate caches.
        """
        connection = await self._delegate.update(connection_id, data)

        if connection is not None:
            # Invalidate specific connection cache
            cache_key = generate_cache_key(connection_id, prefix="connection")
            self._cache.delete(cache_key)

            # Invalidate owner's list cache
            self._cache.clear(f"connection_list:{connection.owner_id}:*")

        return connection

    async def delete(self, connection_id: str) -> bool:
        """
        Delete connection and invalidate all related caches.
        """
        # Get connection first for owner_id (needed for cache invalidation)
        connection = await self._delegate.get(connection_id)
        owner_id = connection.owner_id if connection else None

        result = await self._delegate.delete(connection_id)

        if result:
            # Invalidate specific connection cache
            cache_key = generate_cache_key(connection_id, prefix="connection")
            self._cache.delete(cache_key)

            # Invalidate health cache
            health_key = generate_cache_key(connection_id, prefix="connection_health")
            self._cache.delete(health_key)

            # Invalidate owner's list cache
            if owner_id:
                self._cache.clear(f"connection_list:{owner_id}:*")

        return result

    # ==========================================================================
    # Secret Management (Delegated, not cached)
    # ==========================================================================

    async def store_api_key(self, connection_id: str, api_key: str) -> None:
        """Store API key (not cached)."""
        await self._delegate.store_api_key(connection_id, api_key)

    async def get_api_key(self, connection_id: str) -> str | None:
        """Get API key (not cached for security)."""
        return await self._delegate.get_api_key(connection_id)

    # ==========================================================================
    # OAuth2 State Management (Delegated, not cached)
    # ==========================================================================

    async def create_oauth2_state(
        self,
        connection_id: str,
        state: str,
        code_verifier: str,
        redirect_uri: str,
    ) -> None:
        """Create OAuth2 state (not cached)."""
        await self._delegate.create_oauth2_state(connection_id, state, code_verifier, redirect_uri)

    async def get_and_delete_oauth2_state(self, state: str) -> dict[str, Any] | None:
        """Get and delete OAuth2 state (not cached, one-time use)."""
        return await self._delegate.get_and_delete_oauth2_state(state)

    # ==========================================================================
    # OAuth2 Token Management (Delegated, not cached)
    # ==========================================================================

    async def store_oauth2_tokens(
        self,
        connection_id: str,
        access_token: str,
        refresh_token: str | None,
        expires_at: datetime | None,
    ) -> None:
        """Store OAuth2 tokens (not cached for security)."""
        await self._delegate.store_oauth2_tokens(connection_id, access_token, refresh_token, expires_at)
        # Invalidate connection cache as status may change
        cache_key = generate_cache_key(connection_id, prefix="connection")
        self._cache.delete(cache_key)

    async def get_oauth2_access_token(self, connection_id: str) -> str | None:
        """Get OAuth2 access token (not cached for security)."""
        return await self._delegate.get_oauth2_access_token(connection_id)

    # ==========================================================================
    # Status Management (Cached for health checks)
    # ==========================================================================

    async def update_status(
        self,
        connection_id: str,
        status: str,
        server_name: str | None = None,
        server_version: str | None = None,
        tool_count: int | None = None,
        resource_count: int | None = None,
        prompt_count: int | None = None,
        last_error: str | None = None,
    ) -> None:
        """
        Update connection status and cache health info.
        """
        await self._delegate.update_status(
            connection_id=connection_id,
            status=status,
            server_name=server_name,
            server_version=server_version,
            tool_count=tool_count,
            resource_count=resource_count,
            prompt_count=prompt_count,
            last_error=last_error,
        )

        # Invalidate connection cache
        cache_key = generate_cache_key(connection_id, prefix="connection")
        self._cache.delete(cache_key)

        # Cache health status separately (shorter TTL)
        health_key = generate_cache_key(connection_id, prefix="connection_health")
        self._cache.set(
            health_key,
            {
                "status": status,
                "server_name": server_name,
                "server_version": server_version,
                "tool_count": tool_count,
                "resource_count": resource_count,
                "prompt_count": prompt_count,
                "last_error": last_error,
            },
            ttl=CACHE_TTLS["connection_health"],
        )

    # ==========================================================================
    # Cache Management Utilities
    # ==========================================================================

    def get_cached_health(self, connection_id: str) -> dict[str, Any] | None:
        """
        Get cached health status without database hit.

        Useful for WebSocket health broadcasts.
        """
        health_key = generate_cache_key(connection_id, prefix="connection_health")
        return self._cache.get(health_key)

    def invalidate_connection(self, connection_id: str) -> None:
        """
        Manually invalidate all caches for a connection.
        """
        cache_key = generate_cache_key(connection_id, prefix="connection")
        self._cache.delete(cache_key)

        health_key = generate_cache_key(connection_id, prefix="connection_health")
        self._cache.delete(health_key)

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        return self._cache.get_statistics()
