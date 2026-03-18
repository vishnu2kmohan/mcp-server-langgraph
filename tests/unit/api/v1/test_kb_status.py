"""
Tests for KB Status Endpoint.

TDD: These tests are written FIRST to define the expected behavior
of the KB status endpoint for frontend integration.

Tests verify:
1. GET /kb/status returns current KB configuration state
2. Response includes Qdrant connection status
3. Response includes embedding provider info
4. Response includes collection stats (count, vectors)
5. Proper error handling when Qdrant is unavailable
6. Authorization via get_current_user dependency
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

pytestmark = pytest.mark.unit

if TYPE_CHECKING:
    pass


@pytest.mark.xdist_group(name="kb_status")
class TestKBStatusEndpoint:
    """Test suite for KB status endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def mock_current_user(self) -> MagicMock:
        """Create a mock current user."""
        user = MagicMock()
        user.sub = "user-123"
        user.email = "test@example.com"
        return user

    @pytest.fixture
    def app_with_kb_router(self, mock_current_user: MagicMock) -> FastAPI:
        """Create a FastAPI app with the KB router mounted."""
        from mcp_server_langgraph.api.v1.kb import router
        from mcp_server_langgraph.auth.middleware import get_current_user

        app = FastAPI()
        app.include_router(router, prefix="/api/v1/kb")

        # Override auth dependency
        async def _override_current_user():
            return mock_current_user

        app.dependency_overrides[get_current_user] = _override_current_user

        return app

    @pytest.fixture
    def client(self, app_with_kb_router: FastAPI) -> TestClient:
        """Create test client."""
        return TestClient(app_with_kb_router)

    # =========================================================================
    # GET /kb/status endpoint tests
    # =========================================================================

    def test_get_kb_status_returns_200(
        self,
        client: TestClient,
    ) -> None:
        """GIVEN a configured KB system
        WHEN GET /kb/status is called
        THEN it returns 200 with status information
        """
        with patch("mcp_server_langgraph.api.v1.kb.get_kb_status") as mock_get_status:
            mock_get_status.return_value = {
                "status": "ready",
                "qdrant_connected": True,
                "collection_name": "agent_studio_context",
                "vectors_count": 1500,
                "embedding_provider": "google_vertex",
                "embedding_model": "text-embedding-005",
                "embedding_dimensions": 768,
                "last_updated": "2025-01-06T12:00:00Z",
            }

            response = client.get("/api/v1/kb/status")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ready"
            assert data["qdrant_connected"] is True

    def test_get_kb_status_includes_collection_info(
        self,
        client: TestClient,
    ) -> None:
        """GIVEN a KB system with configured collection
        WHEN GET /kb/status is called
        THEN it includes collection name and vector count
        """
        with patch("mcp_server_langgraph.api.v1.kb.get_kb_status") as mock_get_status:
            mock_get_status.return_value = {
                "status": "ready",
                "qdrant_connected": True,
                "collection_name": "agent_studio_context",
                "vectors_count": 2500,
                "embedding_provider": "google_vertex",
                "embedding_model": "text-embedding-005",
                "embedding_dimensions": 768,
                "last_updated": "2025-01-06T12:00:00Z",
            }

            response = client.get("/api/v1/kb/status")

            data = response.json()
            assert data["collection_name"] == "agent_studio_context"
            assert data["vectors_count"] == 2500

    def test_get_kb_status_includes_embedding_info(
        self,
        client: TestClient,
    ) -> None:
        """GIVEN a KB system with configured embedding provider
        WHEN GET /kb/status is called
        THEN it includes embedding provider and model info
        """
        with patch("mcp_server_langgraph.api.v1.kb.get_kb_status") as mock_get_status:
            mock_get_status.return_value = {
                "status": "ready",
                "qdrant_connected": True,
                "collection_name": "agent_studio_context",
                "vectors_count": 1000,
                "embedding_provider": "openai",
                "embedding_model": "text-embedding-3-small",
                "embedding_dimensions": 1536,
                "last_updated": "2025-01-06T12:00:00Z",
            }

            response = client.get("/api/v1/kb/status")

            data = response.json()
            assert data["embedding_provider"] == "openai"
            assert data["embedding_model"] == "text-embedding-3-small"
            assert data["embedding_dimensions"] == 1536

    def test_get_kb_status_returns_misconfigured_when_qdrant_unavailable(
        self,
        client: TestClient,
    ) -> None:
        """GIVEN Qdrant is not configured
        WHEN GET /kb/status is called
        THEN it returns misconfigured status with guidance
        """
        with patch("mcp_server_langgraph.api.v1.kb.get_kb_status") as mock_get_status:
            mock_get_status.return_value = {
                "status": "misconfigured",
                "qdrant_connected": False,
                "collection_name": None,
                "vectors_count": 0,
                "embedding_provider": None,
                "embedding_model": None,
                "embedding_dimensions": None,
                "last_updated": None,
                "message": "Qdrant URL not configured. Set QDRANT_URL environment variable.",
            }

            response = client.get("/api/v1/kb/status")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "misconfigured"
            assert data["qdrant_connected"] is False
            assert "message" in data

    def test_get_kb_status_returns_unavailable_when_connection_fails(
        self,
        client: TestClient,
    ) -> None:
        """GIVEN Qdrant connection fails
        WHEN GET /kb/status is called
        THEN it returns unavailable status
        """
        with patch("mcp_server_langgraph.api.v1.kb.get_kb_status") as mock_get_status:
            mock_get_status.return_value = {
                "status": "unavailable",
                "qdrant_connected": False,
                "collection_name": "agent_studio_context",
                "vectors_count": 0,
                "embedding_provider": "google_vertex",
                "embedding_model": "text-embedding-005",
                "embedding_dimensions": 768,
                "last_updated": None,
                "message": "Unable to connect to Qdrant at localhost:6333",
            }

            response = client.get("/api/v1/kb/status")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "unavailable"
            assert "Unable to connect" in data["message"]

    def test_get_kb_status_includes_context_budget_info(
        self,
        client: TestClient,
    ) -> None:
        """GIVEN a configured KB system
        WHEN GET /kb/status is called
        THEN it includes context token budget information
        """
        with patch("mcp_server_langgraph.api.v1.kb.get_kb_status") as mock_get_status:
            mock_get_status.return_value = {
                "status": "ready",
                "qdrant_connected": True,
                "collection_name": "agent_studio_context",
                "vectors_count": 1500,
                "embedding_provider": "google_vertex",
                "embedding_model": "text-embedding-005",
                "embedding_dimensions": 768,
                "last_updated": "2025-01-06T12:00:00Z",
                "context_token_budget": 2000,
                "context_top_k": 5,
            }

            response = client.get("/api/v1/kb/status")

            data = response.json()
            assert data["context_token_budget"] == 2000
            assert data["context_top_k"] == 5

    def test_get_kb_status_handles_exception_gracefully(
        self,
        client: TestClient,
    ) -> None:
        """GIVEN an unexpected error occurs
        WHEN GET /kb/status is called
        THEN it returns 500 with error details
        """
        with patch("mcp_server_langgraph.api.v1.kb.get_kb_status") as mock_get_status:
            mock_get_status.side_effect = Exception("Unexpected error")

            response = client.get("/api/v1/kb/status")

            assert response.status_code == 500
            data = response.json()
            assert "detail" in data


@pytest.mark.xdist_group(name="kb_status")
class TestKBStatusResponse:
    """Test suite for KB status response model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_kb_status_response_model_ready(self) -> None:
        """GIVEN valid KB status data
        WHEN creating KBStatusResponse
        THEN it validates correctly
        """
        from mcp_server_langgraph.api.v1.kb import KBStatusResponse

        response = KBStatusResponse(
            status="ready",
            qdrant_connected=True,
            collection_name="agent_studio_context",
            vectors_count=1500,
            embedding_provider="google_vertex",
            embedding_model="text-embedding-005",
            embedding_dimensions=768,
        )

        assert response.status == "ready"
        assert response.qdrant_connected is True
        assert response.collection_name == "agent_studio_context"

    def test_kb_status_response_model_misconfigured(self) -> None:
        """GIVEN misconfigured KB data
        WHEN creating KBStatusResponse
        THEN it validates with None values
        """
        from mcp_server_langgraph.api.v1.kb import KBStatusResponse

        response = KBStatusResponse(
            status="misconfigured",
            qdrant_connected=False,
            message="Missing QDRANT_URL configuration",
        )

        assert response.status == "misconfigured"
        assert response.qdrant_connected is False
        assert response.collection_name is None
        assert response.message == "Missing QDRANT_URL configuration"

    def test_kb_status_enum_values(self) -> None:
        """GIVEN KBStatus enum
        WHEN checking values
        THEN it has ready, misconfigured, and unavailable
        """
        from mcp_server_langgraph.api.v1.kb import KBStatus

        assert KBStatus.READY == "ready"
        assert KBStatus.MISCONFIGURED == "misconfigured"
        assert KBStatus.UNAVAILABLE == "unavailable"
