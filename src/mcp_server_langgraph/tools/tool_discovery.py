"""
Tool discovery for progressive disclosure

Implements search_tools endpoint following Anthropic's MCP best practices
for token-efficient tool discovery.
"""

import logging
from typing import Literal, Optional

from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field

from mcp_server_langgraph.tools import ALL_TOOLS

logger = logging.getLogger(__name__)

DetailLevel = Literal["minimal", "standard", "full"]


class SearchToolsInput(BaseModel):
    """Input schema for search_tools"""

    query: Optional[str] = Field(default=None, description="Search query (keyword or category)")
    category: Optional[str] = Field(
        default=None,
        description="Tool category (calculator, search, filesystem, execution)",
    )
    detail_level: DetailLevel = Field(
        default="minimal",
        description="Level of detail: minimal (name+desc), standard (+params), full (+examples)",
    )


@tool
def search_tools(
    query: Optional[str] = None,
    category: Optional[str] = None,
    detail_level: str = "minimal",
) -> str:
    """
    Search and discover available tools (progressive disclosure for token efficiency).

    Implements Anthropic's best practice for progressive tool discovery, allowing
    agents to query tools by keyword or category rather than loading all tool
    definitions upfront. This can save 98%+ tokens compared to listing all tools.

    Args:
        query: Optional keyword search (searches name and description)
        category: Optional category filter (calculator, search, filesystem, execution)
        detail_level: Level of detail - minimal, standard, or full

    Returns:
        Formatted list of matching tools with requested detail level

    Example:
        >>> search_tools.invoke({"category": "calculator", "detail_level": "minimal"})
        "Found 5 tools:\\n- calculator: Evaluate mathematical expressions\\n..."
    """
    # Get all tools
    tools = ALL_TOOLS

    # Filter by category
    if category:
        category_lower = category.lower()
        if category_lower == "calculator":
            from mcp_server_langgraph.tools import CALCULATOR_TOOLS

            tools = CALCULATOR_TOOLS
        elif category_lower == "search":
            from mcp_server_langgraph.tools import SEARCH_TOOLS

            tools = SEARCH_TOOLS
        elif category_lower == "filesystem":
            from mcp_server_langgraph.tools import FILESYSTEM_TOOLS

            tools = FILESYSTEM_TOOLS
        elif category_lower == "execution":
            from mcp_server_langgraph.tools import CODE_EXECUTION_TOOLS

            tools = CODE_EXECUTION_TOOLS

    # Filter by query
    if query:
        query_lower = query.lower()
        filtered_tools = []
        for tool in tools:
            if query_lower in tool.name.lower() or query_lower in (tool.description or "").lower():
                filtered_tools.append(tool)
        tools = filtered_tools

    if not tools:
        return f"No tools found matching criteria (query={query}, category={category})"

    # Format results based on detail level
    if detail_level == "minimal":
        result = f"Found {len(tools)} tool(s):\n\n"
        for tool in tools:
            result += f"- **{tool.name}**: {tool.description}\n"
        return result

    elif detail_level == "standard":
        result = f"Found {len(tools)} tool(s):\n\n"
        for tool in tools:
            result += f"### {tool.name}\n"
            result += f"{tool.description}\n\n"

            # Add parameter info
            if hasattr(tool, "args_schema") and tool.args_schema:
                schema = tool.args_schema.model_json_schema()
                if "properties" in schema:
                    result += "**Parameters:**\n"
                    for param_name, param_info in schema["properties"].items():
                        param_desc = param_info.get("description", "No description")
                        param_type = param_info.get("type", "any")
                        result += f"- `{param_name}` ({param_type}): {param_desc}\n"
                result += "\n"

        return result

    else:  # full
        result = f"Found {len(tools)} tool(s):\n\n"
        for tool in tools:
            result += f"### {tool.name}\n"
            result += f"{tool.description}\n\n"

            # Add full schema
            if hasattr(tool, "args_schema") and tool.args_schema:
                schema = tool.args_schema.model_json_schema()
                if "properties" in schema:
                    result += "**Parameters:**\n"
                    for param_name, param_info in schema["properties"].items():
                        param_desc = param_info.get("description", "No description")
                        param_type = param_info.get("type", "any")
                        required = param_name in schema.get("required", [])
                        req_str = "required" if required else "optional"
                        result += f"- `{param_name}` ({param_type}, {req_str}): {param_desc}\n"

                    result += "\n**Full Schema:**\n```json\n"
                    import json

                    result += json.dumps(schema, indent=2)
                    result += "\n```\n\n"

        return result
