"""
Integration tests for complete MCP handler hook flow.

Tests the full lifecycle:
- UserPromptSubmit -> PreToolUse -> Handler -> PostToolUse -> Stop

Verifies:
- UnifiedHookRegistry is used in handlers
- Feature flag enforcement works
- Hooks execute on all handlers (Chat, Execution, Agents)
"""

from __future__ import annotations

import gc
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_langgraph.core.hook_registry import HookRegistry, reset_hook_registry
from mcp_server_langgraph.core.hooks import (
    HookContext,
    HookEvent,
    HookMatcher,
    HookResult,
    PreToolUseInput,
    PostToolUseInput,
)

pytestmark = [pytest.mark.integration, pytest.mark.sdk, pytest.mark.hooks]


@pytest.fixture
def enable_sdk_hooks():
    """Enable SDK hooks feature flag for tests."""
    original = os.environ.get("FF_ENABLE_SDK_HOOKS")
    os.environ["FF_ENABLE_SDK_HOOKS"] = "true"
    # Reload feature flags by creating new instance
    yield
    if original is None:
        os.environ.pop("FF_ENABLE_SDK_HOOKS", None)
    else:
        os.environ["FF_ENABLE_SDK_HOOKS"] = original


@pytest.fixture
def disable_sdk_hooks():
    """Disable SDK hooks feature flag for tests."""
    original = os.environ.get("FF_ENABLE_SDK_HOOKS")
    os.environ["FF_ENABLE_SDK_HOOKS"] = "false"
    yield
    if original is None:
        os.environ.pop("FF_ENABLE_SDK_HOOKS", None)
    else:
        os.environ["FF_ENABLE_SDK_HOOKS"] = original


@pytest.fixture
def mock_auth():
    """Create mock auth middleware."""
    auth = MagicMock()
    auth.authorize = AsyncMock(return_value=True)
    return auth


@pytest.fixture
def mock_agent_graph():
    """Create mock agent graph."""
    graph = MagicMock()
    graph.ainvoke = AsyncMock(return_value={"messages": [MagicMock(content="Test response")]})
    graph.checkpointer = None
    return graph


@pytest.fixture
def fresh_hook_registry():
    """Create a fresh hook registry for tests."""
    reset_hook_registry()
    registry = HookRegistry()
    yield registry
    reset_hook_registry()


@pytest.mark.xdist_group(name="mcp_handler_hooks")
class TestMCPHandlerHookIntegration:
    """Integration tests for MCP handler hook dispatch."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_chat_handler_dispatches_pre_and_post_hooks(
        self, mock_auth, mock_agent_graph, enable_sdk_hooks, fresh_hook_registry
    ) -> None:
        """ChatToolHandler should dispatch PreToolUse and PostToolUse hooks."""
        from mcp_server_langgraph.mcp.handlers.chat import ChatToolHandler

        lifecycle_events: list[str] = []

        # Create hooks that track execution
        async def pre_hook(input_data: PreToolUseInput, tool_use_id: str | None, context: HookContext) -> HookResult:
            lifecycle_events.append("PreToolUse")
            return HookResult(behavior="allow")

        async def post_hook(input_data: PostToolUseInput, tool_use_id: str | None, context: HookContext) -> HookResult:
            lifecycle_events.append("PostToolUse")
            return HookResult(behavior="allow")

        # Register hooks using HookMatcher
        fresh_hook_registry.register(
            HookEvent.PRE_TOOL_USE,
            HookMatcher(hooks=[pre_hook], matcher=None),  # None matches all
        )
        fresh_hook_registry.register(HookEvent.POST_TOOL_USE, HookMatcher(hooks=[post_hook], matcher=None))

        handler = ChatToolHandler(
            auth=mock_auth,
            agent_graph=mock_agent_graph,
            hook_registry=fresh_hook_registry,
        )

        mock_span = MagicMock()
        mock_span.get_span_context.return_value = MagicMock(trace_id="test-trace")

        await handler.handle(
            arguments={
                "message": "Hello",
                "thread_id": "test-thread",
                "token": "test-jwt-token",
                "user_id": "test-user",
            },
            span=mock_span,
            user_id="test-user",
        )

        assert "PreToolUse" in lifecycle_events, "PreToolUse hook should have been called"
        assert "PostToolUse" in lifecycle_events, "PostToolUse hook should have been called"
        assert lifecycle_events.index("PreToolUse") < lifecycle_events.index("PostToolUse")

    @pytest.mark.asyncio
    async def test_execution_handler_dispatches_hooks(
        self, mock_auth, mock_agent_graph, enable_sdk_hooks, fresh_hook_registry
    ) -> None:
        """ExecutionToolHandler should dispatch hooks around code execution."""
        from mcp_server_langgraph.mcp.handlers.execution import ExecutionToolHandler

        lifecycle_events: list[str] = []

        async def pre_hook(input_data: PreToolUseInput, tool_use_id: str | None, context: HookContext) -> HookResult:
            lifecycle_events.append("PreToolUse")
            return HookResult(behavior="allow")

        async def post_hook(input_data: PostToolUseInput, tool_use_id: str | None, context: HookContext) -> HookResult:
            lifecycle_events.append("PostToolUse")
            return HookResult(behavior="allow")

        fresh_hook_registry.register(HookEvent.PRE_TOOL_USE, HookMatcher(hooks=[pre_hook], matcher=None))
        fresh_hook_registry.register(HookEvent.POST_TOOL_USE, HookMatcher(hooks=[post_hook], matcher=None))

        handler = ExecutionToolHandler(
            auth=mock_auth,
            agent_graph=mock_agent_graph,
            hook_registry=fresh_hook_registry,
        )

        mock_span = MagicMock()

        # Mock the execute_python tool
        with patch("mcp_server_langgraph.tools.code_execution_tools.execute_python") as mock_exec:
            mock_exec.invoke.return_value = "Success: 42"

            await handler.handle(
                arguments={"code": "print(42)", "timeout": 5},
                span=mock_span,
                user_id="test-user",
            )

        assert "PreToolUse" in lifecycle_events, "ExecutionToolHandler should dispatch PreToolUse"
        assert "PostToolUse" in lifecycle_events, "ExecutionToolHandler should dispatch PostToolUse"

    @pytest.mark.asyncio
    async def test_agents_handler_dispatches_hooks(
        self, mock_auth, mock_agent_graph, enable_sdk_hooks, fresh_hook_registry
    ) -> None:
        """AgentsToolHandler should dispatch hooks around orchestration."""
        from mcp_server_langgraph.mcp.handlers.agents import AgentsToolHandler
        from mcp_server_langgraph.agents import Orchestrator, ModelSelector

        lifecycle_events: list[str] = []

        async def pre_hook(input_data: PreToolUseInput, tool_use_id: str | None, context: HookContext) -> HookResult:
            lifecycle_events.append("PreToolUse")
            return HookResult(behavior="allow")

        async def post_hook(input_data: PostToolUseInput, tool_use_id: str | None, context: HookContext) -> HookResult:
            lifecycle_events.append("PostToolUse")
            return HookResult(behavior="allow")

        fresh_hook_registry.register(HookEvent.PRE_TOOL_USE, HookMatcher(hooks=[pre_hook], matcher=None))
        fresh_hook_registry.register(HookEvent.POST_TOOL_USE, HookMatcher(hooks=[post_hook], matcher=None))

        # Create mock orchestrator
        mock_orchestrator = MagicMock(spec=Orchestrator)
        mock_decomposition = MagicMock()
        mock_decomposition.original_task = "Test task"
        mock_decomposition.subtasks = []
        mock_decomposition.synthesis_instructions = "Synthesize"
        mock_orchestrator.decompose_task.return_value = mock_decomposition

        handler = AgentsToolHandler(
            auth=mock_auth,
            agent_graph=mock_agent_graph,
            orchestrator=mock_orchestrator,
            model_selector=ModelSelector(),
            hook_registry=fresh_hook_registry,
        )

        mock_span = MagicMock()

        await handler.handle(
            arguments={"operation": "decompose", "task": "Test task"},
            span=mock_span,
            user_id="test-user",
        )

        assert "PreToolUse" in lifecycle_events, "AgentsToolHandler should dispatch PreToolUse"
        assert "PostToolUse" in lifecycle_events, "AgentsToolHandler should dispatch PostToolUse"

    @pytest.mark.asyncio
    async def test_hook_can_deny_handler_execution(
        self, mock_auth, mock_agent_graph, enable_sdk_hooks, fresh_hook_registry
    ) -> None:
        """PreToolUse hook should be able to deny handler execution."""
        from mcp_server_langgraph.mcp.handlers.chat import ChatToolHandler

        async def deny_hook(input_data: PreToolUseInput, tool_use_id: str | None, context: HookContext) -> HookResult:
            return HookResult(behavior="deny", message="Blocked by policy")

        fresh_hook_registry.register(HookEvent.PRE_TOOL_USE, HookMatcher(hooks=[deny_hook], matcher=None))

        handler = ChatToolHandler(
            auth=mock_auth,
            agent_graph=mock_agent_graph,
            hook_registry=fresh_hook_registry,
        )

        mock_span = MagicMock()
        mock_span.get_span_context.return_value = MagicMock(trace_id="test-trace")

        result = await handler.handle(
            arguments={
                "message": "Hello",
                "thread_id": "test-thread",
                "token": "test-jwt-token",
                "user_id": "test-user",
            },
            span=mock_span,
            user_id="test-user",
        )

        # Chat handler returns denial message rather than raising
        assert len(result) == 1
        assert "denied" in result[0].text.lower() or "blocked" in result[0].text.lower()

        # Verify agent graph was NOT invoked
        mock_agent_graph.ainvoke.assert_not_called()


@pytest.mark.xdist_group(name="mcp_handler_hooks")
class TestFeatureFlagEnforcement:
    """Tests for feature flag enforcement in hook dispatch."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_hooks_not_dispatched_when_flag_disabled(
        self, mock_auth, mock_agent_graph, disable_sdk_hooks, fresh_hook_registry
    ) -> None:
        """Hooks should not be dispatched when FF_ENABLE_SDK_HOOKS=false."""
        from mcp_server_langgraph.mcp.handlers.chat import ChatToolHandler
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        # Create a fresh FeatureFlags instance to pick up env changes
        fresh_flags = FeatureFlags()

        hooks_called = False

        async def tracking_hook(input_data: PreToolUseInput, tool_use_id: str | None, context: HookContext) -> HookResult:
            nonlocal hooks_called
            hooks_called = True
            return HookResult(behavior="allow")

        fresh_hook_registry.register(HookEvent.PRE_TOOL_USE, HookMatcher(hooks=[tracking_hook], matcher=None))
        fresh_hook_registry.register(HookEvent.POST_TOOL_USE, HookMatcher(hooks=[tracking_hook], matcher=None))

        # Patch the feature_flags in hook_registry where dispatch checks it
        with patch("mcp_server_langgraph.core.hook_registry.feature_flags", fresh_flags):
            handler = ChatToolHandler(
                auth=mock_auth,
                agent_graph=mock_agent_graph,
                hook_registry=fresh_hook_registry,
            )

            mock_span = MagicMock()
            mock_span.get_span_context.return_value = MagicMock(trace_id="test-trace")

            await handler.handle(
                arguments={
                    "message": "Hello",
                    "thread_id": "test-thread",
                    "token": "test-jwt-token",
                    "user_id": "test-user",
                },
                span=mock_span,
                user_id="test-user",
            )

        # When feature flag is disabled, hooks should not be called
        assert not hooks_called, "Hooks should NOT be called when FF_ENABLE_SDK_HOOKS=false"

    @pytest.mark.asyncio
    async def test_hooks_dispatched_when_flag_enabled(
        self, mock_auth, mock_agent_graph, enable_sdk_hooks, fresh_hook_registry
    ) -> None:
        """Hooks should be dispatched when FF_ENABLE_SDK_HOOKS=true."""
        from mcp_server_langgraph.mcp.handlers.chat import ChatToolHandler
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        # Create a fresh FeatureFlags instance to pick up env changes
        FeatureFlags()

        hooks_called = False

        async def tracking_hook(input_data: PreToolUseInput, tool_use_id: str | None, context: HookContext) -> HookResult:
            nonlocal hooks_called
            hooks_called = True
            return HookResult(behavior="allow")

        fresh_hook_registry.register(HookEvent.PRE_TOOL_USE, HookMatcher(hooks=[tracking_hook], matcher=None))

        handler = ChatToolHandler(
            auth=mock_auth,
            agent_graph=mock_agent_graph,
            hook_registry=fresh_hook_registry,
        )

        mock_span = MagicMock()
        mock_span.get_span_context.return_value = MagicMock(trace_id="test-trace")

        await handler.handle(
            arguments={
                "message": "Hello",
                "thread_id": "test-thread",
                "token": "test-jwt-token",
                "user_id": "test-user",
            },
            span=mock_span,
            user_id="test-user",
        )

        # When feature flag is enabled, hooks should be called
        assert hooks_called, "Hooks SHOULD be called when FF_ENABLE_SDK_HOOKS=true"


@pytest.mark.xdist_group(name="mcp_handler_hooks")
class TestUnifiedHookRegistryIntegration:
    """Tests for UnifiedHookRegistry integration with handlers."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_unified_registry_works_with_chat_handler(
        self, mock_auth, mock_agent_graph, enable_sdk_hooks, fresh_hook_registry
    ) -> None:
        """UnifiedHookRegistry should work with ChatToolHandler."""
        from mcp_server_langgraph.mcp.handlers.chat import ChatToolHandler
        from mcp_server_langgraph.sdk import UnifiedHookRegistry
        from mcp_server_langgraph.sdk.hooks import HookResult as SDKHookResult

        lifecycle_events: list[str] = []

        # Create unified registry
        unified_registry = UnifiedHookRegistry(default_timeout=30.0)

        async def sdk_pre_hook(input_data, tool_use_id, context):
            lifecycle_events.append("SDK_PreToolUse")
            return SDKHookResult.allow()

        async def sdk_post_hook(input_data, tool_use_id, context):
            lifecycle_events.append("SDK_PostToolUse")
            return SDKHookResult.allow()

        unified_registry.register_sdk_hook("PreToolUse", "*", sdk_pre_hook)
        unified_registry.register_sdk_hook("PostToolUse", "*", sdk_post_hook)

        # Bridge SDK hooks to core hooks
        async def bridged_pre_hook(input_data: PreToolUseInput, tool_use_id: str | None, context: HookContext) -> HookResult:
            # Convert context to SDK format and call unified registry
            sdk_input = {
                "tool_name": input_data.tool_name,
                "tool_input": input_data.tool_input,
            }
            result = await unified_registry.execute_hooks(
                "PreToolUse",
                input_data.tool_name,
                sdk_input,
                tool_use_id,
                context,
            )
            return HookResult(
                behavior="allow" if result.allowed else "deny",
                message=result.reason,
            )

        async def bridged_post_hook(input_data: PostToolUseInput, tool_use_id: str | None, context: HookContext) -> HookResult:
            sdk_input = {
                "tool_name": input_data.tool_name,
                "tool_input": input_data.tool_input,
                "tool_output": input_data.tool_output,
                "is_error": input_data.is_error,
            }
            result = await unified_registry.execute_hooks(
                "PostToolUse",
                input_data.tool_name,
                sdk_input,
                tool_use_id,
                context,
            )
            return HookResult(
                behavior="allow" if result.allowed else "deny",
                message=result.reason,
            )

        fresh_hook_registry.register(HookEvent.PRE_TOOL_USE, HookMatcher(hooks=[bridged_pre_hook], matcher=None))
        fresh_hook_registry.register(HookEvent.POST_TOOL_USE, HookMatcher(hooks=[bridged_post_hook], matcher=None))

        handler = ChatToolHandler(
            auth=mock_auth,
            agent_graph=mock_agent_graph,
            hook_registry=fresh_hook_registry,
        )

        mock_span = MagicMock()
        mock_span.get_span_context.return_value = MagicMock(trace_id="test-trace")

        await handler.handle(
            arguments={
                "message": "Hello",
                "thread_id": "test-thread",
                "token": "test-jwt-token",
                "user_id": "test-user",
            },
            span=mock_span,
            user_id="test-user",
        )

        assert "SDK_PreToolUse" in lifecycle_events
        assert "SDK_PostToolUse" in lifecycle_events

    @pytest.mark.asyncio
    async def test_unified_registry_timeout_handling(self, enable_sdk_hooks) -> None:
        """UnifiedHookRegistry should handle hook timeouts."""
        import asyncio
        from mcp_server_langgraph.sdk import UnifiedHookRegistry
        from mcp_server_langgraph.sdk.hooks import HookResult as SDKHookResult

        # Create registry with very short timeout
        registry = UnifiedHookRegistry(default_timeout=0.01)  # 10ms

        async def slow_hook(input_data, tool_use_id, context):
            await asyncio.sleep(1.0)  # 1 second - will timeout
            return SDKHookResult.allow()

        registry.register_sdk_hook("PreToolUse", "*", slow_hook)

        context = HookContext(session_id="test", user_id="test")

        with pytest.raises(asyncio.TimeoutError):
            await registry.execute_hooks(
                "PreToolUse",
                "test_tool",
                {"tool_name": "test_tool", "tool_input": {}},
                "test-id",
                context,
            )
