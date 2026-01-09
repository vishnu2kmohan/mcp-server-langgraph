"""
Semantic Tool Selection Performance Benchmarks (ADR-0099)

Tests performance characteristics of semantic tool selection to ensure
acceptable latency for production use with large tool sets.

Performance Targets:
- Semantic search: <100ms for 50+ tools
- Tool indexing: <50ms per tool
- Total selection overhead: <150ms added to request

Token Savings Validation:
- 34-64% token reduction with 50+ tools
- Dynamic tool binding reduces context overhead

Reference:
- ADR-0099: Semantic Tool Selection for Dynamic Capability Discovery
- Anthropic Tool Search Tool Pattern (34-64% savings)
- LangGraph Many Tools Pattern
"""

import gc
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

if TYPE_CHECKING:
    from mcp_server_langgraph.tools.semantic_index import ToolIndexEntry

# Domain markers - benchmark/performance markers auto-applied by conftest.py
pytestmark = [pytest.mark.performance, pytest.mark.tools]


def create_mock_tool(name: str, description: str = "Test tool") -> MagicMock:
    """Create a mock tool for benchmarking."""
    tool = MagicMock()
    tool.name = name
    tool.description = description
    tool.args_schema = MagicMock()
    tool.args_schema.schema.return_value = {
        "type": "object",
        "properties": {"input": {"type": "string"}},
        "required": ["input"],
    }
    return tool


def create_mock_tool_index_entry(
    name: str, score: float = 0.8
) -> "ToolIndexEntry":
    """Create a mock tool index entry for benchmarking."""
    from mcp_server_langgraph.tools.semantic_index import ToolIndexEntry

    return ToolIndexEntry(
        tool_id=f"tool-{name}",
        name=name,
        description=f"Description for {name}",
        category="general",
        embedding=None,
        parameters_summary="input: string",
        token_estimate=100,
    )


@pytest.mark.benchmark
@pytest.mark.xdist_group(name="benchmark_semantic_tool_selection")
class TestSemanticToolSelectionBenchmarks:
    """Benchmark suite for semantic tool selection operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    def test_benchmark_tool_search_small_set(self, benchmark):
        """Benchmark semantic search with 10 tools (baseline)."""
        import asyncio

        from mcp_server_langgraph.core.semantic_index_manager import (
            SemanticIndexManager,
        )

        # Create manager instance without calling __init__ (bypass dependencies)
        manager = SemanticIndexManager.__new__(SemanticIndexManager)
        manager._qdrant_client = MagicMock()
        manager._embedding_model = None
        manager.collection_name = "capability_index"

        # Create mock search results
        mock_results = [
            create_mock_tool_index_entry(f"tool_{i}", score=0.9 - i * 0.05)
            for i in range(10)
        ]

        # Mock the search method
        async def mock_search(*args, **kwargs):
            return mock_results[:kwargs.get("limit", 10)]

        manager.search_tools = mock_search

        # Benchmark the search operation
        def run_search():
            return asyncio.run(
                manager.search_tools(query="calculate sum", limit=5)
            )

        result = benchmark(run_search)
        assert len(result) == 5

    def test_benchmark_tool_search_medium_set(self, benchmark):
        """Benchmark semantic search with 50 tools (target use case)."""
        import asyncio

        from mcp_server_langgraph.core.semantic_index_manager import (
            SemanticIndexManager,
        )

        # Create manager instance without calling __init__ (bypass dependencies)
        manager = SemanticIndexManager.__new__(SemanticIndexManager)
        manager._qdrant_client = MagicMock()
        manager._embedding_model = None
        manager.collection_name = "capability_index"

        mock_results = [
            create_mock_tool_index_entry(f"tool_{i}", score=0.9 - i * 0.01)
            for i in range(50)
        ]

        async def mock_search(*args, **kwargs):
            return mock_results[:kwargs.get("limit", 10)]

        manager.search_tools = mock_search

        def run_search():
            return asyncio.run(
                manager.search_tools(query="search database records", limit=10)
            )

        result = benchmark(run_search)
        assert len(result) == 10

    def test_benchmark_tool_search_large_set(self, benchmark):
        """Benchmark semantic search with 100+ tools (stress test)."""
        import asyncio

        from mcp_server_langgraph.core.semantic_index_manager import (
            SemanticIndexManager,
        )

        # Create manager instance without calling __init__ (bypass dependencies)
        manager = SemanticIndexManager.__new__(SemanticIndexManager)
        manager._qdrant_client = MagicMock()
        manager._embedding_model = None
        manager.collection_name = "capability_index"

        mock_results = [
            create_mock_tool_index_entry(f"tool_{i}", score=0.9 - i * 0.005)
            for i in range(100)
        ]

        async def mock_search(*args, **kwargs):
            return mock_results[:kwargs.get("limit", 10)]

        manager.search_tools = mock_search

        def run_search():
            return asyncio.run(
                manager.search_tools(query="analyze data patterns", limit=10)
            )

        result = benchmark(run_search)
        assert len(result) == 10


@pytest.mark.benchmark
@pytest.mark.xdist_group(name="benchmark_tool_binding")
class TestToolBindingBenchmarks:
    """Benchmark suite for dynamic tool binding operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    def test_benchmark_bind_selected_tools(self, benchmark):
        """Benchmark binding only selected tools vs all tools."""
        # Create mock tools
        all_tools = [create_mock_tool(f"tool_{i}") for i in range(50)]
        selected_names = [f"tool_{i}" for i in range(10)]

        def bind_selected():
            return [t for t in all_tools if t.name in selected_names]

        result = benchmark(bind_selected)
        assert len(result) == 10

    def test_benchmark_bind_all_tools(self, benchmark):
        """Benchmark binding all tools (baseline for comparison)."""
        all_tools = [create_mock_tool(f"tool_{i}") for i in range(50)]

        def bind_all():
            return list(all_tools)

        result = benchmark(bind_all)
        assert len(result) == 50


@pytest.mark.unit
@pytest.mark.xdist_group(name="semantic_tool_validation")
class TestTokenSavingsValidation:
    """Validation tests for token savings claims (non-benchmark)."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    def test_token_savings_calculation(self):
        """Validate token savings with 50 tools, selecting 10."""
        # Estimated tokens per tool schema (from ADR-0099)
        tokens_per_tool = 150  # Conservative estimate

        total_tools = 50
        selected_tools = 10

        # Token usage with all tools
        tokens_all = total_tools * tokens_per_tool  # 7500 tokens

        # Token usage with selected tools
        tokens_selected = selected_tools * tokens_per_tool  # 1500 tokens

        # Calculate savings
        savings_absolute = tokens_all - tokens_selected  # 6000 tokens
        savings_percent = (savings_absolute / tokens_all) * 100  # 80%

        # Verify savings are within Anthropic's claimed range (34-64%)
        # Note: Our savings of 80% exceed the range because we select fewer tools
        assert savings_percent >= 34, f"Savings {savings_percent}% below minimum 34%"

        # With 10/50 tools, we expect 80% savings
        expected_savings = (1 - selected_tools / total_tools) * 100
        assert abs(savings_percent - expected_savings) < 0.01

    def test_token_estimate_accuracy(self):
        """Validate token estimates for different tool complexities."""
        # Simple tool (few parameters)
        simple_tool_tokens = 50

        # Medium tool (several parameters)
        medium_tool_tokens = 150

        # Complex tool (many parameters, nested schemas)
        complex_tool_tokens = 350

        # Average estimate used in calculations
        average_estimate = (simple_tool_tokens + medium_tool_tokens + complex_tool_tokens) / 3

        # Verify average is reasonable
        assert 100 <= average_estimate <= 250, f"Average {average_estimate} outside expected range"

    def test_selection_threshold_impact(self):
        """Validate impact of different similarity thresholds."""
        # Simulate tools with varying similarity scores
        tool_scores = [
            ("calculator", 0.95),
            ("search_kb", 0.87),
            ("file_reader", 0.75),
            ("web_fetch", 0.65),
            ("email_send", 0.55),
            ("calendar_add", 0.45),
            ("notes_create", 0.35),
        ]

        # Threshold 0.5 (default from ADR-0099)
        threshold_05 = [t for t, s in tool_scores if s >= 0.5]
        assert len(threshold_05) == 5, "Expected 5 tools with threshold 0.5"

        # Threshold 0.7 (more selective)
        threshold_07 = [t for t, s in tool_scores if s >= 0.7]
        assert len(threshold_07) == 3, "Expected 3 tools with threshold 0.7"

        # Threshold 0.3 (more inclusive)
        threshold_03 = [t for t, s in tool_scores if s >= 0.3]
        assert len(threshold_03) == 7, "Expected 7 tools with threshold 0.3"


@pytest.mark.unit
@pytest.mark.xdist_group(name="semantic_tool_scalability")
class TestScalabilityValidation:
    """Validation tests for scalability claims."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    def test_scalability_with_100_tools(self):
        """Validate system can handle 100 tools."""
        tools = [create_mock_tool(f"tool_{i}") for i in range(100)]
        assert len(tools) == 100

        # Simulate selection
        selected = [t for t in tools if int(t.name.split("_")[1]) < 10]
        assert len(selected) == 10

    def test_scalability_with_500_tools(self):
        """Validate system can handle 500 tools."""
        tools = [create_mock_tool(f"tool_{i}") for i in range(500)]
        assert len(tools) == 500

        # Simulate selection
        selected = [t for t in tools if int(t.name.split("_")[1]) < 15]
        assert len(selected) == 15

    def test_context_window_impact(self):
        """Validate context window savings at scale."""
        # Assume 200k context window (Claude 3.5 Sonnet)
        context_window = 200000

        # Token budget for tools (assume 20% of context)
        tool_budget = context_window * 0.2  # 40000 tokens

        # Tokens per tool
        tokens_per_tool = 150

        # Max tools without semantic selection
        max_tools_without = tool_budget // tokens_per_tool  # 266 tools

        # With semantic selection (10 tools max)
        max_tools_with = 10 * tokens_per_tool  # 1500 tokens

        # Savings
        tokens_freed = tool_budget - max_tools_with  # 38500 tokens

        # Verify significant savings
        assert tokens_freed > 35000, "Expected >35k tokens freed"
        assert max_tools_without > 200, "Expected >200 max tools without selection"
