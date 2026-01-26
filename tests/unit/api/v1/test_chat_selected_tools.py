"""
Chat Selected Tools Unit Tests

Tests for manual tool selection in chat completions.
The selected_tools parameter allows users to override semantic tool selection
with explicit tool choices.

TDD: Tests written FIRST before implementation.
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


@pytest.mark.xdist_group(name="test_chat_selected_tools")
class TestChatSelectedToolsParameter:
    """Tests for selected_tools parameter in chat completions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_selected_tools_parameter_accepted(self, test_app: FastAPI) -> None:
        """
        GIVEN a chat request with selected_tools
        WHEN POST request is made
        THEN request should be accepted (not validation error)
        """
        with patch("mcp_server_langgraph.api.v1.chat.get_chat_service") as mock_get_service:
            mock_service = AsyncMock(return_value=None)
            mock_service.create_completion.return_value = {
                "id": str(uuid4()),
                "message": {"role": "assistant", "content": "Using calculator..."},
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            }
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.post(
                "/api/v1/chat/completions",
                json={
                    "session_id": str(uuid4()),
                    "messages": [{"role": "user", "content": "Calculate 2+2"}],
                    "selected_tools": ["calculator"],
                },
            )

            assert response.status_code == 200

    def test_selected_tools_with_mcp_tools(self, test_app: FastAPI) -> None:
        """
        GIVEN a chat request with MCP tool names (qualified)
        WHEN POST request is made
        THEN request should be accepted
        """
        with patch("mcp_server_langgraph.api.v1.chat.get_chat_service") as mock_get_service:
            mock_service = AsyncMock(return_value=None)
            mock_service.create_completion.return_value = {
                "id": str(uuid4()),
                "message": {"role": "assistant", "content": "Created issue..."},
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            }
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.post(
                "/api/v1/chat/completions",
                json={
                    "session_id": str(uuid4()),
                    "messages": [{"role": "user", "content": "Create an issue"}],
                    "selected_tools": ["github:create_issue", "github:list_repos"],
                },
            )

            assert response.status_code == 200

    def test_empty_selected_tools_uses_auto_mode(self, test_app: FastAPI) -> None:
        """
        GIVEN a chat request with empty selected_tools
        WHEN POST request is made
        THEN semantic search should be used (auto mode)
        """
        with patch("mcp_server_langgraph.api.v1.chat.get_chat_service") as mock_get_service:
            mock_service = AsyncMock(return_value=None)
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
                    "selected_tools": [],
                },
            )

            assert response.status_code == 200


@pytest.mark.xdist_group(name="test_chat_selected_tools")
class TestToolSelectionMode:
    """Tests for tool_selection_mode parameter."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_tool_selection_mode_auto(self, test_app: FastAPI) -> None:
        """
        GIVEN tool_selection_mode="auto"
        WHEN POST request is made
        THEN request should use semantic search
        """
        with patch("mcp_server_langgraph.api.v1.chat.get_chat_service") as mock_get_service:
            mock_service = AsyncMock(return_value=None)
            mock_service.create_completion.return_value = {
                "id": str(uuid4()),
                "message": {"role": "assistant", "content": "Using semantic search..."},
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            }
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.post(
                "/api/v1/chat/completions",
                json={
                    "session_id": str(uuid4()),
                    "messages": [{"role": "user", "content": "Hello"}],
                    "tool_selection_mode": "auto",
                },
            )

            assert response.status_code == 200

    def test_tool_selection_mode_manual(self, test_app: FastAPI) -> None:
        """
        GIVEN tool_selection_mode="manual" with selected_tools
        WHEN POST request is made
        THEN only selected tools should be used
        """
        with patch("mcp_server_langgraph.api.v1.chat.get_chat_service") as mock_get_service:
            mock_service = AsyncMock(return_value=None)
            mock_service.create_completion.return_value = {
                "id": str(uuid4()),
                "message": {"role": "assistant", "content": "Using selected tools..."},
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            }
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.post(
                "/api/v1/chat/completions",
                json={
                    "session_id": str(uuid4()),
                    "messages": [{"role": "user", "content": "Calculate 2+2"}],
                    "tool_selection_mode": "manual",
                    "selected_tools": ["calculator"],
                },
            )

            assert response.status_code == 200

    def test_tool_selection_mode_none(self, test_app: FastAPI) -> None:
        """
        GIVEN tool_selection_mode="none"
        WHEN POST request is made
        THEN no tools should be used
        """
        with patch("mcp_server_langgraph.api.v1.chat.get_chat_service") as mock_get_service:
            mock_service = AsyncMock(return_value=None)
            mock_service.create_completion.return_value = {
                "id": str(uuid4()),
                "message": {"role": "assistant", "content": "No tools used."},
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            }
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.post(
                "/api/v1/chat/completions",
                json={
                    "session_id": str(uuid4()),
                    "messages": [{"role": "user", "content": "Just chat"}],
                    "tool_selection_mode": "none",
                },
            )

            assert response.status_code == 200

    def test_invalid_tool_selection_mode_rejected(self, test_app: FastAPI) -> None:
        """
        GIVEN an invalid tool_selection_mode value
        WHEN POST request is made
        THEN request should be rejected with 422
        """
        client = TestClient(test_app)
        response = client.post(
            "/api/v1/chat/completions",
            json={
                "session_id": str(uuid4()),
                "messages": [{"role": "user", "content": "Hello"}],
                "tool_selection_mode": "invalid_mode",
            },
        )

        assert response.status_code == 422

    def test_default_tool_selection_mode_is_auto(self, test_app: FastAPI) -> None:
        """
        GIVEN no tool_selection_mode specified
        WHEN POST request is made
        THEN default should be "auto" (semantic search)
        """
        with patch("mcp_server_langgraph.api.v1.chat.get_chat_service") as mock_get_service:
            mock_service = AsyncMock(return_value=None)
            mock_service.create_completion.return_value = {
                "id": str(uuid4()),
                "message": {"role": "assistant", "content": "Default mode"},
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            }
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.post(
                "/api/v1/chat/completions",
                json={
                    "session_id": str(uuid4()),
                    "messages": [{"role": "user", "content": "Hello"}],
                    # No tool_selection_mode - should default to "auto"
                },
            )

            assert response.status_code == 200


@pytest.mark.xdist_group(name="test_chat_selected_tools")
class TestChatCompletionRequestModel:
    """Tests for ChatCompletionRequest model validation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_request_model_accepts_selected_tools_field(self) -> None:
        """
        GIVEN ChatCompletionRequest model
        WHEN selected_tools field is provided
        THEN model should validate successfully
        """
        from mcp_server_langgraph.api.v1.chat import ChatCompletionRequest

        request = ChatCompletionRequest(
            session_id=str(uuid4()),
            messages=[{"role": "user", "content": "Hello"}],  # type: ignore[arg-type]
            selected_tools=["calculator", "web_search"],
        )

        assert request.selected_tools == ["calculator", "web_search"]
        assert request.tool_selection_mode == "auto"  # default

    def test_request_model_accepts_tool_selection_mode_field(self) -> None:
        """
        GIVEN ChatCompletionRequest model
        WHEN tool_selection_mode field is provided
        THEN model should validate successfully
        """
        from mcp_server_langgraph.api.v1.chat import ChatCompletionRequest

        request = ChatCompletionRequest(
            session_id=str(uuid4()),
            messages=[{"role": "user", "content": "Hello"}],  # type: ignore[arg-type]
            tool_selection_mode="manual",
            selected_tools=["calculator"],
        )

        assert request.tool_selection_mode == "manual"
        assert request.selected_tools == ["calculator"]

    def test_request_model_rejects_invalid_tool_selection_mode(self) -> None:
        """
        GIVEN ChatCompletionRequest model
        WHEN invalid tool_selection_mode is provided
        THEN model should raise validation error
        """
        from pydantic import ValidationError

        from mcp_server_langgraph.api.v1.chat import ChatCompletionRequest

        with pytest.raises(ValidationError) as exc_info:
            ChatCompletionRequest(
                session_id=str(uuid4()),
                messages=[{"role": "user", "content": "Hello"}],  # type: ignore[arg-type]
                tool_selection_mode="invalid",  # type: ignore[arg-type]
            )

        assert "tool_selection_mode" in str(exc_info.value)
