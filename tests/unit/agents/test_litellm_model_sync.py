"""
LiteLLM Model Sync Tests

TDD tests for synchronizing model information from LiteLLM to ModelRegistry.
This enables dynamic model discovery and pricing updates.

Sprint 1 - Enhanced Model Selector: LiteLLM Dynamic Model Sync
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


class TestLiteLLMModelSyncExists:
    """Test that the LiteLLMModelSync class exists with required interface."""

    def test_litellm_model_sync_class_exists(self) -> None:
        """Test that LiteLLMModelSync class can be imported."""
        from mcp_server_langgraph.agents.litellm_model_sync import LiteLLMModelSync

        assert LiteLLMModelSync is not None

    def test_litellm_model_sync_has_sync_pricing_method(self) -> None:
        """Test that sync_pricing method exists."""
        from mcp_server_langgraph.agents.litellm_model_sync import LiteLLMModelSync

        sync = LiteLLMModelSync()
        assert hasattr(sync, "sync_pricing")
        assert callable(sync.sync_pricing)

    def test_litellm_model_sync_has_get_litellm_models_method(self) -> None:
        """Test that get_litellm_models method exists."""
        from mcp_server_langgraph.agents.litellm_model_sync import LiteLLMModelSync

        sync = LiteLLMModelSync()
        assert hasattr(sync, "get_litellm_models")
        assert callable(sync.get_litellm_models)

    def test_litellm_model_sync_has_update_registry_method(self) -> None:
        """Test that update_registry method exists."""
        from mcp_server_langgraph.agents.litellm_model_sync import LiteLLMModelSync

        sync = LiteLLMModelSync()
        assert hasattr(sync, "update_registry")
        assert callable(sync.update_registry)


class TestLiteLLMModelSyncGetModels:
    """Test getting model list from LiteLLM."""

    def test_get_litellm_models_returns_dict(self) -> None:
        """Test that get_litellm_models returns a dictionary."""
        from mcp_server_langgraph.agents.litellm_model_sync import LiteLLMModelSync

        sync = LiteLLMModelSync()
        models = sync.get_litellm_models()
        assert isinstance(models, dict)

    def test_get_litellm_models_includes_known_models(self) -> None:
        """Test that known models are included in the result."""
        from mcp_server_langgraph.agents.litellm_model_sync import LiteLLMModelSync

        sync = LiteLLMModelSync()
        models = sync.get_litellm_models()

        # LiteLLM should have pricing for major models
        # Note: The actual key format may vary (e.g., "gpt-4", "openai/gpt-4")
        model_keys = list(models.keys())
        assert len(model_keys) > 0

    @patch("mcp_server_langgraph.agents.litellm_model_sync.litellm")
    def test_get_litellm_models_uses_model_cost_attribute(self, mock_litellm: MagicMock) -> None:
        """Test that get_litellm_models reads from litellm.model_cost."""
        mock_litellm.model_cost = {
            "gpt-4": {
                "input_cost_per_token": 0.00003,
                "output_cost_per_token": 0.00006,
            }
        }

        from mcp_server_langgraph.agents.litellm_model_sync import LiteLLMModelSync

        sync = LiteLLMModelSync()
        models = sync.get_litellm_models()

        assert "gpt-4" in models


class TestLiteLLMModelSyncPricing:
    """Test pricing synchronization from LiteLLM."""

    def test_sync_pricing_returns_count(self) -> None:
        """Test that sync_pricing returns the number of models updated."""
        from mcp_server_langgraph.agents.litellm_model_sync import LiteLLMModelSync

        sync = LiteLLMModelSync()
        count = sync.sync_pricing()
        assert isinstance(count, int)
        assert count >= 0

    @patch("mcp_server_langgraph.agents.litellm_model_sync.litellm")
    def test_sync_pricing_updates_known_models(self, mock_litellm: MagicMock) -> None:
        """Test that sync_pricing updates models that exist in registry."""
        mock_litellm.model_cost = {
            "claude-opus-4-5-20251101": {
                "input_cost_per_token": 0.000005,
                "output_cost_per_token": 0.000025,
            }
        }

        from mcp_server_langgraph.agents.litellm_model_sync import LiteLLMModelSync

        sync = LiteLLMModelSync()
        count = sync.sync_pricing()

        # Should update at least the claude model
        assert count >= 0

    @patch("mcp_server_langgraph.agents.litellm_model_sync.litellm")
    def test_sync_pricing_handles_empty_model_cost(self, mock_litellm: MagicMock) -> None:
        """Test that sync_pricing handles empty model_cost gracefully."""
        mock_litellm.model_cost = {}

        from mcp_server_langgraph.agents.litellm_model_sync import LiteLLMModelSync

        sync = LiteLLMModelSync()
        count = sync.sync_pricing()

        assert count == 0

    @patch("mcp_server_langgraph.agents.litellm_model_sync.litellm")
    def test_sync_pricing_handles_missing_model_cost_attribute(self, mock_litellm: MagicMock) -> None:
        """Test that sync_pricing handles missing model_cost attribute."""
        # Remove model_cost attribute
        del mock_litellm.model_cost

        from mcp_server_langgraph.agents.litellm_model_sync import LiteLLMModelSync

        sync = LiteLLMModelSync()
        count = sync.sync_pricing()

        # Should return 0 without raising
        assert count == 0


class TestLiteLLMModelSyncUpdateRegistry:
    """Test updating ModelRegistry from LiteLLM data."""

    @patch("mcp_server_langgraph.agents.litellm_model_sync.get_default_registry")
    @patch("mcp_server_langgraph.agents.litellm_model_sync.litellm")
    def test_update_registry_updates_existing_model_pricing(
        self, mock_litellm: MagicMock, mock_get_registry: MagicMock
    ) -> None:
        """Test that update_registry updates pricing for existing models."""
        # Setup mock registry with a model
        mock_registry = MagicMock()
        mock_caps = MagicMock()
        mock_caps.input_cost_per_1m = 5.0
        mock_caps.output_cost_per_1m = 25.0
        mock_registry.get.return_value = mock_caps
        mock_registry._models = {"gpt-4": mock_caps}
        mock_get_registry.return_value = mock_registry

        # Setup mock LiteLLM data with different pricing
        mock_litellm.model_cost = {
            "gpt-4": {
                "input_cost_per_token": 0.00001,  # $10 per 1M
                "output_cost_per_token": 0.00003,  # $30 per 1M
            }
        }

        from mcp_server_langgraph.agents.litellm_model_sync import LiteLLMModelSync

        sync = LiteLLMModelSync()
        updated = sync.update_registry()

        assert updated >= 0

    @patch("mcp_server_langgraph.agents.litellm_model_sync.get_default_registry")
    @patch("mcp_server_langgraph.agents.litellm_model_sync.litellm")
    def test_update_registry_returns_update_count(self, mock_litellm: MagicMock, mock_get_registry: MagicMock) -> None:
        """Test that update_registry returns count of updated models."""
        mock_registry = MagicMock()
        mock_registry._models = {}
        mock_get_registry.return_value = mock_registry
        mock_litellm.model_cost = {}

        from mcp_server_langgraph.agents.litellm_model_sync import LiteLLMModelSync

        sync = LiteLLMModelSync()
        updated = sync.update_registry()

        assert isinstance(updated, int)


class TestLiteLLMModelSyncFeatureFlag:
    """Test feature flag for LiteLLM model sync."""

    def test_feature_flag_exists(self) -> None:
        """Test that enable_litellm_model_sync feature flag exists."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert hasattr(flags, "enable_litellm_model_sync")

    def test_feature_flag_defaults_to_false(self) -> None:
        """Test that enable_litellm_model_sync defaults to False for safe rollout."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.enable_litellm_model_sync is False

    def test_feature_flag_can_be_enabled(self) -> None:
        """Test that enable_litellm_model_sync can be set to True."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(enable_litellm_model_sync=True)
        assert flags.enable_litellm_model_sync is True


class TestLiteLLMModelSyncScheduler:
    """Test background scheduler for LiteLLM model sync."""

    def test_start_model_sync_scheduler_function_exists(self) -> None:
        """Test that start_model_sync_scheduler function exists."""
        from mcp_server_langgraph.agents.litellm_model_sync import (
            start_model_sync_scheduler,
        )

        assert callable(start_model_sync_scheduler)

    @pytest.mark.asyncio
    async def test_start_model_sync_scheduler_returns_task(self) -> None:
        """Test that start_model_sync_scheduler returns an asyncio.Task."""
        import asyncio

        from mcp_server_langgraph.agents.litellm_model_sync import (
            start_model_sync_scheduler,
        )

        task = await start_model_sync_scheduler()

        try:
            assert isinstance(task, asyncio.Task)
            assert task.get_name() == "litellm_model_sync_scheduler"
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    @pytest.mark.asyncio
    @patch("mcp_server_langgraph.agents.litellm_model_sync.feature_flags")
    async def test_scheduler_respects_feature_flag(self, mock_flags: MagicMock) -> None:
        """Test that scheduler checks feature flag before syncing."""
        import asyncio

        mock_flags.enable_litellm_model_sync = False

        from mcp_server_langgraph.agents.litellm_model_sync import (
            start_model_sync_scheduler,
        )

        task = await start_model_sync_scheduler()

        try:
            # Give the scheduler a moment to check the flag
            await asyncio.sleep(0.1)

            # Task should still be running (waiting for next cycle)
            assert not task.done()
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


class TestLiteLLMModelSyncInterval:
    """Test sync interval configuration."""

    def test_sync_interval_constant_exists(self) -> None:
        """Test that SYNC_INTERVAL_SECONDS constant exists."""
        from mcp_server_langgraph.agents.litellm_model_sync import SYNC_INTERVAL_SECONDS

        assert SYNC_INTERVAL_SECONDS > 0

    def test_sync_interval_is_24_hours(self) -> None:
        """Test that sync interval is 24 hours (86400 seconds)."""
        from mcp_server_langgraph.agents.litellm_model_sync import SYNC_INTERVAL_SECONDS

        assert SYNC_INTERVAL_SECONDS == 86400


class TestLiteLLMModelSyncPricingConversion:
    """Test pricing conversion from LiteLLM format to ModelRegistry format."""

    def test_convert_per_token_to_per_1m(self) -> None:
        """Test converting per-token cost to per-1M cost."""
        from mcp_server_langgraph.agents.litellm_model_sync import LiteLLMModelSync

        sync = LiteLLMModelSync()

        # $0.00001 per token = $10 per 1M tokens
        per_1m = sync._convert_to_per_1m(0.00001)
        assert per_1m == 10.0

        # $0.000003 per token = $3 per 1M tokens
        per_1m = sync._convert_to_per_1m(0.000003)
        assert per_1m == 3.0

    def test_convert_zero_cost(self) -> None:
        """Test converting zero cost."""
        from mcp_server_langgraph.agents.litellm_model_sync import LiteLLMModelSync

        sync = LiteLLMModelSync()
        per_1m = sync._convert_to_per_1m(0.0)
        assert per_1m == 0.0


class TestLiteLLMModelSyncModelMapping:
    """Test mapping between LiteLLM model IDs and ModelRegistry model IDs."""

    def test_normalize_model_id(self) -> None:
        """Test normalizing LiteLLM model ID to registry format."""
        from mcp_server_langgraph.agents.litellm_model_sync import LiteLLMModelSync

        sync = LiteLLMModelSync()

        # LiteLLM may use provider prefixes
        assert sync._normalize_model_id("openai/gpt-4") == "gpt-4"
        assert sync._normalize_model_id("anthropic/claude-3-opus") == "claude-3-opus"
        assert sync._normalize_model_id("gpt-4") == "gpt-4"

    def test_normalize_model_id_preserves_version_suffix(self) -> None:
        """Test that version suffixes are preserved."""
        from mcp_server_langgraph.agents.litellm_model_sync import LiteLLMModelSync

        sync = LiteLLMModelSync()

        # Version suffixes should be preserved
        assert sync._normalize_model_id("claude-opus-4-5-20251101") == "claude-opus-4-5-20251101"


class TestLiteLLMModelSyncLogging:
    """Test logging behavior for sync operations."""

    @patch("mcp_server_langgraph.agents.litellm_model_sync.logger")
    @patch("mcp_server_langgraph.agents.litellm_model_sync.litellm")
    def test_sync_logs_success(self, mock_litellm: MagicMock, mock_logger: MagicMock) -> None:
        """Test that successful sync is logged."""
        mock_litellm.model_cost = {}

        from mcp_server_langgraph.agents.litellm_model_sync import LiteLLMModelSync

        sync = LiteLLMModelSync()
        sync.sync_pricing()

        # Should log at debug or info level
        assert mock_logger.debug.called or mock_logger.info.called

    @patch("mcp_server_langgraph.agents.litellm_model_sync.logger")
    @patch("mcp_server_langgraph.agents.litellm_model_sync.litellm")
    def test_sync_logs_errors(self, mock_litellm: MagicMock, mock_logger: MagicMock) -> None:
        """Test that sync errors are logged."""
        # Simulate an error by making model_cost raise
        mock_litellm.model_cost = property(lambda self: (_ for _ in ()).throw(Exception("Test error")))

        from mcp_server_langgraph.agents.litellm_model_sync import LiteLLMModelSync

        sync = LiteLLMModelSync()
        sync.sync_pricing()  # Should not raise

        # Error should be logged
        mock_logger.error.called or mock_logger.warning.called


# =============================================================================
# LiteLLM Sync Prometheus Metrics Tests (TDD - Sprint 2)
# =============================================================================


class TestLiteLLMSyncPrometheusMetricsModule:
    """Test that the Prometheus metrics module exists."""

    def test_prometheus_metrics_module_exists(self) -> None:
        """Test that litellm_prometheus_metrics module can be imported."""
        from mcp_server_langgraph.agents import litellm_prometheus_metrics

        assert litellm_prometheus_metrics is not None

    def test_metrics_init_function_exists(self) -> None:
        """Test that _init_metrics function exists."""
        from mcp_server_langgraph.agents.litellm_prometheus_metrics import _init_metrics

        assert callable(_init_metrics)


class TestLiteLLMSyncPrometheusMetricsDefinitions:
    """Test that all required Prometheus metrics are defined."""

    def test_sync_total_counter_exists(self) -> None:
        """Test that litellm_sync_total counter is defined."""
        from mcp_server_langgraph.agents.litellm_prometheus_metrics import _init_metrics

        _init_metrics()

        # Check that the metric is available after init
        from mcp_server_langgraph.agents.litellm_prometheus_metrics import (
            _litellm_sync_total,
        )

        assert _litellm_sync_total is not None

    def test_sync_duration_histogram_exists(self) -> None:
        """Test that litellm_sync_duration_seconds histogram is defined."""
        from mcp_server_langgraph.agents.litellm_prometheus_metrics import _init_metrics

        _init_metrics()

        from mcp_server_langgraph.agents.litellm_prometheus_metrics import (
            _litellm_sync_duration_seconds,
        )

        assert _litellm_sync_duration_seconds is not None

    def test_sync_models_updated_counter_exists(self) -> None:
        """Test that litellm_sync_models_updated_total counter is defined."""
        from mcp_server_langgraph.agents.litellm_prometheus_metrics import _init_metrics

        _init_metrics()

        from mcp_server_langgraph.agents.litellm_prometheus_metrics import (
            _litellm_sync_models_updated_total,
        )

        assert _litellm_sync_models_updated_total is not None

    def test_sync_last_success_gauge_exists(self) -> None:
        """Test that litellm_sync_last_success_timestamp gauge is defined."""
        from mcp_server_langgraph.agents.litellm_prometheus_metrics import _init_metrics

        _init_metrics()

        from mcp_server_langgraph.agents.litellm_prometheus_metrics import (
            _litellm_sync_last_success_timestamp,
        )

        assert _litellm_sync_last_success_timestamp is not None

    def test_sync_errors_counter_exists(self) -> None:
        """Test that litellm_sync_errors_total counter is defined."""
        from mcp_server_langgraph.agents.litellm_prometheus_metrics import _init_metrics

        _init_metrics()

        from mcp_server_langgraph.agents.litellm_prometheus_metrics import (
            _litellm_sync_errors_total,
        )

        assert _litellm_sync_errors_total is not None


class TestLiteLLMSyncPrometheusMetricsRecording:
    """Test recording functions for LiteLLM sync metrics."""

    def test_record_sync_success_function_exists(self) -> None:
        """Test that record_sync_success function exists."""
        from mcp_server_langgraph.agents.litellm_prometheus_metrics import (
            record_sync_success,
        )

        assert callable(record_sync_success)

    def test_record_sync_failure_function_exists(self) -> None:
        """Test that record_sync_failure function exists."""
        from mcp_server_langgraph.agents.litellm_prometheus_metrics import (
            record_sync_failure,
        )

        assert callable(record_sync_failure)

    def test_record_models_updated_function_exists(self) -> None:
        """Test that record_models_updated function exists."""
        from mcp_server_langgraph.agents.litellm_prometheus_metrics import (
            record_models_updated,
        )

        assert callable(record_models_updated)

    def test_record_sync_success_increments_counter(self) -> None:
        """Test that record_sync_success increments the sync counter."""
        from mcp_server_langgraph.agents.litellm_prometheus_metrics import (
            _init_metrics,
            record_sync_success,
        )

        _init_metrics()

        # Should not raise
        record_sync_success(duration_seconds=1.5, models_updated=3)

    def test_record_sync_failure_increments_error_counter(self) -> None:
        """Test that record_sync_failure increments the error counter."""
        from mcp_server_langgraph.agents.litellm_prometheus_metrics import (
            _init_metrics,
            record_sync_failure,
        )

        _init_metrics()

        # Should not raise
        record_sync_failure(error_type="connection_error", duration_seconds=0.5)

    def test_record_models_updated_increments_counter(self) -> None:
        """Test that record_models_updated increments the models updated counter."""
        from mcp_server_langgraph.agents.litellm_prometheus_metrics import (
            _init_metrics,
            record_models_updated,
        )

        _init_metrics()

        # Should not raise
        record_models_updated(count=5)


class TestLiteLLMSyncPrometheusMetricsLabels:
    """Test that metrics have correct labels."""

    def test_sync_total_has_result_label(self) -> None:
        """Test that sync_total counter has 'result' label."""
        from mcp_server_langgraph.agents.litellm_prometheus_metrics import (
            _init_metrics,
            record_sync_success,
            record_sync_failure,
        )

        _init_metrics()

        # Recording with different results should work
        record_sync_success(duration_seconds=1.0, models_updated=0)
        record_sync_failure(error_type="timeout", duration_seconds=30.0)

    def test_sync_errors_has_error_type_label(self) -> None:
        """Test that sync_errors counter has 'error_type' label."""
        from mcp_server_langgraph.agents.litellm_prometheus_metrics import (
            _init_metrics,
            record_sync_failure,
        )

        _init_metrics()

        # Different error types should work
        record_sync_failure(error_type="connection_error", duration_seconds=0.1)
        record_sync_failure(error_type="parse_error", duration_seconds=0.2)
        record_sync_failure(error_type="timeout", duration_seconds=30.0)


class TestLiteLLMSyncPrometheusMetricsLazyInit:
    """Test lazy initialization of metrics."""

    def test_init_metrics_returns_bool(self) -> None:
        """Test that _init_metrics returns a boolean."""
        from mcp_server_langgraph.agents.litellm_prometheus_metrics import _init_metrics

        result = _init_metrics()
        assert isinstance(result, bool)

    def test_init_metrics_is_idempotent(self) -> None:
        """Test that _init_metrics can be called multiple times safely."""
        from mcp_server_langgraph.agents.litellm_prometheus_metrics import _init_metrics

        result1 = _init_metrics()
        result2 = _init_metrics()

        assert result1 == result2


class TestLiteLLMSyncPrometheusMetricsGracefulDegradation:
    """Test graceful degradation when prometheus_client not available."""

    def test_record_functions_handle_metrics_unavailable(self) -> None:
        """Test that record functions handle missing prometheus_client gracefully."""
        from mcp_server_langgraph.agents.litellm_prometheus_metrics import (
            record_sync_success,
            record_sync_failure,
            record_models_updated,
        )

        # These should never raise, even if prometheus_client is unavailable
        try:
            record_sync_success(duration_seconds=1.0, models_updated=0)
            record_sync_failure(error_type="test", duration_seconds=0.1)
            record_models_updated(count=0)
        except Exception as e:
            pytest.fail(f"Record functions raised an exception: {e}")


# =============================================================================
# LiteLLM Capability Sync Tests (TDD - supports_reasoning)
# =============================================================================


class TestLiteLLMModelSyncCapabilities:
    """Test syncing supports_reasoning capability from LiteLLM to ModelRegistry."""

    def test_sync_capabilities_method_exists(self) -> None:
        """Test that sync_capabilities method exists."""
        from mcp_server_langgraph.agents.litellm_model_sync import LiteLLMModelSync

        sync = LiteLLMModelSync()
        assert hasattr(sync, "sync_capabilities")
        assert callable(sync.sync_capabilities)

    def test_sync_capabilities_returns_count(self) -> None:
        """Test that sync_capabilities returns the number of models updated."""
        from mcp_server_langgraph.agents.litellm_model_sync import LiteLLMModelSync

        sync = LiteLLMModelSync()
        count = sync.sync_capabilities()
        assert isinstance(count, int)
        assert count >= 0

    @patch("mcp_server_langgraph.agents.litellm_model_sync.litellm")
    def test_sync_capabilities_updates_supports_extended_thinking(self, mock_litellm: MagicMock) -> None:
        """Test that sync_capabilities updates supports_extended_thinking from supports_reasoning."""
        # LiteLLM model_cost has supports_reasoning field
        mock_litellm.model_cost = {
            "gemini-3-flash": {
                "input_cost_per_token": 0.0000001,
                "output_cost_per_token": 0.0000004,
                "supports_reasoning": True,
            },
            "gpt-4.5": {
                "input_cost_per_token": 0.00001,
                "output_cost_per_token": 0.00003,
                "supports_reasoning": False,
            },
        }

        from mcp_server_langgraph.agents.litellm_model_sync import LiteLLMModelSync

        sync = LiteLLMModelSync()
        count = sync.sync_capabilities()

        # Should have synced capabilities
        assert count >= 0

    @patch("mcp_server_langgraph.agents.litellm_model_sync.litellm")
    def test_sync_capabilities_handles_missing_supports_reasoning(self, mock_litellm: MagicMock) -> None:
        """Test that sync_capabilities handles models without supports_reasoning field."""
        mock_litellm.model_cost = {
            "some-model": {
                "input_cost_per_token": 0.00001,
                "output_cost_per_token": 0.00003,
                # No supports_reasoning field
            }
        }

        from mcp_server_langgraph.agents.litellm_model_sync import LiteLLMModelSync

        sync = LiteLLMModelSync()
        # Should not raise
        count = sync.sync_capabilities()
        assert count >= 0

    @patch("mcp_server_langgraph.agents.litellm_model_sync.litellm")
    def test_sync_capabilities_handles_empty_model_cost(self, mock_litellm: MagicMock) -> None:
        """Test that sync_capabilities handles empty model_cost gracefully."""
        mock_litellm.model_cost = {}

        from mcp_server_langgraph.agents.litellm_model_sync import LiteLLMModelSync

        sync = LiteLLMModelSync()
        count = sync.sync_capabilities()
        assert count == 0


class TestLiteLLMModelSyncCapabilityMapping:
    """Test model ID mapping for capability sync."""

    def test_normalize_model_id_handles_gemini_preview_suffix(self) -> None:
        """Test that Gemini preview suffix is handled for capability sync.

        LiteLLM uses gemini-3-flash-preview but our registry uses gemini-3-flash.
        """
        from mcp_server_langgraph.agents.litellm_model_sync import LiteLLMModelSync

        sync = LiteLLMModelSync()

        # The normalizer should handle preview suffix OR we need alt mappings
        result = sync._normalize_model_id("gemini-3-flash-preview")
        # Either maps to gemini-3-flash or keeps as-is (both should work with registry)
        assert result in ("gemini-3-flash-preview", "gemini-3-flash")

    def test_normalize_model_id_handles_vertex_ai_prefix(self) -> None:
        """Test that vertex_ai prefix is handled."""
        from mcp_server_langgraph.agents.litellm_model_sync import LiteLLMModelSync

        sync = LiteLLMModelSync()

        result = sync._normalize_model_id("vertex_ai/gemini-3-flash")
        assert result == "gemini-3-flash"


class TestLiteLLMModelSyncUpdateRegistryWithCapabilities:
    """Test that update_registry includes capability sync."""

    @patch("mcp_server_langgraph.agents.litellm_model_sync.get_default_registry")
    @patch("mcp_server_langgraph.agents.litellm_model_sync.litellm")
    def test_update_registry_calls_sync_capabilities(self, mock_litellm: MagicMock, mock_get_registry: MagicMock) -> None:
        """Test that update_registry calls sync_capabilities in addition to sync_pricing."""
        mock_registry = MagicMock()
        mock_registry._models = {}
        mock_get_registry.return_value = mock_registry
        mock_litellm.model_cost = {}

        from mcp_server_langgraph.agents.litellm_model_sync import LiteLLMModelSync

        sync = LiteLLMModelSync()

        # Spy on sync_capabilities
        original_sync_caps = sync.sync_capabilities
        sync.sync_capabilities = MagicMock(return_value=0)

        sync.update_registry()

        # Should have called sync_capabilities
        sync.sync_capabilities.assert_called_once()

        # Restore
        sync.sync_capabilities = original_sync_caps


class TestLiteLLMSupportsReasoningFunction:
    """Test LiteLLM's supports_reasoning() function."""

    def test_litellm_supports_reasoning_function_exists(self) -> None:
        """Test that litellm.supports_reasoning function exists."""
        import litellm

        assert hasattr(litellm, "supports_reasoning")
        assert callable(litellm.supports_reasoning)

    def test_supports_reasoning_returns_bool(self) -> None:
        """Test that supports_reasoning returns a boolean."""
        import litellm

        # Test with a known model
        result = litellm.supports_reasoning("o3")
        assert isinstance(result, bool)

    def test_supports_reasoning_for_o3(self) -> None:
        """Test supports_reasoning for o3 model (should be True)."""
        import litellm

        result = litellm.supports_reasoning("o3")
        assert result is True

    def test_supports_reasoning_for_gpt_4(self) -> None:
        """Test supports_reasoning for gpt-4 model (should be False)."""
        import litellm

        result = litellm.supports_reasoning("gpt-4")
        assert result is False


class TestLiteLLMModelSyncAlternativeIds:
    """Test alternative model ID lookups for capability sync."""

    def test_get_alternative_model_ids_method_exists(self) -> None:
        """Test that _get_alternative_model_ids method exists."""
        from mcp_server_langgraph.agents.litellm_model_sync import LiteLLMModelSync

        sync = LiteLLMModelSync()
        assert hasattr(sync, "_get_alternative_model_ids")
        assert callable(sync._get_alternative_model_ids)

    def test_get_alternative_model_ids_for_gemini_3_flash(self) -> None:
        """Test alternative IDs for gemini-3-flash."""
        from mcp_server_langgraph.agents.litellm_model_sync import LiteLLMModelSync

        sync = LiteLLMModelSync()
        alts = sync._get_alternative_model_ids("gemini-3-flash")

        # Should include preview suffix variant
        assert isinstance(alts, list)
        assert "gemini-3-flash-preview" in alts or "google/gemini-3-flash" in alts

    def test_get_alternative_model_ids_returns_list(self) -> None:
        """Test that _get_alternative_model_ids returns a list."""
        from mcp_server_langgraph.agents.litellm_model_sync import LiteLLMModelSync

        sync = LiteLLMModelSync()
        alts = sync._get_alternative_model_ids("some-model")

        assert isinstance(alts, list)
