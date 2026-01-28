"""
Tests for SemanticIndexManager.

TDD tests for the SemanticIndexManager that handles indexing and
semantic search for tools, skills, and memories.

RED Phase: These tests define the expected behavior.
GREEN Phase: Implementation in core/semantic_index_manager.py will make them pass.
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.semantic_search]


@pytest.fixture
def mock_embedder() -> MagicMock:
    """Create a mock embedder that returns consistent embeddings."""
    embedder = MagicMock()
    embedder.embed_query = MagicMock(return_value=[0.1, 0.2, 0.3, 0.4] * 96)  # 384 dims
    embedder.embed_documents = MagicMock(return_value=[[0.1, 0.2, 0.3, 0.4] * 96])
    return embedder


@pytest.fixture
def mock_qdrant_client() -> AsyncMock:
    """Create a mock Qdrant async client."""
    client = AsyncMock(return_value=None)
    client.get_collections = AsyncMock(return_value=MagicMock(collections=[]))
    client.create_collection = AsyncMock(return_value=None)
    client.upsert = AsyncMock(return_value=None)
    # query_points returns response with points attribute (qdrant-client >= 1.7)
    mock_response = MagicMock()
    mock_response.points = []
    client.query_points = AsyncMock(return_value=mock_response)
    return client


@pytest.fixture
def mock_openfga_client() -> AsyncMock:
    """Create a mock OpenFGA client that allows all access."""
    client = AsyncMock(return_value=None)
    # Default: allow all access for basic unit tests
    client.check_permission = AsyncMock(return_value=True)
    return client


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_semantic_index_manager")
class TestSemanticIndexManagerCreation:
    """Tests for SemanticIndexManager initialization."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_semantic_index_manager(self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock) -> None:
        """SemanticIndexManager should be created with embedder and client."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
        )

        assert manager is not None
        assert manager.embedder == mock_embedder
        assert manager.collection_name == "capability_index"

    def test_custom_collection_name(self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock) -> None:
        """SemanticIndexManager should support custom collection name."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
            collection_name="custom_index",
        )

        assert manager.collection_name == "custom_index"


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_semantic_index_manager")
class TestSemanticIndexManagerToolIndexing:
    """Tests for tool indexing functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_index_tool(self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock) -> None:
        """index_tool should store tool with embedding in Qdrant."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager
        from mcp_server_langgraph.tools.semantic_index import ToolIndexEntry

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
        )

        entry = ToolIndexEntry(
            tool_id="builtin:calculator",
            name="calculator",
            description="Perform calculations",
            category="math",
        )

        await manager.index_tool(entry)

        # Verify embedding was generated
        mock_embedder.embed_query.assert_called_once()

        # Verify upsert was called
        mock_qdrant_client.upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_index_tool_with_existing_embedding(self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock) -> None:
        """index_tool should use existing embedding if provided."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager
        from mcp_server_langgraph.tools.semantic_index import ToolIndexEntry

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
        )

        existing_embedding = [0.5] * 384
        entry = ToolIndexEntry(
            tool_id="builtin:search",
            name="search",
            description="Search the web",
            category="search",
            embedding=existing_embedding,
        )

        await manager.index_tool(entry)

        # Embedding should not be regenerated
        mock_embedder.embed_query.assert_not_called()
        mock_qdrant_client.upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_index_tools_batch(self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock) -> None:
        """index_tools_batch should index multiple tools efficiently."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager
        from mcp_server_langgraph.tools.semantic_index import ToolIndexEntry

        mock_embedder.embed_documents.return_value = [[0.1] * 384, [0.2] * 384]

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
        )

        entries = [
            ToolIndexEntry(
                tool_id="builtin:calc",
                name="calc",
                description="Calculator",
                category="math",
            ),
            ToolIndexEntry(
                tool_id="builtin:search",
                name="search",
                description="Web search",
                category="search",
            ),
        ]

        await manager.index_tools_batch(entries)

        # Batch embedding call
        mock_embedder.embed_documents.assert_called_once()
        mock_qdrant_client.upsert.assert_called_once()


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_semantic_index_manager")
class TestSemanticIndexManagerToolSearch:
    """Tests for tool search functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_search_tools_returns_entries(
        self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock, mock_openfga_client: AsyncMock
    ) -> None:
        """search_tools should return ToolIndexEntry list."""
        from qdrant_client.models import ScoredPoint

        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager
        from mcp_server_langgraph.tools.semantic_index import ToolIndexEntry

        # Mock search result
        mock_qdrant_client.query_points.return_value.points = [
            ScoredPoint(
                id="builtin:calculator",
                version=1,
                score=0.95,
                payload={
                    "tool_id": "builtin:calculator",
                    "name": "calculator",
                    "description": "Perform calculations",
                    "category": "math",
                    "ref_type": "tool",
                    "scope": "session",
                },
                vector=None,
            )
        ]

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
        )

        with patch(
            "mcp_server_langgraph.core.semantic_index_manager.get_openfga_client",
            return_value=mock_openfga_client,
        ):
            results = await manager.search_tools(query="math operations", user_id="user:alice", limit=10)

        assert len(results) == 1
        assert isinstance(results[0], ToolIndexEntry)
        assert results[0].name == "calculator"
        assert results[0].tool_id == "builtin:calculator"

    @pytest.mark.asyncio
    async def test_search_tools_with_min_score(
        self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock, mock_openfga_client: AsyncMock
    ) -> None:
        """search_tools should filter by minimum score."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
        )

        with patch(
            "mcp_server_langgraph.core.semantic_index_manager.get_openfga_client",
            return_value=mock_openfga_client,
        ):
            await manager.search_tools(query="test", user_id="user:alice", limit=5, min_score=0.8)

        # Verify search was called with score_threshold
        call_kwargs = mock_qdrant_client.query_points.call_args.kwargs
        assert call_kwargs.get("score_threshold") == 0.8

    @pytest.mark.asyncio
    async def test_search_tools_with_category_filter(
        self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock, mock_openfga_client: AsyncMock
    ) -> None:
        """search_tools should filter by category."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
        )

        with patch(
            "mcp_server_langgraph.core.semantic_index_manager.get_openfga_client",
            return_value=mock_openfga_client,
        ):
            await manager.search_tools(query="test", user_id="user:alice", limit=5, category="math")

        # Verify filter was applied
        call_kwargs = mock_qdrant_client.query_points.call_args.kwargs
        assert "query_filter" in call_kwargs

    @pytest.mark.asyncio
    async def test_search_tools_with_tenant_id(
        self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock, mock_openfga_client: AsyncMock
    ) -> None:
        """search_tools should filter by tenant_id for multi-tenant isolation."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
        )

        with patch(
            "mcp_server_langgraph.core.semantic_index_manager.get_openfga_client",
            return_value=mock_openfga_client,
        ):
            await manager.search_tools(query="test", user_id="user:alice", limit=5, tenant_id="tenant-abc")

        # Verify tenant filter was applied
        call_kwargs = mock_qdrant_client.query_points.call_args.kwargs
        assert "query_filter" in call_kwargs


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_semantic_index_manager")
class TestSemanticIndexManagerSkillIndexing:
    """Tests for skill indexing functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_index_skill(self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock) -> None:
        """index_skill should store skill with embedding in Qdrant."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager
        from mcp_server_langgraph.tools.semantic_index import SkillIndexEntry

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
        )

        entry = SkillIndexEntry(
            skill_id="skill-123",
            name="code_review",
            description="Review code for quality",
            category="development",
        )

        await manager.index_skill(entry)

        mock_embedder.embed_query.assert_called_once()
        mock_qdrant_client.upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_skills(
        self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock, mock_openfga_client: AsyncMock
    ) -> None:
        """search_skills should return SkillIndexEntry list."""
        from qdrant_client.models import ScoredPoint

        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager
        from mcp_server_langgraph.tools.semantic_index import SkillIndexEntry

        mock_qdrant_client.query_points.return_value.points = [
            ScoredPoint(
                id="skill-123",
                version=1,
                score=0.92,
                payload={
                    "skill_id": "skill-123",
                    "name": "code_review",
                    "description": "Review code",
                    "category": "development",
                    "ref_type": "skill",
                    "scope": "project",
                    "tools_needed": ["read_file"],
                },
                vector=None,
            )
        ]

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
        )

        with patch(
            "mcp_server_langgraph.core.semantic_index_manager.get_openfga_client",
            return_value=mock_openfga_client,
        ):
            results = await manager.search_skills(query="review my code", user_id="user:alice", limit=5)

        assert len(results) == 1
        assert isinstance(results[0], SkillIndexEntry)
        assert results[0].name == "code_review"


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_semantic_index_manager")
class TestSemanticIndexManagerMemoryIndexing:
    """Tests for memory indexing functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_index_memory(self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock) -> None:
        """index_memory should store memory with embedding in Qdrant."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager
        from mcp_server_langgraph.tools.semantic_index import MemoryIndexEntry

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
        )

        entry = MemoryIndexEntry(
            memory_id="mem-123",
            content="User prefers dark mode",
            memory_type="preference",
        )

        await manager.index_memory(entry)

        mock_embedder.embed_query.assert_called_once()
        mock_qdrant_client.upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_memories(
        self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock, mock_openfga_client: AsyncMock
    ) -> None:
        """search_memories should return MemoryIndexEntry list."""
        from qdrant_client.models import ScoredPoint

        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager
        from mcp_server_langgraph.tools.semantic_index import MemoryIndexEntry

        mock_qdrant_client.query_points.return_value.points = [
            ScoredPoint(
                id="mem-123",
                version=1,
                score=0.88,
                payload={
                    "memory_id": "mem-123",
                    "content": "User prefers dark mode",
                    "memory_type": "preference",
                    "ref_type": "memory",
                    "scope": "session",
                    "user_id": "user:alice",
                },
                vector=None,
            )
        ]

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
        )

        with patch(
            "mcp_server_langgraph.core.semantic_index_manager.get_openfga_client",
            return_value=mock_openfga_client,
        ):
            results = await manager.search_memories(
                query="what are my preferences",
                current_user_id="user:alice",
                search_user_id="user:alice",
                limit=5,
            )

        assert len(results) == 1
        assert isinstance(results[0], MemoryIndexEntry)
        assert results[0].content == "User prefers dark mode"


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_semantic_index_manager")
class TestSemanticIndexManagerCollectionManagement:
    """Tests for collection initialization and management."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_ensure_collection_creates_if_not_exists(
        self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock
    ) -> None:
        """ensure_collection should create collection if it doesn't exist."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        mock_qdrant_client.get_collections.return_value = MagicMock(collections=[])

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
        )

        await manager.ensure_collection()

        mock_qdrant_client.create_collection.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_collection_skips_if_exists(self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock) -> None:
        """ensure_collection should not create if collection exists."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        # Mock existing collection
        mock_collection = MagicMock()
        mock_collection.name = "capability_index"
        mock_qdrant_client.get_collections.return_value = MagicMock(collections=[mock_collection])

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
        )

        await manager.ensure_collection()

        mock_qdrant_client.create_collection.assert_not_called()


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_semantic_index_tenant_membership")
class TestTenantMembershipDevMode:
    """Tests for _check_tenant_membership dev mode bypass (v26)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_tenant_membership_bypassed_in_dev_mode(
        self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock
    ) -> None:
        """Tenant membership check is bypassed when environment is 'development'."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        # Create mock settings with development environment
        mock_settings = MagicMock(environment="development")

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
            settings=mock_settings,
        )

        # Should return True without calling OpenFGA
        result = await manager._check_tenant_membership(
            user_id="user:alice",
            tenant_id="organization:acme",
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_tenant_membership_fail_closed_in_test_env(
        self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Tenant membership check is NOT bypassed in test environment (fail-closed)."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        # Create mock settings with test environment
        mock_settings = MagicMock(environment="test")

        # Mock get_openfga_client to return None (simulating unavailable)
        monkeypatch.setattr(
            "mcp_server_langgraph.core.semantic_index_manager.get_openfga_client",
            lambda: None,
        )

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
            settings=mock_settings,
        )

        # Should return False (fail-closed, no OpenFGA client)
        result = await manager._check_tenant_membership(
            user_id="user:alice",
            tenant_id="organization:acme",
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_tenant_membership_fail_closed_in_production(
        self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Tenant membership check is NOT bypassed in production environment (fail-closed)."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        # Create mock settings with production environment
        mock_settings = MagicMock(environment="production")

        # Mock get_openfga_client to return None (simulating unavailable)
        monkeypatch.setattr(
            "mcp_server_langgraph.core.semantic_index_manager.get_openfga_client",
            lambda: None,
        )

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
            settings=mock_settings,
        )

        # Should return False (fail-closed, no OpenFGA client)
        result = await manager._check_tenant_membership(
            user_id="user:alice",
            tenant_id="organization:acme",
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_settings_injection_constructor(self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock) -> None:
        """SemanticIndexManager accepts settings parameter for DI."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        mock_settings = MagicMock(environment="production")

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
            settings=mock_settings,
        )

        assert manager._settings is mock_settings
