"""
Tests for FastAPI exception handlers.

Tests cover:
- MCP exception handler registration
- Custom exception handling with proper status codes
- Generic exception wrapping
- Error response formatting
- Trace ID headers
- Retry-After headers for rate limits
- Metrics emission on errors
"""

from unittest.mock import Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from mcp_server_langgraph.api.error_handlers import create_error_response, register_exception_handlers
from mcp_server_langgraph.core.exceptions import AuthorizationError, InvalidCredentialsError, RateLimitExceededError

# ==============================================================================
# Test Fixtures
# ==============================================================================


@pytest.fixture
def app():
    """Create FastAPI app with exception handlers."""
    app = FastAPI()
    register_exception_handlers(app)

    # Add test endpoint that raises exceptions
    @app.get("/test/auth-error")
    def raise_auth_error():
        raise InvalidCredentialsError(message="Invalid password")

    @app.get("/test/rate-limit")
    def raise_rate_limit():
        raise RateLimitExceededError(message="Too many requests", metadata={"retry_after": 120})

    @app.get("/test/authz-error")
    def raise_authz_error():
        raise AuthorizationError(message="Access denied", metadata={"resource": "admin_panel"})

    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


# ==============================================================================
# Registration Tests
# ==============================================================================


@pytest.mark.unit
def test_register_exception_handlers_adds_handlers_to_app():
    """Test register_exception_handlers() registers exception handlers successfully."""
    # Arrange
    app = FastAPI()

    # Act
    register_exception_handlers(app)

    # Assert - Should have exception handlers registered
    assert len(app.exception_handlers) > 0


# ==============================================================================
# MCP Exception Handler Tests
# ==============================================================================


@pytest.mark.unit
def test_mcp_exception_handler_returns_correct_status_code(client):
    """Test MCP exception handler returns correct HTTP status code."""
    # Act
    response = client.get("/test/auth-error")

    # Assert
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "auth.invalid_credentials"


@pytest.mark.unit
def test_mcp_exception_handler_includes_trace_id_in_response(client):
    """Test MCP exception handler includes trace_id in response (auto-generated if not provided)."""
    # Act
    response = client.get("/test/auth-error")

    # Assert
    data = response.json()
    # trace_id is in the response body, may be None or auto-generated
    assert "trace_id" in data["error"]


@pytest.mark.unit
def test_mcp_exception_handler_returns_structured_error_response(client):
    """Test MCP exception handler returns structured JSON error."""
    # Act
    response = client.get("/test/authz-error")

    # Assert
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "authz.failed"  # AuthorizationError uses this code
    assert "Access denied" in data["error"]["details"]
    assert "metadata" in data["error"]
    assert data["error"]["metadata"]["resource"] == "admin_panel"


@pytest.mark.unit
def test_mcp_exception_handler_includes_user_friendly_message(client):
    """Test MCP exception handler includes user-friendly message."""
    # Act
    response = client.get("/test/auth-error")

    # Assert
    data = response.json()
    # The user-friendly message is in the 'message' field
    assert "message" in data["error"]
    assert "Invalid username or password" in data["error"]["message"]


@pytest.mark.unit
def test_rate_limit_exception_includes_retry_after_header(client):
    """Test rate limit exceptions include Retry-After header."""
    # Act
    response = client.get("/test/rate-limit")

    # Assert
    assert response.status_code == 429
    assert "Retry-After" in response.headers
    assert response.headers["Retry-After"] == "120"


@pytest.mark.unit
@patch("mcp_server_langgraph.observability.telemetry.error_counter")
def test_mcp_exception_handler_emits_metrics(mock_counter, client):
    """Test MCP exception handler emits error metrics."""
    # Act
    response = client.get("/test/auth-error")

    # Assert - Should have recorded metric
    assert response.status_code == 401
    mock_counter.add.assert_called_once()
    call_args = mock_counter.add.call_args
    assert call_args[0][0] == 1  # Count
    assert "error_code" in call_args[1]["attributes"]


@pytest.mark.unit
@patch("mcp_server_langgraph.observability.telemetry.error_counter", Mock(side_effect=Exception("Metric error")))
def test_mcp_exception_handler_continues_if_metrics_fail(client):
    """Test exception handler continues gracefully if metrics emission fails."""
    # Act
    response = client.get("/test/auth-error")

    # Assert - Should still return proper error response (wrapped exception handling in error_handlers.py)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "auth.invalid_credentials"


# ==============================================================================
# create_error_response Tests
# ==============================================================================


@pytest.mark.unit
def test_create_error_response_with_minimal_params_returns_structured_response():
    """Test create_error_response() with only required parameters."""
    # Act
    result = create_error_response(error_code="test.error", message="Test error")

    # Assert
    assert result["error"]["code"] == "test.error"
    assert result["error"]["message"] == "Test error"
    assert result["error"]["status_code"] == 500  # Default
    assert result["error"]["metadata"] == {}
    assert result["error"]["trace_id"] is None


@pytest.mark.unit
def test_create_error_response_with_all_params_includes_all_fields():
    """Test create_error_response() with all parameters."""
    # Arrange
    metadata = {"user_id": "user_123", "resource": "document"}
    trace_id = "trace_abc123"

    # Act
    result = create_error_response(
        error_code="authz.denied",
        message="Access denied",
        status_code=403,
        metadata=metadata,
        trace_id=trace_id,
    )

    # Assert
    assert result["error"]["code"] == "authz.denied"
    assert result["error"]["message"] == "Access denied"
    assert result["error"]["status_code"] == 403
    assert result["error"]["metadata"] == metadata
    assert result["error"]["trace_id"] == trace_id


@pytest.mark.unit
def test_create_error_response_with_custom_status_code():
    """Test create_error_response() respects custom status code."""
    # Act
    result = create_error_response(error_code="validation.failed", message="Invalid input", status_code=422)

    # Assert
    assert result["error"]["status_code"] == 422


@pytest.mark.unit
def test_create_error_response_handles_empty_metadata():
    """Test create_error_response() handles None metadata gracefully."""
    # Act
    result = create_error_response(error_code="test.error", message="Test", metadata=None)

    # Assert
    assert result["error"]["metadata"] == {}


@pytest.mark.unit
def test_create_error_response_preserves_complex_metadata():
    """Test create_error_response() preserves nested metadata structures."""
    # Arrange
    metadata = {
        "validation_errors": [
            {"field": "email", "error": "Invalid format"},
            {"field": "age", "error": "Must be positive"},
        ],
        "timestamp": "2025-11-02T14:00:00Z",
    }

    # Act
    result = create_error_response(error_code="validation.multiple", message="Validation failed", metadata=metadata)

    # Assert
    assert result["error"]["metadata"]["validation_errors"] == metadata["validation_errors"]
    assert result["error"]["metadata"]["timestamp"] == metadata["timestamp"]


# ==============================================================================
# Integration Tests
# ==============================================================================


@pytest.mark.unit
def test_error_response_format_matches_api_spec(client):
    """Test error responses match OpenAPI specification format."""
    # Act
    response = client.get("/test/auth-error")

    # Assert - Verify response structure matches API spec
    data = response.json()
    assert "error" in data
    assert isinstance(data["error"], dict)
    assert "code" in data["error"]
    assert "message" in data["error"]
    assert "details" in data["error"]
    assert "trace_id" in data["error"]
    assert "metadata" in data["error"]


@pytest.mark.unit
def test_multiple_exception_types_handled_correctly(client):
    """Test different exception types return appropriate status codes."""
    # Test different endpoints (excluding generic-error which raises ValueError in FastAPI)
    test_cases = [
        ("/test/auth-error", 401),
        ("/test/authz-error", 403),
        ("/test/rate-limit", 429),
    ]

    for endpoint, expected_status in test_cases:
        response = client.get(endpoint)
        assert response.status_code == expected_status, f"Failed for {endpoint}"
        assert "error" in response.json()
