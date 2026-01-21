"""
Tests for tools/constants.py module.

TDD: These tests define the expected behavior for tool constants.
"""

import pytest


class TestToolCategoryMap:
    """Tests for TOOL_CATEGORY_MAP."""

    def test_category_map_is_dict(self) -> None:
        """TOOL_CATEGORY_MAP should be a dict mapping tool names to categories."""
        from mcp_server_langgraph.tools.constants import TOOL_CATEGORY_MAP

        assert isinstance(TOOL_CATEGORY_MAP, dict)
        assert len(TOOL_CATEGORY_MAP) > 0

    def test_category_map_has_expected_tools(self) -> None:
        """TOOL_CATEGORY_MAP should contain known tool mappings."""
        from mcp_server_langgraph.tools.constants import TOOL_CATEGORY_MAP

        # Core tools that should always exist
        expected_tools = [
            ("calculator", "calculator"),
            ("web_search", "search"),
            ("execute_python", "code_execution"),
            ("read_file", "filesystem"),
            ("web_fetch", "web"),
        ]

        for tool_name, expected_category in expected_tools:
            assert tool_name in TOOL_CATEGORY_MAP, f"{tool_name} should be in TOOL_CATEGORY_MAP"
            assert TOOL_CATEGORY_MAP[tool_name] == expected_category


class TestSandboxRequiredTools:
    """Tests for SANDBOX_REQUIRED_TOOLS."""

    def test_sandbox_required_tools_is_frozenset(self) -> None:
        """SANDBOX_REQUIRED_TOOLS should be a frozenset."""
        from mcp_server_langgraph.tools.constants import SANDBOX_REQUIRED_TOOLS

        assert isinstance(SANDBOX_REQUIRED_TOOLS, frozenset)
        assert len(SANDBOX_REQUIRED_TOOLS) > 0

    def test_sandbox_required_tools_contains_risky_tools(self) -> None:
        """SANDBOX_REQUIRED_TOOLS should contain known risky tools."""
        from mcp_server_langgraph.tools.constants import SANDBOX_REQUIRED_TOOLS

        risky_tools = ["execute_bash", "execute_python", "edit_file", "write_file"]

        for tool_name in risky_tools:
            assert tool_name in SANDBOX_REQUIRED_TOOLS, f"{tool_name} should require sandbox"


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_get_tool_category_returns_category(self) -> None:
        """get_tool_category should return the category for known tools."""
        from mcp_server_langgraph.tools.constants import get_tool_category

        assert get_tool_category("calculator") == "calculator"
        assert get_tool_category("web_search") == "search"
        assert get_tool_category("execute_python") == "code_execution"

    def test_get_tool_category_returns_none_for_unknown(self) -> None:
        """get_tool_category should return None for unknown tools."""
        from mcp_server_langgraph.tools.constants import get_tool_category

        assert get_tool_category("unknown_tool") is None

    def test_get_display_name_converts_snake_case(self) -> None:
        """get_display_name should convert snake_case to Title Case."""
        from mcp_server_langgraph.tools.constants import get_display_name

        assert get_display_name("web_search") == "Web Search"
        assert get_display_name("execute_python") == "Execute Python"
        assert get_display_name("calculator") == "Calculator"

    def test_tool_requires_sandbox(self) -> None:
        """tool_requires_sandbox should return True for risky tools."""
        from mcp_server_langgraph.tools.constants import tool_requires_sandbox

        assert tool_requires_sandbox("execute_bash") is True
        assert tool_requires_sandbox("execute_python") is True
        assert tool_requires_sandbox("calculator") is False
        assert tool_requires_sandbox("web_search") is False
