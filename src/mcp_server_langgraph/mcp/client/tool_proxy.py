"""
MCP Tool Proxy for wrapping external MCP tools as LangChain BaseTool.

This module enables external MCP server tools to be used seamlessly
with LangChain/LangGraph agents by wrapping them as BaseTool instances.
"""

import asyncio
from typing import TYPE_CHECKING, Any

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, create_model

from mcp_server_langgraph.mcp.client.tool_registry import MCPToolDefinition, MCPToolRegistry
from mcp_server_langgraph.observability.telemetry import logger

if TYPE_CHECKING:
    from mcp_server_langgraph.mcp.client.executor import MCPExecutor


def _json_type_to_python(json_type: str) -> type:
    """Convert JSON Schema type to Python type."""
    type_map = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "array": list,
        "object": dict,
    }
    return type_map.get(json_type, Any)


def _create_args_schema(
    tool_name: str,
    input_schema: dict[str, Any],
) -> type[BaseModel]:
    """Create a Pydantic model from JSON Schema.

    Args:
        tool_name: Name of the tool (used for model class name)
        input_schema: JSON Schema for the tool's input

    Returns:
        A Pydantic model class
    """
    properties = input_schema.get("properties", {})
    required = set(input_schema.get("required", []))

    # Build field definitions
    field_definitions: dict[str, Any] = {}

    for prop_name, prop_schema in properties.items():
        prop_type = _json_type_to_python(prop_schema.get("type", "string"))
        prop_description = prop_schema.get("description", "")
        is_required = prop_name in required

        if is_required:
            field_definitions[prop_name] = (
                prop_type,
                Field(description=prop_description),
            )
        else:
            field_definitions[prop_name] = (
                prop_type | None,
                Field(default=None, description=prop_description),
            )

    # Handle empty schema - use valid field name (no leading underscore)
    if not field_definitions:
        field_definitions["empty_placeholder"] = (str | None, Field(default=None, description="No arguments"))

    # Create model class name
    class_name = f"{tool_name.title().replace('_', '')}Args"

    return create_model(class_name, **field_definitions)


class MCPToolProxy(BaseTool):
    """Proxy that wraps an external MCP tool as a LangChain BaseTool.

    This allows external MCP tools to be used with LangChain/LangGraph
    agents exactly like built-in tools.

    Example:
        tool_def = MCPToolDefinition(
            server_name="playwright",
            name="screenshot",
            description="Take a screenshot",
            input_schema={"type": "object", "properties": {...}},
        )

        executor = MCPExecutor(registry)
        proxy = MCPToolProxy.from_definition(tool_def, executor)

        # Use with LangChain agent
        result = await proxy.ainvoke({"path": "/tmp/screenshot.png"})
    """

    name: str = Field(description="Tool name in LangChain format")
    description: str = Field(description="Tool description")
    mcp_server: str = Field(description="Source MCP server name")
    mcp_tool_name: str = Field(description="Original tool name on server")
    args_schema: type[BaseModel] = Field(description="Pydantic model for arguments")
    _executor: Any = None  # Store executor without Pydantic validation

    class Config:
        """Pydantic config."""

        arbitrary_types_allowed = True

    def __init__(
        self,
        name: str,
        description: str,
        mcp_server: str,
        mcp_tool_name: str,
        args_schema: type[BaseModel],
        executor: Any,
        **kwargs: Any,
    ):
        """Initialize the proxy.

        Args:
            name: LangChain tool name
            description: Tool description
            mcp_server: MCP server name
            mcp_tool_name: Original tool name
            args_schema: Pydantic model for arguments
            executor: MCPExecutor instance
        """
        super().__init__(
            name=name,
            description=description,
            mcp_server=mcp_server,
            mcp_tool_name=mcp_tool_name,
            args_schema=args_schema,
            **kwargs,
        )
        self._executor = executor

    @classmethod
    def from_definition(
        cls,
        tool_def: MCPToolDefinition,
        executor: Any,
    ) -> "MCPToolProxy":
        """Create a proxy from an MCPToolDefinition.

        Args:
            tool_def: The tool definition from the registry
            executor: MCPExecutor for making tool calls

        Returns:
            MCPToolProxy instance
        """
        # Create LangChain-compatible name (replace : with _)
        lc_name = f"{tool_def.server_name}_{tool_def.name}"

        # Create args schema from input_schema
        args_schema = _create_args_schema(lc_name, tool_def.input_schema)

        return cls(
            name=lc_name,
            description=tool_def.description,
            mcp_server=tool_def.server_name,
            mcp_tool_name=tool_def.name,
            args_schema=args_schema,
            executor=executor,
        )

    async def _arun(self, **kwargs: Any) -> str:
        """Execute the tool asynchronously via MCP protocol.

        Args:
            **kwargs: Tool arguments

        Returns:
            Tool execution result as string
        """
        # Remove any internal/placeholder fields from kwargs
        arguments = {
            k: v for k, v in kwargs.items()
            if not k.startswith("_") and k != "empty_placeholder" and v is not None
        }

        logger.info(
            "Executing MCP tool via proxy",
            extra={
                "server": self.mcp_server,
                "tool": self.mcp_tool_name,
            },
        )

        try:
            result = await self._executor.call_tool(
                server=self.mcp_server,
                tool=self.mcp_tool_name,
                arguments=arguments,
            )

            # Convert result to string for LangChain compatibility
            if isinstance(result, str):
                return result
            elif isinstance(result, dict):
                import json
                return json.dumps(result, indent=2)
            else:
                return str(result)

        except asyncio.TimeoutError:
            error_msg = f"Error: Tool '{self.mcp_tool_name}' timed out on server '{self.mcp_server}'"
            logger.warning(error_msg)
            return error_msg

        except ConnectionError as e:
            error_msg = f"Error: Connection to server '{self.mcp_server}' failed: {e}"
            logger.error(error_msg)
            return error_msg

        except Exception as e:
            error_msg = f"Error executing tool '{self.mcp_tool_name}': {e}"
            logger.error(error_msg, exc_info=True)
            return error_msg

    def _run(self, **kwargs: Any) -> str:
        """Execute the tool synchronously (fallback).

        Note: Synchronous execution is not recommended for MCP tools
        as they typically involve network I/O.

        Args:
            **kwargs: Tool arguments

        Returns:
            Tool execution result as string
        """
        # Get or create event loop
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self._arun(**kwargs))


def create_proxies_from_registry(
    registry: MCPToolRegistry,
    executor: Any,
    server_name: str | None = None,
) -> list[MCPToolProxy]:
    """Create MCPToolProxy instances for all tools in a registry.

    Args:
        registry: The tool registry containing tool definitions
        executor: MCPExecutor for making tool calls
        server_name: If provided, only create proxies for this server

    Returns:
        List of MCPToolProxy instances
    """
    tools = registry.get_tools(server_name=server_name)

    proxies = [MCPToolProxy.from_definition(tool, executor) for tool in tools]

    logger.info(
        "Created MCP tool proxies",
        extra={
            "count": len(proxies),
            "server_filter": server_name,
        },
    )

    return proxies
