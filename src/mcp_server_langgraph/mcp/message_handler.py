"""
MCP Message Handler.

Provides the core MCP protocol message handling logic including:
- JSON-RPC 2.0 message routing
- MCP 2025-11-25 method handlers (initialize, tools/*, resources/*, prompts/*)
- Streaming and trace notification creation

This module is the canonical location for MCPMessageHandler and AuthenticatedMCPHandler.
For backward compatibility, these classes are re-exported from api.v1.mcp_websocket.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    pass

# JSON-RPC 2.0 error codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603

logger = logging.getLogger(__name__)


class MCPMessageHandler:
    """
    Handler for MCP protocol messages over WebSocket.

    Supports all MCP 2025-11-25 methods including:
    - initialize: Protocol handshake
    - tools/list, tools/call: Tool operations
    - resources/list, resources/read: Resource operations
    - prompts/list, prompts/get: Prompt operations
    - elicitation/*, sampling/*: Advanced features
    """

    def __init__(self) -> None:
        """Initialize the message handler."""
        self.protocol_version = "2025-11-25"
        self.server_info = {
            "name": "langgraph-agent",
            "version": "2.8.0",
            "description": "AI Agent with fine-grained authorization, LangGraph workflows, and multi-LLM support",
        }
        self.capabilities = {
            "tools": {"listChanged": False},
            "resources": {"listChanged": False, "subscribe": True},
            "prompts": {"listChanged": False},
            "elicitation": {},
            "sampling": {},
            "logging": {},
            "streaming": {
                "supported": True,
                "textStreaming": True,
                "progressiveRendering": True,
                "chunkedResponses": True,
            },
        }

        # Standard tools available
        self._tools = [
            {
                "name": "langgraph-run",
                "description": "Execute the LangGraph agent with a query",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The query to process",
                        },
                        "session_id": {
                            "type": "string",
                            "description": "Optional session ID for context",
                        },
                    },
                    "required": ["query"],
                },
            }
        ]

        # Standard prompts available
        self._prompts = [
            {
                "name": "code_review",
                "description": "Review code for issues and improvements",
                "arguments": [
                    {"name": "code", "required": True, "description": "Code to review"},
                    {"name": "language", "required": False, "description": "Programming language"},
                ],
            },
            {
                "name": "summarize_conversation",
                "description": "Summarize the current conversation",
                "arguments": [],
            },
            {
                "name": "debug_error",
                "description": "Help debug an error",
                "arguments": [
                    {"name": "error", "required": True, "description": "Error message"},
                    {"name": "context", "required": False, "description": "Additional context"},
                ],
            },
        ]

        # Standard resources available
        self._resources = [
            {
                "uri": "config://studio/default",
                "name": "Default Configuration",
                "mimeType": "application/json",
                "description": "Default studio configuration",
            }
        ]

    def handle_sync(self, message: dict[str, Any]) -> dict[str, Any]:
        """
        Handle an MCP message synchronously.

        Used for simple methods that don't require async operations.
        """
        # Validate JSON-RPC 2.0 structure
        if "method" not in message:
            return self._error_response(message.get("id"), INVALID_REQUEST, "Missing method field")

        method = message.get("method")
        message_id = message.get("id")
        params = message.get("params", {})

        # Handle methods
        if method == "initialize":
            return self._handle_initialize(message_id, params)
        else:
            # Unknown method
            return self._error_response(message_id, METHOD_NOT_FOUND, f"Method not found: {method}")

    async def handle(self, message: dict[str, Any]) -> dict[str, Any]:
        """
        Handle an MCP message asynchronously.

        Supports all MCP methods including async operations.
        """
        # Validate JSON-RPC 2.0 structure
        if "method" not in message:
            return self._error_response(message.get("id"), INVALID_REQUEST, "Missing method field")

        method = str(message.get("method"))
        message_id = message.get("id")
        params = message.get("params", {})

        # Route to appropriate handler - sync handlers
        sync_handlers: dict[str, Callable[[Any, Any], dict[str, Any]]] = {
            "initialize": self._handle_initialize,
            "tools/list": self._handle_tools_list,
            "resources/list": self._handle_resources_list,
            "resources/read": self._handle_resources_read,
            "prompts/list": self._handle_prompts_list,
            "prompts/get": self._handle_prompts_get,
        }

        # Async handler for tools/call
        if method == "tools/call":
            return await self._handle_tools_call(message_id, params)

        sync_handler = sync_handlers.get(method)
        if sync_handler:
            return sync_handler(message_id, params)
        else:
            return self._error_response(message_id, METHOD_NOT_FOUND, f"Method not found: {method}")

    def handle_parse_error(self) -> dict[str, Any]:
        """Return a parse error response for invalid JSON."""
        return self._error_response(None, PARSE_ERROR, "Parse error")

    def _error_response(self, message_id: Any, code: int, message: str, data: Any | None = None) -> dict[str, Any]:
        """Create a JSON-RPC 2.0 error response."""
        error: dict[str, Any] = {"code": code, "message": message}
        if data is not None:
            error["data"] = data
        return {"jsonrpc": "2.0", "id": message_id, "error": error}

    def _success_response(self, message_id: Any, result: Any) -> dict[str, Any]:
        """Create a JSON-RPC 2.0 success response."""
        return {"jsonrpc": "2.0", "id": message_id, "result": result}

    def _handle_initialize(self, message_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        """Handle initialize request."""
        return self._success_response(
            message_id,
            {
                "protocolVersion": self.protocol_version,
                "serverInfo": self.server_info,
                "capabilities": self.capabilities,
            },
        )

    def _handle_tools_list(self, message_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        """Handle tools/list request."""
        return self._success_response(message_id, {"tools": self._tools})

    async def _handle_tools_call(self, message_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        """Handle tools/call request."""
        tool_name = params.get("name")
        if not isinstance(tool_name, str):
            return self._error_response(message_id, INVALID_PARAMS, "Missing or invalid tool name")
        arguments = params.get("arguments", {})

        try:
            result = await self.execute_tool(tool_name, arguments)
            return self._success_response(message_id, {"content": result, "isError": False})
        except Exception as e:
            return self._success_response(
                message_id,
                {
                    "content": [{"type": "text", "text": str(e)}],
                    "isError": True,
                },
            )

    async def execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Execute a tool and return results.

        This is a placeholder that should be overridden or mocked in tests.
        In production, this integrates with the actual tool execution system.
        """
        # Default implementation returns a placeholder
        return [{"type": "text", "text": f"Executed {tool_name} with {arguments}"}]

    def _handle_resources_list(self, message_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        """Handle resources/list request."""
        return self._success_response(message_id, {"resources": self._resources})

    def _handle_resources_read(self, message_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        """Handle resources/read request."""
        uri = params.get("uri", "")

        # Return placeholder content
        content = {
            "uri": uri,
            "mimeType": "application/json",
            "text": json.dumps({"config": "placeholder", "uri": uri}),
        }
        return self._success_response(message_id, {"contents": [content]})

    def _handle_prompts_list(self, message_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        """Handle prompts/list request."""
        return self._success_response(message_id, {"prompts": self._prompts})

    def _handle_prompts_get(self, message_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        """Handle prompts/get request."""
        prompt_name = params.get("name")
        arguments = params.get("arguments", {})

        # Generate prompt messages based on name
        if prompt_name == "code_review":
            code = arguments.get("code", "")
            language = arguments.get("language", "unknown")
            messages = [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": f"Please review the following {language} code:\n\n```{language}\n{code}\n```",
                    },
                }
            ]
        elif prompt_name == "summarize_conversation":
            messages = [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": "Please summarize the current conversation, highlighting key points and decisions.",
                    },
                }
            ]
        elif prompt_name == "debug_error":
            error = arguments.get("error", "")
            context = arguments.get("context", "")
            messages = [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": f"Please help debug this error:\n\nError: {error}\n\nContext: {context}",
                    },
                }
            ]
        else:
            return self._error_response(message_id, INVALID_PARAMS, f"Unknown prompt: {prompt_name}")

        return self._success_response(message_id, {"messages": messages})

    # =========================================================================
    # Streaming Extensions ($/streaming/*)
    # =========================================================================

    def create_streaming_start_notification(self, stream_id: str, tool_call_id: int) -> dict[str, Any]:
        """Create a $/streaming/start notification."""
        return {
            "jsonrpc": "2.0",
            "method": "$/streaming/start",
            "params": {
                "streamId": stream_id,
                "toolCallId": tool_call_id,
            },
        }

    def create_streaming_chunk_notification(self, stream_id: str, content: dict[str, Any]) -> dict[str, Any]:
        """Create a $/streaming/chunk notification."""
        return {
            "jsonrpc": "2.0",
            "method": "$/streaming/chunk",
            "params": {
                "streamId": stream_id,
                "content": content,
            },
        }

    def create_streaming_end_notification(self, stream_id: str) -> dict[str, Any]:
        """Create a $/streaming/end notification."""
        return {
            "jsonrpc": "2.0",
            "method": "$/streaming/end",
            "params": {
                "streamId": stream_id,
            },
        }

    # =========================================================================
    # Trace Extensions ($/trace/*)
    # =========================================================================

    def create_trace_span_notification(
        self,
        trace_id: str,
        span_id: str,
        name: str,
        start_time: str,
        end_time: str,
        status: str,
        attributes: dict[str, Any] | None = None,
        parent_span_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a $/trace/span notification with OpenTelemetry-compatible data."""
        return {
            "jsonrpc": "2.0",
            "method": "$/trace/span",
            "params": {
                "traceId": trace_id,
                "spanId": span_id,
                "parentSpanId": parent_span_id,
                "name": name,
                "startTime": start_time,
                "endTime": end_time,
                "status": status,
                "attributes": attributes or {},
            },
        }

    def create_trace_event_notification(
        self,
        span_id: str,
        name: str,
        timestamp: str,
        attributes: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a $/trace/event notification."""
        return {
            "jsonrpc": "2.0",
            "method": "$/trace/event",
            "params": {
                "spanId": span_id,
                "name": name,
                "timestamp": timestamp,
                "attributes": attributes or {},
            },
        }


class AuthenticatedMCPHandler(MCPMessageHandler):
    """
    MCP message handler with user authentication context.

    Extends MCPMessageHandler with:
    - User ID and roles tracking
    - Authenticated tool execution
    - User context propagation to agent
    """

    def __init__(
        self,
        user_id: str,
        roles: list[str] | None = None,
        notification_callback: Callable[[dict[str, Any]], Any] | None = None,
        session_id: str | None = None,
    ) -> None:
        """
        Initialize the authenticated handler.

        Args:
            user_id: The authenticated user's ID.
            roles: The user's roles for authorization.
            notification_callback: Optional async callback for sending notifications.
            session_id: Optional session ID for connection tracking and idle timeout prevention.
        """
        super().__init__()
        self.user_id = user_id
        self.roles = roles or []
        self.notification_callback = notification_callback
        self.session_id = session_id

    async def _handle_tools_call(self, message_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        """
        Handle tools/call request with streaming support.

        Overrides base method to check for _meta.streaming parameter
        and use StreamingToolCallHandler when streaming is requested.
        """
        tool_name = params.get("name")
        if not isinstance(tool_name, str):
            return self._error_response(message_id, INVALID_PARAMS, "Missing or invalid tool name")
        arguments = params.get("arguments", {})

        # Check for streaming request
        meta = params.get("_meta", {})
        is_streaming_requested = meta.get("streaming", False)

        # Use streaming handler if:
        # 1. Streaming is globally enabled
        # 2. Client requested streaming
        # 3. We have a notification callback
        if is_streaming_requested and self.notification_callback is not None:
            # Import here to avoid circular dependency
            try:
                from mcp_server_langgraph.api.v1.mcp_websocket import (
                    StreamingToolCallHandler,
                    streaming_metrics_collector,
                    is_streaming_enabled,
                    get_outbound_rate_limiter,
                    get_streaming_max_chunk_size,
                    get_connection_manager,
                )

                if is_streaming_enabled():
                    # Cast self to Any for StreamingToolCallHandler compatibility
                    # (message_handler.AuthenticatedMCPHandler implements same interface)
                    streaming_handler = StreamingToolCallHandler(
                        mcp_handler=self,  # type: ignore[arg-type]
                        send_notification=self.notification_callback,
                        metrics_collector=streaming_metrics_collector,
                        outbound_rate_limiter=get_outbound_rate_limiter(),
                        max_chunk_size=get_streaming_max_chunk_size(),
                        connection_manager=get_connection_manager(),
                        session_id=self.session_id,
                    )
                    streaming_result = await streaming_handler.handle_streaming_call(
                        message_id=message_id,
                        tool_name=tool_name,
                        arguments=arguments,
                    )
                    return self._success_response(message_id, streaming_result)
            except ImportError:
                logger.debug("Streaming components not available, falling back to non-streaming")

        # Fall back to non-streaming execution
        try:
            tool_result = await self.execute_tool(tool_name, arguments)
            return self._success_response(message_id, {"content": tool_result, "isError": False})
        except Exception as e:
            return self._success_response(
                message_id,
                {
                    "content": [{"type": "text", "text": str(e)}],
                    "isError": True,
                },
            )

    async def execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Execute a tool with user context.

        Overrides the base method to integrate with the real agent and
        propagate user context for authorization.

        Args:
            tool_name: Name of the tool to execute.
            arguments: Tool arguments.

        Returns:
            List of content items from the tool execution.
        """
        session_id = arguments.get("session_id")

        # Execute with the real agent
        return await self._execute_with_agent(
            tool_name=tool_name,
            arguments=arguments,
            user_id=self.user_id,
            session_id=session_id,
        )

    async def _execute_with_agent(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        user_id: str,
        session_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Execute a tool via the LangGraph agent.

        This method integrates with MCPBridge for real tool execution.

        Args:
            tool_name: Name of the tool to execute.
            arguments: Tool arguments.
            user_id: The user's ID for context.
            session_id: Optional session ID for context preservation.

        Returns:
            List of content items from the agent execution.
        """
        logger.info(
            f"Tool execution requested: {tool_name} by user {user_id}",
            extra={"tool_name": tool_name, "user_id": user_id, "session_id": session_id},
        )

        # Try to get MCPBridge for real tool execution
        try:
            from mcp_server_langgraph.api.v1.mcp_bridge import ChatError, get_mcp_bridge

            bridge = get_mcp_bridge()

            if tool_name == "langgraph-run":
                query = arguments.get("query", "")

                # Use MCPBridge if available
                if bridge and bridge.is_configured:
                    try:
                        response = await bridge.send_chat_message(
                            session_id=session_id or "default",
                            message=query,
                            user_id=user_id,
                        )
                        return [
                            {
                                "type": "text",
                                "text": response.content,
                            }
                        ]
                    except ChatError as e:
                        logger.warning(
                            f"MCPBridge execution failed: {e}",
                            extra={"tool_name": tool_name, "user_id": user_id, "error": str(e)},
                        )
                        return [
                            {
                                "type": "text",
                                "text": f"Error executing query: {e}",
                            }
                        ]

                # Fallback when MCPBridge is not available
                logger.debug(
                    "MCPBridge not available, using placeholder response",
                    extra={"tool_name": tool_name, "user_id": user_id},
                )
                return [
                    {
                        "type": "text",
                        "text": f"[Agent] Processing query for user {user_id}: {query}",
                    }
                ]

            # For other tools, use MCPBridge.call_tool if available
            if bridge and bridge.is_configured:
                try:
                    result = await bridge.call_tool(tool_name, arguments)
                    return result.content
                except ChatError as e:
                    logger.warning(
                        f"MCPBridge tool call failed: {e}",
                        extra={"tool_name": tool_name, "user_id": user_id, "error": str(e)},
                    )
                    return [
                        {
                            "type": "text",
                            "text": f"Error executing tool: {e}",
                        }
                    ]
        except ImportError:
            logger.debug("MCPBridge not available, using fallback")

        return [{"type": "text", "text": f"Executed {tool_name} with {arguments}"}]

    async def execute_tool_streaming(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Execute a tool with streaming response.

        Yields streaming chunks that can be sent as $/streaming/chunk notifications.

        Args:
            tool_name: Name of the tool to execute.
            arguments: Tool arguments.

        Yields:
            Content chunks from the streaming execution.
        """
        session_id = arguments.get("session_id")

        try:
            from mcp_server_langgraph.api.v1.mcp_bridge import ChatError, get_mcp_bridge

            bridge = get_mcp_bridge()

            if tool_name == "langgraph-run":
                query = arguments.get("query", "")

                # Use MCPBridge streaming if available
                if bridge and bridge.is_configured:
                    try:
                        async for chunk in bridge.stream_chat_message(
                            session_id=session_id or "default",
                            message=query,
                            user_id=self.user_id,
                        ):
                            yield {
                                "type": "text",
                                "text": chunk.content,
                                "is_final": chunk.is_final,
                            }
                        return
                    except ChatError as e:
                        logger.warning(
                            f"MCPBridge streaming failed: {e}",
                            extra={"tool_name": tool_name, "user_id": self.user_id},
                        )
                        yield {
                            "type": "text",
                            "text": f"Streaming error: {e}",
                            "is_final": True,
                        }
                        return

                # Fallback: yield single chunk
                yield {
                    "type": "text",
                    "text": f"[Agent] Processing query for user {self.user_id}: {query}",
                    "is_final": True,
                }
                return
        except ImportError:
            pass

        # For other tools, yield single result
        yield {
            "type": "text",
            "text": f"Executed {tool_name} with {arguments}",
            "is_final": True,
        }


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Error codes
    "PARSE_ERROR",
    "INVALID_REQUEST",
    "METHOD_NOT_FOUND",
    "INVALID_PARAMS",
    "INTERNAL_ERROR",
    # Handlers
    "MCPMessageHandler",
    "AuthenticatedMCPHandler",
]
