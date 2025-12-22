"""
MCP Hooks Extension Handler.

Exposes hook management capabilities via MCP tool protocol:
- hooks/list - List registered hooks
- hooks/events - List available hook events
- hooks/register - Register a webhook (admin only)
- hooks/unregister - Unregister a webhook (admin only)

Reference: https://modelcontextprotocol.io/specification/2025-11-25/server/tools
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from mcp.types import TextContent

from mcp_server_langgraph.core.hook_registry import HookEvent, HookMatcher

if TYPE_CHECKING:
    from mcp_server_langgraph.auth.middleware import AuthMiddleware
    from mcp_server_langgraph.core.hook_registry import HookRegistry


# =============================================================================
# Event Descriptions
# =============================================================================

EVENT_DESCRIPTIONS: dict[str, str] = {
    "PRE_TOOL_USE": "Before tool execution - can modify input, validate, or deny",
    "POST_TOOL_USE": "After tool execution - can modify output, audit, or log",
    "BEFORE_MODEL": "Before LLM call - can modify prompt, inject cache, skip call",
    "AFTER_MODEL": "After LLM response - can filter output, add disclaimers, redact",
    "SESSION_START": "Session begins - can inject configuration, auth checks",
    "SESSION_END": "Session ends - cleanup, persist state, finalize metrics",
    "USER_PROMPT_SUBMIT": "User submits prompt - can modify, enhance, or log",
    "STOP": "Agent stops - cleanup, logging, finalization",
    "SUBAGENT_STOP": "Subagent completes - collect results, logging",
    "PRE_COMPACT": "Before context compaction - custom compaction logic",
}


def get_event_description(event: HookEvent | str) -> str:
    """Get description for a hook event.

    Args:
        event: HookEvent enum value or event name string

    Returns:
        Description string for the event
    """
    if isinstance(event, HookEvent):
        event_name = event.name
    else:
        event_name = str(event)
    return EVENT_DESCRIPTIONS.get(event_name, f"Hook event: {event_name}")


# =============================================================================
# Hooks Tool Handler
# =============================================================================


class HooksToolHandler:
    """MCP tool handler for hook management.

    Provides operations to:
    - list: List registered hooks (with optional event filter)
    - events: List available hook events with descriptions
    - register: Register a webhook for an event (admin only)
    - unregister: Unregister a webhook (admin only)
    """

    def __init__(
        self,
        auth: "AuthMiddleware",
        agent_graph: Any,
        hook_registry: "HookRegistry | None" = None,
    ) -> None:
        """Initialize the handler.

        Args:
            auth: Authentication/authorization middleware
            agent_graph: LangGraph agent instance
            hook_registry: Optional hook registry to use.
                          If None, uses the global singleton.
        """
        self.auth = auth
        self.agent_graph = agent_graph
        self._registry = hook_registry

    @property
    def registry(self) -> "HookRegistry":
        """Get the hook registry."""
        if self._registry is None:
            from mcp_server_langgraph.core.hook_registry import get_hook_registry

            return get_hook_registry()
        return self._registry

    async def handle(
        self,
        arguments: dict[str, Any],
        span: Any,
        user_id: str,
    ) -> list[TextContent]:
        """Handle a hooks tool invocation.

        Args:
            arguments: Tool arguments including 'operation'
            span: OpenTelemetry span for tracing
            user_id: Authenticated user ID

        Returns:
            List of TextContent responses
        """
        operation = arguments.get("operation", "list").lower()

        if operation == "list":
            return await self._handle_list(arguments)
        elif operation == "events":
            return await self._handle_events()
        elif operation == "register":
            return await self._handle_register(arguments, user_id)
        elif operation == "unregister":
            return await self._handle_unregister(arguments, user_id)
        else:
            return [TextContent(type="text", text=f"Unknown operation: {operation}")]

    async def _handle_list(self, arguments: dict[str, Any]) -> list[TextContent]:
        """List registered hooks.

        Args:
            arguments: May contain 'event' to filter by event type

        Returns:
            List of TextContent with hooks JSON
        """
        event_filter = arguments.get("event")
        hooks: list[dict[str, Any]] = []

        # Access _hooks directly from registry for iteration
        registry_hooks = getattr(self.registry, "_hooks", {})

        for event, matchers in registry_hooks.items():
            # Apply event filter if specified
            if event_filter and event.name != event_filter:
                continue

            for matcher in matchers:
                hooks.append(
                    {
                        "event": event.name,
                        "matcher": matcher.matcher,
                        "timeout": matcher.timeout,
                        "hook_count": len(matcher.hooks),
                    }
                )

        return [TextContent(type="text", text=json.dumps(hooks))]

    async def _handle_events(self) -> list[TextContent]:
        """List available hook events.

        Returns:
            List of TextContent with events JSON
        """
        events: list[dict[str, str]] = []

        for event in HookEvent:
            events.append(
                {
                    "event": event.name,
                    "description": get_event_description(event),
                }
            )

        return [TextContent(type="text", text=json.dumps(events))]

    async def _handle_register(
        self, arguments: dict[str, Any], user_id: str
    ) -> list[TextContent]:
        """Register a webhook for hook events (admin only).

        Args:
            arguments: Must contain 'event' and 'webhook_url'
            user_id: User ID for authorization check

        Returns:
            List of TextContent with result
        """
        # Check admin authorization
        authorized = await self.auth.authorize(
            user_id=user_id,
            relation="admin",
            resource="hooks",
        )
        if not authorized:
            return [TextContent(type="text", text="Unauthorized: admin role required")]

        event_name = arguments.get("event")
        webhook_url = arguments.get("webhook_url")
        matcher_pattern = arguments.get("matcher")

        if not event_name:
            return [TextContent(type="text", text="Error: 'event' is required")]
        if not webhook_url:
            return [TextContent(type="text", text="Error: 'webhook_url' is required")]

        # Find the HookEvent enum
        try:
            hook_event = HookEvent[event_name]
        except KeyError:
            return [
                TextContent(type="text", text=f"Error: Unknown event '{event_name}'")
            ]

        # Create a webhook callback (placeholder - actual implementation would make HTTP calls)
        async def webhook_callback(
            input_data: dict[str, Any],
            tool_use_id: str | None,
            context: Any,
        ) -> Any:
            """Webhook callback that would POST to the webhook URL."""
            # In production, this would use httpx to POST to webhook_url
            from mcp_server_langgraph.core.hooks import HookResult

            return HookResult(behavior="allow")

        # Register with hook registry
        self.registry.register(
            event=hook_event,
            matcher=HookMatcher(
                hooks=[webhook_callback],
                matcher=matcher_pattern,
            ),
        )

        return [
            TextContent(
                type="text",
                text=f"Hook registered for {event_name} -> {webhook_url}",
            )
        ]

    async def _handle_unregister(
        self, arguments: dict[str, Any], user_id: str
    ) -> list[TextContent]:
        """Unregister a webhook (admin only).

        Args:
            arguments: Must contain 'event'
            user_id: User ID for authorization check

        Returns:
            List of TextContent with result
        """
        # Check admin authorization
        authorized = await self.auth.authorize(
            user_id=user_id,
            relation="admin",
            resource="hooks",
        )
        if not authorized:
            return [TextContent(type="text", text="Unauthorized: admin role required")]

        event_name = arguments.get("event")
        if not event_name:
            return [TextContent(type="text", text="Error: 'event' is required")]

        # Find the HookEvent enum
        try:
            hook_event = HookEvent[event_name]
        except KeyError:
            return [
                TextContent(type="text", text=f"Error: Unknown event '{event_name}'")
            ]

        # Unregister all hooks for this event
        self.registry.unregister_all(event=hook_event)

        return [TextContent(type="text", text=f"Hooks unregistered for {event_name}")]

    def get_tool_definition(self) -> dict[str, Any]:
        """Get the tool definition for MCP registration.

        Returns:
            Tool definition dict with name, description, and inputSchema
        """
        return {
            "name": "hooks",
            "description": "Hook management: list, register, unregister hooks and events",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["list", "events", "register", "unregister"],
                        "description": "Operation to perform",
                    },
                    "event": {
                        "type": "string",
                        "description": "Hook event type (required for register/unregister)",
                    },
                    "webhook_url": {
                        "type": "string",
                        "format": "uri",
                        "description": "Webhook URL (required for register)",
                    },
                    "matcher": {
                        "type": "string",
                        "description": "Optional matcher pattern for register",
                    },
                },
                "required": ["operation"],
            },
        }


# =============================================================================
# Factory Function
# =============================================================================


def create_hooks_tool_handler(
    auth: "AuthMiddleware",
    agent_graph: Any,
    hook_registry: "HookRegistry | None" = None,
) -> HooksToolHandler:
    """Create a hooks tool handler.

    Args:
        auth: Authentication/authorization middleware
        agent_graph: LangGraph agent instance
        hook_registry: Optional hook registry to use

    Returns:
        Configured HooksToolHandler instance
    """
    return HooksToolHandler(
        auth=auth,
        agent_graph=agent_graph,
        hook_registry=hook_registry,
    )
