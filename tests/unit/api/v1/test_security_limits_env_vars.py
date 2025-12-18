"""
Security Limits Environment Variable Tests

TDD Phase: Tests verifying that security limit fields can be configured
via environment variables.
"""

from __future__ import annotations

import gc
import os
from unittest.mock import patch

import pytest


pytestmark = [
    pytest.mark.unit,
    pytest.mark.api,
    pytest.mark.websocket,
]


@pytest.mark.xdist_group(name="test_security_limits_env_vars")
class TestStreamingSettingsEnvVars:
    """Tests for StreamingSettings reading from environment variables."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_max_connections_per_user_from_env(self) -> None:
        """
        GIVEN STREAMING_MAX_CONNECTIONS_PER_USER environment variable set
        WHEN StreamingSettings is created
        THEN should use the environment variable value.
        """
        with patch.dict(os.environ, {"STREAMING_MAX_CONNECTIONS_PER_USER": "15"}):
            from mcp_server_langgraph.core.config.streaming import StreamingSettings

            settings = StreamingSettings()
            assert settings.streaming_max_connections_per_user == 15

    def test_max_message_size_from_env(self) -> None:
        """
        GIVEN STREAMING_MAX_MESSAGE_SIZE environment variable set
        WHEN StreamingSettings is created
        THEN should use the environment variable value.
        """
        with patch.dict(os.environ, {"STREAMING_MAX_MESSAGE_SIZE": "5000000"}):
            from mcp_server_langgraph.core.config.streaming import StreamingSettings

            settings = StreamingSettings()
            assert settings.streaming_max_message_size == 5_000_000

    def test_max_messages_per_minute_from_env(self) -> None:
        """
        GIVEN STREAMING_MAX_MESSAGES_PER_MINUTE environment variable set
        WHEN StreamingSettings is created
        THEN should use the environment variable value.
        """
        with patch.dict(os.environ, {"STREAMING_MAX_MESSAGES_PER_MINUTE": "1200"}):
            from mcp_server_langgraph.core.config.streaming import StreamingSettings

            settings = StreamingSettings()
            assert settings.streaming_max_messages_per_minute == 1200

    def test_idle_timeout_seconds_from_env(self) -> None:
        """
        GIVEN STREAMING_IDLE_TIMEOUT_SECONDS environment variable set
        WHEN StreamingSettings is created
        THEN should use the environment variable value.
        """
        with patch.dict(os.environ, {"STREAMING_IDLE_TIMEOUT_SECONDS": "3600"}):
            from mcp_server_langgraph.core.config.streaming import StreamingSettings

            settings = StreamingSettings()
            assert settings.streaming_idle_timeout_seconds == 3600


@pytest.mark.xdist_group(name="test_security_limits_env_vars")
class TestMainSettingsEnvVars:
    """Tests for main Settings reading security limits from environment."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_main_settings_max_connections_per_user_from_env(self) -> None:
        """
        GIVEN STREAMING_MAX_CONNECTIONS_PER_USER environment variable set
        WHEN Settings is created
        THEN should use the environment variable value.
        """
        with patch.dict(os.environ, {"STREAMING_MAX_CONNECTIONS_PER_USER": "25"}):
            from mcp_server_langgraph.core.config import Settings

            settings = Settings()
            assert settings.streaming_max_connections_per_user == 25

    def test_main_settings_max_message_size_from_env(self) -> None:
        """
        GIVEN STREAMING_MAX_MESSAGE_SIZE environment variable set
        WHEN Settings is created
        THEN should use the environment variable value.
        """
        with patch.dict(os.environ, {"STREAMING_MAX_MESSAGE_SIZE": "10000000"}):
            from mcp_server_langgraph.core.config import Settings

            settings = Settings()
            assert settings.streaming_max_message_size == 10_000_000


@pytest.mark.xdist_group(name="test_security_limits_env_vars")
class TestEnvVarsFlowThroughBootstrap:
    """Tests for environment variables flowing through bootstrap to global singletons."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_connection_limit_from_env_flows_to_global(self) -> None:
        """
        GIVEN custom connection limit via environment variable
        WHEN bootstrap initializes websocket lifecycle
        THEN global connection_manager should use the configured limit.
        """
        from mcp_server_langgraph.bootstrap.websocket import init_websocket_lifecycle
        from mcp_server_langgraph.api.v1.mcp_websocket import get_connection_manager
        from mcp_server_langgraph.core.config.streaming import StreamingSettings

        # Create settings with custom limit (simulating env var)
        settings = StreamingSettings(
            streaming_max_connections_per_user=30,
        )

        state = await init_websocket_lifecycle(streaming_settings=settings)

        try:
            manager = get_connection_manager()
            assert manager.max_connections_per_user == 30
        finally:
            await state.cleanup()

    @pytest.mark.asyncio
    async def test_rate_limit_from_env_flows_to_global(self) -> None:
        """
        GIVEN custom rate limit via environment variable
        WHEN bootstrap initializes websocket lifecycle
        THEN global user_rate_limiter should use the configured limit.
        """
        from mcp_server_langgraph.bootstrap.websocket import init_websocket_lifecycle
        from mcp_server_langgraph.api.v1.mcp_websocket import get_user_rate_limiter
        from mcp_server_langgraph.core.config.streaming import StreamingSettings

        # Create settings with custom limit (simulating env var)
        settings = StreamingSettings(
            streaming_max_messages_per_minute=2500,
        )

        state = await init_websocket_lifecycle(streaming_settings=settings)

        try:
            limiter = get_user_rate_limiter()
            assert limiter.max_messages == 2500
        finally:
            await state.cleanup()
