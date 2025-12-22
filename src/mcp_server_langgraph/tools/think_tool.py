"""
Think Tool for Complex Reasoning

This tool provides a structured reasoning space for LLMs to pause and think
during complex tool chains. Based on Anthropic's research showing 54% relative
improvement in complex policy scenarios when using a think tool.

The think tool is a no-op that:
1. Records the thought for reasoning trace
2. Returns a confirmation without external side effects
3. Helps with policy compliance verification
4. Supports intermediate reasoning during multi-step operations

Two versions available:
- `think`: Simple text-based reasoning (returns string)
- `think_structured`: Structured output with category and confidence (returns dict)

Usage:
    from mcp_server_langgraph.tools.think_tool import think, think_structured

    # Simple
    result = think.invoke({"thought": "Verifying policy compliance..."})

    # Structured
    result = think_structured.invoke({
        "thought": "Verifying policy compliance...",
        "category": "policy_verification",
    })
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel, Field


# =============================================================================
# Structured Output Models
# =============================================================================


class ThoughtCategory(str, Enum):
    """Categories of thought for structured reasoning."""

    POLICY_VERIFICATION = "policy_verification"
    INTERMEDIATE_REASONING = "intermediate_reasoning"
    ERROR_ANALYSIS = "error_analysis"
    PLANNING = "planning"
    DATA_ANALYSIS = "data_analysis"
    SECURITY_CHECK = "security_check"
    OTHER = "other"


class StructuredThoughtOutput(BaseModel):
    """Structured output from think_structured tool.

    Provides typed, JSON-serializable output for reasoning steps.
    """

    thought: str = Field(description="The recorded thought content")
    category: ThoughtCategory = Field(
        description="Category of the thought",
        default=ThoughtCategory.OTHER,
    )
    confidence: float = Field(
        description="Confidence level (0.0 to 1.0) in the reasoning",
        default=0.8,
        ge=0.0,
        le=1.0,
    )
    next_steps: list[str] | None = Field(
        description="Optional suggested next steps based on the thought",
        default=None,
    )

    model_config = {"use_enum_values": True}


# Maximum characters to include in response (avoid token waste)
MAX_THOUGHT_ECHO_LENGTH = 100


def _safe_log(level: str, message: str, **kwargs: Any) -> None:
    """Safely log message, handling cases where observability isn't initialized"""
    try:
        from mcp_server_langgraph.observability.telemetry import logger

        getattr(logger, level)(message, **kwargs)
    except (ImportError, RuntimeError):
        # Observability not available - silently skip
        pass


@tool
def think(
    thought: str = Field(description="The reasoning or thought to record"),
) -> str:
    """Structured reasoning space without external effects.

    Use this tool to pause and reason during complex tool chains,
    verify policy compliance, or analyze tool outputs before proceeding.

    This tool has NO side effects - it simply records your thought
    process and returns a confirmation. Use it to:

    1. Verify policy compliance before sensitive operations
    2. Analyze intermediate results in multi-step workflows
    3. Plan next steps based on previous tool outputs
    4. Document reasoning for audit trails

    Args:
        thought: The reasoning or thought to record. Can be any length,
                but only the first 100 characters are echoed in response.

    Returns:
        Confirmation that the thought was recorded, with a truncated echo.
    """
    # Log the thought for observability (if available)
    _safe_log("debug", "Think tool invoked", thought_preview=thought[:50] if thought else "")

    # Handle empty thought
    if not thought or not thought.strip():
        return "Thought recorded: (empty)"

    # Truncate for response to avoid token waste
    truncated = thought[:MAX_THOUGHT_ECHO_LENGTH]
    if len(thought) > MAX_THOUGHT_ECHO_LENGTH:
        truncated += "..."

    return f"Thought recorded: {truncated}"


# =============================================================================
# Structured Think Tool
# =============================================================================


def _parse_category(category_str: str) -> ThoughtCategory:
    """Parse category string to ThoughtCategory enum, with fallback."""
    try:
        return ThoughtCategory(category_str.lower())
    except ValueError:
        return ThoughtCategory.OTHER


def _resolve_field_default(value: Any, default: Any) -> Any:
    """Resolve FieldInfo to actual default value if needed.

    LangChain's @tool decorator can pass FieldInfo objects instead of
    actual values when parameters aren't provided. This helper extracts
    the actual default.
    """
    from pydantic.fields import FieldInfo

    if isinstance(value, FieldInfo):
        return default
    return value


@tool
def think_structured(
    thought: str = Field(description="The reasoning or thought to record"),
    category: str = Field(
        description="Category of thought: policy_verification, intermediate_reasoning, error_analysis, planning, data_analysis, security_check, other",
        default="other",
    ),
    confidence: float = Field(
        description="Confidence level (0.0 to 1.0) in this reasoning",
        default=0.8,
    ),
    next_steps: list[str] | None = Field(
        description="Optional list of suggested next steps",
        default=None,
    ),
) -> dict[str, Any]:
    """Structured reasoning space with typed output.

    Use this tool for structured reasoning during complex tool chains.
    Returns a typed dictionary that can be easily parsed and processed.

    Unlike the simple `think` tool, this returns structured output including:
    - thought: The recorded reasoning
    - category: Type of reasoning (policy_verification, error_analysis, etc.)
    - confidence: Confidence level (0.0-1.0)
    - next_steps: Optional suggested follow-up actions

    Args:
        thought: The reasoning or thought to record.
        category: Category of the thought (defaults to 'other').
        confidence: Confidence level between 0.0 and 1.0 (defaults to 0.8).
        next_steps: Optional list of suggested next steps.

    Returns:
        Dictionary with thought, category, confidence, and optional next_steps.
    """
    # Resolve any FieldInfo objects to actual defaults
    resolved_category = _resolve_field_default(category, "other")
    resolved_confidence = _resolve_field_default(confidence, 0.8)
    resolved_next_steps = _resolve_field_default(next_steps, None)

    # Log the structured thought for observability
    _safe_log(
        "debug",
        "Structured think tool invoked",
        category=resolved_category,
        thought_preview=thought[:50] if thought else "",
    )

    # Parse and validate category
    parsed_category = _parse_category(resolved_category)

    # Clamp confidence to valid range
    clamped_confidence = max(0.0, min(1.0, resolved_confidence))

    # Build output
    output = StructuredThoughtOutput(
        thought=thought or "",
        category=parsed_category,
        confidence=clamped_confidence,
        next_steps=resolved_next_steps,
    )

    return output.model_dump()
