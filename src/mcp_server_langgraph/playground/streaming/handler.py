"""
Playground Streaming Handler

Handles WebSocket message streaming for the Interactive Playground.
Connects to MCP server for agent interactions.
"""

import asyncio
import logging
import re
import uuid
from datetime import datetime, UTC
from typing import Any, AsyncGenerator

from starlette.websockets import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


def _sanitize_log_value(value: str, max_length: int = 256) -> str:
    """
    Sanitize a value for safe logging to prevent log injection attacks.

    Removes newlines, carriage returns, and other control characters that
    could be used for log forging or injection attacks.

    Args:
        value: The value to sanitize
        max_length: Maximum length of the output (truncates if longer)

    Returns:
        Sanitized string safe for logging
    """
    if not isinstance(value, str):
        value = str(value)
    # Remove control characters (including newlines, carriage returns, tabs)
    sanitized = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", value)
    # Truncate to max length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "..."
    return sanitized


class StreamingHandler:
    """
    Handles streaming responses via WebSocket.

    Features:
    - Token-by-token streaming
    - Cancellation support
    - Error handling
    - Heartbeat/ping-pong
    """

    def __init__(
        self,
        websocket: WebSocket,
        session_id: str,
        mcp_server_url: str | None = None,
    ) -> None:
        """
        Initialize streaming handler.

        Args:
            websocket: WebSocket connection
            session_id: Session ID
            mcp_server_url: MCP server URL for agent calls
        """
        self._websocket = websocket
        self._session_id = session_id
        self._mcp_server_url = mcp_server_url or "http://localhost:8000"
        self._cancelled = False
        self._current_message_id: str | None = None

    async def send_message(self, message: dict[str, Any]) -> None:
        """Send a message to the client."""
        try:
            await self._websocket.send_json(message)
        except WebSocketDisconnect:
            logger.warning(
                "WebSocket disconnected while sending",
                extra={"session_id": _sanitize_log_value(self._session_id)},
            )
            raise

    async def send_connection_ack(self) -> None:
        """Send connection acknowledgment."""
        await self.send_message(
            {
                "type": "connected",
                "session_id": self._session_id,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )

    async def send_error(self, error_message: str) -> None:
        """Send error message to client."""
        await self.send_message(
            {
                "type": "error",
                "message": error_message,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )

    async def handle_ping(self) -> None:
        """Handle ping message by sending pong."""
        await self.send_message(
            {
                "type": "pong",
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )

    async def handle_cancel(self) -> None:
        """Handle cancellation request."""
        self._cancelled = True
        await self.send_message(
            {
                "type": "cancelled",
                "message_id": self._current_message_id,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )

    async def stream_response(
        self,
        message: str,
        message_history: list[dict[str, Any]] | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream response tokens for a message.

        This is a placeholder implementation that simulates streaming.
        In production, this would connect to the MCP server.

        Args:
            message: User message
            message_history: Previous messages for context

        Yields:
            Response tokens
        """
        self._cancelled = False
        self._current_message_id = str(uuid.uuid4())

        # Send message start
        await self.send_message(
            {
                "type": "message_start",
                "message_id": self._current_message_id,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )

        # Simulate streaming response
        # In production, this would call the MCP server
        response_parts = [
            "I ",
            "received ",
            "your ",
            "message: ",
            f'"{message[:50]}"',
            ". ",
            "This ",
            "is ",
            "a ",
            "streaming ",
            "response ",
            "from ",
            "the ",
            "playground.",
        ]

        full_response = ""

        for token in response_parts:
            if self._cancelled:
                break

            full_response += token

            await self.send_message(
                {
                    "type": "token",
                    "content": token,
                    "message_id": self._current_message_id,
                    "timestamp": datetime.now(UTC).isoformat(),
                }
            )

            yield token

            # Small delay to simulate streaming
            await asyncio.sleep(0.05)

        # Send message end
        await self.send_message(
            {
                "type": "message_end",
                "message_id": self._current_message_id,
                "full_response": full_response,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )

    async def handle_message(
        self,
        content: str,
        message_history: list[dict[str, Any]] | None = None,
    ) -> str:
        """
        Handle incoming message and stream response.

        Args:
            content: Message content
            message_history: Previous messages

        Returns:
            Full response text
        """
        full_response = ""

        async for token in self.stream_response(content, message_history):
            full_response += token

        return full_response
