"""
Session Description Field Tests

TDD tests for the session description field feature.
The description field provides longer context for chat sessions,
useful for session summaries, project notes, or AI-generated overviews.
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
    """Create a test app with the sessions router and mock authentication."""
    from mcp_server_langgraph.api.v1.sessions import sessions_router
    from mcp_server_langgraph.auth.middleware import get_current_user

    app = FastAPI()
    app.include_router(sessions_router, prefix="/api/v1")

    async def override_get_current_user() -> dict[str, Any]:
        return mock_user

    app.dependency_overrides[get_current_user] = override_get_current_user

    return app


@pytest.mark.xdist_group(name="test_session_description_field")
class TestSessionDescriptionField:
    """Tests for session description field (TDD RED phase)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_session_with_description(self, test_app: FastAPI) -> None:
        """
        GIVEN valid session data with description
        WHEN POST request is made
        THEN response should include the description field
        """
        with patch("mcp_server_langgraph.api.v1.sessions.get_session_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.create_session.return_value = {
                "id": str(uuid4()),
                "name": "Test Session",
                "description": "A detailed description of this chat session",
                "user_id": "test-user",
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z",
                "status": "active",
            }
            mock_get_service.return_value = mock_service

            with TestClient(test_app) as client:
                response = client.post(
                    "/api/v1/sessions",
                    json={
                        "name": "Test Session",
                        "description": "A detailed description of this chat session",
                    },
                )
                assert response.status_code == 201
                data = response.json()
                assert data["description"] == "A detailed description of this chat session"

    def test_create_session_without_description_defaults_empty(self, test_app: FastAPI) -> None:
        """
        GIVEN session data without description
        WHEN POST request is made
        THEN description should default to empty string
        """
        with patch("mcp_server_langgraph.api.v1.sessions.get_session_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.create_session.return_value = {
                "id": str(uuid4()),
                "name": "Test Session",
                "description": "",
                "user_id": "test-user",
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z",
                "status": "active",
            }
            mock_get_service.return_value = mock_service

            with TestClient(test_app) as client:
                response = client.post(
                    "/api/v1/sessions",
                    json={"name": "Test Session"},
                )
                assert response.status_code == 201
                data = response.json()
                assert data["description"] == ""

    def test_update_session_description(self, test_app: FastAPI) -> None:
        """
        GIVEN a session exists
        WHEN PATCH request updates the description
        THEN response should show updated description
        """
        session_id = str(uuid4())
        with patch("mcp_server_langgraph.api.v1.sessions.get_session_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_session.return_value = {
                "id": session_id,
                "name": "Original Session",
                "description": "",
                "user_id": "test-user-123",
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z",
                "status": "active",
            }
            mock_service.rename_session.return_value = {
                "id": session_id,
                "name": "Original Session",
                "description": "Updated session description with context",
                "user_id": "test-user-123",
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z",
                "status": "active",
            }
            mock_get_service.return_value = mock_service

            with TestClient(test_app) as client:
                response = client.patch(
                    f"/api/v1/sessions/{session_id}",
                    json={"description": "Updated session description with context"},
                )
                assert response.status_code == 200
                data = response.json()
                assert data["description"] == "Updated session description with context"

    def test_get_session_returns_description(self, test_app: FastAPI) -> None:
        """
        GIVEN a session with description exists
        WHEN GET request is made
        THEN response should include description field
        """
        session_id = str(uuid4())
        with patch("mcp_server_langgraph.api.v1.sessions.get_session_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_session.return_value = {
                "id": session_id,
                "name": "Detailed Session",
                "description": "This session discusses architecture patterns",
                "user_id": "test-user-123",
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z",
                "status": "active",
            }
            mock_get_service.return_value = mock_service

            with TestClient(test_app) as client:
                response = client.get(f"/api/v1/sessions/{session_id}")
                assert response.status_code == 200
                data = response.json()
                assert data["description"] == "This session discusses architecture patterns"

    def test_list_sessions_includes_description(self, test_app: FastAPI) -> None:
        """
        GIVEN sessions with descriptions exist
        WHEN GET list request is made
        THEN response should include description in each session
        """
        with patch("mcp_server_langgraph.api.v1.sessions.get_session_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.list_sessions.return_value = (
                [
                    {
                        "id": "1",
                        "name": "Session 1",
                        "description": "First session description",
                        "user_id": "test-user-123",
                        "created_at": "2025-01-01T00:00:00Z",
                        "updated_at": "2025-01-01T00:00:00Z",
                        "status": "active",
                    },
                    {
                        "id": "2",
                        "name": "Session 2",
                        "description": "Second session description",
                        "user_id": "test-user-123",
                        "created_at": "2025-01-01T00:00:00Z",
                        "updated_at": "2025-01-01T00:00:00Z",
                        "status": "active",
                    },
                ],
                None,
            )
            mock_get_service.return_value = mock_service

            with TestClient(test_app) as client:
                response = client.get("/api/v1/sessions")
                assert response.status_code == 200
                data = response.json()
                descriptions = [s["description"] for s in data["data"]]
                assert "First session description" in descriptions
                assert "Second session description" in descriptions
