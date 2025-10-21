"""
Unit tests for calculator tools

Tests arithmetic operations and expression evaluation.
"""

import pytest

from mcp_server_langgraph.tools.calculator_tools import add, calculator, divide, multiply, subtract


@pytest.mark.unit
class TestCalculatorTool:
    """Test suite for calculator tool"""

    def test_calculator_simple_addition(self):
        """Test simple addition expression"""
        result = calculator.invoke({"expression": "2 + 2"})
        assert result == "4.0"

    def test_calculator_complex_expression(self):
        """Test complex mathematical expression"""
        result = calculator.invoke({"expression": "(10 * 3) - 5"})
        assert result == "25.0"

    def test_calculator_division(self):
        """Test division expression"""
        result = calculator.invoke({"expression": "8 / 2"})
        assert result == "4.0"

    def test_calculator_power(self):
        """Test exponentiation"""
        result = calculator.invoke({"expression": "2 ** 3"})
        assert result == "8.0"

    def test_calculator_modulo(self):
        """Test modulo operation"""
        result = calculator.invoke({"expression": "10 % 3"})
        assert result == "1.0"

    def test_calculator_negative_numbers(self):
        """Test negative number handling"""
        result = calculator.invoke({"expression": "-5 + 3"})
        assert result == "-2.0"

    def test_calculator_parentheses(self):
        """Test parentheses precedence"""
        result = calculator.invoke({"expression": "(2 + 3) * 4"})
        assert result == "20.0"

    def test_calculator_invalid_expression(self):
        """Test error handling for invalid expression"""
        result = calculator.invoke({"expression": "2 +"})
        assert "Error" in result

    def test_calculator_unsafe_operation(self):
        """Test security - should reject unsafe operations"""
        result = calculator.invoke({"expression": "import os"})
        assert "Error" in result

    def test_calculator_division_by_zero(self):
        """Test division by zero handling"""
        result = calculator.invoke({"expression": "5 / 0"})
        assert "Error" in result


@pytest.mark.unit
class TestAddTool:
    """Test suite for add tool"""

    def test_add_positive_numbers(self):
        """Test adding two positive numbers"""
        result = add.invoke({"a": 5, "b": 3})
        assert result == "8.0"

    def test_add_negative_numbers(self):
        """Test adding negative numbers"""
        result = add.invoke({"a": -5, "b": -3})
        assert result == "-8.0"

    def test_add_mixed_signs(self):
        """Test adding numbers with different signs"""
        result = add.invoke({"a": 10, "b": -3})
        assert result == "7.0"

    def test_add_zero(self):
        """Test adding zero"""
        result = add.invoke({"a": 5, "b": 0})
        assert result == "5.0"

    def test_add_floats(self):
        """Test adding floating point numbers"""
        result = add.invoke({"a": 2.5, "b": 3.7})
        assert float(result) == pytest.approx(6.2)


@pytest.mark.unit
class TestSubtractTool:
    """Test suite for subtract tool"""

    def test_subtract_positive_numbers(self):
        """Test subtracting positive numbers"""
        result = subtract.invoke({"a": 10, "b": 3})
        assert result == "7.0"

    def test_subtract_negative_result(self):
        """Test subtraction resulting in negative"""
        result = subtract.invoke({"a": 3, "b": 10})
        assert result == "-7.0"

    def test_subtract_zero(self):
        """Test subtracting zero"""
        result = subtract.invoke({"a": 5, "b": 0})
        assert result == "5.0"


@pytest.mark.unit
class TestMultiplyTool:
    """Test suite for multiply tool"""

    def test_multiply_positive_numbers(self):
        """Test multiplying positive numbers"""
        result = multiply.invoke({"a": 5, "b": 3})
        assert result == "15.0"

    def test_multiply_by_zero(self):
        """Test multiplying by zero"""
        result = multiply.invoke({"a": 5, "b": 0})
        assert result == "0.0"

    def test_multiply_negative_numbers(self):
        """Test multiplying negative numbers"""
        result = multiply.invoke({"a": -5, "b": -3})
        assert result == "15.0"

    def test_multiply_mixed_signs(self):
        """Test multiplying numbers with different signs"""
        result = multiply.invoke({"a": 5, "b": -3})
        assert result == "-15.0"


@pytest.mark.unit
class TestDivideTool:
    """Test suite for divide tool"""

    def test_divide_positive_numbers(self):
        """Test dividing positive numbers"""
        result = divide.invoke({"a": 10, "b": 2})
        assert result == "5.0"

    def test_divide_with_remainder(self):
        """Test division with remainder"""
        result = divide.invoke({"a": 10, "b": 3})
        assert float(result) == pytest.approx(3.333333, rel=1e-5)

    def test_divide_by_zero(self):
        """Test division by zero error handling"""
        result = divide.invoke({"a": 10, "b": 0})
        assert result == "Error: Division by zero"

    def test_divide_zero_by_number(self):
        """Test dividing zero"""
        result = divide.invoke({"a": 0, "b": 5})
        assert result == "0.0"

    def test_divide_negative_numbers(self):
        """Test dividing negative numbers"""
        result = divide.invoke({"a": -10, "b": -2})
        assert result == "5.0"


@pytest.mark.unit
class TestToolSchemas:
    """Test tool schema generation"""

    def test_calculator_has_schema(self):
        """Test that calculator tool has proper schema"""
        assert calculator.name == "calculator"
        assert calculator.description is not None
        assert "expression" in str(calculator.args_schema.model_json_schema())

    def test_add_has_schema(self):
        """Test that add tool has proper schema"""
        assert add.name == "add"
        assert add.description is not None
        schema = add.args_schema.model_json_schema()
        assert "a" in str(schema)
        assert "b" in str(schema)

    def test_all_tools_have_names(self):
        """Test that all tools have valid names"""
        tools = [calculator, add, subtract, multiply, divide]
        for tool in tools:
            assert tool.name is not None
            assert len(tool.name) > 0
            assert tool.description is not None
