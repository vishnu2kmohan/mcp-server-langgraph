"""
Integration tests for Chat API endpoints.

Tests the full API path from HTTP request to response,
using the real FastAPI app with mocked LLM/MCP clients.

Tests cover:
- POST /api/v1/chat/completions - Create a chat completion
- POST /api/v1/chat/completions/stream - Create a streaming completion
- GET /api/v1/chat/{session_id}/history - Get chat history
"""

import gc
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from mcp_server_langgraph.app import app

pytestmark = pytest.mark.integration


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_chat_service():
    """Create a mock chat service."""
    service = MagicMock()
    service.create_completion = AsyncMock()  # async-mock-configured
    service.create_stream = AsyncMock()  # async-mock-configured
    service.get_history = AsyncMock()  # async-mock-configured
    return service


@pytest.fixture
def sample_completion_response():
    """Sample ChatCompletionResponse for testing."""
    return {
        "id": "chatcmpl-abc123",
        "message": {
            "role": "assistant",
            "content": "Hello! How can I help you today?",
        },
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 8,
            "total_tokens": 18,
        },
        "model": "gpt-4",
    }


@pytest.fixture
def sample_chat_history():
    """Sample chat history for testing."""
    return [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi! How can I help?"},
        {"role": "user", "content": "What is 2+2?"},
        {"role": "assistant", "content": "2+2 equals 4."},
    ]


@pytest.mark.xdist_group(name="chat_api_integration")
class TestChatCompletionEndpoint:
    """Integration tests for POST /api/v1/chat/completions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_completions_returns_200(self, client, mock_chat_service, sample_completion_response):
        """POST /api/v1/chat/completions should return 200 with valid request."""
        mock_chat_service.create_completion.return_value = sample_completion_response

        with patch("mcp_server_langgraph.api.v1.chat.get_chat_service") as mock_get_service:
            mock_get_service.return_value = mock_chat_service

            response = client.post(
                "/api/v1/chat/completions",
                json={
                    "session_id": "session-123",
                    "messages": [{"role": "user", "content": "Hello"}],
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["message"]["role"] == "assistant"

    def test_completions_with_model_parameter(self, client, mock_chat_service, sample_completion_response):
        """POST /api/v1/chat/completions should accept model parameter."""
        mock_chat_service.create_completion.return_value = sample_completion_response

        with patch("mcp_server_langgraph.api.v1.chat.get_chat_service") as mock_get_service:
            mock_get_service.return_value = mock_chat_service

            response = client.post(
                "/api/v1/chat/completions",
                json={
                    "session_id": "session-123",
                    "messages": [{"role": "user", "content": "Hello"}],
                    "model": "claude-3-opus",
                    "temperature": 0.5,
                },
            )

        assert response.status_code == 200
        # Verify the service was called with model parameter
        call_kwargs = mock_chat_service.create_completion.call_args.kwargs
        assert call_kwargs["model"] == "claude-3-opus"
        assert call_kwargs["temperature"] == 0.5

    def test_completions_includes_usage_info(self, client, mock_chat_service, sample_completion_response):
        """Response should include token usage information."""
        mock_chat_service.create_completion.return_value = sample_completion_response

        with patch("mcp_server_langgraph.api.v1.chat.get_chat_service") as mock_get_service:
            mock_get_service.return_value = mock_chat_service

            response = client.post(
                "/api/v1/chat/completions",
                json={
                    "session_id": "session-123",
                    "messages": [{"role": "user", "content": "Hello"}],
                },
            )

        data = response.json()
        assert "usage" in data
        if data["usage"]:
            assert "prompt_tokens" in data["usage"]
            assert "completion_tokens" in data["usage"]

    def test_completions_returns_422_for_empty_messages(self, client, mock_chat_service):
        """POST /api/v1/chat/completions should return 422 for empty messages."""
        with patch("mcp_server_langgraph.api.v1.chat.get_chat_service") as mock_get_service:
            mock_get_service.return_value = mock_chat_service

            response = client.post(
                "/api/v1/chat/completions",
                json={
                    "session_id": "session-123",
                    "messages": [],  # Empty messages should fail validation
                },
            )

        assert response.status_code == 422


@pytest.mark.xdist_group(name="chat_api_integration")
class TestChatStreamEndpoint:
    """Integration tests for POST /api/v1/chat/completions/stream."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_stream_returns_200(self, client, mock_chat_service):
        """POST /api/v1/chat/completions/stream should return 200."""

        async def mock_stream(*args: Any, **kwargs: Any):
            """Mock async generator for streaming."""
            yield {"delta": {"content": "Hello"}}
            yield {"delta": {"content": " world"}}

        mock_chat_service.create_stream = mock_stream

        with patch("mcp_server_langgraph.api.v1.chat.get_chat_service") as mock_get_service:
            mock_get_service.return_value = mock_chat_service

            response = client.post(
                "/api/v1/chat/completions/stream",
                json={
                    "session_id": "session-123",
                    "messages": [{"role": "user", "content": "Hello"}],
                },
            )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")

    def test_stream_returns_sse_format(self, client, mock_chat_service):
        """Response should be in Server-Sent Events format."""

        async def mock_stream(*args: Any, **kwargs: Any):
            yield {"delta": {"content": "Test"}}

        mock_chat_service.create_stream = mock_stream

        with patch("mcp_server_langgraph.api.v1.chat.get_chat_service") as mock_get_service:
            mock_get_service.return_value = mock_chat_service

            response = client.post(
                "/api/v1/chat/completions/stream",
                json={
                    "session_id": "session-123",
                    "messages": [{"role": "user", "content": "Hello"}],
                },
            )

        # SSE format: "data: {...}\n\n"
        content = response.content.decode()
        assert "data:" in content


@pytest.mark.xdist_group(name="chat_api_integration")
class TestChatHistoryEndpoint:
    """Integration tests for GET /api/v1/chat/{session_id}/history."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_history_returns_200(self, client, mock_chat_service, sample_chat_history):
        """GET /api/v1/chat/{session_id}/history should return 200 with history."""
        mock_chat_service.get_history.return_value = sample_chat_history

        with patch("mcp_server_langgraph.api.v1.chat.get_chat_service") as mock_get_service:
            mock_get_service.return_value = mock_chat_service

            response = client.get("/api/v1/chat/session-123/history")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 4

    def test_history_includes_messages_with_roles(self, client, mock_chat_service, sample_chat_history):
        """Response should include messages with roles and content."""
        mock_chat_service.get_history.return_value = sample_chat_history

        with patch("mcp_server_langgraph.api.v1.chat.get_chat_service") as mock_get_service:
            mock_get_service.return_value = mock_chat_service

            response = client.get("/api/v1/chat/session-123/history")

        data = response.json()
        for message in data:
            assert "role" in message
            assert "content" in message
            assert message["role"] in ("user", "assistant", "system")

    def test_history_returns_404_for_nonexistent_session(self, client, mock_chat_service):
        """GET /api/v1/chat/{session_id}/history should return 404 for not found."""
        mock_chat_service.get_history.return_value = None

        with patch("mcp_server_langgraph.api.v1.chat.get_chat_service") as mock_get_service:
            mock_get_service.return_value = mock_chat_service

            response = client.get("/api/v1/chat/nonexistent/history")

        assert response.status_code == 404

    def test_history_returns_empty_list_for_new_session(self, client, mock_chat_service):
        """GET /api/v1/chat/{session_id}/history should return empty list for new session."""
        mock_chat_service.get_history.return_value = []

        with patch("mcp_server_langgraph.api.v1.chat.get_chat_service") as mock_get_service:
            mock_get_service.return_value = mock_chat_service

            response = client.get("/api/v1/chat/new-session/history")

        assert response.status_code == 200
        data = response.json()
        assert data == []
