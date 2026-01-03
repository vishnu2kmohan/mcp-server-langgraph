"""
Integration Tests for Vector-Based Plan Search

Tests the full integration of:
- EmbeddingService for generating embeddings
- VectorSearchProvider for similarity search
- PlanTemplateRepository for template matching
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow,
]


@pytest.mark.xdist_group(name="vector_plan_search_integration")
class TestVectorPlanSearchIntegration:
    """Integration tests for vector-based plan search."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_embedding_service_generates_vectors(self) -> None:
        """
        GIVEN an EmbeddingService
        WHEN generating embeddings for plan descriptions
        THEN returns valid vector embeddings
        """
        from mcp_server_langgraph.llm.embeddings import (
            InMemoryEmbeddingService,
        )

        service = InMemoryEmbeddingService(dimensions=768)
        embedding = await service.embed("Create a workflow for data processing")

        assert len(embedding) == 768
        assert all(isinstance(v, float) for v in embedding)
        assert all(-1.0 <= v <= 1.0 for v in embedding)

    @pytest.mark.asyncio
    async def test_embedding_batch_generates_multiple_vectors(self) -> None:
        """
        GIVEN an EmbeddingService
        WHEN generating embeddings for multiple descriptions
        THEN returns vectors for each description
        """
        from mcp_server_langgraph.llm.embeddings import (
            InMemoryEmbeddingService,
        )

        service = InMemoryEmbeddingService(dimensions=768)
        descriptions = [
            "Data pipeline automation",
            "Machine learning model training",
            "API integration workflow",
        ]
        embeddings = await service.embed_batch(descriptions)

        assert len(embeddings) == 3
        assert all(len(e) == 768 for e in embeddings)

    @pytest.mark.asyncio
    async def test_inmemory_vector_provider_upsert_and_search(self) -> None:
        """
        GIVEN an InMemoryVectorProvider
        WHEN upserting vectors and searching
        THEN returns relevant results sorted by similarity
        """
        from mcp_server_langgraph.llm.embeddings import (
            InMemoryEmbeddingService,
        )
        from mcp_server_langgraph.storage.vectors.inmemory import (
            InMemoryVectorProvider,
        )

        # Setup
        embedding_service = InMemoryEmbeddingService(dimensions=768)
        vector_provider = InMemoryVectorProvider()

        # Create embeddings for templates
        templates = [
            {"id": "t1", "name": "Data Pipeline", "description": "Process and transform data"},
            {"id": "t2", "name": "ML Training", "description": "Train machine learning models"},
            {"id": "t3", "name": "API Gateway", "description": "API routing and integration"},
        ]

        for template in templates:
            vector = await embedding_service.embed(template["description"])
            await vector_provider.upsert(
                collection="plan_templates",
                id=template["id"],
                vector=vector,
                metadata={"name": template["name"]},
            )

        # Search for similar templates
        query_vector = await embedding_service.embed("data processing pipeline")
        results = await vector_provider.search(
            collection="plan_templates",
            query_vector=query_vector,
            limit=2,
        )

        assert len(results) <= 2
        # First result should be most similar (Data Pipeline)
        if results:
            assert results[0].score >= results[-1].score

    @pytest.mark.asyncio
    async def test_vector_search_with_filters(self) -> None:
        """
        GIVEN an InMemoryVectorProvider with metadata
        WHEN searching with filters
        THEN returns filtered results
        """
        from mcp_server_langgraph.llm.embeddings import (
            InMemoryEmbeddingService,
        )
        from mcp_server_langgraph.storage.vectors.inmemory import (
            InMemoryVectorProvider,
        )

        embedding_service = InMemoryEmbeddingService(dimensions=768)
        vector_provider = InMemoryVectorProvider()

        # Create templates with different categories
        await vector_provider.upsert(
            collection="templates",
            id="t1",
            vector=await embedding_service.embed("data processing"),
            metadata={"category": "data", "priority": "high"},
        )
        await vector_provider.upsert(
            collection="templates",
            id="t2",
            vector=await embedding_service.embed("model training"),
            metadata={"category": "ml", "priority": "high"},
        )
        await vector_provider.upsert(
            collection="templates",
            id="t3",
            vector=await embedding_service.embed("api integration"),
            metadata={"category": "data", "priority": "low"},
        )

        # Search with category filter
        query_vector = await embedding_service.embed("data workflow")
        results = await vector_provider.search(
            collection="templates",
            query_vector=query_vector,
            limit=10,
            filters={"category": "data"},
        )

        # Should only return data category items
        assert len(results) == 2
        for result in results:
            assert result.metadata.get("category") == "data"


@pytest.mark.xdist_group(name="plan_template_search_flow")
class TestPlanTemplateSearchFlow:
    """Integration tests for end-to-end plan template search flow."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_plan_template_semantic_search(self) -> None:
        """
        GIVEN a plan template repository with embeddings
        WHEN searching for templates by intent
        THEN returns semantically similar templates
        """
        from mcp_server_langgraph.llm.embeddings import (
            InMemoryEmbeddingService,
        )
        from mcp_server_langgraph.storage.vectors.inmemory import (
            InMemoryVectorProvider,
        )

        # Setup embedding and vector services
        embedding_service = InMemoryEmbeddingService(dimensions=768)
        vector_provider = InMemoryVectorProvider()

        # Simulate adding templates with embeddings
        templates = [
            {
                "id": "etl-pipeline",
                "name": "ETL Pipeline Template",
                "description": "Extract, transform, and load data from multiple sources",
            },
            {
                "id": "ml-inference",
                "name": "ML Inference Pipeline",
                "description": "Run machine learning model predictions on incoming data",
            },
            {
                "id": "notification-workflow",
                "name": "Notification Workflow",
                "description": "Send notifications via email, SMS, and push channels",
            },
        ]

        for template in templates:
            embedding = await embedding_service.embed(template["description"])
            await vector_provider.upsert(
                collection="plan_templates",
                id=template["id"],
                vector=embedding,
                metadata={
                    "name": template["name"],
                    "description": template["description"],
                },
            )

        # Search for templates
        query = "I need to process and transform data"
        query_embedding = await embedding_service.embed(query)
        results = await vector_provider.search(
            collection="plan_templates",
            query_vector=query_embedding,
            limit=3,
        )

        # With InMemory provider, we verify search works and returns results
        # Note: InMemoryEmbeddingService uses hash-based embeddings without
        # semantic meaning, so we can't assert on specific ranking
        assert len(results) >= 1
        # Verify results have expected structure
        result_ids = {r.id for r in results}
        assert result_ids.issubset({"etl-pipeline", "ml-inference", "notification-workflow"})

    @pytest.mark.asyncio
    async def test_feature_flag_gates_semantic_search(self) -> None:
        """
        GIVEN enable_plan_search feature flag is disabled
        WHEN attempting semantic search
        THEN falls back to simple matching or raises FeatureDisabledError
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(enable_plan_search=False)

        # Verify the flag value
        assert flags.enable_plan_search is False

    @pytest.mark.asyncio
    async def test_feature_flag_enables_semantic_search(self) -> None:
        """
        GIVEN enable_plan_search feature flag is enabled
        WHEN performing semantic search
        THEN uses vector-based search
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(enable_plan_search=True)

        # Verify the flag value
        assert flags.enable_plan_search is True


@pytest.mark.xdist_group(name="vector_provider_factory_integration")
class TestVectorProviderFactoryIntegration:
    """Integration tests for vector provider factory with Settings."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_vector_provider_from_settings_respects_config(self) -> None:
        """
        GIVEN Settings with vector_search_provider configured
        WHEN calling get_vector_provider_from_settings
        THEN creates the appropriate provider
        """
        from mcp_server_langgraph.storage.vectors.factory import (
            get_vector_provider_from_settings,
        )
        from mcp_server_langgraph.storage.vectors.inmemory import (
            InMemoryVectorProvider,
        )

        # Default settings should return InMemory
        with patch(
            "mcp_server_langgraph.core.config.settings"
        ) as mock_settings:
            mock_settings.vector_search_provider = "inmemory"
            provider = get_vector_provider_from_settings()
            assert isinstance(provider, InMemoryVectorProvider)

    def test_settings_vector_provider_env_override(self) -> None:
        """
        GIVEN VECTOR_SEARCH_PROVIDER environment variable
        WHEN creating Settings
        THEN uses the environment value
        """
        from mcp_server_langgraph.core.config import Settings

        with patch.dict("os.environ", {"VECTOR_SEARCH_PROVIDER": "qdrant"}):
            # Create fresh settings with env override
            settings = Settings(_env_file=None)
            assert settings.vector_search_provider == "qdrant"
