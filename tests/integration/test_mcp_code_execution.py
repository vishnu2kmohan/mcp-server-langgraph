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
    async def mcp_server(self, register_mcp_test_users):
        """
        Create MCP server instance with pre-configured auth for tests.

        Uses constructor-based dependency injection to provide AuthMiddleware
        with registered test users. This ensures authorization works in fallback mode.

        OpenAI Codex Finding Fix (2025-11-16):
        =======================================
        Previous implementation tried to add users AFTER server creation, causing
        "user not found" failures. New pattern injects pre-configured auth.
        """
        from unittest.mock import MagicMock

        from mcp_server_langgraph.auth.middleware import AuthMiddleware
        from mcp_server_langgraph.core.config import Settings

        # Create auth middleware with pre-registered user provider
        auth = AuthMiddleware(
            secret_key=register_mcp_test_users.secret_key,
            user_provider=register_mcp_test_users,
            openfga_client=None,
            session_store=None,
            settings=MagicMock(
                allow_auth_fallback=True,
                environment="test",
            ),
        )

        # Create server with injected auth (uses new constructor parameter)
        server = MCPAgentServer(auth=auth)

        return server

    @pytest.fixture
    async def mcp_server_with_code_execution(self, register_mcp_test_users):
        """
        Create MCP server with code execution ENABLED.

        Uses settings dependency injection to enable code execution at runtime
        without module reloading or environment variable manipulation.

        OpenAI Codex Finding Fix (2025-11-16) - UPDATED:
        =================================================
        Now uses Settings dependency injection instead of module reloading.
        This is cleaner, faster, and avoids the settings caching issue entirely.
        """
        from unittest.mock import MagicMock

        from mcp_server_langgraph.auth.middleware import AuthMiddleware
        from mcp_server_langgraph.core.config import Settings

        # Create test settings with code execution enabled
        test_settings = Settings(
            enable_code_execution=True,
            environment="test",
            auth_provider="inmemory",
            allow_auth_fallback=True,
        )

        # Create auth middleware with pre-registered user provider
        auth = AuthMiddleware(
            secret_key=register_mcp_test_users.secret_key,
            user_provider=register_mcp_test_users,
            openfga_client=None,
            session_store=None,
            settings=MagicMock(
                allow_auth_fallback=True,
                environment="test",
            ),
        )

        # Create server with injected auth AND settings
        server = MCPAgentServer(auth=auth, settings=test_settings)

        return server

    @pytest.mark.asyncio
    async def test_execute_python_tool_listed(self, mcp_server_with_code_execution):
        """
        Test that execute_python appears in tool list when enabled.

        OpenAI Codex Finding Fix (2025-11-16):
        =======================================
        Now uses dedicated fixture with code execution enabled VIA environment
        variable BEFORE server creation, not post-init patching.
        """
        # Get tool list from server with code execution enabled
        tools = await mcp_server_with_code_execution.list_tools_public()

        # Should include execute_python
        tool_names = [t.name for t in tools]
        assert "execute_python" in tool_names, f"execute_python not found in {tool_names}"

    @pytest.mark.asyncio
    async def test_execute_python_not_listed_when_disabled(self, mcp_server):
        """
        Test that execute_python is not listed when disabled.

        Uses default mcp_server fixture which has code execution disabled
        (default settings).

        OpenAI Codex Finding Fix (2025-11-16):
        =======================================
        No longer tries to patch settings post-init. Instead relies on default
        settings (code execution disabled) via regular mcp_server fixture.
        """
        # Get tool list from server with default settings (code execution disabled)
        tools = await mcp_server.list_tools_public()

        # Should NOT include execute_python
        tool_names = [t.name for t in tools]
        assert "execute_python" not in tool_names, f"execute_python should not be in {tool_names}"

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
    async def mcp_server(self, register_mcp_test_users):
        """
        Create MCP server instance with pre-configured auth for tests.

        Uses constructor-based dependency injection to provide AuthMiddleware
        with registered test users. This ensures authorization works in fallback mode.

        OpenAI Codex Finding Fix (2025-11-16):
        =======================================
        Previous implementation tried to add users AFTER server creation, causing
        "user not found" failures. New pattern injects pre-configured auth.
        """
        from unittest.mock import MagicMock

        from mcp_server_langgraph.auth.middleware import AuthMiddleware
        from mcp_server_langgraph.core.config import Settings

        # Create auth middleware with pre-registered user provider
        auth = AuthMiddleware(
            secret_key=register_mcp_test_users.secret_key,
            user_provider=register_mcp_test_users,
            openfga_client=None,
            session_store=None,
            settings=MagicMock(
                allow_auth_fallback=True,
                environment="test",
            ),
        )

        # Create server with injected auth (uses new constructor parameter)
        server = MCPAgentServer(auth=auth)

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
