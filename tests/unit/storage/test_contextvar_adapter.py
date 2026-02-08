"""Tests for ContextvarSessionStorageAdapter empty user_id handling.

TDD: Tests written FIRST to define behavior when user_id contextvar is empty.

RC2 Fix: When get_current_user_id() returns "", get_messages() should:
1. Log an error with session context
2. Attempt session-scoped fallback lookup (bypasses user ownership check)
3. Return None only if fallback also fails

Security note: Session-scoped fallback is acceptable because session IDs are
UUIDs created during authenticated session creation.
"""

from __future__ import annotations

import gc
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from mcp_server_langgraph.storage.session.adapter import (
    ContextvarSessionStorageAdapter,
    get_current_user_id,
    set_current_user_id,
)

pytestmark = [
    pytest.mark.unit,
    pytest.mark.xdist_group(name="test_contextvar_adapter"),
]


class TestContextvarAdapterEmptyUserId:
    """Tests for ContextvarSessionStorageAdapter when user_id is empty."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_messages_logs_error_when_user_id_empty(self) -> None:
        """GIVEN user_id contextvar is empty
        WHEN get_messages is called
        THEN an error is logged with session_id context
        """
        mock_service = AsyncMock()  # noqa: async-mock-config
        adapter = ContextvarSessionStorageAdapter(mock_service)

        with (
            patch.object(adapter, "_get_user_id", return_value="")
            if hasattr(adapter, "_get_user_id")
            else patch(
                "mcp_server_langgraph.storage.session.adapter.get_current_user_id",
                return_value="",
            ),
            patch("mcp_server_langgraph.storage.session.adapter.logger") as mock_logger,
        ):
            await adapter.get_messages("test-session-123")

            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args
            assert "test-session-123" in str(call_args)

    @pytest.mark.asyncio
    async def test_get_messages_returns_none_when_user_id_empty_and_no_fallback(
        self,
    ) -> None:
        """GIVEN user_id contextvar is empty and session-scoped fallback fails
        WHEN get_messages is called
        THEN None is returned
        """
        mock_service = AsyncMock()  # noqa: async-mock-config
        mock_service.get_session_messages_by_session = AsyncMock(return_value=None)
        adapter = ContextvarSessionStorageAdapter(mock_service)

        with patch(
            "mcp_server_langgraph.storage.session.adapter.get_current_user_id",
            return_value="",
        ):
            result = await adapter.get_messages("test-session-123")

        assert result is None

    @pytest.mark.asyncio
    async def test_add_message_logs_error_when_user_id_empty(self) -> None:
        """GIVEN user_id contextvar is empty
        WHEN add_message is called
        THEN an error is logged with session_id context
        """
        mock_service = AsyncMock()  # noqa: async-mock-config
        adapter = ContextvarSessionStorageAdapter(mock_service)

        with (
            patch(
                "mcp_server_langgraph.storage.session.adapter.get_current_user_id",
                return_value="",
            ),
            patch("mcp_server_langgraph.storage.session.adapter.logger") as mock_logger,
        ):
            result = await adapter.add_message("test-session-123", {"role": "user", "content": "hello"})

            assert result is None
            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args
            assert "test-session-123" in str(call_args)

    @pytest.mark.asyncio
    async def test_get_messages_falls_back_to_session_scoped_lookup_when_user_id_empty(
        self,
    ) -> None:
        """GIVEN user_id contextvar is empty but session_id is valid
        WHEN get_messages is called
        THEN it falls back to session-scoped lookup (no user ownership check)
        """
        expected_messages: list[dict[str, Any]] = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi there"},
        ]

        mock_service = AsyncMock()  # noqa: async-mock-config
        mock_service.get_session_messages_by_session = AsyncMock(return_value=expected_messages)
        adapter = ContextvarSessionStorageAdapter(mock_service)

        with (
            patch(
                "mcp_server_langgraph.storage.session.adapter.get_current_user_id",
                return_value="",
            ),
            patch("mcp_server_langgraph.storage.session.adapter.logger") as mock_logger,
        ):
            result = await adapter.get_messages("test-session-123")

        assert result == expected_messages
        mock_service.get_session_messages_by_session.assert_called_once_with("test-session-123")
        # Should log warning about fallback path
        mock_logger.warning.assert_called()
        warning_call = str(mock_logger.warning.call_args)
        assert "fallback" in warning_call.lower() or "session-scoped" in warning_call.lower()

    @pytest.mark.asyncio
    async def test_get_messages_skips_fallback_when_setting_disabled(
        self,
    ) -> None:
        """GIVEN user_id is empty and enable_session_scoped_fallback is False
        WHEN get_messages is called
        THEN session-scoped fallback is NOT attempted, returns None
        """
        expected_messages: list[dict[str, Any]] = [
            {"role": "user", "content": "hello"},
        ]

        mock_service = AsyncMock()  # noqa: async-mock-config
        mock_service.get_session_messages_by_session = AsyncMock(return_value=expected_messages)
        adapter = ContextvarSessionStorageAdapter(mock_service)

        with (
            patch(
                "mcp_server_langgraph.storage.session.adapter.get_current_user_id",
                return_value="",
            ),
            patch("mcp_server_langgraph.storage.session.adapter.settings") as mock_settings,
        ):
            mock_settings.enable_session_scoped_fallback = False
            result = await adapter.get_messages("test-session-123")

        assert result is None
        # Fallback should NOT have been called
        mock_service.get_session_messages_by_session.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_messages_normal_path_with_valid_user_id(self) -> None:
        """GIVEN user_id contextvar has valid value
        WHEN get_messages is called
        THEN normal user-scoped lookup is used
        """
        expected_messages: list[dict[str, Any]] = [
            {"role": "user", "content": "hello"},
        ]

        mock_service = AsyncMock()  # noqa: async-mock-config
        mock_service.get_session_messages = AsyncMock(return_value=expected_messages)
        adapter = ContextvarSessionStorageAdapter(mock_service)

        with patch(
            "mcp_server_langgraph.storage.session.adapter.get_current_user_id",
            return_value="user-123",
        ):
            result = await adapter.get_messages("test-session-456")

        assert result == expected_messages
        mock_service.get_session_messages.assert_called_once_with("test-session-456", "user-123")


class TestContextvarAdapterFunctions:
    """Tests for contextvar helper functions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_set_and_get_current_user_id(self) -> None:
        """GIVEN a user_id value
        WHEN set_current_user_id is called
        THEN get_current_user_id returns the same value
        """
        set_current_user_id("test-user-abc")
        assert get_current_user_id() == "test-user-abc"
        # Reset
        set_current_user_id("")

    def test_get_current_user_id_default_is_empty(self) -> None:
        """GIVEN no user_id has been set
        WHEN get_current_user_id is called
        THEN it returns empty string (default)
        """
        set_current_user_id("")
        result = get_current_user_id()
        assert result == ""
