"""
Output Format definitions for structured responses.

This module implements Claude Agent SDK's output_format pattern
for JSON Schema validation of agent responses.

Key features:
- OutputFormat dataclass for format specification
- JSON Schema format type support
- Pre-defined common schemas for typical responses
- Conversion to/from SDK dictionary format
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class OutputFormatType(Enum):
    """Type of output format."""

    JSON_SCHEMA = "json_schema"
    TEXT = "text"


@dataclass
class OutputFormat:
    """
    Specification for structured output format.

    Defines how agent responses should be structured and validated.
    Supports JSON Schema validation for type-safe responses.

    Attributes:
        format_type: The type of format (json_schema or text)
        schema: JSON Schema for validation (required for json_schema type)
        name: Optional name for the format
        description: Optional description
    """

    format_type: OutputFormatType
    schema: dict[str, Any] | None = None
    name: str | None = None
    description: str | None = None

    def __post_init__(self) -> None:
        """Validate the output format configuration."""
        if self.format_type == OutputFormatType.JSON_SCHEMA and self.schema is None:
            msg = "JSON Schema format requires a schema"
            raise ValueError(msg)

    @classmethod
    def from_dict(cls, config: dict[str, Any]) -> OutputFormat:
        """
        Create OutputFormat from SDK-style dictionary.

        Args:
            config: Dictionary with 'type' and optionally 'schema', 'name'

        Returns:
            OutputFormat instance

        Raises:
            ValueError: If format type is unknown
        """
        format_type_str = config.get("type", "text")

        try:
            format_type = OutputFormatType(format_type_str)
        except ValueError:
            msg = f"Unknown output format type: {format_type_str}"
            raise ValueError(msg) from None

        return cls(
            format_type=format_type,
            schema=config.get("schema"),
            name=config.get("name"),
            description=config.get("description"),
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to SDK-style dictionary.

        Returns:
            Dictionary representation suitable for SDK consumption
        """
        result: dict[str, Any] = {"type": self.format_type.value}

        if self.schema is not None:
            result["schema"] = self.schema

        if self.name is not None:
            result["name"] = self.name

        if self.description is not None:
            result["description"] = self.description

        return result


def simple_response_format() -> OutputFormat:
    """
    Create a simple response format.

    Standard format for basic agent responses with result and optional metadata.

    Returns:
        OutputFormat for simple responses
    """
    return OutputFormat(
        format_type=OutputFormatType.JSON_SCHEMA,
        schema={
            "type": "object",
            "properties": {
                "result": {
                    "type": "string",
                    "description": "The main response content",
                },
                "confidence": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                    "description": "Confidence score for the response",
                },
            },
            "required": ["result"],
        },
        name="simple_response",
        description="Basic response format with result and optional confidence",
    )


def analysis_response_format() -> OutputFormat:
    """
    Create an analysis response format.

    Format for responses that include analysis, findings, and recommendations.

    Returns:
        OutputFormat for analysis responses
    """
    return OutputFormat(
        format_type=OutputFormatType.JSON_SCHEMA,
        schema={
            "type": "object",
            "properties": {
                "analysis": {
                    "type": "string",
                    "description": "Detailed analysis of the subject",
                },
                "findings": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Key findings from the analysis",
                },
                "recommendations": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Recommendations based on findings",
                },
                "confidence": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                    "description": "Overall confidence in the analysis",
                },
            },
            "required": ["analysis", "findings"],
        },
        name="analysis_response",
        description="Analysis response with findings and recommendations",
    )


def code_response_format() -> OutputFormat:
    """
    Create a code response format.

    Format for responses that include generated code with explanation.

    Returns:
        OutputFormat for code responses
    """
    return OutputFormat(
        format_type=OutputFormatType.JSON_SCHEMA,
        schema={
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "The generated code",
                },
                "language": {
                    "type": "string",
                    "description": "Programming language of the code",
                },
                "explanation": {
                    "type": "string",
                    "description": "Explanation of what the code does",
                },
                "usage": {
                    "type": "string",
                    "description": "How to use the generated code",
                },
            },
            "required": ["code", "language"],
        },
        name="code_response",
        description="Code response with explanation and usage",
    )
