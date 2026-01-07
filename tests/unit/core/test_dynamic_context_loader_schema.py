"""
Tests for DynamicContextLoader schema fallback.

TDD: These tests are written FIRST to define the expected behavior
of semantic_search and _load_context_impl when encountering simple payloads
that lack the rich schema (ref_id, ref_type, summary).

Bug Reference: KB ingestion writes {"text": ..., **metadata} but
semantic_search and _load_context_impl expect rich schema.

Tests verify:
1. semantic_search handles simple {"text": ...} payloads
2. semantic_search generates fallback ref_id from result.id
3. semantic_search generates fallback summary from text[:100]
4. _load_context_impl handles simple {"text": ...} payloads
5. Both methods still work with rich schema (backward compatible)
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit

if TYPE_CHECKING:
    pass


@pytest.mark.xdist_group(name="dynamic_context_loader_schema")
class TestSemanticSearchSchemaFallback:
    """Tests for semantic_search schema fallback handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_semantic_search_handles_simple_text_payload(self) -> None:
        """GIVEN Qdrant returns a simple {"text": ...} payload
        WHEN semantic_search processes results
        THEN it should create ContextReference with fallback values
        """
        # Mock Qdrant search result with simple payload
        mock_result = MagicMock()
        mock_result.id = "doc-123"
        mock_result.score = 0.85
        mock_result.payload = {"text": "This is a document about Python programming language."}

        mock_client = AsyncMock(return_value=None)
        mock_client.search = AsyncMock(return_value=[mock_result])
        mock_client.get_collections = AsyncMock(return_value=MagicMock(collections=[MagicMock(name="test_collection")]))

        mock_embedder = MagicMock()
        mock_embedder.embed_query = MagicMock(return_value=[0.1] * 768)

        # Patch both the shared client factory and embeddings creation
        with (
            patch(
                "mcp_server_langgraph.core.dynamic_context_loader.get_shared_async_qdrant_client",
                new=AsyncMock(return_value=mock_client),
            ),
            patch(
                "mcp_server_langgraph.core.dynamic_context_loader._create_embeddings",
                return_value=mock_embedder,
            ),
        ):
            from mcp_server_langgraph.core.dynamic_context_loader import (
                DynamicContextLoader,
            )

            loader = DynamicContextLoader(
                qdrant_url="http://localhost:6333",
                collection_name="test_collection",
            )

            results = await loader.semantic_search(query="Python", top_k=5)

            assert len(results) == 1
            ref = results[0]
            # Fallback values should be used
            assert ref.ref_id == "doc-123"  # From result.id
            assert ref.ref_type == "document"  # Default type
            assert "Python programming" in ref.summary  # From text[:100]
            assert ref.relevance_score == 0.85

    @pytest.mark.asyncio
    async def test_semantic_search_handles_rich_schema(self) -> None:
        """GIVEN Qdrant returns a rich schema payload
        WHEN semantic_search processes results
        THEN it should use the provided values (backward compatible)
        """
        mock_result = MagicMock()
        mock_result.id = "doc-456"
        mock_result.score = 0.9
        mock_result.payload = {
            "ref_id": "custom-ref-id",
            "ref_type": "code",
            "summary": "Custom summary for the document",
            "metadata": {"language": "python"},
        }

        mock_client = AsyncMock(return_value=None)
        mock_client.search = AsyncMock(return_value=[mock_result])
        mock_client.get_collections = AsyncMock(return_value=MagicMock(collections=[MagicMock(name="test_collection")]))

        mock_embedder = MagicMock()
        mock_embedder.embed_query = MagicMock(return_value=[0.1] * 768)

        with (
            patch(
                "mcp_server_langgraph.core.dynamic_context_loader.get_shared_async_qdrant_client",
                new=AsyncMock(return_value=mock_client),
            ),
            patch(
                "mcp_server_langgraph.core.dynamic_context_loader._create_embeddings",
                return_value=mock_embedder,
            ),
        ):
            from mcp_server_langgraph.core.dynamic_context_loader import (
                DynamicContextLoader,
            )

            loader = DynamicContextLoader(
                qdrant_url="http://localhost:6333",
                collection_name="test_collection",
            )

            results = await loader.semantic_search(query="Python", top_k=5)

            assert len(results) == 1
            ref = results[0]
            # Rich schema values should be used
            assert ref.ref_id == "custom-ref-id"
            assert ref.ref_type == "code"
            assert ref.summary == "Custom summary for the document"
            assert ref.metadata == {"language": "python"}

    @pytest.mark.asyncio
    async def test_semantic_search_truncates_summary_from_text(self) -> None:
        """GIVEN a simple payload with long text
        WHEN generating fallback summary
        THEN it should truncate to first 100 chars + ellipsis
        """
        long_text = "A" * 200  # 200 character text

        mock_result = MagicMock()
        mock_result.id = "doc-789"
        mock_result.score = 0.75
        mock_result.payload = {"text": long_text}

        mock_client = AsyncMock(return_value=None)
        mock_client.search = AsyncMock(return_value=[mock_result])
        mock_client.get_collections = AsyncMock(return_value=MagicMock(collections=[MagicMock(name="test_collection")]))

        mock_embedder = MagicMock()
        mock_embedder.embed_query = MagicMock(return_value=[0.1] * 768)

        with (
            patch(
                "mcp_server_langgraph.core.dynamic_context_loader.get_shared_async_qdrant_client",
                new=AsyncMock(return_value=mock_client),
            ),
            patch(
                "mcp_server_langgraph.core.dynamic_context_loader._create_embeddings",
                return_value=mock_embedder,
            ),
        ):
            from mcp_server_langgraph.core.dynamic_context_loader import (
                DynamicContextLoader,
            )

            loader = DynamicContextLoader(
                qdrant_url="http://localhost:6333",
                collection_name="test_collection",
            )

            results = await loader.semantic_search(query="test", top_k=5)

            assert len(results) == 1
            ref = results[0]
            # Summary should be truncated
            assert len(ref.summary) <= 103  # 100 chars + "..."
            assert ref.summary.endswith("...")


@pytest.mark.xdist_group(name="dynamic_context_loader_schema")
class TestLoadContextImplSchemaFallback:
    """Tests for _load_context_impl schema fallback handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_load_context_impl_handles_simple_payload(self) -> None:
        """GIVEN Qdrant returns a simple {"text": ...} payload
        WHEN _load_context_impl loads the context
        THEN it should create LoadedContext with fallback values
        """
        mock_result = MagicMock()
        mock_result.id = "doc-123"
        mock_result.payload = {"text": "Document content about Python programming."}

        mock_client = AsyncMock(return_value=None)
        mock_client.retrieve = AsyncMock(return_value=[mock_result])
        mock_client.get_collections = AsyncMock(return_value=MagicMock(collections=[MagicMock(name="test_collection")]))

        mock_embedder = MagicMock()

        with (
            patch(
                "mcp_server_langgraph.core.dynamic_context_loader.get_shared_async_qdrant_client",
                new=AsyncMock(return_value=mock_client),
            ),
            patch(
                "mcp_server_langgraph.core.dynamic_context_loader._create_embeddings",
                return_value=mock_embedder,
            ),
        ):
            from mcp_server_langgraph.core.dynamic_context_loader import (
                DynamicContextLoader,
            )

            loader = DynamicContextLoader(
                qdrant_url="http://localhost:6333",
                collection_name="test_collection",
            )

            loaded = await loader._load_context_impl("doc-123")

            # Check reference fallback values
            assert loaded.reference.ref_id == "doc-123"
            assert loaded.reference.ref_type == "document"
            # Check content fallback (uses "text" field)
            assert loaded.content == "Document content about Python programming."
            # Token count should be estimated if not provided
            assert loaded.token_count >= 0

    @pytest.mark.asyncio
    async def test_load_context_impl_handles_rich_schema(self) -> None:
        """GIVEN Qdrant returns a rich schema payload
        WHEN _load_context_impl loads the context
        THEN it should use the provided values (backward compatible)
        """
        mock_result = MagicMock()
        mock_result.id = "doc-456"
        mock_result.payload = {
            "ref_id": "custom-ref",
            "ref_type": "code",
            "summary": "Custom summary",
            "content": "Full content here",
            "token_count": 150,
            "metadata": {"author": "test"},
        }

        mock_client = AsyncMock(return_value=None)
        mock_client.retrieve = AsyncMock(return_value=[mock_result])
        mock_client.get_collections = AsyncMock(return_value=MagicMock(collections=[MagicMock(name="test_collection")]))

        mock_embedder = MagicMock()

        with (
            patch(
                "mcp_server_langgraph.core.dynamic_context_loader.get_shared_async_qdrant_client",
                new=AsyncMock(return_value=mock_client),
            ),
            patch(
                "mcp_server_langgraph.core.dynamic_context_loader._create_embeddings",
                return_value=mock_embedder,
            ),
        ):
            from mcp_server_langgraph.core.dynamic_context_loader import (
                DynamicContextLoader,
            )

            loader = DynamicContextLoader(
                qdrant_url="http://localhost:6333",
                collection_name="test_collection",
            )

            loaded = await loader._load_context_impl("doc-456")

            # Rich schema values should be used
            assert loaded.reference.ref_id == "custom-ref"
            assert loaded.reference.ref_type == "code"
            assert loaded.content == "Full content here"
            assert loaded.token_count == 150

    @pytest.mark.asyncio
    async def test_load_context_impl_estimates_token_count(self) -> None:
        """GIVEN a simple payload without token_count
        WHEN _load_context_impl loads the context
        THEN it should estimate token count from text length
        """
        text = "Word " * 100  # ~100 words, ~150 tokens estimated

        mock_result = MagicMock()
        mock_result.id = "doc-789"
        mock_result.payload = {"text": text}

        mock_client = AsyncMock(return_value=None)
        mock_client.retrieve = AsyncMock(return_value=[mock_result])
        mock_client.get_collections = AsyncMock(return_value=MagicMock(collections=[MagicMock(name="test_collection")]))

        mock_embedder = MagicMock()

        with (
            patch(
                "mcp_server_langgraph.core.dynamic_context_loader.get_shared_async_qdrant_client",
                new=AsyncMock(return_value=mock_client),
            ),
            patch(
                "mcp_server_langgraph.core.dynamic_context_loader._create_embeddings",
                return_value=mock_embedder,
            ),
        ):
            from mcp_server_langgraph.core.dynamic_context_loader import (
                DynamicContextLoader,
            )

            loader = DynamicContextLoader(
                qdrant_url="http://localhost:6333",
                collection_name="test_collection",
            )

            loaded = await loader._load_context_impl("doc-789")

            # Token count should be estimated (rough: chars / 4)
            assert loaded.token_count > 0
            # Estimate should be reasonable (500 chars / 4 ≈ 125 tokens)
            assert loaded.token_count >= 50  # At least some tokens
