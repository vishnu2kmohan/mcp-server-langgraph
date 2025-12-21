"""
Tests for SDK Tool Adapter - Hook integration for LangChain tools

Following Claude Agent SDK patterns for tool lifecycle hooks.
"""

from __future__ import annotations

import asyncio
import gc
from typing import TYPE_CHECKING, Any

import pytest
from langchain_core.tools import tool

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
def hook_context():
    """Create a HookContext for tests."""
    return HookContext(
        session_id="test-session-123",
        user_id="test-user",
        request_id="test-request-456",
    )


@pytest.fixture
def sample_tool():
    """Create a sample LangChain tool for testing."""

    @tool
    def sample_calculator(expression: str) -> str:
        """Evaluate a simple expression."""
        return f"Result: {eval(expression)}"  # noqa: S307

    return sample_calculator


@pytest.fixture
def async_tool():
    """Create an async LangChain tool for testing."""

    @tool
    async def async_calculator(expression: str) -> str:
        """Evaluate a simple expression asynchronously."""
        await asyncio.sleep(0.01)  # Simulate async work
        return f"Result: {eval(expression)}"  # noqa: S307

    return async_calculator


# ============================================================================
# SDKToolAdapter Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="sdk_adapter")
class TestSDKToolAdapterImport:
    """Test SDKToolAdapter can be imported."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_sdk_tool_adapter_importable(self):
        """SDKToolAdapter should be importable from tools module."""
        from mcp_server_langgraph.tools.sdk_adapter import SDKToolAdapter

        assert SDKToolAdapter is not None

    def test_sdk_tool_adapter_attributes(self):
        """SDKToolAdapter should have required attributes."""
        from mcp_server_langgraph.tools.sdk_adapter import SDKToolAdapter

        assert hasattr(SDKToolAdapter, "__init__")
        assert hasattr(SDKToolAdapter, "invoke")
        assert hasattr(SDKToolAdapter, "ainvoke")


@pytest.mark.unit
@pytest.mark.xdist_group(name="sdk_adapter")
class TestSDKToolAdapterInit:
    """Test SDKToolAdapter initialization."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_adapter_wraps_langchain_tool(self, sample_tool):
        """SDKToolAdapter should wrap a LangChain tool."""
        from mcp_server_langgraph.tools.sdk_adapter import SDKToolAdapter

        adapter = SDKToolAdapter(sample_tool)

        assert adapter.tool == sample_tool
        assert adapter.name == sample_tool.name

    def test_adapter_with_custom_registry(self, sample_tool, hook_registry):
        """SDKToolAdapter should accept custom registry."""
        from mcp_server_langgraph.tools.sdk_adapter import SDKToolAdapter

        adapter = SDKToolAdapter(sample_tool, registry=hook_registry)

        assert adapter.registry == hook_registry

    def test_adapter_uses_global_registry_by_default(self, sample_tool):
        """SDKToolAdapter should use global registry if none provided."""
        from mcp_server_langgraph.tools.sdk_adapter import SDKToolAdapter

        reset_hook_registry()
        adapter = SDKToolAdapter(sample_tool)

        # Should use global registry
        assert adapter.registry is not None


@pytest.mark.unit
@pytest.mark.xdist_group(name="sdk_adapter")
class TestSDKToolAdapterInvoke:
    """Test SDKToolAdapter invoke functionality."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_invoke_executes_tool(self, sample_tool, hook_context):
        """invoke should execute the wrapped tool."""
        from mcp_server_langgraph.tools.sdk_adapter import SDKToolAdapter

        adapter = SDKToolAdapter(sample_tool)
        result = await adapter.ainvoke(
            args={"expression": "2 + 2"},
            context=hook_context,
        )

        assert result["content"][0]["type"] == "text"
        assert "4" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_invoke_returns_sdk_format(self, sample_tool, hook_context):
        """invoke should return SDK-compatible format."""
        from mcp_server_langgraph.tools.sdk_adapter import SDKToolAdapter

        adapter = SDKToolAdapter(sample_tool)
        result = await adapter.ainvoke(
            args={"expression": "3 * 5"},
            context=hook_context,
        )

        # SDK format: {"content": [{"type": "text", "text": "..."}]}
        assert "content" in result
        assert isinstance(result["content"], list)
        assert len(result["content"]) >= 1
        assert result["content"][0]["type"] == "text"

    @pytest.mark.asyncio
    async def test_invoke_handles_tool_error(self, hook_context):
        """invoke should handle tool errors gracefully."""
        from mcp_server_langgraph.tools.sdk_adapter import SDKToolAdapter

        @tool
        def failing_tool(x: str) -> str:
            """Tool that always fails."""
            raise ValueError("Intentional error")

        adapter = SDKToolAdapter(failing_tool)
        result = await adapter.ainvoke(
            args={"x": "test"},
            context=hook_context,
        )

        assert result.get("is_error") is True
        assert "error" in result["content"][0]["text"].lower()

    @pytest.mark.asyncio
    async def test_invoke_async_tool(self, async_tool, hook_context):
        """invoke should work with async tools."""
        from mcp_server_langgraph.tools.sdk_adapter import SDKToolAdapter

        adapter = SDKToolAdapter(async_tool)
        result = await adapter.ainvoke(
            args={"expression": "10 / 2"},
            context=hook_context,
        )

        assert "5" in result["content"][0]["text"]


@pytest.mark.unit
@pytest.mark.xdist_group(name="sdk_adapter")
class TestSDKToolAdapterPreHooks:
    """Test SDKToolAdapter pre-tool-use hooks."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_pre_hook_called_before_tool(self, sample_tool, hook_registry, hook_context):
        """PreToolUse hooks should be called before tool execution."""
        from mcp_server_langgraph.tools.sdk_adapter import SDKToolAdapter

        call_order: list[str] = []

        async def pre_hook(
            input_data: PreToolUseInput,
            tool_use_id: str | None,
            context: HookContext,
        ) -> HookResult:
            call_order.append("pre_hook")
            return HookResult()

        hook_registry.register(
            HookEvent.PRE_TOOL_USE,
            HookMatcher(hooks=[pre_hook], matcher=sample_tool.name),
        )

        adapter = SDKToolAdapter(sample_tool, registry=hook_registry)
        await adapter.ainvoke(args={"expression": "1 + 1"}, context=hook_context)

        assert "pre_hook" in call_order

    @pytest.mark.asyncio
    async def test_pre_hook_can_deny_execution(self, sample_tool, hook_registry, hook_context):
        """PreToolUse hook can deny tool execution."""
        from mcp_server_langgraph.tools.sdk_adapter import SDKToolAdapter

        async def deny_hook(
            input_data: PreToolUseInput,
            tool_use_id: str | None,
            context: HookContext,
        ) -> HookResult:
            return HookResult(behavior="deny", message="Blocked by hook")

        hook_registry.register(
            HookEvent.PRE_TOOL_USE,
            HookMatcher(hooks=[deny_hook], matcher=sample_tool.name),
        )

        adapter = SDKToolAdapter(sample_tool, registry=hook_registry)
        result = await adapter.ainvoke(args={"expression": "1 + 1"}, context=hook_context)

        assert result.get("is_error") is True
        assert "Blocked by hook" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_pre_hook_can_modify_input(self, sample_tool, hook_registry, hook_context):
        """PreToolUse hook can modify tool input."""
        from mcp_server_langgraph.tools.sdk_adapter import SDKToolAdapter

        async def modify_hook(
            input_data: PreToolUseInput,
            tool_use_id: str | None,
            context: HookContext,
        ) -> HookResult:
            # Change expression from "1 + 1" to "10 + 10"
            return HookResult(updated_input={"expression": "10 + 10"})

        hook_registry.register(
            HookEvent.PRE_TOOL_USE,
            HookMatcher(hooks=[modify_hook], matcher=sample_tool.name),
        )

        adapter = SDKToolAdapter(sample_tool, registry=hook_registry)
        result = await adapter.ainvoke(args={"expression": "1 + 1"}, context=hook_context)

        # Should show modified result (20) not original (2)
        assert "20" in result["content"][0]["text"]


@pytest.mark.unit
@pytest.mark.xdist_group(name="sdk_adapter")
class TestSDKToolAdapterPostHooks:
    """Test SDKToolAdapter post-tool-use hooks."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_post_hook_called_after_tool(self, sample_tool, hook_registry, hook_context):
        """PostToolUse hooks should be called after tool execution."""
        from mcp_server_langgraph.tools.sdk_adapter import SDKToolAdapter

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
            HookMatcher(hooks=[post_hook], matcher=sample_tool.name),
        )

        adapter = SDKToolAdapter(sample_tool, registry=hook_registry)
        await adapter.ainvoke(args={"expression": "5 + 5"}, context=hook_context)

        assert post_hook_data["tool_name"] == sample_tool.name
        assert "10" in post_hook_data["tool_output"]
        assert post_hook_data["is_error"] is False

    @pytest.mark.asyncio
    async def test_post_hook_receives_error_status(self, hook_registry, hook_context):
        """PostToolUse hook should receive error status for failed tools."""
        from mcp_server_langgraph.tools.sdk_adapter import SDKToolAdapter

        @tool
        def error_tool(x: str) -> str:
            """Tool that fails."""
            raise RuntimeError("Tool failed")

        post_hook_data: dict[str, Any] = {}

        async def post_hook(
            input_data: PostToolUseInput,
            tool_use_id: str | None,
            context: HookContext,
        ) -> HookResult:
            post_hook_data["is_error"] = input_data.is_error
            post_hook_data["tool_output"] = input_data.tool_output
            return HookResult()

        hook_registry.register(
            HookEvent.POST_TOOL_USE,
            HookMatcher(hooks=[post_hook], matcher="error_tool"),
        )

        adapter = SDKToolAdapter(error_tool, registry=hook_registry)
        await adapter.ainvoke(args={"x": "test"}, context=hook_context)

        assert post_hook_data["is_error"] is True

    @pytest.mark.asyncio
    async def test_post_hook_not_called_on_deny(self, sample_tool, hook_registry, hook_context):
        """PostToolUse hook should NOT be called if PreToolUse denies."""
        from mcp_server_langgraph.tools.sdk_adapter import SDKToolAdapter

        post_hook_called = False

        async def deny_hook(
            input_data: PreToolUseInput,
            tool_use_id: str | None,
            context: HookContext,
        ) -> HookResult:
            return HookResult(behavior="deny", message="Denied")

        async def post_hook(
            input_data: PostToolUseInput,
            tool_use_id: str | None,
            context: HookContext,
        ) -> HookResult:
            nonlocal post_hook_called
            post_hook_called = True
            return HookResult()

        hook_registry.register(
            HookEvent.PRE_TOOL_USE,
            HookMatcher(hooks=[deny_hook], matcher=sample_tool.name),
        )
        hook_registry.register(
            HookEvent.POST_TOOL_USE,
            HookMatcher(hooks=[post_hook], matcher=sample_tool.name),
        )

        adapter = SDKToolAdapter(sample_tool, registry=hook_registry)
        await adapter.ainvoke(args={"expression": "1 + 1"}, context=hook_context)

        assert post_hook_called is False


@pytest.mark.unit
@pytest.mark.xdist_group(name="sdk_adapter")
class TestSDKToolAdapterToolUseId:
    """Test SDKToolAdapter tool_use_id handling."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_tool_use_id_passed_to_hooks(self, sample_tool, hook_registry, hook_context):
        """tool_use_id should be passed to hooks."""
        from mcp_server_langgraph.tools.sdk_adapter import SDKToolAdapter

        received_tool_use_id: str | None = None

        async def capture_hook(
            input_data: PreToolUseInput,
            tool_use_id: str | None,
            context: HookContext,
        ) -> HookResult:
            nonlocal received_tool_use_id
            received_tool_use_id = tool_use_id
            return HookResult()

        hook_registry.register(
            HookEvent.PRE_TOOL_USE,
            HookMatcher(hooks=[capture_hook], matcher=sample_tool.name),
        )

        adapter = SDKToolAdapter(sample_tool, registry=hook_registry)
        await adapter.ainvoke(
            args={"expression": "1 + 1"},
            context=hook_context,
            tool_use_id="tu_12345",
        )

        assert received_tool_use_id == "tu_12345"

    @pytest.mark.asyncio
    async def test_auto_generated_tool_use_id(self, sample_tool, hook_registry, hook_context):
        """tool_use_id should be auto-generated if not provided."""
        from mcp_server_langgraph.tools.sdk_adapter import SDKToolAdapter

        received_tool_use_id: str | None = None

        async def capture_hook(
            input_data: PreToolUseInput,
            tool_use_id: str | None,
            context: HookContext,
        ) -> HookResult:
            nonlocal received_tool_use_id
            received_tool_use_id = tool_use_id
            return HookResult()

        hook_registry.register(
            HookEvent.PRE_TOOL_USE,
            HookMatcher(hooks=[capture_hook], matcher=sample_tool.name),
        )

        adapter = SDKToolAdapter(sample_tool, registry=hook_registry)
        await adapter.ainvoke(
            args={"expression": "1 + 1"},
            context=hook_context,
        )

        # Should have an auto-generated ID
        assert received_tool_use_id is not None
        assert len(received_tool_use_id) > 0


@pytest.mark.unit
@pytest.mark.xdist_group(name="sdk_adapter")
class TestAdaptToolFunction:
    """Test adapt_tool convenience function."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_adapt_tool_exists(self):
        """adapt_tool function should exist."""
        from mcp_server_langgraph.tools.sdk_adapter import adapt_tool

        assert adapt_tool is not None
        assert callable(adapt_tool)

    def test_adapt_tool_returns_adapter(self, sample_tool):
        """adapt_tool should return an SDKToolAdapter."""
        from mcp_server_langgraph.tools.sdk_adapter import SDKToolAdapter, adapt_tool

        adapter = adapt_tool(sample_tool)

        assert isinstance(adapter, SDKToolAdapter)
        assert adapter.tool == sample_tool

    def test_adapt_multiple_tools(self):
        """adapt_tool should work on multiple tools."""
        from mcp_server_langgraph.tools.sdk_adapter import adapt_tools

        @tool
        def tool_a(x: str) -> str:
            """Tool A."""
            return x

        @tool
        def tool_b(x: str) -> str:
            """Tool B."""
            return x

        adapters = adapt_tools([tool_a, tool_b])

        assert len(adapters) == 2
        assert adapters[0].name == "tool_a"
        assert adapters[1].name == "tool_b"


@pytest.mark.unit
@pytest.mark.xdist_group(name="sdk_adapter")
class TestSDKToolAdapterSystemMessage:
    """Test SDKToolAdapter system_message handling from hooks."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_system_message_included_in_result(self, sample_tool, hook_registry, hook_context):
        """System message from hook should be included in result."""
        from mcp_server_langgraph.tools.sdk_adapter import SDKToolAdapter

        async def system_hook(
            input_data: PreToolUseInput,
            tool_use_id: str | None,
            context: HookContext,
        ) -> HookResult:
            return HookResult(system_message="Important system info")

        hook_registry.register(
            HookEvent.PRE_TOOL_USE,
            HookMatcher(hooks=[system_hook], matcher=sample_tool.name),
        )

        adapter = SDKToolAdapter(sample_tool, registry=hook_registry)
        result = await adapter.ainvoke(args={"expression": "1 + 1"}, context=hook_context)

        assert result.get("system_message") == "Important system info"


@pytest.mark.unit
@pytest.mark.xdist_group(name="sdk_adapter")
class TestSDKToolAdapterContextPropagation:
    """Test SDKToolAdapter context propagation."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_context_passed_to_hooks(self, sample_tool, hook_registry, hook_context):
        """HookContext should be passed to hooks."""
        from mcp_server_langgraph.tools.sdk_adapter import SDKToolAdapter

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
            HookMatcher(hooks=[capture_hook], matcher=sample_tool.name),
        )

        adapter = SDKToolAdapter(sample_tool, registry=hook_registry)
        await adapter.ainvoke(args={"expression": "1 + 1"}, context=hook_context)

        assert received_context is not None
        assert received_context.session_id == hook_context.session_id
        assert received_context.user_id == hook_context.user_id

    @pytest.mark.asyncio
    async def test_default_context_used_if_none(self, sample_tool):
        """Default context should be used if none provided."""
        from mcp_server_langgraph.tools.sdk_adapter import SDKToolAdapter

        adapter = SDKToolAdapter(sample_tool)
        # Should not raise even without context
        result = await adapter.ainvoke(args={"expression": "1 + 1"})

        assert "content" in result
