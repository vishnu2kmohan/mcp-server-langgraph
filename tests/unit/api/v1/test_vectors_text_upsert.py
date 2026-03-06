"""
Tests for Vectors Text Upsert Endpoint

TDD tests for POST /api/v1/vectors/upsert-text endpoint.
This endpoint allows upserting vectors using natural language text
instead of raw vector embeddings.
"""

import gc
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_vectors_text")
class TestVectorsTextUpsertEndpoint:
    """Tests for POST /api/v1/vectors/upsert-text endpoint."""

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
            require_editor_permission,
            router as vectors_router,
        )

        app = FastAPI()
        app.include_router(vectors_router, prefix="/api/v1/vectors")

        # Override auth dependency
        async def mock_auth() -> dict[str, Any]:
            return {"preferred_username": "test-user"}

        app.dependency_overrides[require_editor_permission] = mock_auth

        # Override Qdrant dependency
        if mock_qdrant:
            app.dependency_overrides[get_qdrant_client] = lambda: mock_qdrant

        # Override embedding model dependency
        if mock_embeddings:
            app.dependency_overrides[get_embedding_model] = lambda: mock_embeddings

        return app

    @pytest.mark.asyncio
    async def test_upsert_text_returns_200_with_result(self) -> None:
        """POST /api/v1/vectors/upsert-text should return 200 with upsert result."""
        mock_embedding = [0.1] * 384

        mock_model = MagicMock()
        mock_model.embed_query.return_value = mock_embedding

        mock_qdrant = MagicMock()
        mock_qdrant.upsert = AsyncMock(return_value=None)

        app = self._create_app_with_mocks(mock_qdrant=mock_qdrant, mock_embeddings=mock_model)
        client = TestClient(app)

        response = client.post(
            "/api/v1/vectors/upsert-text",
            json={
                "collection_name": "test-collection",
                "text": "This is a sample document to embed",
                "metadata": {"source": "test"},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["collection"] == "test-collection"
        assert "point_id" in data
        assert data["status"] == "created"

    @pytest.mark.asyncio
    async def test_upsert_text_uses_embedding_model(self) -> None:
        """POST /api/v1/vectors/upsert-text should use embedding model to convert text to vector."""
        mock_embedding = [0.5] * 768

        mock_model = MagicMock()
        mock_model.embed_query.return_value = mock_embedding

        mock_qdrant = MagicMock()
        mock_qdrant.upsert = AsyncMock(return_value=None)

        app = self._create_app_with_mocks(mock_qdrant=mock_qdrant, mock_embeddings=mock_model)
        client = TestClient(app)

        client.post(
            "/api/v1/vectors/upsert-text",
            json={"collection_name": "test-collection", "text": "sample text"},
        )

        # Verify embedding model was called with the text
        mock_model.embed_query.assert_called_once_with("sample text")

    @pytest.mark.asyncio
    async def test_upsert_text_calls_qdrant_upsert(self) -> None:
        """POST /api/v1/vectors/upsert-text should call Qdrant upsert."""
        mock_embedding = [0.1] * 384

        mock_model = MagicMock()
        mock_model.embed_query.return_value = mock_embedding

        mock_qdrant = MagicMock()
        mock_qdrant.upsert = AsyncMock(return_value=None)

        app = self._create_app_with_mocks(mock_qdrant=mock_qdrant, mock_embeddings=mock_model)
        client = TestClient(app)

        client.post(
            "/api/v1/vectors/upsert-text",
            json={"collection_name": "test-collection", "text": "sample text", "metadata": {"key": "value"}},
        )

        # Verify Qdrant upsert was called
        mock_qdrant.upsert.assert_called_once()
        call_kwargs = mock_qdrant.upsert.call_args[1]
        assert call_kwargs["collection_name"] == "test-collection"
        assert len(call_kwargs["points"]) == 1

    @pytest.mark.asyncio
    async def test_upsert_text_generates_uuid_for_point(self) -> None:
        """POST /api/v1/vectors/upsert-text should generate a UUID for the point."""
        mock_model = MagicMock()
        mock_model.embed_query.return_value = [0.1] * 384

        mock_qdrant = MagicMock()
        mock_qdrant.upsert = AsyncMock(return_value=None)

        app = self._create_app_with_mocks(mock_qdrant=mock_qdrant, mock_embeddings=mock_model)
        client = TestClient(app)

        response = client.post(
            "/api/v1/vectors/upsert-text",
            json={"collection_name": "test-collection", "text": "sample text"},
        )

        data = response.json()
        point_id = data["point_id"]

        # Verify it looks like a UUID (36 chars with hyphens)
        assert len(point_id) == 36
        assert point_id.count("-") == 4

    @pytest.mark.asyncio
    async def test_upsert_text_stores_original_text_in_payload(self) -> None:
        """POST /api/v1/vectors/upsert-text should store the original text in payload."""
        mock_model = MagicMock()
        mock_model.embed_query.return_value = [0.1] * 384

        mock_qdrant = MagicMock()
        mock_qdrant.upsert = AsyncMock(return_value=None)

        app = self._create_app_with_mocks(mock_qdrant=mock_qdrant, mock_embeddings=mock_model)
        client = TestClient(app)

        client.post(
            "/api/v1/vectors/upsert-text",
            json={"collection_name": "test-collection", "text": "My important text"},
        )

        # Verify the payload includes the original text
        call_kwargs = mock_qdrant.upsert.call_args[1]
        point = call_kwargs["points"][0]
        assert point.payload.get("text") == "My important text"

    @pytest.mark.asyncio
    async def test_upsert_text_includes_metadata_in_payload(self) -> None:
        """POST /api/v1/vectors/upsert-text should include metadata in payload."""
        mock_model = MagicMock()
        mock_model.embed_query.return_value = [0.1] * 384

        mock_qdrant = MagicMock()
        mock_qdrant.upsert = AsyncMock(return_value=None)

        app = self._create_app_with_mocks(mock_qdrant=mock_qdrant, mock_embeddings=mock_model)
        client = TestClient(app)

        client.post(
            "/api/v1/vectors/upsert-text",
            json={
                "collection_name": "test-collection",
                "text": "sample text",
                "metadata": {"source": "user-upload", "category": "documents"},
            },
        )

        call_kwargs = mock_qdrant.upsert.call_args[1]
        point = call_kwargs["points"][0]
        assert point.payload.get("source") == "user-upload"
        assert point.payload.get("category") == "documents"

    @pytest.mark.asyncio
    async def test_upsert_text_requires_collection_name(self) -> None:
        """POST /api/v1/vectors/upsert-text should require collection_name."""
        mock_model = MagicMock()

        app = self._create_app_with_mocks(mock_qdrant=MagicMock(), mock_embeddings=mock_model)
        client = TestClient(app)

        response = client.post("/api/v1/vectors/upsert-text", json={"text": "test"})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_upsert_text_requires_text(self) -> None:
        """POST /api/v1/vectors/upsert-text should require text."""
        mock_model = MagicMock()

        app = self._create_app_with_mocks(mock_qdrant=MagicMock(), mock_embeddings=mock_model)
        client = TestClient(app)

        response = client.post("/api/v1/vectors/upsert-text", json={"collection_name": "test-collection"})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_upsert_text_metadata_is_optional(self) -> None:
        """POST /api/v1/vectors/upsert-text should work without metadata."""
        mock_model = MagicMock()
        mock_model.embed_query.return_value = [0.1] * 384

        mock_qdrant = MagicMock()
        mock_qdrant.upsert = AsyncMock(return_value=None)

        app = self._create_app_with_mocks(mock_qdrant=mock_qdrant, mock_embeddings=mock_model)
        client = TestClient(app)

        response = client.post(
            "/api/v1/vectors/upsert-text",
            json={"collection_name": "test-collection", "text": "sample text"},
        )

        assert response.status_code == 200


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_vectors_text")
class TestTextUpsertRequestModel:
    """Tests for TextUpsertRequest model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_text_upsert_request_model(self) -> None:
        """TextUpsertRequest model should validate required fields."""
        from mcp_server_langgraph.api.v1.vectors import TextUpsertRequest

        request = TextUpsertRequest(
            collection_name="my-collection",
            text="document content to embed",
        )

        assert request.collection_name == "my-collection"
        assert request.text == "document content to embed"
        assert request.metadata == {}  # default

    def test_text_upsert_request_with_metadata(self) -> None:
        """TextUpsertRequest should accept metadata."""
        from mcp_server_langgraph.api.v1.vectors import TextUpsertRequest

        request = TextUpsertRequest(
            collection_name="my-collection",
            text="document content",
            metadata={"source": "api", "user": "test-user"},
        )

        assert request.metadata == {"source": "api", "user": "test-user"}
