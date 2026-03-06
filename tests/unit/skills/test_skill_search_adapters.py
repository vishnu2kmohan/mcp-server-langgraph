"""Tests for SkillSearchTool adapters that bridge to shared infrastructure.

TDD: These tests define the adapters that connect SkillSearchTool
to the existing vector/embedding infrastructure.

The adapters bridge:
- VectorSearchProvider → VectorProviderProtocol
- LangChain Embeddings → EmbeddingServiceProtocol

ADR-0092: Hierarchical Capability Architecture
"""

from __future__ import annotations

import gc
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
class TestVectorProviderAdapter:
    """Tests for VectorProviderAdapter that wraps VectorSearchProvider."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_vector_provider_adapter_class_is_importable(self) -> None:
        """Test VectorProviderAdapter class exists and is importable."""
        from mcp_server_langgraph.skills.adapters import VectorProviderAdapter

        assert VectorProviderAdapter is not None

    def test_adapter_wraps_vector_search_provider(self) -> None:
        """Test adapter accepts VectorSearchProvider."""
        from mcp_server_langgraph.skills.adapters import VectorProviderAdapter

        mock_provider = MagicMock()
        adapter = VectorProviderAdapter(mock_provider)

        assert adapter._provider is mock_provider

    @pytest.mark.asyncio
    async def test_adapter_upsert_delegates_to_provider(self) -> None:
        """Test upsert delegates to wrapped provider."""
        from mcp_server_langgraph.skills.adapters import VectorProviderAdapter

        mock_provider = MagicMock()
        mock_provider.upsert = AsyncMock(return_value=None)

        adapter = VectorProviderAdapter(mock_provider)

        await adapter.upsert(
            collection="test-collection",
            id="doc-123",
            vector=[0.1, 0.2, 0.3],
            metadata={"key": "value"},
        )

        mock_provider.upsert.assert_called_once_with(
            collection="test-collection",
            id="doc-123",
            vector=[0.1, 0.2, 0.3],
            metadata={"key": "value"},
        )

    @pytest.mark.asyncio
    async def test_adapter_upsert_handles_none_metadata(self) -> None:
        """Test upsert handles None metadata by passing empty dict."""
        from mcp_server_langgraph.skills.adapters import VectorProviderAdapter

        mock_provider = MagicMock()
        mock_provider.upsert = AsyncMock(return_value=None)

        adapter = VectorProviderAdapter(mock_provider)

        await adapter.upsert(
            collection="test-collection",
            id="doc-123",
            vector=[0.1, 0.2, 0.3],
            metadata=None,
        )

        # Provider requires non-None metadata, adapter should convert None to {}
        mock_provider.upsert.assert_called_once_with(
            collection="test-collection",
            id="doc-123",
            vector=[0.1, 0.2, 0.3],
            metadata={},
        )

    @pytest.mark.asyncio
    async def test_adapter_search_returns_dicts(self) -> None:
        """Test search returns list of dicts (not VectorSearchResult)."""
        from mcp_server_langgraph.skills.adapters import VectorProviderAdapter
        from mcp_server_langgraph.storage.vectors.base import VectorSearchResult

        mock_provider = MagicMock()
        mock_provider.search = AsyncMock(
            return_value=[
                VectorSearchResult(id="doc-1", score=0.9, metadata={"name": "test"}),
            ]
        )

        adapter = VectorProviderAdapter(mock_provider)

        results = await adapter.search(
            collection="test-collection",
            query_vector=[0.1, 0.2, 0.3],
            limit=5,
            min_score=0.5,
        )

        assert isinstance(results, list)
        assert len(results) == 1
        assert isinstance(results[0], dict)
        assert results[0]["id"] == "doc-1"
        assert results[0]["score"] == 0.9
        assert results[0]["metadata"] == {"name": "test"}

    @pytest.mark.asyncio
    async def test_adapter_search_delegates_filters(self) -> None:
        """Test search passes filters to provider."""
        from mcp_server_langgraph.skills.adapters import VectorProviderAdapter

        mock_provider = MagicMock()
        mock_provider.search = AsyncMock(return_value=[])

        adapter = VectorProviderAdapter(mock_provider)

        await adapter.search(
            collection="skills",
            query_vector=[0.1, 0.2],
            filters={"scope": "user"},
        )

        call_args = mock_provider.search.call_args
        assert call_args[1]["filters"] == {"scope": "user"}


@pytest.mark.unit
class TestEmbeddingServiceAdapter:
    """Tests for EmbeddingServiceAdapter that wraps LangChain Embeddings."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_embedding_service_adapter_class_is_importable(self) -> None:
        """Test EmbeddingServiceAdapter class exists and is importable."""
        from mcp_server_langgraph.skills.adapters import EmbeddingServiceAdapter

        assert EmbeddingServiceAdapter is not None

    def test_adapter_wraps_langchain_embeddings(self) -> None:
        """Test adapter accepts LangChain Embeddings."""
        from mcp_server_langgraph.skills.adapters import EmbeddingServiceAdapter

        mock_embeddings = MagicMock()
        adapter = EmbeddingServiceAdapter(mock_embeddings)

        assert adapter._embeddings is mock_embeddings

    @pytest.mark.asyncio
    async def test_adapter_embed_calls_embed_query(self) -> None:
        """Test embed() calls embeddings.embed_query()."""
        from mcp_server_langgraph.skills.adapters import EmbeddingServiceAdapter

        mock_embeddings = MagicMock()
        mock_embeddings.embed_query = MagicMock(return_value=[0.1, 0.2, 0.3])

        adapter = EmbeddingServiceAdapter(mock_embeddings)

        result = await adapter.embed("test text")

        assert result == [0.1, 0.2, 0.3]
        mock_embeddings.embed_query.assert_called_once_with("test text")

    @pytest.mark.asyncio
    async def test_adapter_embed_runs_in_thread(self) -> None:
        """Test embed() runs sync method in thread pool."""
        from mcp_server_langgraph.skills.adapters import EmbeddingServiceAdapter
        from unittest.mock import patch

        mock_embeddings = MagicMock()
        mock_embeddings.embed_query = MagicMock(return_value=[0.1, 0.2])

        adapter = EmbeddingServiceAdapter(mock_embeddings)

        with patch("asyncio.to_thread", new=AsyncMock(return_value=[0.1, 0.2])) as mock_to_thread:
            result = await adapter.embed("test")
            mock_to_thread.assert_called_once()

        assert result == [0.1, 0.2]


@pytest.mark.unit
class TestSkillSearchToolFactory:
    """Tests for factory that creates SkillSearchTool with adapters."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_skill_search_tool_factory_is_importable(self) -> None:
        """Test create_skill_search_tool factory exists and is importable."""
        from mcp_server_langgraph.skills.adapters import create_skill_search_tool

        assert create_skill_search_tool is not None

    @pytest.mark.asyncio
    async def test_factory_creates_tool_with_qdrant(self) -> None:
        """Test factory creates SkillSearchTool with Qdrant adapter."""
        from mcp_server_langgraph.skills.adapters import create_skill_search_tool
        from mcp_server_langgraph.skills.search import SkillSearchTool
        from unittest.mock import patch

        # Mock the settings and infrastructure - patch at the source modules
        with (
            patch("mcp_server_langgraph.storage.vectors.factory.get_vector_provider_from_settings") as mock_get_provider,
            patch("mcp_server_langgraph.core.dynamic_context_loader._create_embeddings") as mock_create_embeddings,
            patch("mcp_server_langgraph.core.config.settings") as mock_settings,
        ):
            mock_get_provider.return_value = MagicMock()
            mock_create_embeddings.return_value = MagicMock()
            mock_settings.qdrant_url = "http://localhost:6333"
            mock_settings.embedding_provider = "google"
            mock_settings.embedding_model_name = "models/text-embedding-004"
            mock_settings.google_api_key = "test-key"

            tool = create_skill_search_tool()

            assert isinstance(tool, SkillSearchTool)
            assert tool.vector_provider is not None
            assert tool.embedding_service is not None

    def test_factory_returns_none_when_not_configured(self) -> None:
        """Test factory returns None when embeddings not configured."""
        from mcp_server_langgraph.skills.adapters import create_skill_search_tool
        from unittest.mock import patch

        with patch("mcp_server_langgraph.core.config.settings") as mock_settings:
            mock_settings.qdrant_url = None
            mock_settings.embedding_provider = None

            tool = create_skill_search_tool()

            assert tool is None


@pytest.mark.unit
class TestVectorProviderAdapterPgVectorCompatibility:
    """Tests verifying VectorProviderAdapter works with PgVectorProvider.

    These tests ensure the adapter pattern correctly bridges PgVectorProvider
    to the VectorProviderProtocol expected by SkillSearchTool.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_adapter_wraps_pgvector_provider(self) -> None:
        """Test adapter accepts PgVectorProvider."""
        from mcp_server_langgraph.skills.adapters import VectorProviderAdapter
        from mcp_server_langgraph.storage.vectors.pgvector_provider import PgVectorProvider

        # PgVectorProvider requires a connection pool
        mock_pool = MagicMock()
        provider = PgVectorProvider(connection_pool=mock_pool)
        adapter = VectorProviderAdapter(provider)

        assert adapter._provider is provider

    @pytest.mark.asyncio
    async def test_adapter_upsert_delegates_to_pgvector(self) -> None:
        """Test upsert delegates to PgVectorProvider."""
        from mcp_server_langgraph.skills.adapters import VectorProviderAdapter
        from mcp_server_langgraph.storage.vectors.pgvector_provider import PgVectorProvider

        mock_pool = MagicMock()
        provider = PgVectorProvider(connection_pool=mock_pool)

        # Mock the provider's upsert method
        provider.upsert = AsyncMock(return_value=None)  # type: ignore[method-assign]

        adapter = VectorProviderAdapter(provider)

        await adapter.upsert(
            collection="skills",
            id="skill-001",
            vector=[0.1, 0.2, 0.3],
            metadata={"name": "test-skill"},
        )

        provider.upsert.assert_called_once_with(
            collection="skills",
            id="skill-001",
            vector=[0.1, 0.2, 0.3],
            metadata={"name": "test-skill"},
        )

    @pytest.mark.asyncio
    async def test_adapter_search_converts_pgvector_results(self) -> None:
        """Test search converts PgVectorProvider results to dicts."""
        from mcp_server_langgraph.skills.adapters import VectorProviderAdapter
        from mcp_server_langgraph.storage.vectors.base import VectorSearchResult
        from mcp_server_langgraph.storage.vectors.pgvector_provider import PgVectorProvider

        mock_pool = MagicMock()
        provider = PgVectorProvider(connection_pool=mock_pool)

        # Mock search to return VectorSearchResult (same as QdrantProvider)
        provider.search = AsyncMock(  # type: ignore[method-assign]
            return_value=[
                VectorSearchResult(id="skill-001", score=0.95, metadata={"name": "code-review"}),
                VectorSearchResult(id="skill-002", score=0.85, metadata={"name": "test-gen"}),
            ]
        )

        adapter = VectorProviderAdapter(provider)

        results = await adapter.search(
            collection="skills",
            query_vector=[0.1, 0.2, 0.3],
            limit=10,
        )

        # Adapter should convert VectorSearchResult to dict
        assert len(results) == 2
        assert isinstance(results[0], dict)
        assert results[0]["id"] == "skill-001"
        assert results[0]["score"] == 0.95
        assert results[0]["metadata"] == {"name": "code-review"}


@pytest.mark.unit
class TestVectorProviderAdapterInMemoryCompatibility:
    """Tests verifying VectorProviderAdapter works with InMemoryVectorProvider.

    These tests ensure the adapter pattern correctly bridges InMemoryVectorProvider
    (used for testing) to the VectorProviderProtocol expected by SkillSearchTool.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_adapter_wraps_inmemory_provider(self) -> None:
        """Test adapter accepts InMemoryVectorProvider."""
        from mcp_server_langgraph.skills.adapters import VectorProviderAdapter
        from mcp_server_langgraph.storage.vectors.inmemory import InMemoryVectorProvider

        provider = InMemoryVectorProvider()
        adapter = VectorProviderAdapter(provider)

        assert adapter._provider is provider

    @pytest.mark.asyncio
    async def test_adapter_upsert_stores_in_inmemory(self) -> None:
        """Test upsert stores vectors in InMemoryVectorProvider."""
        from mcp_server_langgraph.skills.adapters import VectorProviderAdapter
        from mcp_server_langgraph.storage.vectors.inmemory import InMemoryVectorProvider

        provider = InMemoryVectorProvider()
        adapter = VectorProviderAdapter(provider)

        await adapter.upsert(
            collection="skills",
            id="skill-001",
            vector=[0.1, 0.2, 0.3],
            metadata={"name": "test-skill"},
        )

        # Verify data stored in provider
        key = ("skills", "skill-001")
        assert key in provider._vectors
        assert provider._vectors[key].metadata == {"name": "test-skill"}

    @pytest.mark.asyncio
    async def test_adapter_search_returns_real_results(self) -> None:
        """Test search returns actual results from InMemoryVectorProvider."""
        from mcp_server_langgraph.skills.adapters import VectorProviderAdapter
        from mcp_server_langgraph.storage.vectors.inmemory import InMemoryVectorProvider

        provider = InMemoryVectorProvider()
        adapter = VectorProviderAdapter(provider)

        # Insert test vectors
        await adapter.upsert(
            collection="skills",
            id="skill-001",
            vector=[1.0, 0.0, 0.0],
            metadata={"name": "code-review"},
        )
        await adapter.upsert(
            collection="skills",
            id="skill-002",
            vector=[0.0, 1.0, 0.0],
            metadata={"name": "test-gen"},
        )

        # Search with a query similar to skill-001
        results = await adapter.search(
            collection="skills",
            query_vector=[0.9, 0.1, 0.0],
            limit=2,
        )

        # Should return both results
        assert len(results) == 2
        assert isinstance(results[0], dict)
        # First result should be more similar to query
        assert results[0]["id"] == "skill-001"
        assert results[0]["score"] > results[1]["score"]

    @pytest.mark.asyncio
    async def test_adapter_end_to_end_with_skill_search_tool(self) -> None:
        """Test full SkillSearchTool workflow with InMemoryVectorProvider."""
        from mcp_server_langgraph.skills.adapters import (
            EmbeddingServiceAdapter,
            VectorProviderAdapter,
        )
        from mcp_server_langgraph.skills.models import Skill
        from mcp_server_langgraph.skills.search import SkillSearchTool
        from mcp_server_langgraph.storage.vectors.inmemory import InMemoryVectorProvider

        # Create real in-memory provider
        provider = InMemoryVectorProvider()
        adapter = VectorProviderAdapter(provider)

        # Create mock embedding service
        mock_embeddings = MagicMock()
        mock_embeddings.embed_query = MagicMock(return_value=[0.1] * 768)
        embedding_adapter = EmbeddingServiceAdapter(mock_embeddings)

        # Create tool
        tool = SkillSearchTool(
            vector_provider=adapter,
            embedding_service=embedding_adapter,
        )

        # Index a skill
        skill = Skill(
            name="code-review",
            description="Review code for quality",
            tags=["code", "review"],
        )
        await tool.index_skill(skill, skill_id="skill-001")

        # Verify skill was indexed
        key = ("skills", "skill-001")
        assert key in provider._vectors
        assert provider._vectors[key].metadata["name"] == "code-review"
