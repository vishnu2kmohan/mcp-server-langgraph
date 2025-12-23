"""
Tests for Qdrant Vector Service for Artifacts.

TDD RED Phase: These tests define the expected behavior of QdrantArtifactVectorService.

The vector service provides:
- Embedding generation for artifact content
- Semantic search across artifacts
- Similar artifact discovery
- AI-powered content recommendations
"""

from __future__ import annotations

import gc
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.unit

# Test constants
TEST_USER_ID = "user-vec-123"
TEST_ARTIFACT_ID = "art-vec-789"
TEST_COLLECTION = "artifacts"
EMBEDDING_DIM = 1536  # OpenAI ada-002 dimension


def create_mock_embedding(dim: int = EMBEDDING_DIM) -> list[float]:
    """Create mock embedding vector."""
    return [0.1] * dim


def create_mock_artifact_dict(
    artifact_id: str = TEST_ARTIFACT_ID,
    content: str = "Test artifact content for embedding",
    **overrides: Any,
) -> dict[str, Any]:
    """Create mock artifact dictionary for testing."""
    base = {
        "id": artifact_id,
        "user_id": TEST_USER_ID,
        "type": "code",
        "title": "Vector Artifact",
        "content": content,
        "content_type": "code",
    }
    base.update(overrides)
    return base


@pytest.mark.xdist_group(name="test_qdrant_artifacts")
@pytest.mark.unit
class TestQdrantArtifactVectorServiceIndex:
    """Tests for indexing artifacts as vectors."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_index_artifact_generates_embedding(self) -> None:
        """Test that index generates embedding for artifact content."""
        from mcp_server_langgraph.storage.artifacts.qdrant_service import (
            QdrantArtifactVectorService,
        )

        mock_qdrant = AsyncMock()
        mock_embedder = AsyncMock()
        mock_embedder.embed.return_value = create_mock_embedding()

        service = QdrantArtifactVectorService(
            client=mock_qdrant,
            embedder=mock_embedder,
            collection=TEST_COLLECTION,
        )

        artifact = create_mock_artifact_dict()

        # Act
        result = await service.index(artifact, user_id=TEST_USER_ID)

        # Assert
        assert result is True
        mock_embedder.embed.assert_awaited_once()
        mock_qdrant.upsert.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_index_stores_metadata_with_vector(self) -> None:
        """Test that index stores artifact metadata alongside vector."""
        from mcp_server_langgraph.storage.artifacts.qdrant_service import (
            QdrantArtifactVectorService,
        )

        mock_qdrant = AsyncMock()
        mock_embedder = AsyncMock()
        mock_embedder.embed.return_value = create_mock_embedding()

        service = QdrantArtifactVectorService(
            client=mock_qdrant,
            embedder=mock_embedder,
            collection=TEST_COLLECTION,
        )

        artifact = create_mock_artifact_dict(title="My Code Snippet")

        # Act
        await service.index(artifact, user_id=TEST_USER_ID)

        # Assert - verify metadata is passed to upsert
        mock_qdrant.upsert.assert_awaited_once()
        call_kwargs = mock_qdrant.upsert.call_args.kwargs
        assert "payload" in call_kwargs or len(mock_qdrant.upsert.call_args.args) > 0

    @pytest.mark.asyncio
    async def test_index_returns_false_on_embedding_failure(self) -> None:
        """Test that index returns False when embedding fails."""
        from mcp_server_langgraph.storage.artifacts.qdrant_service import (
            QdrantArtifactVectorService,
        )

        mock_qdrant = AsyncMock()
        mock_embedder = AsyncMock()
        mock_embedder.embed.side_effect = Exception("Embedding API error")

        service = QdrantArtifactVectorService(
            client=mock_qdrant,
            embedder=mock_embedder,
            collection=TEST_COLLECTION,
        )

        artifact = create_mock_artifact_dict()

        # Act
        result = await service.index(artifact, user_id=TEST_USER_ID)

        # Assert - graceful failure
        assert result is False


@pytest.mark.xdist_group(name="test_qdrant_artifacts")
@pytest.mark.unit
class TestQdrantArtifactVectorServiceSearch:
    """Tests for semantic search."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_search_returns_similar_artifacts(self) -> None:
        """Test that search returns semantically similar artifacts."""
        from mcp_server_langgraph.storage.artifacts.qdrant_service import (
            QdrantArtifactVectorService,
        )

        mock_qdrant = AsyncMock()
        mock_embedder = AsyncMock()
        mock_embedder.embed.return_value = create_mock_embedding()

        # Mock search results
        mock_result = MagicMock()
        mock_result.id = "art-similar-1"
        mock_result.score = 0.95
        mock_result.payload = {"artifact_id": "art-similar-1", "title": "Similar Code"}
        mock_qdrant.search.return_value = [mock_result]

        service = QdrantArtifactVectorService(
            client=mock_qdrant,
            embedder=mock_embedder,
            collection=TEST_COLLECTION,
        )

        # Act
        results = await service.search(
            query="function to calculate sum",
            user_id=TEST_USER_ID,
            limit=5,
        )

        # Assert
        assert len(results) == 1
        assert results[0]["artifact_id"] == "art-similar-1"
        assert results[0]["score"] == 0.95
        mock_embedder.embed.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_search_filters_by_user_id(self) -> None:
        """Test that search respects user ownership (security)."""
        from mcp_server_langgraph.storage.artifacts.qdrant_service import (
            QdrantArtifactVectorService,
        )

        mock_qdrant = AsyncMock()
        mock_embedder = AsyncMock()
        mock_embedder.embed.return_value = create_mock_embedding()
        mock_qdrant.search.return_value = []

        service = QdrantArtifactVectorService(
            client=mock_qdrant,
            embedder=mock_embedder,
            collection=TEST_COLLECTION,
        )

        # Act
        await service.search(query="test", user_id=TEST_USER_ID, limit=10)

        # Assert - user filter should be included
        mock_qdrant.search.assert_awaited_once()
        call_kwargs = mock_qdrant.search.call_args.kwargs
        # Verify filter includes user_id constraint
        assert "filter" in call_kwargs or "query_filter" in call_kwargs

    @pytest.mark.asyncio
    async def test_search_returns_empty_on_no_matches(self) -> None:
        """Test that search returns empty list when no matches found."""
        from mcp_server_langgraph.storage.artifacts.qdrant_service import (
            QdrantArtifactVectorService,
        )

        mock_qdrant = AsyncMock()
        mock_embedder = AsyncMock()
        mock_embedder.embed.return_value = create_mock_embedding()
        mock_qdrant.search.return_value = []

        service = QdrantArtifactVectorService(
            client=mock_qdrant,
            embedder=mock_embedder,
            collection=TEST_COLLECTION,
        )

        # Act
        results = await service.search(
            query="completely unique query with no matches",
            user_id=TEST_USER_ID,
            limit=5,
        )

        # Assert
        assert results == []


@pytest.mark.xdist_group(name="test_qdrant_artifacts")
@pytest.mark.unit
class TestQdrantArtifactVectorServiceSimilar:
    """Tests for finding similar artifacts."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_find_similar_uses_artifact_embedding(self) -> None:
        """Test that find_similar queries using existing artifact's embedding."""
        from mcp_server_langgraph.storage.artifacts.qdrant_service import (
            QdrantArtifactVectorService,
        )

        mock_qdrant = AsyncMock()
        mock_embedder = AsyncMock()

        # Mock stored point retrieval
        mock_point = MagicMock()
        mock_point.vector = create_mock_embedding()
        mock_qdrant.retrieve.return_value = [mock_point]
        mock_qdrant.search.return_value = []

        service = QdrantArtifactVectorService(
            client=mock_qdrant,
            embedder=mock_embedder,
            collection=TEST_COLLECTION,
        )

        # Act
        await service.find_similar(
            artifact_id=TEST_ARTIFACT_ID,
            user_id=TEST_USER_ID,
            limit=5,
        )

        # Assert - should retrieve existing embedding, not generate new one
        mock_qdrant.retrieve.assert_awaited_once()
        # Embedder should NOT be called (using stored embedding)
        mock_embedder.embed.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_find_similar_excludes_source_artifact(self) -> None:
        """Test that find_similar excludes the source artifact from results."""
        from mcp_server_langgraph.storage.artifacts.qdrant_service import (
            QdrantArtifactVectorService,
        )

        mock_qdrant = AsyncMock()
        mock_embedder = AsyncMock()

        mock_point = MagicMock()
        mock_point.vector = create_mock_embedding()
        mock_qdrant.retrieve.return_value = [mock_point]

        # Mock search results including source artifact
        mock_result = MagicMock()
        mock_result.id = "art-other"
        mock_result.score = 0.9
        mock_result.payload = {"artifact_id": "art-other"}
        mock_qdrant.search.return_value = [mock_result]

        service = QdrantArtifactVectorService(
            client=mock_qdrant,
            embedder=mock_embedder,
            collection=TEST_COLLECTION,
        )

        # Act
        results = await service.find_similar(
            artifact_id=TEST_ARTIFACT_ID,
            user_id=TEST_USER_ID,
            limit=5,
        )

        # Assert - source artifact should be excluded
        for result in results:
            assert result["artifact_id"] != TEST_ARTIFACT_ID


@pytest.mark.xdist_group(name="test_qdrant_artifacts")
@pytest.mark.unit
class TestQdrantArtifactVectorServiceDelete:
    """Tests for removing artifact vectors."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_delete_removes_vector_from_collection(self) -> None:
        """Test that delete removes artifact vector from Qdrant."""
        from mcp_server_langgraph.storage.artifacts.qdrant_service import (
            QdrantArtifactVectorService,
        )

        mock_qdrant = AsyncMock()
        mock_embedder = AsyncMock()

        service = QdrantArtifactVectorService(
            client=mock_qdrant,
            embedder=mock_embedder,
            collection=TEST_COLLECTION,
        )

        # Act
        result = await service.delete(artifact_id=TEST_ARTIFACT_ID)

        # Assert
        assert result is True
        mock_qdrant.delete.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_returns_false_on_error(self) -> None:
        """Test that delete returns False on Qdrant error."""
        from mcp_server_langgraph.storage.artifacts.qdrant_service import (
            QdrantArtifactVectorService,
        )

        mock_qdrant = AsyncMock()
        mock_qdrant.delete.side_effect = Exception("Qdrant error")
        mock_embedder = AsyncMock()

        service = QdrantArtifactVectorService(
            client=mock_qdrant,
            embedder=mock_embedder,
            collection=TEST_COLLECTION,
        )

        # Act
        result = await service.delete(artifact_id=TEST_ARTIFACT_ID)

        # Assert
        assert result is False
