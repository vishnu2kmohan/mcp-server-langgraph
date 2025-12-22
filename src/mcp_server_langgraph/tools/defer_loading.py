"""
Defer Loading Pattern for Token Efficiency

This module implements the defer_loading pattern from Anthropic's
Advanced Tool Use research, which reduces token usage by excluding
certain tools from the initial tools/list response.

Deferred tools:
- Are NOT included in the initial tools/list response
- CAN be discovered via search_tools or get_tool_by_name
- Are useful for specialized tools that are rarely needed

Usage:
    from mcp_server_langgraph.tools.defer_loading import (
        register_deferred_tool,
        get_visible_tools,
        is_tool_deferred,
    )

    # Mark a tool as deferred
    register_deferred_tool("specialized_analyzer")

    # Get tools for initial listing (excludes deferred)
    visible_tools = get_visible_tools()

    # Check if a specific tool is deferred
    is_deferred = is_tool_deferred("specialized_analyzer")
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langchain_core.tools import BaseTool

# Registry of deferred tool names
# Tools in this set will not appear in initial tools/list
_DEFERRED_TOOLS: set[str] = set()


def _safe_is_feature_enabled(flag_name: str) -> bool:
    """Safely check if a feature flag is enabled.

    Handles cases where feature flags module isn't available.
    """
    try:
        from mcp_server_langgraph.core.feature_flags import is_feature_enabled

        result: bool = is_feature_enabled(flag_name)
        return result
    except (ImportError, RuntimeError):
        # Feature flags not available - default to enabled
        return True


# Expose is_feature_enabled for testing with mocks
def is_feature_enabled(flag_name: str) -> bool:
    """Check if a feature flag is enabled (wrapper for mocking)."""
    return _safe_is_feature_enabled(flag_name)


def get_default_deferred_tools() -> set[str]:
    """Get the default set of deferred tools.

    By default, no tools are deferred. This function returns
    the set of tools that should be deferred on fresh module load.

    Returns:
        Set of tool names that are deferred by default (empty set)
    """
    # Conservative default: no tools are deferred
    # Users can explicitly register tools as deferred if needed
    return set()


def register_deferred_tool(tool_name: str) -> None:
    """Register a tool as deferred.

    Deferred tools will not appear in the initial tools/list response
    but can still be discovered via search_tools or get_tool_by_name.

    Args:
        tool_name: Name of the tool to defer
    """
    _DEFERRED_TOOLS.add(tool_name)


def unregister_deferred_tool(tool_name: str) -> None:
    """Unregister a tool from the deferred list.

    The tool will appear in the initial tools/list response again.

    Args:
        tool_name: Name of the tool to undefer
    """
    _DEFERRED_TOOLS.discard(tool_name)


def is_tool_deferred(tool_name: str) -> bool:
    """Check if a tool is deferred.

    Args:
        tool_name: Name of the tool to check

    Returns:
        True if the tool is deferred, False otherwise
    """
    return tool_name in _DEFERRED_TOOLS


def clear_deferred_tools() -> None:
    """Clear all deferred tool registrations.

    Useful for testing or resetting state.
    """
    _DEFERRED_TOOLS.clear()


def get_visible_tools(settings_override: object | None = None) -> list[BaseTool]:
    """Get tools that should be visible in the initial tools/list.

    This excludes deferred tools unless the feature flag is disabled.

    Args:
        settings_override: Optional settings for tool configuration

    Returns:
        List of visible (non-deferred) tools
    """
    from mcp_server_langgraph.tools import get_all_tools

    all_tools = get_all_tools(settings_override)

    # If defer_loading feature is disabled, return all tools
    if not is_feature_enabled("defer_loading"):
        return all_tools

    # Filter out deferred tools
    return [tool for tool in all_tools if tool.name not in _DEFERRED_TOOLS]


def get_deferred_tools(settings_override: object | None = None) -> list[BaseTool]:
    """Get only the deferred tools.

    Useful for exposing deferred tools via search_tools.

    Args:
        settings_override: Optional settings for tool configuration

    Returns:
        List of deferred tools
    """
    from mcp_server_langgraph.tools import get_all_tools

    all_tools = get_all_tools(settings_override)

    return [tool for tool in all_tools if tool.name in _DEFERRED_TOOLS]


# Public constant for backward compatibility
DEFERRED_TOOLS = _DEFERRED_TOOLS
