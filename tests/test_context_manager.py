"""
Tests for Context Manager (Conversation Compaction)

Tests both unit functionality and integration behavior.
Uses mocking to avoid actual LLM calls for fast execution.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from mcp_server_langgraph.core.context_manager import (
    CompactionResult,
    ContextManager,
    compact_if_needed,
)


@pytest.fixture
def context_manager():
    """Create ContextManager instance for testing."""
    # Mock the settings to avoid loading real config
    mock_settings = MagicMock()
    mock_settings.model_name = "test-model"
    mock_settings.llm_provider = "test-provider"

    # Create context manager with test config
    manager = ContextManager(
        compaction_threshold=1000,  # Lower threshold for testing
        target_after_compaction=500,
        recent_message_count=2,
        settings=mock_settings,
    )

    # Mock the LLM to avoid actual API calls
    manager.llm = AsyncMock()
    manager.llm.ainvoke = AsyncMock(
        return_value=MagicMock(content="Summary: User asked about Python, assistant explained basics.")
    )

    return manager


@pytest.fixture
def short_conversation():
    """Create a short conversation (below threshold)."""
    return [
        HumanMessage(content="Hello"),
        AIMessage(content="Hi! How can I help you?"),
        HumanMessage(content="What is Python?"),
        AIMessage(content="Python is a programming language."),
    ]


@pytest.fixture
def long_conversation():
    """Create a long conversation (above threshold)."""
    messages = []
    # Increase size to ensure > 1000 tokens (threshold in test)
    # Each message ~50 tokens, need 20+ messages or longer content
    for i in range(20):
        messages.append(HumanMessage(content=f"Question {i}: " + "x" * 150))
        messages.append(AIMessage(content=f"Answer {i}: " + "y" * 150))
    return messages


class TestContextManager:
    """Unit tests for ContextManager."""

    def test_initialization(self, context_manager):
        """Test ContextManager initializes with correct config."""
        assert context_manager.compaction_threshold == 1000
        assert context_manager.target_after_compaction == 500
        assert context_manager.recent_message_count == 2

    def test_needs_compaction_short_conversation(self, context_manager, short_conversation):
        """Test that short conversations don't trigger compaction."""
        needs_compaction = context_manager.needs_compaction(short_conversation)
        assert needs_compaction is False

    def test_needs_compaction_long_conversation(self, context_manager, long_conversation):
        """Test that long conversations trigger compaction."""
        needs_compaction = context_manager.needs_compaction(long_conversation)
        assert needs_compaction is True

    @pytest.mark.asyncio
    async def test_compact_conversation_structure(self, context_manager, long_conversation):
        """Test that compaction maintains proper message structure."""
        result = await context_manager.compact_conversation(long_conversation)

        assert isinstance(result, CompactionResult)
        assert result.original_token_count > 0
        assert result.compacted_token_count > 0
        assert result.compacted_token_count < result.original_token_count
        assert result.compression_ratio < 1.0
        assert result.messages_summarized > 0

    @pytest.mark.asyncio
    async def test_compact_conversation_preserves_recent(self, context_manager, long_conversation):
        """Test that compaction preserves recent messages."""
        result = await context_manager.compact_conversation(long_conversation)

        # Should have: summary message + 2 recent messages
        assert len(result.compacted_messages) == 3

        # Last 2 messages should be unchanged
        assert result.compacted_messages[-2].content == long_conversation[-2].content
        assert result.compacted_messages[-1].content == long_conversation[-1].content

        # First message should be summary (SystemMessage)
        assert isinstance(result.compacted_messages[0], SystemMessage)
        assert "Summary" in result.compacted_messages[0].content or "summary" in result.compacted_messages[0].content.lower()

    @pytest.mark.asyncio
    async def test_compact_conversation_with_system_messages(self, context_manager):
        """Test that system messages are preserved during compaction."""
        messages = [
            SystemMessage(content="You are a helpful assistant."),
            HumanMessage(content="Q1: " + "x" * 200),
            AIMessage(content="A1: " + "y" * 200),
            HumanMessage(content="Q2: " + "x" * 200),
            AIMessage(content="A2: " + "y" * 200),
        ]

        result = await context_manager.compact_conversation(messages)

        # Should preserve original system message
        system_messages = [msg for msg in result.compacted_messages if isinstance(msg, SystemMessage)]
        assert len(system_messages) >= 1
        assert any("helpful assistant" in msg.content for msg in system_messages)

    @pytest.mark.asyncio
    async def test_compact_conversation_no_older_messages(self, context_manager):
        """Test compaction with no older messages to summarize."""
        # Create conversation with exactly recent_message_count messages (no older messages)
        # context_manager.recent_message_count = 2
        very_short_conversation = [
            HumanMessage(content="Hello"),
            AIMessage(content="Hi! How can I help?"),
        ]

        result = await context_manager.compact_conversation(very_short_conversation)

        # Should return unchanged if nothing to compact
        assert result.messages_summarized == 0
        assert result.compression_ratio == 1.0
        assert len(result.compacted_messages) == len(very_short_conversation)

    @pytest.mark.asyncio
    async def test_summarization_calls_llm(self, context_manager, long_conversation):
        """Test that summarization actually calls the LLM."""
        await context_manager.compact_conversation(long_conversation)

        # LLM should have been called for summarization
        context_manager.llm.ainvoke.assert_called_once()

        # Check that prompt contains conversation text
        call_args = context_manager.llm.ainvoke.call_args
        prompt = call_args[0][0]
        assert "summarize" in prompt.lower() or "summary" in prompt.lower()

    @pytest.mark.asyncio
    async def test_summarization_fallback_on_error(self, context_manager, long_conversation):
        """Test that summarization has fallback when LLM fails."""
        # Make LLM raise an exception
        context_manager.llm.ainvoke = AsyncMock(side_effect=Exception("LLM API error"))

        # Should not raise, should use fallback
        result = await context_manager.compact_conversation(long_conversation)

        # Should still have compacted messages (with fallback summary)
        assert len(result.compacted_messages) > 0
        assert result.messages_summarized > 0

    def test_message_to_text(self, context_manager):
        """Test conversion of messages to text for token counting."""
        messages = [
            HumanMessage(content="Hello"),
            AIMessage(content="Hi there!"),
            SystemMessage(content="System prompt"),
        ]

        for msg in messages:
            text = context_manager._message_to_text(msg)
            assert isinstance(text, str)
            assert len(text) > 0

    def test_get_role_label(self, context_manager):
        """Test role label extraction from messages."""
        assert context_manager._get_role_label(HumanMessage(content="test")) == "User"
        assert context_manager._get_role_label(AIMessage(content="test")) == "Assistant"
        assert context_manager._get_role_label(SystemMessage(content="test")) == "System"

    def test_extract_key_information(self, context_manager):
        """Test extraction of key information from conversation."""
        messages = [
            HumanMessage(content="We decided to use Python for this project"),
            AIMessage(content="Great choice! We need to install Django."),
            HumanMessage(content="There's an error in the authentication module"),
        ]

        key_info = context_manager.extract_key_information(messages)

        assert "decisions" in key_info
        assert "requirements" in key_info
        assert "issues" in key_info

        # Should detect decision
        assert len(key_info["decisions"]) > 0

        # Should detect requirement
        assert len(key_info["requirements"]) > 0

        # Should detect issue
        assert len(key_info["issues"]) > 0


class TestConvenienceFunctions:
    """Test convenience functions."""

    @pytest.mark.asyncio
    async def test_compact_if_needed_no_compaction(self, short_conversation):
        """Test compact_if_needed doesn't compact short conversations."""
        # Mock ContextManager
        with patch("mcp_server_langgraph.core.context_manager.ContextManager") as MockContextManager:
            mock_manager = MagicMock()
            mock_manager.needs_compaction.return_value = False
            MockContextManager.return_value = mock_manager

            result = await compact_if_needed(short_conversation)

            # Should return unchanged
            assert result == short_conversation
            mock_manager.compact_conversation.assert_not_called()

    @pytest.mark.asyncio
    async def test_compact_if_needed_with_compaction(self, long_conversation):
        """Test compact_if_needed compacts long conversations."""
        # Mock ContextManager
        with patch("mcp_server_langgraph.core.context_manager.ContextManager") as MockContextManager:
            mock_manager = MagicMock()
            mock_manager.needs_compaction.return_value = True

            compacted = long_conversation[:3]  # Simulated compacted result
            mock_result = CompactionResult(
                compacted_messages=compacted,
                original_token_count=1000,
                compacted_token_count=400,
                messages_summarized=10,
                compression_ratio=0.4,
            )
            mock_manager.compact_conversation = AsyncMock(return_value=mock_result)
            MockContextManager.return_value = mock_manager

            result = await compact_if_needed(long_conversation)

            # Should return compacted messages
            assert result == compacted
            mock_manager.compact_conversation.assert_called_once()


@pytest.mark.unit
class TestTokenCounting:
    """Test token counting functionality."""

    def test_token_counting_accuracy(self, context_manager):
        """Test that token counting is reasonably accurate."""
        # Short text
        short_text = "Hello world"
        short_tokens = context_manager.count_tokens(short_text)
        assert short_tokens > 0
        assert short_tokens < 10  # Should be 2-3 tokens

        # Long text
        long_text = "This is a much longer text " * 100
        long_tokens = context_manager.count_tokens(long_text)
        assert long_tokens > short_tokens
        assert long_tokens > 50


@pytest.mark.unit
class TestCompactionResult:
    """Test CompactionResult model."""

    def test_compaction_result_creation(self):
        """Test creating CompactionResult."""
        result = CompactionResult(
            compacted_messages=[HumanMessage(content="test")],
            original_token_count=1000,
            compacted_token_count=500,
            messages_summarized=5,
            compression_ratio=0.5,
        )

        assert len(result.compacted_messages) == 1
        assert result.original_token_count == 1000
        assert result.compacted_token_count == 500
        assert result.messages_summarized == 5
        assert result.compression_ratio == 0.5

    def test_compaction_result_validation(self):
        """Test CompactionResult validation."""
        # Compression ratio should be between 0 and 1
        with pytest.raises(Exception):  # Pydantic validation error
            CompactionResult(
                compacted_messages=[],
                original_token_count=100,
                compacted_token_count=50,
                messages_summarized=0,
                compression_ratio=1.5,  # Invalid: > 1.0
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
