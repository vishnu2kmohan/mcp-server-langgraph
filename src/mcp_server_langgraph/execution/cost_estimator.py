"""
Execution plan cost estimation.

Provides estimated costs for execution plans based on:
- Model pricing (via LiteLLM)
- Task complexity (simple/complicated/complex)
- Task type (chat/code/analysis/data/ops/other)
- Thinking budget (none/light/medium/deep)

Usage:
    from mcp_server_langgraph.execution.cost_estimator import estimate_execution_cost

    cost = estimate_execution_cost(
        model="claude-sonnet-4-20250514",
        task_type="code",
        complexity="complicated",
        thinking_budget="medium",
    )

See: Chat Input UX plan - Phase 4c
"""

from decimal import Decimal
from typing import Literal, TypedDict

from mcp_server_langgraph.monitoring.litellm_cost_callback import (
    get_model_cost_from_litellm,
)


# Type definitions
TaskType = Literal["chat", "code", "analysis", "data", "ops", "other"]
Complexity = Literal["simple", "complicated", "complex"]
ThinkingBudget = Literal["none", "light", "medium", "deep"]


class TokenEstimate(TypedDict):
    """Token estimate for an execution plan."""

    prompt_tokens: int
    completion_tokens: int


class CostEstimateWithConfidence(TypedDict):
    """Cost estimate with confidence interval."""

    min_cost: Decimal
    estimated_cost: Decimal
    max_cost: Decimal


# Token estimation constants
# These are empirical estimates based on typical task patterns

# Base tokens per task type (prompt, completion)
BASE_TOKENS: dict[str, dict[str, int]] = {
    "chat": {"prompt": 500, "completion": 300},
    "code": {"prompt": 1500, "completion": 800},
    "analysis": {"prompt": 2000, "completion": 1000},
    "data": {"prompt": 1000, "completion": 600},
    "ops": {"prompt": 800, "completion": 400},
    "other": {"prompt": 1000, "completion": 500},
}

# Complexity multipliers
COMPLEXITY_MULTIPLIERS: dict[str, float] = {
    "simple": 1.0,
    "complicated": 2.0,
    "complex": 3.5,
}

# Additional thinking tokens (added to completion)
THINKING_TOKENS: dict[str, int] = {
    "none": 0,
    "light": 500,
    "medium": 2000,
    "deep": 5000,
}

# Confidence interval multipliers based on complexity
# Higher complexity = more uncertainty in estimates
CONFIDENCE_MULTIPLIERS: dict[str, dict[str, float]] = {
    "simple": {"lower": 0.8, "upper": 1.2},  # ±20% for simple tasks
    "complicated": {"lower": 0.7, "upper": 1.4},  # -30% to +40% for complicated
    "complex": {"lower": 0.5, "upper": 2.0},  # -50% to +100% for complex
}

# Cost multiplier per critique round (each round adds ~30% overhead)
CRITIQUE_ROUND_MULTIPLIER: float = 1.3


def get_token_estimate(
    *,
    task_type: TaskType | str,
    complexity: Complexity,
    thinking_budget: ThinkingBudget,
) -> TokenEstimate:
    """
    Estimate tokens for an execution plan.

    Args:
        task_type: Type of task (chat, code, analysis, etc.)
        complexity: Task complexity (simple, complicated, complex)
        thinking_budget: Extended thinking level (none, light, medium, deep)

    Returns:
        TokenEstimate with prompt_tokens and completion_tokens.
    """
    # Get base tokens (default to "other" for unknown task types)
    task_base = BASE_TOKENS.get(task_type, BASE_TOKENS["other"])

    # Get complexity multiplier
    multiplier = COMPLEXITY_MULTIPLIERS.get(complexity, 1.0)

    # Get thinking tokens
    thinking_tokens = THINKING_TOKENS.get(thinking_budget, 0)

    # Calculate estimates
    prompt_tokens = int(task_base["prompt"] * multiplier)
    completion_tokens = int(task_base["completion"] * multiplier) + thinking_tokens

    return TokenEstimate(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
    )


def estimate_execution_cost(
    *,
    model: str,
    task_type: TaskType | str,
    complexity: Complexity,
    thinking_budget: ThinkingBudget,
) -> Decimal:
    """
    Estimate the cost of executing a plan.

    Uses LiteLLM pricing data for the model and estimated token counts
    based on task characteristics.

    Args:
        model: Model ID (e.g., "claude-sonnet-4-20250514")
        task_type: Type of task (chat, code, analysis, etc.)
        complexity: Task complexity (simple, complicated, complex)
        thinking_budget: Extended thinking level (none, light, medium, deep)

    Returns:
        Estimated cost in USD as Decimal. Returns Decimal("0") for unknown models.

    Example:
        >>> cost = estimate_execution_cost(
        ...     model="claude-sonnet-4-20250514",
        ...     task_type="code",
        ...     complexity="complicated",
        ...     thinking_budget="medium",
        ... )
        >>> print(f"${cost}")
        $0.12
    """
    # Get token estimate
    token_estimate = get_token_estimate(
        task_type=task_type,
        complexity=complexity,
        thinking_budget=thinking_budget,
    )

    # Calculate cost using LiteLLM pricing
    cost = get_model_cost_from_litellm(
        model=model,
        prompt_tokens=token_estimate["prompt_tokens"],
        completion_tokens=token_estimate["completion_tokens"],
    )

    return cost


def estimate_execution_cost_with_confidence(
    *,
    model: str,
    task_type: TaskType | str,
    complexity: Complexity,
    thinking_budget: ThinkingBudget,
    critique_rounds: int = 0,
) -> CostEstimateWithConfidence:
    """
    Estimate the cost of executing a plan with confidence intervals.

    Extends estimate_execution_cost with:
    - Confidence intervals based on complexity
    - Critique rounds cost adjustment

    Args:
        model: Model ID (e.g., "claude-sonnet-4-20250514")
        task_type: Type of task (chat, code, analysis, etc.)
        complexity: Task complexity (simple, complicated, complex)
        thinking_budget: Extended thinking level (none, light, medium, deep)
        critique_rounds: Number of critique-revise rounds (default 0)

    Returns:
        CostEstimateWithConfidence with min_cost, estimated_cost, max_cost.

    Example:
        >>> result = estimate_execution_cost_with_confidence(
        ...     model="claude-sonnet-4-20250514",
        ...     task_type="code",
        ...     complexity="complicated",
        ...     thinking_budget="medium",
        ...     critique_rounds=2,
        ... )
        >>> print(f"${result['min_cost']} - ${result['max_cost']}")
        $0.08 - $0.18
    """
    # Get base cost estimate
    base_cost = estimate_execution_cost(
        model=model,
        task_type=task_type,
        complexity=complexity,
        thinking_budget=thinking_budget,
    )

    # Apply critique rounds multiplier
    # Each round multiplies cost by CRITIQUE_ROUND_MULTIPLIER
    if critique_rounds > 0:
        critique_multiplier = Decimal(str(CRITIQUE_ROUND_MULTIPLIER**critique_rounds))
        estimated_cost = base_cost * critique_multiplier
    else:
        estimated_cost = base_cost

    # Get confidence multipliers for the complexity level
    multipliers = CONFIDENCE_MULTIPLIERS.get(complexity, CONFIDENCE_MULTIPLIERS["complicated"])

    # Calculate confidence bounds
    min_cost = estimated_cost * Decimal(str(multipliers["lower"]))
    max_cost = estimated_cost * Decimal(str(multipliers["upper"]))

    return CostEstimateWithConfidence(
        min_cost=min_cost,
        estimated_cost=estimated_cost,
        max_cost=max_cost,
    )
