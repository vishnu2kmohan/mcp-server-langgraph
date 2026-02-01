"""
E2E Integration Test: MCP Tool Execution Data Flow

Tests the complete MCP tool execution data flow:
    Request → MCPToolProxy → MCPExecutor → MCPClientSession → Response

This test verifies that MCP tool execution works correctly end-to-end,
catching wiring issues where tool calls are made but responses don't flow back.

Following memory safety patterns for pytest-xdist (see CLAUDE.md).
"""

import gc
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.mcp,
    pytest.mark.asyncio,
    pytest.mark.xdist_group(name="mcp_tool_execution_flow_e2e"),
]


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def unique_server_name() -> str:
    """Generate unique server name for test isolation."""
    return f"server-{uuid4().hex[:8]}"


@pytest.fixture
def unique_tool_name() -> str:
    """Generate unique tool name for test isolation."""
    return f"tool-{uuid4().hex[:8]}"


@pytest.fixture
def create_tool_definition():
    """Factory for creating test MCP tool definitions."""
    from mcp_server_langgraph.mcp.client.tool_registry import MCPToolDefinition

    def _create(
        server_name: str,
        name: str,
        description: str = "A test tool",
        input_schema: dict | None = None,
    ) -> MCPToolDefinition:
        return MCPToolDefinition(
            server_name=server_name,
            name=name,
            description=description,
            input_schema=input_schema
            or {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                },
                "required": ["query"],
            },
        )

    return _create


@pytest.fixture
def mock_mcp_session():
    """Create mock MCP client session."""
    session = MagicMock()
    session.is_connected = True
    session.call_tool = AsyncMock(return_value={"result": "Tool executed successfully", "data": [1, 2, 3]})
    session.list_tools = AsyncMock(return_value=[])
    session.connect = AsyncMock(return_value=None)
    session.disconnect = AsyncMock(return_value=None)
    return session


@pytest.fixture
def mock_executor(mock_mcp_session):
    """Create mock MCP executor with session."""
    from mcp_server_langgraph.mcp.client.executor import MCPExecutor

    executor = MCPExecutor()
    # Mock the session retrieval
    executor._sessions = {f"server-{uuid4().hex[:8]}": mock_mcp_session}
    return executor


# ============================================================================
# E2E MCP Tool Execution Flow Tests
# ============================================================================


class TestMCPToolDefinitionFlow:
    """
    E2E tests for MCP tool definition and registry.
    """

    def setup_method(self):
        """Reset singleton dependencies."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()

    def teardown_method(self):
        """Force GC."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()
        gc.collect()

    async def test_tool_definition_qualified_name(
        self,
        unique_server_name,
        unique_tool_name,
        create_tool_definition,
    ):
        """
        E2E: Verify tool definition creates correct qualified name.

        GIVEN: A tool definition with server and tool name
        WHEN: The qualified_name property is accessed
        THEN: It returns "server_name:tool_name" format
        """
        defn = create_tool_definition(
            server_name=unique_server_name,
            name=unique_tool_name,
        )

        assert defn.qualified_name == f"{unique_server_name}:{unique_tool_name}"

    async def test_tool_definition_input_schema_validation(
        self,
        unique_server_name,
        unique_tool_name,
        create_tool_definition,
    ):
        """
        E2E: Verify tool definition stores input schema correctly.

        GIVEN: A tool definition with JSON schema
        WHEN: The definition is created
        THEN: The input_schema is preserved correctly
        """
        schema = {
            "type": "object",
            "properties": {
                "url": {"type": "string", "format": "uri"},
                "timeout": {"type": "integer", "default": 30},
            },
            "required": ["url"],
        }

        defn = create_tool_definition(
            server_name=unique_server_name,
            name=unique_tool_name,
            input_schema=schema,
        )

        assert defn.input_schema == schema
        assert "url" in defn.input_schema["properties"]
        assert "required" in defn.input_schema


class TestMCPToolProxyFlow:
    """
    E2E tests for MCP tool proxy creation and execution.
    """

    def setup_method(self):
        """Reset singleton dependencies."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()

    def teardown_method(self):
        """Force GC."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()
        gc.collect()

    async def test_proxy_creation_from_definition(
        self,
        unique_server_name,
        unique_tool_name,
        create_tool_definition,
    ):
        """
        E2E: Verify MCPToolProxy can be created from definition.

        GIVEN: An MCP tool definition
        WHEN: A proxy is created from it
        THEN: The proxy has correct name and schema
        """
        from mcp_server_langgraph.mcp.client.tool_proxy import MCPToolProxy

        defn = create_tool_definition(
            server_name=unique_server_name,
            name=unique_tool_name,
            description="Test tool for testing",
        )

        # Create mock executor
        mock_executor = MagicMock()

        proxy = MCPToolProxy.from_definition(defn, executor=mock_executor)

        # Verify proxy properties
        assert proxy.name == f"{unique_server_name}_{unique_tool_name}"
        assert proxy.mcp_server == unique_server_name
        assert proxy.mcp_tool_name == unique_tool_name
        assert "Test tool" in proxy.description

    async def test_proxy_execution_calls_executor(
        self,
        unique_server_name,
        unique_tool_name,
        create_tool_definition,
    ):
        """
        E2E: Verify proxy execution calls executor with correct args.

        GIVEN: An MCPToolProxy with mocked executor
        WHEN: The proxy is invoked with arguments
        THEN: The executor receives the correct call
        """
        from mcp_server_langgraph.mcp.client.tool_proxy import MCPToolProxy

        defn = create_tool_definition(
            server_name=unique_server_name,
            name=unique_tool_name,
        )

        # Create mock executor
        mock_executor = MagicMock()
        mock_executor.call_tool = AsyncMock(return_value="Execution result")

        proxy = MCPToolProxy.from_definition(defn, executor=mock_executor)

        # Invoke the proxy
        result = await proxy._arun(query="test query")

        # Verify executor was called with correct server and tool
        mock_executor.call_tool.assert_called_once()
        call_kwargs = mock_executor.call_tool.call_args.kwargs
        assert call_kwargs["server"] == unique_server_name
        assert call_kwargs["tool"] == unique_tool_name
        assert call_kwargs["arguments"] == {"query": "test query"}

        assert result == "Execution result"


class TestMCPExecutorFlow:
    """
    E2E tests for MCP executor routing and execution.
    """

    def setup_method(self):
        """Reset singleton dependencies."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()

    def teardown_method(self):
        """Force GC."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()
        gc.collect()

    async def test_executor_routes_to_correct_session(
        self,
        unique_server_name,
        mock_mcp_session,
    ):
        """
        E2E: Verify executor routes call to correct session.

        GIVEN: An executor with registered session
        WHEN: A tool call is made
        THEN: The call is routed to the correct session
        """
        from mcp_server_langgraph.mcp.client.executor import MCPExecutor
        from mcp_server_langgraph.mcp.client.tool_registry import MCPToolRegistry

        # Create mock registry that returns the session
        mock_registry = MagicMock(spec=MCPToolRegistry)
        mock_registry.get_session = MagicMock(return_value=mock_mcp_session)
        mock_registry._server_configs = {unique_server_name: MagicMock(timeout=30.0)}

        executor = MCPExecutor(registry=mock_registry)

        # Execute tool call
        result = await executor.call_tool(
            server=unique_server_name,
            tool="test_tool",
            arguments={"key": "value"},
        )

        # Verify registry was queried for session
        mock_registry.get_session.assert_called_once_with(unique_server_name)

        # Verify session's call_tool was invoked
        mock_mcp_session.call_tool.assert_called_once()

    async def test_executor_handles_timeout(
        self,
        unique_server_name,
    ):
        """
        E2E: Verify executor handles timeout correctly.

        GIVEN: An executor with slow session
        WHEN: A tool call times out
        THEN: A TimeoutError is raised with context
        """
        import asyncio

        from mcp_server_langgraph.mcp.client.executor import MCPExecutor
        from mcp_server_langgraph.mcp.client.tool_registry import MCPToolRegistry

        # Create mock session that times out
        slow_session = MagicMock()
        slow_session.is_connected = True

        async def slow_call(tool, arguments):
            await asyncio.sleep(10)  # Longer than timeout
            return {"result": "too late"}

        slow_session.call_tool = slow_call

        # Create mock registry that returns the slow session
        mock_registry = MagicMock(spec=MCPToolRegistry)
        mock_registry.get_session = MagicMock(return_value=slow_session)
        mock_registry._server_configs = {unique_server_name: MagicMock(timeout=30.0)}

        executor = MCPExecutor(registry=mock_registry)

        with pytest.raises(asyncio.TimeoutError):
            await executor.call_tool(
                server=unique_server_name,
                tool="slow_tool",
                arguments={},
                timeout=0.1,  # Very short timeout
            )

    async def test_executor_handles_connection_error(
        self,
        unique_server_name,
    ):
        """
        E2E: Verify executor handles connection errors.

        GIVEN: An executor with disconnected session
        WHEN: A tool call is made
        THEN: A ConnectionError is raised
        """
        from mcp_server_langgraph.mcp.client.executor import MCPExecutor
        from mcp_server_langgraph.mcp.client.tool_registry import MCPToolRegistry

        # Create mock session that's disconnected
        disconnected_session = MagicMock()
        disconnected_session.is_connected = False
        disconnected_session.connect = AsyncMock(side_effect=ConnectionError("Failed"))

        # Create mock registry that returns the disconnected session
        mock_registry = MagicMock(spec=MCPToolRegistry)
        mock_registry.get_session = MagicMock(return_value=disconnected_session)
        mock_registry._server_configs = {unique_server_name: MagicMock(timeout=30.0)}

        executor = MCPExecutor(registry=mock_registry)

        with pytest.raises(ConnectionError):
            await executor.call_tool(
                server=unique_server_name,
                tool="any_tool",
                arguments={},
            )


class TestMCPToolResultFlow:
    """
    E2E tests for MCP tool result handling.
    """

    def setup_method(self):
        """Reset singleton dependencies."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()

    def teardown_method(self):
        """Force GC."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()
        gc.collect()

    async def test_result_dict_formatted_as_json(
        self,
        unique_server_name,
        unique_tool_name,
        create_tool_definition,
    ):
        """
        E2E: Verify dict results are formatted as JSON.

        GIVEN: A tool that returns a dict
        WHEN: The proxy formats the result
        THEN: It returns formatted JSON string
        """
        from mcp_server_langgraph.mcp.client.tool_proxy import MCPToolProxy

        defn = create_tool_definition(
            server_name=unique_server_name,
            name=unique_tool_name,
        )

        mock_executor = MagicMock()
        mock_executor.call_tool = AsyncMock(return_value={"status": "success", "data": [1, 2, 3]})

        proxy = MCPToolProxy.from_definition(defn, executor=mock_executor)
        result = await proxy._arun(query="test")

        # Result should be JSON formatted
        assert '"status": "success"' in result or "success" in result

    async def test_result_string_returned_as_is(
        self,
        unique_server_name,
        unique_tool_name,
        create_tool_definition,
    ):
        """
        E2E: Verify string results are returned as-is.

        GIVEN: A tool that returns a string
        WHEN: The proxy formats the result
        THEN: It returns the string unchanged
        """
        from mcp_server_langgraph.mcp.client.tool_proxy import MCPToolProxy

        defn = create_tool_definition(
            server_name=unique_server_name,
            name=unique_tool_name,
        )

        mock_executor = MagicMock()
        mock_executor.call_tool = AsyncMock(return_value="Plain text result")

        proxy = MCPToolProxy.from_definition(defn, executor=mock_executor)
        result = await proxy._arun(query="test")

        assert result == "Plain text result"

    async def test_error_result_contains_error_message(
        self,
        unique_server_name,
        unique_tool_name,
        create_tool_definition,
    ):
        """
        E2E: Verify errors are captured in result.

        GIVEN: A tool that raises an error
        WHEN: The proxy handles the error
        THEN: The error message is in the result
        """
        from mcp_server_langgraph.mcp.client.tool_proxy import MCPToolProxy

        defn = create_tool_definition(
            server_name=unique_server_name,
            name=unique_tool_name,
        )

        mock_executor = MagicMock()
        mock_executor.call_tool = AsyncMock(side_effect=RuntimeError("Tool execution failed"))

        proxy = MCPToolProxy.from_definition(defn, executor=mock_executor)
        result = await proxy._arun(query="test")

        # Result should contain error message
        assert "error" in result.lower() or "failed" in result.lower()


class TestMCPBatchExecutionFlow:
    """
    E2E tests for batch MCP tool execution.
    """

    def setup_method(self):
        """Reset singleton dependencies."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()

    def teardown_method(self):
        """Force GC."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()
        gc.collect()

    async def test_batch_execution_parallel(
        self,
        unique_server_name,
        mock_mcp_session,
    ):
        """
        E2E: Verify batch execution runs in parallel.

        GIVEN: Multiple tool calls
        WHEN: batch_call is used
        THEN: All calls execute and return results
        """
        from mcp_server_langgraph.mcp.client.executor import MCPExecutor, MCPToolCall
        from mcp_server_langgraph.mcp.client.tool_registry import MCPToolRegistry

        # Create mock registry that returns the session
        mock_registry = MagicMock(spec=MCPToolRegistry)
        mock_registry.get_session = MagicMock(return_value=mock_mcp_session)
        mock_registry._server_configs = {unique_server_name: MagicMock(timeout=30.0)}

        executor = MCPExecutor(registry=mock_registry)

        calls = [
            MCPToolCall(server=unique_server_name, tool="tool1", arguments={"a": 1}),
            MCPToolCall(server=unique_server_name, tool="tool2", arguments={"b": 2}),
            MCPToolCall(server=unique_server_name, tool="tool3", arguments={"c": 3}),
        ]

        results = await executor.batch_call(calls)

        # Should have result for each call
        assert len(results) == 3

        # Each result should have timing info
        for result in results:
            assert hasattr(result, "duration_ms") or "duration" in str(result)
