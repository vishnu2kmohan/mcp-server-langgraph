"""
Tests for Dynamic Context Splitting.

Phase 7 of the Multi-Agent Orchestrator Enhancement Plan.

TDD: Write tests FIRST, then implementation.

Splits large tasks that exceed model context windows into
smaller chunks at semantic boundaries.

Tests cover:
1. TaskChunk data model
2. Feature flags for context splitting
3. ContextSplitter class
4. Semantic boundary detection
5. Integration with ModelRegistry
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    pass



pytestmark = pytest.mark.unit

@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="task_chunk")
class TestTaskChunk:
    """Test TaskChunk data model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_task_chunk_exists(self) -> None:
        """TaskChunk model should exist."""
        from mcp_server_langgraph.agents.context_splitter import TaskChunk

        assert TaskChunk is not None

    def test_task_chunk_has_required_fields(self) -> None:
        """TaskChunk should have content, index, total fields."""
        from mcp_server_langgraph.agents.context_splitter import TaskChunk

        chunk = TaskChunk(
            content="This is a task chunk",
            index=0,
            total=3,
        )

        assert chunk.content == "This is a task chunk"
        assert chunk.index == 0
        assert chunk.total == 3

    def test_task_chunk_optional_fields(self) -> None:
        """TaskChunk should have optional token_count and boundary fields."""
        from mcp_server_langgraph.agents.context_splitter import TaskChunk

        chunk = TaskChunk(
            content="This is a task chunk",
            index=0,
            total=1,
            token_count=50,
            boundary_type="paragraph",
        )

        assert chunk.token_count == 50
        assert chunk.boundary_type == "paragraph"


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="context_split_flags")
class TestContextSplitFeatureFlags:
    """Test feature flags for context splitting."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_enable_dynamic_context_splitting_flag_exists(self) -> None:
        """Feature flags should include enable_dynamic_context_splitting."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        ff = FeatureFlags()
        assert hasattr(ff, "enable_dynamic_context_splitting")

    def test_enable_dynamic_context_splitting_default_true(self) -> None:
        """enable_dynamic_context_splitting should default to True."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        ff = FeatureFlags()
        assert ff.enable_dynamic_context_splitting is True

    def test_context_split_threshold_flag_exists(self) -> None:
        """Feature flags should include context_split_threshold."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        ff = FeatureFlags()
        assert hasattr(ff, "context_split_threshold")

    def test_context_split_threshold_default(self) -> None:
        """context_split_threshold should default to 0.8."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        ff = FeatureFlags()
        assert ff.context_split_threshold == 0.8


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="context_splitter_basic")
class TestContextSplitterBasic:
    """Test ContextSplitter basic functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_context_splitter_exists(self) -> None:
        """ContextSplitter class should exist."""
        from mcp_server_langgraph.agents.context_splitter import ContextSplitter

        assert ContextSplitter is not None

    def test_context_splitter_initialization(self) -> None:
        """ContextSplitter should initialize correctly."""
        from mcp_server_langgraph.agents.context_splitter import ContextSplitter

        splitter = ContextSplitter()
        assert splitter is not None
        assert splitter.model_registry is not None

    def test_context_splitter_has_split_threshold(self) -> None:
        """ContextSplitter should use configurable split threshold."""
        from mcp_server_langgraph.agents.context_splitter import ContextSplitter

        splitter = ContextSplitter(split_threshold=0.7)
        assert splitter.split_threshold == 0.7


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="context_splitter_split")
class TestContextSplitterSplit:
    """Test ContextSplitter split_task functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_split_task_short_returns_single_chunk(self) -> None:
        """Short tasks should return single chunk."""
        from mcp_server_langgraph.agents.context_splitter import ContextSplitter

        splitter = ContextSplitter()
        task = "Analyze this small task."
        chunks = splitter.split_task(task, "claude-opus-4-5-20251101")

        assert len(chunks) == 1
        assert chunks[0].content == task
        assert chunks[0].index == 0
        assert chunks[0].total == 1

    def test_split_task_respects_model_context_limit(self) -> None:
        """split_task should consider model's effective context limit."""
        from mcp_server_langgraph.agents.context_splitter import ContextSplitter

        splitter = ContextSplitter()

        # This is a simulated long task (would need to be very long in practice)
        # For testing, we verify the method exists and handles correctly
        task = "Short task that fits in context."
        chunks = splitter.split_task(task, "claude-opus-4-5-20251101")

        assert len(chunks) >= 1
        # All chunks should have valid indices
        for i, chunk in enumerate(chunks):
            assert chunk.index == i
            assert chunk.total == len(chunks)

    def test_needs_split_returns_false_for_short_task(self) -> None:
        """needs_split should return False for short tasks."""
        from mcp_server_langgraph.agents.context_splitter import ContextSplitter

        splitter = ContextSplitter()
        task = "This is a short task."

        result = splitter.needs_split(task, "claude-opus-4-5-20251101")
        assert result is False

    def test_count_tokens_estimates_correctly(self) -> None:
        """count_tokens should estimate token count."""
        from mcp_server_langgraph.agents.context_splitter import ContextSplitter

        splitter = ContextSplitter()

        # Simple heuristic: ~4 chars per token
        text = "Hello world this is a test."  # 27 chars ~ 7 tokens
        count = splitter.count_tokens(text)

        assert count > 0
        assert count < 20  # Reasonable estimate


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="context_splitter_boundaries")
class TestContextSplitterBoundaries:
    """Test semantic boundary detection."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_find_boundaries_detects_paragraphs(self) -> None:
        """find_boundaries should detect paragraph breaks."""
        from mcp_server_langgraph.agents.context_splitter import ContextSplitter

        splitter = ContextSplitter()
        text = """First paragraph here.

Second paragraph here.

Third paragraph here."""

        boundaries = splitter.find_boundaries(text)

        # Should find paragraph breaks
        assert len(boundaries) >= 2

    def test_find_boundaries_detects_sections(self) -> None:
        """find_boundaries should detect section headers."""
        from mcp_server_langgraph.agents.context_splitter import ContextSplitter

        splitter = ContextSplitter()
        text = """# Section 1
Content for section 1.

## Section 2
Content for section 2.

### Section 3
Content for section 3."""

        boundaries = splitter.find_boundaries(text)

        # Should find section headers as boundaries
        assert len(boundaries) >= 2

    def test_split_at_boundary_preserves_content(self) -> None:
        """Splitting at boundaries should preserve all content."""
        from mcp_server_langgraph.agents.context_splitter import ContextSplitter

        splitter = ContextSplitter()
        text = """First part.

Second part.

Third part."""

        # Simulate splitting (short text won't actually split)
        chunks = splitter.split_task(text, "claude-opus-4-5-20251101")

        # Combine all chunks and verify content preserved
        combined = "".join(c.content for c in chunks)
        # The combined content should contain all original parts
        assert "First part" in combined
        assert "Second part" in combined
        assert "Third part" in combined


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="context_splitter_helpers")
class TestContextSplitterHelpers:
    """Test helper methods."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_effective_limit_uses_registry(self) -> None:
        """get_effective_limit should use ModelRegistry."""
        from mcp_server_langgraph.agents.context_splitter import ContextSplitter

        splitter = ContextSplitter()
        limit = splitter.get_effective_limit("claude-opus-4-5-20251101")

        # Opus effective limit is 130K (65% of 200K)
        assert limit == 130000

    def test_get_split_target_applies_threshold(self) -> None:
        """get_split_target should apply split threshold to effective limit."""
        from mcp_server_langgraph.agents.context_splitter import ContextSplitter

        splitter = ContextSplitter(split_threshold=0.8)
        target = splitter.get_split_target("claude-opus-4-5-20251101")

        # 80% of 130K = 104K
        expected = int(130000 * 0.8)
        assert target == expected
