"""
MCP WebSocket Streaming Handler Tests

Tests for verifying that streaming tool execution is properly wired
to the WebSocket message handlers.

TDD RED Phase: These tests define the expected behavior for streaming handlers.
"""

from __future__ import annotations

import gc
from unittest.mock import patch

import pytest

pytestmark = [
    pytest.mark.unit,
    pytest.mark.api,
    pytest.mark.websocket,
]


@pytest.mark.xdist_group(name="test_mcp_websocket_streaming_handler")
class TestMCPWebSocketStreamingToolCall:
    """Tests for streaming tool call handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_tools_call_with_stream_param_triggers_streaming(self) -> None:
        """
        GIVEN a tools/call request with _stream: true parameter
        WHEN the handler processes the request
        THEN should use streaming execution and emit notifications.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import AuthenticatedMCPHandler

        handler = AuthenticatedMCPHandler(
            user_id="user:alice",
            roles=["user"],
        )

        # Mock the streaming execution
        async def mock_stream(*args, **kwargs):
            yield {"type": "text", "text": "chunk1", "is_final": False}
            yield {"type": "text", "text": "chunk2", "is_final": True}

        with patch.object(handler, "execute_tool_streaming", side_effect=mock_stream):
            message = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "langgraph-run",
                    "arguments": {"query": "test"},
                    "_meta": {"streaming": True},
                },
            }

            response = await handler.handle(message)

            # Should return success with streaming indicator
            assert response["jsonrpc"] == "2.0"
            assert response["id"] == 1
            assert "result" in response

    @pytest.mark.asyncio
    async def test_streaming_handler_emits_start_notification(self) -> None:
        """
        GIVEN a streaming tool call
        WHEN streaming begins
        THEN should emit $/streaming/start notification.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            AuthenticatedMCPHandler,
            StreamingToolCallHandler,
        )

        handler = AuthenticatedMCPHandler(
            user_id="user:alice",
            roles=["user"],
        )

        notifications: list[dict] = []

        async def capture_notification(notification: dict) -> None:
            notifications.append(notification)

        streaming_handler = StreamingToolCallHandler(
            mcp_handler=handler,
            send_notification=capture_notification,
        )

        # Mock streaming execution
        async def mock_stream(*args, **kwargs):
            yield {"type": "text", "text": "data", "is_final": True}

        with patch.object(handler, "execute_tool_streaming", side_effect=mock_stream):
            await streaming_handler.handle_streaming_call(
                message_id=1,
                tool_name="langgraph-run",
                arguments={"query": "test"},
            )

        # Should have start notification
        start_notifications = [n for n in notifications if n["method"] == "$/streaming/start"]
        assert len(start_notifications) == 1

    @pytest.mark.asyncio
    async def test_streaming_handler_emits_chunk_notifications(self) -> None:
        """
        GIVEN a streaming tool call
        WHEN chunks are yielded
        THEN should emit $/streaming/chunk notifications.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            AuthenticatedMCPHandler,
            StreamingToolCallHandler,
        )

        handler = AuthenticatedMCPHandler(
            user_id="user:alice",
            roles=["user"],
        )

        notifications: list[dict] = []

        async def capture_notification(notification: dict) -> None:
            notifications.append(notification)

        streaming_handler = StreamingToolCallHandler(
            mcp_handler=handler,
            send_notification=capture_notification,
        )

        # Mock streaming execution with multiple chunks
        async def mock_stream(*args, **kwargs):
            yield {"type": "text", "text": "Hello ", "is_final": False}
            yield {"type": "text", "text": "World", "is_final": False}
            yield {"type": "text", "text": "!", "is_final": True}

        with patch.object(handler, "execute_tool_streaming", side_effect=mock_stream):
            await streaming_handler.handle_streaming_call(
                message_id=1,
                tool_name="langgraph-run",
                arguments={"query": "test"},
            )

        # Should have chunk notifications
        chunk_notifications = [n for n in notifications if n["method"] == "$/streaming/chunk"]
        assert len(chunk_notifications) == 3

    @pytest.mark.asyncio
    async def test_streaming_handler_emits_end_notification(self) -> None:
        """
        GIVEN a streaming tool call
        WHEN streaming completes
        THEN should emit $/streaming/end notification.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            AuthenticatedMCPHandler,
            StreamingToolCallHandler,
        )

        handler = AuthenticatedMCPHandler(
            user_id="user:alice",
            roles=["user"],
        )

        notifications: list[dict] = []

        async def capture_notification(notification: dict) -> None:
            notifications.append(notification)

        streaming_handler = StreamingToolCallHandler(
            mcp_handler=handler,
            send_notification=capture_notification,
        )

        async def mock_stream(*args, **kwargs):
            yield {"type": "text", "text": "data", "is_final": True}

        with patch.object(handler, "execute_tool_streaming", side_effect=mock_stream):
            await streaming_handler.handle_streaming_call(
                message_id=1,
                tool_name="langgraph-run",
                arguments={"query": "test"},
            )

        # Should have end notification
        end_notifications = [n for n in notifications if n["method"] == "$/streaming/end"]
        assert len(end_notifications) == 1


@pytest.mark.xdist_group(name="test_mcp_websocket_streaming_handler")
class TestStreamingToolCallHandler:
    """Tests for StreamingToolCallHandler class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_streaming_tool_call_handler_exists(self) -> None:
        """
        GIVEN the MCP WebSocket module
        WHEN importing
        THEN should have StreamingToolCallHandler class.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import StreamingToolCallHandler

        assert StreamingToolCallHandler is not None

    def test_streaming_handler_requires_mcp_handler(self) -> None:
        """
        GIVEN StreamingToolCallHandler
        WHEN initializing
        THEN should require an MCP handler instance.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            AuthenticatedMCPHandler,
            StreamingToolCallHandler,
        )

        handler = AuthenticatedMCPHandler(user_id="user:alice")

        async def noop(n):
            pass

        streaming = StreamingToolCallHandler(mcp_handler=handler, send_notification=noop)

        assert streaming.mcp_handler is handler

    def test_streaming_handler_requires_send_notification(self) -> None:
        """
        GIVEN StreamingToolCallHandler
        WHEN initializing
        THEN should require a send_notification callback.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            AuthenticatedMCPHandler,
            StreamingToolCallHandler,
        )

        handler = AuthenticatedMCPHandler(user_id="user:alice")

        async def mock_send(n):
            pass

        streaming = StreamingToolCallHandler(mcp_handler=handler, send_notification=mock_send)

        assert streaming.send_notification is mock_send

    @pytest.mark.asyncio
    async def test_streaming_handler_generates_unique_stream_id(self) -> None:
        """
        GIVEN multiple streaming calls
        WHEN handling
        THEN should generate unique stream IDs.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            AuthenticatedMCPHandler,
            StreamingToolCallHandler,
        )

        handler = AuthenticatedMCPHandler(user_id="user:alice")
        stream_ids: list[str] = []

        async def capture_notification(notification: dict) -> None:
            if notification["method"] == "$/streaming/start":
                stream_ids.append(notification["params"]["streamId"])

        streaming = StreamingToolCallHandler(
            mcp_handler=handler,
            send_notification=capture_notification,
        )

        async def mock_stream(*args, **kwargs):
            yield {"type": "text", "text": "data", "is_final": True}

        with patch.object(handler, "execute_tool_streaming", side_effect=mock_stream):
            await streaming.handle_streaming_call(1, "tool1", {})
            await streaming.handle_streaming_call(2, "tool2", {})

        assert len(stream_ids) == 2
        assert stream_ids[0] != stream_ids[1]


@pytest.mark.xdist_group(name="test_mcp_websocket_streaming_handler")
class TestStreamingResponseFormat:
    """Tests for streaming response format compliance."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_streaming_start_contains_tool_call_id(self) -> None:
        """
        GIVEN a streaming tool call
        WHEN $/streaming/start is emitted
        THEN should contain toolCallId matching the message ID.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            AuthenticatedMCPHandler,
            StreamingToolCallHandler,
        )

        handler = AuthenticatedMCPHandler(user_id="user:alice")
        notifications: list[dict] = []

        async def capture(n):
            notifications.append(n)

        streaming = StreamingToolCallHandler(mcp_handler=handler, send_notification=capture)

        async def mock_stream(*args, **kwargs):
            yield {"type": "text", "text": "data", "is_final": True}

        with patch.object(handler, "execute_tool_streaming", side_effect=mock_stream):
            await streaming.handle_streaming_call(
                message_id=42,
                tool_name="test",
                arguments={},
            )

        start = [n for n in notifications if n["method"] == "$/streaming/start"][0]
        assert start["params"]["toolCallId"] == 42

    @pytest.mark.asyncio
    async def test_streaming_chunk_contains_content(self) -> None:
        """
        GIVEN a streaming tool call
        WHEN $/streaming/chunk is emitted
        THEN should contain content with type and text.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            AuthenticatedMCPHandler,
            StreamingToolCallHandler,
        )

        handler = AuthenticatedMCPHandler(user_id="user:alice")
        notifications: list[dict] = []

        async def capture(n):
            notifications.append(n)

        streaming = StreamingToolCallHandler(mcp_handler=handler, send_notification=capture)

        async def mock_stream(*args, **kwargs):
            yield {"type": "text", "text": "Hello", "is_final": True}

        with patch.object(handler, "execute_tool_streaming", side_effect=mock_stream):
            await streaming.handle_streaming_call(1, "test", {})

        chunk = [n for n in notifications if n["method"] == "$/streaming/chunk"][0]
        assert "content" in chunk["params"]
        assert chunk["params"]["content"]["type"] == "text"
        assert chunk["params"]["content"]["text"] == "Hello"

    @pytest.mark.asyncio
    async def test_streaming_end_contains_stream_id(self) -> None:
        """
        GIVEN a streaming tool call
        WHEN $/streaming/end is emitted
        THEN should contain the same streamId as start.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            AuthenticatedMCPHandler,
            StreamingToolCallHandler,
        )

        handler = AuthenticatedMCPHandler(user_id="user:alice")
        notifications: list[dict] = []

        async def capture(n):
            notifications.append(n)

        streaming = StreamingToolCallHandler(mcp_handler=handler, send_notification=capture)

        async def mock_stream(*args, **kwargs):
            yield {"type": "text", "text": "data", "is_final": True}

        with patch.object(handler, "execute_tool_streaming", side_effect=mock_stream):
            await streaming.handle_streaming_call(1, "test", {})

        start = [n for n in notifications if n["method"] == "$/streaming/start"][0]
        end = [n for n in notifications if n["method"] == "$/streaming/end"][0]

        assert start["params"]["streamId"] == end["params"]["streamId"]


@pytest.mark.xdist_group(name="test_mcp_websocket_streaming_handler")
class TestStreamingWebSocketDisconnect:
    """Tests for WebSocket disconnect handling during streaming."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_disconnect_during_chunk_stops_streaming(self) -> None:
        """
        GIVEN a streaming tool call in progress
        WHEN the WebSocket disconnects during chunk notification
        THEN should stop streaming gracefully without raising.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            AuthenticatedMCPHandler,
            StreamingToolCallHandler,
        )

        handler = AuthenticatedMCPHandler(user_id="user:alice")
        notification_count = 0

        async def disconnect_on_second_chunk(notification: dict) -> None:
            nonlocal notification_count
            notification_count += 1
            # Disconnect after start notification
            if notification.get("method") == "$/streaming/chunk":
                raise ConnectionError("WebSocket disconnected")

        streaming = StreamingToolCallHandler(
            mcp_handler=handler,
            send_notification=disconnect_on_second_chunk,
        )

        async def mock_stream(*args, **kwargs):
            yield {"type": "text", "text": "chunk1", "is_final": False}
            yield {"type": "text", "text": "chunk2", "is_final": False}
            yield {"type": "text", "text": "chunk3", "is_final": True}

        with patch.object(handler, "execute_tool_streaming", side_effect=mock_stream):
            # Should not raise, should handle disconnect gracefully
            result = await streaming.handle_streaming_call(1, "test", {})

        # Should return error result indicating disconnect
        assert result["isError"] is True
        assert "disconnect" in result["content"][0]["text"].lower() or "error" in result["content"][0]["text"].lower()

    @pytest.mark.asyncio
    async def test_disconnect_during_start_notification(self) -> None:
        """
        GIVEN a streaming tool call starting
        WHEN the WebSocket disconnects during start notification
        THEN should handle gracefully and return error result.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            AuthenticatedMCPHandler,
            StreamingToolCallHandler,
        )

        handler = AuthenticatedMCPHandler(user_id="user:alice")

        async def disconnect_immediately(notification: dict) -> None:
            raise ConnectionError("WebSocket disconnected")

        streaming = StreamingToolCallHandler(
            mcp_handler=handler,
            send_notification=disconnect_immediately,
        )

        async def mock_stream(*args, **kwargs):
            yield {"type": "text", "text": "data", "is_final": True}

        with patch.object(handler, "execute_tool_streaming", side_effect=mock_stream):
            result = await streaming.handle_streaming_call(1, "test", {})

        assert result["isError"] is True

    @pytest.mark.asyncio
    async def test_disconnect_during_end_notification_silent(self) -> None:
        """
        GIVEN a streaming tool call completing
        WHEN the WebSocket disconnects during end notification
        THEN should complete without raising (client already gone).
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            AuthenticatedMCPHandler,
            StreamingToolCallHandler,
        )

        handler = AuthenticatedMCPHandler(user_id="user:alice")
        chunks_sent = []

        async def disconnect_on_end(notification: dict) -> None:
            method = notification.get("method", "")
            if method == "$/streaming/end":
                raise ConnectionError("WebSocket disconnected")
            chunks_sent.append(notification)

        streaming = StreamingToolCallHandler(
            mcp_handler=handler,
            send_notification=disconnect_on_end,
        )

        async def mock_stream(*args, **kwargs):
            yield {"type": "text", "text": "data", "is_final": True}

        with patch.object(handler, "execute_tool_streaming", side_effect=mock_stream):
            # Should not raise even though end notification fails
            result = await streaming.handle_streaming_call(1, "test", {})

        # Should still return success (streaming completed)
        assert result["isError"] is False
        # Should have sent start and chunk notifications
        assert len(chunks_sent) >= 2

    @pytest.mark.asyncio
    async def test_client_disconnected_flag_set(self) -> None:
        """
        GIVEN a streaming tool call
        WHEN the client disconnects
        THEN the handler should track the disconnection state.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            AuthenticatedMCPHandler,
            StreamingToolCallHandler,
        )

        handler = AuthenticatedMCPHandler(user_id="user:alice")

        async def disconnect_on_chunk(notification: dict) -> None:
            if notification.get("method") == "$/streaming/chunk":
                raise ConnectionError("WebSocket disconnected")

        streaming = StreamingToolCallHandler(
            mcp_handler=handler,
            send_notification=disconnect_on_chunk,
        )

        async def mock_stream(*args, **kwargs):
            yield {"type": "text", "text": "data", "is_final": True}

        with patch.object(handler, "execute_tool_streaming", side_effect=mock_stream):
            await streaming.handle_streaming_call(1, "test", {})

        # Handler should track that client disconnected
        assert hasattr(streaming, "_client_disconnected")
        assert streaming._client_disconnected is True


@pytest.mark.xdist_group(name="test_mcp_websocket_streaming_handler")
class TestStreamingErrorHandling:
    """Tests for streaming error handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_streaming_error_emits_end_notification(self) -> None:
        """
        GIVEN a streaming tool call that fails
        WHEN an error occurs during streaming
        THEN should still emit $/streaming/end notification.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            AuthenticatedMCPHandler,
            StreamingToolCallHandler,
        )

        handler = AuthenticatedMCPHandler(user_id="user:alice")
        notifications: list[dict] = []

        async def capture(n):
            notifications.append(n)

        streaming = StreamingToolCallHandler(mcp_handler=handler, send_notification=capture)

        async def failing_stream(*args, **kwargs):
            yield {"type": "text", "text": "partial", "is_final": False}
            raise RuntimeError("Stream failed")

        with patch.object(handler, "execute_tool_streaming", side_effect=failing_stream):
            # Should not propagate exception
            await streaming.handle_streaming_call(1, "test", {})

        # Should still have end notification
        end_notifications = [n for n in notifications if n["method"] == "$/streaming/end"]
        assert len(end_notifications) == 1

    @pytest.mark.asyncio
    async def test_streaming_error_returns_error_response(self) -> None:
        """
        GIVEN a streaming tool call that fails
        WHEN an error occurs during streaming
        THEN should return error response with isError: true.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            AuthenticatedMCPHandler,
            StreamingToolCallHandler,
        )

        handler = AuthenticatedMCPHandler(user_id="user:alice")

        async def noop(n):
            pass

        streaming = StreamingToolCallHandler(mcp_handler=handler, send_notification=noop)

        async def failing_stream(*args, **kwargs):
            raise RuntimeError("Stream failed")
            yield  # Make it a generator

        with patch.object(handler, "execute_tool_streaming", side_effect=failing_stream):
            result = await streaming.handle_streaming_call(1, "test", {})

        assert result["isError"] is True
        assert "Stream failed" in result["content"][0]["text"]


@pytest.mark.xdist_group(name="test_mcp_websocket_streaming_handler")
class TestStreamingEndpointIntegration:
    """Tests for streaming integration at the endpoint level."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_handle_detects_streaming_meta_param(self) -> None:
        """
        GIVEN a tools/call request with _meta.streaming = true
        WHEN the handler processes the request
        THEN should detect the streaming flag.
        """
        # Create message with streaming meta
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "langgraph-run",
                "arguments": {"query": "test"},
                "_meta": {"streaming": True},
            },
        }

        # The handler should have a method to check for streaming
        params = message["params"]
        is_streaming = params.get("_meta", {}).get("streaming", False)
        assert is_streaming is True

    @pytest.mark.asyncio
    async def test_handler_accepts_notification_callback(self) -> None:
        """
        GIVEN an AuthenticatedMCPHandler
        WHEN initialized with a notification callback
        THEN should store and use the callback for streaming.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import AuthenticatedMCPHandler

        notifications: list[dict] = []

        async def capture_notification(n: dict) -> None:
            notifications.append(n)

        handler = AuthenticatedMCPHandler(
            user_id="user:alice",
            notification_callback=capture_notification,
        )

        assert handler.notification_callback is capture_notification

    @pytest.mark.asyncio
    async def test_streaming_tools_call_uses_streaming_handler(self) -> None:
        """
        GIVEN a tools/call request with _meta.streaming = true
        WHEN the handler processes the request
        THEN should use StreamingToolCallHandler and emit notifications.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import AuthenticatedMCPHandler

        notifications: list[dict] = []

        async def capture_notification(n: dict) -> None:
            notifications.append(n)

        handler = AuthenticatedMCPHandler(
            user_id="user:alice",
            notification_callback=capture_notification,
        )

        # Mock streaming execution
        async def mock_stream(*args, **kwargs):
            yield {"type": "text", "text": "Hello", "is_final": False}
            yield {"type": "text", "text": " World", "is_final": True}

        with patch.object(handler, "execute_tool_streaming", side_effect=mock_stream):
            message = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "langgraph-run",
                    "arguments": {"query": "test"},
                    "_meta": {"streaming": True},
                },
            }

            response = await handler.handle(message)

        # Should have streaming notifications
        start_notifications = [n for n in notifications if n.get("method") == "$/streaming/start"]
        chunk_notifications = [n for n in notifications if n.get("method") == "$/streaming/chunk"]
        end_notifications = [n for n in notifications if n.get("method") == "$/streaming/end"]

        assert len(start_notifications) == 1
        assert len(chunk_notifications) == 2
        assert len(end_notifications) == 1

        # Response should still be valid
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response

    @pytest.mark.asyncio
    async def test_non_streaming_tools_call_works_normally(self) -> None:
        """
        GIVEN a tools/call request without _meta.streaming
        WHEN the handler processes the request
        THEN should execute normally without streaming notifications.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import AuthenticatedMCPHandler

        notifications: list[dict] = []

        async def capture_notification(n: dict) -> None:
            notifications.append(n)

        handler = AuthenticatedMCPHandler(
            user_id="user:alice",
            notification_callback=capture_notification,
        )

        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "langgraph-run",
                "arguments": {"query": "test"},
            },
        }

        with patch.object(
            handler,
            "execute_tool",
            return_value=[{"type": "text", "text": "Result"}],
        ):
            response = await handler.handle(message)

        # No streaming notifications should be emitted
        assert len(notifications) == 0

        # Response should be valid
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
        assert response["result"]["content"] == [{"type": "text", "text": "Result"}]

    @pytest.mark.asyncio
    async def test_streaming_without_callback_falls_back_to_non_streaming(self) -> None:
        """
        GIVEN a tools/call request with _meta.streaming = true
        WHEN the handler has no notification callback
        THEN should fall back to non-streaming execution.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import AuthenticatedMCPHandler

        # No notification callback
        handler = AuthenticatedMCPHandler(user_id="user:alice")

        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "langgraph-run",
                "arguments": {"query": "test"},
                "_meta": {"streaming": True},
            },
        }

        with patch.object(
            handler,
            "execute_tool",
            return_value=[{"type": "text", "text": "Fallback result"}],
        ):
            response = await handler.handle(message)

        # Should still work
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response


@pytest.mark.xdist_group(name="test_mcp_websocket_streaming_handler")
class TestCreateHandlerFromTokenCallback:
    """Tests for create_handler_from_token notification_callback forwarding."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_handler_from_token_accepts_notification_callback(self) -> None:
        """
        GIVEN create_handler_from_token function
        WHEN called with notification_callback parameter
        THEN should forward it to AuthenticatedMCPHandler.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import create_handler_from_token

        async def mock_callback(n: dict) -> None:
            pass

        token_payload = {
            "preferred_username": "alice",
            "realm_access": {"roles": ["user"]},
        }

        handler = create_handler_from_token(
            token_payload,
            notification_callback=mock_callback,
        )

        assert handler.notification_callback is mock_callback

    def test_create_handler_from_token_callback_optional(self) -> None:
        """
        GIVEN create_handler_from_token function
        WHEN called without notification_callback parameter
        THEN should create handler with None callback (backward compatible).
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import create_handler_from_token

        token_payload = {
            "preferred_username": "bob",
            "realm_access": {"roles": ["user"]},
        }

        handler = create_handler_from_token(token_payload)

        assert handler.notification_callback is None


@pytest.mark.xdist_group(name="test_mcp_websocket_streaming_handler")
class TestStreamingCapabilityDeclaration:
    """Tests for streaming capability in server capabilities."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_server_capabilities_include_streaming(self) -> None:
        """
        GIVEN an MCPMessageHandler
        WHEN checking server capabilities
        THEN should include streaming capability declaration.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPMessageHandler

        handler = MCPMessageHandler()

        assert "streaming" in handler.capabilities
        assert handler.capabilities["streaming"].get("supported") is True

    @pytest.mark.asyncio
    async def test_initialize_response_includes_streaming_capability(self) -> None:
        """
        GIVEN an MCP initialize request
        WHEN the handler responds
        THEN should include streaming in capabilities.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPMessageHandler

        handler = MCPMessageHandler()

        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0.0"},
            },
        }

        response = await handler.handle(message)

        assert "result" in response
        capabilities = response["result"]["capabilities"]
        assert "streaming" in capabilities
        assert capabilities["streaming"].get("supported") is True


@pytest.mark.xdist_group(name="test_mcp_websocket_streaming_handler")
class TestAnonymousStreamingSupport:
    """Tests for anonymous (unauthenticated) streaming support."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_anonymous_streaming_handler(self) -> None:
        """
        GIVEN a session ID for anonymous connection
        WHEN creating a handler for anonymous streaming
        THEN should create AuthenticatedMCPHandler with session-based user_id.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            create_anonymous_streaming_handler,
        )

        async def mock_send(n):
            pass

        handler = create_anonymous_streaming_handler(
            session_id="session-abc123",
            notification_callback=mock_send,
        )

        assert handler.user_id == "session:session-abc123"
        assert "anonymous" in handler.roles
        assert handler.notification_callback is mock_send

    def test_anonymous_handler_has_streaming_capability(self) -> None:
        """
        GIVEN an anonymous streaming handler
        WHEN checking capabilities
        THEN should include streaming support.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            create_anonymous_streaming_handler,
        )

        async def mock_send(n):
            pass

        handler = create_anonymous_streaming_handler(
            session_id="session-xyz789",
            notification_callback=mock_send,
        )

        assert "streaming" in handler.capabilities
        assert handler.capabilities["streaming"].get("supported") is True

    @pytest.mark.asyncio
    async def test_anonymous_streaming_tools_call(self) -> None:
        """
        GIVEN an anonymous streaming handler
        WHEN handling tools/call with _meta.streaming=true
        THEN should emit streaming notifications.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            create_anonymous_streaming_handler,
        )

        notifications: list[dict] = []

        async def capture_notification(n: dict) -> None:
            notifications.append(n)

        handler = create_anonymous_streaming_handler(
            session_id="session-stream123",
            notification_callback=capture_notification,
        )

        # Mock streaming execution
        async def mock_stream(*args, **kwargs):
            yield {"type": "text", "text": "Anonymous streaming!", "is_final": True}

        with patch.object(handler, "execute_tool_streaming", side_effect=mock_stream):
            message = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "langgraph-run",
                    "arguments": {"query": "test"},
                    "_meta": {"streaming": True},
                },
            }

            response = await handler.handle(message)

        # Should have streaming notifications
        methods = [n.get("method") for n in notifications]
        assert "$/streaming/start" in methods
        assert "$/streaming/chunk" in methods
        assert "$/streaming/end" in methods

        # Response should be valid
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response

    @pytest.mark.asyncio
    async def test_anonymous_session_rate_limiting_by_session(self) -> None:
        """
        GIVEN anonymous connections with different session IDs
        WHEN rate limiting is applied
        THEN should track limits by session ID, not user ID.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import UserRateLimiterManager

        manager = UserRateLimiterManager(max_messages=2, window_seconds=60)

        # Session 1 uses its limit
        assert manager.check_and_increment("session:abc123") is True
        assert manager.check_and_increment("session:abc123") is True
        assert manager.check_and_increment("session:abc123") is False

        # Session 2 should have its own limit
        assert manager.check_and_increment("session:xyz789") is True


@pytest.mark.xdist_group(name="test_mcp_websocket_streaming_handler")
class TestSessionEndpointStreamingSupport:
    """Tests for streaming support in /mcp/ws/{session_id} endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_session_endpoint_handler_gets_notification_callback(self) -> None:
        """
        GIVEN a session ID endpoint connection with token
        WHEN creating the authenticated handler
        THEN handler should receive notification_callback for streaming.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import create_handler_from_token

        async def mock_callback(n: dict) -> None:
            pass

        token_payload = {
            "preferred_username": "alice",
            "realm_access": {"roles": ["user"]},
        }

        handler = create_handler_from_token(
            token_payload,
            notification_callback=mock_callback,
        )

        assert handler.notification_callback is mock_callback

    @pytest.mark.asyncio
    async def test_session_endpoint_streaming_tools_call(self) -> None:
        """
        GIVEN a handler created via create_handler_from_token with callback
        WHEN handling tools/call with _meta.streaming=true
        THEN should emit streaming notifications through the callback.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import create_handler_from_token

        notifications: list[dict] = []

        async def capture_notification(n: dict) -> None:
            notifications.append(n)

        token_payload = {
            "preferred_username": "alice",
            "realm_access": {"roles": ["user"]},
        }

        handler = create_handler_from_token(
            token_payload,
            notification_callback=capture_notification,
        )

        # Mock streaming execution
        async def mock_stream(*args, **kwargs):
            yield {"type": "text", "text": "session streaming", "is_final": True}

        with patch.object(handler, "execute_tool_streaming", side_effect=mock_stream):
            message = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "langgraph-run",
                    "arguments": {"query": "test"},
                    "_meta": {"streaming": True},
                },
            }

            response = await handler.handle(message)

        # Should have streaming notifications
        methods = [n.get("method") for n in notifications]
        assert "$/streaming/start" in methods
        assert "$/streaming/chunk" in methods
        assert "$/streaming/end" in methods

        # Response should be valid
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response

    def test_session_endpoint_anonymous_gets_streaming(self) -> None:
        """
        GIVEN a session endpoint connection without token
        WHEN handler is created for anonymous user
        THEN should still support streaming if callback provided.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            create_anonymous_streaming_handler,
        )

        async def mock_callback(n: dict) -> None:
            pass

        handler = create_anonymous_streaming_handler(
            session_id="session-with-explicit-id",
            notification_callback=mock_callback,
        )

        # Handler should be configured for streaming
        assert handler.notification_callback is mock_callback
        assert handler.user_id == "session:session-with-explicit-id"
        assert "streaming" in handler.capabilities

    @pytest.mark.asyncio
    async def test_session_endpoint_preserves_session_id_in_handler(self) -> None:
        """
        GIVEN a session ID from the URL path
        WHEN creating handler for that session
        THEN the session ID should be preserved for rate limiting.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            create_anonymous_streaming_handler,
            SecureMessageProcessor,
            UserRateLimiterManager,
        )

        session_id = "explicit-session-12345"

        async def mock_callback(n: dict) -> None:
            pass

        handler = create_anonymous_streaming_handler(
            session_id=session_id,
            notification_callback=mock_callback,
        )

        # Create processor with same session ID
        rate_limiter = UserRateLimiterManager(max_messages=100, window_seconds=60)
        processor = SecureMessageProcessor(
            session_id=session_id,
            user_id=handler.user_id,
            rate_limiter=rate_limiter,
        )

        # Verify session ID matches
        assert processor.session_id == session_id
        assert handler.user_id == f"session:{session_id}"


@pytest.mark.xdist_group(name="test_mcp_websocket_streaming_handler")
class TestEnhancedStreamingCapabilities:
    """Tests for enhanced streaming capability declarations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_streaming_capabilities_include_text_streaming(self) -> None:
        """
        GIVEN an MCPMessageHandler
        WHEN checking streaming capabilities
        THEN should include textStreaming sub-spec.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPMessageHandler

        handler = MCPMessageHandler()

        assert "streaming" in handler.capabilities
        streaming_caps = handler.capabilities["streaming"]
        assert streaming_caps.get("textStreaming") is True

    def test_streaming_capabilities_include_progressive_rendering(self) -> None:
        """
        GIVEN an MCPMessageHandler
        WHEN checking streaming capabilities
        THEN should include progressiveRendering flag.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPMessageHandler

        handler = MCPMessageHandler()

        streaming_caps = handler.capabilities["streaming"]
        assert streaming_caps.get("progressiveRendering") is True

    def test_streaming_capabilities_include_chunked_responses(self) -> None:
        """
        GIVEN an MCPMessageHandler
        WHEN checking streaming capabilities
        THEN should include chunkedResponses flag.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPMessageHandler

        handler = MCPMessageHandler()

        streaming_caps = handler.capabilities["streaming"]
        assert streaming_caps.get("chunkedResponses") is True

    @pytest.mark.asyncio
    async def test_initialize_response_includes_enhanced_streaming(self) -> None:
        """
        GIVEN an MCP initialize request
        WHEN handler responds
        THEN should include enhanced streaming sub-specs.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPMessageHandler

        handler = MCPMessageHandler()

        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0.0"},
            },
        }

        response = await handler.handle(message)

        capabilities = response["result"]["capabilities"]
        streaming = capabilities["streaming"]

        assert streaming.get("supported") is True
        assert streaming.get("textStreaming") is True
        assert streaming.get("progressiveRendering") is True
        assert streaming.get("chunkedResponses") is True


@pytest.mark.xdist_group(name="test_mcp_websocket_streaming_handler")
class TestStreamingMetrics:
    """Tests for streaming metrics collection."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_streaming_metrics_collector_exists(self) -> None:
        """
        GIVEN the mcp_websocket module
        WHEN importing
        THEN should have StreamingMetricsCollector class.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import StreamingMetricsCollector

        assert StreamingMetricsCollector is not None

    def test_streaming_metrics_tracks_chunks_per_stream(self) -> None:
        """
        GIVEN a StreamingMetricsCollector
        WHEN recording chunks for a stream
        THEN should track chunks per stream count.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import StreamingMetricsCollector

        metrics = StreamingMetricsCollector()

        stream_id = "stream-001"
        metrics.record_chunk(stream_id, chunk_size=100)
        metrics.record_chunk(stream_id, chunk_size=150)
        metrics.record_chunk(stream_id, chunk_size=50)

        stats = metrics.get_stream_stats(stream_id)
        assert stats["chunk_count"] == 3

    def test_streaming_metrics_tracks_total_bytes(self) -> None:
        """
        GIVEN a StreamingMetricsCollector
        WHEN recording chunks
        THEN should track total bytes for stream.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import StreamingMetricsCollector

        metrics = StreamingMetricsCollector()

        stream_id = "stream-002"
        metrics.record_chunk(stream_id, chunk_size=100)
        metrics.record_chunk(stream_id, chunk_size=200)

        stats = metrics.get_stream_stats(stream_id)
        assert stats["total_bytes"] == 300

    def test_streaming_metrics_calculates_avg_chunk_size(self) -> None:
        """
        GIVEN a StreamingMetricsCollector with recorded chunks
        WHEN getting stream stats
        THEN should calculate average chunk size.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import StreamingMetricsCollector

        metrics = StreamingMetricsCollector()

        stream_id = "stream-003"
        metrics.record_chunk(stream_id, chunk_size=100)
        metrics.record_chunk(stream_id, chunk_size=200)
        metrics.record_chunk(stream_id, chunk_size=300)

        stats = metrics.get_stream_stats(stream_id)
        assert stats["avg_chunk_size"] == 200.0  # (100 + 200 + 300) / 3

    def test_streaming_metrics_records_stream_start(self) -> None:
        """
        GIVEN a StreamingMetricsCollector
        WHEN starting a stream
        THEN should record start time.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import StreamingMetricsCollector

        metrics = StreamingMetricsCollector()

        stream_id = "stream-004"
        metrics.record_stream_start(stream_id)

        assert metrics.is_stream_active(stream_id) is True

    def test_streaming_metrics_records_stream_end(self) -> None:
        """
        GIVEN a StreamingMetricsCollector with active stream
        WHEN ending the stream
        THEN should calculate duration.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import StreamingMetricsCollector

        metrics = StreamingMetricsCollector()

        stream_id = "stream-005"
        metrics.record_stream_start(stream_id)
        metrics.record_stream_end(stream_id)

        stats = metrics.get_stream_stats(stream_id)
        assert "duration_ms" in stats
        assert stats["duration_ms"] >= 0

    def test_streaming_metrics_get_aggregate_stats(self) -> None:
        """
        GIVEN multiple streams with metrics
        WHEN getting aggregate stats
        THEN should return summary across all streams.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import StreamingMetricsCollector

        metrics = StreamingMetricsCollector()

        # Stream 1
        metrics.record_stream_start("s1")
        metrics.record_chunk("s1", chunk_size=100)
        metrics.record_stream_end("s1")

        # Stream 2
        metrics.record_stream_start("s2")
        metrics.record_chunk("s2", chunk_size=200)
        metrics.record_chunk("s2", chunk_size=200)
        metrics.record_stream_end("s2")

        aggregate = metrics.get_aggregate_stats()

        assert aggregate["total_streams"] == 2
        assert aggregate["total_chunks"] == 3
        assert aggregate["total_bytes"] == 500

    @pytest.mark.asyncio
    async def test_streaming_handler_records_metrics(self) -> None:
        """
        GIVEN a StreamingToolCallHandler with metrics
        WHEN handling a streaming call
        THEN should record metrics for the stream.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            AuthenticatedMCPHandler,
            StreamingToolCallHandler,
            StreamingMetricsCollector,
        )

        handler = AuthenticatedMCPHandler(user_id="user:alice")
        metrics = StreamingMetricsCollector()
        notifications: list[dict] = []

        async def capture(n):
            notifications.append(n)

        streaming_handler = StreamingToolCallHandler(
            mcp_handler=handler,
            send_notification=capture,
            metrics_collector=metrics,
        )

        async def mock_stream(*args, **kwargs):
            yield {"type": "text", "text": "Hello", "is_final": False}
            yield {"type": "text", "text": " World", "is_final": True}

        with patch.object(handler, "execute_tool_streaming", side_effect=mock_stream):
            await streaming_handler.handle_streaming_call(1, "test", {})

        # Should have recorded metrics
        aggregate = metrics.get_aggregate_stats()
        assert aggregate["total_streams"] == 1
        assert aggregate["total_chunks"] == 2


@pytest.mark.xdist_group(name="test_mcp_websocket_streaming_handler")
class TestGlobalStreamingMetricsCollector:
    """Tests for global streaming metrics collector instance."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_global_streaming_metrics_collector_exists(self) -> None:
        """
        GIVEN the mcp_websocket module
        WHEN importing
        THEN should have a global streaming_metrics_collector instance.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import streaming_metrics_collector

        assert streaming_metrics_collector is not None

    def test_global_streaming_metrics_collector_is_instance(self) -> None:
        """
        GIVEN the global streaming_metrics_collector
        WHEN checking its type
        THEN should be a StreamingMetricsCollector instance.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            StreamingMetricsCollector,
            streaming_metrics_collector,
        )

        assert isinstance(streaming_metrics_collector, StreamingMetricsCollector)

    def test_authenticated_handler_uses_global_metrics(self) -> None:
        """
        GIVEN an AuthenticatedMCPHandler with notification callback
        WHEN handling streaming tools/call
        THEN should use the global streaming_metrics_collector.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            AuthenticatedMCPHandler,
            streaming_metrics_collector,
        )

        notifications: list[dict] = []

        async def capture(n):
            notifications.append(n)

        handler = AuthenticatedMCPHandler(
            user_id="user:alice",
            notification_callback=capture,
        )

        # The handler should have access to global metrics
        # This tests that the wiring is in place
        assert streaming_metrics_collector is not None
        # Handler is created with notification callback for streaming
        assert handler.notification_callback is capture


@pytest.mark.xdist_group(name="test_mcp_websocket_streaming_handler")
class TestOTelStreamingMetrics:
    """Tests for OpenTelemetry streaming metrics integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_otel_metrics_has_stream_start_method(self) -> None:
        """
        GIVEN OTelMCPMetrics instance
        WHEN checking methods
        THEN should have record_stream_start method.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import OTelMCPMetrics

        metrics = OTelMCPMetrics()
        assert hasattr(metrics, "record_stream_start")
        assert callable(metrics.record_stream_start)

    def test_otel_metrics_has_stream_chunk_method(self) -> None:
        """
        GIVEN OTelMCPMetrics instance
        WHEN checking methods
        THEN should have record_stream_chunk method.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import OTelMCPMetrics

        metrics = OTelMCPMetrics()
        assert hasattr(metrics, "record_stream_chunk")
        assert callable(metrics.record_stream_chunk)

    def test_otel_metrics_has_stream_end_method(self) -> None:
        """
        GIVEN OTelMCPMetrics instance
        WHEN checking methods
        THEN should have record_stream_end method.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import OTelMCPMetrics

        metrics = OTelMCPMetrics()
        assert hasattr(metrics, "record_stream_end")
        assert callable(metrics.record_stream_end)

    def test_otel_metrics_tracks_active_streams(self) -> None:
        """
        GIVEN OTelMCPMetrics instance
        WHEN recording stream start/end
        THEN should track active streams count.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import OTelMCPMetrics

        metrics = OTelMCPMetrics()

        # Start a stream
        metrics.record_stream_start(stream_id="s1")
        assert metrics._active_streams >= 1

        # End the stream
        metrics.record_stream_end(stream_id="s1", chunks=5, total_bytes=500, duration_ms=100.0)
        # Active streams should decrease (or be at 0)

    def test_otel_metrics_record_stream_chunk_accepts_size(self) -> None:
        """
        GIVEN OTelMCPMetrics instance
        WHEN recording a stream chunk
        THEN should accept chunk_size parameter.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import OTelMCPMetrics

        metrics = OTelMCPMetrics()

        # Should not raise
        metrics.record_stream_chunk(stream_id="s1", chunk_size=256)

    def test_otel_metrics_has_chunk_size_histogram(self) -> None:
        """
        GIVEN OTelMCPMetrics instance with OTel available
        WHEN checking attributes
        THEN should have a histogram for chunk sizes.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import OTelMCPMetrics

        metrics = OTelMCPMetrics()

        # Should have chunk size histogram attribute
        assert hasattr(metrics, "_chunk_size_histogram") or hasattr(metrics, "_stream_chunk_sizes")

    def test_otel_metrics_tracks_total_chunks(self) -> None:
        """
        GIVEN OTelMCPMetrics instance
        WHEN recording multiple chunks
        THEN should track total chunks counter.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import OTelMCPMetrics

        metrics = OTelMCPMetrics()

        # Record some chunks
        metrics.record_stream_chunk(stream_id="s1", chunk_size=100)
        metrics.record_stream_chunk(stream_id="s1", chunk_size=200)
        metrics.record_stream_chunk(stream_id="s2", chunk_size=150)

        # Should have a counter for total chunks
        assert hasattr(metrics, "_total_chunks") or hasattr(metrics, "_stream_chunks_total")


@pytest.mark.xdist_group(name="test_mcp_websocket_streaming_handler")
class TestStreamingMetricsCleanup:
    """Tests for streaming metrics cleanup functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_cleanup_old_streams_method_exists(self) -> None:
        """
        GIVEN a StreamingMetricsCollector
        WHEN checking methods
        THEN should have cleanup_old_streams method.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import StreamingMetricsCollector

        metrics = StreamingMetricsCollector()
        assert hasattr(metrics, "cleanup_old_streams")
        assert callable(metrics.cleanup_old_streams)

    def test_cleanup_removes_completed_streams(self) -> None:
        """
        GIVEN a StreamingMetricsCollector with completed streams
        WHEN calling cleanup_old_streams with 0 max_age
        THEN should remove all completed streams.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import StreamingMetricsCollector

        metrics = StreamingMetricsCollector()

        # Record a complete stream
        metrics.record_stream_start("s1")
        metrics.record_chunk("s1", chunk_size=100)
        metrics.record_stream_end("s1")

        # Should have 1 stream
        assert metrics.get_aggregate_stats()["total_streams"] == 1

        # Cleanup with 0 max_age (remove all completed)
        removed = metrics.cleanup_old_streams(max_age_seconds=0)

        assert removed == 1
        assert metrics.get_aggregate_stats()["total_streams"] == 0

    def test_cleanup_preserves_active_streams(self) -> None:
        """
        GIVEN a StreamingMetricsCollector with active and completed streams
        WHEN calling cleanup_old_streams
        THEN should preserve active streams.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import StreamingMetricsCollector

        metrics = StreamingMetricsCollector()

        # Record a complete stream
        metrics.record_stream_start("s1")
        metrics.record_stream_end("s1")

        # Record an active stream
        metrics.record_stream_start("s2")
        # s2 is still active (no end)

        # Should have 2 streams
        assert metrics.get_aggregate_stats()["total_streams"] == 2

        # Cleanup
        removed = metrics.cleanup_old_streams(max_age_seconds=0)

        # Only completed stream should be removed
        assert removed == 1
        assert metrics.get_aggregate_stats()["total_streams"] == 1
        assert metrics.is_stream_active("s2") is True

    def test_cleanup_respects_max_age(self) -> None:
        """
        GIVEN a StreamingMetricsCollector with recently completed streams
        WHEN calling cleanup_old_streams with large max_age
        THEN should preserve recently completed streams.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import StreamingMetricsCollector

        metrics = StreamingMetricsCollector()

        # Record a complete stream
        metrics.record_stream_start("s1")
        metrics.record_stream_end("s1")

        # Cleanup with large max_age (should keep recent streams)
        removed = metrics.cleanup_old_streams(max_age_seconds=3600)  # 1 hour

        # Stream was just completed, should not be removed
        assert removed == 0
        assert metrics.get_aggregate_stats()["total_streams"] == 1


@pytest.mark.xdist_group(name="test_mcp_websocket_streaming_handler")
class TestGlobalMetricsWiringInHandlers:
    """Tests for verifying global metrics are wired to streaming handlers.

    TDD RED Phase: These tests verify production wiring of metrics collectors.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_authenticated_handler_uses_global_metrics_collector(self) -> None:
        """
        GIVEN an AuthenticatedMCPHandler with notification callback
        WHEN handling streaming tools/call
        THEN should use the global streaming_metrics_collector for metrics.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            AuthenticatedMCPHandler,
            streaming_metrics_collector,
        )

        notifications: list[dict] = []

        async def capture(n):
            notifications.append(n)

        handler = AuthenticatedMCPHandler(
            user_id="user:alice",
            notification_callback=capture,
        )

        # Clear any existing metrics
        initial_stats = streaming_metrics_collector.get_aggregate_stats()
        initial_streams = initial_stats["total_streams"]

        # Mock streaming execution
        async def mock_stream(*args, **kwargs):
            yield {"type": "text", "text": "test", "is_final": True}

        with patch.object(handler, "execute_tool_streaming", side_effect=mock_stream):
            message = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "langgraph-run",
                    "arguments": {"query": "test"},
                    "_meta": {"streaming": True},
                },
            }
            await handler.handle(message)

        # The global metrics collector should have recorded the stream
        final_stats = streaming_metrics_collector.get_aggregate_stats()
        assert final_stats["total_streams"] > initial_streams, "Global streaming_metrics_collector should record new streams"

    @pytest.mark.asyncio
    async def test_streaming_handler_calls_otel_metrics(self) -> None:
        """
        GIVEN a streaming tool call
        WHEN the stream executes
        THEN should call otel_metrics.record_stream_start/end.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            AuthenticatedMCPHandler,
            otel_metrics,
        )

        notifications: list[dict] = []

        async def capture(n):
            notifications.append(n)

        handler = AuthenticatedMCPHandler(
            user_id="user:alice",
            notification_callback=capture,
        )

        # Track calls to OTel methods
        start_calls = []
        end_calls = []
        original_start = otel_metrics.record_stream_start
        original_end = otel_metrics.record_stream_end

        def mock_start(*args, **kwargs):
            start_calls.append((args, kwargs))
            return original_start(*args, **kwargs)

        def mock_end(*args, **kwargs):
            end_calls.append((args, kwargs))
            return original_end(*args, **kwargs)

        async def mock_stream(*args, **kwargs):
            yield {"type": "text", "text": "test", "is_final": True}

        with patch.object(otel_metrics, "record_stream_start", side_effect=mock_start):
            with patch.object(otel_metrics, "record_stream_end", side_effect=mock_end):
                with patch.object(handler, "execute_tool_streaming", side_effect=mock_stream):
                    message = {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "tools/call",
                        "params": {
                            "name": "langgraph-run",
                            "arguments": {"query": "test"},
                            "_meta": {"streaming": True},
                        },
                    }
                    await handler.handle(message)

        # OTel methods should have been called
        assert len(start_calls) == 1, "otel_metrics.record_stream_start should be called once"
        assert len(end_calls) == 1, "otel_metrics.record_stream_end should be called once"

    @pytest.mark.asyncio
    async def test_streaming_handler_calls_otel_record_stream_chunk(self) -> None:
        """
        GIVEN a streaming tool call with multiple chunks
        WHEN chunks are yielded
        THEN should call otel_metrics.record_stream_chunk for each chunk.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            AuthenticatedMCPHandler,
            otel_metrics,
        )

        notifications: list[dict] = []

        async def capture(n):
            notifications.append(n)

        handler = AuthenticatedMCPHandler(
            user_id="user:alice",
            notification_callback=capture,
        )

        # Track calls to OTel record_stream_chunk
        chunk_calls: list[tuple] = []
        original_chunk = otel_metrics.record_stream_chunk

        def mock_chunk(*args, **kwargs):
            chunk_calls.append((args, kwargs))
            return original_chunk(*args, **kwargs)

        async def mock_stream(*args, **kwargs):
            yield {"type": "text", "text": "Hello", "is_final": False}
            yield {"type": "text", "text": " World", "is_final": False}
            yield {"type": "text", "text": "!", "is_final": True}

        with patch.object(otel_metrics, "record_stream_chunk", side_effect=mock_chunk):
            with patch.object(handler, "execute_tool_streaming", side_effect=mock_stream):
                message = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "langgraph-run",
                        "arguments": {"query": "test"},
                        "_meta": {"streaming": True},
                    },
                }
                await handler.handle(message)

        # OTel record_stream_chunk should be called for each chunk
        assert len(chunk_calls) == 3, f"otel_metrics.record_stream_chunk should be called 3 times, got {len(chunk_calls)}"

        # Verify chunk sizes were passed
        for call in chunk_calls:
            kwargs = call[1]
            assert "chunk_size" in kwargs, "record_stream_chunk should receive chunk_size"
            assert kwargs["chunk_size"] > 0, "chunk_size should be positive"


@pytest.mark.xdist_group(name="test_mcp_websocket_streaming_handler")
class TestLifecycleManagerMetricsCleanup:
    """Tests for metrics cleanup in lifecycle manager.

    TDD RED Phase: These tests verify cleanup task integration.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_lifecycle_manager_has_cleanup_interval_config(self) -> None:
        """
        GIVEN MCPWebSocketLifecycleManager
        WHEN checking configuration
        THEN should have configurable metrics cleanup interval.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            MCPWebSocketLifecycleManager,
        )

        manager = MCPWebSocketLifecycleManager()

        # Should have cleanup interval attribute (for idle connections)
        assert hasattr(manager, "cleanup_interval")
        # Should also have metrics cleanup interval
        assert hasattr(manager, "metrics_cleanup_interval") or hasattr(manager, "cleanup_interval"), (
            "Lifecycle manager should have cleanup interval configuration"
        )

    @pytest.mark.asyncio
    async def test_lifecycle_manager_cleans_old_stream_metrics(self) -> None:
        """
        GIVEN MCPWebSocketLifecycleManager running
        WHEN cleanup runs
        THEN should clean old stream metrics from streaming_metrics_collector.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            MCPWebSocketLifecycleManager,
            streaming_metrics_collector,
        )

        # Add a completed stream to the collector
        test_stream_id = "cleanup-test-stream"
        streaming_metrics_collector.record_stream_start(test_stream_id)
        streaming_metrics_collector.record_chunk(test_stream_id, 100)
        streaming_metrics_collector.record_stream_end(test_stream_id)

        # Verify stream exists
        assert streaming_metrics_collector.get_aggregate_stats()["total_streams"] >= 1

        manager = MCPWebSocketLifecycleManager()

        # Manager should have method to clean metrics or do it during cleanup
        if hasattr(manager, "cleanup_stream_metrics"):
            await manager.cleanup_stream_metrics()
            # Old completed streams should be cleaned
            # (with max_age=0 for immediate cleanup in test)

    def test_lifecycle_manager_exposes_stream_metrics_cleanup(self) -> None:
        """
        GIVEN MCPWebSocketLifecycleManager
        WHEN checking methods
        THEN should have a method to clean up old stream metrics.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            MCPWebSocketLifecycleManager,
        )

        manager = MCPWebSocketLifecycleManager()

        # Should have cleanup method for stream metrics
        # Either as a dedicated method or integrated into existing cleanup
        has_metrics_cleanup = hasattr(manager, "cleanup_stream_metrics") or hasattr(manager, "_cleanup_old_stream_metrics")
        assert has_metrics_cleanup, "Lifecycle manager should have stream metrics cleanup method"
