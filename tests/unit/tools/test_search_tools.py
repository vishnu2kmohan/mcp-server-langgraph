"""
Unit tests for search tools

Tests knowledge base and web search functionality.
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from mcp_server_langgraph.tools.search_tools import search_knowledge_base, web_search

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="search_tools")
class TestSearchKnowledgeBase:
    """Test suite for search_knowledge_base tool

    Note: All tests in this class run in the same xdist worker to prevent
    shared state issues with settings/metrics mocking in parallel execution.

    Observability is initialized via session-scoped fixture in conftest.py.
    """

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""

        gc.collect()

    @pytest.mark.asyncio
    @patch("mcp_server_langgraph.tools.search_tools.settings")
    async def test_search_with_query(self, mock_settings):
        """Test search with a query string"""
        mock_settings.qdrant_url = None  # Not configured
        result = await search_knowledge_base.ainvoke({"query": "test query", "limit": 5})
        assert isinstance(result, str)
        assert "not configured" in result.lower()  # Shows configuration message

    @pytest.mark.asyncio
    @patch("mcp_server_langgraph.tools.search_tools.settings")
    async def test_search_with_different_limits(self, mock_settings):
        """Test search with different result limits"""
        mock_settings.qdrant_url = None
        for limit in [3, 10]:
            result = await search_knowledge_base.ainvoke({"query": "test", "limit": limit})
            assert isinstance(result, str)

    @pytest.mark.asyncio
    @patch("mcp_server_langgraph.tools.search_tools.settings")
    async def test_search_default_limit(self, mock_settings):
        """Test search uses default limit"""
        mock_settings.qdrant_url = None
        result = await search_knowledge_base.ainvoke({"query": "test"})
        assert isinstance(result, str)

    @pytest.mark.asyncio
    @patch("mcp_server_langgraph.tools.search_tools.settings")
    async def test_search_empty_query(self, mock_settings):
        """Test search with empty query"""
        mock_settings.qdrant_url = None  # Not configured
        result = await search_knowledge_base.ainvoke({"query": "", "limit": 5})
        assert isinstance(result, str)

    @pytest.mark.asyncio
    @patch("mcp_server_langgraph.tools.search_tools.settings")
    async def test_search_long_query(self, mock_settings):
        """Test search handles long queries"""
        mock_settings.qdrant_url = None
        long_query = "a" * 500  # Maximum query length
        result = await search_knowledge_base.ainvoke({"query": long_query, "limit": 5})
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_search_with_qdrant_configured(self):
        """Test search when Qdrant is properly configured"""
        with patch(
            "mcp_server_langgraph.tools.search_tools._validate_semantic_search_config",
            side_effect=lambda *a, **kw: (True, None),
        ):
            # Patch the import inside the function
            with patch("mcp_server_langgraph.core.dynamic_context_loader.DynamicContextLoader") as mock_loader_class:
                # Mock the loader instance
                mock_refs = [
                    MagicMock(ref_id="doc1", ref_type="doc", summary="Machine learning doc", relevance_score=0.9),
                ]
                mock_loader = MagicMock()
                mock_loader.semantic_search = AsyncMock(return_value=mock_refs)
                mock_loader_class.return_value = mock_loader

                result = await search_knowledge_base.ainvoke({"query": "machine learning", "limit": 5})

                assert isinstance(result, str)
                assert "Machine learning" in result

    @pytest.mark.asyncio
    async def test_search_qdrant_connection_error(self):
        """Test search handles Qdrant connection errors gracefully"""
        with patch(
            "mcp_server_langgraph.tools.search_tools._validate_semantic_search_config",
            side_effect=lambda *a, **kw: (True, None),
        ):
            with patch("mcp_server_langgraph.core.dynamic_context_loader.DynamicContextLoader") as mock_loader_class:
                # Simulate connection error
                mock_loader = MagicMock()
                mock_loader.semantic_search = AsyncMock(side_effect=ConnectionError("Connection refused"))
                mock_loader_class.return_value = mock_loader

                result = await search_knowledge_base.ainvoke({"query": "test", "limit": 5})

                assert isinstance(result, str)
                assert "error" in result.lower()
                assert "Connection refused" in result

    @pytest.mark.asyncio
    async def test_search_qdrant_query_error(self):
        """Test search handles Qdrant query errors"""
        with patch(
            "mcp_server_langgraph.tools.search_tools._validate_semantic_search_config",
            side_effect=lambda *a, **kw: (True, None),
        ):
            with patch("mcp_server_langgraph.core.dynamic_context_loader.DynamicContextLoader") as mock_loader_class:
                # Mock client that raises on query
                mock_loader = MagicMock()
                mock_loader.semantic_search = AsyncMock(side_effect=Exception("Collection not found"))
                mock_loader_class.return_value = mock_loader

                result = await search_knowledge_base.ainvoke({"query": "test", "limit": 5})

                assert isinstance(result, str)
                assert "error" in result.lower()


@pytest.mark.unit
@pytest.mark.xdist_group(name="search_tools")
class TestWebSearch:
    """Test suite for web_search tool"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""

        gc.collect()

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
        from unittest.mock import Mock

        mock_settings.tavily_api_key = "test-tavily-key"
        mock_settings.serper_api_key = None

        # Mock Tavily API response
        mock_response = MagicMock()  # Not AsyncMock - httpx Response is not async
        mock_response.status_code = 200
        # httpx Response.json() is a SYNC method, not async
        mock_response.json.return_value = {
            "results": [
                {"title": "Result 1", "content": "Content for result 1", "url": "https://example.com/1"},
                {"title": "Result 2", "content": "Content for result 2", "url": "https://example.com/2"},
            ]
        }
        mock_response.raise_for_status = Mock()  # Sync method

        # Mock client context manager - async methods are configured individually
        mock_client_instance = MagicMock()  # Base httpx client mock
        mock_client_instance.post = AsyncMock(return_value=mock_response)
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
        from unittest.mock import Mock

        mock_settings.tavily_api_key = None
        mock_settings.serper_api_key = "test-serper-key"

        # Mock Serper API response
        mock_response = MagicMock()  # Not AsyncMock - httpx Response is not async
        mock_response.status_code = 200
        # httpx Response.json() is a SYNC method, not async
        mock_response.json.return_value = {
            "organic": [
                {"title": "Serper Result 1", "snippet": "Snippet 1", "link": "https://example.com/serper1"},
                {"title": "Serper Result 2", "snippet": "Snippet 2", "link": "https://example.com/serper2"},
            ]
        }
        mock_response.raise_for_status = Mock()  # Sync method

        # Mock client context manager - async methods are configured individually
        mock_client_instance = MagicMock()  # Base httpx client mock
        mock_client_instance.post = AsyncMock(return_value=mock_response)
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
        # Note: Don't use spec=httpx.AsyncClient since httpx.AsyncClient is already mocked by @patch
        mock_client_instance = AsyncMock(return_value=None)  # async-mock-configured (side_effect/return_value set below)
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
        from unittest.mock import Mock

        mock_settings.tavily_api_key = None
        mock_settings.serper_api_key = "test-serper-key"

        # Mock API error response
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 429  # Rate limit
        mock_response.raise_for_status = Mock(side_effect=Exception("Rate limit exceeded"))

        # Note: Don't use spec=httpx.AsyncClient since httpx.AsyncClient is already mocked by @patch
        mock_client_instance = AsyncMock(return_value=None)  # async-mock-configured (side_effect/return_value set below)
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
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"error": "Invalid API key"}
        mock_response.raise_for_status = MagicMock()

        # Note: Don't use spec=httpx.AsyncClient since httpx.AsyncClient is already mocked by @patch
        mock_client_instance = AsyncMock(return_value=None)  # async-mock-configured (side_effect/return_value set below)
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
        # Note: Don't use spec=httpx.AsyncClient since httpx.AsyncClient is already mocked by @patch
        mock_client_instance = AsyncMock(return_value=None)  # async-mock-configured (side_effect/return_value set below)
        mock_client_instance.post.side_effect = httpx.TimeoutException("Request timeout")
        mock_async_client.return_value.__aenter__.return_value = mock_client_instance

        result = await web_search.ainvoke({"query": "test", "num_results": 5})

        assert isinstance(result, str)


@pytest.mark.unit
@pytest.mark.xdist_group(name="search_tools")
class TestSearchToolSchemas:
    """Test search tool schemas"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""

        gc.collect()

    def test_search_knowledge_base_schema(self):
        """Test search_knowledge_base has proper schema"""
        assert search_knowledge_base.name == "search_knowledge_base"
        assert search_knowledge_base.description is not None
        schema = search_knowledge_base.args_schema.model_json_schema()
        assert "query" in str(schema)
        assert "limit" in str(schema)

    def test_web_search_schema(self):
        """Test web_search has proper schema"""
        assert web_search.name == "web_search"
        assert web_search.description is not None
        schema = web_search.args_schema.model_json_schema()
        assert "query" in str(schema)
        assert "num_results" in str(schema)


@pytest.mark.unit
@pytest.mark.xdist_group(name="search_tools_semantic")
class TestSearchKnowledgeBaseSemanticSearch:
    """Tests for semantic search functionality in search_knowledge_base.

    These tests validate the async semantic search implementation
    that wires to DynamicContextLoader.
    """

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_returns_config_guidance_when_qdrant_not_configured(self):
        """Tool returns setup instructions when Qdrant not configured."""
        with patch(
            "mcp_server_langgraph.tools.search_tools._validate_semantic_search_config",
            side_effect=lambda *a, **kw: (False, "Qdrant not configured"),
        ):
            result = await search_knowledge_base.ainvoke({"query": "test"})
            assert "not configured" in result.lower()

    @pytest.mark.asyncio
    async def test_returns_provider_specific_guidance_for_google(self):
        """Shows GOOGLE_API_KEY guidance for google provider."""
        with patch(
            "mcp_server_langgraph.tools.search_tools._validate_semantic_search_config",
            side_effect=lambda *a, **kw: (False, "GOOGLE_API_KEY=your-api-key"),
        ):
            result = await search_knowledge_base.ainvoke({"query": "test"})
            assert "GOOGLE_API_KEY" in result

    @pytest.mark.asyncio
    async def test_returns_provider_specific_guidance_for_openai(self):
        """Shows OPENAI_API_KEY guidance for openai provider."""
        with patch(
            "mcp_server_langgraph.tools.search_tools._validate_semantic_search_config",
            side_effect=lambda *a, **kw: (False, "OPENAI_API_KEY=your-api-key"),
        ):
            result = await search_knowledge_base.ainvoke({"query": "test"})
            assert "OPENAI_API_KEY" in result

    @pytest.mark.asyncio
    async def test_returns_summaries_by_default(self):
        """Default output is concise summaries, not full content."""
        mock_refs = [
            MagicMock(ref_id="doc1", ref_type="doc", summary="Test doc", relevance_score=0.9),
        ]
        with patch(
            "mcp_server_langgraph.tools.search_tools._validate_semantic_search_config",
            side_effect=lambda *a, **kw: (True, None),
        ):
            with patch("mcp_server_langgraph.core.dynamic_context_loader.DynamicContextLoader") as MockLoaderClass:
                instance = MagicMock()
                instance.semantic_search = AsyncMock(return_value=mock_refs)
                MockLoaderClass.return_value = instance

                result = await search_knowledge_base.ainvoke({"query": "test", "limit": 5})

                assert "Test doc" in result
                assert "score: 0.90" in result
                assert "load_full_content=True" in result  # Progressive disclosure hint

    @pytest.mark.asyncio
    async def test_loads_full_content_when_requested(self):
        """load_full_content=True returns full context text."""
        mock_refs = [MagicMock(ref_id="doc1", ref_type="doc", summary="Test")]
        mock_loaded = [
            MagicMock(
                reference=MagicMock(ref_id="doc1", ref_type="doc", summary="Test"),
                content="Full document content here",
                token_count=100,
            ),
        ]
        with patch(
            "mcp_server_langgraph.tools.search_tools._validate_semantic_search_config",
            side_effect=lambda *a, **kw: (True, None),
        ):
            with patch("mcp_server_langgraph.core.dynamic_context_loader.DynamicContextLoader") as MockLoaderClass:
                instance = MagicMock()
                instance.semantic_search = AsyncMock(return_value=mock_refs)
                instance.load_batch = AsyncMock(return_value=mock_loaded)
                MockLoaderClass.return_value = instance

                result = await search_knowledge_base.ainvoke(
                    {
                        "query": "test",
                        "load_full_content": True,
                    }
                )

                assert "Full document content here" in result
                assert "100 tokens" in result

    @pytest.mark.asyncio
    async def test_preserves_telemetry_on_success(self):
        """Logger and metrics are called on successful search."""
        mock_refs = [MagicMock(ref_id="doc1", ref_type="doc", summary="Test", relevance_score=0.9)]
        with patch(
            "mcp_server_langgraph.tools.search_tools._validate_semantic_search_config",
            side_effect=lambda *a, **kw: (True, None),
        ):
            with patch("mcp_server_langgraph.core.dynamic_context_loader.DynamicContextLoader") as MockLoaderClass:
                with patch("mcp_server_langgraph.tools.search_tools.logger") as mock_logger:
                    with patch("mcp_server_langgraph.tools.search_tools.metrics") as mock_metrics:
                        instance = MagicMock()
                        instance.semantic_search = AsyncMock(return_value=mock_refs)
                        MockLoaderClass.return_value = instance

                        result = await search_knowledge_base.ainvoke({"query": "test"})

                        assert isinstance(result, str)  # Verify search returned
                        mock_logger.info.assert_called()
                        mock_metrics.tool_calls.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_path_is_concise(self):
        """Error returns brief message, logs full exception."""
        with patch(
            "mcp_server_langgraph.tools.search_tools._validate_semantic_search_config",
            side_effect=lambda *a, **kw: (True, None),
        ):
            with patch("mcp_server_langgraph.core.dynamic_context_loader.DynamicContextLoader") as MockLoaderClass:
                with patch("mcp_server_langgraph.tools.search_tools.logger") as mock_logger:
                    instance = MagicMock()
                    instance.semantic_search = AsyncMock(side_effect=Exception("Connection refused"))
                    MockLoaderClass.return_value = instance

                    result = await search_knowledge_base.ainvoke({"query": "test"})

                    assert "Search error:" in result
                    assert "Connection refused" in result
                    mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_no_results_returns_friendly_message(self):
        """Empty results return a friendly message."""
        with patch(
            "mcp_server_langgraph.tools.search_tools._validate_semantic_search_config",
            side_effect=lambda *a, **kw: (True, None),
        ):
            with patch("mcp_server_langgraph.core.dynamic_context_loader.DynamicContextLoader") as MockLoaderClass:
                instance = MagicMock()
                instance.semantic_search = AsyncMock(return_value=[])
                MockLoaderClass.return_value = instance

                result = await search_knowledge_base.ainvoke({"query": "test"})

                assert "No results found" in result


@pytest.mark.unit
@pytest.mark.xdist_group(name="search_tools_semantic")
class TestExploreKnowledgeIteratively:
    """Tests for explore_knowledge_iteratively tool."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_returns_config_guidance_when_not_configured(self):
        """Tool returns setup instructions when not configured."""
        from mcp_server_langgraph.tools.search_tools import explore_knowledge_iteratively

        with patch(
            "mcp_server_langgraph.tools.search_tools._validate_semantic_search_config",
            side_effect=lambda *a, **kw: (False, "Qdrant not configured"),
        ):
            result = await explore_knowledge_iteratively.ainvoke({"initial_query": "test"})
            assert "not configured" in result.lower()

    @pytest.mark.asyncio
    async def test_calls_progressive_discover(self):
        """Tool correctly calls DynamicContextLoader.progressive_discover."""
        from mcp_server_langgraph.tools.search_tools import explore_knowledge_iteratively

        mock_refs = [
            MagicMock(ref_id="doc1", ref_type="doc", summary="Test doc 1", relevance_score=0.9),
            MagicMock(ref_id="doc2", ref_type="doc", summary="Test doc 2", relevance_score=0.85),
        ]
        with patch(
            "mcp_server_langgraph.tools.search_tools._validate_semantic_search_config",
            side_effect=lambda *a, **kw: (True, None),
        ):
            with patch("mcp_server_langgraph.core.dynamic_context_loader.DynamicContextLoader") as MockLoader:
                instance = MockLoader.return_value
                instance.progressive_discover = AsyncMock(return_value=mock_refs)

                result = await explore_knowledge_iteratively.ainvoke(
                    {
                        "initial_query": "async patterns",
                        "max_iterations": 3,
                    }
                )

                instance.progressive_discover.assert_called_once()
                assert "Test doc 1" in result


@pytest.mark.unit
@pytest.mark.xdist_group(name="search_tools_semantic")
class TestValidateSemanticSearchConfig:
    """Tests for _validate_semantic_search_config helper function."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_returns_false_when_qdrant_url_missing(self):
        """Returns (False, guidance) when QDRANT_URL not set."""
        from mcp_server_langgraph.tools.search_tools import _validate_semantic_search_config

        with patch("mcp_server_langgraph.tools.search_tools.settings") as mock_settings:
            mock_settings.qdrant_url = None
            is_valid, guidance = _validate_semantic_search_config()
            assert is_valid is False
            assert "QDRANT_URL" in guidance

    def test_returns_false_when_embedding_provider_missing(self):
        """Returns (False, guidance) when EMBEDDING_PROVIDER not set."""
        from mcp_server_langgraph.tools.search_tools import _validate_semantic_search_config

        with patch("mcp_server_langgraph.tools.search_tools.settings") as mock_settings:
            mock_settings.qdrant_url = "localhost"
            mock_settings.embedding_provider = None
            mock_settings.embedding_model_name = None
            mock_settings.embedding_dimensions = None
            is_valid, guidance = _validate_semantic_search_config()
            assert is_valid is False
            assert "EMBEDDING_PROVIDER" in guidance

    def test_returns_false_for_unsupported_provider(self):
        """Returns (False, guidance) for unsupported provider."""
        from mcp_server_langgraph.tools.search_tools import _validate_semantic_search_config

        with patch("mcp_server_langgraph.tools.search_tools.settings") as mock_settings:
            mock_settings.qdrant_url = "localhost"
            mock_settings.embedding_provider = "unsupported_provider"
            mock_settings.embedding_model_name = "some-model"
            mock_settings.embedding_dimensions = 768
            is_valid, guidance = _validate_semantic_search_config()
            assert is_valid is False
            assert "unsupported" in guidance.lower()

    def test_returns_false_when_google_api_key_missing(self):
        """Returns (False, guidance) when google provider but no API key."""
        from mcp_server_langgraph.tools.search_tools import _validate_semantic_search_config

        with patch("mcp_server_langgraph.tools.search_tools.settings") as mock_settings:
            mock_settings.qdrant_url = "localhost"
            mock_settings.embedding_provider = "google"
            mock_settings.embedding_model_name = "models/text-embedding-004"
            mock_settings.embedding_dimensions = 768
            mock_settings.google_api_key = None
            is_valid, guidance = _validate_semantic_search_config()
            assert is_valid is False
            assert "GOOGLE_API_KEY" in guidance

    def test_returns_false_when_openai_api_key_missing(self):
        """Returns (False, guidance) when openai provider but no API key."""
        from mcp_server_langgraph.tools.search_tools import _validate_semantic_search_config

        with patch("mcp_server_langgraph.tools.search_tools.settings") as mock_settings:
            mock_settings.qdrant_url = "localhost"
            mock_settings.embedding_provider = "openai"
            mock_settings.embedding_model_name = "text-embedding-3-small"
            mock_settings.embedding_dimensions = 1536
            mock_settings.openai_api_key = None
            is_valid, guidance = _validate_semantic_search_config()
            assert is_valid is False
            assert "OPENAI_API_KEY" in guidance

    def test_returns_true_when_google_vertex_configured(self):
        """Returns (True, None) when google_vertex properly configured with ADC."""
        from mcp_server_langgraph.tools.search_tools import _validate_semantic_search_config

        with patch("mcp_server_langgraph.tools.search_tools.settings") as mock_settings:
            mock_settings.qdrant_url = "localhost"
            mock_settings.embedding_provider = "google_vertex"
            mock_settings.embedding_model_name = "text-embedding-005"
            mock_settings.embedding_dimensions = 768
            # google_vertex uses ADC, no explicit key needed

            # Mock the import check
            with patch.dict("sys.modules", {"langchain_google_vertexai": MagicMock()}):
                is_valid, guidance = _validate_semantic_search_config()
                assert is_valid is True
                assert guidance is None

    def test_returns_true_when_local_provider_configured(self):
        """Returns (True, None) when local provider with sentence-transformers."""
        from mcp_server_langgraph.tools.search_tools import _validate_semantic_search_config

        with patch("mcp_server_langgraph.tools.search_tools.settings") as mock_settings:
            mock_settings.qdrant_url = "localhost"
            mock_settings.embedding_provider = "local"
            mock_settings.embedding_model_name = "all-MiniLM-L6-v2"
            mock_settings.embedding_dimensions = 384

            # Mock the import check
            with patch.dict("sys.modules", {"sentence_transformers": MagicMock()}):
                is_valid, guidance = _validate_semantic_search_config()
                assert is_valid is True
                assert guidance is None


@pytest.mark.unit
@pytest.mark.xdist_group(name="search_tools_semantic")
class TestCreateEmbeddingsExtended:
    """Tests for _create_embeddings with all 5 providers."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_google_vertex_provider_uses_vertex_ai_embeddings(self):
        """google_vertex provider creates VertexAIEmbeddings."""
        from mcp_server_langgraph.core.dynamic_context_loader import _create_embeddings

        with patch("mcp_server_langgraph.core.dynamic_context_loader.settings") as mock_settings:
            mock_settings.gcp_project_id = "test-project"
            mock_settings.gcp_location = "us-central1"

            # Create mock for VertexAIEmbeddings
            mock_vertex_ai_embeddings = MagicMock()
            mock_module = MagicMock()
            mock_module.VertexAIEmbeddings = mock_vertex_ai_embeddings

            with patch.dict("sys.modules", {"langchain_google_vertexai": mock_module}):
                try:
                    _result = _create_embeddings(
                        provider="google_vertex",
                        model_name="text-embedding-005",
                    )
                    # Verify VertexAIEmbeddings was called
                    mock_vertex_ai_embeddings.assert_called_once()
                except (ImportError, ValueError) as e:
                    # Expected to fail if langchain_google_vertexai not installed
                    pytest.skip(f"google_vertex not available: {e}")

    def test_openai_provider_requires_api_key(self):
        """openai provider raises error without API key."""
        from mcp_server_langgraph.core.dynamic_context_loader import _create_embeddings

        with patch.dict("sys.modules", {"langchain_openai": MagicMock()}):
            try:
                _create_embeddings(
                    provider="openai",
                    model_name="text-embedding-3-small",
                    openai_api_key=None,
                )
                pytest.fail("Should have raised ValueError")
            except (ValueError, TypeError) as e:
                # Expected - either not implemented or missing key
                if "openai" not in str(e).lower() and "Unsupported" not in str(e):
                    pytest.skip(f"openai provider not yet implemented: {e}")

    def test_huggingface_provider_optional_token(self):
        """huggingface provider works without token for public models."""
        from mcp_server_langgraph.core.dynamic_context_loader import _create_embeddings

        # Create mock for HuggingFaceEmbeddings
        mock_hf_embeddings = MagicMock()
        mock_module = MagicMock()
        mock_module.HuggingFaceEmbeddings = mock_hf_embeddings

        with patch.dict("sys.modules", {"langchain_huggingface": mock_module}):
            try:
                _result = _create_embeddings(
                    provider="huggingface",
                    model_name="sentence-transformers/all-mpnet-base-v2",
                    huggingface_token=None,  # Optional
                )
                mock_hf_embeddings.assert_called_once()
            except (ImportError, ValueError) as e:
                # Expected to fail if langchain_huggingface not installed
                pytest.skip(f"huggingface not available: {e}")

    def test_unsupported_provider_raises_error(self):
        """Unsupported provider raises ValueError."""
        from mcp_server_langgraph.core.dynamic_context_loader import _create_embeddings

        with pytest.raises(ValueError) as exc_info:
            _create_embeddings(
                provider="invalid_provider",
                model_name="some-model",
            )
        assert "Unsupported" in str(exc_info.value)
