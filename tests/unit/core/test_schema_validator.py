"""
Tests for Schema Validator (Phase 4.2)

Following TDD: Write tests FIRST, then implementation.

This module tests the JSON Schema validator for structured output
validation following Claude Agent SDK's output_format pattern.
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    pass

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="schema_validator")
class TestSchemaValidatorImport:
    """Test schema validator components can be imported."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_schema_validator_importable(self) -> None:
        """SchemaValidator should be importable."""
        from mcp_server_langgraph.core.schema_validator import SchemaValidator

        assert SchemaValidator is not None

    def test_validation_result_importable(self) -> None:
        """ValidationResult should be importable."""
        from mcp_server_langgraph.core.schema_validator import ValidationResult

        assert ValidationResult is not None


@pytest.mark.xdist_group(name="schema_validator")
class TestValidationResult:
    """Test ValidationResult dataclass."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_validation_result_success(self) -> None:
        """ValidationResult should represent successful validation."""
        from mcp_server_langgraph.core.schema_validator import ValidationResult

        result = ValidationResult(valid=True)

        assert result.valid is True
        assert result.errors == []

    def test_validation_result_with_errors(self) -> None:
        """ValidationResult should hold errors for failed validation."""
        from mcp_server_langgraph.core.schema_validator import ValidationResult

        result = ValidationResult(valid=False, errors=["Missing required field: name"])

        assert result.valid is False
        assert len(result.errors) == 1
        assert "name" in result.errors[0]


@pytest.mark.xdist_group(name="schema_validator")
class TestSchemaValidatorBasic:
    """Test basic SchemaValidator functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_validate_simple_object(self) -> None:
        """Should validate simple object against schema."""
        from mcp_server_langgraph.core.schema_validator import SchemaValidator

        schema = {
            "type": "object",
            "properties": {
                "result": {"type": "string"},
            },
            "required": ["result"],
        }

        validator = SchemaValidator(schema)
        result = validator.validate({"result": "success"})

        assert result.valid is True
        assert result.errors == []

    def test_validate_missing_required_field(self) -> None:
        """Should fail validation when required field is missing."""
        from mcp_server_langgraph.core.schema_validator import SchemaValidator

        schema = {
            "type": "object",
            "properties": {
                "result": {"type": "string"},
            },
            "required": ["result"],
        }

        validator = SchemaValidator(schema)
        result = validator.validate({})

        assert result.valid is False
        assert len(result.errors) > 0

    def test_validate_wrong_type(self) -> None:
        """Should fail validation when type is wrong."""
        from mcp_server_langgraph.core.schema_validator import SchemaValidator

        schema = {
            "type": "object",
            "properties": {
                "count": {"type": "integer"},
            },
        }

        validator = SchemaValidator(schema)
        result = validator.validate({"count": "not-a-number"})

        assert result.valid is False
        assert len(result.errors) > 0


@pytest.mark.xdist_group(name="schema_validator")
class TestSchemaValidatorComplex:
    """Test SchemaValidator with complex schemas."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_validate_nested_object(self) -> None:
        """Should validate nested objects."""
        from mcp_server_langgraph.core.schema_validator import SchemaValidator

        schema = {
            "type": "object",
            "properties": {
                "user": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "age": {"type": "integer"},
                    },
                    "required": ["name"],
                },
            },
            "required": ["user"],
        }

        validator = SchemaValidator(schema)

        # Valid nested object
        result = validator.validate({"user": {"name": "Alice", "age": 30}})
        assert result.valid is True

        # Invalid - missing nested required field
        result = validator.validate({"user": {"age": 30}})
        assert result.valid is False

    def test_validate_array_items_with_correct_type_succeeds(self) -> None:
        """Should validate arrays with correct item types."""
        from mcp_server_langgraph.core.schema_validator import SchemaValidator

        schema = {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
        }

        validator = SchemaValidator(schema)

        # Valid array
        result = validator.validate({"items": ["a", "b", "c"]})
        assert result.valid is True

        # Invalid - wrong item type
        result = validator.validate({"items": [1, 2, 3]})
        assert result.valid is False

    def test_validate_with_additional_properties_false(self) -> None:
        """Should fail when additionalProperties is false and extra props exist."""
        from mcp_server_langgraph.core.schema_validator import SchemaValidator

        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
            },
            "additionalProperties": False,
        }

        validator = SchemaValidator(schema)

        # Valid - only defined properties
        result = validator.validate({"name": "test"})
        assert result.valid is True

        # Invalid - extra property
        result = validator.validate({"name": "test", "extra": "value"})
        assert result.valid is False


@pytest.mark.xdist_group(name="schema_validator")
class TestSchemaValidatorWithOutputFormat:
    """Test SchemaValidator integration with OutputFormat."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_validate_with_output_format(self) -> None:
        """Should validate output using OutputFormat."""
        from mcp_server_langgraph.core.output_format import (
            OutputFormat,
            OutputFormatType,
        )
        from mcp_server_langgraph.core.schema_validator import SchemaValidator

        output_format = OutputFormat(
            format_type=OutputFormatType.JSON_SCHEMA,
            schema={
                "type": "object",
                "properties": {
                    "answer": {"type": "string"},
                },
                "required": ["answer"],
            },
        )

        validator = SchemaValidator.from_output_format(output_format)

        result = validator.validate({"answer": "42"})
        assert result.valid is True

    def test_validate_with_simple_response_format(self) -> None:
        """Should validate output using simple_response_format."""
        from mcp_server_langgraph.core.output_format import simple_response_format
        from mcp_server_langgraph.core.schema_validator import SchemaValidator

        output_format = simple_response_format()
        validator = SchemaValidator.from_output_format(output_format)

        # Valid simple response
        result = validator.validate({"result": "Hello, world!"})
        assert result.valid is True

        # Valid with optional confidence
        result = validator.validate({"result": "Hello", "confidence": 0.95})
        assert result.valid is True

        # Invalid - missing result
        result = validator.validate({"confidence": 0.5})
        assert result.valid is False

    def test_validate_with_analysis_response_format(self) -> None:
        """Should validate output using analysis_response_format."""
        from mcp_server_langgraph.core.output_format import analysis_response_format
        from mcp_server_langgraph.core.schema_validator import SchemaValidator

        output_format = analysis_response_format()
        validator = SchemaValidator.from_output_format(output_format)

        # Valid analysis response
        result = validator.validate(
            {
                "analysis": "Detailed analysis here",
                "findings": ["Finding 1", "Finding 2"],
                "recommendations": ["Recommendation 1"],
            }
        )
        assert result.valid is True

        # Invalid - missing findings
        result = validator.validate({"analysis": "Analysis"})
        assert result.valid is False


@pytest.mark.xdist_group(name="schema_validator")
class TestSchemaValidatorEdgeCases:
    """Test SchemaValidator edge cases."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_validate_null_value(self) -> None:
        """Should handle null values correctly."""
        from mcp_server_langgraph.core.schema_validator import SchemaValidator

        schema = {
            "type": "object",
            "properties": {
                "value": {"type": ["string", "null"]},
            },
        }

        validator = SchemaValidator(schema)

        result = validator.validate({"value": None})
        assert result.valid is True

        result = validator.validate({"value": "text"})
        assert result.valid is True

    def test_validate_empty_object(self) -> None:
        """Should validate empty objects when allowed."""
        from mcp_server_langgraph.core.schema_validator import SchemaValidator

        schema = {
            "type": "object",
            "properties": {},
        }

        validator = SchemaValidator(schema)
        result = validator.validate({})

        assert result.valid is True

    def test_invalid_schema_raises_error(self) -> None:
        """Should raise error for invalid schema."""
        from mcp_server_langgraph.core.schema_validator import SchemaValidator

        # Invalid schema - type is not a valid JSON Schema type
        invalid_schema = {
            "type": "invalid_type",
        }

        with pytest.raises(ValueError):
            SchemaValidator(invalid_schema)

    def test_text_format_raises_error(self) -> None:
        """Should raise error when trying to validate with text format."""
        from mcp_server_langgraph.core.output_format import (
            OutputFormat,
            OutputFormatType,
        )
        from mcp_server_langgraph.core.schema_validator import SchemaValidator

        output_format = OutputFormat(format_type=OutputFormatType.TEXT)

        with pytest.raises(ValueError):
            SchemaValidator.from_output_format(output_format)
