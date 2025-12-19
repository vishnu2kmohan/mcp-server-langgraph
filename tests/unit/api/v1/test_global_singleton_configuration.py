"""
Global Singleton Configuration Tests

TDD RED Phase: Tests for configuring global singletons with custom security limits.
These tests verify that connection_manager, user_rate_limiter, and other global
instances can be configured with custom values from StreamingSettings.
"""

from __future__ import annotations

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


pytestmark = [
    pytest.mark.unit,
    pytest.mark.api,
    pytest.mark.websocket,
]


@pytest.mark.xdist_group(name="test_global_singleton_configuration")
class TestConnectionManagerSetter:
    """Tests for set_connection_manager function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_set_connection_manager_function_exists(self) -> None:
        """
        GIVEN mcp_websocket module
        WHEN checking for set_connection_manager function
        THEN should exist and be callable.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import set_connection_manager

        assert callable(set_connection_manager)

    def test_set_connection_manager_replaces_global(self) -> None:
        """
        GIVEN a custom ConnectionManager
        WHEN set_connection_manager is called
        THEN should replace the global connection_manager.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            ConnectionManager,
            set_connection_manager,
            get_connection_manager,
        )

        # Create custom manager with different limit
        custom_manager = ConnectionManager(max_connections_per_user=10)

        # Set as global
        set_connection_manager(custom_manager)

        # Verify it's the global now
        assert get_connection_manager() is custom_manager
        assert get_connection_manager().max_connections_per_user == 10

    def test_get_connection_manager_function_exists(self) -> None:
        """
        GIVEN mcp_websocket module
        WHEN checking for get_connection_manager function
        THEN should exist and be callable.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import get_connection_manager

        assert callable(get_connection_manager)

    def test_get_connection_manager_returns_current_global(self) -> None:
        """
        GIVEN the global connection_manager
        WHEN get_connection_manager is called
        THEN should return the current global instance.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            get_connection_manager,
            ConnectionManager,
        )

        manager = get_connection_manager()
        assert isinstance(manager, ConnectionManager)


@pytest.mark.xdist_group(name="test_global_singleton_configuration")
class TestUserRateLimiterSetter:
    """Tests for set_user_rate_limiter function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_set_user_rate_limiter_function_exists(self) -> None:
        """
        GIVEN mcp_websocket module
        WHEN checking for set_user_rate_limiter function
        THEN should exist and be callable.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import set_user_rate_limiter

        assert callable(set_user_rate_limiter)

    def test_set_user_rate_limiter_replaces_global(self) -> None:
        """
        GIVEN a custom UserRateLimiterManager
        WHEN set_user_rate_limiter is called
        THEN should replace the global user_rate_limiter.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            UserRateLimiterManager,
            set_user_rate_limiter,
            get_user_rate_limiter,
        )

        # Create custom limiter with different limit
        custom_limiter = UserRateLimiterManager(max_messages=1200, window_seconds=60)

        # Set as global
        set_user_rate_limiter(custom_limiter)

        # Verify it's the global now
        assert get_user_rate_limiter() is custom_limiter
        assert get_user_rate_limiter().max_messages == 1200

    def test_get_user_rate_limiter_function_exists(self) -> None:
        """
        GIVEN mcp_websocket module
        WHEN checking for get_user_rate_limiter function
        THEN should exist and be callable.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import get_user_rate_limiter

        assert callable(get_user_rate_limiter)

    def test_get_user_rate_limiter_returns_current_global(self) -> None:
        """
        GIVEN the global user_rate_limiter
        WHEN get_user_rate_limiter is called
        THEN should return the current global instance.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            get_user_rate_limiter,
            UserRateLimiterManager,
        )

        limiter = get_user_rate_limiter()
        assert isinstance(limiter, UserRateLimiterManager)


@pytest.mark.xdist_group(name="test_global_singleton_configuration")
class TestBootstrapConfiguresGlobalSingletons:
    """Tests for bootstrap configuring global singletons."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_init_websocket_lifecycle_configures_connection_manager(self) -> None:
        """
        GIVEN StreamingSettings with custom connection limit
        WHEN init_websocket_lifecycle is called
        THEN should configure global connection_manager with custom limit.
        """
        from mcp_server_langgraph.bootstrap.websocket import init_websocket_lifecycle
        from mcp_server_langgraph.api.v1.mcp_websocket import get_connection_manager
        from mcp_server_langgraph.core.config.streaming import StreamingSettings

        settings = StreamingSettings(
            streaming_max_connections_per_user=15,
        )

        state = await init_websocket_lifecycle(streaming_settings=settings)

        try:
            manager = get_connection_manager()
            assert manager.max_connections_per_user == 15
        finally:
            await state.cleanup()

    @pytest.mark.asyncio
    async def test_init_websocket_lifecycle_configures_user_rate_limiter(self) -> None:
        """
        GIVEN StreamingSettings with custom rate limit
        WHEN init_websocket_lifecycle is called
        THEN should configure global user_rate_limiter with custom limit.
        """
        from mcp_server_langgraph.bootstrap.websocket import init_websocket_lifecycle
        from mcp_server_langgraph.api.v1.mcp_websocket import get_user_rate_limiter
        from mcp_server_langgraph.core.config.streaming import StreamingSettings

        settings = StreamingSettings(
            streaming_max_messages_per_minute=1500,
        )

        state = await init_websocket_lifecycle(streaming_settings=settings)

        try:
            limiter = get_user_rate_limiter()
            assert limiter.max_messages == 1500
        finally:
            await state.cleanup()

    @pytest.mark.asyncio
    async def test_bootstrap_all_configures_security_limits(self) -> None:
        """
        GIVEN Settings with custom security limits
        WHEN bootstrap_all is called
        THEN should configure all global singletons with custom limits.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            get_connection_manager,
            get_user_rate_limiter,
        )

        # Mock settings with custom values
        mock_settings = MagicMock()
        mock_settings.streaming_enabled = True
        mock_settings.streaming_idle_cleanup_interval = 60
        mock_settings.streaming_metrics_cleanup_interval = 300
        mock_settings.streaming_max_age_seconds = 3600
        mock_settings.streaming_max_chunk_size = 65536
        mock_settings.streaming_max_notifications_per_second = 100
        mock_settings.streaming_max_connections_per_user = 20
        mock_settings.streaming_max_message_size = 2_000_000
        mock_settings.streaming_max_messages_per_minute = 1000
        mock_settings.streaming_idle_timeout_seconds = 3600

        # Mock the other bootstrap functions to avoid side effects
        with (
            patch("mcp_server_langgraph.bootstrap.init_observability") as mock_obs,
            patch("mcp_server_langgraph.bootstrap.init_auth") as mock_auth,
            patch("mcp_server_langgraph.bootstrap.init_storage") as mock_storage,
            patch("mcp_server_langgraph.bootstrap.init_http_client") as mock_http,
        ):
            mock_obs.return_value = MagicMock()
            mock_auth.return_value = MagicMock(cleanup=AsyncMock())  # async-mock-configured (cleanup callback)
            mock_storage.return_value = MagicMock(cleanup=AsyncMock())  # async-mock-configured (cleanup callback)
            mock_http.return_value = MagicMock(cleanup=AsyncMock())  # async-mock-configured (cleanup callback)

            from mcp_server_langgraph.bootstrap import bootstrap_all

            state = await bootstrap_all(mock_settings)

            try:
                # Verify connection manager was configured
                conn_manager = get_connection_manager()
                assert conn_manager.max_connections_per_user == 20

                # Verify rate limiter was configured
                rate_limiter = get_user_rate_limiter()
                assert rate_limiter.max_messages == 1000
            finally:
                await state.cleanup()


@pytest.mark.xdist_group(name="test_global_singleton_configuration")
class TestCreateConfiguredInstances:
    """Tests for factory functions that create configured instances."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_connection_manager_from_settings(self) -> None:
        """
        GIVEN StreamingSettings with custom connection limit
        WHEN create_connection_manager is called
        THEN should return ConnectionManager with configured limit.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import create_connection_manager
        from mcp_server_langgraph.core.config.streaming import StreamingSettings

        settings = StreamingSettings(
            streaming_max_connections_per_user=25,
        )

        manager = create_connection_manager(streaming_settings=settings)

        assert manager.max_connections_per_user == 25

    def test_create_user_rate_limiter_from_settings(self) -> None:
        """
        GIVEN StreamingSettings with custom rate limit
        WHEN create_user_rate_limiter is called
        THEN should return UserRateLimiterManager with configured limit.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import create_user_rate_limiter
        from mcp_server_langgraph.core.config.streaming import StreamingSettings

        settings = StreamingSettings(
            streaming_max_messages_per_minute=2000,
        )

        limiter = create_user_rate_limiter(streaming_settings=settings)

        assert limiter.max_messages == 2000


@pytest.mark.xdist_group(name="test_global_singleton_configuration")
class TestWebSocketStateIncludesSecurityConfig:
    """Tests for WebSocketState including security configuration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_websocket_state_has_connection_manager(self) -> None:
        """
        GIVEN WebSocketState
        WHEN initialized
        THEN should have connection_manager attribute.
        """
        from mcp_server_langgraph.bootstrap.websocket import WebSocketState

        state = WebSocketState()
        assert hasattr(state, "connection_manager")

    def test_websocket_state_has_user_rate_limiter(self) -> None:
        """
        GIVEN WebSocketState
        WHEN initialized
        THEN should have user_rate_limiter attribute.
        """
        from mcp_server_langgraph.bootstrap.websocket import WebSocketState

        state = WebSocketState()
        assert hasattr(state, "user_rate_limiter")
