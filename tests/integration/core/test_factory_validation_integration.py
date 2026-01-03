"""
Integration Tests for LLM Factory Validation

Tests the complete validation workflow including:
- Schema validation with real Pydantic models
- Telemetry integration with prompt tracking
- Feature flag gating for validation behavior
- Error recovery patterns with fallback values

Memory Safety:
- Uses @pytest.mark.xdist_group for parallel test safety
- Includes teardown_method with gc.collect()

References:
- ADR-0089: Prompt Architecture Centralization
- Phase 7: Telemetry & Metadata
- Phase 8: Comprehensive Tests
"""

from __future__ import annotations

import gc
import json
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel, Field

pytestmark = [
    pytest.mark.integration,
]


# =============================================================================
# TEST SCHEMAS FOR INTEGRATION TESTS
# =============================================================================


class SimpleSchema(BaseModel):
    """Minimal schema for basic validation testing."""

    value: str


class ComplexSchema(BaseModel):
    """Schema with multiple fields and constraints."""

    content: str
    confidence: float = Field(ge=0.0, le=1.0)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class NestedSchema(BaseModel):
    """Schema with nested structure."""

    outer: str
    inner: SimpleSchema


# =============================================================================
# FACTORY VALIDATION INTEGRATION TESTS
# =============================================================================


@pytest.mark.xdist_group(name="factory_validation_integration")
class TestFactoryValidationWorkflow:
    """Integration tests for complete factory validation workflow."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_validation_workflow_with_real_schema(self) -> None:
        """
        GIVEN an LLMFactory and a real Pydantic schema
        WHEN validating LLM output against the schema
        THEN correctly parses and validates the response
        """
        from mcp_server_langgraph.core.prompts.schemas import ResponseOutput
        from mcp_server_langgraph.core.prompts.validation import validate_output
        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(model_name="gpt-4", provider="openai")

        # Valid response that matches ResponseOutput schema
        valid_response = json.dumps({
            "content": "Integration test response",
            "confidence": 0.85,
            "requires_clarification": False,
            "sources": ["test_source"],
        })

        with patch.object(factory, "ainvoke", new_callable=AsyncMock) as mock_ainvoke:
            mock_ainvoke.return_value = AIMessage(content=valid_response)

            result = await factory.ainvoke_validated(
                messages=[HumanMessage(content="Test")],
                schema=ResponseOutput,
                prompt_name="response",
            )

            assert result.success is True
            assert result.parsed_output is not None
            assert result.parsed_output.content == "Integration test response"
            assert result.parsed_output.confidence == 0.85

    @pytest.mark.asyncio
    async def test_validation_workflow_with_complex_schema(self) -> None:
        """
        GIVEN a complex schema with constraints
        WHEN validating LLM output
        THEN enforces all field constraints
        """
        from mcp_server_langgraph.core.prompts.validation import validate_output

        valid_data = json.dumps({
            "content": "Complex data",
            "confidence": 0.75,
            "tags": ["tag1", "tag2"],
            "metadata": {"key": "value"},
        })

        result = validate_output(
            content=valid_data,
            schema=ComplexSchema,
            prompt_name="test",
        )

        assert result.success is True
        assert result.parsed_output.content == "Complex data"
        assert result.parsed_output.tags == ["tag1", "tag2"]
        assert result.parsed_output.metadata == {"key": "value"}

    @pytest.mark.asyncio
    async def test_validation_workflow_with_nested_schema(self) -> None:
        """
        GIVEN a schema with nested structures
        WHEN validating LLM output
        THEN correctly parses nested objects
        """
        from mcp_server_langgraph.core.prompts.validation import validate_output

        nested_data = json.dumps({
            "outer": "outer_value",
            "inner": {"value": "inner_value"},
        })

        result = validate_output(
            content=nested_data,
            schema=NestedSchema,
            prompt_name="test",
        )

        assert result.success is True
        assert result.parsed_output.outer == "outer_value"
        assert result.parsed_output.inner.value == "inner_value"


@pytest.mark.xdist_group(name="factory_validation_error_handling")
class TestFactoryValidationErrorHandling:
    """Integration tests for validation error handling scenarios."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_validation_handles_markdown_wrapped_json(self) -> None:
        """
        GIVEN JSON wrapped in markdown code blocks
        WHEN validating the output
        THEN strips markdown and parses correctly
        """
        from mcp_server_langgraph.core.prompts.validation import validate_output

        markdown_wrapped = '''```json
{"value": "test"}
```'''

        result = validate_output(
            content=markdown_wrapped,
            schema=SimpleSchema,
            prompt_name="test",
        )

        assert result.success is True
        assert result.parsed_output.value == "test"

    @pytest.mark.asyncio
    async def test_validation_handles_multiple_code_blocks(self) -> None:
        """
        GIVEN JSON with multiple markdown code blocks
        WHEN validating the output
        THEN extracts and parses the JSON block
        """
        from mcp_server_langgraph.core.prompts.validation import validate_output

        multi_block = '''Here's the output:

```json
{"value": "extracted"}
```

Additional text after.'''

        result = validate_output(
            content=multi_block,
            schema=SimpleSchema,
            prompt_name="test",
        )

        assert result.success is True
        assert result.parsed_output.value == "extracted"

    @pytest.mark.asyncio
    async def test_validation_categorizes_missing_field_errors(self) -> None:
        """
        GIVEN JSON missing required fields
        WHEN validating the output
        THEN reports error with field information
        """
        from mcp_server_langgraph.core.prompts.validation import validate_output

        missing_field = json.dumps({"extra": "ignored"})

        result = validate_output(
            content=missing_field,
            schema=SimpleSchema,
            prompt_name="test",
        )

        assert result.success is False
        assert result.error is not None
        # Error should mention the missing field
        assert "value" in result.error.lower() or "required" in result.error.lower()

    @pytest.mark.asyncio
    async def test_validation_categorizes_constraint_violations(self) -> None:
        """
        GIVEN JSON with constraint violations
        WHEN validating the output
        THEN reports error with constraint information
        """
        from mcp_server_langgraph.core.prompts.validation import validate_output

        violation = json.dumps({
            "content": "test",
            "confidence": 2.0,  # > 1.0 violates le=1.0
        })

        result = validate_output(
            content=violation,
            schema=ComplexSchema,
            prompt_name="test",
        )

        assert result.success is False
        assert result.error is not None
        # Error should mention constraint violation
        assert "confidence" in result.error.lower() or "less than" in result.error.lower()


@pytest.mark.xdist_group(name="factory_validation_fallback")
class TestFactoryValidationFallback:
    """Integration tests for fallback behavior."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_fallback_used_on_parse_error(self) -> None:
        """
        GIVEN a fallback value and invalid JSON
        WHEN validation fails
        THEN uses the fallback value
        """
        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(model_name="gpt-4", provider="openai")
        fallback = SimpleSchema(value="fallback_value")

        with patch.object(factory, "ainvoke", new_callable=AsyncMock) as mock_ainvoke:
            mock_ainvoke.return_value = AIMessage(content="not valid json")

            result = await factory.ainvoke_validated(
                messages=[HumanMessage(content="Test")],
                schema=SimpleSchema,
                prompt_name="test",
                fallback=fallback,
            )

            assert result.success is False
            assert result.used_fallback is True
            assert result.parsed_output.value == "fallback_value"

    @pytest.mark.asyncio
    async def test_no_fallback_returns_none_output(self) -> None:
        """
        GIVEN no fallback value and invalid JSON
        WHEN validation fails
        THEN parsed_output is None
        """
        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(model_name="gpt-4", provider="openai")

        with patch.object(factory, "ainvoke", new_callable=AsyncMock) as mock_ainvoke:
            mock_ainvoke.return_value = AIMessage(content="invalid")

            result = await factory.ainvoke_validated(
                messages=[HumanMessage(content="Test")],
                schema=SimpleSchema,
                prompt_name="test",
            )

            assert result.success is False
            assert result.parsed_output is None
            assert result.used_fallback is False


@pytest.mark.xdist_group(name="factory_validation_telemetry")
class TestFactoryValidationTelemetry:
    """Integration tests for validation telemetry."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_validation_records_telemetry_on_success(self) -> None:
        """
        GIVEN a successful validation
        WHEN validation completes
        THEN records prompt usage telemetry
        """
        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(model_name="gpt-4", provider="openai")
        valid_response = json.dumps({"value": "test"})

        with (
            patch.object(factory, "ainvoke", new_callable=AsyncMock) as mock_ainvoke,
            patch(
                "mcp_server_langgraph.core.prompts.telemetry.record_prompt_usage"
            ) as mock_telemetry,
        ):
            mock_ainvoke.return_value = AIMessage(content=valid_response)

            await factory.ainvoke_validated(
                messages=[HumanMessage(content="Test")],
                schema=SimpleSchema,
                prompt_name="custom_prompt",
            )

            # Telemetry uses "latest" as default version
            mock_telemetry.assert_called_once_with(
                prompt_name="custom_prompt",
                prompt_version="latest",
            )

    @pytest.mark.asyncio
    async def test_validation_records_metrics_on_failure(self) -> None:
        """
        GIVEN a validation failure
        WHEN validation completes
        THEN records failure metrics
        """
        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(model_name="gpt-4", provider="openai")

        with (
            patch.object(factory, "ainvoke", new_callable=AsyncMock) as mock_ainvoke,
            patch(
                "mcp_server_langgraph.core.prompts.validation._record_validation_metric"
            ) as mock_metric,
        ):
            mock_ainvoke.return_value = AIMessage(content="invalid json")

            await factory.ainvoke_validated(
                messages=[HumanMessage(content="Test")],
                schema=SimpleSchema,
                prompt_name="test",
            )

            # Should record failure metric
            mock_metric.assert_called()


@pytest.mark.xdist_group(name="factory_validation_production_patterns")
class TestFactoryValidationProductionPatterns:
    """Integration tests for production-ready validation patterns."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_router_output_validation(self) -> None:
        """
        GIVEN a RouterOutput schema from orchestration
        WHEN validating router LLM response
        THEN correctly parses orchestration routing decisions
        """
        from typing import Literal

        from pydantic import BaseModel

        from mcp_server_langgraph.core.prompts.validation import validate_output

        router_response = json.dumps({
            "complexity": "complicated",
            "risk": "medium",
            "task_type": "code",
            "tools_needed": ["code_executor", "file_reader"],
            "suggested_orchestrator": "standard",
            "critique_rounds": 2,
            "thinking_budget": "medium",
            "confidence": 0.85,
        })

        # Create a schema matching RouterOutput
        class RouterOutput(BaseModel):
            complexity: Literal["simple", "complicated", "complex"]
            risk: Literal["low", "medium", "high"]
            task_type: str
            tools_needed: list[str]
            suggested_orchestrator: str
            critique_rounds: int = Field(ge=0, le=3)
            thinking_budget: str
            confidence: float = Field(ge=0.0, le=1.0)

        result = validate_output(
            content=router_response,
            schema=RouterOutput,
            prompt_name="orchestration_router",
        )

        assert result.success is True
        assert result.parsed_output.complexity == "complicated"
        assert result.parsed_output.suggested_orchestrator == "standard"

    @pytest.mark.asyncio
    async def test_verification_output_validation(self) -> None:
        """
        GIVEN a VerificationOutput schema
        WHEN validating verification LLM response
        THEN correctly parses quality evaluation scores
        """
        from mcp_server_langgraph.core.prompts.schemas import VerificationOutput
        from mcp_server_langgraph.core.prompts.validation import validate_output

        verification_response = json.dumps({
            "accuracy": 0.9,
            "completeness": 0.85,
            "clarity": 0.88,
            "relevance": 0.92,
            "safety": 1.0,
            "sources": 0.7,
            "overall": 0.87,
            "critical_issues": [],
            "suggestions": ["Add more examples"],
            "requires_refinement": False,
            "feedback": "Good response overall",
        })

        result = validate_output(
            content=verification_response,
            schema=VerificationOutput,
            prompt_name="verification",
        )

        assert result.success is True
        assert result.parsed_output.overall == 0.87
        assert result.parsed_output.requires_refinement is False

    @pytest.mark.asyncio
    async def test_error_analysis_output_validation(self) -> None:
        """
        GIVEN an ErrorAnalysisOutput schema
        WHEN validating error analysis LLM response
        THEN correctly parses error categorization
        """
        from mcp_server_langgraph.core.prompts.schemas import ErrorAnalysisOutput
        from mcp_server_langgraph.core.prompts.validation import validate_output

        # Match the actual ErrorAnalysisOutput schema fields
        error_response = json.dumps({
            "category": "network",  # Required: Literal category
            "subcategory": "timeout",  # Required: More specific classification
            "confidence": 0.85,  # Required: Classification confidence 0.0-1.0
            "root_cause": "Network timeout during API call",  # Required
            "suggestions": [
                {
                    "action": "retry",  # Literal from RecoverySuggestion
                    "label": "Retry with exponential backoff",
                    "estimated_success": 0.8,  # Required: Estimated success probability
                }
            ],
        })

        result = validate_output(
            content=error_response,
            schema=ErrorAnalysisOutput,
            prompt_name="error_analysis",
        )

        assert result.success is True
        assert result.parsed_output.category == "network"
        assert result.parsed_output.confidence == 0.85
