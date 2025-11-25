"""
Unit tests for auth/middleware.py helper functions and models.

Tests utility functions and Pydantic models in the middleware module.
Follows TDD principles and memory safety patterns for pytest-xdist.
"""

import gc

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="middleware_helpers")
class TestNormalizeUserId:
    """Test normalize_user_id helper function."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_normalize_plain_username(self):
        """Test that plain username is returned unchanged."""
        from mcp_server_langgraph.auth.middleware import normalize_user_id

        assert normalize_user_id("alice") == "alice"
        assert normalize_user_id("bob") == "bob"

    @pytest.mark.unit
    def test_normalize_prefixed_user_id(self):
        """Test that user: prefix is removed."""
        from mcp_server_langgraph.auth.middleware import normalize_user_id

        assert normalize_user_id("user:alice") == "alice"
        assert normalize_user_id("user:bob") == "bob"

    @pytest.mark.unit
    def test_normalize_other_prefixes(self):
        """Test that other prefixes are also removed."""
        from mcp_server_langgraph.auth.middleware import normalize_user_id

        assert normalize_user_id("uid:123") == "123"
        assert normalize_user_id("id:user-456") == "user-456"

    @pytest.mark.unit
    def test_normalize_empty_string(self):
        """Test that empty string is returned unchanged."""
        from mcp_server_langgraph.auth.middleware import normalize_user_id

        assert normalize_user_id("") == ""

    @pytest.mark.unit
    def test_normalize_none_like(self):
        """Test behavior with empty/falsy values."""
        from mcp_server_langgraph.auth.middleware import normalize_user_id

        # Empty string should return empty string
        assert normalize_user_id("") == ""


@pytest.mark.xdist_group(name="middleware_helpers")
class TestAuthorizationResult:
    """Test AuthorizationResult Pydantic model."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_create_authorized_result(self):
        """Test creating an authorized result."""
        from mcp_server_langgraph.auth.middleware import AuthorizationResult

        result = AuthorizationResult(
            authorized=True,
            user_id="user:alice",
            relation="executor",
            resource="tool:chat",
            reason=None,
            used_fallback=False,
        )

        assert result.authorized is True
        assert result.user_id == "user:alice"
        assert result.relation == "executor"
        assert result.resource == "tool:chat"
        assert result.reason is None
        assert result.used_fallback is False

    @pytest.mark.unit
    def test_create_denied_result(self):
        """Test creating a denied result with reason."""
        from mcp_server_langgraph.auth.middleware import AuthorizationResult

        result = AuthorizationResult(
            authorized=False,
            user_id="user:bob",
            relation="admin",
            resource="system:config",
            reason="User does not have admin role",
            used_fallback=False,
        )

        assert result.authorized is False
        assert result.reason == "User does not have admin role"

    @pytest.mark.unit
    def test_to_dict_method(self):
        """Test to_dict conversion method."""
        from mcp_server_langgraph.auth.middleware import AuthorizationResult

        result = AuthorizationResult(
            authorized=True,
            user_id="user:alice",
            relation="viewer",
            resource="conversation:123",
        )

        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict["authorized"] is True
        assert result_dict["user_id"] == "user:alice"

    @pytest.mark.unit
    def test_authorization_result_with_fallback_flag_set_to_true(self):
        """Test used_fallback flag when fallback authorization is used."""
        from mcp_server_langgraph.auth.middleware import AuthorizationResult

        result = AuthorizationResult(
            authorized=True,
            user_id="user:alice",
            relation="executor",
            resource="tool:chat",
            used_fallback=True,  # Indicates fallback auth was used
        )

        assert result.used_fallback is True


@pytest.mark.xdist_group(name="middleware_helpers")
class TestTokenVerificationModel:
    """Test TokenVerification model."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_valid_token_verification(self):
        """Test creating a valid token verification result."""
        from mcp_server_langgraph.auth.middleware import TokenVerification

        result = TokenVerification(
            valid=True,
            payload={"sub": "user:alice", "roles": ["user", "admin"]},
            error=None,
        )

        assert result.valid is True
        assert result.payload["sub"] == "user:alice"
        assert result.error is None

    @pytest.mark.unit
    def test_invalid_token_verification(self):
        """Test creating an invalid token verification result."""
        from mcp_server_langgraph.auth.middleware import TokenVerification

        result = TokenVerification(
            valid=False,
            payload=None,
            error="Token expired",
        )

        assert result.valid is False
        assert result.payload is None
        assert result.error == "Token expired"


@pytest.mark.xdist_group(name="middleware_helpers")
class TestAuthResponseModel:
    """Test AuthResponse model."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_successful_auth_response(self):
        """Test creating a successful auth response."""
        from mcp_server_langgraph.auth.middleware import AuthResponse

        response = AuthResponse(
            authorized=True,
            user_id="user:alice",
            username="alice",
            roles=["user", "admin"],
            error=None,
        )

        assert response.authorized is True
        assert response.user_id == "user:alice"
        assert response.username == "alice"
        assert "admin" in response.roles

    @pytest.mark.unit
    def test_failed_auth_response(self):
        """Test creating a failed auth response."""
        from mcp_server_langgraph.auth.middleware import AuthResponse

        response = AuthResponse(
            authorized=False,
            user_id=None,
            username=None,
            roles=[],
            error="Invalid credentials",
        )

        assert response.authorized is False
        assert response.error == "Invalid credentials"
