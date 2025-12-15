"""Tests for JWT utility functions.

Tests the shared user extraction logic used across middleware components.
Following TDD: Write tests FIRST, then implementation.
"""

import gc

import pytest

# Import will fail until we create the module (TDD RED phase)
# from mcp_server_langgraph.auth.jwt_utils import extract_user_from_jwt_payload

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.auth
@pytest.mark.xdist_group(name="jwt_utils_tests")
class TestExtractUserFromJWTPayload:
    """Test extract_user_from_jwt_payload function."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_extract_keycloak_token_with_preferred_username(self):
        """Test extraction from standard Keycloak token."""
        from mcp_server_langgraph.auth.jwt_utils import extract_user_from_jwt_payload

        payload = {
            "sub": "550e8400-e29b-41d4-a716-446655440000",
            "preferred_username": "alice",
            "email": "alice@acme.com",
            "realm_access": {"roles": ["user", "premium"]},
            "resource_access": {"my-client": {"roles": ["executor"]}},
        }

        result = extract_user_from_jwt_payload(payload)

        assert result["username"] == "alice"
        assert result["user_id"] == "user:alice"
        assert result["keycloak_id"] == "550e8400-e29b-41d4-a716-446655440000"
        assert result["email"] == "alice@acme.com"
        assert "user" in result["roles"]
        assert "premium" in result["roles"]
        assert "executor" in result["roles"]

    def test_extract_inmemory_token_with_direct_roles(self):
        """Test extraction from InMemoryUserProvider token."""
        from mcp_server_langgraph.auth.jwt_utils import extract_user_from_jwt_payload

        payload = {
            "sub": "user:bob",
            "username": "bob",
            "email": "bob@acme.com",
            "roles": ["admin", "developer"],
        }

        result = extract_user_from_jwt_payload(payload)

        assert result["username"] == "bob"
        assert result["user_id"] == "user:bob"  # Preserved from sub
        assert result["keycloak_id"] == "user:bob"
        assert result["email"] == "bob@acme.com"
        assert result["roles"] == ["admin", "developer"]

    def test_extract_worker_safe_id_from_sub(self):
        """Test extraction of worker-safe IDs for pytest-xdist."""
        from mcp_server_langgraph.auth.jwt_utils import extract_user_from_jwt_payload

        payload = {
            "sub": "user:test_gw0_charlie",
            "roles": ["user"],
        }

        result = extract_user_from_jwt_payload(payload)

        # Worker-safe ID should be preserved in user_id
        assert result["user_id"] == "user:test_gw0_charlie"
        # Username should extract the base name
        assert result["username"] == "charlie"
        assert result["keycloak_id"] == "user:test_gw0_charlie"

    def test_extract_fallback_to_sub_for_username(self):
        """Test fallback when neither preferred_username nor username present."""
        from mcp_server_langgraph.auth.jwt_utils import extract_user_from_jwt_payload

        payload = {
            "sub": "some-uuid-123",
            "email": "user@example.com",
        }

        result = extract_user_from_jwt_payload(payload)

        assert result["username"] == "some-uuid-123"
        assert result["user_id"] == "user:some-uuid-123"
        assert result["keycloak_id"] == "some-uuid-123"

    def test_extract_empty_roles_when_none_present(self):
        """Test that empty roles list returned when no roles in token."""
        from mcp_server_langgraph.auth.jwt_utils import extract_user_from_jwt_payload

        payload = {
            "sub": "user:test",
            "username": "test",
        }

        result = extract_user_from_jwt_payload(payload)

        assert result["roles"] == []

    def test_extract_handles_missing_sub_gracefully(self):
        """Test handling of token without sub claim."""
        from mcp_server_langgraph.auth.jwt_utils import extract_user_from_jwt_payload

        payload = {
            "preferred_username": "alice",
            "email": "alice@example.com",
        }

        result = extract_user_from_jwt_payload(payload)

        assert result["username"] == "alice"
        assert result["user_id"] == "user:alice"
        assert result["keycloak_id"] is None

    def test_extract_realm_access_roles_only(self):
        """Test extraction of realm_access roles without resource_access."""
        from mcp_server_langgraph.auth.jwt_utils import extract_user_from_jwt_payload

        payload = {
            "sub": "uuid-123",
            "preferred_username": "admin",
            "realm_access": {"roles": ["admin", "user"]},
        }

        result = extract_user_from_jwt_payload(payload)

        assert "admin" in result["roles"]
        assert "user" in result["roles"]
        assert len(result["roles"]) == 2

    def test_extract_resource_access_roles_only(self):
        """Test extraction of resource_access roles without realm_access."""
        from mcp_server_langgraph.auth.jwt_utils import extract_user_from_jwt_payload

        payload = {
            "sub": "uuid-123",
            "preferred_username": "service",
            "resource_access": {
                "client-a": {"roles": ["read"]},
                "client-b": {"roles": ["write", "admin"]},
            },
        }

        result = extract_user_from_jwt_payload(payload)

        assert "read" in result["roles"]
        assert "write" in result["roles"]
        assert "admin" in result["roles"]
        assert len(result["roles"]) == 3

    def test_extract_combined_realm_and_resource_roles(self):
        """Test extraction combines roles from both realm and resource access."""
        from mcp_server_langgraph.auth.jwt_utils import extract_user_from_jwt_payload

        payload = {
            "sub": "uuid-123",
            "preferred_username": "power-user",
            "realm_access": {"roles": ["user"]},
            "resource_access": {"my-app": {"roles": ["editor"]}},
        }

        result = extract_user_from_jwt_payload(payload)

        assert "user" in result["roles"]
        assert "editor" in result["roles"]

    def test_extract_ignores_invalid_realm_access_structure(self):
        """Test that invalid realm_access structure is handled gracefully."""
        from mcp_server_langgraph.auth.jwt_utils import extract_user_from_jwt_payload

        payload = {
            "sub": "uuid-123",
            "preferred_username": "test",
            "realm_access": "not-a-dict",  # Invalid structure
        }

        result = extract_user_from_jwt_payload(payload)

        assert result["roles"] == []

    def test_extract_ignores_invalid_resource_access_structure(self):
        """Test that invalid resource_access structure is handled gracefully."""
        from mcp_server_langgraph.auth.jwt_utils import extract_user_from_jwt_payload

        payload = {
            "sub": "uuid-123",
            "preferred_username": "test",
            "resource_access": {"client": "not-a-dict"},  # Invalid structure
        }

        result = extract_user_from_jwt_payload(payload)

        assert result["roles"] == []
