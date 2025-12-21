"""
Tests for Output Format (Phase 4.1)

Following TDD: Write tests FIRST, then implementation.

This module tests the output format definitions following
Claude Agent SDK's output_format pattern for JSON Schema validation.
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    pass

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="output_format")
class TestOutputFormatImport:
    """Test output format components can be imported."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_output_format_importable(self) -> None:
        """OutputFormat should be importable."""
        from mcp_server_langgraph.core.output_format import OutputFormat

        assert OutputFormat is not None

    def test_output_format_type_importable(self) -> None:
        """OutputFormatType should be importable."""
        from mcp_server_langgraph.core.output_format import OutputFormatType

        assert OutputFormatType is not None


@pytest.mark.xdist_group(name="output_format")
class TestOutputFormatCreation:
    """Test creating OutputFormat instances."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_json_schema_format(self) -> None:
        """Should create JSON Schema output format."""
        from mcp_server_langgraph.core.output_format import (
            OutputFormat,
            OutputFormatType,
        )

        schema = {
            "type": "object",
            "properties": {
                "result": {"type": "string"},
            },
            "required": ["result"],
        }

        output_format = OutputFormat(
            format_type=OutputFormatType.JSON_SCHEMA,
            schema=schema,
        )

        assert output_format.format_type == OutputFormatType.JSON_SCHEMA
        assert output_format.schema == schema

    def test_create_text_format(self) -> None:
        """Should create text output format (no schema)."""
        from mcp_server_langgraph.core.output_format import (
            OutputFormat,
            OutputFormatType,
        )

        output_format = OutputFormat(format_type=OutputFormatType.TEXT)

        assert output_format.format_type == OutputFormatType.TEXT
        assert output_format.schema is None

    def test_json_schema_requires_schema(self) -> None:
        """JSON Schema format should require a schema."""
        from mcp_server_langgraph.core.output_format import (
            OutputFormat,
            OutputFormatType,
        )

        with pytest.raises(ValueError):
            OutputFormat(format_type=OutputFormatType.JSON_SCHEMA)

    def test_output_format_with_name(self) -> None:
        """OutputFormat should support optional name."""
        from mcp_server_langgraph.core.output_format import (
            OutputFormat,
            OutputFormatType,
        )

        output_format = OutputFormat(
            format_type=OutputFormatType.JSON_SCHEMA,
            schema={"type": "object"},
            name="my_response",
        )

        assert output_format.name == "my_response"


@pytest.mark.xdist_group(name="output_format")
class TestOutputFormatFromDict:
    """Test creating OutputFormat from dictionary."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_from_dict_json_schema(self) -> None:
        """Should create from SDK-style dictionary."""
        from mcp_server_langgraph.core.output_format import (
            OutputFormat,
            OutputFormatType,
        )

        config = {
            "type": "json_schema",
            "schema": {
                "type": "object",
                "properties": {"status": {"type": "string"}},
            },
        }

        output_format = OutputFormat.from_dict(config)

        assert output_format.format_type == OutputFormatType.JSON_SCHEMA
        assert output_format.schema["type"] == "object"

    def test_from_dict_text(self) -> None:
        """Should create text format from dictionary."""
        from mcp_server_langgraph.core.output_format import (
            OutputFormat,
            OutputFormatType,
        )

        config = {"type": "text"}

        output_format = OutputFormat.from_dict(config)

        assert output_format.format_type == OutputFormatType.TEXT

    def test_from_dict_invalid_type(self) -> None:
        """Should raise for invalid format type."""
        from mcp_server_langgraph.core.output_format import OutputFormat

        config = {"type": "unknown"}

        with pytest.raises(ValueError):
            OutputFormat.from_dict(config)


@pytest.mark.xdist_group(name="output_format")
class TestOutputFormatToDict:
    """Test converting OutputFormat to dictionary."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_to_dict_json_schema(self) -> None:
        """Should convert to SDK-style dictionary."""
        from mcp_server_langgraph.core.output_format import (
            OutputFormat,
            OutputFormatType,
        )

        output_format = OutputFormat(
            format_type=OutputFormatType.JSON_SCHEMA,
            schema={"type": "object"},
            name="response",
        )

        result = output_format.to_dict()

        assert result["type"] == "json_schema"
        assert result["schema"] == {"type": "object"}
        assert result.get("name") == "response"

    def test_to_dict_text(self) -> None:
        """Should convert text format to dictionary."""
        from mcp_server_langgraph.core.output_format import (
            OutputFormat,
            OutputFormatType,
        )

        output_format = OutputFormat(format_type=OutputFormatType.TEXT)

        result = output_format.to_dict()

        assert result["type"] == "text"
        assert "schema" not in result


@pytest.mark.xdist_group(name="output_format")
class TestCommonSchemas:
    """Test common pre-defined schemas."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_simple_response_schema_exists(self) -> None:
        """Should have simple response schema helper."""
        from mcp_server_langgraph.core.output_format import simple_response_format

        output_format = simple_response_format()

        assert output_format is not None
        assert output_format.schema is not None

    def test_analysis_response_schema_exists(self) -> None:
        """Should have analysis response schema helper."""
        from mcp_server_langgraph.core.output_format import analysis_response_format

        output_format = analysis_response_format()

        assert output_format is not None
        assert output_format.schema is not None
        assert "analysis" in output_format.schema.get("properties", {})
