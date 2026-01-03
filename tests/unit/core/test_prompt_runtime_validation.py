"""
Tests for Runtime Output Validation (TDD - RED Phase)

Tests the validation layer that validates LLM outputs against Pydantic schemas
at runtime. This catches LLM output drift in production.

Following TDD pattern:
1. Write these tests first (RED)
2. Implement validation module (GREEN)
3. Refactor as needed

Memory Safety:
- Uses @pytest.mark.xdist_group for parallel test safety
- Includes teardown_method with gc.collect()

References:
- ADR-0089: Prompt Architecture Centralization
- Phase 7: Telemetry & Metadata
"""

from __future__ import annotations

import gc
import json
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    pass

# Module-level pytest marker
pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="prompt_runtime_validation")
class TestValidateOutputExists:
    """Tests that validate_output function exists and is callable."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_validate_output_function_exists(self) -> None:
        """Verify validate_output function can be imported."""
        from mcp_server_langgraph.core.prompts.validation import validate_output

        assert callable(validate_output)

    def test_validate_output_result_class_exists(self) -> None:
        """Verify ValidationResult class can be imported."""
        from mcp_server_langgraph.core.prompts.validation import ValidationResult

        assert ValidationResult is not None


@pytest.mark.xdist_group(name="prompt_runtime_validation")
class TestValidateOutputSuccess:
    """Tests for successful validation scenarios."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_validate_output_valid_response_output(self) -> None:
        """Verify validation succeeds for valid ResponseOutput JSON."""
        from mcp_server_langgraph.core.prompts.schemas import ResponseOutput
        from mcp_server_langgraph.core.prompts.validation import validate_output

        valid_json = json.dumps(
            {
                "content": "Hello, how can I help?",
                "confidence": 0.95,
                "requires_clarification": False,
                "sources": [],
            }
        )

        result = validate_output(valid_json, ResponseOutput, prompt_name="response")

        assert result.success is True
        assert result.parsed_output is not None
        assert isinstance(result.parsed_output, ResponseOutput)
        assert result.parsed_output.content == "Hello, how can I help?"
        assert result.error is None

    def test_validate_output_valid_error_analysis_output(self) -> None:
        """Verify validation succeeds for valid ErrorAnalysisOutput JSON."""
        from mcp_server_langgraph.core.prompts.schemas import ErrorAnalysisOutput
        from mcp_server_langgraph.core.prompts.validation import validate_output

        valid_json = json.dumps(
            {
                "category": "network",
                "subcategory": "connection_timeout",
                "confidence": 0.85,
                "root_cause": "Server not responding",
                "suggestions": [],
            }
        )

        result = validate_output(valid_json, ErrorAnalysisOutput, prompt_name="error_analysis")

        assert result.success is True
        assert result.parsed_output is not None
        assert result.parsed_output.category == "network"

    def test_validate_output_returns_validation_result(self) -> None:
        """Verify validate_output returns ValidationResult."""
        from mcp_server_langgraph.core.prompts.schemas import ResponseOutput
        from mcp_server_langgraph.core.prompts.validation import (
            ValidationResult,
            validate_output,
        )

        valid_json = json.dumps(
            {
                "content": "Test",
                "confidence": 0.5,
            }
        )

        result = validate_output(valid_json, ResponseOutput, prompt_name="response")

        assert isinstance(result, ValidationResult)


@pytest.mark.xdist_group(name="prompt_runtime_validation")
class TestValidateOutputFailure:
    """Tests for validation failure scenarios."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_validate_output_invalid_json(self) -> None:
        """Verify validation fails gracefully for invalid JSON."""
        from mcp_server_langgraph.core.prompts.schemas import ResponseOutput
        from mcp_server_langgraph.core.prompts.validation import validate_output

        invalid_json = "not valid json {"

        result = validate_output(invalid_json, ResponseOutput, prompt_name="response")

        assert result.success is False
        assert result.parsed_output is None
        assert result.error is not None
        assert "json" in result.error.lower() or "parse" in result.error.lower()

    def test_validate_output_schema_mismatch(self) -> None:
        """Verify validation fails for schema mismatch."""
        from mcp_server_langgraph.core.prompts.schemas import ResponseOutput
        from mcp_server_langgraph.core.prompts.validation import validate_output

        # Missing required 'content' field
        invalid_schema = json.dumps(
            {
                "confidence": 0.5,
            }
        )

        result = validate_output(invalid_schema, ResponseOutput, prompt_name="response")

        assert result.success is False
        assert result.error is not None

    def test_validate_output_invalid_enum_value(self) -> None:
        """Verify validation fails for invalid enum values."""
        from mcp_server_langgraph.core.prompts.schemas import ErrorAnalysisOutput
        from mcp_server_langgraph.core.prompts.validation import validate_output

        invalid_enum = json.dumps(
            {
                "category": "invalid_category",  # Not in allowed enum
                "subcategory": "test",
                "confidence": 0.5,
                "root_cause": "Test",
            }
        )

        result = validate_output(invalid_enum, ErrorAnalysisOutput, prompt_name="error_analysis")

        assert result.success is False
        assert result.error is not None

    def test_validate_output_constraint_violation(self) -> None:
        """Verify validation fails for constraint violations."""
        from mcp_server_langgraph.core.prompts.schemas import ResponseOutput
        from mcp_server_langgraph.core.prompts.validation import validate_output

        # Confidence > 1.0 violates constraint
        invalid_constraint = json.dumps(
            {
                "content": "Test",
                "confidence": 1.5,  # Invalid: > 1.0
            }
        )

        result = validate_output(invalid_constraint, ResponseOutput, prompt_name="response")

        assert result.success is False
        assert result.error is not None


@pytest.mark.xdist_group(name="prompt_runtime_validation")
class TestValidateOutputFallback:
    """Tests for fallback behavior on validation failure."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_validate_output_with_fallback(self) -> None:
        """Verify fallback value is used on validation failure."""
        from mcp_server_langgraph.core.prompts.schemas import ResponseOutput
        from mcp_server_langgraph.core.prompts.validation import validate_output

        fallback = ResponseOutput(
            content="Fallback response",
            confidence=0.0,
        )

        result = validate_output(
            "invalid json",
            ResponseOutput,
            prompt_name="response",
            fallback=fallback,
        )

        assert result.success is False
        assert result.parsed_output is not None
        assert result.parsed_output.content == "Fallback response"
        assert result.used_fallback is True

    def test_validate_output_without_fallback(self) -> None:
        """Verify None returned when no fallback provided."""
        from mcp_server_langgraph.core.prompts.schemas import ResponseOutput
        from mcp_server_langgraph.core.prompts.validation import validate_output

        result = validate_output("invalid json", ResponseOutput, prompt_name="response")

        assert result.success is False
        assert result.parsed_output is None
        assert result.used_fallback is False


@pytest.mark.xdist_group(name="prompt_runtime_validation")
class TestValidateOutputMetrics:
    """Tests for validation metrics recording."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_validation_records_success_metric(self) -> None:
        """Verify successful validation increments success counter."""
        from mcp_server_langgraph.core.prompts.schemas import ResponseOutput
        from mcp_server_langgraph.core.prompts.validation import validate_output

        with patch("mcp_server_langgraph.core.prompts.validation._record_validation_metric") as mock_metric:
            valid_json = json.dumps({"content": "Test", "confidence": 0.5})
            validate_output(valid_json, ResponseOutput, prompt_name="response")

            mock_metric.assert_called()
            # Check it was called with success=True
            call_args = mock_metric.call_args
            assert call_args is not None

    def test_validation_records_failure_metric(self) -> None:
        """Verify failed validation increments failure counter."""
        from mcp_server_langgraph.core.prompts.schemas import ResponseOutput
        from mcp_server_langgraph.core.prompts.validation import validate_output

        with patch("mcp_server_langgraph.core.prompts.validation._record_validation_metric") as mock_metric:
            validate_output("invalid json", ResponseOutput, prompt_name="response")

            mock_metric.assert_called()


@pytest.mark.xdist_group(name="prompt_runtime_validation")
class TestValidateOutputMarkdownStripping:
    """Tests for markdown code block stripping."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_validate_output_strips_json_code_block(self) -> None:
        """Verify validation strips ```json code blocks."""
        from mcp_server_langgraph.core.prompts.schemas import ResponseOutput
        from mcp_server_langgraph.core.prompts.validation import validate_output

        json_with_markdown = """```json
{"content": "Test", "confidence": 0.5}
```"""

        result = validate_output(json_with_markdown, ResponseOutput, prompt_name="response")

        assert result.success is True
        assert result.parsed_output is not None
        assert result.parsed_output.content == "Test"

    def test_validate_output_strips_generic_code_block(self) -> None:
        """Verify validation strips generic ``` code blocks."""
        from mcp_server_langgraph.core.prompts.schemas import ResponseOutput
        from mcp_server_langgraph.core.prompts.validation import validate_output

        json_with_markdown = """```
{"content": "Test", "confidence": 0.5}
```"""

        result = validate_output(json_with_markdown, ResponseOutput, prompt_name="response")

        assert result.success is True


@pytest.mark.xdist_group(name="prompt_runtime_validation")
class TestValidationResultAttributes:
    """Tests for ValidationResult dataclass attributes."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_validation_result_has_success_attribute(self) -> None:
        """Verify ValidationResult has success attribute."""
        from mcp_server_langgraph.core.prompts.validation import ValidationResult

        result = ValidationResult(success=True, parsed_output=None)
        assert hasattr(result, "success")

    def test_validation_result_has_parsed_output_attribute(self) -> None:
        """Verify ValidationResult has parsed_output attribute."""
        from mcp_server_langgraph.core.prompts.validation import ValidationResult

        result = ValidationResult(success=True, parsed_output=None)
        assert hasattr(result, "parsed_output")

    def test_validation_result_has_error_attribute(self) -> None:
        """Verify ValidationResult has error attribute."""
        from mcp_server_langgraph.core.prompts.validation import ValidationResult

        result = ValidationResult(success=False, parsed_output=None, error="Test error")
        assert hasattr(result, "error")
        assert result.error == "Test error"

    def test_validation_result_has_used_fallback_attribute(self) -> None:
        """Verify ValidationResult has used_fallback attribute."""
        from mcp_server_langgraph.core.prompts.validation import ValidationResult

        result = ValidationResult(success=False, parsed_output=None, used_fallback=True)
        assert hasattr(result, "used_fallback")
        assert result.used_fallback is True

    def test_validation_result_has_prompt_name_attribute(self) -> None:
        """Verify ValidationResult has prompt_name attribute."""
        from mcp_server_langgraph.core.prompts.validation import ValidationResult

        result = ValidationResult(success=True, parsed_output=None, prompt_name="response")
        assert hasattr(result, "prompt_name")
        assert result.prompt_name == "response"


@pytest.mark.xdist_group(name="prompt_runtime_validation")
class TestValidationNonBlocking:
    """Tests that validation never raises exceptions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_validate_output_never_raises_on_invalid_json(self) -> None:
        """Verify validate_output doesn't raise on invalid JSON."""
        from mcp_server_langgraph.core.prompts.schemas import ResponseOutput
        from mcp_server_langgraph.core.prompts.validation import validate_output

        # Should not raise
        result = validate_output("{{{{invalid", ResponseOutput, prompt_name="response")
        assert result.success is False

    def test_validate_output_never_raises_on_none_input(self) -> None:
        """Verify validate_output handles None input gracefully."""
        from mcp_server_langgraph.core.prompts.schemas import ResponseOutput
        from mcp_server_langgraph.core.prompts.validation import validate_output

        # Should not raise
        result = validate_output(None, ResponseOutput, prompt_name="response")  # type: ignore[arg-type]
        assert result.success is False

    def test_validate_output_never_raises_on_empty_string(self) -> None:
        """Verify validate_output handles empty string gracefully."""
        from mcp_server_langgraph.core.prompts.schemas import ResponseOutput
        from mcp_server_langgraph.core.prompts.validation import validate_output

        # Should not raise
        result = validate_output("", ResponseOutput, prompt_name="response")
        assert result.success is False


@pytest.mark.xdist_group(name="prompt_runtime_validation")
class TestValidationMetricsEdgeCases:
    """Tests for validation metrics edge cases and graceful degradation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_normalize_failure_type_known_types(self) -> None:
        """Verify known failure types are returned as-is."""
        from mcp_server_langgraph.core.prompts.validation import _normalize_failure_type

        assert _normalize_failure_type("json_parse_error") == "json_parse_error"
        assert _normalize_failure_type("schema_validation_error") == "schema_validation_error"
        assert _normalize_failure_type("constraint_violation") == "constraint_violation"
        assert _normalize_failure_type("missing_field") == "missing_field"
        assert _normalize_failure_type("invalid_enum") == "invalid_enum"
        assert _normalize_failure_type("type_error") == "type_error"

    def test_normalize_failure_type_unknown_returns_other(self) -> None:
        """Verify unknown failure types are normalized to 'other'."""
        from mcp_server_langgraph.core.prompts.validation import _normalize_failure_type

        assert _normalize_failure_type("unknown_error") == "other"
        assert _normalize_failure_type("custom_validation_failure") == "other"
        assert _normalize_failure_type("") == "other"

    def test_init_metrics_returns_cached_result(self) -> None:
        """Verify _init_validation_metrics returns cached result on subsequent calls."""
        from mcp_server_langgraph.core.prompts.validation import (
            _init_validation_metrics,
        )

        # Call multiple times - should return same cached value
        result1 = _init_validation_metrics()
        result2 = _init_validation_metrics()
        assert result1 == result2

    def test_record_validation_metric_handles_exception(self) -> None:
        """Verify _record_validation_metric handles exceptions gracefully."""
        from mcp_server_langgraph.core.prompts.validation import _record_validation_metric

        # Patch the counter to raise an exception
        with patch("mcp_server_langgraph.core.prompts.validation._validation_success_total") as mock_counter:
            mock_counter.labels.side_effect = Exception("Counter error")

            # Should not raise - fire-and-forget
            _record_validation_metric(
                prompt_name="test",
                schema_name="TestSchema",
                success=True,
            )

    def test_record_validation_metric_when_metrics_disabled(self) -> None:
        """Verify _record_validation_metric returns early when metrics disabled."""
        from mcp_server_langgraph.core.prompts.validation import _record_validation_metric

        with patch("mcp_server_langgraph.core.prompts.validation._metrics_available", False):
            # Should return early without error
            _record_validation_metric(
                prompt_name="test",
                schema_name="TestSchema",
                success=True,
            )

    def test_record_parse_error_when_metrics_disabled(self) -> None:
        """Verify _record_parse_error returns early when metrics disabled."""
        from mcp_server_langgraph.core.prompts.validation import _record_parse_error

        with patch("mcp_server_langgraph.core.prompts.validation._metrics_available", False):
            # Should return early without error
            _record_parse_error(prompt_name="test")

    def test_record_parse_error_handles_exception(self) -> None:
        """Verify _record_parse_error handles exceptions gracefully."""
        from mcp_server_langgraph.core.prompts.validation import _record_parse_error

        with patch("mcp_server_langgraph.core.prompts.validation._validation_parse_error_total") as mock_counter:
            mock_counter.labels.side_effect = Exception("Counter error")

            # Should not raise
            _record_parse_error(prompt_name="test")


@pytest.mark.xdist_group(name="prompt_runtime_validation")
class TestCategorizePydanticError:
    """Tests for _categorize_pydantic_error function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_categorize_empty_errors_returns_schema_validation_error(self) -> None:
        """Verify empty error list returns schema_validation_error."""
        from pydantic import ValidationError

        from mcp_server_langgraph.core.prompts.validation import _categorize_pydantic_error

        # Create a mock ValidationError with empty errors
        mock_error = MagicMock(spec=ValidationError)
        mock_error.errors.return_value = []

        result = _categorize_pydantic_error(mock_error)
        assert result == "schema_validation_error"

    def test_categorize_missing_field_error(self) -> None:
        """Verify missing field error is categorized correctly."""
        from pydantic import ValidationError

        from mcp_server_langgraph.core.prompts.validation import _categorize_pydantic_error

        mock_error = MagicMock(spec=ValidationError)
        mock_error.errors.return_value = [{"type": "value_error.missing"}]

        result = _categorize_pydantic_error(mock_error)
        assert result == "missing_field"

    def test_categorize_enum_error(self) -> None:
        """Verify enum error is categorized correctly."""
        from pydantic import ValidationError

        from mcp_server_langgraph.core.prompts.validation import _categorize_pydantic_error

        mock_error = MagicMock(spec=ValidationError)
        mock_error.errors.return_value = [{"type": "enum"}]

        result = _categorize_pydantic_error(mock_error)
        assert result == "invalid_enum"

    def test_categorize_literal_error(self) -> None:
        """Verify literal error is categorized as invalid_enum."""
        from pydantic import ValidationError

        from mcp_server_langgraph.core.prompts.validation import _categorize_pydantic_error

        mock_error = MagicMock(spec=ValidationError)
        mock_error.errors.return_value = [{"type": "literal_error"}]

        result = _categorize_pydantic_error(mock_error)
        assert result == "invalid_enum"

    def test_categorize_type_error(self) -> None:
        """Verify type error is categorized correctly."""
        from pydantic import ValidationError

        from mcp_server_langgraph.core.prompts.validation import _categorize_pydantic_error

        mock_error = MagicMock(spec=ValidationError)
        mock_error.errors.return_value = [{"type": "type_error.integer"}]

        result = _categorize_pydantic_error(mock_error)
        assert result == "type_error"

    def test_categorize_constraint_violation_greater_than(self) -> None:
        """Verify greater_than constraint is categorized correctly."""
        from pydantic import ValidationError

        from mcp_server_langgraph.core.prompts.validation import _categorize_pydantic_error

        mock_error = MagicMock(spec=ValidationError)
        mock_error.errors.return_value = [{"type": "greater_than_equal"}]

        result = _categorize_pydantic_error(mock_error)
        assert result == "constraint_violation"

    def test_categorize_constraint_violation_less_than(self) -> None:
        """Verify less_than constraint is categorized correctly."""
        from pydantic import ValidationError

        from mcp_server_langgraph.core.prompts.validation import _categorize_pydantic_error

        mock_error = MagicMock(spec=ValidationError)
        mock_error.errors.return_value = [{"type": "less_than_equal"}]

        result = _categorize_pydantic_error(mock_error)
        assert result == "constraint_violation"

    def test_categorize_unknown_error_type(self) -> None:
        """Verify unknown error type returns schema_validation_error."""
        from pydantic import ValidationError

        from mcp_server_langgraph.core.prompts.validation import _categorize_pydantic_error

        mock_error = MagicMock(spec=ValidationError)
        # Use a string that doesn't contain any of the keywords: missing, enum, literal, type, greater_than, less_than
        mock_error.errors.return_value = [{"type": "value_error.arbitrary"}]

        result = _categorize_pydantic_error(mock_error)
        assert result == "schema_validation_error"


@pytest.mark.xdist_group(name="prompt_runtime_validation")
class TestValidateOutputExceptionHandling:
    """Tests for exception handling in validate_output."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_validate_output_handles_markdown_strip_exception(self) -> None:
        """Verify validate_output handles exceptions during markdown stripping."""
        from mcp_server_langgraph.core.prompts.schemas import ResponseOutput
        from mcp_server_langgraph.core.prompts.validation import validate_output

        # Patch _strip_markdown_code_blocks to raise an exception
        with patch("mcp_server_langgraph.core.prompts.validation._strip_markdown_code_blocks") as mock_strip:
            mock_strip.side_effect = Exception("Markdown stripping error")

            # Should still work - uses original content as fallback
            valid_json = json.dumps({"content": "Test", "confidence": 0.5})
            result = validate_output(valid_json, ResponseOutput, prompt_name="response")

            # Should succeed because it falls back to original content
            assert result.success is True

    def test_validate_output_handles_unexpected_schema_exception(self) -> None:
        """Verify validate_output handles unexpected exceptions during schema validation."""
        from mcp_server_langgraph.core.prompts.schemas import ResponseOutput
        from mcp_server_langgraph.core.prompts.validation import validate_output

        # Create a schema that raises unexpected exception
        with patch.object(ResponseOutput, "__init__") as mock_init:
            mock_init.side_effect = RuntimeError("Unexpected error")

            valid_json = json.dumps({"content": "Test", "confidence": 0.5})
            result = validate_output(valid_json, ResponseOutput, prompt_name="response")

            assert result.success is False
            assert "Unexpected error" in result.error

    def test_validate_output_record_failure_with_failure_type(self) -> None:
        """Verify validation failures record the correct failure type."""
        from mcp_server_langgraph.core.prompts.schemas import ResponseOutput
        from mcp_server_langgraph.core.prompts.validation import validate_output

        with patch("mcp_server_langgraph.core.prompts.validation._record_validation_metric") as mock_metric:
            # Missing required field
            invalid_json = json.dumps({"confidence": 0.5})
            validate_output(invalid_json, ResponseOutput, prompt_name="response")

            # Should have been called with failure_type
            mock_metric.assert_called()
            calls = mock_metric.call_args_list
            # Find the failure call
            failure_calls = [c for c in calls if c.kwargs.get("success") is False]
            assert len(failure_calls) > 0
