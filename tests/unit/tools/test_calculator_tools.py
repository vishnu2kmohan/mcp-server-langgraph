"""
Unit tests for tools/calculator_tools.py.

Tests safe mathematical expression evaluation and arithmetic tools.
Follows TDD principles and memory safety patterns for pytest-xdist.
"""

import gc

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="calculator_tools")
class TestSafeEval:
    """Test _safe_eval function for expression evaluation."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_safe_eval_addition(self):
        """Test addition evaluation."""
        from mcp_server_langgraph.tools.calculator_tools import _safe_eval

        result = _safe_eval("2 + 2")
        assert result == 4.0

    @pytest.mark.unit
    def test_safe_eval_subtraction(self):
        """Test subtraction evaluation."""
        from mcp_server_langgraph.tools.calculator_tools import _safe_eval

        result = _safe_eval("10 - 3")
        assert result == 7.0

    @pytest.mark.unit
    def test_safe_eval_multiplication(self):
        """Test multiplication evaluation."""
        from mcp_server_langgraph.tools.calculator_tools import _safe_eval

        result = _safe_eval("5 * 6")
        assert result == 30.0

    @pytest.mark.unit
    def test_safe_eval_division(self):
        """Test division evaluation."""
        from mcp_server_langgraph.tools.calculator_tools import _safe_eval

        result = _safe_eval("20 / 4")
        assert result == 5.0

    @pytest.mark.unit
    def test_safe_eval_power(self):
        """Test power evaluation."""
        from mcp_server_langgraph.tools.calculator_tools import _safe_eval

        result = _safe_eval("2 ** 3")
        assert result == 8.0

    @pytest.mark.unit
    def test_safe_eval_modulo(self):
        """Test modulo evaluation."""
        from mcp_server_langgraph.tools.calculator_tools import _safe_eval

        result = _safe_eval("10 % 3")
        assert result == 1.0

    @pytest.mark.unit
    def test_safe_eval_parentheses(self):
        """Test parentheses in expressions."""
        from mcp_server_langgraph.tools.calculator_tools import _safe_eval

        result = _safe_eval("(2 + 3) * 4")
        assert result == 20.0

    @pytest.mark.unit
    def test_safe_eval_negative_numbers(self):
        """Test negative number handling."""
        from mcp_server_langgraph.tools.calculator_tools import _safe_eval

        result = _safe_eval("-5 + 10")
        assert result == 5.0

    @pytest.mark.unit
    def test_safe_eval_positive_unary(self):
        """Test positive unary operator."""
        from mcp_server_langgraph.tools.calculator_tools import _safe_eval

        result = _safe_eval("+5")
        assert result == 5.0

    @pytest.mark.unit
    def test_safe_eval_float_numbers(self):
        """Test float number handling."""
        from mcp_server_langgraph.tools.calculator_tools import _safe_eval

        result = _safe_eval("3.5 + 2.5")
        assert result == 6.0

    @pytest.mark.unit
    def test_safe_eval_complex_expression(self):
        """Test complex nested expression."""
        from mcp_server_langgraph.tools.calculator_tools import _safe_eval

        result = _safe_eval("((2 + 3) * 4 - 10) / 2")
        assert result == 5.0

    @pytest.mark.unit
    def test_safe_eval_rejects_function_calls(self):
        """Test that function calls are rejected."""
        from mcp_server_langgraph.tools.calculator_tools import _safe_eval

        with pytest.raises(ValueError, match="Unsafe node type"):
            _safe_eval("print('hello')")

    @pytest.mark.unit
    def test_safe_eval_rejects_imports(self):
        """Test that import statements are rejected."""
        from mcp_server_langgraph.tools.calculator_tools import _safe_eval

        with pytest.raises(ValueError):
            _safe_eval("__import__('os')")

    @pytest.mark.unit
    def test_safe_eval_rejects_variables(self):
        """Test that variable access is rejected."""
        from mcp_server_langgraph.tools.calculator_tools import _safe_eval

        with pytest.raises(ValueError, match="Unsafe node type"):
            _safe_eval("x + 1")

    @pytest.mark.unit
    def test_safe_eval_rejects_string_constants(self):
        """Test that string constants are rejected."""
        from mcp_server_langgraph.tools.calculator_tools import _safe_eval

        with pytest.raises(ValueError, match="Invalid constant type"):
            _safe_eval("'hello'")

    @pytest.mark.unit
    def test_safe_eval_division_by_zero_raises_error(self):
        """Test that division by zero raises error."""
        from mcp_server_langgraph.tools.calculator_tools import _safe_eval

        with pytest.raises(ValueError, match="Invalid expression"):
            _safe_eval("1 / 0")


@pytest.mark.xdist_group(name="calculator_tools")
class TestCalculatorTool:
    """Test calculator tool."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_calculator_returns_result_string(self):
        """Test that calculator returns result as string."""
        from mcp_server_langgraph.tools.calculator_tools import calculator

        result = calculator.invoke({"expression": "2 + 2"})
        assert result == "4.0"

    @pytest.mark.unit
    def test_calculator_handles_complex_expression(self):
        """Test calculator with complex expression."""
        from mcp_server_langgraph.tools.calculator_tools import calculator

        result = calculator.invoke({"expression": "(10 * 3) - 5"})
        assert result == "25.0"

    @pytest.mark.unit
    def test_calculator_returns_error_for_invalid_expression(self):
        """Test that calculator returns error for invalid expression."""
        from mcp_server_langgraph.tools.calculator_tools import calculator

        result = calculator.invoke({"expression": "invalid"})
        assert "Error" in result


@pytest.mark.xdist_group(name="calculator_tools")
class TestAddTool:
    """Test add tool."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_add_returns_sum_as_string(self):
        """Test that add returns sum as string."""
        from mcp_server_langgraph.tools.calculator_tools import add

        result = add.invoke({"a": 5.0, "b": 3.0})
        assert result == "8.0"

    @pytest.mark.unit
    def test_add_handles_negative_numbers(self):
        """Test add with negative numbers."""
        from mcp_server_langgraph.tools.calculator_tools import add

        result = add.invoke({"a": -10.0, "b": 5.0})
        assert result == "-5.0"


@pytest.mark.xdist_group(name="calculator_tools")
class TestSubtractTool:
    """Test subtract tool."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_subtract_returns_difference_as_string(self):
        """Test that subtract returns difference as string."""
        from mcp_server_langgraph.tools.calculator_tools import subtract

        result = subtract.invoke({"a": 10.0, "b": 3.0})
        assert result == "7.0"

    @pytest.mark.unit
    def test_subtract_handles_negative_result(self):
        """Test subtract with negative result."""
        from mcp_server_langgraph.tools.calculator_tools import subtract

        result = subtract.invoke({"a": 3.0, "b": 10.0})
        assert result == "-7.0"


@pytest.mark.xdist_group(name="calculator_tools")
class TestMultiplyTool:
    """Test multiply tool."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_multiply_returns_product_as_string(self):
        """Test that multiply returns product as string."""
        from mcp_server_langgraph.tools.calculator_tools import multiply

        result = multiply.invoke({"a": 5.0, "b": 6.0})
        assert result == "30.0"

    @pytest.mark.unit
    def test_multiply_handles_zero(self):
        """Test multiply with zero."""
        from mcp_server_langgraph.tools.calculator_tools import multiply

        result = multiply.invoke({"a": 100.0, "b": 0.0})
        assert result == "0.0"


@pytest.mark.xdist_group(name="calculator_tools")
class TestDivideTool:
    """Test divide tool."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_divide_returns_quotient_as_string(self):
        """Test that divide returns quotient as string."""
        from mcp_server_langgraph.tools.calculator_tools import divide

        result = divide.invoke({"a": 20.0, "b": 4.0})
        assert result == "5.0"

    @pytest.mark.unit
    def test_divide_handles_division_by_zero(self):
        """Test divide with division by zero."""
        from mcp_server_langgraph.tools.calculator_tools import divide

        result = divide.invoke({"a": 10.0, "b": 0.0})
        assert result == "Error: Division by zero"

    @pytest.mark.unit
    def test_divide_handles_fractional_result(self):
        """Test divide with fractional result."""
        from mcp_server_langgraph.tools.calculator_tools import divide

        result = divide.invoke({"a": 7.0, "b": 2.0})
        assert result == "3.5"


@pytest.mark.xdist_group(name="calculator_tools")
class TestSafeLogging:
    """Test safe logging utilities."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_safe_log_handles_normal_logging(self):
        """Test that _safe_log works with valid observability."""
        from mcp_server_langgraph.tools.calculator_tools import _safe_log

        # Should not raise - observability is initialized in test suite
        _safe_log("info", "test message", extra={"key": "value"})

    @pytest.mark.unit
    def test_safe_metric_handles_normal_metrics(self):
        """Test that _safe_metric works with valid observability."""
        from mcp_server_langgraph.tools.calculator_tools import _safe_metric

        # Should not raise - observability is initialized in test suite
        _safe_metric("tool_calls", 1, {"tool": "test"})
