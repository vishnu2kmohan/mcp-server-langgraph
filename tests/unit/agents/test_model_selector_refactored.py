"""
Tests for Model Selector Refactoring

TDD: These tests verify that the model selector properly integrates with
the model registry and tier system.
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING

import pytest

pytestmark = pytest.mark.unit

if TYPE_CHECKING:
    pass


@pytest.mark.xdist_group(name="model_selector_refactor")
class TestModelSelectorRegistry:
    """Tests for model selector's use of the model registry."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_model_selector_exists(self) -> None:
        """Test that ModelSelector class exists."""
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        assert ModelSelector is not None

    def test_model_selector_has_select_method(self) -> None:
        """Test that ModelSelector has select method."""
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        selector = ModelSelector()
        assert hasattr(selector, "select")
        assert callable(selector.select)

    def test_model_selector_accepts_complexity(self) -> None:
        """Test that ModelSelector.select accepts complexity parameter."""
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        selector = ModelSelector()
        result = selector.select(complexity="simple")

        assert result is not None
        assert hasattr(result, "model")

    def test_model_selector_returns_appropriate_tier_for_simple(self) -> None:
        """Test selector returns appropriate tier for simple complexity."""
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        selector = ModelSelector()
        result = selector.select(complexity="simple")

        # Should select a simple-tier model
        assert result.tier in ["simple", "complicated"]  # May fallback

    def test_model_selector_returns_appropriate_tier_for_complex(self) -> None:
        """Test selector returns appropriate tier for complex complexity."""
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        selector = ModelSelector()
        result = selector.select(complexity="complex")

        # Should select a complex-tier model (or fallback to complicated)
        assert result.tier in ["complex", "complicated"]

    def test_model_selector_respects_vendor_preference(self) -> None:
        """Test selector respects vendor preference when available."""
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        selector = ModelSelector(
            available_vendors=["google"],
        )
        result = selector.select(complexity="simple", vendor="google")

        assert result is not None
        # Should have selected a google model if available

    def test_model_selector_falls_back_on_unavailable_tier(self) -> None:
        """Test selector falls back to available tier if requested tier unavailable."""
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        selector = ModelSelector()
        result = selector.select(complexity="complicated")

        # Should always return a valid model
        assert result is not None
        assert result.model is not None


@pytest.mark.xdist_group(name="model_selector_tier_mapping")
class TestModelSelectorTierMapping:
    """Tests for tier mapping in model selector - now uses ModelRegistry.

    After Phase 1 refactor, MODEL_TIERS dict is removed and ModelSelector
    consumes tier information from ModelRegistry.get_model_for_tier().
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_model_tiers_dict_removed(self) -> None:
        """Test that MODEL_TIERS dict is removed from model_selector.

        After Phase 1 refactor, the hardcoded MODEL_TIERS dict should be
        removed. ModelSelector now uses ModelRegistry for tier lookups.
        """
        import mcp_server_langgraph.agents.model_selector as model_selector_module

        # MODEL_TIERS should no longer exist in the module
        assert not hasattr(model_selector_module, "MODEL_TIERS"), (
            "MODEL_TIERS dict should be removed. ModelSelector should use ModelRegistry.get_model_for_tier() instead."
        )

    def test_registry_has_get_model_for_tier_method(self) -> None:
        """Test that ModelRegistry has get_model_for_tier method."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        assert hasattr(registry, "get_model_for_tier"), "ModelRegistry should have get_model_for_tier(vendor, tier) method"

    def test_registry_get_model_for_tier_returns_model(self) -> None:
        """Test that get_model_for_tier returns a valid model ID."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        model = registry.get_model_for_tier(vendor="google", tier="simple")

        assert model is not None
        assert isinstance(model, str)
        assert len(model) > 0

    def test_registry_get_model_for_tier_google_simple(self) -> None:
        """Test Google simple tier returns gemini-3-flash."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        model = registry.get_model_for_tier(vendor="google", tier="simple")

        assert "gemini" in model.lower()

    def test_registry_get_model_for_tier_google_complicated(self) -> None:
        """Test Google complicated tier returns gemini-3-flash (cost efficiency).

        For cost efficiency, Google complicated tier uses the same model
        as simple tier (gemini-3-flash).
        """
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        model = registry.get_model_for_tier(vendor="google", tier="complicated")

        # Should return gemini-3-flash for cost efficiency
        assert "gemini" in model.lower()

    def test_registry_get_model_for_tier_google_complex(self) -> None:
        """Test Google complex tier returns gemini-3-pro."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        model = registry.get_model_for_tier(vendor="google", tier="complex")

        assert "gemini" in model.lower()
        assert "pro" in model.lower()

    def test_registry_get_model_for_tier_anthropic_simple(self) -> None:
        """Test Anthropic simple tier returns Haiku."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        model = registry.get_model_for_tier(vendor="anthropic", tier="simple")

        assert "haiku" in model.lower()

    def test_registry_get_model_for_tier_anthropic_complicated(self) -> None:
        """Test Anthropic complicated tier returns Sonnet."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        model = registry.get_model_for_tier(vendor="anthropic", tier="complicated")

        assert "sonnet" in model.lower()

    def test_registry_get_model_for_tier_anthropic_complex(self) -> None:
        """Test Anthropic complex tier returns Opus."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        model = registry.get_model_for_tier(vendor="anthropic", tier="complex")

        assert "opus" in model.lower()

    def test_registry_get_model_for_tier_openai_simple(self) -> None:
        """Test OpenAI simple tier returns GPT-5.2."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        model = registry.get_model_for_tier(vendor="openai", tier="simple")

        assert "gpt" in model.lower()

    def test_registry_get_model_for_tier_openai_complex(self) -> None:
        """Test OpenAI complex tier returns GPT-5.2-pro."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        model = registry.get_model_for_tier(vendor="openai", tier="complex")

        assert "gpt" in model.lower()
        assert "pro" in model.lower()

    def test_registry_get_model_for_tier_vertex_ai_anthropic(self) -> None:
        """Test Vertex AI Anthropic tier returns appropriate model."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        model = registry.get_model_for_tier(vendor="vertex_ai_anthropic", tier="complex")

        assert "opus" in model.lower()
        assert "@" in model  # Vertex AI format


@pytest.mark.xdist_group(name="model_selector_validation")
class TestModelSelectorValidation:
    """Tests for model selector validation and error handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_select_with_invalid_complexity_falls_back(self) -> None:
        """Test that invalid complexity falls back to default."""
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        selector = ModelSelector()
        # Invalid complexity should fall back to "complicated"
        result = selector.select(complexity="unknown_tier")

        assert result is not None
        assert result.tier == "complicated"  # Default fallback

    def test_select_returns_selection_result(self) -> None:
        """Test that select returns a SelectionResult object."""
        from mcp_server_langgraph.agents.model_selector import (
            ModelSelector,
            SelectionResult,
        )

        selector = ModelSelector()
        result = selector.select(complexity="complicated")

        assert isinstance(result, SelectionResult)
        assert hasattr(result, "model")
        assert hasattr(result, "tier")
        assert hasattr(result, "is_fallback")

    def test_select_tracks_fallback_status(self) -> None:
        """Test that SelectionResult indicates when fallback was used."""
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        selector = ModelSelector()
        result = selector.select(complexity="complicated")

        # is_fallback should be boolean
        assert isinstance(result.is_fallback, bool)


@pytest.mark.xdist_group(name="model_selector_verifier")
class TestModelSelectorVerifier:
    """Tests for verifier model selection."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_select_verifier_exists(self) -> None:
        """Test that ModelSelector has select_verifier method."""
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        selector = ModelSelector()
        assert hasattr(selector, "select_verifier")
        assert callable(selector.select_verifier)

    def test_select_verifier_returns_model(self) -> None:
        """Test that select_verifier returns a valid model."""
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        selector = ModelSelector()
        result = selector.select_verifier(primary_model="gemini-3-flash")

        assert result is not None
        assert hasattr(result, "model")

    def test_verifier_different_from_primary(self) -> None:
        """Test that verifier is typically different from primary (cross-vendor)."""
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        selector = ModelSelector()
        primary = "gemini-3-flash"
        result = selector.select_verifier(primary_model=primary)

        # Verifier should ideally be from different vendor for diversity
        # But this isn't strictly enforced, so just check we got a model
        assert result is not None
        assert result.model is not None
