"""
Tool Bridge

Enables programmatic tool calling from sandboxed code execution.
Sandbox code can invoke MCP tools without returning to model context,
reducing token usage for intermediate results.

Usage:
    from mcp_server_langgraph.execution.tool_bridge import ToolBridge

    bridge = ToolBridge()
    bridge.register_tool("search", search_function)
    result = await bridge.call_tool("search", {"query": "..."})
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Callable, Coroutine

from pydantic import BaseModel, Field

from mcp_server_langgraph.core.feature_flags import feature_gated


class ToolResult(BaseModel):
    """Result of a tool invocation."""

    success: bool = Field(description="Whether the tool execution succeeded")
    tool_name: str = Field(description="Name of the tool that was called")
    output: str | None = Field(default=None, description="Tool output if successful")
    error: str | None = Field(default=None, description="Error message if failed")
    duration_ms: float = Field(default=0.0, description="Execution duration in ms")


# Type alias for async tool functions
ToolFunction = Callable[..., Coroutine[Any, Any, Any]]


class ToolBridge:
    """Bridge for programmatic tool calling from sandbox code.

    Enables sandbox code to invoke MCP tools directly without
    returning intermediate results to the model context.
    """

    def __init__(self) -> None:
        """Initialize the tool bridge."""
        self.registered_tools: dict[str, ToolFunction] = {}

    def register_tool(self, name: str, func: ToolFunction) -> None:
        """Register a tool for sandbox invocation.

        Args:
            name: Tool name for invocation
            func: Async function implementing the tool
        """
        self.registered_tools[name] = func

    def unregister_tool(self, name: str) -> None:
        """Unregister a tool.

        Args:
            name: Tool name to unregister
        """
        self.registered_tools.pop(name, None)

    @feature_gated("enable_programmatic_tools", "Programmatic Tools")
    async def call_tool(
        self,
        tool_name: str,
        args: dict[str, Any],
    ) -> ToolResult:
        """Call a registered tool.

        Args:
            tool_name: Name of the tool to call
            args: Arguments to pass to the tool

        Returns:
            ToolResult with success/failure and output

        Raises:
            FeatureDisabledError: If programmatic tools is disabled
        """
        start_time = time.perf_counter()

        # Check if tool exists
        if tool_name not in self.registered_tools:
            return ToolResult(
                success=False,
                tool_name=tool_name,
                error=f"Tool '{tool_name}' not found",
            )

        tool_func = self.registered_tools[tool_name]

        try:
            result = await tool_func(**args)
            duration_ms = (time.perf_counter() - start_time) * 1000

            return ToolResult(
                success=True,
                tool_name=tool_name,
                output=str(result),
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000

            return ToolResult(
                success=False,
                tool_name=tool_name,
                error=str(e),
                duration_ms=duration_ms,
            )

    async def gather_tools(
        self,
        *calls: tuple[str, dict[str, Any]],
    ) -> list[ToolResult]:
        """Execute multiple tool calls in parallel.

        Args:
            *calls: Tuples of (tool_name, args)

        Returns:
            List of ToolResult in same order as calls
        """
        tasks = [self.call_tool(tool_name, args) for tool_name, args in calls]
        return await asyncio.gather(*tasks)

    def list_tools(self) -> list[str]:
        """List all registered tool names.

        Returns:
            List of registered tool names
        """
        return list(self.registered_tools.keys())
