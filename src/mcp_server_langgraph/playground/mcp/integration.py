"""
Playground-MCP integration bridge.

Provides a bridge between the Playground API and MCP protocol:
- Translates chat messages to MCP tool calls
- Handles streaming responses
- Manages session context
- Propagates observability context

Example:
    from mcp_server_langgraph.playground.mcp.integration import PlaygroundMCPBridge

    bridge = PlaygroundMCPBridge(mcp_client=client)
    response = await bridge.send_chat_message(
        session_id="session-123",
        message="Hello",
        token="jwt-token",
        user_id="alice",
    )
"""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from mcp_server_langgraph.observability.telemetry import logger, tracer

from .client import MCPClient, MCPError, MCPPermissionError, MCPStreamingClient


# ==============================================================================
# Exceptions
# ==============================================================================


class ChatError(Exception):
    """Base exception for chat errors."""

    def __init__(self, message: str, cause: Exception | None = None):
        super().__init__(message)
        self.cause = cause


# ==============================================================================
# Response Models
# ==============================================================================


@dataclass
class ChatResponse:
    """Response from a chat message."""

    content: str
    message_id: str | None = None
    usage: dict[str, Any] | None = None
    trace_id: str | None = None


@dataclass
class ChatChunk:
    """A streaming chunk from a chat response."""

    content: str
    is_final: bool = False
    message_id: str | None = None


# ==============================================================================
# MCP Bridge
# ==============================================================================


class PlaygroundMCPBridge:
    """
    Bridge between Playground API and MCP protocol.

    Translates playground chat requests to MCP tool calls,
    handling both synchronous and streaming responses.
    """

    _client: MCPClient | None
    _streaming_client: MCPStreamingClient | None

    def __init__(
        self,
        mcp_client: MCPClient | None = None,
        streaming_client: MCPStreamingClient | None = None,
        mcp_url: str | None = None,
    ) -> None:
        """
        Initialize the bridge.

        Args:
            mcp_client: MCPClient instance for synchronous calls
            streaming_client: MCPStreamingClient for streaming
            mcp_url: MCP server URL (creates clients if not provided)
        """
        if mcp_client:
            self._client = mcp_client
        elif mcp_url:
            self._client = MCPClient(base_url=mcp_url)
        else:
            self._client = None

        if streaming_client:
            self._streaming_client = streaming_client
        elif mcp_url:
            self._streaming_client = MCPStreamingClient(base_url=mcp_url)
        else:
            self._streaming_client = None

    async def send_chat_message(
        self,
        session_id: str,
        message: str,
        token: str,
        user_id: str,
        response_format: str = "detailed",
        trace_id: str | None = None,
    ) -> ChatResponse:
        """
        Send a chat message via MCP agent_chat tool.

        Args:
            session_id: Playground session ID (used as thread_id)
            message: User message
            token: JWT authentication token
            user_id: User identifier
            response_format: Response format ("concise" or "detailed")
            trace_id: Optional trace ID for observability

        Returns:
            ChatResponse with assistant's reply

        Raises:
            ChatError: If the chat fails
        """
        if not self._client:
            raise ChatError("MCP client not configured")

        with tracer.start_as_current_span(
            "playground.chat.send",
            attributes={
                "session.id": session_id,
                "user.id": user_id,
            },
        ) as _span:
            try:
                # Build MCP tool call arguments
                arguments = {
                    "message": message,
                    "token": token,
                    "user_id": user_id,
                    "thread_id": session_id,
                    "response_format": response_format,
                }

                # Call MCP agent_chat tool
                result = await self._client.call_tool("agent_chat", arguments)

                # Extract response content
                content = ""
                for item in result:
                    if item.get("type") == "text":
                        content += item.get("text", "")

                logger.info(
                    "Chat message sent via MCP",
                    extra={
                        "session_id": session_id,
                        "response_length": len(content),
                    },
                )

                return ChatResponse(
                    content=content,
                    trace_id=trace_id,
                )

            except MCPPermissionError as e:
                logger.warning(
                    "Chat permission denied",
                    extra={"session_id": session_id, "error": str(e)},
                )
                raise ChatError(f"Permission denied: {e}", cause=e)

            except MCPError as e:
                logger.error(
                    "Chat failed via MCP",
                    extra={"session_id": session_id, "error": str(e)},
                )
                raise ChatError(f"Chat failed: {e}", cause=e)

            except Exception as e:
                logger.error(
                    "Unexpected error in chat",
                    extra={"session_id": session_id, "error": str(e)},
                    exc_info=True,
                )
                raise ChatError(f"Unexpected error: {e}", cause=e)

    async def stream_chat_message(
        self,
        session_id: str,
        message: str,
        token: str,
        user_id: str,
        response_format: str = "detailed",
        trace_id: str | None = None,
    ) -> AsyncIterator[ChatChunk]:
        """
        Stream a chat message response via MCP.

        Args:
            session_id: Playground session ID
            message: User message
            token: JWT authentication token
            user_id: User identifier
            response_format: Response format
            trace_id: Optional trace ID

        Yields:
            ChatChunk objects as they arrive

        Raises:
            ChatError: If streaming fails
        """
        if not self._streaming_client:
            raise ChatError("MCP streaming client not configured")

        with tracer.start_as_current_span(
            "playground.chat.stream",
            attributes={
                "session.id": session_id,
                "user.id": user_id,
            },
        ):
            try:
                # Build MCP tool call arguments
                arguments = {
                    "message": message,
                    "token": token,
                    "user_id": user_id,
                    "thread_id": session_id,
                    "response_format": response_format,
                }

                # Stream MCP agent_chat tool call
                chunk_count = 0
                async for result in self._streaming_client.stream_tool_call("agent_chat", arguments):
                    chunk_count += 1
                    content_items = result.get("content", [])

                    for item in content_items:
                        if item.get("type") == "text":
                            yield ChatChunk(
                                content=item.get("text", ""),
                                is_final=False,
                            )

                # Yield final chunk marker
                yield ChatChunk(content="", is_final=True)

                logger.info(
                    "Chat stream completed",
                    extra={
                        "session_id": session_id,
                        "chunk_count": chunk_count,
                    },
                )

            except MCPPermissionError as e:
                logger.warning(
                    "Stream permission denied",
                    extra={"session_id": session_id, "error": str(e)},
                )
                raise ChatError(f"Permission denied: {e}", cause=e)

            except MCPError as e:
                logger.error(
                    "Stream failed via MCP",
                    extra={"session_id": session_id, "error": str(e)},
                )
                raise ChatError(f"Stream failed: {e}", cause=e)

            except Exception as e:
                logger.error(
                    "Unexpected error in stream",
                    extra={"session_id": session_id, "error": str(e)},
                    exc_info=True,
                )
                raise ChatError(f"Unexpected error: {e}", cause=e)
