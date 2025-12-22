"""
Unit tests for Tool Bridge

Tests programmatic tool calling from sandboxed code execution.
Enables sandbox code to invoke MCP tools without returning to model context.

TDD: RED phase - these tests define expected behavior before implementation.
"""

import gc

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.programmatic_tools]


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_tool_bridge_basic")
class TestToolBridgeBasic:
    """Test suite for basic tool bridge functionality"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_tool_bridge_exists(self):
        """GIVEN the execution module
        WHEN importing ToolBridge
        THEN it should be available
        """
        from mcp_server_langgraph.execution.tool_bridge import ToolBridge

        bridge = ToolBridge()
        assert bridge is not None

    def test_tool_bridge_has_registry(self):
        """GIVEN a ToolBridge
        WHEN checking configuration
        THEN it should have a tool registry
        """
        from mcp_server_langgraph.execution.tool_bridge import ToolBridge

        bridge = ToolBridge()

        assert hasattr(bridge, "registered_tools")
        assert isinstance(bridge.registered_tools, dict)


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_tool_bridge_registration")
class TestToolBridgeRegistration:
    """Test suite for tool registration"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_register_tool(self):
        """GIVEN a ToolBridge
        WHEN registering a tool
        THEN the tool should be available
        """
        from mcp_server_langgraph.execution.tool_bridge import ToolBridge

        bridge = ToolBridge()

        async def sample_tool(query: str) -> str:
            return f"Result for: {query}"

        bridge.register_tool("search", sample_tool)

        assert "search" in bridge.registered_tools

    def test_register_multiple_tools(self):
        """GIVEN a ToolBridge
        WHEN registering multiple tools
        THEN all tools should be available
        """
        from mcp_server_langgraph.execution.tool_bridge import ToolBridge

        bridge = ToolBridge()

        async def tool1() -> str:
            return "tool1"

        async def tool2() -> str:
            return "tool2"

        bridge.register_tool("tool1", tool1)
        bridge.register_tool("tool2", tool2)

        assert len(bridge.registered_tools) == 2

    def test_unregister_tool(self):
        """GIVEN a ToolBridge with registered tools
        WHEN unregistering a tool
        THEN the tool should be removed
        """
        from mcp_server_langgraph.execution.tool_bridge import ToolBridge

        bridge = ToolBridge()

        async def sample_tool() -> str:
            return "sample"

        bridge.register_tool("sample", sample_tool)
        bridge.unregister_tool("sample")

        assert "sample" not in bridge.registered_tools


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_tool_bridge_invocation")
class TestToolBridgeInvocation:
    """Test suite for tool invocation"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_call_tool(self):
        """GIVEN a ToolBridge with registered tools
        WHEN calling a tool
        THEN the result should be returned
        """
        from mcp_server_langgraph.execution.tool_bridge import ToolBridge

        bridge = ToolBridge()

        async def echo_tool(message: str) -> str:
            return f"Echo: {message}"

        bridge.register_tool("echo", echo_tool)

        result = await bridge.call_tool("echo", {"message": "hello"})

        assert result.success is True
        assert "Echo: hello" in result.output

    @pytest.mark.asyncio
    async def test_call_nonexistent_tool_fails(self):
        """GIVEN a ToolBridge
        WHEN calling a nonexistent tool
        THEN an error should be returned
        """
        from mcp_server_langgraph.execution.tool_bridge import ToolBridge

        bridge = ToolBridge()

        result = await bridge.call_tool("nonexistent", {})

        assert result.success is False
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_call_tool_with_error(self):
        """GIVEN a tool that raises an exception
        WHEN calling the tool
        THEN the error should be captured
        """
        from mcp_server_langgraph.execution.tool_bridge import ToolBridge

        bridge = ToolBridge()

        async def failing_tool() -> str:
            raise ValueError("Tool execution failed")

        bridge.register_tool("failing", failing_tool)

        result = await bridge.call_tool("failing", {})

        assert result.success is False
        assert "Tool execution failed" in result.error


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_tool_bridge_parallel")
class TestToolBridgeParallel:
    """Test suite for parallel tool execution"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_gather_tools(self):
        """GIVEN a ToolBridge with tools
        WHEN calling gather_tools with multiple calls
        THEN all results should be returned
        """
        from mcp_server_langgraph.execution.tool_bridge import ToolBridge

        bridge = ToolBridge()

        async def search_tool(query: str) -> str:
            return f"Results for: {query}"

        bridge.register_tool("search", search_tool)

        results = await bridge.gather_tools(
            ("search", {"query": "topic1"}),
            ("search", {"query": "topic2"}),
            ("search", {"query": "topic3"}),
        )

        assert len(results) == 3
        assert all(r.success for r in results)


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_tool_result")
class TestToolResult:
    """Test suite for tool result model"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_tool_result_success(self):
        """GIVEN a successful tool execution
        WHEN creating ToolResult
        THEN it should contain output
        """
        from mcp_server_langgraph.execution.tool_bridge import ToolResult

        result = ToolResult(
            success=True,
            tool_name="search",
            output="Search results here",
            duration_ms=45.2,
        )

        assert result.success is True
        assert result.output == "Search results here"
        assert result.error is None

    def test_tool_result_failure(self):
        """GIVEN a failed tool execution
        WHEN creating ToolResult
        THEN it should contain error
        """
        from mcp_server_langgraph.execution.tool_bridge import ToolResult

        result = ToolResult(
            success=False,
            tool_name="failing_tool",
            error="Connection timeout",
        )

        assert result.success is False
        assert "timeout" in result.error.lower()


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_sandbox_context")
class TestSandboxContext:
    """Test suite for sandbox execution context"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_sandbox_context_exists(self):
        """GIVEN the execution module
        WHEN importing SandboxContext
        THEN it should be available
        """
        from mcp_server_langgraph.execution.sandbox_context import SandboxContext

        context = SandboxContext()
        assert context is not None

    def test_sandbox_context_has_bridge(self):
        """GIVEN a SandboxContext
        WHEN checking configuration
        THEN it should have a tool bridge
        """
        from mcp_server_langgraph.execution.sandbox_context import SandboxContext
        from mcp_server_langgraph.execution.tool_bridge import ToolBridge

        context = SandboxContext()

        assert hasattr(context, "tool_bridge")
        assert isinstance(context.tool_bridge, ToolBridge)

    def test_sandbox_context_call_mcp_tool(self):
        """GIVEN a SandboxContext
        WHEN using call_mcp_tool helper
        THEN it should delegate to bridge
        """
        from mcp_server_langgraph.execution.sandbox_context import SandboxContext

        context = SandboxContext()

        # call_mcp_tool should return a coroutine
        coro = context.call_mcp_tool("search", {"query": "test"})
        assert coro is not None
        # Clean up coroutine
        coro.close()
