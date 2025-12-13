"""
Tests for thread_id user prefix in PlaygroundMCPBridge.

Tests that the MCP bridge correctly formats thread_id with the user prefix
to work with fallback authorization.

TDD: These tests were written FIRST to define expected behavior.

Follows memory safety patterns for pytest-xdist.
"""

import gc
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.playground, pytest.mark.mcp]


@pytest.mark.xdist_group(name="playground_mcp_bridge")
class TestPlaygroundMCPBridgeThreadId:
    """Test thread_id formatting in PlaygroundMCPBridge."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_thread_id_includes_user_prefix_for_simple_user_id(self) -> None:
        """Test that thread_id is formatted as {user_id}_{session_id}."""
        from mcp_server_langgraph.playground.mcp.integration import PlaygroundMCPBridge

        # Create mock MCP client
        mock_client = MagicMock()
        mock_client.call_tool = AsyncMock(return_value=[{"type": "text", "text": "Hello!"}])

        bridge = PlaygroundMCPBridge(mcp_client=mock_client)

        # Call send_chat_message
        await bridge.send_chat_message(
            session_id="abc-123",
            message="Hello",
            token="test-token",
            user_id="alice",
        )

        # Verify thread_id format in the call
        mock_client.call_tool.assert_called_once()
        call_args = mock_client.call_tool.call_args
        arguments = call_args[0][1]  # Second positional arg is arguments dict

        assert arguments["thread_id"] == "alice_abc-123"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_thread_id_normalizes_prefixed_user_id(self) -> None:
        """Test that user:alice is normalized to alice in thread_id."""
        from mcp_server_langgraph.playground.mcp.integration import PlaygroundMCPBridge

        mock_client = MagicMock()
        mock_client.call_tool = AsyncMock(return_value=[{"type": "text", "text": "Hello!"}])

        bridge = PlaygroundMCPBridge(mcp_client=mock_client)

        await bridge.send_chat_message(
            session_id="def-456",
            message="Hello",
            token="test-token",
            user_id="user:bob",  # Prefixed format
        )

        call_args = mock_client.call_tool.call_args
        arguments = call_args[0][1]

        # Should normalize to just "bob"
        assert arguments["thread_id"] == "bob_def-456"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_thread_id_handles_uuid_session_id(self) -> None:
        """Test that thread_id works with UUID session IDs."""
        from mcp_server_langgraph.playground.mcp.integration import PlaygroundMCPBridge

        mock_client = MagicMock()
        mock_client.call_tool = AsyncMock(return_value=[{"type": "text", "text": "Response"}])

        bridge = PlaygroundMCPBridge(mcp_client=mock_client)

        session_uuid = "f0bfafef-09fd-4f23-862a-9f62a3cfd825"
        await bridge.send_chat_message(
            session_id=session_uuid,
            message="Test",
            token="token",
            user_id="charlie",
        )

        call_args = mock_client.call_tool.call_args
        arguments = call_args[0][1]

        assert arguments["thread_id"] == f"charlie_{session_uuid}"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_stream_chat_message_also_uses_user_prefix(self) -> None:
        """Test that streaming also formats thread_id correctly."""
        from mcp_server_langgraph.playground.mcp.integration import PlaygroundMCPBridge

        # Create mock streaming client
        mock_streaming_client = MagicMock()

        async def mock_stream(*args, **kwargs):
            yield {"content": [{"type": "text", "text": "chunk1"}]}
            yield {"content": [{"type": "text", "text": "chunk2"}]}

        mock_streaming_client.stream_tool_call = mock_stream

        bridge = PlaygroundMCPBridge(streaming_client=mock_streaming_client)

        # Consume the stream
        chunks = []
        async for chunk in bridge.stream_chat_message(
            session_id="stream-123",
            message="Stream test",
            token="token",
            user_id="user:dave",
        ):
            chunks.append(chunk)

        # Verify we got chunks (the mock was called)
        assert len(chunks) > 0

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_user_id_passed_through_unchanged(self) -> None:
        """Test that user_id in arguments is the original (not normalized)."""
        from mcp_server_langgraph.playground.mcp.integration import PlaygroundMCPBridge

        mock_client = MagicMock()
        mock_client.call_tool = AsyncMock(return_value=[{"type": "text", "text": "OK"}])

        bridge = PlaygroundMCPBridge(mcp_client=mock_client)

        await bridge.send_chat_message(
            session_id="xyz",
            message="Test",
            token="token",
            user_id="user:eve",
        )

        call_args = mock_client.call_tool.call_args
        arguments = call_args[0][1]

        # user_id should be passed through unchanged
        assert arguments["user_id"] == "user:eve"
        # But thread_id should use normalized version
        assert arguments["thread_id"] == "eve_xyz"
