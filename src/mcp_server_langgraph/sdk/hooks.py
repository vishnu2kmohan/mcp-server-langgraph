"""
Pre-Tool-Use Security Hooks

Security hooks that run before tool execution to validate,
sanitize, and enforce policies.

Usage:
    from mcp_server_langgraph.sdk.hooks import SecurityHookRegistry

    registry = SecurityHookRegistry()
    registry.register("PreToolUse", "Bash", command_allowlist_hook)
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable, Awaitable

from pydantic import BaseModel, Field


class HookResult(BaseModel):
    """Result from a security hook."""

    allowed: bool = Field(description="Whether the operation is allowed")
    reason: str | None = Field(default=None, description="Reason if denied")
    modified_input: dict[str, Any] | None = Field(
        default=None,
        description="Modified input if hook transformed data",
    )

    @classmethod
    def allow(cls, modified_input: dict[str, Any] | None = None) -> HookResult:
        """Create an allow result.

        Args:
            modified_input: Optional modified input data

        Returns:
            HookResult indicating allowed
        """
        return cls(allowed=True, modified_input=modified_input)

    @classmethod
    def deny(cls, reason: str) -> HookResult:
        """Create a deny result.

        Args:
            reason: Reason for denial

        Returns:
            HookResult indicating denied
        """
        return cls(allowed=False, reason=reason)


# Type for hook functions
HookFunction = Callable[
    [dict[str, Any], str, dict[str, Any]],
    Awaitable[HookResult],
]


class PreToolUseHook:
    """Base class for pre-tool-use hooks.

    Subclass this to create custom hooks.
    """

    async def execute(
        self,
        input_data: dict[str, Any],
        tool_use_id: str,
        context: dict[str, Any],
    ) -> HookResult:
        """Execute the hook.

        Args:
            input_data: Tool input data
            tool_use_id: Unique tool use identifier
            context: Execution context

        Returns:
            HookResult
        """
        return HookResult.allow()


async def pii_detection_hook(
    input_data: dict[str, Any],
    tool_use_id: str,
    context: dict[str, Any],
) -> HookResult:
    """Detect and tokenize PII before LLM exposure.

    Args:
        input_data: Tool input data
        tool_use_id: Tool use identifier
        context: Execution context

    Returns:
        HookResult with potentially modified input
    """
    from mcp_server_langgraph.core.feature_flags import feature_flags

    # Skip if PII tokenization disabled
    if not feature_flags.enable_pii_tokenization:
        return HookResult.allow()

    try:
        from mcp_server_langgraph.privacy import PIITokenizer

        tokenizer = PIITokenizer()

        tool_input = input_data.get("tool_input", {})
        modified = False
        lookup_table: dict[str, str] = {}

        for key, value in list(tool_input.items()):
            if isinstance(value, str):
                # tokenize() internally calls detect_pii and returns lookup
                tokenized_text, lookup = tokenizer.tokenize(value)
                if lookup:  # PII was found and tokenized
                    tool_input[key] = tokenized_text
                    lookup_table.update(lookup)
                    modified = True

        if modified:
            context["pii_lookup"] = lookup_table
            return HookResult.allow(modified_input={"tool_input": tool_input})

        return HookResult.allow()

    except ImportError:
        # Privacy module not available
        return HookResult.allow()


async def command_allowlist_hook(
    input_data: dict[str, Any],
    tool_use_id: str,
    context: dict[str, Any],
) -> HookResult:
    """Validate bash commands against allowlist.

    Args:
        input_data: Tool input data
        tool_use_id: Tool use identifier
        context: Execution context

    Returns:
        HookResult
    """
    if input_data.get("tool_name") != "Bash":
        return HookResult.allow()

    command = input_data.get("tool_input", {}).get("command", "")

    # Dangerous patterns to block
    blocked_patterns = [
        "rm -rf /",
        "rm -rf ~",
        "sudo rm",
        "> /dev/",
        "curl | bash",
        "wget | bash",
        ":(){ :|:& };:",  # Fork bomb
        "dd if=/dev/zero",
        "mkfs.",
        "chmod 777 /",
    ]

    for pattern in blocked_patterns:
        if pattern in command:
            return HookResult.deny(f"Blocked dangerous pattern: {pattern}")

    return HookResult.allow()


async def rate_limit_hook(
    input_data: dict[str, Any],
    tool_use_id: str,
    context: dict[str, Any],
) -> HookResult:
    """Enforce rate limits on tool calls.

    Args:
        input_data: Tool input data
        tool_use_id: Tool use identifier
        context: Execution context with user_id

    Returns:
        HookResult
    """
    # Simple in-memory rate limiting (would use Redis in production)
    # For now, always allow
    return HookResult.allow()


class SecurityHookRegistry:
    """Registry for security hooks.

    Manages pre-tool-use hooks and executes them before tool calls.
    """

    def __init__(self) -> None:
        """Initialize hook registry."""
        # Map: event_type -> tool_pattern -> list of hooks
        self._hooks: dict[str, dict[str, list[HookFunction]]] = defaultdict(lambda: defaultdict(list))

    def register(
        self,
        event_type: str,
        tool_pattern: str,
        hook: HookFunction,
    ) -> None:
        """Register a hook.

        Args:
            event_type: Event type (e.g., "PreToolUse")
            tool_pattern: Tool name pattern ("*" for all tools)
            hook: Hook function to register
        """
        self._hooks[event_type][tool_pattern].append(hook)

    def get_hooks(
        self,
        event_type: str,
        tool_name: str,
    ) -> list[HookFunction]:
        """Get hooks matching event and tool.

        Args:
            event_type: Event type
            tool_name: Tool name

        Returns:
            List of matching hooks
        """
        hooks = []

        # Get wildcard hooks
        hooks.extend(self._hooks[event_type].get("*", []))

        # Get tool-specific hooks
        hooks.extend(self._hooks[event_type].get(tool_name, []))

        return hooks

    async def execute_hooks(
        self,
        event_type: str,
        tool_name: str,
        input_data: dict[str, Any],
        tool_use_id: str,
        context: dict[str, Any],
    ) -> HookResult:
        """Execute all matching hooks.

        Args:
            event_type: Event type
            tool_name: Tool name
            input_data: Tool input data
            tool_use_id: Tool use identifier
            context: Execution context

        Returns:
            Combined HookResult (stops on first deny)
        """
        hooks = self.get_hooks(event_type, tool_name)

        current_input = input_data.copy()

        for hook in hooks:
            result = await hook(current_input, tool_use_id, context)

            if not result.allowed:
                return result

            # Apply modifications for next hook
            if result.modified_input:
                current_input.update(result.modified_input)

        return HookResult.allow(modified_input=current_input if current_input != input_data else None)


# Default security hooks
DEFAULT_SECURITY_HOOKS = SecurityHookRegistry()
DEFAULT_SECURITY_HOOKS.register("PreToolUse", "*", pii_detection_hook)
DEFAULT_SECURITY_HOOKS.register("PreToolUse", "Bash", command_allowlist_hook)
DEFAULT_SECURITY_HOOKS.register("PreToolUse", "*", rate_limit_hook)
