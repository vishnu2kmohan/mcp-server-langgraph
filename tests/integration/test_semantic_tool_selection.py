"""
Integration tests for Semantic Tool Selection.

Tests the end-to-end flow of semantic tool selection, from indexing
tools to dynamic selection during agent graph execution.

Uses mock Qdrant client and embedder for isolated testing.
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.integration


@pytest.fixture
def mock_openfga_client() -> AsyncMock:
    """Create a mock OpenFGA client that always returns True for authorization."""
    client = AsyncMock(return_value=None)
    client.check_permission = AsyncMock(return_value=True)
    return client


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


@pytest.mark.integration
@pytest.mark.xdist_group(name="test_semantic_tool_selection_integration")
class TestSemanticToolSelectionIntegration:
    """Integration tests for semantic tool selection flow."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_semantic_index_manager_indexes_and_searches_tools(
        self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock, mock_openfga_client: AsyncMock
    ) -> None:
        """SemanticIndexManager should index tools and search them."""
        from qdrant_client.models import ScoredPoint

        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager
        from mcp_server_langgraph.tools.semantic_index import ToolIndexEntry

        # Setup mock search results
        mock_qdrant_client.query_points.return_value.points = [
            ScoredPoint(
                id="tool-123",
                version=1,
                score=0.95,
                payload={
                    "tool_id": "tool-123",
                    "name": "calculator",
                    "description": "Perform calculations",
                    "category": "math",
                    "ref_type": "tool",
                    "scope": "session",
                },
                vector=None,
            )
        ]

        # Create manager and index tools
        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
        )

        # Index a tool
        entry = ToolIndexEntry(
            tool_id="builtin:test_tool",
            name="calculator",
            description="Perform calculations",
            category="math",
        )
        await manager.index_tool(entry)

        # Search for tools (with authorization mock)
        with patch(
            "mcp_server_langgraph.core.semantic_index_manager.get_openfga_client",
            return_value=mock_openfga_client,
        ):
            results = await manager.search_tools(
                query="math calculations",
                user_id="user:test_alice",
                limit=5,
            )

        # Verify results
        assert len(results) == 1
        assert results[0].name == "calculator"
        assert results[0].category == "math"

    @pytest.mark.asyncio
    async def test_graph_with_semantic_tool_selection_builds_correctly(self, monkeypatch) -> None:
        """Graph with semantic tool selection should build and have correct nodes."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from mcp_server_langgraph.core.agent_config import AgentConfig
        from mcp_server_langgraph.core.agent_graph_builder import build_agent_graph

        config = AgentConfig(
            enable_semantic_tool_search=True,
            enable_verification=False,
            enable_context_compaction=False,
        )

        graph = build_agent_graph(config)

        # Verify graph structure
        assert graph is not None
        assert "retrieve_tools" in graph.nodes
        assert "router" in graph.nodes
        assert "tools" in graph.nodes
        assert "respond" in graph.nodes

    @pytest.mark.asyncio
    async def test_graph_version_differs_with_semantic_selection(self, monkeypatch) -> None:
        """Graph version should differ when semantic selection is enabled."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from mcp_server_langgraph.core.agent_config import AgentConfig

        config_without = AgentConfig(enable_semantic_tool_search=False)
        config_with = AgentConfig(enable_semantic_tool_search=True)

        # Different topology = different graph versions
        assert config_without.graph_version != config_with.graph_version

    @pytest.mark.asyncio
    async def test_semantic_index_manager_batch_indexing(
        self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock
    ) -> None:
        """SemanticIndexManager should efficiently batch-index multiple tools."""
        mock_embedder.embed_documents.return_value = [
            [0.1] * 384,
            [0.2] * 384,
            [0.3] * 384,
        ]

        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager
        from mcp_server_langgraph.tools.semantic_index import ToolIndexEntry

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
        )

        # Batch index multiple tools
        entries = [
            ToolIndexEntry(
                tool_id=f"builtin:tool_{i}",
                name=f"tool_{i}",
                description=f"Tool {i} description",
                category="test",
            )
            for i in range(3)
        ]

        await manager.index_tools_batch(entries)

        # Verify batch embedding was used
        mock_embedder.embed_documents.assert_called_once()
        mock_qdrant_client.upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_semantic_index_supports_multi_tenant_isolation(
        self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock, mock_openfga_client: AsyncMock
    ) -> None:
        """SemanticIndexManager should support multi-tenant isolation via tenant_id."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
        )

        # Search with tenant_id filter (with authorization mock)
        with patch(
            "mcp_server_langgraph.core.semantic_index_manager.get_openfga_client",
            return_value=mock_openfga_client,
        ):
            await manager.search_tools(
                query="test query",
                user_id="user:test_alice",
                limit=5,
                tenant_id="tenant-abc",
            )

        # Verify tenant filter was applied in search
        call_kwargs = mock_qdrant_client.query_points.call_args.kwargs
        assert "query_filter" in call_kwargs


@pytest.mark.integration
@pytest.mark.xdist_group(name="test_skill_memory_indexing")
class TestSkillAndMemoryIndexing:
    """Integration tests for skill and memory indexing."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_semantic_index_manager_indexes_skills(
        self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock, mock_openfga_client: AsyncMock
    ) -> None:
        """SemanticIndexManager should index and search skills."""
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

        # Index a skill
        entry = SkillIndexEntry(
            skill_id="skill-123",
            name="code_review",
            description="Review code for quality",
            category="development",
        )
        await manager.index_skill(entry)

        # Search for skills (with authorization mock)
        with patch(
            "mcp_server_langgraph.core.semantic_index_manager.get_openfga_client",
            return_value=mock_openfga_client,
        ):
            results = await manager.search_skills(
                query="review my code",
                user_id="user:test_alice",
                limit=5,
            )

        assert len(results) == 1
        assert results[0].name == "code_review"

    @pytest.mark.asyncio
    async def test_semantic_index_manager_indexes_memories(
        self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock, mock_openfga_client: AsyncMock
    ) -> None:
        """SemanticIndexManager should index and search memories."""
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
                    "user_id": "user:test_alice",
                },
                vector=None,
            )
        ]

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
        )

        # Index a memory
        entry = MemoryIndexEntry(
            memory_id="mem-123",
            content="User prefers dark mode",
            memory_type="preference",
            user_id="user:test_alice",
        )
        await manager.index_memory(entry)

        # Search for memories (with authorization mock)
        with patch(
            "mcp_server_langgraph.core.semantic_index_manager.get_openfga_client",
            return_value=mock_openfga_client,
        ):
            results = await manager.search_memories(
                query="what are my preferences",
                current_user_id="user:test_alice",
                search_user_id="user:test_alice",
                limit=5,
            )

        assert len(results) == 1
        assert results[0].content == "User prefers dark mode"
