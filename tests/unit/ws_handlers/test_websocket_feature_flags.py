"""
WebSocket Feature Flags Tests.

TDD tests for WebSocket infrastructure feature flags integration.
"""

from __future__ import annotations

import gc
import os
from unittest.mock import patch

import pytest

from mcp_server_langgraph.core.feature_flags import FeatureFlags, get_feature_flags

pytestmark = [pytest.mark.unit, pytest.mark.websocket, pytest.mark.feature_flags]


@pytest.mark.xdist_group(name="websocket_feature_flags")
class TestWebSocketFeatureFlags:
    """Test WebSocket feature flag definitions and defaults."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_websocket_new_base_flag_exists(self) -> None:
        """
        GIVEN the FeatureFlags class
        WHEN checking for enable_websocket_new_base
        THEN it should exist and default to True.
        """
        flags = FeatureFlags()
        assert hasattr(flags, "enable_websocket_new_base")
        assert flags.enable_websocket_new_base is True

    def test_websocket_server_heartbeat_flag_exists(self) -> None:
        """
        GIVEN the FeatureFlags class
        WHEN checking for enable_websocket_server_heartbeat
        THEN it should exist and default to True.
        """
        flags = FeatureFlags()
        assert hasattr(flags, "enable_websocket_server_heartbeat")
        assert flags.enable_websocket_server_heartbeat is True

    def test_websocket_enhanced_metrics_flag_exists(self) -> None:
        """
        GIVEN the FeatureFlags class
        WHEN checking for enable_websocket_enhanced_metrics
        THEN it should exist and default to True.
        """
        flags = FeatureFlags()
        assert hasattr(flags, "enable_websocket_enhanced_metrics")
        assert flags.enable_websocket_enhanced_metrics is True

    def test_websocket_heartbeat_interval_setting(self) -> None:
        """
        GIVEN the FeatureFlags class
        WHEN checking websocket_heartbeat_interval_seconds
        THEN it should exist with correct default and constraints.
        """
        flags = FeatureFlags()
        assert hasattr(flags, "websocket_heartbeat_interval_seconds")
        assert flags.websocket_heartbeat_interval_seconds == 30

    def test_websocket_idle_timeout_setting(self) -> None:
        """
        GIVEN the FeatureFlags class
        WHEN checking websocket_idle_timeout_seconds
        THEN it should exist with correct default (30 min).
        """
        flags = FeatureFlags()
        assert hasattr(flags, "websocket_idle_timeout_seconds")
        assert flags.websocket_idle_timeout_seconds == 1800

    def test_websocket_rate_limit_setting(self) -> None:
        """
        GIVEN the FeatureFlags class
        WHEN checking websocket_rate_limit_per_minute
        THEN it should exist with correct default.
        """
        flags = FeatureFlags()
        assert hasattr(flags, "websocket_rate_limit_per_minute")
        assert flags.websocket_rate_limit_per_minute == 600

    def test_websocket_flags_in_ui_features(self) -> None:
        """
        GIVEN the FeatureFlags class
        WHEN getting UI features for a role
        THEN WebSocket flags should be included.
        """
        flags = FeatureFlags()
        ui_features = flags.get_ui_features_for_role("user")

        assert "websocket_new_base" in ui_features
        assert "websocket_server_heartbeat" in ui_features
        assert "websocket_enhanced_metrics" in ui_features

    def test_websocket_flags_can_be_disabled_via_env(self) -> None:
        """
        GIVEN environment variables to disable flags
        WHEN creating FeatureFlags
        THEN flags should be disabled.
        """
        with patch.dict(
            os.environ,
            {
                "FF_ENABLE_WEBSOCKET_NEW_BASE": "false",
                "FF_ENABLE_WEBSOCKET_SERVER_HEARTBEAT": "false",
            },
        ):
            flags = FeatureFlags()
            assert flags.enable_websocket_new_base is False
            assert flags.enable_websocket_server_heartbeat is False

    def test_websocket_heartbeat_interval_can_be_configured(self) -> None:
        """
        GIVEN environment variable for heartbeat interval
        WHEN creating FeatureFlags
        THEN the interval should be customized.
        """
        with patch.dict(
            os.environ,
            {"FF_WEBSOCKET_HEARTBEAT_INTERVAL_SECONDS": "60"},
        ):
            flags = FeatureFlags()
            assert flags.websocket_heartbeat_interval_seconds == 60

    def test_global_feature_flags_instance(self) -> None:
        """
        GIVEN the global feature flags getter
        WHEN calling get_feature_flags
        THEN it should return a FeatureFlags instance.
        """
        flags = get_feature_flags()
        assert isinstance(flags, FeatureFlags)
        assert hasattr(flags, "enable_websocket_new_base")
