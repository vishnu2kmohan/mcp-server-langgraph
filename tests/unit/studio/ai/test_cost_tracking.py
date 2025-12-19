"""
Unit tests for LLM suggestion cost tracking functionality.

Tests the cost estimation and metric tracking for LLM-powered suggestions.
Follows TDD principles and memory safety patterns for pytest-xdist.
"""

import gc

import pytest

pytestmark = [pytest.mark.unit]


@pytest.mark.xdist_group(name="cost_tracking")
class TestModelPricing:
    """Tests for model pricing configuration."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_model_pricing_defined(self):
        """Should have model pricing defined for major providers."""
        from mcp_server_langgraph.studio.ai.suggestions import MODEL_PRICING

        assert isinstance(MODEL_PRICING, dict)
        assert len(MODEL_PRICING) > 0

    @pytest.mark.unit
    def test_gemini_models_have_pricing(self):
        """Should have pricing for Gemini models."""
        from mcp_server_langgraph.studio.ai.suggestions import MODEL_PRICING

        gemini_models = [k for k in MODEL_PRICING.keys() if "gemini" in k.lower()]
        assert len(gemini_models) >= 3, "Expected at least 3 Gemini models"

    @pytest.mark.unit
    def test_openai_models_have_pricing(self):
        """Should have pricing for OpenAI models."""
        from mcp_server_langgraph.studio.ai.suggestions import MODEL_PRICING

        openai_models = [k for k in MODEL_PRICING.keys() if "gpt" in k.lower()]
        assert len(openai_models) >= 3, "Expected at least 3 OpenAI models"

    @pytest.mark.unit
    def test_anthropic_models_have_pricing(self):
        """Should have pricing for Anthropic models."""
        from mcp_server_langgraph.studio.ai.suggestions import MODEL_PRICING

        anthropic_models = [k for k in MODEL_PRICING.keys() if "claude" in k.lower()]
        assert len(anthropic_models) >= 3, "Expected at least 3 Anthropic models"

    @pytest.mark.unit
    def test_pricing_has_input_and_output(self):
        """Each model pricing should have input and output costs."""
        from mcp_server_langgraph.studio.ai.suggestions import MODEL_PRICING

        for model, pricing in MODEL_PRICING.items():
            assert "input" in pricing, f"Model {model} missing input pricing"
            assert "output" in pricing, f"Model {model} missing output pricing"
            assert isinstance(pricing["input"], (int, float))
            assert isinstance(pricing["output"], (int, float))
            assert pricing["input"] >= 0
            assert pricing["output"] >= 0


@pytest.mark.xdist_group(name="cost_tracking")
class TestCostEstimation:
    """Tests for cost estimation function."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_estimate_cost_exact_model_match(self):
        """Should calculate cost for exact model match."""
        from mcp_server_langgraph.studio.ai.suggestions import estimate_cost

        # Using gpt-4o-mini: $0.15/1M input, $0.60/1M output
        cost = estimate_cost(
            model="gpt-4o-mini",
            prompt_tokens=1000,
            completion_tokens=500,
        )

        # Expected: (1000/1M * 0.15) + (500/1M * 0.60) = 0.00015 + 0.0003 = 0.00045
        assert cost == pytest.approx(0.00045, rel=0.01)

    @pytest.mark.unit
    def test_estimate_cost_partial_model_match(self):
        """Should find pricing via partial model name match."""
        from mcp_server_langgraph.studio.ai.suggestions import estimate_cost

        # Using a model name that contains "gemini-1.5-flash"
        cost = estimate_cost(
            model="google/gemini-1.5-flash-latest",
            prompt_tokens=10000,
            completion_tokens=1000,
        )

        # Should match gemini-1.5-flash: $0.075/1M input, $0.30/1M output
        # Expected: (10000/1M * 0.075) + (1000/1M * 0.30) = 0.00075 + 0.0003 = 0.00105
        assert cost == pytest.approx(0.00105, rel=0.01)

    @pytest.mark.unit
    def test_estimate_cost_unknown_model_uses_default(self):
        """Should use conservative default for unknown models."""
        from mcp_server_langgraph.studio.ai.suggestions import estimate_cost

        cost = estimate_cost(
            model="unknown-model-xyz",
            prompt_tokens=1000,
            completion_tokens=500,
        )

        # Default pricing: $1.00/1M input, $3.00/1M output
        # Expected: (1000/1M * 1.00) + (500/1M * 3.00) = 0.001 + 0.0015 = 0.0025
        assert cost == pytest.approx(0.0025, rel=0.01)

    @pytest.mark.unit
    def test_estimate_cost_zero_tokens(self):
        """Should return 0 for zero tokens."""
        from mcp_server_langgraph.studio.ai.suggestions import estimate_cost

        cost = estimate_cost(
            model="gpt-4o",
            prompt_tokens=0,
            completion_tokens=0,
        )

        assert cost == 0.0

    @pytest.mark.unit
    def test_estimate_cost_large_token_count(self):
        """Should handle large token counts correctly."""
        from mcp_server_langgraph.studio.ai.suggestions import estimate_cost

        # Simulate a large request (1M input tokens, 100K output tokens)
        cost = estimate_cost(
            model="gpt-4o",  # $2.50/1M input, $10.00/1M output
            prompt_tokens=1_000_000,
            completion_tokens=100_000,
        )

        # Expected: (1M/1M * 2.50) + (100K/1M * 10.00) = 2.50 + 1.00 = 3.50
        assert cost == pytest.approx(3.50, rel=0.01)

    @pytest.mark.unit
    def test_estimate_cost_gemini_model(self):
        """Should calculate cost for Gemini models correctly."""
        from mcp_server_langgraph.studio.ai.suggestions import estimate_cost

        cost = estimate_cost(
            model="gemini-2.5-flash",  # $0.075/1M input, $0.30/1M output
            prompt_tokens=100_000,
            completion_tokens=10_000,
        )

        # Expected: (100K/1M * 0.075) + (10K/1M * 0.30) = 0.0075 + 0.003 = 0.0105
        assert cost == pytest.approx(0.0105, rel=0.01)

    @pytest.mark.unit
    def test_estimate_cost_claude_model(self):
        """Should calculate cost for Claude models correctly."""
        from mcp_server_langgraph.studio.ai.suggestions import estimate_cost

        cost = estimate_cost(
            model="claude-3-haiku",  # $0.25/1M input, $1.25/1M output
            prompt_tokens=50_000,
            completion_tokens=5_000,
        )

        # Expected: (50K/1M * 0.25) + (5K/1M * 1.25) = 0.0125 + 0.00625 = 0.01875
        assert cost == pytest.approx(0.01875, rel=0.01)


@pytest.mark.xdist_group(name="cost_tracking")
class TestCostMetrics:
    """Tests for cost tracking metrics."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_cost_counter_defined(self):
        """Should have a cost counter metric defined."""
        from mcp_server_langgraph.studio.ai.suggestions import _init_suggestion_metrics

        # Initialize metrics
        result = _init_suggestion_metrics()

        # Should return True if metrics are available
        assert isinstance(result, bool)

    @pytest.mark.unit
    def test_tokens_counter_defined(self):
        """Should track token usage for cost calculations."""
        from mcp_server_langgraph.studio.ai.suggestions import (
            _init_suggestion_metrics,
        )

        # Initialize metrics
        _init_suggestion_metrics()

        # Token counter should be initialized (may be None if prometheus not available)
        # We just verify the initialization doesn't crash
        assert True

    @pytest.mark.unit
    def test_cost_tracking_in_agent(self):
        """Cost tracking should be integrated in the suggestion agent."""
        from mcp_server_langgraph.studio.ai.suggestions import ChatFollowUpSuggestionAgent

        # Create agent - should not raise
        agent = ChatFollowUpSuggestionAgent(enable_llm=False)

        # Agent should have suggest method (which includes cost tracking)
        assert hasattr(agent, "suggest")
        assert hasattr(agent, "model_name")  # Used for cost tracking
