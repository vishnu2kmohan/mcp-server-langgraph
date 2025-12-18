"""
Configurable Security Limits Tests

TDD RED Phase: Tests for verifying security limits are configurable via settings.
These limits were previously hardcoded in mcp_websocket.py.
"""

from __future__ import annotations

import gc
from unittest.mock import MagicMock

import pytest


pytestmark = [
    pytest.mark.unit,
    pytest.mark.api,
    pytest.mark.websocket,
]


@pytest.mark.xdist_group(name="test_configurable_security_limits")
class TestStreamingSettingsSecurityFields:
    """Tests for security limit fields in StreamingSettings."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_streaming_settings_has_max_connections_per_user(self) -> None:
        """
        GIVEN StreamingSettings
        WHEN checking attributes
        THEN should have streaming_max_connections_per_user field.
        """
        from mcp_server_langgraph.core.config.streaming import StreamingSettings

        settings = StreamingSettings()
        assert hasattr(settings, "streaming_max_connections_per_user")
        assert isinstance(settings.streaming_max_connections_per_user, int)
        assert settings.streaming_max_connections_per_user == 5  # Default

    def test_streaming_settings_has_max_message_size(self) -> None:
        """
        GIVEN StreamingSettings
        WHEN checking attributes
        THEN should have streaming_max_message_size field.
        """
        from mcp_server_langgraph.core.config.streaming import StreamingSettings

        settings = StreamingSettings()
        assert hasattr(settings, "streaming_max_message_size")
        assert isinstance(settings.streaming_max_message_size, int)
        assert settings.streaming_max_message_size == 1_000_000  # Default 1MB

    def test_streaming_settings_has_max_messages_per_minute(self) -> None:
        """
        GIVEN StreamingSettings
        WHEN checking attributes
        THEN should have streaming_max_messages_per_minute field.
        """
        from mcp_server_langgraph.core.config.streaming import StreamingSettings

        settings = StreamingSettings()
        assert hasattr(settings, "streaming_max_messages_per_minute")
        assert isinstance(settings.streaming_max_messages_per_minute, int)
        assert settings.streaming_max_messages_per_minute == 600  # Default

    def test_streaming_settings_has_idle_timeout_seconds(self) -> None:
        """
        GIVEN StreamingSettings
        WHEN checking attributes
        THEN should have streaming_idle_timeout_seconds field.
        """
        from mcp_server_langgraph.core.config.streaming import StreamingSettings

        settings = StreamingSettings()
        assert hasattr(settings, "streaming_idle_timeout_seconds")
        assert isinstance(settings.streaming_idle_timeout_seconds, int)
        assert settings.streaming_idle_timeout_seconds == 1800  # Default 30 min

    def test_streaming_settings_security_limits_configurable(self) -> None:
        """
        GIVEN StreamingSettings with custom security limits
        WHEN checking values
        THEN should use configured values.
        """
        from mcp_server_langgraph.core.config.streaming import StreamingSettings

        settings = StreamingSettings(
            streaming_max_connections_per_user=10,
            streaming_max_message_size=2_000_000,
            streaming_max_messages_per_minute=1200,
            streaming_idle_timeout_seconds=3600,
        )

        assert settings.streaming_max_connections_per_user == 10
        assert settings.streaming_max_message_size == 2_000_000
        assert settings.streaming_max_messages_per_minute == 1200
        assert settings.streaming_idle_timeout_seconds == 3600


@pytest.mark.xdist_group(name="test_configurable_security_limits")
class TestMainSettingsSecurityFields:
    """Tests for security limit fields in main Settings class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_main_settings_has_security_limit_fields(self) -> None:
        """
        GIVEN main Settings class
        WHEN checking attributes
        THEN should have all security limit fields.
        """
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()

        assert hasattr(settings, "streaming_max_connections_per_user")
        assert hasattr(settings, "streaming_max_message_size")
        assert hasattr(settings, "streaming_max_messages_per_minute")
        assert hasattr(settings, "streaming_idle_timeout_seconds")


@pytest.mark.xdist_group(name="test_configurable_security_limits")
class TestSecurityLimitsUsage:
    """Tests for security limits being used in mcp_websocket module."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_connection_manager_accepts_max_connections(self) -> None:
        """
        GIVEN ConnectionManager
        WHEN constructed
        THEN should accept max_connections_per_user parameter.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import ConnectionManager

        manager = ConnectionManager(max_connections_per_user=10)
        assert manager.max_connections_per_user == 10

    def test_connection_manager_uses_configured_limit(self) -> None:
        """
        GIVEN ConnectionManager with custom limit
        WHEN checking if user can connect
        THEN should use configured limit.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import ConnectionManager

        manager = ConnectionManager(max_connections_per_user=2)

        # Simulate 2 connections for user
        manager._user_connections["user:test"] = ["session1", "session2"]

        # Should not allow 3rd connection
        assert not manager.can_user_connect("user:test")

        # With default limit of 5, should allow
        default_manager = ConnectionManager()
        default_manager._user_connections["user:test"] = ["session1", "session2"]
        assert default_manager.can_user_connect("user:test")

    def test_validate_message_size_accepts_custom_limit(self) -> None:
        """
        GIVEN validate_message_size function
        WHEN called with custom limit
        THEN should use that limit.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import validate_message_size

        # Test with 100 byte limit
        assert validate_message_size("x" * 50, max_size=100) is True
        assert validate_message_size("x" * 150, max_size=100) is False

    def test_user_rate_limiter_accepts_custom_rate(self) -> None:
        """
        GIVEN UserRateLimiterManager
        WHEN constructed with custom rate
        THEN should use that rate.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import UserRateLimiterManager

        limiter = UserRateLimiterManager(max_messages=100, window_seconds=60)
        assert limiter.max_messages == 100

    def test_is_connection_idle_accepts_custom_timeout(self) -> None:
        """
        GIVEN is_connection_idle function
        WHEN called with custom timeout
        THEN should use that timeout.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            ConnectionInfo,
            is_connection_idle,
        )
        from datetime import datetime, timedelta, UTC

        mock_ws = MagicMock()

        # Connection that's 10 minutes old
        conn_info = ConnectionInfo(
            websocket=mock_ws,
            session_id="test",
            last_activity=datetime.now(UTC) - timedelta(minutes=10),
        )

        # With 5 minute timeout, should be idle
        assert is_connection_idle(conn_info, timeout_seconds=300) is True

        # With 30 minute timeout, should NOT be idle
        assert is_connection_idle(conn_info, timeout_seconds=1800) is False


@pytest.mark.xdist_group(name="test_configurable_security_limits")
class TestSecureMessageProcessorConfigurable:
    """Tests for SecureMessageProcessor using configurable limits."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_secure_processor_accepts_max_message_size(self) -> None:
        """
        GIVEN SecureMessageProcessor
        WHEN constructed
        THEN should accept max_message_size parameter.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import SecureMessageProcessor

        processor = SecureMessageProcessor(
            session_id="test",
            max_message_size=500_000,
        )

        assert processor.max_message_size == 500_000

    def test_secure_processor_validates_with_custom_size(self) -> None:
        """
        GIVEN SecureMessageProcessor with custom message size
        WHEN validating message
        THEN should use custom limit.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import SecureMessageProcessor

        processor = SecureMessageProcessor(
            session_id="test",
            max_message_size=100,  # Very small for testing
        )

        # Small message should pass
        result = processor.validate_incoming("x" * 50)
        assert result.is_valid

        # Large message should fail
        result = processor.validate_incoming("x" * 150)
        assert not result.is_valid
        assert "size" in result.error_message.lower()


@pytest.mark.xdist_group(name="test_configurable_security_limits")
class TestBootstrapSecurityLimitsWiring:
    """Tests for security limits wiring through bootstrap."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_streaming_settings_extracts_all_security_limits(self) -> None:
        """
        GIVEN main Settings with custom security limits
        WHEN StreamingSettings is constructed
        THEN should contain all security limits.
        """
        from mcp_server_langgraph.core.config.streaming import StreamingSettings

        settings = StreamingSettings(
            streaming_max_connections_per_user=8,
            streaming_max_message_size=500_000,
            streaming_max_messages_per_minute=300,
            streaming_idle_timeout_seconds=900,
        )

        assert settings.streaming_max_connections_per_user == 8
        assert settings.streaming_max_message_size == 500_000
        assert settings.streaming_max_messages_per_minute == 300
        assert settings.streaming_idle_timeout_seconds == 900
