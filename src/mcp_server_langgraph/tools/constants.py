"""
Tool constants shared across modules.

Centralized definitions for tool categories, sandbox requirements,
and helper functions. Moved from api/v1/tools.py to avoid import cycles.
"""

# =============================================================================
# Category Mapping for Built-in Tools
# =============================================================================

# Map tool names to categories
TOOL_CATEGORY_MAP: dict[str, str] = {
    # Calculator tools
    "calculator": "calculator",
    "add": "calculator",
    "subtract": "calculator",
    "multiply": "calculator",
    "divide": "calculator",
    # Search tools
    "search_knowledge_base": "search",
    "web_search": "search",
    "explore_knowledge_iteratively": "search",
    # Filesystem tools (read-only)
    "read_file": "filesystem",
    "list_directory": "filesystem",
    "search_files": "filesystem",
    # File mutation tools
    "edit_file": "filesystem",
    "write_file": "filesystem",
    # Code execution tools
    "execute_bash": "code_execution",
    "execute_python": "code_execution",
    # Web tools
    "web_fetch": "web",
    # Visual tools
    "capture_screenshot": "visual",
    # Computer use tools
    "navigate": "computer_use",
    "go_back": "computer_use",
    "go_forward": "computer_use",
    "mouse_click": "computer_use",
    "mouse_move": "computer_use",
    "mouse_drag": "computer_use",
    "keyboard_type": "computer_use",
    "keyboard_press": "computer_use",
    "scroll": "computer_use",
    "select_option": "computer_use",
    "fill_form": "computer_use",
    "get_element_info": "computer_use",
    "get_screen_info": "computer_use",
}

# Tools that require sandbox environment (high-risk operations)
SANDBOX_REQUIRED_TOOLS: frozenset[str] = frozenset(
    {
        "execute_bash",
        "execute_python",
        "edit_file",
        "write_file",
        "web_fetch",
        "navigate",
        "go_back",
        "go_forward",
        "mouse_click",
        "mouse_move",
        "mouse_drag",
        "keyboard_type",
        "keyboard_press",
        "scroll",
        "select_option",
        "fill_form",
        "get_element_info",
        "get_screen_info",
        "capture_screenshot",
    }
)


# =============================================================================
# Helper Functions
# =============================================================================


def get_tool_category(tool_name: str) -> str | None:
    """Get the category for a tool by name.

    Args:
        tool_name: The tool name to look up

    Returns:
        The category string or None if not found
    """
    return TOOL_CATEGORY_MAP.get(tool_name)


def get_display_name(tool_name: str) -> str:
    """Convert tool name to human-readable display name.

    Args:
        tool_name: The tool name in snake_case

    Returns:
        Human-readable Title Case name
    """
    return tool_name.replace("_", " ").title()


def tool_requires_sandbox(tool_name: str) -> bool:
    """Check if a tool requires sandbox environment.

    Args:
        tool_name: The tool name to check

    Returns:
        True if the tool requires sandbox, False otherwise
    """
    return tool_name in SANDBOX_REQUIRED_TOOLS
