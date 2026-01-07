"""Tests for full conversation history in LangGraph state.

TDD: These tests define the contract for passing full conversation
history to LangGraph instead of just the last user message.

Finding 4.1: _stream_via_langgraph only passes last user message.
The fix passes properly role-mapped full conversation history.

ADR Reference: Phase 4.1 of audit plan
"""

from __future__ import annotations

import gc
from typing import Any
from unittest.mock import MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="chat_full_conversation")
class TestBuildLangGraphMessages:
    """Tests for building properly role-mapped messages for LangGraph."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_build_langgraph_messages_function_exists(self) -> None:
        """Test that _build_langgraph_messages helper function exists."""
        from mcp_server_langgraph.api.v1.chat import _build_langgraph_messages

        assert callable(_build_langgraph_messages)

    def test_build_langgraph_messages_handles_user_role(self) -> None:
        """Test user messages become HumanMessage."""
        from mcp_server_langgraph.api.v1.chat import _build_langgraph_messages

        messages = [{"role": "user", "content": "Hello"}]
        result = _build_langgraph_messages(messages, record_metrics=False)

        assert len(result) == 1
        assert isinstance(result[0], HumanMessage)
        assert result[0].content == "Hello"

    def test_build_langgraph_messages_handles_assistant_role(self) -> None:
        """Test assistant messages become AIMessage."""
        from mcp_server_langgraph.api.v1.chat import _build_langgraph_messages

        messages = [{"role": "assistant", "content": "Hi there"}]
        result = _build_langgraph_messages(messages, record_metrics=False)

        assert len(result) == 1
        assert isinstance(result[0], AIMessage)
        assert result[0].content == "Hi there"

    def test_build_langgraph_messages_handles_system_role(self) -> None:
        """Test system messages become SystemMessage."""
        from mcp_server_langgraph.api.v1.chat import _build_langgraph_messages

        messages = [{"role": "system", "content": "You are helpful"}]
        result = _build_langgraph_messages(messages, record_metrics=False)

        assert len(result) == 1
        assert isinstance(result[0], SystemMessage)
        assert result[0].content == "You are helpful"

    def test_build_langgraph_messages_preserves_order(self) -> None:
        """Test message order is preserved in output."""
        from mcp_server_langgraph.api.v1.chat import _build_langgraph_messages

        messages = [
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "First question"},
            {"role": "assistant", "content": "First answer"},
            {"role": "user", "content": "Second question"},
        ]
        result = _build_langgraph_messages(messages, record_metrics=False)

        assert len(result) == 4
        assert isinstance(result[0], SystemMessage)
        assert isinstance(result[1], HumanMessage)
        assert isinstance(result[2], AIMessage)
        assert isinstance(result[3], HumanMessage)
        assert result[0].content == "System prompt"
        assert result[3].content == "Second question"

    def test_build_langgraph_messages_handles_empty_list(self) -> None:
        """Test empty message list returns empty result."""
        from mcp_server_langgraph.api.v1.chat import _build_langgraph_messages

        result = _build_langgraph_messages([])

        assert result == []

    def test_build_langgraph_messages_handles_unknown_role_as_user(self) -> None:
        """Test unknown roles default to HumanMessage."""
        from mcp_server_langgraph.api.v1.chat import _build_langgraph_messages

        messages = [{"role": "unknown", "content": "Unknown role"}]
        result = _build_langgraph_messages(messages, record_metrics=False)

        assert len(result) == 1
        assert isinstance(result[0], HumanMessage)


@pytest.mark.unit
@pytest.mark.xdist_group(name="chat_full_conversation")
class TestStreamViaLangGraphFullConversation:
    """Tests for _stream_via_langgraph using full conversation history."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_stream_via_langgraph_passes_full_conversation(self) -> None:
        """GIVEN a multi-turn conversation
        WHEN _stream_via_langgraph is called
        THEN all messages are passed to LangGraph (not just last user message)
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        # Track what astream_events was called with
        captured_args: list[Any] = []

        async def mock_astream_events(initial_state: Any, *args: Any, **kwargs: Any):
            captured_args.append(initial_state)
            # Yield nothing - we just want to capture the call
            return
            yield  # Make this an async generator  # noqa: RET503

        mock_agent = MagicMock()
        mock_agent.astream_events = mock_astream_events

        service = ChatServiceImpl.__new__(ChatServiceImpl)
        service._langgraph_agent = mock_agent

        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "First question"},
            {"role": "assistant", "content": "First answer"},
            {"role": "user", "content": "Second question"},
        ]

        # Consume the generator
        events = []
        async for event in service._stream_via_langgraph(
            session_id="test-session",
            messages=messages,
        ):
            events.append(event)

        # Verify astream_events was called and captured initial_state
        assert len(captured_args) == 1
        initial_state = captured_args[0]

        # Check that all 4 messages are present (not just last user message)
        langgraph_messages = initial_state.get("messages", [])
        assert len(langgraph_messages) == 4, (
            f"Expected 4 messages in state, got {len(langgraph_messages)}. "
            "Full conversation history should be passed, not just last user message."
        )

    @pytest.mark.asyncio
    async def test_stream_via_langgraph_maps_roles_correctly(self) -> None:
        """GIVEN messages with different roles
        WHEN _stream_via_langgraph is called
        THEN messages are mapped to correct LangChain message types
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        # Track what astream_events was called with
        captured_args: list[Any] = []

        async def mock_astream_events(initial_state: Any, *args: Any, **kwargs: Any):
            captured_args.append(initial_state)
            return
            yield  # Make this an async generator  # noqa: RET503

        mock_agent = MagicMock()
        mock_agent.astream_events = mock_astream_events

        service = ChatServiceImpl.__new__(ChatServiceImpl)
        service._langgraph_agent = mock_agent

        messages = [
            {"role": "system", "content": "System"},
            {"role": "user", "content": "User"},
            {"role": "assistant", "content": "Assistant"},
        ]

        async for _ in service._stream_via_langgraph(
            session_id="test-session",
            messages=messages,
        ):
            pass

        assert len(captured_args) == 1
        initial_state = captured_args[0]
        langgraph_messages = initial_state.get("messages", [])

        # Verify correct types
        assert isinstance(langgraph_messages[0], SystemMessage)
        assert isinstance(langgraph_messages[1], HumanMessage)
        assert isinstance(langgraph_messages[2], AIMessage)


class AsyncIteratorMock:
    """Mock async iterator for testing."""

    def __init__(self, items: list[Any]) -> None:
        self.items = items
        self.index = 0

    def __aiter__(self) -> AsyncIteratorMock:
        return self

    async def __anext__(self) -> Any:
        if self.index >= len(self.items):
            raise StopAsyncIteration
        item = self.items[self.index]
        self.index += 1
        return item


def make_async_iterator(items: list[Any]) -> MagicMock:
    """Create a mock that returns an async iterator."""

    async def async_gen(*args: Any, **kwargs: Any) -> AsyncIteratorMock:
        return AsyncIteratorMock(items)

    # Create an async generator function that yields items
    async def async_iter(*args: Any, **kwargs: Any):
        for item in items:
            yield item

    mock = MagicMock()
    mock.return_value = async_iter()
    return mock
