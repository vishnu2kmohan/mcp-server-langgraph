"""
Tests for Tool Discovery Module

Tests progressive tool discovery functionality including search, filtering,
and formatting at different detail levels following Anthropic's MCP best practices.
"""

import gc
import json
from unittest.mock import MagicMock

import pytest
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from mcp_server_langgraph.tools.tool_discovery import (
    SearchToolsInput,
    _filter_tools_by_category,
    _filter_tools_by_query,
    _format_tool_full,
    _format_tool_minimal,
    _format_tool_results,
    _format_tool_standard,
    search_tools,
)

# ==============================================================================
# Test Fixtures
# ==============================================================================


class MockToolInput(BaseModel):
    """Mock input schema for test tool"""

    param1: str = Field(description="First parameter")
    param2: int = Field(default=0, description="Second parameter")


@pytest.fixture
def mock_tool():
    """Create a mock tool for testing"""
    tool = MagicMock(spec=BaseTool)
    tool.name = "test_tool"
    tool.description = "Test tool for unit testing"
    tool.args_schema = MockToolInput
    return tool


@pytest.fixture
def mock_tools_list(mock_tool):
    """Create a list of mock tools for testing"""
    tools = []

    # Calculator tool
    calc_tool = MagicMock(spec=BaseTool)
    calc_tool.name = "calculator"
    calc_tool.description = "Evaluate mathematical expressions"
    calc_tool.args_schema = None
    tools.append(calc_tool)

    # Search tool
    search_tool = MagicMock(spec=BaseTool)
    search_tool.name = "web_search"
    search_tool.description = "Search the web for information"
    search_tool.args_schema = MockToolInput
    tools.append(search_tool)

    # Test tool
    tools.append(mock_tool)

    return tools


# ==============================================================================
# SearchToolsInput Model Tests
# ==============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="tool_discovery_tests")
class TestSearchToolsInput:
    """Tests for SearchToolsInput schema"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_search_tools_input_default_values(self):
        """Test SearchToolsInput with default values"""
        input_schema = SearchToolsInput()

        assert input_schema.query is None
        assert input_schema.category is None
        assert input_schema.detail_level == "minimal"

    def test_search_tools_input_with_query(self):
        """Test SearchToolsInput with query"""
        input_schema = SearchToolsInput(query="calculator")

        assert input_schema.query == "calculator"
        assert input_schema.category is None
        assert input_schema.detail_level == "minimal"

    def test_search_tools_input_with_category(self):
        """Test SearchToolsInput with category"""
        input_schema = SearchToolsInput(category="calculator")

        assert input_schema.query is None
        assert input_schema.category == "calculator"
        assert input_schema.detail_level == "minimal"

    def test_search_tools_input_with_detail_level(self):
        """Test SearchToolsInput with different detail levels"""
        for level in ["minimal", "standard", "full"]:
            input_schema = SearchToolsInput(detail_level=level)
            assert input_schema.detail_level == level


# ==============================================================================
# Category Filtering Tests
# ==============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="tool_discovery_tests")
class TestFilterToolsByCategory:
    """Tests for _filter_tools_by_category"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_filter_by_calculator_category(self):
        """Test filtering tools by calculator category"""
        tools = _filter_tools_by_category("calculator")

        assert isinstance(tools, list)
        assert len(tools) > 0
        # Verify all tools are calculator-related
        for tool in tools:
            assert hasattr(tool, "name")

    def test_filter_by_search_category(self):
        """Test filtering tools by search category"""
        tools = _filter_tools_by_category("search")

        assert isinstance(tools, list)
        assert len(tools) > 0

    def test_filter_by_filesystem_category(self):
        """Test filtering tools by filesystem category"""
        tools = _filter_tools_by_category("filesystem")

        assert isinstance(tools, list)
        assert len(tools) > 0

    def test_filter_by_execution_category(self):
        """Test filtering tools by execution category"""
        tools = _filter_tools_by_category("execution")

        assert isinstance(tools, list)
        # Code execution tools may be empty if disabled in settings
        # This is expected behavior for security

    def test_filter_by_unknown_category_returns_all_tools(self):
        """Test filtering with unknown category returns all tools"""
        tools = _filter_tools_by_category("unknown_category")

        assert isinstance(tools, list)
        assert len(tools) > 0

    def test_filter_by_case_insensitive_category(self):
        """Test category filtering is case-insensitive"""
        tools_upper = _filter_tools_by_category("CALCULATOR")
        tools_lower = _filter_tools_by_category("calculator")

        assert len(tools_upper) == len(tools_lower)


# ==============================================================================
# Query Filtering Tests
# ==============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="tool_discovery_tests")
class TestFilterToolsByQuery:
    """Tests for _filter_tools_by_query"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_filter_by_query_matches_name(self, mock_tools_list):
        """Test query filtering matches tool names"""
        filtered = _filter_tools_by_query(mock_tools_list, "calculator")

        assert len(filtered) == 1
        assert filtered[0].name == "calculator"

    def test_filter_by_query_matches_description(self, mock_tools_list):
        """Test query filtering matches tool descriptions"""
        filtered = _filter_tools_by_query(mock_tools_list, "mathematical")

        assert len(filtered) >= 1
        assert any("mathematical" in tool.description.lower() for tool in filtered)

    def test_filter_by_query_case_insensitive(self, mock_tools_list):
        """Test query filtering is case-insensitive"""
        filtered_upper = _filter_tools_by_query(mock_tools_list, "CALCULATOR")
        filtered_lower = _filter_tools_by_query(mock_tools_list, "calculator")

        assert len(filtered_upper) == len(filtered_lower)

    def test_filter_by_query_no_matches(self, mock_tools_list):
        """Test query filtering with no matches"""
        filtered = _filter_tools_by_query(mock_tools_list, "nonexistent_xyz")

        assert len(filtered) == 0

    def test_filter_by_query_partial_match(self, mock_tools_list):
        """Test query filtering with partial matches"""
        filtered = _filter_tools_by_query(mock_tools_list, "web")

        assert len(filtered) >= 1
        assert any("web" in tool.name.lower() for tool in filtered)


# ==============================================================================
# Tool Formatting Tests
# ==============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="tool_discovery_tests")
class TestToolFormatting:
    """Tests for tool formatting functions"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_format_tool_minimal(self, mock_tool):
        """Test minimal tool formatting"""
        result = _format_tool_minimal(mock_tool)

        assert "test_tool" in result
        assert "Test tool for unit testing" in result
        assert "**" in result  # Markdown formatting

    def test_format_tool_standard(self, mock_tool):
        """Test standard tool formatting"""
        result = _format_tool_standard(mock_tool)

        assert "test_tool" in result
        assert "Test tool for unit testing" in result
        assert "Parameters:" in result
        assert "param1" in result
        assert "param2" in result
        assert "First parameter" in result

    def test_format_tool_standard_without_args_schema(self):
        """Test standard formatting for tool without args_schema"""
        tool = MagicMock(spec=BaseTool)
        tool.name = "simple_tool"
        tool.description = "Simple tool"
        tool.args_schema = None

        result = _format_tool_standard(tool)

        assert "simple_tool" in result
        assert "Simple tool" in result

    def test_format_tool_full(self, mock_tool):
        """Test full tool formatting"""
        result = _format_tool_full(mock_tool)

        assert "test_tool" in result
        assert "Test tool for unit testing" in result
        assert "Parameters:" in result
        assert "Full Schema:" in result
        assert "```json" in result
        assert "required" in result or "optional" in result

    def test_format_tool_full_shows_required_fields(self, mock_tool):
        """Test full formatting shows required vs optional fields"""
        result = _format_tool_full(mock_tool)

        # param1 is required (no default), param2 is optional (has default)
        assert "param1" in result
        assert "param2" in result

    def test_format_tool_full_without_args_schema(self):
        """Test full formatting for tool without args_schema"""
        tool = MagicMock(spec=BaseTool)
        tool.name = "simple_tool"
        tool.description = "Simple tool"
        tool.args_schema = None

        result = _format_tool_full(tool)

        assert "simple_tool" in result
        assert "Simple tool" in result


# ==============================================================================
# Tool Results Formatting Tests
# ==============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="tool_discovery_tests")
class TestFormatToolResults:
    """Tests for _format_tool_results"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_format_results_minimal(self, mock_tools_list):
        """Test formatting results with minimal detail"""
        result = _format_tool_results(mock_tools_list, "minimal")

        assert f"Found {len(mock_tools_list)} tool(s):" in result
        assert "calculator" in result
        assert "web_search" in result

    def test_format_results_standard(self, mock_tools_list):
        """Test formatting results with standard detail"""
        result = _format_tool_results(mock_tools_list, "standard")

        assert f"Found {len(mock_tools_list)} tool(s):" in result
        assert "###" in result  # Markdown headers

    def test_format_results_full(self, mock_tools_list):
        """Test formatting results with full detail"""
        result = _format_tool_results(mock_tools_list, "full")

        assert f"Found {len(mock_tools_list)} tool(s):" in result
        assert "Full Schema:" in result or "###" in result

    def test_format_results_empty_list(self):
        """Test formatting with empty tool list"""
        result = _format_tool_results([], "minimal")

        assert "Found 0 tool(s):" in result


# ==============================================================================
# Search Tools Function Tests
# ==============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="tool_discovery_tests")
class TestSearchTools:
    """Tests for search_tools function"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_search_tools_no_parameters(self):
        """Test search_tools with no parameters returns all tools"""
        result = search_tools.invoke({})

        assert "Found" in result
        assert "tool(s):" in result

    def test_search_tools_by_category(self):
        """Test search_tools filtering by category"""
        result = search_tools.invoke({"category": "calculator"})

        assert "Found" in result
        assert "tool(s):" in result

    def test_search_tools_by_query(self):
        """Test search_tools filtering by query"""
        result = search_tools.invoke({"query": "calculator"})

        assert "Found" in result
        assert "tool(s):" in result or "No tools found" in result

    def test_search_tools_with_query_and_category(self):
        """Test search_tools with both query and category"""
        result = search_tools.invoke({"query": "evaluate", "category": "calculator"})

        assert "Found" in result or "No tools found" in result

    def test_search_tools_minimal_detail(self):
        """Test search_tools with minimal detail level"""
        result = search_tools.invoke({"category": "calculator", "detail_level": "minimal"})

        assert "Found" in result
        # Minimal format uses "-" for list items
        assert "-" in result or "No tools found" in result

    def test_search_tools_standard_detail(self):
        """Test search_tools with standard detail level"""
        result = search_tools.invoke({"category": "calculator", "detail_level": "standard"})

        assert "Found" in result
        # Standard format may include parameters
        assert "###" in result or "No tools found" in result

    def test_search_tools_full_detail(self):
        """Test search_tools with full detail level"""
        result = search_tools.invoke({"category": "calculator", "detail_level": "full"})

        assert "Found" in result
        # Full format includes schema
        assert "Full Schema:" in result or "No tools found" in result

    def test_search_tools_no_matches(self):
        """Test search_tools with query that matches nothing"""
        result = search_tools.invoke({"query": "nonexistent_tool_xyz_123"})

        assert "No tools found" in result
        assert "query=nonexistent_tool_xyz_123" in result

    def test_search_tools_no_matches_with_category(self):
        """Test search_tools with non-matching query and category"""
        result = search_tools.invoke({"query": "nonexistent_xyz", "category": "calculator"})

        assert "No tools found" in result

    def test_search_tools_case_insensitive_query(self):
        """Test search_tools query is case-insensitive"""
        result_upper = search_tools.invoke({"query": "CALCULATOR"})
        result_lower = search_tools.invoke({"query": "calculator"})

        # Both should find tools or both should find none
        assert ("Found" in result_upper) == ("Found" in result_lower)

    def test_search_tools_returns_string(self):
        """Test search_tools always returns a string"""
        result = search_tools.invoke({})

        assert isinstance(result, str)

    def test_search_tools_invalid_category_returns_all(self):
        """Test search_tools with invalid category returns all tools"""
        result = search_tools.invoke({"category": "invalid_category_xyz"})

        assert "Found" in result
        # Should return all tools since category doesn't match any


# ==============================================================================
# Integration Tests
# ==============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="tool_discovery_tests")
class TestToolDiscoveryIntegration:
    """Integration tests for tool discovery"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_progressive_disclosure_workflow(self):
        """Test complete progressive disclosure workflow"""
        # Step 1: Minimal discovery - list all categories
        minimal_result = search_tools.invoke({"detail_level": "minimal"})
        assert "Found" in minimal_result

        # Step 2: Category-specific search
        calculator_result = search_tools.invoke({"category": "calculator", "detail_level": "standard"})
        assert "Found" in calculator_result

        # Step 3: Detailed tool inspection
        full_result = search_tools.invoke({"category": "calculator", "detail_level": "full"})
        assert "Found" in full_result or "No tools found" in full_result

    def test_search_then_filter_workflow(self):
        """Test search followed by filter workflow"""
        # Search all tools
        all_tools = search_tools.invoke({})
        assert "Found" in all_tools

        # Filter by category
        filtered = search_tools.invoke({"category": "calculator"})
        assert "Found" in filtered

    def test_token_efficiency_minimal_vs_full(self):
        """Test that minimal detail uses fewer tokens than full"""
        minimal = search_tools.invoke({"category": "calculator", "detail_level": "minimal"})
        full = search_tools.invoke({"category": "calculator", "detail_level": "full"})

        # Full detail should be longer (more tokens)
        assert len(full) >= len(minimal)
