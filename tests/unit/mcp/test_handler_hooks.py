"""
Tests for MCP Handler Hook Integration

Verifies that MCP handlers properly dispatch PreToolUse and PostToolUse hooks.
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_server_langgraph.core.hooks import (
    HookContext,
    HookEvent,
    HookMatcher,
    HookResult,
    PostToolUseInput,
    PreToolUseInput,
)
from mcp_server_langgraph.core.hook_registry import (
    HookRegistry,
    reset_hook_registry,
)

if TYPE_CHECKING:
    pass

pytestmark = pytest.mark.unit

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def hook_registry():
    """Create a fresh HookRegistry for each test."""
    reset_hook_registry()
    registry = HookRegistry()
    yield registry
    reset_hook_registry()


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
    graph.ainvoke = AsyncMock(
        return_value={
            "messages": [MagicMock(content="Test response")],
        }
    )
    graph.checkpointer = None
    return graph


@pytest.fixture
def mock_span():
    """Create mock OpenTelemetry span."""
    span = MagicMock()
    span.get_span_context.return_value = MagicMock(trace_id="test-trace-123")
    span.set_attribute = MagicMock()
    span.record_exception = MagicMock()
    return span


# ============================================================================
# Hook Mixin Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="handler_hooks")
class TestHookMixinImport:
    """Test HookMixin can be imported."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_hook_mixin_importable(self):
        """HookMixin should be importable from handlers.base."""
        from mcp_server_langgraph.mcp.handlers.base import HookMixin

        assert HookMixin is not None

    def test_hook_mixin_has_required_methods(self):
        """HookMixin should have hook dispatch methods."""
        from mcp_server_langgraph.mcp.handlers.base import HookMixin

        assert hasattr(HookMixin, "dispatch_pre_handler_hook")
        assert hasattr(HookMixin, "dispatch_post_handler_hook")
        assert hasattr(HookMixin, "get_hook_context")


@pytest.mark.unit
@pytest.mark.xdist_group(name="handler_hooks")
class TestHookMixinContext:
    """Test HookMixin context creation."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_hook_context_creates_valid_context(self):
        """get_hook_context should create a valid HookContext."""
        from mcp_server_langgraph.mcp.handlers.base import HookMixin

        mixin = HookMixin()
        context = mixin.get_hook_context(
            session_id="test-session",
            user_id="test-user",
            request_id="test-request",
        )

        assert isinstance(context, HookContext)
        assert context.session_id == "test-session"
        assert context.user_id == "test-user"
        assert context.request_id == "test-request"

    def test_get_hook_context_optional_fields(self):
        """get_hook_context should handle optional fields."""
        from mcp_server_langgraph.mcp.handlers.base import HookMixin

        mixin = HookMixin()
        context = mixin.get_hook_context(session_id="test-session")

        assert context.session_id == "test-session"
        assert context.user_id is None
        assert context.request_id is None


@pytest.mark.unit
@pytest.mark.xdist_group(name="handler_hooks")
class TestHookMixinPreHook:
    """Test HookMixin pre-handler hook dispatch."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_dispatch_pre_handler_hook_returns_result(self, hook_registry):
        """dispatch_pre_handler_hook should return HookResult."""
        from mcp_server_langgraph.mcp.handlers.base import HookMixin

        mixin = HookMixin(hook_registry=hook_registry)
        context = mixin.get_hook_context(session_id="test")

        result = await mixin.dispatch_pre_handler_hook(
            tool_name="test_tool",
            tool_input={"arg": "value"},
            context=context,
        )

        assert isinstance(result, HookResult)
        assert result.behavior == "allow"

    @pytest.mark.asyncio
    async def test_dispatch_pre_handler_hook_executes_hooks(self, hook_registry):
        """dispatch_pre_handler_hook should execute registered hooks."""
        from mcp_server_langgraph.mcp.handlers.base import HookMixin

        hook_called = False

        async def test_hook(
            input_data: PreToolUseInput,
            tool_use_id: str | None,
            context: HookContext,
        ) -> HookResult:
            nonlocal hook_called
            hook_called = True
            return HookResult()

        hook_registry.register(
            HookEvent.PRE_TOOL_USE,
            HookMatcher(hooks=[test_hook], matcher="test_tool"),
        )

        mixin = HookMixin(hook_registry=hook_registry)
        context = mixin.get_hook_context(session_id="test")

        await mixin.dispatch_pre_handler_hook(
            tool_name="test_tool",
            tool_input={"arg": "value"},
            context=context,
        )

        assert hook_called is True

    @pytest.mark.asyncio
    async def test_dispatch_pre_handler_hook_deny_stops_execution(self, hook_registry):
        """dispatch_pre_handler_hook should return deny result."""
        from mcp_server_langgraph.mcp.handlers.base import HookMixin

        async def deny_hook(
            input_data: PreToolUseInput,
            tool_use_id: str | None,
            context: HookContext,
        ) -> HookResult:
            return HookResult(behavior="deny", message="Access denied")

        hook_registry.register(
            HookEvent.PRE_TOOL_USE,
            HookMatcher(hooks=[deny_hook], matcher="test_tool"),
        )

        mixin = HookMixin(hook_registry=hook_registry)
        context = mixin.get_hook_context(session_id="test")

        result = await mixin.dispatch_pre_handler_hook(
            tool_name="test_tool",
            tool_input={"arg": "value"},
            context=context,
        )

        assert result.behavior == "deny"
        assert result.message == "Access denied"


@pytest.mark.unit
@pytest.mark.xdist_group(name="handler_hooks")
class TestHookMixinPostHook:
    """Test HookMixin post-handler hook dispatch."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_dispatch_post_handler_hook_executes_hooks(self, hook_registry):
        """dispatch_post_handler_hook should execute registered hooks."""
        from mcp_server_langgraph.mcp.handlers.base import HookMixin

        post_hook_data: dict[str, Any] = {}

        async def post_hook(
            input_data: PostToolUseInput,
            tool_use_id: str | None,
            context: HookContext,
        ) -> HookResult:
            post_hook_data["tool_name"] = input_data.tool_name
            post_hook_data["tool_output"] = input_data.tool_output
            post_hook_data["is_error"] = input_data.is_error
            return HookResult()

        hook_registry.register(
            HookEvent.POST_TOOL_USE,
            HookMatcher(hooks=[post_hook], matcher="test_tool"),
        )

        mixin = HookMixin(hook_registry=hook_registry)
        context = mixin.get_hook_context(session_id="test")

        await mixin.dispatch_post_handler_hook(
            tool_name="test_tool",
            tool_input={"arg": "value"},
            tool_output="Success result",
            is_error=False,
            context=context,
        )

        assert post_hook_data["tool_name"] == "test_tool"
        assert post_hook_data["tool_output"] == "Success result"
        assert post_hook_data["is_error"] is False

    @pytest.mark.asyncio
    async def test_dispatch_post_handler_hook_with_error(self, hook_registry):
        """dispatch_post_handler_hook should pass is_error status."""
        from mcp_server_langgraph.mcp.handlers.base import HookMixin

        received_is_error: bool | None = None

        async def post_hook(
            input_data: PostToolUseInput,
            tool_use_id: str | None,
            context: HookContext,
        ) -> HookResult:
            nonlocal received_is_error
            received_is_error = input_data.is_error
            return HookResult()

        hook_registry.register(
            HookEvent.POST_TOOL_USE,
            HookMatcher(hooks=[post_hook], matcher="test_tool"),
        )

        mixin = HookMixin(hook_registry=hook_registry)
        context = mixin.get_hook_context(session_id="test")

        await mixin.dispatch_post_handler_hook(
            tool_name="test_tool",
            tool_input={},
            tool_output="Error: Something failed",
            is_error=True,
            context=context,
        )

        assert received_is_error is True


@pytest.mark.unit
@pytest.mark.xdist_group(name="handler_hooks")
class TestAbstractToolHandlerWithHooks:
    """Test AbstractToolHandler hook integration."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_abstract_handler_inherits_hook_mixin(self, mock_auth, mock_agent_graph):
        """AbstractToolHandler should inherit from HookMixin."""
        from mcp_server_langgraph.mcp.handlers.base import AbstractToolHandler, HookMixin

        # Check class hierarchy
        assert issubclass(AbstractToolHandler, HookMixin)

    def test_abstract_handler_has_hook_methods(self, mock_auth, mock_agent_graph):
        """AbstractToolHandler should have hook dispatch methods."""
        from mcp_server_langgraph.mcp.handlers.base import AbstractToolHandler

        assert hasattr(AbstractToolHandler, "dispatch_pre_handler_hook")
        assert hasattr(AbstractToolHandler, "dispatch_post_handler_hook")


@pytest.mark.unit
@pytest.mark.xdist_group(name="handler_hooks")
class TestChatHandlerHooks:
    """Test ChatToolHandler hook integration."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_chat_handler_dispatches_pre_hook(self, hook_registry, mock_auth, mock_agent_graph, mock_span):
        """ChatToolHandler should dispatch PreToolUse hooks."""
        from mcp_server_langgraph.mcp.handlers.chat import ChatToolHandler

        pre_hook_called = False

        async def pre_hook(
            input_data: PreToolUseInput,
            tool_use_id: str | None,
            context: HookContext,
        ) -> HookResult:
            nonlocal pre_hook_called
            pre_hook_called = True
            return HookResult()

        hook_registry.register(
            HookEvent.PRE_TOOL_USE,
            HookMatcher(hooks=[pre_hook], matcher="agent_chat"),
        )

        # Pass registry directly - no patch needed
        handler = ChatToolHandler(mock_auth, mock_agent_graph, hook_registry=hook_registry)

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

        assert pre_hook_called is True

    @pytest.mark.asyncio
    async def test_chat_handler_dispatches_post_hook(self, hook_registry, mock_auth, mock_agent_graph, mock_span):
        """ChatToolHandler should dispatch PostToolUse hooks."""
        from mcp_server_langgraph.mcp.handlers.chat import ChatToolHandler

        post_hook_data: dict[str, Any] = {}

        async def post_hook(
            input_data: PostToolUseInput,
            tool_use_id: str | None,
            context: HookContext,
        ) -> HookResult:
            post_hook_data["called"] = True
            post_hook_data["tool_name"] = input_data.tool_name
            return HookResult()

        hook_registry.register(
            HookEvent.POST_TOOL_USE,
            HookMatcher(hooks=[post_hook], matcher="agent_chat"),
        )

        # Pass registry directly - no patch needed
        handler = ChatToolHandler(mock_auth, mock_agent_graph, hook_registry=hook_registry)

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

        assert post_hook_data.get("called") is True
        assert post_hook_data.get("tool_name") == "agent_chat"

    @pytest.mark.asyncio
    async def test_chat_handler_pre_hook_deny_returns_error(self, hook_registry, mock_auth, mock_agent_graph, mock_span):
        """ChatToolHandler should return error when PreToolUse denies."""
        from mcp_server_langgraph.mcp.handlers.chat import ChatToolHandler

        async def deny_hook(
            input_data: PreToolUseInput,
            tool_use_id: str | None,
            context: HookContext,
        ) -> HookResult:
            return HookResult(behavior="deny", message="Chat blocked by policy")

        hook_registry.register(
            HookEvent.PRE_TOOL_USE,
            HookMatcher(hooks=[deny_hook], matcher="agent_chat"),
        )

        # Pass registry directly - no patch needed
        handler = ChatToolHandler(mock_auth, mock_agent_graph, hook_registry=hook_registry)

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

        # Should return error response
        assert len(result) == 1
        assert "blocked" in result[0].text.lower() or "denied" in result[0].text.lower()


@pytest.mark.unit
@pytest.mark.xdist_group(name="handler_hooks")
class TestHandlerHookContextMetadata:
    """Test hook context contains handler metadata."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_hook_context_includes_user_id(self, hook_registry, mock_auth, mock_agent_graph, mock_span):
        """Hook context should include user_id from handler."""
        from mcp_server_langgraph.mcp.handlers.chat import ChatToolHandler

        received_context: HookContext | None = None

        async def capture_hook(
            input_data: PreToolUseInput,
            tool_use_id: str | None,
            context: HookContext,
        ) -> HookResult:
            nonlocal received_context
            received_context = context
            return HookResult()

        hook_registry.register(
            HookEvent.PRE_TOOL_USE,
            HookMatcher(hooks=[capture_hook], matcher="agent_chat"),
        )

        # Pass registry directly - no patch needed
        handler = ChatToolHandler(mock_auth, mock_agent_graph, hook_registry=hook_registry)

        await handler.handle(
            arguments={
                "message": "Hello",
                "thread_id": "test-thread",
                "token": "test-jwt-token",
                "user_id": "alice@example.com",
            },
            span=mock_span,
            user_id="alice@example.com",
        )

        assert received_context is not None
        assert received_context.user_id == "alice@example.com"

    @pytest.mark.asyncio
    async def test_hook_context_includes_request_id(self, hook_registry, mock_auth, mock_agent_graph, mock_span):
        """Hook context should include request_id from span."""
        from mcp_server_langgraph.mcp.handlers.chat import ChatToolHandler

        received_context: HookContext | None = None

        async def capture_hook(
            input_data: PreToolUseInput,
            tool_use_id: str | None,
            context: HookContext,
        ) -> HookResult:
            nonlocal received_context
            received_context = context
            return HookResult()

        hook_registry.register(
            HookEvent.PRE_TOOL_USE,
            HookMatcher(hooks=[capture_hook], matcher="agent_chat"),
        )

        # Pass registry directly - no patch needed
        handler = ChatToolHandler(mock_auth, mock_agent_graph, hook_registry=hook_registry)

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

        assert received_context is not None
        # request_id should be derived from trace
        assert received_context.request_id is not None
