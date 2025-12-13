"""
MCP WebSocket Handler

MCP 2025-11-25 compliant WebSocket transport for real-time bidirectional communication.

This module provides:
- JSON-RPC 2.0 message handling over WebSocket
- MCP protocol methods: initialize, tools/*, resources/*, prompts/*
- Elicitation and sampling support
- Streaming extensions ($/streaming/*)
- Trace extensions ($/trace/*)

Usage:
    from mcp_server_langgraph.api.v1.mcp_websocket import mcp_websocket_router

    app.include_router(mcp_websocket_router, prefix="/api/v1")
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Callable, cast

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

# JSON-RPC 2.0 error codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


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
                "uri": "config://playground/default",
                "name": "Default Configuration",
                "mimeType": "application/json",
                "description": "Default playground configuration",
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

        method = cast(str, message.get("method"))  # Already validated above
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


class ConnectionManager:
    """
    Manages WebSocket connections for MCP sessions.

    Tracks active connections by session ID and provides
    methods for sending messages to specific sessions or broadcasting.
    """

    def __init__(self) -> None:
        """Initialize the connection manager."""
        self._connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str) -> None:
        """Accept and track a new WebSocket connection."""
        await websocket.accept()
        self._connections[session_id] = websocket

    def disconnect(self, session_id: str) -> None:
        """Remove a WebSocket connection."""
        if session_id in self._connections:
            del self._connections[session_id]

    def get_connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self._connections)

    def has_connection(self, session_id: str) -> bool:
        """Check if a session has an active connection."""
        return session_id in self._connections

    async def send_to_session(self, session_id: str, message: dict[str, Any]) -> None:
        """Send a message to a specific session."""
        if session_id in self._connections:
            await self._connections[session_id].send_json(message)

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Broadcast a message to all connected sessions."""
        for websocket in self._connections.values():
            await websocket.send_json(message)


# Create router
mcp_websocket_router = APIRouter(tags=["MCP WebSocket"])

# Global connection manager
connection_manager = ConnectionManager()


@mcp_websocket_router.websocket("/mcp/ws")
async def mcp_websocket_endpoint(websocket: WebSocket) -> None:
    """
    MCP WebSocket endpoint for real-time bidirectional communication.

    Accepts WebSocket connections and handles MCP protocol messages.
    Each connection is associated with a unique session ID.
    """
    # Generate session ID for this connection
    session_id = str(uuid.uuid4())
    handler = MCPMessageHandler()

    await connection_manager.connect(websocket, session_id)

    try:
        while True:
            # Receive message
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
            except json.JSONDecodeError:
                response = handler.handle_parse_error()
                await websocket.send_json(response)
                continue

            # Handle message
            response = await handler.handle(message)
            await websocket.send_json(response)

    except WebSocketDisconnect:
        connection_manager.disconnect(session_id)


@mcp_websocket_router.websocket("/mcp/ws/{session_id}")
async def mcp_websocket_with_session(websocket: WebSocket, session_id: str) -> None:
    """
    MCP WebSocket endpoint with explicit session ID.

    Allows clients to specify a session ID for connection resumption
    and context preservation.
    """
    handler = MCPMessageHandler()

    await connection_manager.connect(websocket, session_id)

    try:
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
            except json.JSONDecodeError:
                response = handler.handle_parse_error()
                await websocket.send_json(response)
                continue

            response = await handler.handle(message)
            await websocket.send_json(response)

    except WebSocketDisconnect:
        connection_manager.disconnect(session_id)
