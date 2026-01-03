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

import logging
from typing import Any, Literal

from mcp_server_langgraph.storage.vectors.base import VectorSearchProvider

logger = logging.getLogger(__name__)

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
        raise ValueError(
            f"Unsupported provider type: {provider_type}. "
            f"Supported: {SUPPORTED_PROVIDERS}"
        )

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
    logger.warning(
        "Unknown vector_search_provider '%s', using inmemory", provider_type
    )
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
    raise RuntimeError(
        "Database pool not configured. "
        "Use dependency injection or app state to provide the pool."
    )


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
        raise RuntimeError(
            "qdrant-client not installed. "
            "Install with: pip install qdrant-client"
        )
