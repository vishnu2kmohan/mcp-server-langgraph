"""
MCP Tool Validation Errors (SEP-1303).

MCP 2025-11-25 specifies that tool input validation errors should be
returned as Tool Errors (isError=True in result), not Protocol Errors
(JSON-RPC error response).

This module provides utilities for handling validation errors in tool calls
according to SEP-1303.

Reference: https://modelcontextprotocol.io/specification/2025-11-25/server/tools
"""

from typing import Any

from pydantic import ValidationError


def is_validation_error(error: Exception) -> bool:
    """Check if an exception is a validation error.

    Validation errors include:
    - Pydantic ValidationError
    - ValueError (commonly used for input validation)
    - TypeError (commonly used for type validation)

    Runtime errors, IO errors, and other exceptions are NOT validation errors
    and should be handled differently.

    Args:
        error: Exception to check

    Returns:
        True if this is a validation error, False otherwise
    """
    # Pydantic validation errors
    if isinstance(error, ValidationError):
        return True

    # Standard Python validation errors
    return isinstance(error, (ValueError, TypeError))


def create_validation_error_result(error_message: str) -> dict[str, Any]:
    """Create a tool error result for validation failures.

    Per SEP-1303, validation errors should be returned as tool errors
    with isError=True, not as JSON-RPC protocol errors.

    Args:
        error_message: Human-readable error message

    Returns:
        Tool result dict with isError=True and error in content
    """
    return {
        "isError": True,
        "content": [
            {
                "type": "text",
                "text": f"Input validation failed: {error_message}",
            }
        ],
    }


def handle_tool_validation_error(error: Exception) -> dict[str, Any]:
    """Handle a validation error and create tool error result.

    Converts various exception types to tool error results per SEP-1303.

    Args:
        error: Validation exception (ValidationError, ValueError, TypeError)

    Returns:
        Tool result dict with isError=True
    """
    if isinstance(error, ValidationError):
        # Pydantic ValidationError - extract error details
        errors = error.errors()
        if errors:
            # Format the first error for readability
            first_error = errors[0]
            loc = ".".join(str(x) for x in first_error.get("loc", []))
            msg = first_error.get("msg", str(error))
            error_message = f"Validation error at '{loc}': {msg}"
        else:
            error_message = str(error)
    else:
        # ValueError, TypeError, etc.
        error_message = str(error)

    return create_validation_error_result(error_message)
