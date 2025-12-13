"""
Tests for JWT user extraction in Playground authentication.

Tests the verify_playground_auth function to ensure it correctly
extracts user information from JWT tokens in development/test mode.

TDD: These tests were written FIRST to define expected behavior,
then implementation was updated to make them pass.

Follows memory safety patterns for pytest-xdist.
"""

import base64
import gc
import json
import os
from unittest.mock import patch

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.playground, pytest.mark.auth]


def create_mock_jwt(payload: dict) -> str:
    """Create a mock JWT token with the given payload.

    JWT format: header.payload.signature (base64url encoded)
    For testing, we only need a valid payload section.
    """
    header = {"alg": "RS256", "typ": "JWT"}
    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    signature = "mock_signature"
    return f"{header_b64}.{payload_b64}.{signature}"


@pytest.mark.xdist_group(name="playground_auth_jwt")
class TestVerifyPlaygroundAuthJWTExtraction:
    """Test JWT user extraction in verify_playground_auth."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_extracts_username_from_preferred_username_claim(self) -> None:
        """Test that preferred_username claim is extracted from JWT."""
        from mcp_server_langgraph.playground.api.server import verify_playground_auth

        jwt_payload = {
            "preferred_username": "alice",
            "sub": "user-uuid-123",
            "realm_access": {"roles": ["user", "offline_access"]},
        }
        token = create_mock_jwt(jwt_payload)
        authorization = f"Bearer {token}"

        with patch.dict(os.environ, {"ENVIRONMENT": "test"}):
            result = verify_playground_auth(authorization)

        assert result is not None
        assert result["user_id"] == "alice"

    @pytest.mark.unit
    def test_extracts_username_from_username_claim_fallback(self) -> None:
        """Test that username claim is used when preferred_username is missing."""
        from mcp_server_langgraph.playground.api.server import verify_playground_auth

        jwt_payload = {
            "username": "bob",
            "sub": "user-uuid-456",
            "realm_access": {"roles": ["user"]},
        }
        token = create_mock_jwt(jwt_payload)
        authorization = f"Bearer {token}"

        with patch.dict(os.environ, {"ENVIRONMENT": "test"}):
            result = verify_playground_auth(authorization)

        assert result is not None
        assert result["user_id"] == "bob"

    @pytest.mark.unit
    def test_extracts_username_from_sub_claim_fallback(self) -> None:
        """Test that sub claim is used when username claims are missing."""
        from mcp_server_langgraph.playground.api.server import verify_playground_auth

        jwt_payload = {
            "sub": "user-uuid-789",
            "realm_access": {"roles": ["user"]},
        }
        token = create_mock_jwt(jwt_payload)
        authorization = f"Bearer {token}"

        with patch.dict(os.environ, {"ENVIRONMENT": "test"}):
            result = verify_playground_auth(authorization)

        assert result is not None
        assert result["user_id"] == "user-uuid-789"

    @pytest.mark.unit
    def test_extracts_roles_from_realm_access(self) -> None:
        """Test that roles are extracted from realm_access.roles claim."""
        from mcp_server_langgraph.playground.api.server import verify_playground_auth

        jwt_payload = {
            "preferred_username": "alice",
            "realm_access": {"roles": ["user", "premium", "offline_access"]},
        }
        token = create_mock_jwt(jwt_payload)
        authorization = f"Bearer {token}"

        with patch.dict(os.environ, {"ENVIRONMENT": "test"}):
            result = verify_playground_auth(authorization)

        assert result is not None
        assert "user" in result["roles"]
        assert "premium" in result["roles"]

    @pytest.mark.unit
    def test_returns_dev_user_when_no_authorization_header(self) -> None:
        """Test that dev-user is returned when no token is provided."""
        from mcp_server_langgraph.playground.api.server import verify_playground_auth

        with patch.dict(os.environ, {"ENVIRONMENT": "test"}):
            result = verify_playground_auth(None)

        assert result is not None
        assert result["user_id"] == "dev-user"
        assert "user" in result["roles"]

    @pytest.mark.unit
    def test_returns_dev_user_when_jwt_decoding_fails(self) -> None:
        """Test that dev-user is returned when JWT cannot be decoded."""
        from mcp_server_langgraph.playground.api.server import verify_playground_auth

        # Invalid JWT format
        authorization = "Bearer invalid.jwt.token"

        with patch.dict(os.environ, {"ENVIRONMENT": "test"}):
            result = verify_playground_auth(authorization)

        assert result is not None
        assert result["user_id"] == "dev-user"

    @pytest.mark.unit
    def test_handles_jwt_with_padding_issues(self) -> None:
        """Test that JWT with base64 padding issues is handled correctly."""
        from mcp_server_langgraph.playground.api.server import verify_playground_auth

        # Create a JWT where the payload might need padding
        jwt_payload = {
            "preferred_username": "charlie",
            "sub": "x",  # Short to test padding
        }
        token = create_mock_jwt(jwt_payload)
        authorization = f"Bearer {token}"

        with patch.dict(os.environ, {"ENVIRONMENT": "test"}):
            result = verify_playground_auth(authorization)

        assert result is not None
        assert result["user_id"] == "charlie"
