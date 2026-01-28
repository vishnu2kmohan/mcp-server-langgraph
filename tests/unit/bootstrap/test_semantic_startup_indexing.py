"""
Tests for Semantic Index Startup Tool Indexing.

TDD tests for automatic tool indexing during bootstrap:
1. Index all available tools at startup when semantic search enabled
2. Skip indexing when semantic search disabled
3. Handle indexing errors gracefully (fail-open)
4. Track indexing metrics

RED Phase: These tests define the expected behavior.
GREEN Phase: Implementation will add indexing to bootstrap/semantic.py.
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.bootstrap]


@pytest.mark.xdist_group(name="semantic_startup_indexing")
class TestStartupToolIndexing:
    """Tests for automatic tool indexing at startup."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_init_semantic_indexes_tools_when_enabled(self) -> None:
        """init_semantic should index all tools when semantic tool search is enabled."""
        from mcp_server_langgraph.core.config import Settings

        mock_settings = MagicMock(spec=Settings)
        mock_settings.qdrant_url = "localhost"
        mock_settings.qdrant_port = 6333
        mock_settings.qdrant_collection_name = "test_collection"
        mock_settings.embedding_provider = "local"
        mock_settings.embedding_model_name = "all-MiniLM-L6-v2"
        mock_settings.embedding_dimensions = 384
        mock_settings.auth_cache_warm_entries = []

        mock_manager = AsyncMock(return_value=None)
        mock_manager.ensure_collection = AsyncMock(return_value=None)
        mock_manager.index_tools_batch = AsyncMock(return_value=None)

        # Mock tools
        mock_tool1 = MagicMock()
        mock_tool1.name = "calculator"
        mock_tool1.description = "Perform calculations"
        mock_tool2 = MagicMock()
        mock_tool2.name = "search"
        mock_tool2.description = "Search knowledge base"

        with (
            patch("mcp_server_langgraph.bootstrap.semantic.feature_flags") as mock_ff,
            patch(
                "qdrant_client.AsyncQdrantClient",
            ),
            patch(
                "mcp_server_langgraph.core.dynamic_context_loader._create_embeddings",
            ),
            patch(
                "mcp_server_langgraph.core.semantic_index_manager.SemanticIndexManager",
                return_value=mock_manager,
            ),
            patch(
                "mcp_server_langgraph.bootstrap.semantic.set_semantic_index_manager",
            ),
            patch(
                "mcp_server_langgraph.bootstrap.semantic.get_all_tools",
                return_value=[mock_tool1, mock_tool2],
            ),
        ):
            mock_ff.enable_semantic_tool_search = True
            mock_ff.enable_semantic_skill_search = False
            mock_ff.enable_semantic_memory_search = False

            from mcp_server_langgraph.bootstrap.semantic import init_semantic

            await init_semantic(mock_settings)

            # Verify tools were indexed
            mock_manager.index_tools_batch.assert_called_once()
            call_args = mock_manager.index_tools_batch.call_args
            indexed_tools = call_args[0][0]  # First positional arg
            assert len(indexed_tools) == 2

    @pytest.mark.asyncio
    async def test_init_semantic_skips_tool_indexing_when_tool_search_disabled(self) -> None:
        """init_semantic should skip tool indexing when tool search is disabled."""
        from mcp_server_langgraph.core.config import Settings

        mock_settings = MagicMock(spec=Settings)
        mock_settings.qdrant_url = "localhost"
        mock_settings.qdrant_port = 6333
        mock_settings.qdrant_collection_name = "test_collection"
        mock_settings.embedding_provider = "local"
        mock_settings.embedding_model_name = "all-MiniLM-L6-v2"
        mock_settings.embedding_dimensions = 384
        mock_settings.auth_cache_warm_entries = []

        mock_manager = AsyncMock(return_value=None)
        mock_manager.ensure_collection = AsyncMock(return_value=None)
        mock_manager.index_tools_batch = AsyncMock(return_value=None)

        with (
            patch("mcp_server_langgraph.bootstrap.semantic.feature_flags") as mock_ff,
            patch(
                "qdrant_client.AsyncQdrantClient",
            ),
            patch(
                "mcp_server_langgraph.core.dynamic_context_loader._create_embeddings",
            ),
            patch(
                "mcp_server_langgraph.core.semantic_index_manager.SemanticIndexManager",
                return_value=mock_manager,
            ),
            patch(
                "mcp_server_langgraph.bootstrap.semantic.set_semantic_index_manager",
            ),
            patch(
                "mcp_server_langgraph.bootstrap.semantic.get_all_tools",
            ) as mock_get_tools,
        ):
            # Enable skill search but NOT tool search
            mock_ff.enable_semantic_tool_search = False
            mock_ff.enable_semantic_skill_search = True
            mock_ff.enable_semantic_memory_search = False

            from mcp_server_langgraph.bootstrap.semantic import init_semantic

            await init_semantic(mock_settings)

            # Tool indexing should NOT happen
            mock_manager.index_tools_batch.assert_not_called()
            mock_get_tools.assert_not_called()

    @pytest.mark.asyncio
    async def test_init_semantic_handles_indexing_error_gracefully(self) -> None:
        """init_semantic should continue even if tool indexing fails."""
        from mcp_server_langgraph.core.config import Settings

        mock_settings = MagicMock(spec=Settings)
        mock_settings.qdrant_url = "localhost"
        mock_settings.qdrant_port = 6333
        mock_settings.qdrant_collection_name = "test_collection"
        mock_settings.embedding_provider = "local"
        mock_settings.embedding_model_name = "all-MiniLM-L6-v2"
        mock_settings.embedding_dimensions = 384
        mock_settings.auth_cache_warm_entries = []

        mock_manager = AsyncMock(return_value=None)
        mock_manager.ensure_collection = AsyncMock(return_value=None)
        mock_manager.index_tools_batch = AsyncMock(side_effect=Exception("Qdrant connection failed"))

        mock_tool = MagicMock()
        mock_tool.name = "calculator"
        mock_tool.description = "Perform calculations"

        with (
            patch("mcp_server_langgraph.bootstrap.semantic.feature_flags") as mock_ff,
            patch(
                "qdrant_client.AsyncQdrantClient",
            ),
            patch(
                "mcp_server_langgraph.core.dynamic_context_loader._create_embeddings",
            ),
            patch(
                "mcp_server_langgraph.core.semantic_index_manager.SemanticIndexManager",
                return_value=mock_manager,
            ),
            patch(
                "mcp_server_langgraph.bootstrap.semantic.set_semantic_index_manager",
            ),
            patch(
                "mcp_server_langgraph.bootstrap.semantic.get_all_tools",
                return_value=[mock_tool],
            ),
        ):
            mock_ff.enable_semantic_tool_search = True
            mock_ff.enable_semantic_skill_search = False
            mock_ff.enable_semantic_memory_search = False

            from mcp_server_langgraph.bootstrap.semantic import init_semantic

            # Should not raise, should return state (fail-open)
            result = await init_semantic(mock_settings)
            assert result is not None
            assert result.manager is mock_manager


@pytest.mark.xdist_group(name="semantic_startup_indexing")
class TestToolToIndexEntryConversion:
    """Tests for converting tools to ToolIndexEntry for indexing."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_convert_tool_to_index_entry(self) -> None:
        """Should convert a BaseTool to ToolIndexEntry with proper fields."""
        from mcp_server_langgraph.bootstrap.semantic import _tool_to_index_entry
        from mcp_server_langgraph.tools.semantic_index import ToolCategory

        mock_tool = MagicMock()
        mock_tool.name = "calculator"
        mock_tool.description = "Perform mathematical calculations"

        entry = _tool_to_index_entry(mock_tool)

        assert entry.tool_id == "tool:calculator"
        assert entry.name == "calculator"
        assert entry.description == "Perform mathematical calculations"
        assert entry.category == ToolCategory.OTHER.value

    def test_convert_tool_with_empty_description(self) -> None:
        """Should handle tools with empty or missing descriptions."""
        from mcp_server_langgraph.bootstrap.semantic import _tool_to_index_entry

        mock_tool = MagicMock()
        mock_tool.name = "mystery_tool"
        mock_tool.description = ""

        entry = _tool_to_index_entry(mock_tool)

        assert entry.tool_id == "tool:mystery_tool"
        assert entry.name == "mystery_tool"
        assert entry.description == ""  # Empty is OK


@pytest.mark.xdist_group(name="semantic_startup_indexing")
class TestStartupIndexingMetrics:
    """Tests for startup indexing metrics."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_init_semantic_logs_indexed_count(self) -> None:
        """init_semantic should log the number of tools indexed."""
        from mcp_server_langgraph.core.config import Settings

        mock_settings = MagicMock(spec=Settings)
        mock_settings.qdrant_url = "localhost"
        mock_settings.qdrant_port = 6333
        mock_settings.qdrant_collection_name = "test_collection"
        mock_settings.embedding_provider = "local"
        mock_settings.embedding_model_name = "all-MiniLM-L6-v2"
        mock_settings.embedding_dimensions = 384
        mock_settings.auth_cache_warm_entries = []

        mock_manager = AsyncMock(return_value=None)
        mock_manager.ensure_collection = AsyncMock(return_value=None)
        mock_manager.index_tools_batch = AsyncMock(return_value=None)

        mock_tools = [MagicMock(name=f"tool_{i}", description=f"Tool {i}") for i in range(10)]

        with (
            patch("mcp_server_langgraph.bootstrap.semantic.feature_flags") as mock_ff,
            patch(
                "qdrant_client.AsyncQdrantClient",
            ),
            patch(
                "mcp_server_langgraph.core.dynamic_context_loader._create_embeddings",
            ),
            patch(
                "mcp_server_langgraph.core.semantic_index_manager.SemanticIndexManager",
                return_value=mock_manager,
            ),
            patch(
                "mcp_server_langgraph.bootstrap.semantic.set_semantic_index_manager",
            ),
            patch(
                "mcp_server_langgraph.bootstrap.semantic.get_all_tools",
                return_value=mock_tools,
            ),
            patch("mcp_server_langgraph.bootstrap.semantic.logger") as mock_logger,
        ):
            mock_ff.enable_semantic_tool_search = True
            mock_ff.enable_semantic_skill_search = False
            mock_ff.enable_semantic_memory_search = False

            from mcp_server_langgraph.bootstrap.semantic import init_semantic

            await init_semantic(mock_settings)

            # Verify info log was called with indexed count
            mock_logger.info.assert_called()
            # Check that at least one call mentions indexing
            log_calls = [str(call) for call in mock_logger.info.call_args_list]
            assert any("indexed" in call.lower() or "tool" in call.lower() for call in log_calls)
