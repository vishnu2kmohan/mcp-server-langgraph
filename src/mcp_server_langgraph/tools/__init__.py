"""
Tool catalog for LangGraph agent

Provides a registry of tools that the agent can execute.
Tools are defined using LangChain's @tool decorator for automatic schema generation.
"""

from typing import Any

from langchain_core.tools import BaseTool

from mcp_server_langgraph.core.config import Settings, settings
from mcp_server_langgraph.tools.calculator_tools import add, calculator, divide, multiply, subtract
from mcp_server_langgraph.tools.computer_use_tools import (
    fill_form,
    get_element_info,
    get_screen_info,
    go_back,
    go_forward,
    keyboard_press,
    keyboard_type,
    mouse_click,
    mouse_drag,
    mouse_move,
    navigate,
    scroll,
    select_option,
)
from mcp_server_langgraph.tools.bash_tools import execute_bash
from mcp_server_langgraph.tools.edit_file_tools import edit_file
from mcp_server_langgraph.tools.write_file_tools import write_file
from mcp_server_langgraph.tools.defer_loading import DEFERRED_TOOLS
from mcp_server_langgraph.tools.filesystem_tools import list_directory, read_file, search_files
from mcp_server_langgraph.tools.screenshot_tools import capture_screenshot
from mcp_server_langgraph.tools.search_tools import search_knowledge_base, web_search
from mcp_server_langgraph.tools.web_fetch_tools import web_fetch


def get_all_tools(settings_override: Any | None = None) -> list[BaseTool]:
    """
    Factory function to get all tools based on settings.

    This allows runtime configuration of tools, enabling:
    - Multi-tenant deployments with different tool sets
    - Dynamic enable/disable of code execution
    - Testing with custom settings

    Args:
        settings_override: Optional Settings instance. If None, uses global settings.

    Returns:
        List of all available tools based on settings
    """
    # Use override settings if provided, otherwise use global settings
    effective_settings: Settings = settings_override if settings_override is not None else settings

    # Base tools (always available)
    tools: list[BaseTool] = [
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
    ]

    # High-risk tools should only be exposed in sandboxed environments.
    # Use env/feature flag checks to gate them.
    sandbox_tools_enabled = effective_settings.environment.lower() in ("test", "sandbox") or str(
        getattr(effective_settings, "enable_sandbox_tools", False)
    ).lower() in ("1", "true", "yes")

    if sandbox_tools_enabled:
        # Computer use tools
        tools.extend(
            [
                navigate,
                go_back,
                go_forward,
                mouse_click,
                mouse_move,
                mouse_drag,
                keyboard_type,
                keyboard_press,
                scroll,
                select_option,
                fill_form,
                get_element_info,
                get_screen_info,
            ]
        )

        # Bash (allowlist) and workspace file mutation tools
        tools.append(execute_bash)
        tools.append(edit_file)
        tools.append(write_file)
        # Network fetch (with SSRF protections)
        tools.append(web_fetch)

    # Code execution tools (conditional on configuration)
    if effective_settings.enable_code_execution:
        try:
            from mcp_server_langgraph.tools.code_execution_tools import execute_python

            # Mark execute_python as requiring HITL approval in downstream agents
            # Handle case where metadata is None (not just missing)
            existing_metadata = getattr(execute_python, "metadata", None) or {}
            execute_python.metadata = {**existing_metadata, "requires_hitl": True}
            tools.append(execute_python)
        except ImportError:
            # Code execution dependencies not installed - silently skip
            pass

    # Visual verification tools (conditional on configuration) - only in sandbox
    if sandbox_tools_enabled and getattr(effective_settings, "enable_visual_verification", False):
        tools.append(capture_screenshot)

    return tools


# Backward compatibility: ALL_TOOLS uses default settings
# NOTE: For multi-tenant or runtime configuration, use get_all_tools(settings) instead
ALL_TOOLS: list[BaseTool] = get_all_tools()

# Tool groups for conditional loading
CALCULATOR_TOOLS = [calculator, add, subtract, multiply, divide]
SEARCH_TOOLS = [search_knowledge_base, web_search]
FILESYSTEM_TOOLS = [read_file, list_directory, search_files]
VISUAL_VERIFICATION_TOOLS: list[BaseTool] = [capture_screenshot]


# Code execution tools group (conditionally loaded based on settings)
# Returns empty list if code execution is disabled
def _get_code_execution_tools() -> list[BaseTool]:
    """Get code execution tools if enabled in settings"""
    if settings.enable_code_execution:
        try:
            from mcp_server_langgraph.tools.code_execution_tools import execute_python

            return [execute_python]
        except ImportError:
            pass
    return []


CODE_EXECUTION_TOOLS = _get_code_execution_tools()


def get_tools(categories: list[str] | None = None, settings_override: Any | None = None) -> list[BaseTool]:
    """
    Get tools by category.

    Args:
        categories: List of categories to include (None = all tools)
                   Options: "calculator", "search", "filesystem", "code_execution"
        settings_override: Optional Settings instance for runtime configuration

    Returns:
        List of tools matching the categories
    """
    all_tools = get_all_tools(settings_override)

    if categories is None:
        return all_tools

    tools: list[BaseTool] = []
    category_map = {
        "calculator": CALCULATOR_TOOLS,
        "search": SEARCH_TOOLS,
        "filesystem": FILESYSTEM_TOOLS,
        "visual_verification": VISUAL_VERIFICATION_TOOLS,
    }

    for category in categories:
        if category in category_map:
            tools.extend(category_map[category])
        elif category == "code_execution":
            # Dynamically include code execution tools if enabled
            code_tools = [t for t in all_tools if t.name == "execute_python"]
            tools.extend(code_tools)

    return tools


def get_tool_by_name(name: str, settings_override: Any | None = None) -> BaseTool | None:
    """
    Get a specific tool by name.

    Args:
        name: Tool name
        settings_override: Optional Settings instance for runtime configuration

    Returns:
        Tool instance or None if not found
    """
    all_tools = get_all_tools(settings_override)
    for tool in all_tools:
        if tool.name == name:
            return tool
    return None


__all__ = [
    "ALL_TOOLS",
    "CALCULATOR_TOOLS",
    "CODE_EXECUTION_TOOLS",
    "DEFERRED_TOOLS",
    "FILESYSTEM_TOOLS",
    "SEARCH_TOOLS",
    "VISUAL_VERIFICATION_TOOLS",
    "add",
    "calculator",
    "capture_screenshot",
    "divide",
    # Computer Use tools
    "fill_form",
    "get_element_info",
    "get_screen_info",
    "go_back",
    "go_forward",
    "keyboard_press",
    "keyboard_type",
    "mouse_click",
    "mouse_drag",
    "mouse_move",
    "navigate",
    "scroll",
    "select_option",
    # Factory functions
    "get_all_tools",  # Factory function for runtime tool configuration
    "get_tool_by_name",
    "get_tools",
    "list_directory",
    "multiply",
    "read_file",
    "search_files",
    "search_knowledge_base",
    "subtract",
    "web_search",
]
