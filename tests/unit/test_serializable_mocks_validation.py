"""
Test Suite for Serializable Mock Validation

This test module ensures that serializable mocks used in performance regression
tests maintain compatibility with LangGraph's checkpoint serialization system.

These tests prevent the following classes of issues:
1. Mixing Python @dataclass with Pydantic BaseModel (incompatible)
2. Missing Pydantic Field definitions for mutable defaults
3. Serialization/deserialization failures in LangGraph checkpoints

Test-Driven Development (TDD) Approach:
- RED: These tests would fail if @dataclass is used with BaseChatModel
- GREEN: Tests pass with proper Pydantic Field usage
- REFACTOR: Validates best practices for mock object design
"""

import gc
import inspect
from dataclasses import is_dataclass
from typing import get_type_hints

import pytest
from pydantic import BaseModel

from tests.fixtures.serializable_mocks import SerializableLLMMock, SerializableToolMock


# Mark as unit test to ensure it runs in CI
pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="testserializablellmmockvalidation")
class TestSerializableLLMMockValidation:
    """
    Validation tests for SerializableLLMMock to prevent Pydantic conflicts.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_serializable_llm_mock_not_using_dataclass(self):
        """
        CRITICAL: Ensure SerializableLLMMock does NOT use @dataclass decorator.

        Background:
        - BaseChatModel (from LangChain) inherits from Pydantic BaseModel
        - Python @dataclass and Pydantic BaseModel are incompatible
        - Mixing them causes: ValueError: mutable default ... use default_factory

        This test prevents regression to the bug found in run 19148140358.
        """
        # Verify SerializableLLMMock is NOT a dataclass
        assert not is_dataclass(SerializableLLMMock), (
            "SerializableLLMMock must NOT use @dataclass decorator! "
            "It inherits from BaseChatModel (Pydantic BaseModel) which is incompatible with @dataclass. "
            "Use Pydantic Field() instead of dataclass field()."
        )

    def test_serializable_llm_mock_is_pydantic_model(self):
        """
        Ensure SerializableLLMMock properly inherits from Pydantic BaseModel.
        """
        # Verify it's a Pydantic model through BaseChatModel
        assert issubclass(
            SerializableLLMMock, BaseModel
        ), "SerializableLLMMock must inherit from BaseChatModel (which is a Pydantic BaseModel)"

    def test_serializable_llm_mock_uses_pydantic_fields(self):
        """
        Validate that SerializableLLMMock uses Pydantic Field() for all attributes.
        """
        # Get the class annotations
        annotations = get_type_hints(SerializableLLMMock)

        # Check that key fields exist
        assert "responses" in annotations, "responses field must be defined"
        assert "delay_seconds" in annotations, "delay_seconds field must be defined"
        assert "model_name" in annotations, "model_name field must be defined"

        # Verify model has Pydantic model fields
        assert hasattr(SerializableLLMMock, "model_fields"), "SerializableLLMMock must have Pydantic model_fields"

    def test_serializable_llm_mock_instantiation(self):
        """
        Test that SerializableLLMMock can be instantiated without errors.

        This would fail if there were Pydantic/dataclass conflicts.
        """
        # Default instantiation
        mock = SerializableLLMMock()
        assert mock is not None
        assert mock.responses == ["Mock LLM response"]
        assert mock.delay_seconds == 0.0
        assert mock.model_name == "mock-llm"

        # Custom instantiation
        custom_mock = SerializableLLMMock(responses=["Response 1", "Response 2"], delay_seconds=0.5, model_name="custom-mock")
        assert custom_mock.responses == ["Response 1", "Response 2"]
        assert custom_mock.delay_seconds == 0.5
        assert custom_mock.model_name == "custom-mock"

    def test_serializable_llm_mock_serialization(self):
        """
        Test that SerializableLLMMock can be serialized/deserialized.

        This is critical for LangGraph checkpoint system.
        """
        mock = SerializableLLMMock(responses=["Test response"], delay_seconds=0.1)

        # Test pickle serialization (used by LangGraph)
        import pickle

        serialized = pickle.dumps(mock)  # nosec B301 - intentional pickle use in test
        deserialized = pickle.loads(serialized)  # nosec B301 - controlled test data

        assert deserialized.responses == mock.responses
        assert deserialized.delay_seconds == mock.delay_seconds
        assert deserialized.model_name == mock.model_name

    def test_serializable_llm_mock_response_generation(self):
        """
        Test that SerializableLLMMock generates responses correctly.
        """
        from langchain_core.messages import HumanMessage

        mock = SerializableLLMMock(responses=["Response 1", "Response 2"])

        # Test synchronous generation
        result = mock._generate([HumanMessage(content="test")])
        assert result.generations[0].message.content == "Response 1"

        # Test response cycling
        result2 = mock._generate([HumanMessage(content="test2")])
        assert result2.generations[0].message.content == "Response 2"

        result3 = mock._generate([HumanMessage(content="test3")])
        assert result3.generations[0].message.content == "Response 1"  # Cycles back

    @pytest.mark.asyncio
    async def test_serializable_llm_mock_async_generation(self):
        """
        Test async response generation.
        """
        from langchain_core.messages import HumanMessage

        mock = SerializableLLMMock(responses=["Async response"])

        result = await mock._agenerate([HumanMessage(content="test")])
        assert result.generations[0].message.content == "Async response"

    def test_serializable_llm_mock_call_counting(self):
        """
        Test that call_count tracking works correctly.
        """
        from langchain_core.messages import HumanMessage

        mock = SerializableLLMMock()

        assert mock.call_count == 0

        mock._generate([HumanMessage(content="test1")])
        assert mock.call_count == 1

        mock._generate([HumanMessage(content="test2")])
        assert mock.call_count == 2

        mock.reset()
        assert mock.call_count == 0

    def test_serializable_llm_mock_reset(self):
        """
        Test reset functionality.
        """
        from langchain_core.messages import HumanMessage

        mock = SerializableLLMMock(responses=["R1", "R2"])

        # Generate some responses
        mock._generate([HumanMessage(content="test")])
        mock._generate([HumanMessage(content="test")])

        assert mock.call_count == 2
        assert mock._current_index == 2

        # Reset
        mock.reset()

        assert mock.call_count == 0
        assert mock._current_index == 0


@pytest.mark.xdist_group(name="testserializabletoolmockvalidation")
class TestSerializableToolMockValidation:
    """
    Validation tests for SerializableToolMock.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_serializable_tool_mock_is_plain_class(self):
        """
        SerializableToolMock can use @dataclass since it doesn't inherit from Pydantic.
        """
        # This is fine - plain Python class can use @dataclass
        assert is_dataclass(SerializableToolMock), "SerializableToolMock should use @dataclass"

    def test_serializable_tool_mock_instantiation(self):
        """
        Test tool mock instantiation.
        """
        tool = SerializableToolMock()
        assert tool.name == "mock_tool"
        assert tool.return_value == "Mock tool result"
        assert tool.execution_time == 0.0
        assert tool.call_count == 0

    def test_serializable_tool_mock_invocation(self):
        """
        Test tool invocation and call tracking.
        """
        tool = SerializableToolMock(return_value="test_result")

        result = tool(arg1="value1", arg2="value2")

        assert result == "test_result"
        assert tool.call_count == 1
        assert tool.call_args[0] == {"arg1": "value1", "arg2": "value2"}

    @pytest.mark.asyncio
    async def test_serializable_tool_mock_async_invocation(self):
        """
        Test async tool invocation.
        """
        tool = SerializableToolMock(return_value="async_result")

        result = await tool.ainvoke(arg="value")

        assert result == "async_result"
        assert tool.call_count == 1


@pytest.mark.xdist_group(name="testmockcompatibilityguards")
class TestMockCompatibilityGuards:
    """
    Guard tests to prevent incompatible patterns in mock objects.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_no_dataclass_on_pydantic_subclasses(self):
        """
        META-TEST: Scan all test fixtures for @dataclass on Pydantic subclasses.

        This test prevents the entire class of bugs where @dataclass is
        accidentally mixed with Pydantic BaseModel inheritance.
        """
        from tests.fixtures import serializable_mocks

        # Get all classes from the module
        for name, obj in inspect.getmembers(serializable_mocks, inspect.isclass):
            # Skip imported classes
            if obj.__module__ != serializable_mocks.__name__:
                continue

            # If it's a Pydantic model, it MUST NOT be a dataclass
            if issubclass(obj, BaseModel):
                assert not is_dataclass(obj), (
                    f"{name} inherits from Pydantic BaseModel but uses @dataclass! "
                    f"This is incompatible. Use Pydantic Field() instead."
                )

    def test_pydantic_mocks_have_required_methods(self):
        """
        Validate that Pydantic-based mocks implement required LangChain methods.
        """
        mock = SerializableLLMMock()

        # Check for required LangChain methods
        assert hasattr(mock, "_generate"), "Must implement _generate"
        assert hasattr(mock, "_agenerate"), "Must implement _agenerate"
        assert hasattr(mock, "_llm_type"), "Must implement _llm_type property"

        # Verify they're callable/accessible
        assert callable(mock._generate)
        assert callable(mock._agenerate)
        assert isinstance(mock._llm_type, str)
