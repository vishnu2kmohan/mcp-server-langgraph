"""
MCP StreamableHTTP client for the Interactive Playground.

Provides a client for communicating with MCP servers via StreamableHTTP:
- JSON-RPC message formatting
- Tool invocation (agent_chat, etc.)
- Streaming response handling (NDJSON)
- Error handling and retries

Example:
    from mcp_server_langgraph.playground.mcp.client import MCPClient

    client = MCPClient(base_url="http://localhost:8000")
    result = await client.initialize()
    tools = await client.list_tools()
    response = await client.call_tool("agent_chat", {"message": "Hello"})
"""

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from mcp_server_langgraph.observability.telemetry import logger, tracer


# ==============================================================================
# Exceptions
# ==============================================================================


class MCPError(Exception):
    """Base exception for MCP client errors."""

    pass


class MCPConnectionError(MCPError):
    """Raised when connection to MCP server fails."""

    pass


class MCPPermissionError(MCPError):
    """Raised when MCP server returns permission denied."""

    pass


class MCPValidationError(MCPError):
    """Raised when MCP server returns validation error."""

    pass


# ==============================================================================
# MCP Client
# ==============================================================================


class MCPClient:
    """
    MCP StreamableHTTP client for synchronous requests.

    Implements the MCP protocol over HTTP with JSON-RPC messaging.
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
    ) -> None:
        """
        Initialize MCP client.

        Args:
            base_url: Base URL of MCP server (e.g., "http://localhost:8000")
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._request_id = 0

    def _next_request_id(self) -> int:
        """Generate next JSON-RPC request ID."""
        self._request_id += 1
        return self._request_id

    def _build_jsonrpc_request(
        self,
        method: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build a JSON-RPC 2.0 request message."""
        request = {
            "jsonrpc": "2.0",
            "id": self._next_request_id(),
            "method": method,
        }
        if params is not None:
            request["params"] = params
        return request

    def _handle_error_response(self, response: dict[str, Any]) -> None:
        """Handle JSON-RPC error response."""
        error = response.get("error", {})
        code = error.get("code", -32603)
        message = error.get("message", "Unknown error")

        if code == -32001:  # Permission denied
            raise MCPPermissionError(message)
        elif code == -32602:  # Invalid params
            raise MCPValidationError(message)
        else:
            raise MCPError(f"MCP error {code}: {message}")

    async def initialize(self) -> dict[str, Any]:
        """
        Perform MCP initialization handshake.

        Returns:
            Server capabilities and info
        """
        with tracer.start_as_current_span("mcp.client.initialize"):
            request = self._build_jsonrpc_request("initialize")

            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/message",
                        json=request,
                    )
                    data = response.json()

                    if "error" in data:
                        self._handle_error_response(data)

                    logger.info(
                        "MCP initialization successful",
                        extra={"server": data.get("result", {}).get("serverInfo", {})},
                    )

                    result: dict[str, Any] = data.get("result", {})
                    return result

            except httpx.ConnectError as e:
                raise MCPConnectionError(f"Failed to connect to MCP server: {e}")
            except Exception as e:
                if isinstance(e, MCPError):
                    raise
                raise MCPConnectionError(f"MCP initialization failed: {e}")

    async def list_tools(self) -> list[dict[str, Any]]:
        """
        List available tools from MCP server.

        Returns:
            List of tool definitions
        """
        with tracer.start_as_current_span("mcp.client.list_tools"):
            request = self._build_jsonrpc_request("tools/list")

            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/message",
                        json=request,
                    )
                    data = response.json()

                    if "error" in data:
                        self._handle_error_response(data)

                    tools: list[dict[str, Any]] = data.get("result", {}).get("tools", [])
                    logger.debug(f"Retrieved {len(tools)} tools from MCP server")

                    return tools

            except httpx.ConnectError as e:
                raise MCPConnectionError(f"Failed to connect to MCP server: {e}")
            except Exception as e:
                if isinstance(e, MCPError):
                    raise
                raise MCPError(f"Failed to list tools: {e}")

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Call a tool on the MCP server.

        Args:
            name: Tool name (e.g., "agent_chat")
            arguments: Tool arguments

        Returns:
            List of content items from tool response
        """
        with tracer.start_as_current_span("mcp.client.call_tool", attributes={"tool.name": name}):
            request = self._build_jsonrpc_request(
                "tools/call",
                params={"name": name, "arguments": arguments},
            )

            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/message",
                        json=request,
                    )
                    data = response.json()

                    if "error" in data:
                        self._handle_error_response(data)

                    content: list[dict[str, Any]] = data.get("result", {}).get("content", [])
                    logger.info(
                        f"Tool {name} returned {len(content)} content items",
                        extra={"tool": name},
                    )

                    return content

            except httpx.ConnectError as e:
                raise MCPConnectionError(f"Failed to connect to MCP server: {e}")
            except Exception as e:
                if isinstance(e, MCPError):
                    raise
                raise MCPError(f"Tool call failed: {e}")


# ==============================================================================
# Streaming MCP Client
# ==============================================================================


class MCPStreamingClient:
    """
    MCP StreamableHTTP client with streaming response support.

    Uses NDJSON (newline-delimited JSON) for streaming responses.
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 60.0,
    ) -> None:
        """
        Initialize streaming MCP client.

        Args:
            base_url: Base URL of MCP server
            timeout: Request timeout in seconds (longer for streaming)
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._request_id = 0

    def _next_request_id(self) -> int:
        """Generate next JSON-RPC request ID."""
        self._request_id += 1
        return self._request_id

    async def stream_tool_call(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Stream a tool call response.

        Args:
            name: Tool name
            arguments: Tool arguments

        Yields:
            Response chunks as they arrive
        """
        with tracer.start_as_current_span("mcp.client.stream_tool", attributes={"tool.name": name}):
            request = {
                "jsonrpc": "2.0",
                "id": self._next_request_id(),
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            }

            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    async with client.stream(
                        "POST",
                        f"{self.base_url}/message",
                        json=request,
                        headers={"Accept": "application/x-ndjson, application/json"},
                    ) as response:
                        content_type = response.headers.get("content-type", "")

                        if "application/x-ndjson" in content_type:
                            # Stream NDJSON responses
                            async for line in response.aiter_lines():
                                if line.strip():
                                    try:
                                        data = json.loads(line)
                                        if "error" in data:
                                            error = data["error"]
                                            if error.get("code") == -32001:
                                                raise MCPPermissionError(error.get("message", "Permission denied"))
                                            raise MCPError(f"MCP error: {error.get('message')}")
                                        yield data.get("result", {})
                                    except json.JSONDecodeError:
                                        logger.warning(f"Failed to parse NDJSON line: {line}")
                        else:
                            # Fall back to regular JSON response
                            body = await response.aread()
                            data = json.loads(body)
                            if "error" in data:
                                error = data["error"]
                                if error.get("code") == -32001:
                                    raise MCPPermissionError(error.get("message", "Permission denied"))
                                raise MCPError(f"MCP error: {error.get('message')}")
                            yield data.get("result", {})

            except httpx.ConnectError as e:
                raise MCPConnectionError(f"Failed to connect to MCP server: {e}")
            except Exception as e:
                if isinstance(e, MCPError):
                    raise
                raise MCPError(f"Streaming tool call failed: {e}")
