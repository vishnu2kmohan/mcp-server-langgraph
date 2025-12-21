"""
Tests for hook registry and dispatcher (Phase 1.2)

Following TDD: Write tests FIRST, then implementation.

This module tests the HookRegistry which manages registration and dispatching
of hooks for tool execution and agent operations.

The registry provides:
- Registration of hooks for specific events
- Dispatching hooks in order with timeout enforcement
- Combining results from multiple hooks
- Thread-safe access for concurrent operations
"""

from __future__ import annotations

import asyncio
import gc
from typing import Any

import pytest

# pytestmark placed after all imports
pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="hook_registry")
class TestHookRegistry:
    """Test HookRegistry for hook management."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_registry_is_singleton(self) -> None:
        """HookRegistry should use singleton pattern for global access."""
        from mcp_server_langgraph.core.hook_registry import get_hook_registry

        registry1 = get_hook_registry()
        registry2 = get_hook_registry()
        assert registry1 is registry2

    def test_registry_can_be_reset(self) -> None:
        """HookRegistry should support reset for testing."""
        from mcp_server_langgraph.core.hook_registry import (
            get_hook_registry,
            reset_hook_registry,
        )

        registry1 = get_hook_registry()
        reset_hook_registry()
        registry2 = get_hook_registry()
        assert registry1 is not registry2

    def test_registry_register_hook_for_event(self) -> None:
        """Registry should allow registering hooks for events."""
        from mcp_server_langgraph.core.hook_registry import (
            HookRegistry,
        )
        from mcp_server_langgraph.core.hooks import (
            HookEvent,
            HookMatcher,
            HookResult,
        )

        async def my_hook(input_data: Any, tool_use_id: str | None, context: Any) -> HookResult:
            return HookResult()

        registry = HookRegistry()
        matcher = HookMatcher(hooks=[my_hook])
        registry.register(HookEvent.PRE_TOOL_USE, matcher)

        assert len(registry.get_matchers(HookEvent.PRE_TOOL_USE)) == 1

    def test_registry_get_matchers_returns_empty_list_for_unregistered(self) -> None:
        """Registry should return empty list for events with no hooks."""
        from mcp_server_langgraph.core.hook_registry import HookRegistry
        from mcp_server_langgraph.core.hooks import HookEvent

        registry = HookRegistry()
        matchers = registry.get_matchers(HookEvent.POST_TOOL_USE)
        assert matchers == []

    def test_registry_multiple_matchers_for_same_event(self) -> None:
        """Registry should support multiple matchers for same event."""
        from mcp_server_langgraph.core.hook_registry import HookRegistry
        from mcp_server_langgraph.core.hooks import (
            HookEvent,
            HookMatcher,
            HookResult,
        )

        async def hook1(input_data: Any, tool_use_id: str | None, context: Any) -> HookResult:
            return HookResult()

        async def hook2(input_data: Any, tool_use_id: str | None, context: Any) -> HookResult:
            return HookResult()

        registry = HookRegistry()
        registry.register(HookEvent.PRE_TOOL_USE, HookMatcher(matcher="Bash", hooks=[hook1]))
        registry.register(HookEvent.PRE_TOOL_USE, HookMatcher(matcher="Write", hooks=[hook2]))

        matchers = registry.get_matchers(HookEvent.PRE_TOOL_USE)
        assert len(matchers) == 2

    def test_registry_unregister_all_for_event(self) -> None:
        """Registry should allow clearing all hooks for an event."""
        from mcp_server_langgraph.core.hook_registry import HookRegistry
        from mcp_server_langgraph.core.hooks import (
            HookEvent,
            HookMatcher,
            HookResult,
        )

        async def my_hook(input_data: Any, tool_use_id: str | None, context: Any) -> HookResult:
            return HookResult()

        registry = HookRegistry()
        registry.register(HookEvent.PRE_TOOL_USE, HookMatcher(hooks=[my_hook]))
        registry.unregister_all(HookEvent.PRE_TOOL_USE)

        assert len(registry.get_matchers(HookEvent.PRE_TOOL_USE)) == 0

    def test_registry_clear_all(self) -> None:
        """Registry should allow clearing all hooks."""
        from mcp_server_langgraph.core.hook_registry import HookRegistry
        from mcp_server_langgraph.core.hooks import (
            HookEvent,
            HookMatcher,
            HookResult,
        )

        async def my_hook(input_data: Any, tool_use_id: str | None, context: Any) -> HookResult:
            return HookResult()

        registry = HookRegistry()
        registry.register(HookEvent.PRE_TOOL_USE, HookMatcher(hooks=[my_hook]))
        registry.register(HookEvent.POST_TOOL_USE, HookMatcher(hooks=[my_hook]))
        registry.clear()

        assert len(registry.get_matchers(HookEvent.PRE_TOOL_USE)) == 0
        assert len(registry.get_matchers(HookEvent.POST_TOOL_USE)) == 0


@pytest.mark.xdist_group(name="hook_registry")
class TestHookDispatcher:
    """Test HookDispatcher for executing hooks."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_dispatcher_executes_matching_hooks(self) -> None:
        """Dispatcher should execute hooks that match the tool."""
        from mcp_server_langgraph.core.hook_registry import HookDispatcher, HookRegistry
        from mcp_server_langgraph.core.hooks import (
            HookContext,
            HookEvent,
            HookMatcher,
            HookResult,
            PreToolUseInput,
        )

        called = []

        async def my_hook(input_data: Any, tool_use_id: str | None, context: Any) -> HookResult:
            called.append(input_data.tool_name)
            return HookResult()

        registry = HookRegistry()
        registry.register(HookEvent.PRE_TOOL_USE, HookMatcher(matcher="Bash", hooks=[my_hook]))

        dispatcher = HookDispatcher(registry)
        await dispatcher.dispatch(
            HookEvent.PRE_TOOL_USE,
            PreToolUseInput(tool_name="Bash", tool_input={}),
            None,
            HookContext(session_id="test"),
        )

        assert called == ["Bash"]

    @pytest.mark.asyncio
    async def test_dispatcher_skips_non_matching_hooks(self) -> None:
        """Dispatcher should skip hooks that don't match the tool."""
        from mcp_server_langgraph.core.hook_registry import HookDispatcher, HookRegistry
        from mcp_server_langgraph.core.hooks import (
            HookContext,
            HookEvent,
            HookMatcher,
            HookResult,
            PreToolUseInput,
        )

        called = []

        async def my_hook(input_data: Any, tool_use_id: str | None, context: Any) -> HookResult:
            called.append(input_data.tool_name)
            return HookResult()

        registry = HookRegistry()
        registry.register(HookEvent.PRE_TOOL_USE, HookMatcher(matcher="Bash", hooks=[my_hook]))

        dispatcher = HookDispatcher(registry)
        await dispatcher.dispatch(
            HookEvent.PRE_TOOL_USE,
            PreToolUseInput(tool_name="Write", tool_input={}),  # Different tool
            None,
            HookContext(session_id="test"),
        )

        assert called == []  # Hook not called

    @pytest.mark.asyncio
    async def test_dispatcher_returns_combined_result(self) -> None:
        """Dispatcher should combine results from multiple hooks."""
        from mcp_server_langgraph.core.hook_registry import HookDispatcher, HookRegistry
        from mcp_server_langgraph.core.hooks import (
            HookContext,
            HookEvent,
            HookMatcher,
            HookResult,
            PreToolUseInput,
        )

        async def add_message(input_data: Any, tool_use_id: str | None, context: Any) -> HookResult:
            return HookResult(system_message="Message from hook 1")

        async def modify_input(input_data: Any, tool_use_id: str | None, context: Any) -> HookResult:
            return HookResult(updated_input={"modified": True})

        registry = HookRegistry()
        registry.register(HookEvent.PRE_TOOL_USE, HookMatcher(hooks=[add_message, modify_input]))

        dispatcher = HookDispatcher(registry)
        result = await dispatcher.dispatch(
            HookEvent.PRE_TOOL_USE,
            PreToolUseInput(tool_name="Test", tool_input={}),
            None,
            HookContext(session_id="test"),
        )

        assert result.should_proceed is True
        # Last non-None values should be used
        assert result.updated_input == {"modified": True}

    @pytest.mark.asyncio
    async def test_dispatcher_stops_on_deny(self) -> None:
        """Dispatcher should stop executing hooks when one denies."""
        from mcp_server_langgraph.core.hook_registry import HookDispatcher, HookRegistry
        from mcp_server_langgraph.core.hooks import (
            HookContext,
            HookEvent,
            HookMatcher,
            HookResult,
            PreToolUseInput,
        )

        called = []

        async def deny_hook(input_data: Any, tool_use_id: str | None, context: Any) -> HookResult:
            called.append("deny")
            return HookResult(behavior="deny", message="Blocked")

        async def allow_hook(input_data: Any, tool_use_id: str | None, context: Any) -> HookResult:
            called.append("allow")
            return HookResult()

        registry = HookRegistry()
        registry.register(HookEvent.PRE_TOOL_USE, HookMatcher(hooks=[deny_hook, allow_hook]))

        dispatcher = HookDispatcher(registry)
        result = await dispatcher.dispatch(
            HookEvent.PRE_TOOL_USE,
            PreToolUseInput(tool_name="Test", tool_input={}),
            None,
            HookContext(session_id="test"),
        )

        assert result.behavior == "deny"
        assert result.message == "Blocked"
        assert called == ["deny"]  # Second hook not called

    @pytest.mark.asyncio
    async def test_dispatcher_respects_timeout(self) -> None:
        """Dispatcher should enforce timeout on hook execution."""
        from mcp_server_langgraph.core.hook_registry import HookDispatcher, HookRegistry
        from mcp_server_langgraph.core.hooks import (
            HookContext,
            HookEvent,
            HookMatcher,
            HookResult,
            PreToolUseInput,
        )

        async def slow_hook(input_data: Any, tool_use_id: str | None, context: Any) -> HookResult:
            await asyncio.sleep(0.5)  # Longer than 0.1s timeout
            return HookResult()

        registry = HookRegistry()
        registry.register(HookEvent.PRE_TOOL_USE, HookMatcher(hooks=[slow_hook], timeout=0.1))

        dispatcher = HookDispatcher(registry)

        with pytest.raises(asyncio.TimeoutError):
            await dispatcher.dispatch(
                HookEvent.PRE_TOOL_USE,
                PreToolUseInput(tool_name="Test", tool_input={}),
                None,
                HookContext(session_id="test"),
            )

    @pytest.mark.asyncio
    async def test_dispatcher_executes_hooks_in_order(self) -> None:
        """Dispatcher should execute hooks in registration order."""
        from mcp_server_langgraph.core.hook_registry import HookDispatcher, HookRegistry
        from mcp_server_langgraph.core.hooks import (
            HookContext,
            HookEvent,
            HookMatcher,
            HookResult,
            PreToolUseInput,
        )

        order = []

        async def hook1(input_data: Any, tool_use_id: str | None, context: Any) -> HookResult:
            order.append(1)
            return HookResult()

        async def hook2(input_data: Any, tool_use_id: str | None, context: Any) -> HookResult:
            order.append(2)
            return HookResult()

        async def hook3(input_data: Any, tool_use_id: str | None, context: Any) -> HookResult:
            order.append(3)
            return HookResult()

        registry = HookRegistry()
        registry.register(HookEvent.PRE_TOOL_USE, HookMatcher(hooks=[hook1, hook2, hook3]))

        dispatcher = HookDispatcher(registry)
        await dispatcher.dispatch(
            HookEvent.PRE_TOOL_USE,
            PreToolUseInput(tool_name="Test", tool_input={}),
            None,
            HookContext(session_id="test"),
        )

        assert order == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_dispatcher_passes_updated_input_to_next_hook(self) -> None:
        """Dispatcher should pass updated input from one hook to the next."""
        from mcp_server_langgraph.core.hook_registry import HookDispatcher, HookRegistry
        from mcp_server_langgraph.core.hooks import (
            HookContext,
            HookEvent,
            HookMatcher,
            HookResult,
            PreToolUseInput,
        )

        received_inputs = []

        async def add_field(input_data: Any, tool_use_id: str | None, context: Any) -> HookResult:
            received_inputs.append(dict(input_data.tool_input))
            updated = dict(input_data.tool_input)
            updated["added_by_hook1"] = True
            return HookResult(updated_input=updated)

        async def check_field(input_data: Any, tool_use_id: str | None, context: Any) -> HookResult:
            received_inputs.append(dict(input_data.tool_input))
            return HookResult()

        registry = HookRegistry()
        registry.register(HookEvent.PRE_TOOL_USE, HookMatcher(hooks=[add_field, check_field]))

        dispatcher = HookDispatcher(registry)
        await dispatcher.dispatch(
            HookEvent.PRE_TOOL_USE,
            PreToolUseInput(tool_name="Test", tool_input={"original": True}),
            None,
            HookContext(session_id="test"),
        )

        # First hook sees original input
        assert received_inputs[0] == {"original": True}
        # Second hook sees updated input
        assert received_inputs[1] == {"original": True, "added_by_hook1": True}


@pytest.mark.xdist_group(name="hook_registry")
class TestDispatchPreToolUse:
    """Test convenience method for dispatching PreToolUse hooks."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_dispatch_pre_tool_use_convenience(self) -> None:
        """dispatch_pre_tool_use should be a convenience wrapper."""
        from mcp_server_langgraph.core.hook_registry import HookDispatcher, HookRegistry
        from mcp_server_langgraph.core.hooks import (
            HookContext,
            HookEvent,
            HookMatcher,
            HookResult,
        )

        called = False

        async def my_hook(input_data: Any, tool_use_id: str | None, context: Any) -> HookResult:
            nonlocal called
            called = True
            return HookResult()

        registry = HookRegistry()
        registry.register(HookEvent.PRE_TOOL_USE, HookMatcher(hooks=[my_hook]))

        dispatcher = HookDispatcher(registry)
        result = await dispatcher.dispatch_pre_tool_use(
            tool_name="Test",
            tool_input={"arg": "value"},
            tool_use_id="tool-123",
            context=HookContext(session_id="test"),
        )

        assert called is True
        assert result.should_proceed is True


@pytest.mark.xdist_group(name="hook_registry")
class TestDispatchPostToolUse:
    """Test convenience method for dispatching PostToolUse hooks."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_dispatch_post_tool_use_convenience(self) -> None:
        """dispatch_post_tool_use should be a convenience wrapper."""
        from mcp_server_langgraph.core.hook_registry import HookDispatcher, HookRegistry
        from mcp_server_langgraph.core.hooks import (
            HookContext,
            HookEvent,
            HookMatcher,
            HookResult,
        )

        received_output = None

        async def my_hook(input_data: Any, tool_use_id: str | None, context: Any) -> HookResult:
            nonlocal received_output
            received_output = input_data.tool_output
            return HookResult()

        registry = HookRegistry()
        registry.register(HookEvent.POST_TOOL_USE, HookMatcher(hooks=[my_hook]))

        dispatcher = HookDispatcher(registry)
        await dispatcher.dispatch_post_tool_use(
            tool_name="Test",
            tool_input={"arg": "value"},
            tool_output="Result",
            tool_use_id="tool-123",
            is_error=False,
            context=HookContext(session_id="test"),
        )

        assert received_output == "Result"


@pytest.mark.xdist_group(name="hook_registry")
class TestHookRegistryContextManager:
    """Test context manager support for temporary hook registration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_temporary_hooks_context_manager(self) -> None:
        """Context manager should allow temporary hook registration."""
        from mcp_server_langgraph.core.hook_registry import HookRegistry, temporary_hooks
        from mcp_server_langgraph.core.hooks import (
            HookEvent,
            HookMatcher,
            HookResult,
        )

        async def temp_hook(input_data: Any, tool_use_id: str | None, context: Any) -> HookResult:
            return HookResult()

        registry = HookRegistry()

        # Before context: no hooks
        assert len(registry.get_matchers(HookEvent.PRE_TOOL_USE)) == 0

        # Inside context: hook registered
        async with temporary_hooks(registry, {HookEvent.PRE_TOOL_USE: [HookMatcher(hooks=[temp_hook])]}):
            assert len(registry.get_matchers(HookEvent.PRE_TOOL_USE)) == 1

        # After context: hooks removed
        assert len(registry.get_matchers(HookEvent.PRE_TOOL_USE)) == 0
