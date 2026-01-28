"""
Unit tests for Semantic Index Manager decision trace integration.

TDD RED Phase: Tests for decision trace indexing and precedent search
in core/semantic_index_manager.py.

Tests:
- DECISION_TRACE_COLLECTION constant
- ensure_decision_collection method
- index_decision method
- search_precedents method
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.semantic_search]


@pytest.fixture
def mock_embedder():
    """Create a mock embedder."""
    embedder = MagicMock()
    embedder.embed_query = MagicMock(return_value=[0.1] * 384)
    embedder.embed_documents = MagicMock(return_value=[[0.1] * 384])
    return embedder


@pytest.fixture
def mock_qdrant_client():
    """Create a mock Qdrant client."""
    client = AsyncMock(return_value=None)
    client.get_collections = AsyncMock(return_value=MagicMock(collections=[]))
    client.create_collection = AsyncMock(return_value=None)
    client.upsert = AsyncMock(return_value=None)

    # Mock query_points response
    mock_response = MagicMock()
    mock_response.points = []
    client.query_points = AsyncMock(return_value=mock_response)
    return client


@pytest.fixture
def semantic_manager(mock_embedder, mock_qdrant_client):
    """Create a SemanticIndexManager instance."""
    from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

    return SemanticIndexManager(
        embedder=mock_embedder,
        qdrant_client=mock_qdrant_client,
        auth_cache_ttl_seconds=0,  # Disable caching for tests
    )


@pytest.mark.xdist_group(name="test_semantic_index_decisions")
class TestDecisionTraceCollectionConstant:
    """Tests for DECISION_TRACE_COLLECTION constant."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_decision_trace_collection_constant_exists(self) -> None:
        """DECISION_TRACE_COLLECTION constant should exist."""
        from mcp_server_langgraph.core.semantic_index_manager import (
            DECISION_TRACE_COLLECTION,
        )

        assert DECISION_TRACE_COLLECTION is not None

    def test_decision_trace_collection_value(self) -> None:
        """DECISION_TRACE_COLLECTION should be 'decision_traces'."""
        from mcp_server_langgraph.core.semantic_index_manager import (
            DECISION_TRACE_COLLECTION,
        )

        assert DECISION_TRACE_COLLECTION == "decision_traces"


@pytest.mark.xdist_group(name="test_semantic_index_decisions")
class TestEnsureDecisionCollection:
    """Tests for ensure_decision_collection method."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_ensure_decision_collection_method_exists(self, semantic_manager) -> None:
        """ensure_decision_collection method should exist."""
        assert hasattr(semantic_manager, "ensure_decision_collection")
        assert callable(semantic_manager.ensure_decision_collection)

    @pytest.mark.asyncio
    async def test_ensure_decision_collection_creates_collection(self, semantic_manager, mock_qdrant_client) -> None:
        """ensure_decision_collection should create collection if not exists."""
        with patch("mcp_server_langgraph.core.semantic_index_manager.feature_flags") as mock_flags:
            mock_flags.enable_precedent_search = True

            await semantic_manager.ensure_decision_collection()

            mock_qdrant_client.create_collection.assert_called_once()
            call_kwargs = mock_qdrant_client.create_collection.call_args
            assert call_kwargs.kwargs["collection_name"] == "decision_traces"

    @pytest.mark.asyncio
    async def test_ensure_decision_collection_skips_when_disabled(self, semantic_manager, mock_qdrant_client) -> None:
        """ensure_decision_collection should do nothing when feature disabled."""
        with patch("mcp_server_langgraph.core.semantic_index_manager.feature_flags") as mock_flags:
            mock_flags.enable_precedent_search = False

            await semantic_manager.ensure_decision_collection()

            mock_qdrant_client.create_collection.assert_not_called()


@pytest.mark.xdist_group(name="test_semantic_index_decisions")
class TestIndexDecision:
    """Tests for index_decision method."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_index_decision_method_exists(self, semantic_manager) -> None:
        """index_decision method should exist."""
        assert hasattr(semantic_manager, "index_decision")
        assert callable(semantic_manager.index_decision)

    @pytest.mark.asyncio
    async def test_index_decision_upserts_to_qdrant(self, semantic_manager, mock_qdrant_client, mock_embedder) -> None:
        """index_decision should upsert point to Qdrant."""
        with patch("mcp_server_langgraph.core.semantic_index_manager.feature_flags") as mock_flags:
            mock_flags.enable_precedent_search = True

            await semantic_manager.index_decision(
                trace_id="trace-123",
                embedding_text="deploy application to kubernetes",
                metadata={
                    "decision_type": "tool_selection",
                    "outcome": "success",
                    "session_id": "session-456",
                    "user_id": "user:alice",
                    "organization_id": "org:acme",
                },
            )

            mock_qdrant_client.upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_index_decision_skips_when_disabled(self, semantic_manager, mock_qdrant_client) -> None:
        """index_decision should do nothing when feature disabled."""
        with patch("mcp_server_langgraph.core.semantic_index_manager.feature_flags") as mock_flags:
            mock_flags.enable_precedent_search = False

            await semantic_manager.index_decision(
                trace_id="trace-123",
                embedding_text="test query",
                metadata={},
            )

            mock_qdrant_client.upsert.assert_not_called()

    @pytest.mark.asyncio
    async def test_index_decision_uses_decision_trace_collection(self, semantic_manager, mock_qdrant_client) -> None:
        """index_decision should upsert to decision_traces collection."""
        with patch("mcp_server_langgraph.core.semantic_index_manager.feature_flags") as mock_flags:
            mock_flags.enable_precedent_search = True

            await semantic_manager.index_decision(
                trace_id="trace-789",
                embedding_text="test embedding text",
                metadata={"decision_type": "routing"},
            )

            call_kwargs = mock_qdrant_client.upsert.call_args
            assert call_kwargs.kwargs["collection_name"] == "decision_traces"


@pytest.mark.xdist_group(name="test_semantic_index_decisions")
class TestSearchPrecedents:
    """Tests for search_precedents method."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_search_precedents_method_exists(self, semantic_manager) -> None:
        """search_precedents method should exist."""
        assert hasattr(semantic_manager, "search_precedents")
        assert callable(semantic_manager.search_precedents)

    @pytest.mark.asyncio
    async def test_search_precedents_returns_list(self, semantic_manager) -> None:
        """search_precedents should return list of results."""
        with patch("mcp_server_langgraph.core.semantic_index_manager.feature_flags") as mock_flags:
            mock_flags.enable_precedent_search = True

            results = await semantic_manager.search_precedents(
                query="deploy to kubernetes",
                user_id="user:alice",
                organization_id="org:acme",
                limit=10,
            )

            assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_precedents_returns_empty_when_disabled(self, semantic_manager) -> None:
        """search_precedents should return empty list when feature disabled."""
        with patch("mcp_server_langgraph.core.semantic_index_manager.feature_flags") as mock_flags:
            mock_flags.enable_precedent_search = False

            results = await semantic_manager.search_precedents(
                query="test query",
                user_id="user:alice",
                organization_id="org:acme",
            )

            assert results == []

    @pytest.mark.asyncio
    async def test_search_precedents_queries_qdrant(self, semantic_manager, mock_qdrant_client) -> None:
        """search_precedents should query Qdrant with filters."""
        with patch("mcp_server_langgraph.core.semantic_index_manager.feature_flags") as mock_flags:
            mock_flags.enable_precedent_search = True
            mock_flags.precedent_search_min_score = 0.5

            await semantic_manager.search_precedents(
                query="deploy application",
                user_id="user:alice",
                organization_id="org:acme",
                limit=5,
            )

            mock_qdrant_client.query_points.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_precedents_filters_by_organization(self, semantic_manager, mock_qdrant_client) -> None:
        """search_precedents should filter by organization_id."""
        with patch("mcp_server_langgraph.core.semantic_index_manager.feature_flags") as mock_flags:
            mock_flags.enable_precedent_search = True

            await semantic_manager.search_precedents(
                query="test",
                user_id="user:alice",
                organization_id="org:acme",
            )

            # Check filter includes organization_id
            call_kwargs = mock_qdrant_client.query_points.call_args
            query_filter = call_kwargs.kwargs.get("query_filter")
            assert query_filter is not None

    @pytest.mark.asyncio
    async def test_search_precedents_with_decision_type_filter(self, semantic_manager, mock_qdrant_client) -> None:
        """search_precedents should filter by decision_type when provided."""
        with patch("mcp_server_langgraph.core.semantic_index_manager.feature_flags") as mock_flags:
            mock_flags.enable_precedent_search = True

            await semantic_manager.search_precedents(
                query="test",
                user_id="user:alice",
                organization_id="org:acme",
                decision_type="routing",
            )

            mock_qdrant_client.query_points.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_precedents_returns_trace_ids_and_scores(self, semantic_manager, mock_qdrant_client) -> None:
        """search_precedents should return trace_ids and scores."""
        # Setup mock response with results
        mock_point = MagicMock()
        mock_point.payload = {
            "trace_id": "trace-abc",
            "decision_type": "routing",
        }
        mock_point.score = 0.85

        mock_response = MagicMock()
        mock_response.points = [mock_point]
        mock_qdrant_client.query_points = AsyncMock(return_value=mock_response)

        with patch("mcp_server_langgraph.core.semantic_index_manager.feature_flags") as mock_flags:
            mock_flags.enable_precedent_search = True

            results = await semantic_manager.search_precedents(
                query="test",
                user_id="user:alice",
                organization_id="org:acme",
            )

            assert len(results) == 1
            assert results[0]["trace_id"] == "trace-abc"
            assert results[0]["score"] == 0.85


@pytest.mark.xdist_group(name="test_semantic_index_decisions")
class TestSemanticIndexDecisionExports:
    """Tests for module exports."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_decision_trace_collection_exported(self) -> None:
        """DECISION_TRACE_COLLECTION should be in __all__."""
        from mcp_server_langgraph.core import semantic_index_manager

        assert "DECISION_TRACE_COLLECTION" in semantic_index_manager.__all__
