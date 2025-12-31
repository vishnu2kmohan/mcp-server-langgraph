"""
Artifact Description Field Tests

TDD tests for the artifact description field feature.
The description field provides explanatory text for artifacts,
useful for documenting code purpose, diagram context, or content overview.
"""

import gc
from typing import Any
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
def test_app(mock_user: dict[str, Any]) -> FastAPI:
    """Create a test app with the artifacts router and mock authentication."""
    from mcp_server_langgraph.api.v1.artifacts import artifacts_router
    from mcp_server_langgraph.auth.middleware import get_current_user

    app = FastAPI()
    app.include_router(artifacts_router, prefix="/api/v1")

    async def override_get_current_user() -> dict[str, Any]:
        return mock_user

    app.dependency_overrides[get_current_user] = override_get_current_user

    return app


@pytest.mark.xdist_group(name="test_artifact_description_field")
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
            mock_service = AsyncMock()  # noqa: async-mock-config
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
                    "/api/v1/artifacts",
                    json={
                        "type": "code",
                        "content": "function hello() { return 'world'; }",
                        "content_type": "code",
                        "session_id": session_id,
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
            mock_service = AsyncMock()  # noqa: async-mock-config
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
                    "/api/v1/artifacts",
                    json={
                        "type": "code",
                        "content": "const x = 1;",
                        "content_type": "code",
                        "session_id": session_id,
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
            mock_service = AsyncMock()  # noqa: async-mock-config
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
            mock_service = AsyncMock()  # noqa: async-mock-config
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
            mock_service = AsyncMock()  # noqa: async-mock-config
            # list_artifacts returns (items, next_cursor, has_more)
            mock_service.list_artifacts.return_value = (
                [
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
                ],
                None,  # next_cursor
                False,  # has_more
            )
            mock_get_service.return_value = mock_service

            with TestClient(test_app) as client:
                response = client.get(f"/api/v1/artifacts?session_id={session_id}")
                assert response.status_code == 200
                data = response.json()
                descriptions = [a["description"] for a in data["items"]]
                assert "First artifact description" in descriptions
                assert "Second artifact description" in descriptions
