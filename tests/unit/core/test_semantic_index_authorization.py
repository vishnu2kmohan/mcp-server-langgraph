"""
Tests for SemanticIndexManager Authorization.

TDD tests for fine-grained access control on semantic search operations.
Ensures admin, alice, bob personas have appropriate permissions.

RED Phase: These tests define the expected authorization behavior.
GREEN Phase: Implementation will add authorization checks to SemanticIndexManager.

ADR Reference: ADR-0099 Semantic Tool Selection + ADR-0068 OpenFGA ReBAC
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.authorization, pytest.mark.adr0099]


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
    mock_response = MagicMock()
    mock_response.points = []
    client.query_points = AsyncMock(return_value=mock_response)
    return client


@pytest.fixture
def mock_openfga_client() -> AsyncMock:
    """Create a mock OpenFGA client for authorization checks."""
    client = AsyncMock(return_value=None)
    # Default: deny all - tests will configure allowed permissions
    # The actual OpenFGAClient uses check_permission which returns bool directly
    client.check_permission = AsyncMock(return_value=False)
    return client


@pytest.mark.xdist_group(name="semantic_index_authorization")
class TestToolIndexAuthorization:
    """Tests for tool index authorization."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_search_tools_requires_viewer_permission(
        self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock, mock_openfga_client: AsyncMock
    ) -> None:
        """search_tools should check viewer permission on tool_index."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        # Configure: user:bob denied access to tool_index
        mock_openfga_client.check_permission = AsyncMock(return_value=False)

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
        )

        with patch(
            "mcp_server_langgraph.core.semantic_index_manager.get_openfga_client",
            return_value=mock_openfga_client,
        ):
            results = await manager.search_tools(
                query="calculate",
                user_id="user:bob",
                limit=10,
            )

        # Should return empty results when authorization denied
        assert len(results) == 0
        # Should have called OpenFGA check_permission
        mock_openfga_client.check_permission.assert_called()

    @pytest.mark.asyncio
    async def test_search_tools_allowed_with_viewer_permission(
        self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock, mock_openfga_client: AsyncMock
    ) -> None:
        """search_tools should return results when user has viewer permission."""
        from qdrant_client.models import ScoredPoint

        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        # Configure: user:alice allowed access to tool_index
        mock_openfga_client.check_permission = AsyncMock(return_value=True)

        # Configure: mock search results
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

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
        )

        with patch(
            "mcp_server_langgraph.core.semantic_index_manager.get_openfga_client",
            return_value=mock_openfga_client,
        ):
            results = await manager.search_tools(
                query="calculate",
                user_id="user:alice",
                limit=10,
            )

        # Should return results when authorized
        assert len(results) == 1
        assert results[0].name == "calculator"

    @pytest.mark.asyncio
    async def test_search_tools_admin_has_access(
        self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock, mock_openfga_client: AsyncMock
    ) -> None:
        """Admin user should have access to tool_index."""
        from qdrant_client.models import ScoredPoint

        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        # Configure: user:admin allowed (admin relation implies viewer)
        mock_openfga_client.check_permission = AsyncMock(return_value=True)

        mock_qdrant_client.query_points.return_value.points = [
            ScoredPoint(
                id="tool-1",
                version=1,
                score=0.9,
                payload={
                    "tool_id": "tool-1",
                    "name": "admin_tool",
                    "description": "Admin only tool",
                    "category": "admin",
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
            results = await manager.search_tools(
                query="admin",
                user_id="user:admin",
                limit=10,
            )

        assert len(results) == 1
        assert results[0].name == "admin_tool"


@pytest.mark.xdist_group(name="semantic_index_authorization")
class TestSkillIndexAuthorization:
    """Tests for skill index authorization."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_search_skills_requires_viewer_permission(
        self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock, mock_openfga_client: AsyncMock
    ) -> None:
        """search_skills should check viewer permission on skill_index."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        # Configure: user denied
        mock_openfga_client.check_permission = AsyncMock(return_value=False)

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
        )

        with patch(
            "mcp_server_langgraph.core.semantic_index_manager.get_openfga_client",
            return_value=mock_openfga_client,
        ):
            results = await manager.search_skills(
                query="code review",
                user_id="user:bob",
                limit=5,
            )

        # Should return empty results when authorization denied
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_search_skills_allowed_with_permission(
        self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock, mock_openfga_client: AsyncMock
    ) -> None:
        """search_skills should return results when authorized."""
        from qdrant_client.models import ScoredPoint

        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        mock_openfga_client.check_permission = AsyncMock(return_value=True)

        mock_qdrant_client.query_points.return_value.points = [
            ScoredPoint(
                id="skill-1",
                version=1,
                score=0.92,
                payload={
                    "skill_id": "skill-1",
                    "name": "code_review",
                    "description": "Review code",
                    "category": "development",
                    "ref_type": "skill",
                    "scope": "project",
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
            results = await manager.search_skills(
                query="code review",
                user_id="user:alice",
                limit=5,
            )

        assert len(results) == 1
        assert results[0].name == "code_review"


@pytest.mark.xdist_group(name="semantic_index_authorization")
class TestMemoryIndexAuthorization:
    """Tests for memory index authorization - critical for privacy."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_search_memories_own_user_allowed(
        self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock, mock_openfga_client: AsyncMock
    ) -> None:
        """Users can always search their own memories."""
        from qdrant_client.models import ScoredPoint

        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        # User searching own memories - viewer permission on memory_index:alice
        mock_openfga_client.check_permission = AsyncMock(return_value=True)

        mock_qdrant_client.query_points.return_value.points = [
            ScoredPoint(
                id="mem-1",
                version=1,
                score=0.88,
                payload={
                    "memory_id": "mem-1",
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
                query="preferences",
                current_user_id="user:alice",
                search_user_id="user:alice",
                limit=5,
            )

        assert len(results) == 1
        assert results[0].content == "User prefers dark mode"

    @pytest.mark.asyncio
    async def test_search_memories_other_user_denied(
        self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock, mock_openfga_client: AsyncMock
    ) -> None:
        """Users cannot search other users' memories without admin permission."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        # Bob trying to access Alice's memories - denied
        mock_openfga_client.check_permission = AsyncMock(return_value=False)

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
        )

        with patch(
            "mcp_server_langgraph.core.semantic_index_manager.get_openfga_client",
            return_value=mock_openfga_client,
        ):
            results = await manager.search_memories(
                query="preferences",
                current_user_id="user:bob",
                search_user_id="user:alice",  # Trying to access alice's memories
                limit=5,
            )

        # Should return empty - bob cannot access alice's memories
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_search_memories_admin_can_access_others(
        self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock, mock_openfga_client: AsyncMock
    ) -> None:
        """Admin can access other users' memories with admin relation."""
        from qdrant_client.models import ScoredPoint

        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        # Admin accessing Bob's memories - allowed via admin relation
        mock_openfga_client.check_permission = AsyncMock(return_value=True)

        mock_qdrant_client.query_points.return_value.points = [
            ScoredPoint(
                id="mem-bob-1",
                version=1,
                score=0.85,
                payload={
                    "memory_id": "mem-bob-1",
                    "content": "Bob likes Python",
                    "memory_type": "preference",
                    "ref_type": "memory",
                    "scope": "session",
                    "user_id": "user:bob",
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
                query="preferences",
                current_user_id="user:admin",
                search_user_id="user:bob",  # Admin accessing bob's memories
                limit=5,
            )

        # Admin should have access
        assert len(results) == 1
        assert results[0].content == "Bob likes Python"


@pytest.mark.xdist_group(name="semantic_index_authorization")
class TestTenantIsolation:
    """Tests for multi-tenant isolation in semantic search."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_search_tools_validates_tenant_membership(
        self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock, mock_openfga_client: AsyncMock
    ) -> None:
        """Users can only search tools in tenants they belong to."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        # First call: check tool_index:viewer - allowed
        # Second call: check organization:member for other_org - denied
        mock_openfga_client.check_permission = AsyncMock(
            side_effect=[True, False]  # tool_index viewer allowed, organization member denied
        )

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
        )

        with patch(
            "mcp_server_langgraph.core.semantic_index_manager.get_openfga_client",
            return_value=mock_openfga_client,
        ):
            results = await manager.search_tools(
                query="calculate",
                user_id="user:alice",
                tenant_id="organization:competitor",  # Alice not member of this org
                limit=10,
            )

        # Should return empty - user not member of tenant
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_search_tools_allowed_for_tenant_member(
        self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock, mock_openfga_client: AsyncMock
    ) -> None:
        """Users can search tools in their own tenant."""
        from qdrant_client.models import ScoredPoint

        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        # Both checks pass
        mock_openfga_client.check_permission = AsyncMock(return_value=True)

        mock_qdrant_client.query_points.return_value.points = [
            ScoredPoint(
                id="tool-acme-1",
                version=1,
                score=0.9,
                payload={
                    "tool_id": "tool-acme-1",
                    "name": "acme_calculator",
                    "description": "ACME org calculator",
                    "category": "math",
                    "ref_type": "tool",
                    "scope": "session",
                    "tenant_id": "organization:acme",
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
            results = await manager.search_tools(
                query="calculate",
                user_id="user:alice",
                tenant_id="organization:acme",  # Alice is member of acme
                limit=10,
            )

        # Should return results for authorized tenant
        assert len(results) == 1
        assert results[0].name == "acme_calculator"


@pytest.mark.xdist_group(name="semantic_index_authorization")
class TestAuthorizationFailClosed:
    """Tests for fail-closed authorization behavior."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_search_tools_returns_empty_on_openfga_error(
        self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock, mock_openfga_client: AsyncMock
    ) -> None:
        """Search should return empty results if OpenFGA check fails."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        # Simulate OpenFGA connection error
        mock_openfga_client.check_permission = AsyncMock(side_effect=Exception("OpenFGA connection error"))

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
        )

        with patch(
            "mcp_server_langgraph.core.semantic_index_manager.get_openfga_client",
            return_value=mock_openfga_client,
        ):
            results = await manager.search_tools(
                query="calculate",
                user_id="user:alice",
                limit=10,
            )

        # Fail-closed: return empty on authorization errors
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_search_tools_requires_user_id(
        self, mock_embedder: MagicMock, mock_qdrant_client: AsyncMock
    ) -> None:
        """search_tools should require user_id parameter."""
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant_client,
        )

        # Calling without user_id should raise or return empty
        with pytest.raises(TypeError):
            await manager.search_tools(
                query="calculate",
                # Missing user_id - should fail
                limit=10,
            )
