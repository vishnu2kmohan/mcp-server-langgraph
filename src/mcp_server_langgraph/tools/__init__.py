"""
Tool catalog for LangGraph agent

Provides a registry of tools that the agent can execute.
Tools are defined using LangChain's @tool decorator for automatic schema generation.
"""

from typing import Any

from langchain_core.tools import BaseTool

from mcp_server_langgraph.core.config import settings
from mcp_server_langgraph.tools.calculator_tools import add, calculator, divide, multiply, subtract
from mcp_server_langgraph.tools.filesystem_tools import list_directory, read_file, search_files
from mcp_server_langgraph.tools.search_tools import search_knowledge_base, web_search

# Code execution tools (conditional on configuration)
CODE_EXECUTION_TOOLS = []
if settings.enable_code_execution:
    try:
        from mcp_server_langgraph.tools.code_execution_tools import execute_python

        CODE_EXECUTION_TOOLS = [execute_python]
    except ImportError:
        # Code execution dependencies not installed
        pass

# Tool registry - all available tools for the agent
ALL_TOOLS: list[BaseTool] = [
    # Calculator tools
    calculator,
    add,
    subtract,
    multiply,
    divide,
    # Search tools
    search_knowledge_base,
    web_search,
    # Filesystem tools (read-only for safety)
    read_file,
    list_directory,
    search_files,
    # Code execution tools (conditional)
    *CODE_EXECUTION_TOOLS,
]

# Tool groups for conditional loading
CALCULATOR_TOOLS = [calculator, add, subtract, multiply, divide]
SEARCH_TOOLS = [search_knowledge_base, web_search]
FILESYSTEM_TOOLS = [read_file, list_directory, search_files]


def get_tools(categories: list[str] | None = None) -> list[BaseTool]:
    """
    Get tools by category.

    Args:
        categories: List of categories to include (None = all tools)
                   Options: "calculator", "search", "filesystem"

    Returns:
        List of tools matching the categories
    """
    if categories is None:
        return ALL_TOOLS

    tools: list[BaseTool] = []
    category_map = {
        "calculator": CALCULATOR_TOOLS,
        "search": SEARCH_TOOLS,
        "filesystem": FILESYSTEM_TOOLS,
    }

    for category in categories:
        if category in category_map:
            tools.extend(category_map[category])

    return tools


def get_tool_by_name(name: str) -> BaseTool | None:
    """
    Get a specific tool by name.

    Args:
        name: Tool name

    Returns:
        Tool instance or None if not found
    """
    for tool in ALL_TOOLS:
        if tool.name == name:
            return tool
    return None


__all__ = [
    "ALL_TOOLS",
    "CALCULATOR_TOOLS",
    "SEARCH_TOOLS",
    "FILESYSTEM_TOOLS",
    "get_tools",
    "get_tool_by_name",
    "calculator",
    "add",
    "subtract",
    "multiply",
    "divide",
    "search_knowledge_base",
    "web_search",
    "read_file",
    "list_directory",
    "search_files",
]
