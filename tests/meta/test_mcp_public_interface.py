"""
Meta-test: Validate MCP Public Interface

This test ensures that MCPAgentServer exposes expected public methods,
preventing regressions where tests try to call non-existent methods.

Related: OpenAI Codex Finding 2025-11-15 - Integration test failures due to
missing call_tool_public() method.
"""

import gc
import inspect

import pytest

pytestmark = pytest.mark.meta


@pytest.mark.meta
@pytest.mark.xdist_group(name="mcp_public_interface")
class TestMCPPublicInterface:
    """Validate MCPAgentServer public interface"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_mcp_server_has_call_tool_public(self):
        """
        Verify MCPAgentServer.call_tool_public() method exists and is callable.

        This prevents regression of the issue where integration tests tried to call
        call_tool() directly on the server instance, but it was only available as
        an inner function in the decorator.

        References:
        - src/mcp_server_langgraph/mcp/server_stdio.py:272-355
        - tests/integration/test_mcp_code_execution.py:91,112,150,163
        """
        from mcp_server_langgraph.mcp.server_stdio import MCPAgentServer

        # Verify method exists
        assert hasattr(MCPAgentServer, "call_tool_public"), (
            "MCPAgentServer must expose call_tool_public() method for testing. "
            "Integration tests rely on this method to invoke tools without MCP protocol overhead."
        )

        # Verify it's a coroutine function (async method)
        assert inspect.iscoroutinefunction(MCPAgentServer.call_tool_public), (
            "MCPAgentServer.call_tool_public() must be an async method"
        )

        # Verify signature
        sig = inspect.signature(MCPAgentServer.call_tool_public)
        params = list(sig.parameters.keys())

        assert "name" in params, "call_tool_public() must accept 'name' parameter"
        assert "arguments" in params, "call_tool_public() must accept 'arguments' parameter"

    def test_mcp_server_has_list_tools_public(self):
        """
        Verify MCPAgentServer.list_tools_public() method exists and is callable.

        This follows the same pattern as call_tool_public - a public method
        that the MCP protocol handler delegates to.

        References:
        - src/mcp_server_langgraph/mcp/server_stdio.py:164-270
        """
        from mcp_server_langgraph.mcp.server_stdio import MCPAgentServer

        # Verify method exists
        assert hasattr(MCPAgentServer, "list_tools_public"), "MCPAgentServer must expose list_tools_public() method"

        # Verify it's a coroutine function (async method)
        assert inspect.iscoroutinefunction(MCPAgentServer.list_tools_public), (
            "MCPAgentServer.list_tools_public() must be an async method"
        )

    def test_mcp_server_has_auth_attribute(self):
        """
        Verify MCPAgentServer.auth attribute exists for authorization.

        This prevents regression where tests try to patch authorization methods
        that don't exist.

        References:
        - src/mcp_server_langgraph/mcp/server_stdio.py:335 (self.auth.authorize)
        - tests/integration/test_mcp_code_execution.py:106 (patch target)
        """
        from mcp_server_langgraph.mcp.server_stdio import MCPAgentServer

        # Create instance to verify initialization
        server = MCPAgentServer()

        assert hasattr(server, "auth"), "MCPAgentServer must have 'auth' attribute for authorization"

        # Verify auth has authorize method
        assert hasattr(server.auth, "authorize"), "MCPAgentServer.auth must have 'authorize' method"

        # Verify authorize is a coroutine function
        assert inspect.iscoroutinefunction(server.auth.authorize), "MCPAgentServer.auth.authorize() must be an async method"

    def test_mcp_server_public_methods_are_documented(self):
        """
        Verify public methods have docstrings explaining their purpose.

        Good documentation helps prevent confusion about which methods are
        for testing vs production use.
        """
        from mcp_server_langgraph.mcp.server_stdio import MCPAgentServer

        public_methods = ["call_tool_public", "list_tools_public"]

        for method_name in public_methods:
            method = getattr(MCPAgentServer, method_name)
            assert method.__doc__, f"{method_name} must have a docstring"
            assert len(method.__doc__) > 50, f"{method_name} docstring should be descriptive (>50 chars)"
