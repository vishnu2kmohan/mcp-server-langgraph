"""
Tests for ChatServiceImpl.

TDD: These tests are written FIRST to define the expected behavior
of ChatServiceImpl, which wraps the LLM layer for chat completions.

Tests verify:
1. create_completion() returns a dict matching ChatCompletionResponse format
2. create_stream() yields chunks for streaming completions
3. get_history() returns message history or None if not found
4. Response includes id, message, usage, and model
5. Streaming chunks include delta content
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit

if TYPE_CHECKING:
    pass


@pytest.mark.xdist_group(name="chat_service_impl")
class TestChatServiceImpl:
    """Test suite for ChatServiceImpl."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def mock_llm_response(self) -> MagicMock:
        """Create a mock LiteLLM response."""
        response = MagicMock()
        response.id = "chatcmpl-abc123"
        response.model = "gpt-4"

        # Mock the message
        message = MagicMock()
        message.role = "assistant"
        message.content = "Hello! How can I help you today?"
        response.choices = [MagicMock(message=message)]

        # Mock usage
        usage = MagicMock()
        usage.prompt_tokens = 10
        usage.completion_tokens = 15
        usage.total_tokens = 25
        response.usage = usage

        return response

    @pytest.fixture
    def sample_messages(self) -> list[dict]:
        """Create sample messages for testing."""
        return [
            {"role": "user", "content": "Hello!"},
        ]

    # =========================================================================
    # create_completion() tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_create_completion_returns_dict(
        self,
        sample_messages: list[dict],
        mock_llm_response: MagicMock,
    ) -> None:
        """GIVEN a ChatServiceImpl with mocked LLM
        WHEN create_completion() is called
        THEN it returns a dict matching ChatCompletionResponse format
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        with patch("mcp_server_langgraph.api.v1.chat.acompletion") as mock_acompletion:
            mock_acompletion.return_value = mock_llm_response

            service = ChatServiceImpl()
            result = await service.create_completion(
                session_id="test-session",
                messages=sample_messages,
            )

        assert "id" in result
        assert "message" in result
        assert result["message"]["role"] == "assistant"
        assert result["message"]["content"] == "Hello! How can I help you today?"

    @pytest.mark.asyncio
    async def test_create_completion_includes_usage(
        self,
        sample_messages: list[dict],
        mock_llm_response: MagicMock,
    ) -> None:
        """GIVEN a ChatServiceImpl response
        WHEN create_completion() is called
        THEN it includes token usage information
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        with patch("mcp_server_langgraph.api.v1.chat.acompletion") as mock_acompletion:
            mock_acompletion.return_value = mock_llm_response

            service = ChatServiceImpl()
            result = await service.create_completion(
                session_id="test-session",
                messages=sample_messages,
            )

        assert "usage" in result
        assert result["usage"]["prompt_tokens"] == 10
        assert result["usage"]["completion_tokens"] == 15

    @pytest.mark.asyncio
    async def test_create_completion_passes_model_parameter(
        self,
        sample_messages: list[dict],
        mock_llm_response: MagicMock,
    ) -> None:
        """GIVEN a model parameter
        WHEN create_completion() is called
        THEN it passes the model to the LLM
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        with patch("mcp_server_langgraph.api.v1.chat.acompletion") as mock_acompletion:
            mock_acompletion.return_value = mock_llm_response

            service = ChatServiceImpl()
            await service.create_completion(
                session_id="test-session",
                messages=sample_messages,
                model="claude-3-opus",
            )

        mock_acompletion.assert_called_once()
        call_kwargs = mock_acompletion.call_args.kwargs
        assert call_kwargs["model"] == "claude-3-opus"

    @pytest.mark.asyncio
    async def test_create_completion_uses_default_model(
        self,
        sample_messages: list[dict],
        mock_llm_response: MagicMock,
    ) -> None:
        """GIVEN no model parameter
        WHEN create_completion() is called
        THEN it uses the default model from settings
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        with patch("mcp_server_langgraph.api.v1.chat.acompletion") as mock_acompletion:
            mock_acompletion.return_value = mock_llm_response

            service = ChatServiceImpl()
            await service.create_completion(
                session_id="test-session",
                messages=sample_messages,
            )

        mock_acompletion.assert_called_once()
        call_kwargs = mock_acompletion.call_args.kwargs
        # Should have a model (either from settings or default)
        assert "model" in call_kwargs

    @pytest.mark.asyncio
    async def test_create_completion_includes_trace_id(
        self,
        sample_messages: list[dict],
        mock_llm_response: MagicMock,
    ) -> None:
        """GIVEN a ChatServiceImpl response within a traced context
        WHEN create_completion() is called
        THEN it includes the current trace_id for observability correlation
        """
        from unittest.mock import MagicMock as MockClass

        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        # Create a mock span context with a valid trace ID
        mock_span = MockClass()
        mock_span_context = MockClass()
        mock_span_context.trace_id = 0x12345678901234567890123456789ABC
        mock_span.get_span_context.return_value = mock_span_context

        with (
            patch("mcp_server_langgraph.api.v1.chat.acompletion") as mock_acompletion,
            patch("mcp_server_langgraph.api.v1.chat.trace") as mock_trace,
        ):
            mock_acompletion.return_value = mock_llm_response
            mock_trace.get_current_span.return_value = mock_span

            service = ChatServiceImpl()
            result = await service.create_completion(
                session_id="test-session",
                messages=sample_messages,
            )

        assert "trace_id" in result
        assert result["trace_id"] == "12345678901234567890123456789abc"

    # =========================================================================
    # create_stream() tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_create_stream_yields_chunks(
        self,
        sample_messages: list[dict],
    ) -> None:
        """GIVEN a ChatServiceImpl with streaming enabled
        WHEN create_stream() is called
        THEN it yields streaming chunks
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        # Create mock streaming chunks
        async def mock_stream():
            for chunk in [
                MagicMock(choices=[MagicMock(delta=MagicMock(content="Hello"))]),
                MagicMock(choices=[MagicMock(delta=MagicMock(content=" world"))]),
                MagicMock(choices=[MagicMock(delta=MagicMock(content="!"))]),
            ]:
                yield chunk

        with patch("mcp_server_langgraph.api.v1.chat.acompletion") as mock_acompletion:
            mock_acompletion.return_value = mock_stream()

            service = ChatServiceImpl()
            chunks = []
            async for chunk in service.create_stream(
                session_id="test-session",
                messages=sample_messages,
            ):
                chunks.append(chunk)

        assert len(chunks) == 3
        assert chunks[0]["delta"]["content"] == "Hello"
        assert chunks[1]["delta"]["content"] == " world"
        assert chunks[2]["delta"]["content"] == "!"

    @pytest.mark.asyncio
    async def test_create_stream_passes_stream_parameter(
        self,
        sample_messages: list[dict],
    ) -> None:
        """GIVEN a streaming request
        WHEN create_stream() is called
        THEN it passes stream=True to the LLM
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        async def mock_stream():
            yield MagicMock(choices=[MagicMock(delta=MagicMock(content="Hi"))])

        with patch("mcp_server_langgraph.api.v1.chat.acompletion") as mock_acompletion:
            mock_acompletion.return_value = mock_stream()

            service = ChatServiceImpl()
            async for _ in service.create_stream(
                session_id="test-session",
                messages=sample_messages,
            ):
                pass

        mock_acompletion.assert_called_once()
        call_kwargs = mock_acompletion.call_args.kwargs
        assert call_kwargs["stream"] is True

    # =========================================================================
    # get_history() tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_get_history_returns_messages(self) -> None:
        """GIVEN a session with history
        WHEN get_history() is called
        THEN it returns the message history
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        mock_storage = MagicMock()
        mock_storage.get_messages = AsyncMock(
            return_value=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"},
            ]
        )

        service = ChatServiceImpl(session_storage=mock_storage)
        history = await service.get_history("test-session")

        assert history is not None
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_get_history_returns_none_for_unknown_session(self) -> None:
        """GIVEN a non-existent session
        WHEN get_history() is called
        THEN it returns None
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        mock_storage = MagicMock()
        mock_storage.get_messages = AsyncMock(return_value=None)

        service = ChatServiceImpl(session_storage=mock_storage)
        history = await service.get_history("unknown-session")

        assert history is None

    @pytest.mark.asyncio
    async def test_get_history_returns_empty_list_without_storage(self) -> None:
        """GIVEN no session storage configured
        WHEN get_history() is called
        THEN it returns an empty list (graceful fallback)
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        service = ChatServiceImpl(session_storage=None)
        history = await service.get_history("any-session")

        # Without storage, return empty list as graceful fallback
        assert history == []

    # =========================================================================
    # get_chat_service() integration tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_get_chat_service_returns_impl(self) -> None:
        """GIVEN the chat service getter
        WHEN get_chat_service() is called
        THEN it returns a ChatServiceImpl (not the stub)
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl, get_chat_service

        service = get_chat_service()

        assert isinstance(service, ChatServiceImpl)

    @pytest.mark.asyncio
    async def test_chat_service_impl_does_not_raise_not_implemented(
        self,
        sample_messages: list[dict],
        mock_llm_response: MagicMock,
    ) -> None:
        """GIVEN a ChatServiceImpl
        WHEN any method is called
        THEN it does NOT raise NotImplementedError
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        async def mock_stream():
            yield MagicMock(choices=[MagicMock(delta=MagicMock(content="Hi"))])

        with patch("mcp_server_langgraph.api.v1.chat.acompletion") as mock_acompletion:
            mock_acompletion.return_value = mock_llm_response

            service = ChatServiceImpl()

            # These should NOT raise NotImplementedError
            await service.create_completion(
                session_id="test-session",
                messages=sample_messages,
            )

        with patch("mcp_server_langgraph.api.v1.chat.acompletion") as mock_acompletion:
            mock_acompletion.return_value = mock_stream()

            async for _ in service.create_stream(
                session_id="test-session",
                messages=sample_messages,
            ):
                pass

        # get_history should work without storage
        await service.get_history("test-session")

    # =========================================================================
    # Resource injection tests (MCP 2025-11-25)
    # =========================================================================

    @pytest.mark.asyncio
    async def test_create_completion_with_resource_uris_injects_content(
        self,
        sample_messages: list[dict],
        mock_llm_response: MagicMock,
    ) -> None:
        """GIVEN a ChatServiceImpl with resource URIs
        WHEN create_completion() is called with resource_uris
        THEN it reads resources and injects content as system context
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl
        from mcp_server_langgraph.api.v1.mcp_bridge import MCPResourceContent

        # Mock MCP bridge for resource reading only (use LiteLLM for completion)
        mock_bridge = MagicMock()
        mock_bridge.is_configured = False  # Use LiteLLM path for completion
        mock_bridge.read_resource = AsyncMock(
            return_value=[
                MCPResourceContent(
                    uri="file:///data.txt",
                    mime_type="text/plain",
                    text="Important context data",
                )
            ]
        )

        with patch("mcp_server_langgraph.api.v1.chat.acompletion") as mock_acompletion:
            mock_acompletion.return_value = mock_llm_response

            service = ChatServiceImpl(mcp_bridge=mock_bridge)
            await service.create_completion(
                session_id="test-session",
                messages=sample_messages,
                resource_uris=["file:///data.txt"],
            )

        # Verify resources were read
        mock_bridge.read_resource.assert_called_once_with("file:///data.txt")

        # Verify LLM was called with injected context in messages
        mock_acompletion.assert_called_once()
        call_kwargs = mock_acompletion.call_args.kwargs
        messages = call_kwargs["messages"]

        # Should have a system message with resource content prepended
        assert any(msg.get("role") == "system" and "Important context data" in msg.get("content", "") for msg in messages)

    @pytest.mark.asyncio
    async def test_create_completion_with_multiple_resources_injects_all(
        self,
        sample_messages: list[dict],
        mock_llm_response: MagicMock,
    ) -> None:
        """GIVEN multiple resource URIs
        WHEN create_completion() is called
        THEN all resources are read and injected
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl
        from mcp_server_langgraph.api.v1.mcp_bridge import MCPResourceContent

        mock_bridge = MagicMock()
        mock_bridge.is_configured = False  # Use LiteLLM path for completion

        # Return different content for each resource
        async def mock_read_resource(uri: str) -> list[MCPResourceContent]:
            if uri == "file:///doc1.txt":
                return [MCPResourceContent(uri=uri, mime_type="text/plain", text="Document one content")]
            elif uri == "file:///doc2.txt":
                return [MCPResourceContent(uri=uri, mime_type="text/plain", text="Document two content")]
            return []

        mock_bridge.read_resource = AsyncMock(side_effect=mock_read_resource)

        with patch("mcp_server_langgraph.api.v1.chat.acompletion") as mock_acompletion:
            mock_acompletion.return_value = mock_llm_response

            service = ChatServiceImpl(mcp_bridge=mock_bridge)
            await service.create_completion(
                session_id="test-session",
                messages=sample_messages,
                resource_uris=["file:///doc1.txt", "file:///doc2.txt"],
            )

        # Verify both resources were read
        assert mock_bridge.read_resource.call_count == 2

        # Verify LLM was called with both resources in context
        call_kwargs = mock_acompletion.call_args.kwargs
        messages = call_kwargs["messages"]
        system_messages = [m for m in messages if m.get("role") == "system"]
        assert len(system_messages) >= 1
        context_content = " ".join(m.get("content", "") for m in system_messages)
        assert "Document one content" in context_content
        assert "Document two content" in context_content

    @pytest.mark.asyncio
    async def test_create_completion_without_resource_uris_works_normally(
        self,
        sample_messages: list[dict],
        mock_llm_response: MagicMock,
    ) -> None:
        """GIVEN no resource URIs
        WHEN create_completion() is called
        THEN it works normally without resource injection
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        with patch("mcp_server_langgraph.api.v1.chat.acompletion") as mock_acompletion:
            mock_acompletion.return_value = mock_llm_response

            service = ChatServiceImpl()
            result = await service.create_completion(
                session_id="test-session",
                messages=sample_messages,
                # No resource_uris parameter
            )

        assert result["message"]["content"] == "Hello! How can I help you today?"

    @pytest.mark.asyncio
    async def test_create_completion_handles_resource_not_found(
        self,
        sample_messages: list[dict],
        mock_llm_response: MagicMock,
    ) -> None:
        """GIVEN a non-existent resource URI
        WHEN create_completion() is called
        THEN it handles the error gracefully and proceeds without that resource
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl
        from mcp_server_langgraph.api.v1.mcp_bridge import MCPResourceNotFoundError

        mock_bridge = MagicMock()
        mock_bridge.is_configured = False  # Use LiteLLM path for completion
        mock_bridge.read_resource = AsyncMock(
            side_effect=MCPResourceNotFoundError("Resource not found", uri="file:///missing.txt")
        )

        with patch("mcp_server_langgraph.api.v1.chat.acompletion") as mock_acompletion:
            mock_acompletion.return_value = mock_llm_response

            service = ChatServiceImpl(mcp_bridge=mock_bridge)
            # Should NOT raise, should log warning and continue
            result = await service.create_completion(
                session_id="test-session",
                messages=sample_messages,
                resource_uris=["file:///missing.txt"],
            )

        # Should still return a valid response
        assert "message" in result

    @pytest.mark.asyncio
    async def test_create_completion_resource_injection_without_mcp_bridge(
        self,
        sample_messages: list[dict],
        mock_llm_response: MagicMock,
    ) -> None:
        """GIVEN resource URIs but no MCP bridge configured
        WHEN create_completion() is called
        THEN it proceeds without resource injection (logs warning)
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        with patch("mcp_server_langgraph.api.v1.chat.acompletion") as mock_acompletion:
            mock_acompletion.return_value = mock_llm_response

            # Service with no MCP bridge
            service = ChatServiceImpl(mcp_bridge=None)
            result = await service.create_completion(
                session_id="test-session",
                messages=sample_messages,
                resource_uris=["file:///data.txt"],
            )

        # Should still return a valid response
        assert "message" in result
        assert result["message"]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_create_stream_with_resource_uris_injects_content(
        self,
        sample_messages: list[dict],
    ) -> None:
        """GIVEN resource URIs for streaming
        WHEN create_stream() is called
        THEN resources are injected before streaming
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl
        from mcp_server_langgraph.api.v1.mcp_bridge import MCPResourceContent

        mock_bridge = MagicMock()
        mock_bridge.is_configured = False  # Use LiteLLM path for streaming
        mock_bridge.read_resource = AsyncMock(
            return_value=[
                MCPResourceContent(
                    uri="file:///context.txt",
                    mime_type="text/plain",
                    text="Streaming context data",
                )
            ]
        )

        async def mock_stream():
            yield MagicMock(choices=[MagicMock(delta=MagicMock(content="Response"))])

        with patch("mcp_server_langgraph.api.v1.chat.acompletion") as mock_acompletion:
            mock_acompletion.return_value = mock_stream()

            service = ChatServiceImpl(mcp_bridge=mock_bridge)
            chunks = []
            async for chunk in service.create_stream(
                session_id="test-session",
                messages=sample_messages,
                resource_uris=["file:///context.txt"],
            ):
                chunks.append(chunk)

        # Verify resource was read
        mock_bridge.read_resource.assert_called_once_with("file:///context.txt")

        # Verify streaming still works
        assert len(chunks) == 1
        assert chunks[0]["delta"]["content"] == "Response"
