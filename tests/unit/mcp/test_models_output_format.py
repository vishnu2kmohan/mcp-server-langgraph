"""
Tests for output_format field in MCP models.

Verifies that ChatInput and other MCP models support optional
JSON Schema output format for structured response validation.
"""

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.sdk]


class TestMCPModelsOutputFormat:
    """Tests for output_format integration in MCP models."""

    def test_chat_input_has_output_format_field(self) -> None:
        """ChatInput model should have optional output_format field."""
        from mcp_server_langgraph.mcp.models import ChatInput

        # Create ChatInput with output_format
        chat_input = ChatInput(
            message="Test message",
            token="test-token",
            user_id="test-user",
            output_format={
                "type": "json_schema",
                "schema": {
                    "type": "object",
                    "properties": {"result": {"type": "string"}},
                    "required": ["result"],
                },
            },
        )

        assert chat_input.output_format is not None
        assert chat_input.output_format["type"] == "json_schema"

    def test_chat_input_output_format_is_optional(self) -> None:
        """ChatInput should work without output_format (backwards compatible)."""
        from mcp_server_langgraph.mcp.models import ChatInput

        chat_input = ChatInput(
            message="Test message",
            token="test-token",
            user_id="test-user",
        )

        assert chat_input.output_format is None

    def test_chat_input_output_format_validates_type(self) -> None:
        """output_format should validate the type field."""
        from mcp_server_langgraph.mcp.models import ChatInput

        # Valid type: json_schema
        chat_input = ChatInput(
            message="Test message",
            token="test-token",
            user_id="test-user",
            output_format={"type": "json_schema", "schema": {"type": "object"}},
        )
        assert chat_input.output_format["type"] == "json_schema"

    def test_output_format_can_be_used_with_output_format_module(self) -> None:
        """output_format dict should be compatible with OutputFormat from core."""
        from mcp_server_langgraph.core.output_format import OutputFormat
        from mcp_server_langgraph.mcp.models import ChatInput

        output_format: OutputFormat = {
            "type": "json_schema",
            "schema": {
                "type": "object",
                "properties": {"answer": {"type": "string"}},
                "required": ["answer"],
            },
        }

        chat_input = ChatInput(
            message="What is 2+2?",
            token="test-token",
            user_id="test-user",
            output_format=output_format,
        )

        assert chat_input.output_format == output_format

    def test_output_format_with_schema_validator(self) -> None:
        """output_format from ChatInput should work with SchemaValidator."""
        from mcp_server_langgraph.core.schema_validator import SchemaValidator
        from mcp_server_langgraph.mcp.models import ChatInput

        chat_input = ChatInput(
            message="Get user info",
            token="test-token",
            user_id="test-user",
            output_format={
                "type": "json_schema",
                "schema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "age": {"type": "integer"},
                    },
                    "required": ["name"],
                },
            },
        )

        # Create validator from output_format
        assert chat_input.output_format is not None
        validator = SchemaValidator(chat_input.output_format["schema"])

        # Validate conforming data
        result = validator.validate({"name": "Alice", "age": 30})
        assert result.valid is True

        # Validate non-conforming data
        result = validator.validate({"age": 30})  # Missing required 'name'
        assert result.valid is False

    def test_chat_input_serialization_with_output_format(self) -> None:
        """ChatInput with output_format should serialize correctly."""
        from mcp_server_langgraph.mcp.models import ChatInput

        chat_input = ChatInput(
            message="Test",
            token="token",
            user_id="user",
            output_format={
                "type": "json_schema",
                "schema": {"type": "string"},
            },
        )

        # Convert to dict
        data = chat_input.model_dump()
        assert "output_format" in data
        assert data["output_format"]["type"] == "json_schema"

    def test_chat_input_deserialization_with_output_format(self) -> None:
        """ChatInput should deserialize correctly with output_format."""
        from mcp_server_langgraph.mcp.models import ChatInput

        data = {
            "message": "Test",
            "token": "token",
            "user_id": "user",
            "output_format": {
                "type": "json_schema",
                "schema": {"type": "boolean"},
            },
        }

        chat_input = ChatInput.model_validate(data)
        assert chat_input.output_format is not None
        assert chat_input.output_format["schema"]["type"] == "boolean"

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()
