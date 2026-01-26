"""
LLM Streaming WebSocket Handler Tests.

TDD tests for the LLM Streaming WebSocket using the standardized WebSocketBase.

Tests verify:
- Handler extends WebSocketBase correctly
- Method signatures match base class contract
- Message handling dispatches correctly
- Subscription/unsubscription flows work
"""

from __future__ import annotations

import gc
from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_server_langgraph.websocket import MessageEnvelope, WebSocketConfig

pytestmark = [pytest.mark.unit, pytest.mark.websocket]


@pytest.fixture
def mock_websocket() -> MagicMock:
    """Create a mock WebSocket for testing."""
    ws = MagicMock()
    ws.accept = AsyncMock(return_value=None)  # noqa: async-mock-config
    ws.close = AsyncMock(return_value=None)  # noqa: async-mock-config
    ws.send_json = AsyncMock(return_value=None)  # noqa: async-mock-config
    ws.send_text = AsyncMock(return_value=None)  # noqa: async-mock-config
    ws.receive_json = AsyncMock(return_value=None)  # noqa: async-mock-config
    ws.receive_text = AsyncMock(return_value=None)  # noqa: async-mock-config
    ws.query_params = {}
    ws.headers = {}
    ws.client_state = MagicMock()
    return ws


@pytest.mark.xdist_group(name="llm_streaming_ws")
class TestLLMStreamingHandlerConstruction:
    """Test LLMStreamingHandler initialization and base class contract."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_handler_extends_websocket_base(self) -> None:
        """
        GIVEN the LLMStreamingHandler class
        WHEN checking its base classes
        THEN it should extend WebSocketBase.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase
        from mcp_server_langgraph.websocket.handlers.llm_streaming import (
            LLMStreamingHandler,
        )

        handler = LLMStreamingHandler(
            config=WebSocketConfig(endpoint_name="llm-streaming")
        )
        assert isinstance(handler, WebSocketBase)

    def test_handler_has_abstract_method_handle_message(self) -> None:
        """
        GIVEN the LLMStreamingHandler class
        WHEN inspecting its methods
        THEN it should implement handle_message (not on_message).
        """
        from mcp_server_langgraph.websocket.handlers.llm_streaming import (
            LLMStreamingHandler,
        )

        handler = LLMStreamingHandler(
            config=WebSocketConfig(endpoint_name="llm-streaming")
        )

        # Should have handle_message method, not on_message
        assert hasattr(handler, "handle_message")
        assert callable(getattr(handler, "handle_message"))


@pytest.mark.xdist_group(name="llm_streaming_ws")
class TestLLMStreamingLifecycle:
    """Test LLM Streaming WebSocket lifecycle methods."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_on_connect_receives_auth_user(self, mock_websocket: MagicMock) -> None:
        """
        GIVEN an LLMStreamingHandler
        WHEN on_connect is called
        THEN it should accept AuthUser (not optional).
        """
        from mcp_server_langgraph.websocket.handlers.llm_streaming import (
            LLMStreamingHandler,
        )
        from mcp_server_langgraph.websocket.types import AuthUser

        handler = LLMStreamingHandler(
            config=WebSocketConfig(endpoint_name="llm-streaming")
        )
        handler._websocket = mock_websocket

        user = AuthUser(id="test-user", username="testuser")

        # Should not raise - on_connect accepts AuthUser
        await handler.on_connect(user)

    @pytest.mark.asyncio
    async def test_on_disconnect_has_no_parameters(self, mock_websocket: MagicMock) -> None:
        """
        GIVEN an LLMStreamingHandler with an active connection
        WHEN on_disconnect is called
        THEN it should accept no parameters (accesses self._user if needed).
        """
        from mcp_server_langgraph.websocket.handlers.llm_streaming import (
            LLMStreamingHandler,
        )
        from mcp_server_langgraph.websocket.types import AuthUser

        handler = LLMStreamingHandler(
            config=WebSocketConfig(endpoint_name="llm-streaming")
        )
        handler._websocket = mock_websocket
        handler._user = AuthUser(id="test-user", username="testuser")

        # Should not raise - on_disconnect takes no parameters
        await handler.on_disconnect()


@pytest.mark.xdist_group(name="llm_streaming_ws")
class TestLLMStreamingMessageHandling:
    """Test LLM Streaming message handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_handle_message_dispatches_subscribe_stream(self) -> None:
        """
        GIVEN a subscribe_stream message
        WHEN handle_message is called
        THEN it should subscribe to the stream and return confirmation.
        """
        from mcp_server_langgraph.websocket.handlers.llm_streaming import (
            LLMStreamingHandler,
        )

        handler = LLMStreamingHandler(
            config=WebSocketConfig(endpoint_name="llm-streaming")
        )

        message = MessageEnvelope(
            type="subscribe_stream",
            payload={"stream_id": "stream-123"},
            id="msg-1",
        )

        response = await handler.handle_message(message)

        assert response is not None
        # Response should be MessageEnvelope
        assert isinstance(response, MessageEnvelope)
        assert response.type == "subscribed"
        assert response.payload is not None
        assert response.payload.get("stream_id") == "stream-123"

    @pytest.mark.asyncio
    async def test_handle_message_dispatches_unsubscribe_stream(self) -> None:
        """
        GIVEN an unsubscribe_stream message
        WHEN handle_message is called
        THEN it should unsubscribe and return confirmation.
        """
        from mcp_server_langgraph.websocket.handlers.llm_streaming import (
            LLMStreamingHandler,
        )

        handler = LLMStreamingHandler(
            config=WebSocketConfig(endpoint_name="llm-streaming")
        )
        # First subscribe
        handler._subscribed_streams.add("stream-123")

        message = MessageEnvelope(
            type="unsubscribe_stream",
            payload={"stream_id": "stream-123"},
            id="msg-2",
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert isinstance(response, MessageEnvelope)
        assert response.type == "unsubscribed"
        assert "stream-123" not in handler._subscribed_streams

    @pytest.mark.asyncio
    async def test_handle_message_dispatches_cancel_stream(self) -> None:
        """
        GIVEN a cancel_stream message
        WHEN handle_message is called
        THEN it should cancel and return confirmation.
        """
        from mcp_server_langgraph.websocket.handlers.llm_streaming import (
            LLMStreamingHandler,
        )

        handler = LLMStreamingHandler(
            config=WebSocketConfig(endpoint_name="llm-streaming")
        )
        handler._subscribed_streams.add("stream-456")

        message = MessageEnvelope(
            type="cancel_stream",
            payload={"stream_id": "stream-456"},
            id="msg-3",
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert isinstance(response, MessageEnvelope)
        assert response.type == "stream_cancelled"
        assert response.payload is not None
        assert response.payload.get("stream_id") == "stream-456"
        assert "stream-456" not in handler._subscribed_streams

    @pytest.mark.asyncio
    async def test_handle_message_dispatches_ping(self) -> None:
        """
        GIVEN a ping message
        WHEN handle_message is called
        THEN it should return pong response.
        """
        from mcp_server_langgraph.websocket.handlers.llm_streaming import (
            LLMStreamingHandler,
        )

        handler = LLMStreamingHandler(
            config=WebSocketConfig(endpoint_name="llm-streaming")
        )

        message = MessageEnvelope(
            type="ping",
            payload={},
            id="msg-4",
            timestamp="2024-01-01T00:00:00Z",
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert isinstance(response, MessageEnvelope)
        assert response.type == "pong"

    @pytest.mark.asyncio
    async def test_handle_message_returns_error_for_unknown_type(self) -> None:
        """
        GIVEN an unknown message type
        WHEN handle_message is called
        THEN it should return an error response.
        """
        from mcp_server_langgraph.websocket.handlers.llm_streaming import (
            LLMStreamingHandler,
        )

        handler = LLMStreamingHandler(
            config=WebSocketConfig(endpoint_name="llm-streaming")
        )

        message = MessageEnvelope(
            type="unknown_type",
            payload={},
            id="msg-5",
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert isinstance(response, MessageEnvelope)
        assert response.type == "error"
        assert response.payload is not None
        assert "unknown_message_type" in response.payload.get("code", "")


@pytest.mark.xdist_group(name="llm_streaming_ws")
class TestLLMStreamingSubscriptionErrors:
    """Test LLM Streaming subscription error handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_subscribe_without_stream_id_returns_error(self) -> None:
        """
        GIVEN a subscribe_stream message without stream_id
        WHEN handle_message is called
        THEN it should return an error.
        """
        from mcp_server_langgraph.websocket.handlers.llm_streaming import (
            LLMStreamingHandler,
        )

        handler = LLMStreamingHandler(
            config=WebSocketConfig(endpoint_name="llm-streaming")
        )

        message = MessageEnvelope(
            type="subscribe_stream",
            payload={},  # Missing stream_id
            id="msg-err-1",
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert isinstance(response, MessageEnvelope)
        assert response.type == "error"
        assert response.payload is not None
        assert "missing_stream_id" in response.payload.get("code", "")

    @pytest.mark.asyncio
    async def test_cancel_without_stream_id_returns_error(self) -> None:
        """
        GIVEN a cancel_stream message without stream_id
        WHEN handle_message is called
        THEN it should return an error.
        """
        from mcp_server_langgraph.websocket.handlers.llm_streaming import (
            LLMStreamingHandler,
        )

        handler = LLMStreamingHandler(
            config=WebSocketConfig(endpoint_name="llm-streaming")
        )

        message = MessageEnvelope(
            type="cancel_stream",
            payload={},  # Missing stream_id
            id="msg-err-2",
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert isinstance(response, MessageEnvelope)
        assert response.type == "error"
        assert response.payload is not None
        assert "missing_stream_id" in response.payload.get("code", "")
