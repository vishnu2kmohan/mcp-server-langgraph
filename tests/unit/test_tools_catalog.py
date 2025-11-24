"""
Unit tests for tools catalog and registry

Tests tool organization and access patterns.
"""

import gc

import pytest
from langchain_core.tools import BaseTool

from mcp_server_langgraph.tools import ALL_TOOLS, CALCULATOR_TOOLS, FILESYSTEM_TOOLS, SEARCH_TOOLS, get_tool_by_name, get_tools

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="testtoolscatalog")
class TestToolsCatalog:
    """Test suite for tools catalog"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_all_tools_count(self):
        """Test that ALL_TOOLS contains expected number of tools"""
        assert len(ALL_TOOLS) == 10  # 5 calculator + 2 search + 3 filesystem

    def test_all_tools_are_base_tool(self):
        """Test that all tools are BaseTool instances"""
        for tool in ALL_TOOLS:
            assert isinstance(tool, BaseTool)

    def test_all_tools_have_unique_names(self):
        """Test that all tools have unique names"""
        names = [tool.name for tool in ALL_TOOLS]
        assert len(names) == len(set(names))  # No duplicates

    def test_calculator_tools_count(self):
        """Test calculator tools group"""
        assert len(CALCULATOR_TOOLS) == 5

    def test_search_tools_count(self):
        """Test search tools group"""
        assert len(SEARCH_TOOLS) == 2

    def test_filesystem_tools_count(self):
        """Test filesystem tools group"""
        assert len(FILESYSTEM_TOOLS) == 3

    def test_get_tools_all(self):
        """Test get_tools returns all tools when no categories specified"""
        tools = get_tools()
        assert len(tools) == len(ALL_TOOLS)

    def test_get_tools_by_category(self):
        """Test get_tools with specific categories"""
        calculator_tools = get_tools(["calculator"])
        assert len(calculator_tools) == 5

        search_tools = get_tools(["search"])
        assert len(search_tools) == 2

        filesystem_tools = get_tools(["filesystem"])
        assert len(filesystem_tools) == 3

    def test_get_tools_multiple_categories(self):
        """Test get_tools with multiple categories"""
        tools = get_tools(["calculator", "search"])
        assert len(tools) == 7  # 5 calculator + 2 search

    def test_get_tools_invalid_category(self):
        """Test get_tools with invalid category returns empty list"""
        tools = get_tools(["invalid_category"])
        assert len(tools) == 0

    def test_get_tool_by_name_existing(self):
        """Test getting tool by name"""
        tool = get_tool_by_name("calculator")
        assert tool is not None
        assert tool.name == "calculator"

        tool = get_tool_by_name("add")
        assert tool is not None
        assert tool.name == "add"

    def test_get_tool_by_name_nonexistent(self):
        """Test getting nonexistent tool returns None"""
        tool = get_tool_by_name("nonexistent_tool")
        assert tool is None

    def test_all_tools_have_descriptions(self):
        """Test that all tools have descriptions"""
        for tool in ALL_TOOLS:
            assert tool.description is not None
            assert len(tool.description) > 0

    def test_all_tools_have_args_schema(self):
        """Test that all tools have args schema"""
        for tool in ALL_TOOLS:
            assert tool.args_schema is not None

    def test_tool_names_match_expected(self):
        """Test that tool names match expected values"""
        expected_names = {
            # Calculator tools
            "calculator",
            "add",
            "subtract",
            "multiply",
            "divide",
            # Search tools
            "search_knowledge_base",
            "web_search",
            # Filesystem tools
            "read_file",
            "list_directory",
            "search_files",
        }

        actual_names = {tool.name for tool in ALL_TOOLS}
        assert actual_names == expected_names


@pytest.mark.unit
@pytest.mark.xdist_group(name="testtoolinvocation")
class TestToolInvocation:
    """Test tool invocation patterns"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_tools_are_invocable(self):
        """Test that all tools can be invoked"""
        # Test with simple calculator tool
        tool = get_tool_by_name("add")
        assert tool is not None

        result = tool.invoke({"a": 2, "b": 3})
        assert result == "5.0"

    def test_tools_handle_errors_gracefully(self):
        """Test that tools handle errors without crashing"""
        tool = get_tool_by_name("divide")
        assert tool is not None

        # Should return error message, not raise exception
        result = tool.invoke({"a": 5, "b": 0})
        assert "Error" in result

    def test_tool_schemas_are_serializable(self):
        """Test that tool schemas can be serialized to JSON"""
        import json

        for tool in ALL_TOOLS:
            schema = tool.args_schema.model_json_schema()
            # Should not raise exception
            json_str = json.dumps(schema)
            assert len(json_str) > 0
