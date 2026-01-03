"""
Template Recommender EmbeddingService Integration Tests

TDD RED PHASE: Tests for unified EmbeddingService integration
with the TemplateRecommender class.

These tests verify:
1. EmbeddingService can be injected into TemplateRecommender
2. Fallback chain: EmbeddingService → sentence-transformers → keywords
3. Async embedding generation works with TemplateRecommender
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [
    pytest.mark.unit,
    pytest.mark.studio,
]


@pytest.mark.xdist_group(name="template_embedding_service")
class TestTemplateRecommenderEmbeddingService:
    """Tests for EmbeddingService integration with TemplateRecommender."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_template_recommender_accepts_embedding_service(self) -> None:
        """
        GIVEN a TemplateRecommender class
        WHEN instantiated with an EmbeddingService
        THEN should accept and store the embedding service
        """
        from mcp_server_langgraph.llm.embeddings import InMemoryEmbeddingService
        from mcp_server_langgraph.studio.ai.templates import TemplateRecommender

        embedding_service = InMemoryEmbeddingService(dimensions=768)
        recommender = TemplateRecommender(embedding_service=embedding_service)

        assert recommender._embedding_service is embedding_service

    def test_template_recommender_uses_default_when_no_service_provided(self) -> None:
        """
        GIVEN a TemplateRecommender class
        WHEN instantiated without an EmbeddingService
        THEN should fall back to sentence-transformers or keywords
        """
        from mcp_server_langgraph.studio.ai.templates import TemplateRecommender

        recommender = TemplateRecommender()

        # Should have None for embedding_service (uses legacy path)
        assert recommender._embedding_service is None

    @pytest.mark.asyncio
    async def test_recommend_uses_injected_embedding_service(self) -> None:
        """
        GIVEN a TemplateRecommender with injected EmbeddingService
        WHEN calling recommend()
        THEN should use the EmbeddingService for similarity computation
        """
        from mcp_server_langgraph.llm.embeddings import InMemoryEmbeddingService
        from mcp_server_langgraph.studio.ai.templates import TemplateRecommender

        embedding_service = InMemoryEmbeddingService(dimensions=768)
        recommender = TemplateRecommender(embedding_service=embedding_service)

        result = await recommender.recommend(
            description="I want to build a data processing pipeline"
        )

        assert isinstance(result, list)
        assert len(result) > 0
        # Verify results have similarity scores
        for r in result:
            assert "similarity" in r

    @pytest.mark.asyncio
    async def test_embedding_service_called_for_query(self) -> None:
        """
        GIVEN a TemplateRecommender with mock EmbeddingService
        WHEN calling recommend()
        THEN should call embed() on the EmbeddingService
        """
        from mcp_server_langgraph.studio.ai.templates import TemplateRecommender

        mock_service = MagicMock()
        mock_service.embed = AsyncMock(return_value=[0.1] * 768)

        recommender = TemplateRecommender(embedding_service=mock_service)

        await recommender.recommend(description="chatbot with RAG")

        # Verify embed was called for the query
        mock_service.embed.assert_called()

    @pytest.mark.asyncio
    async def test_embedding_service_computes_similarity(self) -> None:
        """
        GIVEN a TemplateRecommender with EmbeddingService
        WHEN computing similarity
        THEN should use cosine similarity between embeddings
        """
        from mcp_server_langgraph.llm.embeddings import InMemoryEmbeddingService
        from mcp_server_langgraph.studio.ai.templates import TemplateRecommender

        embedding_service = InMemoryEmbeddingService(dimensions=768)
        recommender = TemplateRecommender(embedding_service=embedding_service)

        result = await recommender.recommend(
            description="multi-agent collaboration system"
        )

        # All similarity scores should be in valid range
        for r in result:
            assert 0.0 <= r["similarity"] <= 1.0

    @pytest.mark.asyncio
    async def test_fallback_to_keywords_when_embedding_fails(self) -> None:
        """
        GIVEN a TemplateRecommender with failing EmbeddingService
        WHEN calling recommend()
        THEN should fallback to keyword matching
        """
        from mcp_server_langgraph.studio.ai.templates import TemplateRecommender

        mock_service = MagicMock()
        mock_service.embed = AsyncMock(side_effect=Exception("Embedding failed"))

        recommender = TemplateRecommender(embedding_service=mock_service)

        # Should not raise, should fallback to keywords
        result = await recommender.recommend(description="chatbot")

        assert isinstance(result, list)


@pytest.mark.xdist_group(name="template_embedding_precompute")
class TestTemplateEmbeddingPrecomputation:
    """Tests for pre-computing template embeddings."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_template_embeddings_precomputed(self) -> None:
        """
        GIVEN a TemplateRecommender with EmbeddingService
        WHEN embeddings are initialized
        THEN all template embeddings should be pre-computed
        """
        from mcp_server_langgraph.llm.embeddings import InMemoryEmbeddingService
        from mcp_server_langgraph.studio.ai.templates import TemplateRecommender

        embedding_service = InMemoryEmbeddingService(dimensions=768)
        recommender = TemplateRecommender(embedding_service=embedding_service)

        # Trigger initialization by making a recommendation
        await recommender.recommend(description="test")

        # Check that template embeddings are cached
        templates = recommender.get_available_templates()
        assert len(recommender._template_embeddings_cache) == len(templates)

    @pytest.mark.asyncio
    async def test_template_embeddings_cached_for_reuse(self) -> None:
        """
        GIVEN a TemplateRecommender with pre-computed embeddings
        WHEN making multiple recommendations
        THEN should reuse cached embeddings for templates
        """
        from mcp_server_langgraph.studio.ai.templates import TemplateRecommender

        mock_service = MagicMock()
        mock_service.embed = AsyncMock(return_value=[0.1] * 768)

        recommender = TemplateRecommender(embedding_service=mock_service)

        # First call - computes query + all template embeddings
        await recommender.recommend(description="chatbot")
        first_call_count = mock_service.embed.call_count

        # Second call - should only compute new query embedding
        # Template embeddings should be cached
        await recommender.recommend(description="api agent")
        second_call_count = mock_service.embed.call_count

        # The second call should add exactly 1 call (for the new query)
        # because template embeddings are cached
        num_templates = len(recommender.get_available_templates())
        expected_first_calls = num_templates + 1  # templates + query
        expected_second_calls = expected_first_calls + 1  # just new query

        assert first_call_count == expected_first_calls
        assert second_call_count == expected_second_calls


@pytest.mark.xdist_group(name="template_embedding_factory")
class TestTemplateRecommenderFactory:
    """Tests for factory function to create TemplateRecommender with EmbeddingService."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_template_recommender_factory_exists(self) -> None:
        """
        GIVEN the templates module
        WHEN importing get_template_recommender
        THEN should be available as a factory function
        """
        from mcp_server_langgraph.studio.ai.templates import get_template_recommender

        assert callable(get_template_recommender)

    def test_get_template_recommender_returns_recommender(self) -> None:
        """
        GIVEN get_template_recommender factory
        WHEN called
        THEN should return a TemplateRecommender instance
        """
        from mcp_server_langgraph.studio.ai.templates import (
            TemplateRecommender,
            get_template_recommender,
        )

        recommender = get_template_recommender()

        assert isinstance(recommender, TemplateRecommender)

    def test_get_template_recommender_uses_embedding_service_from_settings(self) -> None:
        """
        GIVEN get_template_recommender factory
        WHEN called without arguments
        THEN should use EmbeddingService from get_embedding_service()
        """
        from mcp_server_langgraph.studio.ai.templates import get_template_recommender

        # Patch at the import location inside the function
        with patch(
            "mcp_server_langgraph.llm.embeddings.get_embedding_service"
        ) as mock_get:
            mock_service = MagicMock()
            mock_get.return_value = mock_service

            recommender = get_template_recommender()

            mock_get.assert_called_once()
            assert recommender._embedding_service is mock_service
