"""
Unit tests for search tools

Tests knowledge base and web search functionality.
"""

from unittest.mock import AsyncMock, MagicMock, patch

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

    @patch("mcp_server_langgraph.tools.search_tools.QdrantClient")
    @patch("mcp_server_langgraph.tools.search_tools.settings")
    def test_search_with_qdrant_configured(self, mock_settings, mock_qdrant_client):
        """Test search when Qdrant is properly configured"""
        # Configure Qdrant settings
        mock_settings.qdrant_url = "http://localhost"
        mock_settings.qdrant_port = 6333
        mock_settings.qdrant_collection_name = "test_collection"

        # Mock Qdrant client
        mock_client_instance = MagicMock()
        mock_qdrant_client.return_value = mock_client_instance

        result = search_knowledge_base.invoke({"query": "machine learning", "limit": 5})

        # Verify Qdrant client was created with correct params
        mock_qdrant_client.assert_called_once_with(url="http://localhost", port=6333)
        assert isinstance(result, str)
        assert "machine learning" in result
        assert "test_collection" in result

    @patch("mcp_server_langgraph.tools.search_tools.QdrantClient")
    @patch("mcp_server_langgraph.tools.search_tools.settings")
    def test_search_qdrant_connection_error(self, mock_settings, mock_qdrant_client):
        """Test search handles Qdrant connection errors gracefully"""
        mock_settings.qdrant_url = "http://localhost"
        mock_settings.qdrant_port = 6333

        # Simulate connection error
        mock_qdrant_client.side_effect = ConnectionError("Connection refused")

        result = search_knowledge_base.invoke({"query": "test", "limit": 5})

        assert isinstance(result, str)
        assert "error" in result.lower()
        assert "Connection refused" in result

    @patch("mcp_server_langgraph.tools.search_tools.QdrantClient")
    @patch("mcp_server_langgraph.tools.search_tools.settings")
    def test_search_qdrant_query_error(self, mock_settings, mock_qdrant_client):
        """Test search handles Qdrant query errors"""
        mock_settings.qdrant_url = "http://localhost"
        mock_settings.qdrant_port = 6333

        # Mock client that raises on query
        mock_client_instance = MagicMock()
        mock_client_instance.search.side_effect = Exception("Collection not found")
        mock_qdrant_client.return_value = mock_client_instance

        result = search_knowledge_base.invoke({"query": "test", "limit": 5})

        assert isinstance(result, str)
        # Should show configured message even if query fails
        assert "Qdrant" in result


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

        result = await web_search.ainvoke({"query": "test query", "num_results": 5})
        assert isinstance(result, str)
        assert "not configured" in result.lower()  # Shows configuration message

    @pytest.mark.asyncio
    @patch("mcp_server_langgraph.tools.search_tools.settings")
    async def test_web_search_different_result_counts(self, mock_settings):
        """Test web search with different result counts"""
        mock_settings.tavily_api_key = None
        mock_settings.serper_api_key = None

        result = await web_search.ainvoke({"query": "test", "num_results": 3})
        assert isinstance(result, str)

    @pytest.mark.asyncio
    @patch("mcp_server_langgraph.tools.search_tools.settings")
    async def test_web_search_default_results(self, mock_settings):
        """Test web search uses default result count"""
        mock_settings.tavily_api_key = None
        result = await web_search.ainvoke({"query": "test"})
        assert isinstance(result, str)

    @pytest.mark.asyncio
    @patch("mcp_server_langgraph.tools.search_tools.settings")
    async def test_web_search_shows_api_notice(self, mock_settings):
        """Test that updated implementation shows API configuration notice"""
        mock_settings.tavily_api_key = None
        mock_settings.serper_api_key = None
        mock_settings.brave_api_key = None

        result = await web_search.ainvoke({"query": "test", "num_results": 5})
        assert "not configured" in result.lower()  # Updated implementation

    @pytest.mark.asyncio
    @patch("mcp_server_langgraph.tools.search_tools.httpx.AsyncClient")
    @patch("mcp_server_langgraph.tools.search_tools.settings")
    async def test_web_search_tavily_success(self, mock_settings, mock_async_client):
        """Test successful web search with Tavily API"""
        mock_settings.tavily_api_key = "test-tavily-key"
        mock_settings.serper_api_key = None

        # Mock Tavily API response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {"title": "Result 1", "content": "Content for result 1", "url": "https://example.com/1"},
                {"title": "Result 2", "content": "Content for result 2", "url": "https://example.com/2"},
            ]
        }
        mock_response.raise_for_status = MagicMock()

        # Mock client context manager
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_async_client.return_value.__aenter__.return_value = mock_client_instance

        result = await web_search.ainvoke({"query": "Python programming", "num_results": 2})

        # Verify API was called correctly
        mock_client_instance.post.assert_called_once()
        call_args = mock_client_instance.post.call_args
        assert call_args[0][0] == "https://api.tavily.com/search"
        assert call_args[1]["json"]["query"] == "Python programming"
        assert call_args[1]["json"]["max_results"] == 2

        # Verify response formatting
        assert isinstance(result, str)
        assert "Python programming" in result
        assert "Result 1" in result
        assert "Result 2" in result
        assert "https://example.com/1" in result

    @pytest.mark.asyncio
    @patch("mcp_server_langgraph.tools.search_tools.httpx.AsyncClient")
    @patch("mcp_server_langgraph.tools.search_tools.settings")
    async def test_web_search_serper_success(self, mock_settings, mock_async_client):
        """Test successful web search with Serper API"""
        mock_settings.tavily_api_key = None
        mock_settings.serper_api_key = "test-serper-key"

        # Mock Serper API response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "organic": [
                {"title": "Serper Result 1", "snippet": "Snippet 1", "link": "https://example.com/serper1"},
                {"title": "Serper Result 2", "snippet": "Snippet 2", "link": "https://example.com/serper2"},
            ]
        }
        mock_response.raise_for_status = MagicMock()

        # Mock client context manager
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_async_client.return_value.__aenter__.return_value = mock_client_instance

        result = await web_search.ainvoke({"query": "machine learning", "num_results": 2})

        # Verify API was called correctly
        mock_client_instance.post.assert_called_once()
        call_args = mock_client_instance.post.call_args
        assert call_args[0][0] == "https://google.serper.dev/search"
        assert call_args[1]["json"]["q"] == "machine learning"
        assert call_args[1]["json"]["num"] == 2
        assert call_args[1]["headers"]["X-API-KEY"] == "test-serper-key"

        # Verify response formatting
        assert isinstance(result, str)
        assert "machine learning" in result
        assert "Serper Result 1" in result
        assert "Snippet 1" in result

    @pytest.mark.asyncio
    @patch("mcp_server_langgraph.tools.search_tools.httpx.AsyncClient")
    @patch("mcp_server_langgraph.tools.search_tools.settings")
    async def test_web_search_tavily_network_error(self, mock_settings, mock_async_client):
        """Test web search handles Tavily network errors gracefully"""
        mock_settings.tavily_api_key = "test-tavily-key"

        # Mock network error
        mock_client_instance = AsyncMock()
        mock_client_instance.post.side_effect = Exception("Network timeout")
        mock_async_client.return_value.__aenter__.return_value = mock_client_instance

        result = await web_search.ainvoke({"query": "test", "num_results": 5})

        # Should fallback to config message
        assert isinstance(result, str)
        assert "not configured" in result.lower() or "Web search" in result

    @pytest.mark.asyncio
    @patch("mcp_server_langgraph.tools.search_tools.httpx.AsyncClient")
    @patch("mcp_server_langgraph.tools.search_tools.settings")
    async def test_web_search_serper_api_error(self, mock_settings, mock_async_client):
        """Test web search handles Serper API errors"""
        mock_settings.tavily_api_key = None
        mock_settings.serper_api_key = "test-serper-key"

        # Mock API error response
        mock_response = AsyncMock()
        mock_response.status_code = 429  # Rate limit
        mock_response.raise_for_status.side_effect = Exception("Rate limit exceeded")

        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_async_client.return_value.__aenter__.return_value = mock_client_instance

        result = await web_search.ainvoke({"query": "test", "num_results": 5})

        # Should handle error gracefully
        assert isinstance(result, str)

    @pytest.mark.asyncio
    @patch("mcp_server_langgraph.tools.search_tools.httpx.AsyncClient")
    @patch("mcp_server_langgraph.tools.search_tools.settings")
    async def test_web_search_tavily_invalid_response(self, mock_settings, mock_async_client):
        """Test web search handles invalid Tavily JSON response"""
        mock_settings.tavily_api_key = "test-tavily-key"

        # Mock invalid response (missing 'results' key)
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"error": "Invalid API key"}
        mock_response.raise_for_status = MagicMock()

        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_async_client.return_value.__aenter__.return_value = mock_client_instance

        result = await web_search.ainvoke({"query": "test", "num_results": 5})

        assert isinstance(result, str)
        # Should handle missing results gracefully
        assert "No results found" in result or "Web search" in result

    @pytest.mark.asyncio
    @patch("mcp_server_langgraph.tools.search_tools.httpx.AsyncClient")
    @patch("mcp_server_langgraph.tools.search_tools.settings")
    async def test_web_search_timeout_handling(self, mock_settings, mock_async_client):
        """Test web search handles timeout errors"""
        import httpx

        mock_settings.tavily_api_key = "test-tavily-key"

        # Mock timeout error
        mock_client_instance = AsyncMock()
        mock_client_instance.post.side_effect = httpx.TimeoutException("Request timeout")
        mock_async_client.return_value.__aenter__.return_value = mock_client_instance

        result = await web_search.ainvoke({"query": "test", "num_results": 5})

        assert isinstance(result, str)


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
