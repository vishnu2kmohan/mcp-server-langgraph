"""
MCP Executor for routing tool calls to external MCP servers.

This module provides the MCPExecutor class that routes tool calls
to the appropriate external MCP server based on the tool registry.
"""

import asyncio
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

from mcp_server_langgraph.mcp.client.tool_registry import MCPToolRegistry
from mcp_server_langgraph.observability.telemetry import logger

if TYPE_CHECKING:
    from mcp_server_langgraph.mcp.client.tool_registry import MCPClientSessionProtocol


class AuthProvider(Protocol):
    """Protocol for authentication providers."""

    async def get_credentials(self, server_name: str) -> dict[str, Any]:
        """Get credentials for a specific server."""
        ...


@dataclass
class MCPToolCall:
    """Represents a single tool call request."""

    server: str
    """Name of the MCP server to call."""

    tool: str
    """Name of the tool to execute."""

    arguments: dict[str, Any]
    """Arguments to pass to the tool."""


@dataclass
class MCPToolResult:
    """Result of a tool call."""

    server: str
    """Name of the MCP server that was called."""

    tool: str
    """Name of the tool that was executed."""

    success: bool
    """Whether the tool call succeeded."""

    result: Any | None
    """Tool execution result (if successful)."""

    error: str | None
    """Error message (if failed)."""

    duration_ms: float
    """Execution duration in milliseconds."""


class MCPExecutor:
    """Execute tool calls on external MCP servers.

    This class routes tool calls to the appropriate MCP server
    based on the tool registry and handles timeouts, retries,
    and error handling.

    Example:
        registry = MCPToolRegistry()
        await registry.register_server(config)

        executor = MCPExecutor(registry)
        result = await executor.call_tool(
            server="playwright",
            tool="screenshot",
            arguments={"url": "https://example.com"}
        )
    """

    def __init__(
        self,
        registry: MCPToolRegistry,
        auth_provider: AuthProvider | None = None,
    ):
        """Initialize the executor.

        Args:
            registry: The tool registry containing server sessions
            auth_provider: Optional auth provider for server credentials
        """
        self.registry = registry
        self.auth_provider = auth_provider

    async def _ensure_connected(
        self, session: "MCPClientSessionProtocol", server_name: str
    ) -> None:
        """Ensure the session is connected, reconnecting if necessary."""
        if not session.is_connected:
            logger.info(
                "Reconnecting to MCP server",
                extra={"server_name": server_name},
            )
            await session.connect()

    async def call_tool(
        self,
        server: str,
        tool: str,
        arguments: dict[str, Any],
        timeout: float | None = None,
    ) -> Any:
        """Execute a tool on the specified MCP server.

        Args:
            server: Name of the MCP server
            tool: Name of the tool to execute
            arguments: Tool arguments
            timeout: Optional timeout in seconds (uses server default if not specified)

        Returns:
            Tool execution result

        Raises:
            KeyError: If server is not registered
            asyncio.TimeoutError: If execution times out
            ConnectionError: If unable to connect to server
        """
        session = self.registry.get_session(server)
        if session is None:
            raise KeyError(f"Server '{server}' not registered")

        # Ensure connected
        await self._ensure_connected(session, server)

        # Get timeout from server config if not specified
        if timeout is None:
            config = self.registry._server_configs.get(server)
            timeout = config.timeout if config else 30.0

        logger.info(
            "Executing tool via MCP executor",
            extra={
                "server": server,
                "tool": tool,
                "timeout": timeout,
            },
        )

        try:
            result = await asyncio.wait_for(
                session.call_tool(tool, arguments),
                timeout=timeout,
            )
            return result
        except asyncio.TimeoutError:
            logger.warning(
                "Tool execution timed out",
                extra={"server": server, "tool": tool, "timeout": timeout},
            )
            raise

    async def batch_call(
        self,
        calls: list[MCPToolCall],
        timeout: float | None = None,
    ) -> list[MCPToolResult]:
        """Execute multiple tool calls in parallel.

        Args:
            calls: List of tool calls to execute
            timeout: Optional timeout per call

        Returns:
            List of results in the same order as calls
        """

        async def execute_one(call: MCPToolCall) -> MCPToolResult:
            """Execute a single call and wrap the result."""
            start_time = time.perf_counter()
            try:
                result = await self.call_tool(
                    server=call.server,
                    tool=call.tool,
                    arguments=call.arguments,
                    timeout=timeout,
                )
                duration_ms = (time.perf_counter() - start_time) * 1000
                return MCPToolResult(
                    server=call.server,
                    tool=call.tool,
                    success=True,
                    result=result,
                    error=None,
                    duration_ms=duration_ms,
                )
            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000
                return MCPToolResult(
                    server=call.server,
                    tool=call.tool,
                    success=False,
                    result=None,
                    error=str(e),
                    duration_ms=duration_ms,
                )

        # Execute all calls in parallel
        tasks = [execute_one(call) for call in calls]
        results = await asyncio.gather(*tasks)

        logger.info(
            "Batch tool execution complete",
            extra={
                "total_calls": len(calls),
                "successful": sum(1 for r in results if r.success),
                "failed": sum(1 for r in results if not r.success),
            },
        )

        return list(results)
