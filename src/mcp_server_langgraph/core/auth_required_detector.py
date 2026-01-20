"""
Auth Required Detection for MCP Tool Execution.

This module provides detection logic for when a tool call requires authentication.
It checks connection status and emits auth_required events via LangGraph custom events.

Usage in tool execution flow:
    from mcp_server_langgraph.core.auth_required_detector import (
        check_tool_auth_required,
        emit_auth_required_event,
    )

    # Before executing tool
    auth_info = await check_tool_auth_required(tool_name)
    if auth_info:
        await emit_auth_required_event(auth_info)
        # Return fallback response instead of executing tool
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from mcp_server_langgraph.observability.telemetry import logger

if TYPE_CHECKING:
    pass


# Template ID mapping from tool name prefixes
# Maps MCP server names to connection template IDs
TOOL_PREFIX_TO_TEMPLATE: dict[str, str] = {
    "github": "github",
    "slack": "slack",
    "notion": "notion",
    "jira": "jira",
    "linear": "linear",
    "gitlab": "gitlab",
    "google-drive": "google-drive",
    "dropbox": "dropbox",
    "discord": "discord",
    "airtable": "airtable",
}


@dataclass
class AuthRequiredInfo:
    """Information about an auth requirement for a tool call."""

    tool_name: str
    """Qualified tool name that triggered the auth requirement."""

    connection_id: str | None
    """Existing connection ID that needs re-authentication, if any."""

    template_id: str | None
    """Suggested template ID if no connection exists."""

    message: str
    """User-friendly message explaining the auth requirement."""

    retry_message_id: str | None = None
    """Original message ID to retry after auth, if any."""


def infer_template_from_tool_name(tool_name: str) -> str | None:
    """Infer a template ID from a qualified tool name.

    Args:
        tool_name: Tool name, potentially qualified (e.g., 'github:list_pull_requests')

    Returns:
        Template ID if a match is found, None otherwise.
    """
    # Handle qualified names with :: or : separator
    if "::" in tool_name:
        server_name = tool_name.split("::")[0].lower()
    elif ":" in tool_name:
        server_name = tool_name.split(":")[0].lower()
    else:
        # Try to match by prefix
        server_name = tool_name.split("_")[0].lower() if "_" in tool_name else tool_name.lower()

    return TOOL_PREFIX_TO_TEMPLATE.get(server_name)


async def check_tool_auth_required(
    tool_name: str,
    user_id: str | None = None,
) -> AuthRequiredInfo | None:
    """Check if a tool requires authentication.

    This function checks if:
    1. The tool is from an MCP server
    2. A connection exists for that server
    3. The connection status is 'auth_required'

    If no connection exists but a matching template is found,
    returns auth info with template_id for setup flow.

    Args:
        tool_name: Qualified tool name (e.g., 'github:list_pull_requests')
        user_id: User ID for scoped connection lookup

    Returns:
        AuthRequiredInfo if auth is required, None otherwise.
    """
    # Infer template from tool name
    template_id = infer_template_from_tool_name(tool_name)

    if template_id is None:
        # Not an MCP tool or unknown template
        return None

    # TODO: Phase 2+ - Lookup actual connection status from repository
    # For now, return None (no auth required) as placeholder
    # This will be enhanced in future to actually check connection status:
    #
    # connection = await connection_repo.get_by_template_id(template_id, user_id)
    # if connection is None:
    #     # No connection - suggest setup
    #     return AuthRequiredInfo(
    #         tool_name=tool_name,
    #         connection_id=None,
    #         template_id=template_id,
    #         message=f"To use {tool_name}, please connect your {template_id} account.",
    #     )
    # elif connection.status == "auth_required":
    #     # Connection exists but needs re-auth
    #     return AuthRequiredInfo(
    #         tool_name=tool_name,
    #         connection_id=connection.id,
    #         template_id=template_id,
    #         message=f"Your {template_id} connection requires re-authentication.",
    #     )

    logger.debug(f"Auth check for tool {tool_name}: template_id={template_id}")
    return None


async def emit_auth_required_event(
    auth_info: AuthRequiredInfo,
    retry_message_id: str | None = None,
) -> None:
    """Emit an auth_required custom event via LangGraph callbacks.

    This event will be captured by the SSE stream and forwarded to the frontend.

    Args:
        auth_info: Auth requirement information
        retry_message_id: Optional message ID for retry after auth
    """
    from langchain_core.callbacks.manager import adispatch_custom_event

    event_data = {
        "tool_name": auth_info.tool_name,
        "connection_id": auth_info.connection_id,
        "template_id": auth_info.template_id,
        "message": auth_info.message,
        "retry_message_id": retry_message_id or auth_info.retry_message_id,
    }

    logger.info(
        f"Emitting auth_required event for tool {auth_info.tool_name}",
        extra={"template_id": auth_info.template_id},
    )

    await adispatch_custom_event("auth_required", event_data)


# Convenience function for tool execution flow
async def check_and_emit_if_auth_required(
    tool_name: str,
    user_id: str | None = None,
    retry_message_id: str | None = None,
) -> bool:
    """Check if tool requires auth and emit event if so.

    Args:
        tool_name: Tool name to check
        user_id: User ID for connection lookup
        retry_message_id: Message ID to retry after auth

    Returns:
        True if auth is required (event emitted), False otherwise.
    """
    auth_info = await check_tool_auth_required(tool_name, user_id)

    if auth_info:
        await emit_auth_required_event(auth_info, retry_message_id)
        return True

    return False
