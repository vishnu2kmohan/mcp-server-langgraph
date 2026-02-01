"""
Chat Router Unit Tests

Tests for /api/v1/chat endpoints per TDD methodology.
Tests written FIRST before implementation (RED phase).

The chat endpoint provides real-time chat interactions.
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
    """Create a test app with the chat router."""
    from mcp_server_langgraph.api.v1.chat import chat_router
    from mcp_server_langgraph.auth.dependencies import get_current_user

    app = FastAPI()
    app.include_router(chat_router, prefix="/api/v1")

    # Mock authentication
    mock_user = {
        "sub": "test-user-id",
        "user_id": "test-user-id",
        "username": "testuser",
        "email": "testuser@example.com",
        "roles": ["user"],
        "realm_access": {"roles": ["user"]},
    }
    app.dependency_overrides[get_current_user] = lambda: mock_user

    return app


@pytest.fixture
def client(test_app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(test_app)


@pytest.mark.xdist_group(name="test_chat_router")
class TestChatCompletionEndpoint:
    """Tests for POST /api/v1/chat/completions endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_chat_completion_returns_200(self, test_app: FastAPI) -> None:
        """
        GIVEN a valid chat request
        WHEN POST request is made to /chat/completions
        THEN response should be 200 OK
        """
        with patch("mcp_server_langgraph.api.v1.chat.get_chat_service") as mock_get_service:
            mock_service = AsyncMock(
                return_value=None
            )  # async-mock-configured (return_value set below)  # noqa: async-mock-config
            mock_service.create_completion.return_value = {
                "id": str(uuid4()),
                "message": {"role": "assistant", "content": "Hello!"},
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            }
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.post(
                "/api/v1/chat/completions",
                json={
                    "session_id": str(uuid4()),
                    "messages": [{"role": "user", "content": "Hello"}],
                },
            )

            assert response.status_code == 200

    def test_chat_completion_returns_response(self, test_app: FastAPI) -> None:
        """
        GIVEN a valid chat request
        WHEN POST request is made
        THEN response should contain assistant message
        """
        with patch("mcp_server_langgraph.api.v1.chat.get_chat_service") as mock_get_service:
            mock_service = AsyncMock(
                return_value=None
            )  # async-mock-configured (return_value set below)  # noqa: async-mock-config
            mock_service.create_completion.return_value = {
                "id": str(uuid4()),
                "message": {"role": "assistant", "content": "I can help!"},
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            }
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.post(
                "/api/v1/chat/completions",
                json={
                    "session_id": str(uuid4()),
                    "messages": [{"role": "user", "content": "Can you help?"}],
                },
            )
            data = response.json()

            assert "message" in data
            assert data["message"]["role"] == "assistant"

    def test_chat_completion_validates_messages(self, test_app: FastAPI) -> None:
        """
        GIVEN an invalid chat request (empty messages)
        WHEN POST request is made
        THEN response should be 422 Unprocessable Entity
        """
        with patch("mcp_server_langgraph.api.v1.chat.get_chat_service") as mock_get_service:
            mock_service = AsyncMock(return_value=None)  # Not called due to validation failure
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.post(
                "/api/v1/chat/completions",
                json={
                    "session_id": str(uuid4()),
                    "messages": [],  # Empty messages should fail
                },
            )

            assert response.status_code == 422


@pytest.mark.xdist_group(name="test_chat_router")
class TestChatStreamEndpoint:
    """Tests for POST /api/v1/chat/completions/stream endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.skip(
        reason="Streaming endpoint requires httpx.AsyncClient for proper testing. "
        "TestClient has limitations with async generators. Covered in integration tests."
    )
    def test_chat_stream_returns_200(self, test_app: FastAPI) -> None:
        """
        GIVEN a valid streaming chat request
        WHEN POST request is made to /chat/completions/stream
        THEN response should be 200 OK with streaming content

        NOTE: This test is skipped in unit tests due to TestClient limitations
        with async streaming responses. Integration tests cover this properly.
        """
        pass


@pytest.mark.xdist_group(name="test_chat_router")
class TestChatHistoryEndpoint:
    """Tests for GET /api/v1/chat/{session_id}/history endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_history_returns_200(self, test_app: FastAPI) -> None:
        """
        GIVEN a valid session ID
        WHEN GET request is made to /chat/{id}/history
        THEN response should be 200 OK
        """
        session_id = str(uuid4())
        with patch("mcp_server_langgraph.api.v1.chat.get_chat_service") as mock_get_service:
            mock_service = AsyncMock(
                return_value=None
            )  # async-mock-configured (return_value set below)  # noqa: async-mock-config
            mock_service.get_history.return_value = [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi!"},
            ]
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get(f"/api/v1/chat/{session_id}/history")

            assert response.status_code == 200

    def test_get_history_returns_messages(self, test_app: FastAPI) -> None:
        """
        GIVEN a session with messages
        WHEN GET request is made
        THEN response should contain message array
        """
        session_id = str(uuid4())
        with patch("mcp_server_langgraph.api.v1.chat.get_chat_service") as mock_get_service:
            mock_service = AsyncMock(
                return_value=None
            )  # async-mock-configured (return_value set below)  # noqa: async-mock-config
            mock_service.get_history.return_value = [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi!"},
            ]
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get(f"/api/v1/chat/{session_id}/history")
            data = response.json()

            assert isinstance(data, list)
            assert len(data) == 2

    def test_get_history_not_found_returns_404(self, test_app: FastAPI) -> None:
        """
        GIVEN a non-existent session ID
        WHEN GET request is made
        THEN response should be 404 Not Found
        """
        session_id = str(uuid4())
        with patch("mcp_server_langgraph.api.v1.chat.get_chat_service") as mock_get_service:
            mock_service = AsyncMock(
                return_value=None
            )  # async-mock-configured (return_value set below)  # noqa: async-mock-config
            mock_service.get_history.return_value = None
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get(f"/api/v1/chat/{session_id}/history")

            assert response.status_code == 404


@pytest.mark.xdist_group(name="test_chat_router")
class TestChatErrorHandling:
    """Tests for chat router error handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_elicitation_required_returns_428(self, test_app: FastAPI) -> None:
        """
        GIVEN a chat service that raises MCPElicitationRequiredError
        WHEN POST request is made to /chat/completions
        THEN response should be 428 Precondition Required with elicitation details
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import MCPElicitationRequiredError

        with patch("mcp_server_langgraph.api.v1.chat.get_chat_service") as mock_get_service:
            mock_service = AsyncMock(
                return_value=None
            )  # async-mock-configured (return_value set below)  # noqa: async-mock-config
            mock_service.create_completion.side_effect = MCPElicitationRequiredError(
                "User authentication required",
                elicitations=[
                    {"type": "url", "url": "https://oauth.example.com/authorize"},
                ],
            )
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.post(
                "/api/v1/chat/completions",
                json={
                    "session_id": str(uuid4()),
                    "messages": [{"role": "user", "content": "Hello"}],
                },
            )

            assert response.status_code == 428
            data = response.json()
            assert "detail" in data
            assert "elicitations" in data["detail"]
            assert len(data["detail"]["elicitations"]) == 1
            assert data["detail"]["elicitations"][0]["type"] == "url"

    def test_mcp_connection_error_returns_503(self, test_app: FastAPI) -> None:
        """
        GIVEN a chat service that raises MCPConnectionError
        WHEN POST request is made to /chat/completions
        THEN response should be 503 Service Unavailable
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import MCPConnectionError

        with patch("mcp_server_langgraph.api.v1.chat.get_chat_service") as mock_get_service:
            mock_service = AsyncMock(
                return_value=None
            )  # async-mock-configured (return_value set below)  # noqa: async-mock-config
            mock_service.create_completion.side_effect = MCPConnectionError("MCP server connection refused")
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.post(
                "/api/v1/chat/completions",
                json={
                    "session_id": str(uuid4()),
                    "messages": [{"role": "user", "content": "Hello"}],
                },
            )

            assert response.status_code == 503
            assert "connection" in response.json()["detail"].lower()

    def test_mcp_permission_error_returns_403(self, test_app: FastAPI) -> None:
        """
        GIVEN a chat service that raises MCPPermissionError
        WHEN POST request is made to /chat/completions
        THEN response should be 403 Forbidden
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import MCPPermissionError

        with patch("mcp_server_langgraph.api.v1.chat.get_chat_service") as mock_get_service:
            mock_service = AsyncMock(
                return_value=None
            )  # async-mock-configured (return_value set below)  # noqa: async-mock-config
            mock_service.create_completion.side_effect = MCPPermissionError("Access denied to chat resource")
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.post(
                "/api/v1/chat/completions",
                json={
                    "session_id": str(uuid4()),
                    "messages": [{"role": "user", "content": "Hello"}],
                },
            )

            assert response.status_code == 403
            assert "denied" in response.json()["detail"].lower()
