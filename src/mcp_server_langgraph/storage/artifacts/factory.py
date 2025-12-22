"""
Artifacts Service Factory.

Creates and wires together all artifacts storage layer components:
- PostgresArtifactsRepository (primary storage)
- RedisCachedArtifactsService (cache wrapper)
- HybridCloudStorageService (cloud storage)
- QdrantArtifactVectorService (vector embeddings)
- CompositeArtifactsService (orchestration)
- CompositeArtifactsServiceAdapter (protocol adapter)

Usage:
    from mcp_server_langgraph.storage.artifacts.factory import create_artifacts_service

    service = create_artifacts_service(
        db_session_factory=get_async_session,
        redis_client=redis,
    )
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Callable

from mcp_server_langgraph.storage.artifacts.cloud_storage import (
    HybridCloudStorageService,
)
from mcp_server_langgraph.storage.artifacts.composite_service import (
    CompositeArtifactsService,
)
from mcp_server_langgraph.storage.artifacts.postgres_repository import (
    PostgresArtifactsRepository,
)
from mcp_server_langgraph.storage.artifacts.qdrant_service import (
    QdrantArtifactVectorService,
)
from mcp_server_langgraph.storage.artifacts.redis_cache import (
    RedisCachedArtifactsService,
)
from mcp_server_langgraph.storage.artifacts.service_adapter import (
    CompositeArtifactsServiceAdapter,
)

if TYPE_CHECKING:
    from redis.asyncio import Redis
    from sqlalchemy.ext.asyncio import AsyncSession


logger = logging.getLogger(__name__)


class NoOpVectorService:
    """
    No-operation vector service for when Qdrant is disabled.

    Provides the same interface as QdrantArtifactVectorService but
    returns empty results. Used for graceful degradation when vector
    search is not available.
    """

    async def search(
        self,
        query: str,
        user_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Return empty results for search."""
        return []

    async def find_similar(
        self,
        artifact_id: str,
        user_id: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Return empty results for find_similar."""
        return []

    async def index(
        self,
        artifact: dict[str, Any],
        user_id: str,
    ) -> None:
        """No-op for indexing."""
        pass

    async def delete(
        self,
        artifact_id: str,
    ) -> None:
        """No-op for deletion."""
        pass


def create_artifacts_service(
    db_session_factory: Callable[[], AsyncSession],
    redis_client: Redis,
    *,
    cloud_provider: str = "s3",
    cloud_bucket: str | None = None,
    content_size_threshold: int = 100_000,  # 100KB default
    qdrant_enabled: bool = True,
    qdrant_url: str | None = None,
    qdrant_collection: str = "artifacts",
    cache_ttl: int = 3600,  # 1 hour default
) -> CompositeArtifactsServiceAdapter:
    """
    Create a fully configured artifacts service stack.

    This factory creates and wires together all the storage layers:
    1. PostgresArtifactsRepository - primary storage with versioning
    2. RedisCachedArtifactsService - caching layer
    3. HybridCloudStorageService - cloud storage for large content
    4. QdrantArtifactVectorService - vector embeddings (optional)
    5. CompositeArtifactsService - orchestrates all layers
    6. CompositeArtifactsServiceAdapter - adapts to API protocol

    Args:
        db_session_factory: Factory for database sessions
        redis_client: Redis client for caching
        cloud_provider: Cloud storage provider ('s3', 'gcs', 'azure')
        cloud_bucket: Cloud storage bucket name
        content_size_threshold: Size threshold for cloud storage (bytes)
        qdrant_enabled: Whether to enable Qdrant vector search
        qdrant_url: Qdrant server URL
        qdrant_collection: Qdrant collection name
        cache_ttl: Redis cache TTL in seconds

    Returns:
        CompositeArtifactsServiceAdapter ready for use with API router
    """
    logger.info(
        "Creating artifacts service",
        extra={
            "cloud_provider": cloud_provider,
            "qdrant_enabled": qdrant_enabled,
            "content_size_threshold": content_size_threshold,
        },
    )

    # 1. Create PostgreSQL repository
    # Note: Factory uses session_factory but repo expects session - interface mismatch
    postgres_repo = PostgresArtifactsRepository(
        session_factory=db_session_factory,  # type: ignore[call-arg]
    )

    # 2. Wrap with Redis cache
    # Note: Factory uses redis_client but service expects cache: CacheService - interface mismatch
    cached_service = RedisCachedArtifactsService(
        repository=postgres_repo,
        redis_client=redis_client,  # type: ignore[call-arg]
        ttl=cache_ttl,
    )

    # 3. Create cloud storage service
    # Note: Factory uses cloud_provider/bucket but service expects client/bucket - interface mismatch
    cloud_storage = HybridCloudStorageService(
        cloud_provider=cloud_provider,  # type: ignore[call-arg]
        bucket=cloud_bucket,  # type: ignore[arg-type]
        size_threshold=content_size_threshold,
    )

    # 4. Create vector service (or NoOp if disabled)
    # Note: Factory uses qdrant_url/collection_name but service expects client/embedder/collection
    if qdrant_enabled and qdrant_url:
        vector_service: QdrantArtifactVectorService | NoOpVectorService = (
            QdrantArtifactVectorService(
                qdrant_url=qdrant_url,  # type: ignore[call-arg]
                collection_name=qdrant_collection,
            )
        )
        logger.info("Qdrant vector service enabled", extra={"url": qdrant_url})
    else:
        vector_service = NoOpVectorService()
        if qdrant_enabled:
            logger.warning(
                "Qdrant enabled but no URL provided, using NoOp vector service"
            )
        else:
            logger.info("Qdrant vector service disabled, using NoOp")

    # 5. Create composite service that orchestrates all layers
    composite_service = CompositeArtifactsService(
        cached_service=cached_service,
        cloud_storage=cloud_storage,
        vector_service=vector_service,  # type: ignore[arg-type]
    )

    # 6. Create adapter for API protocol
    adapter = CompositeArtifactsServiceAdapter(
        composite_service=composite_service,
    )

    logger.info("Artifacts service created successfully")

    return adapter
