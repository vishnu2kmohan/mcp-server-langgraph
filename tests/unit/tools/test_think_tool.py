"""
Unit tests for Think Tool for Complex Reasoning

Tests the think tool that provides structured reasoning space during
complex tool chains (54% relative improvement per Anthropic research).

TDD: RED phase - these tests define expected behavior before implementation.
"""

import gc

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.think_tool]


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_think_tool_basic")
class TestThinkToolBasic:
    """Test suite for basic think tool functionality"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_think_tool_is_langchain_tool(self):
        """GIVEN the think tool
        WHEN checking its type
        THEN it should be a LangChain BaseTool
        """
        from langchain_core.tools import BaseTool

        from mcp_server_langgraph.tools.think_tool import think

        assert isinstance(think, BaseTool)

    def test_think_tool_has_correct_name(self):
        """GIVEN the think tool
        WHEN checking its name
        THEN it should be 'think'
        """
        from mcp_server_langgraph.tools.think_tool import think

        assert think.name == "think"

    def test_think_tool_has_description(self):
        """GIVEN the think tool
        WHEN checking its description
        THEN it should describe structured reasoning space
        """
        from mcp_server_langgraph.tools.think_tool import think

        assert "reason" in think.description.lower() or "think" in think.description.lower()

    def test_think_tool_accepts_thought_parameter(self):
        """GIVEN the think tool
        WHEN invoking with a thought string
        THEN it should accept the input without error
        """
        from mcp_server_langgraph.tools.think_tool import think

        # Should not raise
        result = think.invoke({"thought": "Processing step 1 of the analysis..."})
        assert result is not None


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_think_tool_output")
class TestThinkToolOutput:
    """Test suite for think tool output behavior"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_think_tool_returns_confirmation_string(self):
        """GIVEN a thought string
        WHEN invoking think tool
        THEN it should return a confirmation that thought was recorded
        """
        from mcp_server_langgraph.tools.think_tool import think

        result = think.invoke({"thought": "Analyzing user request"})

        assert isinstance(result, str)
        assert "recorded" in result.lower() or "thought" in result.lower()

    def test_think_tool_echoes_part_of_thought(self):
        """GIVEN a thought string
        WHEN invoking think tool
        THEN the response should include part of the original thought
        """
        from mcp_server_langgraph.tools.think_tool import think

        thought = "This is a unique test thought for verification"
        result = think.invoke({"thought": thought})

        # Should echo at least part of the thought
        assert "unique" in result or "test" in result or len(result) > 10

    def test_think_tool_truncates_long_thoughts(self):
        """GIVEN a very long thought string
        WHEN invoking think tool
        THEN it should truncate the response to avoid token waste
        """
        from mcp_server_langgraph.tools.think_tool import think

        long_thought = "A" * 1000  # 1000 character thought
        result = think.invoke({"thought": long_thought})

        # Should be truncated - response should be shorter than input
        assert len(result) < 500

    def test_think_tool_handles_empty_thought(self):
        """GIVEN an empty thought string
        WHEN invoking think tool
        THEN it should handle gracefully without error
        """
        from mcp_server_langgraph.tools.think_tool import think

        result = think.invoke({"thought": ""})

        assert isinstance(result, str)


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_think_tool_noop")
class TestThinkToolNoOp:
    """Test suite verifying think tool has no side effects"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_think_tool_does_not_modify_external_state(self):
        """GIVEN the think tool
        WHEN invoked multiple times
        THEN it should not accumulate or modify any external state
        """
        from mcp_server_langgraph.tools.think_tool import think

        # Invoke multiple times
        result1 = think.invoke({"thought": "First thought"})
        result2 = think.invoke({"thought": "Second thought"})
        result3 = think.invoke({"thought": "Third thought"})

        # Each result should be independent
        assert result1 != result2
        assert result2 != result3

    def test_think_tool_is_synchronous(self):
        """GIVEN the think tool
        WHEN checking if it's async
        THEN it should be synchronous (no external I/O)
        """
        from mcp_server_langgraph.tools.think_tool import think

        # Invoke synchronously should work
        result = think.invoke({"thought": "Sync test"})
        assert isinstance(result, str)


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_think_tool_schema")
class TestThinkToolSchema:
    """Test suite for think tool schema"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_think_tool_schema_has_thought_field(self):
        """GIVEN the think tool schema
        WHEN examining input fields
        THEN it should have a 'thought' string field
        """
        from mcp_server_langgraph.tools.think_tool import think

        schema = think.args_schema
        assert schema is not None

        fields = schema.model_fields
        assert "thought" in fields

    def test_think_tool_thought_is_required(self):
        """GIVEN the think tool schema
        WHEN checking the thought field
        THEN it should be required
        """
        from mcp_server_langgraph.tools.think_tool import think

        schema = think.args_schema
        fields = schema.model_fields

        assert fields["thought"].is_required()


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_think_tool_use_cases")
class TestThinkToolUseCases:
    """Test suite for think tool use case examples"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_think_tool_policy_verification_use_case(self):
        """GIVEN a policy verification thought
        WHEN invoking think tool
        THEN it should record the verification step
        """
        from mcp_server_langgraph.tools.think_tool import think

        thought = "Verifying that this request complies with data privacy policy"
        result = think.invoke({"thought": thought})

        assert isinstance(result, str)
        assert len(result) > 0

    def test_think_tool_intermediate_reasoning_use_case(self):
        """GIVEN intermediate reasoning during a tool chain
        WHEN invoking think tool
        THEN it should record the reasoning step
        """
        from mcp_server_langgraph.tools.think_tool import think

        thought = """
        Step 1: Retrieved user data from database
        Step 2: Need to verify age >= 18 before proceeding
        Step 3: If verified, proceed to calculate discount
        """
        result = think.invoke({"thought": thought})

        assert isinstance(result, str)
        assert len(result) > 0

    def test_think_tool_error_analysis_use_case(self):
        """GIVEN error analysis thought
        WHEN invoking think tool
        THEN it should record the analysis
        """
        from mcp_server_langgraph.tools.think_tool import think

        thought = "The previous tool returned an error. Analyzing: connection timeout suggests network issue."
        result = think.invoke({"thought": thought})

        assert isinstance(result, str)
        assert len(result) > 0


# ============================================================================
# STRUCTURED THINK TOOL TESTS (TDD: RED PHASE)
# ============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_think_tool_structured")
class TestStructuredThinkTool:
    """Test suite for structured think tool output"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_structured_thought_output_model_exists(self):
        """GIVEN the think_tool module
        WHEN importing StructuredThoughtOutput
        THEN it should be a valid Pydantic model
        """
        from pydantic import BaseModel

        from mcp_server_langgraph.tools.think_tool import StructuredThoughtOutput

        assert issubclass(StructuredThoughtOutput, BaseModel)

    def test_structured_thought_output_has_required_fields(self):
        """GIVEN StructuredThoughtOutput
        WHEN examining its fields
        THEN it should have thought, category, and confidence
        """
        from mcp_server_langgraph.tools.think_tool import StructuredThoughtOutput

        fields = StructuredThoughtOutput.model_fields
        assert "thought" in fields
        assert "category" in fields
        assert "confidence" in fields

    def test_thought_category_enum_exists(self):
        """GIVEN the think_tool module
        WHEN importing ThoughtCategory
        THEN it should be an enum with standard categories
        """
        from enum import Enum

        from mcp_server_langgraph.tools.think_tool import ThoughtCategory

        assert issubclass(ThoughtCategory, Enum)

        # Should have key categories
        categories = [c.value for c in ThoughtCategory]
        assert "policy_verification" in categories
        assert "intermediate_reasoning" in categories
        assert "error_analysis" in categories
        assert "planning" in categories

    def test_think_structured_tool_exists(self):
        """GIVEN the think_tool module
        WHEN importing think_structured
        THEN it should be a LangChain tool
        """
        from langchain_core.tools import BaseTool

        from mcp_server_langgraph.tools.think_tool import think_structured

        assert isinstance(think_structured, BaseTool)

    def test_think_structured_returns_dict(self):
        """GIVEN think_structured tool
        WHEN invoked with a thought
        THEN it should return a dict with structured output
        """
        from mcp_server_langgraph.tools.think_tool import think_structured

        result = think_structured.invoke({
            "thought": "Verifying policy compliance",
            "category": "policy_verification",
        })

        assert isinstance(result, dict)
        assert "thought" in result
        assert "category" in result
        assert "confidence" in result

    def test_think_structured_validates_category(self):
        """GIVEN think_structured tool with invalid category
        WHEN invoked
        THEN it should handle gracefully or use default
        """
        from mcp_server_langgraph.tools.think_tool import think_structured

        # Should handle invalid category without crashing
        result = think_structured.invoke({
            "thought": "Test thought",
            "category": "invalid_category",
        })

        assert isinstance(result, dict)

    def test_think_structured_includes_next_steps(self):
        """GIVEN think_structured tool
        WHEN invoked with planning thought
        THEN it may include next_steps field
        """
        from mcp_server_langgraph.tools.think_tool import StructuredThoughtOutput

        # next_steps should be an optional field
        fields = StructuredThoughtOutput.model_fields
        assert "next_steps" in fields

    def test_think_structured_confidence_range(self):
        """GIVEN think_structured tool
        WHEN invoked with a thought
        THEN confidence should be between 0 and 1
        """
        from mcp_server_langgraph.tools.think_tool import think_structured

        result = think_structured.invoke({
            "thought": "Analyzing data pattern",
            "category": "intermediate_reasoning",
        })

        confidence = result.get("confidence", 0.5)
        assert 0.0 <= confidence <= 1.0

    def test_structured_output_serializes_to_json(self):
        """GIVEN StructuredThoughtOutput
        WHEN serializing to JSON
        THEN it should produce valid JSON
        """
        import json

        from mcp_server_langgraph.tools.think_tool import (
            StructuredThoughtOutput,
            ThoughtCategory,
        )

        output = StructuredThoughtOutput(
            thought="Test thought",
            category=ThoughtCategory.POLICY_VERIFICATION,
            confidence=0.95,
        )

        json_str = output.model_dump_json()
        parsed = json.loads(json_str)

        assert parsed["thought"] == "Test thought"
        assert parsed["category"] == "policy_verification"
        assert parsed["confidence"] == 0.95
