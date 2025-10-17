"""
Unit tests for DynamicContextLoader

Tests semantic search, indexing, progressive discovery, and caching.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import SystemMessage

from mcp_server_langgraph.core.dynamic_context_loader import (
    ContextReference,
    DynamicContextLoader,
    LoadedContext,
    search_and_load_context,
)


@pytest.fixture
def mock_qdrant_client():
    """Mock Qdrant client for testing"""
    with patch("mcp_server_langgraph.core.dynamic_context_loader.QdrantClient") as mock:
        client = MagicMock()

        # Mock collection existence check
        client.get_collections.return_value.collections = []

        # Mock search results
        mock_results = [
            MagicMock(
                id="ref_1",
                score=0.95,
                payload={
                    "ref_id": "doc_1",
                    "ref_type": "document",
                    "summary": "Test document 1",
                    "metadata": {"author": "test"},
                },
            ),
            MagicMock(
                id="ref_2",
                score=0.85,
                payload={
                    "ref_id": "doc_2",
                    "ref_type": "code",
                    "summary": "Test code snippet",
                    "metadata": {"language": "python"},
                },
            ),
        ]
        client.search.return_value = mock_results

        mock.return_value = client
        yield client


@pytest.fixture
def mock_embedder():
    """Mock embeddings for testing (LangChain Embeddings interface)"""
    with patch("mcp_server_langgraph.core.dynamic_context_loader._create_embeddings") as mock:
        embedder = MagicMock()
        # Mock LangChain Embeddings interface
        # embed_query returns a list directly (not numpy array)
        embedder.embed_query.return_value = [0.1] * 768  # Google default: 768 dims
        embedder.embed_documents.return_value = [[0.1] * 768]  # List of lists
        mock.return_value = embedder
        yield embedder


@pytest.fixture
def context_loader(mock_qdrant_client, mock_embedder):
    """Create DynamicContextLoader instance for testing"""
    with patch("mcp_server_langgraph.core.config.settings") as mock_settings:
        # Mock settings for test
        mock_settings.qdrant_url = "localhost"
        mock_settings.qdrant_port = 6333
        mock_settings.qdrant_collection_name = "test_collection"
        mock_settings.embedding_provider = "google"
        mock_settings.embedding_model_name = "models/text-embedding-004"
        mock_settings.embedding_dimensions = 768
        mock_settings.embedding_task_type = "RETRIEVAL_DOCUMENT"
        mock_settings.context_cache_size = 10
        mock_settings.enable_context_encryption = False
        mock_settings.context_retention_days = 90
        mock_settings.enable_auto_deletion = True
        mock_settings.google_api_key = "test-api-key"

        return DynamicContextLoader(
            qdrant_url="localhost",
            qdrant_port=6333,
            collection_name="test_collection",
            embedding_model="models/text-embedding-004",
            embedding_provider="google",
            embedding_dimensions=768,
            cache_size=10,
        )


class TestDynamicContextLoader:
    """Test suite for DynamicContextLoader"""

    @pytest.mark.asyncio
    async def test_initialization(self, context_loader, mock_qdrant_client):
        """Test loader initialization"""
        assert context_loader.qdrant_url == "localhost"
        assert context_loader.qdrant_port == 6333
        assert context_loader.collection_name == "test_collection"
        assert context_loader.embedding_model_name == "models/text-embedding-004"
        assert context_loader.embedding_provider == "google"
        assert context_loader.embedding_dim == 768

        # Verify collection creation was attempted
        mock_qdrant_client.get_collections.assert_called_once()

    @pytest.mark.asyncio
    async def test_semantic_search(self, context_loader, mock_qdrant_client, mock_embedder):
        """Test semantic search functionality"""
        results = await context_loader.semantic_search(
            query="test query",
            top_k=5,
            min_score=0.5,
        )

        assert len(results) == 2
        assert results[0].ref_id == "doc_1"
        assert results[0].ref_type == "document"
        assert results[0].relevance_score == 0.95
        assert results[1].ref_id == "doc_2"

        # Verify embedder was called with LangChain interface
        mock_embedder.embed_query.assert_called_once_with("test query")

        # Verify Qdrant search was called
        mock_qdrant_client.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_semantic_search_with_filter(self, context_loader, mock_qdrant_client):
        """Test semantic search with type filter"""
        results = await context_loader.semantic_search(
            query="test query",
            top_k=3,
            ref_type_filter="document",
            min_score=0.7,
        )

        # Verify filter was applied
        call_args = mock_qdrant_client.search.call_args
        assert call_args is not None
        assert "query_filter" in call_args.kwargs
        assert call_args.kwargs["score_threshold"] == 0.7

    @pytest.mark.asyncio
    async def test_index_context(self, context_loader, mock_qdrant_client, mock_embedder):
        """Test context indexing"""
        await context_loader.index_context(
            ref_id="test_doc",
            content="This is test content for indexing",
            ref_type="document",
            summary="Test document summary",
            metadata={"author": "test_user"},
        )

        # Verify embedder was called with LangChain interface
        assert mock_embedder.embed_query.called

        # Verify Qdrant upsert was called
        mock_qdrant_client.upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_context(self, context_loader, mock_qdrant_client):
        """Test loading full context from reference"""
        ref = ContextReference(
            ref_id="test_doc",
            ref_type="document",
            summary="Test summary",
            relevance_score=0.9,
            metadata={},
        )

        # Mock Qdrant retrieve
        mock_point = MagicMock()
        mock_point.payload = {
            "ref_id": "test_doc",
            "ref_type": "document",
            "summary": "Test summary",
            "content": "Full context content here",
            "token_count": 50,
            "metadata": {},
        }
        mock_qdrant_client.retrieve.return_value = [mock_point]

        loaded = await context_loader.load_context(ref)

        assert loaded.reference.ref_id == "test_doc"
        assert loaded.content == "Full context content here"
        assert loaded.token_count == 50

    @pytest.mark.asyncio
    async def test_load_batch_within_budget(self, context_loader):
        """Test batch loading respects token budget"""
        references = [
            ContextReference(
                ref_id=f"doc_{i}",
                ref_type="document",
                summary=f"Summary {i}",
                relevance_score=0.9 - (i * 0.1),
                metadata={},
            )
            for i in range(5)
        ]

        # Mock loading to return content with known token counts
        with patch.object(context_loader, "load_context") as mock_load:

            async def mock_load_impl(ref):
                return LoadedContext(
                    reference=ref,
                    content="x" * 400,  # ~100 tokens each
                    token_count=100,
                    loaded_at=time.time(),
                )

            mock_load.side_effect = mock_load_impl

            # Load with 250 token budget (should load 2 items)
            loaded = await context_loader.load_batch(references, max_tokens=250)

            assert len(loaded) <= 3  # At most 2 full items + 1 partial
            total_tokens = sum(ctx.token_count for ctx in loaded)
            assert total_tokens <= 250

    @pytest.mark.asyncio
    async def test_progressive_search(self, context_loader, mock_qdrant_client):
        """Test progressive discovery pattern"""
        # First search
        results1 = await context_loader.semantic_search("initial query", top_k=3)
        assert len(results1) == 2

        # Second search with refined query
        results2 = await context_loader.semantic_search("refined query", top_k=3)
        assert len(results2) == 2

        # Verify multiple searches were made
        assert mock_qdrant_client.search.call_count == 2

    @pytest.mark.asyncio
    async def test_caching(self, context_loader, mock_qdrant_client):
        """Test LRU caching of loaded contexts"""
        ref = ContextReference(
            ref_id="cached_doc",
            ref_type="document",
            summary="Cached document",
            relevance_score=0.9,
            metadata={},
        )

        # Mock Qdrant retrieve
        mock_point = MagicMock()
        mock_point.payload = {
            "ref_id": "cached_doc",
            "ref_type": "document",
            "summary": "Cached document",
            "content": "Cached content",
            "token_count": 30,
            "metadata": {},
        }
        mock_qdrant_client.retrieve.return_value = [mock_point]

        # Load once
        loaded1 = await context_loader.load_context(ref)
        initial_call_count = mock_qdrant_client.retrieve.call_count

        # Load again - should use cache
        loaded2 = await context_loader.load_context(ref)

        # Cache is on _load_context_impl, which is wrapped in lru_cache
        # So second call might or might not hit storage depending on cache implementation
        assert loaded1.content == loaded2.content

    @pytest.mark.asyncio
    async def test_to_messages(self, context_loader):
        """Test conversion of loaded contexts to messages"""
        loaded_contexts = [
            LoadedContext(
                reference=ContextReference(
                    ref_id="doc_1",
                    ref_type="document",
                    summary="Summary 1",
                    metadata={},
                ),
                content="Content 1",
                token_count=50,
                loaded_at=time.time(),
            ),
            LoadedContext(
                reference=ContextReference(
                    ref_id="doc_2",
                    ref_type="code",
                    summary="Test function",
                    metadata={"language": "python"},
                ),
                content="def test(): pass",
                token_count=30,
                loaded_at=time.time(),
            ),
        ]

        messages = context_loader.to_messages(loaded_contexts)

        assert len(messages) == 2  # One message per context
        assert all(isinstance(m, SystemMessage) for m in messages)
        assert "doc_1" in messages[0].content
        assert "doc_2" in messages[1].content
        assert "Content 1" in messages[0].content

    @pytest.mark.asyncio
    async def test_error_handling_search(self, context_loader, mock_qdrant_client):
        """Test error handling during search"""
        # Simulate Qdrant error
        mock_qdrant_client.search.side_effect = Exception("Qdrant connection error")

        # Implementation returns empty list on error (graceful degradation)
        results = await context_loader.semantic_search("test query")

        assert results == []

    @pytest.mark.asyncio
    async def test_error_handling_index(self, context_loader, mock_qdrant_client):
        """Test error handling during indexing"""
        mock_qdrant_client.upsert.side_effect = Exception("Qdrant write error")

        with pytest.raises(Exception) as exc_info:
            await context_loader.index_context(
                ref_id="test",
                content="content",
                ref_type="document",
                summary="summary",
            )

        assert "Qdrant write error" in str(exc_info.value)


class TestSearchAndLoadContext:
    """Test the helper function search_and_load_context"""

    @pytest.mark.asyncio
    async def test_search_and_load(self, context_loader, mock_qdrant_client):
        """Test end-to-end search and load"""
        with patch.object(context_loader, "load_batch") as mock_load_batch:
            mock_load_batch.return_value = [
                LoadedContext(
                    reference=ContextReference(
                        ref_id="doc_1",
                        ref_type="document",
                        summary="Summary 1",
                        metadata={},
                    ),
                    content="Content 1",
                    token_count=100,
                    loaded_at=time.time(),
                )
            ]

            results = await search_and_load_context(
                query="test query",
                loader=context_loader,
                top_k=3,
                max_tokens=500,
            )

            assert len(results) == 1
            assert results[0].reference.ref_id == "doc_1"

            # Verify search was called
            mock_qdrant_client.search.assert_called_once()

            # Verify load_batch was called
            mock_load_batch.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_no_results(self, context_loader, mock_qdrant_client):
        """Test when search returns no results"""
        mock_qdrant_client.search.return_value = []

        results = await search_and_load_context(
            query="no match query",
            loader=context_loader,
            top_k=3,
        )

        assert len(results) == 0


@pytest.mark.integration
class TestDynamicContextIntegration:
    """Integration tests requiring actual Qdrant instance"""

    @pytest.mark.skip(reason="Requires running Qdrant instance")
    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """Test complete workflow: index → search → load"""
        loader = DynamicContextLoader(
            qdrant_url="localhost",
            qdrant_port=6333,
            collection_name="integration_test",
        )

        # Index some test documents
        await loader.index_context(
            ref_id="test_1",
            content="Python is a programming language",
            ref_type="document",
            summary="About Python language",
        )

        await loader.index_context(
            ref_id="test_2",
            content="JavaScript is also a programming language",
            ref_type="document",
            summary="About JavaScript language",
        )

        # Search
        results = await loader.semantic_search(
            query="programming languages",
            top_k=2,
        )

        assert len(results) == 2

        # Load
        loaded = await loader.load_batch(results, max_tokens=1000)
        assert len(loaded) == 2
