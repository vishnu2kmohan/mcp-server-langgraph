"""
Artifacts Storage Module.

Multi-layer storage for canvas artifacts:
- PostgreSQL: Primary storage with versioning
- Redis: Cache layer for hot artifacts
- S3/GCS/Azure: Hybrid storage for large content
- Qdrant: Vector embeddings for AI features
"""

from mcp_server_langgraph.storage.artifacts.models import (
    ArtifactBase,
    ArtifactModel,
    ArtifactVersionModel,
)
from mcp_server_langgraph.storage.artifacts.postgres_repository import (
    PostgresArtifactsRepository,
)
from mcp_server_langgraph.storage.artifacts.redis_cache import (
    RedisCachedArtifactsService,
)
from mcp_server_langgraph.storage.artifacts.cloud_storage import (
    HybridCloudStorageService,
)
from mcp_server_langgraph.storage.artifacts.qdrant_service import (
    QdrantArtifactVectorService,
)
from mcp_server_langgraph.storage.artifacts.composite_service import (
    CompositeArtifactsService,
)
from mcp_server_langgraph.storage.artifacts.service_adapter import (
    CompositeArtifactsServiceAdapter,
)
from mcp_server_langgraph.storage.artifacts.factory import (
    create_artifacts_service,
    NoOpVectorService,
)

__all__ = [
    "ArtifactBase",
    "ArtifactModel",
    "ArtifactVersionModel",
    "PostgresArtifactsRepository",
    "RedisCachedArtifactsService",
    "HybridCloudStorageService",
    "QdrantArtifactVectorService",
    "CompositeArtifactsService",
    "CompositeArtifactsServiceAdapter",
    "create_artifacts_service",
    "NoOpVectorService",
]
