"""
Sessions Router Unit Tests

Tests for /api/v1/sessions endpoints per TDD methodology.
Tests written FIRST before implementation (RED phase).

The sessions endpoint provides CRUD operations for chat session management.
"""

import gc
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
def test_app() -> FastAPI:
    """Create a test app with the sessions router."""
    from mcp_server_langgraph.api.v1.sessions import sessions_router

    app = FastAPI()
    app.include_router(sessions_router, prefix="/api/v1")
    return app


@pytest.fixture
def client(test_app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(test_app)


@pytest.fixture
def sample_session() -> dict:
    """Sample session data for testing."""
    return {
        "id": str(uuid4()),
        "title": "Test Chat Session",
        "workflow_id": str(uuid4()),
        "messages": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ],
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z",
        "status": "active",
    }


@pytest.mark.xdist_group(name="test_sessions_router")
class TestSessionsListEndpoint:
    """Tests for GET /api/v1/sessions endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_sessions_returns_200(self, test_app: FastAPI) -> None:
        """
        GIVEN a request to /api/v1/sessions
        WHEN GET request is made
        THEN response should be 200 OK
        """
        with patch("mcp_server_langgraph.api.v1.sessions.get_session_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.list_sessions.return_value = ([], None)
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get("/api/v1/sessions")

            assert response.status_code == 200

    def test_list_sessions_returns_array(self, test_app: FastAPI) -> None:
        """
        GIVEN sessions exist
        WHEN GET request is made
        THEN response should contain array of sessions
        """
        with patch("mcp_server_langgraph.api.v1.sessions.get_session_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.list_sessions.return_value = (
                [{"id": "1", "title": "Test"}],
                None,
            )
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get("/api/v1/sessions")
            data = response.json()

            assert "data" in data
            assert isinstance(data["data"], list)

    def test_list_sessions_with_workflow_filter(self, test_app: FastAPI) -> None:
        """
        GIVEN a workflow_id filter
        WHEN GET request is made
        THEN response should only include sessions for that workflow
        """
        workflow_id = str(uuid4())
        with patch("mcp_server_langgraph.api.v1.sessions.get_session_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.list_sessions.return_value = (
                [{"id": "1", "workflow_id": workflow_id}],
                None,
            )
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get(f"/api/v1/sessions?workflow_id={workflow_id}")
            _ = response.json()  # Validate response is valid JSON

            assert response.status_code == 200
            mock_service.list_sessions.assert_called_once()


@pytest.mark.xdist_group(name="test_sessions_router")
class TestSessionsGetEndpoint:
    """Tests for GET /api/v1/sessions/{id} endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_session_returns_200(self, test_app: FastAPI, sample_session: dict) -> None:
        """
        GIVEN a session exists
        WHEN GET request is made with session ID
        THEN response should be 200 OK
        """
        with patch("mcp_server_langgraph.api.v1.sessions.get_session_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_session.return_value = sample_session
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get(f"/api/v1/sessions/{sample_session['id']}")

            assert response.status_code == 200

    def test_get_session_returns_session_data(self, test_app: FastAPI, sample_session: dict) -> None:
        """
        GIVEN a session exists
        WHEN GET request is made
        THEN response should contain session data with messages
        """
        with patch("mcp_server_langgraph.api.v1.sessions.get_session_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_session.return_value = sample_session
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get(f"/api/v1/sessions/{sample_session['id']}")
            data = response.json()

            assert data["id"] == sample_session["id"]
            assert data["title"] == sample_session["title"]
            assert "messages" in data

    def test_get_session_not_found_returns_404(self, test_app: FastAPI) -> None:
        """
        GIVEN a session does not exist
        WHEN GET request is made
        THEN response should be 404 Not Found
        """
        with patch("mcp_server_langgraph.api.v1.sessions.get_session_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_session.return_value = None
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            session_id = str(uuid4())
            response = client.get(f"/api/v1/sessions/{session_id}")

            assert response.status_code == 404


@pytest.mark.xdist_group(name="test_sessions_router")
class TestSessionsCreateEndpoint:
    """Tests for POST /api/v1/sessions endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_session_returns_201(self, test_app: FastAPI, sample_session: dict) -> None:
        """
        GIVEN valid session data
        WHEN POST request is made
        THEN response should be 201 Created
        """
        with patch("mcp_server_langgraph.api.v1.sessions.get_session_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.create_session.return_value = sample_session
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.post(
                "/api/v1/sessions",
                json={
                    "title": sample_session["title"],
                    "workflow_id": sample_session["workflow_id"],
                },
            )

            assert response.status_code == 201

    def test_create_session_returns_created_session(self, test_app: FastAPI, sample_session: dict) -> None:
        """
        GIVEN valid session data
        WHEN POST request is made
        THEN response should contain created session with ID
        """
        with patch("mcp_server_langgraph.api.v1.sessions.get_session_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.create_session.return_value = sample_session
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.post(
                "/api/v1/sessions",
                json={
                    "title": sample_session["title"],
                    "workflow_id": sample_session["workflow_id"],
                },
            )
            data = response.json()

            assert "id" in data
            assert data["title"] == sample_session["title"]


@pytest.mark.xdist_group(name="test_sessions_router")
class TestSessionsDeleteEndpoint:
    """Tests for DELETE /api/v1/sessions/{id} endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_delete_session_returns_204(self, test_app: FastAPI, sample_session: dict) -> None:
        """
        GIVEN a session exists
        WHEN DELETE request is made
        THEN response should be 204 No Content
        """
        with patch("mcp_server_langgraph.api.v1.sessions.get_session_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.delete_session.return_value = True
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.delete(f"/api/v1/sessions/{sample_session['id']}")

            assert response.status_code == 204

    def test_delete_session_not_found_returns_404(self, test_app: FastAPI) -> None:
        """
        GIVEN a session does not exist
        WHEN DELETE request is made
        THEN response should be 404 Not Found
        """
        with patch("mcp_server_langgraph.api.v1.sessions.get_session_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.delete_session.return_value = False
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            session_id = str(uuid4())
            response = client.delete(f"/api/v1/sessions/{session_id}")

            assert response.status_code == 404


@pytest.mark.xdist_group(name="test_sessions_router")
class TestSessionsMessagesEndpoint:
    """Tests for GET/POST /api/v1/sessions/{id}/messages endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_messages_returns_200(self, test_app: FastAPI, sample_session: dict) -> None:
        """
        GIVEN a session exists
        WHEN GET request is made to /sessions/{id}/messages
        THEN response should be 200 OK with messages array
        """
        with patch("mcp_server_langgraph.api.v1.sessions.get_session_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_session_messages.return_value = sample_session["messages"]
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get(f"/api/v1/sessions/{sample_session['id']}/messages")

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

    def test_add_message_returns_201(self, test_app: FastAPI, sample_session: dict) -> None:
        """
        GIVEN a session exists
        WHEN POST request is made to /sessions/{id}/messages
        THEN response should be 201 Created
        """
        with patch("mcp_server_langgraph.api.v1.sessions.get_session_service") as mock_get_service:
            mock_service = AsyncMock()
            new_message = {"role": "user", "content": "New message"}
            mock_service.add_message.return_value = new_message
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.post(
                f"/api/v1/sessions/{sample_session['id']}/messages",
                json={"role": "user", "content": "New message"},
            )

            assert response.status_code == 201
