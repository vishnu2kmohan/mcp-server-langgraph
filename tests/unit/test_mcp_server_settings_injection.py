"""
Unit tests for MCPAgentServer settings injection.

Tests verify that settings can be injected into MCPAgentServer at construction time,
allowing runtime configuration of features like code execution without module reloading.
"""

import gc
import os
from unittest.mock import MagicMock

import pytest

from mcp_server_langgraph.core.config import Settings
from mcp_server_langgraph.mcp.server_stdio import MCPAgentServer

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="test_settings_injection")
class TestMCPServerSettingsInjection:
    """Test MCPAgentServer settings injection functionality"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_server_accepts_settings_parameter(self):
        """
        Test that MCPAgentServer constructor accepts optional settings parameter.

        This enables dependency injection for testing and runtime configuration.
        """
        # GIVEN: Custom settings with specific configuration
        custom_settings = Settings(enable_code_execution=True)

        # WHEN: Creating server with injected settings
        server = MCPAgentServer(settings=custom_settings)

        # THEN: Server should store the injected settings
        assert server.settings is custom_settings
        assert server.settings.enable_code_execution is True

    @pytest.mark.asyncio
    async def test_server_uses_global_settings_by_default(self):
        """
        Test backward compatibility: server uses global settings when none injected.

        Ensures existing code continues to work without modification.
        """
        # WHEN: Creating server without settings parameter
        server = MCPAgentServer()

        # THEN: Server should use global settings
        from mcp_server_langgraph.core import config

        # NOTE: Use equality check (==) instead of identity (is) for xdist compatibility.
        # In pytest-xdist parallel mode, module imports may result in different
        # Settings instances across workers. What matters functionally is that
        # the settings values are equivalent, not that they're the same object.
        assert server.settings == config.settings

    @pytest.mark.asyncio
    async def test_code_execution_tools_appear_when_enabled(self):
        """
        Test that execute_python tool appears when code execution is enabled.

        This is the primary use case: enabling code execution via settings injection.
        """
        # GIVEN: Settings with code execution enabled
        settings_with_execution = Settings(enable_code_execution=True)

        # WHEN: Creating server and listing tools
        server = MCPAgentServer(settings=settings_with_execution)
        tools = await server.list_tools_public()

        # THEN: execute_python tool should be in the list
        tool_names = [tool.name for tool in tools]
        assert "execute_python" in tool_names, f"execute_python not found in {tool_names}"

    @pytest.mark.asyncio
    async def test_code_execution_tools_hidden_when_disabled(self):
        """
        Test that execute_python tool is hidden when code execution is disabled.

        Verifies runtime evaluation of settings (not import-time caching).
        """
        # GIVEN: Settings with code execution disabled
        settings_without_execution = Settings(enable_code_execution=False)

        # WHEN: Creating server and listing tools
        server = MCPAgentServer(settings=settings_without_execution)
        tools = await server.list_tools_public()

        # THEN: execute_python tool should NOT be in the list
        tool_names = [tool.name for tool in tools]
        assert "execute_python" not in tool_names, f"execute_python should be hidden but found in {tool_names}"

    @pytest.mark.asyncio
    async def test_multiple_servers_with_different_settings(self):
        """
        Test that multiple server instances with different settings work independently.

        Ensures settings isolation between instances (no global state pollution).
        """
        # GIVEN: Two different settings configurations
        settings_enabled = Settings(enable_code_execution=True)
        settings_disabled = Settings(enable_code_execution=False)

        # WHEN: Creating two servers with different settings
        server_with_execution = MCPAgentServer(settings=settings_enabled)
        server_without_execution = MCPAgentServer(settings=settings_disabled)

        # THEN: Each server should respect its own settings
        tools_enabled = await server_with_execution.list_tools_public()
        tools_disabled = await server_without_execution.list_tools_public()

        tools_enabled_names = [tool.name for tool in tools_enabled]
        tools_disabled_names = [tool.name for tool in tools_disabled]

        assert "execute_python" in tools_enabled_names, "Server with enabled setting should have execute_python"
        assert "execute_python" not in tools_disabled_names, "Server with disabled setting should not have execute_python"

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        os.getenv("PYTEST_XDIST_WORKER") is not None, reason="Settings isolation test may interfere with parallel execution"
    )
    async def test_settings_injection_does_not_affect_global_settings(self):
        """
        Test that injecting settings into a server doesn't modify global settings.

        Ensures no side effects on the global configuration object.
        """
        # GIVEN: Initial global settings state
        from mcp_server_langgraph.core import config

        original_code_execution = config.settings.enable_code_execution

        # WHEN: Creating server with different settings
        custom_settings = Settings(enable_code_execution=not original_code_execution)
        server = MCPAgentServer(settings=custom_settings)

        # THEN: Global settings should remain unchanged
        assert (
            config.settings.enable_code_execution == original_code_execution
        ), "Global settings should not be modified by injecting custom settings"

        # AND: Server should use custom settings
        assert server.settings.enable_code_execution == (not original_code_execution)

    @pytest.mark.asyncio
    async def test_settings_injection_with_other_dependencies(self):
        """
        Test that settings injection works alongside other dependency injection (auth).

        Ensures compatibility with existing DI pattern.
        """
        # GIVEN: Mock auth middleware and custom settings
        mock_auth = MagicMock()
        custom_settings = Settings(enable_code_execution=True)

        # WHEN: Creating server with both auth and settings injection
        server = MCPAgentServer(auth=mock_auth, settings=custom_settings)

        # THEN: Both dependencies should be properly injected
        assert server.auth is mock_auth
        assert server.settings is custom_settings
        assert server.settings.enable_code_execution is True
