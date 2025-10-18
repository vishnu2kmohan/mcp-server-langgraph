"""
Unit tests for search tools

Tests knowledge base and web search functionality.
"""

from unittest.mock import patch

import pytest

from mcp_server_langgraph.tools.search_tools import search_knowledge_base, web_search


@pytest.mark.unit
class TestSearchKnowledgeBase:
    """Test suite for search_knowledge_base tool"""

    @patch("mcp_server_langgraph.tools.search_tools.settings")
    def test_search_with_query(self, mock_settings):
        """Test search with a query string"""
        mock_settings.qdrant_url = None  # Not configured
        result = search_knowledge_base.invoke({"query": "test query", "limit": 5})
        assert isinstance(result, str)
        assert "not configured" in result.lower()  # Shows configuration message

    @patch("mcp_server_langgraph.tools.search_tools.settings")
    def test_search_with_different_limits(self, mock_settings):
        """Test search with different result limits"""
        mock_settings.qdrant_url = None
        for limit in [3, 10]:
            result = search_knowledge_base.invoke({"query": "test", "limit": limit})
            assert isinstance(result, str)

    @patch("mcp_server_langgraph.tools.search_tools.settings")
    def test_search_default_limit(self, mock_settings):
        """Test search uses default limit"""
        mock_settings.qdrant_url = None
        result = search_knowledge_base.invoke({"query": "test"})
        assert isinstance(result, str)

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

    @pytest.mark.asyncio
    @patch("mcp_server_langgraph.tools.search_tools.settings")
    async def test_web_search_with_query(self, mock_settings):
        """Test web search with a query"""
        mock_settings.tavily_api_key = None
        mock_settings.serper_api_key = None
        mock_settings.brave_api_key = None

        result = await web_search.invoke({"query": "test query", "num_results": 5})
        assert isinstance(result, str)
        assert "not configured" in result.lower()  # Shows configuration message

    @pytest.mark.asyncio
    @patch("mcp_server_langgraph.tools.search_tools.settings")
    async def test_web_search_different_result_counts(self, mock_settings):
        """Test web search with different result counts"""
        mock_settings.tavily_api_key = None
        mock_settings.serper_api_key = None

        result = await web_search.invoke({"query": "test", "num_results": 3})
        assert isinstance(result, str)

    @pytest.mark.asyncio
    @patch("mcp_server_langgraph.tools.search_tools.settings")
    async def test_web_search_default_results(self, mock_settings):
        """Test web search uses default result count"""
        mock_settings.tavily_api_key = None
        result = await web_search.invoke({"query": "test"})
        assert isinstance(result, str)

    @pytest.mark.asyncio
    @patch("mcp_server_langgraph.tools.search_tools.settings")
    async def test_web_search_shows_api_notice(self, mock_settings):
        """Test that updated implementation shows API configuration notice"""
        mock_settings.tavily_api_key = None
        mock_settings.serper_api_key = None
        mock_settings.brave_api_key = None

        result = await web_search.invoke({"query": "test", "num_results": 5})
        assert "not configured" in result.lower()  # Updated implementation


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
