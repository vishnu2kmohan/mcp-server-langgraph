"""
Tests for DynamicContextLoader Extended Reference Types.

TDD tests for new ref_types: tool, skill, memory.

This extends the existing ref_types (conversation, document, tool_usage, file)
to support semantic search for capabilities (tools, skills) and memories.

RED Phase: These tests define the expected behavior.
GREEN Phase: Implementation will add new ref_types to ContextReference.
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_extended_ref_types_model")
class TestContextReferenceExtendedTypes:
    """Tests for ContextReference with extended ref_types."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_context_reference_accepts_tool_ref_type(self) -> None:
        """ContextReference should accept 'tool' as a valid ref_type."""
        from mcp_server_langgraph.core.dynamic_context_loader import ContextReference

        ref = ContextReference(
            ref_id="tool-calculator",
            ref_type="tool",
            summary="Calculator tool for math operations",
            metadata={"tool_id": "tool-calculator", "category": "math"},
        )

        assert ref.ref_type == "tool"
        assert ref.ref_id == "tool-calculator"

    def test_context_reference_accepts_skill_ref_type(self) -> None:
        """ContextReference should accept 'skill' as a valid ref_type."""
        from mcp_server_langgraph.core.dynamic_context_loader import ContextReference

        ref = ContextReference(
            ref_id="skill-code-review",
            ref_type="skill",
            summary="Code review skill for development",
            metadata={"skill_id": "skill-code-review", "category": "development"},
        )

        assert ref.ref_type == "skill"
        assert ref.ref_id == "skill-code-review"

    def test_context_reference_accepts_memory_ref_type(self) -> None:
        """ContextReference should accept 'memory' as a valid ref_type."""
        from mcp_server_langgraph.core.dynamic_context_loader import ContextReference

        ref = ContextReference(
            ref_id="mem-user-preference-001",
            ref_type="memory",
            summary="User prefers dark mode UI",
            metadata={"memory_type": "preference", "user_id": "user-123"},
        )

        assert ref.ref_type == "memory"
        assert ref.ref_id == "mem-user-preference-001"

    def test_context_reference_backward_compatible_with_existing_types(self) -> None:
        """ContextReference should still accept existing ref_types."""
        from mcp_server_langgraph.core.dynamic_context_loader import ContextReference

        # Existing types should still work
        existing_types = ["conversation", "document", "tool_usage", "file"]

        for ref_type in existing_types:
            ref = ContextReference(
                ref_id=f"ref-{ref_type}",
                ref_type=ref_type,
                summary=f"Test {ref_type} reference",
            )
            assert ref.ref_type == ref_type


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_extended_ref_types_loading")
class TestDynamicContextLoaderExtendedTypes:
    """Tests for loading tool, skill, and memory references."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_semantic_search_returns_tool_references(self) -> None:
        """semantic_search should return tool references from Qdrant."""
        mock_result = MagicMock()
        mock_result.id = "tool-calc-123"
        mock_result.score = 0.92
        mock_result.payload = {
            "ref_id": "tool-calc-123",
            "ref_type": "tool",
            "summary": "Calculator for math operations",
            "text": "Calculator tool description...",
            "metadata": {"tool_id": "calculator", "category": "math"},
        }

        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value=[mock_result])
        mock_client.get_collections = AsyncMock(return_value=MagicMock(collections=[MagicMock(name="test")]))

        mock_embedder = MagicMock()
        mock_embedder.embed_query = MagicMock(return_value=[0.1] * 768)

        with (
            patch(
                "mcp_server_langgraph.core.dynamic_context_loader.get_shared_async_qdrant_client",
                new=AsyncMock(return_value=mock_client),
            ),
            patch(
                "mcp_server_langgraph.core.dynamic_context_loader._create_embeddings",
                return_value=mock_embedder,
            ),
        ):
            from mcp_server_langgraph.core.dynamic_context_loader import (
                DynamicContextLoader,
            )

            loader = DynamicContextLoader(
                qdrant_url="http://localhost:6333",
                collection_name="test",
            )

            results = await loader.semantic_search(query="math calculation", top_k=5)

            assert len(results) == 1
            assert results[0].ref_type == "tool"
            assert results[0].ref_id == "tool-calc-123"

    @pytest.mark.asyncio
    async def test_semantic_search_returns_skill_references(self) -> None:
        """semantic_search should return skill references from Qdrant."""
        mock_result = MagicMock()
        mock_result.id = "skill-review-456"
        mock_result.score = 0.88
        mock_result.payload = {
            "ref_id": "skill-review-456",
            "ref_type": "skill",
            "summary": "Code review skill",
            "text": "Skill for reviewing code quality...",
            "metadata": {"skill_id": "code_review", "category": "development"},
        }

        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value=[mock_result])
        mock_client.get_collections = AsyncMock(return_value=MagicMock(collections=[MagicMock(name="test")]))

        mock_embedder = MagicMock()
        mock_embedder.embed_query = MagicMock(return_value=[0.1] * 768)

        with (
            patch(
                "mcp_server_langgraph.core.dynamic_context_loader.get_shared_async_qdrant_client",
                new=AsyncMock(return_value=mock_client),
            ),
            patch(
                "mcp_server_langgraph.core.dynamic_context_loader._create_embeddings",
                return_value=mock_embedder,
            ),
        ):
            from mcp_server_langgraph.core.dynamic_context_loader import (
                DynamicContextLoader,
            )

            loader = DynamicContextLoader(
                qdrant_url="http://localhost:6333",
                collection_name="test",
            )

            results = await loader.semantic_search(query="review code", top_k=5)

            assert len(results) == 1
            assert results[0].ref_type == "skill"
            assert results[0].ref_id == "skill-review-456"

    @pytest.mark.asyncio
    async def test_semantic_search_returns_memory_references(self) -> None:
        """semantic_search should return memory references from Qdrant."""
        mock_result = MagicMock()
        mock_result.id = "mem-789"
        mock_result.score = 0.95
        mock_result.payload = {
            "ref_id": "mem-789",
            "ref_type": "memory",
            "summary": "User prefers dark mode",
            "text": "User expressed preference for dark mode UI theme",
            "metadata": {"memory_type": "preference", "user_id": "user-123"},
        }

        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value=[mock_result])
        mock_client.get_collections = AsyncMock(return_value=MagicMock(collections=[MagicMock(name="test")]))

        mock_embedder = MagicMock()
        mock_embedder.embed_query = MagicMock(return_value=[0.1] * 768)

        with (
            patch(
                "mcp_server_langgraph.core.dynamic_context_loader.get_shared_async_qdrant_client",
                new=AsyncMock(return_value=mock_client),
            ),
            patch(
                "mcp_server_langgraph.core.dynamic_context_loader._create_embeddings",
                return_value=mock_embedder,
            ),
        ):
            from mcp_server_langgraph.core.dynamic_context_loader import (
                DynamicContextLoader,
            )

            loader = DynamicContextLoader(
                qdrant_url="http://localhost:6333",
                collection_name="test",
            )

            results = await loader.semantic_search(query="user preferences", top_k=5)

            assert len(results) == 1
            assert results[0].ref_type == "memory"
            assert results[0].ref_id == "mem-789"


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_extended_ref_types_filter")
class TestSemanticSearchRefTypeFiltering:
    """Tests for filtering semantic search by ref_type."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_semantic_search_with_tool_ref_type_filter(self) -> None:
        """semantic_search should support filtering by tool ref_type."""
        mock_result = MagicMock()
        mock_result.id = "tool-123"
        mock_result.score = 0.9
        mock_result.payload = {
            "ref_id": "tool-123",
            "ref_type": "tool",
            "summary": "Calculator tool",
            "text": "Tool description",
        }

        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value=[mock_result])
        mock_client.get_collections = AsyncMock(return_value=MagicMock(collections=[MagicMock(name="test")]))

        mock_embedder = MagicMock()
        mock_embedder.embed_query = MagicMock(return_value=[0.1] * 768)

        with (
            patch(
                "mcp_server_langgraph.core.dynamic_context_loader.get_shared_async_qdrant_client",
                new=AsyncMock(return_value=mock_client),
            ),
            patch(
                "mcp_server_langgraph.core.dynamic_context_loader._create_embeddings",
                return_value=mock_embedder,
            ),
        ):
            from mcp_server_langgraph.core.dynamic_context_loader import (
                DynamicContextLoader,
            )

            loader = DynamicContextLoader(
                qdrant_url="http://localhost:6333",
                collection_name="test",
            )

            # Call semantic_search with ref_type filter
            results = await loader.semantic_search(query="math", top_k=5, ref_types=["tool"])

            # Verify the filter was applied in the search call
            mock_client.search.assert_called_once()
            call_kwargs = mock_client.search.call_args.kwargs
            assert "query_filter" in call_kwargs

            # Should return results
            assert len(results) == 1
            assert results[0].ref_type == "tool"

    @pytest.mark.asyncio
    async def test_semantic_search_with_multiple_ref_type_filter(self) -> None:
        """semantic_search should support filtering by multiple ref_types."""
        mock_results = [
            MagicMock(
                id="tool-1",
                score=0.9,
                payload={
                    "ref_id": "tool-1",
                    "ref_type": "tool",
                    "summary": "Tool 1",
                    "text": "Tool",
                },
            ),
            MagicMock(
                id="skill-1",
                score=0.85,
                payload={
                    "ref_id": "skill-1",
                    "ref_type": "skill",
                    "summary": "Skill 1",
                    "text": "Skill",
                },
            ),
        ]

        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value=mock_results)
        mock_client.get_collections = AsyncMock(return_value=MagicMock(collections=[MagicMock(name="test")]))

        mock_embedder = MagicMock()
        mock_embedder.embed_query = MagicMock(return_value=[0.1] * 768)

        with (
            patch(
                "mcp_server_langgraph.core.dynamic_context_loader.get_shared_async_qdrant_client",
                new=AsyncMock(return_value=mock_client),
            ),
            patch(
                "mcp_server_langgraph.core.dynamic_context_loader._create_embeddings",
                return_value=mock_embedder,
            ),
        ):
            from mcp_server_langgraph.core.dynamic_context_loader import (
                DynamicContextLoader,
            )

            loader = DynamicContextLoader(
                qdrant_url="http://localhost:6333",
                collection_name="test",
            )

            # Call with multiple ref_types
            results = await loader.semantic_search(query="capabilities", top_k=5, ref_types=["tool", "skill"])

            # Should return both types
            assert len(results) == 2
            ref_types = {r.ref_type for r in results}
            assert ref_types == {"tool", "skill"}


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_extended_ref_types_constants")
class TestRefTypeConstants:
    """Tests for ref_type constants."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_valid_ref_types_constant_exists(self) -> None:
        """VALID_REF_TYPES constant should exist and include all types."""
        from mcp_server_langgraph.core.dynamic_context_loader import VALID_REF_TYPES

        expected_types = {
            "conversation",
            "document",
            "tool_usage",
            "file",
            "tool",
            "skill",
            "memory",
        }
        assert set(VALID_REF_TYPES) == expected_types

    def test_capability_ref_types_constant_exists(self) -> None:
        """CAPABILITY_REF_TYPES constant should exist for tool/skill lookup."""
        from mcp_server_langgraph.core.dynamic_context_loader import CAPABILITY_REF_TYPES

        expected_types = {"tool", "skill"}
        assert set(CAPABILITY_REF_TYPES) == expected_types
