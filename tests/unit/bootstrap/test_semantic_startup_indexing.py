"""
Tests for Semantic Index Startup Tool Indexing.

TDD tests for automatic tool indexing during bootstrap:
1. Index all available tools at startup when semantic search enabled
2. Skip indexing when semantic search disabled
3. Handle indexing errors gracefully (fail-open)
4. Track indexing metrics

Architecture (v26):
- init_semantic_manager(): Creates manager, registers singleton
- index_all_tools(): Indexes tools from unified registry (after MCP sync)
- init_semantic(): Backwards-compatible alias for init_semantic_manager()
- ToolIndexEntry.from_langchain_tool(): Factory method for creating index entries
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
        """index_all_tools should index tools from unified registry when enabled."""
        mock_manager = AsyncMock(return_value=None)
        mock_manager.ensure_collection = AsyncMock(return_value=None)
        mock_manager.index_tools_batch = AsyncMock(return_value=None)

        # Mock registered tools from unified registry
        mock_reg1 = MagicMock()
        mock_reg1.name = "calculator"
        mock_reg1.source = "builtin"
        mock_reg1.tool_id = "builtin:calculator"
        mock_reg1.tool = MagicMock()
        mock_reg1.tool.name = "calculator"
        mock_reg1.tool.description = "Perform calculations"

        mock_reg2 = MagicMock()
        mock_reg2.name = "search"
        mock_reg2.source = "builtin"
        mock_reg2.tool_id = "builtin:search"
        mock_reg2.tool = MagicMock()
        mock_reg2.tool.name = "search"
        mock_reg2.tool.description = "Search knowledge base"

        mock_registry = MagicMock()
        mock_registry.get_all.return_value = [mock_reg1, mock_reg2]

        with (
            patch("mcp_server_langgraph.bootstrap.semantic.feature_flags") as mock_ff,
            patch(
                "mcp_server_langgraph.bootstrap.semantic.get_semantic_index_manager",
                side_effect=lambda *a, **kw: mock_manager,
            ),
            patch(
                "mcp_server_langgraph.tools.unified_registry.get_tool_registry",
                side_effect=lambda *a, **kw: mock_registry,
            ),
            patch(
                "mcp_server_langgraph.tools.semantic_index.ToolIndexEntry.from_langchain_tool",
                side_effect=lambda tool, tool_id: MagicMock(name=tool.name, tool_id=tool_id),
            ),
        ):
            mock_ff.enable_semantic_tool_search = True

            from mcp_server_langgraph.bootstrap.semantic import index_all_tools

            await index_all_tools()

            # Verify tools were indexed
            mock_manager.index_tools_batch.assert_called_once()
            call_args = mock_manager.index_tools_batch.call_args
            indexed_tools = call_args[0][0]  # First positional arg
            assert len(indexed_tools) == 2

    @pytest.mark.asyncio
    async def test_init_semantic_skips_tool_indexing_when_tool_search_disabled(self) -> None:
        """index_all_tools should skip indexing when tool search is disabled."""
        mock_manager = AsyncMock(return_value=None)
        mock_manager.index_tools_batch = AsyncMock(return_value=None)

        with (
            patch("mcp_server_langgraph.bootstrap.semantic.feature_flags") as mock_ff,
            patch(
                "mcp_server_langgraph.bootstrap.semantic.get_semantic_index_manager",
                side_effect=lambda *a, **kw: mock_manager,
            ),
        ):
            mock_ff.enable_semantic_tool_search = False

            from mcp_server_langgraph.bootstrap.semantic import index_all_tools

            await index_all_tools()

            # Tool indexing should NOT happen
            mock_manager.index_tools_batch.assert_not_called()

    @pytest.mark.asyncio
    async def test_init_semantic_handles_indexing_error_gracefully(self) -> None:
        """index_all_tools should continue even if tool indexing fails (fail-open)."""
        mock_manager = AsyncMock(return_value=None)
        mock_manager.ensure_collection = AsyncMock(return_value=None)
        mock_manager.index_tools_batch = AsyncMock(side_effect=Exception("Qdrant connection failed"))

        mock_reg = MagicMock()
        mock_reg.name = "calculator"
        mock_reg.source = "builtin"
        mock_reg.tool_id = "builtin:calculator"
        mock_reg.tool = MagicMock()
        mock_reg.tool.name = "calculator"
        mock_reg.tool.description = "Perform calculations"

        mock_registry = MagicMock()
        mock_registry.get_all.return_value = [mock_reg]

        with (
            patch("mcp_server_langgraph.bootstrap.semantic.feature_flags") as mock_ff,
            patch(
                "mcp_server_langgraph.bootstrap.semantic.get_semantic_index_manager",
                side_effect=lambda *a, **kw: mock_manager,
            ),
            patch(
                "mcp_server_langgraph.tools.unified_registry.get_tool_registry",
                side_effect=lambda *a, **kw: mock_registry,
            ),
            patch(
                "mcp_server_langgraph.tools.semantic_index.ToolIndexEntry.from_langchain_tool",
                side_effect=lambda tool, tool_id: MagicMock(name=tool.name, tool_id=tool_id),
            ),
        ):
            mock_ff.enable_semantic_tool_search = True

            from mcp_server_langgraph.bootstrap.semantic import index_all_tools

            # Should not raise (fail-open)
            await index_all_tools()


@pytest.mark.xdist_group(name="semantic_startup_indexing")
class TestToolToIndexEntryConversion:
    """Tests for converting tools to ToolIndexEntry via factory method."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_convert_tool_to_index_entry(self) -> None:
        """Should convert a tool to ToolIndexEntry with proper fields via from_langchain_tool."""
        from mcp_server_langgraph.tools.semantic_index import ToolIndexEntry

        mock_tool = MagicMock()
        mock_tool.name = "calculator"
        mock_tool.description = "Perform mathematical calculations"
        mock_tool.args_schema = None

        entry = ToolIndexEntry.from_langchain_tool(
            mock_tool,
            tool_id="builtin:calculator",
        )

        assert entry.tool_id == "builtin:calculator"
        assert entry.name == "calculator"
        assert entry.description == "Perform mathematical calculations"

    def test_convert_tool_with_empty_description(self) -> None:
        """Should handle tools with empty or missing descriptions."""
        from mcp_server_langgraph.tools.semantic_index import ToolIndexEntry

        mock_tool = MagicMock()
        mock_tool.name = "mystery_tool"
        mock_tool.description = ""
        mock_tool.args_schema = None

        entry = ToolIndexEntry.from_langchain_tool(
            mock_tool,
            tool_id="builtin:mystery_tool",
        )

        assert entry.tool_id == "builtin:mystery_tool"
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
        """index_all_tools should log the number of tools indexed."""
        mock_manager = AsyncMock(return_value=None)
        mock_manager.ensure_collection = AsyncMock(return_value=None)
        mock_manager.index_tools_batch = AsyncMock(return_value=None)

        mock_regs = []
        for i in range(10):
            reg = MagicMock()
            reg.name = f"tool_{i}"
            reg.source = "builtin"
            reg.tool_id = f"builtin:tool_{i}"
            reg.tool = MagicMock()
            reg.tool.name = f"tool_{i}"
            reg.tool.description = f"Tool {i}"
            mock_regs.append(reg)

        mock_registry = MagicMock()
        mock_registry.get_all.return_value = mock_regs

        with (
            patch("mcp_server_langgraph.bootstrap.semantic.feature_flags") as mock_ff,
            patch(
                "mcp_server_langgraph.bootstrap.semantic.get_semantic_index_manager",
                side_effect=lambda *a, **kw: mock_manager,
            ),
            patch(
                "mcp_server_langgraph.tools.unified_registry.get_tool_registry",
                side_effect=lambda *a, **kw: mock_registry,
            ),
            patch(
                "mcp_server_langgraph.tools.semantic_index.ToolIndexEntry.from_langchain_tool",
                side_effect=lambda tool, tool_id: MagicMock(name=tool.name, tool_id=tool_id),
            ),
            patch("mcp_server_langgraph.bootstrap.semantic.logger") as mock_logger,
        ):
            mock_ff.enable_semantic_tool_search = True

            from mcp_server_langgraph.bootstrap.semantic import index_all_tools

            await index_all_tools()

            # Verify info log was called with indexed count
            mock_logger.info.assert_called()
            # Check that at least one call mentions indexing
            log_calls = [str(call) for call in mock_logger.info.call_args_list]
            assert any("indexed" in call.lower() or "tool" in call.lower() for call in log_calls)
