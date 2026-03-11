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
        service._llm_factory = None  # __new__ bypasses __init__; set manually

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
        service._llm_factory = None  # __new__ bypasses __init__; set manually

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
        service._llm_factory = None  # __new__ bypasses __init__; set manually

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
        service._llm_factory = None  # __new__ bypasses __init__; set manually

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
        with patch.object(service, "_get_model_aware_history_limit", side_effect=lambda *a, **kw: 8000):
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


@pytest.mark.unit
@pytest.mark.xdist_group(name="chat_history_loading")
class TestLoadAndMergeHistoryErrorHandling:
    """Tests for _load_and_merge_history exception handling (RC3 fix)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_load_and_merge_history_logs_error_on_exception(self) -> None:
        """GIVEN storage raises an exception during history loading
        WHEN _load_and_merge_history is called
        THEN the exception is logged at ERROR level (not WARNING)
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        mock_storage = AsyncMock()  # noqa: async-mock-config
        mock_storage.get_messages = AsyncMock(side_effect=ConnectionError("Redis connection refused"))

        service = ChatServiceImpl.__new__(ChatServiceImpl)
        service._session_storage = mock_storage

        new_messages = [{"role": "user", "content": "Hello"}]

        with patch("mcp_server_langgraph.observability.telemetry.logger") as mock_logger:
            result = await service._load_and_merge_history(
                session_id="test-session",
                new_messages=new_messages,
            )

        # Should fall back to just new messages
        assert result == new_messages

        # Should log at ERROR level, not WARNING
        mock_logger.error.assert_called_once()
        error_msg = str(mock_logger.error.call_args)
        assert "test-session" in error_msg

        # Should NOT use warning for storage failures
        mock_logger.warning.assert_not_called()

    @pytest.mark.asyncio
    async def test_load_and_merge_history_includes_traceback_on_exception(
        self,
    ) -> None:
        """GIVEN storage raises an exception
        WHEN _load_and_merge_history is called
        THEN the error log includes exc_info for traceback
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        mock_storage = AsyncMock()  # noqa: async-mock-config
        mock_storage.get_messages = AsyncMock(side_effect=RuntimeError("Unexpected error"))

        service = ChatServiceImpl.__new__(ChatServiceImpl)
        service._session_storage = mock_storage

        new_messages = [{"role": "user", "content": "Test"}]

        with patch("mcp_server_langgraph.observability.telemetry.logger") as mock_logger:
            await service._load_and_merge_history(
                session_id="test-session",
                new_messages=new_messages,
            )

        # Verify exc_info=True is passed for traceback
        call_kwargs = mock_logger.error.call_args
        # exc_info can be passed as keyword arg or in the call
        assert call_kwargs is not None
        # Check if exc_info=True was passed
        _, kwargs = call_kwargs
        assert kwargs.get("exc_info") is True


@pytest.mark.unit
@pytest.mark.xdist_group(name="chat_history_loading")
class TestClientHistoryFallback:
    """Tests for client-supplied history fallback and ID-based dedup (RC4 fix)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_client_history_only_used_when_stored_history_unavailable(
        self,
    ) -> None:
        """GIVEN stored history IS available
        WHEN _load_and_merge_history receives messages with client_history_fallback
        THEN stored history is used, not client history
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        # Stored history exists
        mock_storage = AsyncMock(return_value=None)
        mock_storage.get_messages = AsyncMock(
            return_value=[
                {"role": "user", "content": "Stored msg 1"},
                {"role": "assistant", "content": "Stored response 1"},
            ]
        )

        service = ChatServiceImpl.__new__(ChatServiceImpl)
        service._session_storage = mock_storage

        # Client sends history (would only be used if stored fails)
        new_messages = [{"role": "user", "content": "New question"}]

        with patch.object(service, "_get_model_aware_history_limit", side_effect=lambda *a, **kw: 100000):
            result = await service._load_and_merge_history(
                session_id="test-session",
                new_messages=new_messages,
            )

        # Stored history should be used
        assert len(result) == 3
        assert result[0]["content"] == "Stored msg 1"

    @pytest.mark.asyncio
    async def test_dedup_uses_message_id_not_content(self) -> None:
        """GIVEN history contains messages with IDs
        WHEN a new message has the same content but different ID
        THEN it is NOT deduplicated (legitimate repeated message like "ok")
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        mock_storage = AsyncMock(return_value=None)
        mock_storage.get_messages = AsyncMock(
            return_value=[
                {"id": "msg-1", "role": "user", "content": "ok"},
                {"id": "msg-2", "role": "assistant", "content": "Got it"},
            ]
        )

        service = ChatServiceImpl.__new__(ChatServiceImpl)
        service._session_storage = mock_storage

        # New message has same content "ok" but different ID
        new_messages = [{"id": "msg-3", "role": "user", "content": "ok"}]

        with patch.object(service, "_get_model_aware_history_limit", side_effect=lambda *a, **kw: 100000):
            result = await service._load_and_merge_history(
                session_id="test-session",
                new_messages=new_messages,
            )

        # Should have all 3 messages (not deduped by content)
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_dedup_removes_duplicate_by_id(self) -> None:
        """GIVEN history contains a message with the same ID as a new message
        WHEN _load_and_merge_history merges them
        THEN the duplicate is removed (same message persisted twice)
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        mock_storage = AsyncMock(return_value=None)
        mock_storage.get_messages = AsyncMock(
            return_value=[
                {"id": "msg-1", "role": "user", "content": "Hello"},
                {"id": "msg-2", "role": "assistant", "content": "Hi"},
                {"id": "msg-3", "role": "user", "content": "How are you?"},
            ]
        )

        service = ChatServiceImpl.__new__(ChatServiceImpl)
        service._session_storage = mock_storage

        # Same ID as existing message (e.g., streaming endpoint already persisted it)
        new_messages = [{"id": "msg-3", "role": "user", "content": "How are you?"}]

        with patch.object(service, "_get_model_aware_history_limit", side_effect=lambda *a, **kw: 100000):
            result = await service._load_and_merge_history(
                session_id="test-session",
                new_messages=new_messages,
            )

        # Should have 3 messages, not 4 (deduped by ID)
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_dedup_handles_message_id_key_from_stored_messages(self) -> None:
        """GIVEN stored messages use 'message_id' key (not 'id')
        WHEN a new message has the same message_id
        THEN it is deduplicated correctly
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        # Stored messages use 'message_id' (the key used by SessionService)
        mock_storage = AsyncMock(return_value=None)
        mock_storage.get_messages = AsyncMock(
            return_value=[
                {"message_id": "msg-1", "role": "user", "content": "Hello"},
                {"message_id": "msg-2", "role": "assistant", "content": "Hi"},
            ]
        )

        service = ChatServiceImpl.__new__(ChatServiceImpl)
        service._session_storage = mock_storage

        # Client sends message with 'id' key matching stored 'message_id'
        new_messages = [{"id": "msg-1", "role": "user", "content": "Hello"}]

        with patch.object(service, "_get_model_aware_history_limit", side_effect=lambda *a, **kw: 100000):
            result = await service._load_and_merge_history(
                session_id="test-session",
                new_messages=new_messages,
            )

        # Should have 2 messages (deduped msg-1), not 3
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_content_dedup_includes_messages_with_ids(self) -> None:
        """GIVEN stored history has messages WITH IDs (persisted by streaming endpoint)
        WHEN a new message without an ID has the same (role, content)
        THEN it IS deduplicated by content fallback (Finding 1 fix)

        Bug: The original code only built history_content_set from messages
        WITHOUT IDs, so messages persisted by the streaming endpoint (which
        assigns IDs) were excluded from the content fallback set.
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        # Streaming endpoint persisted the user message with an ID
        mock_storage = AsyncMock(return_value=None)
        mock_storage.get_messages = AsyncMock(
            return_value=[
                {"message_id": "msg-1", "role": "user", "content": "Hello world"},
                {"message_id": "msg-2", "role": "assistant", "content": "Hi there"},
            ]
        )

        service = ChatServiceImpl.__new__(ChatServiceImpl)
        service._session_storage = mock_storage

        # Frontend sends same message WITHOUT an ID (optimistic send)
        new_messages = [{"role": "user", "content": "Hello world"}]

        with patch.object(service, "_get_model_aware_history_limit", side_effect=lambda *a, **kw: 100000):
            result = await service._load_and_merge_history(
                session_id="test-session",
                new_messages=new_messages,
            )

        # Should have 2 messages (deduped by content), NOT 3
        assert len(result) == 2, (
            f"Expected 2 messages (content-deduped), got {len(result)}. "
            "Messages with IDs must be included in the content fallback set."
        )


@pytest.mark.unit
@pytest.mark.xdist_group(name="chat_history_loading")
class TestServerSideHistoryEnforcement:
    """Tests for server-side client_history_fallback enforcement (Finding 2 & 6)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_client_history_stripped_when_stored_history_exists(self) -> None:
        """GIVEN stored history exists and client_history_fallback=True
        WHEN _load_and_merge_history is called with client history
        THEN client history is stripped, keeping only the last user message
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        # Server has stored history
        mock_storage = AsyncMock(return_value=None)
        mock_storage.get_messages = AsyncMock(
            return_value=[
                {"role": "user", "content": "Stored msg 1"},
                {"role": "assistant", "content": "Stored response 1"},
            ]
        )

        service = ChatServiceImpl.__new__(ChatServiceImpl)
        service._session_storage = mock_storage

        # Client sends full history + new message (fallback mode)
        new_messages = [
            {"role": "user", "content": "Client history msg 1"},
            {"role": "assistant", "content": "Client history resp 1"},
            {"role": "user", "content": "New question"},
        ]

        with patch.object(service, "_get_model_aware_history_limit", side_effect=lambda *a, **kw: 100000):
            result = await service._load_and_merge_history(
                session_id="test-session",
                new_messages=new_messages,
                client_history_fallback=True,
            )

        # Should have stored history + only the new user message (3 total)
        assert len(result) == 3
        assert result[0]["content"] == "Stored msg 1"
        assert result[1]["content"] == "Stored response 1"
        assert result[2]["content"] == "New question"

    @pytest.mark.asyncio
    async def test_client_history_used_when_no_stored_history(self) -> None:
        """GIVEN no stored history and client_history_fallback=True
        WHEN _load_and_merge_history is called with client history
        THEN client history is used as fallback
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        mock_storage = AsyncMock(return_value=None)
        mock_storage.get_messages = AsyncMock(return_value=[])

        service = ChatServiceImpl.__new__(ChatServiceImpl)
        service._session_storage = mock_storage

        new_messages = [
            {"role": "user", "content": "Previous msg"},
            {"role": "assistant", "content": "Previous resp"},
            {"role": "user", "content": "New question"},
        ]

        with patch.object(service, "_get_model_aware_history_limit", side_effect=lambda *a, **kw: 100000):
            result = await service._load_and_merge_history(
                session_id="test-session",
                new_messages=new_messages,
                client_history_fallback=True,
            )

        # All client messages should be used (no stored history to prefer)
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_server_caps_client_history_at_max(self) -> None:
        """GIVEN client_history_fallback=True with >50 messages
        WHEN _load_and_merge_history is called
        THEN messages are capped to most recent MAX_CLIENT_HISTORY_MESSAGES
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        mock_storage = AsyncMock(return_value=None)
        mock_storage.get_messages = AsyncMock(return_value=[])

        service = ChatServiceImpl.__new__(ChatServiceImpl)
        service._session_storage = mock_storage

        # Client sends 60 messages (exceeds MAX_CLIENT_HISTORY_MESSAGES=50)
        new_messages = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"Message {i}"} for i in range(60)]

        with patch.object(service, "_get_model_aware_history_limit", side_effect=lambda *a, **kw: 100000):
            result = await service._load_and_merge_history(
                session_id="test-session",
                new_messages=new_messages,
                client_history_fallback=True,
            )

        # Should be capped at 50 (most recent)
        assert len(result) <= 50
        # Most recent message should be preserved
        assert result[-1]["content"] == "Message 59"

    @pytest.mark.asyncio
    async def test_no_enforcement_when_flag_is_false(self) -> None:
        """GIVEN client_history_fallback=False (default)
        WHEN _load_and_merge_history is called
        THEN all new_messages are treated normally (no stripping or capping)
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        mock_storage = AsyncMock(return_value=None)
        mock_storage.get_messages = AsyncMock(return_value=[])

        service = ChatServiceImpl.__new__(ChatServiceImpl)
        service._session_storage = mock_storage

        new_messages = [{"role": "user", "content": "Normal message"}]

        with patch.object(service, "_get_model_aware_history_limit", side_effect=lambda *a, **kw: 100000):
            result = await service._load_and_merge_history(
                session_id="test-session",
                new_messages=new_messages,
                client_history_fallback=False,
            )

        assert len(result) == 1
        assert result[0]["content"] == "Normal message"
