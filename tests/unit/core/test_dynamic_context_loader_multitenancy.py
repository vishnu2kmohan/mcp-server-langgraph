"""
Tests for DynamicContextLoader multi-tenant isolation.

TDD: These tests are written FIRST to define the expected behavior
of tenant_id filtering in semantic_search and _load_context_impl.

ADR-0095: Multi-Tenant Vector Search Isolation

Tests verify:
1. semantic_search includes tenant_id filter when multi-tenant isolation enabled
2. semantic_search raises error if tenant_id missing when isolation enabled
3. semantic_search works without tenant_id when isolation disabled (legacy mode)
4. _load_context_impl respects tenant_id isolation
5. Backward compatibility with single-tenant deployments
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit

if TYPE_CHECKING:
    pass


@pytest.mark.xdist_group(name="dynamic_context_loader_multitenancy")
class TestSemanticSearchTenantIsolation:
    """Tests for tenant isolation in semantic_search."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_semantic_search_accepts_tenant_id_parameter(self) -> None:
        """GIVEN DynamicContextLoader with multi-tenant isolation enabled
        WHEN semantic_search is called with tenant_id
        THEN it should accept the parameter without error
        """
        mock_result = MagicMock()
        mock_result.id = "doc-123"
        mock_result.score = 0.85
        mock_result.payload = {
            "ref_id": "ref-123",
            "ref_type": "document",
            "summary": "Test document",
            "tenant_id": "tenant-1",
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
                side_effect=lambda *a, **kw: mock_embedder,
            ),
            patch("mcp_server_langgraph.core.dynamic_context_loader.settings") as mock_settings,
        ):
            mock_settings.enable_multi_tenant_isolation = True
            mock_settings.qdrant_url = "http://localhost:6333"
            mock_settings.qdrant_port = 6333
            mock_settings.qdrant_collection_name = "test_collection"
            mock_settings.embedding_provider = "google"
            mock_settings.embedding_model_name = "text-embedding-004"
            mock_settings.embedding_dimensions = 768
            mock_settings.context_cache_size = 100
            mock_settings.enable_context_encryption = False
            mock_settings.context_retention_days = 30
            mock_settings.enable_auto_deletion = False
            mock_settings.google_api_key = "test-key"
            mock_settings.embedding_task_type = None

            from mcp_server_langgraph.core.dynamic_context_loader import (
                DynamicContextLoader,
            )

            loader = DynamicContextLoader(
                qdrant_url="http://localhost:6333",
                collection_name="test_collection",
            )

            # Should accept tenant_id without error
            results = await loader.semantic_search(
                query="test query",
                tenant_id="tenant-1",
                top_k=5,
            )

            assert len(results) == 1

    @pytest.mark.asyncio
    async def test_semantic_search_includes_tenant_filter(self) -> None:
        """GIVEN DynamicContextLoader with multi-tenant isolation enabled
        WHEN semantic_search is called with tenant_id
        THEN the Qdrant search should include tenant_id filter
        """
        mock_result = MagicMock()
        mock_result.id = "doc-123"
        mock_result.score = 0.85
        mock_result.payload = {
            "ref_id": "ref-123",
            "ref_type": "document",
            "summary": "Test document",
            "tenant_id": "tenant-1",
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
                side_effect=lambda *a, **kw: mock_embedder,
            ),
            patch("mcp_server_langgraph.core.dynamic_context_loader.settings") as mock_settings,
        ):
            mock_settings.enable_multi_tenant_isolation = True
            mock_settings.qdrant_url = "http://localhost:6333"
            mock_settings.qdrant_port = 6333
            mock_settings.qdrant_collection_name = "test_collection"
            mock_settings.embedding_provider = "google"
            mock_settings.embedding_model_name = "text-embedding-004"
            mock_settings.embedding_dimensions = 768
            mock_settings.context_cache_size = 100
            mock_settings.enable_context_encryption = False
            mock_settings.context_retention_days = 30
            mock_settings.enable_auto_deletion = False
            mock_settings.google_api_key = "test-key"
            mock_settings.embedding_task_type = None

            from mcp_server_langgraph.core.dynamic_context_loader import (
                DynamicContextLoader,
            )

            loader = DynamicContextLoader(
                qdrant_url="http://localhost:6333",
                collection_name="test_collection",
            )

            await loader.semantic_search(
                query="test query",
                tenant_id="tenant-1",
                top_k=5,
            )

            # Verify tenant filter was passed to Qdrant
            mock_client.search.assert_called_once()
            call_kwargs = mock_client.search.call_args.kwargs
            query_filter = call_kwargs.get("query_filter")

            assert query_filter is not None, "Query filter should include tenant_id"
            # Check that filter includes tenant_id condition
            filter_conditions = query_filter.must
            assert any(getattr(cond, "key", None) == "tenant_id" for cond in filter_conditions), (
                "Filter should include tenant_id condition"
            )

    @pytest.mark.asyncio
    async def test_semantic_search_raises_error_when_tenant_id_missing(self) -> None:
        """GIVEN DynamicContextLoader with multi-tenant isolation enabled
        WHEN semantic_search is called WITHOUT tenant_id
        THEN it should raise ValueError
        """
        mock_client = AsyncMock(return_value=None)
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
                side_effect=lambda *a, **kw: mock_embedder,
            ),
            patch("mcp_server_langgraph.core.dynamic_context_loader.settings") as mock_settings,
        ):
            mock_settings.enable_multi_tenant_isolation = True
            mock_settings.qdrant_url = "http://localhost:6333"
            mock_settings.qdrant_port = 6333
            mock_settings.qdrant_collection_name = "test_collection"
            mock_settings.embedding_provider = "google"
            mock_settings.embedding_model_name = "text-embedding-004"
            mock_settings.embedding_dimensions = 768
            mock_settings.context_cache_size = 100
            mock_settings.enable_context_encryption = False
            mock_settings.context_retention_days = 30
            mock_settings.enable_auto_deletion = False
            mock_settings.google_api_key = "test-key"
            mock_settings.embedding_task_type = None

            from mcp_server_langgraph.core.dynamic_context_loader import (
                DynamicContextLoader,
            )

            loader = DynamicContextLoader(
                qdrant_url="http://localhost:6333",
                collection_name="test_collection",
            )

            with pytest.raises(ValueError, match="tenant_id required"):
                await loader.semantic_search(
                    query="test query",
                    top_k=5,
                    # No tenant_id provided
                )


@pytest.mark.xdist_group(name="dynamic_context_loader_multitenancy")
class TestSemanticSearchBackwardCompatibility:
    """Tests for backward compatibility when multi-tenant isolation is disabled."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_semantic_search_works_without_tenant_id_when_isolation_disabled(
        self,
    ) -> None:
        """GIVEN DynamicContextLoader with multi-tenant isolation DISABLED
        WHEN semantic_search is called WITHOUT tenant_id
        THEN it should work (legacy single-tenant mode)
        """
        mock_result = MagicMock()
        mock_result.id = "doc-123"
        mock_result.score = 0.85
        mock_result.payload = {
            "ref_id": "ref-123",
            "ref_type": "document",
            "summary": "Test document",
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
                side_effect=lambda *a, **kw: mock_embedder,
            ),
            patch("mcp_server_langgraph.core.dynamic_context_loader.settings") as mock_settings,
        ):
            mock_settings.enable_multi_tenant_isolation = False  # Disabled
            mock_settings.qdrant_url = "http://localhost:6333"
            mock_settings.qdrant_port = 6333
            mock_settings.qdrant_collection_name = "test_collection"
            mock_settings.embedding_provider = "google"
            mock_settings.embedding_model_name = "text-embedding-004"
            mock_settings.embedding_dimensions = 768
            mock_settings.context_cache_size = 100
            mock_settings.enable_context_encryption = False
            mock_settings.context_retention_days = 30
            mock_settings.enable_auto_deletion = False
            mock_settings.google_api_key = "test-key"
            mock_settings.embedding_task_type = None

            from mcp_server_langgraph.core.dynamic_context_loader import (
                DynamicContextLoader,
            )

            loader = DynamicContextLoader(
                qdrant_url="http://localhost:6333",
                collection_name="test_collection",
            )

            # Should work without tenant_id in legacy mode
            results = await loader.semantic_search(
                query="test query",
                top_k=5,
            )

            assert len(results) == 1

    @pytest.mark.asyncio
    async def test_semantic_search_ignores_tenant_id_when_isolation_disabled(
        self,
    ) -> None:
        """GIVEN DynamicContextLoader with multi-tenant isolation DISABLED
        WHEN semantic_search is called WITH tenant_id
        THEN it should still work (tenant_id is ignored)
        """
        mock_result = MagicMock()
        mock_result.id = "doc-123"
        mock_result.score = 0.85
        mock_result.payload = {
            "ref_id": "ref-123",
            "ref_type": "document",
            "summary": "Test document",
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
                side_effect=lambda *a, **kw: mock_embedder,
            ),
            patch("mcp_server_langgraph.core.dynamic_context_loader.settings") as mock_settings,
        ):
            mock_settings.enable_multi_tenant_isolation = False  # Disabled
            mock_settings.qdrant_url = "http://localhost:6333"
            mock_settings.qdrant_port = 6333
            mock_settings.qdrant_collection_name = "test_collection"
            mock_settings.embedding_provider = "google"
            mock_settings.embedding_model_name = "text-embedding-004"
            mock_settings.embedding_dimensions = 768
            mock_settings.context_cache_size = 100
            mock_settings.enable_context_encryption = False
            mock_settings.context_retention_days = 30
            mock_settings.enable_auto_deletion = False
            mock_settings.google_api_key = "test-key"
            mock_settings.embedding_task_type = None

            from mcp_server_langgraph.core.dynamic_context_loader import (
                DynamicContextLoader,
            )

            loader = DynamicContextLoader(
                qdrant_url="http://localhost:6333",
                collection_name="test_collection",
            )

            # Should work with tenant_id even when isolation is disabled
            results = await loader.semantic_search(
                query="test query",
                tenant_id="tenant-1",  # Provided but should be ignored
                top_k=5,
            )

            assert len(results) == 1


@pytest.mark.xdist_group(name="dynamic_context_loader_multitenancy")
class TestLoadContextImplTenantIsolation:
    """Tests for tenant isolation in _load_context_impl."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_load_context_impl_validates_tenant_id(self) -> None:
        """GIVEN DynamicContextLoader with multi-tenant isolation enabled
        WHEN _load_context_impl retrieves a document
        THEN it should validate the document belongs to the requesting tenant
        """
        mock_result = MagicMock()
        mock_result.id = "doc-123"
        mock_result.payload = {
            "ref_id": "ref-123",
            "ref_type": "document",
            "summary": "Test document",
            "content": "Full content",
            "token_count": 100,
            "tenant_id": "tenant-1",  # Document belongs to tenant-1
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
                side_effect=lambda *a, **kw: mock_embedder,
            ),
            patch("mcp_server_langgraph.core.dynamic_context_loader.settings") as mock_settings,
        ):
            mock_settings.enable_multi_tenant_isolation = True
            mock_settings.qdrant_url = "http://localhost:6333"
            mock_settings.qdrant_port = 6333
            mock_settings.qdrant_collection_name = "test_collection"
            mock_settings.embedding_provider = "google"
            mock_settings.embedding_model_name = "text-embedding-004"
            mock_settings.embedding_dimensions = 768
            mock_settings.context_cache_size = 100
            mock_settings.enable_context_encryption = False
            mock_settings.context_retention_days = 30
            mock_settings.enable_auto_deletion = False
            mock_settings.google_api_key = "test-key"
            mock_settings.embedding_task_type = None

            from mcp_server_langgraph.core.dynamic_context_loader import (
                DynamicContextLoader,
            )

            loader = DynamicContextLoader(
                qdrant_url="http://localhost:6333",
                collection_name="test_collection",
            )

            # Requesting as tenant-1 (correct tenant)
            loaded = await loader._load_context_impl("doc-123", tenant_id="tenant-1")
            assert loaded.reference.ref_id == "ref-123"

    @pytest.mark.asyncio
    async def test_load_context_impl_rejects_wrong_tenant(self) -> None:
        """GIVEN DynamicContextLoader with multi-tenant isolation enabled
        WHEN _load_context_impl retrieves a document belonging to another tenant
        THEN it should raise PermissionError
        """
        mock_result = MagicMock()
        mock_result.id = "doc-123"
        mock_result.payload = {
            "ref_id": "ref-123",
            "ref_type": "document",
            "summary": "Test document",
            "content": "Full content",
            "token_count": 100,
            "tenant_id": "tenant-1",  # Document belongs to tenant-1
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
                side_effect=lambda *a, **kw: mock_embedder,
            ),
            patch("mcp_server_langgraph.core.dynamic_context_loader.settings") as mock_settings,
        ):
            mock_settings.enable_multi_tenant_isolation = True
            mock_settings.qdrant_url = "http://localhost:6333"
            mock_settings.qdrant_port = 6333
            mock_settings.qdrant_collection_name = "test_collection"
            mock_settings.embedding_provider = "google"
            mock_settings.embedding_model_name = "text-embedding-004"
            mock_settings.embedding_dimensions = 768
            mock_settings.context_cache_size = 100
            mock_settings.enable_context_encryption = False
            mock_settings.context_retention_days = 30
            mock_settings.enable_auto_deletion = False
            mock_settings.google_api_key = "test-key"
            mock_settings.embedding_task_type = None

            from mcp_server_langgraph.core.dynamic_context_loader import (
                DynamicContextLoader,
            )

            loader = DynamicContextLoader(
                qdrant_url="http://localhost:6333",
                collection_name="test_collection",
            )

            # Requesting as tenant-2 (wrong tenant)
            with pytest.raises(PermissionError, match="tenant"):
                await loader._load_context_impl("doc-123", tenant_id="tenant-2")
