"""
LLM Pricing Table and Cost Calculation

Provides pricing data for all supported LLM providers and accurate cost calculation
based on token usage.

Pricing is updated monthly based on provider pricing pages:
- Anthropic: https://www.anthropic.com/pricing
- OpenAI: https://openai.com/pricing
- Google: https://ai.google.dev/pricing

Example:
    >>> from mcp_server_langgraph.monitoring.pricing import calculate_cost
    >>> cost = calculate_cost(
    ...     model="claude-sonnet-4-5-20250929",
    ...     provider="anthropic",
    ...     prompt_tokens=1000,
    ...     completion_tokens=500
    ... )
    >>> print(f"${cost}")
    $0.0105
"""

from decimal import Decimal

# ==============================================================================
# Pricing Table - Updated: 2025-12-01
# ==============================================================================

PRICING_TABLE: dict[str, dict[str, dict[str, Decimal]]] = {
    "anthropic": {
        # Latest Claude 4.5 models (2025)
        "claude-sonnet-4-5-20250929": {
            "input": Decimal("0.003"),  # $3.00 per 1M tokens
            "output": Decimal("0.015"),  # $15.00 per 1M tokens
        },
        "claude-haiku-4-5-20251001": {
            "input": Decimal("0.001"),  # $1.00 per 1M tokens
            "output": Decimal("0.005"),  # $5.00 per 1M tokens
        },
        "claude-opus-4-5-20251101": {
            "input": Decimal("0.005"),  # $5.00 per 1M tokens (66% reduction from Opus 4.1)
            "output": Decimal("0.025"),  # $25.00 per 1M tokens
        },
        "claude-opus-4-1-20250805": {
            "input": Decimal("0.015"),  # $15.00 per 1M tokens
            "output": Decimal("0.075"),  # $75.00 per 1M tokens
        },
    },
    "vertex_ai": {
        # Anthropic Claude models via Vertex AI (same pricing as direct API)
        "claude-sonnet-4-5@20250929": {
            "input": Decimal("0.003"),  # $3.00 per 1M tokens
            "output": Decimal("0.015"),  # $15.00 per 1M tokens
        },
        "claude-haiku-4-5@20251001": {
            "input": Decimal("0.001"),  # $1.00 per 1M tokens
            "output": Decimal("0.005"),  # $5.00 per 1M tokens
        },
        "claude-opus-4-5@20251101": {
            "input": Decimal("0.005"),  # $5.00 per 1M tokens
            "output": Decimal("0.025"),  # $25.00 per 1M tokens
        },
        "claude-opus-4-1@20250805": {
            "input": Decimal("0.015"),  # $15.00 per 1M tokens
            "output": Decimal("0.075"),  # $75.00 per 1M tokens
        },
        # Google Gemini models via Vertex AI
        "gemini-3-pro-preview": {
            "input": Decimal("0.002"),  # $2.00 per 1M tokens
            "output": Decimal("0.012"),  # $12.00 per 1M tokens
        },
        "gemini-2.5-flash": {
            "input": Decimal("0.0003"),  # $0.30 per 1M tokens
            "output": Decimal("0.0025"),  # $2.50 per 1M tokens
        },
        "gemini-2.5-flash-lite": {
            "input": Decimal("0.0001"),  # $0.10 per 1M tokens
            "output": Decimal("0.0004"),  # $0.40 per 1M tokens
        },
        "gemini-2.5-pro": {
            "input": Decimal("0.00125"),  # $1.25 per 1M tokens (≤200K)
            "output": Decimal("0.010"),  # $10.00 per 1M tokens (≤200K)
        },
    },
    "openai": {
        # Latest GPT-5.x models (Nov 2025)
        "gpt-5.1": {
            "input": Decimal("0.00125"),  # $1.25 per 1M tokens
            "output": Decimal("0.01"),  # $10.00 per 1M tokens
        },
        "gpt-5.1-thinking": {
            "input": Decimal("0.0025"),  # $2.50 per 1M tokens
            "output": Decimal("0.015"),  # $15.00 per 1M tokens
        },
        "gpt-5-mini": {
            "input": Decimal("0.00025"),  # $0.25 per 1M tokens
            "output": Decimal("0.002"),  # $2.00 per 1M tokens
        },
        "gpt-5-nano": {
            "input": Decimal("0.00005"),  # $0.05 per 1M tokens
            "output": Decimal("0.0004"),  # $0.40 per 1M tokens
        },
    },
    "google": {
        # Latest Gemini 3.0 (Nov 2025)
        "gemini-3-pro-preview": {
            "input": Decimal("0.002"),  # $2.00 per 1M tokens
            "output": Decimal("0.012"),  # $12.00 per 1M tokens
        },
        # Gemini 2.5 (current stable)
        "gemini-2.5-pro": {
            "input": Decimal("0.00125"),  # $1.25 per 1M tokens (≤200K)
            "output": Decimal("0.010"),  # $10.00 per 1M tokens (≤200K)
        },
        "gemini-2.5-flash": {
            "input": Decimal("0.0003"),  # $0.30 per 1M tokens
            "output": Decimal("0.0025"),  # $2.50 per 1M tokens
        },
        "gemini-2.5-flash-lite": {
            "input": Decimal("0.0001"),  # $0.10 per 1M tokens
            "output": Decimal("0.0004"),  # $0.40 per 1M tokens
        },
    },
}


def calculate_cost(
    model: str,
    provider: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> Decimal:
    """
    Calculate cost for an LLM API call based on token usage.

    Args:
        model: Model name (e.g., "claude-sonnet-4-5-20250929")
        provider: Provider name ("anthropic", "openai", "google")
        prompt_tokens: Number of input/prompt tokens
        completion_tokens: Number of output/completion tokens

    Returns:
        Total cost in USD as Decimal

    Raises:
        KeyError: If provider or model not found in pricing table

    Example:
        >>> cost = calculate_cost(
        ...     model="claude-sonnet-4-5-20250929",
        ...     provider="anthropic",
        ...     prompt_tokens=1000,
        ...     completion_tokens=500
        ... )
        >>> cost
        Decimal('0.0105')
    """
    # Get pricing for model
    pricing = PRICING_TABLE[provider][model]

    # Calculate input cost (per 1K tokens)
    input_cost = (Decimal(prompt_tokens) / 1000) * pricing["input"]

    # Calculate output cost (per 1K tokens)
    output_cost = (Decimal(completion_tokens) / 1000) * pricing["output"]

    # Return total cost
    return input_cost + output_cost


def get_all_models() -> dict[str, list[str]]:
    """
    Get all available models grouped by provider.

    Returns:
        Dict mapping provider names to lists of model names

    Example:
        >>> models = get_all_models()
        >>> models["anthropic"]
        ['claude-sonnet-4-5-20250929', 'claude-haiku-4-5-20251001', ...]
    """
    return {provider: list(models.keys()) for provider, models in PRICING_TABLE.items()}


def get_model_pricing(provider: str, model: str) -> dict[str, Decimal]:
    """
    Get pricing information for a specific model.

    Args:
        provider: Provider name
        model: Model name

    Returns:
        Dict with "input" and "output" pricing per 1K tokens

    Raises:
        KeyError: If provider or model not found

    Example:
        >>> pricing = get_model_pricing("anthropic", "claude-sonnet-4-5-20250929")
        >>> pricing["input"]
        Decimal('0.003')
    """
    return PRICING_TABLE[provider][model].copy()


def estimate_cost_from_text(
    model: str,
    provider: str,
    input_text: str,
    estimated_output_tokens: int = 500,
    chars_per_token: int = 4,
) -> Decimal:
    """
    Estimate cost from input text before making API call.

    Uses rough approximation of ~4 characters per token.

    Args:
        model: Model name
        provider: Provider name
        input_text: Input text to send to model
        estimated_output_tokens: Expected output length (default: 500)
        chars_per_token: Character to token ratio (default: 4)

    Returns:
        Estimated cost in USD

    Example:
        >>> text = "Explain quantum computing in simple terms."
        >>> cost = estimate_cost_from_text(
        ...     model="claude-sonnet-4-5-20250929",
        ...     provider="anthropic",
        ...     input_text=text,
        ...     estimated_output_tokens=300
        ... )
    """
    # Estimate input tokens
    estimated_input_tokens = len(input_text) // chars_per_token

    # Calculate cost
    return calculate_cost(
        model=model,
        provider=provider,
        prompt_tokens=estimated_input_tokens,
        completion_tokens=estimated_output_tokens,
    )
