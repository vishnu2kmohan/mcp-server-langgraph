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
