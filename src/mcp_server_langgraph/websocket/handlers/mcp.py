"""
MCP WebSocket Handler.

Provides standardized WebSocket infrastructure for MCP protocol
by extending WebSocketBase and delegating to MCPMessageHandler.

This handler bridges the existing MCP message handling with the
new standardized WebSocket base class infrastructure.
"""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING, Any

from mcp_server_langgraph.websocket.base import WebSocketBase
from mcp_server_langgraph.websocket.types import WebSocketConfig

if TYPE_CHECKING:
    from mcp_server_langgraph.websocket.types import AuthUser

# JSON-RPC 2.0 error codes (local definitions to avoid circular imports)
INVALID_REQUEST = -32600
INTERNAL_ERROR = -32603

logger = logging.getLogger(__name__)


class MCPWebSocketHandler(WebSocketBase):
    """
    WebSocket handler for MCP protocol using standardized infrastructure.

    Extends WebSocketBase to provide:
    - Standardized authentication/authorization flow
    - Server-initiated heartbeat
    - Rate limiting
    - Metrics and tracing
    - Idle timeout management

    Delegates MCP protocol handling to MCPMessageHandler/AuthenticatedMCPHandler.
    """

    def __init__(
        self,
        config: WebSocketConfig | None = None,
        session_id: str | None = None,
    ) -> None:
        """
        Initialize the MCP WebSocket handler.

        Args:
            config: Optional custom WebSocketConfig. If not provided,
                uses default MCP configuration.
            session_id: Optional explicit session ID. If not provided,
                generates a new UUID.
        """
        if config is None:
            config = WebSocketConfig(
                endpoint_name="mcp",
                require_auth=False,
                rate_limit_per_minute=600,  # 10 messages/second
                message_timeout=30,
                heartbeat_interval=30,
                idle_timeout=1800,  # 30 minutes
            )
        super().__init__(config)

        self.session_id = session_id or str(uuid.uuid4())
        self._mcp_handler: Any = None  # MCPMessageHandler or AuthenticatedMCPHandler
        self._user_id: str | None = None
        self._roles: list[str] = []
        self._websocket: Any = None
        self._metrics: Any = None
        self._disconnected = False

    async def on_connect(self, user: AuthUser | None) -> None:
        """
        Handle connection establishment.

        Creates appropriate MCP message handler based on authentication.

        Args:
            user: Authenticated user or None for anonymous connections.
        """
        if user is not None:
            # Authenticated connection
            self._user_id = user.id
            self._roles = getattr(user, "roles", [])

            # Create authenticated handler (lazy import to avoid circular dependency)
            from mcp_server_langgraph.mcp.message_handler import (
                AuthenticatedMCPHandler,
            )

            self._mcp_handler = AuthenticatedMCPHandler(
                user_id=self._user_id,
                roles=self._roles,
                notification_callback=self._send_notification,
                session_id=self.session_id,
            )
            logger.info(
                f"MCP authenticated connection established for {self._user_id}",
                extra={"user_id": self._user_id, "session_id": self.session_id},
            )
        else:
            # Anonymous connection (lazy import to avoid circular dependency)
            from mcp_server_langgraph.mcp.message_handler import MCPMessageHandler

            self._mcp_handler = MCPMessageHandler()
            logger.info(
                "MCP anonymous connection established",
                extra={"session_id": self.session_id},
            )

    async def on_disconnect(self) -> None:
        """
        Handle connection cleanup.

        Clears MCP handler and marks connection as disconnected.
        """
        self._disconnected = True
        self._mcp_handler = None
        logger.info(
            "MCP connection disconnected",
            extra={"user_id": self._user_id, "session_id": self.session_id},
        )

    async def handle_message(  # type: ignore[override]
        self, message: dict[str, Any]
    ) -> dict[str, Any] | None:
        """
        Handle incoming MCP protocol message.

        Routes the message to the internal MCPMessageHandler.
        Note: Intentionally differs from base class signature for MCP protocol.

        Args:
            message: Parsed JSON-RPC 2.0 message.

        Returns:
            JSON-RPC response or None for notifications.
        """
        # Validate JSON-RPC structure
        validation_error = self._validate_jsonrpc(message)
        if validation_error:
            return validation_error

        # If no handler initialized, create base handler
        if self._mcp_handler is None:
            from mcp_server_langgraph.mcp.message_handler import MCPMessageHandler

            self._mcp_handler = MCPMessageHandler()

        # Route to MCP handler
        try:
            response: dict[str, Any] | None = await self._mcp_handler.handle(message)
            return response
        except Exception as e:
            logger.exception(
                f"Error handling MCP message: {e}",
                extra={"session_id": self.session_id, "method": message.get("method")},
            )
            return self._error_response(
                message.get("id"),
                INTERNAL_ERROR,
                f"Internal error: {str(e)}",
            )

    def _validate_jsonrpc(self, message: dict[str, Any]) -> dict[str, Any] | None:
        """
        Validate JSON-RPC 2.0 message structure.

        Args:
            message: The message to validate.

        Returns:
            Error response if invalid, None if valid.
        """
        message_id = message.get("id")

        # Check for jsonrpc version
        if message.get("jsonrpc") != "2.0":
            return self._error_response(
                message_id,
                INVALID_REQUEST,
                "Invalid JSON-RPC version, expected '2.0'",
            )

        # Check for method (except for responses)
        if "method" not in message and "result" not in message and "error" not in message:
            return self._error_response(
                message_id,
                INVALID_REQUEST,
                "Missing 'method' field",
            )

        return None

    def _error_response(
        self,
        message_id: Any,
        code: int,
        message: str,
    ) -> dict[str, Any]:
        """
        Create a JSON-RPC 2.0 error response.

        Args:
            message_id: The request ID.
            code: Error code.
            message: Error message.

        Returns:
            JSON-RPC error response dict.
        """
        return {
            "jsonrpc": "2.0",
            "id": message_id,
            "error": {
                "code": code,
                "message": message,
            },
        }

    async def _send_notification(self, notification: dict[str, Any]) -> None:
        """
        Send a JSON-RPC notification to the client.

        Used for streaming tool calls and other async notifications.

        Args:
            notification: The notification to send.
        """
        if self._websocket is not None:
            await self._websocket.send_json(notification)
