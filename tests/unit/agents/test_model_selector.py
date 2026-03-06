"""
Tests for Model Selector

Comprehensive tests for three-tier model selection with cross-vendor
verification, graceful fallbacks, and vendor detection.
"""

from __future__ import annotations

import gc
import os
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit

if TYPE_CHECKING:
    pass


@pytest.mark.unit
@pytest.mark.agents
class TestModelSelectorBasics:
    """Basic tests for ModelSelector initialization and model tiers."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_model_selector_class_exists(self) -> None:
        """Test that ModelSelector class exists."""
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        assert ModelSelector is not None

    def test_model_selector_initialization_defaults(self) -> None:
        """Test ModelSelector initialization with defaults."""
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        selector = ModelSelector()

        assert selector.available_tiers == ["simple", "complicated", "complex"]
        assert len(selector.available_vendors) >= 1
        assert selector.primary_vendor is not None

    def test_model_selector_initialization_with_vendors(self) -> None:
        """Test ModelSelector initialization with explicit vendors."""
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        selector = ModelSelector(available_vendors=["anthropic", "google"])

        assert selector.available_vendors == ["anthropic", "google"]
        assert selector.primary_vendor == "anthropic"

    def test_model_selector_initialization_with_tiers(self) -> None:
        """Test ModelSelector initialization with limited tiers."""
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        selector = ModelSelector(available_tiers=["simple", "complex"])

        assert selector.available_tiers == ["simple", "complex"]

    def test_registry_has_all_tiers_and_vendors(self) -> None:
        """Test ModelRegistry.get_model_for_tier works for all tiers and vendors.

        After Phase 1 refactor, MODEL_TIERS dict was removed. Tier-to-model
        mapping now lives in ModelRegistry.get_model_for_tier().
        """
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()

        # All tiers should return valid models for main vendors
        for tier in ["simple", "complicated", "complex"]:
            for vendor in ["google", "anthropic", "openai"]:
                model = registry.get_model_for_tier(vendor=vendor, tier=tier)
                assert model is not None
                assert isinstance(model, str)
                assert len(model) > 0

    def test_vendor_priority_constant(self) -> None:
        """Test VENDOR_PRIORITY defines priority order."""
        from mcp_server_langgraph.agents.model_selector import VENDOR_PRIORITY

        # Phase 8: Added vertex_ai_anthropic for enterprise deployments
        assert VENDOR_PRIORITY == ["google", "anthropic", "openai", "vertex_ai_anthropic"]


@pytest.mark.unit
@pytest.mark.agents
class TestVendorDetection:
    """Tests for vendor auto-detection from environment variables."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_detect_vendors_no_env_vars_defaults_to_google(self) -> None:
        """Test vendor detection defaults to google when no env vars set."""
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        with patch.dict(os.environ, {}, clear=True):
            # Remove any existing API keys
            env_vars_to_remove = [
                "GOOGLE_API_KEY",
                "VERTEX_AI_PROJECT",
                "ANTHROPIC_API_KEY",
                "OPENAI_API_KEY",
            ]
            for var in env_vars_to_remove:
                os.environ.pop(var, None)

            selector = ModelSelector(available_vendors=None)
            # Re-detect vendors
            vendors = selector._detect_vendors()

            assert vendors == ["google"]

    def test_detect_vendors_google_api_key(self) -> None:
        """Test vendor detection with GOOGLE_API_KEY."""
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        with patch.dict(
            os.environ,
            {"GOOGLE_API_KEY": "test-key"},
            clear=True,
        ):
            selector = ModelSelector()
            vendors = selector._detect_vendors()

            assert "google" in vendors

    def test_detect_vendors_vertex_ai_project(self) -> None:
        """Test vendor detection with VERTEX_AI_PROJECT."""
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        with patch.dict(
            os.environ,
            {"VERTEX_AI_PROJECT": "test-project"},
            clear=True,
        ):
            selector = ModelSelector()
            vendors = selector._detect_vendors()

            assert "google" in vendors

    def test_detect_vendors_anthropic_api_key(self) -> None:
        """Test vendor detection with ANTHROPIC_API_KEY."""
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        with patch.dict(
            os.environ,
            {"ANTHROPIC_API_KEY": "test-key"},
            clear=True,
        ):
            selector = ModelSelector()
            vendors = selector._detect_vendors()

            assert "anthropic" in vendors

    def test_detect_vendors_openai_api_key(self) -> None:
        """Test vendor detection with OPENAI_API_KEY."""
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        with patch.dict(
            os.environ,
            {"OPENAI_API_KEY": "test-key"},
            clear=True,
        ):
            selector = ModelSelector()
            vendors = selector._detect_vendors()

            assert "openai" in vendors

    def test_detect_vendors_all_vendors(self) -> None:
        """Test vendor detection with all API keys set."""
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        with patch.dict(
            os.environ,
            {
                "GOOGLE_API_KEY": "test-key",
                "ANTHROPIC_API_KEY": "test-key",
                "OPENAI_API_KEY": "test-key",
            },
            clear=True,
        ):
            selector = ModelSelector()
            vendors = selector._detect_vendors()

            # Should be in priority order
            assert vendors == ["google", "anthropic", "openai"]

    def test_detect_vendors_anthropic_and_openai_only(self) -> None:
        """Test vendor detection without Google."""
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        with patch.dict(
            os.environ,
            {
                "ANTHROPIC_API_KEY": "test-key",
                "OPENAI_API_KEY": "test-key",
            },
            clear=True,
        ):
            selector = ModelSelector()
            vendors = selector._detect_vendors()

            assert vendors == ["anthropic", "openai"]
            assert "google" not in vendors


@pytest.mark.unit
@pytest.mark.agents
class TestTierFallback:
    """Tests for tier fallback logic."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_fallback_tier_requested_available(self) -> None:
        """Test fallback returns requested tier when available."""
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        selector = ModelSelector(
            available_vendors=["google"],
            available_tiers=["simple", "complicated", "complex"],
        )

        assert selector._fallback_tier("simple") == "simple"
        assert selector._fallback_tier("complicated") == "complicated"
        assert selector._fallback_tier("complex") == "complex"

    def test_fallback_tier_single_tier_available(self) -> None:
        """Test fallback when only one tier is available."""
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        selector = ModelSelector(
            available_vendors=["google"],
            available_tiers=["complex"],
        )

        # All requests should fall back to complex
        assert selector._fallback_tier("simple") == "complex"
        assert selector._fallback_tier("complicated") == "complex"
        assert selector._fallback_tier("complex") == "complex"

    def test_fallback_tier_missing_complicated(self) -> None:
        """Test fallback when complicated tier is missing."""
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        selector = ModelSelector(
            available_vendors=["google"],
            available_tiers=["simple", "complex"],
        )

        # Complicated should fall back to simple (closest lower tier)
        assert selector._fallback_tier("complicated") == "simple"
        assert selector._fallback_tier("simple") == "simple"
        assert selector._fallback_tier("complex") == "complex"

    def test_fallback_tier_invalid_tier(self) -> None:
        """Test fallback with invalid tier name."""
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        selector = ModelSelector(
            available_vendors=["google"],
            available_tiers=["simple", "complicated", "complex"],
        )

        # Invalid tier should return highest available
        result = selector._fallback_tier("ultra")
        assert result == "complex"

    def test_fallback_tier_only_high_tier_available(self) -> None:
        """Test fallback when only high tier is available."""
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        selector = ModelSelector(
            available_vendors=["google"],
            available_tiers=["complex"],
        )

        # Simple should fall back to complex (only available)
        assert selector._fallback_tier("simple") == "complex"

    def test_fallback_tier_empty_string(self) -> None:
        """Test fallback with empty string tier."""
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        selector = ModelSelector(
            available_vendors=["google"],
            available_tiers=["simple", "complex"],
        )

        # Empty string should return highest available
        result = selector._fallback_tier("")
        assert result == "complex"


@pytest.mark.unit
@pytest.mark.agents
class TestModelSelection:
    """Tests for model selection."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_select_model_simple_google(self) -> None:
        """Test selecting simple model with Google as primary."""
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        selector = ModelSelector(available_vendors=["google"])

        model = selector.select_model("simple")

        assert "gemini" in model.lower() or "flash" in model.lower()

    def test_select_model_complicated_anthropic(self) -> None:
        """Test selecting complicated model with Anthropic as primary."""
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        selector = ModelSelector(available_vendors=["anthropic"])

        model = selector.select_model("complicated")

        assert "claude" in model.lower() or "sonnet" in model.lower()

    def test_select_model_complex_openai(self) -> None:
        """Test selecting complex model with OpenAI as primary."""
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        selector = ModelSelector(available_vendors=["openai"])

        model = selector.select_model("complex")

        assert "o3" in model.lower() or "gpt" in model.lower()

    def test_select_model_vendor_fallback(self) -> None:
        """Test model selection falls back through vendors."""
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        # Primary vendor is google, but should still work
        selector = ModelSelector(
            available_vendors=["google", "anthropic"],
        )

        model = selector.select_model("complicated")

        # Should get a valid model
        assert model is not None
        assert len(model) > 0

    def test_select_model_all_tiers(self) -> None:
        """Test selecting models for all complexity tiers."""
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        selector = ModelSelector(available_vendors=["google"])

        simple_model = selector.select_model("simple")
        complicated_model = selector.select_model("complicated")
        complex_model = selector.select_model("complex")

        # Phase 8: Google simple and complicated tiers use same model for cost efficiency
        # Only complex tier uses a different (more powerful) model
        assert simple_model == complicated_model  # Both use gemini-3-flash
        assert complicated_model != complex_model  # Complex uses gemini-3-pro
        assert simple_model != complex_model


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.xdist_group(name="model_selector_verifier")
class TestVerifierSelection:
    """Tests for cross-vendor verification model selection."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_select_verifier_same_vendor(self) -> None:
        """Test selecting verifier from same vendor."""
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        selector = ModelSelector(available_vendors=["google"])

        verifier = selector.select_verifier("same")

        # Should return a complicated tier model
        assert verifier is not None
        assert "gemini" in verifier.model.lower() or "flash" in verifier.model.lower()

    def test_select_verifier_auto_cross_vendor(self) -> None:
        """Test auto verifier prefers cross-vendor."""
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        selector = ModelSelector(
            available_vendors=["google", "anthropic"],
        )

        verifier = selector.select_verifier("auto")

        # Primary is google, so verifier should be anthropic
        assert "claude" in verifier.model.lower() or "sonnet" in verifier.model.lower()

    def test_select_verifier_auto_single_vendor_fallback(self) -> None:
        """Test auto verifier falls back to same vendor when only one available."""
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        selector = ModelSelector(available_vendors=["google"])

        verifier = selector.select_verifier("auto")

        # Should fall back to google since it's the only vendor
        assert "gemini" in verifier.model.lower() or "flash" in verifier.model.lower()

    def test_select_verifier_explicit_anthropic(self) -> None:
        """Test explicit anthropic verifier."""
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        selector = ModelSelector(available_vendors=["google"])

        verifier = selector.select_verifier("anthropic")

        assert "claude" in verifier.model.lower() or "sonnet" in verifier.model.lower()

    def test_select_verifier_explicit_google(self) -> None:
        """Test explicit google verifier."""
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        selector = ModelSelector(available_vendors=["anthropic"])

        verifier = selector.select_verifier("google")

        assert "gemini" in verifier.model.lower()

    def test_select_verifier_explicit_openai(self) -> None:
        """Test explicit openai verifier."""
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        selector = ModelSelector(available_vendors=["google"])

        verifier = selector.select_verifier("openai")

        assert "gpt" in verifier.model.lower() or "o3" in verifier.model.lower() or "mini" in verifier.model.lower()

    def test_select_verifier_invalid_vendor_defaults_to_anthropic(self) -> None:
        """Test invalid verifier vendor defaults to anthropic."""
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        selector = ModelSelector(available_vendors=["google"])

        verifier = selector.select_verifier("invalid_vendor")

        # Should default to anthropic
        assert "claude" in verifier.model.lower() or "sonnet" in verifier.model.lower()


@pytest.mark.unit
@pytest.mark.agents
class TestModelForTaskScore:
    """Tests for get_model_for_task with complexity scores."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_model_for_task_score_1(self) -> None:
        """Test complexity score 1 gets simple model."""
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        selector = ModelSelector(available_vendors=["google"])

        model = selector.get_model_for_task(1)

        # Score 1 should be simple tier
        assert "flash" in model.lower() or "gemini-3" in model.lower()

    def test_get_model_for_task_score_3_boundary(self) -> None:
        """Test complexity score 3 (upper boundary of simple)."""
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        selector = ModelSelector(available_vendors=["google"])

        model = selector.get_model_for_task(3)

        # Score 3 should still be simple tier
        assert "flash" in model.lower() or "gemini-3-flash" in model.lower()

    def test_get_model_for_task_score_4_boundary(self) -> None:
        """Test complexity score 4 (lower boundary of complicated)."""
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        selector = ModelSelector(available_vendors=["google"])

        model = selector.get_model_for_task(4)

        # Phase 8: Score 4 is complicated tier, which uses gemini-3-flash (same as simple)
        assert "gemini-3-flash" in model or "gemini" in model.lower()

    def test_get_model_for_task_score_7_boundary(self) -> None:
        """Test complexity score 7 (upper boundary of complicated)."""
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        selector = ModelSelector(available_vendors=["google"])

        model = selector.get_model_for_task(7)

        # Score 7 should still be complicated tier
        assert "2.5" in model or "flash" in model.lower()

    def test_get_model_for_task_score_8_boundary(self) -> None:
        """Test complexity score 8 (lower boundary of complex)."""
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        selector = ModelSelector(available_vendors=["google"])

        model = selector.get_model_for_task(8)

        # Score 8 should be complex tier
        assert "pro" in model.lower() or "gemini-3-pro" in model.lower()

    def test_get_model_for_task_score_10(self) -> None:
        """Test complexity score 10 gets complex model."""
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        selector = ModelSelector(available_vendors=["google"])

        model = selector.get_model_for_task(10)

        # Score 10 should be complex tier
        assert "pro" in model.lower()

    def test_get_model_for_task_consistency_within_tiers(self) -> None:
        """Test models are consistent within tier boundaries."""
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        selector = ModelSelector(available_vendors=["google"])

        # Simple tier (1-3)
        simple_models = [selector.get_model_for_task(i) for i in range(1, 4)]
        assert len(set(simple_models)) == 1  # All same model

        # Complicated tier (4-7)
        complicated_models = [selector.get_model_for_task(i) for i in range(4, 8)]
        assert len(set(complicated_models)) == 1  # All same model

        # Complex tier (8-10)
        complex_models = [selector.get_model_for_task(i) for i in range(8, 11)]
        assert len(set(complex_models)) == 1  # All same model


@pytest.mark.unit
@pytest.mark.agents
class TestModelSelectorEdgeCases:
    """Edge case tests for ModelSelector."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_empty_vendors_list_uses_default(self) -> None:
        """Test empty vendors list falls back to default."""
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        selector = ModelSelector(available_vendors=[])

        # Should handle empty list gracefully
        # Primary vendor will be empty string or default
        model = selector.select_model("simple")
        assert model is not None

    def test_single_vendor_multi_tier(self) -> None:
        """Test single vendor works across all tiers."""
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        selector = ModelSelector(
            available_vendors=["anthropic"],
            available_tiers=["simple", "complicated", "complex"],
        )

        simple = selector.select_model("simple")
        complicated = selector.select_model("complicated")
        complex_model = selector.select_model("complex")

        # All should be Anthropic models
        assert "claude" in simple.lower() or "haiku" in simple.lower()
        assert "claude" in complicated.lower() or "sonnet" in complicated.lower()
        assert "claude" in complex_model.lower() or "opus" in complex_model.lower()

    def test_verifier_with_three_vendors(self) -> None:
        """Test verifier selection with three vendors available."""
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        selector = ModelSelector(
            available_vendors=["google", "anthropic", "openai"],
        )

        verifier = selector.select_verifier("auto")

        # Should pick anthropic (first non-primary)
        assert "claude" in verifier.model.lower() or "sonnet" in verifier.model.lower()

    def test_verifier_auto_with_openai_primary(self) -> None:
        """Test auto verifier when OpenAI is primary."""
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        selector = ModelSelector(
            available_vendors=["openai", "anthropic"],
        )

        verifier = selector.select_verifier("auto")

        # Should pick anthropic as verifier
        assert "claude" in verifier.model.lower() or "sonnet" in verifier.model.lower()


@pytest.mark.unit
@pytest.mark.agents
class TestModelSelectorVertexAIAnthropic:
    """Tests for Vertex AI Anthropic vendor support (Phase 8).

    Validates that MODEL_TIERS includes vertex_ai_anthropic
    for enterprise deployments through Google Cloud Vertex AI.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_registry_has_vertex_ai_anthropic(self) -> None:
        """ModelRegistry.get_model_for_tier should include vertex_ai_anthropic vendor.

        After Phase 1 refactor, MODEL_TIERS dict was removed. Vertex AI Anthropic
        tier mapping now lives in ModelRegistry.get_model_for_tier().
        """
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()

        for tier in ["simple", "complicated", "complex"]:
            model = registry.get_model_for_tier(vendor="vertex_ai_anthropic", tier=tier)
            assert model is not None, f"Missing vertex_ai_anthropic model for {tier} tier"

    def test_vertex_ai_anthropic_simple_tier(self) -> None:
        """Vertex AI Anthropic simple tier should use Haiku."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        model = registry.get_model_for_tier(vendor="vertex_ai_anthropic", tier="simple")
        assert "haiku" in model.lower()
        assert "@" in model  # Vertex AI format uses @version

    def test_vertex_ai_anthropic_complicated_tier(self) -> None:
        """Vertex AI Anthropic complicated tier should use Sonnet."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        model = registry.get_model_for_tier(vendor="vertex_ai_anthropic", tier="complicated")
        assert "sonnet" in model.lower()
        assert "@" in model

    def test_vertex_ai_anthropic_complex_tier(self) -> None:
        """Vertex AI Anthropic complex tier should use Opus."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        model = registry.get_model_for_tier(vendor="vertex_ai_anthropic", tier="complex")
        assert "opus" in model.lower()
        assert "@" in model

    def test_vendor_priority_includes_vertex_ai(self) -> None:
        """VENDOR_PRIORITY should include vertex_ai_anthropic."""
        from mcp_server_langgraph.agents.model_selector import VENDOR_PRIORITY

        assert "vertex_ai_anthropic" in VENDOR_PRIORITY

    def test_select_model_with_vertex_ai_anthropic(self) -> None:
        """ModelSelector should work with vertex_ai_anthropic vendor."""
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        selector = ModelSelector(available_vendors=["vertex_ai_anthropic"])

        simple = selector.select_model("simple")
        complicated = selector.select_model("complicated")
        complex_model = selector.select_model("complex")

        assert "haiku" in simple.lower() or "claude" in simple.lower()
        assert "sonnet" in complicated.lower() or "claude" in complicated.lower()
        assert "opus" in complex_model.lower() or "claude" in complex_model.lower()


@pytest.mark.unit
@pytest.mark.agents
class TestLiteLLMModelID:
    """Tests for get_litellm_model_id function (Phase 9)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_litellm_model_id_function_exists(self) -> None:
        """get_litellm_model_id function should exist."""
        from mcp_server_langgraph.agents.model_selector import get_litellm_model_id

        assert callable(get_litellm_model_id)

    def test_vertex_ai_anthropic_adds_prefix(self) -> None:
        """Vertex AI Anthropic models should get vertex_ai/ prefix."""
        from mcp_server_langgraph.agents.model_selector import get_litellm_model_id

        model_id = get_litellm_model_id("claude-opus-4-5@20251101", "vertex_ai_anthropic")
        assert model_id == "vertex_ai/claude-opus-4-5@20251101"

    def test_anthropic_direct_no_prefix(self) -> None:
        """Direct Anthropic models should not get prefix."""
        from mcp_server_langgraph.agents.model_selector import get_litellm_model_id

        model_id = get_litellm_model_id("claude-opus-4-5-20251101", "anthropic")
        assert model_id == "claude-opus-4-5-20251101"

    def test_google_no_prefix(self) -> None:
        """Google/Gemini models should not get prefix."""
        from mcp_server_langgraph.agents.model_selector import get_litellm_model_id

        model_id = get_litellm_model_id("gemini-3-flash", "google")
        assert model_id == "gemini-3-flash"

    def test_openai_no_prefix(self) -> None:
        """OpenAI models should not get prefix."""
        from mcp_server_langgraph.agents.model_selector import get_litellm_model_id

        model_id = get_litellm_model_id("gpt-5.2", "openai")
        assert model_id == "gpt-5.2"

    def test_azure_adds_prefix(self) -> None:
        """Azure models should get azure/ prefix."""
        from mcp_server_langgraph.agents.model_selector import get_litellm_model_id

        model_id = get_litellm_model_id("gpt-5.2", "azure")
        assert model_id == "azure/gpt-5.2"

    def test_bedrock_adds_prefix(self) -> None:
        """Bedrock models should get bedrock/ prefix."""
        from mcp_server_langgraph.agents.model_selector import get_litellm_model_id

        model_id = get_litellm_model_id("claude-3-opus", "bedrock")
        assert model_id == "bedrock/claude-3-opus"

    def test_already_prefixed_model_not_double_prefixed(self) -> None:
        """Models already with prefix should not be double-prefixed."""
        from mcp_server_langgraph.agents.model_selector import get_litellm_model_id

        model_id = get_litellm_model_id("vertex_ai/gemini-3-pro", "vertex_ai")
        assert model_id == "vertex_ai/gemini-3-pro"

    def test_select_model_for_litellm(self) -> None:
        """ModelSelector should have select_model_for_litellm method."""
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        selector = ModelSelector(available_vendors=["vertex_ai_anthropic"])
        model_id = selector.select_model_for_litellm("complex")

        assert model_id.startswith("vertex_ai/")
        assert "opus" in model_id.lower()
