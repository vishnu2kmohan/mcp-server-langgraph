"""
In-Process Tool Server

Provides in-process tool execution without subprocess overhead.

Usage:
    from mcp_server_langgraph.sdk.tools import InProcessToolServer

    server = InProcessToolServer(name="langgraph-tools")
    server.register_tool("think", think_tool, {"thought": str})
    result = await server.call_tool("think", {"thought": "..."})
"""

from __future__ import annotations

from typing import Any, Callable, Awaitable

from pydantic import BaseModel, Field


class ToolDefinition(BaseModel):
    """Definition of a registered tool."""

    name: str = Field(description="Tool name")
    description: str = Field(default="", description="Tool description")
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Tool parameter schema",
    )


class InProcessToolServer:
    """In-process MCP tool server.

    Provides fast tool execution without subprocess overhead,
    ideal for SDK-integrated tools.
    """

    def __init__(
        self,
        name: str = "langgraph-tools",
        version: str = "1.0.0",
    ) -> None:
        """Initialize tool server.

        Args:
            name: Server name
            version: Server version
        """
        self.name = name
        self.version = version
        self._tools: dict[str, Callable[..., Awaitable[Any]]] = {}
        self._definitions: dict[str, ToolDefinition] = {}

    def register_tool(
        self,
        name: str,
        handler: Callable[..., Awaitable[Any]],
        parameters: dict[str, Any],
        description: str = "",
    ) -> None:
        """Register a tool.

        Args:
            name: Tool name
            handler: Async function to handle tool calls
            parameters: Parameter schema
            description: Tool description
        """
        self._tools[name] = handler
        self._definitions[name] = ToolDefinition(
            name=name,
            description=description,
            parameters=parameters,
        )

    def list_tools(self) -> list[str]:
        """List registered tool names.

        Returns:
            List of tool names
        """
        return list(self._tools.keys())

    def get_tool_definitions(self) -> list[ToolDefinition]:
        """Get all tool definitions.

        Returns:
            List of tool definitions
        """
        return list(self._definitions.values())

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> Any:
        """Call a registered tool.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Tool result

        Raises:
            KeyError: If tool not found
        """
        if name not in self._tools:
            raise KeyError(f"Tool not found: {name}")

        handler = self._tools[name]
        return await handler(**arguments)


# Pre-built tools
async def think_tool(thought: str) -> str:
    """Structured reasoning space without external effects.

    Use this tool to pause and reason during complex tool chains,
    verify policy compliance, or analyze tool outputs before proceeding.

    Args:
        thought: The reasoning to record

    Returns:
        Acknowledgment message
    """
    # No-op tool - just records thought for reasoning
    return f"Recorded thought: {thought[:100]}..."


async def search_tools_tool(query: str, detail: str = "standard") -> str:
    """Search available tools with progressive disclosure.

    Args:
        query: Search query
        detail: Detail level (minimal, standard, full)

    Returns:
        Tool search results
    """
    # Placeholder - would integrate with actual tool registry
    return f"Searched tools for '{query}' with {detail} detail"


# Default in-process server with built-in tools
def create_default_server() -> InProcessToolServer:
    """Create default in-process server with standard tools.

    Returns:
        Configured InProcessToolServer
    """
    server = InProcessToolServer(name="langgraph-sdk", version="1.0.0")

    server.register_tool(
        "think",
        think_tool,
        {"thought": str},
        "Structured reasoning space",
    )

    server.register_tool(
        "search_tools",
        search_tools_tool,
        {"query": str, "detail": str},
        "Search available tools",
    )

    return server
