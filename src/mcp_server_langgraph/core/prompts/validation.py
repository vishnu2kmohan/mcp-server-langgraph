"""
Runtime Output Validation for LLM Responses

Validates LLM outputs against Pydantic schemas at runtime to catch output drift
in production. Provides graceful degradation with fallback support.

Features:
- Schema validation against Pydantic models
- Markdown code block stripping (```json)
- Fallback value support on validation failure
- Non-blocking operation (never raises)
- Prometheus metrics for validation success/failure

Performance Requirements:
- Validation must be < 5ms overhead
- Non-blocking (fire-and-forget metrics)
- Graceful degradation without prometheus_client

References:
- ADR-0089: Prompt Architecture Centralization
- Phase 7: Telemetry & Metadata
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, TypeVar

from pydantic import BaseModel, ValidationError

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Type variable for Pydantic model
T = TypeVar("T", bound=BaseModel)


# =============================================================================
# LAZY-LOADED PROMETHEUS METRICS
# =============================================================================

_metrics_available: bool | None = None
_validation_success_total: Any = None
_validation_failure_total: Any = None
_validation_parse_error_total: Any = None


def _init_validation_metrics() -> bool:
    """Initialize validation metrics lazily."""
    global _metrics_available  # noqa: PLW0603
    global _validation_success_total  # noqa: PLW0603
    global _validation_failure_total  # noqa: PLW0603
    global _validation_parse_error_total  # noqa: PLW0603

    if _metrics_available is not None:
        return _metrics_available

    try:
        from prometheus_client import Counter

        _validation_success_total = Counter(
            "prompt_validation_success_total",
            "Total successful prompt output validations",
            ["prompt_name", "schema_name"],
        )

        _validation_failure_total = Counter(
            "prompt_validation_failure_total",
            "Total failed prompt output validations",
            ["prompt_name", "schema_name", "failure_type"],
        )

        _validation_parse_error_total = Counter(
            "prompt_validation_parse_error_total",
            "Total JSON parse errors in prompt output validation",
            ["prompt_name"],
        )

        _metrics_available = True
        logger.debug("Validation metrics initialized successfully")
        return True

    except ImportError:
        _metrics_available = False
        logger.debug("prometheus_client not available, validation metrics disabled")
        return False


# Initialize on module load
_init_validation_metrics()


# =============================================================================
# BOUNDED LABELS
# =============================================================================

BOUNDED_FAILURE_TYPES: frozenset[str] = frozenset(
    {
        "json_parse_error",
        "schema_validation_error",
        "constraint_violation",
        "missing_field",
        "invalid_enum",
        "type_error",
        "other",
    }
)


def _normalize_failure_type(failure_type: str) -> str:
    """Normalize failure type to bounded value."""
    if failure_type in BOUNDED_FAILURE_TYPES:
        return failure_type
    return "other"


# =============================================================================
# VALIDATION RESULT
# =============================================================================


@dataclass
class ValidationResult:
    """Result of LLM output validation.

    Attributes:
        success: Whether validation succeeded
        parsed_output: The validated and parsed output (or fallback)
        error: Error message if validation failed
        used_fallback: Whether fallback was used
        prompt_name: Name of the prompt being validated
    """

    success: bool
    parsed_output: BaseModel | None = None
    error: str | None = None
    used_fallback: bool = False
    prompt_name: str | None = None


# =============================================================================
# METRICS RECORDING
# =============================================================================


def _record_validation_metric(
    prompt_name: str,
    schema_name: str,
    success: bool,
    failure_type: str | None = None,
) -> None:
    """Record validation metric (fire-and-forget).

    Args:
        prompt_name: Name of the prompt
        schema_name: Name of the schema class
        success: Whether validation succeeded
        failure_type: Type of failure (if any)
    """
    if not _metrics_available:
        return

    try:
        if success:
            if _validation_success_total:
                _validation_success_total.labels(
                    prompt_name=prompt_name,
                    schema_name=schema_name,
                ).inc()
        else:
            if _validation_failure_total and failure_type:
                normalized_type = _normalize_failure_type(failure_type)
                _validation_failure_total.labels(
                    prompt_name=prompt_name,
                    schema_name=schema_name,
                    failure_type=normalized_type,
                ).inc()
    except Exception as e:
        # Fire-and-forget: never let metrics recording affect application
        logger.debug("Failed to record validation metric: %s", e)


def _record_parse_error(prompt_name: str) -> None:
    """Record JSON parse error metric."""
    if not _metrics_available:
        return

    try:
        if _validation_parse_error_total:
            _validation_parse_error_total.labels(prompt_name=prompt_name).inc()
    except Exception as e:
        logger.debug("Failed to record parse error metric: %s", e)


# =============================================================================
# JSON PREPROCESSING
# =============================================================================

# Regex pattern to match markdown code blocks
CODE_BLOCK_PATTERN = re.compile(r"```(?:json)?\s*\n?(.*?)\n?```", re.DOTALL)


def _strip_markdown_code_blocks(content: str) -> str:
    """Strip markdown code blocks from content.

    Args:
        content: Raw LLM response content

    Returns:
        Content with markdown code blocks stripped
    """
    content = content.strip()

    # Try to find and extract code block content
    match = CODE_BLOCK_PATTERN.search(content)
    if match:
        return match.group(1).strip()

    return content


# =============================================================================
# MAIN VALIDATION FUNCTION
# =============================================================================


def validate_output(
    content: str | None,
    schema: type[T],
    prompt_name: str,
    fallback: T | None = None,
) -> ValidationResult:
    """Validate LLM output against a Pydantic schema.

    This function NEVER raises exceptions. It returns a ValidationResult
    indicating success/failure and provides graceful degradation.

    Args:
        content: Raw LLM response content (JSON string)
        schema: Pydantic model class to validate against
        prompt_name: Name of the prompt (for metrics)
        fallback: Optional fallback value on validation failure

    Returns:
        ValidationResult with validation status and parsed output

    Examples:
        >>> from mcp_server_langgraph.core.prompts.schemas import ResponseOutput
        >>> result = validate_output(
        ...     '{"content": "Hello", "confidence": 0.9}',
        ...     ResponseOutput,
        ...     prompt_name="response"
        ... )
        >>> assert result.success
        >>> assert result.parsed_output.content == "Hello"
    """
    schema_name = schema.__name__

    # Handle None or empty input
    if not content:
        _record_validation_metric(
            prompt_name=prompt_name,
            schema_name=schema_name,
            success=False,
            failure_type="json_parse_error",
        )
        return ValidationResult(
            success=False,
            parsed_output=fallback,
            error="Empty or None content",
            used_fallback=fallback is not None,
            prompt_name=prompt_name,
        )

    # Strip markdown code blocks
    try:
        cleaned_content = _strip_markdown_code_blocks(content)
    except Exception as e:
        logger.debug("Failed to strip markdown: %s", e)
        cleaned_content = content

    # Parse JSON
    try:
        data = json.loads(cleaned_content)
    except json.JSONDecodeError as e:
        _record_parse_error(prompt_name)
        _record_validation_metric(
            prompt_name=prompt_name,
            schema_name=schema_name,
            success=False,
            failure_type="json_parse_error",
        )
        logger.debug("JSON parse error for %s: %s", prompt_name, e)
        return ValidationResult(
            success=False,
            parsed_output=fallback,
            error=f"JSON parse error: {e}",
            used_fallback=fallback is not None,
            prompt_name=prompt_name,
        )

    # Validate against schema
    try:
        parsed = schema(**data)
        _record_validation_metric(
            prompt_name=prompt_name,
            schema_name=schema_name,
            success=True,
        )
        return ValidationResult(
            success=True,
            parsed_output=parsed,
            error=None,
            used_fallback=False,
            prompt_name=prompt_name,
        )
    except ValidationError as e:
        # Determine failure type from Pydantic error
        failure_type = _categorize_pydantic_error(e)
        _record_validation_metric(
            prompt_name=prompt_name,
            schema_name=schema_name,
            success=False,
            failure_type=failure_type,
        )
        logger.debug("Schema validation error for %s: %s", prompt_name, e)
        return ValidationResult(
            success=False,
            parsed_output=fallback,
            error=f"Schema validation error: {e}",
            used_fallback=fallback is not None,
            prompt_name=prompt_name,
        )
    except Exception as e:
        # Catch-all for unexpected errors
        _record_validation_metric(
            prompt_name=prompt_name,
            schema_name=schema_name,
            success=False,
            failure_type="other",
        )
        logger.debug("Unexpected validation error for %s: %s", prompt_name, e)
        return ValidationResult(
            success=False,
            parsed_output=fallback,
            error=f"Unexpected error: {e}",
            used_fallback=fallback is not None,
            prompt_name=prompt_name,
        )


def _categorize_pydantic_error(error: ValidationError) -> str:
    """Categorize Pydantic validation error for metrics.

    Args:
        error: Pydantic ValidationError

    Returns:
        Failure type string
    """
    errors = error.errors()
    if not errors:
        return "schema_validation_error"

    first_error = errors[0]
    error_type = first_error.get("type", "")

    if "missing" in error_type:
        return "missing_field"
    elif "enum" in error_type or "literal" in error_type:
        return "invalid_enum"
    elif "type" in error_type:
        return "type_error"
    elif "greater_than" in error_type or "less_than" in error_type:
        return "constraint_violation"
    else:
        return "schema_validation_error"


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "ValidationResult",
    "validate_output",
]
