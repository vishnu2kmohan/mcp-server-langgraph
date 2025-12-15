"""
Tests for Vectors Text Search Endpoint

TDD tests for POST /api/v1/vectors/search-text endpoint.
This endpoint allows searching vectors using natural language text
instead of raw vector embeddings.
"""

import gc
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_vectors_text")
class TestVectorsTextSearchEndpoint:
    """Tests for POST /api/v1/vectors/search-text endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def _create_app_with_mocks(
        self,
        mock_qdrant: MagicMock | None = None,
        mock_embeddings: MagicMock | None = None,
    ) -> FastAPI:
        """Create a FastAPI app with mocked dependencies."""
        from mcp_server_langgraph.api.v1.vectors import (
            get_embedding_model,
            get_qdrant_client,
            require_viewer_permission,
            router as vectors_router,
        )

        app = FastAPI()
        app.include_router(vectors_router, prefix="/api/v1/vectors")

        # Override auth dependency
        async def mock_auth() -> dict[str, Any]:
            return {"preferred_username": "test-user"}

        app.dependency_overrides[require_viewer_permission] = mock_auth

        # Override Qdrant dependency
        if mock_qdrant:
            app.dependency_overrides[get_qdrant_client] = lambda: mock_qdrant

        # Override embedding model dependency
        if mock_embeddings:
            app.dependency_overrides[get_embedding_model] = lambda: mock_embeddings

        return app

    @pytest.mark.asyncio
    async def test_search_text_returns_200_with_results(self) -> None:
        """POST /api/v1/vectors/search-text should return 200 with search results."""
        mock_embedding = [0.1] * 384

        mock_model = MagicMock()
        mock_model.embed_query.return_value = mock_embedding

        mock_qdrant = MagicMock()
        mock_result = MagicMock()
        mock_result.id = "point-1"
        mock_result.score = 0.95
        mock_result.payload = {"text": "Sample result"}
        mock_qdrant.search.return_value = [mock_result]

        app = self._create_app_with_mocks(mock_qdrant=mock_qdrant, mock_embeddings=mock_model)
        client = TestClient(app)

        response = client.post(
            "/api/v1/vectors/search-text",
            json={"collection_name": "test-collection", "query_text": "find similar documents", "limit": 5},
        )

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert len(data["results"]) == 1
        assert data["results"][0]["id"] == "point-1"
        assert data["results"][0]["score"] == 0.95

    @pytest.mark.asyncio
    async def test_search_text_uses_embedding_model(self) -> None:
        """POST /api/v1/vectors/search-text should use embedding model to convert text to vector."""
        mock_embedding = [0.5] * 768

        mock_model = MagicMock()
        mock_model.embed_query.return_value = mock_embedding

        mock_qdrant = MagicMock()
        mock_qdrant.search.return_value = []

        app = self._create_app_with_mocks(mock_qdrant=mock_qdrant, mock_embeddings=mock_model)
        client = TestClient(app)

        client.post(
            "/api/v1/vectors/search-text",
            json={"collection_name": "test-collection", "query_text": "test query"},
        )

        # Verify embedding model was called with the query text
        mock_model.embed_query.assert_called_once_with("test query")

        # Verify Qdrant was called with the generated embedding
        mock_qdrant.search.assert_called_once()
        call_kwargs = mock_qdrant.search.call_args[1]
        assert call_kwargs["query_vector"] == mock_embedding

    @pytest.mark.asyncio
    async def test_search_text_default_limit(self) -> None:
        """POST /api/v1/vectors/search-text should use default limit of 10."""
        mock_model = MagicMock()
        mock_model.embed_query.return_value = [0.1] * 384

        mock_qdrant = MagicMock()
        mock_qdrant.search.return_value = []

        app = self._create_app_with_mocks(mock_qdrant=mock_qdrant, mock_embeddings=mock_model)
        client = TestClient(app)

        client.post(
            "/api/v1/vectors/search-text",
            json={"collection_name": "test-collection", "query_text": "test"},
        )

        call_kwargs = mock_qdrant.search.call_args[1]
        assert call_kwargs["limit"] == 10

    @pytest.mark.asyncio
    async def test_search_text_respects_limit_param(self) -> None:
        """POST /api/v1/vectors/search-text should respect custom limit parameter."""
        mock_model = MagicMock()
        mock_model.embed_query.return_value = [0.1] * 384

        mock_qdrant = MagicMock()
        mock_qdrant.search.return_value = []

        app = self._create_app_with_mocks(mock_qdrant=mock_qdrant, mock_embeddings=mock_model)
        client = TestClient(app)

        client.post(
            "/api/v1/vectors/search-text",
            json={"collection_name": "test-collection", "query_text": "test", "limit": 25},
        )

        call_kwargs = mock_qdrant.search.call_args[1]
        assert call_kwargs["limit"] == 25

    @pytest.mark.asyncio
    async def test_search_text_requires_collection_name(self) -> None:
        """POST /api/v1/vectors/search-text should require collection_name."""
        mock_model = MagicMock()
        mock_model.embed_query.return_value = [0.1] * 384

        app = self._create_app_with_mocks(mock_qdrant=MagicMock(), mock_embeddings=mock_model)
        client = TestClient(app)

        response = client.post("/api/v1/vectors/search-text", json={"query_text": "test"})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_search_text_requires_query_text(self) -> None:
        """POST /api/v1/vectors/search-text should require query_text."""
        mock_model = MagicMock()

        app = self._create_app_with_mocks(mock_qdrant=MagicMock(), mock_embeddings=mock_model)
        client = TestClient(app)

        response = client.post("/api/v1/vectors/search-text", json={"collection_name": "test-collection"})
        assert response.status_code == 422


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_vectors_text")
class TestTextSearchRequestModel:
    """Tests for TextSearchRequest model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_text_search_request_model(self) -> None:
        """TextSearchRequest model should validate required fields."""
        from mcp_server_langgraph.api.v1.vectors import TextSearchRequest

        request = TextSearchRequest(
            collection_name="my-collection",
            query_text="find similar documents",
        )

        assert request.collection_name == "my-collection"
        assert request.query_text == "find similar documents"
        assert request.limit == 10  # default value

    def test_text_search_request_with_custom_limit(self) -> None:
        """TextSearchRequest should accept custom limit."""
        from mcp_server_langgraph.api.v1.vectors import TextSearchRequest

        request = TextSearchRequest(
            collection_name="my-collection",
            query_text="search query",
            limit=50,
        )

        assert request.limit == 50

    def test_text_search_request_limit_bounds(self) -> None:
        """TextSearchRequest limit should be between 1 and 100."""
        from pydantic import ValidationError

        from mcp_server_langgraph.api.v1.vectors import TextSearchRequest

        # Valid limits
        TextSearchRequest(collection_name="test", query_text="query", limit=1)
        TextSearchRequest(collection_name="test", query_text="query", limit=100)

        # Invalid limit (too high)
        with pytest.raises(ValidationError):
            TextSearchRequest(collection_name="test", query_text="query", limit=101)

        # Invalid limit (too low)
        with pytest.raises(ValidationError):
            TextSearchRequest(collection_name="test", query_text="query", limit=0)
