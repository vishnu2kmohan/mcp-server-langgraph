"""
Tests for Artifacts Service Factory.

TDD RED Phase: These tests define the expected behavior of the factory
that creates and wires together all artifacts storage layer components.

The factory creates:
- PostgresArtifactsRepository (primary storage)
- RedisCachedArtifactsService (cache wrapper)
- HybridCloudStorageService (cloud storage)
- QdrantArtifactVectorService (vector embeddings)
- CompositeArtifactsService (orchestration)
- CompositeArtifactsServiceAdapter (protocol adapter)
"""

from __future__ import annotations

import gc
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit

# Test constants
TEST_DB_URL = "postgresql+asyncpg://test:test@localhost:5432/test_artifacts"
TEST_REDIS_URL = "redis://localhost:6379/0"
TEST_QDRANT_URL = "http://localhost:6333"


@pytest.mark.xdist_group(name="test_artifacts_factory")
@pytest.mark.unit
class TestArtifactsServiceFactory:
    """Tests for the artifacts service factory."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_artifacts_service_returns_adapter(self) -> None:
        """Test that factory returns CompositeArtifactsServiceAdapter."""
        from mcp_server_langgraph.storage.artifacts.factory import (
            create_artifacts_service,
        )
        from mcp_server_langgraph.storage.artifacts.service_adapter import (
            CompositeArtifactsServiceAdapter,
        )

        # Create with mock dependencies
        with patch(
            "mcp_server_langgraph.storage.artifacts.factory.PostgresArtifactsRepository"
        ) as mock_pg, patch(
            "mcp_server_langgraph.storage.artifacts.factory.RedisCachedArtifactsService"
        ) as mock_redis, patch(
            "mcp_server_langgraph.storage.artifacts.factory.HybridCloudStorageService"
        ) as mock_cloud, patch(
            "mcp_server_langgraph.storage.artifacts.factory.QdrantArtifactVectorService"
        ) as mock_qdrant:
            mock_pg.return_value = MagicMock()
            mock_redis.return_value = MagicMock()
            mock_cloud.return_value = MagicMock()
            mock_qdrant.return_value = MagicMock()

            result = create_artifacts_service(
                db_session_factory=MagicMock(),
                redis_client=MagicMock(),
            )

            assert isinstance(result, CompositeArtifactsServiceAdapter)

    def test_create_with_optional_qdrant_disabled(self) -> None:
        """Test that factory works without Qdrant (optional service)."""
        from mcp_server_langgraph.storage.artifacts.factory import (
            create_artifacts_service,
        )

        with patch(
            "mcp_server_langgraph.storage.artifacts.factory.PostgresArtifactsRepository"
        ) as mock_pg, patch(
            "mcp_server_langgraph.storage.artifacts.factory.RedisCachedArtifactsService"
        ) as mock_redis, patch(
            "mcp_server_langgraph.storage.artifacts.factory.HybridCloudStorageService"
        ) as mock_cloud, patch(
            "mcp_server_langgraph.storage.artifacts.factory.QdrantArtifactVectorService"
        ) as mock_qdrant:
            mock_pg.return_value = MagicMock()
            mock_redis.return_value = MagicMock()
            mock_cloud.return_value = MagicMock()
            mock_qdrant.return_value = MagicMock()

            result = create_artifacts_service(
                db_session_factory=MagicMock(),
                redis_client=MagicMock(),
                qdrant_enabled=False,
            )

            # Should still return valid service
            assert result is not None


@pytest.mark.xdist_group(name="test_artifacts_factory")
@pytest.mark.unit
class TestArtifactsServiceFactoryConfiguration:
    """Tests for factory configuration options."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_factory_uses_provided_cloud_provider(self) -> None:
        """Test that factory respects cloud provider configuration."""
        from mcp_server_langgraph.storage.artifacts.factory import (
            create_artifacts_service,
        )

        with patch(
            "mcp_server_langgraph.storage.artifacts.factory.PostgresArtifactsRepository"
        ) as mock_pg, patch(
            "mcp_server_langgraph.storage.artifacts.factory.RedisCachedArtifactsService"
        ) as mock_redis, patch(
            "mcp_server_langgraph.storage.artifacts.factory.HybridCloudStorageService"
        ) as mock_cloud, patch(
            "mcp_server_langgraph.storage.artifacts.factory.QdrantArtifactVectorService"
        ) as mock_qdrant:
            mock_pg.return_value = MagicMock()
            mock_redis.return_value = MagicMock()
            mock_cloud.return_value = MagicMock()
            mock_qdrant.return_value = MagicMock()

            create_artifacts_service(
                db_session_factory=MagicMock(),
                redis_client=MagicMock(),
                cloud_provider="gcs",
            )

            # Cloud storage should be configured with GCS
            mock_cloud.assert_called_once()
            call_kwargs = mock_cloud.call_args[1]
            assert call_kwargs.get("cloud_provider") == "gcs"

    def test_factory_uses_default_cloud_provider(self) -> None:
        """Test that factory uses S3 as default cloud provider."""
        from mcp_server_langgraph.storage.artifacts.factory import (
            create_artifacts_service,
        )

        with patch(
            "mcp_server_langgraph.storage.artifacts.factory.PostgresArtifactsRepository"
        ) as mock_pg, patch(
            "mcp_server_langgraph.storage.artifacts.factory.RedisCachedArtifactsService"
        ) as mock_redis, patch(
            "mcp_server_langgraph.storage.artifacts.factory.HybridCloudStorageService"
        ) as mock_cloud, patch(
            "mcp_server_langgraph.storage.artifacts.factory.QdrantArtifactVectorService"
        ) as mock_qdrant:
            mock_pg.return_value = MagicMock()
            mock_redis.return_value = MagicMock()
            mock_cloud.return_value = MagicMock()
            mock_qdrant.return_value = MagicMock()

            create_artifacts_service(
                db_session_factory=MagicMock(),
                redis_client=MagicMock(),
            )

            mock_cloud.assert_called_once()
            call_kwargs = mock_cloud.call_args[1]
            assert call_kwargs.get("cloud_provider") == "s3"

    def test_factory_configures_content_size_threshold(self) -> None:
        """Test that factory passes content size threshold to cloud storage."""
        from mcp_server_langgraph.storage.artifacts.factory import (
            create_artifacts_service,
        )

        with patch(
            "mcp_server_langgraph.storage.artifacts.factory.PostgresArtifactsRepository"
        ) as mock_pg, patch(
            "mcp_server_langgraph.storage.artifacts.factory.RedisCachedArtifactsService"
        ) as mock_redis, patch(
            "mcp_server_langgraph.storage.artifacts.factory.HybridCloudStorageService"
        ) as mock_cloud, patch(
            "mcp_server_langgraph.storage.artifacts.factory.QdrantArtifactVectorService"
        ) as mock_qdrant:
            mock_pg.return_value = MagicMock()
            mock_redis.return_value = MagicMock()
            mock_cloud.return_value = MagicMock()
            mock_qdrant.return_value = MagicMock()

            create_artifacts_service(
                db_session_factory=MagicMock(),
                redis_client=MagicMock(),
                content_size_threshold=500_000,  # 500KB
            )

            mock_cloud.assert_called_once()
            call_kwargs = mock_cloud.call_args[1]
            assert call_kwargs.get("size_threshold") == 500_000


@pytest.mark.xdist_group(name="test_artifacts_factory")
@pytest.mark.unit
class TestArtifactsServiceFactoryNoOpVector:
    """Tests for NoOp vector service when Qdrant is disabled."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_noop_vector_service_returns_empty_on_search(self) -> None:
        """Test that NoOp vector service returns empty list for search."""
        from mcp_server_langgraph.storage.artifacts.factory import (
            NoOpVectorService,
        )

        service = NoOpVectorService()
        results = await service.search(query="test", user_id="user1", limit=10)

        assert results == []

    @pytest.mark.asyncio
    async def test_noop_vector_service_returns_empty_on_find_similar(self) -> None:
        """Test that NoOp vector service returns empty list for find_similar."""
        from mcp_server_langgraph.storage.artifacts.factory import (
            NoOpVectorService,
        )

        service = NoOpVectorService()
        results = await service.find_similar(
            artifact_id="art-1", user_id="user1", limit=5
        )

        assert results == []

    @pytest.mark.asyncio
    async def test_noop_vector_service_index_succeeds(self) -> None:
        """Test that NoOp vector service index operation succeeds silently."""
        from mcp_server_langgraph.storage.artifacts.factory import (
            NoOpVectorService,
        )

        service = NoOpVectorService()
        # Should not raise
        await service.index(artifact={"id": "art-1", "content": "test"}, user_id="user1")

    @pytest.mark.asyncio
    async def test_noop_vector_service_delete_succeeds(self) -> None:
        """Test that NoOp vector service delete operation succeeds silently."""
        from mcp_server_langgraph.storage.artifacts.factory import (
            NoOpVectorService,
        )

        service = NoOpVectorService()
        # Should not raise
        await service.delete(artifact_id="art-1")
