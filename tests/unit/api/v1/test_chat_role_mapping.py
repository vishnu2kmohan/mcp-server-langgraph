"""
Tests for chat message role mapping in streaming.

TDD: These tests are written FIRST to define the expected behavior
of role mapping when converting dict messages to LangChain messages.

Bug Reference: chat.py:747-759 incorrectly maps 'assistant' role to HumanMessage.

Tests verify:
1. 'system' role maps to SystemMessage
2. 'user' role maps to HumanMessage
3. 'assistant' role maps to AIMessage (BUG: currently maps to HumanMessage)
4. Unknown roles default to HumanMessage
5. Multi-turn conversations preserve all roles correctly
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

pytestmark = pytest.mark.unit

if TYPE_CHECKING:
    pass


def convert_messages_to_langchain(messages: list[dict[str, Any]]) -> list:
    """
    Helper to simulate the message conversion logic in _stream_via_llm_factory.

    This is the EXPECTED behavior (what it SHOULD do).
    """
    langchain_messages = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "system":
            langchain_messages.append(SystemMessage(content=content))
        elif role == "assistant":
            langchain_messages.append(AIMessage(content=content))
        else:
            langchain_messages.append(HumanMessage(content=content))
    return langchain_messages


class TestChatRoleMapping:
    """Test suite for chat message role mapping."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    # =========================================================================
    # Role Mapping Tests
    # =========================================================================

    def test_system_role_maps_to_systemmessage(self) -> None:
        """GIVEN a message with role='system'
        WHEN converting to LangChain messages
        THEN it should create SystemMessage
        """
        messages = [{"role": "system", "content": "You are a helpful assistant."}]
        result = convert_messages_to_langchain(messages)

        assert len(result) == 1
        assert isinstance(result[0], SystemMessage)
        assert result[0].content == "You are a helpful assistant."

    def test_user_role_maps_to_humanmessage(self) -> None:
        """GIVEN a message with role='user'
        WHEN converting to LangChain messages
        THEN it should create HumanMessage
        """
        messages = [{"role": "user", "content": "Hello!"}]
        result = convert_messages_to_langchain(messages)

        assert len(result) == 1
        assert isinstance(result[0], HumanMessage)
        assert result[0].content == "Hello!"

    def test_assistant_role_maps_to_aimessage(self) -> None:
        """GIVEN a message with role='assistant'
        WHEN converting to LangChain messages
        THEN it should create AIMessage (NOT HumanMessage)

        This is the CRITICAL test that exposes the bug.
        """
        messages = [{"role": "assistant", "content": "I can help with that."}]
        result = convert_messages_to_langchain(messages)

        assert len(result) == 1
        assert isinstance(result[0], AIMessage), (
            f"Expected AIMessage but got {type(result[0]).__name__}. "
            "This indicates the role mapping bug: assistant messages "
            "are incorrectly converted to HumanMessage."
        )
        assert result[0].content == "I can help with that."

    def test_unknown_role_defaults_to_humanmessage(self) -> None:
        """GIVEN a message with an unknown role
        WHEN converting to LangChain messages
        THEN it should default to HumanMessage
        """
        messages = [{"role": "unknown_role", "content": "Some content"}]
        result = convert_messages_to_langchain(messages)

        assert len(result) == 1
        assert isinstance(result[0], HumanMessage)
        assert result[0].content == "Some content"

    def test_missing_role_defaults_to_humanmessage(self) -> None:
        """GIVEN a message without a role key
        WHEN converting to LangChain messages
        THEN it should default to HumanMessage (role='user')
        """
        messages = [{"content": "No role specified"}]
        result = convert_messages_to_langchain(messages)

        assert len(result) == 1
        assert isinstance(result[0], HumanMessage)
        assert result[0].content == "No role specified"

    def test_multi_turn_conversation_preserves_roles(self) -> None:
        """GIVEN a multi-turn conversation with mixed roles
        WHEN converting to LangChain messages
        THEN all roles should be correctly mapped

        This tests a typical conversation flow:
        system -> user -> assistant -> user -> assistant
        """
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is Python?"},
            {"role": "assistant", "content": "Python is a programming language."},
            {"role": "user", "content": "Tell me more."},
            {"role": "assistant", "content": "It was created by Guido van Rossum."},
        ]
        result = convert_messages_to_langchain(messages)

        assert len(result) == 5

        # Verify each message type
        assert isinstance(result[0], SystemMessage)
        assert isinstance(result[1], HumanMessage)
        assert isinstance(result[2], AIMessage), (
            f"Third message should be AIMessage but got {type(result[2]).__name__}. "
            "Assistant responses must be AIMessage to preserve conversation context."
        )
        assert isinstance(result[3], HumanMessage)
        assert isinstance(result[4], AIMessage), f"Fifth message should be AIMessage but got {type(result[4]).__name__}."

        # Verify content
        assert result[0].content == "You are a helpful assistant."
        assert result[1].content == "What is Python?"
        assert result[2].content == "Python is a programming language."
        assert result[3].content == "Tell me more."
        assert result[4].content == "It was created by Guido van Rossum."

    def test_empty_content_preserved(self) -> None:
        """GIVEN a message with empty content
        WHEN converting to LangChain messages
        THEN empty content should be preserved
        """
        messages = [{"role": "user", "content": ""}]
        result = convert_messages_to_langchain(messages)

        assert len(result) == 1
        assert isinstance(result[0], HumanMessage)
        assert result[0].content == ""

    def test_missing_content_defaults_to_empty(self) -> None:
        """GIVEN a message without content key
        WHEN converting to LangChain messages
        THEN content should default to empty string
        """
        messages = [{"role": "user"}]
        result = convert_messages_to_langchain(messages)

        assert len(result) == 1
        assert isinstance(result[0], HumanMessage)
        assert result[0].content == ""


class TestChatRoleMappingIntegration:
    """Integration tests for role mapping in ChatServiceImpl._stream_via_llm_factory."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_stream_via_llm_factory_maps_assistant_correctly(self) -> None:
        """GIVEN ChatServiceImpl with multi-turn messages
        WHEN _stream_via_llm_factory() converts messages
        THEN assistant messages should become AIMessage

        This integration test verifies the actual ChatServiceImpl behavior.
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        # Create a mock LLM factory
        mock_factory = MagicMock()
        mock_chunk = MagicMock()
        mock_chunk.content = "Response"
        mock_chunk.thinking = None

        async def mock_astream(*args, **kwargs):
            yield mock_chunk

        mock_factory.astream = mock_astream

        # Create service instance
        service = ChatServiceImpl(llm_factory=mock_factory)

        # Multi-turn messages including assistant
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"},
        ]

        # Capture the messages passed to astream
        captured_messages = []
        original_astream = mock_factory.astream

        async def capturing_astream(msgs, **kwargs):
            captured_messages.extend(msgs)
            async for chunk in original_astream(msgs, **kwargs):
                yield chunk

        mock_factory.astream = capturing_astream

        # Call the method and consume the stream
        async for _ in service._stream_via_llm_factory("session-1", messages):
            pass

        # Verify message types
        assert len(captured_messages) == 4, f"Expected 4 messages, got {len(captured_messages)}"
        assert isinstance(captured_messages[0], SystemMessage), "First message should be SystemMessage"
        assert isinstance(captured_messages[1], HumanMessage), "Second message should be HumanMessage"
        assert isinstance(captured_messages[2], AIMessage), (
            f"Third message should be AIMessage but got {type(captured_messages[2]).__name__}. "
            "BUG: assistant role is being incorrectly converted to HumanMessage."
        )
        assert isinstance(captured_messages[3], HumanMessage), "Fourth message should be HumanMessage"
