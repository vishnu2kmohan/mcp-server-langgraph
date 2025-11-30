"""
Tool creation command for MCP Server CLI.

Generates tool files with boilerplate code.
"""

from pathlib import Path

TOOL_TEMPLATE = """\"\"\"
{name} Tool

{description}
\"\"\"

from typing import Any, Dict
from pydantic import BaseModel, Field


class {class_name}Input(BaseModel):
    \"\"\"Input schema for {name} tool.\"\"\"
    # TODO: Define input fields
    input_text: str = Field(description="Input for the tool")


class {class_name}Output(BaseModel):
    \"\"\"Output schema for {name} tool.\"\"\"
    result: str = Field(description="Result from the tool")
    success: bool = Field(description="Whether the operation succeeded")


def {function_name}(input_data: {class_name}Input) -> {class_name}Output:
    \"\"\"
    {description}

    Args:
        input_data: Input parameters for the tool

    Returns:
        Output with result and success status

    Example:
        >>> result = {function_name}({class_name}Input(input_text="test"))
        >>> print(result.result)
    \"\"\"
    # TODO: Implement your tool logic here

    try:
        # Your implementation here
        result = f"Processed: {{input_data.input_text}}"

        return {class_name}Output(
            result=result,
            success=True
        )
    except Exception as e:
        return {class_name}Output(
            result=f"Error: {{str(e)}}",
            success=False
        )


# Tool metadata for MCP registration
TOOL_METADATA = {{
    "name": "{name}",
    "description": "{description}",
    "input_schema": {class_name}Input.model_json_schema(),
    "output_schema": {class_name}Output.model_json_schema(),
}}
"""


def generate_tool(name: str, description: str) -> None:
    """
    Generate a tool file with boilerplate code.

    Args:
        name: Name of the tool (e.g., "web_scraper")
        description: What the tool does

    Raises:
        FileExistsError: If tool file already exists
    """
    # Create tools directory if it doesn't exist
    tools_dir = Path("src/tools")
    tools_dir.mkdir(parents=True, exist_ok=True)

    # Generate file name
    tool_file = tools_dir / f"{name}_tool.py"

    if tool_file.exists():
        msg = f"Tool file already exists: {tool_file}"
        raise FileExistsError(msg)

    # Generate class and function names
    class_name = "".join(word.capitalize() for word in name.split("_"))
    function_name = name.replace("-", "_")

    # Fill template
    content = TOOL_TEMPLATE.format(
        name=name,
        description=description,
        class_name=class_name,
        function_name=function_name,
    )

    # Write file
    tool_file.write_text(content)

    # Create test file
    tests_dir = Path("tests/tools")
    tests_dir.mkdir(parents=True, exist_ok=True)

    test_file = tests_dir / f"test_{name}_tool.py"
    test_content = f'''"""
Tests for {name} tool.
"""

import pytest
from src.tools.{name}_tool import {function_name}, {class_name}Input, {class_name}Output


def test_{function_name}_success():
    """Test successful tool execution."""
    input_data = {class_name}Input(input_text="test input")
    result = {function_name}(input_data)

    assert isinstance(result, {class_name}Output)
    assert result.success is True
    assert result.result is not None


def test_{function_name}_with_empty_input():
    """Test tool with empty input."""
    input_data = {class_name}Input(input_text="")
    result = {function_name}(input_data)

    assert isinstance(result, {class_name}Output)
    # TODO: Add assertions for expected behavior


@pytest.mark.parametrize("test_input,expected_success", [
    ("valid input", True),
    ("another valid input", True),
])
def test_{function_name}_parametrized(test_input: str, expected_success: bool):
    """Parametrized tests for {name} tool."""
    input_data = {class_name}Input(input_text=test_input)
    result = {function_name}(input_data)

    assert result.success == expected_success
'''

    test_file.write_text(test_content)
