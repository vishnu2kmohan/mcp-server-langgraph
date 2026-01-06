"""
Vector Provider Factory

Creates vector search provider instances based on configuration.

Supported providers:
- inmemory: In-memory storage for testing
- pgvector: PostgreSQL pgvector extension
- qdrant: Qdrant vector database

Usage:
    from mcp_server_langgraph.storage.vectors.factory import get_vector_provider

    # For testing
    provider = get_vector_provider("inmemory")

    # For production (requires configuration)
    provider = get_vector_provider("qdrant", url="http://localhost:6333")
"""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import TYPE_CHECKING, Any, Literal

from mcp_server_langgraph.storage.vectors.base import VectorSearchProvider

if TYPE_CHECKING:
    from qdrant_client import AsyncQdrantClient, QdrantClient

logger = logging.getLogger(__name__)

# Shared sync Qdrant client (singleton for sync endpoints like api/v1/vectors.py)
# This prevents creating a new client per request which causes connection exhaustion
_qdrant_client: QdrantClient | None = None
_qdrant_lock = threading.Lock()  # Sync lock for sync endpoints

# Shared async Qdrant client (singleton for async endpoints)
# Uses asyncio.Lock for async-safe initialization
_async_qdrant_client: AsyncQdrantClient | None = None
_async_qdrant_lock = asyncio.Lock()  # Async lock for async endpoints

# Supported provider types
SUPPORTED_PROVIDERS = {"inmemory", "pgvector", "qdrant"}

ProviderType = Literal["inmemory", "pgvector", "qdrant"]


def get_vector_provider(
    provider_type: ProviderType = "inmemory",
    **kwargs: Any,
) -> VectorSearchProvider:
    """Get a vector search provider instance.

    Args:
        provider_type: Type of provider ("inmemory", "pgvector", "qdrant")
        **kwargs: Provider-specific configuration

    Returns:
        VectorSearchProvider instance

    Raises:
        ValueError: If provider_type is not supported
        ImportError: If required dependencies are not installed
    """
    if provider_type not in SUPPORTED_PROVIDERS:
        raise ValueError(f"Unsupported provider type: {provider_type}. Supported: {SUPPORTED_PROVIDERS}")

    if provider_type == "inmemory":
        from mcp_server_langgraph.storage.vectors.inmemory import (
            InMemoryVectorProvider,
        )

        return InMemoryVectorProvider()

    elif provider_type == "pgvector":
        # Lazy import to avoid dependency issues
        try:
            from mcp_server_langgraph.storage.vectors.pgvector_provider import (
                PgVectorProvider,
            )

            return PgVectorProvider(**kwargs)
        except ImportError as e:
            logger.warning(
                "pgvector dependencies not available, falling back to inmemory: %s",
                e,
            )
            from mcp_server_langgraph.storage.vectors.inmemory import (
                InMemoryVectorProvider,
            )

            return InMemoryVectorProvider()

    elif provider_type == "qdrant":
        # Lazy import to avoid dependency issues
        try:
            from mcp_server_langgraph.storage.vectors.qdrant_provider import (
                QdrantVectorProvider,
            )

            return QdrantVectorProvider(**kwargs)
        except ImportError as e:
            logger.warning(
                "qdrant dependencies not available, falling back to inmemory: %s",
                e,
            )
            from mcp_server_langgraph.storage.vectors.inmemory import (
                InMemoryVectorProvider,
            )

            return InMemoryVectorProvider()

    # Should never reach here due to validation above
    raise ValueError(f"Unknown provider type: {provider_type}")


def get_vector_provider_from_settings() -> VectorSearchProvider:
    """Get a vector search provider based on application Settings.

    Reads the vector_search_provider setting and creates the appropriate
    provider instance with configuration from Settings.

    Provider resolution:
    - "inmemory": InMemoryVectorProvider (no dependencies)
    - "pgvector": PgVectorProvider (requires database pool)
    - "qdrant": QdrantVectorProvider (requires Qdrant client)

    Returns:
        VectorSearchProvider configured from Settings

    Example:
        from mcp_server_langgraph.storage.vectors.factory import (
            get_vector_provider_from_settings,
        )

        provider = get_vector_provider_from_settings()
        results = await provider.search("collection", query_vector)
    """
    from mcp_server_langgraph.core.config import settings as app_settings

    provider_type = app_settings.vector_search_provider

    if provider_type == "inmemory":
        from mcp_server_langgraph.storage.vectors.inmemory import (
            InMemoryVectorProvider,
        )

        return InMemoryVectorProvider()

    elif provider_type == "pgvector":
        try:
            from mcp_server_langgraph.storage.vectors.pgvector_provider import (
                PgVectorProvider,
            )

            # Get database pool from application
            pool = get_database_pool()
            return PgVectorProvider(connection_pool=pool)
        except Exception as e:
            logger.warning(
                "Failed to create pgvector provider, falling back to inmemory: %s",
                e,
            )
            from mcp_server_langgraph.storage.vectors.inmemory import (
                InMemoryVectorProvider,
            )

            return InMemoryVectorProvider()

    elif provider_type == "qdrant":
        try:
            from mcp_server_langgraph.storage.vectors.qdrant_provider import (
                QdrantVectorProvider,
            )

            # Get Qdrant client from application
            client = get_qdrant_client()
            return QdrantVectorProvider(
                client=client,
                vector_size=app_settings.embedding_dimensions,
            )
        except Exception as e:
            logger.warning(
                "Failed to create qdrant provider, falling back to inmemory: %s",
                e,
            )
            from mcp_server_langgraph.storage.vectors.inmemory import (
                InMemoryVectorProvider,
            )

            return InMemoryVectorProvider()

    # Default fallback
    logger.warning("Unknown vector_search_provider '%s', using inmemory", provider_type)
    from mcp_server_langgraph.storage.vectors.inmemory import (
        InMemoryVectorProvider,
    )

    return InMemoryVectorProvider()


def get_database_pool() -> Any:
    """Get the database connection pool for pgvector.

    This is a placeholder for the actual database pool acquisition.
    In production, this would return the SQLAlchemy async engine or pool.

    Returns:
        Database connection pool

    Raises:
        RuntimeError: If database pool is not configured
    """
    # Placeholder - actual implementation depends on app initialization
    # This would typically be injected or retrieved from app state
    raise RuntimeError("Database pool not configured. Use dependency injection or app state to provide the pool.")


def get_qdrant_client() -> Any:
    """Get the Qdrant client for vector operations.

    This is a placeholder for actual Qdrant client acquisition.
    In production, this would return a configured QdrantAsyncClient.

    Returns:
        QdrantAsyncClient instance

    Raises:
        RuntimeError: If Qdrant client is not configured
    """
    from mcp_server_langgraph.core.config import settings as app_settings

    try:
        from qdrant_client import AsyncQdrantClient

        return AsyncQdrantClient(
            url=app_settings.qdrant_url,
            port=app_settings.qdrant_port,
        )
    except ImportError:
        raise RuntimeError("qdrant-client not installed. Install with: pip install qdrant-client")


def get_shared_qdrant_client() -> QdrantClient:
    """Get shared sync Qdrant client (singleton).

    Used by sync endpoints in api/v1/vectors.py to avoid creating a new
    client per request, which would cause connection exhaustion.

    Thread-safe using double-checked locking pattern:
    - Fast path: Return existing client if already created
    - Slow path: Acquire lock, double-check, create if needed

    Returns:
        QdrantClient instance (sync, not async)

    Raises:
        RuntimeError: If qdrant-client is not installed

    Example:
        >>> client = get_shared_qdrant_client()
        >>> client.get_collections()
    """
    global _qdrant_client

    # Fast path: Return existing client without lock
    if _qdrant_client is not None:
        return _qdrant_client

    # Slow path: Acquire lock and create if needed
    with _qdrant_lock:
        # Double-check after acquiring lock (another thread may have created it)
        if _qdrant_client is None:
            from mcp_server_langgraph.core.config import settings as app_settings

            try:
                from qdrant_client import QdrantClient

                _qdrant_client = QdrantClient(
                    url=app_settings.qdrant_url,
                    port=app_settings.qdrant_port,
                )
                logger.info(
                    "Shared Qdrant client created",
                    extra={
                        "url": app_settings.qdrant_url,
                        "port": app_settings.qdrant_port,
                    },
                )
            except ImportError:
                raise RuntimeError("qdrant-client not installed. Install with: pip install qdrant-client")

        return _qdrant_client


def close_qdrant_client() -> None:
    """Close the shared Qdrant client (idempotent).

    Safe to call multiple times - subsequent calls are no-ops.
    Safe to call even if no client was created.

    This is a SYNC function (no await needed) because QdrantClient.close()
    is synchronous.

    Called from:
    - mcp_server_langgraph.lifecycle.cleanup.cleanup_all_clients()

    Example:
        >>> close_qdrant_client()  # First call closes client
        >>> close_qdrant_client()  # Safe, no-op
    """
    global _qdrant_client

    if _qdrant_client is not None:
        try:
            _qdrant_client.close()
            logger.debug("Shared Qdrant client closed")
        except Exception as e:
            logger.warning(f"Error closing Qdrant client: {e}")
        finally:
            _qdrant_client = None


async def get_shared_async_qdrant_client() -> AsyncQdrantClient:
    """Get shared async Qdrant client (singleton).

    Used by async endpoints to avoid creating a new client per request,
    which would cause connection exhaustion.

    Async-safe using double-checked locking pattern with asyncio.Lock:
    - Fast path: Return existing client if already created
    - Slow path: Acquire async lock, double-check, create if needed

    Returns:
        AsyncQdrantClient instance

    Raises:
        RuntimeError: If qdrant-client is not installed

    Example:
        >>> client = await get_shared_async_qdrant_client()
        >>> await client.get_collections()
    """
    global _async_qdrant_client

    # Fast path: Return existing client without lock
    if _async_qdrant_client is not None:
        return _async_qdrant_client

    # Slow path: Acquire async lock and create if needed
    async with _async_qdrant_lock:
        # Double-check after acquiring lock (another coroutine may have created it)
        if _async_qdrant_client is None:
            from mcp_server_langgraph.core.config import settings

            try:
                from qdrant_client import AsyncQdrantClient

                _async_qdrant_client = AsyncQdrantClient(
                    url=settings.qdrant_url,
                    port=settings.qdrant_port,
                )
                logger.info(
                    "Shared async Qdrant client created",
                    extra={
                        "url": settings.qdrant_url,
                        "port": settings.qdrant_port,
                    },
                )
            except ImportError:
                raise RuntimeError("qdrant-client not installed. Install with: pip install qdrant-client")

        return _async_qdrant_client


async def aclose_async_qdrant_client() -> None:
    """Close the shared async Qdrant client (idempotent).

    Safe to call multiple times - subsequent calls are no-ops.
    Safe to call even if no client was created.

    This is an ASYNC function because AsyncQdrantClient.close() is async.

    Called from:
    - mcp_server_langgraph.lifecycle.cleanup.cleanup_all_clients()

    Example:
        >>> await aclose_async_qdrant_client()  # First call closes client
        >>> await aclose_async_qdrant_client()  # Safe, no-op
    """
    global _async_qdrant_client

    if _async_qdrant_client is not None:
        try:
            await _async_qdrant_client.close()
            logger.debug("Shared async Qdrant client closed")
        except Exception as e:
            logger.warning(f"Error closing async Qdrant client: {e}")
        finally:
            _async_qdrant_client = None
