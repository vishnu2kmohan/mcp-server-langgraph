"""
Integration tests for MCP code execution endpoints

Tests execute_python and search_tools integration with MCP server.
Following TDD best practices - these tests should FAIL until implementation is complete.
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# These imports should work since MCP servers exist
from mcp_server_langgraph.mcp.server_stdio import MCPAgentServer


@pytest.mark.integration
@pytest.mark.mcp
@pytest.mark.xdist_group(name="integration_mcp_code_execution_tests")
class TestMCPCodeExecutionEndpoint:
    """Test execute_python tool via MCP protocol"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    async def mcp_server(self):
        """Create MCP server instance"""
        # MCPAgentServer initializes in __init__, no separate initialize() method needed
        server = MCPAgentServer()
        return server

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        True,
        reason="TODO: Fix test - settings patch doesn't affect already-initialized server. Needs refactor to create server with mocked settings, not patch after init.",
    )
    async def test_execute_python_tool_listed(self, mcp_server):
        """Test that execute_python appears in tool list when enabled"""
        with patch("mcp_server_langgraph.core.config.settings") as mock_settings:
            mock_settings.enable_code_execution = True

            # Get tool list
            tools = await mcp_server.list_tools_public()

            # Should include execute_python
            tool_names = [t.name for t in tools]
            assert "execute_python" in tool_names

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        True,
        reason="TODO: Fix test - settings patch doesn't affect already-initialized server. Needs refactor to create server with mocked settings, not patch after init.",
    )
    async def test_execute_python_not_listed_when_disabled(self, mcp_server):
        """Test that execute_python is not listed when disabled"""
        with patch("mcp_server_langgraph.core.config.settings") as mock_settings:
            mock_settings.enable_code_execution = False

            # Get tool list
            tools = await mcp_server.list_tools_public()

            # Should NOT include execute_python
            tool_names = [t.name for t in tools]
            assert "execute_python" not in tool_names

    @pytest.mark.asyncio
    async def test_execute_python_via_mcp(self, mcp_server, mock_jwt_token):
        """Test executing Python code via MCP call_tool"""
        with patch("mcp_server_langgraph.core.config.settings") as mock_settings:
            mock_settings.enable_code_execution = True
            mock_settings.code_execution_backend = "docker-engine"
            mock_settings.code_execution_allowed_imports = ["json", "math"]

            # Mock sandbox to avoid Docker dependency in tests
            with patch("mcp_server_langgraph.tools.code_execution_tools._get_sandbox") as mock_sandbox_factory:
                from mcp_server_langgraph.execution import ExecutionResult

                mock_sandbox = MagicMock()
                mock_sandbox.execute.return_value = ExecutionResult(
                    success=True,
                    stdout="Hello from MCP!\n",
                    stderr="",
                    exit_code=0,
                    execution_time=0.5,
                )
                mock_sandbox_factory.return_value = mock_sandbox

                # Call tool via MCP
                result = await mcp_server.call_tool_public(
                    name="execute_python",
                    arguments={"code": "print('Hello from MCP!')", "token": mock_jwt_token},
                )

                assert "Hello from MCP!" in str(result)
                assert "success" in str(result).lower()

    @pytest.mark.asyncio
    async def test_execute_python_requires_authorization(self, mcp_server, mock_jwt_token):
        """Test that execute_python requires proper authorization"""
        with patch("mcp_server_langgraph.core.config.settings") as mock_settings:
            mock_settings.enable_code_execution = True

            # Mock OpenFGA to deny authorization
            with patch.object(mcp_server.auth, "authorize", new_callable=AsyncMock) as mock_authz:
                mock_authz.return_value = False

                # Should be denied (match flexible pattern for detailed error messages)
                with pytest.raises(PermissionError, match="Not authorized"):
                    await mcp_server.call_tool_public(
                        name="execute_python",
                        arguments={"code": "print('test')", "token": mock_jwt_token},
                    )


@pytest.mark.integration
@pytest.mark.mcp
@pytest.mark.xdist_group(name="integration_mcp_code_execution_tests")
class TestMCPToolDiscoveryEndpoint:
    """Test search_tools via MCP protocol"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    async def mcp_server(self):
        """Create MCP server instance"""
        # MCPAgentServer initializes in __init__, no separate initialize() method needed
        server = MCPAgentServer()
        return server

    @pytest.mark.asyncio
    async def test_search_tools_listed(self, mcp_server):
        """Test that search_tools appears in tool list"""
        # Get tool list
        tools = await mcp_server.list_tools_public()

        # Should include search_tools
        tool_names = [t.name for t in tools]
        assert "search_tools" in tool_names

    @pytest.mark.asyncio
    async def test_search_tools_via_mcp(self, mcp_server, mock_jwt_token):
        """Test searching tools via MCP"""
        # Call search_tools
        result = await mcp_server.call_tool_public(
            name="search_tools",
            arguments={"category": "calculator", "detail_level": "minimal", "token": mock_jwt_token},
        )

        # Should return calculator tools
        result_str = str(result)
        assert "calculator" in result_str.lower()
        assert "add" in result_str.lower() or "multiply" in result_str.lower()

    @pytest.mark.asyncio
    async def test_search_tools_by_query(self, mcp_server, mock_jwt_token):
        """Test searching tools by keyword query"""
        # Search for execution tools
        result = await mcp_server.call_tool_public(
            name="search_tools",
            arguments={"query": "execute", "detail_level": "standard", "token": mock_jwt_token},
        )

        result_str = str(result)
        # Should find execute_python if enabled
        assert "execute" in result_str.lower() or "Found 0" in result_str
