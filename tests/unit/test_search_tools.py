"""
Unit tests for search tools

Tests knowledge base and web search functionality.
"""

import pytest

from mcp_server_langgraph.tools.search_tools import search_knowledge_base, web_search


@pytest.mark.unit
class TestSearchKnowledgeBase:
    """Test suite for search_knowledge_base tool"""

    def test_search_with_query(self):
        """Test search with a query string"""
        result = search_knowledge_base.invoke({"query": "test query", "limit": 5})
        assert isinstance(result, str)
        assert "test query" in result
        assert "PLACEHOLDER" in result  # Current placeholder implementation

    def test_search_with_different_limits(self):
        """Test search with different result limits"""
        result1 = search_knowledge_base.invoke({"query": "test", "limit": 3})
        result2 = search_knowledge_base.invoke({"query": "test", "limit": 10})
        assert "Top 3 results" in result1
        assert "Top 10 results" in result2

    def test_search_default_limit(self):
        """Test search uses default limit"""
        result = search_knowledge_base.invoke({"query": "test"})
        assert "Top 5 results" in result  # Default limit is 5

    def test_search_empty_query(self):
        """Test search with empty query"""
        result = search_knowledge_base.invoke({"query": "", "limit": 5})
        assert isinstance(result, str)

    def test_search_long_query(self):
        """Test search handles long queries"""
        long_query = "a" * 500  # Maximum query length
        result = search_knowledge_base.invoke({"query": long_query, "limit": 5})
        assert isinstance(result, str)


@pytest.mark.unit
class TestWebSearch:
    """Test suite for web_search tool"""

    def test_web_search_with_query(self):
        """Test web search with a query"""
        result = web_search.invoke({"query": "test query", "num_results": 5})
        assert isinstance(result, str)
        assert "test query" in result
        assert "PLACEHOLDER" in result  # Current placeholder implementation

    def test_web_search_different_result_counts(self):
        """Test web search with different result counts"""
        result1 = web_search.invoke({"query": "test", "num_results": 3})
        result2 = web_search.invoke({"query": "test", "num_results": 8})
        assert "Top 3 results" in result1
        assert "Top 8 results" in result2

    def test_web_search_default_results(self):
        """Test web search uses default result count"""
        result = web_search.invoke({"query": "test"})
        assert "Top 5 results" in result  # Default is 5

    def test_web_search_shows_api_notice(self):
        """Test that placeholder shows API configuration notice"""
        result = web_search.invoke({"query": "test", "num_results": 5})
        assert "API not configured" in result or "PLACEHOLDER" in result


@pytest.mark.unit
class TestSearchToolSchemas:
    """Test search tool schemas"""

    def test_search_knowledge_base_schema(self):
        """Test search_knowledge_base has proper schema"""
        assert search_knowledge_base.name == "search_knowledge_base"
        assert search_knowledge_base.description is not None
        schema = search_knowledge_base.args_schema.schema()
        assert "query" in str(schema)
        assert "limit" in str(schema)

    def test_web_search_schema(self):
        """Test web_search has proper schema"""
        assert web_search.name == "web_search"
        assert web_search.description is not None
        schema = web_search.args_schema.schema()
        assert "query" in str(schema)
        assert "num_results" in str(schema)
