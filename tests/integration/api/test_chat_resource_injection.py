"""
Integration tests for Chat API resource injection (MCP 2025-11-25).

TDD: These tests verify the integration between the Chat API and MCP
resource injection feature. Tests ensure that when resource_uris are
provided to the chat completion endpoint, resources are read from the
MCP bridge and injected into the LLM context.

Tested integration:
1. Chat API endpoint receives resource_uris
2. ChatServiceImpl reads resources via MCPBridge
3. Resource content is injected as system message context
4. LLM completion proceeds with enriched context
"""

import gc
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Module-level marker for test categorization
pytestmark = [pytest.mark.integration, pytest.mark.api]

if TYPE_CHECKING:
    pass


@pytest.fixture
def app_with_chat_router() -> FastAPI:
    """Create a test FastAPI app with the chat router mounted."""
    from mcp_server_langgraph.api.v1.chat import chat_router

    app = FastAPI()
    app.include_router(chat_router, prefix="/api/v1")
    return app


@pytest.fixture
def mock_llm_response() -> MagicMock:
    """Create a mock LiteLLM response."""
    response = MagicMock()
    response.id = "chatcmpl-test123"
    response.model = "gpt-4"

    message = MagicMock()
    message.role = "assistant"
    message.content = "Based on the provided context, I can help you with that."
    response.choices = [MagicMock(message=message)]

    usage = MagicMock()
    usage.prompt_tokens = 50
    usage.completion_tokens = 20
    usage.total_tokens = 70
    response.usage = usage

    return response


@pytest.mark.xdist_group(name="chat_resource_injection")
class TestChatResourceInjectionIntegration:
    """Integration tests for chat API resource injection."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_chat_completion_endpoint_accepts_resource_uris(
        self,
        app_with_chat_router: FastAPI,
        mock_llm_response: MagicMock,
    ) -> None:
        """
        GIVEN a chat completion request with resource_uris
        WHEN the /api/v1/chat/completions endpoint is called
        THEN the request is accepted and processed successfully
        """
        from mcp_server_langgraph.api.v1.chat import reset_chat_service

        # Reset singleton to ensure clean state
        reset_chat_service()

        with patch("mcp_server_langgraph.api.v1.chat.acompletion") as mock_acompletion:
            mock_acompletion.return_value = mock_llm_response

            client = TestClient(app_with_chat_router)
            response = client.post(
                "/api/v1/chat/completions",
                json={
                    "session_id": "test-session",
                    "messages": [{"role": "user", "content": "Tell me about the data."}],
                    "resource_uris": ["file:///data.txt"],
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["message"]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_resources_are_read_and_injected_into_context(
        self,
        app_with_chat_router: FastAPI,
        mock_llm_response: MagicMock,
    ) -> None:
        """
        GIVEN a configured MCPBridge with readable resources
        WHEN chat completion is called with resource_uris
        THEN resources are read and their content appears in the LLM messages
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl, set_chat_service, reset_chat_service
        from mcp_server_langgraph.api.v1.mcp_bridge import MCPResourceContent

        # Reset singleton
        reset_chat_service()

        # Create mock bridge with resource reading capability
        mock_bridge = MagicMock()
        mock_bridge.is_configured = False  # Use LiteLLM path (not MCP agent)
        mock_bridge.read_resource = AsyncMock(
            return_value=[
                MCPResourceContent(
                    uri="file:///project-docs.md",
                    mime_type="text/markdown",
                    text="# Project Documentation\n\nThis is the important context.",
                )
            ]
        )

        # Create service with mock bridge
        service = ChatServiceImpl(mcp_bridge=mock_bridge)
        set_chat_service(service)

        captured_messages = []

        async def capture_messages(*args, **kwargs):
            captured_messages.extend(kwargs.get("messages", []))
            return mock_llm_response

        with patch("mcp_server_langgraph.api.v1.chat.acompletion", side_effect=capture_messages):
            client = TestClient(app_with_chat_router)
            response = client.post(
                "/api/v1/chat/completions",
                json={
                    "session_id": "test-session",
                    "messages": [{"role": "user", "content": "What does the documentation say?"}],
                    "resource_uris": ["file:///project-docs.md"],
                },
            )

        assert response.status_code == 200

        # Verify resource was read
        mock_bridge.read_resource.assert_called_once_with("file:///project-docs.md")

        # Verify context was injected into messages
        assert len(captured_messages) > 0
        system_messages = [m for m in captured_messages if m.get("role") == "system"]
        assert len(system_messages) >= 1
        context_content = " ".join(m.get("content", "") for m in system_messages)
        assert "Project Documentation" in context_content
        assert "important context" in context_content

        # Clean up
        reset_chat_service()

    @pytest.mark.asyncio
    async def test_multiple_resources_all_injected(
        self,
        app_with_chat_router: FastAPI,
        mock_llm_response: MagicMock,
    ) -> None:
        """
        GIVEN multiple resource URIs
        WHEN chat completion is called
        THEN all resources are read and injected
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl, set_chat_service, reset_chat_service
        from mcp_server_langgraph.api.v1.mcp_bridge import MCPResourceContent

        reset_chat_service()

        mock_bridge = MagicMock()
        mock_bridge.is_configured = False

        async def mock_read_resource(uri: str):
            if "config" in uri:
                return [MCPResourceContent(uri=uri, mime_type="application/json", text='{"setting": "value"}')]
            elif "readme" in uri:
                return [MCPResourceContent(uri=uri, mime_type="text/markdown", text="# README\n\nGetting started guide")]
            return []

        mock_bridge.read_resource = AsyncMock(side_effect=mock_read_resource)

        service = ChatServiceImpl(mcp_bridge=mock_bridge)
        set_chat_service(service)

        captured_messages = []

        async def capture_messages(*args, **kwargs):
            captured_messages.extend(kwargs.get("messages", []))
            return mock_llm_response

        with patch("mcp_server_langgraph.api.v1.chat.acompletion", side_effect=capture_messages):
            client = TestClient(app_with_chat_router)
            response = client.post(
                "/api/v1/chat/completions",
                json={
                    "session_id": "test-session",
                    "messages": [{"role": "user", "content": "Explain both files."}],
                    "resource_uris": ["file:///config.json", "file:///readme.md"],
                },
            )

        assert response.status_code == 200
        assert mock_bridge.read_resource.call_count == 2

        # Both resources should be in context
        context_content = " ".join(m.get("content", "") for m in captured_messages if m.get("role") == "system")
        assert "setting" in context_content
        assert "README" in context_content

        reset_chat_service()

    @pytest.mark.asyncio
    async def test_missing_resources_handled_gracefully(
        self,
        app_with_chat_router: FastAPI,
        mock_llm_response: MagicMock,
    ) -> None:
        """
        GIVEN a resource URI that doesn't exist
        WHEN chat completion is called
        THEN the error is handled gracefully and the request succeeds
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl, set_chat_service, reset_chat_service
        from mcp_server_langgraph.api.v1.mcp_bridge import MCPResourceNotFoundError

        reset_chat_service()

        mock_bridge = MagicMock()
        mock_bridge.is_configured = False
        mock_bridge.read_resource = AsyncMock(
            side_effect=MCPResourceNotFoundError("Resource not found", uri="file:///missing.txt")
        )

        service = ChatServiceImpl(mcp_bridge=mock_bridge)
        set_chat_service(service)

        with patch("mcp_server_langgraph.api.v1.chat.acompletion") as mock_acompletion:
            mock_acompletion.return_value = mock_llm_response

            client = TestClient(app_with_chat_router)
            response = client.post(
                "/api/v1/chat/completions",
                json={
                    "session_id": "test-session",
                    "messages": [{"role": "user", "content": "Hello"}],
                    "resource_uris": ["file:///missing.txt"],
                },
            )

        # Should succeed despite missing resource
        assert response.status_code == 200
        assert "message" in response.json()

        reset_chat_service()

    @pytest.mark.asyncio
    async def test_streaming_with_resource_injection(
        self,
        app_with_chat_router: FastAPI,
    ) -> None:
        """
        GIVEN resource URIs for a streaming request
        WHEN /api/v1/chat/completions/stream is called
        THEN resources are injected and streaming works correctly
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl, set_chat_service, reset_chat_service
        from mcp_server_langgraph.api.v1.mcp_bridge import MCPResourceContent

        reset_chat_service()

        mock_bridge = MagicMock()
        mock_bridge.is_configured = False
        mock_bridge.read_resource = AsyncMock(
            return_value=[
                MCPResourceContent(
                    uri="file:///context.txt",
                    mime_type="text/plain",
                    text="Streaming test context",
                )
            ]
        )

        service = ChatServiceImpl(mcp_bridge=mock_bridge)
        set_chat_service(service)

        async def mock_stream_response(*args, **kwargs):
            async def stream_chunks():
                yield MagicMock(choices=[MagicMock(delta=MagicMock(content="Hello"))])
                yield MagicMock(choices=[MagicMock(delta=MagicMock(content=" world"))])

            return stream_chunks()

        with patch("mcp_server_langgraph.api.v1.chat.acompletion", side_effect=mock_stream_response):
            client = TestClient(app_with_chat_router)
            response = client.post(
                "/api/v1/chat/completions/stream",
                json={
                    "session_id": "test-session",
                    "messages": [{"role": "user", "content": "Stream this"}],
                    "resource_uris": ["file:///context.txt"],
                },
            )

        assert response.status_code == 200
        # SSE format
        assert response.headers.get("content-type", "").startswith("text/event-stream")

        # Verify resource was read
        mock_bridge.read_resource.assert_called_once_with("file:///context.txt")

        reset_chat_service()

    @pytest.mark.asyncio
    async def test_resource_injection_preserves_original_messages(
        self,
        app_with_chat_router: FastAPI,
        mock_llm_response: MagicMock,
    ) -> None:
        """
        GIVEN a conversation with multiple messages and resource URIs
        WHEN chat completion is called
        THEN original messages are preserved alongside injected context
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl, set_chat_service, reset_chat_service
        from mcp_server_langgraph.api.v1.mcp_bridge import MCPResourceContent

        reset_chat_service()

        mock_bridge = MagicMock()
        mock_bridge.is_configured = False
        mock_bridge.read_resource = AsyncMock(
            return_value=[MCPResourceContent(uri="file:///data.txt", mime_type="text/plain", text="Context data here")]
        )

        service = ChatServiceImpl(mcp_bridge=mock_bridge)
        set_chat_service(service)

        captured_messages = []

        async def capture_messages(*args, **kwargs):
            captured_messages.extend(kwargs.get("messages", []))
            return mock_llm_response

        with patch("mcp_server_langgraph.api.v1.chat.acompletion", side_effect=capture_messages):
            client = TestClient(app_with_chat_router)
            response = client.post(
                "/api/v1/chat/completions",
                json={
                    "session_id": "test-session",
                    "messages": [
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": "First question"},
                        {"role": "assistant", "content": "First answer"},
                        {"role": "user", "content": "Follow-up question"},
                    ],
                    "resource_uris": ["file:///data.txt"],
                },
            )

        assert response.status_code == 200

        # Should have resource context + all original messages
        roles = [m.get("role") for m in captured_messages]

        # Resource context should be prepended as system message
        assert "system" in roles

        # Original messages should still be there
        user_messages = [m for m in captured_messages if m.get("role") == "user"]
        assert len(user_messages) >= 2  # Both user messages preserved

        # Context should contain resource data
        system_contents = " ".join(m.get("content", "") for m in captured_messages if m.get("role") == "system")
        assert "Context data here" in system_contents

        reset_chat_service()
