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

    def test_builtin_haiku_4_5_has_thinking_tokens(self) -> None:
        """Test Claude Haiku 4.5 has thinking tokens (first Haiku with extended thinking).

        Per Anthropic announcement (Oct 2025): Claude Haiku 4.5 is 'the first Haiku
        model to support extended thinking'.
        """
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("claude-haiku-4-5-20251001")

        assert caps.supports_extended_thinking is True
        assert caps.max_thinking_tokens is not None
        assert caps.max_thinking_tokens >= 1024  # Minimum per Anthropic docs

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


# =============================================================================
# Frontend Integration Tests (Sprint 1 - Enhanced Model Selector)
# =============================================================================


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="model_registry_frontend")
class TestModelRegistryFrontendIntegration:
    """Tests for frontend model list generation from ModelRegistry.

    Sprint 1: Enhanced Model Selector - Single source of truth for model capabilities.
    The ModelRegistry should be able to generate the frontend-compatible model list
    that was previously hardcoded in AVAILABLE_MODELS.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_model_capabilities_has_display_name_field(self) -> None:
        """Test ModelCapabilities has display_name field for frontend display."""
        from mcp_server_langgraph.agents.model_registry import ModelCapabilities

        caps = ModelCapabilities(
            model_id="claude-opus-4-5-20251101",
            vendor="anthropic",
            context_limit=200_000,
            max_output_tokens=64_000,
            input_cost_per_1m=5.00,
            output_cost_per_1m=25.00,
            display_name="Claude Opus 4.5",
        )

        assert hasattr(caps, "display_name")
        assert caps.display_name == "Claude Opus 4.5"

    def test_model_capabilities_has_public_id_field(self) -> None:
        """Test ModelCapabilities has public_id field for user-friendly ID."""
        from mcp_server_langgraph.agents.model_registry import ModelCapabilities

        caps = ModelCapabilities(
            model_id="claude-opus-4-5-20251101",
            vendor="anthropic",
            context_limit=200_000,
            max_output_tokens=64_000,
            input_cost_per_1m=5.00,
            output_cost_per_1m=25.00,
            public_id="claude-3-opus",
        )

        assert hasattr(caps, "public_id")
        assert caps.public_id == "claude-3-opus"

    def test_model_capabilities_display_name_defaults_to_model_id(self) -> None:
        """Test display_name defaults to model_id if not specified."""
        from mcp_server_langgraph.agents.model_registry import ModelCapabilities

        caps = ModelCapabilities(
            model_id="some-internal-model",
            vendor="test",
            context_limit=100_000,
            max_output_tokens=10_000,
            input_cost_per_1m=1.0,
            output_cost_per_1m=2.0,
        )

        # display_name should default to model_id
        assert caps.display_name == "some-internal-model"

    def test_model_capabilities_public_id_defaults_to_model_id(self) -> None:
        """Test public_id defaults to model_id if not specified."""
        from mcp_server_langgraph.agents.model_registry import ModelCapabilities

        caps = ModelCapabilities(
            model_id="some-internal-model",
            vendor="test",
            context_limit=100_000,
            max_output_tokens=10_000,
            input_cost_per_1m=1.0,
            output_cost_per_1m=2.0,
        )

        # public_id should default to model_id
        assert caps.public_id == "some-internal-model"

    def test_model_registry_has_get_frontend_models_method(self) -> None:
        """Test ModelRegistry has get_frontend_models method."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()

        assert hasattr(registry, "get_frontend_models")
        assert callable(registry.get_frontend_models)

    def test_get_frontend_models_returns_list_of_dicts(self) -> None:
        """Test get_frontend_models returns list of dictionaries."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        models = registry.get_frontend_models()

        assert isinstance(models, list)
        assert len(models) > 0
        assert all(isinstance(m, dict) for m in models)

    def test_get_frontend_models_has_required_fields(self) -> None:
        """Test frontend models have all required fields for Enhanced Model Selector."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        models = registry.get_frontend_models()

        # Required fields for frontend Enhanced Model Selector (Sprint 1)
        required_fields = [
            "id",
            "name",
            "provider",
            "supports_thinking",
            "supports_vision",
            "supports_tools",
        ]

        for model in models:
            for field in required_fields:
                assert field in model, f"Model missing required field: {field}"

    def test_get_frontend_models_uses_public_id_as_id(self) -> None:
        """Test frontend models use public_id as the 'id' field."""
        from mcp_server_langgraph.agents.model_registry import (
            ModelCapabilities,
            ModelRegistry,
        )

        registry = ModelRegistry()

        # Register a model with explicit public_id
        custom = ModelCapabilities(
            model_id="internal-test-model-v1",
            vendor="test",
            context_limit=100_000,
            max_output_tokens=10_000,
            input_cost_per_1m=1.0,
            output_cost_per_1m=2.0,
            public_id="test-model",
            display_name="Test Model",
        )
        registry.register(custom)

        models = registry.get_frontend_models()
        test_model = next((m for m in models if m["id"] == "test-model"), None)

        assert test_model is not None
        assert test_model["id"] == "test-model"  # public_id
        assert test_model["name"] == "Test Model"  # display_name

    def test_get_frontend_models_uses_display_name_as_name(self) -> None:
        """Test frontend models use display_name as the 'name' field."""
        from mcp_server_langgraph.agents.model_registry import (
            ModelCapabilities,
            ModelRegistry,
        )

        registry = ModelRegistry()

        custom = ModelCapabilities(
            model_id="some-internal-id",
            vendor="test",
            context_limit=100_000,
            max_output_tokens=10_000,
            input_cost_per_1m=1.0,
            output_cost_per_1m=2.0,
            display_name="User Friendly Name",
        )
        registry.register(custom)

        models = registry.get_frontend_models()
        test_model = next((m for m in models if m["name"] == "User Friendly Name"), None)

        assert test_model is not None
        assert test_model["name"] == "User Friendly Name"

    def test_get_frontend_models_maps_vendor_to_provider(self) -> None:
        """Test frontend models map vendor to provider field."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        models = registry.get_frontend_models()

        # Check we have models from different providers
        providers = {m["provider"] for m in models}
        assert "anthropic" in providers
        assert "google" in providers or "vertex_ai" in providers
        assert "openai" in providers or "azure" in providers

    def test_get_frontend_models_maps_supports_thinking_correctly(self) -> None:
        """Test supports_thinking maps from supports_extended_thinking."""
        from mcp_server_langgraph.agents.model_registry import (
            ModelCapabilities,
            ModelRegistry,
        )

        registry = ModelRegistry()

        # Model with extended thinking
        thinking_model = ModelCapabilities(
            model_id="thinking-test",
            vendor="test",
            context_limit=100_000,
            max_output_tokens=10_000,
            input_cost_per_1m=1.0,
            output_cost_per_1m=2.0,
            supports_extended_thinking=True,
            public_id="thinking-test",
        )
        registry.register(thinking_model)

        # Model without extended thinking
        no_thinking_model = ModelCapabilities(
            model_id="no-thinking-test",
            vendor="test",
            context_limit=100_000,
            max_output_tokens=10_000,
            input_cost_per_1m=1.0,
            output_cost_per_1m=2.0,
            supports_extended_thinking=False,
            public_id="no-thinking-test",
        )
        registry.register(no_thinking_model)

        models = registry.get_frontend_models()

        thinking = next((m for m in models if m["id"] == "thinking-test"), None)
        no_thinking = next((m for m in models if m["id"] == "no-thinking-test"), None)

        assert thinking is not None
        assert thinking["supports_thinking"] is True

        assert no_thinking is not None
        assert no_thinking["supports_thinking"] is False

    def test_get_frontend_models_excludes_internal_models(self) -> None:
        """Test get_frontend_models can filter out internal-only models."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        models = registry.get_frontend_models()

        # Should not expose Vertex AI internal model IDs directly
        # Models with public_id should use that, not the internal ID
        model_ids = [m["id"] for m in models]

        # Verify we're getting user-friendly IDs
        for model_id in model_ids:
            # Internal Vertex AI format shouldn't leak through
            assert not model_id.startswith("vertex_ai/claude"), f"Internal model ID leaked: {model_id}"

    def test_builtin_claude_models_have_frontend_fields(self) -> None:
        """Test built-in Claude models have proper frontend fields."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()

        # Check Claude Opus 4.5 has display_name and public_id
        caps = registry.get("claude-opus-4-5-20251101")

        assert caps.display_name is not None
        assert len(caps.display_name) > 0
        assert caps.public_id is not None
        assert len(caps.public_id) > 0

    def test_get_frontend_models_includes_all_capability_badges(self) -> None:
        """Test frontend models include all capability badge fields (Sprint 1)."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        models = registry.get_frontend_models()

        for model in models:
            # All capability badge fields must be booleans
            assert isinstance(model["supports_thinking"], bool)
            assert isinstance(model["supports_vision"], bool)
            assert isinstance(model["supports_tools"], bool)


# =============================================================================
# Model Status Tests (TDD - Lifecycle Status Field)
# =============================================================================


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="model_registry_status")
class TestModelCapabilitiesStatus:
    """Tests for status field on ModelCapabilities (lifecycle status).

    Models have a lifecycle status:
    - current: Generally available, recommended for production
    - preview: Preview/beta, feature-complete but not GA
    - legacy: Older version, still supported but superseded
    - deprecated: Scheduled for retirement, migrate away
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_model_status_type_literal_exists(self) -> None:
        """Test ModelStatus type literal exists in module."""
        from mcp_server_langgraph.agents.model_registry import ModelStatus

        assert ModelStatus is not None

    def test_model_capabilities_has_status_field(self) -> None:
        """Test ModelCapabilities has status field."""
        from mcp_server_langgraph.agents.model_registry import ModelCapabilities

        caps = ModelCapabilities(
            model_id="test-model",
            vendor="test",
            context_limit=100_000,
            max_output_tokens=10_000,
            input_cost_per_1m=1.0,
            output_cost_per_1m=2.0,
            status="current",
        )

        assert hasattr(caps, "status")
        assert caps.status == "current"

    def test_status_defaults_to_current(self) -> None:
        """Test status defaults to 'current' for new models."""
        from mcp_server_langgraph.agents.model_registry import ModelCapabilities

        caps = ModelCapabilities(
            model_id="test-model",
            vendor="test",
            context_limit=100_000,
            max_output_tokens=10_000,
            input_cost_per_1m=1.0,
            output_cost_per_1m=2.0,
        )

        assert caps.status == "current"

    def test_status_accepts_valid_values(self) -> None:
        """Test status accepts all valid lifecycle values."""
        from mcp_server_langgraph.agents.model_registry import ModelCapabilities

        for status in ["current", "preview", "legacy", "deprecated"]:
            caps = ModelCapabilities(
                model_id=f"test-{status}",
                vendor="test",
                context_limit=100_000,
                max_output_tokens=10_000,
                input_cost_per_1m=1.0,
                output_cost_per_1m=2.0,
                status=status,
            )
            assert caps.status == status

    def test_all_registered_models_have_valid_status(self) -> None:
        """Audit test: All registered models must have valid status."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        all_models = registry.list_models()
        valid_statuses = {"current", "preview", "legacy", "deprecated"}

        for model_id in all_models:
            caps = registry.get(model_id)
            assert caps.status in valid_statuses, f"Model {model_id} has invalid status: {caps.status}"


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="model_registry_status_builtin")
class TestBuiltInModelStatuses:
    """Tests for correct status assignments on built-in models.

    Based on official provider documentation (Jan 2026):
    - Current: Claude 4.5, Gemini 2.5, GPT-5.x, o3, o4-mini
    - Preview: Gemini 3.x (-preview suffix)
    - Legacy: GPT-4o, GPT-4-turbo
    - Deprecated: o1-preview, o1-mini
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    # =========================================================================
    # Anthropic Claude 4.5 Models (CURRENT)
    # =========================================================================

    def test_claude_opus_4_5_is_current(self) -> None:
        """Test Claude Opus 4.5 has current status (GA Nov 2025)."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("claude-opus-4-5-20251101")

        assert caps.status == "current"

    def test_claude_sonnet_4_5_is_current(self) -> None:
        """Test Claude Sonnet 4.5 has current status (GA Sep 2025)."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("claude-sonnet-4-5-20250929")

        assert caps.status == "current"

    def test_claude_haiku_4_5_is_current(self) -> None:
        """Test Claude Haiku 4.5 has current status (GA Oct 2025)."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("claude-haiku-4-5-20251001")

        assert caps.status == "current"

    # =========================================================================
    # Google Gemini 2.5 Models (CURRENT)
    # =========================================================================

    def test_gemini_2_5_flash_is_current(self) -> None:
        """Test Gemini 2.5 Flash has current status (GA Aug 2025)."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("gemini-2.5-flash")

        assert caps.status == "current"

    def test_gemini_2_5_pro_is_current(self) -> None:
        """Test Gemini 2.5 Pro has current status (GA Aug 2025)."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("gemini-2.5-pro")

        assert caps.status == "current"

    # =========================================================================
    # Google Gemini 3 Models (PREVIEW - not yet GA)
    # =========================================================================

    def test_gemini_3_flash_is_preview(self) -> None:
        """Test Gemini 3 Flash has preview status (not yet GA)."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("gemini-3-flash")

        assert caps.status == "preview"

    def test_gemini_3_pro_is_preview(self) -> None:
        """Test Gemini 3 Pro has preview status (not yet GA)."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("gemini-3-pro")

        assert caps.status == "preview"

    def test_vertex_ai_gemini_3_flash_preview_is_preview(self) -> None:
        """Test Vertex AI Gemini 3 Flash Preview has preview status."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("vertex_ai/gemini-3-flash-preview")

        assert caps.status == "preview"

    def test_vertex_ai_gemini_3_pro_preview_is_preview(self) -> None:
        """Test Vertex AI Gemini 3 Pro Preview has preview status."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("vertex_ai/gemini-3-pro-preview")

        assert caps.status == "preview"

    # =========================================================================
    # OpenAI GPT-5.x Models (CURRENT)
    # =========================================================================

    def test_gpt_5_2_is_current(self) -> None:
        """Test GPT-5.2 has current status (latest GA)."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("gpt-5.2")

        assert caps.status == "current"

    def test_gpt_5_2_pro_is_current(self) -> None:
        """Test GPT-5.2-pro has current status (latest reasoning)."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("gpt-5.2-pro")

        assert caps.status == "current"

    # =========================================================================
    # OpenAI o3/o4 Models (CURRENT)
    # =========================================================================

    def test_o3_is_current(self) -> None:
        """Test o3 has current status (latest reasoning model)."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("o3")

        assert caps.status == "current"

    # =========================================================================
    # OpenAI Legacy Models (LEGACY - older but still supported)
    # =========================================================================

    def test_gpt_4o_is_legacy(self) -> None:
        """Test GPT-4o has legacy status (superseded by GPT-5.x)."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("gpt-4o")

        assert caps.status == "legacy"

    def test_gpt_4o_mini_is_legacy(self) -> None:
        """Test GPT-4o-mini has legacy status (superseded by GPT-5.x)."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("gpt-4o-mini")

        assert caps.status == "legacy"

    def test_gpt_4_turbo_is_legacy(self) -> None:
        """Test GPT-4-turbo has legacy status (superseded by GPT-5.x)."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("gpt-4-turbo")

        assert caps.status == "legacy"

    def test_gpt_4_1_nano_is_legacy(self) -> None:
        """Test GPT-4.1-nano has legacy status."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("gpt-4.1-nano")

        assert caps.status == "legacy"

    def test_gpt_4_1_mini_is_legacy(self) -> None:
        """Test GPT-4.1-mini has legacy status."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("gpt-4.1-mini")

        assert caps.status == "legacy"

    # =========================================================================
    # OpenAI Deprecated Models (DEPRECATED - scheduled for retirement)
    # =========================================================================

    def test_o1_preview_is_deprecated(self) -> None:
        """Test o1-preview has deprecated status (replaced by o3)."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("o1-preview")

        assert caps.status == "deprecated"

    def test_o1_mini_is_deprecated(self) -> None:
        """Test o1-mini has deprecated status (replaced by o3)."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("o1-mini")

        assert caps.status == "deprecated"

    # =========================================================================
    # Google Legacy Models (LEGACY)
    # =========================================================================

    def test_gemini_pro_is_legacy(self) -> None:
        """Test Gemini Pro (1.0) has legacy status (superseded by 2.5)."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("gemini-pro")

        assert caps.status == "legacy"


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="model_registry_status_filter")
class TestModelStatusFiltering:
    """Tests for filtering models by status."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_models_supports_status_filter(self) -> None:
        """Test list_models supports filtering by status."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()

        current_models = registry.list_models(status="current")
        preview_models = registry.list_models(status="preview")
        legacy_models = registry.list_models(status="legacy")
        deprecated_models = registry.list_models(status="deprecated")

        # Should have models in each category
        assert len(current_models) > 0, "No current models found"
        assert len(preview_models) > 0, "No preview models found"
        assert len(legacy_models) > 0, "No legacy models found"
        assert len(deprecated_models) > 0, "No deprecated models found"

    def test_list_models_current_excludes_deprecated(self) -> None:
        """Test current filter excludes deprecated models."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()

        current_models = registry.list_models(status="current")

        # Deprecated models should not be in current
        assert "o1-preview" not in current_models
        assert "o1-mini" not in current_models

    def test_list_models_status_combined_with_vendor(self) -> None:
        """Test status filter combines with vendor filter."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()

        current_anthropic = registry.list_models(vendor="anthropic", status="current")

        # All results should be current Anthropic models
        for model_id in current_anthropic:
            caps = registry.get(model_id)
            assert caps.vendor == "anthropic"
            assert caps.status == "current"

    def test_get_frontend_models_includes_status(self) -> None:
        """Test get_frontend_models includes status field for frontend filtering."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        models = registry.get_frontend_models()

        # Every frontend model should have status field
        for model in models:
            assert "status" in model, f"Model missing status: {model.get('id')}"
            assert model["status"] in {"current", "preview", "legacy", "deprecated"}

    def test_get_frontend_models_can_filter_by_status(self) -> None:
        """Test get_frontend_models can optionally filter by status."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()

        # Get all models
        all_models = registry.get_frontend_models()

        # Get only current (recommended for production)
        current_models = registry.get_frontend_models(status="current")

        # Current should be subset of all
        assert len(current_models) < len(all_models)
        assert all(m["status"] == "current" for m in current_models)


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="model_registry_sunset_date")
class TestModelSunsetDate:
    """Tests for sunset_date field on ModelCapabilities.

    Deprecated models should have a sunset_date indicating when they will be retired.
    This enables frontend deprecation warnings and migration planning.

    Sprint 2 - Enhanced Model Selector: Model Deprecation Warnings
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_model_capabilities_has_sunset_date_field(self) -> None:
        """Test ModelCapabilities has optional sunset_date field."""
        from mcp_server_langgraph.agents.model_registry import ModelCapabilities

        caps = ModelCapabilities(
            model_id="test-model",
            vendor="test",
            context_limit=100_000,
            max_output_tokens=10_000,
            input_cost_per_1m=1.0,
            output_cost_per_1m=2.0,
            status="deprecated",
            sunset_date="2026-06-01",
        )

        assert hasattr(caps, "sunset_date")
        assert caps.sunset_date == "2026-06-01"

    def test_sunset_date_defaults_to_none(self) -> None:
        """Test sunset_date defaults to None for non-deprecated models."""
        from mcp_server_langgraph.agents.model_registry import ModelCapabilities

        caps = ModelCapabilities(
            model_id="test-model",
            vendor="test",
            context_limit=100_000,
            max_output_tokens=10_000,
            input_cost_per_1m=1.0,
            output_cost_per_1m=2.0,
        )

        assert caps.sunset_date is None

    def test_deprecated_models_should_have_sunset_date(self) -> None:
        """Test deprecated models in registry have sunset_date set."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        deprecated_models = registry.list_models(status="deprecated")

        for model_id in deprecated_models:
            caps = registry.get(model_id)
            assert caps.sunset_date is not None, f"Deprecated model {model_id} should have sunset_date"

    def test_sunset_date_format_is_iso_date(self) -> None:
        """Test sunset_date uses ISO 8601 date format (YYYY-MM-DD)."""
        from datetime import datetime

        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        deprecated_models = registry.list_models(status="deprecated")

        for model_id in deprecated_models:
            caps = registry.get(model_id)
            if caps.sunset_date:
                # Should parse as ISO date
                try:
                    datetime.strptime(caps.sunset_date, "%Y-%m-%d")
                except ValueError:
                    pytest.fail(f"Model {model_id} has invalid sunset_date format: {caps.sunset_date} (expected YYYY-MM-DD)")

    def test_get_frontend_models_includes_sunset_date(self) -> None:
        """Test get_frontend_models includes sunset_date for deprecated models."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        models = registry.get_frontend_models()

        for model in models:
            if model.get("status") == "deprecated":
                assert "sunset_date" in model, f"Deprecated model {model.get('id')} missing sunset_date in frontend data"

    def test_current_models_sunset_date_is_none_or_absent(self) -> None:
        """Test current models don't have sunset_date."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        current_models = registry.list_models(status="current")

        for model_id in current_models:
            caps = registry.get(model_id)
            assert caps.sunset_date is None, f"Current model {model_id} should not have sunset_date"


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="model_registry_thinking")
class TestModelExtendedThinkingCapabilities:
    """
    Tests for extended thinking capabilities in ModelRegistry.

    These tests validate that models are correctly configured with
    supports_extended_thinking and max_thinking_tokens based on
    actual provider capabilities.

    Reference sources:
    - Google Gemini 3 docs: Both Flash and Pro support thinking_level
    - Anthropic Claude 4.5 docs: Haiku 4.5 supports extended thinking
    - OpenAI docs: o3-mini supports reasoning_effort, gpt-4.5 does NOT
    - LiteLLM model_cost data: supports_reasoning field
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        import gc

        gc.collect()

    # =========================================================================
    # Gemini 3 Flash - MUST support extended thinking
    # Per Google docs: gemini-3-flash supports thinking_level parameter
    # =========================================================================

    def test_gemini_3_flash_supports_extended_thinking(self) -> None:
        """Test Gemini 3 Flash supports extended thinking.

        Per Google's Gemini 3 Developer Guide, BOTH Flash and Pro support
        the thinking_level parameter. Flash even has MORE options (minimal,
        low, medium, high) than Pro (low, high).
        """
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("gemini-3-flash")

        assert caps.supports_extended_thinking is True, "Gemini 3 Flash MUST support extended thinking per Google docs"

    def test_gemini_3_flash_has_thinking_tokens(self) -> None:
        """Test Gemini 3 Flash has max_thinking_tokens configured."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("gemini-3-flash")

        assert caps.max_thinking_tokens is not None, "Gemini 3 Flash should have max_thinking_tokens set"
        assert caps.max_thinking_tokens >= 8192, "Gemini 3 Flash should have reasonable thinking budget"

    # =========================================================================
    # Gemini 2.5 Flash - MUST support extended thinking
    # Per Google docs: gemini-2.5-flash supports thinking_budget parameter
    # =========================================================================

    def test_gemini_2_5_flash_supports_extended_thinking(self) -> None:
        """Test Gemini 2.5 Flash supports extended thinking.

        Per Google's docs, Gemini 2.5 Flash is a 'hybrid reasoning model'
        that supports thinking_budget (0 to 24576 tokens).
        """
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("gemini-2.5-flash")

        assert caps.supports_extended_thinking is True, "Gemini 2.5 Flash MUST support extended thinking per Google docs"

    def test_gemini_2_5_flash_has_thinking_tokens(self) -> None:
        """Test Gemini 2.5 Flash has max_thinking_tokens configured."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("gemini-2.5-flash")

        assert caps.max_thinking_tokens is not None
        # Gemini 2.5 Flash budget is 0-24576
        assert caps.max_thinking_tokens <= 24576

    # =========================================================================
    # Claude Haiku 4.5 - MUST support extended thinking
    # Per Anthropic docs: "first Haiku model to support extended thinking"
    # =========================================================================

    def test_claude_haiku_4_5_supports_extended_thinking(self) -> None:
        """Test Claude Haiku 4.5 supports extended thinking.

        Per Anthropic's announcement, Claude Haiku 4.5 is 'the first Haiku
        model to support extended thinking'.
        """
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("claude-haiku-4-5-20251001")

        assert caps.supports_extended_thinking is True, "Claude Haiku 4.5 MUST support extended thinking per Anthropic docs"

    def test_claude_haiku_4_5_has_thinking_tokens(self) -> None:
        """Test Claude Haiku 4.5 has max_thinking_tokens configured."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("claude-haiku-4-5-20251001")

        assert caps.max_thinking_tokens is not None
        # Minimum thinking budget for Anthropic is 1024
        assert caps.max_thinking_tokens >= 1024

    # =========================================================================
    # o3-mini - MUST support extended thinking
    # Per OpenAI docs: o3-mini supports reasoning_effort (low, medium, high)
    # =========================================================================

    def test_o3_mini_supports_extended_thinking(self) -> None:
        """Test o3-mini supports extended thinking.

        Per OpenAI's docs, o3-mini supports the reasoning_effort parameter
        with low, medium, high values.
        """
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("o3-mini")

        assert caps.supports_extended_thinking is True, "o3-mini MUST support extended thinking per OpenAI docs"

    def test_o3_mini_has_thinking_tokens(self) -> None:
        """Test o3-mini has max_thinking_tokens configured."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("o3-mini")

        assert caps.max_thinking_tokens is not None
        assert caps.max_thinking_tokens >= 8192

    # =========================================================================
    # o4-mini - New model, MUST exist and support extended thinking
    # Per OpenAI docs: o4-mini is latest reasoning model with 128K context
    # =========================================================================

    def test_o4_mini_exists_in_registry(self) -> None:
        """Test o4-mini model exists in registry.

        o4-mini was released April 2025 as the successor to o3-mini,
        with 128K context and improved reasoning.
        """
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("o4-mini")

        assert caps is not None, "o4-mini should exist in registry"

    def test_o4_mini_supports_extended_thinking(self) -> None:
        """Test o4-mini supports extended thinking."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("o4-mini")

        assert caps.supports_extended_thinking is True

    def test_o4_mini_has_128k_context(self) -> None:
        """Test o4-mini has 128K context window."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("o4-mini")

        assert caps.context_limit >= 128_000

    # =========================================================================
    # gpt-4.5 - MUST NOT support extended thinking
    # Per OpenAI docs: "GPT-4.5 doesn't think before it responds"
    # =========================================================================

    def test_gpt_4_5_does_not_support_extended_thinking(self) -> None:
        """Test gpt-4.5 does NOT support extended thinking.

        Per OpenAI's announcement, 'GPT-4.5 doesn't think before it responds,
        making its strengths different from reasoning models like o1.'
        """
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("gpt-4.5")

        assert caps.supports_extended_thinking is False, "gpt-4.5 should NOT support extended thinking per OpenAI docs"

    def test_gpt_4_5_has_no_thinking_tokens(self) -> None:
        """Test gpt-4.5 has no max_thinking_tokens."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("gpt-4.5")

        assert caps.max_thinking_tokens is None, "gpt-4.5 should have no thinking tokens since it doesn't reason"

    # =========================================================================
    # Existing models - verify they still work
    # =========================================================================

    def test_gemini_3_pro_supports_extended_thinking(self) -> None:
        """Test Gemini 3 Pro supports extended thinking (existing behavior)."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("gemini-3-pro")

        assert caps.supports_extended_thinking is True

    def test_claude_opus_4_5_supports_extended_thinking(self) -> None:
        """Test Claude Opus 4.5 supports extended thinking (existing behavior)."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("claude-opus-4-5-20251101")

        assert caps.supports_extended_thinking is True

    def test_claude_sonnet_4_5_supports_extended_thinking(self) -> None:
        """Test Claude Sonnet 4.5 supports extended thinking (existing behavior)."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("claude-sonnet-4-5-20250929")

        assert caps.supports_extended_thinking is True

    def test_o1_preview_supports_extended_thinking(self) -> None:
        """Test o1-preview supports extended thinking (existing behavior)."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("o1-preview")

        assert caps.supports_extended_thinking is True


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.xdist_group(name="model_registry_native_tools")
class TestModelNativeToolCapabilities:
    """Tests for native LLM provider tool capabilities (v7).

    Verifies that models correctly report their native tool support:
    - Anthropic: web_search_20250305, code_execution_20250825
    - Google: googleSearch (grounded search)
    - OpenAI: web_search, code_interpreter (via Responses API)

    Also tests Vertex AI variants which have different capabilities.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    # =========================================================================
    # Direct API Models (Full Native Tool Support)
    # =========================================================================

    def test_claude_opus_4_5_supports_native_web_search(self) -> None:
        """Test Claude Opus 4.5 (direct API) supports native web search."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("claude-opus-4-5-20251101")

        assert caps.supports_native_web_search is True
        assert caps.native_provider == "anthropic"

    def test_claude_opus_4_5_supports_native_code_execution(self) -> None:
        """Test Claude Opus 4.5 (direct API) supports native code execution."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("claude-opus-4-5-20251101")

        assert caps.supports_native_code_execution is True

    def test_gemini_3_flash_supports_native_web_search(self) -> None:
        """Test Gemini 3 Flash (direct API) supports native web search."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("gemini-3-flash")

        assert caps.supports_native_web_search is True
        assert caps.native_provider == "google"

    def test_gpt_5_2_supports_native_web_search(self) -> None:
        """Test GPT-5.2 supports native web search via Responses API."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("gpt-5.2")

        assert caps.supports_native_web_search is True
        assert caps.native_provider == "openai"

    def test_gpt_5_2_supports_native_code_execution(self) -> None:
        """Test GPT-5.2 supports native code interpreter via Responses API."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("gpt-5.2")

        assert caps.supports_native_code_execution is True

    # =========================================================================
    # Vertex AI Anthropic Models (Web Search Only, No Code Execution)
    # =========================================================================

    def test_vertex_ai_claude_opus_supports_native_web_search(self) -> None:
        """Test Claude Opus 4.5 via Vertex AI supports native web search."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("claude-opus-4-5@20251101")

        assert caps.supports_native_web_search is True
        assert caps.native_provider == "anthropic"
        assert caps.vendor == "vertex_ai_anthropic"

    def test_vertex_ai_claude_opus_no_code_execution(self) -> None:
        """Test Claude Opus 4.5 via Vertex AI does NOT support code execution.

        Code execution is only available via direct Anthropic API or AWS Bedrock,
        not through Google Cloud Vertex AI.
        """
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("claude-opus-4-5@20251101")

        # Code execution NOT supported on Vertex AI
        assert caps.supports_native_code_execution is False

    def test_vertex_ai_claude_sonnet_supports_native_web_search(self) -> None:
        """Test Claude Sonnet 4.5 via Vertex AI supports native web search."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("claude-sonnet-4-5@20250929")

        assert caps.supports_native_web_search is True
        assert caps.native_provider == "anthropic"

    def test_vertex_ai_claude_haiku_supports_native_web_search(self) -> None:
        """Test Claude Haiku 4.5 via Vertex AI supports native web search."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("claude-haiku-4-5@20251001")

        assert caps.supports_native_web_search is True
        assert caps.native_provider == "anthropic"

    # =========================================================================
    # Vertex AI Gemini Models (Google Search Grounding)
    # =========================================================================

    def test_vertex_ai_gemini_3_flash_supports_native_web_search(self) -> None:
        """Test Gemini 3 Flash via Vertex AI supports googleSearch grounding."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("vertex_ai/gemini-3-flash")

        assert caps.supports_native_web_search is True
        assert caps.native_provider == "google"
        assert caps.vendor == "vertex_ai"

    def test_vertex_ai_gemini_3_pro_supports_native_web_search(self) -> None:
        """Test Gemini 3 Pro via Vertex AI supports googleSearch grounding."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("vertex_ai/gemini-3-pro")

        assert caps.supports_native_web_search is True
        assert caps.native_provider == "google"

    def test_vertex_ai_gemini_3_flash_preview_supports_native_web_search(self) -> None:
        """Test Gemini 3 Flash Preview via Vertex AI supports googleSearch."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("vertex_ai/gemini-3-flash-preview")

        assert caps.supports_native_web_search is True
        assert caps.native_provider == "google"

    def test_vertex_ai_gemini_3_pro_preview_supports_native_web_search(self) -> None:
        """Test Gemini 3 Pro Preview via Vertex AI supports googleSearch."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("vertex_ai/gemini-3-pro-preview")

        assert caps.supports_native_web_search is True
        assert caps.native_provider == "google"

    # =========================================================================
    # Models Without Native Tool Support
    # =========================================================================

    def test_legacy_model_no_native_tools(self) -> None:
        """Test legacy models don't have native tool support."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        # GPT-4 Turbo is a legacy model without native tools
        caps = registry.get("gpt-4-turbo")

        assert caps.supports_native_web_search is False
        assert caps.supports_native_code_execution is False
        assert caps.native_provider is None
