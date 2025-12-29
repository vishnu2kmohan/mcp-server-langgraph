"""
Streaming Enabled Flag Enforcement Tests

TDD RED Phase: Tests for verifying streaming_enabled flag is enforced.
When streaming is disabled, streaming requests should fall back to non-streaming.
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


@pytest.mark.xdist_group(name="test_streaming_enabled_flag")
class TestStreamingEnabledFlagExists:
    """Tests for streaming_enabled flag existence."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_streaming_settings_has_enabled_flag(self) -> None:
        """
        GIVEN StreamingSettings
        WHEN checking attributes
        THEN should have streaming_enabled field.
        """
        from mcp_server_langgraph.core.config.streaming import StreamingSettings

        settings = StreamingSettings()
        assert hasattr(settings, "streaming_enabled")
        assert isinstance(settings.streaming_enabled, bool)

    def test_streaming_enabled_default_true(self) -> None:
        """
        GIVEN StreamingSettings with no override
        WHEN checking streaming_enabled
        THEN should default to True.
        """
        from mcp_server_langgraph.core.config.streaming import StreamingSettings

        settings = StreamingSettings()
        assert settings.streaming_enabled is True


@pytest.mark.xdist_group(name="test_streaming_enabled_flag")
class TestStreamingDisabledBehavior:
    """Tests for behavior when streaming is disabled."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_streaming_disabled_falls_back_to_non_streaming(self) -> None:
        """
        GIVEN streaming_enabled=False and a streaming request
        WHEN handler processes the request
        THEN should use non-streaming execution (no streaming notifications).
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            AuthenticatedMCPHandler,
        )

        notifications: list[dict] = []

        async def capture(n):
            notifications.append(n)

        handler = AuthenticatedMCPHandler(
            user_id="user:alice",
            notification_callback=capture,
        )

        # Disable streaming globally - patch the NEW location that the handler imports from
        with patch.object(
            handler,
            "execute_tool",
            return_value=[{"type": "text", "text": "Non-streaming result"}],
        ):
            with patch(
                "mcp_server_langgraph.mcp.websocket.config.is_streaming_enabled",
                return_value=False,
            ):
                message = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "langgraph-run",
                        "arguments": {"query": "test"},
                        "_meta": {"streaming": True},  # Request streaming
                    },
                }
                response = await handler.handle(message)

        # Should NOT have any streaming notifications
        streaming_notifications = [n for n in notifications if n.get("method", "").startswith("$/streaming/")]
        assert len(streaming_notifications) == 0, "No streaming notifications should be emitted when streaming is disabled"

        # Should still return valid response
        assert response["jsonrpc"] == "2.0"
        assert "result" in response

    def test_is_streaming_enabled_function_exists(self) -> None:
        """
        GIVEN the mcp_websocket module
        WHEN importing
        THEN should have is_streaming_enabled function.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import is_streaming_enabled

        assert is_streaming_enabled is not None
        assert callable(is_streaming_enabled)

    def test_is_streaming_enabled_returns_bool(self) -> None:
        """
        GIVEN is_streaming_enabled function
        WHEN called
        THEN should return boolean.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import is_streaming_enabled

        result = is_streaming_enabled()
        assert isinstance(result, bool)


@pytest.mark.xdist_group(name="test_streaming_enabled_flag")
class TestStreamingEnabledWithConfig:
    """Tests for streaming enabled with configuration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_is_streaming_enabled_reads_from_settings(self) -> None:
        """
        GIVEN is_streaming_enabled function
        WHEN called with settings override
        THEN should respect settings value.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            set_streaming_enabled,
            is_streaming_enabled,
        )

        # Disable streaming
        set_streaming_enabled(False)
        assert is_streaming_enabled() is False

        # Re-enable streaming
        set_streaming_enabled(True)
        assert is_streaming_enabled() is True

    def test_set_streaming_enabled_function_exists(self) -> None:
        """
        GIVEN the mcp_websocket module
        WHEN importing
        THEN should have set_streaming_enabled function.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import set_streaming_enabled

        assert set_streaming_enabled is not None
        assert callable(set_streaming_enabled)


@pytest.mark.xdist_group(name="test_streaming_enabled_flag")
class TestLifecycleManagerWithStreamingDisabled:
    """Tests for lifecycle manager behavior when streaming is disabled."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_lifecycle_manager_skips_startup_when_disabled(self) -> None:
        """
        GIVEN streaming_enabled=False
        WHEN lifecycle manager startup is called
        THEN should skip starting cleanup tasks.
        """
        from mcp_server_langgraph.bootstrap.websocket import init_websocket_lifecycle
        from mcp_server_langgraph.core.config.streaming import StreamingSettings

        settings = StreamingSettings(streaming_enabled=False)

        with patch(
            "mcp_server_langgraph.api.v1.mcp_websocket._lifecycle_manager",
            None,
        ):
            state = await init_websocket_lifecycle(streaming_settings=settings)

        # Manager should exist but not have started cleanup tasks
        assert state.mcp_lifecycle_manager is not None
        # When disabled, cleanup task should not be started
        assert state.mcp_lifecycle_manager.cleanup_task is None

        # Cleanup (even though nothing to clean)
        await state.cleanup()

    @pytest.mark.asyncio
    async def test_lifecycle_manager_starts_tasks_when_enabled(self) -> None:
        """
        GIVEN streaming_enabled=True (default)
        WHEN lifecycle manager startup is called
        THEN should start cleanup tasks normally.
        """
        from mcp_server_langgraph.bootstrap.websocket import init_websocket_lifecycle
        from mcp_server_langgraph.core.config.streaming import StreamingSettings

        settings = StreamingSettings(streaming_enabled=True)

        with patch(
            "mcp_server_langgraph.api.v1.mcp_websocket._lifecycle_manager",
            None,
        ):
            state = await init_websocket_lifecycle(streaming_settings=settings)

        # Manager should have started cleanup tasks
        assert state.mcp_lifecycle_manager is not None
        assert state.mcp_lifecycle_manager.cleanup_task is not None

        # Cleanup
        await state.cleanup()


@pytest.mark.xdist_group(name="test_streaming_enabled_flag")
class TestMetricsEndpointWithStreamingDisabled:
    """Tests for metrics endpoint when streaming is disabled."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_metrics_endpoint_returns_disabled_status(self) -> None:
        """
        GIVEN streaming_enabled=False
        WHEN GET /mcp/metrics/streams is called
        THEN response should indicate streaming is disabled.
        """
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from mcp_server_langgraph.api.v1.mcp_websocket import mcp_websocket_router

        app = FastAPI()
        app.include_router(mcp_websocket_router, prefix="/api/v1")

        # Patch the package namespace where the endpoint imports from
        # The endpoint does: from mcp_server_langgraph.mcp.websocket import is_streaming_enabled
        with patch(
            "mcp_server_langgraph.mcp.websocket.is_streaming_enabled",
            return_value=False,
        ):
            client = TestClient(app)
            response = client.get("/api/v1/mcp/metrics/streams")

            data = response.json()

            # Should include streaming_enabled status
            assert "streaming_enabled" in data
            assert data["streaming_enabled"] is False
