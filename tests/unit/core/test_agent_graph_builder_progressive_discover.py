"""Tests for progressive discovery in LangGraph context loading.

TDD: These tests define the contract for using progressive_discover
in the load_dynamic_context node for complex queries.

Finding 3.2: progressive_discover() is not used in LangGraph load_dynamic_context.

The fix adds:
1. Query complexity detection
2. Use progressive_discover for complex/multi-entity queries
3. Keep semantic_search for simple queries
"""

from __future__ import annotations

import gc
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="agent_graph_builder_progressive")
class TestQueryComplexityDetection:
    """Tests for query complexity detection."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_is_complex_query_function_exists(self) -> None:
        """Test that is_complex_query function exists in agent_graph_builder."""
        from mcp_server_langgraph.core.agent_graph_builder import is_complex_query

        assert callable(is_complex_query)

    def test_simple_query_returns_false(self) -> None:
        """Test simple queries are not marked as complex."""
        from mcp_server_langgraph.core.agent_graph_builder import is_complex_query

        simple_queries = [
            "What is Python?",
            "How do I create a function?",
            "Tell me about lists",
        ]

        for query in simple_queries:
            assert is_complex_query(query) is False, f"Simple query should not be complex: {query}"

    def test_complex_query_with_multiple_entities_returns_true(self) -> None:
        """Test queries with multiple entities are marked as complex."""
        from mcp_server_langgraph.core.agent_graph_builder import is_complex_query

        complex_queries = [
            "Compare Python and JavaScript for web development and discuss their ecosystems",
            "How do TDD, BDD, and ATDD differ in their approach to testing and documentation?",
            "Explain the relationship between Redis, PostgreSQL, and Qdrant in our architecture",
        ]

        for query in complex_queries:
            assert is_complex_query(query) is True, f"Complex query should be marked complex: {query}"

    def test_complex_query_with_long_text_returns_true(self) -> None:
        """Test long queries are marked as complex (likely multi-faceted)."""
        from mcp_server_langgraph.core.agent_graph_builder import is_complex_query

        long_query = " ".join(["word"] * 50)  # 50 words
        assert is_complex_query(long_query) is True

    def test_complex_query_with_comparison_keywords_returns_true(self) -> None:
        """Test queries with comparison keywords are marked as complex."""
        from mcp_server_langgraph.core.agent_graph_builder import is_complex_query

        comparison_queries = [
            "Compare function A vs function B",
            "What are the differences between X and Y?",
            "Contrast the two approaches",
        ]

        for query in comparison_queries:
            assert is_complex_query(query) is True, f"Comparison query should be complex: {query}"


@pytest.mark.xdist_group(name="agent_graph_builder_progressive")
class TestLoadDynamicContextProgressiveDiscovery:
    """Tests for progressive discovery in load_dynamic_context."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_simple_query_uses_semantic_search(self) -> None:
        """GIVEN a simple query
        WHEN load_dynamic_context runs
        THEN it should use semantic_search (not progressive_discover)
        """
        from langchain_core.messages import HumanMessage

        from mcp_server_langgraph.core.agent_graph_builder import _load_dynamic_context_impl

        mock_loader = MagicMock()
        mock_loader.semantic_search = AsyncMock(return_value=[])
        mock_loader.progressive_discover = AsyncMock(return_value=[])
        mock_loader.load_batch = AsyncMock(return_value=[])
        mock_loader.to_messages = MagicMock(return_value=[])

        state: dict[str, Any] = {
            "messages": [HumanMessage(content="What is Python?")],
            "kb_focus": "all",
        }

        # Patch in the correct module where the import happens
        with patch(
            "mcp_server_langgraph.core.dynamic_context_loader.search_and_load_context",
            new=AsyncMock(return_value=[]),
        ):
            await _load_dynamic_context_impl(state, mock_loader)

        # semantic_search should have been called (via search_and_load_context)
        # progressive_discover should NOT have been called directly
        mock_loader.progressive_discover.assert_not_called()

    @pytest.mark.asyncio
    async def test_complex_query_uses_progressive_discover(self) -> None:
        """GIVEN a complex multi-entity query
        WHEN load_dynamic_context runs with enable_progressive_discovery=True
        THEN it should use progressive_discover
        """
        from langchain_core.messages import HumanMessage

        from mcp_server_langgraph.core.agent_graph_builder import _load_dynamic_context_impl

        mock_loader = MagicMock()
        mock_loader.semantic_search = AsyncMock(return_value=[])
        mock_loader.progressive_discover = AsyncMock(return_value=[])
        mock_loader.load_batch = AsyncMock(return_value=[])
        mock_loader.to_messages = MagicMock(return_value=[])

        state: dict[str, Any] = {
            "messages": [
                HumanMessage(
                    content="Compare Python and JavaScript for web development, "
                    "discussing their ecosystems, frameworks, and performance characteristics"
                )
            ],
            "kb_focus": "all",
        }

        await _load_dynamic_context_impl(
            state,
            mock_loader,
            enable_progressive=True,  # Enable progressive discovery
        )

        # progressive_discover should have been called for complex query
        mock_loader.progressive_discover.assert_called_once()

    @pytest.mark.asyncio
    async def test_progressive_discovery_disabled_by_default(self) -> None:
        """GIVEN a complex query
        WHEN load_dynamic_context runs without enable_progressive=True
        THEN it should use semantic_search (backward compatible)
        """
        from langchain_core.messages import HumanMessage

        from mcp_server_langgraph.core.agent_graph_builder import _load_dynamic_context_impl

        mock_loader = MagicMock()
        mock_loader.semantic_search = AsyncMock(return_value=[])
        mock_loader.progressive_discover = AsyncMock(return_value=[])
        mock_loader.load_batch = AsyncMock(return_value=[])
        mock_loader.to_messages = MagicMock(return_value=[])

        state: dict[str, Any] = {
            "messages": [HumanMessage(content="Compare Python, JavaScript, and Go for microservices")],
            "kb_focus": "all",
        }

        with patch(
            "mcp_server_langgraph.core.dynamic_context_loader.search_and_load_context",
            new=AsyncMock(return_value=[]),
        ):
            await _load_dynamic_context_impl(state, mock_loader)

        # Default should use search_and_load_context (semantic_search)
        mock_loader.progressive_discover.assert_not_called()


@pytest.mark.xdist_group(name="agent_graph_builder_progressive")
class TestProgressiveDiscoveryFeatureFlag:
    """Tests for progressive discovery feature flag."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_feature_flag_exists(self) -> None:
        """Test enable_progressive_context_discovery feature flag exists."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert hasattr(flags, "enable_progressive_context_discovery")
        assert isinstance(flags.enable_progressive_context_discovery, bool)

    def test_feature_flag_defaults_to_false(self) -> None:
        """Test feature flag defaults to False for backward compatibility."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.enable_progressive_context_discovery is False
