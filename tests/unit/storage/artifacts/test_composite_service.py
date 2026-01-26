"""
Tests for Composite ArtifactsService.

TDD RED Phase: These tests define the expected behavior of the composite
ArtifactsService that orchestrates all storage layers:
- PostgreSQL: Primary storage with versioning
- Redis: Cache layer for hot artifacts
- Cloud Storage: Hybrid storage for large content
- Qdrant: Vector embeddings for AI features
"""

from __future__ import annotations

import gc
from typing import Any
from unittest.mock import AsyncMock

import pytest

pytestmark = pytest.mark.unit

# Test constants
TEST_USER_ID = "user-comp-123"
TEST_SESSION_ID = "session-comp-456"
TEST_ARTIFACT_ID = "art-comp-789"


def create_test_artifact(
    artifact_id: str = TEST_ARTIFACT_ID,
    **overrides: Any,
) -> dict[str, Any]:
    """Create test artifact dictionary."""
    base = {
        "id": artifact_id,
        "session_id": TEST_SESSION_ID,
        "user_id": TEST_USER_ID,
        "type": "code",
        "title": "Test Artifact",
        "content": "def hello(): pass",
        "content_type": "code",
        "version": 1,
        "storage_type": "inline",
        "storage_key": None,
    }
    base.update(overrides)
    return base


@pytest.mark.xdist_group(name="test_composite_service")
@pytest.mark.unit
class TestCompositeArtifactsServiceCreate:
    """Tests for artifact creation through composite service."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_create_stores_in_db_and_indexes_vector(self) -> None:
        """Test that create stores artifact in DB and indexes in Qdrant."""
        from mcp_server_langgraph.storage.artifacts.composite_service import (
            CompositeArtifactsService,
        )

        mock_cached_service = AsyncMock(return_value=None)
        mock_cloud_storage = AsyncMock(return_value=None)
        mock_vector_service = AsyncMock(return_value=None)

        # Mock DB create returns artifact
        created_artifact = create_test_artifact()
        mock_cached_service.create.return_value = created_artifact
        mock_cloud_storage.upload.return_value = {
            "storage_type": "inline",
            "storage_key": None,
        }
        mock_vector_service.index.return_value = True

        service = CompositeArtifactsService(
            cached_service=mock_cached_service,
            cloud_storage=mock_cloud_storage,
            vector_service=mock_vector_service,
        )

        # Act
        result = await service.create(
            session_id=TEST_SESSION_ID,
            user_id=TEST_USER_ID,
            artifact_type="code",
            title="Test Artifact",
            content="def hello(): pass",
            content_type="code",
        )

        # Assert
        assert result is not None
        assert result["id"] == TEST_ARTIFACT_ID
        mock_cached_service.create.assert_awaited_once()
        # Vector indexing should happen
        mock_vector_service.index.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_uses_cloud_storage_for_large_content(self) -> None:
        """Test that create routes large content to cloud storage."""
        from mcp_server_langgraph.storage.artifacts.composite_service import (
            CompositeArtifactsService,
        )

        mock_cached_service = AsyncMock(return_value=None)
        mock_cloud_storage = AsyncMock(return_value=None)
        mock_vector_service = AsyncMock(return_value=None)

        large_content = "x" * 200_000  # 200KB
        created_artifact = create_test_artifact(
            content=large_content,
            storage_type="s3",
            storage_key="artifacts/art-comp-789/abc123",
        )
        mock_cached_service.create.return_value = created_artifact
        mock_cloud_storage.upload.return_value = {
            "storage_type": "s3",
            "storage_key": "artifacts/art-comp-789/abc123",
        }
        mock_vector_service.index.return_value = True

        service = CompositeArtifactsService(
            cached_service=mock_cached_service,
            cloud_storage=mock_cloud_storage,
            vector_service=mock_vector_service,
        )

        # Act
        result = await service.create(
            session_id=TEST_SESSION_ID,
            user_id=TEST_USER_ID,
            artifact_type="code",
            title="Large Artifact",
            content=large_content,
            content_type="code",
        )

        # Assert
        assert result is not None
        mock_cloud_storage.upload.assert_awaited_once()


@pytest.mark.xdist_group(name="test_composite_service")
@pytest.mark.unit
class TestCompositeArtifactsServiceGet:
    """Tests for artifact retrieval through composite service."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_retrieves_from_cached_service(self) -> None:
        """Test that get delegates to cached service."""
        from mcp_server_langgraph.storage.artifacts.composite_service import (
            CompositeArtifactsService,
        )

        mock_cached_service = AsyncMock(return_value=None)
        mock_cloud_storage = AsyncMock(return_value=None)
        mock_vector_service = AsyncMock(return_value=None)

        artifact = create_test_artifact()
        mock_cached_service.get.return_value = artifact

        service = CompositeArtifactsService(
            cached_service=mock_cached_service,
            cloud_storage=mock_cloud_storage,
            vector_service=mock_vector_service,
        )

        # Act
        result = await service.get(artifact_id=TEST_ARTIFACT_ID, user_id=TEST_USER_ID)

        # Assert
        assert result is not None
        assert result["id"] == TEST_ARTIFACT_ID
        mock_cached_service.get.assert_awaited_once_with(artifact_id=TEST_ARTIFACT_ID, user_id=TEST_USER_ID)

    @pytest.mark.asyncio
    async def test_get_fetches_content_from_cloud_when_stored_there(self) -> None:
        """Test that get fetches content from cloud storage when needed."""
        from mcp_server_langgraph.storage.artifacts.composite_service import (
            CompositeArtifactsService,
        )

        mock_cached_service = AsyncMock(return_value=None)
        mock_cloud_storage = AsyncMock(return_value=None)
        mock_vector_service = AsyncMock(return_value=None)

        # Artifact metadata from DB (content is in cloud)
        artifact = create_test_artifact(
            content="",  # Content not inline
            storage_type="s3",
            storage_key="artifacts/art-comp-789/abc123",
        )
        mock_cached_service.get.return_value = artifact
        mock_cloud_storage.download.return_value = "cloud content here"

        service = CompositeArtifactsService(
            cached_service=mock_cached_service,
            cloud_storage=mock_cloud_storage,
            vector_service=mock_vector_service,
        )

        # Act
        result = await service.get(artifact_id=TEST_ARTIFACT_ID, user_id=TEST_USER_ID)

        # Assert - content should be fetched from cloud
        assert result is not None
        assert result["content"] == "cloud content here"
        mock_cloud_storage.download.assert_awaited_once_with("artifacts/art-comp-789/abc123")


@pytest.mark.xdist_group(name="test_composite_service")
@pytest.mark.unit
class TestCompositeArtifactsServiceUpdate:
    """Tests for artifact update through composite service."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_update_updates_db_and_reindexes_vector(self) -> None:
        """Test that update updates DB and reindexes in Qdrant."""
        from mcp_server_langgraph.storage.artifacts.composite_service import (
            CompositeArtifactsService,
        )

        mock_cached_service = AsyncMock(return_value=None)
        mock_cloud_storage = AsyncMock(return_value=None)
        mock_vector_service = AsyncMock(return_value=None)

        updated_artifact = create_test_artifact(
            content="updated content",
            version=2,
        )
        mock_cached_service.update.return_value = updated_artifact
        mock_cloud_storage.upload.return_value = {
            "storage_type": "inline",
            "storage_key": None,
        }
        mock_vector_service.index.return_value = True

        service = CompositeArtifactsService(
            cached_service=mock_cached_service,
            cloud_storage=mock_cloud_storage,
            vector_service=mock_vector_service,
        )

        # Act
        result = await service.update(
            artifact_id=TEST_ARTIFACT_ID,
            user_id=TEST_USER_ID,
            content="updated content",
        )

        # Assert
        assert result is not None
        assert result["version"] == 2
        mock_cached_service.update.assert_awaited_once()
        # Vector should be reindexed
        mock_vector_service.index.assert_awaited_once()


@pytest.mark.xdist_group(name="test_composite_service")
@pytest.mark.unit
class TestCompositeArtifactsServiceDelete:
    """Tests for artifact deletion through composite service."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_delete_removes_from_all_layers(self) -> None:
        """Test that delete removes artifact from DB, cloud, and Qdrant."""
        from mcp_server_langgraph.storage.artifacts.composite_service import (
            CompositeArtifactsService,
        )

        mock_cached_service = AsyncMock(return_value=None)
        mock_cloud_storage = AsyncMock(return_value=None)
        mock_vector_service = AsyncMock(return_value=None)

        # Get returns artifact with cloud storage key
        artifact = create_test_artifact(
            storage_type="s3",
            storage_key="artifacts/art-comp-789/abc123",
        )
        mock_cached_service.get.return_value = artifact
        mock_cached_service.delete.return_value = True
        mock_cloud_storage.delete.return_value = True
        mock_vector_service.delete.return_value = True

        service = CompositeArtifactsService(
            cached_service=mock_cached_service,
            cloud_storage=mock_cloud_storage,
            vector_service=mock_vector_service,
        )

        # Act
        result = await service.delete(
            artifact_id=TEST_ARTIFACT_ID,
            user_id=TEST_USER_ID,
        )

        # Assert
        assert result is True
        mock_cached_service.delete.assert_awaited_once()
        mock_cloud_storage.delete.assert_awaited_once_with("artifacts/art-comp-789/abc123")
        mock_vector_service.delete.assert_awaited_once_with(artifact_id=TEST_ARTIFACT_ID)


@pytest.mark.xdist_group(name="test_composite_service")
@pytest.mark.unit
class TestCompositeArtifactsServiceSearch:
    """Tests for semantic search through composite service."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_semantic_search_uses_vector_service(self) -> None:
        """Test that semantic_search delegates to Qdrant vector service."""
        from mcp_server_langgraph.storage.artifacts.composite_service import (
            CompositeArtifactsService,
        )

        mock_cached_service = AsyncMock(return_value=None)
        mock_cloud_storage = AsyncMock(return_value=None)
        mock_vector_service = AsyncMock(return_value=None)

        mock_vector_service.search.return_value = [
            {"artifact_id": "art-1", "score": 0.95, "title": "Function Sum"},
            {"artifact_id": "art-2", "score": 0.85, "title": "Calculator"},
        ]

        service = CompositeArtifactsService(
            cached_service=mock_cached_service,
            cloud_storage=mock_cloud_storage,
            vector_service=mock_vector_service,
        )

        # Act
        results = await service.semantic_search(
            query="function to add numbers",
            user_id=TEST_USER_ID,
            limit=10,
        )

        # Assert
        assert len(results) == 2
        assert results[0]["artifact_id"] == "art-1"
        assert results[0]["score"] == 0.95
        mock_vector_service.search.assert_awaited_once_with(
            query="function to add numbers",
            user_id=TEST_USER_ID,
            limit=10,
        )

    @pytest.mark.asyncio
    async def test_find_similar_uses_vector_service(self) -> None:
        """Test that find_similar delegates to Qdrant vector service."""
        from mcp_server_langgraph.storage.artifacts.composite_service import (
            CompositeArtifactsService,
        )

        mock_cached_service = AsyncMock(return_value=None)
        mock_cloud_storage = AsyncMock(return_value=None)
        mock_vector_service = AsyncMock(return_value=None)

        mock_vector_service.find_similar.return_value = [
            {"artifact_id": "art-similar-1", "score": 0.9},
        ]

        service = CompositeArtifactsService(
            cached_service=mock_cached_service,
            cloud_storage=mock_cloud_storage,
            vector_service=mock_vector_service,
        )

        # Act
        results = await service.find_similar(
            artifact_id=TEST_ARTIFACT_ID,
            user_id=TEST_USER_ID,
            limit=5,
        )

        # Assert
        assert len(results) == 1
        mock_vector_service.find_similar.assert_awaited_once_with(
            artifact_id=TEST_ARTIFACT_ID,
            user_id=TEST_USER_ID,
            limit=5,
        )


@pytest.mark.xdist_group(name="test_composite_service")
@pytest.mark.unit
class TestCompositeArtifactsServiceGracefulDegradation:
    """Tests for graceful degradation when optional services fail."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_create_succeeds_when_vector_indexing_fails(self) -> None:
        """Test that create succeeds even when vector indexing fails."""
        from mcp_server_langgraph.storage.artifacts.composite_service import (
            CompositeArtifactsService,
        )

        mock_cached_service = AsyncMock(return_value=None)
        mock_cloud_storage = AsyncMock(return_value=None)
        mock_vector_service = AsyncMock(return_value=None)

        created_artifact = create_test_artifact()
        mock_cached_service.create.return_value = created_artifact
        mock_cloud_storage.upload.return_value = {
            "storage_type": "inline",
            "storage_key": None,
        }
        # Vector indexing fails
        mock_vector_service.index.side_effect = Exception("Qdrant unavailable")

        service = CompositeArtifactsService(
            cached_service=mock_cached_service,
            cloud_storage=mock_cloud_storage,
            vector_service=mock_vector_service,
        )

        # Act - should not raise
        result = await service.create(
            session_id=TEST_SESSION_ID,
            user_id=TEST_USER_ID,
            artifact_type="code",
            title="Test Artifact",
            content="def hello(): pass",
            content_type="code",
        )

        # Assert - creation still succeeds
        assert result is not None
        assert result["id"] == TEST_ARTIFACT_ID

    @pytest.mark.asyncio
    async def test_semantic_search_returns_empty_on_vector_failure(self) -> None:
        """Test that semantic_search returns empty list on vector service failure."""
        from mcp_server_langgraph.storage.artifacts.composite_service import (
            CompositeArtifactsService,
        )

        mock_cached_service = AsyncMock(return_value=None)
        mock_cloud_storage = AsyncMock(return_value=None)
        mock_vector_service = AsyncMock(return_value=None)

        # Vector search fails
        mock_vector_service.search.side_effect = Exception("Qdrant timeout")

        service = CompositeArtifactsService(
            cached_service=mock_cached_service,
            cloud_storage=mock_cloud_storage,
            vector_service=mock_vector_service,
        )

        # Act - should not raise
        results = await service.semantic_search(
            query="test query",
            user_id=TEST_USER_ID,
            limit=10,
        )

        # Assert - returns empty list
        assert results == []
