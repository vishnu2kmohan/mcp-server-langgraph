"""
Calculator tools for mathematical operations

Provides basic arithmetic and evaluation tools for the agent.
"""

import ast
import operator
from typing import Any

from langchain_core.tools import tool
from pydantic import Field


def _safe_log(level: str, message: str, **kwargs) -> None:
    """Safely log message, handling cases where observability isn't initialized"""
    try:
        from mcp_server_langgraph.observability.telemetry import logger

        getattr(logger, level)(message, **kwargs)
    except (ImportError, RuntimeError):
        # Observability not available - silently skip
        pass


def _safe_metric(metric_name: str, value: float, attributes: dict) -> None:
    """Safely record metric, handling cases where observability isn't initialized"""
    try:
        from mcp_server_langgraph.observability.telemetry import metrics

        getattr(metrics, metric_name).add(value, attributes)
    except (ImportError, RuntimeError):
        # Observability not available - silently skip
        pass


# Safe operators for calculator evaluation
SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
    ast.Mod: operator.mod,
}


def _safe_eval(expression: str) -> float:
    """
    Safely evaluate a mathematical expression.

    Args:
        expression: Mathematical expression (e.g., "2 + 2", "10 * 3")

    Returns:
        Result of evaluation

    Raises:
        ValueError: If expression contains unsafe operations
        SyntaxError: If expression is malformed
    """

    def _eval(node: Any) -> float:
        if isinstance(node, ast.Constant):  # Number (Python 3.8+)
            return float(node.value)
        elif isinstance(node, ast.BinOp):  # Binary operation
            op_func = SAFE_OPERATORS.get(type(node.op))
            if op_func is None:
                raise ValueError(f"Unsafe operator: {type(node.op).__name__}")
            return op_func(_eval(node.left), _eval(node.right))
        elif isinstance(node, ast.UnaryOp):  # Unary operation
            op_func = SAFE_OPERATORS.get(type(node.op))
            if op_func is None:
                raise ValueError(f"Unsafe operator: {type(node.op).__name__}")
            return op_func(_eval(node.operand))
        else:
            raise ValueError(f"Unsafe node type: {type(node).__name__}")

    try:
        tree = ast.parse(expression, mode="eval")
        result = _eval(tree.body)
        return result
    except (ValueError, SyntaxError, ZeroDivisionError) as e:
        raise ValueError(f"Invalid expression: {e}") from e


@tool
def calculator(expression: str = Field(description="Mathematical expression to evaluate (e.g., '2 + 2', '10 * 3')")) -> str:
    """
    Evaluate a mathematical expression safely.

    Supports: +, -, *, /, **, %, and parentheses.
    Does NOT support: functions, variables, or imports for security.

    Examples:
    - "2 + 2" → 4.0
    - "10 * 3 - 5" → 25.0
    - "(8 / 2) ** 2" → 16.0
    """
    try:
        _safe_log("info", "Calculator tool invoked", extra={"expression": expression})
        _safe_metric("tool_calls", 1, {"tool": "calculator"})

        result = _safe_eval(expression)

        _safe_log("info", "Calculator result", extra={"expression": expression, "result": result})
        return f"{result}"

    except Exception as e:
        error_msg = f"Error evaluating expression '{expression}': {e}"
        _safe_log("error", error_msg, exc_info=True)
        return f"Error: {e}"


@tool
def add(a: float = Field(description="First number"), b: float = Field(description="Second number")) -> str:
    """Add two numbers together."""
    try:
        _safe_log("info", "Add tool invoked", extra={"a": a, "b": b})
        _safe_metric("tool_calls", 1, {"tool": "add"})

        result = a + b
        return f"{result}"

    except Exception as e:
        _safe_log("error", f"Error in add tool: {e}", exc_info=True)
        return f"Error: {e}"


@tool
def subtract(a: float = Field(description="First number"), b: float = Field(description="Second number")) -> str:
    """Subtract second number from first number."""
    try:
        _safe_log("info", "Subtract tool invoked", extra={"a": a, "b": b})
        _safe_metric("tool_calls", 1, {"tool": "subtract"})

        result = a - b
        return f"{result}"

    except Exception as e:
        _safe_log("error", f"Error in subtract tool: {e}", exc_info=True)
        return f"Error: {e}"


@tool
def multiply(a: float = Field(description="First number"), b: float = Field(description="Second number")) -> str:
    """Multiply two numbers together."""
    try:
        _safe_log("info", "Multiply tool invoked", extra={"a": a, "b": b})
        _safe_metric("tool_calls", 1, {"tool": "multiply"})

        result = a * b
        return f"{result}"

    except Exception as e:
        _safe_log("error", f"Error in multiply tool: {e}", exc_info=True)
        return f"Error: {e}"


@tool
def divide(a: float = Field(description="Numerator"), b: float = Field(description="Denominator (cannot be zero)")) -> str:
    """Divide first number by second number."""
    try:
        _safe_log("info", "Divide tool invoked", extra={"a": a, "b": b})
        _safe_metric("tool_calls", 1, {"tool": "divide"})

        if b == 0:
            return "Error: Division by zero"

        result = a / b
        return f"{result}"

    except Exception as e:
        _safe_log("error", f"Error in divide tool: {e}", exc_info=True)
        return f"Error: {e}"
