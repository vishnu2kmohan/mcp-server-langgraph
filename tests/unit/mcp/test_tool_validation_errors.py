"""
Tests for MCP Tool Validation Errors (SEP-1303).

MCP 2025-11-25 specifies that tool input validation errors should be
returned as Tool Errors (isError=True in result), not Protocol Errors
(JSON-RPC error response).

TDD: RED phase - Define expected behavior for SEP-1303 implementation.
"""

import pytest

pytestmark = pytest.mark.unit


class TestToolValidationErrorResponse:
    """Test that validation errors are returned as tool errors."""

    def test_validation_error_result_format(self) -> None:
        """Validation errors should return isError=True in result."""
        from mcp_server_langgraph.mcp.tool_errors import (
            create_validation_error_result,
        )

        # Simulate a Pydantic validation error message
        error_message = "Field 'query' is required"

        result = create_validation_error_result(error_message)

        assert result["isError"] is True
        assert len(result["content"]) == 1
        assert result["content"][0]["type"] == "text"
        assert "query" in result["content"][0]["text"]

    def test_validation_error_preserves_error_details(self) -> None:
        """Error details should be preserved in the text content."""
        from mcp_server_langgraph.mcp.tool_errors import (
            create_validation_error_result,
        )

        error_message = "Invalid type for 'count': expected integer, got string"

        result = create_validation_error_result(error_message)

        assert "Invalid type" in result["content"][0]["text"]
        assert "count" in result["content"][0]["text"]
        assert "integer" in result["content"][0]["text"]


class TestToolValidationErrorHandler:
    """Test tool validation error handler utility."""

    def test_handle_pydantic_validation_error(self) -> None:
        """Should handle Pydantic ValidationError and return tool error."""
        from pydantic import BaseModel, ValidationError

        from mcp_server_langgraph.mcp.tool_errors import (
            handle_tool_validation_error,
        )

        class TestInput(BaseModel):
            query: str
            count: int

        # Create a validation error by providing invalid input
        try:
            TestInput(query=123, count="not-a-number")  # type: ignore[arg-type]
        except ValidationError as e:
            result = handle_tool_validation_error(e)

        assert result["isError"] is True
        assert "content" in result
        # Should contain error details
        text = result["content"][0]["text"]
        assert "validation" in text.lower() or "error" in text.lower()

    def test_handle_generic_validation_error(self) -> None:
        """Should handle generic ValueError and return tool error."""
        from mcp_server_langgraph.mcp.tool_errors import (
            handle_tool_validation_error,
        )

        error = ValueError("Missing required parameter: thread_id")
        result = handle_tool_validation_error(error)

        assert result["isError"] is True
        assert "thread_id" in result["content"][0]["text"]


class TestToolErrorTypes:
    """Test tool error type classification."""

    def test_is_validation_error_for_pydantic(self) -> None:
        """Should identify Pydantic ValidationError as validation error."""
        from pydantic import BaseModel, ValidationError

        from mcp_server_langgraph.mcp.tool_errors import is_validation_error

        class TestModel(BaseModel):
            value: int

        try:
            TestModel(value="not-an-int")  # type: ignore[arg-type]
        except ValidationError as e:
            assert is_validation_error(e) is True

    def test_is_validation_error_for_value_error(self) -> None:
        """Should identify ValueError as validation error."""
        from mcp_server_langgraph.mcp.tool_errors import is_validation_error

        error = ValueError("Invalid input")
        assert is_validation_error(error) is True

    def test_is_validation_error_for_type_error(self) -> None:
        """Should identify TypeError as validation error."""
        from mcp_server_langgraph.mcp.tool_errors import is_validation_error

        error = TypeError("Expected str, got int")
        assert is_validation_error(error) is True

    def test_is_not_validation_error_for_runtime(self) -> None:
        """Should NOT identify RuntimeError as validation error."""
        from mcp_server_langgraph.mcp.tool_errors import is_validation_error

        error = RuntimeError("Something went wrong during execution")
        assert is_validation_error(error) is False

    def test_is_not_validation_error_for_io_error(self) -> None:
        """Should NOT identify IOError as validation error."""
        from mcp_server_langgraph.mcp.tool_errors import is_validation_error

        error = OSError("File not found")
        assert is_validation_error(error) is False
