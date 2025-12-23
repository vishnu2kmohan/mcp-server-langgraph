"""
Tests for unified hook adapter bridging SDK and core hook systems.

The adapter allows hooks written for either system to work with both,
providing a unified interface while maintaining backward compatibility.
"""

from __future__ import annotations

import asyncio
import gc
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.sdk]


@pytest.mark.xdist_group(name="sdk_hook_adapter")
class TestUnifiedHookAdapter:
    """Tests for UnifiedHookAdapter that bridges SDK and core hooks."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_adapter_converts_sdk_hook_to_core_format(self) -> None:
        """SDK hooks should work with core hook dispatcher via adapter."""
        from mcp_server_langgraph.sdk.hook_adapter import UnifiedHookAdapter
        from mcp_server_langgraph.sdk.hooks import HookResult as SDKHookResult
        from mcp_server_langgraph.core.hooks import (
            HookContext,
            PreToolUseInput,
        )

        # SDK-style hook function
        async def sdk_hook(
            input_data: dict[str, Any],
            tool_use_id: str,
            context: dict[str, Any],
        ) -> SDKHookResult:
            return SDKHookResult.allow()

        adapter = UnifiedHookAdapter()
        wrapped = adapter.wrap_sdk_hook(sdk_hook)

        # Call with core-style arguments
        core_context = HookContext(session_id="test-session", user_id="user-1")
        core_input = PreToolUseInput(
            tool_name="Bash",
            tool_input={"command": "ls"},
            tool_use_id="tool-123",
        )

        result = await wrapped(core_input, "tool-123", core_context)

        # Should return core-compatible result
        assert result.behavior == "allow"

    @pytest.mark.asyncio
    async def test_adapter_converts_core_hook_to_sdk_format(self) -> None:
        """Core hooks should work with SDK registry via adapter."""
        from mcp_server_langgraph.sdk.hook_adapter import UnifiedHookAdapter
        from mcp_server_langgraph.core.hooks import (
            HookContext,
            PreToolUseInput,
            HookResult as CoreHookResult,
        )

        # Core-style hook function
        async def core_hook(
            input_data: PreToolUseInput,
            tool_use_id: str | None,
            context: HookContext,
        ) -> CoreHookResult:
            return CoreHookResult(behavior="allow")

        adapter = UnifiedHookAdapter()
        wrapped = adapter.wrap_core_hook(core_hook)

        # Call with SDK-style arguments
        sdk_input = {"tool_name": "Bash", "tool_input": {"command": "ls"}}
        sdk_context = {"session_id": "test-session", "user_id": "user-1"}

        result = await wrapped(sdk_input, "tool-123", sdk_context)

        # Should return SDK-compatible result
        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_adapter_preserves_deny_with_reason(self) -> None:
        """Deny results should preserve the reason across formats."""
        from mcp_server_langgraph.sdk.hook_adapter import UnifiedHookAdapter
        from mcp_server_langgraph.sdk.hooks import HookResult as SDKHookResult
        from mcp_server_langgraph.core.hooks import HookContext, PreToolUseInput

        async def sdk_deny_hook(
            input_data: dict[str, Any],
            tool_use_id: str,
            context: dict[str, Any],
        ) -> SDKHookResult:
            return SDKHookResult.deny("Operation blocked for security")

        adapter = UnifiedHookAdapter()
        wrapped = adapter.wrap_sdk_hook(sdk_deny_hook)

        core_context = HookContext(session_id="test-session")
        core_input = PreToolUseInput(tool_name="Write", tool_input={})

        result = await wrapped(core_input, "tool-123", core_context)

        assert result.behavior == "deny"
        assert result.message == "Operation blocked for security"

    @pytest.mark.asyncio
    async def test_adapter_preserves_modified_input(self) -> None:
        """Modified input should be preserved when converting formats."""
        from mcp_server_langgraph.sdk.hook_adapter import UnifiedHookAdapter
        from mcp_server_langgraph.sdk.hooks import HookResult as SDKHookResult
        from mcp_server_langgraph.core.hooks import HookContext, PreToolUseInput

        async def sdk_modify_hook(
            input_data: dict[str, Any],
            tool_use_id: str,
            context: dict[str, Any],
        ) -> SDKHookResult:
            modified = {"tool_input": {"command": "ls -la"}}
            return SDKHookResult.allow(modified_input=modified)

        adapter = UnifiedHookAdapter()
        wrapped = adapter.wrap_sdk_hook(sdk_modify_hook)

        core_context = HookContext(session_id="test-session")
        core_input = PreToolUseInput(tool_name="Bash", tool_input={"command": "ls"})

        result = await wrapped(core_input, "tool-123", core_context)

        assert result.behavior == "allow"
        assert result.updated_input == {"command": "ls -la"}

    @pytest.mark.asyncio
    async def test_adapter_handles_context_conversion(self) -> None:
        """Context should be properly converted between formats."""
        from mcp_server_langgraph.sdk.hook_adapter import UnifiedHookAdapter
        from mcp_server_langgraph.sdk.hooks import HookResult as SDKHookResult
        from mcp_server_langgraph.core.hooks import HookContext, PreToolUseInput

        captured_context: dict[str, Any] = {}

        async def sdk_hook(
            input_data: dict[str, Any],
            tool_use_id: str,
            context: dict[str, Any],
        ) -> SDKHookResult:
            captured_context.update(context)
            return SDKHookResult.allow()

        adapter = UnifiedHookAdapter()
        wrapped = adapter.wrap_sdk_hook(sdk_hook)

        core_context = HookContext(
            session_id="sess-123",
            user_id="user-456",
            request_id="req-789",
            metadata={"custom": "value"},
        )
        core_input = PreToolUseInput(tool_name="Read", tool_input={})

        await wrapped(core_input, "tool-123", core_context)

        # Verify context was converted to dict format
        assert captured_context["session_id"] == "sess-123"
        assert captured_context["user_id"] == "user-456"
        assert captured_context["request_id"] == "req-789"
        assert captured_context["metadata"]["custom"] == "value"


@pytest.mark.xdist_group(name="sdk_hook_adapter")
class TestUnifiedHookRegistry:
    """Tests for unified hook registry that accepts both hook formats."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_registry_accepts_sdk_hooks(self) -> None:
        """Registry should accept SDK-style hooks."""
        from mcp_server_langgraph.sdk.hook_adapter import UnifiedHookRegistry
        from mcp_server_langgraph.sdk.hooks import HookResult as SDKHookResult

        registry = UnifiedHookRegistry()

        async def sdk_hook(
            input_data: dict[str, Any],
            tool_use_id: str,
            context: dict[str, Any],
        ) -> SDKHookResult:
            return SDKHookResult.allow()

        registry.register_sdk_hook("PreToolUse", "*", sdk_hook)

        hooks = registry.get_hooks("PreToolUse", "Bash")
        assert len(hooks) == 1

    @pytest.mark.asyncio
    async def test_registry_accepts_core_hooks(self) -> None:
        """Registry should accept core-style hooks."""
        from mcp_server_langgraph.sdk.hook_adapter import UnifiedHookRegistry
        from mcp_server_langgraph.core.hooks import (
            HookContext,
            PreToolUseInput,
            HookResult as CoreHookResult,
        )

        registry = UnifiedHookRegistry()

        async def core_hook(
            input_data: PreToolUseInput,
            tool_use_id: str | None,
            context: HookContext,
        ) -> CoreHookResult:
            return CoreHookResult(behavior="allow")

        registry.register_core_hook("PreToolUse", "*", core_hook)

        hooks = registry.get_hooks("PreToolUse", "Bash")
        assert len(hooks) == 1

    @pytest.mark.asyncio
    async def test_registry_executes_mixed_hooks_in_order(self) -> None:
        """Mixed SDK and core hooks should execute in registration order."""
        from mcp_server_langgraph.sdk.hook_adapter import UnifiedHookRegistry
        from mcp_server_langgraph.sdk.hooks import HookResult as SDKHookResult
        from mcp_server_langgraph.core.hooks import (
            HookContext,
            PreToolUseInput,
            HookResult as CoreHookResult,
        )

        registry = UnifiedHookRegistry()
        execution_order: list[str] = []

        async def sdk_hook_1(
            input_data: dict[str, Any],
            tool_use_id: str,
            context: dict[str, Any],
        ) -> SDKHookResult:
            execution_order.append("sdk_1")
            return SDKHookResult.allow()

        async def core_hook_2(
            input_data: PreToolUseInput,
            tool_use_id: str | None,
            context: HookContext,
        ) -> CoreHookResult:
            execution_order.append("core_2")
            return CoreHookResult(behavior="allow")

        async def sdk_hook_3(
            input_data: dict[str, Any],
            tool_use_id: str,
            context: dict[str, Any],
        ) -> SDKHookResult:
            execution_order.append("sdk_3")
            return SDKHookResult.allow()

        registry.register_sdk_hook("PreToolUse", "*", sdk_hook_1)
        registry.register_core_hook("PreToolUse", "*", core_hook_2)
        registry.register_sdk_hook("PreToolUse", "*", sdk_hook_3)

        context = HookContext(session_id="test")
        await registry.execute_hooks(
            "PreToolUse",
            "Bash",
            {"tool_name": "Bash", "tool_input": {}},
            "tool-123",
            context,
        )

        assert execution_order == ["sdk_1", "core_2", "sdk_3"]

    @pytest.mark.asyncio
    async def test_registry_stops_on_first_deny(self) -> None:
        """Execution should stop on first deny result."""
        from mcp_server_langgraph.sdk.hook_adapter import UnifiedHookRegistry
        from mcp_server_langgraph.sdk.hooks import HookResult as SDKHookResult
        from mcp_server_langgraph.core.hooks import HookContext

        registry = UnifiedHookRegistry()
        execution_order: list[str] = []

        async def hook_allow(
            input_data: dict[str, Any],
            tool_use_id: str,
            context: dict[str, Any],
        ) -> SDKHookResult:
            execution_order.append("allow")
            return SDKHookResult.allow()

        async def hook_deny(
            input_data: dict[str, Any],
            tool_use_id: str,
            context: dict[str, Any],
        ) -> SDKHookResult:
            execution_order.append("deny")
            return SDKHookResult.deny("Blocked")

        async def hook_after(
            input_data: dict[str, Any],
            tool_use_id: str,
            context: dict[str, Any],
        ) -> SDKHookResult:
            execution_order.append("after")
            return SDKHookResult.allow()

        registry.register_sdk_hook("PreToolUse", "*", hook_allow)
        registry.register_sdk_hook("PreToolUse", "*", hook_deny)
        registry.register_sdk_hook("PreToolUse", "*", hook_after)

        context = HookContext(session_id="test")
        result = await registry.execute_hooks(
            "PreToolUse",
            "Bash",
            {"tool_name": "Bash", "tool_input": {}},
            "tool-123",
            context,
        )

        assert execution_order == ["allow", "deny"]  # "after" not executed
        assert not result.allowed
        assert result.reason == "Blocked"


@pytest.mark.xdist_group(name="sdk_hook_adapter")
class TestHookTypeSupport:
    """Tests for all hook types in unified registry."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_registry_supports_post_tool_use(self) -> None:
        """PostToolUse hooks should be supported."""
        from mcp_server_langgraph.sdk.hook_adapter import UnifiedHookRegistry
        from mcp_server_langgraph.sdk.hooks import HookResult as SDKHookResult
        from mcp_server_langgraph.core.hooks import HookContext

        registry = UnifiedHookRegistry()
        hook_called = False

        async def post_hook(
            input_data: dict[str, Any],
            tool_use_id: str,
            context: dict[str, Any],
        ) -> SDKHookResult:
            nonlocal hook_called
            hook_called = True
            assert input_data.get("tool_output") == "result"
            assert input_data.get("is_error") is False
            return SDKHookResult.allow()

        registry.register_sdk_hook("PostToolUse", "*", post_hook)

        context = HookContext(session_id="test")
        await registry.execute_hooks(
            "PostToolUse",
            "Bash",
            {
                "tool_name": "Bash",
                "tool_input": {"command": "ls"},
                "tool_output": "result",
                "is_error": False,
            },
            "tool-123",
            context,
        )

        assert hook_called

    @pytest.mark.asyncio
    async def test_registry_supports_user_prompt_submit(self) -> None:
        """UserPromptSubmit hooks should be supported."""
        from mcp_server_langgraph.sdk.hook_adapter import UnifiedHookRegistry
        from mcp_server_langgraph.sdk.hooks import HookResult as SDKHookResult
        from mcp_server_langgraph.core.hooks import HookContext

        registry = UnifiedHookRegistry()
        captured_prompt: str = ""

        async def prompt_hook(
            input_data: dict[str, Any],
            tool_use_id: str,
            context: dict[str, Any],
        ) -> SDKHookResult:
            nonlocal captured_prompt
            captured_prompt = input_data.get("prompt", "")
            return SDKHookResult.allow()

        registry.register_sdk_hook("UserPromptSubmit", "*", prompt_hook)

        context = HookContext(session_id="test")
        await registry.execute_hooks(
            "UserPromptSubmit",
            "*",  # No tool name for prompt hooks
            {"prompt": "Hello, world!"},
            None,
            context,
        )

        assert captured_prompt == "Hello, world!"

    @pytest.mark.asyncio
    async def test_registry_supports_stop_hook(self) -> None:
        """Stop hooks should be supported."""
        from mcp_server_langgraph.sdk.hook_adapter import UnifiedHookRegistry
        from mcp_server_langgraph.sdk.hooks import HookResult as SDKHookResult
        from mcp_server_langgraph.core.hooks import HookContext

        registry = UnifiedHookRegistry()
        stop_called = False

        async def stop_hook(
            input_data: dict[str, Any],
            tool_use_id: str,
            context: dict[str, Any],
        ) -> SDKHookResult:
            nonlocal stop_called
            stop_called = True
            assert input_data.get("reason") == "completed"
            return SDKHookResult.allow()

        registry.register_sdk_hook("Stop", "*", stop_hook)

        context = HookContext(session_id="test")
        await registry.execute_hooks(
            "Stop",
            "*",
            {"reason": "completed", "is_error": False},
            None,
            context,
        )

        assert stop_called


@pytest.mark.xdist_group(name="sdk_hook_adapter")
class TestHookTimeout:
    """Tests for hook timeout handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_hook_timeout_raises_error(self) -> None:
        """Hooks that exceed timeout should raise TimeoutError."""
        from mcp_server_langgraph.sdk.hook_adapter import UnifiedHookRegistry
        from mcp_server_langgraph.sdk.hooks import HookResult as SDKHookResult
        from mcp_server_langgraph.core.hooks import HookContext

        registry = UnifiedHookRegistry(default_timeout=0.1)

        async def slow_hook(
            input_data: dict[str, Any],
            tool_use_id: str,
            context: dict[str, Any],
        ) -> SDKHookResult:
            await asyncio.sleep(0.5)
            return SDKHookResult.allow()

        registry.register_sdk_hook("PreToolUse", "*", slow_hook)

        context = HookContext(session_id="test")

        with pytest.raises(asyncio.TimeoutError):
            await registry.execute_hooks(
                "PreToolUse",
                "Bash",
                {"tool_name": "Bash", "tool_input": {}},
                "tool-123",
                context,
            )

    @pytest.mark.asyncio
    async def test_hook_timeout_can_be_configured(self) -> None:
        """Timeout should be configurable per hook."""
        from mcp_server_langgraph.sdk.hook_adapter import UnifiedHookRegistry
        from mcp_server_langgraph.sdk.hooks import HookResult as SDKHookResult
        from mcp_server_langgraph.core.hooks import HookContext

        registry = UnifiedHookRegistry(default_timeout=0.05)

        async def slow_but_allowed_hook(
            input_data: dict[str, Any],
            tool_use_id: str,
            context: dict[str, Any],
        ) -> SDKHookResult:
            await asyncio.sleep(0.1)
            return SDKHookResult.allow()

        # Register with custom timeout
        registry.register_sdk_hook("PreToolUse", "*", slow_but_allowed_hook, timeout=0.5)

        context = HookContext(session_id="test")

        # Should not timeout with custom timeout
        result = await registry.execute_hooks(
            "PreToolUse",
            "Bash",
            {"tool_name": "Bash", "tool_input": {}},
            "tool-123",
            context,
        )

        assert result.allowed


@pytest.mark.xdist_group(name="sdk_hook_adapter")
class TestHookObservability:
    """Tests for hook observability (metrics and tracing)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_hook_execution_emits_metrics(self) -> None:
        """Hook execution should emit Prometheus metrics."""
        from mcp_server_langgraph.sdk.hook_adapter import UnifiedHookRegistry
        from mcp_server_langgraph.sdk.hooks import HookResult as SDKHookResult
        from mcp_server_langgraph.core.hooks import HookContext

        registry = UnifiedHookRegistry()

        async def my_hook(
            input_data: dict[str, Any],
            tool_use_id: str,
            context: dict[str, Any],
        ) -> SDKHookResult:
            return SDKHookResult.allow()

        registry.register_sdk_hook("PreToolUse", "*", my_hook)

        context = HookContext(session_id="test")

        with patch.object(registry, "_record_hook_metric") as mock_metric:
            await registry.execute_hooks(
                "PreToolUse",
                "Bash",
                {"tool_name": "Bash", "tool_input": {}},
                "tool-123",
                context,
            )

            mock_metric.assert_called()

    @pytest.mark.asyncio
    async def test_hook_execution_creates_trace_span(self) -> None:
        """Hook execution should create OpenTelemetry trace spans."""
        from mcp_server_langgraph.sdk.hook_adapter import UnifiedHookRegistry
        from mcp_server_langgraph.sdk.hooks import HookResult as SDKHookResult
        from mcp_server_langgraph.core.hooks import HookContext

        registry = UnifiedHookRegistry()

        async def my_hook(
            input_data: dict[str, Any],
            tool_use_id: str,
            context: dict[str, Any],
        ) -> SDKHookResult:
            return SDKHookResult.allow()

        registry.register_sdk_hook("PreToolUse", "*", my_hook)

        context = HookContext(session_id="test")

        with patch.object(registry, "_create_trace_span") as mock_span:
            mock_span.return_value.__enter__ = MagicMock(return_value=MagicMock())
            mock_span.return_value.__exit__ = MagicMock(return_value=None)

            await registry.execute_hooks(
                "PreToolUse",
                "Bash",
                {"tool_name": "Bash", "tool_input": {}},
                "tool-123",
                context,
            )

            mock_span.assert_called()

    @pytest.mark.asyncio
    async def test_hook_deny_records_reason_in_metrics(self) -> None:
        """Denied hooks should record the reason in metrics."""
        from mcp_server_langgraph.sdk.hook_adapter import UnifiedHookRegistry
        from mcp_server_langgraph.sdk.hooks import HookResult as SDKHookResult
        from mcp_server_langgraph.core.hooks import HookContext

        registry = UnifiedHookRegistry()

        async def deny_hook(
            input_data: dict[str, Any],
            tool_use_id: str,
            context: dict[str, Any],
        ) -> SDKHookResult:
            return SDKHookResult.deny("Security violation")

        registry.register_sdk_hook("PreToolUse", "Bash", deny_hook)

        context = HookContext(session_id="test")

        with patch.object(registry, "_record_hook_denial") as mock_denial:
            await registry.execute_hooks(
                "PreToolUse",
                "Bash",
                {"tool_name": "Bash", "tool_input": {}},
                "tool-123",
                context,
            )

            mock_denial.assert_called_once()
            call_args = mock_denial.call_args
            assert "Security violation" in str(call_args)
