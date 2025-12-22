"""
Sandbox Context

Provides execution context for sandboxed code with access to
MCP tools via the tool bridge.

Usage:
    from mcp_server_langgraph.execution.sandbox_context import SandboxContext

    context = SandboxContext()
    result = await context.call_mcp_tool("search", {"query": "..."})
"""

from __future__ import annotations

from typing import Any

from mcp_server_langgraph.execution.tool_bridge import ToolBridge, ToolResult


class SandboxContext:
    """Execution context for sandboxed code.

    Provides a controlled environment for executing skill scripts
    with access to MCP tools via the tool bridge.
    """

    def __init__(
        self,
        tool_bridge: ToolBridge | None = None,
    ) -> None:
        """Initialize sandbox context.

        Args:
            tool_bridge: Optional pre-configured tool bridge
        """
        self.tool_bridge = tool_bridge or ToolBridge()
        self._environment: dict[str, str] = {}
        self._working_directory: str | None = None

    def set_environment(self, env: dict[str, str]) -> None:
        """Set environment variables for the sandbox.

        Args:
            env: Dictionary of environment variables
        """
        self._environment = dict(env)

    def get_environment(self) -> dict[str, str]:
        """Get environment variables.

        Returns:
            Copy of environment dictionary
        """
        return dict(self._environment)

    def set_working_directory(self, path: str) -> None:
        """Set working directory for the sandbox.

        Args:
            path: Working directory path
        """
        self._working_directory = path

    def get_working_directory(self) -> str | None:
        """Get working directory.

        Returns:
            Working directory path or None
        """
        return self._working_directory

    async def call_mcp_tool(
        self,
        tool_name: str,
        args: dict[str, Any],
    ) -> ToolResult:
        """Call an MCP tool from sandbox code.

        This is the primary interface for sandbox code to
        invoke MCP tools programmatically.

        Args:
            tool_name: Name of the tool to call
            args: Arguments to pass to the tool

        Returns:
            ToolResult with success/failure and output
        """
        return await self.tool_bridge.call_tool(tool_name, args)

    async def gather_mcp_tools(
        self,
        *calls: tuple[str, dict[str, Any]],
    ) -> list[ToolResult]:
        """Execute multiple MCP tool calls in parallel.

        Args:
            *calls: Tuples of (tool_name, args)

        Returns:
            List of ToolResult in same order as calls
        """
        return await self.tool_bridge.gather_tools(*calls)

    def list_available_tools(self) -> list[str]:
        """List available tools in this context.

        Returns:
            List of available tool names
        """
        return self.tool_bridge.list_tools()
