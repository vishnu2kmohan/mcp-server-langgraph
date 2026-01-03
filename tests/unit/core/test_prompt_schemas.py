"""
Unit tests for prompt output schemas.

Tests Pydantic models for structured prompt outputs:
- ResponseOutput: Agentic response generation
- VerificationOutput: LLM-as-judge quality evaluation
- ErrorAnalysisOutput: Error analysis and recovery suggestions
- WidgetConfigOutput: GenUI widget configuration

TDD: These tests are written FIRST before implementation.
"""

import gc
import json

import pytest
from pydantic import ValidationError

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="test_prompt_schemas")
class TestResponseOutputSchema:
    """Test ResponseOutput Pydantic schema."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_response_output_exists(self) -> None:
        """Test ResponseOutput schema is defined."""
        from mcp_server_langgraph.core.prompts.schemas import ResponseOutput

        assert ResponseOutput is not None

    def test_response_output_valid_minimal(self) -> None:
        """Test ResponseOutput with minimal required fields."""
        from mcp_server_langgraph.core.prompts.schemas import ResponseOutput

        output = ResponseOutput(
            content="Hello, how can I help?",
            confidence=0.95,
        )
        assert output.content == "Hello, how can I help?"
        assert output.confidence == 0.95
        assert output.requires_clarification is False  # default

    def test_response_output_valid_with_clarification(self) -> None:
        """Test ResponseOutput with clarification request."""
        from mcp_server_langgraph.core.prompts.schemas import ResponseOutput

        output = ResponseOutput(
            content="I need more information.",
            confidence=0.6,
            requires_clarification=True,
            clarification_question="What programming language are you using?",
        )
        assert output.requires_clarification is True
        assert output.clarification_question is not None

    def test_response_output_confidence_clamped_max(self) -> None:
        """Test confidence > 1.0 raises ValidationError."""
        from mcp_server_langgraph.core.prompts.schemas import ResponseOutput

        with pytest.raises(ValidationError):
            ResponseOutput(content="test", confidence=1.5)

    def test_response_output_confidence_clamped_min(self) -> None:
        """Test confidence < 0.0 raises ValidationError."""
        from mcp_server_langgraph.core.prompts.schemas import ResponseOutput

        with pytest.raises(ValidationError):
            ResponseOutput(content="test", confidence=-0.1)


@pytest.mark.xdist_group(name="test_prompt_schemas")
class TestVerificationOutputSchema:
    """Test VerificationOutput Pydantic schema."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_verification_output_exists(self) -> None:
        """Test VerificationOutput schema is defined."""
        from mcp_server_langgraph.core.prompts.schemas import VerificationOutput

        assert VerificationOutput is not None

    def test_verification_output_valid(self) -> None:
        """Test valid VerificationOutput."""
        from mcp_server_langgraph.core.prompts.schemas import VerificationOutput

        output = VerificationOutput(
            accuracy=0.9,
            completeness=0.85,
            clarity=0.95,
            relevance=0.88,
            safety=1.0,
            sources=0.7,
            overall=0.88,
            critical_issues=[],
            suggestions=["Consider adding more examples"],
            requires_refinement=False,
            feedback="Response is accurate and complete.",
        )
        assert output.overall == 0.88
        assert output.requires_refinement is False

    def test_verification_output_score_clamped_max(self) -> None:
        """Test score > 1.0 raises ValidationError."""
        from mcp_server_langgraph.core.prompts.schemas import VerificationOutput

        with pytest.raises(ValidationError):
            VerificationOutput(
                accuracy=1.5,  # Invalid
                completeness=0.85,
                clarity=0.95,
                relevance=0.88,
                safety=1.0,
                sources=0.7,
                overall=0.88,
                requires_refinement=False,
                feedback="test",
            )


@pytest.mark.xdist_group(name="test_prompt_schemas")
class TestErrorAnalysisOutputSchema:
    """Test ErrorAnalysisOutput Pydantic schema."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_error_analysis_output_exists(self) -> None:
        """Test ErrorAnalysisOutput schema is defined."""
        from mcp_server_langgraph.core.prompts.schemas import ErrorAnalysisOutput

        assert ErrorAnalysisOutput is not None

    def test_error_analysis_output_valid(self) -> None:
        """Test valid ErrorAnalysisOutput."""
        from mcp_server_langgraph.core.prompts.schemas import (
            ErrorAnalysisOutput,
            RecoverySuggestion,
        )

        output = ErrorAnalysisOutput(
            category="network",
            subcategory="connection_timeout",
            confidence=0.85,
            root_cause="Server took too long to respond",
            suggestions=[
                RecoverySuggestion(
                    action="retry",
                    label="Try again",
                    guidance="Wait a moment and try again",
                    estimated_success=0.7,
                )
            ],
        )
        assert output.category == "network"
        assert len(output.suggestions) == 1

    def test_error_analysis_output_invalid_category(self) -> None:
        """Test invalid category raises ValidationError."""
        from mcp_server_langgraph.core.prompts.schemas import ErrorAnalysisOutput

        with pytest.raises(ValidationError):
            ErrorAnalysisOutput(
                category="invalid_category",  # Not in allowed list
                subcategory="test",
                confidence=0.8,
                root_cause="test",
                suggestions=[],
            )


@pytest.mark.xdist_group(name="test_prompt_schemas")
class TestWidgetConfigOutputSchema:
    """Test WidgetConfigOutput Pydantic schema."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_widget_config_output_exists(self) -> None:
        """Test WidgetConfigOutput schema is defined."""
        from mcp_server_langgraph.core.prompts.schemas import WidgetConfigOutput

        assert WidgetConfigOutput is not None

    def test_widget_config_output_chart(self) -> None:
        """Test valid chart widget configuration."""
        from mcp_server_langgraph.core.prompts.schemas import WidgetConfigOutput

        output = WidgetConfigOutput(
            widget_type="chart",
            title="Sales Data",
            data={"labels": ["Q1", "Q2", "Q3"], "values": [100, 150, 200]},
            confidence=0.9,
        )
        assert output.widget_type == "chart"
        assert output.title == "Sales Data"

    def test_widget_config_output_invalid_type(self) -> None:
        """Test invalid widget_type raises ValidationError."""
        from mcp_server_langgraph.core.prompts.schemas import WidgetConfigOutput

        with pytest.raises(ValidationError):
            WidgetConfigOutput(
                widget_type="invalid_type",  # Not chart|table|text
                title="Test",
                data={},
                confidence=0.9,
            )


@pytest.mark.xdist_group(name="test_prompt_schemas")
class TestSchemaJSONParsing:
    """Test schema JSON parsing and serialization."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_response_output_from_json(self) -> None:
        """Test ResponseOutput parses from JSON."""
        from mcp_server_langgraph.core.prompts.schemas import ResponseOutput

        json_str = json.dumps(
            {
                "content": "Hello world",
                "confidence": 0.9,
                "requires_clarification": False,
                "sources": ["doc1.md", "doc2.md"],
            }
        )
        data = json.loads(json_str)
        output = ResponseOutput(**data)
        assert output.content == "Hello world"
        assert output.sources == ["doc1.md", "doc2.md"]

    def test_verification_output_to_json(self) -> None:
        """Test VerificationOutput serializes to JSON."""
        from mcp_server_langgraph.core.prompts.schemas import VerificationOutput

        output = VerificationOutput(
            accuracy=0.9,
            completeness=0.85,
            clarity=0.95,
            relevance=0.88,
            safety=1.0,
            sources=0.7,
            overall=0.88,
            critical_issues=[],
            suggestions=[],
            requires_refinement=False,
            feedback="Good response",
        )
        json_str = output.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["overall"] == 0.88
        assert parsed["requires_refinement"] is False
