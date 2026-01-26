"""
Project Context API Tests.

TDD tests for the project context endpoint.

Endpoints tested:
- GET /api/v1/context - Get project context
- PUT /api/v1/context - Update project context
- DELETE /api/v1/context - Delete project context
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from mcp_server_langgraph.api.v1.project_context import (
    project_context_router,
)

# Module-level pytest marker
pytestmark = pytest.mark.unit


# ==============================================================================
# Mock Data
# ==============================================================================

MOCK_PROJECT_CONTEXT = {
    "project_id": "project-123",
    "content": "# Project Context\n\nThis is the project context file.",
    "path": ".studio/context.md",
    "exists": True,
    "last_modified": "2024-12-01T10:00:00Z",
}


# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture
def mock_current_user() -> dict[str, Any]:
    """Mock authenticated user."""
    return {
        "user_id": "user:testuser",
        "username": "testuser",
        "email": "test@example.com",
        "roles": ["user"],
    }


@pytest.fixture
def mock_context_service() -> AsyncMock:
    """Mock context service."""
    service = AsyncMock(return_value=None)  # async-mock-configured (return_value set below)  # noqa: async-mock-config
    service.get_context.return_value = MOCK_PROJECT_CONTEXT
    service.update_context.return_value = MOCK_PROJECT_CONTEXT
    service.delete_context.return_value = True
    return service


@pytest.fixture
def app(mock_current_user: dict[str, Any], mock_context_service: AsyncMock) -> FastAPI:
    """Create test FastAPI app with context router."""
    from mcp_server_langgraph.api.v1.project_context import set_context_service
    from mcp_server_langgraph.auth.middleware import get_current_user

    test_app = FastAPI()

    # Override auth dependency
    async def override_get_current_user() -> dict[str, Any]:
        return mock_current_user

    test_app.dependency_overrides[get_current_user] = override_get_current_user

    # Set mock context service
    set_context_service(mock_context_service)

    test_app.include_router(project_context_router, prefix="/api/v1")

    yield test_app

    # Cleanup
    set_context_service(None)


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create test client."""
    return TestClient(app)


# ==============================================================================
# GET /context Tests
# ==============================================================================


class TestGetContext:
    """Tests for GET /api/v1/context endpoint."""

    def test_get_context_returns_content(self, client: TestClient, mock_context_service: AsyncMock) -> None:
        """Should return project context content."""
        response = client.get("/api/v1/context?project_id=project-123")

        assert response.status_code == 200
        data = response.json()
        assert data["content"] == MOCK_PROJECT_CONTEXT["content"]
        assert data["exists"] is True

    def test_get_context_without_project_id_returns_422(self, client: TestClient) -> None:
        """Missing project_id should return 422."""
        response = client.get("/api/v1/context")

        assert response.status_code == 422

    def test_get_context_not_found_returns_empty(self, client: TestClient, mock_context_service: AsyncMock) -> None:
        """Non-existent context should return empty content with exists=False."""
        mock_context_service.get_context.return_value = {
            "project_id": "project-123",
            "content": "",
            "path": ".studio/context.md",
            "exists": False,
            "last_modified": None,
        }

        response = client.get("/api/v1/context?project_id=project-123")

        assert response.status_code == 200
        data = response.json()
        assert data["exists"] is False
        assert data["content"] == ""


# ==============================================================================
# PUT /context Tests
# ==============================================================================


class TestUpdateContext:
    """Tests for PUT /api/v1/context endpoint."""

    def test_update_context_creates_new(self, client: TestClient, mock_context_service: AsyncMock) -> None:
        """Should create new context file."""
        response = client.put(
            "/api/v1/context",
            json={
                "project_id": "project-123",
                "content": "# New Context\n\nNew content here.",
            },
        )

        assert response.status_code == 200
        mock_context_service.update_context.assert_called_once()

    def test_update_context_modifies_existing(self, client: TestClient, mock_context_service: AsyncMock) -> None:
        """Should update existing context file."""
        updated_content = "# Updated Context\n\nUpdated content."
        mock_context_service.update_context.return_value = {
            **MOCK_PROJECT_CONTEXT,
            "content": updated_content,
        }

        response = client.put(
            "/api/v1/context",
            json={
                "project_id": "project-123",
                "content": updated_content,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["content"] == updated_content

    def test_update_context_validates_content_size(self, client: TestClient) -> None:
        """Content should be validated for max size."""
        # Very large content should be rejected
        large_content = "x" * (1024 * 1024 + 1)  # 1MB + 1 byte

        response = client.put(
            "/api/v1/context",
            json={
                "project_id": "project-123",
                "content": large_content,
            },
        )

        assert response.status_code == 422


# ==============================================================================
# DELETE /context Tests
# ==============================================================================


class TestDeleteContext:
    """Tests for DELETE /api/v1/context endpoint."""

    def test_delete_context_succeeds(self, client: TestClient, mock_context_service: AsyncMock) -> None:
        """Should delete context file."""
        response = client.delete("/api/v1/context?project_id=project-123")

        assert response.status_code == 200
        mock_context_service.delete_context.assert_called_once()

    def test_delete_context_not_found_returns_404(self, client: TestClient, mock_context_service: AsyncMock) -> None:
        """Deleting non-existent context should return 404."""
        mock_context_service.delete_context.return_value = False

        response = client.delete("/api/v1/context?project_id=project-123")

        assert response.status_code == 404


# ==============================================================================
# Response Format Tests
# ==============================================================================


class TestContextResponse:
    """Tests for context response format."""

    def test_response_includes_metadata(self, client: TestClient) -> None:
        """Response should include metadata fields."""
        response = client.get("/api/v1/context?project_id=project-123")

        assert response.status_code == 200
        data = response.json()

        assert "project_id" in data
        assert "content" in data
        assert "path" in data
        assert "exists" in data
        assert "last_modified" in data
