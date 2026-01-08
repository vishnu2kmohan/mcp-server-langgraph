"""Numeric utilities for safe handling of float values.

This module provides utilities for safely handling float values that may
contain NaN, Inf, or None - common when working with metrics systems like
Prometheus where histogram_quantile() returns NaN when there's no data.

Problem:
    JSON serialization fails with ValueError for NaN/Inf values:
        ValueError: Out of range float values are not JSON compliant

    This breaks FastAPI responses, WebSocket streaming, and any JSON-based APIs.

Solution:
    Use these safe numeric functions at data boundaries:
    - API response models (with Pydantic field_validator)
    - WebSocket message payloads
    - Prometheus metric calculations
    - Any division or aggregation that could produce invalid floats

Usage Patterns:

    1. Direct value sanitization:
        >>> from mcp_server_langgraph.core.numeric import safe_float
        >>> safe_float(prometheus_result)  # NaN -> 0.0

    2. Safe aggregations:
        >>> from mcp_server_langgraph.core.numeric import safe_average
        >>> avg = safe_average(latency_values)  # Filters NaN, handles empty

    3. Safe division (prevents div-by-zero AND NaN inputs):
        >>> from mcp_server_langgraph.core.numeric import safe_divide
        >>> rate = safe_divide(errors, total) * 100

    4. Pydantic field validators (defense-in-depth):
        >>> from pydantic import BaseModel, field_validator
        >>> from mcp_server_langgraph.core.numeric import safe_float
        >>>
        >>> class MetricsResponse(BaseModel):
        ...     latency_ms: float
        ...
        ...     @field_validator("latency_ms", mode="before")
        ...     @classmethod
        ...     def validate_latency(cls, v):
        ...         return safe_float(v)

    5. Rounding with safety:
        >>> from mcp_server_langgraph.core.numeric import safe_round
        >>> score = safe_round(health_score, 1)  # NaN-safe rounding

    6. Percentage calculation with bounds:
        >>> from mcp_server_langgraph.core.numeric import safe_percentage
        >>> pct = safe_percentage(used, total)  # NaN/zero-safe, clamped to 0-100

    7. SafeFloat annotated type for Pydantic models (NEW):
        >>> from pydantic import BaseModel
        >>> from mcp_server_langgraph.core.numeric import SafeFloat
        >>>
        >>> class MetricsResponse(BaseModel):
        ...     latency_ms: SafeFloat  # Auto-sanitizes NaN/Inf to 0.0
        ...     error_rate: SafeFloat
        ...
        >>> # OpenAPI schema includes NaN-safety documentation
        >>> # JSON serialization is always safe (no ValueError)

Architecture Notes:
    - These utilities implement defense-in-depth for numeric data
    - Apply at BOTH source (calculation) AND boundary (serialization)
    - All functions are pure, side-effect free, and thread-safe
    - Performance: O(1) for single values, O(n) for list operations

Files Using This Module:
    - api/health.py - Health check latency and resilience stats
    - api/v1/observability.py - Metrics API responses (with field validators)
    - api/v1/cost.py - Budget status responses (with field validators)
    - api/v1/surveys.py - SUS survey score calculations
    - api/metrics.py - Prometheus endpoint metrics
    - monitoring/prometheus_client.py - Prometheus query results
    - monitoring/sla.py - SLA compliance calculations
    - monitoring/cost_budget.py - Budget percentage calculations
    - websocket/protocols.py - WebSocket message payloads (with field validators)
    - websocket/services/heart_metrics.py - Health score streaming
    - websocket/metrics.py - WebSocket metrics calculations
    - alerts/recommendation_scoring.py - AI recommendation scoring
    - llm/verifier.py - LLM verification scores
    - patterns/swarm.py - Swarm pattern metrics

Frontend TypeScript Equivalent:
    - studio/frontend/src/utils/numeric.ts - Same API for defense-in-depth
    - Functions: safeFloat, safeAverage, safeDivide, safeRound, safeSum, safePercentage

Validation Enforcement:
    - scripts/validation/check_unsafe_float_patterns.py - Pre-commit hook
    - Detects sum()/len() and unsafe round() patterns
    - Runs on pre-push stage for all Python files

See Also:
    - tests/unit/core/test_numeric.py - Comprehensive test coverage (39 tests)
    - tests/unit/api/v1/test_response_model_nan_validators.py - Validator tests (25 tests)
    - ADR-0026 - Cost Tracking Enhancements (budget calculations)
"""

from __future__ import annotations

import math
from typing import Annotated, overload

from pydantic import BeforeValidator, Field


@overload
def safe_float(value: float | None) -> float: ...


@overload
def safe_float(value: float | None, default: float) -> float: ...


def safe_float(value: float | None, default: float = 0.0) -> float:
    """Safely convert a float value, handling None, NaN, and Inf.

    Prometheus histogram_quantile() returns NaN when there's no data in
    histogram buckets. JSON encoding fails for NaN/Inf values, so we
    convert them to a safe default.

    Args:
        value: The float value to check (may be None, NaN, or Inf)
        default: The default value to use if value is invalid (default: 0.0)

    Returns:
        The original value if valid (not None, NaN, or Inf), otherwise the default

    Examples:
        >>> safe_float(1.5)
        1.5
        >>> safe_float(None)
        0.0
        >>> safe_float(float('nan'))
        0.0
        >>> safe_float(float('inf'), default=-1.0)
        -1.0
    """
    if value is None or math.isnan(value) or math.isinf(value):
        return default
    return float(value)


def safe_average(values: list[float], default: float = 0.0) -> float:
    """Compute average, handling empty lists and NaN values.

    Filters out NaN/Inf values before computing the average.
    Returns default if no valid values remain.

    Args:
        values: List of float values (may contain NaN/Inf)
        default: Default value if no valid values exist

    Returns:
        Average of valid values, or default if none exist

    Examples:
        >>> safe_average([1.0, 2.0, 3.0])
        2.0
        >>> safe_average([])
        0.0
        >>> safe_average([float('nan'), 1.0, 2.0])
        1.5
    """
    valid = [v for v in values if v is not None and not math.isnan(v) and not math.isinf(v)]
    if not valid:
        return default
    return sum(valid) / len(valid)


def safe_sum(values: list[float], default: float = 0.0) -> float:
    """Compute sum, filtering out NaN/Inf values.

    Args:
        values: List of float values (may contain NaN/Inf)
        default: Default value if no valid values exist

    Returns:
        Sum of valid values, or default if none exist

    Examples:
        >>> safe_sum([1.0, 2.0, 3.0])
        6.0
        >>> safe_sum([float('nan'), 1.0, 2.0])
        3.0
    """
    valid = [v for v in values if v is not None and not math.isnan(v) and not math.isinf(v)]
    if not valid:
        return default
    return sum(valid)


def safe_round(value: float | None, ndigits: int = 0, default: float = 0.0) -> float:
    """Round a value, handling NaN/Inf.

    Args:
        value: The float value to round
        ndigits: Number of decimal places
        default: Default value if value is invalid

    Returns:
        Rounded value, or default if value is NaN/Inf/None

    Examples:
        >>> safe_round(1.567, 2)
        1.57
        >>> safe_round(float('nan'), 2)
        0.0
    """
    safe_val = safe_float(value, default)
    return round(safe_val, ndigits)


def safe_divide(
    numerator: float | None,
    denominator: float | None,
    default: float = 0.0,
) -> float:
    """Safely divide two values, handling NaN/Inf and division by zero.

    Args:
        numerator: The numerator (may be None, NaN, or Inf)
        denominator: The denominator (may be None, NaN, Inf, or zero)
        default: Default value if division is invalid

    Returns:
        Result of division, or default if invalid

    Examples:
        >>> safe_divide(10.0, 2.0)
        5.0
        >>> safe_divide(1.0, 0.0)
        0.0
        >>> safe_divide(float('nan'), 2.0)
        0.0
    """
    safe_num = safe_float(numerator, default=float("nan"))
    safe_denom = safe_float(denominator, default=float("nan"))

    # Check if inputs were invalid
    if math.isnan(safe_num) or math.isnan(safe_denom):
        return default

    # Check for division by zero
    if safe_denom == 0.0:
        return default

    result = safe_num / safe_denom

    # Check result for overflow to Inf
    if math.isinf(result):
        return default

    return result


def safe_percentage(
    numerator: float | None,
    denominator: float | None,
    *,
    default: float = 0.0,
    clamp: bool = True,
    min_val: float = 0.0,
    max_val: float = 100.0,
    ndigits: int | None = None,
) -> float:
    """Safely calculate a percentage with NaN/Inf/zero protection and optional clamping.

    Computes (numerator / denominator) * 100, with protection against:
    - Division by zero
    - NaN/Inf inputs
    - None values
    - Out-of-bounds results (optionally clamped to 0-100 or custom range)

    This is a convenience wrapper combining safe_divide with percentage calculation
    and optional bounds clamping, commonly needed for metrics and progress indicators.

    Args:
        numerator: The numerator (may be None, NaN, or Inf)
        denominator: The denominator (may be None, NaN, Inf, or zero)
        default: Default value if calculation is invalid (default: 0.0)
        clamp: Whether to clamp result to min_val/max_val range (default: True)
        min_val: Minimum allowed value when clamping (default: 0.0)
        max_val: Maximum allowed value when clamping (default: 100.0)
        ndigits: Number of decimal places to round to (default: None = no rounding)

    Returns:
        Percentage value, optionally clamped and rounded

    Examples:
        >>> safe_percentage(50, 100)
        50.0
        >>> safe_percentage(150, 100)  # Clamped to 100
        100.0
        >>> safe_percentage(150, 100, clamp=False)
        150.0
        >>> safe_percentage(1, 3, ndigits=2)
        33.33
        >>> safe_percentage(50, 0)  # Division by zero
        0.0
        >>> safe_percentage(float('nan'), 100)
        0.0
    """
    # Use safe_divide for the core calculation
    ratio = safe_divide(numerator, denominator, default=float("nan"))

    # Check if division failed
    if math.isnan(ratio):
        return default

    # Calculate percentage
    percentage = ratio * 100.0

    # Apply clamping if enabled
    if clamp:
        percentage = max(min_val, min(max_val, percentage))

    # Apply rounding if specified
    if ndigits is not None:
        percentage = round(percentage, ndigits)

    return percentage


def _sanitize_float(value: object) -> float | object:
    """Pydantic BeforeValidator for SafeFloat type.

    Sanitizes NaN, Inf, and None values to 0.0 before Pydantic validation.
    Used as the validator function for the SafeFloat annotated type.

    Args:
        value: The input value (any type - Pydantic passes raw input)

    Returns:
        Sanitized float value (0.0 for invalid inputs), or original value
        for non-numeric types (lets Pydantic handle type errors)
    """
    if value is None:
        return 0.0
    if not isinstance(value, (int, float)):
        # Let Pydantic handle type coercion/errors for non-numeric types
        return value
    return safe_float(float(value))


# SafeFloat: Annotated type for NaN/Infinity-safe floats in Pydantic models
#
# Use this type annotation in Pydantic models for fields that may receive
# NaN or Infinity values from external sources (Prometheus metrics, etc.).
# The type automatically sanitizes invalid values to 0.0 and documents
# this behavior in the OpenAPI schema.
#
# Usage:
#     class MetricsResponse(BaseModel):
#         latency_ms: SafeFloat
#         error_rate: SafeFloat
#         health_score: SafeFloat | None = None  # Optional with None
#
# Benefits:
#     1. Automatic NaN/Inf sanitization via BeforeValidator
#     2. OpenAPI schema documentation for API consumers
#     3. JSON serialization safety (no ValueError for NaN/Inf)
#     4. Type-safe with full IDE support
#
SafeFloat = Annotated[
    float,
    BeforeValidator(_sanitize_float),
    Field(
        description="NaN/Infinity-safe float value. "
        "Invalid values (NaN, Inf, -Inf) are automatically converted to 0.0 "
        "to ensure JSON serialization safety."
    ),
]
