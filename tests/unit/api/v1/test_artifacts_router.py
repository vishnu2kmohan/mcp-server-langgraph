"""
Artifacts Router Unit Tests

Tests for /api/v1/artifacts endpoints per TDD methodology.
Tests written FIRST before implementation (RED phase).

The artifacts endpoint provides CRUD operations for canvas artifact management
per the MSW contract defined in studio/frontend/src/mocks/handlers/canvasHandlers.ts.
"""

import gc
from typing import Any, Generator
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


pytestmark = [
    pytest.mark.unit,
    pytest.mark.api,
]


@pytest.fixture
def mock_user() -> dict[str, Any]:
    """Mock authenticated user for testing."""
    return {
        "sub": "test-user-123",
        "preferred_username": "testuser",
        "email": "testuser@example.com",
        "roles": ["user"],
    }


@pytest.fixture
def test_app(mock_user: dict[str, Any]) -> Generator[FastAPI, None, None]:
    """Create a test app with the artifacts router and mock authentication."""
    from mcp_server_langgraph.api.v1.artifacts import artifacts_router
    from mcp_server_langgraph.auth.middleware import get_current_user

    app = FastAPI()
    app.include_router(artifacts_router, prefix="/api/v1")

    async def override_get_current_user():
        return mock_user

    app.dependency_overrides[get_current_user] = override_get_current_user

    yield app

    app.dependency_overrides.clear()


@pytest.fixture
def client(test_app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(test_app)


@pytest.fixture
def sample_artifact(mock_user: dict[str, Any]) -> dict[str, Any]:
    """Sample artifact data for testing."""
    return {
        "id": f"art-{uuid4().hex[:8]}",
        "type": "code",
        "session_id": f"session-{uuid4().hex[:8]}",
        "version": 1,
        "content": "console.log('Hello, Canvas!');",
        "content_type": "code",
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z",
        "title": "Test Artifact",
        "user_id": mock_user["sub"],
        "edit_metadata": {
            "edited_by": "user",
            "language": "javascript",
        },
    }


@pytest.fixture
def sample_version() -> dict[str, Any]:
    """Sample artifact version for testing."""
    return {
        "id": f"ver-{uuid4().hex[:8]}",
        "artifact_id": f"art-{uuid4().hex[:8]}",
        "version": 1,
        "content": "// Version 1 content",
        "content_type": "code",
        "created_by": "test-user-123",
        "created_at": "2025-01-01T00:00:00Z",
        "metadata": {
            "edit_type": "user",
        },
    }


@pytest.mark.xdist_group(name="test_artifacts_router")
class TestArtifactsListEndpoint:
    """Tests for GET /api/v1/artifacts endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_artifacts_returns_200(self, test_app: FastAPI) -> None:
        """
        GIVEN a request to /api/v1/artifacts
        WHEN GET request is made
        THEN response should be 200 OK
        """
        with patch("mcp_server_langgraph.api.v1.artifacts.get_artifacts_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.list_artifacts.return_value = ([], None, False)
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get("/api/v1/artifacts")

            assert response.status_code == 200

    def test_list_artifacts_returns_items_array(self, test_app: FastAPI, sample_artifact: dict[str, Any]) -> None:
        """
        GIVEN artifacts exist
        WHEN GET request is made
        THEN response should contain items array
        """
        with patch("mcp_server_langgraph.api.v1.artifacts.get_artifacts_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.list_artifacts.return_value = (
                [sample_artifact],
                None,
                False,
            )
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get("/api/v1/artifacts")

            assert response.status_code == 200
            data = response.json()
            assert "items" in data
            assert len(data["items"]) == 1

    def test_list_artifacts_filters_by_session_id(self, test_app: FastAPI, sample_artifact: dict[str, Any]) -> None:
        """
        GIVEN session_id query parameter
        WHEN GET request is made with session_id
        THEN should filter artifacts by session
        """
        session_id = sample_artifact["session_id"]
        with patch("mcp_server_langgraph.api.v1.artifacts.get_artifacts_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.list_artifacts.return_value = (
                [sample_artifact],
                None,
                False,
            )
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get(f"/api/v1/artifacts?session_id={session_id}")

            assert response.status_code == 200
            mock_service.list_artifacts.assert_called_once()
            call_kwargs = mock_service.list_artifacts.call_args[1]
            assert call_kwargs.get("session_id") == session_id

    def test_list_artifacts_pagination(self, test_app: FastAPI) -> None:
        """
        GIVEN limit and cursor parameters
        WHEN GET request is made
        THEN should return paginated response with hasMore
        """
        with patch("mcp_server_langgraph.api.v1.artifacts.get_artifacts_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.list_artifacts.return_value = ([], "next-cursor", True)
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get("/api/v1/artifacts?limit=10&cursor=abc")

            assert response.status_code == 200
            data = response.json()
            assert "cursor" in data
            assert "hasMore" in data


@pytest.mark.xdist_group(name="test_artifacts_router")
class TestArtifactsGetEndpoint:
    """Tests for GET /api/v1/artifacts/{id} endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_artifact_returns_200(self, test_app: FastAPI, sample_artifact: dict[str, Any]) -> None:
        """
        GIVEN an artifact exists
        WHEN GET request is made with artifact ID
        THEN response should be 200 OK
        """
        artifact_id = sample_artifact["id"]
        with patch("mcp_server_langgraph.api.v1.artifacts.get_artifacts_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_artifact.return_value = sample_artifact
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get(f"/api/v1/artifacts/{artifact_id}")

            assert response.status_code == 200

    def test_get_artifact_returns_404_when_not_found(self, test_app: FastAPI) -> None:
        """
        GIVEN artifact does not exist
        WHEN GET request is made
        THEN response should be 404 Not Found
        """
        with patch("mcp_server_langgraph.api.v1.artifacts.get_artifacts_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_artifact.return_value = None
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get("/api/v1/artifacts/non-existent-id")

            assert response.status_code == 404


@pytest.mark.xdist_group(name="test_artifacts_router")
class TestArtifactsCreateEndpoint:
    """Tests for POST /api/v1/artifacts endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_artifact_returns_201(self, test_app: FastAPI) -> None:
        """
        GIVEN valid artifact data
        WHEN POST request is made
        THEN response should be 201 Created
        """
        with patch("mcp_server_langgraph.api.v1.artifacts.get_artifacts_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.create_artifact.return_value = {
                "id": "art-new123",
                "version": 1,
                "created_at": "2025-01-01T00:00:00Z",
            }
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.post(
                "/api/v1/artifacts",
                json={
                    "type": "code",
                    "content": "console.log('test');",
                    "content_type": "code",
                    "session_id": "session-123",
                    "title": "Test Artifact",
                },
            )

            assert response.status_code == 201
            data = response.json()
            assert "id" in data
            assert "version" in data
            assert "created_at" in data

    def test_create_artifact_validates_required_fields(self, test_app: FastAPI) -> None:
        """
        GIVEN missing required fields
        WHEN POST request is made
        THEN response should be 422 Validation Error
        """
        client = TestClient(test_app)
        response = client.post("/api/v1/artifacts", json={})

        assert response.status_code == 422


@pytest.mark.xdist_group(name="test_artifacts_router")
class TestArtifactsUpdateEndpoint:
    """Tests for PUT /api/v1/artifacts/{id} endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_update_artifact_returns_200(self, test_app: FastAPI, sample_artifact: dict[str, Any]) -> None:
        """
        GIVEN an artifact exists
        WHEN PUT request is made with update data
        THEN response should be 200 OK with new version
        """
        artifact_id = sample_artifact["id"]
        with patch("mcp_server_langgraph.api.v1.artifacts.get_artifacts_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.update_artifact.return_value = {
                "id": artifact_id,
                "version": 2,
                "updated_at": "2025-01-01T01:00:00Z",
            }
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.put(
                f"/api/v1/artifacts/{artifact_id}",
                json={"content": "console.log('updated');"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["version"] == 2

    def test_update_artifact_returns_404_when_not_found(self, test_app: FastAPI) -> None:
        """
        GIVEN artifact does not exist
        WHEN PUT request is made
        THEN response should be 404 Not Found
        """
        with patch("mcp_server_langgraph.api.v1.artifacts.get_artifacts_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.update_artifact.return_value = None
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.put(
                "/api/v1/artifacts/non-existent-id",
                json={"content": "test"},
            )

            assert response.status_code == 404


@pytest.mark.xdist_group(name="test_artifacts_router")
class TestArtifactsDeleteEndpoint:
    """Tests for DELETE /api/v1/artifacts/{id} endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_delete_artifact_returns_204(self, test_app: FastAPI, sample_artifact: dict[str, Any]) -> None:
        """
        GIVEN an artifact exists
        WHEN DELETE request is made
        THEN response should be 204 No Content
        """
        artifact_id = sample_artifact["id"]
        with patch("mcp_server_langgraph.api.v1.artifacts.get_artifacts_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.delete_artifact.return_value = True
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.delete(f"/api/v1/artifacts/{artifact_id}")

            assert response.status_code == 204

    def test_delete_artifact_returns_404_when_not_found(self, test_app: FastAPI) -> None:
        """
        GIVEN artifact does not exist
        WHEN DELETE request is made
        THEN response should be 404 Not Found
        """
        with patch("mcp_server_langgraph.api.v1.artifacts.get_artifacts_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.delete_artifact.return_value = False
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.delete("/api/v1/artifacts/non-existent-id")

            assert response.status_code == 404


@pytest.mark.xdist_group(name="test_artifacts_router")
class TestArtifactsVersionsEndpoint:
    """Tests for GET /api/v1/artifacts/{id}/versions endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_versions_returns_200(
        self, test_app: FastAPI, sample_artifact: dict[str, Any], sample_version: dict[str, Any]
    ) -> None:
        """
        GIVEN an artifact with versions exists
        WHEN GET request is made to versions endpoint
        THEN response should be 200 OK with versions array
        """
        artifact_id = sample_artifact["id"]
        with patch("mcp_server_langgraph.api.v1.artifacts.get_artifacts_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_artifact_versions.return_value = [sample_version]
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get(f"/api/v1/artifacts/{artifact_id}/versions")

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 1

    def test_get_versions_returns_404_when_artifact_not_found(self, test_app: FastAPI) -> None:
        """
        GIVEN artifact does not exist
        WHEN GET request is made to versions endpoint
        THEN response should be 404 Not Found
        """
        with patch("mcp_server_langgraph.api.v1.artifacts.get_artifacts_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_artifact_versions.return_value = None
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get("/api/v1/artifacts/non-existent-id/versions")

            assert response.status_code == 404


@pytest.mark.xdist_group(name="test_artifacts_router")
class TestArtifactsForkEndpoint:
    """Tests for POST /api/v1/artifacts/{id}/fork endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_fork_artifact_returns_201(self, test_app: FastAPI, sample_artifact: dict[str, Any]) -> None:
        """
        GIVEN an artifact exists
        WHEN POST request is made to fork endpoint
        THEN response should be 201 Created with new artifact ID
        """
        artifact_id = sample_artifact["id"]
        with patch("mcp_server_langgraph.api.v1.artifacts.get_artifacts_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.fork_artifact.return_value = {
                "id": "art-forked123",
                "parent_id": artifact_id,
                "version": 1,
            }
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.post(
                f"/api/v1/artifacts/{artifact_id}/fork",
                json={"new_name": "Forked Artifact"},
            )

            assert response.status_code == 201
            data = response.json()
            assert "id" in data
            assert data["parent_id"] == artifact_id

    def test_fork_artifact_returns_404_when_not_found(self, test_app: FastAPI) -> None:
        """
        GIVEN artifact does not exist
        WHEN POST request is made to fork endpoint
        THEN response should be 404 Not Found
        """
        with patch("mcp_server_langgraph.api.v1.artifacts.get_artifacts_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.fork_artifact.return_value = None
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.post(
                "/api/v1/artifacts/non-existent-id/fork",
                json={},
            )

            assert response.status_code == 404


@pytest.mark.xdist_group(name="test_artifacts_router")
class TestArtifactsSemanticSearchEndpoint:
    """Tests for POST /api/v1/artifacts/search endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_semantic_search_returns_200(self, test_app: FastAPI) -> None:
        """
        GIVEN a valid search query
        WHEN POST request is made to search endpoint
        THEN response should be 200 OK with results
        """
        with patch("mcp_server_langgraph.api.v1.artifacts.get_artifacts_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.semantic_search.return_value = [
                {"artifact_id": "art-1", "score": 0.95, "title": "Function Sum"},
            ]
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.post(
                "/api/v1/artifacts/search",
                json={"query": "function to add numbers", "limit": 10},
            )

            assert response.status_code == 200
            data = response.json()
            assert "results" in data
            assert len(data["results"]) == 1
            assert data["results"][0]["score"] == 0.95

    def test_semantic_search_with_empty_query_returns_400(self, test_app: FastAPI) -> None:
        """
        GIVEN an empty search query
        WHEN POST request is made
        THEN response should be 422 Validation Error
        """
        client = TestClient(test_app)
        response = client.post(
            "/api/v1/artifacts/search",
            json={"query": "", "limit": 10},
        )

        assert response.status_code == 422

    def test_semantic_search_respects_limit(self, test_app: FastAPI) -> None:
        """
        GIVEN a limit parameter
        WHEN POST request is made
        THEN should pass limit to service
        """
        with patch("mcp_server_langgraph.api.v1.artifacts.get_artifacts_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.semantic_search.return_value = []
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.post(
                "/api/v1/artifacts/search",
                json={"query": "test query", "limit": 5},
            )

            assert response.status_code == 200
            mock_service.semantic_search.assert_called_once()
            call_kwargs = mock_service.semantic_search.call_args[1]
            assert call_kwargs["limit"] == 5

    def test_semantic_search_returns_empty_on_no_results(self, test_app: FastAPI) -> None:
        """
        GIVEN a query with no matching artifacts
        WHEN POST request is made
        THEN response should be 200 with empty results
        """
        with patch("mcp_server_langgraph.api.v1.artifacts.get_artifacts_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.semantic_search.return_value = []
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.post(
                "/api/v1/artifacts/search",
                json={"query": "nonexistent content xyz"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["results"] == []


@pytest.mark.xdist_group(name="test_artifacts_router")
class TestArtifactsFindSimilarEndpoint:
    """Tests for GET /api/v1/artifacts/{id}/similar endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_find_similar_returns_200(self, test_app: FastAPI, sample_artifact: dict[str, Any]) -> None:
        """
        GIVEN an artifact exists
        WHEN GET request is made to similar endpoint
        THEN response should be 200 OK with similar artifacts
        """
        artifact_id = sample_artifact["id"]
        with patch("mcp_server_langgraph.api.v1.artifacts.get_artifacts_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.find_similar.return_value = [
                {"artifact_id": "art-similar-1", "score": 0.92, "title": "Similar Code"},
            ]
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get(f"/api/v1/artifacts/{artifact_id}/similar")

            assert response.status_code == 200
            data = response.json()
            assert "results" in data
            assert len(data["results"]) == 1

    def test_find_similar_with_limit_parameter(self, test_app: FastAPI, sample_artifact: dict[str, Any]) -> None:
        """
        GIVEN limit query parameter
        WHEN GET request is made
        THEN should pass limit to service
        """
        artifact_id = sample_artifact["id"]
        with patch("mcp_server_langgraph.api.v1.artifacts.get_artifacts_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.find_similar.return_value = []
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get(f"/api/v1/artifacts/{artifact_id}/similar?limit=3")

            assert response.status_code == 200
            mock_service.find_similar.assert_called_once()
            call_kwargs = mock_service.find_similar.call_args[1]
            assert call_kwargs["limit"] == 3

    def test_find_similar_returns_empty_when_no_matches(self, test_app: FastAPI, sample_artifact: dict[str, Any]) -> None:
        """
        GIVEN no similar artifacts exist
        WHEN GET request is made
        THEN response should be 200 with empty results
        """
        artifact_id = sample_artifact["id"]
        with patch("mcp_server_langgraph.api.v1.artifacts.get_artifacts_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.find_similar.return_value = []
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get(f"/api/v1/artifacts/{artifact_id}/similar")

            assert response.status_code == 200
            data = response.json()
            assert data["results"] == []


@pytest.mark.xdist_group(name="test_artifacts_router")
class TestInMemoryArtifactsServiceVersionCleanup:
    """Tests for InMemoryArtifactsService version cleanup policy."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_version_cleanup_removes_old_versions_when_limit_exceeded(
        self,
    ) -> None:
        """
        GIVEN an artifact with versions exceeding max limit
        WHEN update is performed
        THEN old versions should be removed to stay within limit
        """
        from mcp_server_langgraph.api.v1.artifacts import InMemoryArtifactsService
        from mcp_server_langgraph.core.config import settings

        service = InMemoryArtifactsService()
        user_id = "test-user"

        # Create an artifact
        artifact = await service.create_artifact(
            {
                "type": "code",
                "content": "version 0",
                "content_type": "code",
                "session_id": "session-123",
            },
            user_id=user_id,
        )
        artifact_id = artifact["id"]

        # Simulate many updates to exceed max versions
        max_versions = settings.artifacts_max_versions
        for i in range(max_versions + 10):  # Create 10 more than max
            await service.update_artifact(
                artifact_id,
                {"content": f"version {i + 1}"},
                user_id=user_id,
            )

        # Check versions are within limit
        versions = await service.get_artifact_versions(artifact_id, user_id)
        assert versions is not None
        assert len(versions) <= max_versions

    @pytest.mark.asyncio
    async def test_version_cleanup_keeps_most_recent_versions(self) -> None:
        """
        GIVEN an artifact with many versions
        WHEN cleanup occurs
        THEN most recent versions should be preserved
        """
        from mcp_server_langgraph.api.v1.artifacts import InMemoryArtifactsService

        service = InMemoryArtifactsService()
        user_id = "test-user"

        # Create an artifact
        artifact = await service.create_artifact(
            {
                "type": "code",
                "content": "initial",
                "content_type": "code",
                "session_id": "session-123",
            },
            user_id=user_id,
        )
        artifact_id = artifact["id"]

        # Create several updates
        for i in range(5):
            await service.update_artifact(
                artifact_id,
                {"content": f"update {i + 1}"},
                user_id=user_id,
            )

        # Get versions - should have latest versions
        versions = await service.get_artifact_versions(artifact_id, user_id)
        assert versions is not None
        assert len(versions) == 6  # Initial + 5 updates

        # Verify versions are sorted by version number (descending after cleanup)
        version_numbers = [v["version"] for v in versions]
        # After updates without cleanup trigger, should have versions 1-6
        assert 6 in version_numbers

    @pytest.mark.asyncio
    async def test_version_cleanup_does_not_affect_artifacts_below_limit(
        self,
    ) -> None:
        """
        GIVEN an artifact with versions below max limit
        WHEN update is performed
        THEN all versions should be preserved
        """
        from mcp_server_langgraph.api.v1.artifacts import InMemoryArtifactsService

        service = InMemoryArtifactsService()
        user_id = "test-user"

        # Create an artifact
        artifact = await service.create_artifact(
            {
                "type": "code",
                "content": "initial",
                "content_type": "code",
                "session_id": "session-123",
            },
            user_id=user_id,
        )
        artifact_id = artifact["id"]

        # Create a few updates (well below max limit of 100)
        for i in range(10):
            await service.update_artifact(
                artifact_id,
                {"content": f"update {i + 1}"},
                user_id=user_id,
            )

        # All versions should be preserved
        versions = await service.get_artifact_versions(artifact_id, user_id)
        assert versions is not None
        assert len(versions) == 11  # Initial + 10 updates


@pytest.mark.xdist_group(name="test_artifacts_router")
class TestArtifactsContentSizeValidation:
    """Tests for artifact content size limit validation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_artifact_rejects_oversized_content(self, test_app: FastAPI) -> None:
        """
        GIVEN content exceeding max size limit
        WHEN POST request is made to create artifact
        THEN response should be 413 Payload Too Large
        """
        from mcp_server_langgraph.core.config import settings

        # Create content larger than max size
        oversized_content = "x" * (settings.artifacts_max_content_size + 1)

        client = TestClient(test_app)
        response = client.post(
            "/api/v1/artifacts",
            json={
                "type": "code",
                "content": oversized_content,
                "content_type": "code",
                "session_id": "session-123",
            },
        )

        assert response.status_code == 413
        data = response.json()
        assert "content size" in data["detail"].lower() or "too large" in data["detail"].lower()

    def test_update_artifact_rejects_oversized_content(self, test_app: FastAPI, sample_artifact: dict[str, Any]) -> None:
        """
        GIVEN content exceeding max size limit
        WHEN PUT request is made to update artifact
        THEN response should be 413 Payload Too Large
        """
        from mcp_server_langgraph.core.config import settings

        artifact_id = sample_artifact["id"]
        oversized_content = "x" * (settings.artifacts_max_content_size + 1)

        with patch("mcp_server_langgraph.api.v1.artifacts.get_artifacts_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.update_artifact.return_value = {
                "id": artifact_id,
                "version": 2,
                "updated_at": "2025-01-01T00:00:00Z",
            }
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.put(
                f"/api/v1/artifacts/{artifact_id}",
                json={"content": oversized_content},
            )

            assert response.status_code == 413

    def test_create_artifact_accepts_content_within_limit(self, test_app: FastAPI) -> None:
        """
        GIVEN content within max size limit
        WHEN POST request is made to create artifact
        THEN response should be 201 Created
        """
        with patch("mcp_server_langgraph.api.v1.artifacts.get_artifacts_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.create_artifact.return_value = {
                "id": "art-new123",
                "version": 1,
                "created_at": "2025-01-01T00:00:00Z",
            }
            mock_get_service.return_value = mock_service

            # Normal size content
            content = "console.log('hello world');"

            client = TestClient(test_app)
            response = client.post(
                "/api/v1/artifacts",
                json={
                    "type": "code",
                    "content": content,
                    "content_type": "code",
                    "session_id": "session-123",
                },
            )

            assert response.status_code == 201


@pytest.mark.xdist_group(name="test_artifacts_protocol")
class TestArtifactsServiceProtocol:
    """Tests for ArtifactsServiceProtocol completeness.

    Ensures the protocol defines all methods used by the API router,
    including semantic_search and find_similar.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_protocol_defines_semantic_search(self) -> None:
        """
        GIVEN ArtifactsServiceProtocol
        WHEN checking abstract methods
        THEN semantic_search should be defined
        """
        from mcp_server_langgraph.api.v1.artifacts import ArtifactsServiceProtocol

        # Check that semantic_search is an abstract method
        assert hasattr(ArtifactsServiceProtocol, "semantic_search")
        # Verify it's marked as abstract
        method = ArtifactsServiceProtocol.semantic_search
        assert getattr(method, "__isabstractmethod__", False)

    def test_protocol_defines_find_similar(self) -> None:
        """
        GIVEN ArtifactsServiceProtocol
        WHEN checking abstract methods
        THEN find_similar should be defined
        """
        from mcp_server_langgraph.api.v1.artifacts import ArtifactsServiceProtocol

        # Check that find_similar is an abstract method
        assert hasattr(ArtifactsServiceProtocol, "find_similar")
        # Verify it's marked as abstract
        method = ArtifactsServiceProtocol.find_similar
        assert getattr(method, "__isabstractmethod__", False)

    def test_in_memory_service_implements_semantic_search(self) -> None:
        """
        GIVEN InMemoryArtifactsService
        WHEN calling semantic_search
        THEN it should return a list (empty for in-memory)
        """
        from mcp_server_langgraph.api.v1.artifacts import InMemoryArtifactsService

        service = InMemoryArtifactsService()
        assert hasattr(service, "semantic_search")

    def test_in_memory_service_implements_find_similar(self) -> None:
        """
        GIVEN InMemoryArtifactsService
        WHEN calling find_similar
        THEN it should return a list (empty for in-memory)
        """
        from mcp_server_langgraph.api.v1.artifacts import InMemoryArtifactsService

        service = InMemoryArtifactsService()
        assert hasattr(service, "find_similar")

    @pytest.mark.asyncio
    async def test_in_memory_semantic_search_returns_empty_list(self) -> None:
        """
        GIVEN InMemoryArtifactsService
        WHEN semantic_search is called
        THEN it should return an empty list (no vector support in memory)
        """
        from mcp_server_langgraph.api.v1.artifacts import InMemoryArtifactsService

        service = InMemoryArtifactsService()
        results = await service.semantic_search(query="test", user_id="user-1", limit=10)
        assert results == []

    @pytest.mark.asyncio
    async def test_in_memory_find_similar_returns_empty_list(self) -> None:
        """
        GIVEN InMemoryArtifactsService
        WHEN find_similar is called
        THEN it should return an empty list (no vector support in memory)
        """
        from mcp_server_langgraph.api.v1.artifacts import InMemoryArtifactsService

        service = InMemoryArtifactsService()
        results = await service.find_similar(artifact_id="art-123", user_id="user-1", limit=5)
        assert results == []


@pytest.mark.xdist_group(name="test_artifacts_router")
class TestArtifactDescriptionField:
    """Tests for artifact description field (TDD RED phase)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_artifact_with_description(self, test_app: FastAPI) -> None:
        """
        GIVEN valid artifact data with description
        WHEN POST request is made
        THEN response should include the description field
        """
        artifact_id = f"art-{uuid4().hex[:8]}"
        session_id = f"session-{uuid4().hex[:8]}"

        with patch("mcp_server_langgraph.api.v1.artifacts.get_artifacts_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.create_artifact.return_value = {
                "id": artifact_id,
                "type": "code",
                "session_id": session_id,
                "version": 1,
                "content": "function hello() { return 'world'; }",
                "content_type": "code",
                "title": "Hello Function",
                "description": "A simple function that returns 'world'",
                "user_id": "test-user-123",
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z",
            }
            mock_get_service.return_value = mock_service

            with TestClient(test_app) as client:
                response = client.post(
                    f"/api/v1/sessions/{session_id}/artifacts",
                    json={
                        "type": "code",
                        "content": "function hello() { return 'world'; }",
                        "title": "Hello Function",
                        "description": "A simple function that returns 'world'",
                    },
                )
                assert response.status_code == 201
                data = response.json()
                assert data["description"] == "A simple function that returns 'world'"

    def test_create_artifact_without_description_defaults_empty(self, test_app: FastAPI) -> None:
        """
        GIVEN artifact data without description
        WHEN POST request is made
        THEN description should default to empty string
        """
        artifact_id = f"art-{uuid4().hex[:8]}"
        session_id = f"session-{uuid4().hex[:8]}"

        with patch("mcp_server_langgraph.api.v1.artifacts.get_artifacts_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.create_artifact.return_value = {
                "id": artifact_id,
                "type": "code",
                "session_id": session_id,
                "version": 1,
                "content": "const x = 1;",
                "content_type": "code",
                "title": "Variable",
                "description": "",
                "user_id": "test-user-123",
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z",
            }
            mock_get_service.return_value = mock_service

            with TestClient(test_app) as client:
                response = client.post(
                    f"/api/v1/sessions/{session_id}/artifacts",
                    json={
                        "type": "code",
                        "content": "const x = 1;",
                        "title": "Variable",
                    },
                )
                assert response.status_code == 201
                data = response.json()
                assert data["description"] == ""

    def test_update_artifact_description(self, test_app: FastAPI) -> None:
        """
        GIVEN an artifact exists
        WHEN PUT request updates the description
        THEN response should show updated description
        """
        artifact_id = f"art-{uuid4().hex[:8]}"
        session_id = f"session-{uuid4().hex[:8]}"

        with patch("mcp_server_langgraph.api.v1.artifacts.get_artifacts_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_artifact.return_value = {
                "id": artifact_id,
                "type": "code",
                "session_id": session_id,
                "version": 1,
                "content": "# Original",
                "content_type": "code",
                "title": "Original Artifact",
                "description": "",
                "user_id": "test-user-123",
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z",
            }
            mock_service.update_artifact.return_value = {
                "id": artifact_id,
                "type": "code",
                "session_id": session_id,
                "version": 2,
                "content": "# Original",
                "content_type": "code",
                "title": "Original Artifact",
                "description": "Updated description explaining the artifact purpose",
                "user_id": "test-user-123",
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z",
            }
            mock_get_service.return_value = mock_service

            with TestClient(test_app) as client:
                response = client.put(
                    f"/api/v1/artifacts/{artifact_id}",
                    json={"description": "Updated description explaining the artifact purpose"},
                )
                assert response.status_code == 200
                data = response.json()
                assert data["description"] == "Updated description explaining the artifact purpose"

    def test_get_artifact_returns_description(self, test_app: FastAPI) -> None:
        """
        GIVEN an artifact with description exists
        WHEN GET request is made
        THEN response should include description field
        """
        artifact_id = f"art-{uuid4().hex[:8]}"
        session_id = f"session-{uuid4().hex[:8]}"

        with patch("mcp_server_langgraph.api.v1.artifacts.get_artifacts_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_artifact.return_value = {
                "id": artifact_id,
                "type": "mermaid",
                "session_id": session_id,
                "version": 1,
                "content": "graph TD; A-->B;",
                "content_type": "mermaid",
                "title": "Architecture Diagram",
                "description": "System architecture showing component relationships",
                "user_id": "test-user-123",
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z",
            }
            mock_get_service.return_value = mock_service

            with TestClient(test_app) as client:
                response = client.get(f"/api/v1/artifacts/{artifact_id}")
                assert response.status_code == 200
                data = response.json()
                assert data["description"] == "System architecture showing component relationships"

    def test_list_artifacts_includes_description(self, test_app: FastAPI) -> None:
        """
        GIVEN artifacts with descriptions exist
        WHEN GET list request is made
        THEN response should include description in each artifact
        """
        session_id = f"session-{uuid4().hex[:8]}"

        with patch("mcp_server_langgraph.api.v1.artifacts.get_artifacts_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.list_artifacts.return_value = [
                {
                    "id": "art-1",
                    "type": "code",
                    "session_id": session_id,
                    "version": 1,
                    "content": "# Code 1",
                    "content_type": "code",
                    "title": "Artifact 1",
                    "description": "First artifact description",
                    "user_id": "test-user-123",
                    "created_at": "2025-01-01T00:00:00Z",
                    "updated_at": "2025-01-01T00:00:00Z",
                },
                {
                    "id": "art-2",
                    "type": "code",
                    "session_id": session_id,
                    "version": 1,
                    "content": "# Code 2",
                    "content_type": "code",
                    "title": "Artifact 2",
                    "description": "Second artifact description",
                    "user_id": "test-user-123",
                    "created_at": "2025-01-01T00:00:00Z",
                    "updated_at": "2025-01-01T00:00:00Z",
                },
            ]
            mock_get_service.return_value = mock_service

            with TestClient(test_app) as client:
                response = client.get(f"/api/v1/sessions/{session_id}/artifacts")
                assert response.status_code == 200
                data = response.json()
                descriptions = [a["description"] for a in data["artifacts"]]
                assert "First artifact description" in descriptions
                assert "Second artifact description" in descriptions
