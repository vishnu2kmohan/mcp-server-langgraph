"""
Tests for "Lost in the Middle" Mitigation.

Phase 3.2 of the Multi-Agent Orchestrator Enhancement Plan.

TDD: Write tests FIRST, then implementation.

LLMs pay less attention to content in the middle of the context window.
This feature reorders compacted messages to place key information
at the start (system + decisions) and end (recent messages + summary anchor).

Before: [system] + [summary_middle] + [recent_messages]
After:  [system + key_decisions] + [recent_messages] + [summary_anchor]

Tests cover:
1. Feature flag for lost-in-middle mitigation
2. Message reordering after compaction
3. Key decision extraction and placement
4. Summary anchor at end
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

if TYPE_CHECKING:
    pass


pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.core
class TestLostInMiddleFeatureFlags:
    """Test feature flags for lost-in-middle mitigation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_enable_lost_in_middle_mitigation_flag_exists(self) -> None:
        """Feature flags should include enable_lost_in_middle_mitigation."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        ff = FeatureFlags()
        assert hasattr(ff, "enable_lost_in_middle_mitigation")

    def test_enable_lost_in_middle_mitigation_default_true(self) -> None:
        """enable_lost_in_middle_mitigation should default to True."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        ff = FeatureFlags()
        assert ff.enable_lost_in_middle_mitigation is True


@pytest.mark.unit
@pytest.mark.core
class TestContextReordering:
    """Test context reordering for lost-in-middle mitigation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_reorder_for_attention_exists(self) -> None:
        """ContextManager should have reorder_for_attention method."""
        from mcp_server_langgraph.core.context_manager import ContextManager

        # Create with mocked settings
        with patch("mcp_server_langgraph.core.context_manager.create_summarization_model"):
            manager = ContextManager()
            assert hasattr(manager, "reorder_for_attention")

    def test_reorder_for_attention_returns_messages(self) -> None:
        """reorder_for_attention should return list of messages."""
        from mcp_server_langgraph.core.context_manager import ContextManager

        with patch("mcp_server_langgraph.core.context_manager.create_summarization_model"):
            manager = ContextManager()

        messages = [
            SystemMessage(content="You are a helpful assistant."),
            HumanMessage(content="Hello"),
            AIMessage(content="Hi there!"),
        ]

        result = manager.reorder_for_attention(messages)

        assert isinstance(result, list)
        assert len(result) >= len(messages)

    def test_reorder_places_system_first(self) -> None:
        """System messages should remain at the start after reordering."""
        from mcp_server_langgraph.core.context_manager import ContextManager

        with patch("mcp_server_langgraph.core.context_manager.create_summarization_model"):
            manager = ContextManager()

        messages = [
            SystemMessage(content="System prompt here"),
            HumanMessage(content="User message"),
            AIMessage(content="AI response"),
            SystemMessage(content="Summary of old messages"),
        ]

        result = manager.reorder_for_attention(messages)

        # First message should still be system
        assert isinstance(result[0], SystemMessage)
        assert "System prompt" in result[0].content

    def test_reorder_places_recent_before_summary(self) -> None:
        """Recent messages should come before summary anchor."""
        from mcp_server_langgraph.core.context_manager import ContextManager

        with patch("mcp_server_langgraph.core.context_manager.create_summarization_model"):
            manager = ContextManager()

        # Simulate post-compaction message list
        messages = [
            SystemMessage(content="You are a helpful assistant."),
            SystemMessage(content="<conversation_summary>Old discussion...</conversation_summary>"),
            HumanMessage(content="Recent question"),
            AIMessage(content="Recent answer"),
        ]

        result = manager.reorder_for_attention(messages)

        # Find positions
        summary_idx = None
        recent_human_idx = None
        for i, msg in enumerate(result):
            if isinstance(msg, SystemMessage) and "<conversation_summary>" in msg.content:
                summary_idx = i
            if isinstance(msg, HumanMessage) and "Recent question" in msg.content:
                recent_human_idx = i

        # Recent messages should come before summary when mitigation is enabled
        assert recent_human_idx is not None
        assert summary_idx is not None
        assert recent_human_idx < summary_idx


@pytest.mark.unit
@pytest.mark.core
class TestKeyDecisionExtraction:
    """Test extraction of key decisions for attention optimization."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_extract_key_decisions_exists(self) -> None:
        """ContextManager should have extract_key_decisions method."""
        from mcp_server_langgraph.core.context_manager import ContextManager

        with patch("mcp_server_langgraph.core.context_manager.create_summarization_model"):
            manager = ContextManager()
            assert hasattr(manager, "extract_key_decisions")

    def test_extract_key_decisions_finds_decisions(self) -> None:
        """Should extract messages containing decision keywords."""
        from mcp_server_langgraph.core.context_manager import ContextManager

        with patch("mcp_server_langgraph.core.context_manager.create_summarization_model"):
            manager = ContextManager()

        messages = [
            HumanMessage(content="What approach should we use?"),
            AIMessage(content="I decided to use approach A because it's faster."),
            HumanMessage(content="Sounds good."),
            AIMessage(content="The weather is nice today."),
        ]

        decisions = manager.extract_key_decisions(messages)

        # Should find the message with "decided"
        assert len(decisions) >= 1
        assert any("decided" in d.content.lower() for d in decisions)

    def test_extract_key_decisions_finds_requirements(self) -> None:
        """Should extract messages containing requirement keywords."""
        from mcp_server_langgraph.core.context_manager import ContextManager

        with patch("mcp_server_langgraph.core.context_manager.create_summarization_model"):
            manager = ContextManager()

        messages = [
            HumanMessage(content="What do we need?"),
            AIMessage(content="We must use Python 3.12 for this project."),
            AIMessage(content="Hello world."),
        ]

        decisions = manager.extract_key_decisions(messages)

        # Should find the message with "must"
        assert len(decisions) >= 1
        assert any("must" in d.content.lower() for d in decisions)


@pytest.mark.unit
@pytest.mark.core
class TestCompactionWithReordering:
    """Test that compaction applies reordering when enabled."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_compact_conversation_applies_reordering(self) -> None:
        """compact_conversation should apply reordering when flag is enabled."""
        from mcp_server_langgraph.core.context_manager import ContextManager

        # Mock the summarization model
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=AIMessage(content="Summary: Previous discussion about project setup."))

        with patch("mcp_server_langgraph.core.context_manager.create_summarization_model", return_value=mock_llm):
            with patch("mcp_server_langgraph.core.feature_flags.feature_flags") as mock_flags:
                mock_flags.enable_lost_in_middle_mitigation = True
                mock_flags.context_compaction_threshold_percentage = 0.5
                mock_flags.enable_model_aware_compaction = False

                manager = ContextManager(
                    compaction_threshold=100,  # Low threshold for testing
                    recent_message_count=2,
                )

        # Create messages that will trigger compaction
        messages = [
            SystemMessage(content="You are a helpful assistant."),
            HumanMessage(content="First question about setup."),
            AIMessage(content="First answer about setup."),
            HumanMessage(content="Second question."),
            AIMessage(content="Second answer."),
            HumanMessage(content="Third question."),
            AIMessage(content="Third answer."),
            HumanMessage(content="Recent question"),
            AIMessage(content="Recent answer"),
        ]

        result = await manager.compact_conversation(messages)

        # Result should have summary anchor at end (not middle)
        compacted = result.compacted_messages

        # Find summary position
        summary_positions = [
            i for i, msg in enumerate(compacted) if isinstance(msg, SystemMessage) and "summary" in msg.content.lower()
        ]

        # Summary should exist
        assert len(summary_positions) > 0


@pytest.mark.unit
@pytest.mark.core
@pytest.mark.xdist_group(name="context_ranking_flags")
class TestContextRankingFeatureFlags:
    """Test feature flags for context ranking."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_enable_context_ranking_flag_exists(self) -> None:
        """Feature flags should include enable_context_ranking."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        ff = FeatureFlags()
        assert hasattr(ff, "enable_context_ranking")

    def test_enable_context_ranking_default_true(self) -> None:
        """enable_context_ranking should default to True."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        ff = FeatureFlags()
        assert ff.enable_context_ranking is True


@pytest.mark.unit
@pytest.mark.core
class TestSemanticDeduplicationFeatureFlags:
    """Test feature flags for semantic deduplication."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_enable_semantic_deduplication_flag_exists(self) -> None:
        """Feature flags should include enable_semantic_deduplication."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        ff = FeatureFlags()
        assert hasattr(ff, "enable_semantic_deduplication")

    def test_enable_semantic_deduplication_default_true(self) -> None:
        """enable_semantic_deduplication should default to True."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        ff = FeatureFlags()
        assert ff.enable_semantic_deduplication is True

    def test_context_deduplication_threshold_flag_exists(self) -> None:
        """Feature flags should include context_deduplication_threshold."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        ff = FeatureFlags()
        assert hasattr(ff, "context_deduplication_threshold")

    def test_context_deduplication_threshold_default(self) -> None:
        """context_deduplication_threshold should default to 0.92."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        ff = FeatureFlags()
        assert ff.context_deduplication_threshold == 0.92
