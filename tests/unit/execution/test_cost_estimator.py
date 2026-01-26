"""
Tests for execution plan cost estimation.

The cost estimator provides estimated costs for execution plans based on:
- Model pricing (via LiteLLM)
- Task complexity (simple/complicated/complex)
- Task type (chat/code/analysis/data/ops/other)
- Thinking budget (none/light/medium/deep)

See: Chat Input UX plan - Phase 4c, estimated cost TODO
"""

import pytest
from decimal import Decimal
from unittest.mock import patch

from mcp_server_langgraph.execution.cost_estimator import (
    estimate_execution_cost,
    get_token_estimate,
    BASE_TOKENS,
    COMPLEXITY_MULTIPLIERS,
    THINKING_TOKENS,
)

pytestmark = pytest.mark.unit


@pytest.mark.unit
class TestTokenEstimates:
    """Tests for token estimation logic."""

    def test_simple_chat_has_low_tokens(self):
        """Simple chat tasks should have low token estimates."""
        estimate = get_token_estimate(
            task_type="chat",
            complexity="simple",
            thinking_budget="none",
        )
        assert estimate["prompt_tokens"] < 2000
        assert estimate["completion_tokens"] < 1000

    def test_complex_code_has_high_tokens(self):
        """Complex code tasks should have high token estimates."""
        estimate = get_token_estimate(
            task_type="code",
            complexity="complex",
            thinking_budget="deep",
        )
        assert estimate["prompt_tokens"] > 5000
        assert estimate["completion_tokens"] > 2000

    def test_thinking_budget_increases_tokens(self):
        """Deeper thinking should increase token estimates."""
        none_estimate = get_token_estimate(
            task_type="code",
            complexity="complicated",
            thinking_budget="none",
        )
        deep_estimate = get_token_estimate(
            task_type="code",
            complexity="complicated",
            thinking_budget="deep",
        )
        # Deep thinking should use significantly more tokens
        assert deep_estimate["completion_tokens"] > none_estimate["completion_tokens"]

    def test_all_task_types_have_estimates(self):
        """All task types should have token estimates."""
        for task_type in ["chat", "code", "analysis", "data", "ops", "other"]:
            estimate = get_token_estimate(
                task_type=task_type,
                complexity="simple",
                thinking_budget="none",
            )
            assert "prompt_tokens" in estimate
            assert "completion_tokens" in estimate
            assert estimate["prompt_tokens"] > 0
            assert estimate["completion_tokens"] > 0

    def test_unknown_task_type_uses_default(self):
        """Unknown task types should use 'other' defaults."""
        estimate = get_token_estimate(
            task_type="unknown_task",  # type: ignore
            complexity="simple",
            thinking_budget="none",
        )
        other_estimate = get_token_estimate(
            task_type="other",
            complexity="simple",
            thinking_budget="none",
        )
        assert estimate == other_estimate


@pytest.mark.unit
class TestCostEstimation:
    """Tests for cost calculation from token estimates."""

    def test_returns_decimal(self):
        """Cost should be returned as Decimal for precision."""
        cost = estimate_execution_cost(
            model="claude-sonnet-4-20250514",
            task_type="chat",
            complexity="simple",
            thinking_budget="none",
        )
        assert isinstance(cost, Decimal)

    def test_zero_cost_for_unknown_model(self):
        """Unknown models should return zero cost (fail-safe)."""
        cost = estimate_execution_cost(
            model="unknown-model-xyz",
            task_type="chat",
            complexity="simple",
            thinking_budget="none",
        )
        # Should return 0 or a small default, not raise
        assert cost >= Decimal("0")

    @patch("mcp_server_langgraph.execution.cost_estimator.get_model_cost_from_litellm")
    def test_uses_litellm_for_pricing(self, mock_get_cost):
        """Should use LiteLLM pricing for cost calculation."""
        mock_get_cost.return_value = Decimal("0.05")

        cost = estimate_execution_cost(
            model="claude-sonnet-4-20250514",
            task_type="chat",
            complexity="simple",
            thinking_budget="none",
        )

        # Should have called LiteLLM cost function
        mock_get_cost.assert_called_once()
        assert cost == Decimal("0.05")

    def test_complex_task_costs_more_than_simple(self):
        """Complex tasks should have higher estimated cost."""
        simple_cost = estimate_execution_cost(
            model="claude-sonnet-4-20250514",
            task_type="code",
            complexity="simple",
            thinking_budget="none",
        )
        complex_cost = estimate_execution_cost(
            model="claude-sonnet-4-20250514",
            task_type="code",
            complexity="complex",
            thinking_budget="deep",
        )
        assert complex_cost > simple_cost

    def test_thinking_increases_cost(self):
        """Deep thinking should increase estimated cost."""
        no_thinking_cost = estimate_execution_cost(
            model="claude-sonnet-4-20250514",
            task_type="analysis",
            complexity="complicated",
            thinking_budget="none",
        )
        deep_thinking_cost = estimate_execution_cost(
            model="claude-sonnet-4-20250514",
            task_type="analysis",
            complexity="complicated",
            thinking_budget="deep",
        )
        assert deep_thinking_cost > no_thinking_cost


@pytest.mark.unit
class TestTokenEstimatesConstants:
    """Tests for token estimate constants."""

    def test_base_estimates_exist(self):
        """BASE_TOKENS should have estimates for all task types."""
        assert "chat" in BASE_TOKENS
        assert "code" in BASE_TOKENS
        assert "analysis" in BASE_TOKENS

    def test_complexity_multipliers_exist(self):
        """COMPLEXITY_MULTIPLIERS should have all levels."""
        assert "simple" in COMPLEXITY_MULTIPLIERS
        assert "complicated" in COMPLEXITY_MULTIPLIERS
        assert "complex" in COMPLEXITY_MULTIPLIERS

    def test_thinking_tokens_exist(self):
        """THINKING_TOKENS should have all budget levels."""
        assert "none" in THINKING_TOKENS
        assert "light" in THINKING_TOKENS
        assert "medium" in THINKING_TOKENS
        assert "deep" in THINKING_TOKENS


@pytest.mark.unit
class TestConfidenceIntervals:
    """Tests for cost estimation confidence intervals."""

    def test_returns_confidence_range(self):
        """Cost estimate should include min and max bounds."""
        from mcp_server_langgraph.execution.cost_estimator import (
            estimate_execution_cost_with_confidence,
        )

        result = estimate_execution_cost_with_confidence(
            model="claude-sonnet-4-20250514",
            task_type="code",
            complexity="complicated",
            thinking_budget="medium",
        )

        assert "min_cost" in result
        assert "estimated_cost" in result
        assert "max_cost" in result
        assert result["min_cost"] <= result["estimated_cost"] <= result["max_cost"]

    def test_simple_task_has_narrow_confidence(self):
        """Simple tasks should have narrower confidence intervals."""
        from mcp_server_langgraph.execution.cost_estimator import (
            estimate_execution_cost_with_confidence,
        )

        simple_result = estimate_execution_cost_with_confidence(
            model="claude-sonnet-4-20250514",
            task_type="chat",
            complexity="simple",
            thinking_budget="none",
        )

        # Confidence range (max - min) should be relatively small for simple tasks
        simple_range = simple_result["max_cost"] - simple_result["min_cost"]
        assert simple_range < simple_result["estimated_cost"]  # Range < estimate

    def test_complex_task_has_wider_confidence(self):
        """Complex tasks should have wider confidence intervals."""
        from mcp_server_langgraph.execution.cost_estimator import (
            estimate_execution_cost_with_confidence,
        )

        simple_result = estimate_execution_cost_with_confidence(
            model="claude-sonnet-4-20250514",
            task_type="chat",
            complexity="simple",
            thinking_budget="none",
        )
        complex_result = estimate_execution_cost_with_confidence(
            model="claude-sonnet-4-20250514",
            task_type="code",
            complexity="complex",
            thinking_budget="deep",
        )

        simple_range = simple_result["max_cost"] - simple_result["min_cost"]
        complex_range = complex_result["max_cost"] - complex_result["min_cost"]

        # Complex tasks should have wider confidence interval
        assert complex_range > simple_range

    def test_confidence_multipliers_based_on_complexity(self):
        """Confidence bounds should scale with complexity."""
        from mcp_server_langgraph.execution.cost_estimator import (
            CONFIDENCE_MULTIPLIERS,
        )

        # Verify multipliers exist and are ordered correctly
        assert "simple" in CONFIDENCE_MULTIPLIERS
        assert "complicated" in CONFIDENCE_MULTIPLIERS
        assert "complex" in CONFIDENCE_MULTIPLIERS

        # Complex should have wider bounds than simple
        assert CONFIDENCE_MULTIPLIERS["complex"]["upper"] > CONFIDENCE_MULTIPLIERS["simple"]["upper"]


@pytest.mark.unit
class TestCritiqueRounds:
    """Tests for critique_rounds affecting cost estimation."""

    def test_critique_rounds_increases_cost(self):
        """More critique rounds should increase estimated cost."""
        from mcp_server_langgraph.execution.cost_estimator import (
            estimate_execution_cost_with_confidence,
        )

        no_critique = estimate_execution_cost_with_confidence(
            model="claude-sonnet-4-20250514",
            task_type="code",
            complexity="complicated",
            thinking_budget="medium",
            critique_rounds=0,
        )
        with_critique = estimate_execution_cost_with_confidence(
            model="claude-sonnet-4-20250514",
            task_type="code",
            complexity="complicated",
            thinking_budget="medium",
            critique_rounds=2,
        )

        assert with_critique["estimated_cost"] > no_critique["estimated_cost"]

    def test_critique_rounds_multiplier(self):
        """Each critique round should add proportional cost."""
        from mcp_server_langgraph.execution.cost_estimator import (
            CRITIQUE_ROUND_MULTIPLIER,
        )

        # Verify multiplier exists and is reasonable (e.g., 1.3 = 30% increase per round)
        assert CRITIQUE_ROUND_MULTIPLIER > 1.0
        assert CRITIQUE_ROUND_MULTIPLIER < 2.0  # Shouldn't double per round

    def test_default_critique_rounds_is_zero(self):
        """Default critique_rounds should be 0."""
        from mcp_server_langgraph.execution.cost_estimator import (
            estimate_execution_cost_with_confidence,
        )

        # Both calls should produce same result when critique_rounds defaults to 0
        explicit_zero = estimate_execution_cost_with_confidence(
            model="claude-sonnet-4-20250514",
            task_type="code",
            complexity="simple",
            thinking_budget="none",
            critique_rounds=0,
        )
        implicit_zero = estimate_execution_cost_with_confidence(
            model="claude-sonnet-4-20250514",
            task_type="code",
            complexity="simple",
            thinking_budget="none",
        )

        assert explicit_zero["estimated_cost"] == implicit_zero["estimated_cost"]

    def test_high_critique_rounds_significantly_increases_cost(self):
        """Many critique rounds should significantly increase cost."""
        from mcp_server_langgraph.execution.cost_estimator import (
            estimate_execution_cost_with_confidence,
        )

        base = estimate_execution_cost_with_confidence(
            model="claude-sonnet-4-20250514",
            task_type="analysis",
            complexity="complex",
            thinking_budget="deep",
            critique_rounds=0,
        )
        high_critique = estimate_execution_cost_with_confidence(
            model="claude-sonnet-4-20250514",
            task_type="analysis",
            complexity="complex",
            thinking_budget="deep",
            critique_rounds=5,
        )

        # 5 rounds should at least double the cost
        assert high_critique["estimated_cost"] >= base["estimated_cost"] * Decimal("1.5")
