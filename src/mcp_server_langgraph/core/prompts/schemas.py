"""
Prompt Output Schemas - Pydantic Models for Structured Outputs

This module defines Pydantic models for validating LLM outputs from centralized prompts.
These schemas enforce type safety, value constraints, and provide documentation.

Schema Categories:
- Response: ResponseOutput for agentic response generation
- Verification: VerificationOutput for LLM-as-judge quality evaluation
- Error Handling: ErrorAnalysisOutput, RecoverySuggestion
- GenUI: WidgetConfigOutput for widget configuration

All schemas include:
- Field constraints (min/max values, enums)
- Default values where appropriate
- JSON serialization support
- Validation error messages

References:
- ADR-0089: Prompt Architecture Centralization
- Pydantic V2 documentation
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


# =============================================================================
# Response Output Schemas
# =============================================================================


class ResponseOutput(BaseModel):
    """Schema for agentic response generation output.

    Used by: response_prompt.py

    Attributes:
        content: The response content to display
        confidence: Model's confidence in the response (0.0-1.0)
        requires_clarification: Whether clarification is needed
        clarification_question: Optional question to ask user
        sources: List of source references used
    """

    content: str = Field(min_length=1, description="The response content")
    confidence: float = Field(ge=0.0, le=1.0, description="Response confidence 0.0-1.0")
    requires_clarification: bool = Field(default=False, description="Whether clarification is needed")
    clarification_question: str | None = Field(default=None, description="Optional clarification question")
    sources: list[str] = Field(default_factory=list, description="Source references used")


# =============================================================================
# Verification Output Schemas
# =============================================================================


class VerificationOutput(BaseModel):
    """Schema for LLM-as-judge quality evaluation output.

    Used by: verification_prompt.py

    Attributes:
        accuracy: Accuracy score (0.0-1.0)
        completeness: Completeness score (0.0-1.0)
        clarity: Clarity score (0.0-1.0)
        relevance: Relevance score (0.0-1.0)
        safety: Safety score (0.0-1.0)
        sources: Source quality score (0.0-1.0)
        overall: Overall quality score (0.0-1.0)
        critical_issues: List of critical issues found
        suggestions: List of improvement suggestions
        requires_refinement: Whether response needs refinement
        feedback: Human-readable feedback summary
    """

    accuracy: float = Field(ge=0.0, le=1.0, description="Accuracy score 0.0-1.0")
    completeness: float = Field(ge=0.0, le=1.0, description="Completeness score 0.0-1.0")
    clarity: float = Field(ge=0.0, le=1.0, description="Clarity score 0.0-1.0")
    relevance: float = Field(ge=0.0, le=1.0, description="Relevance score 0.0-1.0")
    safety: float = Field(ge=0.0, le=1.0, description="Safety score 0.0-1.0")
    sources: float = Field(ge=0.0, le=1.0, description="Source quality score 0.0-1.0")
    overall: float = Field(ge=0.0, le=1.0, description="Overall quality score 0.0-1.0")
    critical_issues: list[str] = Field(default_factory=list, description="List of critical issues")
    suggestions: list[str] = Field(default_factory=list, description="Improvement suggestions")
    requires_refinement: bool = Field(description="Whether response needs refinement")
    feedback: str = Field(description="Human-readable feedback summary")


# =============================================================================
# Error Analysis Output Schemas
# =============================================================================


class RecoverySuggestion(BaseModel):
    """Schema for error recovery suggestion.

    Used by: ERROR_ANALYSIS_SYSTEM_PROMPT in ai_ux_prompts.py

    Attributes:
        action: Recovery action type
        label: Button/action label text
        guidance: Optional detailed guidance
        estimated_success: Estimated success probability (0.0-1.0)
    """

    action: Literal["navigate", "retry", "wait", "simplify", "contact", "modal", "execute"] = Field(
        description="Recovery action type"
    )
    label: str = Field(description="Button/action label text")
    guidance: str | None = Field(default=None, description="Optional detailed guidance")
    estimated_success: float = Field(ge=0.0, le=1.0, description="Estimated success probability 0.0-1.0")


class ErrorAnalysisOutput(BaseModel):
    """Schema for error analysis output.

    Used by: ERROR_ANALYSIS_SYSTEM_PROMPT in ai_ux_prompts.py

    Attributes:
        category: Error category
        subcategory: More specific classification
        confidence: Confidence in classification (0.0-1.0)
        root_cause: Human-readable explanation
        suggestions: List of recovery suggestions
    """

    category: Literal[
        "network",
        "authentication",
        "authorization",
        "validation",
        "server",
        "client",
        "timeout",
        "quota",
        "unknown",
    ] = Field(description="Error category")
    subcategory: str = Field(description="More specific classification")
    confidence: float = Field(ge=0.0, le=1.0, description="Classification confidence 0.0-1.0")
    root_cause: str = Field(description="Human-readable explanation of the error cause")
    suggestions: list[RecoverySuggestion] = Field(default_factory=list, description="List of recovery suggestions")


# =============================================================================
# GenUI Output Schemas
# =============================================================================


class WidgetConfigOutput(BaseModel):
    """Schema for GenUI widget configuration output.

    Used by: GENUI_WIDGET_SYSTEM_PROMPT in genui_prompts.py

    Attributes:
        widget_type: Type of widget to render
        title: Widget title
        data: Widget-specific data payload
        confidence: Confidence in widget selection (0.0-1.0)
    """

    widget_type: Literal["chart", "table", "text"] = Field(description="Type of widget to render")
    title: str = Field(description="Widget title")
    data: dict[str, Any] = Field(description="Widget-specific data payload")
    confidence: float = Field(ge=0.0, le=1.0, description="Widget selection confidence 0.0-1.0")


# =============================================================================
# Workflow Output Schemas
# =============================================================================


class WorkflowNode(BaseModel):
    """Schema for workflow node definition.

    Attributes:
        id: Unique node identifier
        type: Node type
        label: Human-readable label
        config: Node-specific configuration
    """

    id: str = Field(description="Unique node identifier")
    type: Literal["start", "end", "llm", "tool", "router", "condition", "memory"] = Field(description="Node type")
    label: str = Field(description="Human-readable label")
    config: dict[str, Any] = Field(default_factory=dict, description="Node configuration")


class WorkflowEdge(BaseModel):
    """Schema for workflow edge definition.

    Attributes:
        source: Source node ID
        target: Target node ID
        condition: Optional condition for edge traversal
    """

    source: str = Field(description="Source node ID")
    target: str = Field(description="Target node ID")
    condition: str | None = Field(default=None, description="Optional condition")


class WorkflowOutput(BaseModel):
    """Schema for workflow generator output.

    Used by: WORKFLOW_GENERATOR_SYSTEM_PROMPT in workflow_prompts.py

    Attributes:
        name: Workflow name
        description: Workflow description
        nodes: List of workflow nodes
        edges: List of workflow edges
        reasoning: Explanation of design decisions
    """

    name: str = Field(description="Workflow name")
    description: str = Field(description="Workflow description")
    nodes: list[WorkflowNode] = Field(description="List of workflow nodes")
    edges: list[WorkflowEdge] = Field(description="List of workflow edges")
    reasoning: str = Field(description="Explanation of design decisions")


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Response
    "ResponseOutput",
    # Verification
    "VerificationOutput",
    # Error Analysis
    "RecoverySuggestion",
    "ErrorAnalysisOutput",
    # GenUI
    "WidgetConfigOutput",
    # Workflow
    "WorkflowNode",
    "WorkflowEdge",
    "WorkflowOutput",
]
