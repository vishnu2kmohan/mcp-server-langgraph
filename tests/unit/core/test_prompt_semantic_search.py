"""
Tests for Semantic Prompt Search (TDD - RED Phase)

Tests the ability to search prompts by semantic similarity using embeddings.
This enables finding relevant prompts based on natural language queries.

Following TDD pattern:
1. Write these tests first (RED)
2. Implement semantic search (GREEN)
3. Refactor as needed

Memory Safety:
- Uses @pytest.mark.xdist_group for parallel test safety
- Includes teardown_method with gc.collect()

References:
- ADR-0089: Prompt Architecture Centralization
- Phase 6: Plan Editor Prompts (semantic search for templates)
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest

if TYPE_CHECKING:
    pass

# Module-level pytest marker
pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="prompt_semantic_search")
class TestPromptSemanticSearchExists:
    """Tests that semantic search functions exist and are callable."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_search_prompts_function_exists(self) -> None:
        """Verify search_prompts function can be imported."""
        from mcp_server_langgraph.core.prompts.search import search_prompts

        assert callable(search_prompts)

    def test_search_result_class_exists(self) -> None:
        """Verify PromptSearchResult class can be imported."""
        from mcp_server_langgraph.core.prompts.search import PromptSearchResult

        assert PromptSearchResult is not None

    def test_prompt_index_class_exists(self) -> None:
        """Verify PromptIndex class can be imported."""
        from mcp_server_langgraph.core.prompts.search import PromptIndex

        assert PromptIndex is not None


@pytest.mark.xdist_group(name="prompt_semantic_search")
class TestPromptSemanticSearchBasic:
    """Tests for basic semantic search functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_search_prompts_returns_list(self) -> None:
        """Verify search_prompts returns a list of results."""
        from mcp_server_langgraph.core.prompts.search import (
            PromptIndex,
            PromptSearchResult,
            search_prompts,
        )
        from mcp_server_langgraph.llm.embeddings import InMemoryEmbeddingService

        # Create index with in-memory embeddings
        index = PromptIndex(embedding_service=InMemoryEmbeddingService())
        await index.build()

        results = await search_prompts("error handling", index=index, top_k=5)

        assert isinstance(results, list)
        for result in results:
            assert isinstance(result, PromptSearchResult)

    @pytest.mark.asyncio
    async def test_search_prompts_returns_prompt_names(self) -> None:
        """Verify search results include prompt names."""
        from mcp_server_langgraph.core.prompts.search import PromptIndex, search_prompts
        from mcp_server_langgraph.llm.embeddings import InMemoryEmbeddingService

        index = PromptIndex(embedding_service=InMemoryEmbeddingService())
        await index.build()

        results = await search_prompts("error handling", index=index, top_k=5)

        if results:  # May be empty with in-memory service
            assert results[0].prompt_name is not None
            assert isinstance(results[0].prompt_name, str)

    @pytest.mark.asyncio
    async def test_search_prompts_returns_similarity_scores(self) -> None:
        """Verify search results include similarity scores."""
        from mcp_server_langgraph.core.prompts.search import PromptIndex, search_prompts
        from mcp_server_langgraph.llm.embeddings import InMemoryEmbeddingService

        index = PromptIndex(embedding_service=InMemoryEmbeddingService())
        await index.build()

        results = await search_prompts("error handling", index=index, top_k=5)

        if results:
            assert hasattr(results[0], "similarity")
            assert isinstance(results[0].similarity, float)
            assert 0.0 <= results[0].similarity <= 1.0


@pytest.mark.xdist_group(name="prompt_semantic_search")
class TestPromptSemanticSearchFiltering:
    """Tests for search filtering by category."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_search_prompts_filters_by_category(self) -> None:
        """Verify search can filter by prompt category."""
        from mcp_server_langgraph.core.prompts.search import PromptIndex, search_prompts
        from mcp_server_langgraph.llm.embeddings import InMemoryEmbeddingService

        index = PromptIndex(embedding_service=InMemoryEmbeddingService())
        await index.build()

        results = await search_prompts(
            "session analysis",
            index=index,
            top_k=10,
            category="ai_ux",
        )

        # All results should be from ai_ux category (when category is specified)
        for result in results:
            if result.category:  # Only check if category is set
                assert result.category == "ai_ux"

    @pytest.mark.asyncio
    async def test_search_prompts_top_k_limits_results(self) -> None:
        """Verify top_k parameter limits number of results."""
        from mcp_server_langgraph.core.prompts.search import PromptIndex, search_prompts
        from mcp_server_langgraph.llm.embeddings import InMemoryEmbeddingService

        index = PromptIndex(embedding_service=InMemoryEmbeddingService())
        await index.build()

        results = await search_prompts("any query", index=index, top_k=3)

        assert len(results) <= 3


@pytest.mark.xdist_group(name="prompt_semantic_search")
class TestPromptIndex:
    """Tests for PromptIndex class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_prompt_index_build_indexes_prompts(self) -> None:
        """Verify PromptIndex.build() indexes all registered prompts."""
        from mcp_server_langgraph.core.prompts.search import PromptIndex
        from mcp_server_langgraph.llm.embeddings import InMemoryEmbeddingService

        index = PromptIndex(embedding_service=InMemoryEmbeddingService())
        await index.build()

        # Should have indexed prompts
        assert index.is_built
        assert index.prompt_count > 0

    @pytest.mark.asyncio
    async def test_prompt_index_search_returns_ordered_results(self) -> None:
        """Verify search results are ordered by similarity (descending)."""
        from mcp_server_langgraph.core.prompts.search import PromptIndex
        from mcp_server_langgraph.llm.embeddings import InMemoryEmbeddingService

        index = PromptIndex(embedding_service=InMemoryEmbeddingService())
        await index.build()

        results = await index.search("error analysis", top_k=5)

        # Results should be ordered by similarity (descending)
        if len(results) > 1:
            for i in range(len(results) - 1):
                assert results[i].similarity >= results[i + 1].similarity


@pytest.mark.xdist_group(name="prompt_semantic_search")
class TestPromptSearchResult:
    """Tests for PromptSearchResult dataclass."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_prompt_search_result_has_required_fields(self) -> None:
        """Verify PromptSearchResult has all required fields."""
        from mcp_server_langgraph.core.prompts.search import PromptSearchResult

        result = PromptSearchResult(
            prompt_name="error_analysis",
            similarity=0.95,
            category="ai_ux",
            version="v1",
        )

        assert result.prompt_name == "error_analysis"
        assert result.similarity == 0.95
        assert result.category == "ai_ux"
        assert result.version == "v1"

    def test_prompt_search_result_optional_content(self) -> None:
        """Verify PromptSearchResult can include prompt content."""
        from mcp_server_langgraph.core.prompts.search import PromptSearchResult

        result = PromptSearchResult(
            prompt_name="response",
            similarity=0.88,
            category="core",
            version="v1",
            content_preview="You are an AI assistant...",
        )

        assert result.content_preview == "You are an AI assistant..."


@pytest.mark.xdist_group(name="prompt_semantic_search")
class TestPromptSearchWithMockEmbeddings:
    """Tests for semantic search with mocked embeddings."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_search_uses_embedding_service(self) -> None:
        """Verify search calls embedding service for query."""
        from mcp_server_langgraph.core.prompts.search import PromptIndex

        mock_service = AsyncMock()
        mock_service.embed = AsyncMock(return_value=[0.1, 0.2, 0.3])
        mock_service.embed_batch = AsyncMock(return_value=[[0.1, 0.2, 0.3]])

        index = PromptIndex(embedding_service=mock_service)
        await index.build()

        await index.search("test query", top_k=5)

        # Should have called embed for the query
        mock_service.embed.assert_called()

    @pytest.mark.asyncio
    async def test_search_without_index_builds_automatically(self) -> None:
        """Verify search builds index if not already built."""
        from mcp_server_langgraph.core.prompts.search import PromptIndex, search_prompts
        from mcp_server_langgraph.llm.embeddings import InMemoryEmbeddingService

        index = PromptIndex(embedding_service=InMemoryEmbeddingService())
        # Explicitly NOT calling build()

        await search_prompts("test", index=index, top_k=5)

        # Should have auto-built the index
        assert index.is_built


@pytest.mark.xdist_group(name="prompt_semantic_search")
class TestPromptSearchFeatureFlag:
    """Tests for feature flag integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_search_respects_feature_flag(self) -> None:
        """Verify search respects ff_enable_plan_search feature flag."""
        from mcp_server_langgraph.core.feature_flags import feature_flags
        from mcp_server_langgraph.core.prompts.search import PromptIndex, search_prompts
        from mcp_server_langgraph.llm.embeddings import InMemoryEmbeddingService

        index = PromptIndex(embedding_service=InMemoryEmbeddingService())
        await index.build()

        # When feature flag is disabled, should return empty or raise
        with patch.object(feature_flags, "enable_plan_search", False):
            results = await search_prompts(
                "test",
                index=index,
                top_k=5,
                respect_feature_flags=True,
            )
            # Should return empty list when disabled
            assert results == []


@pytest.mark.xdist_group(name="prompt_semantic_search")
class TestPromptSearchGracefulDegradation:
    """Tests for graceful degradation when embeddings unavailable."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_search_handles_embedding_error(self) -> None:
        """Verify search handles embedding service errors gracefully."""
        from mcp_server_langgraph.core.prompts.search import PromptIndex, search_prompts

        mock_service = AsyncMock()
        mock_service.embed = AsyncMock(side_effect=Exception("Embedding service unavailable"))
        mock_service.embed_batch = AsyncMock(return_value=[[0.1, 0.2, 0.3]])

        index = PromptIndex(embedding_service=mock_service)
        await index.build()

        # Should not raise, should return empty results or fallback
        results = await search_prompts("test", index=index, top_k=5)
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_falls_back_to_keyword_search(self) -> None:
        """Verify fallback to keyword-based search when embeddings fail."""
        from mcp_server_langgraph.core.prompts.search import PromptIndex, search_prompts

        mock_service = AsyncMock()
        mock_service.embed = AsyncMock(side_effect=Exception("Embedding unavailable"))
        mock_service.embed_batch = AsyncMock(return_value=[[0.1, 0.2, 0.3]])

        index = PromptIndex(embedding_service=mock_service)
        await index.build()

        # Should fall back to keyword search
        results = await search_prompts(
            "error",  # Should match ERROR_ANALYSIS_SYSTEM_PROMPT by name
            index=index,
            top_k=5,
            allow_fallback=True,
        )

        # May return results from keyword fallback
        assert isinstance(results, list)


@pytest.mark.xdist_group(name="prompt_semantic_search")
class TestPromptIndexBuildEdgeCases:
    """Tests for PromptIndex.build() edge cases."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_build_handles_empty_prompt_registry(self) -> None:
        """Verify build handles empty prompt registry gracefully."""
        from mcp_server_langgraph.core.prompts.search import PromptIndex

        mock_service = AsyncMock()
        mock_service.embed_batch = AsyncMock(return_value=[])

        index = PromptIndex(embedding_service=mock_service)

        # Patch _PROMPT_VERSIONS at the prompts module level (where it's imported from)
        with patch("mcp_server_langgraph.core.prompts._PROMPT_VERSIONS", {}):
            await index.build()

        assert index.is_built
        assert index.prompt_count == 0

    @pytest.mark.asyncio
    async def test_build_handles_get_prompt_value_error(self) -> None:
        """Verify build skips prompts that raise ValueError."""
        from mcp_server_langgraph.core.prompts.search import PromptIndex

        mock_service = AsyncMock()
        mock_service.embed_batch = AsyncMock(return_value=[[0.1, 0.2]])

        index = PromptIndex(embedding_service=mock_service)

        # Patch get_prompt at the prompts module level (where it's imported from)
        with patch("mcp_server_langgraph.core.prompts.get_prompt") as mock_get:
            mock_get.side_effect = ValueError("Unknown prompt")

            await index.build()

        # Should still complete (with 0 entries due to all errors)
        assert index.is_built

    @pytest.mark.asyncio
    async def test_build_handles_embedding_batch_exception(self) -> None:
        """Verify build creates entries without embeddings on batch exception."""
        from mcp_server_langgraph.core.prompts.search import PromptIndex

        mock_service = AsyncMock()
        mock_service.embed_batch = AsyncMock(side_effect=Exception("Embedding service error"))

        index = PromptIndex(embedding_service=mock_service)
        await index.build()

        # Should have entries but without embeddings
        assert index.is_built
        assert index.prompt_count > 0


@pytest.mark.xdist_group(name="prompt_semantic_search")
class TestPromptIndexSearchEdgeCases:
    """Tests for PromptIndex.search() edge cases."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_search_skips_entries_without_embeddings(self) -> None:
        """Verify search skips entries that have no embeddings."""
        from mcp_server_langgraph.core.prompts.search import PromptIndex, _PromptEntry

        mock_service = AsyncMock()
        mock_service.embed = AsyncMock(return_value=[0.1, 0.2, 0.3])
        mock_service.embed_batch = AsyncMock(return_value=[])

        index = PromptIndex(embedding_service=mock_service)

        # Manually add entry without embedding
        index._entries = [
            _PromptEntry(
                name="test_prompt",
                category="test",
                content="Test content",
                embedding=[],  # Empty embedding
            )
        ]
        index._is_built = True

        results = await index.search("test query", top_k=5)

        # Should return empty since all entries lack embeddings
        assert results == []

    @pytest.mark.asyncio
    async def test_search_filters_by_category(self) -> None:
        """Verify search correctly filters by category."""
        from mcp_server_langgraph.core.prompts.search import PromptIndex, _PromptEntry

        mock_service = AsyncMock()
        mock_service.embed = AsyncMock(return_value=[0.1, 0.2, 0.3])

        index = PromptIndex(embedding_service=mock_service)

        # Add entries with different categories
        index._entries = [
            _PromptEntry(
                name="ai_ux_prompt",
                category="ai_ux",
                content="AI UX content",
                embedding=[0.1, 0.2, 0.3],
            ),
            _PromptEntry(
                name="core_prompt",
                category="core",
                content="Core content",
                embedding=[0.4, 0.5, 0.6],
            ),
        ]
        index._is_built = True

        results = await index.search("test", top_k=5, category="ai_ux")

        # Should only return ai_ux category
        assert len(results) == 1
        assert results[0].category == "ai_ux"


@pytest.mark.xdist_group(name="prompt_semantic_search")
class TestCosineSimilarityEdgeCases:
    """Tests for cosine similarity calculation edge cases."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_cosine_similarity_different_length_vectors(self) -> None:
        """Verify cosine similarity returns 0 for different length vectors."""
        from mcp_server_langgraph.core.prompts.search import PromptIndex

        result = PromptIndex._cosine_similarity([0.1, 0.2], [0.1, 0.2, 0.3])
        assert result == 0.0

    def test_cosine_similarity_empty_vectors(self) -> None:
        """Verify cosine similarity returns 0 for empty vectors."""
        from mcp_server_langgraph.core.prompts.search import PromptIndex

        result = PromptIndex._cosine_similarity([], [])
        assert result == 0.0

    def test_cosine_similarity_zero_magnitude_vector(self) -> None:
        """Verify cosine similarity returns 0 for zero magnitude vectors."""
        from mcp_server_langgraph.core.prompts.search import PromptIndex

        result = PromptIndex._cosine_similarity([0.0, 0.0, 0.0], [0.1, 0.2, 0.3])
        assert result == 0.0

    def test_cosine_similarity_identical_vectors(self) -> None:
        """Verify cosine similarity returns 1.0 for identical vectors."""
        from mcp_server_langgraph.core.prompts.search import PromptIndex

        result = PromptIndex._cosine_similarity([0.5, 0.5, 0.5], [0.5, 0.5, 0.5])
        assert result == 1.0


@pytest.mark.xdist_group(name="prompt_semantic_search")
class TestKeywordSearchEdgeCases:
    """Tests for keyword search functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_keyword_search_name_match_weighted_higher(self) -> None:
        """Verify keyword matches in name are weighted higher than content."""
        from mcp_server_langgraph.core.prompts.search import PromptIndex, _PromptEntry

        mock_service = AsyncMock()
        index = PromptIndex(embedding_service=mock_service)

        index._entries = [
            _PromptEntry(
                name="error_analysis",
                category="ai_ux",
                content="Some content without error word",
                embedding=[],
            ),
            _PromptEntry(
                name="other_prompt",
                category="ai_ux",
                content="Content with error word",
                embedding=[],
            ),
        ]
        index._is_built = True

        results = index._keyword_search("error", top_k=5, category=None)

        # Name match should be first (weighted higher)
        assert len(results) >= 1
        assert results[0].prompt_name == "error_analysis"

    def test_keyword_search_filters_by_category(self) -> None:
        """Verify keyword search filters by category."""
        from mcp_server_langgraph.core.prompts.search import PromptIndex, _PromptEntry

        mock_service = AsyncMock()
        index = PromptIndex(embedding_service=mock_service)

        index._entries = [
            _PromptEntry(
                name="error_analysis",
                category="ai_ux",
                content="Error content",
                embedding=[],
            ),
            _PromptEntry(
                name="core_error",
                category="core",
                content="Error content",
                embedding=[],
            ),
        ]
        index._is_built = True

        results = index._keyword_search("error", top_k=5, category="ai_ux")

        # Should only return ai_ux category
        assert len(results) == 1
        assert results[0].category == "ai_ux"

    def test_keyword_search_no_matches_returns_empty(self) -> None:
        """Verify keyword search returns empty when no matches."""
        from mcp_server_langgraph.core.prompts.search import PromptIndex, _PromptEntry

        mock_service = AsyncMock()
        index = PromptIndex(embedding_service=mock_service)

        index._entries = [
            _PromptEntry(
                name="router",
                category="core",
                content="Routing content",
                embedding=[],
            ),
        ]
        index._is_built = True

        results = index._keyword_search("nonexistent", top_k=5, category=None)

        assert results == []


@pytest.mark.xdist_group(name="prompt_semantic_search")
class TestSearchPromptsEdgeCases:
    """Tests for search_prompts() edge cases."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_search_prompts_no_fallback_returns_empty_on_error(self) -> None:
        """Verify search_prompts returns empty when allow_fallback=False and error occurs."""
        from mcp_server_langgraph.core.prompts.search import PromptIndex, search_prompts

        mock_service = AsyncMock()
        mock_service.embed = AsyncMock(side_effect=Exception("Embedding error"))
        mock_service.embed_batch = AsyncMock(return_value=[[0.1, 0.2, 0.3]])

        index = PromptIndex(embedding_service=mock_service)
        await index.build()

        results = await search_prompts(
            "test",
            index=index,
            top_k=5,
            allow_fallback=False,
        )

        assert results == []

    @pytest.mark.asyncio
    async def test_search_prompts_exception_with_fallback(self) -> None:
        """Verify search_prompts falls back on exception when allow_fallback=True."""
        from mcp_server_langgraph.core.prompts.search import PromptIndex, search_prompts

        mock_service = AsyncMock()
        mock_service.embed_batch = AsyncMock(return_value=[[0.1, 0.2, 0.3]])

        index = PromptIndex(embedding_service=mock_service)
        await index.build()

        # Patch index.search to raise exception
        with patch.object(index, "search", side_effect=Exception("Search error")):
            results = await search_prompts(
                "error",
                index=index,
                top_k=5,
                allow_fallback=True,
            )

        # Should return keyword search results
        assert isinstance(results, list)
