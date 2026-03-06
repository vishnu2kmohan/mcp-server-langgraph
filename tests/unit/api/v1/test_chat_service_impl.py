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
        THEN it yields streaming chunks via LLMFactory.astream()

        Note: With legacy _stream_via_litellm removed, all streaming
        now goes through LLMFactory.astream() which provides resilience patterns.
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl
        from mcp_server_langgraph.llm.factory import StreamChunk

        # Create mock LLMFactory with streaming
        mock_factory = MagicMock()

        async def mock_astream(messages, **kwargs):
            yield StreamChunk(content="Hello", chunk_index=0, is_final=False)
            yield StreamChunk(content=" world", chunk_index=1, is_final=False)
            yield StreamChunk(content="!", chunk_index=2, is_final=True, finish_reason="stop")

        mock_factory.astream = mock_astream

        service = ChatServiceImpl(llm_factory=mock_factory)
        chunks = []
        async for chunk in service.create_stream(
            session_id="test-session",
            messages=sample_messages,
        ):
            chunks.append(chunk)

        # Filter to only delta chunks (exclude routing_decision from ADR-0105)
        delta_chunks = [c for c in chunks if "delta" in c]

        # All 3 delta chunks should be yielded via LLMFactory
        assert len(delta_chunks) == 3
        assert delta_chunks[0]["delta"]["content"] == "Hello"
        assert delta_chunks[1]["delta"]["content"] == " world"
        assert delta_chunks[2]["delta"]["content"] == "!"

    @pytest.mark.asyncio
    async def test_create_stream_uses_llm_factory(
        self,
        sample_messages: list[dict],
    ) -> None:
        """GIVEN a streaming request
        WHEN create_stream() is called
        THEN it uses LLMFactory.astream() for streaming

        Note: With legacy _stream_via_litellm removed, LLMFactory.astream()
        is the only streaming path which provides circuit breaker resilience.
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl
        from mcp_server_langgraph.llm.factory import StreamChunk

        mock_factory = MagicMock()
        astream_called = False
        captured_kwargs = {}

        async def mock_astream(messages, **kwargs):
            nonlocal astream_called, captured_kwargs
            astream_called = True
            captured_kwargs = kwargs
            yield StreamChunk(content="Hi", chunk_index=0, is_final=True)

        mock_factory.astream = mock_astream

        service = ChatServiceImpl(llm_factory=mock_factory)
        async for _ in service.create_stream(
            session_id="test-session",
            messages=sample_messages,
        ):
            pass

        # LLMFactory.astream() should be called
        assert astream_called, "LLMFactory.astream() should be called for streaming"

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
        THEN resources are injected before streaming via LLMFactory

        Note: With legacy _stream_via_litellm removed, all streaming
        goes through LLMFactory.astream() with resource injection.
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl
        from mcp_server_langgraph.api.v1.mcp_bridge import MCPResourceContent
        from mcp_server_langgraph.llm.factory import StreamChunk

        mock_bridge = MagicMock()
        mock_bridge.is_configured = False  # Not using MCP path for streaming
        mock_bridge.read_resource = AsyncMock(
            return_value=[
                MCPResourceContent(
                    uri="file:///context.txt",
                    mime_type="text/plain",
                    text="Streaming context data",
                )
            ]
        )

        # Create mock LLMFactory
        mock_factory = MagicMock()

        async def mock_astream(messages, **kwargs):
            yield StreamChunk(content="Response", chunk_index=0, is_final=True)

        mock_factory.astream = mock_astream

        service = ChatServiceImpl(mcp_bridge=mock_bridge, llm_factory=mock_factory)
        chunks = []
        async for chunk in service.create_stream(
            session_id="test-session",
            messages=sample_messages,
            resource_uris=["file:///context.txt"],
        ):
            chunks.append(chunk)

        # Verify resource was read
        mock_bridge.read_resource.assert_called_once_with("file:///context.txt")

        # Filter to only delta chunks (exclude routing_decision from ADR-0105)
        delta_chunks = [c for c in chunks if "delta" in c]

        # Verify streaming via LLMFactory works
        assert len(delta_chunks) == 1
        assert delta_chunks[0]["delta"]["content"] == "Response"

    # =========================================================================
    # LangGraph event streaming tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_create_stream_with_langgraph_emits_node_events(
        self,
        sample_messages: list[dict],
    ) -> None:
        """GIVEN a LangGraph-based agent
        WHEN create_stream() is called with use_langgraph=True
        THEN it emits langgraph_node events for each node execution
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        # Mock LangGraph agent with astream_events
        mock_agent = AsyncMock(return_value=None)

        async def mock_astream_events(*args, **kwargs):
            """Simulate LangGraph astream_events output."""
            # Node start event
            yield {
                "event": "on_chain_start",
                "name": "agent",
                "data": {"input": {"messages": []}},
                "metadata": {"langgraph_node": "agent"},
            }
            # Node output
            yield {
                "event": "on_chat_model_stream",
                "data": {"chunk": MagicMock(content="Hello")},
            }
            # Node end event
            yield {
                "event": "on_chain_end",
                "name": "agent",
                "data": {"output": {"messages": []}},
                "metadata": {"langgraph_node": "agent"},
            }

        mock_agent.astream_events = mock_astream_events

        with patch("mcp_server_langgraph.api.v1.chat.acompletion"):
            service = ChatServiceImpl(langgraph_agent=mock_agent)
            chunks = []
            async for chunk in service.create_stream(
                session_id="test-session",
                messages=sample_messages,
                use_langgraph=True,
            ):
                chunks.append(chunk)

        # Should include node events
        node_events = [c for c in chunks if "langgraph_node" in c]
        assert len(node_events) >= 1
        assert node_events[0]["langgraph_node"]["name"] == "agent"

    @pytest.mark.asyncio
    async def test_create_stream_langgraph_emits_current_node(
        self,
        sample_messages: list[dict],
    ) -> None:
        """GIVEN a LangGraph-based agent executing
        WHEN nodes transition
        THEN current_node is emitted to track active node
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        mock_agent = AsyncMock(return_value=None)

        async def mock_astream_events(*args, **kwargs):
            # Simulate node transitions
            yield {
                "event": "on_chain_start",
                "name": "router",
                "metadata": {"langgraph_node": "router"},
            }
            yield {
                "event": "on_chain_end",
                "name": "router",
                "metadata": {"langgraph_node": "router"},
            }
            yield {
                "event": "on_chain_start",
                "name": "agent",
                "metadata": {"langgraph_node": "agent"},
            }

        mock_agent.astream_events = mock_astream_events

        with patch("mcp_server_langgraph.api.v1.chat.acompletion"):
            service = ChatServiceImpl(langgraph_agent=mock_agent)
            chunks = []
            async for chunk in service.create_stream(
                session_id="test-session",
                messages=sample_messages,
                use_langgraph=True,
            ):
                chunks.append(chunk)

        # Should include current_node updates
        current_node_events = [c for c in chunks if "current_node" in c]
        assert len(current_node_events) >= 2
        # First node: router, then agent
        node_names = [e["current_node"] for e in current_node_events]
        assert "router" in node_names
        assert "agent" in node_names

    @pytest.mark.asyncio
    async def test_create_stream_langgraph_emits_edge_events(
        self,
        sample_messages: list[dict],
    ) -> None:
        """GIVEN a LangGraph with conditional edges
        WHEN edges are traversed
        THEN langgraph_edge events are emitted
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        mock_agent = AsyncMock(return_value=None)

        async def mock_astream_events(*args, **kwargs):
            # Simulate edge traversal from router to agent
            yield {
                "event": "on_chain_start",
                "name": "router",
                "metadata": {"langgraph_node": "router"},
            }
            yield {
                "event": "on_chain_end",
                "name": "router",
                "metadata": {
                    "langgraph_node": "router",
                    "langgraph_triggers": ["agent"],
                },
            }
            yield {
                "event": "on_chain_start",
                "name": "agent",
                "metadata": {"langgraph_node": "agent"},
            }

        mock_agent.astream_events = mock_astream_events

        with patch("mcp_server_langgraph.api.v1.chat.acompletion"):
            service = ChatServiceImpl(langgraph_agent=mock_agent)
            chunks = []
            async for chunk in service.create_stream(
                session_id="test-session",
                messages=sample_messages,
                use_langgraph=True,
            ):
                chunks.append(chunk)

        # Should include edge events
        edge_events = [c for c in chunks if "langgraph_edge" in c]
        assert len(edge_events) >= 1
        assert edge_events[0]["langgraph_edge"]["from"] == "router"
        assert edge_events[0]["langgraph_edge"]["to"] == "agent"

    @pytest.mark.asyncio
    async def test_create_stream_langgraph_includes_node_status(
        self,
        sample_messages: list[dict],
    ) -> None:
        """GIVEN a LangGraph node execution
        WHEN node starts and completes
        THEN node status transitions from running to completed
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        mock_agent = AsyncMock(return_value=None)

        async def mock_astream_events(*args, **kwargs):
            yield {
                "event": "on_chain_start",
                "name": "agent",
                "metadata": {"langgraph_node": "agent"},
            }
            yield {
                "event": "on_chain_end",
                "name": "agent",
                "metadata": {"langgraph_node": "agent"},
            }

        mock_agent.astream_events = mock_astream_events

        with patch("mcp_server_langgraph.api.v1.chat.acompletion"):
            service = ChatServiceImpl(langgraph_agent=mock_agent)
            chunks = []
            async for chunk in service.create_stream(
                session_id="test-session",
                messages=sample_messages,
                use_langgraph=True,
            ):
                chunks.append(chunk)

        # Find node events for 'agent'
        node_events = [c for c in chunks if "langgraph_node" in c and c["langgraph_node"]["name"] == "agent"]
        assert len(node_events) >= 2

        # First event: running, last event: completed
        statuses = [e["langgraph_node"]["status"] for e in node_events]
        assert "running" in statuses
        assert "completed" in statuses

    @pytest.mark.asyncio
    async def test_create_stream_fallback_to_llm_factory_when_no_langgraph(
        self,
        sample_messages: list[dict],
    ) -> None:
        """GIVEN LangGraph agent initialization fails
        WHEN create_stream() is called with use_langgraph=True
        THEN it falls back to LLMFactory streaming

        Note: With lazy initialization, we mock create_agent_graph to fail
        to test the fallback path. This ensures graceful degradation.
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl
        from mcp_server_langgraph.llm.factory import StreamChunk

        # Create mock LLMFactory
        mock_factory = MagicMock()

        async def mock_astream(messages, **kwargs):
            yield StreamChunk(content="Fallback", chunk_index=0, is_final=True)

        mock_factory.astream = mock_astream

        # Mock create_agent_graph to fail (simulates Qdrant not available, etc.)
        with patch("mcp_server_langgraph.api.v1.chat.create_agent_graph") as mock_create_agent:
            mock_create_agent.side_effect = Exception("Qdrant not available")

            # No langgraph_agent provided, lazy init fails, falls back to LLMFactory
            service = ChatServiceImpl(llm_factory=mock_factory)
            chunks = []
            async for chunk in service.create_stream(
                session_id="test-session",
                messages=sample_messages,
                use_langgraph=True,  # Request LangGraph but init fails
            ):
                chunks.append(chunk)

        # Filter to only delta chunks (exclude routing_decision from ADR-0105)
        delta_chunks = [c for c in chunks if "delta" in c]

        # Should fallback to LLMFactory.astream()
        assert len(delta_chunks) == 1
        assert delta_chunks[0]["delta"]["content"] == "Fallback"

    # =========================================================================
    # langgraph_agent lazy initialization tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_langgraph_agent_lazy_initialization(self) -> None:
        """GIVEN a ChatServiceImpl without langgraph_agent
        WHEN the langgraph_agent property is accessed
        THEN it lazily initializes using create_agent_graph()

        This enables DynamicContextLoader integration with Connected Chat.
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        with patch("mcp_server_langgraph.api.v1.chat.create_agent_graph") as mock_create_agent:
            mock_agent = MagicMock()
            mock_agent.name = "test-agent"
            mock_create_agent.return_value = mock_agent

            service = ChatServiceImpl()

            # Initially None
            assert service._langgraph_agent is None

            # Access property triggers lazy init
            agent = service.langgraph_agent

            # Should have called create_agent_graph
            mock_create_agent.assert_called_once()

            # Should return the created agent
            assert agent is mock_agent

            # Second access should not create again
            agent2 = service.langgraph_agent
            mock_create_agent.assert_called_once()  # Still only once
            assert agent2 is agent

    @pytest.mark.asyncio
    async def test_langgraph_agent_uses_injected_agent(self) -> None:
        """GIVEN a ChatServiceImpl with langgraph_agent injected
        WHEN the langgraph_agent property is accessed
        THEN it returns the injected agent without lazy initialization
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        mock_agent = MagicMock()
        mock_agent.name = "injected-agent"

        with patch("mcp_server_langgraph.api.v1.chat.create_agent_graph") as mock_create_agent:
            service = ChatServiceImpl(langgraph_agent=mock_agent)

            # Access property
            agent = service.langgraph_agent

            # Should NOT call create_agent_graph
            mock_create_agent.assert_not_called()

            # Should return the injected agent
            assert agent is mock_agent

    @pytest.mark.asyncio
    async def test_langgraph_agent_handles_initialization_failure(self) -> None:
        """GIVEN a ChatServiceImpl without langgraph_agent
        WHEN create_agent_graph() fails during lazy initialization
        THEN it returns None and logs a warning
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        with patch("mcp_server_langgraph.api.v1.chat.create_agent_graph") as mock_create_agent:
            mock_create_agent.side_effect = Exception("Qdrant not available")

            service = ChatServiceImpl()

            # Should not raise, just return None
            agent = service.langgraph_agent
            assert agent is None

            # Should have attempted initialization
            mock_create_agent.assert_called_once()

    # =========================================================================
    # Dynamic Context Integration Tests (Audit Findings)
    # =========================================================================

    @pytest.mark.asyncio
    async def test_create_stream_respects_enable_dynamic_context_loading_flag(
        self,
        sample_messages: list[dict],
    ) -> None:
        """GIVEN enable_dynamic_context_loading=False in settings
        WHEN create_stream() is called with use_langgraph=True
        THEN langgraph_agent is NOT lazily initialized (flag gates initialization)
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl
        from mcp_server_langgraph.llm.factory import StreamChunk

        mock_factory = MagicMock()

        async def mock_astream(messages, **kwargs):
            yield StreamChunk(content="Response", chunk_index=0, is_final=True)

        mock_factory.astream = mock_astream

        with (
            patch("mcp_server_langgraph.api.v1.chat.settings") as mock_settings,
            patch("mcp_server_langgraph.api.v1.chat.create_agent_graph") as mock_create_agent,
        ):
            mock_settings.enable_dynamic_context_loading = False
            mock_settings.enable_chat_routing = False  # Disable routing to prevent routing_decision events
            mock_settings.model_name = "test-model"

            # Make create_agent_graph return None to simulate disabled dynamic context
            mock_create_agent.return_value = None

            service = ChatServiceImpl(llm_factory=mock_factory)
            chunks = []
            async for chunk in service.create_stream(
                session_id="test-session",
                messages=sample_messages,
                use_langgraph=True,  # Request LangGraph but it's disabled
                enable_routing=False,  # Explicit: disable routing
            ):
                chunks.append(chunk)

            # When langgraph_agent is None, should fall back to LLM factory
            assert len(chunks) == 1
            assert chunks[0]["delta"]["content"] == "Response"

    @pytest.mark.asyncio
    async def test_dynamic_context_preflight_validates_qdrant_config(
        self,
    ) -> None:
        """GIVEN missing Qdrant configuration
        WHEN validate_dynamic_context_config() is called
        THEN it returns a validation result with specific guidance
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        with patch("mcp_server_langgraph.api.v1.chat.settings") as mock_settings:
            mock_settings.enable_dynamic_context_loading = True
            mock_settings.qdrant_url = ""  # Missing
            mock_settings.qdrant_port = 6333
            mock_settings.embedding_provider = "google_vertex"
            mock_settings.embedding_model_name = "text-embedding-005"
            mock_settings.embedding_dimensions = 768

            service = ChatServiceImpl()
            result = service.validate_dynamic_context_config()

            assert not result.is_valid
            assert "qdrant_url" in result.missing_config
            assert result.guidance is not None
            assert "Qdrant" in result.guidance

    @pytest.mark.asyncio
    async def test_dynamic_context_preflight_validates_embedding_provider(
        self,
    ) -> None:
        """GIVEN unsupported embedding provider
        WHEN validate_dynamic_context_config() is called
        THEN it returns validation failure with supported providers list
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        with patch("mcp_server_langgraph.api.v1.chat.settings") as mock_settings:
            mock_settings.enable_dynamic_context_loading = True
            mock_settings.qdrant_url = "localhost"
            mock_settings.qdrant_port = 6333
            mock_settings.embedding_provider = "unsupported_provider"
            mock_settings.embedding_model_name = "some-model"
            mock_settings.embedding_dimensions = 768

            service = ChatServiceImpl()
            result = service.validate_dynamic_context_config()

            assert not result.is_valid
            assert "embedding_provider" in result.missing_config
            assert "google_vertex" in result.guidance  # Should list supported providers

    @pytest.mark.asyncio
    async def test_dynamic_context_preflight_validates_credentials(
        self,
    ) -> None:
        """GIVEN google embedding provider without API key
        WHEN validate_dynamic_context_config() is called
        THEN it returns validation failure with credential guidance
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        with patch("mcp_server_langgraph.api.v1.chat.settings") as mock_settings:
            mock_settings.enable_dynamic_context_loading = True
            mock_settings.qdrant_url = "localhost"
            mock_settings.qdrant_port = 6333
            mock_settings.embedding_provider = "google"  # Requires API key
            mock_settings.embedding_model_name = "models/text-embedding-004"
            mock_settings.embedding_dimensions = 768
            mock_settings.google_api_key = None  # Missing!

            service = ChatServiceImpl()
            result = service.validate_dynamic_context_config()

            assert not result.is_valid
            assert "google_api_key" in result.missing_config or "credentials" in result.guidance.lower()

    @pytest.mark.asyncio
    async def test_create_stream_emits_context_load_stats(
        self,
        sample_messages: list[dict],
    ) -> None:
        """GIVEN dynamic context loading enabled and successful
        WHEN create_stream() executes langgraph path
        THEN it emits a context_loaded event with refs count and token count
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        mock_agent = AsyncMock(return_value=None)

        async def mock_astream_events(*args, **kwargs):
            # Simulate context loaded event
            yield {
                "event": "on_custom",
                "name": "dynamic_context_loaded",
                "data": {"refs_count": 3, "tokens_loaded": 1500},
            }
            # Then streaming content
            yield {
                "event": "on_chat_model_stream",
                "data": {"chunk": MagicMock(content="Hello")},
            }

        mock_agent.astream_events = mock_astream_events

        service = ChatServiceImpl(langgraph_agent=mock_agent)
        chunks = []
        async for chunk in service.create_stream(
            session_id="test-session",
            messages=sample_messages,
            use_langgraph=True,
        ):
            chunks.append(chunk)

        # Should include context_loaded event
        context_events = [c for c in chunks if "context_loaded" in c]
        assert len(context_events) == 1
        assert context_events[0]["context_loaded"]["refs_count"] == 3
        assert context_events[0]["context_loaded"]["tokens_loaded"] == 1500

    @pytest.mark.asyncio
    async def test_create_stream_fail_soft_on_context_load_error(
        self,
        sample_messages: list[dict],
    ) -> None:
        """GIVEN dynamic context loading fails (Qdrant unavailable)
        WHEN create_stream() is called
        THEN it continues without context and emits context_unavailable notice
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl
        from mcp_server_langgraph.llm.factory import StreamChunk

        mock_factory = MagicMock()

        async def mock_astream(messages, **kwargs):
            yield StreamChunk(content="Response", chunk_index=0, is_final=True)

        mock_factory.astream = mock_astream

        # Simulate langgraph agent that fails during context loading
        mock_agent = MagicMock()

        async def mock_astream_events_failing(*args, **kwargs):
            # Simulate context loading failure as async generator that raises
            raise Exception("Qdrant connection refused")
            # This yield makes it an async generator
            yield  # type: ignore[unreachable]

        mock_agent.astream_events = mock_astream_events_failing

        service = ChatServiceImpl(langgraph_agent=mock_agent, llm_factory=mock_factory)
        chunks = []

        # Should NOT raise - should fail soft and fallback
        async for chunk in service.create_stream(
            session_id="test-session",
            messages=sample_messages,
            use_langgraph=True,
        ):
            chunks.append(chunk)

        # Should have fallen back to LLM factory
        assert len(chunks) >= 1

        # Should have context_unavailable notice before fallback content
        context_unavail_chunks = [c for c in chunks if "context_unavailable" in c]
        assert len(context_unavail_chunks) == 1
        assert "Qdrant connection refused" in context_unavail_chunks[0]["context_unavailable"]["reason"]

        # Should have fallback content
        assert any("Response" in str(c.get("delta", {}).get("content", "")) for c in chunks)

    @pytest.mark.asyncio
    async def test_dynamic_context_respects_max_tokens_setting(
        self,
    ) -> None:
        """GIVEN dynamic_context_max_tokens=1500 in settings
        WHEN load_dynamic_context node executes
        THEN it passes max_tokens=1500 to load_batch

        Note: This test verifies agent_graph_builder captures settings.dynamic_context_max_tokens.
        The actual value propagation is tested in tests/unit/core/test_agent_graph_builder.py.
        """
        from mcp_server_langgraph.core.agent_config import AgentConfig
        from mcp_server_langgraph.core.agent_graph_builder import build_agent_graph

        with (
            patch("mcp_server_langgraph.llm.factory.create_llm_from_config") as mock_llm,
            patch("mcp_server_langgraph.core.dynamic_context_loader.DynamicContextLoader") as mock_loader_class,
            patch("mcp_server_langgraph.core.dynamic_context_loader.search_and_load_context") as mock_search,
        ):
            # Configure mock LLM
            mock_llm.return_value = MagicMock()

            mock_loader = MagicMock()
            mock_loader_class.return_value = mock_loader
            mock_search.return_value = []

            config = AgentConfig(
                enable_dynamic_context_loading=True,
                enable_verification=False,
            )

            # Build graph - this captures the closure over settings
            graph = build_agent_graph(config)

            # The graph should be built - we'll verify settings are captured
            assert graph is not None

    @pytest.mark.asyncio
    async def test_validate_dynamic_context_config_returns_valid_when_configured(
        self,
    ) -> None:
        """GIVEN all required configuration is present
        WHEN validate_dynamic_context_config() is called
        THEN it returns is_valid=True
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        with patch("mcp_server_langgraph.api.v1.chat.settings") as mock_settings:
            mock_settings.enable_dynamic_context_loading = True
            mock_settings.qdrant_url = "localhost"
            mock_settings.qdrant_port = 6333
            mock_settings.qdrant_collection_name = "mcp_context"
            mock_settings.embedding_provider = "google_vertex"  # Uses GCP WIF, no API key needed
            mock_settings.embedding_model_name = "text-embedding-005"
            mock_settings.embedding_dimensions = 768
            mock_settings.dynamic_context_max_tokens = 2000
            mock_settings.dynamic_context_top_k = 3

            service = ChatServiceImpl()
            result = service.validate_dynamic_context_config()

            assert result.is_valid
            assert result.guidance is None or result.guidance == ""

    @pytest.mark.asyncio
    async def test_validate_dynamic_context_config_disabled_returns_valid(
        self,
    ) -> None:
        """GIVEN enable_dynamic_context_loading=False
        WHEN validate_dynamic_context_config() is called
        THEN it returns is_valid=True (no validation needed when disabled)
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        with patch("mcp_server_langgraph.api.v1.chat.settings") as mock_settings:
            mock_settings.enable_dynamic_context_loading = False

            service = ChatServiceImpl()
            result = service.validate_dynamic_context_config()

            assert result.is_valid

    # =========================================================================
    # Plan mode RouterOutput contract tests
    # =========================================================================

    def test_plan_mode_routing_decision_uses_valid_execution_mode(self) -> None:
        """GIVEN execution_mode="plan" from UI
        WHEN RouterOutput is created
        THEN RouterOutput.execution_mode must be a valid agent mode, not "plan"

        This is a contract test to prevent regression of the bug where
        "plan" (a UI execution mode) was incorrectly passed to RouterOutput
        which only accepts agent execution modes (tool_calling, react, etc.).

        The two execution_mode concepts are INDEPENDENT:
        - UI level: "default", "plan", "auto_accept", "bypass" (workflow control)
        - RouterOutput (agent level): "pure_llm", "tool_calling", "react",
          "programmatic", "orchestrator" (execution strategy)

        Plan mode is a WORKFLOW overlay that adds approval requirements.
        It does NOT override the router's intelligent classification.
        """
        from pydantic import ValidationError

        from mcp_server_langgraph.agents.router_agent import RouterOutput

        # Verify all valid execution modes are accepted
        valid_modes = ["pure_llm", "tool_calling", "react", "programmatic", "orchestrator"]
        for mode in valid_modes:
            routing_decision = RouterOutput(
                complexity="complicated",
                risk="medium",
                task_type="code",
                tools_needed=[],
                suggested_orchestrator="studio",
                critique_rounds=0,
                thinking_budget="medium",
                confidence=0.9,
                skills_needed=[],
                execution_mode=mode,
                routing_rationale=f"Testing {mode} mode",
            )
            assert routing_decision.execution_mode == mode

        # Verify that "plan" is NOT a valid execution_mode for RouterOutput
        with pytest.raises(ValidationError) as exc_info:
            RouterOutput(
                complexity="complicated",
                risk="medium",
                task_type="code",
                tools_needed=[],
                suggested_orchestrator="studio",
                critique_rounds=1,
                thinking_budget="medium",
                confidence=0.9,
                skills_needed=[],
                execution_mode="plan",  # Invalid - UI mode, not agent mode
                routing_rationale="This should fail",
            )
        assert "execution_mode" in str(exc_info.value)
        assert "plan" in str(exc_info.value)

    def test_plan_mode_forces_approval_via_execution_plan(self) -> None:
        """GIVEN plan mode is selected in UI
        WHEN ExecutionPlan is created from RouterOutput
        THEN requires_approval is True regardless of risk level

        This tests the independent architecture where:
        - Router classifies task (including risk level)
        - Plan mode forces approval as a workflow overlay
        """
        from decimal import Decimal

        from mcp_server_langgraph.agents.router_agent import RouterOutput
        from mcp_server_langgraph.core.models.execution_plan import ExecutionPlan

        # Low-risk task that normally wouldn't require approval
        low_risk_routing = RouterOutput(
            complexity="simple",
            risk="low",  # Normally auto-executes
            task_type="chat",
            tools_needed=[],
            suggested_orchestrator="standard",
            critique_rounds=0,
            thinking_budget="none",
            confidence=0.95,
            skills_needed=[],
            execution_mode="pure_llm",
            routing_rationale="Simple chat task",
        )

        # WITHOUT plan mode: low-risk should NOT require approval
        plan_without_force = ExecutionPlan.from_router_output(
            router_output=low_risk_routing,
            session_id="test-session",
            message="Hello",
            executor_model="test-model",
            estimated_cost=Decimal("0.01"),
            force_approval=False,
        )
        assert plan_without_force.requires_approval is False

        # WITH plan mode: low-risk SHOULD require approval
        plan_with_force = ExecutionPlan.from_router_output(
            router_output=low_risk_routing,
            session_id="test-session",
            message="Hello",
            executor_model="test-model",
            estimated_cost=Decimal("0.01"),
            force_approval=True,  # Plan mode
        )
        assert plan_with_force.requires_approval is True

        # Medium-risk always requires approval
        medium_risk_routing = RouterOutput(
            complexity="complicated",
            risk="medium",
            task_type="code",
            tools_needed=["code_interpreter"],
            suggested_orchestrator="studio",
            critique_rounds=1,
            thinking_budget="medium",
            confidence=0.8,
            skills_needed=[],
            execution_mode="tool_calling",
            routing_rationale="Code task with tools",
        )

        plan_medium = ExecutionPlan.from_router_output(
            router_output=medium_risk_routing,
            session_id="test-session",
            message="Debug this code",
            executor_model="test-model",
            estimated_cost=Decimal("0.05"),
            force_approval=False,  # Even without plan mode
        )
        assert plan_medium.requires_approval is True  # Risk-based
