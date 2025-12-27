"""
MCP Client Session Manager for managing connections to external MCP servers.

Handles connection lifecycle including connect, disconnect, and tool operations
across different transport types (STDIO, HTTP, SSE, WebSocket).

Implements MCP Protocol Specification version 2025-11-25.
Reference: https://modelcontextprotocol.io/specification/2025-11-25
"""

import asyncio
import json
from enum import Enum
from typing import TYPE_CHECKING, Any

from mcp_server_langgraph.mcp.client.protocol import (
    MCPRequest,
    MCPResponse,
    ServerInfo,
    create_initialize_request,
    create_initialized_notification,
    create_prompts_list_request,
    create_resources_list_request,
    create_tools_call_request,
    create_tools_list_request,
    frame_stdio_message,
    get_mcp_headers,
    parse_initialize_result,
    parse_prompts_list_result,
    parse_resources_list_result,
    parse_tools_call_result,
    parse_tools_list_result,
)
from mcp_server_langgraph.mcp.client.tool_registry import MCPServerConfig
from mcp_server_langgraph.observability.telemetry import logger

if TYPE_CHECKING:
    pass


class MCPTransportType(Enum):
    """Transport types for MCP communication."""

    STDIO = "stdio"
    """Standard I/O transport (subprocess)."""

    HTTP = "http"
    """HTTP transport."""

    SSE = "sse"
    """Server-Sent Events transport."""

    WEBSOCKET = "websocket"
    """WebSocket transport."""


class MCPClientSession:
    """Manages connection to a single MCP server.

    This class handles the connection lifecycle for a single external MCP server,
    including establishing connections, listing available tools, and executing
    tool calls.

    Implements MCP Protocol Specification v2025-11-25 with full JSON-RPC 2.0
    message support and proper initialize/initialized handshake.

    Example:
        config = MCPServerConfig(
            name="playwright",
            command="npx",
            args=["@playwright/mcp@latest"],
        )

        session = MCPClientSession(config)
        await session.connect()

        tools = await session.list_tools()
        result = await session.call_tool("screenshot", {"url": "https://example.com"})

        await session.disconnect()
    """

    def __init__(
        self,
        config: MCPServerConfig,
        transport_type: MCPTransportType | None = None,
    ):
        """Initialize session with configuration.

        Args:
            config: Server configuration
            transport_type: Override transport type detection
        """
        self.config = config
        self.transport_type = transport_type or self._detect_transport()
        self._connected = False
        self._tools: list[dict[str, Any]] = []
        self._process: asyncio.subprocess.Process | None = None  # For STDIO transport
        self._pending_requests: dict[str, asyncio.Future[MCPResponse]] = {}
        self.server_info: ServerInfo | None = None
        self._session_id: str | None = None  # For HTTP transport session tracking
        self._http_client: Any | None = None  # For HTTP transport (aiohttp.ClientSession)

    def _detect_transport(self) -> MCPTransportType:
        """Detect transport type from configuration.

        Returns:
            Detected transport type
        """
        if self.config.url:
            url_lower = self.config.url.lower()
            if url_lower.startswith("ws://") or url_lower.startswith("wss://"):
                return MCPTransportType.WEBSOCKET
            return MCPTransportType.HTTP
        return MCPTransportType.STDIO

    async def connect(self) -> None:
        """Establish connection to MCP server.

        Raises:
            ConnectionError: If unable to connect
            ValueError: If configuration is invalid
        """
        if self._connected:
            return

        logger.info(
            "Connecting to MCP server",
            extra={
                "server_name": self.config.name,
                "transport": self.transport_type.value,
            },
        )

        if self.transport_type == MCPTransportType.STDIO:
            await self._connect_stdio()
        elif self.transport_type == MCPTransportType.HTTP:
            await self._connect_http()
        elif self.transport_type == MCPTransportType.SSE:
            await self._connect_sse()
        elif self.transport_type == MCPTransportType.WEBSOCKET:
            await self._connect_websocket()

        self._connected = True

        logger.info("Connected to MCP server", extra={"server_name": self.config.name})

    async def _connect_stdio(self) -> None:
        """Establish STDIO connection by spawning subprocess.

        This method:
        1. Spawns the MCP server subprocess
        2. Sends the initialize request
        3. Waits for initialize response
        4. Sends initialized notification

        Raises:
            ConnectionError: If unable to spawn or handshake fails
        """
        if not self.config.command:
            raise ValueError("STDIO transport requires 'command' in config")

        # Build command args
        cmd_args = [self.config.command] + (self.config.args or [])

        # Build environment
        env = None
        if self.config.env:
            import os

            env = os.environ.copy()
            env.update(self.config.env)

        try:
            self._process = await asyncio.create_subprocess_exec(
                *cmd_args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
        except FileNotFoundError as e:
            raise ConnectionError(f"Failed to spawn MCP server: {e}") from e
        except Exception as e:
            raise ConnectionError(f"Failed to spawn MCP server: {e}") from e

        # Send initialize request
        init_request = create_initialize_request(
            client_name="mcp-server-langgraph",
            client_version="1.0.0",
        )

        await self._send_request_stdio(init_request)

        # Wait for initialize response
        response = await self._read_response_stdio()

        if not response.is_success:
            error_msg = response.error.get("message", "Unknown error") if response.error else "Unknown error"
            if self._process:
                self._process.terminate()
                self._process = None
            raise ConnectionError(f"Initialize failed: {error_msg}")

        # Parse server info
        if response.result is None:
            raise ConnectionError("Initialize succeeded but returned no result")
        self.server_info = parse_initialize_result(response.result)

        logger.info(
            "MCP server initialized",
            extra={
                "server_name": self.server_info.server_name,
                "protocol_version": self.server_info.protocol_version,
                "has_tools": self.server_info.has_tools,
            },
        )

        # Send initialized notification
        initialized_notification = create_initialized_notification()
        await self._send_notification_stdio(initialized_notification)

    async def _send_request_stdio(self, request: MCPRequest) -> None:
        """Send a JSON-RPC request via STDIO."""
        if not self._process or not self._process.stdin:
            raise ConnectionError("Not connected")

        message = request.to_dict()
        framed = frame_stdio_message(message)

        self._process.stdin.write(framed.encode())
        await self._process.stdin.drain()

    async def _send_notification_stdio(self, notification: Any) -> None:
        """Send a JSON-RPC notification via STDIO."""
        if not self._process or not self._process.stdin:
            raise ConnectionError("Not connected")

        message = notification.to_dict()
        framed = frame_stdio_message(message)

        self._process.stdin.write(framed.encode())
        await self._process.stdin.drain()

    async def _read_response_stdio(self) -> MCPResponse:
        """Read a JSON-RPC response from STDIO."""
        if not self._process or not self._process.stdout:
            raise ConnectionError("Not connected")

        line = await self._process.stdout.readline()
        if not line:
            raise ConnectionError("Server closed connection")

        data = json.loads(line.decode())
        return MCPResponse.from_dict(data)

    async def _connect_http(self) -> None:
        """Establish HTTP connection via Streamable HTTP transport.

        This method:
        1. Creates an HTTP client session
        2. Sends the initialize request via HTTP POST
        3. Parses the initialize response
        4. Stores session ID from response headers
        5. Sends initialized notification

        Raises:
            ConnectionError: If HTTP request fails or handshake fails
        """
        import aiohttp

        if not self.config.url:
            raise ValueError("HTTP transport requires 'url' in config")

        # Create HTTP client session
        self._http_client = aiohttp.ClientSession()

        try:
            # Create initialize request
            init_request = create_initialize_request(
                client_name="mcp-server-langgraph",
                client_version="1.0.0",
            )

            # Get MCP headers (no session ID yet for initial request)
            headers = get_mcp_headers(session_id=None)

            # Send initialize request via HTTP POST
            async with self._http_client.post(
                self.config.url,
                json=init_request.to_dict(),
                headers=headers,
            ) as resp:
                # Check HTTP status
                if resp.status >= 400:
                    error_text = await resp.text()
                    raise ConnectionError(f"HTTP error {resp.status}: {error_text}")

                # Parse JSON-RPC response
                data = await resp.json()
                response = MCPResponse.from_dict(data)

                if not response.is_success:
                    error_msg = response.error.get("message", "Unknown error") if response.error else "Unknown error"
                    raise ConnectionError(f"Initialize failed: {error_msg}")

                # Store session ID from response headers if provided
                if "MCP-Session-Id" in resp.headers:
                    self._session_id = resp.headers["MCP-Session-Id"]

                # Parse server info
                if response.result is None:
                    raise ConnectionError("Initialize succeeded but returned no result")
                self.server_info = parse_initialize_result(response.result)

            logger.info(
                "MCP HTTP server initialized",
                extra={
                    "server_name": self.server_info.server_name,
                    "protocol_version": self.server_info.protocol_version,
                    "has_tools": self.server_info.has_tools,
                    "session_id": self._session_id,
                },
            )

            # Send initialized notification
            initialized_notification = create_initialized_notification()
            headers = get_mcp_headers(session_id=self._session_id)

            async with self._http_client.post(
                self.config.url,
                json=initialized_notification.to_dict(),
                headers=headers,
            ) as resp:
                # Notifications don't require a response, just check for errors
                if resp.status >= 400:
                    logger.warning(
                        "Failed to send initialized notification",
                        extra={"status": resp.status},
                    )

        except aiohttp.ClientError as e:
            await self._http_client.close()
            self._http_client = None
            raise ConnectionError(f"HTTP connection error: {e}") from e

    async def _connect_sse(self) -> None:
        """Establish SSE connection."""
        if not self.config.url:
            raise ValueError("SSE transport requires 'url' in config")
        # Implementation placeholder
        pass

    async def _connect_websocket(self) -> None:
        """Establish WebSocket connection."""
        if not self.config.url:
            raise ValueError("WebSocket transport requires 'url' in config")
        # Implementation placeholder
        pass

    async def disconnect(self) -> None:
        """Close connection to MCP server."""
        if not self._connected:
            return

        logger.info("Disconnecting from MCP server", extra={"server_name": self.config.name})

        if self.transport_type == MCPTransportType.STDIO and self._process:
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except TimeoutError:
                self._process.kill()
            self._process = None

        if self.transport_type == MCPTransportType.HTTP and self._http_client:
            await self._http_client.close()
            self._http_client = None

        self._connected = False
        self._tools = []
        self.server_info = None
        self._session_id = None

        logger.info("Disconnected from MCP server", extra={"server_name": self.config.name})

    async def list_tools(self) -> list[dict[str, Any]]:
        """Get available tools from the server.

        Returns:
            List of tool definitions as dictionaries with:
                - name: Tool name
                - description: Tool description
                - inputSchema: JSON Schema for parameters

        Raises:
            ConnectionError: If not connected
        """
        if not self._connected:
            raise ConnectionError("Not connected to MCP server")

        if self.transport_type == MCPTransportType.STDIO:
            return await self._list_tools_stdio()
        elif self.transport_type == MCPTransportType.HTTP:
            return await self._list_tools_http()

        # For other transports, return cached tools
        return self._tools

    async def _list_tools_stdio(self) -> list[dict[str, Any]]:
        """List tools via STDIO transport."""
        request = create_tools_list_request(cursor=None)
        await self._send_request_stdio(request)

        response = await self._read_response_stdio()
        if not response.is_success:
            error_msg = response.error.get("message", "Unknown error") if response.error else "Unknown error"
            raise ConnectionError(f"tools/list failed: {error_msg}")

        if response.result is None:
            raise ConnectionError("tools/list succeeded but returned no result")
        tools, _next_cursor = parse_tools_list_result(response.result)
        self._tools = tools
        return tools

    async def _list_tools_http(self) -> list[dict[str, Any]]:
        """List tools via HTTP transport."""
        if not self._http_client:
            raise ConnectionError("HTTP client not initialized")

        request = create_tools_list_request(cursor=None)
        headers = get_mcp_headers(session_id=self._session_id)

        async with self._http_client.post(
            self.config.url,
            json=request.to_dict(),
            headers=headers,
        ) as resp:
            if resp.status >= 400:
                error_text = await resp.text()
                raise ConnectionError(f"HTTP error {resp.status}: {error_text}")

            data = await resp.json()
            response = MCPResponse.from_dict(data)

            if not response.is_success:
                error_msg = response.error.get("message", "Unknown error") if response.error else "Unknown error"
                raise ConnectionError(f"tools/list failed: {error_msg}")

            if response.result is None:
                raise ConnectionError("tools/list succeeded but returned no result")
            tools, _next_cursor = parse_tools_list_result(response.result)
            self._tools = tools
            return tools

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> Any:
        """Execute a tool on this server.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Tool execution result with:
                - content: List of content items
                - isError: Boolean indicating if tool execution failed

        Raises:
            ConnectionError: If not connected
            ValueError: If tool not found
        """
        if not self._connected:
            raise ConnectionError("Not connected to MCP server")

        logger.info(
            "Calling MCP tool",
            extra={
                "server_name": self.config.name,
                "tool_name": name,
            },
        )

        if self.transport_type == MCPTransportType.STDIO:
            return await self._call_tool_stdio(name, arguments)
        elif self.transport_type == MCPTransportType.HTTP:
            return await self._call_tool_http(name, arguments)

        # Placeholder for other transports
        return {"content": [], "isError": False}

    async def _call_tool_stdio(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call a tool via STDIO transport."""
        request = create_tools_call_request(name=name, arguments=arguments)
        await self._send_request_stdio(request)

        response = await self._read_response_stdio()
        if not response.is_success:
            error_msg = response.error.get("message", "Unknown error") if response.error else "Unknown error"
            raise ConnectionError(f"tools/call failed: {error_msg}")

        if response.result is None:
            raise ConnectionError("tools/call succeeded but returned no result")
        content, is_error = parse_tools_call_result(response.result)
        return {"content": content, "isError": is_error}

    async def _call_tool_http(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call a tool via HTTP transport."""
        if not self._http_client:
            raise ConnectionError("HTTP client not initialized")

        request = create_tools_call_request(name=name, arguments=arguments)
        headers = get_mcp_headers(session_id=self._session_id)

        async with self._http_client.post(
            self.config.url,
            json=request.to_dict(),
            headers=headers,
        ) as resp:
            if resp.status >= 400:
                error_text = await resp.text()
                raise ConnectionError(f"HTTP error {resp.status}: {error_text}")

            data = await resp.json()
            response = MCPResponse.from_dict(data)

            if not response.is_success:
                error_msg = response.error.get("message", "Unknown error") if response.error else "Unknown error"
                raise ConnectionError(f"tools/call failed: {error_msg}")

            if response.result is None:
                raise ConnectionError("tools/call succeeded but returned no result")
            content, is_error = parse_tools_call_result(response.result)
            return {"content": content, "isError": is_error}

    @property
    def is_connected(self) -> bool:
        """Check if connected to the server."""
        return self._connected

    # =========================================================================
    # Resources Methods (MCP 2025-11-25)
    # =========================================================================

    async def list_resources(self) -> list[dict[str, Any]]:
        """Get available resources from the server.

        Returns:
            List of resource definitions as dictionaries with:
                - uri: Resource URI
                - name: Resource name
                - description: Optional description
                - mimeType: Optional MIME type

        Raises:
            ConnectionError: If not connected
        """
        if not self._connected:
            raise ConnectionError("Not connected to MCP server")

        if self.transport_type == MCPTransportType.STDIO:
            return await self._list_resources_stdio()
        elif self.transport_type == MCPTransportType.HTTP:
            return await self._list_resources_http()

        # For other transports, return empty list
        return []

    async def _list_resources_stdio(self) -> list[dict[str, Any]]:
        """List resources via STDIO transport."""
        request = create_resources_list_request(cursor=None)
        await self._send_request_stdio(request)

        response = await self._read_response_stdio()
        if not response.is_success:
            error_msg = response.error.get("message", "Unknown error") if response.error else "Unknown error"
            raise ConnectionError(f"resources/list failed: {error_msg}")

        if response.result is None:
            raise ConnectionError("resources/list succeeded but returned no result")
        resources, _next_cursor = parse_resources_list_result(response.result)
        return resources

    async def _list_resources_http(self) -> list[dict[str, Any]]:
        """List resources via HTTP transport."""
        if not self._http_client:
            raise ConnectionError("HTTP client not initialized")

        request = create_resources_list_request(cursor=None)
        headers = get_mcp_headers(session_id=self._session_id)

        async with self._http_client.post(
            self.config.url,
            json=request.to_dict(),
            headers=headers,
        ) as resp:
            if resp.status >= 400:
                error_text = await resp.text()
                raise ConnectionError(f"HTTP error {resp.status}: {error_text}")

            data = await resp.json()
            response = MCPResponse.from_dict(data)

            if not response.is_success:
                error_msg = response.error.get("message", "Unknown error") if response.error else "Unknown error"
                raise ConnectionError(f"resources/list failed: {error_msg}")

            if response.result is None:
                raise ConnectionError("resources/list succeeded but returned no result")
            resources, _next_cursor = parse_resources_list_result(response.result)
            return resources

    async def _send_request_http(
        self,
        request: MCPRequest,
    ) -> dict[str, Any]:
        """Send an HTTP request and return the result.

        This is a general-purpose method for sending MCP requests via HTTP.
        """
        if not self._http_client:
            raise ConnectionError("HTTP client not initialized")

        headers = get_mcp_headers(session_id=self._session_id)

        async with self._http_client.post(
            self.config.url,
            json=request.to_dict(),
            headers=headers,
        ) as resp:
            if resp.status >= 400:
                error_text = await resp.text()
                raise ConnectionError(f"HTTP error {resp.status}: {error_text}")

            data = await resp.json()
            response = MCPResponse.from_dict(data)

            if not response.is_success:
                error_msg = response.error.get("message", "Unknown error") if response.error else "Unknown error"
                raise ConnectionError(f"Request failed: {error_msg}")

            if response.result is None:
                raise ConnectionError("Request succeeded but returned no result")
            return response.result

    # =========================================================================
    # Prompts Methods (MCP 2025-11-25)
    # =========================================================================

    async def list_prompts(self) -> list[dict[str, Any]]:
        """Get available prompts from the server.

        Returns:
            List of prompt definitions as dictionaries with:
                - name: Prompt name
                - description: Optional description
                - arguments: List of argument definitions

        Raises:
            ConnectionError: If not connected
        """
        if not self._connected:
            raise ConnectionError("Not connected to MCP server")

        if self.transport_type == MCPTransportType.STDIO:
            return await self._list_prompts_stdio()
        elif self.transport_type == MCPTransportType.HTTP:
            return await self._list_prompts_http()

        # For other transports, return empty list
        return []

    async def _list_prompts_stdio(self) -> list[dict[str, Any]]:
        """List prompts via STDIO transport."""
        request = create_prompts_list_request(cursor=None)
        await self._send_request_stdio(request)

        response = await self._read_response_stdio()
        if not response.is_success:
            error_msg = response.error.get("message", "Unknown error") if response.error else "Unknown error"
            raise ConnectionError(f"prompts/list failed: {error_msg}")

        if response.result is None:
            raise ConnectionError("prompts/list succeeded but returned no result")
        prompts, _next_cursor = parse_prompts_list_result(response.result)
        return prompts

    async def _list_prompts_http(self) -> list[dict[str, Any]]:
        """List prompts via HTTP transport."""
        if not self._http_client:
            raise ConnectionError("HTTP client not initialized")

        request = create_prompts_list_request(cursor=None)
        headers = get_mcp_headers(session_id=self._session_id)

        async with self._http_client.post(
            self.config.url,
            json=request.to_dict(),
            headers=headers,
        ) as resp:
            if resp.status >= 400:
                error_text = await resp.text()
                raise ConnectionError(f"HTTP error {resp.status}: {error_text}")

            data = await resp.json()
            response = MCPResponse.from_dict(data)

            if not response.is_success:
                error_msg = response.error.get("message", "Unknown error") if response.error else "Unknown error"
                raise ConnectionError(f"prompts/list failed: {error_msg}")

            if response.result is None:
                raise ConnectionError("prompts/list succeeded but returned no result")
            prompts, _next_cursor = parse_prompts_list_result(response.result)
            return prompts
