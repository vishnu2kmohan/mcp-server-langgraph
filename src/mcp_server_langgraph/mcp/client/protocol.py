"""
MCP Protocol Messages (v2025-11-25)

Implements JSON-RPC 2.0 message formatting and parsing per the
MCP Protocol Specification version 2025-11-25.

Reference: https://modelcontextprotocol.io/specification/2025-11-25
"""

import json
import uuid
from dataclasses import dataclass, field
from typing import Any


# Protocol version
MCP_PROTOCOL_VERSION = "2025-11-25"


def _generate_request_id() -> str:
    """Generate a unique request ID."""
    return str(uuid.uuid4())


@dataclass
class MCPRequest:
    """JSON-RPC 2.0 request message."""

    method: str
    """The method to call."""

    params: dict[str, Any] | None = None
    """Method parameters."""

    id: str = field(default_factory=_generate_request_id)
    """Unique request identifier."""

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-RPC 2.0 message dict."""
        msg: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": self.id,
            "method": self.method,
        }
        if self.params is not None:
            msg["params"] = self.params
        return msg

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict())


@dataclass
class MCPNotification:
    """JSON-RPC 2.0 notification message (no id, no response expected)."""

    method: str
    """The notification method."""

    params: dict[str, Any] | None = None
    """Notification parameters."""

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-RPC 2.0 message dict."""
        msg: dict[str, Any] = {
            "jsonrpc": "2.0",
            "method": self.method,
        }
        if self.params is not None:
            msg["params"] = self.params
        return msg

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict())


@dataclass
class MCPResponse:
    """JSON-RPC 2.0 response message."""

    id: str | int | None
    """Request ID this responds to."""

    result: Any | None = None
    """Result data (on success)."""

    error: dict[str, Any] | None = None
    """Error data (on failure)."""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MCPResponse":
        """Parse from JSON-RPC 2.0 message dict."""
        return cls(
            id=data.get("id"),
            result=data.get("result"),
            error=data.get("error"),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "MCPResponse":
        """Parse from JSON string."""
        return cls.from_dict(json.loads(json_str))

    @property
    def is_success(self) -> bool:
        """Check if response indicates success."""
        return self.error is None


# =============================================================================
# Initialize Handshake
# =============================================================================


@dataclass
class ServerInfo:
    """Parsed server information from initialize response."""

    protocol_version: str
    server_name: str
    server_version: str | None
    has_tools: bool
    tools_list_changed: bool
    has_resources: bool
    has_prompts: bool
    raw_capabilities: dict[str, Any]


def create_initialize_request(
    client_name: str,
    client_version: str,
    client_description: str | None = None,
) -> MCPRequest:
    """Create an initialize request per MCP spec.

    Args:
        client_name: Name of the client application
        client_version: Client version string
        client_description: Optional client description

    Returns:
        MCPRequest for initialization
    """
    client_info: dict[str, Any] = {
        "name": client_name,
        "version": client_version,
    }
    if client_description:
        client_info["description"] = client_description

    params: dict[str, Any] = {
        "protocolVersion": MCP_PROTOCOL_VERSION,
        "capabilities": {
            # Client capabilities we support
            "roots": {"listChanged": False},
            "sampling": {},
        },
        "clientInfo": client_info,
    }

    return MCPRequest(method="initialize", params=params)


def parse_initialize_result(result: dict[str, Any]) -> ServerInfo:
    """Parse initialize response result.

    Args:
        result: The 'result' field from the initialize response

    Returns:
        ServerInfo with parsed capabilities
    """
    capabilities = result.get("capabilities", {})
    server_info = result.get("serverInfo", {})
    tools_cap = capabilities.get("tools", {})
    resources_cap = capabilities.get("resources", {})
    prompts_cap = capabilities.get("prompts", {})

    return ServerInfo(
        protocol_version=result.get("protocolVersion", "unknown"),
        server_name=server_info.get("name", "unknown"),
        server_version=server_info.get("version"),
        has_tools=bool(tools_cap),
        tools_list_changed=tools_cap.get("listChanged", False) if tools_cap else False,
        has_resources=bool(resources_cap),
        has_prompts=bool(prompts_cap),
        raw_capabilities=capabilities,
    )


def create_initialized_notification() -> MCPNotification:
    """Create the initialized notification to complete handshake.

    Returns:
        MCPNotification for initialized
    """
    return MCPNotification(method="notifications/initialized")


# =============================================================================
# Tools Protocol
# =============================================================================


def create_tools_list_request(cursor: str | None = None) -> MCPRequest:
    """Create a tools/list request.

    Args:
        cursor: Optional pagination cursor

    Returns:
        MCPRequest for tools/list
    """
    params: dict[str, Any] = {}
    if cursor is not None:
        params["cursor"] = cursor
    else:
        params["cursor"] = None  # Explicit null per spec

    return MCPRequest(method="tools/list", params=params)


def parse_tools_list_result(
    result: dict[str, Any],
) -> tuple[list[dict[str, Any]], str | None]:
    """Parse tools/list response result.

    Args:
        result: The 'result' field from the tools/list response

    Returns:
        Tuple of (list of tool definitions, next cursor or None)
    """
    tools = result.get("tools", [])
    next_cursor = result.get("nextCursor")
    return tools, next_cursor


def create_tools_call_request(
    name: str,
    arguments: dict[str, Any],
) -> MCPRequest:
    """Create a tools/call request.

    Args:
        name: Tool name to call
        arguments: Tool arguments

    Returns:
        MCPRequest for tools/call
    """
    return MCPRequest(
        method="tools/call",
        params={
            "name": name,
            "arguments": arguments,
        },
    )


def parse_tools_call_result(
    result: dict[str, Any],
) -> tuple[list[dict[str, Any]], bool]:
    """Parse tools/call response result.

    Args:
        result: The 'result' field from the tools/call response

    Returns:
        Tuple of (content list, isError flag)
    """
    content = result.get("content", [])
    is_error = result.get("isError", False)
    return content, is_error


# =============================================================================
# HTTP Headers
# =============================================================================


def get_mcp_headers(session_id: str | None = None) -> dict[str, str]:
    """Generate required MCP HTTP headers.

    Args:
        session_id: Optional session ID for subsequent requests

    Returns:
        Dict of HTTP headers
    """
    headers = {
        "MCP-Protocol-Version": MCP_PROTOCOL_VERSION,
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
    }
    if session_id is not None:
        headers["MCP-Session-Id"] = session_id
    return headers


# =============================================================================
# STDIO Transport Framing
# =============================================================================


def frame_stdio_message(message: dict[str, Any]) -> str:
    """Frame a message for STDIO transport.

    Per spec, messages are newline-delimited with no embedded newlines.

    Args:
        message: JSON-RPC message dict

    Returns:
        Newline-terminated JSON string
    """
    # Compact JSON (no newlines), then add trailing newline
    return json.dumps(message, separators=(",", ":")) + "\n"


def parse_stdio_messages(raw: str) -> list[dict[str, Any]]:
    """Parse newline-delimited STDIO messages.

    Args:
        raw: Raw string with potentially multiple messages

    Returns:
        List of parsed message dicts (only complete messages)
    """
    messages: list[dict[str, Any]] = []
    lines = raw.split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            messages.append(json.loads(line))
        except json.JSONDecodeError:
            # Incomplete message - ignore (would be buffered in real impl)
            pass

    return messages


# =============================================================================
# Resources Protocol
# =============================================================================


def create_resources_list_request(cursor: str | None = None) -> MCPRequest:
    """Create a resources/list request.

    Args:
        cursor: Optional pagination cursor

    Returns:
        MCPRequest for resources/list
    """
    params: dict[str, Any] = {}
    if cursor is not None:
        params["cursor"] = cursor
    else:
        params["cursor"] = None  # Explicit null per spec

    return MCPRequest(method="resources/list", params=params)


def parse_resources_list_result(
    result: dict[str, Any],
) -> tuple[list[dict[str, Any]], str | None]:
    """Parse resources/list response result.

    Args:
        result: The 'result' field from the resources/list response

    Returns:
        Tuple of (list of resource definitions, next cursor or None)
    """
    resources = result.get("resources", [])
    next_cursor = result.get("nextCursor")
    return resources, next_cursor


# =============================================================================
# Prompts Protocol
# =============================================================================


def create_prompts_list_request(cursor: str | None = None) -> MCPRequest:
    """Create a prompts/list request.

    Args:
        cursor: Optional pagination cursor

    Returns:
        MCPRequest for prompts/list
    """
    params: dict[str, Any] = {}
    if cursor is not None:
        params["cursor"] = cursor
    else:
        params["cursor"] = None  # Explicit null per spec

    return MCPRequest(method="prompts/list", params=params)


def parse_prompts_list_result(
    result: dict[str, Any],
) -> tuple[list[dict[str, Any]], str | None]:
    """Parse prompts/list response result.

    Args:
        result: The 'result' field from the prompts/list response

    Returns:
        Tuple of (list of prompt definitions, next cursor or None)
    """
    prompts = result.get("prompts", [])
    next_cursor = result.get("nextCursor")
    return prompts, next_cursor
