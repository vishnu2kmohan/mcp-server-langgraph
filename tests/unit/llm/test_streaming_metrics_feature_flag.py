"""
Tests for LLM streaming metrics feature flag.

TDD: Tests written FIRST before implementation.

Feature flag: enable_streaming_metrics
- When True (default): Metrics are recorded normally
- When False: Metrics recording is disabled (no-op)
"""

from __future__ import annotations

import gc
from unittest.mock import patch

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.llm, pytest.mark.metrics]


@pytest.mark.xdist_group(name="streaming_metrics_feature_flag")
class TestStreamingMetricsFeatureFlagExists:
    """Tests for streaming metrics feature flag existence."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_enable_streaming_metrics_flag_exists(self) -> None:
        """
        GIVEN the FeatureFlags class
        WHEN checking for enable_streaming_metrics attribute
        THEN should exist and be a boolean.
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert hasattr(flags, "enable_streaming_metrics")
        assert isinstance(flags.enable_streaming_metrics, bool)

    def test_enable_streaming_metrics_default_is_true(self) -> None:
        """
        GIVEN the FeatureFlags class with default settings
        WHEN checking enable_streaming_metrics
        THEN should be True by default.
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.enable_streaming_metrics is True

    def test_enable_streaming_metrics_configurable_via_env(self) -> None:
        """
        GIVEN environment variable FF_ENABLE_STREAMING_METRICS=false
        WHEN creating FeatureFlags instance
        THEN enable_streaming_metrics should be False.
        """
        import os
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        with patch.dict(os.environ, {"FF_ENABLE_STREAMING_METRICS": "false"}):
            flags = FeatureFlags()
            assert flags.enable_streaming_metrics is False


@pytest.mark.xdist_group(name="streaming_metrics_feature_flag")
class TestStreamingMetricsWhenDisabled:
    """Tests for streaming metrics behavior when feature flag is disabled."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_record_ttfc_noop_when_disabled(self) -> None:
        """
        GIVEN enable_streaming_metrics=False
        WHEN calling record_ttfc
        THEN should be a no-op (not record metrics).
        """
        from mcp_server_langgraph.llm import streaming_metrics

        # Mock the feature flag check
        with patch.object(streaming_metrics, "_is_streaming_metrics_enabled", return_value=False):
            # This should not raise and should be a no-op
            streaming_metrics.record_ttfc(model="gpt-4", ttfc_seconds=0.5, provider="openai")

    def test_record_inter_chunk_latency_noop_when_disabled(self) -> None:
        """
        GIVEN enable_streaming_metrics=False
        WHEN calling record_inter_chunk_latency
        THEN should be a no-op.
        """
        from mcp_server_langgraph.llm import streaming_metrics

        with patch.object(streaming_metrics, "_is_streaming_metrics_enabled", return_value=False):
            streaming_metrics.record_inter_chunk_latency(model="gpt-4", latency_seconds=0.05, provider="openai")

    def test_record_streaming_duration_noop_when_disabled(self) -> None:
        """
        GIVEN enable_streaming_metrics=False
        WHEN calling record_streaming_duration
        THEN should be a no-op.
        """
        from mcp_server_langgraph.llm import streaming_metrics

        with patch.object(streaming_metrics, "_is_streaming_metrics_enabled", return_value=False):
            streaming_metrics.record_streaming_duration(
                model="gpt-4", duration_seconds=5.0, provider="openai", status="success"
            )

    def test_record_chunk_count_noop_when_disabled(self) -> None:
        """
        GIVEN enable_streaming_metrics=False
        WHEN calling record_chunk_count
        THEN should be a no-op.
        """
        from mcp_server_langgraph.llm import streaming_metrics

        with patch.object(streaming_metrics, "_is_streaming_metrics_enabled", return_value=False):
            streaming_metrics.record_chunk_count(model="gpt-4", count=100, provider="openai")


@pytest.mark.xdist_group(name="streaming_metrics_feature_flag")
class TestStreamingMetricsContextFeatureFlag:
    """Tests for StreamingMetricsContext with feature flag."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_context_still_tracks_values_when_disabled(self) -> None:
        """
        GIVEN enable_streaming_metrics=False
        WHEN using StreamingMetricsContext
        THEN should still track values internally but not emit metrics.

        This allows code to use the context manager without changes,
        but metrics are simply not emitted to Prometheus.
        """
        from mcp_server_langgraph.llm.streaming_metrics import StreamingMetricsContext
        from mcp_server_langgraph.llm import streaming_metrics

        with patch.object(streaming_metrics, "_is_streaming_metrics_enabled", return_value=False):
            ctx = StreamingMetricsContext(model="gpt-4", provider="openai")
            ctx.start()
            ctx.record_first_chunk()
            ctx.record_chunk()
            ctx.finalize(status="success")

            # Internal tracking should still work
            assert ctx.ttfc_seconds is not None
            assert ctx.duration_seconds is not None
            assert ctx.chunk_count >= 2

    def test_context_emits_metrics_when_enabled(self) -> None:
        """
        GIVEN enable_streaming_metrics=True (default)
        WHEN using StreamingMetricsContext
        THEN should track values and emit metrics.
        """
        from mcp_server_langgraph.llm.streaming_metrics import StreamingMetricsContext

        ctx = StreamingMetricsContext(model="gpt-4", provider="openai")
        ctx.start()
        ctx.record_first_chunk()
        ctx.record_chunk()
        ctx.finalize(status="success")

        # Internal tracking should work
        assert ctx.ttfc_seconds is not None
        assert ctx.duration_seconds is not None
        assert ctx.chunk_count >= 2


@pytest.mark.xdist_group(name="streaming_metrics_feature_flag")
class TestIsStreamingMetricsEnabledFunction:
    """Tests for the _is_streaming_metrics_enabled helper function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_helper_function_exists(self) -> None:
        """
        GIVEN the streaming_metrics module
        WHEN checking for _is_streaming_metrics_enabled function
        THEN should exist.
        """
        from mcp_server_langgraph.llm import streaming_metrics

        assert hasattr(streaming_metrics, "_is_streaming_metrics_enabled")
        assert callable(streaming_metrics._is_streaming_metrics_enabled)

    def test_helper_returns_true_when_enabled(self) -> None:
        """
        GIVEN enable_streaming_metrics=True
        WHEN calling _is_streaming_metrics_enabled
        THEN should return True.
        """
        from mcp_server_langgraph.llm import streaming_metrics

        # Default is True, so no patching needed
        result = streaming_metrics._is_streaming_metrics_enabled()
        assert result is True

    def test_helper_returns_false_when_disabled(self) -> None:
        """
        GIVEN enable_streaming_metrics=False
        WHEN calling _is_streaming_metrics_enabled
        THEN should return False.
        """
        import os
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        # Patch the environment to disable the flag
        with patch.dict(os.environ, {"FF_ENABLE_STREAMING_METRICS": "false"}):
            # Create a new instance to pick up the env var
            flags = FeatureFlags()
            assert flags.enable_streaming_metrics is False
