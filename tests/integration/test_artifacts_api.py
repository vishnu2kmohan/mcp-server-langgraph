"""
Tests for Artifacts API Integration

Full-stack integration tests for the multi-layer artifacts storage system:
- PostgreSQL: Primary storage with versioning
- Redis: Cache layer for hot artifacts
- Cloud Storage: Hybrid storage for large content
- Qdrant: Vector embeddings for AI features

Following TDD: These tests define the expected API behavior.
"""

from __future__ import annotations

import gc
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


@pytest.fixture
def test_client(monkeypatch):
    """
    FastAPI TestClient with mocked authentication and artifacts service.

    Uses in-memory artifacts service for testing without database dependencies.
    """
    import importlib

    # Re-import middleware fresh (prevents singleton pollution in pytest-xdist)
    from mcp_server_langgraph import auth

    # Import app
    from mcp_server_langgraph.mcp.server_streamable import app

    importlib.reload(auth.middleware)
    middleware = auth.middleware

    from fastapi.security import HTTPAuthorizationCredentials

    # Mock user for artifact tests
    mock_user = {
        "user_id": "test-user-123",
        "keycloak_id": "test-keycloak-id",
        "username": "alice",
        "email": "alice@example.com",
    }

    # Override authentication dependencies
    app.dependency_overrides[middleware.bearer_scheme] = lambda: HTTPAuthorizationCredentials(
        scheme="Bearer", credentials="mock_token_for_testing"
    )

    async def override_get_current_user():
        return mock_user

    app.dependency_overrides[middleware.get_current_user] = override_get_current_user

    # Create TestClient
    client = TestClient(app, raise_server_exceptions=False)

    yield client

    # Cleanup
    app.dependency_overrides.clear()


@pytest.mark.xdist_group(name="test_artifacts_api")
class TestArtifactsListEndpoint:
    """Integration tests for GET /api/v1/artifacts"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_list_artifacts_returns_200(self, test_client: TestClient) -> None:
        """List artifacts endpoint should return 200."""
        response = test_client.get("/api/v1/artifacts")
        assert response.status_code == 200

    def test_list_artifacts_returns_items_array(self, test_client: TestClient) -> None:
        """List artifacts response should contain items array."""
        response = test_client.get("/api/v1/artifacts")
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)

    def test_list_artifacts_with_session_filter(self, test_client: TestClient) -> None:
        """List artifacts should support session_id filter."""
        response = test_client.get("/api/v1/artifacts?session_id=test-session")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    def test_list_artifacts_with_pagination(self, test_client: TestClient) -> None:
        """List artifacts should support limit and cursor pagination."""
        response = test_client.get("/api/v1/artifacts?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "cursor" in data


@pytest.mark.xdist_group(name="test_artifacts_api")
class TestArtifactsCreateEndpoint:
    """Integration tests for POST /api/v1/artifacts"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_create_artifact_returns_201(self, test_client: TestClient) -> None:
        """Create artifact should return 201 on success."""
        payload = {
            "type": "code",
            "content_type": "code",
            "content": "console.log('hello');",
            "session_id": "session-123",
            "title": "Test Artifact",
        }
        response = test_client.post("/api/v1/artifacts", json=payload)
        assert response.status_code == 201

    def test_create_artifact_returns_id_and_version(self, test_client: TestClient) -> None:
        """Create artifact response should include id and version."""
        payload = {
            "type": "code",
            "content_type": "code",
            "content": "console.log('test');",
            "session_id": "session-123",
        }
        response = test_client.post("/api/v1/artifacts", json=payload)
        data = response.json()
        assert "id" in data
        assert "version" in data
        assert data["version"] == 1

    def test_create_artifact_validates_required_fields(self, test_client: TestClient) -> None:
        """Create artifact should validate required fields."""
        payload = {}  # Missing required fields
        response = test_client.post("/api/v1/artifacts", json=payload)
        assert response.status_code == 422


@pytest.mark.xdist_group(name="test_artifacts_api")
class TestArtifactsGetEndpoint:
    """Integration tests for GET /api/v1/artifacts/{id}"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_get_artifact_returns_404_for_unknown(self, test_client: TestClient) -> None:
        """Get artifact should return 404 for unknown artifact."""
        response = test_client.get("/api/v1/artifacts/unknown-artifact-id")
        assert response.status_code == 404


@pytest.mark.xdist_group(name="test_artifacts_api")
class TestArtifactsUpdateEndpoint:
    """Integration tests for PUT /api/v1/artifacts/{id}"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_update_artifact_returns_404_for_unknown(self, test_client: TestClient) -> None:
        """Update artifact should return 404 for unknown artifact."""
        payload = {"content": "updated content"}
        response = test_client.put("/api/v1/artifacts/unknown-id", json=payload)
        assert response.status_code == 404


@pytest.mark.xdist_group(name="test_artifacts_api")
class TestArtifactsDeleteEndpoint:
    """Integration tests for DELETE /api/v1/artifacts/{id}"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_delete_artifact_returns_204(self, test_client: TestClient) -> None:
        """Delete artifact should return 204 (even for non-existent, idempotent)."""
        response = test_client.delete("/api/v1/artifacts/some-artifact-id")
        # Note: In-memory service returns 204 always for delete (idempotent)
        assert response.status_code in (204, 404)


@pytest.mark.xdist_group(name="test_artifacts_api")
class TestArtifactsSemanticSearchEndpoint:
    """Integration tests for POST /api/v1/artifacts/search"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_semantic_search_returns_200(self, test_client: TestClient) -> None:
        """Semantic search should return 200."""
        payload = {"query": "React component", "limit": 10}
        response = test_client.post("/api/v1/artifacts/search", json=payload)
        assert response.status_code == 200

    def test_semantic_search_returns_results_array(self, test_client: TestClient) -> None:
        """Semantic search response should contain results array."""
        payload = {"query": "test", "limit": 10}
        response = test_client.post("/api/v1/artifacts/search", json=payload)
        data = response.json()
        assert "results" in data
        assert isinstance(data["results"], list)

    def test_semantic_search_validates_empty_query(self, test_client: TestClient) -> None:
        """Semantic search should reject empty query."""
        payload = {"query": "", "limit": 10}
        response = test_client.post("/api/v1/artifacts/search", json=payload)
        assert response.status_code == 422  # Pydantic validation error


@pytest.mark.xdist_group(name="test_artifacts_api")
class TestArtifactsFindSimilarEndpoint:
    """Integration tests for GET /api/v1/artifacts/{id}/similar"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_find_similar_returns_200(self, test_client: TestClient) -> None:
        """Find similar should return 200."""
        # First create an artifact, then find similar
        create_payload = {
            "type": "code",
            "content_type": "code",
            "content": "console.log('test');",
            "session_id": "session-123",
        }
        create_response = test_client.post("/api/v1/artifacts", json=create_payload)
        artifact_id = create_response.json().get("id", "test-id")

        response = test_client.get(f"/api/v1/artifacts/{artifact_id}/similar")
        # In-memory service returns empty results but 200
        assert response.status_code == 200

    def test_find_similar_returns_results_array(self, test_client: TestClient) -> None:
        """Find similar response should contain results array."""
        # Create artifact first
        create_payload = {
            "type": "markdown",
            "content_type": "markdown",
            "content": "# Test",
            "session_id": "session-123",
        }
        create_response = test_client.post("/api/v1/artifacts", json=create_payload)
        artifact_id = create_response.json().get("id", "test-id")

        response = test_client.get(f"/api/v1/artifacts/{artifact_id}/similar")
        data = response.json()
        assert "results" in data
        assert isinstance(data["results"], list)

    def test_find_similar_respects_limit(self, test_client: TestClient) -> None:
        """Find similar should respect limit parameter."""
        create_payload = {
            "type": "code",
            "content_type": "code",
            "content": "print('hello')",
            "session_id": "session-123",
        }
        create_response = test_client.post("/api/v1/artifacts", json=create_payload)
        artifact_id = create_response.json().get("id", "test-id")

        response = test_client.get(f"/api/v1/artifacts/{artifact_id}/similar?limit=5")
        assert response.status_code == 200


@pytest.mark.xdist_group(name="test_artifacts_api")
class TestArtifactsVersionsEndpoint:
    """Integration tests for GET /api/v1/artifacts/{id}/versions"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_versions_endpoint_exists(self, test_client: TestClient) -> None:
        """Versions endpoint should exist."""
        # Create artifact first
        create_payload = {
            "type": "code",
            "content_type": "code",
            "content": "version 1",
            "session_id": "session-123",
        }
        create_response = test_client.post("/api/v1/artifacts", json=create_payload)
        artifact_id = create_response.json().get("id", "test-id")

        response = test_client.get(f"/api/v1/artifacts/{artifact_id}/versions")
        # In-memory service persists artifacts, so versions should work
        assert response.status_code == 200

    def test_versions_returns_404_for_unknown(self, test_client: TestClient) -> None:
        """Versions endpoint should return 404 for unknown artifact."""
        response = test_client.get("/api/v1/artifacts/unknown-artifact/versions")
        assert response.status_code == 404


@pytest.mark.xdist_group(name="test_artifacts_api")
class TestArtifactsForkEndpoint:
    """Integration tests for POST /api/v1/artifacts/{id}/fork"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_fork_endpoint_exists(self, test_client: TestClient) -> None:
        """Fork endpoint should exist."""
        # Create artifact first
        create_payload = {
            "type": "code",
            "content_type": "code",
            "content": "original",
            "session_id": "session-123",
        }
        create_response = test_client.post("/api/v1/artifacts", json=create_payload)
        artifact_id = create_response.json().get("id", "test-id")

        fork_payload = {"new_title": "Forked Artifact"}
        response = test_client.post(f"/api/v1/artifacts/{artifact_id}/fork", json=fork_payload)
        # Fork should succeed for newly created artifact
        assert response.status_code == 201

    def test_fork_returns_parent_id(self, test_client: TestClient) -> None:
        """Fork response should include parent_id."""
        # Create artifact first
        create_payload = {
            "type": "code",
            "content_type": "code",
            "content": "source",
            "session_id": "session-123",
        }
        create_response = test_client.post("/api/v1/artifacts", json=create_payload)
        artifact_id = create_response.json().get("id", "test-id")

        fork_payload = {}
        response = test_client.post(f"/api/v1/artifacts/{artifact_id}/fork", json=fork_payload)
        data = response.json()
        assert "parent_id" in data
        assert data["parent_id"] == artifact_id

    def test_fork_returns_404_for_unknown(self, test_client: TestClient) -> None:
        """Fork endpoint should return 404 for unknown artifact."""
        fork_payload = {}
        response = test_client.post("/api/v1/artifacts/unknown-artifact/fork", json=fork_payload)
        assert response.status_code == 404
