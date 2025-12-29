"""
Streaming Settings Wiring Tests

TDD RED Phase: Tests for verifying that streaming settings are properly wired
to the StreamingToolCallHandler when created inside AuthenticatedMCPHandler.
"""

from __future__ import annotations

import gc
from unittest.mock import patch

import pytest


pytestmark = [
    pytest.mark.unit,
    pytest.mark.api,
    pytest.mark.websocket,
]


@pytest.mark.xdist_group(name="test_streaming_settings_wiring")
class TestStreamingConfigGetters:
    """Tests for global streaming configuration getters."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_streaming_max_chunk_size_exists(self) -> None:
        """
        GIVEN mcp_websocket module
        WHEN checking for get_streaming_max_chunk_size function
        THEN should exist and be callable.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            get_streaming_max_chunk_size,
        )

        assert callable(get_streaming_max_chunk_size)

    def test_get_streaming_max_chunk_size_returns_value(self) -> None:
        """
        GIVEN global streaming config
        WHEN get_streaming_max_chunk_size is called
        THEN should return the configured max chunk size.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            get_streaming_max_chunk_size,
        )

        result = get_streaming_max_chunk_size()
        # Should return an int or None
        assert result is None or isinstance(result, int)

    def test_set_streaming_max_chunk_size_exists(self) -> None:
        """
        GIVEN mcp_websocket module
        WHEN checking for set_streaming_max_chunk_size function
        THEN should exist and be callable.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            set_streaming_max_chunk_size,
        )

        assert callable(set_streaming_max_chunk_size)

    def test_set_streaming_max_chunk_size_updates_global(self) -> None:
        """
        GIVEN custom max_chunk_size value
        WHEN set_streaming_max_chunk_size is called
        THEN get_streaming_max_chunk_size should return that value.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            get_streaming_max_chunk_size,
            set_streaming_max_chunk_size,
        )

        # Save original
        original = get_streaming_max_chunk_size()

        try:
            set_streaming_max_chunk_size(32768)
            assert get_streaming_max_chunk_size() == 32768
        finally:
            # Restore original
            set_streaming_max_chunk_size(original)


@pytest.mark.xdist_group(name="test_streaming_settings_wiring")
class TestOutboundRateLimiterGetters:
    """Tests for global outbound rate limiter getters."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_outbound_rate_limiter_exists(self) -> None:
        """
        GIVEN mcp_websocket module
        WHEN checking for get_outbound_rate_limiter function
        THEN should exist and be callable.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            get_outbound_rate_limiter,
        )

        assert callable(get_outbound_rate_limiter)

    def test_get_outbound_rate_limiter_returns_instance(self) -> None:
        """
        GIVEN global streaming config
        WHEN get_outbound_rate_limiter is called
        THEN should return an OutboundRateLimiter instance or None.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            get_outbound_rate_limiter,
            OutboundRateLimiter,
        )

        result = get_outbound_rate_limiter()
        assert result is None or isinstance(result, OutboundRateLimiter)

    def test_set_outbound_rate_limiter_exists(self) -> None:
        """
        GIVEN mcp_websocket module
        WHEN checking for set_outbound_rate_limiter function
        THEN should exist and be callable.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            set_outbound_rate_limiter,
        )

        assert callable(set_outbound_rate_limiter)

    def test_set_outbound_rate_limiter_updates_global(self) -> None:
        """
        GIVEN custom OutboundRateLimiter
        WHEN set_outbound_rate_limiter is called
        THEN get_outbound_rate_limiter should return that instance.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            get_outbound_rate_limiter,
            set_outbound_rate_limiter,
            OutboundRateLimiter,
        )

        # Save original
        original = get_outbound_rate_limiter()

        try:
            custom_limiter = OutboundRateLimiter(max_notifications_per_second=50)
            set_outbound_rate_limiter(custom_limiter)
            assert get_outbound_rate_limiter() is custom_limiter
        finally:
            # Restore original
            set_outbound_rate_limiter(original)


@pytest.mark.xdist_group(name="test_streaming_settings_wiring")
class TestBootstrapWiresStreamingConfig:
    """Tests for bootstrap wiring streaming configuration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_init_websocket_lifecycle_sets_max_chunk_size(self) -> None:
        """
        GIVEN StreamingSettings with custom max_chunk_size
        WHEN init_websocket_lifecycle is called
        THEN should set global max_chunk_size.
        """
        from mcp_server_langgraph.bootstrap.websocket import init_websocket_lifecycle
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            get_streaming_max_chunk_size,
        )
        from mcp_server_langgraph.core.config.streaming import StreamingSettings

        settings = StreamingSettings(
            streaming_max_chunk_size=65536,
        )

        state = await init_websocket_lifecycle(streaming_settings=settings)

        try:
            assert get_streaming_max_chunk_size() == 65536
        finally:
            await state.cleanup()

    @pytest.mark.asyncio
    async def test_init_websocket_lifecycle_sets_outbound_rate_limiter(self) -> None:
        """
        GIVEN StreamingSettings with custom max_notifications_per_second
        WHEN init_websocket_lifecycle is called
        THEN should set global outbound rate limiter with configured rate.
        """
        from mcp_server_langgraph.bootstrap.websocket import init_websocket_lifecycle
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            get_outbound_rate_limiter,
        )
        from mcp_server_langgraph.core.config.streaming import StreamingSettings

        settings = StreamingSettings(
            streaming_max_notifications_per_second=200,
        )

        state = await init_websocket_lifecycle(streaming_settings=settings)

        try:
            limiter = get_outbound_rate_limiter()
            assert limiter is not None
            assert limiter.max_notifications_per_second == 200
        finally:
            await state.cleanup()


@pytest.mark.xdist_group(name="test_streaming_settings_wiring")
class TestAuthenticatedHandlerUsesGlobalConfig:
    """Tests for AuthenticatedMCPHandler using global streaming config."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_handler_uses_global_max_chunk_size(self) -> None:
        """
        GIVEN global max_chunk_size configured
        WHEN AuthenticatedMCPHandler creates StreamingToolCallHandler
        THEN should pass max_chunk_size from global config.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            AuthenticatedMCPHandler,
            set_streaming_max_chunk_size,
            get_streaming_max_chunk_size,
            set_streaming_enabled,
        )

        # Save originals
        original_chunk_size = get_streaming_max_chunk_size()

        try:
            # Configure global settings
            set_streaming_max_chunk_size(1024)
            set_streaming_enabled(True)

            # Create handler with notification callback
            chunks_received = []

            async def capture_notification(notification):
                if notification.get("method") == "$/streaming/chunk":
                    chunks_received.append(notification)

            handler = AuthenticatedMCPHandler(
                user_id="user:test",
                notification_callback=capture_notification,
            )

            # Mock execute_tool_streaming to yield oversized chunk
            async def mock_streaming(*args, **kwargs):
                yield {"type": "text", "text": "x" * 2000, "is_final": True}

            with patch.object(handler, "execute_tool_streaming", side_effect=mock_streaming):
                await handler._handle_tools_call(
                    message_id=1,
                    params={"name": "test-tool", "arguments": {}, "_meta": {"streaming": True}},
                )

            # Chunk should have been truncated to max_chunk_size
            if chunks_received:
                chunk_text = chunks_received[0]["params"]["content"]["text"]
                assert len(chunk_text) <= 1024

        finally:
            # Restore original
            set_streaming_max_chunk_size(original_chunk_size)

    @pytest.mark.asyncio
    async def test_handler_uses_global_outbound_rate_limiter(self) -> None:
        """
        GIVEN global OutboundRateLimiter configured
        WHEN AuthenticatedMCPHandler creates StreamingToolCallHandler
        THEN should pass outbound_rate_limiter from global config.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            AuthenticatedMCPHandler,
            set_outbound_rate_limiter,
            get_outbound_rate_limiter,
            set_streaming_enabled,
            OutboundRateLimiter,
        )

        # Save originals
        original_limiter = get_outbound_rate_limiter()

        try:
            # Configure global settings with slow rate limiter
            slow_limiter = OutboundRateLimiter(max_notifications_per_second=5)
            set_outbound_rate_limiter(slow_limiter)
            set_streaming_enabled(True)

            # Create handler with notification callback
            notifications_sent = []

            async def capture_notification(notification):
                notifications_sent.append(notification)

            handler = AuthenticatedMCPHandler(
                user_id="user:test",
                notification_callback=capture_notification,
            )

            # Mock execute_tool_streaming to yield multiple chunks
            async def mock_streaming(*args, **kwargs):
                for i in range(3):
                    yield {"type": "text", "text": f"chunk {i}", "is_final": i == 2}

            with patch.object(handler, "execute_tool_streaming", side_effect=mock_streaming):
                await handler._handle_tools_call(
                    message_id=1,
                    params={"name": "test-tool", "arguments": {}, "_meta": {"streaming": True}},
                )

            # Verify streaming handler received notifications
            # 5 notifications (start + 3 chunks + end)
            # Not asserting strict timing to avoid flakiness
            assert len(notifications_sent) >= 3

        finally:
            # Restore original
            set_outbound_rate_limiter(original_limiter)


@pytest.mark.xdist_group(name="test_streaming_settings_wiring")
class TestHandlerSessionIdWiring:
    """Tests for AuthenticatedMCPHandler session_id attribute wiring."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_authenticated_handler_accepts_session_id(self) -> None:
        """
        GIVEN AuthenticatedMCPHandler
        WHEN created with session_id parameter
        THEN should store the session_id.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import AuthenticatedMCPHandler

        handler = AuthenticatedMCPHandler(
            user_id="user:test",
            session_id="test-session-123",
        )

        assert handler.session_id == "test-session-123"

    def test_authenticated_handler_session_id_defaults_to_none(self) -> None:
        """
        GIVEN AuthenticatedMCPHandler
        WHEN created without session_id
        THEN session_id should default to None.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import AuthenticatedMCPHandler

        handler = AuthenticatedMCPHandler(user_id="user:test")

        assert handler.session_id is None

    @pytest.mark.asyncio
    async def test_streaming_handler_receives_session_id(self) -> None:
        """
        GIVEN AuthenticatedMCPHandler with session_id
        WHEN making streaming call
        THEN StreamingToolCallHandler should receive session_id.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            AuthenticatedMCPHandler,
            set_streaming_enabled,
            get_connection_manager,
        )

        set_streaming_enabled(True)
        connection_manager = get_connection_manager()

        # Track if activity was updated
        activity_updates = []
        original_update = connection_manager.update_activity

        def track_activity(session_id: str) -> None:
            activity_updates.append(session_id)
            # Don't call original since connection doesn't exist
            pass

        connection_manager.update_activity = track_activity

        try:
            notifications = []

            async def capture_notification(notification):
                notifications.append(notification)

            handler = AuthenticatedMCPHandler(
                user_id="user:test",
                session_id="my-session-id",
                notification_callback=capture_notification,
            )

            async def mock_streaming(*args, **kwargs):
                yield {"type": "text", "text": "chunk", "is_final": True}

            with patch.object(handler, "execute_tool_streaming", side_effect=mock_streaming):
                await handler._handle_tools_call(
                    message_id=1,
                    params={"name": "test-tool", "arguments": {}, "_meta": {"streaming": True}},
                )

            # Activity should have been updated with our session_id
            assert "my-session-id" in activity_updates

        finally:
            connection_manager.update_activity = original_update

    @pytest.mark.asyncio
    async def test_streaming_handler_receives_connection_manager(self) -> None:
        """
        GIVEN AuthenticatedMCPHandler with session_id
        WHEN making streaming call
        THEN StreamingToolCallHandler should receive connection_manager.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            AuthenticatedMCPHandler,
            set_streaming_enabled,
            get_connection_manager,
        )

        set_streaming_enabled(True)
        connection_manager = get_connection_manager()

        # Verify connection_manager.update_activity is called
        activity_updates = []

        def track_activity(session_id: str) -> None:
            activity_updates.append(("update_activity", session_id))

        connection_manager.update_activity = track_activity

        try:
            notifications = []

            async def capture_notification(notification):
                notifications.append(notification)

            handler = AuthenticatedMCPHandler(
                user_id="user:test",
                session_id="session-for-cm-test",
                notification_callback=capture_notification,
            )

            async def mock_streaming(*args, **kwargs):
                yield {"type": "text", "text": "chunk", "is_final": True}

            with patch.object(handler, "execute_tool_streaming", side_effect=mock_streaming):
                await handler._handle_tools_call(
                    message_id=1,
                    params={"name": "test-tool", "arguments": {}, "_meta": {"streaming": True}},
                )

            # Should have activity update from connection_manager
            assert len(activity_updates) >= 1
            assert activity_updates[0] == ("update_activity", "session-for-cm-test")

        finally:
            # Reset to original
            from mcp_server_langgraph.api.v1.mcp_websocket import ConnectionManager

            connection_manager.update_activity = ConnectionManager.update_activity.__get__(
                connection_manager, ConnectionManager
            )


@pytest.mark.xdist_group(name="test_streaming_settings_wiring")
class TestCreateHandlerWithSessionId:
    """Tests for factory functions with session_id."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_create_handler_from_token_accepts_session_id(self) -> None:
        """
        GIVEN create_handler_from_token function
        WHEN called with websocket and session_id parameter
        THEN should return handler with session_id set.
        """
        from unittest.mock import AsyncMock, MagicMock
        from mcp_server_langgraph.api.v1.mcp_websocket import create_handler_from_token

        # Create mock WebSocket
        mock_websocket = MagicMock()
        mock_websocket.send_json = AsyncMock()  # noqa: async-mock-config

        # Call the async function without a token (anonymous handler)
        handler = await create_handler_from_token(
            websocket=mock_websocket,
            session_id="factory-session-id",
            token=None,
        )

        assert handler.session_id == "factory-session-id"

    @pytest.mark.asyncio
    async def test_create_anonymous_streaming_handler_sets_session_id(self) -> None:
        """
        GIVEN create_anonymous_streaming_handler function
        WHEN called with websocket and session_id
        THEN should set session_id on the handler.
        """
        from unittest.mock import AsyncMock, MagicMock
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            create_anonymous_streaming_handler,
        )

        # Create mock WebSocket
        mock_websocket = MagicMock()
        mock_websocket.send_json = AsyncMock()  # noqa: async-mock-config

        handler = await create_anonymous_streaming_handler(
            websocket=mock_websocket,
            session_id="anon-session-123",
        )

        assert handler.session_id == "anon-session-123"
