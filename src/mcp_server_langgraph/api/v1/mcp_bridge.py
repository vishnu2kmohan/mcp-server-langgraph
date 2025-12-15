"""
MCP Bridge for Unified API.

Implements the MCP Protocol Specification 2025-11-25 for full protocol compliance.

Features implemented:
- Streamable HTTP Transport with SSE support
- Session management (MCP-Session-Id header)
- Protocol version negotiation (MCP-Protocol-Version header)
- Tools (tools/list, tools/call with structured output)
- Resources (resources/list, resources/read, resources/subscribe)
- Sampling (sampling/createMessage for server-initiated LLM)
- Elicitation (elicitation/create for user input requests)
- Tasks (experimental - durable state machines for long-running ops)
- Progress notifications
- Error handling with proper JSON-RPC error codes

Provides a bridge between the unified API and MCP protocol:
- Translates chat messages to MCP tool calls
- Handles streaming responses via SSE
- Manages session context via thread_id
- Propagates observability context

Specification: https://modelcontextprotocol.io/specification/2025-11-25

Example:
    from mcp_server_langgraph.api.v1.mcp_bridge import MCPBridge

    bridge = MCPBridge(mcp_url="http://localhost:8001")
    response = await bridge.send_chat_message(
        session_id="session-123",
        message="Hello",
        user_id="alice",
    )
"""

from __future__ import annotations

import json
import secrets
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Literal

import httpx

from mcp_server_langgraph.observability.telemetry import logger, tracer


# ==============================================================================
# Constants - MCP Protocol 2025-11-25
# ==============================================================================

MCP_PROTOCOL_VERSION = "2025-11-25"
MCP_ENDPOINT = "/mcp"  # Default endpoint for Streamable HTTP transport


# ==============================================================================
# Exceptions - JSON-RPC Error Codes from MCP Spec
# ==============================================================================


class MCPError(Exception):
    """Base exception for MCP client errors."""

    def __init__(self, message: str, code: int = -32603, data: Any = None):
        super().__init__(message)
        self.code = code
        self.data = data


class MCPConnectionError(MCPError):
    """Raised when connection to MCP server fails."""

    def __init__(self, message: str):
        super().__init__(message, code=-32000)


class MCPPermissionError(MCPError):
    """Raised when MCP server returns permission denied (code: -32001)."""

    def __init__(self, message: str):
        super().__init__(message, code=-32001)


class MCPResourceNotFoundError(MCPError):
    """Raised when a resource is not found (code: -32002)."""

    def __init__(self, message: str, uri: str | None = None):
        super().__init__(message, code=-32002, data={"uri": uri} if uri else None)


class MCPElicitationRequiredError(MCPError):
    """Raised when elicitation is required before proceeding (code: -32042)."""

    def __init__(self, message: str, elicitations: list[dict[str, Any]] | None = None):
        super().__init__(message, code=-32042, data={"elicitations": elicitations})
        self.elicitations = elicitations or []


class MCPInvalidParamsError(MCPError):
    """Raised for invalid parameters (code: -32602)."""

    def __init__(self, message: str):
        super().__init__(message, code=-32602)


class MCPTaskNotFoundError(MCPError):
    """Raised when a task is not found or expired."""

    def __init__(self, message: str, task_id: str | None = None):
        super().__init__(message, code=-32602, data={"taskId": task_id} if task_id else None)


class ChatError(Exception):
    """Base exception for chat errors."""

    def __init__(self, message: str, cause: Exception | None = None):
        super().__init__(message)
        self.cause = cause


# ==============================================================================
# Enums - MCP Protocol Types
# ==============================================================================


class TaskStatus(str, Enum):
    """Task status per MCP 2025-11-25 spec."""

    WORKING = "working"
    INPUT_REQUIRED = "input_required"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ContentType(str, Enum):
    """Content types supported by MCP."""

    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    RESOURCE = "resource"
    RESOURCE_LINK = "resource_link"
    TOOL_USE = "tool_use"
    TOOL_RESULT = "tool_result"


class ToolChoiceMode(str, Enum):
    """Tool choice modes for sampling."""

    AUTO = "auto"
    REQUIRED = "required"
    NONE = "none"


class ElicitationMode(str, Enum):
    """Elicitation modes."""

    FORM = "form"
    URL = "url"


class ElicitationAction(str, Enum):
    """Elicitation response actions."""

    ACCEPT = "accept"
    DECLINE = "decline"
    CANCEL = "cancel"


# ==============================================================================
# Response Models - Core Types
# ==============================================================================


@dataclass
class ChatResponse:
    """Response from a chat message."""

    content: str
    message_id: str | None = None
    usage: dict[str, Any] | None = None
    trace_id: str | None = None
    model: str | None = None
    stop_reason: str | None = None
    tool_calls: list[dict[str, Any]] | None = None


@dataclass
class ChatChunk:
    """A streaming chunk from a chat response."""

    content: str
    is_final: bool = False
    message_id: str | None = None
    tool_call: dict[str, Any] | None = None
    delta_type: str = "text"  # text, tool_use


@dataclass
class MCPToolResult:
    """Result from an MCP tool call."""

    content: list[dict[str, Any]] = field(default_factory=list)
    is_error: bool = False
    structured_content: dict[str, Any] | None = None


# ==============================================================================
# Response Models - Resources
# ==============================================================================


@dataclass
class MCPResource:
    """An MCP resource per 2025-11-25 spec."""

    uri: str
    name: str
    title: str | None = None
    description: str | None = None
    mime_type: str | None = None
    annotations: dict[str, Any] | None = None


@dataclass
class MCPResourceContent:
    """Content of an MCP resource."""

    uri: str
    mime_type: str | None = None
    text: str | None = None
    blob: str | None = None  # Base64 encoded


@dataclass
class MCPResourceTemplate:
    """An MCP resource template (RFC 6570 URI template)."""

    uri_template: str
    name: str
    title: str | None = None
    description: str | None = None
    mime_type: str | None = None


# ==============================================================================
# Response Models - Tools
# ==============================================================================


@dataclass
class MCPTool:
    """An MCP tool per 2025-11-25 spec."""

    name: str
    description: str
    input_schema: dict[str, Any]
    title: str | None = None
    output_schema: dict[str, Any] | None = None
    annotations: dict[str, Any] | None = None


# ==============================================================================
# Response Models - Sampling
# ==============================================================================


@dataclass
class SamplingMessage:
    """A message for sampling/createMessage."""

    role: Literal["user", "assistant"]
    content: dict[str, Any] | list[dict[str, Any]]


@dataclass
class SamplingRequest:
    """Request for sampling/createMessage per MCP 2025-11-25."""

    messages: list[SamplingMessage]
    system_prompt: str | None = None
    max_tokens: int = 1000
    model_preferences: dict[str, Any] | None = None
    tools: list[dict[str, Any]] | None = None
    tool_choice: dict[str, Any] | None = None


@dataclass
class SamplingResponse:
    """Response from sampling/createMessage."""

    role: str
    content: dict[str, Any]
    model: str | None = None
    stop_reason: str | None = None


# ==============================================================================
# Response Models - Tasks
# ==============================================================================


@dataclass
class MCPTask:
    """An MCP task per 2025-11-25 spec (experimental)."""

    task_id: str
    status: TaskStatus
    created_at: datetime
    last_updated_at: datetime
    ttl: int | None = None  # milliseconds
    poll_interval: int | None = None  # milliseconds
    status_message: str | None = None


# ==============================================================================
# Response Models - Elicitation
# ==============================================================================


@dataclass
class ElicitationRequest:
    """Request for elicitation/create."""

    message: str
    mode: ElicitationMode = ElicitationMode.FORM
    requested_schema: dict[str, Any] | None = None
    url: str | None = None
    elicitation_id: str | None = None


@dataclass
class ElicitationResponse:
    """Response from elicitation/create."""

    action: ElicitationAction
    content: dict[str, Any] | None = None


# ==============================================================================
# MCP Client - Full 2025-11-25 Protocol Implementation
# ==============================================================================


class MCPClient:
    """
    MCP StreamableHTTP client implementing the 2025-11-25 protocol specification.

    Features:
    - Streamable HTTP transport with SSE support
    - Session management (MCP-Session-Id header)
    - Protocol version negotiation (MCP-Protocol-Version header)
    - Tools (tools/list, tools/call)
    - Resources (resources/list, resources/read, resources/subscribe)
    - Sampling (sampling/createMessage)
    - Elicitation (elicitation/create)
    - Tasks (experimental - durable state machines)
    - Progress notifications
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 60.0,
        endpoint: str = MCP_ENDPOINT,
    ) -> None:
        """
        Initialize MCP client.

        Args:
            base_url: Base URL of MCP server (e.g., "http://localhost:8001")
            timeout: Request timeout in seconds
            endpoint: MCP endpoint path (default: /mcp)
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.endpoint = endpoint
        self._request_id = 0
        self._session_id: str | None = None
        self._last_event_id: str | None = None
        self._capabilities: dict[str, Any] = {}
        self._server_capabilities: dict[str, Any] = {}

    @property
    def session_id(self) -> str | None:
        """Get the current session ID."""
        return self._session_id

    @property
    def is_initialized(self) -> bool:
        """Check if the client has been initialized with the server."""
        return self._session_id is not None

    def _next_request_id(self) -> int:
        """Generate next JSON-RPC request ID."""
        self._request_id += 1
        return self._request_id

    def _build_headers(self, accept_sse: bool = False) -> dict[str, str]:
        """Build HTTP headers per MCP 2025-11-25 spec."""
        headers = {
            "MCP-Protocol-Version": MCP_PROTOCOL_VERSION,
            "Content-Type": "application/json",
        }

        if accept_sse:
            headers["Accept"] = "application/json, text/event-stream"
        else:
            headers["Accept"] = "application/json"

        if self._session_id:
            headers["MCP-Session-Id"] = self._session_id

        if self._last_event_id:
            headers["Last-Event-ID"] = self._last_event_id

        return headers

    def _build_jsonrpc_request(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        meta: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build a JSON-RPC 2.0 request message."""
        request: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": self._next_request_id(),
            "method": method,
        }
        if params is not None:
            # Add _meta if provided (for task association)
            if meta:
                params = {**params, "_meta": meta}
            request["params"] = params
        return request

    def _handle_error_response(self, response: dict[str, Any]) -> None:
        """Handle JSON-RPC error response per MCP 2025-11-25 error codes."""
        error = response.get("error", {})
        code = error.get("code", -32603)
        message = error.get("message", "Unknown error")
        data = error.get("data")

        if code == -32001:  # Permission denied
            raise MCPPermissionError(message)
        elif code == -32002:  # Resource not found
            uri = data.get("uri") if data else None
            raise MCPResourceNotFoundError(message, uri=uri)
        elif code == -32042:  # Elicitation required
            elicitations = data.get("elicitations", []) if data else []
            raise MCPElicitationRequiredError(message, elicitations=elicitations)
        elif code == -32602:  # Invalid params (also used for task not found)
            if data and "taskId" in data:
                raise MCPTaskNotFoundError(message, task_id=data.get("taskId"))
            raise MCPInvalidParamsError(message)
        else:
            raise MCPError(f"MCP error {code}: {message}", code=code, data=data)

    # =========================================================================
    # Lifecycle Methods
    # =========================================================================

    async def initialize(
        self,
        client_info: dict[str, Any] | None = None,
        capabilities: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Initialize connection with MCP server.

        Args:
            client_info: Client name and version
            capabilities: Client capabilities to declare

        Returns:
            Server capabilities and info
        """
        params: dict[str, Any] = {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "clientInfo": client_info
            or {
                "name": "mcp-server-langgraph",
                "version": "1.0.0",
            },
            "capabilities": capabilities
            or {
                "sampling": {"tools": {}},
                "elicitation": {"form": {}, "url": {}},
                "roots": {},
            },
        }

        request = self._build_jsonrpc_request("initialize", params)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}{self.endpoint}",
                    json=request,
                    headers=self._build_headers(),
                )

                # Extract session ID from response header
                session_id = response.headers.get("MCP-Session-Id")
                if session_id:
                    self._session_id = session_id

                data = response.json()
                if "error" in data:
                    self._handle_error_response(data)

                result: dict[str, Any] = data.get("result", {})
                self._server_capabilities = result.get("capabilities", {})

                # Send initialized notification
                await self._send_notification("notifications/initialized")

                logger.info(
                    "MCP client initialized",
                    extra={
                        "session_id": self._session_id,
                        "server_capabilities": list(self._server_capabilities.keys()),
                    },
                )

                return result

        except httpx.ConnectError as e:
            raise MCPConnectionError(f"Failed to connect to MCP server: {e}")
        except MCPError:
            raise
        except Exception as e:
            raise MCPError(f"Initialization failed: {e}")

    async def _send_notification(self, method: str, params: dict[str, Any] | None = None) -> None:
        """Send a notification (no response expected)."""
        notification: dict[str, Any] = {
            "jsonrpc": "2.0",
            "method": method,
        }
        if params:
            notification["params"] = params

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                await client.post(
                    f"{self.base_url}{self.endpoint}",
                    json=notification,
                    headers=self._build_headers(),
                )
        except Exception as e:
            logger.warning(f"Failed to send notification {method}: {e}")

    async def terminate_session(self) -> None:
        """Terminate the current session per MCP spec."""
        if not self._session_id:
            return

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                await client.delete(
                    f"{self.base_url}{self.endpoint}",
                    headers=self._build_headers(),
                )
            self._session_id = None
            logger.info("MCP session terminated")
        except Exception as e:
            logger.warning(f"Failed to terminate session: {e}")

    # =========================================================================
    # Tools Methods
    # =========================================================================

    async def list_tools(self, cursor: str | None = None) -> tuple[list[MCPTool], str | None]:
        """
        List available tools from the server.

        Args:
            cursor: Pagination cursor

        Returns:
            Tuple of (tools, next_cursor)
        """
        params: dict[str, Any] = {}
        if cursor:
            params["cursor"] = cursor

        request = self._build_jsonrpc_request("tools/list", params if params else None)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}{self.endpoint}",
                    json=request,
                    headers=self._build_headers(),
                )
                data = response.json()

                if "error" in data:
                    self._handle_error_response(data)

                result = data.get("result", {})
                tools_data = result.get("tools", [])
                next_cursor = result.get("nextCursor")

                tools = [
                    MCPTool(
                        name=t["name"],
                        description=t.get("description", ""),
                        input_schema=t.get("inputSchema", {}),
                        title=t.get("title"),
                        output_schema=t.get("outputSchema"),
                        annotations=t.get("annotations"),
                    )
                    for t in tools_data
                ]

                return tools, next_cursor

        except httpx.ConnectError as e:
            raise MCPConnectionError(f"Failed to connect to MCP server: {e}")
        except MCPError:
            raise
        except Exception as e:
            raise MCPError(f"Failed to list tools: {e}")

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        task_ttl: int | None = None,
    ) -> MCPToolResult:
        """
        Call an MCP tool.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
            task_ttl: Optional TTL in ms to create as task

        Returns:
            MCPToolResult with content and optional structured output

        Raises:
            MCPError: If the tool call fails
        """
        params: dict[str, Any] = {
            "name": tool_name,
            "arguments": arguments,
        }

        # Add task augmentation if requested
        if task_ttl is not None:
            params["task"] = {"ttl": task_ttl}

        request = self._build_jsonrpc_request("tools/call", params)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}{self.endpoint}",
                    json=request,
                    headers=self._build_headers(accept_sse=True),
                )

                # Handle SSE response
                content_type = response.headers.get("Content-Type", "")
                if "text/event-stream" in content_type:
                    # Process SSE stream and return final result
                    return await self._process_sse_tool_response(response)

                data = response.json()

                if "error" in data:
                    self._handle_error_response(data)

                result = data.get("result", {})

                # Check if this is a task response
                if "task" in result:
                    # Return task info - caller should poll
                    return MCPToolResult(
                        content=[{"type": "task", "task": result["task"]}],
                        is_error=False,
                    )

                return MCPToolResult(
                    content=result.get("content", []),
                    is_error=result.get("isError", False),
                    structured_content=result.get("structuredContent"),
                )

        except httpx.ConnectError as e:
            raise MCPConnectionError(f"Failed to connect to MCP server: {e}")
        except MCPError:
            raise
        except Exception as e:
            raise MCPError(f"Tool call failed: {e}")

    async def _process_sse_tool_response(self, response: httpx.Response) -> MCPToolResult:
        """Process SSE stream from tool call and return final result."""
        content: list[dict[str, Any]] = []
        is_error = False
        structured_content = None

        async for line in response.aiter_lines():
            if not line or line.startswith(":"):
                continue
            if line.startswith("event:"):
                continue
            if line.startswith("id:"):
                self._last_event_id = line[3:].strip()
                continue
            if line.startswith("data:"):
                data_str = line[5:].strip()
                if data_str:
                    try:
                        data = json.loads(data_str)
                        if "error" in data:
                            self._handle_error_response(data)
                        if "result" in data:
                            result = data["result"]
                            content.extend(result.get("content", []))
                            if result.get("isError"):
                                is_error = True
                            if result.get("structuredContent"):
                                structured_content = result["structuredContent"]
                    except json.JSONDecodeError:
                        continue

        return MCPToolResult(
            content=content,
            is_error=is_error,
            structured_content=structured_content,
        )

    async def stream_tool_call(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Call an MCP tool with streaming SSE response.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Yields:
            Streaming chunks from SSE

        Raises:
            MCPError: If the tool call fails
        """
        request = self._build_jsonrpc_request(
            "tools/call",
            params={
                "name": tool_name,
                "arguments": arguments,
            },
        )

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}{self.endpoint}",
                    json=request,
                    headers=self._build_headers(accept_sse=True),
                ) as response:
                    async for line in response.aiter_lines():
                        if not line or line.startswith(":"):
                            continue
                        if line.startswith("event:"):
                            continue
                        if line.startswith("id:"):
                            self._last_event_id = line[3:].strip()
                            continue
                        if line.startswith("data:"):
                            data_str = line[5:].strip()
                            if data_str:
                                try:
                                    data = json.loads(data_str)
                                    if "error" in data:
                                        self._handle_error_response(data)
                                    yield data.get("result", {})
                                except json.JSONDecodeError:
                                    continue

        except httpx.ConnectError as e:
            raise MCPConnectionError(f"Failed to connect to MCP server: {e}")
        except MCPError:
            raise
        except Exception as e:
            raise MCPError(f"Streaming tool call failed: {e}")

    # =========================================================================
    # Resources Methods
    # =========================================================================

    async def list_resources(self, cursor: str | None = None) -> tuple[list[MCPResource], str | None]:
        """
        List available resources from the server.

        Args:
            cursor: Pagination cursor

        Returns:
            Tuple of (resources, next_cursor)
        """
        params: dict[str, Any] = {}
        if cursor:
            params["cursor"] = cursor

        request = self._build_jsonrpc_request("resources/list", params if params else None)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}{self.endpoint}",
                    json=request,
                    headers=self._build_headers(),
                )
                data = response.json()

                if "error" in data:
                    self._handle_error_response(data)

                result = data.get("result", {})
                resources_data = result.get("resources", [])
                next_cursor = result.get("nextCursor")

                resources = [
                    MCPResource(
                        uri=r["uri"],
                        name=r["name"],
                        title=r.get("title"),
                        description=r.get("description"),
                        mime_type=r.get("mimeType"),
                        annotations=r.get("annotations"),
                    )
                    for r in resources_data
                ]

                return resources, next_cursor

        except httpx.ConnectError as e:
            raise MCPConnectionError(f"Failed to connect to MCP server: {e}")
        except MCPError:
            raise
        except Exception as e:
            raise MCPError(f"Failed to list resources: {e}")

    async def read_resource(self, uri: str) -> list[MCPResourceContent]:
        """
        Read a resource by URI.

        Args:
            uri: Resource URI

        Returns:
            List of resource contents
        """
        request = self._build_jsonrpc_request("resources/read", {"uri": uri})

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}{self.endpoint}",
                    json=request,
                    headers=self._build_headers(),
                )
                data = response.json()

                if "error" in data:
                    self._handle_error_response(data)

                result = data.get("result", {})
                contents_data = result.get("contents", [])

                return [
                    MCPResourceContent(
                        uri=c["uri"],
                        mime_type=c.get("mimeType"),
                        text=c.get("text"),
                        blob=c.get("blob"),
                    )
                    for c in contents_data
                ]

        except httpx.ConnectError as e:
            raise MCPConnectionError(f"Failed to connect to MCP server: {e}")
        except MCPError:
            raise
        except Exception as e:
            raise MCPError(f"Failed to read resource: {e}")

    async def subscribe_resource(self, uri: str) -> bool:
        """
        Subscribe to resource updates.

        Args:
            uri: Resource URI to subscribe to

        Returns:
            True if subscription was successful
        """
        request = self._build_jsonrpc_request("resources/subscribe", {"uri": uri})

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}{self.endpoint}",
                    json=request,
                    headers=self._build_headers(),
                )
                data = response.json()

                if "error" in data:
                    self._handle_error_response(data)

                return True

        except MCPError:
            raise
        except Exception as e:
            raise MCPError(f"Failed to subscribe to resource: {e}")

    # =========================================================================
    # Sampling Methods
    # =========================================================================

    async def create_message(
        self,
        messages: list[dict[str, Any]],
        max_tokens: int = 1000,
        system_prompt: str | None = None,
        model_preferences: dict[str, Any] | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: dict[str, Any] | None = None,
    ) -> SamplingResponse:
        """
        Request LLM completion from client via sampling/createMessage.

        This is a server-initiated request asking the client to sample from an LLM.

        Args:
            messages: Conversation messages
            max_tokens: Maximum tokens to generate
            system_prompt: Optional system prompt
            model_preferences: Model selection hints and priorities
            tools: Optional tools available for the LLM
            tool_choice: Tool choice mode (auto, required, none)

        Returns:
            SamplingResponse with generated content
        """
        params: dict[str, Any] = {
            "messages": messages,
            "maxTokens": max_tokens,
        }

        if system_prompt:
            params["systemPrompt"] = system_prompt
        if model_preferences:
            params["modelPreferences"] = model_preferences
        if tools:
            params["tools"] = tools
        if tool_choice:
            params["toolChoice"] = tool_choice

        request = self._build_jsonrpc_request("sampling/createMessage", params)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}{self.endpoint}",
                    json=request,
                    headers=self._build_headers(),
                )
                data = response.json()

                if "error" in data:
                    self._handle_error_response(data)

                result = data.get("result", {})

                return SamplingResponse(
                    role=result.get("role", "assistant"),
                    content=result.get("content", {}),
                    model=result.get("model"),
                    stop_reason=result.get("stopReason"),
                )

        except httpx.ConnectError as e:
            raise MCPConnectionError(f"Failed to connect to MCP server: {e}")
        except MCPError:
            raise
        except Exception as e:
            raise MCPError(f"Sampling request failed: {e}")

    # =========================================================================
    # Elicitation Methods
    # =========================================================================

    async def create_elicitation(
        self,
        message: str,
        mode: ElicitationMode = ElicitationMode.FORM,
        requested_schema: dict[str, Any] | None = None,
        url: str | None = None,
    ) -> ElicitationResponse:
        """
        Request user input via elicitation/create.

        Args:
            message: Human-readable explanation of why input is needed
            mode: Elicitation mode (form or url)
            requested_schema: JSON Schema for form mode
            url: URL for url mode

        Returns:
            ElicitationResponse with user's response
        """
        params: dict[str, Any] = {
            "message": message,
            "mode": mode.value,
        }

        if mode == ElicitationMode.FORM and requested_schema:
            params["requestedSchema"] = requested_schema
        elif mode == ElicitationMode.URL:
            if not url:
                raise MCPInvalidParamsError("URL is required for url mode elicitation")
            params["url"] = url
            params["elicitationId"] = secrets.token_urlsafe(32)

        request = self._build_jsonrpc_request("elicitation/create", params)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}{self.endpoint}",
                    json=request,
                    headers=self._build_headers(),
                )
                data = response.json()

                if "error" in data:
                    self._handle_error_response(data)

                result = data.get("result", {})

                return ElicitationResponse(
                    action=ElicitationAction(result.get("action", "cancel")),
                    content=result.get("content"),
                )

        except httpx.ConnectError as e:
            raise MCPConnectionError(f"Failed to connect to MCP server: {e}")
        except MCPError:
            raise
        except Exception as e:
            raise MCPError(f"Elicitation request failed: {e}")

    # =========================================================================
    # Tasks Methods (Experimental)
    # =========================================================================

    async def get_task(self, task_id: str) -> MCPTask:
        """
        Get task status.

        Args:
            task_id: Task ID to get status for

        Returns:
            MCPTask with current status
        """
        request = self._build_jsonrpc_request("tasks/get", {"taskId": task_id})

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}{self.endpoint}",
                    json=request,
                    headers=self._build_headers(),
                )
                data = response.json()

                if "error" in data:
                    self._handle_error_response(data)

                result = data.get("result", {})

                return MCPTask(
                    task_id=result["taskId"],
                    status=TaskStatus(result["status"]),
                    created_at=datetime.fromisoformat(result["createdAt"].replace("Z", "+00:00")),
                    last_updated_at=datetime.fromisoformat(result["lastUpdatedAt"].replace("Z", "+00:00")),
                    ttl=result.get("ttl"),
                    poll_interval=result.get("pollInterval"),
                    status_message=result.get("statusMessage"),
                )

        except httpx.ConnectError as e:
            raise MCPConnectionError(f"Failed to connect to MCP server: {e}")
        except MCPError:
            raise
        except Exception as e:
            raise MCPError(f"Failed to get task: {e}")

    async def get_task_result(self, task_id: str) -> MCPToolResult:
        """
        Get task result (blocks until task completes).

        Args:
            task_id: Task ID to get result for

        Returns:
            MCPToolResult with task output
        """
        request = self._build_jsonrpc_request("tasks/result", {"taskId": task_id})

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}{self.endpoint}",
                    json=request,
                    headers=self._build_headers(accept_sse=True),
                )

                # May return SSE for long-running tasks
                content_type = response.headers.get("Content-Type", "")
                if "text/event-stream" in content_type:
                    return await self._process_sse_tool_response(response)

                data = response.json()

                if "error" in data:
                    self._handle_error_response(data)

                result = data.get("result", {})

                return MCPToolResult(
                    content=result.get("content", []),
                    is_error=result.get("isError", False),
                    structured_content=result.get("structuredContent"),
                )

        except httpx.ConnectError as e:
            raise MCPConnectionError(f"Failed to connect to MCP server: {e}")
        except MCPError:
            raise
        except Exception as e:
            raise MCPError(f"Failed to get task result: {e}")

    async def cancel_task(self, task_id: str) -> MCPTask:
        """
        Cancel a running task.

        Args:
            task_id: Task ID to cancel

        Returns:
            MCPTask with cancelled status
        """
        request = self._build_jsonrpc_request("tasks/cancel", {"taskId": task_id})

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}{self.endpoint}",
                    json=request,
                    headers=self._build_headers(),
                )
                data = response.json()

                if "error" in data:
                    self._handle_error_response(data)

                result = data.get("result", {})

                return MCPTask(
                    task_id=result["taskId"],
                    status=TaskStatus(result["status"]),
                    created_at=datetime.fromisoformat(result["createdAt"].replace("Z", "+00:00")),
                    last_updated_at=datetime.fromisoformat(result["lastUpdatedAt"].replace("Z", "+00:00")),
                    ttl=result.get("ttl"),
                    poll_interval=result.get("pollInterval"),
                    status_message=result.get("statusMessage"),
                )

        except httpx.ConnectError as e:
            raise MCPConnectionError(f"Failed to connect to MCP server: {e}")
        except MCPError:
            raise
        except Exception as e:
            raise MCPError(f"Failed to cancel task: {e}")

    async def list_tasks(self, cursor: str | None = None) -> tuple[list[MCPTask], str | None]:
        """
        List active tasks.

        Args:
            cursor: Pagination cursor

        Returns:
            Tuple of (tasks, next_cursor)
        """
        params: dict[str, Any] = {}
        if cursor:
            params["cursor"] = cursor

        request = self._build_jsonrpc_request("tasks/list", params if params else None)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}{self.endpoint}",
                    json=request,
                    headers=self._build_headers(),
                )
                data = response.json()

                if "error" in data:
                    self._handle_error_response(data)

                result = data.get("result", {})
                tasks_data = result.get("tasks", [])
                next_cursor = result.get("nextCursor")

                tasks = [
                    MCPTask(
                        task_id=t["taskId"],
                        status=TaskStatus(t["status"]),
                        created_at=datetime.fromisoformat(t["createdAt"].replace("Z", "+00:00")),
                        last_updated_at=datetime.fromisoformat(t["lastUpdatedAt"].replace("Z", "+00:00")),
                        ttl=t.get("ttl"),
                        poll_interval=t.get("pollInterval"),
                        status_message=t.get("statusMessage"),
                    )
                    for t in tasks_data
                ]

                return tasks, next_cursor

        except httpx.ConnectError as e:
            raise MCPConnectionError(f"Failed to connect to MCP server: {e}")
        except MCPError:
            raise
        except Exception as e:
            raise MCPError(f"Failed to list tasks: {e}")


# ==============================================================================
# MCP Bridge - Full 2025-11-25 Protocol Support
# ==============================================================================


class MCPBridge:
    """
    Bridge between Unified API and MCP protocol.

    Implements full MCP 2025-11-25 protocol support:
    - Chat via tools/call (agent_chat)
    - Streaming via SSE
    - Resource access
    - Sampling for LLM completions
    - Elicitation for user input
    - Task management for long-running operations

    Translates chat requests to MCP tool calls,
    handling both synchronous and streaming responses.
    """

    def __init__(
        self,
        mcp_url: str | None = None,
        mcp_client: MCPClient | None = None,
        endpoint: str = MCP_ENDPOINT,
    ) -> None:
        """
        Initialize the bridge.

        Args:
            mcp_url: MCP server URL (creates client if not provided)
            mcp_client: Pre-configured MCPClient instance
            endpoint: MCP endpoint path (default: /mcp)
        """
        self._client: MCPClient | None
        if mcp_client:
            self._client = mcp_client
        elif mcp_url:
            self._client = MCPClient(base_url=mcp_url, endpoint=endpoint)
        else:
            self._client = None

        self._initialized = False
        self._available_tools: list[MCPTool] = []
        self._available_resources: list[MCPResource] = []

    @property
    def is_configured(self) -> bool:
        """Check if the bridge is properly configured."""
        return self._client is not None

    @property
    def is_initialized(self) -> bool:
        """Check if the bridge has been initialized with the server."""
        return self._client is not None and self._client.is_initialized

    @property
    def session_id(self) -> str | None:
        """Get the current MCP session ID."""
        return self._client.session_id if self._client else None

    @property
    def available_tools(self) -> list[MCPTool]:
        """Get cached list of available tools."""
        return self._available_tools

    @property
    def available_resources(self) -> list[MCPResource]:
        """Get cached list of available resources."""
        return self._available_resources

    # =========================================================================
    # Lifecycle Methods
    # =========================================================================

    async def initialize(
        self,
        client_info: dict[str, Any] | None = None,
        capabilities: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Initialize connection with MCP server.

        Must be called before using other methods for full protocol compliance.

        Args:
            client_info: Client name and version
            capabilities: Client capabilities to declare

        Returns:
            Server capabilities and info
        """
        if not self._client:
            raise ChatError("MCP client not configured")

        result = await self._client.initialize(client_info, capabilities)
        self._initialized = True

        # Cache available tools and resources
        await self.refresh_tools()
        await self.refresh_resources()

        return result

    async def close(self) -> None:
        """Close the MCP session."""
        if self._client:
            await self._client.terminate_session()
            self._initialized = False

    async def refresh_tools(self) -> list[MCPTool]:
        """Refresh the cached list of available tools."""
        if not self._client:
            return []

        tools: list[MCPTool] = []
        cursor = None

        while True:
            batch, next_cursor = await self._client.list_tools(cursor)
            tools.extend(batch)
            if not next_cursor:
                break
            cursor = next_cursor

        self._available_tools = tools
        return tools

    async def refresh_resources(self) -> list[MCPResource]:
        """Refresh the cached list of available resources."""
        if not self._client:
            return []

        resources: list[MCPResource] = []
        cursor = None

        try:
            while True:
                batch, next_cursor = await self._client.list_resources(cursor)
                resources.extend(batch)
                if not next_cursor:
                    break
                cursor = next_cursor
        except MCPError:
            # Resources might not be supported
            pass

        self._available_resources = resources
        return resources

    # =========================================================================
    # Resource Methods
    # =========================================================================

    async def read_resource(self, uri: str) -> list[MCPResourceContent]:
        """
        Read a resource by URI.

        Args:
            uri: Resource URI

        Returns:
            List of resource contents
        """
        if not self._client:
            raise ChatError("MCP client not configured")

        return await self._client.read_resource(uri)

    async def subscribe_resource(self, uri: str) -> bool:
        """Subscribe to resource updates."""
        if not self._client:
            raise ChatError("MCP client not configured")

        return await self._client.subscribe_resource(uri)

    # =========================================================================
    # Tool Methods
    # =========================================================================

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        as_task: bool = False,
        task_ttl: int = 60000,
    ) -> MCPToolResult:
        """
        Call an MCP tool directly.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
            as_task: Whether to execute as a task (for long-running ops)
            task_ttl: Task TTL in milliseconds if as_task is True

        Returns:
            MCPToolResult with content
        """
        if not self._client:
            raise ChatError("MCP client not configured")

        return await self._client.call_tool(
            tool_name,
            arguments,
            task_ttl=task_ttl if as_task else None,
        )

    # =========================================================================
    # Sampling Methods (Server-initiated LLM)
    # =========================================================================

    async def request_sampling(
        self,
        messages: list[dict[str, Any]],
        max_tokens: int = 1000,
        system_prompt: str | None = None,
        model_hints: list[str] | None = None,
        intelligence_priority: float = 0.5,
        speed_priority: float = 0.5,
        cost_priority: float = 0.5,
        tools: list[dict[str, Any]] | None = None,
        tool_choice_mode: ToolChoiceMode = ToolChoiceMode.AUTO,
    ) -> SamplingResponse:
        """
        Request LLM completion via sampling/createMessage.

        This allows the server to request the client to sample from an LLM.
        Useful for agent patterns where the server needs LLM assistance.

        Args:
            messages: Conversation messages
            max_tokens: Maximum tokens to generate
            system_prompt: Optional system prompt
            model_hints: Model name hints (e.g., ["claude-3-sonnet", "gpt-4"])
            intelligence_priority: Priority for model capability (0-1)
            speed_priority: Priority for low latency (0-1)
            cost_priority: Priority for low cost (0-1)
            tools: Optional tools for the LLM to use
            tool_choice_mode: How the LLM should choose tools

        Returns:
            SamplingResponse with generated content
        """
        if not self._client:
            raise ChatError("MCP client not configured")

        model_preferences: dict[str, Any] = {
            "intelligencePriority": intelligence_priority,
            "speedPriority": speed_priority,
            "costPriority": cost_priority,
        }

        if model_hints:
            model_preferences["hints"] = [{"name": h} for h in model_hints]

        tool_choice = {"mode": tool_choice_mode.value} if tools else None

        return await self._client.create_message(
            messages=messages,
            max_tokens=max_tokens,
            system_prompt=system_prompt,
            model_preferences=model_preferences,
            tools=tools,
            tool_choice=tool_choice,
        )

    # =========================================================================
    # Elicitation Methods (User Input)
    # =========================================================================

    async def request_user_input(
        self,
        message: str,
        schema: dict[str, Any] | None = None,
    ) -> ElicitationResponse:
        """
        Request structured user input via form elicitation.

        Args:
            message: Human-readable explanation
            schema: JSON Schema for the expected input

        Returns:
            ElicitationResponse with user's input
        """
        if not self._client:
            raise ChatError("MCP client not configured")

        return await self._client.create_elicitation(
            message=message,
            mode=ElicitationMode.FORM,
            requested_schema=schema,
        )

    async def request_user_url_action(
        self,
        message: str,
        url: str,
    ) -> ElicitationResponse:
        """
        Request user to navigate to a URL (for OAuth, sensitive data).

        Args:
            message: Human-readable explanation
            url: URL for the user to navigate to

        Returns:
            ElicitationResponse indicating if user completed action
        """
        if not self._client:
            raise ChatError("MCP client not configured")

        return await self._client.create_elicitation(
            message=message,
            mode=ElicitationMode.URL,
            url=url,
        )

    # =========================================================================
    # Task Methods (Long-running Operations)
    # =========================================================================

    async def get_task(self, task_id: str) -> MCPTask:
        """Get task status."""
        if not self._client:
            raise ChatError("MCP client not configured")
        return await self._client.get_task(task_id)

    async def get_task_result(self, task_id: str) -> MCPToolResult:
        """Get task result (blocks until complete)."""
        if not self._client:
            raise ChatError("MCP client not configured")
        return await self._client.get_task_result(task_id)

    async def cancel_task(self, task_id: str) -> MCPTask:
        """Cancel a running task."""
        if not self._client:
            raise ChatError("MCP client not configured")
        return await self._client.cancel_task(task_id)

    async def list_tasks(self) -> list[MCPTask]:
        """List all active tasks."""
        if not self._client:
            raise ChatError("MCP client not configured")

        tasks: list[MCPTask] = []
        cursor = None

        while True:
            batch, next_cursor = await self._client.list_tasks(cursor)
            tasks.extend(batch)
            if not next_cursor:
                break
            cursor = next_cursor

        return tasks

    async def send_chat_message(
        self,
        session_id: str,
        message: str,
        user_id: str = "anonymous",
        token: str = "",
        response_format: str = "detailed",
    ) -> ChatResponse:
        """
        Send a chat message via MCP agent_chat tool.

        Args:
            session_id: Session ID (used as thread_id)
            message: User message
            user_id: User identifier
            token: JWT authentication token
            response_format: Response format ("concise" or "detailed")

        Returns:
            ChatResponse with assistant's reply

        Raises:
            ChatError: If the chat fails
        """
        if not self._client:
            raise ChatError("MCP client not configured")

        with tracer.start_as_current_span(
            "mcp_bridge.chat.send",
            attributes={
                "session.id": session_id,
                "user.id": user_id,
            },
        ):
            try:
                # Construct user-owned thread_id for authorization
                user_id_normalized = user_id.split(":")[-1] if ":" in user_id else user_id
                thread_id = f"{user_id_normalized}_{session_id}"

                arguments = {
                    "message": message,
                    "token": token,
                    "user_id": user_id,
                    "thread_id": thread_id,
                    "response_format": response_format,
                }

                # Call MCP agent_chat tool
                result = await self._client.call_tool("agent_chat", arguments)

                # Extract response content
                content = ""
                for item in result.content:
                    if item.get("type") == "text":
                        content += item.get("text", "")

                logger.info(
                    "Chat message sent via MCP",
                    extra={
                        "session_id": session_id,
                        "response_length": len(content),
                    },
                )

                return ChatResponse(content=content)

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
        user_id: str = "anonymous",
        token: str = "",
        response_format: str = "detailed",
    ) -> AsyncIterator[ChatChunk]:
        """
        Stream a chat message response via MCP.

        Args:
            session_id: Session ID
            message: User message
            user_id: User identifier
            token: JWT authentication token
            response_format: Response format

        Yields:
            ChatChunk objects as they arrive

        Raises:
            ChatError: If streaming fails
        """
        if not self._client:
            raise ChatError("MCP client not configured")

        with tracer.start_as_current_span(
            "mcp_bridge.chat.stream",
            attributes={
                "session.id": session_id,
                "user.id": user_id,
            },
        ):
            try:
                # Construct user-owned thread_id for authorization
                user_id_normalized = user_id.split(":")[-1] if ":" in user_id else user_id
                thread_id = f"{user_id_normalized}_{session_id}"

                arguments = {
                    "message": message,
                    "token": token,
                    "user_id": user_id,
                    "thread_id": thread_id,
                    "response_format": response_format,
                }

                # Stream MCP agent_chat tool call
                chunk_count = 0
                async for result in self._client.stream_tool_call("agent_chat", arguments):
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


# ==============================================================================
# Factory Function
# ==============================================================================


_mcp_bridge: MCPBridge | None = None


def get_mcp_bridge() -> MCPBridge | None:
    """
    Get the global MCP bridge instance.

    Returns None if MCP_SERVER_URL is not configured.
    """
    import os

    global _mcp_bridge

    if _mcp_bridge is None:
        mcp_url = os.getenv("MCP_SERVER_URL")
        if mcp_url:
            _mcp_bridge = MCPBridge(mcp_url=mcp_url)
            logger.info(f"MCP bridge configured for {mcp_url}")
        else:
            logger.debug("MCP_SERVER_URL not set, MCP bridge not available")

    return _mcp_bridge


def reset_mcp_bridge() -> None:
    """Reset the MCP bridge singleton (for testing)."""
    global _mcp_bridge
    _mcp_bridge = None
