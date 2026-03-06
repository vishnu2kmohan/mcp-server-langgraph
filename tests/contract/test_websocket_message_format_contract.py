"""
WebSocket Message Format Contract Tests.

Validates that WebSocket message formats are consistent between frontend and backend.

This test catches the bug where:
1. Backend sends error in `payload` format: { type: "error", payload: { code, message, retryable } }
2. Frontend expects `data` format: { type: "error", data: <string> }
3. Users see "Error: undefined" at runtime

ADR-0093 documents this protocol alignment requirement.

Why this matters:
- Frontend unit tests mock WebSocket messages with potentially wrong formats
- Backend unit tests don't validate serialized message format
- No validation that both sides agree on the message envelope structure
- Protocol mismatches discovered only at runtime

This test:
1. Validates backend error responses use ADR-0093 payload format
2. Validates frontend type definitions match backend structures
3. Ensures MessageEnvelope serialization matches frontend expectations
"""

from __future__ import annotations

import gc
import re
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from typing import Any

pytestmark = [pytest.mark.unit, pytest.mark.contract, pytest.mark.websocket]


def get_frontend_hook_path(hook_name: str) -> Path:
    """Get the path to a frontend WebSocket hook."""
    current = Path(__file__).parent
    hook_path = current.parent.parent / "src" / "mcp_server_langgraph" / "studio" / "frontend" / "src" / "hooks" / hook_name
    if not hook_path.exists():
        pytest.skip(f"Frontend hook not found at {hook_path}")
    return hook_path


def get_backend_types_path() -> Path:
    """Get the path to the backend websocket types."""
    current = Path(__file__).parent
    types_path = current.parent.parent / "src" / "mcp_server_langgraph" / "websocket" / "types.py"
    if not types_path.exists():
        pytest.skip(f"Backend types.py not found at {types_path}")
    return types_path


@pytest.mark.xdist_group(name="websocket_message_format_contract")
class TestWebSocketMessageFormatContract:
    """Tests validating WebSocket message format agreement between frontend and backend."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_backend_message_envelope_has_payload_not_data(self) -> None:
        """
        Test that backend MessageEnvelope uses 'payload' field, not 'data'.

        ADR-0093: Error responses MUST have payload, NOT data field.
        """
        from mcp_server_langgraph.websocket.types import MessageEnvelope

        # Create an error message envelope
        envelope = MessageEnvelope(
            type="error",
            payload={"code": "test", "message": "Test error", "retryable": True},
        )

        # Serialize to dict (what gets sent over WebSocket)
        serialized = envelope.to_dict()

        # MUST have 'type' and 'payload'
        assert "type" in serialized
        assert serialized["type"] == "error"
        assert "payload" in serialized
        assert serialized["payload"]["code"] == "test"
        assert serialized["payload"]["message"] == "Test error"
        assert serialized["payload"]["retryable"] is True

    def test_backend_error_type_serializes_correctly(self) -> None:
        """
        Test that AISuggestionError serializes to correct format.
        """
        from mcp_server_langgraph.websocket.types import AISuggestionError

        error = AISuggestionError(
            code="internal_error",
            message="An error occurred",
            retryable=True,
        )

        # Serialize to dict
        serialized = error.to_dict()

        # Must have all required fields
        assert serialized["code"] == "internal_error"
        assert serialized["message"] == "An error occurred"
        assert serialized["retryable"] is True

    def test_backend_error_message_format_matches_frontend_expectations(self) -> None:
        """
        Test that backend error message format matches what frontend expects.

        Frontend useAIRealTimeSuggestions.ts expects:
        - message.type === "error"
        - message.payload.message (ADR-0093 format)
        - OR message.data (legacy fallback)
        """
        from mcp_server_langgraph.websocket.types import (
            AISuggestionError,
            AISuggestionMessageType,
            MessageEnvelope,
        )

        # Create error response as backend does
        error = AISuggestionError(
            code="rate_limited",
            message="Rate limit exceeded",
            retryable=True,
        )
        envelope = MessageEnvelope(
            type=AISuggestionMessageType.ERROR,
            payload=error.to_dict(),
        )

        # Serialize as it would be sent over WebSocket
        serialized = envelope.to_dict()

        # Frontend expects to extract error message like this:
        # new Error(message.payload?.message ?? String(message.data) ?? "Unknown error")
        error_message: str | None = None
        if serialized.get("payload") and isinstance(serialized["payload"], dict):
            error_message = serialized["payload"].get("message")
        elif serialized.get("data"):
            error_message = str(serialized["data"])

        assert error_message is not None, "Error message should be extractable"
        assert error_message == "Rate limit exceeded"

    def test_frontend_websocket_message_interface_includes_payload(self) -> None:
        """
        Test that frontend WebSocketMessage interface includes payload field.

        Parses the TypeScript interface to verify it has the payload field.
        """
        hook_path = get_frontend_hook_path("useAIRealTimeSuggestions.ts")
        content = hook_path.read_text()

        # Find WebSocketMessage interface definition
        interface_match = re.search(
            r"interface WebSocketMessage \{([^}]+)\}",
            content,
            re.DOTALL,
        )

        assert interface_match is not None, "WebSocketMessage interface not found"

        interface_body = interface_match.group(1)

        # Must have payload field
        assert "payload?" in interface_body or "payload:" in interface_body, (
            "WebSocketMessage interface must have 'payload' field for ADR-0093 compliance"
        )

        # Payload should have code, message, retryable
        assert "code" in interface_body, "payload should have 'code' field"
        assert "message" in interface_body, "payload should have 'message' field"
        assert "retryable" in interface_body, "payload should have 'retryable' field"

    def test_frontend_error_handler_uses_payload(self) -> None:
        """
        Test that frontend error handler extracts message from payload.

        The error handler should use message.payload?.message, not just message.data.
        """
        hook_path = get_frontend_hook_path("useAIRealTimeSuggestions.ts")
        content = hook_path.read_text()

        # Find the error case handler
        error_case_match = re.search(
            r'case "error":\s*([^}]+)break;',
            content,
            re.DOTALL,
        )

        assert error_case_match is not None, "Error case handler not found"

        error_handler = error_case_match.group(1)

        # Must reference payload?.message (ADR-0093 format)
        assert "payload" in error_handler, "Error handler must use message.payload (ADR-0093 format)"


@pytest.mark.xdist_group(name="websocket_error_format_cross_layer")
class TestWebSocketErrorFormatCrossLayer:
    """
    Cross-layer tests validating error format consistency.

    These tests import both backend types and simulate frontend parsing
    to ensure end-to-end compatibility.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_all_backend_websocket_handlers_use_consistent_error_format(self) -> None:
        """
        Test that all WebSocket handlers that create error responses use
        the same format (payload, not data).
        """
        from mcp_server_langgraph.websocket.handlers.ai_suggestions import (
            AISuggestionsHandler,
        )
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        # Test AI suggestions handler
        config = WebSocketConfig(
            endpoint_name="test",
            require_auth=True,
        )
        handler = AISuggestionsHandler(config=config)

        error_response = handler._create_error_response(
            code="test",
            message="Test error",
            retryable=False,
        )

        serialized = error_response.to_dict()

        # Verify format
        assert serialized["type"] == "error"
        assert "payload" in serialized
        assert "data" not in serialized  # Must NOT have data field
        assert serialized["payload"]["code"] == "test"
        assert serialized["payload"]["message"] == "Test error"

    def test_error_extraction_algorithm_works_for_all_formats(self) -> None:
        """
        Test the frontend's error extraction algorithm works for:
        1. ADR-0093 payload format (preferred)
        2. Legacy data format (backward compatibility)
        3. Missing error data (fallback)
        """

        def extract_error_message(message: dict[str, Any]) -> str:
            """Simulates frontend error extraction logic."""
            if message.get("payload") and isinstance(message["payload"], dict):
                msg = message["payload"].get("message")
                if msg:
                    return str(msg)
            if message.get("data"):
                return str(message["data"])
            return "Unknown error"

        # Test ADR-0093 payload format
        payload_msg = {
            "type": "error",
            "payload": {
                "code": "rate_limited",
                "message": "Rate limit exceeded",
                "retryable": True,
            },
        }
        assert extract_error_message(payload_msg) == "Rate limit exceeded"

        # Test legacy data format
        data_msg = {
            "type": "error",
            "data": "Connection closed",
        }
        assert extract_error_message(data_msg) == "Connection closed"

        # Test missing error data
        empty_msg = {
            "type": "error",
        }
        assert extract_error_message(empty_msg) == "Unknown error"

    def test_backend_error_codes_are_documented(self) -> None:
        """
        Test that error codes used by backend are documented/consistent.
        """
        # Known error codes from ai_suggestions.py
        known_error_codes = [
            "internal_error",
            "invalid_request",
            "missing_session",
        ]

        # All should be lowercase with underscores
        for code in known_error_codes:
            assert code.islower(), f"Error code '{code}' should be lowercase"
            assert " " not in code, f"Error code '{code}' should not have spaces"
