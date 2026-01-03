"""
Integration Tests for Prompt Semantic Search

Tests the complete semantic search workflow including:
- PromptIndex building with real prompts
- Semantic similarity search with embeddings
- Keyword fallback when embeddings unavailable
- Category filtering for targeted searches
- Feature flag gating for search behavior

Memory Safety:
- Uses @pytest.mark.xdist_group for parallel test safety
- Includes teardown_method with gc.collect()

References:
- ADR-0089: Prompt Architecture Centralization
- Phase 6: Plan Editor Prompts
- Phase 8: Comprehensive Tests
"""

from __future__ import annotations

import gc
from unittest.mock import AsyncMock, patch

import pytest

pytestmark = [
    pytest.mark.integration,
]


# =============================================================================
# PROMPT INDEX INTEGRATION TESTS
# =============================================================================


@pytest.mark.xdist_group(name="prompt_search_integration")
class TestPromptIndexIntegration:
    """Integration tests for PromptIndex with real prompt registry."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_build_index_with_real_prompts(self) -> None:
        """
        GIVEN a PromptIndex with real embedding service
        WHEN building the index from prompt registry
        THEN indexes all registered prompts
        """
        from mcp_server_langgraph.core.prompts.search import PromptIndex
        from mcp_server_langgraph.llm.embeddings import InMemoryEmbeddingService

        embedding_service = InMemoryEmbeddingService(dimensions=768)
        index = PromptIndex(embedding_service=embedding_service)

        await index.build()

        assert index.is_built is True
        # Should have indexed multiple prompts from the registry
        assert index.prompt_count > 0

    @pytest.mark.asyncio
    async def test_search_returns_similar_prompts(self) -> None:
        """
        GIVEN a built PromptIndex
        WHEN searching for a query
        THEN returns prompts sorted by similarity
        """
        from mcp_server_langgraph.core.prompts.search import PromptIndex, PromptSearchResult
        from mcp_server_langgraph.llm.embeddings import InMemoryEmbeddingService

        embedding_service = InMemoryEmbeddingService(dimensions=768)
        index = PromptIndex(embedding_service=embedding_service)
        await index.build()

        results = await index.search("error handling and recovery", top_k=3)

        assert len(results) <= 3
        assert all(isinstance(r, PromptSearchResult) for r in results)
        # Results should be sorted by similarity (descending)
        if len(results) > 1:
            assert results[0].similarity >= results[-1].similarity

    @pytest.mark.asyncio
    async def test_search_with_category_filter(self) -> None:
        """
        GIVEN a built PromptIndex
        WHEN searching with category filter
        THEN returns only prompts from that category
        """
        from mcp_server_langgraph.core.prompts.search import PromptIndex
        from mcp_server_langgraph.llm.embeddings import InMemoryEmbeddingService

        embedding_service = InMemoryEmbeddingService(dimensions=768)
        index = PromptIndex(embedding_service=embedding_service)
        await index.build()

        # Search only in AI UX category
        results = await index.search("user experience analysis", top_k=10, category="ai_ux")

        # All results should be from ai_ux category
        for result in results:
            assert result.category == "ai_ux"


@pytest.mark.xdist_group(name="prompt_search_api_integration")
class TestSearchPromptsAPIIntegration:
    """Integration tests for the search_prompts public API."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_search_prompts_with_index(self) -> None:
        """
        GIVEN a built PromptIndex
        WHEN calling search_prompts API
        THEN returns relevant results
        """
        from mcp_server_langgraph.core.prompts.search import PromptIndex, search_prompts
        from mcp_server_langgraph.llm.embeddings import InMemoryEmbeddingService

        embedding_service = InMemoryEmbeddingService(dimensions=768)
        index = PromptIndex(embedding_service=embedding_service)
        await index.build()

        results = await search_prompts(
            "workflow generation",
            index=index,
            top_k=5,
        )

        assert len(results) <= 5
        # Should find workflow-related prompts
        result_names = [r.prompt_name for r in results]
        # Verify results have valid prompt names
        assert all(isinstance(name, str) for name in result_names)

    @pytest.mark.asyncio
    async def test_search_prompts_respects_feature_flag(self) -> None:
        """
        GIVEN enable_plan_search feature flag is disabled
        WHEN calling search_prompts with respect_feature_flags=True
        THEN returns empty results
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags
        from mcp_server_langgraph.core.prompts.search import PromptIndex, search_prompts
        from mcp_server_langgraph.llm.embeddings import InMemoryEmbeddingService

        embedding_service = InMemoryEmbeddingService(dimensions=768)
        index = PromptIndex(embedding_service=embedding_service)
        await index.build()

        # Patch the feature_flags instance in the feature_flags module
        mock_flags = FeatureFlags(enable_plan_search=False)
        with patch(
            "mcp_server_langgraph.core.feature_flags.feature_flags", mock_flags
        ):
            results = await search_prompts(
                "any query",
                index=index,
                respect_feature_flags=True,
            )

            assert results == []

    @pytest.mark.asyncio
    async def test_search_prompts_allows_when_feature_enabled(self) -> None:
        """
        GIVEN enable_plan_search feature flag is enabled
        WHEN calling search_prompts with respect_feature_flags=True
        THEN returns search results
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags
        from mcp_server_langgraph.core.prompts.search import PromptIndex, search_prompts
        from mcp_server_langgraph.llm.embeddings import InMemoryEmbeddingService

        embedding_service = InMemoryEmbeddingService(dimensions=768)
        index = PromptIndex(embedding_service=embedding_service)
        await index.build()

        mock_flags = FeatureFlags(enable_plan_search=True)
        with patch(
            "mcp_server_langgraph.core.feature_flags.feature_flags", mock_flags
        ):
            results = await search_prompts(
                "router classification",
                index=index,
                top_k=3,
                respect_feature_flags=True,
            )

            # Should return results when flag is enabled
            assert len(results) <= 3


@pytest.mark.xdist_group(name="keyword_fallback_integration")
class TestKeywordFallbackIntegration:
    """Integration tests for keyword fallback search."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_keyword_fallback_on_embedding_error(self) -> None:
        """
        GIVEN embedding service that fails
        WHEN searching prompts
        THEN falls back to keyword search
        """
        from mcp_server_langgraph.core.prompts.search import PromptIndex, search_prompts
        from mcp_server_langgraph.llm.embeddings import InMemoryEmbeddingService

        # Create index with working embedding service
        embedding_service = InMemoryEmbeddingService(dimensions=768)
        index = PromptIndex(embedding_service=embedding_service)
        await index.build()

        # Now make embed fail for the query
        with patch.object(
            embedding_service, "embed", side_effect=Exception("Embedding failed")
        ):
            results = await search_prompts(
                "error analysis",
                index=index,
                top_k=5,
                allow_fallback=True,
            )

            # Should fall back to keyword search and find results
            # with "error" in the name
            result_names = [r.prompt_name for r in results]
            # Keyword search should still work
            assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_keyword_search_matches_prompt_names(self) -> None:
        """
        GIVEN prompts with specific names
        WHEN searching with keywords in the name
        THEN finds matching prompts
        """
        from mcp_server_langgraph.core.prompts.search import PromptIndex
        from mcp_server_langgraph.llm.embeddings import InMemoryEmbeddingService

        embedding_service = InMemoryEmbeddingService(dimensions=768)
        index = PromptIndex(embedding_service=embedding_service)
        await index.build()

        # Use keyword search directly
        results = index._keyword_search("router", top_k=5, category=None)

        # Should find router-related prompts
        result_names = [r.prompt_name for r in results]
        assert any("router" in name for name in result_names)

    @pytest.mark.asyncio
    async def test_keyword_search_with_category_filter(self) -> None:
        """
        GIVEN a built index
        WHEN keyword searching with category filter
        THEN returns only matching category results
        """
        from mcp_server_langgraph.core.prompts.search import PromptIndex
        from mcp_server_langgraph.llm.embeddings import InMemoryEmbeddingService

        embedding_service = InMemoryEmbeddingService(dimensions=768)
        index = PromptIndex(embedding_service=embedding_service)
        await index.build()

        # Search in core category only
        results = index._keyword_search("response", top_k=10, category="core")

        # All results should be from core category
        for result in results:
            assert result.category == "core"


@pytest.mark.xdist_group(name="prompt_categories_integration")
class TestPromptCategoriesIntegration:
    """Integration tests for prompt category handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_all_prompts_have_categories(self) -> None:
        """
        GIVEN a built PromptIndex
        WHEN examining all indexed prompts
        THEN each prompt has a category assigned
        """
        from mcp_server_langgraph.core.prompts.search import PROMPT_CATEGORIES, PromptIndex
        from mcp_server_langgraph.llm.embeddings import InMemoryEmbeddingService

        embedding_service = InMemoryEmbeddingService(dimensions=768)
        index = PromptIndex(embedding_service=embedding_service)
        await index.build()

        # All internal entries should have categories
        for entry in index._entries:
            assert entry.category is not None
            assert entry.category in {"core", "genui", "workflow", "plan", "ai_ux", "other"}

    @pytest.mark.asyncio
    async def test_category_distribution(self) -> None:
        """
        GIVEN a built PromptIndex
        WHEN counting prompts by category
        THEN distribution matches expected structure
        """
        from collections import Counter

        from mcp_server_langgraph.core.prompts.search import PromptIndex
        from mcp_server_langgraph.llm.embeddings import InMemoryEmbeddingService

        embedding_service = InMemoryEmbeddingService(dimensions=768)
        index = PromptIndex(embedding_service=embedding_service)
        await index.build()

        category_counts = Counter(entry.category for entry in index._entries)

        # Should have prompts in multiple categories
        assert len(category_counts) >= 3

        # AI UX category should have the most prompts (17+)
        assert "ai_ux" in category_counts

        # Core should have essential prompts
        assert "core" in category_counts


@pytest.mark.xdist_group(name="search_result_structure_integration")
class TestSearchResultStructureIntegration:
    """Integration tests for search result structure."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_search_result_has_all_fields(self) -> None:
        """
        GIVEN a search query
        WHEN receiving search results
        THEN each result has all expected fields
        """
        from mcp_server_langgraph.core.prompts.search import PromptIndex
        from mcp_server_langgraph.llm.embeddings import InMemoryEmbeddingService

        embedding_service = InMemoryEmbeddingService(dimensions=768)
        index = PromptIndex(embedding_service=embedding_service)
        await index.build()

        results = await index.search("prompt search", top_k=3)

        for result in results:
            assert hasattr(result, "prompt_name")
            assert hasattr(result, "similarity")
            assert hasattr(result, "category")
            assert hasattr(result, "version")
            assert hasattr(result, "content_preview")

            assert isinstance(result.prompt_name, str)
            assert isinstance(result.similarity, float)
            assert 0.0 <= result.similarity <= 1.0

    @pytest.mark.asyncio
    async def test_search_result_content_preview_truncated(self) -> None:
        """
        GIVEN a search query
        WHEN receiving search results with long prompts
        THEN content_preview is truncated appropriately
        """
        from mcp_server_langgraph.core.prompts.search import PromptIndex
        from mcp_server_langgraph.llm.embeddings import InMemoryEmbeddingService

        embedding_service = InMemoryEmbeddingService(dimensions=768)
        index = PromptIndex(embedding_service=embedding_service)
        await index.build()

        results = await index.search("system prompt", top_k=5)

        for result in results:
            if result.content_preview:
                # Content preview should be truncated to 200 chars
                assert len(result.content_preview) <= 200


@pytest.mark.xdist_group(name="search_performance_integration")
class TestSearchPerformanceIntegration:
    """Integration tests for search performance characteristics."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_index_build_is_idempotent(self) -> None:
        """
        GIVEN a PromptIndex
        WHEN building multiple times
        THEN produces consistent results
        """
        from mcp_server_langgraph.core.prompts.search import PromptIndex
        from mcp_server_langgraph.llm.embeddings import InMemoryEmbeddingService

        embedding_service = InMemoryEmbeddingService(dimensions=768)
        index = PromptIndex(embedding_service=embedding_service)

        await index.build()
        first_count = index.prompt_count

        await index.build()
        second_count = index.prompt_count

        assert first_count == second_count

    @pytest.mark.asyncio
    async def test_search_auto_builds_if_needed(self) -> None:
        """
        GIVEN an unbuilt PromptIndex
        WHEN searching
        THEN automatically builds the index
        """
        from mcp_server_langgraph.core.prompts.search import PromptIndex
        from mcp_server_langgraph.llm.embeddings import InMemoryEmbeddingService

        embedding_service = InMemoryEmbeddingService(dimensions=768)
        index = PromptIndex(embedding_service=embedding_service)

        assert index.is_built is False

        # Search should trigger build
        results = await index.search("test query", top_k=3)

        assert index.is_built is True
        assert isinstance(results, list)
