"""
Schema Validator for structured output validation.

This module implements JSON Schema validation for agent responses
following Claude Agent SDK's output_format pattern.

Key features:
- JSON Schema validation using jsonschema library
- Integration with OutputFormat
- Detailed validation error reporting
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import jsonschema  # type: ignore[import-untyped]
from jsonschema import Draft7Validator, ValidationError

if TYPE_CHECKING:
    from mcp_server_langgraph.core.output_format import OutputFormat


@dataclass
class ValidationResult:
    """
    Result of a schema validation operation.

    Attributes:
        valid: Whether the validation passed
        errors: List of error messages if validation failed
    """

    valid: bool
    errors: list[str] = field(default_factory=list)


class SchemaValidator:
    """
    Validator for JSON Schema based output validation.

    Validates output against a JSON Schema, providing detailed
    error messages for validation failures.

    Example:
        schema = {
            "type": "object",
            "properties": {
                "result": {"type": "string"},
            },
            "required": ["result"]
        }

        validator = SchemaValidator(schema)
        result = validator.validate({"result": "success"})

        if result.valid:
            print("Output is valid")
        else:
            print(f"Validation errors: {result.errors}")
    """

    def __init__(self, schema: dict[str, Any]) -> None:
        """
        Initialize the validator with a JSON Schema.

        Args:
            schema: JSON Schema to validate against

        Raises:
            ValueError: If schema is invalid
        """
        self._schema = schema
        self._validate_schema()

    def _validate_schema(self) -> None:
        """
        Validate that the schema itself is valid.

        Raises:
            ValueError: If schema is invalid
        """
        try:
            Draft7Validator.check_schema(self._schema)
        except jsonschema.SchemaError as e:
            msg = f"Invalid JSON Schema: {e.message}"
            raise ValueError(msg) from e

    def validate(self, data: Any) -> ValidationResult:
        """
        Validate data against the schema.

        Args:
            data: Data to validate

        Returns:
            ValidationResult with valid flag and any errors
        """
        validator = Draft7Validator(self._schema)
        errors: list[str] = []

        for error in validator.iter_errors(data):
            error_msg = self._format_error(error)
            errors.append(error_msg)

        return ValidationResult(valid=len(errors) == 0, errors=errors)

    def _format_error(self, error: ValidationError) -> str:
        """
        Format a validation error into a human-readable message.

        Args:
            error: ValidationError from jsonschema

        Returns:
            Formatted error message
        """
        path = ".".join(str(p) for p in error.absolute_path) if error.absolute_path else "root"
        return f"{path}: {error.message}"

    @classmethod
    def from_output_format(cls, output_format: OutputFormat) -> SchemaValidator:
        """
        Create a SchemaValidator from an OutputFormat.

        Args:
            output_format: OutputFormat with JSON Schema

        Returns:
            SchemaValidator instance

        Raises:
            ValueError: If output_format doesn't have a schema
        """
        from mcp_server_langgraph.core.output_format import OutputFormatType

        if output_format.format_type != OutputFormatType.JSON_SCHEMA:
            msg = "Cannot create validator from non-JSON Schema output format"
            raise ValueError(msg)

        if output_format.schema is None:
            msg = "OutputFormat has no schema defined"
            raise ValueError(msg)

        return cls(output_format.schema)

    @property
    def schema(self) -> dict[str, Any]:
        """Get the schema used by this validator."""
        return self._schema
