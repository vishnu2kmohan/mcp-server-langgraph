"""
Unified Hook Adapter

Bridges the SDK hook system and core hook system, allowing hooks written
for either system to work with both. Provides a unified interface while
maintaining backward compatibility.

Features:
- Automatic format conversion between SDK and core hooks
- Support for all hook types (PreToolUse, PostToolUse, UserPromptSubmit, Stop)
- Configurable timeout handling
- Observability (metrics and tracing)
- Execution order guarantee (registration order)

Usage:
    from mcp_server_langgraph.sdk.hook_adapter import UnifiedHookRegistry

    registry = UnifiedHookRegistry()

    # Register SDK-style hook
    async def my_sdk_hook(input_data, tool_use_id, context):
        return SDKHookResult.allow()

    registry.register_sdk_hook("PreToolUse", "*", my_sdk_hook)

    # Register core-style hook
    async def my_core_hook(input_data, tool_use_id, context):
        return CoreHookResult(behavior="allow")

    registry.register_core_hook("PreToolUse", "*", my_core_hook)
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Generator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Callable, Literal, cast

from mcp_server_langgraph.core.hooks import (
    HookContext,
    HookResult as CoreHookResult,
    PostToolUseInput,
    PreToolUseInput,
    StopInput,
    UserPromptSubmitInput,
)
from mcp_server_langgraph.sdk.hooks import HookResult as SDKHookResult

# Module-level metrics (to avoid duplicate registration)
_hook_metrics_initialized = False
_hook_executions_counter: Any = None
_hook_duration_histogram: Any = None
_hook_denials_counter: Any = None
_hook_timeouts_counter: Any = None


def _init_hook_metrics() -> None:
    """Initialize hook metrics once at module level."""
    global _hook_metrics_initialized, _hook_executions_counter, _hook_duration_histogram
    global _hook_denials_counter, _hook_timeouts_counter

    if _hook_metrics_initialized:
        return

    try:
        from prometheus_client import Counter, Histogram

        _hook_executions_counter = Counter(
            "sdk_hook_executions_total",
            "Total hook executions",
            ["hook_name", "event_type", "tool_name", "result"],
        )
        _hook_duration_histogram = Histogram(
            "sdk_hook_duration_ms",
            "Hook execution duration in milliseconds",
            ["hook_name", "event_type"],
        )
        _hook_denials_counter = Counter(
            "sdk_hook_denials_total",
            "Total hook denials",
            ["hook_name", "event_type", "tool_name"],
        )
        _hook_timeouts_counter = Counter(
            "sdk_hook_timeouts_total",
            "Total hook timeouts",
            ["hook_name", "event_type", "tool_name"],
        )
        _hook_metrics_initialized = True
    except ImportError:
        pass


# Type aliases
SDKHookFunction = Callable[
    [dict[str, Any], str, dict[str, Any]],
    Awaitable[SDKHookResult],
]

CoreHookFunction = Callable[
    [Any, str | None, HookContext],
    Awaitable[CoreHookResult],
]


@dataclass
class RegisteredHook:
    """A registered hook with metadata."""

    hook_type: Literal["sdk", "core"]
    event_type: str
    tool_pattern: str
    hook_fn: Callable[..., Awaitable[Any]]
    timeout: float
    name: str | None = None


class UnifiedHookAdapter:
    """Adapter for converting between SDK and core hook formats.

    Enables interoperability between the two hook systems.
    """

    def wrap_sdk_hook(
        self,
        sdk_hook: SDKHookFunction,
    ) -> CoreHookFunction:
        """Wrap an SDK-style hook to work with core hook dispatcher.

        Args:
            sdk_hook: SDK-style hook function

        Returns:
            Core-compatible hook function
        """

        async def wrapped(
            input_data: PreToolUseInput | PostToolUseInput | Any,
            tool_use_id: str | None,
            context: HookContext,
        ) -> CoreHookResult:
            # Convert core input to SDK format
            sdk_input = self._core_input_to_sdk(input_data)
            sdk_context = self._core_context_to_sdk(context)

            # Call SDK hook
            sdk_result = await sdk_hook(
                sdk_input,
                tool_use_id or "",
                sdk_context,
            )

            # Convert result back to core format
            return self._sdk_result_to_core(sdk_result)

        return wrapped

    def wrap_core_hook(
        self,
        core_hook: CoreHookFunction,
    ) -> SDKHookFunction:
        """Wrap a core-style hook to work with SDK registry.

        Args:
            core_hook: Core-style hook function

        Returns:
            SDK-compatible hook function
        """

        async def wrapped(
            input_data: dict[str, Any],
            tool_use_id: str,
            context: dict[str, Any],
        ) -> SDKHookResult:
            # Convert SDK input to core format
            core_input = self._sdk_input_to_core(input_data)
            core_context = self._sdk_context_to_core(context)

            # Call core hook
            core_result = await core_hook(
                core_input,
                tool_use_id or None,
                core_context,
            )

            # Convert result back to SDK format
            return self._core_result_to_sdk(core_result)

        return wrapped

    def _core_input_to_sdk(
        self,
        input_data: PreToolUseInput | PostToolUseInput | Any,
    ) -> dict[str, Any]:
        """Convert core input to SDK dict format."""
        if isinstance(input_data, PreToolUseInput):
            return {
                "tool_name": input_data.tool_name,
                "tool_input": input_data.tool_input,
            }
        elif isinstance(input_data, PostToolUseInput):
            return {
                "tool_name": input_data.tool_name,
                "tool_input": input_data.tool_input,
                "tool_output": input_data.tool_output,
                "is_error": input_data.is_error,
            }
        elif isinstance(input_data, UserPromptSubmitInput):
            return {"prompt": input_data.prompt}
        elif isinstance(input_data, StopInput):
            return {
                "reason": input_data.reason,
                "is_error": input_data.is_error,
                "result": input_data.result,
            }
        else:
            # Generic dict passthrough
            return dict(input_data) if hasattr(input_data, "__iter__") else {}

    def _sdk_input_to_core(
        self,
        input_data: dict[str, Any],
    ) -> PreToolUseInput | PostToolUseInput | UserPromptSubmitInput | StopInput:
        """Convert SDK dict to core input format."""
        if "tool_output" in input_data:
            return PostToolUseInput(
                tool_name=input_data.get("tool_name", ""),
                tool_input=input_data.get("tool_input", {}),
                tool_output=input_data.get("tool_output", ""),
                is_error=input_data.get("is_error", False),
            )
        elif "prompt" in input_data:
            return UserPromptSubmitInput(
                prompt=input_data.get("prompt", ""),
            )
        elif "reason" in input_data:
            return StopInput(
                reason=input_data.get("reason", ""),
                is_error=input_data.get("is_error", False),
                result=input_data.get("result"),
            )
        else:
            return PreToolUseInput(
                tool_name=input_data.get("tool_name", ""),
                tool_input=input_data.get("tool_input", {}),
            )

    def _core_context_to_sdk(self, context: HookContext) -> dict[str, Any]:
        """Convert core HookContext to SDK dict format."""
        return {
            "session_id": context.session_id,
            "user_id": context.user_id,
            "request_id": context.request_id,
            "metadata": context.metadata,
        }

    def _sdk_context_to_core(self, context: dict[str, Any]) -> HookContext:
        """Convert SDK dict to core HookContext."""
        return HookContext(
            session_id=context.get("session_id", ""),
            user_id=context.get("user_id"),
            request_id=context.get("request_id"),
            metadata=context.get("metadata", {}),
        )

    def _sdk_result_to_core(self, result: SDKHookResult) -> CoreHookResult:
        """Convert SDK HookResult to core HookResult."""
        behavior: Literal["allow", "deny"] = "allow" if result.allowed else "deny"

        # Extract tool_input from modified_input if present
        updated_input = None
        if result.modified_input:
            updated_input = result.modified_input.get("tool_input", result.modified_input)

        return CoreHookResult(
            behavior=behavior,
            message=result.reason,
            updated_input=updated_input,
        )

    def _core_result_to_sdk(self, result: CoreHookResult) -> SDKHookResult:
        """Convert core HookResult to SDK HookResult."""
        if result.behavior == "deny":
            return SDKHookResult.deny(result.message or "Denied")
        else:
            modified = None
            if result.updated_input:
                modified = {"tool_input": result.updated_input}
            return SDKHookResult.allow(modified_input=modified)


class UnifiedHookRegistry:
    """Unified registry that accepts both SDK and core hook formats.

    Provides a single interface for hook registration and execution,
    with support for timeout handling and observability.
    """

    def __init__(self, default_timeout: float = 60.0) -> None:
        """Initialize unified registry.

        Args:
            default_timeout: Default timeout for hook execution in seconds
        """
        self._hooks: list[RegisteredHook] = []
        self._adapter = UnifiedHookAdapter()
        self._default_timeout = default_timeout

    def register_sdk_hook(
        self,
        event_type: str,
        tool_pattern: str,
        hook: SDKHookFunction,
        timeout: float | None = None,
        name: str | None = None,
    ) -> None:
        """Register an SDK-style hook.

        Args:
            event_type: Event type (PreToolUse, PostToolUse, etc.)
            tool_pattern: Tool name pattern ("*" for all)
            hook: SDK-style hook function
            timeout: Optional custom timeout
            name: Optional hook name for observability
        """
        self._hooks.append(
            RegisteredHook(
                hook_type="sdk",
                event_type=event_type,
                tool_pattern=tool_pattern,
                hook_fn=hook,
                timeout=timeout or self._default_timeout,
                name=name or hook.__name__,
            )
        )

    def register_core_hook(
        self,
        event_type: str,
        tool_pattern: str,
        hook: CoreHookFunction,
        timeout: float | None = None,
        name: str | None = None,
    ) -> None:
        """Register a core-style hook.

        Args:
            event_type: Event type (PreToolUse, PostToolUse, etc.)
            tool_pattern: Tool name pattern ("*" for all)
            hook: Core-style hook function
            timeout: Optional custom timeout
            name: Optional hook name for observability
        """
        self._hooks.append(
            RegisteredHook(
                hook_type="core",
                event_type=event_type,
                tool_pattern=tool_pattern,
                hook_fn=hook,
                timeout=timeout or self._default_timeout,
                name=name or hook.__name__,
            )
        )

    def get_hooks(
        self,
        event_type: str,
        tool_name: str,
    ) -> list[RegisteredHook]:
        """Get hooks matching event and tool.

        Args:
            event_type: Event type
            tool_name: Tool name

        Returns:
            List of matching hooks in registration order
        """
        matching = []
        for hook in self._hooks:
            if hook.event_type != event_type:
                continue
            if hook.tool_pattern == "*" or hook.tool_pattern == tool_name:
                matching.append(hook)
        return matching

    async def execute_hooks(
        self,
        event_type: str,
        tool_name: str,
        input_data: dict[str, Any],
        tool_use_id: str | None,
        context: HookContext,
    ) -> SDKHookResult:
        """Execute all matching hooks.

        Args:
            event_type: Event type
            tool_name: Tool name
            input_data: Input data in SDK format
            tool_use_id: Tool use identifier
            context: Hook context

        Returns:
            Combined result (stops on first deny)

        Raises:
            asyncio.TimeoutError: If a hook exceeds its timeout
        """
        hooks = self.get_hooks(event_type, tool_name)
        current_input = input_data.copy()

        for registered_hook in hooks:
            start_time = time.monotonic()

            try:
                with self._create_trace_span(registered_hook, event_type, tool_name):
                    if registered_hook.hook_type == "sdk":
                        # Execute SDK hook directly
                        result = await asyncio.wait_for(
                            registered_hook.hook_fn(
                                current_input,
                                tool_use_id or "",
                                self._adapter._core_context_to_sdk(context),
                            ),
                            timeout=registered_hook.timeout,
                        )
                    else:
                        # Wrap and execute core hook
                        wrapped = self._adapter.wrap_core_hook(registered_hook.hook_fn)
                        result = await asyncio.wait_for(
                            wrapped(
                                current_input,
                                tool_use_id or "",
                                self._adapter._core_context_to_sdk(context),
                            ),
                            timeout=registered_hook.timeout,
                        )

                # Record metrics
                duration_ms = (time.monotonic() - start_time) * 1000
                self._record_hook_metric(
                    registered_hook,
                    event_type,
                    tool_name,
                    result.allowed,
                    duration_ms,
                )

                if not result.allowed:
                    self._record_hook_denial(
                        registered_hook,
                        event_type,
                        tool_name,
                        result.reason,
                    )
                    return cast(SDKHookResult, result)

                # Apply modifications for next hook
                if result.modified_input:
                    current_input.update(result.modified_input)

            except TimeoutError:
                self._record_hook_timeout(registered_hook, event_type, tool_name)
                raise

        # Build final result with any modifications
        if current_input != input_data:
            return SDKHookResult.allow(modified_input=current_input)
        return SDKHookResult.allow()

    @contextmanager
    def _create_trace_span(
        self,
        hook: RegisteredHook,
        event_type: str,
        tool_name: str,
    ) -> Generator[None, None, None]:
        """Create OpenTelemetry trace span for hook execution.

        Args:
            hook: The registered hook
            event_type: Event type
            tool_name: Tool name

        Yields:
            None
        """
        try:
            from mcp_server_langgraph.observability.telemetry import tracer

            with tracer.start_as_current_span(
                f"hook.{event_type}.{hook.name}",
                attributes={
                    "hook.name": hook.name or "unknown",
                    "hook.type": hook.hook_type,
                    "hook.event_type": event_type,
                    "hook.tool_pattern": hook.tool_pattern,
                    "hook.tool_name": tool_name,
                },
            ):
                yield
        except ImportError:
            # Telemetry not available
            yield

    def _record_hook_metric(
        self,
        hook: RegisteredHook,
        event_type: str,
        tool_name: str,
        allowed: bool,
        duration_ms: float,
    ) -> None:
        """Record Prometheus metrics for hook execution.

        Args:
            hook: The registered hook
            event_type: Event type
            tool_name: Tool name
            allowed: Whether the hook allowed the operation
            duration_ms: Execution duration in milliseconds
        """
        _init_hook_metrics()

        if _hook_executions_counter is not None:
            result = "allowed" if allowed else "denied"
            _hook_executions_counter.labels(
                hook_name=hook.name or "unknown",
                event_type=event_type,
                tool_name=tool_name,
                result=result,
            ).inc()

        if _hook_duration_histogram is not None:
            _hook_duration_histogram.labels(
                hook_name=hook.name or "unknown",
                event_type=event_type,
            ).observe(duration_ms)

    def _record_hook_denial(
        self,
        hook: RegisteredHook,
        event_type: str,
        tool_name: str,
        reason: str | None,
    ) -> None:
        """Record metrics for hook denial.

        Args:
            hook: The registered hook
            event_type: Event type
            tool_name: Tool name
            reason: Denial reason
        """
        _init_hook_metrics()

        if _hook_denials_counter is not None:
            _hook_denials_counter.labels(
                hook_name=hook.name or "unknown",
                event_type=event_type,
                tool_name=tool_name,
            ).inc()

    def _record_hook_timeout(
        self,
        hook: RegisteredHook,
        event_type: str,
        tool_name: str,
    ) -> None:
        """Record metrics for hook timeout.

        Args:
            hook: The registered hook
            event_type: Event type
            tool_name: Tool name
        """
        _init_hook_metrics()

        if _hook_timeouts_counter is not None:
            _hook_timeouts_counter.labels(
                hook_name=hook.name or "unknown",
                event_type=event_type,
                tool_name=tool_name,
            ).inc()


__all__ = [
    "UnifiedHookAdapter",
    "UnifiedHookRegistry",
    "RegisteredHook",
]
