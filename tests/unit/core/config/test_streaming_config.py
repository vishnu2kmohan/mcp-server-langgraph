"""
Tests for streaming configuration module.

TDD RED Phase: These tests define the expected behavior for streaming config.
"""

import gc

import pytest

pytestmark = [
    pytest.mark.unit,
]


@pytest.mark.xdist_group(name="test_streaming_config")
class TestStreamingConfigImports:
    """Tests for streaming configuration imports."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_streaming_settings_class_exists(self) -> None:
        """
        GIVEN the config package
        WHEN importing StreamingSettings
        THEN should find the class.
        """
        from mcp_server_langgraph.core.config.streaming import StreamingSettings

        assert StreamingSettings is not None

    def test_streaming_settings_is_domain_settings(self) -> None:
        """
        GIVEN StreamingSettings class
        WHEN checking inheritance
        THEN should extend DomainSettings.
        """
        from mcp_server_langgraph.core.config.base import DomainSettings
        from mcp_server_langgraph.core.config.streaming import StreamingSettings

        assert issubclass(StreamingSettings, DomainSettings)

    def test_streaming_settings_importable_from_package(self) -> None:
        """
        GIVEN the config package __init__.py
        WHEN importing StreamingSettings
        THEN should be available.
        """
        from mcp_server_langgraph.core.config import StreamingSettings

        assert StreamingSettings is not None


@pytest.mark.xdist_group(name="test_streaming_config")
class TestStreamingConfigDefaults:
    """Tests for streaming configuration default values."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_streaming_metrics_cleanup_interval_default(self) -> None:
        """
        GIVEN StreamingSettings with no overrides
        WHEN checking streaming_metrics_cleanup_interval
        THEN should default to 300 seconds (5 minutes).
        """
        from mcp_server_langgraph.core.config.streaming import StreamingSettings

        settings = StreamingSettings()
        assert settings.streaming_metrics_cleanup_interval == 300

    def test_streaming_max_age_seconds_default(self) -> None:
        """
        GIVEN StreamingSettings with no overrides
        WHEN checking streaming_max_age_seconds
        THEN should default to 3600 seconds (1 hour).
        """
        from mcp_server_langgraph.core.config.streaming import StreamingSettings

        settings = StreamingSettings()
        assert settings.streaming_max_age_seconds == 3600

    def test_streaming_idle_connection_cleanup_interval_default(self) -> None:
        """
        GIVEN StreamingSettings with no overrides
        WHEN checking streaming_idle_cleanup_interval
        THEN should default to 60 seconds.
        """
        from mcp_server_langgraph.core.config.streaming import StreamingSettings

        settings = StreamingSettings()
        assert settings.streaming_idle_cleanup_interval == 60

    def test_streaming_max_chunk_size_default(self) -> None:
        """
        GIVEN StreamingSettings with no overrides
        WHEN checking streaming_max_chunk_size
        THEN should default to 65536 bytes (64KB).
        """
        from mcp_server_langgraph.core.config.streaming import StreamingSettings

        settings = StreamingSettings()
        assert settings.streaming_max_chunk_size == 65536

    def test_streaming_enabled_default(self) -> None:
        """
        GIVEN StreamingSettings with no overrides
        WHEN checking streaming_enabled
        THEN should default to True.
        """
        from mcp_server_langgraph.core.config.streaming import StreamingSettings

        settings = StreamingSettings()
        assert settings.streaming_enabled is True


@pytest.mark.xdist_group(name="test_streaming_config")
class TestStreamingConfigEnvVars:
    """Tests for streaming configuration from environment variables."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_streaming_metrics_cleanup_interval_from_env(self, monkeypatch) -> None:
        """
        GIVEN STREAMING_METRICS_CLEANUP_INTERVAL env var
        WHEN creating StreamingSettings
        THEN should use the env var value.
        """
        monkeypatch.setenv("STREAMING_METRICS_CLEANUP_INTERVAL", "600")

        from mcp_server_langgraph.core.config.streaming import StreamingSettings

        settings = StreamingSettings()
        assert settings.streaming_metrics_cleanup_interval == 600

    def test_streaming_max_age_seconds_from_env(self, monkeypatch) -> None:
        """
        GIVEN STREAMING_MAX_AGE_SECONDS env var
        WHEN creating StreamingSettings
        THEN should use the env var value.
        """
        monkeypatch.setenv("STREAMING_MAX_AGE_SECONDS", "7200")

        from mcp_server_langgraph.core.config.streaming import StreamingSettings

        settings = StreamingSettings()
        assert settings.streaming_max_age_seconds == 7200

    def test_streaming_idle_cleanup_interval_from_env(self, monkeypatch) -> None:
        """
        GIVEN STREAMING_IDLE_CLEANUP_INTERVAL env var
        WHEN creating StreamingSettings
        THEN should use the env var value.
        """
        monkeypatch.setenv("STREAMING_IDLE_CLEANUP_INTERVAL", "120")

        from mcp_server_langgraph.core.config.streaming import StreamingSettings

        settings = StreamingSettings()
        assert settings.streaming_idle_cleanup_interval == 120

    def test_streaming_enabled_from_env(self, monkeypatch) -> None:
        """
        GIVEN STREAMING_ENABLED env var set to false
        WHEN creating StreamingSettings
        THEN should disable streaming.
        """
        monkeypatch.setenv("STREAMING_ENABLED", "false")

        from mcp_server_langgraph.core.config.streaming import StreamingSettings

        settings = StreamingSettings()
        assert settings.streaming_enabled is False


@pytest.mark.xdist_group(name="test_streaming_config")
class TestStreamingSettingsIntegration:
    """Tests for streaming settings integration with main Settings."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_main_settings_has_streaming_config(self) -> None:
        """
        GIVEN the main Settings class
        WHEN checking for streaming attributes
        THEN should have streaming configuration fields.
        """
        from mcp_server_langgraph.core.config import Settings

        s = Settings()

        # These should be accessible on main settings
        assert hasattr(s, "streaming_metrics_cleanup_interval")
        assert hasattr(s, "streaming_max_age_seconds")
        assert hasattr(s, "streaming_idle_cleanup_interval")
        assert hasattr(s, "streaming_enabled")

    def test_main_settings_streaming_defaults(self) -> None:
        """
        GIVEN the main Settings class
        WHEN checking streaming defaults
        THEN should have correct default values.
        """
        from mcp_server_langgraph.core.config import Settings

        s = Settings()

        assert s.streaming_metrics_cleanup_interval == 300
        assert s.streaming_max_age_seconds == 3600
        assert s.streaming_idle_cleanup_interval == 60
        assert s.streaming_enabled is True


@pytest.mark.xdist_group(name="test_streaming_config")
class TestTokenValidationIntervalConfig:
    """Tests for token validation interval configuration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_streaming_token_validation_interval_default(self) -> None:
        """
        GIVEN StreamingSettings with no overrides
        WHEN checking streaming_token_validation_interval
        THEN should default to 300 seconds (5 minutes).
        """
        from mcp_server_langgraph.core.config.streaming import StreamingSettings

        settings = StreamingSettings()
        assert settings.streaming_token_validation_interval == 300

    def test_streaming_token_validation_interval_from_env(self, monkeypatch) -> None:
        """
        GIVEN STREAMING_TOKEN_VALIDATION_INTERVAL env var
        WHEN creating StreamingSettings
        THEN should use the env var value.
        """
        monkeypatch.setenv("STREAMING_TOKEN_VALIDATION_INTERVAL", "120")

        from mcp_server_langgraph.core.config.streaming import StreamingSettings

        settings = StreamingSettings()
        assert settings.streaming_token_validation_interval == 120

    def test_main_settings_has_token_validation_interval(self) -> None:
        """
        GIVEN the main Settings class
        WHEN checking for token_validation_interval attribute
        THEN should have the field.
        """
        from mcp_server_langgraph.core.config import Settings

        s = Settings()
        assert hasattr(s, "streaming_token_validation_interval")
        assert s.streaming_token_validation_interval == 300


@pytest.mark.xdist_group(name="test_streaming_config")
class TestTokenValidationIntervalGlobal:
    """Tests for global token validation interval getter/setter."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_token_validation_interval_default(self) -> None:
        """
        GIVEN no explicit configuration
        WHEN getting token_validation_interval
        THEN should return default (300 seconds).
        """
        from mcp_server_langgraph.mcp.websocket.config import (
            get_token_validation_interval,
        )

        # Default should be 300 seconds
        assert get_token_validation_interval() == 300

    def test_set_token_validation_interval(self) -> None:
        """
        GIVEN a custom interval value
        WHEN setting token_validation_interval
        THEN get should return the custom value.
        """
        from mcp_server_langgraph.mcp.websocket.config import (
            get_token_validation_interval,
            set_token_validation_interval,
        )

        # Set custom value
        set_token_validation_interval(120)

        try:
            assert get_token_validation_interval() == 120
        finally:
            # Reset to default
            set_token_validation_interval(300)

    def test_set_token_validation_interval_zero_disables(self) -> None:
        """
        GIVEN interval set to 0
        WHEN getting token_validation_interval
        THEN should return 0 (disabled).
        """
        from mcp_server_langgraph.mcp.websocket.config import (
            get_token_validation_interval,
            set_token_validation_interval,
        )

        set_token_validation_interval(0)

        try:
            assert get_token_validation_interval() == 0
        finally:
            # Reset to default
            set_token_validation_interval(300)


@pytest.mark.xdist_group(name="test_streaming_config")
class TestCreateWebSocketConfigFactory:
    """Tests for create_websocket_config factory function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_websocket_config_uses_global_interval(self) -> None:
        """
        GIVEN global token_validation_interval set to 120
        WHEN creating WebSocketConfig via factory
        THEN should use the global value.
        """
        from mcp_server_langgraph.mcp.websocket.config import (
            create_websocket_config,
            set_token_validation_interval,
        )

        set_token_validation_interval(120)

        try:
            config = create_websocket_config(endpoint_name="test")
            assert config.token_validation_interval == 120
        finally:
            set_token_validation_interval(300)

    def test_create_websocket_config_allows_override(self) -> None:
        """
        GIVEN explicit token_validation_interval
        WHEN creating WebSocketConfig via factory
        THEN should use the explicit value.
        """
        from mcp_server_langgraph.mcp.websocket.config import (
            create_websocket_config,
            set_token_validation_interval,
        )

        set_token_validation_interval(120)

        try:
            config = create_websocket_config(
                endpoint_name="test",
                token_validation_interval=60,  # Explicit override
            )
            assert config.token_validation_interval == 60
        finally:
            set_token_validation_interval(300)

    def test_create_websocket_config_sets_other_fields(self) -> None:
        """
        GIVEN create_websocket_config call
        WHEN specifying custom fields
        THEN should set them correctly.
        """
        from mcp_server_langgraph.mcp.websocket.config import create_websocket_config

        config = create_websocket_config(
            endpoint_name="notifications",
            require_auth=True,
            rate_limit_per_minute=300,
        )

        assert config.endpoint_name == "notifications"
        assert config.require_auth is True
        assert config.rate_limit_per_minute == 300
