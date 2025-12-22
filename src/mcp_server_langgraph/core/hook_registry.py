"""
Hook registry and dispatcher for tool execution lifecycle

This module provides the HookRegistry for managing hook registration and
the HookDispatcher for executing hooks in the correct order.

Usage:
    from mcp_server_langgraph.core.hook_registry import (
        get_hook_registry,
        HookDispatcher,
    )
    from mcp_server_langgraph.core.hooks import HookEvent, HookMatcher

    registry = get_hook_registry()
    registry.register(HookEvent.PRE_TOOL_USE, HookMatcher(matcher="Bash", hooks=[my_hook]))

    dispatcher = HookDispatcher(registry)
    result = await dispatcher.dispatch_pre_tool_use(
        tool_name="Bash",
        tool_input={"command": "ls"},
        context=HookContext(session_id="test"),
    )
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from mcp_server_langgraph.core.feature_flags import feature_flags
from mcp_server_langgraph.core.hooks import (
    AfterModelInput,
    BeforeModelInput,
    HookContext,
    HookEvent,
    HookMatcher,
    HookResult,
    PostToolUseInput,
    PreToolUseInput,
    TokenUsage,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


# Global singleton registry
_hook_registry: HookRegistry | None = None


def get_hook_registry() -> HookRegistry:
    """Get the global singleton hook registry.

    Returns:
        The global HookRegistry instance
    """
    global _hook_registry
    if _hook_registry is None:
        _hook_registry = HookRegistry()
    return _hook_registry


def reset_hook_registry() -> None:
    """Reset the global hook registry (for testing)."""
    global _hook_registry
    _hook_registry = None


@dataclass
class HookRegistry:
    """Registry for managing hook registration.

    Provides thread-safe registration and retrieval of hooks for different events.
    """

    _hooks: dict[HookEvent, list[HookMatcher]] = field(default_factory=dict)

    def register(self, event: HookEvent, matcher: HookMatcher) -> None:
        """Register a hook matcher for an event.

        Args:
            event: The hook event type
            matcher: The HookMatcher containing hooks and pattern
        """
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(matcher)

    def get_matchers(self, event: HookEvent) -> list[HookMatcher]:
        """Get all matchers registered for an event.

        Args:
            event: The hook event type

        Returns:
            List of HookMatcher instances (empty if none registered)
        """
        return self._hooks.get(event, [])

    def unregister_all(self, event: HookEvent) -> None:
        """Remove all hooks for a specific event.

        Args:
            event: The hook event type
        """
        self._hooks.pop(event, None)

    def clear(self) -> None:
        """Remove all hooks from the registry."""
        self._hooks.clear()


class HookDispatcher:
    """Dispatcher for executing hooks in order.

    Handles hook matching, timeout enforcement, and result combination.
    """

    def __init__(self, registry: HookRegistry) -> None:
        """Initialize the dispatcher with a registry.

        Args:
            registry: The HookRegistry to use for hook lookup
        """
        self.registry = registry

    async def dispatch(
        self,
        event: HookEvent,
        input_data: PreToolUseInput | PostToolUseInput | Any,
        tool_use_id: str | None = None,
        context: HookContext | None = None,
        *,
        tool_name: str | None = None,
    ) -> HookResult:
        """Dispatch hooks for an event.

        Executes all matching hooks in order, stopping on first deny or skip.
        Passes updated input from one hook to the next.

        Feature flag enforcement:
        - When FF_ENABLE_SDK_HOOKS=false, hooks are skipped (returns allow)
        - When FF_ENABLE_SDK_HOOKS=true (default), hooks execute normally

        Args:
            event: The hook event type
            input_data: The input data for the hooks
            tool_use_id: Optional tool use ID
            context: The hook context
            tool_name: Optional tool name for matching (keyword-only)

        Returns:
            Combined HookResult from all executed hooks

        Raises:
            asyncio.TimeoutError: If a hook exceeds its timeout
        """
        # Feature flag enforcement: skip hooks when disabled
        if not feature_flags.enable_sdk_hooks:
            return HookResult()

        matchers = self.registry.get_matchers(event)

        # Determine tool name for matching - explicit parameter takes precedence
        effective_tool_name = tool_name
        if effective_tool_name is None and hasattr(input_data, "tool_name"):
            effective_tool_name = input_data.tool_name

        combined_result = HookResult()
        current_input = input_data

        for matcher in matchers:
            # Check if matcher applies to this tool
            if effective_tool_name is not None and not matcher.matches(effective_tool_name):
                continue

            # Execute all hooks in this matcher
            for hook in matcher.hooks:
                result = await asyncio.wait_for(
                    hook(current_input, tool_use_id, context),
                    timeout=matcher.timeout,
                )

                # Update combined result
                if result.message is not None:
                    combined_result.message = result.message
                if result.updated_input is not None:
                    combined_result.updated_input = result.updated_input
                    # Update input for next hook if it's a PreToolUseInput
                    if isinstance(current_input, PreToolUseInput):
                        current_input = PreToolUseInput(
                            tool_name=current_input.tool_name,
                            tool_input=result.updated_input,
                            tool_use_id=current_input.tool_use_id,
                        )
                if result.system_message is not None:
                    combined_result.system_message = result.system_message

                # Handle early_return for BEFORE_MODEL hooks
                if result.early_return is not None:
                    combined_result.early_return = result.early_return

                # Handle modified_output for AFTER_MODEL hooks
                if result.modified_output is not None:
                    combined_result.modified_output = result.modified_output

                # Stop on deny
                if result.behavior == "deny":
                    combined_result.behavior = "deny"
                    return combined_result

                # Stop on skip (e.g., cache hit for BEFORE_MODEL)
                if result.behavior == "skip":
                    combined_result.behavior = "skip"
                    return combined_result

        return combined_result

    async def dispatch_pre_tool_use(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        tool_use_id: str | None,
        context: HookContext,
    ) -> HookResult:
        """Convenience method for dispatching PreToolUse hooks.

        Args:
            tool_name: Name of the tool being executed
            tool_input: Arguments for the tool
            tool_use_id: Optional tool use ID
            context: The hook context

        Returns:
            HookResult with combined results
        """
        input_data = PreToolUseInput(
            tool_name=tool_name,
            tool_input=tool_input,
            tool_use_id=tool_use_id,
        )
        return await self.dispatch(
            HookEvent.PRE_TOOL_USE,
            input_data,
            tool_use_id,
            context,
        )

    async def dispatch_post_tool_use(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        tool_output: str,
        tool_use_id: str | None,
        is_error: bool,
        context: HookContext,
    ) -> HookResult:
        """Convenience method for dispatching PostToolUse hooks.

        Args:
            tool_name: Name of the tool that was executed
            tool_input: Arguments that were passed to the tool
            tool_output: Output from the tool
            tool_use_id: Optional tool use ID
            is_error: Whether the tool returned an error
            context: The hook context

        Returns:
            HookResult with combined results
        """
        input_data = PostToolUseInput(
            tool_name=tool_name,
            tool_input=tool_input,
            tool_output=tool_output,
            tool_use_id=tool_use_id,
            is_error=is_error,
        )
        return await self.dispatch(
            HookEvent.POST_TOOL_USE,
            input_data,
            tool_use_id,
            context,
        )

    async def dispatch_before_model(
        self,
        messages: list[dict[str, Any]],
        model: str,
        context: HookContext,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]] | None = None,
        config: dict[str, Any] | None = None,
    ) -> HookResult:
        """Convenience method for dispatching BeforeModel hooks (ADR-0080).

        Before LLM call hooks can:
        - Modify the request (prompt injection, context addition)
        - Return cached response (skip LLM call entirely with early_return)
        - Block forbidden content before token spend (deny)

        Args:
            messages: Messages to send to the LLM
            model: Model identifier
            context: The hook context with session/user info
            temperature: Optional temperature setting
            max_tokens: Optional max tokens setting
            tools: Optional tools configuration
            config: Optional additional configuration

        Returns:
            HookResult with behavior, early_return, or updated_input
        """
        # Check feature flag for LLM hooks
        if not feature_flags.enable_llm_hooks:
            return HookResult()

        input_data = BeforeModelInput(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,
            config=config or {},
        )
        return await self.dispatch(
            HookEvent.BEFORE_MODEL,
            input_data,
            tool_use_id=None,
            context=context,
            tool_name="llm",  # Use "llm" as the tool name for matching
        )

    async def dispatch_after_model(
        self,
        content: str,
        model: str,
        context: HookContext,
        *,
        tool_calls: list[dict[str, Any]] | None = None,
        usage: TokenUsage | None = None,
        finish_reason: str = "",
        latency_ms: float = 0.0,
    ) -> HookResult:
        """Convenience method for dispatching AfterModel hooks (ADR-0080).

        After LLM call hooks can:
        - Filter or redact output content
        - Add disclaimers or formatting
        - Transform response structure via modified_output

        Args:
            content: LLM response content
            model: Model identifier
            context: The hook context with session/user info
            tool_calls: Optional tool calls from response
            usage: Optional token usage statistics
            finish_reason: Optional finish reason
            latency_ms: Optional latency in milliseconds

        Returns:
            HookResult with behavior or modified_output
        """
        # Check feature flag for LLM hooks
        if not feature_flags.enable_llm_hooks:
            return HookResult()

        input_data = AfterModelInput(
            content=content,
            model=model,
            tool_calls=tool_calls,
            usage=usage,
            finish_reason=finish_reason,
            latency_ms=latency_ms,
        )
        return await self.dispatch(
            HookEvent.AFTER_MODEL,
            input_data,
            tool_use_id=None,
            context=context,
            tool_name="llm",  # Use "llm" as the tool name for matching
        )


@asynccontextmanager
async def temporary_hooks(
    registry: HookRegistry,
    hooks: dict[HookEvent, list[HookMatcher]],
) -> AsyncIterator[None]:
    """Context manager for temporary hook registration.

    Registers hooks on entry and removes them on exit.
    Useful for testing or scoped hook configuration.

    Args:
        registry: The registry to modify
        hooks: Dict mapping events to lists of matchers

    Yields:
        None
    """
    # Register hooks
    for event, matchers in hooks.items():
        for matcher in matchers:
            registry.register(event, matcher)

    try:
        yield
    finally:
        # Unregister hooks
        for event in hooks:
            registry.unregister_all(event)


__all__ = [
    "HookDispatcher",
    "HookRegistry",
    "get_hook_registry",
    "reset_hook_registry",
    "temporary_hooks",
]
