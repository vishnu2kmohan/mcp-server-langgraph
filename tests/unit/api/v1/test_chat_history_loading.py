"""Tests for session history loading before LLM calls.

TDD: These tests define the contract that create_stream() must load
stored session messages before calling the LLM, ensuring full
conversation context is available.

Bug Fix: The LLM was receiving only the current message because
create_stream() never loaded history from storage.
"""

from __future__ import annotations

import gc
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="chat_history_loading")
class TestCreateStreamLoadsHistory:
    """Tests for create_stream loading session history from storage."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_create_stream_loads_history_from_storage(self) -> None:
        """GIVEN a session with stored message history
        WHEN create_stream is called with a new message
        THEN history is loaded from storage before calling LLM
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        # Create mock storage that returns history
        mock_storage = AsyncMock(return_value=None)
        mock_storage.get_messages = AsyncMock(
            return_value=[
                {"role": "user", "content": "My favorite color is blue"},
                {"role": "assistant", "content": "Great! Blue is a nice color."},
            ]
        )

        # Track messages passed to LLM
        captured_messages: list[Any] = []

        async def mock_stream(*args: Any, **kwargs: Any):
            captured_messages.extend(kwargs.get("messages", args[1] if len(args) > 1 else []))
            yield {"delta": {"content": "Response"}}

        service = ChatServiceImpl.__new__(ChatServiceImpl)
        service._session_storage = mock_storage
        service._mcp_bridge = None
        service._langgraph_agent = None
        service._router_agent = None
        service._llm_factory = MagicMock()
        service._llm_factory.astream = mock_stream

        # Call with only the new message (simulating frontend behavior)
        new_message = [{"role": "user", "content": "What is my favorite color?"}]

        with patch.object(service, "_stream_via_llm_factory", mock_stream):
            async for _ in service.create_stream(
                session_id="test-session",
                messages=new_message,
            ):
                pass

        # Verify storage was queried for history
        mock_storage.get_messages.assert_called_once_with("test-session")

        # Verify all 3 messages were passed to LLM (2 from history + 1 new)
        assert len(captured_messages) == 3, (
            f"Expected 3 messages (2 history + 1 new), got {len(captured_messages)}. "
            "History must be loaded and merged before LLM call."
        )

    @pytest.mark.asyncio
    async def test_create_stream_merges_history_with_new_message(self) -> None:
        """GIVEN stored history and a new message
        WHEN create_stream is called
        THEN history appears before the new message in correct order
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        mock_storage = AsyncMock(return_value=None)
        mock_storage.get_messages = AsyncMock(
            return_value=[
                {"role": "user", "content": "First"},
                {"role": "assistant", "content": "Response to first"},
            ]
        )

        captured_messages: list[dict[str, Any]] = []

        async def mock_stream(session_id: str, messages: list[dict[str, Any]], **kwargs: Any):
            captured_messages.extend(messages)
            yield {"delta": {"content": "Response"}}

        service = ChatServiceImpl.__new__(ChatServiceImpl)
        service._session_storage = mock_storage
        service._mcp_bridge = None
        service._langgraph_agent = None
        service._router_agent = None

        new_message = [{"role": "user", "content": "Second question"}]

        with patch.object(service, "_stream_via_llm_factory", mock_stream):
            async for _ in service.create_stream(
                session_id="test-session",
                messages=new_message,
            ):
                pass

        # Verify order: history first, then new message
        assert len(captured_messages) == 3
        assert captured_messages[0]["content"] == "First"
        assert captured_messages[1]["content"] == "Response to first"
        assert captured_messages[2]["content"] == "Second question"

    @pytest.mark.asyncio
    async def test_create_stream_handles_empty_history(self) -> None:
        """GIVEN a new session with no history
        WHEN create_stream is called
        THEN only the new message is passed to LLM
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        mock_storage = AsyncMock(return_value=None)
        mock_storage.get_messages = AsyncMock(return_value=[])

        captured_messages: list[dict[str, Any]] = []

        async def mock_stream(session_id: str, messages: list[dict[str, Any]], **kwargs: Any):
            captured_messages.extend(messages)
            yield {"delta": {"content": "Response"}}

        service = ChatServiceImpl.__new__(ChatServiceImpl)
        service._session_storage = mock_storage
        service._mcp_bridge = None
        service._langgraph_agent = None
        service._router_agent = None

        new_message = [{"role": "user", "content": "First message ever"}]

        with patch.object(service, "_stream_via_llm_factory", mock_stream):
            async for _ in service.create_stream(
                session_id="test-session",
                messages=new_message,
            ):
                pass

        # Only the new message should be passed
        assert len(captured_messages) == 1
        assert captured_messages[0]["content"] == "First message ever"

    @pytest.mark.asyncio
    async def test_create_stream_handles_no_storage_configured(self) -> None:
        """GIVEN no storage backend is configured
        WHEN create_stream is called
        THEN only the request messages are used (graceful fallback)
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        captured_messages: list[dict[str, Any]] = []

        async def mock_stream(session_id: str, messages: list[dict[str, Any]], **kwargs: Any):
            captured_messages.extend(messages)
            yield {"delta": {"content": "Response"}}

        service = ChatServiceImpl.__new__(ChatServiceImpl)
        service._session_storage = None  # No storage configured
        service._mcp_bridge = None
        service._langgraph_agent = None
        service._router_agent = None

        new_message = [{"role": "user", "content": "Hello"}]

        with patch.object(service, "_stream_via_llm_factory", mock_stream):
            async for _ in service.create_stream(
                session_id="test-session",
                messages=new_message,
            ):
                pass

        # Should still work with just the request message
        assert len(captured_messages) == 1
        assert captured_messages[0]["content"] == "Hello"

    @pytest.mark.asyncio
    async def test_create_stream_deduplicates_messages(self) -> None:
        """GIVEN history contains the same message as the request
        WHEN create_stream is called
        THEN duplicate messages are not sent to LLM
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        # History already has the current message (e.g., already saved by frontend)
        mock_storage = AsyncMock(return_value=None)
        mock_storage.get_messages = AsyncMock(
            return_value=[
                {"role": "user", "content": "Previous message"},
                {"role": "assistant", "content": "Previous response"},
                {"role": "user", "content": "Current question"},  # Same as new message
            ]
        )

        captured_messages: list[dict[str, Any]] = []

        async def mock_stream(session_id: str, messages: list[dict[str, Any]], **kwargs: Any):
            captured_messages.extend(messages)
            yield {"delta": {"content": "Response"}}

        service = ChatServiceImpl.__new__(ChatServiceImpl)
        service._session_storage = mock_storage
        service._mcp_bridge = None
        service._langgraph_agent = None
        service._router_agent = None

        # Frontend sends the same message that's already in history
        new_message = [{"role": "user", "content": "Current question"}]

        with patch.object(service, "_stream_via_llm_factory", mock_stream):
            async for _ in service.create_stream(
                session_id="test-session",
                messages=new_message,
            ):
                pass

        # Should have 3 messages, not 4 (deduplicated)
        assert len(captured_messages) == 3, (
            f"Expected 3 messages (deduped), got {len(captured_messages)}. Duplicate messages should not be sent to LLM."
        )

    @pytest.mark.asyncio
    async def test_load_and_merge_history_applies_progressive_loading(self) -> None:
        """GIVEN a very long conversation history
        WHEN _load_and_merge_history is called with a limited token budget
        THEN history is truncated using progressive loading (keeping recent messages)
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        # Create a very long history (would exceed token limits)
        # Each message has ~500 chars = ~125 tokens
        # 200 messages = ~25000 tokens, exceeds 8000 limit
        long_history = []
        for i in range(100):
            long_history.append({"role": "user", "content": f"Message {i}: " + "x" * 500})
            long_history.append({"role": "assistant", "content": f"Response {i}: " + "y" * 500})

        mock_storage = AsyncMock(return_value=None)
        mock_storage.get_messages = AsyncMock(return_value=long_history)

        service = ChatServiceImpl.__new__(ChatServiceImpl)
        service._session_storage = mock_storage

        new_message = [{"role": "user", "content": "Final question"}]

        # Mock a smaller token limit to force truncation
        # Default model limit is 325000, which is too high for this test
        with patch.object(service, "_get_model_aware_history_limit", return_value=8000):
            result = await service._load_and_merge_history(
                session_id="test-session",
                new_messages=new_message,
            )

        # Progressive loading should truncate - we should have fewer than 201 messages
        # With 8000 max tokens and ~130 tokens per message, expect ~60 messages
        assert len(result) < 201, f"Expected fewer than 201 messages after progressive loading, got {len(result)}"
        # But we should still have some messages (not empty)
        assert len(result) > 0

        # Most recent message should be preserved (the new one we sent)
        assert result[-1]["content"] == "Final question"

        # Recent messages from history should also be present
        # The newest historical message should be near the end
        assert any("Message 99" in msg["content"] for msg in result)

    def test_get_model_aware_history_limit_default(self) -> None:
        """GIVEN model-aware compaction is disabled
        WHEN _get_model_aware_history_limit is called
        THEN it returns the default limit (8000)
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        service = ChatServiceImpl.__new__(ChatServiceImpl)

        with patch("mcp_server_langgraph.core.feature_flags.feature_flags") as mock_flags:
            mock_flags.enable_model_aware_compaction = False

            limit = service._get_model_aware_history_limit()

            assert limit == 8000

    def test_get_model_aware_history_limit_uses_model_context(self) -> None:
        """GIVEN model-aware compaction is enabled
        WHEN _get_model_aware_history_limit is called
        THEN it calculates limit based on model's context window
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        service = ChatServiceImpl.__new__(ChatServiceImpl)

        with (
            patch("mcp_server_langgraph.core.feature_flags.feature_flags") as mock_flags,
            patch("mcp_server_langgraph.core.config.settings") as mock_settings,
            patch("mcp_server_langgraph.agents.model_registry.get_default_registry") as mock_registry,
        ):
            mock_flags.enable_model_aware_compaction = True
            mock_flags.context_compaction_threshold_percentage = 0.5
            mock_settings.model_name = "claude-3-opus"

            # Mock model with 200k context
            mock_caps = MagicMock()
            mock_caps.effective_limit = 200000
            mock_caps.context_limit = 200000
            mock_registry.return_value.get.return_value = mock_caps

            limit = service._get_model_aware_history_limit()

            # 200k * 0.5 = 100k
            assert limit == 100000
