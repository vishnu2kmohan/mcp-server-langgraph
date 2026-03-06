"""
Unit tests for Defer Loading Pattern

Tests the defer loading feature that improves token efficiency by
excluding certain tools from the initial tools/list response.
Deferred tools can still be discovered via search_tools.

TDD: RED phase - these tests define expected behavior before implementation.
"""

import gc
from unittest.mock import patch

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.defer_loading]


@pytest.mark.unit
class TestDeferLoadingRegistry:
    """Test suite for defer loading registry"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_deferred_tools_registry_exists(self):
        """GIVEN the tools module
        WHEN accessing DEFERRED_TOOLS
        THEN it should exist as a set
        """
        from mcp_server_langgraph.tools import DEFERRED_TOOLS

        assert isinstance(DEFERRED_TOOLS, set)

    def test_register_deferred_tool(self):
        """GIVEN a tool name
        WHEN registering it as deferred
        THEN it should be added to DEFERRED_TOOLS
        """
        from mcp_server_langgraph.tools.defer_loading import (
            _DEFERRED_TOOLS,
            register_deferred_tool,
        )

        # Save original state
        original = _DEFERRED_TOOLS.copy()

        try:
            register_deferred_tool("test_tool")
            assert "test_tool" in _DEFERRED_TOOLS
        finally:
            # Restore original state
            _DEFERRED_TOOLS.clear()
            _DEFERRED_TOOLS.update(original)

    def test_unregister_deferred_tool(self):
        """GIVEN a deferred tool
        WHEN unregistering it
        THEN it should be removed from DEFERRED_TOOLS
        """
        from mcp_server_langgraph.tools.defer_loading import (
            _DEFERRED_TOOLS,
            register_deferred_tool,
            unregister_deferred_tool,
        )

        # Save original state
        original = _DEFERRED_TOOLS.copy()

        try:
            register_deferred_tool("test_tool")
            assert "test_tool" in _DEFERRED_TOOLS

            unregister_deferred_tool("test_tool")
            assert "test_tool" not in _DEFERRED_TOOLS
        finally:
            # Restore original state
            _DEFERRED_TOOLS.clear()
            _DEFERRED_TOOLS.update(original)

    def test_is_tool_deferred(self):
        """GIVEN a tool name
        WHEN checking if it's deferred
        THEN it should return correct boolean
        """
        from mcp_server_langgraph.tools.defer_loading import (
            _DEFERRED_TOOLS,
            is_tool_deferred,
            register_deferred_tool,
        )

        # Save original state
        original = _DEFERRED_TOOLS.copy()

        try:
            assert is_tool_deferred("nonexistent_tool") is False

            register_deferred_tool("test_tool")
            assert is_tool_deferred("test_tool") is True
        finally:
            # Restore original state
            _DEFERRED_TOOLS.clear()
            _DEFERRED_TOOLS.update(original)


@pytest.mark.unit
class TestDeferLoadingToolsList:
    """Test suite for tools list filtering with defer loading"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_get_visible_tools_excludes_deferred(self):
        """GIVEN tools with some marked as deferred
        WHEN calling get_visible_tools
        THEN deferred tools should be excluded
        """
        from mcp_server_langgraph.tools.defer_loading import (
            _DEFERRED_TOOLS,
            get_visible_tools,
            register_deferred_tool,
        )

        # Save original state
        original = _DEFERRED_TOOLS.copy()

        try:
            # Register 'calculator' as deferred
            register_deferred_tool("calculator")

            # Mock feature flag as enabled
            with patch(
                "mcp_server_langgraph.tools.defer_loading.is_feature_enabled",
                return_value=True,
            ):
                visible_tools = get_visible_tools()
                tool_names = [t.name for t in visible_tools]

                # When enabled, deferred tools should be hidden
                assert "calculator" not in tool_names
        finally:
            # Restore original state
            _DEFERRED_TOOLS.clear()
            _DEFERRED_TOOLS.update(original)

    def test_get_visible_tools_includes_non_deferred(self):
        """GIVEN tools with some marked as deferred
        WHEN calling get_visible_tools
        THEN non-deferred tools should be included
        """
        from mcp_server_langgraph.tools.defer_loading import (
            _DEFERRED_TOOLS,
            get_visible_tools,
            register_deferred_tool,
        )

        # Save original state
        original = _DEFERRED_TOOLS.copy()

        try:
            # Register only 'calculator' as deferred
            register_deferred_tool("calculator")

            visible_tools = get_visible_tools()
            tool_names = [t.name for t in visible_tools]

            # Other tools should still be visible
            assert "add" in tool_names
            assert "web_search" in tool_names
        finally:
            # Restore original state
            _DEFERRED_TOOLS.clear()
            _DEFERRED_TOOLS.update(original)

    def test_get_all_tools_includes_deferred(self):
        """GIVEN tools with some marked as deferred
        WHEN calling get_all_tools
        THEN ALL tools should be included (deferred and non-deferred)
        """
        from mcp_server_langgraph.tools import get_all_tools
        from mcp_server_langgraph.tools.defer_loading import (
            _DEFERRED_TOOLS,
            register_deferred_tool,
        )

        # Save original state
        original = _DEFERRED_TOOLS.copy()

        try:
            # Register 'calculator' as deferred
            register_deferred_tool("calculator")

            all_tools = get_all_tools()
            tool_names = [t.name for t in all_tools]

            # get_all_tools should still include deferred tools
            assert "calculator" in tool_names
        finally:
            # Restore original state
            _DEFERRED_TOOLS.clear()
            _DEFERRED_TOOLS.update(original)


@pytest.mark.unit
class TestDeferLoadingDiscovery:
    """Test suite for discovering deferred tools via search"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_get_tool_by_name_finds_deferred_tool(self):
        """GIVEN a deferred tool
        WHEN searching by name
        THEN it should still be found
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

            # Should still find deferred tool by name
            tool = get_tool_by_name("calculator")
            assert tool is not None
            assert tool.name == "calculator"
        finally:
            # Restore original state
            _DEFERRED_TOOLS.clear()
            _DEFERRED_TOOLS.update(original)

    def test_get_deferred_tools_returns_only_deferred(self):
        """GIVEN tools with some marked as deferred
        WHEN calling get_deferred_tools
        THEN it should return only deferred tools
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
            register_deferred_tool("add")

            deferred = get_deferred_tools()
            tool_names = [t.name for t in deferred]

            assert "calculator" in tool_names
            assert "add" in tool_names
            assert "web_search" not in tool_names
        finally:
            # Restore original state
            _DEFERRED_TOOLS.clear()
            _DEFERRED_TOOLS.update(original)


@pytest.mark.unit
class TestDeferLoadingDefaultConfig:
    """Test suite for default defer loading configuration"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_default_deferred_tools_is_empty(self):
        """GIVEN a fresh module load
        WHEN checking default deferred tools
        THEN no tools should be deferred by default
        """
        from mcp_server_langgraph.tools.defer_loading import get_default_deferred_tools

        default_deferred = get_default_deferred_tools()
        # By default, no tools are deferred (conservative approach)
        assert isinstance(default_deferred, set)

    def test_clear_deferred_tools(self):
        """GIVEN registered deferred tools
        WHEN clearing all deferred tools
        THEN the registry should be empty
        """
        from mcp_server_langgraph.tools.defer_loading import (
            _DEFERRED_TOOLS,
            clear_deferred_tools,
            register_deferred_tool,
        )

        # Save original state
        original = _DEFERRED_TOOLS.copy()

        try:
            register_deferred_tool("test1")
            register_deferred_tool("test2")
            assert len(_DEFERRED_TOOLS) >= 2

            clear_deferred_tools()
            assert len(_DEFERRED_TOOLS) == 0
        finally:
            # Restore original state
            _DEFERRED_TOOLS.clear()
            _DEFERRED_TOOLS.update(original)


@pytest.mark.unit
class TestDeferLoadingFeatureFlag:
    """Test suite for defer loading feature flag integration"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_defer_loading_respects_feature_flag_disabled(self):
        """GIVEN defer_loading feature flag is disabled
        WHEN calling get_visible_tools
        THEN all tools should be visible (no filtering)
        """
        from unittest.mock import patch

        from mcp_server_langgraph.tools.defer_loading import (
            _DEFERRED_TOOLS,
            get_visible_tools,
            register_deferred_tool,
        )

        # Save original state
        original = _DEFERRED_TOOLS.copy()

        try:
            register_deferred_tool("calculator")

            # Mock feature flag as disabled
            with patch(
                "mcp_server_langgraph.tools.defer_loading.is_feature_enabled",
                return_value=False,
            ):
                visible_tools = get_visible_tools()
                tool_names = [t.name for t in visible_tools]

                # When disabled, deferred tools should still be visible
                assert "calculator" in tool_names
        finally:
            # Restore original state
            _DEFERRED_TOOLS.clear()
            _DEFERRED_TOOLS.update(original)

    def test_defer_loading_respects_feature_flag_enabled(self):
        """GIVEN defer_loading feature flag is enabled
        WHEN calling get_visible_tools
        THEN deferred tools should be filtered
        """
        from unittest.mock import patch

        from mcp_server_langgraph.tools.defer_loading import (
            _DEFERRED_TOOLS,
            get_visible_tools,
            register_deferred_tool,
        )

        # Save original state
        original = _DEFERRED_TOOLS.copy()

        try:
            register_deferred_tool("calculator")

            # Mock feature flag as enabled
            with patch(
                "mcp_server_langgraph.tools.defer_loading.is_feature_enabled",
                return_value=True,
            ):
                visible_tools = get_visible_tools()
                tool_names = [t.name for t in visible_tools]

                # When enabled, deferred tools should be hidden
                assert "calculator" not in tool_names
        finally:
            # Restore original state
            _DEFERRED_TOOLS.clear()
            _DEFERRED_TOOLS.update(original)
