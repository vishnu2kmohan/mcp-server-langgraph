"""
Tests for model-aware context compaction.

Phase 2 of the Multi-Agent Orchestrator Enhancement Plan.

TDD: Write tests FIRST, then implementation.

Tests:
1. ContextManager accepts model_name parameter
2. Dynamic threshold calculation based on model's effective limit
3. Feature flag controls threshold percentage
4. Integration with ModelRegistry
5. Fallback for unknown models
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

if TYPE_CHECKING:
    pass



pytestmark = pytest.mark.unit

@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="context_manager_model_aware")
class TestModelAwareContextManager:
    """Test model-aware context compaction features."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_context_manager_accepts_model_name_parameter(self) -> None:
        """ContextManager should accept optional model_name parameter."""
        from mcp_server_langgraph.core.context_manager import ContextManager

        # Should not raise when model_name is provided
        cm = ContextManager(model_name="claude-opus-4-5-20251101")
        assert cm.model_name == "claude-opus-4-5-20251101"

    def test_context_manager_model_name_defaults_to_settings(self) -> None:
        """ContextManager should use settings.model_name when not provided."""
        from mcp_server_langgraph.core.context_manager import ContextManager

        mock_settings = MagicMock()
        mock_settings.model_name = "gpt-5.2"

        cm = ContextManager(settings=mock_settings)
        assert cm.model_name == "gpt-5.2"

    def test_get_dynamic_threshold_method_exists(self) -> None:
        """ContextManager should have get_dynamic_threshold method."""
        from mcp_server_langgraph.core.context_manager import ContextManager

        cm = ContextManager(model_name="claude-opus-4-5-20251101")
        assert hasattr(cm, "get_dynamic_threshold")
        assert callable(cm.get_dynamic_threshold)


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="context_manager_threshold_calculation")
class TestDynamicThresholdCalculation:
    """Test dynamic threshold calculation based on model capabilities."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_dynamic_threshold_for_claude_opus(self) -> None:
        """Claude Opus 4.5 should have threshold based on 130K effective limit."""
        from mcp_server_langgraph.core.context_manager import ContextManager

        cm = ContextManager(model_name="claude-opus-4-5-20251101")

        # With 50% threshold (default), 130K effective -> 65K threshold
        threshold = cm.get_dynamic_threshold()
        assert threshold == 65_000

    def test_dynamic_threshold_for_gemini_flash(self) -> None:
        """Gemini 3 Flash should have threshold based on 650K effective limit."""
        from mcp_server_langgraph.core.context_manager import ContextManager

        cm = ContextManager(model_name="gemini-3-flash")

        # With 50% threshold (default), 650K effective -> 325K threshold
        threshold = cm.get_dynamic_threshold()
        assert threshold == 325_000

    def test_dynamic_threshold_for_gpt_5_2(self) -> None:
        """GPT-5.2 should have threshold based on 260K effective limit."""
        from mcp_server_langgraph.core.context_manager import ContextManager

        cm = ContextManager(model_name="gpt-5.2")

        # With 50% threshold (default), 260K effective -> 130K threshold
        threshold = cm.get_dynamic_threshold()
        assert threshold == 130_000

    def test_dynamic_threshold_unknown_model_uses_default(self) -> None:
        """Unknown models should use default context limit for threshold."""
        from mcp_server_langgraph.core.context_manager import ContextManager

        cm = ContextManager(model_name="unknown-model-xyz")

        # Default effective limit is 128K * 0.65 = 83.2K, at 50% -> 41.6K
        threshold = cm.get_dynamic_threshold()
        # Should fall back to registry default
        assert threshold > 0  # Has a valid threshold
        assert threshold <= 100_000  # Reasonable default range

    def test_dynamic_threshold_respects_threshold_percentage(self) -> None:
        """Threshold should change based on configured percentage."""
        from mcp_server_langgraph.core.context_manager import ContextManager

        # With 30% threshold percentage
        cm = ContextManager(
            model_name="claude-opus-4-5-20251101",
            compaction_threshold_percentage=0.30,
        )

        # 130K effective * 0.30 = 39K
        threshold = cm.get_dynamic_threshold()
        assert threshold == 39_000


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="context_manager_feature_flags")
class TestFeatureFlagIntegration:
    """Test feature flag integration for model-aware compaction."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_feature_flag_context_compaction_threshold_percentage_exists(self) -> None:
        """Feature flags should include context_compaction_threshold_percentage."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        ff = FeatureFlags()
        assert hasattr(ff, "context_compaction_threshold_percentage")
        # Default should be 0.5 (50%)
        assert ff.context_compaction_threshold_percentage == 0.5

    def test_feature_flag_enable_model_aware_compaction_exists(self) -> None:
        """Feature flags should include enable_model_aware_compaction."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        ff = FeatureFlags()
        assert hasattr(ff, "enable_model_aware_compaction")
        # Default should be True (enabled by default)
        assert ff.enable_model_aware_compaction is True

    def test_context_manager_uses_feature_flag_percentage(self) -> None:
        """ContextManager should read percentage from feature flags."""
        from mcp_server_langgraph.core.context_manager import ContextManager

        # When not explicitly set, should use feature flag value
        cm = ContextManager(model_name="claude-opus-4-5-20251101")

        # Check that it uses the default feature flag percentage (0.5)
        threshold = cm.get_dynamic_threshold()
        # Claude Opus effective: 130K * 0.5 = 65K
        assert threshold == 65_000


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="context_manager_backward_compat")
class TestBackwardCompatibility:
    """Test backward compatibility with fixed thresholds."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_explicit_threshold_overrides_dynamic(self) -> None:
        """Explicitly set compaction_threshold should override dynamic calculation."""
        from mcp_server_langgraph.core.context_manager import ContextManager

        cm = ContextManager(
            compaction_threshold=8000,  # Explicit fixed threshold
            model_name="claude-opus-4-5-20251101",
        )

        # When compaction_threshold is explicitly set, it should be used
        # But get_dynamic_threshold should still work for reference
        assert cm.compaction_threshold == 8000

    def test_model_aware_disabled_uses_fixed_threshold(self) -> None:
        """When model-aware compaction disabled, should use fixed threshold."""
        from mcp_server_langgraph.core.context_manager import ContextManager

        with patch(
            "mcp_server_langgraph.core.context_manager.feature_flags"
        ) as mock_flags:
            mock_flags.enable_model_aware_compaction = False
            mock_flags.context_compaction_threshold_percentage = 0.5

            cm = ContextManager(
                compaction_threshold=8000,
                model_name="claude-opus-4-5-20251101",
            )

            # Should use the fixed threshold
            assert cm.compaction_threshold == 8000


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="context_manager_integration")
class TestModelRegistryIntegration:
    """Test integration with ModelRegistry."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_context_manager_uses_model_registry(self) -> None:
        """ContextManager should query ModelRegistry for effective limits."""
        from mcp_server_langgraph.core.context_manager import ContextManager

        cm = ContextManager(model_name="claude-opus-4-5-20251101")

        # Should use registry to get model capabilities
        assert hasattr(cm, "_model_registry") or hasattr(cm, "model_registry")

    def test_vertex_ai_model_uses_correct_threshold(self) -> None:
        """Vertex AI Anthropic models should use correct thresholds."""
        from mcp_server_langgraph.core.context_manager import ContextManager

        cm = ContextManager(model_name="claude-opus-4-5@20251101")

        # Vertex AI Opus also has 130K effective limit
        threshold = cm.get_dynamic_threshold()
        assert threshold == 65_000

    def test_azure_model_uses_correct_threshold(self) -> None:
        """Azure OpenAI models should use correct thresholds."""
        from mcp_server_langgraph.core.context_manager import ContextManager

        cm = ContextManager(model_name="azure/gpt-5.2")

        # Azure GPT-5.2 has 260K effective limit
        threshold = cm.get_dynamic_threshold()
        assert threshold == 130_000


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="context_manager_needs_compaction")
class TestNeedsCompactionModelAware:
    """Test needs_compaction with model-aware thresholds."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_needs_compaction_uses_dynamic_threshold(self) -> None:
        """needs_compaction should use model-aware threshold when enabled."""
        from mcp_server_langgraph.core.context_manager import ContextManager

        cm = ContextManager(model_name="claude-opus-4-5-20251101")

        # Create messages that exceed fixed threshold but not dynamic
        # Fixed: 8000, Dynamic: 65000
        # This test verifies dynamic threshold is used
        messages = [HumanMessage(content="x" * 10000)]  # ~10K tokens

        # With dynamic threshold (65K), this should NOT need compaction
        # With fixed threshold (8K), this would need compaction
        # Result depends on which threshold is active
        result = cm.needs_compaction(messages)

        # Dynamic threshold (65K) should not trigger compaction for 10K tokens
        assert result is False

    def test_needs_compaction_respects_model_limits(self) -> None:
        """Compaction should trigger based on model's effective limit."""
        from mcp_server_langgraph.core.context_manager import ContextManager

        # Use Claude Haiku with smaller context
        cm = ContextManager(model_name="claude-haiku-4-5-20251001")

        # Haiku: 200K context, 130K effective, 65K threshold at 50%
        # Same as Opus, so similar behavior
        threshold = cm.get_dynamic_threshold()
        assert threshold == 65_000


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="context_manager_target_after")
class TestTargetAfterCompaction:
    """Test target_after_compaction with model-aware scaling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_target_after_compaction_scales_with_threshold(self) -> None:
        """Target after compaction should be proportional to threshold."""
        from mcp_server_langgraph.core.context_manager import ContextManager

        cm = ContextManager(model_name="claude-opus-4-5-20251101")

        # Dynamic target should be half of dynamic threshold (typical ratio)
        target = cm.get_dynamic_target()
        threshold = cm.get_dynamic_threshold()

        # Target should be approximately 50% of threshold
        assert target == threshold // 2

    def test_get_dynamic_target_method_exists(self) -> None:
        """ContextManager should have get_dynamic_target method."""
        from mcp_server_langgraph.core.context_manager import ContextManager

        cm = ContextManager(model_name="claude-opus-4-5-20251101")
        assert hasattr(cm, "get_dynamic_target")
        assert callable(cm.get_dynamic_target)
