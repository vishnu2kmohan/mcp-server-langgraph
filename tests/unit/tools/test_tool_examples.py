"""
Unit tests for tool input examples feature

Tests the ToolExample model and registry for improving LLM accuracy
with complex tool parameters (72% → 90% improvement per Anthropic research).

TDD: RED phase - these tests define expected behavior before implementation.
"""

import gc

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.tool_examples]


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_tool_example_model")
class TestToolExampleModel:
    """Test suite for ToolExample Pydantic model"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_tool_example_requires_description_and_input(self):
        """GIVEN a ToolExample model
        WHEN instantiated with description and input
        THEN it should store both fields correctly
        """
        from mcp_server_langgraph.tools.examples import ToolExample

        example = ToolExample(
            description="Compound interest calculation",
            input={"expression": "1000 * (1.05) ** 10"},
        )

        assert example.description == "Compound interest calculation"
        assert example.input == {"expression": "1000 * (1.05) ** 10"}

    def test_tool_example_validates_description_is_string(self):
        """GIVEN a ToolExample model
        WHEN instantiated with non-string description
        THEN it should raise ValidationError
        """
        from pydantic import ValidationError

        from mcp_server_langgraph.tools.examples import ToolExample

        with pytest.raises(ValidationError):
            ToolExample(description=123, input={"foo": "bar"})

    def test_tool_example_validates_input_is_dict(self):
        """GIVEN a ToolExample model
        WHEN instantiated with non-dict input
        THEN it should raise ValidationError
        """
        from pydantic import ValidationError

        from mcp_server_langgraph.tools.examples import ToolExample

        with pytest.raises(ValidationError):
            ToolExample(description="test", input="not a dict")

    def test_tool_example_input_accepts_any_value_types(self):
        """GIVEN a ToolExample model
        WHEN input contains various value types (str, int, list, dict, bool)
        THEN it should accept all of them
        """
        from mcp_server_langgraph.tools.examples import ToolExample

        example = ToolExample(
            description="Complex input",
            input={
                "string_param": "value",
                "int_param": 42,
                "bool_param": True,
                "list_param": [1, 2, 3],
                "nested_param": {"key": "value"},
            },
        )

        assert example.input["string_param"] == "value"
        assert example.input["int_param"] == 42
        assert example.input["bool_param"] is True


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_tool_examples_registry")
class TestToolExamplesRegistry:
    """Test suite for TOOL_EXAMPLES registry"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_registry_contains_calculator_examples(self):
        """GIVEN the TOOL_EXAMPLES registry
        WHEN checking for calculator examples
        THEN it should contain at least one example
        """
        from mcp_server_langgraph.tools.examples import TOOL_EXAMPLES

        assert "calculator" in TOOL_EXAMPLES
        assert len(TOOL_EXAMPLES["calculator"]) >= 1

    def test_registry_calculator_example_has_expression_param(self):
        """GIVEN calculator examples in registry
        WHEN examining the first example
        THEN it should have an 'expression' parameter
        """
        from mcp_server_langgraph.tools.examples import TOOL_EXAMPLES

        calc_examples = TOOL_EXAMPLES["calculator"]
        assert "expression" in calc_examples[0].input

    def test_registry_contains_web_search_examples(self):
        """GIVEN the TOOL_EXAMPLES registry
        WHEN checking for web_search examples
        THEN it should contain at least one example
        """
        from mcp_server_langgraph.tools.examples import TOOL_EXAMPLES

        assert "web_search" in TOOL_EXAMPLES
        assert len(TOOL_EXAMPLES["web_search"]) >= 1

    def test_registry_returns_empty_list_for_unknown_tool(self):
        """GIVEN the TOOL_EXAMPLES registry
        WHEN querying for a non-existent tool
        THEN it should return empty list
        """
        from mcp_server_langgraph.tools.examples import get_examples_for_tool

        examples = get_examples_for_tool("non_existent_tool")
        assert examples == []


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_get_examples_for_tool")
class TestGetExamplesForTool:
    """Test suite for get_examples_for_tool function"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_get_examples_returns_list_of_tool_examples(self):
        """GIVEN a tool name with registered examples
        WHEN calling get_examples_for_tool
        THEN it should return a list of ToolExample objects
        """
        from mcp_server_langgraph.tools.examples import ToolExample, get_examples_for_tool

        examples = get_examples_for_tool("calculator")

        assert isinstance(examples, list)
        assert all(isinstance(ex, ToolExample) for ex in examples)

    def test_get_examples_returns_copy_not_reference(self):
        """GIVEN a tool name with registered examples
        WHEN calling get_examples_for_tool twice
        THEN modifying one result should not affect the other
        """
        from mcp_server_langgraph.tools.examples import get_examples_for_tool

        examples1 = get_examples_for_tool("calculator")
        examples2 = get_examples_for_tool("calculator")

        # Modify first result
        if examples1:
            examples1.pop()

        # Second result should be unchanged
        assert len(examples2) > len(examples1)


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_example_schema_validation")
class TestExampleSchemaValidation:
    """Test suite for validating examples against tool schemas"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_validate_examples_against_tool_schema_passes_for_valid(self):
        """GIVEN a tool with registered examples
        WHEN validating examples against the tool's schema
        THEN valid examples should pass validation
        """
        from mcp_server_langgraph.tools.examples import validate_examples_for_tool

        # Should not raise for valid examples
        errors = validate_examples_for_tool("calculator")
        assert errors == []

    def test_validate_examples_detects_missing_required_params(self):
        """GIVEN an example missing a required parameter
        WHEN validating against tool schema
        THEN it should report the missing parameter
        """
        from mcp_server_langgraph.tools.examples import ToolExample, validate_example_against_schema

        # Calculator requires 'expression' parameter
        bad_example = ToolExample(description="Missing expression", input={})

        errors = validate_example_against_schema("calculator", bad_example)
        assert len(errors) > 0
        assert "expression" in errors[0].lower() or "required" in errors[0].lower()


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_examples_serialization")
class TestExamplesSerialization:
    """Test suite for serializing examples for MCP tools/list response"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_serialize_examples_returns_list_of_dicts(self):
        """GIVEN examples for a tool
        WHEN serializing for MCP response
        THEN it should return a list of dictionaries
        """
        from mcp_server_langgraph.tools.examples import serialize_examples_for_tool

        serialized = serialize_examples_for_tool("calculator")

        assert isinstance(serialized, list)
        assert all(isinstance(ex, dict) for ex in serialized)

    def test_serialized_example_has_description_and_input(self):
        """GIVEN serialized examples
        WHEN examining the structure
        THEN each should have 'description' and 'input' keys
        """
        from mcp_server_langgraph.tools.examples import serialize_examples_for_tool

        serialized = serialize_examples_for_tool("calculator")

        if serialized:  # Only test if examples exist
            for example in serialized:
                assert "description" in example
                assert "input" in example


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_register_example")
class TestRegisterExample:
    """Test suite for dynamically registering examples"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_register_example_adds_to_registry(self):
        """GIVEN a new tool example
        WHEN registering it for a tool
        THEN it should appear in the registry
        """
        from mcp_server_langgraph.tools.examples import (
            ToolExample,
            get_examples_for_tool,
            register_example,
        )

        # Use a unique tool name to avoid polluting other tests
        tool_name = "test_register_tool_unique"

        example = ToolExample(description="Test example", input={"param": "value"})

        register_example(tool_name, example)

        examples = get_examples_for_tool(tool_name)
        assert len(examples) >= 1
        assert any(ex.description == "Test example" for ex in examples)

    def test_register_multiple_examples_for_same_tool(self):
        """GIVEN a tool with no examples
        WHEN registering multiple examples
        THEN all should be retrievable
        """
        from mcp_server_langgraph.tools.examples import (
            ToolExample,
            get_examples_for_tool,
            register_example,
        )

        tool_name = "test_multi_example_tool"

        example1 = ToolExample(description="Example 1", input={"a": 1})
        example2 = ToolExample(description="Example 2", input={"b": 2})

        register_example(tool_name, example1)
        register_example(tool_name, example2)

        examples = get_examples_for_tool(tool_name)
        assert len(examples) >= 2
