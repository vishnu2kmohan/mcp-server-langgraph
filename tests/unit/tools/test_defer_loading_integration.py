"""
TDD: Integration tests for Defer Loading with MCP tools/list handler

Tests the integration of defer_loading with the MCP server's tools/list
response, following Anthropic's Advanced Tool Use best practices.

RED phase: These tests define expected behavior before implementation.
"""

import gc
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.defer_loading, pytest.mark.mcp]


class TestDeferLoadingMCPIntegration:
    """Test defer_loading integration with MCP tools/list handler."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_mcp_tools_list_excludes_deferred_when_flag_enabled(self):
        """GIVEN defer_loading feature is enabled and tools are deferred
        WHEN calling MCP tools/list
        THEN deferred tools should be excluded from response
        """
        from mcp_server_langgraph.tools.defer_loading import (
            _DEFERRED_TOOLS,
            register_deferred_tool,
        )

        # Save original state
        original = _DEFERRED_TOOLS.copy()

        try:
            # Register a tool as deferred
            register_deferred_tool("specialized_analyzer")

            # Mock feature flag as enabled
            with patch(
                "mcp_server_langgraph.mcp.server_streamable.is_defer_loading_enabled",
                side_effect=lambda *a, **kw: True,
            ):
                with patch("mcp_server_langgraph.mcp.server_streamable.is_tool_deferred") as mock_is_deferred:
                    mock_is_deferred.side_effect = lambda name: name in _DEFERRED_TOOLS

                    # The tools list should filter out deferred tools
                    # This test verifies the integration exists
                    from mcp_server_langgraph.mcp.server_streamable import (
                        filter_deferred_tools,
                    )

                    mock_tools = [
                        MagicMock(name="agent_chat"),
                        MagicMock(name="specialized_analyzer"),
                        MagicMock(name="web_search"),
                    ]
                    # Set the name attribute properly for MagicMock
                    mock_tools[0].name = "agent_chat"
                    mock_tools[1].name = "specialized_analyzer"
                    mock_tools[2].name = "web_search"

                    filtered = filter_deferred_tools(mock_tools)
                    filtered_names = [t.name for t in filtered]

                    assert "specialized_analyzer" not in filtered_names
                    assert "agent_chat" in filtered_names
                    assert "web_search" in filtered_names
        finally:
            _DEFERRED_TOOLS.clear()
            _DEFERRED_TOOLS.update(original)

    @pytest.mark.asyncio
    async def test_mcp_tools_list_includes_all_when_flag_disabled(self):
        """GIVEN defer_loading feature is disabled
        WHEN calling MCP tools/list
        THEN all tools should be included (no filtering)
        """
        from mcp_server_langgraph.tools.defer_loading import (
            _DEFERRED_TOOLS,
            register_deferred_tool,
        )

        # Save original state
        original = _DEFERRED_TOOLS.copy()

        try:
            register_deferred_tool("specialized_analyzer")

            # Mock feature flag as disabled
            with patch(
                "mcp_server_langgraph.mcp.server_streamable.is_defer_loading_enabled",
                side_effect=lambda *a, **kw: False,
            ):
                from mcp_server_langgraph.mcp.server_streamable import (
                    filter_deferred_tools,
                )

                mock_tools = [
                    MagicMock(name="agent_chat"),
                    MagicMock(name="specialized_analyzer"),
                    MagicMock(name="web_search"),
                ]
                mock_tools[0].name = "agent_chat"
                mock_tools[1].name = "specialized_analyzer"
                mock_tools[2].name = "web_search"

                # When flag is disabled, all tools should be returned
                filtered = filter_deferred_tools(mock_tools)
                filtered_names = [t.name for t in filtered]

                assert "specialized_analyzer" in filtered_names
                assert "agent_chat" in filtered_names
                assert "web_search" in filtered_names
        finally:
            _DEFERRED_TOOLS.clear()
            _DEFERRED_TOOLS.update(original)


class TestDeferLoadingSearchDiscovery:
    """Test that deferred tools are discoverable via search endpoints."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_search_tools_finds_deferred_tools(self):
        """GIVEN a deferred tool
        WHEN searching via search_tools
        THEN the deferred tool should be discoverable
        """
        from mcp_server_langgraph.tools.defer_loading import (
            _DEFERRED_TOOLS,
            get_deferred_tools,
            register_deferred_tool,
        )

        # Save original state
        original = _DEFERRED_TOOLS.copy()

        try:
            register_deferred_tool("calculator")

            # get_deferred_tools should return deferred tools for search
            deferred = get_deferred_tools()
            deferred_names = [t.name for t in deferred]

            # Calculator should be discoverable via search
            assert "calculator" in deferred_names
        finally:
            _DEFERRED_TOOLS.clear()
            _DEFERRED_TOOLS.update(original)

    @pytest.mark.asyncio
    async def test_get_tool_by_name_returns_deferred_tool(self):
        """GIVEN a deferred tool
        WHEN requesting it by name
        THEN the tool should be returned
        """
        from mcp_server_langgraph.tools import get_tool_by_name
        from mcp_server_langgraph.tools.defer_loading import (
            _DEFERRED_TOOLS,
            register_deferred_tool,
        )

        # Save original state
        original = _DEFERRED_TOOLS.copy()

        try:
            register_deferred_tool("calculator")

            # Even though deferred, should still be accessible by name
            tool = get_tool_by_name("calculator")
            assert tool is not None
            assert tool.name == "calculator"
        finally:
            _DEFERRED_TOOLS.clear()
            _DEFERRED_TOOLS.update(original)


class TestDeferLoadingFeatureGated:
    """Test feature flag gating for defer_loading."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_is_defer_loading_enabled_helper_exists(self):
        """GIVEN the server_streamable module
        WHEN importing is_defer_loading_enabled
        THEN it should be available
        """
        from mcp_server_langgraph.mcp.server_streamable import (
            is_defer_loading_enabled,
        )

        # Should be callable
        assert callable(is_defer_loading_enabled)

    def test_filter_deferred_tools_function_exists(self):
        """GIVEN the server_streamable module
        WHEN importing filter_deferred_tools
        THEN it should be available
        """
        from mcp_server_langgraph.mcp.server_streamable import (
            filter_deferred_tools,
        )

        # Should be callable
        assert callable(filter_deferred_tools)
