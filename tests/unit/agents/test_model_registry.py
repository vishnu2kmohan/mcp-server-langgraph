"""
Tests for Model Registry

Comprehensive tests for model capabilities registry that tracks context limits,
capabilities, and costs for all supported LLM models.

TDD: These tests are written FIRST before implementation.
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING

import pytest

pytestmark = pytest.mark.unit

if TYPE_CHECKING:
    pass


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="model_registry_capabilities")
class TestModelCapabilities:
    """Tests for ModelCapabilities dataclass."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_model_capabilities_class_exists(self) -> None:
        """Test that ModelCapabilities class exists."""
        from mcp_server_langgraph.agents.model_registry import ModelCapabilities

        assert ModelCapabilities is not None

    def test_model_capabilities_has_required_fields(self) -> None:
        """Test ModelCapabilities has all required fields."""
        from mcp_server_langgraph.agents.model_registry import ModelCapabilities

        caps = ModelCapabilities(
            model_id="claude-opus-4-5-20251101",
            vendor="anthropic",
            context_limit=200_000,
            effective_limit=130_000,
            max_output_tokens=64_000,
            input_cost_per_1m=5.00,
            output_cost_per_1m=25.00,
            supports_vision=True,
            supports_tools=True,
            supports_streaming=True,
            supports_extended_thinking=True,
            supports_effort_param=True,
        )

        assert caps.model_id == "claude-opus-4-5-20251101"
        assert caps.vendor == "anthropic"
        assert caps.context_limit == 200_000
        assert caps.effective_limit == 130_000
        assert caps.max_output_tokens == 64_000
        assert caps.input_cost_per_1m == 5.00
        assert caps.output_cost_per_1m == 25.00
        assert caps.supports_vision is True
        assert caps.supports_tools is True
        assert caps.supports_streaming is True
        assert caps.supports_extended_thinking is True
        assert caps.supports_effort_param is True

    def test_model_capabilities_effective_limit_defaults(self) -> None:
        """Test effective_limit defaults to 65% of context_limit if not specified."""
        from mcp_server_langgraph.agents.model_registry import ModelCapabilities

        caps = ModelCapabilities(
            model_id="test-model",
            vendor="test",
            context_limit=200_000,
            # effective_limit not specified
            max_output_tokens=10_000,
            input_cost_per_1m=1.0,
            output_cost_per_1m=2.0,
        )

        # Should default to 65% of context_limit
        assert caps.effective_limit == int(200_000 * 0.65)

    def test_model_capabilities_default_false_for_capabilities(self) -> None:
        """Test capability flags default to False."""
        from mcp_server_langgraph.agents.model_registry import ModelCapabilities

        caps = ModelCapabilities(
            model_id="test-model",
            vendor="test",
            context_limit=100_000,
            max_output_tokens=10_000,
            input_cost_per_1m=1.0,
            output_cost_per_1m=2.0,
        )

        # All capability flags should default to False
        assert caps.supports_vision is False
        assert caps.supports_tools is False
        assert caps.supports_streaming is False
        assert caps.supports_extended_thinking is False
        assert caps.supports_effort_param is False


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="model_registry_core")
class TestModelRegistry:
    """Tests for ModelRegistry class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_model_registry_class_exists(self) -> None:
        """Test that ModelRegistry class exists."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        assert ModelRegistry is not None

    def test_model_registry_initialization(self) -> None:
        """Test ModelRegistry can be initialized."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()

        assert registry is not None

    def test_model_registry_has_get_method(self) -> None:
        """Test ModelRegistry has get method."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()

        assert hasattr(registry, "get")
        assert callable(registry.get)

    def test_model_registry_has_register_method(self) -> None:
        """Test ModelRegistry has register method."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()

        assert hasattr(registry, "register")
        assert callable(registry.register)

    def test_model_registry_has_list_models_method(self) -> None:
        """Test ModelRegistry has list_models method."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()

        assert hasattr(registry, "list_models")
        assert callable(registry.list_models)


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="model_registry_builtin")
class TestBuiltInModels:
    """Tests for built-in model registrations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_claude_opus_4_5_registered(self) -> None:
        """Test Claude Opus 4.5 is registered with correct limits."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("claude-opus-4-5-20251101")

        assert caps is not None
        assert caps.vendor == "anthropic"
        assert caps.context_limit == 200_000
        assert caps.effective_limit == 130_000  # 65% of 200K
        assert caps.max_output_tokens == 64_000
        assert caps.supports_effort_param is True
        assert caps.supports_extended_thinking is True
        assert caps.supports_tools is True
        assert caps.supports_vision is True

    def test_claude_sonnet_4_5_registered(self) -> None:
        """Test Claude Sonnet 4.5 is registered with correct limits."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("claude-sonnet-4-5-20250929")

        assert caps is not None
        assert caps.vendor == "anthropic"
        assert caps.context_limit == 1_000_000  # 1M beta
        assert caps.supports_tools is True
        assert caps.supports_vision is True

    def test_claude_haiku_4_5_registered(self) -> None:
        """Test Claude Haiku 4.5 is registered."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("claude-haiku-4-5-20251001")

        assert caps is not None
        assert caps.vendor == "anthropic"
        assert caps.supports_tools is True

    def test_gemini_3_flash_registered(self) -> None:
        """Test Gemini 3 Flash is registered with correct limits."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("gemini-3-flash")

        assert caps is not None
        assert caps.vendor == "google"
        assert caps.context_limit == 1_000_000
        assert caps.supports_tools is True
        assert caps.supports_vision is True

    def test_gemini_3_pro_registered(self) -> None:
        """Test Gemini 3 Pro is registered with correct limits."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("gemini-3-pro")

        assert caps is not None
        assert caps.vendor == "google"
        assert caps.context_limit == 2_000_000
        assert caps.supports_extended_thinking is True
        assert caps.supports_tools is True

    def test_gpt_5_2_registered(self) -> None:
        """Test GPT-5.2 is registered with correct limits."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("gpt-5.2")

        assert caps is not None
        assert caps.vendor == "openai"
        assert caps.context_limit == 400_000
        assert caps.max_output_tokens == 128_000
        assert caps.supports_tools is True

    def test_gpt_5_2_pro_registered(self) -> None:
        """Test GPT-5.2-pro is registered."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("gpt-5.2-pro")

        assert caps is not None
        assert caps.vendor == "openai"
        assert caps.supports_extended_thinking is True


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="model_registry_lookup")
class TestModelLookup:
    """Tests for model lookup functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_context_limit(self) -> None:
        """Test get_context_limit helper method."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()

        limit = registry.get_context_limit("claude-opus-4-5-20251101")

        assert limit == 200_000

    def test_get_effective_limit(self) -> None:
        """Test get_effective_limit helper method."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()

        limit = registry.get_effective_limit("claude-opus-4-5-20251101")

        assert limit == 130_000

    def test_get_unknown_model_returns_default(self) -> None:
        """Test unknown model returns default capabilities."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("unknown-model-xyz")

        # Should return default fallback
        assert caps is not None
        assert caps.context_limit == 128_000  # Conservative default
        assert caps.effective_limit == int(128_000 * 0.65)

    def test_get_context_limit_unknown_model_returns_default(self) -> None:
        """Test get_context_limit returns default for unknown model."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()

        limit = registry.get_context_limit("unknown-model")

        assert limit == 128_000  # Default

    def test_supports_capability_check(self) -> None:
        """Test supports_capability method."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()

        # Claude Opus supports effort param
        assert registry.supports_capability("claude-opus-4-5-20251101", "effort_param") is True

        # Gemini Flash does not support effort param
        assert registry.supports_capability("gemini-3-flash", "effort_param") is False

        # Both support tools
        assert registry.supports_capability("claude-opus-4-5-20251101", "tools") is True
        assert registry.supports_capability("gemini-3-flash", "tools") is True

    def test_supports_capability_unknown_capability_returns_false(self) -> None:
        """Test unknown capability returns False."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()

        result = registry.supports_capability("claude-opus-4-5-20251101", "unknown_capability")

        assert result is False

    def test_list_models_returns_all_registered(self) -> None:
        """Test list_models returns all registered models."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()

        models = registry.list_models()

        assert len(models) >= 6  # At least our built-in models
        assert "claude-opus-4-5-20251101" in models
        assert "gemini-3-flash" in models
        assert "gpt-5.2" in models

    def test_list_models_by_vendor(self) -> None:
        """Test list_models with vendor filter."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()

        anthropic_models = registry.list_models(vendor="anthropic")

        assert all("claude" in m for m in anthropic_models)
        assert len(anthropic_models) >= 3  # Opus, Sonnet, Haiku

    def test_list_models_by_capability(self) -> None:
        """Test list_models with capability filter."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()

        effort_models = registry.list_models(capability="effort_param")

        # Only Claude Opus 4.5 supports effort param
        assert "claude-opus-4-5-20251101" in effort_models


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="model_registry_registration")
class TestModelRegistration:
    """Tests for custom model registration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_register_custom_model(self) -> None:
        """Test registering a custom model."""
        from mcp_server_langgraph.agents.model_registry import (
            ModelCapabilities,
            ModelRegistry,
        )

        registry = ModelRegistry()

        custom_caps = ModelCapabilities(
            model_id="custom-model-v1",
            vendor="custom",
            context_limit=50_000,
            max_output_tokens=5_000,
            input_cost_per_1m=0.50,
            output_cost_per_1m=1.00,
            supports_tools=True,
        )

        registry.register(custom_caps)

        retrieved = registry.get("custom-model-v1")
        assert retrieved is not None
        assert retrieved.context_limit == 50_000
        assert retrieved.vendor == "custom"

    def test_register_overwrites_existing(self) -> None:
        """Test registering overwrites existing model."""
        from mcp_server_langgraph.agents.model_registry import (
            ModelCapabilities,
            ModelRegistry,
        )

        registry = ModelRegistry()

        # Get original limit
        original = registry.get("gemini-3-flash")
        original_limit = original.context_limit

        # Register replacement
        replacement = ModelCapabilities(
            model_id="gemini-3-flash",
            vendor="google",
            context_limit=999_999,  # Different limit
            max_output_tokens=65_000,
            input_cost_per_1m=0.10,
            output_cost_per_1m=0.40,
        )

        registry.register(replacement)

        updated = registry.get("gemini-3-flash")
        assert updated.context_limit == 999_999
        assert updated.context_limit != original_limit

    def test_unregister_model_returns_default_fallback(self) -> None:
        """Test unregistering a model returns default fallback on get."""
        from mcp_server_langgraph.agents.model_registry import (
            ModelCapabilities,
            ModelRegistry,
        )

        registry = ModelRegistry()

        # Register then unregister
        custom_caps = ModelCapabilities(
            model_id="temp-model",
            vendor="temp",
            context_limit=10_000,
            max_output_tokens=1_000,
            input_cost_per_1m=0.01,
            output_cost_per_1m=0.02,
        )

        registry.register(custom_caps)
        assert registry.get("temp-model") is not None

        registry.unregister("temp-model")

        # Should now return default fallback
        result = registry.get("temp-model")
        assert result.model_id != "temp-model"  # Fallback model


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="model_registry_cost")
class TestCostCalculation:
    """Tests for cost calculation helpers."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_calculate_cost_basic(self) -> None:
        """Test basic cost calculation."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()

        # Claude Opus: $5/1M input, $25/1M output
        cost = registry.calculate_cost(
            model_id="claude-opus-4-5-20251101",
            input_tokens=1000,
            output_tokens=500,
        )

        expected_input_cost = (1000 / 1_000_000) * 5.00
        expected_output_cost = (500 / 1_000_000) * 25.00
        expected_total = expected_input_cost + expected_output_cost

        assert abs(cost - expected_total) < 0.0001

    def test_calculate_cost_large_tokens(self) -> None:
        """Test cost calculation with larger token counts."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()

        # 100K input, 10K output
        cost = registry.calculate_cost(
            model_id="claude-opus-4-5-20251101",
            input_tokens=100_000,
            output_tokens=10_000,
        )

        # Cost breakdown (for documentation):
        # Input: (100_000 / 1_000_000) * 5.00 = $0.50
        # Output: (10_000 / 1_000_000) * 25.00 = $0.25
        expected_total = 0.75

        assert abs(cost - expected_total) < 0.0001

    def test_calculate_cost_unknown_model_uses_default(self) -> None:
        """Test cost calculation for unknown model uses defaults."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()

        cost = registry.calculate_cost(
            model_id="unknown-model",
            input_tokens=1000,
            output_tokens=500,
        )

        # Should return some reasonable cost (default pricing)
        assert cost > 0
        assert cost < 1.0  # Should be reasonable for small token counts


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="model_registry_vertex_ai")
class TestVertexAIModels:
    """Tests for Vertex AI model registrations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_vertex_ai_anthropic_claude_opus_registered(self) -> None:
        """Test Vertex AI Anthropic Claude Opus is registered."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()

        # Vertex AI format uses @ instead of -
        caps = registry.get("claude-opus-4-5@20251101")

        assert caps is not None
        assert caps.vendor == "vertex_ai_anthropic"
        assert caps.context_limit == 200_000

    def test_vertex_ai_gemini_registered(self) -> None:
        """Test Vertex AI Gemini models are registered."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()

        # Vertex AI format
        caps = registry.get("vertex_ai/gemini-3-flash")

        assert caps is not None
        assert caps.vendor in ("google", "vertex_ai")


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="model_registry_azure")
class TestAzureModels:
    """Tests for Azure OpenAI model registrations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_azure_gpt_models_registered(self) -> None:
        """Test Azure GPT models are registered."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()

        # Azure format
        caps = registry.get("azure/gpt-5.2")

        assert caps is not None
        assert caps.vendor in ("openai", "azure")
        assert caps.context_limit == 400_000


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="model_registry_singleton")
class TestModelRegistrySingleton:
    """Tests for singleton pattern."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_default_registry_returns_singleton(self) -> None:
        """Test get_default_registry returns same instance."""
        from mcp_server_langgraph.agents.model_registry import get_default_registry

        registry1 = get_default_registry()
        registry2 = get_default_registry()

        assert registry1 is registry2

    def test_default_registry_has_builtin_models(self) -> None:
        """Test default registry comes with built-in models."""
        from mcp_server_langgraph.agents.model_registry import get_default_registry

        registry = get_default_registry()

        # Should have all built-in models
        assert registry.get("claude-opus-4-5-20251101") is not None
        assert registry.get("gemini-3-flash") is not None
        assert registry.get("gpt-5.2") is not None


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="model_registry_feature_flags")
class TestModelRegistryFeatureFlags:
    """Tests for model registry feature flags."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_enable_model_capabilities_routing_flag_exists(self) -> None:
        """Test that enable_model_capabilities_routing flag exists."""
        from mcp_server_langgraph.core.feature_flags import feature_flags

        assert hasattr(feature_flags, "enable_model_capabilities_routing")

    def test_enable_model_capabilities_routing_default_true(self) -> None:
        """Test that model capabilities routing is enabled by default."""
        from mcp_server_langgraph.core.feature_flags import feature_flags

        assert feature_flags.enable_model_capabilities_routing is True


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="model_registry_tier")
class TestModelCapabilitiesTier:
    """Tests for tier field on ModelCapabilities (Phase 1 orchestration)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_model_capabilities_has_tier_field(self) -> None:
        """Test ModelCapabilities has tier field."""
        from mcp_server_langgraph.agents.model_registry import ModelCapabilities

        caps = ModelCapabilities(
            model_id="test-model",
            vendor="test",
            context_limit=100_000,
            max_output_tokens=10_000,
            input_cost_per_1m=1.0,
            output_cost_per_1m=2.0,
            tier="simple",
        )

        assert hasattr(caps, "tier")
        assert caps.tier == "simple"

    def test_tier_defaults_to_complicated(self) -> None:
        """Test tier defaults to 'complicated' (middle tier)."""
        from mcp_server_langgraph.agents.model_registry import ModelCapabilities

        caps = ModelCapabilities(
            model_id="test-model",
            vendor="test",
            context_limit=100_000,
            max_output_tokens=10_000,
            input_cost_per_1m=1.0,
            output_cost_per_1m=2.0,
        )

        assert caps.tier == "complicated"

    def test_tier_accepts_valid_values(self) -> None:
        """Test tier accepts all valid values: simple, complicated, complex."""
        from mcp_server_langgraph.agents.model_registry import ModelCapabilities

        for tier in ["simple", "complicated", "complex"]:
            caps = ModelCapabilities(
                model_id=f"test-{tier}",
                vendor="test",
                context_limit=100_000,
                max_output_tokens=10_000,
                input_cost_per_1m=1.0,
                output_cost_per_1m=2.0,
                tier=tier,
            )
            assert caps.tier == tier

    def test_builtin_claude_opus_has_complex_tier(self) -> None:
        """Test Claude Opus 4.5 is registered with complex tier."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("claude-opus-4-5-20251101")

        assert caps.tier == "complex"

    def test_builtin_claude_sonnet_has_complicated_tier(self) -> None:
        """Test Claude Sonnet 4.5 is registered with complicated tier."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("claude-sonnet-4-5-20250929")

        assert caps.tier == "complicated"

    def test_builtin_claude_haiku_has_simple_tier(self) -> None:
        """Test Claude Haiku 4.5 is registered with simple tier."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("claude-haiku-4-5-20251001")

        assert caps.tier == "simple"

    def test_builtin_gemini_flash_has_simple_tier(self) -> None:
        """Test Gemini Flash is registered with simple tier."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("gemini-3-flash")

        assert caps.tier == "simple"

    def test_builtin_gemini_pro_has_complex_tier(self) -> None:
        """Test Gemini Pro is registered with complex tier."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("gemini-3-pro")

        assert caps.tier == "complex"

    def test_builtin_gpt_5_2_has_complicated_tier(self) -> None:
        """Test GPT-5.2 is registered with complicated tier."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("gpt-5.2")

        assert caps.tier == "complicated"

    def test_builtin_gpt_5_2_pro_has_complex_tier(self) -> None:
        """Test GPT-5.2-pro is registered with complex tier."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("gpt-5.2-pro")

        assert caps.tier == "complex"

    def test_list_models_by_tier(self) -> None:
        """Test list_models supports tier filter."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()

        complex_models = registry.list_models(tier="complex")

        assert "claude-opus-4-5-20251101" in complex_models
        assert "gemini-3-pro" in complex_models
        assert "gpt-5.2-pro" in complex_models

    def test_all_registered_models_have_tier(self) -> None:
        """Audit test: All registered models must have tier set."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        all_models = registry.list_models()

        for model_id in all_models:
            caps = registry.get(model_id)
            assert caps.tier in ["simple", "complicated", "complex"], f"Model {model_id} has invalid tier: {caps.tier}"


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="model_registry_json_mode")
class TestModelCapabilitiesJsonMode:
    """Tests for supports_json_mode field on ModelCapabilities."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_model_capabilities_has_json_mode_field(self) -> None:
        """Test ModelCapabilities has supports_json_mode field."""
        from mcp_server_langgraph.agents.model_registry import ModelCapabilities

        caps = ModelCapabilities(
            model_id="test-model",
            vendor="test",
            context_limit=100_000,
            max_output_tokens=10_000,
            input_cost_per_1m=1.0,
            output_cost_per_1m=2.0,
            supports_json_mode=True,
        )

        assert hasattr(caps, "supports_json_mode")
        assert caps.supports_json_mode is True

    def test_json_mode_defaults_to_false(self) -> None:
        """Test supports_json_mode defaults to False."""
        from mcp_server_langgraph.agents.model_registry import ModelCapabilities

        caps = ModelCapabilities(
            model_id="test-model",
            vendor="test",
            context_limit=100_000,
            max_output_tokens=10_000,
            input_cost_per_1m=1.0,
            output_cost_per_1m=2.0,
        )

        assert caps.supports_json_mode is False

    def test_supports_capability_includes_json_mode(self) -> None:
        """Test supports_capability works with json_mode."""
        from mcp_server_langgraph.agents.model_registry import (
            ModelCapabilities,
            ModelRegistry,
        )

        registry = ModelRegistry()

        custom_caps = ModelCapabilities(
            model_id="json-capable-model",
            vendor="test",
            context_limit=100_000,
            max_output_tokens=10_000,
            input_cost_per_1m=1.0,
            output_cost_per_1m=2.0,
            supports_json_mode=True,
        )
        registry.register(custom_caps)

        assert registry.supports_capability("json-capable-model", "json_mode") is True


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="model_registry_thinking_tokens")
class TestModelCapabilitiesThinkingTokens:
    """Tests for max_thinking_tokens field on ModelCapabilities."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_model_capabilities_has_max_thinking_tokens_field(self) -> None:
        """Test ModelCapabilities has max_thinking_tokens field."""
        from mcp_server_langgraph.agents.model_registry import ModelCapabilities

        caps = ModelCapabilities(
            model_id="test-model",
            vendor="test",
            context_limit=100_000,
            max_output_tokens=10_000,
            input_cost_per_1m=1.0,
            output_cost_per_1m=2.0,
            max_thinking_tokens=32768,
        )

        assert hasattr(caps, "max_thinking_tokens")
        assert caps.max_thinking_tokens == 32768

    def test_max_thinking_tokens_defaults_to_none(self) -> None:
        """Test max_thinking_tokens defaults to None (not supported)."""
        from mcp_server_langgraph.agents.model_registry import ModelCapabilities

        caps = ModelCapabilities(
            model_id="test-model",
            vendor="test",
            context_limit=100_000,
            max_output_tokens=10_000,
            input_cost_per_1m=1.0,
            output_cost_per_1m=2.0,
        )

        assert caps.max_thinking_tokens is None

    def test_builtin_claude_opus_has_max_thinking_tokens(self) -> None:
        """Test Claude Opus 4.5 has max_thinking_tokens set (supports thinking)."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("claude-opus-4-5-20251101")

        assert caps.max_thinking_tokens is not None
        assert caps.max_thinking_tokens > 0

    def test_builtin_gemini_pro_has_max_thinking_tokens(self) -> None:
        """Test Gemini Pro has max_thinking_tokens set (Deep Think)."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("gemini-3-pro")

        assert caps.supports_extended_thinking is True
        assert caps.max_thinking_tokens is not None

    def test_builtin_haiku_has_no_thinking_tokens(self) -> None:
        """Test Claude Haiku has no thinking tokens (not supported)."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("claude-haiku-4-5-20251001")

        assert caps.supports_extended_thinking is False
        assert caps.max_thinking_tokens is None

    def test_all_thinking_models_have_max_tokens_set(self) -> None:
        """Audit: All models with extended_thinking must have max_thinking_tokens."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        all_models = registry.list_models()

        for model_id in all_models:
            caps = registry.get(model_id)
            if caps.supports_extended_thinking:
                assert caps.max_thinking_tokens is not None, (
                    f"Model {model_id} supports extended_thinking but has no max_thinking_tokens"
                )


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="model_registry_capabilities_set")
class TestModelCapabilitiesSet:
    """Tests for capabilities aggregation property."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_model_capabilities_has_capabilities_property(self) -> None:
        """Test ModelCapabilities has capabilities property returning set."""
        from mcp_server_langgraph.agents.model_registry import ModelCapabilities

        caps = ModelCapabilities(
            model_id="test-model",
            vendor="test",
            context_limit=100_000,
            max_output_tokens=10_000,
            input_cost_per_1m=1.0,
            output_cost_per_1m=2.0,
            supports_vision=True,
            supports_tools=True,
            supports_streaming=True,
        )

        assert hasattr(caps, "capabilities")
        capabilities = caps.capabilities
        assert isinstance(capabilities, set)
        assert "vision" in capabilities
        assert "tools" in capabilities
        assert "streaming" in capabilities

    def test_capabilities_includes_all_enabled_flags(self) -> None:
        """Test capabilities property includes all enabled capability flags."""
        from mcp_server_langgraph.agents.model_registry import ModelCapabilities

        caps = ModelCapabilities(
            model_id="full-model",
            vendor="test",
            context_limit=100_000,
            max_output_tokens=10_000,
            input_cost_per_1m=1.0,
            output_cost_per_1m=2.0,
            supports_vision=True,
            supports_tools=True,
            supports_streaming=True,
            supports_extended_thinking=True,
            supports_effort_param=True,
            supports_json_mode=True,
        )

        capabilities = caps.capabilities
        expected = {"vision", "tools", "streaming", "extended_thinking", "effort_param", "json_mode"}
        assert capabilities == expected

    def test_capabilities_excludes_disabled_flags(self) -> None:
        """Test capabilities property excludes disabled capability flags."""
        from mcp_server_langgraph.agents.model_registry import ModelCapabilities

        caps = ModelCapabilities(
            model_id="minimal-model",
            vendor="test",
            context_limit=100_000,
            max_output_tokens=10_000,
            input_cost_per_1m=1.0,
            output_cost_per_1m=2.0,
            supports_tools=True,  # Only this enabled
        )

        capabilities = caps.capabilities
        assert "tools" in capabilities
        assert "vision" not in capabilities
        assert "streaming" not in capabilities
