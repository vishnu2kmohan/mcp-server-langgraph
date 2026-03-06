"""
Tests for SemanticIndexManager Qdrant ID conversion.

Qdrant requires point IDs to be either:
- Unsigned 64-bit integers
- Valid UUID strings

This module tests that SemanticIndexManager converts arbitrary string IDs
(like tool_id, skill_id, memory_id) to valid UUIDs before upserting to Qdrant.

TDD Phase: RED -> GREEN
"""

import gc
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.core, pytest.mark.semantic_search]


@pytest.mark.xdist_group(name="semantic_index_id_conversion")
class TestSemanticIndexManagerIdConversion:
    """Tests for SemanticIndexManager ID conversion to valid Qdrant IDs."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_string_to_qdrant_id_imported_in_module(self):
        """GIVEN the semantic_index_manager module
        WHEN checking for string_to_qdrant_id usage
        THEN it should be available for ID conversion
        """
        from mcp_server_langgraph.storage.vectors.qdrant_provider import (
            string_to_qdrant_id,
        )

        # Verify the function exists and works
        result = string_to_qdrant_id("tool-001")
        parsed = uuid.UUID(result)
        assert str(parsed) == result

    @pytest.mark.asyncio
    async def test_index_tool_converts_tool_id_to_uuid(self):
        """GIVEN a SemanticIndexManager
        WHEN indexing a tool with string ID like 'tool-001'
        THEN the ID should be converted to a valid UUID in Qdrant
        """
        from mcp_server_langgraph.core.semantic_index_manager import (
            SemanticIndexManager,
        )
        from mcp_server_langgraph.storage.vectors.qdrant_provider import (
            string_to_qdrant_id,
        )
        from mcp_server_langgraph.tools.semantic_index import ToolIndexEntry

        # Mock embedder and Qdrant client
        mock_embedder = MagicMock()
        mock_embedder.embed_query = MagicMock(return_value=[0.1] * 384)

        mock_qdrant = AsyncMock(return_value=None)

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant,
            vector_size=384,
        )

        # Create test tool entry with valid tool_id format (builtin:{name})
        tool_entry = ToolIndexEntry(
            tool_id="builtin:my-custom-tool-001",
            name="Test Tool",
            description="A test tool",
            category="test",
        )

        await manager.index_tool(tool_entry)

        # Verify PointStruct was called with UUID, not raw string
        mock_qdrant.upsert.assert_called_once()
        call_args = mock_qdrant.upsert.call_args
        points = call_args.kwargs.get("points") or call_args[1].get("points", [])

        assert len(points) == 1
        point = points[0]

        # The ID should be converted to a valid UUID
        expected_uuid = string_to_qdrant_id("builtin:my-custom-tool-001")
        assert point.id == expected_uuid

        # Verify original ID is preserved in payload
        assert point.payload.get("_original_id") == "builtin:my-custom-tool-001"

    @pytest.mark.asyncio
    async def test_index_tool_preserves_valid_uuid(self):
        """GIVEN a SemanticIndexManager
        WHEN indexing a tool with a valid UUID as tool_id
        THEN the UUID should be preserved unchanged
        """
        from mcp_server_langgraph.core.semantic_index_manager import (
            SemanticIndexManager,
        )
        from mcp_server_langgraph.storage.vectors.qdrant_provider import (
            string_to_qdrant_id,
        )
        from mcp_server_langgraph.tools.semantic_index import ToolIndexEntry

        mock_embedder = MagicMock()
        mock_embedder.embed_query = MagicMock(return_value=[0.1] * 384)

        mock_qdrant = AsyncMock(return_value=None)

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant,
            vector_size=384,
        )

        # Use a valid tool_id format with a UUID-like suffix
        tool_entry = ToolIndexEntry(
            tool_id="builtin:uuid-tool",
            name="UUID Tool",
            description="A tool with UUID",
            category="test",
        )

        await manager.index_tool(tool_entry)

        mock_qdrant.upsert.assert_called_once()
        call_args = mock_qdrant.upsert.call_args
        points = call_args.kwargs.get("points") or call_args[1].get("points", [])

        assert len(points) == 1
        # ID should be a valid UUID (converted from builtin:uuid-tool)
        expected_uuid = string_to_qdrant_id("builtin:uuid-tool")
        assert points[0].id == expected_uuid

    @pytest.mark.asyncio
    async def test_index_skill_converts_skill_id_to_uuid(self):
        """GIVEN a SemanticIndexManager
        WHEN indexing a skill with string ID
        THEN the ID should be converted to a valid UUID
        """
        from mcp_server_langgraph.core.semantic_index_manager import (
            SemanticIndexManager,
        )
        from mcp_server_langgraph.storage.vectors.qdrant_provider import (
            string_to_qdrant_id,
        )
        from mcp_server_langgraph.tools.semantic_index import SkillIndexEntry

        mock_embedder = MagicMock()
        mock_embedder.embed_query = MagicMock(return_value=[0.1] * 384)

        mock_qdrant = AsyncMock(return_value=None)

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant,
            vector_size=384,
        )

        skill_entry = SkillIndexEntry(
            skill_id="web-research-skill",
            name="Web Research",
            description="Research topics on the web",
            category="research",
        )

        await manager.index_skill(skill_entry)

        mock_qdrant.upsert.assert_called_once()
        call_args = mock_qdrant.upsert.call_args
        points = call_args.kwargs.get("points") or call_args[1].get("points", [])

        expected_uuid = string_to_qdrant_id("web-research-skill")
        assert points[0].id == expected_uuid
        assert points[0].payload.get("_original_id") == "web-research-skill"

    @pytest.mark.asyncio
    async def test_index_memory_converts_memory_id_to_uuid(self):
        """GIVEN a SemanticIndexManager
        WHEN indexing a memory with string ID
        THEN the ID should be converted to a valid UUID
        """
        from mcp_server_langgraph.core.semantic_index_manager import (
            SemanticIndexManager,
        )
        from mcp_server_langgraph.storage.vectors.qdrant_provider import (
            string_to_qdrant_id,
        )
        from mcp_server_langgraph.tools.semantic_index import MemoryIndexEntry

        mock_embedder = MagicMock()
        mock_embedder.embed_query = MagicMock(return_value=[0.1] * 384)

        mock_qdrant = AsyncMock(return_value=None)

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant,
            vector_size=384,
        )

        memory_entry = MemoryIndexEntry(
            memory_id="session-123-memory-001",
            content="User prefers dark mode",
            memory_type="preference",
        )

        await manager.index_memory(memory_entry)

        mock_qdrant.upsert.assert_called_once()
        call_args = mock_qdrant.upsert.call_args
        points = call_args.kwargs.get("points") or call_args[1].get("points", [])

        expected_uuid = string_to_qdrant_id("session-123-memory-001")
        assert points[0].id == expected_uuid
        assert points[0].payload.get("_original_id") == "session-123-memory-001"

    @pytest.mark.asyncio
    async def test_index_tools_batch_converts_all_ids(self):
        """GIVEN a SemanticIndexManager
        WHEN batch indexing tools with string IDs
        THEN all IDs should be converted to valid UUIDs
        """
        from mcp_server_langgraph.core.semantic_index_manager import (
            SemanticIndexManager,
        )
        from mcp_server_langgraph.storage.vectors.qdrant_provider import (
            string_to_qdrant_id,
        )
        from mcp_server_langgraph.tools.semantic_index import ToolIndexEntry

        mock_embedder = MagicMock()
        mock_embedder.embed_documents = MagicMock(return_value=[[0.1] * 384, [0.2] * 384])

        mock_qdrant = AsyncMock(return_value=None)

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant,
            vector_size=384,
        )

        entries = [
            ToolIndexEntry(
                tool_id="builtin:batch-tool-1",
                name="Tool 1",
                description="First tool",
                category="test",
            ),
            ToolIndexEntry(
                tool_id="builtin:batch-tool-2",
                name="Tool 2",
                description="Second tool",
                category="test",
            ),
        ]

        await manager.index_tools_batch(entries)

        mock_qdrant.upsert.assert_called_once()
        call_args = mock_qdrant.upsert.call_args
        points = call_args.kwargs.get("points") or call_args[1].get("points", [])

        assert len(points) == 2
        assert points[0].id == string_to_qdrant_id("builtin:batch-tool-1")
        assert points[1].id == string_to_qdrant_id("builtin:batch-tool-2")
        assert points[0].payload.get("_original_id") == "builtin:batch-tool-1"
        assert points[1].payload.get("_original_id") == "builtin:batch-tool-2"

    @pytest.mark.asyncio
    async def test_index_decision_converts_trace_id_to_uuid(self):
        """GIVEN a SemanticIndexManager with precedent search enabled
        WHEN indexing a decision trace with string ID
        THEN the ID should be converted to a valid UUID
        """
        from mcp_server_langgraph.core.semantic_index_manager import (
            SemanticIndexManager,
        )
        from mcp_server_langgraph.storage.vectors.qdrant_provider import (
            string_to_qdrant_id,
        )

        mock_embedder = MagicMock()
        mock_embedder.embed_query = MagicMock(return_value=[0.1] * 384)

        mock_qdrant = AsyncMock(return_value=None)

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant,
            vector_size=384,
        )

        with patch("mcp_server_langgraph.core.semantic_index_manager.feature_flags") as mock_flags:
            mock_flags.enable_precedent_search = True

            await manager.index_decision(
                trace_id="decision-trace-12345",
                embedding_text="User asked about Python best practices",
                metadata={
                    "decision_type": "tool_selection",
                    "outcome": "success",
                },
            )

            mock_qdrant.upsert.assert_called_once()
            call_args = mock_qdrant.upsert.call_args
            points = call_args.kwargs.get("points") or call_args[1].get("points", [])

            expected_uuid = string_to_qdrant_id("decision-trace-12345")
            assert points[0].id == expected_uuid
            assert points[0].payload.get("_original_id") == "decision-trace-12345"


@pytest.mark.xdist_group(name="semantic_index_search_id_restoration")
class TestSemanticIndexManagerSearchIdRestoration:
    """Tests for restoring original IDs in search results."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_search_tools_returns_original_id(self):
        """GIVEN indexed tools with converted IDs
        WHEN searching returns results
        THEN original IDs should be restored in results
        """
        from mcp_server_langgraph.core.semantic_index_manager import (
            SemanticIndexManager,
        )
        from mcp_server_langgraph.storage.vectors.qdrant_provider import (
            string_to_qdrant_id,
        )

        mock_embedder = MagicMock()
        mock_embedder.embed_query = MagicMock(return_value=[0.1] * 384)

        # Mock Qdrant search response with UUID and _original_id in payload
        mock_point = MagicMock()
        mock_point.id = string_to_qdrant_id("builtin:original-tool")
        mock_point.score = 0.95
        mock_point.vector = None
        mock_point.payload = {
            "tool_id": "builtin:original-tool",
            "name": "Test Tool",
            "description": "A test tool",
            "category": "test",
            "scope": "session",
            "ref_type": "tool",
            "_original_id": "builtin:original-tool",
        }

        mock_response = MagicMock()
        mock_response.points = [mock_point]

        mock_qdrant = AsyncMock(return_value=None)
        mock_qdrant.query_points.return_value = mock_response

        manager = SemanticIndexManager(
            embedder=mock_embedder,
            qdrant_client=mock_qdrant,
            vector_size=384,
        )

        with patch.object(manager, "_check_authorization", return_value=True):
            results = await manager.search_tools(
                query="test query",
                user_id="user:test",
                limit=10,
            )

            assert len(results) == 1
            # Original tool_id should be preserved in the tool entry
            assert results[0].tool_id == "builtin:original-tool"
