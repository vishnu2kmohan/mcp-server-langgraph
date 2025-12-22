"""
Tool input examples for improving LLM accuracy

This module implements the input_examples pattern from Anthropic's
Advanced Tool Use research, which shows 72% → 90% accuracy improvement
on complex tool parameters when examples are provided.

Example usage:
    from mcp_server_langgraph.tools.examples import get_examples_for_tool

    examples = get_examples_for_tool("calculator")
    # Returns list of ToolExample objects with description and input
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from pydantic import BaseModel, field_validator


class ToolExample(BaseModel):
    """A single input example for a tool.

    Attributes:
        description: What this example demonstrates (e.g., "Compound interest")
        input: Dictionary of input arguments matching the tool's schema
    """

    description: str
    input: dict[str, Any]

    @field_validator("description", mode="before")
    @classmethod
    def validate_description_is_string(cls, v: Any) -> str:
        """Ensure description is a string"""
        if not isinstance(v, str):
            raise ValueError("description must be a string")
        return v

    @field_validator("input", mode="before")
    @classmethod
    def validate_input_is_dict(cls, v: Any) -> dict[str, Any]:
        """Ensure input is a dictionary"""
        if not isinstance(v, dict):
            raise ValueError("input must be a dictionary")
        return v


# Registry of tool examples
# Key: tool name, Value: list of ToolExample objects
_TOOL_EXAMPLES: dict[str, list[ToolExample]] = {}


def _initialize_default_examples() -> None:
    """Initialize default examples for built-in tools.

    These examples are based on Anthropic's research showing that
    providing input examples significantly improves accuracy on
    complex parameters.
    """
    global _TOOL_EXAMPLES

    # Calculator examples
    _TOOL_EXAMPLES["calculator"] = [
        ToolExample(
            description="Compound interest calculation over 10 years at 5%",
            input={"expression": "1000 * (1.05) ** 10"},
        ),
        ToolExample(
            description="Percentage calculation (15% of 250)",
            input={"expression": "250 * 0.15"},
        ),
        ToolExample(
            description="Complex expression with parentheses",
            input={"expression": "(100 + 50) * 2 - 25"},
        ),
    ]

    # Web search examples
    _TOOL_EXAMPLES["web_search"] = [
        ToolExample(
            description="Search for recent news on a topic",
            input={"query": "quantum computing breakthroughs 2025"},
        ),
        ToolExample(
            description="Search for technical documentation",
            input={"query": "Python asyncio best practices"},
        ),
    ]

    # Search knowledge base examples
    _TOOL_EXAMPLES["search_knowledge_base"] = [
        ToolExample(
            description="Search internal documentation",
            input={"query": "API authentication flow"},
        ),
    ]

    # File read examples
    _TOOL_EXAMPLES["read_file"] = [
        ToolExample(
            description="Read a Python source file",
            input={"path": "src/main.py"},
        ),
    ]

    # Code execution examples
    _TOOL_EXAMPLES["execute_python"] = [
        ToolExample(
            description="Simple data analysis",
            input={"code": "import json\ndata = {'count': 10}\nprint(json.dumps(data))"},
        ),
    ]


# Initialize default examples on module load
_initialize_default_examples()

# Public constant for backward compatibility
TOOL_EXAMPLES: dict[str, list[ToolExample]] = _TOOL_EXAMPLES


def get_examples_for_tool(tool_name: str) -> list[ToolExample]:
    """Get input examples for a specific tool.

    Args:
        tool_name: Name of the tool to get examples for

    Returns:
        List of ToolExample objects, or empty list if no examples exist
    """
    examples = _TOOL_EXAMPLES.get(tool_name, [])
    # Return a deep copy to prevent mutation of the registry
    return deepcopy(examples)


def register_example(tool_name: str, example: ToolExample) -> None:
    """Register a new example for a tool.

    Args:
        tool_name: Name of the tool to register example for
        example: ToolExample object to register
    """
    if tool_name not in _TOOL_EXAMPLES:
        _TOOL_EXAMPLES[tool_name] = []
    _TOOL_EXAMPLES[tool_name].append(example)


def serialize_examples_for_tool(tool_name: str) -> list[dict[str, Any]]:
    """Serialize examples for MCP tools/list response.

    Args:
        tool_name: Name of the tool

    Returns:
        List of dictionaries with 'description' and 'input' keys
    """
    examples = get_examples_for_tool(tool_name)
    return [{"description": ex.description, "input": ex.input} for ex in examples]


def validate_example_against_schema(tool_name: str, example: ToolExample) -> list[str]:
    """Validate an example against a tool's schema.

    Args:
        tool_name: Name of the tool
        example: ToolExample to validate

    Returns:
        List of validation errors, empty if valid
    """
    errors: list[str] = []

    # Get tool schema based on tool name
    try:
        from mcp_server_langgraph.tools import ALL_TOOLS

        tool = next((t for t in ALL_TOOLS if t.name == tool_name), None)
        if tool is None:
            return [f"Unknown tool: {tool_name}"]

        # Get required parameters from tool schema
        schema = tool.args_schema
        if schema is None:
            return []

        # Get model fields and check required (only for BaseModel schemas)
        if hasattr(schema, "model_fields"):
            for field_name, field_info in schema.model_fields.items():
                if field_info.is_required() and field_name not in example.input:
                    errors.append(f"Missing required parameter: {field_name}")

    except ImportError:
        errors.append("Could not import tools module for validation")

    return errors


def validate_examples_for_tool(tool_name: str) -> list[str]:
    """Validate all registered examples for a tool.

    Args:
        tool_name: Name of the tool

    Returns:
        List of validation errors, empty if all examples are valid
    """
    errors: list[str] = []
    examples = get_examples_for_tool(tool_name)

    for i, example in enumerate(examples):
        example_errors = validate_example_against_schema(tool_name, example)
        for error in example_errors:
            errors.append(f"Example {i + 1}: {error}")

    return errors
