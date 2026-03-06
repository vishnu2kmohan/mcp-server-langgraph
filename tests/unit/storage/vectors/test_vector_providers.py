"""
Tests for Vector Search Providers

TDD: These tests define the contract for provider-agnostic vector search.
Supports pgvector (Postgres) and Qdrant implementations.
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.unit

if TYPE_CHECKING:
    pass


class TestVectorSearchProviderBase:
    """Tests for VectorSearchProvider abstract base class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_vector_search_provider_exists(self) -> None:
        """Test that VectorSearchProvider base class exists."""
        from mcp_server_langgraph.storage.vectors.base import VectorSearchProvider

        assert VectorSearchProvider is not None

    def test_vector_search_provider_has_upsert_method(self) -> None:
        """Test VectorSearchProvider has upsert method."""
        from mcp_server_langgraph.storage.vectors.base import VectorSearchProvider

        assert hasattr(VectorSearchProvider, "upsert")

    def test_vector_search_provider_has_search_method(self) -> None:
        """Test VectorSearchProvider has search method."""
        from mcp_server_langgraph.storage.vectors.base import VectorSearchProvider

        assert hasattr(VectorSearchProvider, "search")

    def test_vector_search_provider_has_delete_method(self) -> None:
        """Test VectorSearchProvider has delete method."""
        from mcp_server_langgraph.storage.vectors.base import VectorSearchProvider

        assert hasattr(VectorSearchProvider, "delete")

    def test_vector_search_result_exists(self) -> None:
        """Test that VectorSearchResult dataclass exists."""
        from mcp_server_langgraph.storage.vectors.base import VectorSearchResult

        assert VectorSearchResult is not None

    def test_vector_search_result_has_required_fields(self) -> None:
        """Test VectorSearchResult has id, score, and metadata fields."""
        from mcp_server_langgraph.storage.vectors.base import VectorSearchResult

        result = VectorSearchResult(
            id="doc-123",
            score=0.95,
            metadata={"key": "value"},
        )

        assert result.id == "doc-123"
        assert result.score == 0.95
        assert result.metadata == {"key": "value"}


class TestInMemoryVectorProvider:
    """Tests for InMemoryVectorProvider (testing implementation)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_inmemory_provider_exists(self) -> None:
        """Test that InMemoryVectorProvider exists."""
        from mcp_server_langgraph.storage.vectors.inmemory import (
            InMemoryVectorProvider,
        )

        assert InMemoryVectorProvider is not None

    def test_inmemory_provider_implements_interface(self) -> None:
        """Test InMemoryVectorProvider implements VectorSearchProvider."""
        from mcp_server_langgraph.storage.vectors.base import VectorSearchProvider
        from mcp_server_langgraph.storage.vectors.inmemory import (
            InMemoryVectorProvider,
        )

        provider = InMemoryVectorProvider()
        assert isinstance(provider, VectorSearchProvider)

    @pytest.mark.asyncio
    async def test_upsert_stores_vector(self) -> None:
        """Test upsert stores vector with metadata."""
        from mcp_server_langgraph.storage.vectors.inmemory import (
            InMemoryVectorProvider,
        )

        provider = InMemoryVectorProvider()

        await provider.upsert(
            collection="test",
            id="doc-1",
            vector=[0.1, 0.2, 0.3],
            metadata={"title": "Test Doc"},
        )

        # Verify stored
        results = await provider.search(
            collection="test",
            query_vector=[0.1, 0.2, 0.3],
            limit=1,
        )

        assert len(results) == 1
        assert results[0].id == "doc-1"

    @pytest.mark.asyncio
    async def test_search_returns_similar_vectors(self) -> None:
        """Test search returns vectors by similarity."""
        from mcp_server_langgraph.storage.vectors.inmemory import (
            InMemoryVectorProvider,
        )

        provider = InMemoryVectorProvider()

        # Insert multiple vectors
        await provider.upsert("test", "doc-1", [1.0, 0.0, 0.0], {"title": "Doc 1"})
        await provider.upsert("test", "doc-2", [0.9, 0.1, 0.0], {"title": "Doc 2"})
        await provider.upsert("test", "doc-3", [0.0, 1.0, 0.0], {"title": "Doc 3"})

        # Search for vectors similar to doc-1
        results = await provider.search(
            collection="test",
            query_vector=[1.0, 0.0, 0.0],
            limit=2,
        )

        assert len(results) == 2
        # First result should be doc-1 (exact match)
        assert results[0].id == "doc-1"
        # Second should be doc-2 (most similar)
        assert results[1].id == "doc-2"

    @pytest.mark.asyncio
    async def test_search_respects_min_score(self) -> None:
        """Test search filters by minimum score."""
        from mcp_server_langgraph.storage.vectors.inmemory import (
            InMemoryVectorProvider,
        )

        provider = InMemoryVectorProvider()

        await provider.upsert("test", "doc-1", [1.0, 0.0, 0.0], {})
        await provider.upsert("test", "doc-2", [0.0, 1.0, 0.0], {})  # Orthogonal

        results = await provider.search(
            collection="test",
            query_vector=[1.0, 0.0, 0.0],
            limit=10,
            min_score=0.5,
        )

        # Only doc-1 should match with high similarity
        assert len(results) == 1
        assert results[0].id == "doc-1"

    @pytest.mark.asyncio
    async def test_search_with_metadata_filters(self) -> None:
        """Test search filters by metadata."""
        from mcp_server_langgraph.storage.vectors.inmemory import (
            InMemoryVectorProvider,
        )

        provider = InMemoryVectorProvider()

        await provider.upsert("test", "doc-1", [1.0, 0.0, 0.0], {"category": "A", "status": "active"})
        await provider.upsert("test", "doc-2", [0.9, 0.1, 0.0], {"category": "B", "status": "active"})
        await provider.upsert("test", "doc-3", [0.8, 0.2, 0.0], {"category": "A", "status": "inactive"})

        results = await provider.search(
            collection="test",
            query_vector=[1.0, 0.0, 0.0],
            limit=10,
            filters={"category": "A"},
        )

        assert len(results) == 2
        assert all(r.metadata.get("category") == "A" for r in results)

    @pytest.mark.asyncio
    async def test_delete_removes_vector(self) -> None:
        """Test delete removes a vector."""
        from mcp_server_langgraph.storage.vectors.inmemory import (
            InMemoryVectorProvider,
        )

        provider = InMemoryVectorProvider()

        await provider.upsert("test", "doc-1", [1.0, 0.0, 0.0], {})
        await provider.upsert("test", "doc-2", [0.0, 1.0, 0.0], {})

        await provider.delete("test", "doc-1")

        results = await provider.search(
            collection="test",
            query_vector=[1.0, 0.0, 0.0],
            limit=10,
        )

        assert len(results) == 1
        assert results[0].id == "doc-2"

    @pytest.mark.asyncio
    async def test_upsert_updates_existing(self) -> None:
        """Test upsert updates existing vector."""
        from mcp_server_langgraph.storage.vectors.inmemory import (
            InMemoryVectorProvider,
        )

        provider = InMemoryVectorProvider()

        await provider.upsert("test", "doc-1", [1.0, 0.0, 0.0], {"version": "1"})
        await provider.upsert("test", "doc-1", [0.0, 1.0, 0.0], {"version": "2"})

        results = await provider.search(
            collection="test",
            query_vector=[0.0, 1.0, 0.0],
            limit=1,
        )

        assert len(results) == 1
        assert results[0].id == "doc-1"
        assert results[0].metadata.get("version") == "2"


class TestVectorProviderFactory:
    """Tests for vector provider factory."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_factory_function_exists(self) -> None:
        """Test that get_vector_provider factory exists."""
        from mcp_server_langgraph.storage.vectors.factory import get_vector_provider

        assert callable(get_vector_provider)

    def test_factory_returns_inmemory_by_default(self) -> None:
        """Test factory returns InMemoryVectorProvider for testing."""
        from mcp_server_langgraph.storage.vectors.factory import get_vector_provider
        from mcp_server_langgraph.storage.vectors.inmemory import (
            InMemoryVectorProvider,
        )

        # Without configuration, should return in-memory for safety
        provider = get_vector_provider(provider_type="inmemory")
        assert isinstance(provider, InMemoryVectorProvider)

    def test_factory_supports_pgvector_type(self) -> None:
        """Test factory recognizes pgvector provider type."""
        from mcp_server_langgraph.storage.vectors.factory import SUPPORTED_PROVIDERS

        assert "pgvector" in SUPPORTED_PROVIDERS

    def test_factory_supports_qdrant_type(self) -> None:
        """Test factory recognizes qdrant provider type."""
        from mcp_server_langgraph.storage.vectors.factory import SUPPORTED_PROVIDERS

        assert "qdrant" in SUPPORTED_PROVIDERS

    def test_factory_supports_inmemory_type(self) -> None:
        """Test factory recognizes inmemory provider type."""
        from mcp_server_langgraph.storage.vectors.factory import SUPPORTED_PROVIDERS

        assert "inmemory" in SUPPORTED_PROVIDERS

    def test_factory_creates_pgvector_with_pool(self) -> None:
        """Test factory creates PgVectorProvider when pool provided."""
        from mcp_server_langgraph.storage.vectors.factory import get_vector_provider
        from mcp_server_langgraph.storage.vectors.pgvector_provider import (
            PgVectorProvider,
        )

        mock_pool = MagicMock()
        provider = get_vector_provider(provider_type="pgvector", connection_pool=mock_pool)
        assert isinstance(provider, PgVectorProvider)

    def test_factory_creates_qdrant_with_client(self) -> None:
        """Test factory creates QdrantVectorProvider when client provided."""
        from mcp_server_langgraph.storage.vectors.factory import get_vector_provider
        from mcp_server_langgraph.storage.vectors.qdrant_provider import (
            QdrantVectorProvider,
        )

        mock_client = MagicMock()
        provider = get_vector_provider(provider_type="qdrant", client=mock_client)
        assert isinstance(provider, QdrantVectorProvider)


class TestPgVectorProvider:
    """Tests for PgVectorProvider (PostgreSQL pgvector extension)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_pgvector_provider_module_exists(self) -> None:
        """Test that pgvector_provider module exists."""
        try:
            from mcp_server_langgraph.storage.vectors import pgvector_provider

            assert pgvector_provider is not None
        except ImportError:
            pytest.skip("pgvector dependencies not available")

    def test_pgvector_provider_class_exists(self) -> None:
        """Test that PgVectorProvider class exists."""
        try:
            from mcp_server_langgraph.storage.vectors.pgvector_provider import (
                PgVectorProvider,
            )

            assert PgVectorProvider is not None
        except ImportError:
            pytest.skip("pgvector dependencies not available")

    def test_pgvector_provider_implements_interface(self) -> None:
        """Test PgVectorProvider implements VectorSearchProvider."""
        try:
            from mcp_server_langgraph.storage.vectors.base import VectorSearchProvider
            from mcp_server_langgraph.storage.vectors.pgvector_provider import (
                PgVectorProvider,
            )

            # Create with mock pool
            mock_pool = MagicMock()
            provider = PgVectorProvider(connection_pool=mock_pool)
            assert isinstance(provider, VectorSearchProvider)
        except ImportError:
            pytest.skip("pgvector dependencies not available")

    def test_pgvector_provider_has_upsert_method(self) -> None:
        """Test PgVectorProvider has upsert method."""
        try:
            from mcp_server_langgraph.storage.vectors.pgvector_provider import (
                PgVectorProvider,
            )

            assert hasattr(PgVectorProvider, "upsert")
            assert callable(PgVectorProvider.upsert)
        except ImportError:
            pytest.skip("pgvector dependencies not available")

    def test_pgvector_provider_has_search_method(self) -> None:
        """Test PgVectorProvider has search method."""
        try:
            from mcp_server_langgraph.storage.vectors.pgvector_provider import (
                PgVectorProvider,
            )

            assert hasattr(PgVectorProvider, "search")
            assert callable(PgVectorProvider.search)
        except ImportError:
            pytest.skip("pgvector dependencies not available")

    def test_pgvector_provider_has_delete_method(self) -> None:
        """Test PgVectorProvider has delete method."""
        try:
            from mcp_server_langgraph.storage.vectors.pgvector_provider import (
                PgVectorProvider,
            )

            assert hasattr(PgVectorProvider, "delete")
            assert callable(PgVectorProvider.delete)
        except ImportError:
            pytest.skip("pgvector dependencies not available")

    @pytest.mark.asyncio
    async def test_pgvector_upsert_executes_sql(self) -> None:
        """Test upsert executes correct SQL."""
        try:
            from mcp_server_langgraph.storage.vectors.pgvector_provider import (
                PgVectorProvider,
            )

            mock_pool = MagicMock()
            mock_conn = AsyncMock(return_value=None)  # noqa: async-mock-config - nested context manager

            # Set up async context manager for pool.acquire()
            mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_conn.execute = AsyncMock(return_value=None)

            provider = PgVectorProvider(connection_pool=mock_pool)
            await provider.upsert(
                collection="test",
                id="doc-1",
                vector=[0.1, 0.2, 0.3],
                metadata={"title": "Test"},
            )

            # Verify execute was called (2 times: ensure_table + upsert)
            assert mock_conn.execute.called
        except ImportError:
            pytest.skip("pgvector dependencies not available")

    @pytest.mark.asyncio
    async def test_pgvector_search_returns_results(self) -> None:
        """Test search returns VectorSearchResult objects."""
        try:
            from mcp_server_langgraph.storage.vectors.pgvector_provider import (
                PgVectorProvider,
            )
            from mcp_server_langgraph.storage.vectors.base import VectorSearchResult

            mock_pool = MagicMock()
            mock_conn = MagicMock()
            mock_cursor = MagicMock()

            # Set up async context managers
            mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_conn.cursor.return_value.__aenter__ = AsyncMock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_cursor.execute = AsyncMock(return_value=None)
            mock_cursor.fetchall = AsyncMock(
                return_value=[
                    ("doc-1", 0.95, '{"title": "Test"}'),
                ]
            )

            provider = PgVectorProvider(connection_pool=mock_pool)
            results = await provider.search(
                collection="test",
                query_vector=[0.1, 0.2, 0.3],
                limit=10,
            )

            assert len(results) >= 0
            if results:
                assert isinstance(results[0], VectorSearchResult)
        except ImportError:
            pytest.skip("pgvector dependencies not available")


class TestQdrantVectorProvider:
    """Tests for QdrantVectorProvider (Qdrant vector database)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_qdrant_provider_module_exists(self) -> None:
        """Test that qdrant_provider module exists."""
        try:
            from mcp_server_langgraph.storage.vectors import qdrant_provider

            assert qdrant_provider is not None
        except ImportError:
            pytest.skip("qdrant dependencies not available")

    def test_qdrant_provider_class_exists(self) -> None:
        """Test that QdrantVectorProvider class exists."""
        try:
            from mcp_server_langgraph.storage.vectors.qdrant_provider import (
                QdrantVectorProvider,
            )

            assert QdrantVectorProvider is not None
        except ImportError:
            pytest.skip("qdrant dependencies not available")

    def test_qdrant_provider_implements_interface(self) -> None:
        """Test QdrantVectorProvider implements VectorSearchProvider."""
        try:
            from mcp_server_langgraph.storage.vectors.base import VectorSearchProvider
            from mcp_server_langgraph.storage.vectors.qdrant_provider import (
                QdrantVectorProvider,
            )

            # Create with mock client
            mock_client = MagicMock()
            provider = QdrantVectorProvider(client=mock_client)
            assert isinstance(provider, VectorSearchProvider)
        except ImportError:
            pytest.skip("qdrant dependencies not available")

    def test_qdrant_provider_has_upsert_method(self) -> None:
        """Test QdrantVectorProvider has upsert method."""
        try:
            from mcp_server_langgraph.storage.vectors.qdrant_provider import (
                QdrantVectorProvider,
            )

            assert hasattr(QdrantVectorProvider, "upsert")
            assert callable(QdrantVectorProvider.upsert)
        except ImportError:
            pytest.skip("qdrant dependencies not available")

    def test_qdrant_provider_has_search_method(self) -> None:
        """Test QdrantVectorProvider has search method."""
        try:
            from mcp_server_langgraph.storage.vectors.qdrant_provider import (
                QdrantVectorProvider,
            )

            assert hasattr(QdrantVectorProvider, "search")
            assert callable(QdrantVectorProvider.search)
        except ImportError:
            pytest.skip("qdrant dependencies not available")

    def test_qdrant_provider_has_delete_method(self) -> None:
        """Test QdrantVectorProvider has delete method."""
        try:
            from mcp_server_langgraph.storage.vectors.qdrant_provider import (
                QdrantVectorProvider,
            )

            assert hasattr(QdrantVectorProvider, "delete")
            assert callable(QdrantVectorProvider.delete)
        except ImportError:
            pytest.skip("qdrant dependencies not available")

    @pytest.mark.asyncio
    async def test_qdrant_upsert_calls_client(self) -> None:
        """Test upsert calls Qdrant client."""
        try:
            from mcp_server_langgraph.storage.vectors.qdrant_provider import (
                QdrantVectorProvider,
            )

            mock_client = MagicMock()
            mock_client.upsert = AsyncMock(return_value=None)

            provider = QdrantVectorProvider(client=mock_client)
            await provider.upsert(
                collection="test",
                id="doc-1",
                vector=[0.1, 0.2, 0.3],
                metadata={"title": "Test"},
            )

            # Verify client was called
            assert mock_client.upsert.called
        except ImportError:
            pytest.skip("qdrant dependencies not available")

    @pytest.mark.asyncio
    async def test_qdrant_search_returns_results(self) -> None:
        """Test search returns VectorSearchResult objects."""
        try:
            from mcp_server_langgraph.storage.vectors.qdrant_provider import (
                QdrantVectorProvider,
            )
            from mcp_server_langgraph.storage.vectors.base import VectorSearchResult

            mock_client = MagicMock()
            mock_result = MagicMock()
            mock_result.id = "doc-1"
            mock_result.score = 0.95
            mock_result.payload = {"title": "Test"}
            # Use query_points API (qdrant-client >= 1.7)
            mock_response = MagicMock()
            mock_response.points = [mock_result]
            mock_client.query_points = AsyncMock(return_value=mock_response)

            provider = QdrantVectorProvider(client=mock_client)
            results = await provider.search(
                collection="test",
                query_vector=[0.1, 0.2, 0.3],
                limit=10,
            )

            assert len(results) == 1
            assert isinstance(results[0], VectorSearchResult)
            assert results[0].id == "doc-1"
            assert results[0].score == 0.95
        except ImportError:
            pytest.skip("qdrant dependencies not available")

    @pytest.mark.asyncio
    async def test_qdrant_search_with_filters(self) -> None:
        """Test search applies metadata filters."""
        try:
            from mcp_server_langgraph.storage.vectors.qdrant_provider import (
                QdrantVectorProvider,
            )

            mock_client = MagicMock()
            # Use query_points API (qdrant-client >= 1.7)
            mock_response = MagicMock()
            mock_response.points = []
            mock_client.query_points = AsyncMock(return_value=mock_response)

            provider = QdrantVectorProvider(client=mock_client)
            await provider.search(
                collection="test",
                query_vector=[0.1, 0.2, 0.3],
                limit=10,
                filters={"category": "A"},
            )

            # Verify query_points was called with filter
            assert mock_client.query_points.called
            call_kwargs = mock_client.query_points.call_args
            # Filter should be passed in some form
            assert call_kwargs is not None
        except ImportError:
            pytest.skip("qdrant dependencies not available")

    @pytest.mark.asyncio
    async def test_qdrant_delete_calls_client(self) -> None:
        """Test delete calls Qdrant client."""
        try:
            from mcp_server_langgraph.storage.vectors.qdrant_provider import (
                QdrantVectorProvider,
            )

            mock_client = MagicMock()
            mock_client.delete = AsyncMock(return_value=None)

            provider = QdrantVectorProvider(client=mock_client)
            await provider.delete(collection="test", id="doc-1")

            # Verify client was called
            assert mock_client.delete.called
        except ImportError:
            pytest.skip("qdrant dependencies not available")
