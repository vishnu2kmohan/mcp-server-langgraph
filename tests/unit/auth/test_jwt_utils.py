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


@pytest.mark.unit
@pytest.mark.auth
@pytest.mark.xdist_group(name="jwt_utils_tests")
class TestOrganizationalHierarchyExtraction:
    """Test organization, project, team extraction from JWT payload."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_extract_organization_from_direct_claim(self):
        """
        GIVEN: JWT payload with organization_id claim
        WHEN: Extracting user from payload
        THEN: organization_id should be in the result
        """
        from mcp_server_langgraph.auth.jwt_utils import extract_user_from_jwt_payload

        payload = {
            "sub": "uuid-123",
            "preferred_username": "alice",
            "organization_id": "acme-corp",
        }

        result = extract_user_from_jwt_payload(payload)

        assert result["organization_id"] == "organization:acme-corp"

    def test_extract_organization_from_org_id_claim(self):
        """
        GIVEN: JWT payload with org_id claim (alternate naming)
        WHEN: Extracting user from payload
        THEN: organization_id should be normalized from org_id
        """
        from mcp_server_langgraph.auth.jwt_utils import extract_user_from_jwt_payload

        payload = {
            "sub": "uuid-123",
            "preferred_username": "bob",
            "org_id": "contoso",
        }

        result = extract_user_from_jwt_payload(payload)

        assert result["organization_id"] == "organization:contoso"

    def test_extract_organization_from_groups(self):
        """
        GIVEN: JWT payload with Keycloak groups containing org path
        WHEN: Extracting user from payload
        THEN: organization_id should be parsed from groups
        """
        from mcp_server_langgraph.auth.jwt_utils import extract_user_from_jwt_payload

        payload = {
            "sub": "uuid-123",
            "preferred_username": "charlie",
            "groups": ["/org/acme", "/teams/platform", "/projects/backend"],
        }

        result = extract_user_from_jwt_payload(payload)

        assert result["organization_id"] == "organization:acme"

    def test_extract_organization_from_groups_alternate_format(self):
        """
        GIVEN: JWT payload with groups using 'organization/' prefix
        WHEN: Extracting user from payload
        THEN: organization_id should be extracted correctly
        """
        from mcp_server_langgraph.auth.jwt_utils import extract_user_from_jwt_payload

        payload = {
            "sub": "uuid-123",
            "preferred_username": "david",
            "groups": ["/organization/contoso", "/team/engineering"],
        }

        result = extract_user_from_jwt_payload(payload)

        assert result["organization_id"] == "organization:contoso"

    def test_extract_organization_preserves_prefix_if_already_present(self):
        """
        GIVEN: JWT payload with organization_id already prefixed
        WHEN: Extracting user from payload
        THEN: organization_id should not be double-prefixed
        """
        from mcp_server_langgraph.auth.jwt_utils import extract_user_from_jwt_payload

        payload = {
            "sub": "uuid-123",
            "preferred_username": "eve",
            "organization_id": "organization:already-prefixed",
        }

        result = extract_user_from_jwt_payload(payload)

        assert result["organization_id"] == "organization:already-prefixed"

    def test_extract_organization_none_when_not_present(self):
        """
        GIVEN: JWT payload without organization info
        WHEN: Extracting user from payload
        THEN: organization_id should be None
        """
        from mcp_server_langgraph.auth.jwt_utils import extract_user_from_jwt_payload

        payload = {
            "sub": "uuid-123",
            "preferred_username": "frank",
        }

        result = extract_user_from_jwt_payload(payload)

        assert result["organization_id"] is None

    def test_extract_project_and_team_from_claims(self):
        """
        GIVEN: JWT payload with project_id and team_id claims
        WHEN: Extracting user from payload
        THEN: project_id and team_id should be in the result
        """
        from mcp_server_langgraph.auth.jwt_utils import extract_user_from_jwt_payload

        payload = {
            "sub": "uuid-123",
            "preferred_username": "grace",
            "project_id": "backend-api",
            "team_id": "platform-engineering",
        }

        result = extract_user_from_jwt_payload(payload)

        assert result["project_id"] == "project:backend-api"
        assert result["team_id"] == "team:platform-engineering"

    def test_extract_project_and_team_from_groups(self):
        """
        GIVEN: JWT payload with Keycloak groups containing project and team paths
        WHEN: Extracting user from payload
        THEN: project_id and team_id should be parsed from groups
        """
        from mcp_server_langgraph.auth.jwt_utils import extract_user_from_jwt_payload

        payload = {
            "sub": "uuid-123",
            "preferred_username": "henry",
            "groups": ["/org/acme", "/project/frontend", "/team/ui-ux"],
        }

        result = extract_user_from_jwt_payload(payload)

        assert result["organization_id"] == "organization:acme"
        assert result["project_id"] == "project:frontend"
        assert result["team_id"] == "team:ui-ux"

    def test_direct_claims_take_precedence_over_groups(self):
        """
        GIVEN: JWT payload with both direct claims and groups
        WHEN: Extracting user from payload
        THEN: Direct claims should take precedence over groups
        """
        from mcp_server_langgraph.auth.jwt_utils import extract_user_from_jwt_payload

        payload = {
            "sub": "uuid-123",
            "preferred_username": "ivy",
            "organization_id": "direct-org",
            "groups": ["/org/group-org"],  # Should be ignored
        }

        result = extract_user_from_jwt_payload(payload)

        # Direct claim wins
        assert result["organization_id"] == "organization:direct-org"
