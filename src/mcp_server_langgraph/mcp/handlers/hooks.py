"""
MCP Hooks Extension Handler.

Exposes hook management capabilities via MCP tool protocol:
- List registered hooks
- List available hook events
- Event descriptions with documentation

Reference: https://modelcontextprotocol.io/specification/2025-11-25/server/tools
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from mcp_server_langgraph.core.hooks import HookEvent

if TYPE_CHECKING:
    from mcp_server_langgraph.core.hook_registry import HookRegistry


# =============================================================================
# Event Descriptions
# =============================================================================

EVENT_DESCRIPTIONS: dict[str, str] = {
    "PreToolUse": "Before tool execution - can modify input, validate, or deny",
    "PostToolUse": "After tool execution - can modify output, audit, or log",
    "BeforeModel": "Before LLM call - can modify prompt, inject cache, skip call",
    "AfterModel": "After LLM response - can filter output, add disclaimers, redact",
    "SessionStart": "Session begins - can inject configuration, auth checks",
    "SessionEnd": "Session ends - cleanup, persist state, finalize metrics",
    "UserPromptSubmit": "User submits prompt - can modify, enhance, or log",
    "Stop": "Agent stops - cleanup, logging, finalization",
    "SubagentStop": "Subagent completes - collect results, logging",
    "PreCompact": "Before context compaction - custom compaction logic",
}


def get_event_description(event: HookEvent | Any) -> str:
    """Get description for a hook event.

    Args:
        event: HookEvent enum value or any object with value attribute

    Returns:
        Description string for the event
    """
    event_value = getattr(event, "value", str(event))
    return EVENT_DESCRIPTIONS.get(event_value, f"Hook event: {event_value}")


# =============================================================================
# Hooks Tool Handler
# =============================================================================


class HooksToolHandler:
    """MCP tool handler for hook management.

    Provides operations to list registered hooks and available events.
    """

    def __init__(self, hook_registry: HookRegistry | None = None) -> None:
        """Initialize the handler.

        Args:
            hook_registry: Optional hook registry to use.
                          If None, uses the global singleton.
        """
        self._registry = hook_registry

    @property
    def registry(self) -> HookRegistry:
        """Get the hook registry."""
        if self._registry is None:
            from mcp_server_langgraph.core.hook_registry import get_hook_registry

            return get_hook_registry()
        return self._registry

    async def handle_operation(
        self,
        operation: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle a hooks tool operation.

        Args:
            operation: Operation name (list, events)
            arguments: Operation arguments

        Returns:
            Operation result
        """
        op = operation.lower()

        if op == "list":
            return await self._handle_list(arguments)
        elif op == "events":
            return await self._handle_events()
        else:
            return {"error": f"Unknown operation: {operation}"}

    async def _handle_list(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """List registered hooks.

        Args:
            arguments: May contain 'event' to filter by event type

        Returns:
            Dict with 'hooks' list
        """
        event_filter = arguments.get("event")
        hooks: list[dict[str, Any]] = []

        for event in HookEvent:
            # Apply event filter if specified
            if event_filter and event.value != event_filter:
                continue

            matchers = self.registry.get_matchers(event)
            for matcher in matchers:
                hooks.append(
                    {
                        "event": event.value,
                        "matcher": matcher.matcher,
                        "timeout": matcher.timeout,
                        "hook_count": len(matcher.hooks),
                    }
                )

        return {"hooks": hooks}

    async def _handle_events(self) -> dict[str, Any]:
        """List available hook events.

        Returns:
            Dict with 'events' list containing event info
        """
        events: list[dict[str, str]] = []

        for event in HookEvent:
            events.append(
                {
                    "event": event.value,
                    "description": get_event_description(event),
                }
            )

        return {"events": events}

    def get_tool_definition(self) -> dict[str, Any]:
        """Get the tool definition for MCP registration.

        Returns:
            Tool definition dict with name, description, and inputSchema
        """
        return {
            "name": "hooks",
            "description": "Hook management: list registered hooks and available events",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["list", "events"],
                        "description": "Operation to perform",
                    },
                    "event": {
                        "type": "string",
                        "description": "Filter by event type (optional, for list operation)",
                    },
                },
                "required": ["operation"],
            },
        }


# =============================================================================
# Factory Function
# =============================================================================


def create_hooks_tool_handler(
    hook_registry: HookRegistry | None = None,
) -> HooksToolHandler:
    """Create a hooks tool handler.

    Args:
        hook_registry: Optional hook registry to use

    Returns:
        Configured HooksToolHandler instance
    """
    return HooksToolHandler(hook_registry=hook_registry)
