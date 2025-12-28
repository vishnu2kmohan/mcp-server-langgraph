"""
Redis Cached MCP Unified Registry.

Provides caching layer for the MCPUnifiedRegistry to improve performance
of aggregated capability lookups.

Features:
- Cache-aside pattern for listing tools/resources/prompts
- TTL-based expiration (30 minutes default)
- Cache invalidation on server registration/unregistration
- Graceful degradation on cache failures
- Optional real-time capability broadcasting via WebSocket

Reference: MCP Protocol 2025-11-25 capability aggregation
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from mcp_server_langgraph.observability.telemetry import logger

if TYPE_CHECKING:
    from mcp_server_langgraph.core.cache import CacheService
    from mcp_server_langgraph.mcp.client.tool_registry import MCPServerConfig
    from mcp_server_langgraph.mcp.client.unified_registry import MCPUnifiedRegistry

# Default cache TTL for MCP capabilities (30 minutes)
MCP_CACHE_TTL = 1800

# Cache key prefixes
CACHE_PREFIX = "mcp:"


# =============================================================================
# Capability Broadcaster Protocol
# =============================================================================


@runtime_checkable
class CapabilityBroadcasterProtocol(Protocol):
    """Protocol for capability change broadcasters.

    Defines the interface for broadcasting MCP capability changes
    to connected WebSocket clients.

    Reference: MCP Protocol 2025-11-25 notifications
    """

    async def broadcast_server_registered(
        self,
        server_name: str,
        tool_count: int,
        resource_count: int,
        prompt_count: int,
    ) -> None:
        """Broadcast server registration event."""
        ...

    async def broadcast_server_unregistered(self, server_name: str) -> None:
        """Broadcast server unregistration event."""
        ...

    async def broadcast_tools_changed(self, server_name: str, count: int) -> None:
        """Broadcast tools list changed event."""
        ...

    async def broadcast_resources_changed(self, server_name: str, count: int) -> None:
        """Broadcast resources list changed event."""
        ...

    async def broadcast_prompts_changed(self, server_name: str, count: int) -> None:
        """Broadcast prompts list changed event."""
        ...


# =============================================================================
# Cache Key Generation Functions
# =============================================================================


def generate_tools_cache_key(server_name: str | None) -> str:
    """Generate cache key for tools list.

    Args:
        server_name: Optional server filter. None means all servers.

    Returns:
        Cache key string
    """
    if server_name is None:
        return f"{CACHE_PREFIX}tools:all"
    return f"{CACHE_PREFIX}tools:{server_name}"


def generate_resources_cache_key(server_name: str | None) -> str:
    """Generate cache key for resources list.

    Args:
        server_name: Optional server filter. None means all servers.

    Returns:
        Cache key string
    """
    if server_name is None:
        return f"{CACHE_PREFIX}resources:all"
    return f"{CACHE_PREFIX}resources:{server_name}"


def generate_prompts_cache_key(server_name: str | None) -> str:
    """Generate cache key for prompts list.

    Args:
        server_name: Optional server filter. None means all servers.

    Returns:
        Cache key string
    """
    if server_name is None:
        return f"{CACHE_PREFIX}prompts:all"
    return f"{CACHE_PREFIX}prompts:{server_name}"


def generate_server_list_cache_key() -> str:
    """Generate cache key for server list.

    Returns:
        Cache key string
    """
    return f"{CACHE_PREFIX}servers:all"


def generate_server_capabilities_cache_key(server_name: str) -> str:
    """Generate cache key for server capabilities.

    Args:
        server_name: Name of the server

    Returns:
        Cache key string
    """
    return f"{CACHE_PREFIX}server:{server_name}:capabilities"


# =============================================================================
# Serialization Helpers
# =============================================================================


def _serialize_definition(obj: Any) -> dict[str, Any]:
    """Serialize a definition object to a dictionary.

    Handles dataclasses, objects with __dict__, and plain dicts.

    Args:
        obj: Object to serialize

    Returns:
        Dictionary representation
    """
    if isinstance(obj, dict):
        return obj
    if is_dataclass(obj) and not isinstance(obj, type):
        return asdict(obj)
    # For objects with __dict__ (mock or regular objects)
    result: dict[str, Any] = {}
    for attr in ["name", "server_name", "qualified_name", "description", "input_schema", "uri", "mime_type", "arguments"]:
        if hasattr(obj, attr):
            result[attr] = getattr(obj, attr)
    return result


def _serialize_definitions(definitions: list[Any]) -> list[dict[str, Any]]:
    """Serialize a list of definition objects.

    Args:
        definitions: List of definition objects

    Returns:
        List of dictionaries
    """
    return [_serialize_definition(d) for d in definitions]


# =============================================================================
# Cached Unified Registry
# =============================================================================


class CachedUnifiedRegistry:
    """Cache layer for MCPUnifiedRegistry.

    Implements cache-aside pattern for MCP capability lookups:
    - Check cache first
    - On miss, fetch from registry and populate cache
    - On update, invalidate relevant cache keys
    - Optionally broadcast capability changes via WebSocket

    Example:
        from mcp_server_langgraph.core.cache import get_cache
        from mcp_server_langgraph.mcp.client.unified_registry import get_unified_registry

        registry = get_unified_registry()
        cache = get_cache()

        cached_registry = CachedUnifiedRegistry(
            registry=registry,
            cache=cache,
        )

        # First call hits registry and caches
        tools = await cached_registry.get_tools()

        # Second call returns from cache
        tools = await cached_registry.get_tools()

        # After server registration, cache is invalidated
        await cached_registry.register_server(config)
    """

    def __init__(
        self,
        registry: MCPUnifiedRegistry,
        cache: CacheService,
        ttl: int = MCP_CACHE_TTL,
        broadcaster: CapabilityBroadcasterProtocol | None = None,
    ) -> None:
        """Initialize cached registry.

        Args:
            registry: The underlying unified registry
            cache: Cache service (L1 + L2)
            ttl: Time-to-live for cached items in seconds (default: 30 minutes)
            broadcaster: Optional broadcaster for real-time WebSocket notifications
        """
        self._registry = registry
        self._cache = cache
        self._ttl = ttl
        self._broadcaster = broadcaster

    def set_broadcaster(
        self,
        broadcaster: CapabilityBroadcasterProtocol | None,
    ) -> None:
        """Set or replace the capability broadcaster.

        Enables runtime wiring of the broadcaster during application startup,
        avoiding circular import issues.

        Args:
            broadcaster: The broadcaster to use, or None to disable broadcasting

        Example:
            # In app startup:
            from mcp_server_langgraph.websocket.registry import get_mcp_aggregated_broadcaster

            cached_registry = get_cached_unified_registry()
            cached_registry.set_broadcaster(get_mcp_aggregated_broadcaster())
        """
        self._broadcaster = broadcaster
        logger.debug(
            "Broadcaster updated",
            extra={"has_broadcaster": broadcaster is not None},
        )

    # =========================================================================
    # Cache-Aside Read Methods
    # =========================================================================

    async def get_tools(
        self,
        server_name: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get tools with cache-aside pattern.

        Args:
            server_name: Optional filter by server name

        Returns:
            List of tool definition dictionaries
        """
        cache_key = generate_tools_cache_key(server_name)

        # Try cache first
        try:
            cached = await self._cache.aget(cache_key)
            if cached is not None:
                logger.debug(
                    "Cache hit for tools",
                    extra={"cache_key": cache_key, "count": len(cached)},
                )
                return cached
        except Exception as e:
            logger.warning(
                "Cache get failed for tools, falling back to registry",
                extra={"cache_key": cache_key, "error": str(e)},
            )

        # Cache miss - fetch from registry
        tools = self._registry.get_tools(server_name)
        serialized = _serialize_definitions(tools)

        # Populate cache
        try:
            await self._cache.aset(cache_key, serialized, ttl=self._ttl)
            logger.debug(
                "Cached tools",
                extra={"cache_key": cache_key, "count": len(serialized)},
            )
        except Exception as e:
            logger.warning(
                "Cache set failed for tools",
                extra={"cache_key": cache_key, "error": str(e)},
            )

        return serialized

    async def get_resources(
        self,
        server_name: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get resources with cache-aside pattern.

        Args:
            server_name: Optional filter by server name

        Returns:
            List of resource definition dictionaries
        """
        cache_key = generate_resources_cache_key(server_name)

        # Try cache first
        try:
            cached = await self._cache.aget(cache_key)
            if cached is not None:
                logger.debug(
                    "Cache hit for resources",
                    extra={"cache_key": cache_key, "count": len(cached)},
                )
                return cached
        except Exception as e:
            logger.warning(
                "Cache get failed for resources, falling back to registry",
                extra={"cache_key": cache_key, "error": str(e)},
            )

        # Cache miss - fetch from registry
        resources = self._registry.get_resources(server_name)
        serialized = _serialize_definitions(resources)

        # Populate cache
        try:
            await self._cache.aset(cache_key, serialized, ttl=self._ttl)
            logger.debug(
                "Cached resources",
                extra={"cache_key": cache_key, "count": len(serialized)},
            )
        except Exception as e:
            logger.warning(
                "Cache set failed for resources",
                extra={"cache_key": cache_key, "error": str(e)},
            )

        return serialized

    async def get_prompts(
        self,
        server_name: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get prompts with cache-aside pattern.

        Args:
            server_name: Optional filter by server name

        Returns:
            List of prompt definition dictionaries
        """
        cache_key = generate_prompts_cache_key(server_name)

        # Try cache first
        try:
            cached = await self._cache.aget(cache_key)
            if cached is not None:
                logger.debug(
                    "Cache hit for prompts",
                    extra={"cache_key": cache_key, "count": len(cached)},
                )
                return cached
        except Exception as e:
            logger.warning(
                "Cache get failed for prompts, falling back to registry",
                extra={"cache_key": cache_key, "error": str(e)},
            )

        # Cache miss - fetch from registry
        prompts = self._registry.get_prompts(server_name)
        serialized = _serialize_definitions(prompts)

        # Populate cache
        try:
            await self._cache.aset(cache_key, serialized, ttl=self._ttl)
            logger.debug(
                "Cached prompts",
                extra={"cache_key": cache_key, "count": len(serialized)},
            )
        except Exception as e:
            logger.warning(
                "Cache set failed for prompts",
                extra={"cache_key": cache_key, "error": str(e)},
            )

        return serialized

    async def get_server_names(self) -> list[str]:
        """Get server names with cache-aside pattern.

        Returns:
            List of registered server names
        """
        cache_key = generate_server_list_cache_key()

        # Try cache first
        try:
            cached = await self._cache.aget(cache_key)
            if cached is not None:
                logger.debug(
                    "Cache hit for server names",
                    extra={"cache_key": cache_key, "count": len(cached)},
                )
                return cached
        except Exception as e:
            logger.warning(
                "Cache get failed for server names, falling back to registry",
                extra={"cache_key": cache_key, "error": str(e)},
            )

        # Cache miss - fetch from registry
        server_names = self._registry.get_server_names()

        # Populate cache
        try:
            await self._cache.aset(cache_key, server_names, ttl=self._ttl)
            logger.debug(
                "Cached server names",
                extra={"cache_key": cache_key, "count": len(server_names)},
            )
        except Exception as e:
            logger.warning(
                "Cache set failed for server names",
                extra={"cache_key": cache_key, "error": str(e)},
            )

        return server_names

    async def get_server_capabilities(
        self,
        server_name: str,
    ) -> dict[str, int]:
        """Get server capabilities with cache-aside pattern.

        Args:
            server_name: Name of the server

        Returns:
            Dict with tool_count, resource_count, prompt_count
        """
        cache_key = generate_server_capabilities_cache_key(server_name)

        # Try cache first
        try:
            cached = await self._cache.aget(cache_key)
            if cached is not None:
                logger.debug(
                    "Cache hit for server capabilities",
                    extra={"cache_key": cache_key, "server_name": server_name},
                )
                return cached
        except Exception as e:
            logger.warning(
                "Cache get failed for server capabilities, falling back to registry",
                extra={"cache_key": cache_key, "error": str(e)},
            )

        # Cache miss - fetch from registry
        capabilities = self._registry.get_server_capabilities(server_name)

        # Populate cache
        try:
            await self._cache.aset(cache_key, capabilities, ttl=self._ttl)
            logger.debug(
                "Cached server capabilities",
                extra={"cache_key": cache_key, "server_name": server_name},
            )
        except Exception as e:
            logger.warning(
                "Cache set failed for server capabilities",
                extra={"cache_key": cache_key, "error": str(e)},
            )

        return capabilities

    # =========================================================================
    # Cache Invalidation Methods
    # =========================================================================

    async def invalidate_server(self, server_name: str) -> int:
        """Invalidate all cache entries for a specific server.

        Args:
            server_name: Name of the server to invalidate

        Returns:
            Number of keys deleted
        """
        try:
            # Delete server-specific keys
            pattern = f"{CACHE_PREFIX}*:{server_name}*"
            count = await self._cache.adelete_pattern(pattern)

            # Also invalidate "all" keys since they contain this server's data
            await self._cache.adelete_pattern(f"{CACHE_PREFIX}*:all")

            logger.info(
                "Invalidated cache for server",
                extra={"server_name": server_name, "keys_deleted": count},
            )
            return count
        except Exception as e:
            logger.warning(
                "Cache invalidation failed for server",
                extra={"server_name": server_name, "error": str(e)},
            )
            return 0

    async def invalidate_all(self) -> int:
        """Invalidate all MCP cache entries.

        Returns:
            Number of keys deleted
        """
        try:
            pattern = f"{CACHE_PREFIX}*"
            count = await self._cache.adelete_pattern(pattern)
            logger.info(
                "Invalidated all MCP cache entries",
                extra={"keys_deleted": count},
            )
            return count
        except Exception as e:
            logger.warning(
                "Cache invalidation failed",
                extra={"error": str(e)},
            )
            return 0

    # =========================================================================
    # Passthrough Methods (with cache invalidation)
    # =========================================================================

    async def register_server(
        self,
        config: MCPServerConfig,
    ) -> dict[str, int]:
        """Register a server and invalidate cache.

        Args:
            config: Server configuration

        Returns:
            Dict with capability counts
        """
        # Invalidate cache before registration
        await self.invalidate_all()

        # Register with underlying registry
        result = await self._registry.register_server(config)

        logger.info(
            "Registered server via cached registry",
            extra={"server_name": config.name, **result},
        )

        # Broadcast server registration event
        if self._broadcaster is not None:
            try:
                await self._broadcaster.broadcast_server_registered(
                    server_name=config.name,
                    tool_count=result.get("tool_count", 0),
                    resource_count=result.get("resource_count", 0),
                    prompt_count=result.get("prompt_count", 0),
                )
            except Exception as e:
                logger.warning(
                    "Failed to broadcast server registered event",
                    extra={"server_name": config.name, "error": str(e)},
                )

        return result

    async def unregister_server(self, name: str) -> None:
        """Unregister a server and invalidate cache.

        Args:
            name: Name of the server to unregister
        """
        # Invalidate cache for this server
        await self.invalidate_server(name)

        # Unregister from underlying registry
        await self._registry.unregister_server(name)

        logger.info(
            "Unregistered server via cached registry",
            extra={"server_name": name},
        )

        # Broadcast server unregistration event
        if self._broadcaster is not None:
            try:
                await self._broadcaster.broadcast_server_unregistered(server_name=name)
            except Exception as e:
                logger.warning(
                    "Failed to broadcast server unregistered event",
                    extra={"server_name": name, "error": str(e)},
                )

    async def refresh_all(self, server_name: str) -> dict[str, int]:
        """Refresh capabilities from a server and invalidate cache.

        Args:
            server_name: Name of the server to refresh

        Returns:
            Dict with updated capability counts
        """
        # Invalidate cache for this server
        await self.invalidate_server(server_name)

        # Refresh from underlying registry
        result = await self._registry.refresh_all(server_name)

        logger.info(
            "Refreshed server via cached registry",
            extra={"server_name": server_name, **result},
        )

        # Broadcast capability changed events
        if self._broadcaster is not None:
            try:
                await self._broadcaster.broadcast_tools_changed(server_name=server_name, count=result.get("tool_count", 0))
                await self._broadcaster.broadcast_resources_changed(
                    server_name=server_name, count=result.get("resource_count", 0)
                )
                await self._broadcaster.broadcast_prompts_changed(server_name=server_name, count=result.get("prompt_count", 0))
            except Exception as e:
                logger.warning(
                    "Failed to broadcast capability changed events",
                    extra={"server_name": server_name, "error": str(e)},
                )

        return result

    # =========================================================================
    # Direct Passthrough Methods (no caching needed)
    # =========================================================================

    def get_tool(self, qualified_name: str) -> Any:
        """Get a specific tool by qualified name (passthrough)."""
        return self._registry.get_tool(qualified_name)

    def get_resource(self, qualified_name: str) -> Any:
        """Get a specific resource by qualified name (passthrough)."""
        return self._registry.get_resource(qualified_name)

    def get_prompt(self, qualified_name: str) -> Any:
        """Get a specific prompt by qualified name (passthrough)."""
        return self._registry.get_prompt(qualified_name)

    def get_session(self, server_name: str) -> Any:
        """Get session for a server (passthrough)."""
        return self._registry.get_session(server_name)


# =============================================================================
# Singleton Instance
# =============================================================================

_cached_registry: CachedUnifiedRegistry | None = None


def get_cached_unified_registry() -> CachedUnifiedRegistry:
    """Get the application-wide cached unified registry instance.

    Returns:
        Singleton CachedUnifiedRegistry instance
    """
    global _cached_registry
    if _cached_registry is None:
        from mcp_server_langgraph.core.cache import get_cache
        from mcp_server_langgraph.mcp.client.unified_registry import get_unified_registry

        _cached_registry = CachedUnifiedRegistry(
            registry=get_unified_registry(),
            cache=get_cache(),
        )
    return _cached_registry


def reset_cached_unified_registry() -> None:
    """Reset the cached unified registry (for testing)."""
    global _cached_registry
    _cached_registry = None
