"""Tests for ConversationProgressiveLoader.

TDD: These tests define the contract for progressive loading
of conversation context with summarization support.

ADR-0092: Hierarchical Capability Architecture
"""

from __future__ import annotations

import gc

import pytest
from datetime import UTC

pytestmark = pytest.mark.unit


@pytest.mark.unit
class TestConversationProgressiveLoaderBasic:
    """Tests for ConversationProgressiveLoader basic functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_conversation_loader_exists(self) -> None:
        """Test ConversationProgressiveLoader class exists."""
        from mcp_server_langgraph.context.conversation_loader import (
            ConversationProgressiveLoader,
        )

        assert ConversationProgressiveLoader is not None

    def test_conversation_loader_has_load_method(self) -> None:
        """Test ConversationProgressiveLoader has load method."""
        from mcp_server_langgraph.context.conversation_loader import (
            ConversationProgressiveLoader,
        )

        loader = ConversationProgressiveLoader()

        assert hasattr(loader, "load")

    def test_conversation_loader_accepts_max_tokens(self) -> None:
        """Test ConversationProgressiveLoader accepts max_tokens parameter."""
        from mcp_server_langgraph.context.conversation_loader import (
            ConversationProgressiveLoader,
        )

        loader = ConversationProgressiveLoader(max_tokens=4000)

        assert loader.max_tokens == 4000


@pytest.mark.unit
class TestConversationMessage:
    """Tests for ConversationMessage dataclass."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_conversation_message_exists(self) -> None:
        """Test ConversationMessage dataclass exists."""
        from mcp_server_langgraph.context.conversation_loader import (
            ConversationMessage,
        )

        assert ConversationMessage is not None

    def test_conversation_message_has_role(self) -> None:
        """Test ConversationMessage has role field."""
        from mcp_server_langgraph.context.conversation_loader import (
            ConversationMessage,
        )

        msg = ConversationMessage(role="user", content="Hello")

        assert msg.role == "user"

    def test_conversation_message_has_content(self) -> None:
        """Test ConversationMessage has content field."""
        from mcp_server_langgraph.context.conversation_loader import (
            ConversationMessage,
        )

        msg = ConversationMessage(role="assistant", content="Hi there!")

        assert msg.content == "Hi there!"

    def test_conversation_message_has_optional_timestamp(self) -> None:
        """Test ConversationMessage has optional timestamp field."""
        from datetime import datetime

        from mcp_server_langgraph.context.conversation_loader import (
            ConversationMessage,
        )

        now = datetime.now(UTC)
        msg = ConversationMessage(role="user", content="Hello", timestamp=now)

        assert msg.timestamp == now


@pytest.mark.unit
class TestLoadedContext:
    """Tests for LoadedContext dataclass."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_loaded_context_exists(self) -> None:
        """Test LoadedContext dataclass exists."""
        from mcp_server_langgraph.context.conversation_loader import LoadedContext

        assert LoadedContext is not None

    def test_loaded_context_has_messages(self) -> None:
        """Test LoadedContext has messages field."""
        from mcp_server_langgraph.context.conversation_loader import (
            ConversationMessage,
            LoadedContext,
        )

        msg = ConversationMessage(role="user", content="Hello")
        context = LoadedContext(messages=[msg], total_tokens=10, was_truncated=False)

        assert len(context.messages) == 1
        assert context.messages[0] is msg

    def test_loaded_context_has_total_tokens(self) -> None:
        """Test LoadedContext has total_tokens field."""
        from mcp_server_langgraph.context.conversation_loader import LoadedContext

        context = LoadedContext(messages=[], total_tokens=500, was_truncated=False)

        assert context.total_tokens == 500

    def test_loaded_context_has_was_truncated(self) -> None:
        """Test LoadedContext has was_truncated field."""
        from mcp_server_langgraph.context.conversation_loader import LoadedContext

        context = LoadedContext(messages=[], total_tokens=500, was_truncated=True)

        assert context.was_truncated is True

    def test_loaded_context_has_optional_summary(self) -> None:
        """Test LoadedContext has optional summary field."""
        from mcp_server_langgraph.context.conversation_loader import LoadedContext

        context = LoadedContext(
            messages=[],
            total_tokens=500,
            was_truncated=True,
            summary="This conversation discussed project setup.",
        )

        assert context.summary == "This conversation discussed project setup."


@pytest.mark.unit
class TestConversationProgressiveLoaderLoad:
    """Tests for ConversationProgressiveLoader.load() method."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_load_returns_loaded_context(self) -> None:
        """Test load() returns LoadedContext."""
        from mcp_server_langgraph.context.conversation_loader import (
            ConversationMessage,
            ConversationProgressiveLoader,
            LoadedContext,
        )

        loader = ConversationProgressiveLoader()
        messages = [
            ConversationMessage(role="user", content="Hello"),
            ConversationMessage(role="assistant", content="Hi!"),
        ]

        result = await loader.load(messages)

        assert isinstance(result, LoadedContext)

    @pytest.mark.asyncio
    async def test_load_preserves_messages_within_limit(self) -> None:
        """Test load() preserves all messages when within token limit."""
        from mcp_server_langgraph.context.conversation_loader import (
            ConversationMessage,
            ConversationProgressiveLoader,
        )

        loader = ConversationProgressiveLoader(max_tokens=10000)
        messages = [
            ConversationMessage(role="user", content="Hello"),
            ConversationMessage(role="assistant", content="Hi!"),
        ]

        result = await loader.load(messages)

        assert len(result.messages) == 2
        assert result.was_truncated is False

    @pytest.mark.asyncio
    async def test_load_truncates_when_over_limit(self) -> None:
        """Test load() truncates when over token limit."""
        from mcp_server_langgraph.context.conversation_loader import (
            ConversationMessage,
            ConversationProgressiveLoader,
        )

        loader = ConversationProgressiveLoader(max_tokens=50)
        # Create many messages to exceed the limit
        messages = [ConversationMessage(role="user", content="Hello " * 20) for _ in range(10)]

        result = await loader.load(messages)

        assert result.was_truncated is True
        assert len(result.messages) < len(messages)

    @pytest.mark.asyncio
    async def test_load_keeps_recent_messages_priority(self) -> None:
        """Test load() prioritizes recent messages when truncating."""
        from mcp_server_langgraph.context.conversation_loader import (
            ConversationMessage,
            ConversationProgressiveLoader,
        )

        loader = ConversationProgressiveLoader(max_tokens=100)
        messages = [ConversationMessage(role="user", content=f"Message {i}") for i in range(10)]

        result = await loader.load(messages)

        # Recent messages should be preserved
        if result.was_truncated:
            # Last message should always be included
            assert result.messages[-1].content == "Message 9"


@pytest.mark.unit
class TestConversationProgressiveLoaderEstimate:
    """Tests for token estimation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_estimate_tokens_exists(self) -> None:
        """Test estimate_tokens method exists."""
        from mcp_server_langgraph.context.conversation_loader import (
            ConversationProgressiveLoader,
        )

        loader = ConversationProgressiveLoader()

        assert hasattr(loader, "estimate_tokens")

    def test_estimate_tokens_returns_int(self) -> None:
        """Test estimate_tokens returns integer."""
        from mcp_server_langgraph.context.conversation_loader import (
            ConversationProgressiveLoader,
        )

        loader = ConversationProgressiveLoader()
        estimate = loader.estimate_tokens("Hello world")

        assert isinstance(estimate, int)
        assert estimate > 0
