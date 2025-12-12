"""
MCP Icons Metadata (SEP-973).

MCP 2025-11-25 adds optional icon metadata for tools, resources, and prompts.
Icons can be data: URIs or https: URIs for client rendering.

Reference: https://modelcontextprotocol.io/specification/2025-11-25
"""

from typing import Any

from pydantic import BaseModel


class IconReference(BaseModel):
    """Reference to an icon for MCP entities.

    Icons can be:
    - data: URIs (e.g., data:image/svg+xml,<svg>...</svg>)
    - https: URIs (e.g., https://example.com/icon.svg)

    Clients use icons to visually represent tools, resources, and prompts.
    """

    uri: str


class ToolWithIcon(BaseModel):
    """Tool definition with optional icon metadata (SEP-973).

    Extends standard MCP tool definition with icon field.
    """

    name: str
    description: str | None = None
    inputSchema: dict[str, Any]
    icon: IconReference | None = None

    def to_mcp_format(self) -> dict[str, Any]:
        """Convert to MCP tools/list response format."""
        result: dict[str, Any] = {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.inputSchema,
        }
        if self.icon is not None:
            result["icon"] = self.icon.model_dump()
        return result


class ResourceWithIcon(BaseModel):
    """Resource definition with optional icon metadata (SEP-973).

    Extends standard MCP resource definition with icon field.
    """

    uri: str
    name: str
    description: str | None = None
    mimeType: str | None = None
    icon: IconReference | None = None

    def to_mcp_format(self) -> dict[str, Any]:
        """Convert to MCP resources/list response format."""
        result: dict[str, Any] = {
            "uri": self.uri,
            "name": self.name,
        }
        if self.description is not None:
            result["description"] = self.description
        if self.mimeType is not None:
            result["mimeType"] = self.mimeType
        if self.icon is not None:
            result["icon"] = self.icon.model_dump()
        return result


class PromptWithIcon(BaseModel):
    """Prompt definition with optional icon metadata (SEP-973).

    Extends standard MCP prompt definition with icon field.
    """

    name: str
    description: str | None = None
    arguments: list[dict[str, Any]] | None = None
    icon: IconReference | None = None

    def to_mcp_format(self) -> dict[str, Any]:
        """Convert to MCP prompts/list response format."""
        result: dict[str, Any] = {
            "name": self.name,
        }
        if self.description is not None:
            result["description"] = self.description
        if self.arguments is not None:
            result["arguments"] = self.arguments
        if self.icon is not None:
            result["icon"] = self.icon.model_dump()
        return result


# =============================================================================
# Predefined Icons for Common Tools
# =============================================================================

# Simple SVG icons as data URIs for common tools
# These provide sensible defaults when no custom icon is specified

_CHAT_ICON = (
    "data:image/svg+xml,"
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='currentColor'>"
    "<path d='M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z'/>"
    "</svg>"
)

_SEARCH_ICON = (
    "data:image/svg+xml,"
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='currentColor'>"
    "<path d='M15.5 14h-.79l-.28-.27A6.471 6.471 0 0016 9.5 6.5 6.5 0 109.5 16c1.61 0 "
    "3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5z'/>"
    "</svg>"
)

_CODE_ICON = (
    "data:image/svg+xml,"
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='currentColor'>"
    "<path d='M9.4 16.6L4.8 12l4.6-4.6L8 6l-6 6 6 6 1.4-1.4zm5.2 0l4.6-4.6-4.6-4.6L16 6l6 6-6 6-1.4-1.4z'/>"
    "</svg>"
)

_DOC_ICON = (
    "data:image/svg+xml,"
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='currentColor'>"
    "<path d='M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6z'/>"
    "</svg>"
)

_TOOL_ICON = (
    "data:image/svg+xml,"
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='currentColor'>"
    "<path d='M22.7 19l-9.1-9.1c.9-2.3.4-5-1.5-6.9-2-2-5-2.4-7.4-1.3L9 6 6 9 1.6 4.7C.4 7.1.9 "
    "10.1 2.9 12.1c1.9 1.9 4.6 2.4 6.9 1.5l9.1 9.1c.4.4 1 .4 1.4 0l2.3-2.3c.5-.4.5-1.1.1-1.4z'/>"
    "</svg>"
)

# Map of tool names to their default icons
DEFAULT_TOOL_ICONS: dict[str, IconReference] = {
    "agent_chat": IconReference(uri=_CHAT_ICON),
    "conversation_get": IconReference(uri=_DOC_ICON),
    "conversation_list": IconReference(uri=_DOC_ICON),
    "execute_python": IconReference(uri=_CODE_ICON),
    "search": IconReference(uri=_SEARCH_ICON),
    "web_search": IconReference(uri=_SEARCH_ICON),
}


def get_tool_icon(tool_name: str) -> IconReference | None:
    """Get the default icon for a tool by name.

    Args:
        tool_name: Name of the tool

    Returns:
        IconReference if a default icon exists, None otherwise
    """
    return DEFAULT_TOOL_ICONS.get(tool_name)
