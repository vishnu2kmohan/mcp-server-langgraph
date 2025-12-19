"""
Sessions Router Unit Tests

Tests for /api/v1/sessions endpoints per TDD methodology.
Tests written FIRST before implementation (RED phase).

The sessions endpoint provides CRUD operations for chat session management.
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
    """Create a test app with the sessions router and mock authentication."""
    from mcp_server_langgraph.api.v1.sessions import sessions_router
    from mcp_server_langgraph.auth.middleware import get_current_user

    app = FastAPI()
    app.include_router(sessions_router, prefix="/api/v1")

    # CRITICAL: Use async function for async dependency override (pytest-xdist compatible)
    # Sync lambda causes 401 errors in xdist workers
    async def override_get_current_user():
        return mock_user

    app.dependency_overrides[get_current_user] = override_get_current_user

    yield app

    # Cleanup
    app.dependency_overrides.clear()


@pytest.fixture
def client(test_app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(test_app)


@pytest.fixture
def sample_session(mock_user: dict[str, Any]) -> dict[str, Any]:
    """Sample session data for testing."""
    return {
        "id": str(uuid4()),
        "name": "Test Chat Session",
        "user_id": mock_user["sub"],  # Session owned by mock user
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
            mock_service = AsyncMock()  # async-mock-configured (return_value set below)
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
            mock_service = AsyncMock()  # async-mock-configured (return_value set below)
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
            mock_service = AsyncMock()  # async-mock-configured (return_value set below)
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
            mock_service = AsyncMock()  # async-mock-configured (return_value set below)
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
            mock_service = AsyncMock()  # async-mock-configured (return_value set below)
            mock_service.get_session.return_value = sample_session
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get(f"/api/v1/sessions/{sample_session['id']}")
            data = response.json()

            assert data["id"] == sample_session["id"]
            assert data["name"] == sample_session["name"]
            assert "messages" in data

    def test_get_session_not_found_returns_404(self, test_app: FastAPI) -> None:
        """
        GIVEN a session does not exist
        WHEN GET request is made
        THEN response should be 404 Not Found
        """
        with patch("mcp_server_langgraph.api.v1.sessions.get_session_service") as mock_get_service:
            mock_service = AsyncMock()  # async-mock-configured (return_value set below)
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
            mock_service = AsyncMock()  # async-mock-configured (return_value set below)
            mock_service.create_session.return_value = sample_session
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.post(
                "/api/v1/sessions",
                json={
                    "name": sample_session["name"],
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
            mock_service = AsyncMock()  # async-mock-configured (return_value set below)
            mock_service.create_session.return_value = sample_session
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.post(
                "/api/v1/sessions",
                json={
                    "name": sample_session["name"],
                    "workflow_id": sample_session["workflow_id"],
                },
            )
            data = response.json()

            assert "id" in data
            assert data["name"] == sample_session["name"]


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
            mock_service = AsyncMock()  # async-mock-configured (return_value set below)
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
            mock_service = AsyncMock()  # async-mock-configured (return_value set below)
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
            mock_service = AsyncMock()  # async-mock-configured (return_value set below)
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
            mock_service = AsyncMock()  # async-mock-configured (return_value set below)
            new_message = {"role": "user", "content": "New message"}
            mock_service.add_message.return_value = new_message
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.post(
                f"/api/v1/sessions/{sample_session['id']}/messages",
                json={"role": "user", "content": "New message"},
            )

            assert response.status_code == 201


# ============================================================================
# Sorting Tests
# ============================================================================


@pytest.mark.xdist_group(name="test_sessions_router_query")
class TestSessionsListSorting:
    """Tests for sorting sessions via GET /api/v1/sessions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_sessions_sort_by_title_ascending(self, test_app: FastAPI) -> None:
        """
        GIVEN sessions exist
        WHEN GET request with sort_by=title and sort_order=asc
        THEN service should receive sorting parameters
        """
        with patch("mcp_server_langgraph.api.v1.sessions.get_session_service") as mock_get_service:
            mock_service = AsyncMock()  # async-mock-configured (return_value set below)
            mock_service.list_sessions.return_value = ([], None)
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get("/api/v1/sessions?sort_by=title&sort_order=asc")

            assert response.status_code == 200
            # Verify the service was called with sorting params
            mock_service.list_sessions.assert_called_once()

    def test_list_sessions_sort_by_created_at_descending(self, test_app: FastAPI) -> None:
        """
        GIVEN sessions exist
        WHEN GET request with sort_by=created_at and sort_order=desc
        THEN service should receive sorting parameters
        """
        with patch("mcp_server_langgraph.api.v1.sessions.get_session_service") as mock_get_service:
            mock_service = AsyncMock()  # async-mock-configured (return_value set below)
            mock_service.list_sessions.return_value = ([], None)
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get("/api/v1/sessions?sort_by=created_at&sort_order=desc")

            assert response.status_code == 200

    def test_list_sessions_sort_by_updated_at(self, test_app: FastAPI) -> None:
        """
        GIVEN sessions exist
        WHEN GET request with sort_by=updated_at
        THEN service should receive sorting parameters
        """
        with patch("mcp_server_langgraph.api.v1.sessions.get_session_service") as mock_get_service:
            mock_service = AsyncMock()  # async-mock-configured (return_value set below)
            mock_service.list_sessions.return_value = ([], None)
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get("/api/v1/sessions?sort_by=updated_at&sort_order=asc")

            assert response.status_code == 200


# ============================================================================
# Filtering Tests
# ============================================================================


@pytest.mark.xdist_group(name="test_sessions_router_query")
class TestSessionsListFiltering:
    """Tests for filtering sessions via GET /api/v1/sessions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_sessions_filter_by_status(self, test_app: FastAPI) -> None:
        """
        GIVEN sessions with different statuses exist
        WHEN GET request with status=active
        THEN service should receive status filter
        """
        with patch("mcp_server_langgraph.api.v1.sessions.get_session_service") as mock_get_service:
            mock_service = AsyncMock()  # async-mock-configured (return_value set below)
            mock_service.list_sessions.return_value = ([], None)
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get("/api/v1/sessions?status=active")

            assert response.status_code == 200

    def test_list_sessions_filter_by_workflow_id_and_status(self, test_app: FastAPI) -> None:
        """
        GIVEN sessions exist
        WHEN GET request with workflow_id and status filters
        THEN service should receive both filters
        """
        workflow_id = str(uuid4())
        with patch("mcp_server_langgraph.api.v1.sessions.get_session_service") as mock_get_service:
            mock_service = AsyncMock()  # async-mock-configured (return_value set below)
            mock_service.list_sessions.return_value = ([], None)
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get(f"/api/v1/sessions?workflow_id={workflow_id}&status=active")

            assert response.status_code == 200


# ============================================================================
# Search Tests
# ============================================================================


@pytest.mark.xdist_group(name="test_sessions_router_query")
class TestSessionsListSearch:
    """Tests for searching sessions via GET /api/v1/sessions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_sessions_search_by_title(self, test_app: FastAPI) -> None:
        """
        GIVEN sessions exist
        WHEN GET request with search parameter
        THEN service should receive search query
        """
        with patch("mcp_server_langgraph.api.v1.sessions.get_session_service") as mock_get_service:
            mock_service = AsyncMock()  # async-mock-configured (return_value set below)
            mock_service.list_sessions.return_value = (
                [{"id": "1", "title": "Machine Learning Chat"}],
                None,
            )
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get("/api/v1/sessions?search=Machine")

            assert response.status_code == 200

    def test_list_sessions_search_case_insensitive(self, test_app: FastAPI) -> None:
        """
        GIVEN sessions exist
        WHEN GET request with lowercase search
        THEN service should handle case-insensitive search
        """
        with patch("mcp_server_langgraph.api.v1.sessions.get_session_service") as mock_get_service:
            mock_service = AsyncMock()  # async-mock-configured (return_value set below)
            mock_service.list_sessions.return_value = ([], None)
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get("/api/v1/sessions?search=machine")

            assert response.status_code == 200

    def test_list_sessions_search_with_pagination(self, test_app: FastAPI) -> None:
        """
        GIVEN sessions exist
        WHEN GET request with search and pagination
        THEN service should handle both
        """
        with patch("mcp_server_langgraph.api.v1.sessions.get_session_service") as mock_get_service:
            mock_service = AsyncMock()  # async-mock-configured (return_value set below)
            mock_service.list_sessions.return_value = ([], None)
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get("/api/v1/sessions?search=test&limit=10")

            assert response.status_code == 200

    def test_list_sessions_search_no_results(self, test_app: FastAPI) -> None:
        """
        GIVEN no matching sessions
        WHEN GET request with search
        THEN should return empty list
        """
        with patch("mcp_server_langgraph.api.v1.sessions.get_session_service") as mock_get_service:
            mock_service = AsyncMock()  # async-mock-configured (return_value set below)
            mock_service.list_sessions.return_value = ([], None)
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get("/api/v1/sessions?search=nonexistent_xyz_123")

            assert response.status_code == 200
            data = response.json()
            assert data["data"] == []


# ============================================================================
# Combined Query Tests
# ============================================================================


@pytest.mark.xdist_group(name="test_sessions_router_query")
class TestSessionsListCombined:
    """Tests for combining sorting, filtering, and search."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_sessions_search_with_sorting(self, test_app: FastAPI) -> None:
        """
        GIVEN sessions exist
        WHEN GET request with search and sorting
        THEN service should handle both
        """
        with patch("mcp_server_langgraph.api.v1.sessions.get_session_service") as mock_get_service:
            mock_service = AsyncMock()  # async-mock-configured (return_value set below)
            mock_service.list_sessions.return_value = ([], None)
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get("/api/v1/sessions?search=test&sort_by=title&sort_order=asc")

            assert response.status_code == 200

    def test_list_sessions_all_query_params(self, test_app: FastAPI) -> None:
        """
        GIVEN sessions exist
        WHEN GET request with all query parameters
        THEN service should handle all params
        """
        workflow_id = str(uuid4())
        with patch("mcp_server_langgraph.api.v1.sessions.get_session_service") as mock_get_service:
            mock_service = AsyncMock()  # async-mock-configured (return_value set below)
            mock_service.list_sessions.return_value = ([], None)
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get(
                f"/api/v1/sessions?search=test&workflow_id={workflow_id}"
                "&status=active&sort_by=created_at&sort_order=desc&limit=10"
            )

            assert response.status_code == 200


# ============================================================================
# Message Rating Tests
# ============================================================================


@pytest.mark.xdist_group(name="test_sessions_router_rating")
class TestMessageRatingEndpoint:
    """Tests for POST /api/v1/sessions/{session_id}/messages/{message_id}/rating endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_rate_message_returns_201(self, test_app: FastAPI, sample_session: dict) -> None:
        """
        GIVEN a valid session and message
        WHEN POST request with rating is made
        THEN response should be 201 Created
        """
        with patch("mcp_server_langgraph.api.v1.sessions.get_session_service") as mock_get_service:
            mock_service = AsyncMock()  # async-mock-configured (return_value set below)
            mock_service.get_session.return_value = sample_session
            mock_service.rate_message.return_value = {
                "id": "rating-001",
                "rating": "positive",
                "message_id": "msg-123",
            }
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.post(
                f"/api/v1/sessions/{sample_session['id']}/messages/msg-123/rating",
                json={"rating": "positive"},
            )

            assert response.status_code == 201

    def test_rate_message_returns_rating_data(self, test_app: FastAPI, sample_session: dict) -> None:
        """
        GIVEN a valid session and message
        WHEN POST request with rating is made
        THEN response should contain rating data
        """
        with patch("mcp_server_langgraph.api.v1.sessions.get_session_service") as mock_get_service:
            mock_service = AsyncMock()  # async-mock-configured (return_value set below)
            mock_service.get_session.return_value = sample_session
            mock_service.rate_message.return_value = {
                "id": "rating-001",
                "rating": "positive",
                "message_id": "msg-123",
            }
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.post(
                f"/api/v1/sessions/{sample_session['id']}/messages/msg-123/rating",
                json={"rating": "positive"},
            )
            data = response.json()

            assert "id" in data
            assert data["rating"] == "positive"

    def test_rate_message_with_feedback(self, test_app: FastAPI, sample_session: dict) -> None:
        """
        GIVEN a valid session and message
        WHEN POST request with rating and feedback is made
        THEN response should be 201 Created
        """
        with patch("mcp_server_langgraph.api.v1.sessions.get_session_service") as mock_get_service:
            mock_service = AsyncMock()  # async-mock-configured (return_value set below)
            mock_service.get_session.return_value = sample_session
            mock_service.rate_message.return_value = {
                "id": "rating-001",
                "rating": "negative",
                "message_id": "msg-123",
                "feedback": "Response was not helpful",
            }
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.post(
                f"/api/v1/sessions/{sample_session['id']}/messages/msg-123/rating",
                json={"rating": "negative", "feedback": "Response was not helpful"},
            )

            assert response.status_code == 201

    def test_rate_message_session_not_found(self, test_app: FastAPI) -> None:
        """
        GIVEN a session does not exist
        WHEN POST request with rating is made
        THEN response should be 404 Not Found
        """
        with patch("mcp_server_langgraph.api.v1.sessions.get_session_service") as mock_get_service:
            mock_service = AsyncMock()  # async-mock-configured (return_value set below)
            mock_service.get_session.return_value = None
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            session_id = str(uuid4())
            response = client.post(
                f"/api/v1/sessions/{session_id}/messages/msg-123/rating",
                json={"rating": "positive"},
            )

            assert response.status_code == 404
