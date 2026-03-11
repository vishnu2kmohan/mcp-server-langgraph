"""
Integration tests for LiteLLM capability sync.

Tests the sync_capabilities() method with real LiteLLM data (not mocked).
Validates that ModelRegistry can be updated from LiteLLM's model_cost
dictionary which contains supports_reasoning field.

Sprint 1 - Enhanced Model Selector: LiteLLM Dynamic Model Sync
"""

from __future__ import annotations

import gc

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.xdist_group(name="litellm_capability_sync"),
]


@pytest.mark.xdist_group("test_lite_l_l_m_model_cost_access")
@pytest.mark.integration
class TestLiteLLMModelCostAccess:
    """Integration tests for accessing LiteLLM's model_cost data."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_litellm_model_cost_is_accessible(self) -> None:
        """Test that litellm.model_cost attribute exists and is a dict."""
        import litellm

        model_cost = getattr(litellm, "model_cost", None)

        assert model_cost is not None, "litellm.model_cost should be accessible"
        assert isinstance(model_cost, dict), "litellm.model_cost should be a dict"

    def test_litellm_model_cost_has_entries(self) -> None:
        """Test that model_cost has model entries."""
        import litellm

        model_cost = litellm.model_cost

        assert len(model_cost) > 0, "litellm.model_cost should have entries"
        # Should have at least 100 models
        assert len(model_cost) > 100, f"Expected 100+ models, got {len(model_cost)}"

    def test_litellm_model_cost_has_pricing_fields(self) -> None:
        """Test that model entries have pricing fields."""
        import litellm

        model_cost = litellm.model_cost

        # Find a known model
        sample_model = None
        for key in ["gpt-4", "gpt-4o", "claude-3-opus"]:
            if key in model_cost:
                sample_model = model_cost[key]
                break

        assert sample_model is not None, "Should find a known model in model_cost"
        assert "input_cost_per_token" in sample_model or "input_cost_per_character" in sample_model

    def test_litellm_model_cost_has_supports_reasoning_field(self) -> None:
        """Test that some models have supports_reasoning field.

        Not all models have this field - only reasoning models like o3, o1.
        """
        import litellm

        model_cost = litellm.model_cost

        # Look for models with supports_reasoning field
        models_with_reasoning = [
            key for key, value in model_cost.items() if isinstance(value, dict) and "supports_reasoning" in value
        ]

        assert len(models_with_reasoning) > 0, "At least some models should have supports_reasoning field"

    def test_litellm_known_reasoning_models_have_field_true(self) -> None:
        """Test that known reasoning models have supports_reasoning=True."""
        import litellm

        model_cost = litellm.model_cost

        # OpenAI o-series models are known reasoning models
        reasoning_model_patterns = ["o1", "o3", "o4"]

        found_reasoning_model = False
        for key, value in model_cost.items():
            if isinstance(value, dict):
                for pattern in reasoning_model_patterns:
                    if pattern in key.lower():
                        if value.get("supports_reasoning") is True:
                            found_reasoning_model = True
                            break

        assert found_reasoning_model, "Should find at least one o-series model with supports_reasoning=True"


@pytest.mark.xdist_group("test_lite_l_l_m_supports_reasoning_function")
@pytest.mark.integration
class TestLiteLLMSupportsReasoningFunction:
    """Integration tests for litellm.supports_reasoning() function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_supports_reasoning_function_exists(self) -> None:
        """Test that litellm.supports_reasoning function is available."""
        import litellm

        assert hasattr(litellm, "supports_reasoning")
        assert callable(litellm.supports_reasoning)

    def test_supports_reasoning_returns_true_for_o3(self) -> None:
        """Test o3 model returns True for supports_reasoning."""
        import litellm

        result = litellm.supports_reasoning("o3")

        assert result is True, "o3 should support reasoning"

    def test_supports_reasoning_returns_true_for_o3_mini(self) -> None:
        """Test o3-mini model returns True for supports_reasoning."""
        import litellm

        result = litellm.supports_reasoning("o3-mini")

        assert result is True, "o3-mini should support reasoning"

    def test_supports_reasoning_returns_false_for_gpt4(self) -> None:
        """Test gpt-4 model returns False for supports_reasoning."""
        import litellm

        result = litellm.supports_reasoning("gpt-4")

        assert result is False, "gpt-4 should not support reasoning"

    def test_supports_reasoning_returns_bool(self) -> None:
        """Test supports_reasoning always returns a boolean."""
        import litellm

        test_models = ["o3", "gpt-4", "claude-3-opus", "unknown-model-xyz"]

        for model in test_models:
            result = litellm.supports_reasoning(model)
            assert isinstance(result, bool), f"supports_reasoning({model}) should return bool"

    def test_supports_reasoning_gemini_2_5_flash(self) -> None:
        """Test gemini-2.5-flash returns True for supports_reasoning.

        Per Google docs, Gemini 2.5 Flash is a 'hybrid reasoning model'
        that supports thinking_budget parameter.
        """
        import litellm

        result = litellm.supports_reasoning("gemini-2.5-flash")

        assert result is True, "gemini-2.5-flash should support reasoning per Google docs"


@pytest.mark.xdist_group("test_lite_l_l_m_model_sync_integration")
@pytest.mark.integration
class TestLiteLLMModelSyncIntegration:
    """Integration tests for LiteLLMModelSync with real data."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_litellm_models_returns_real_data(self) -> None:
        """Test get_litellm_models returns actual LiteLLM data."""
        from mcp_server_langgraph.agents.litellm_model_sync import LiteLLMModelSync

        sync = LiteLLMModelSync()
        models = sync.get_litellm_models()

        assert isinstance(models, dict)
        assert len(models) > 100, f"Expected 100+ models, got {len(models)}"

    def test_sync_pricing_with_real_data(self) -> None:
        """Test sync_pricing works with real LiteLLM data."""
        from mcp_server_langgraph.agents.litellm_model_sync import LiteLLMModelSync

        sync = LiteLLMModelSync()
        count = sync.sync_pricing()

        # Should return a count (may be 0 if prices already match)
        assert isinstance(count, int)
        assert count >= 0

    def test_sync_capabilities_with_real_data(self) -> None:
        """Test sync_capabilities works with real LiteLLM data."""
        from mcp_server_langgraph.agents.litellm_model_sync import LiteLLMModelSync

        sync = LiteLLMModelSync()
        count = sync.sync_capabilities()

        # Should return a count (may be 0 if capabilities already match)
        assert isinstance(count, int)
        assert count >= 0

    def test_update_registry_with_real_data(self) -> None:
        """Test update_registry combines pricing and capabilities sync."""
        from mcp_server_langgraph.agents.litellm_model_sync import LiteLLMModelSync

        sync = LiteLLMModelSync()
        count = sync.update_registry()

        # Should return combined count
        assert isinstance(count, int)
        assert count >= 0

    def test_normalize_model_id_with_real_litellm_keys(self) -> None:
        """Test model ID normalization works with actual LiteLLM keys."""
        from mcp_server_langgraph.agents.litellm_model_sync import LiteLLMModelSync
        import litellm

        sync = LiteLLMModelSync()
        model_cost = litellm.model_cost

        # Check that normalization handles prefixed keys
        prefixed_keys = [key for key in model_cost.keys() if "/" in key and isinstance(key, str)]

        assert len(prefixed_keys) > 0, "LiteLLM should have prefixed model keys"

        # Normalize some prefixed keys
        for key in prefixed_keys[:5]:
            normalized = sync._normalize_model_id(key)
            # Normalized should not contain the prefix
            if key.startswith(("openai/", "anthropic/", "google/", "azure/")):
                assert not normalized.startswith(("openai/", "anthropic/", "google/", "azure/"))


@pytest.mark.xdist_group("test_lite_l_l_m_capability_accuracy")
@pytest.mark.integration
class TestLiteLLMCapabilityAccuracy:
    """Integration tests to document LiteLLM capability accuracy.

    These tests document known discrepancies between LiteLLM's
    supports_reasoning data and actual provider capabilities.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_document_gemini_3_flash_discrepancy(self) -> None:
        """Document: LiteLLM incorrectly reports gemini-3-flash as non-reasoning.

        Per Google's Gemini 3 Developer Guide, gemini-3-flash supports
        thinking_level parameter with values: minimal, low, medium, high.

        This test documents the known discrepancy. Our ModelRegistry
        has the correct static value (supports_extended_thinking=True).

        See: https://ai.google.dev/gemini-api
        """
        import litellm

        # Document the current (incorrect) LiteLLM behavior
        result = litellm.supports_reasoning("gemini-3-flash")

        # This assertion documents the discrepancy
        # When LiteLLM fixes this, this test will fail and can be updated
        if result is False:
            # Known discrepancy - LiteLLM is wrong
            pytest.skip(
                "LiteLLM incorrectly returns False for gemini-3-flash. "
                "Our ModelRegistry has correct static value. "
                "Consider filing issue at https://github.com/BerriAI/litellm"
            )
        else:
            # LiteLLM has been fixed
            assert result is True

    def test_registry_has_correct_gemini_3_flash_capability(self) -> None:
        """Verify our ModelRegistry has correct gemini-3-flash capability."""
        from mcp_server_langgraph.agents.model_registry import get_default_registry

        registry = get_default_registry()
        caps = registry.get("gemini-3-flash")

        # Our registry should have the correct value
        assert caps.supports_extended_thinking is True, (
            "ModelRegistry should have gemini-3-flash with supports_extended_thinking=True per Google docs"
        )

    def test_registry_overrides_incorrect_litellm_data(self) -> None:
        """Test that registry maintains correct values even if LiteLLM is wrong.

        The registry's static values are the source of truth.
        LiteLLM sync is supplementary and doesn't overwrite with incorrect data
        because our registry already has the correct values set.
        """
        from mcp_server_langgraph.agents.model_registry import get_default_registry
        from mcp_server_langgraph.agents.litellm_model_sync import LiteLLMModelSync

        registry = get_default_registry()

        # Verify pre-sync value is correct
        pre_sync_caps = registry.get("gemini-3-flash")
        assert pre_sync_caps.supports_extended_thinking is True

        # Run capability sync
        sync = LiteLLMModelSync()
        sync.sync_capabilities()

        # Get post-sync value
        post_sync_caps = registry.get("gemini-3-flash")
        post_sync_thinking = post_sync_caps.supports_extended_thinking

        # Registry should maintain correct value
        assert post_sync_thinking is True, "Registry should maintain correct gemini-3-flash capability even after sync"


@pytest.mark.xdist_group("test_alternative_model_id_lookup")
@pytest.mark.integration
class TestAlternativeModelIdLookup:
    """Integration tests for alternative model ID lookup with real data."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_alternative_ids_for_gemini_models(self) -> None:
        """Test alternative ID generation for Gemini models."""
        from mcp_server_langgraph.agents.litellm_model_sync import LiteLLMModelSync

        sync = LiteLLMModelSync()

        # Test gemini-3-flash alternatives
        alts = sync._get_alternative_model_ids("gemini-3-flash")

        assert isinstance(alts, list)
        assert "gemini-3-flash-preview" in alts or "google/gemini-3-flash" in alts

    def test_alternative_ids_for_openai_models(self) -> None:
        """Test alternative ID generation for OpenAI models."""
        from mcp_server_langgraph.agents.litellm_model_sync import LiteLLMModelSync

        sync = LiteLLMModelSync()

        # Test o3-mini alternatives
        alts = sync._get_alternative_model_ids("o3-mini")

        assert isinstance(alts, list)
        assert "openai/o3-mini" in alts or "azure/o3-mini" in alts

    def test_alternative_ids_help_find_registry_match(self) -> None:
        """Test that alternative IDs can help match LiteLLM to registry entries."""
        from mcp_server_langgraph.agents.litellm_model_sync import LiteLLMModelSync
        from mcp_server_langgraph.agents.model_registry import get_default_registry
        import litellm

        sync = LiteLLMModelSync()
        registry = get_default_registry()
        model_cost = litellm.model_cost

        # Use specific known models that exist in both LiteLLM and registry
        # (first N keys are often image generation models, not LLMs)
        known_models = [
            "gpt-4o",
            "gpt-4-turbo",
            "gemini-pro",
            "o1-preview",
            "o3",
        ]

        # Count how many known models can be matched
        matched_count = 0
        for litellm_key in known_models:
            if litellm_key not in model_cost:
                continue

            normalized = sync._normalize_model_id(litellm_key)

            # Try normalized ID
            if normalized in registry._models:
                matched_count += 1
                continue

            # Try alternatives
            for alt in sync._get_alternative_model_ids(normalized):
                if alt in registry._models:
                    matched_count += 1
                    break

        # Should match at least some known models
        assert matched_count >= 3, f"Should match at least 3 known models, got {matched_count}"
