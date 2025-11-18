"""
Tool discovery for progressive disclosure

Implements search_tools endpoint following Anthropic's MCP best practices
for token-efficient tool discovery.
"""

import json
import logging
from typing import List, Literal, Optional

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


def _filter_tools_by_category(category: str) -> List[BaseTool]:
    """Filter tools by category."""
    category_lower = category.lower()
    if category_lower == "calculator":
        from mcp_server_langgraph.tools import CALCULATOR_TOOLS

        return CALCULATOR_TOOLS
    elif category_lower == "search":
        from mcp_server_langgraph.tools import SEARCH_TOOLS

        return SEARCH_TOOLS
    elif category_lower == "filesystem":
        from mcp_server_langgraph.tools import FILESYSTEM_TOOLS

        return FILESYSTEM_TOOLS
    elif category_lower == "execution":
        from mcp_server_langgraph.tools import CODE_EXECUTION_TOOLS

        return CODE_EXECUTION_TOOLS
    return ALL_TOOLS


def _filter_tools_by_query(tools: List[BaseTool], query: str) -> List[BaseTool]:
    """Filter tools by search query."""
    query_lower = query.lower()
    return [t for t in tools if query_lower in t.name.lower() or query_lower in (t.description or "").lower()]


def _format_tool_minimal(t: BaseTool) -> str:
    """Format tool in minimal mode."""
    return f"- **{t.name}**: {t.description}\n"


def _format_tool_standard(t: BaseTool) -> str:
    """Format tool in standard mode."""
    result = f"### {t.name}\n{t.description}\n\n"

    if hasattr(t, "args_schema") and t.args_schema:
        schema = t.args_schema.model_json_schema()
        if "properties" in schema:
            result += "**Parameters:**\n"
            for param_name, param_info in schema["properties"].items():
                param_desc = param_info.get("description", "No description")
                param_type = param_info.get("type", "any")
                result += f"- `{param_name}` ({param_type}): {param_desc}\n"
        result += "\n"

    return result


def _format_tool_full(t: BaseTool) -> str:
    """Format tool in full mode."""
    result = f"### {t.name}\n{t.description}\n\n"

    if hasattr(t, "args_schema") and t.args_schema:
        schema = t.args_schema.model_json_schema()
        if "properties" in schema:
            result += "**Parameters:**\n"
            for param_name, param_info in schema["properties"].items():
                param_desc = param_info.get("description", "No description")
                param_type = param_info.get("type", "any")
                required = param_name in schema.get("required", [])
                req_str = "required" if required else "optional"
                result += f"- `{param_name}` ({param_type}, {req_str}): {param_desc}\n"

            result += "\n**Full Schema:**\n```json\n"
            result += json.dumps(schema, indent=2)
            result += "\n```\n\n"

    return result


def _format_tool_results(tools: List[BaseTool], detail_level: str) -> str:
    """Format tool results based on detail level."""
    result = f"Found {len(tools)} tool(s):\n\n"

    if detail_level == "minimal":
        for t in tools:
            result += _format_tool_minimal(t)
    elif detail_level == "standard":
        for t in tools:
            result += _format_tool_standard(t)
    else:  # full
        for t in tools:
            result += _format_tool_full(t)

    return result


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
    # Get all tools or filter by category
    tools = _filter_tools_by_category(category) if category else ALL_TOOLS

    # Filter by query if provided
    if query:
        tools = _filter_tools_by_query(tools, query)

    if not tools:
        return f"No tools found matching criteria (query={query}, category={category})"

    # Format and return results
    return _format_tool_results(tools, detail_level)
