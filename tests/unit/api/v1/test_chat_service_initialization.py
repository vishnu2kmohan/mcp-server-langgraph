"""Tests for ChatService initialization and dependency injection.

TDD: These tests verify that get_chat_service() properly initializes
ChatServiceImpl with session_storage so that conversation history
is loaded from the database.

Bug Fix: get_chat_service() was creating ChatServiceImpl() without
passing session_storage, causing _load_and_merge_history() to return
early and not load conversation history.
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

if TYPE_CHECKING:
    from mcp_server_langgraph.api.v1.chat import ChatService

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="chat_service_init")
class TestGetChatServiceInitialization:
    """Tests for get_chat_service() proper initialization."""

    def teardown_method(self) -> None:
        """Force GC and reset singleton to prevent state leakage."""
        from mcp_server_langgraph.api.v1.chat import reset_chat_service

        reset_chat_service()
        gc.collect()

    def test_get_chat_service_initializes_with_session_storage(self) -> None:
        """GIVEN get_chat_service is called
        WHEN the singleton is created
        THEN session_storage should be set to a valid repository
        """
        from mcp_server_langgraph.api.v1.chat import (
            ChatServiceImpl,
            get_chat_service,
            reset_chat_service,
        )

        # Reset to ensure fresh singleton
        reset_chat_service()

        # Get the service
        service = get_chat_service()

        # Verify it's a ChatServiceImpl
        assert isinstance(service, ChatServiceImpl)

        # Verify session_storage is set (not None)
        assert service._session_storage is not None, (
            "ChatServiceImpl._session_storage should not be None. "
            "get_chat_service() must pass session_storage to constructor "
            "so that _load_and_merge_history() can load conversation history."
        )

    def test_get_chat_service_session_storage_has_get_messages(self) -> None:
        """GIVEN get_chat_service creates a service with session_storage
        WHEN we inspect the storage
        THEN it should have a get_messages method
        """
        from mcp_server_langgraph.api.v1.chat import (
            get_chat_service,
            reset_chat_service,
        )

        reset_chat_service()
        service = get_chat_service()

        # Verify storage has the required method
        storage = service._session_storage
        assert storage is not None
        assert hasattr(storage, "get_messages"), (
            "session_storage must have get_messages() method for history loading"
        )

    @pytest.mark.asyncio
    async def test_get_chat_service_session_storage_can_load_history(self) -> None:
        """GIVEN a properly initialized ChatService
        WHEN _load_and_merge_history is called
        THEN it should attempt to load from storage (not return early)
        """
        from mcp_server_langgraph.api.v1.chat import (
            ChatServiceImpl,
            get_chat_service,
            reset_chat_service,
        )

        reset_chat_service()
        service = get_chat_service()

        assert isinstance(service, ChatServiceImpl)

        # Mock the storage's get_messages to track if it's called
        mock_get_messages = AsyncMock(return_value=[])
        original_storage = service._session_storage

        # Only mock if storage exists
        if original_storage is not None:
            with patch.object(original_storage, "get_messages", mock_get_messages):
                result = await service._load_and_merge_history(
                    session_id="test-session",
                    new_messages=[{"role": "user", "content": "Hello"}],
                )

                # Verify storage was queried (not early return)
                mock_get_messages.assert_called_once_with("test-session")

    def test_chat_service_singleton_reuses_storage(self) -> None:
        """GIVEN get_chat_service is called multiple times
        WHEN the singleton already exists
        THEN the same storage instance should be reused
        """
        from mcp_server_langgraph.api.v1.chat import (
            get_chat_service,
            reset_chat_service,
        )

        reset_chat_service()

        service1 = get_chat_service()
        service2 = get_chat_service()

        # Same singleton
        assert service1 is service2

        # Same storage instance
        assert service1._session_storage is service2._session_storage


@pytest.mark.unit
@pytest.mark.xdist_group(name="chat_service_init")
class TestChatServiceImplWithStorage:
    """Tests for ChatServiceImpl behavior with storage."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_load_and_merge_history_uses_storage(self) -> None:
        """GIVEN a ChatServiceImpl with session_storage configured
        WHEN _load_and_merge_history is called
        THEN it loads history from storage
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        mock_storage = AsyncMock()
        mock_storage.get_messages = AsyncMock(
            return_value=[
                {"role": "user", "content": "Previous question"},
                {"role": "assistant", "content": "Previous answer"},
            ]
        )

        service = ChatServiceImpl(session_storage=mock_storage)

        result = await service._load_and_merge_history(
            session_id="test-session",
            new_messages=[{"role": "user", "content": "New question"}],
        )

        # Verify storage was called
        mock_storage.get_messages.assert_called_once_with("test-session")

        # Verify messages were merged
        assert len(result) == 3
        assert result[0]["content"] == "Previous question"
        assert result[1]["content"] == "Previous answer"
        assert result[2]["content"] == "New question"

    @pytest.mark.asyncio
    async def test_load_and_merge_history_returns_early_without_storage(self) -> None:
        """GIVEN a ChatServiceImpl with NO session_storage
        WHEN _load_and_merge_history is called
        THEN it returns only new messages (graceful fallback)
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        service = ChatServiceImpl(session_storage=None)

        result = await service._load_and_merge_history(
            session_id="test-session",
            new_messages=[{"role": "user", "content": "Hello"}],
        )

        # Should return only new messages
        assert len(result) == 1
        assert result[0]["content"] == "Hello"
